#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 08 —— 去重与真实地址数（纯报告，只读自家的 Release，不动任何数据）

问题：三步采下来 8,360 万行，但 KS 采了 111 个层叠加 → 覆盖率算出 415%。
     需要回答「独立地址到底多少」。

做法：
  1. 列 Release（按 steps.json 的 tag_prefixes 过滤）
  2. 逐层下载 part 包 → 解压 → 流式解析每行的 `addr_key`（采集时已写好，md5 前 16 位）
  3. **按州**精确去重（州内一个 set，处理完就丢，峰值只跟最大州有关）
  4. 额外给「重复来源 Top」：每州取前 3 层做两两重叠抽样

输出：
  collect/reports/DEDUP_REPORT.md
  collect/dedup_status.json

用法：
  python3 collect/dedup.py                 # 全量
  python3 collect/dedup.py --limit-layers 40   # 只跑 40 层（自测）
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
PLAN_F = os.path.join(HERE, "layer_plan.csv")
STEPS_F = os.path.join(HERE, "steps.json")
OUT_MD = os.path.join(HERE, "reports", "DEDUP_REPORT.md")
OUT_JSON = os.path.join(HERE, "dedup_status.json")
HU = {  # 2020 Census 住房单元数（覆盖率分母）
    "AL": 2270000, "AK": 328000, "AZ": 3030000, "AR": 1370000, "CA": 14300000, "CO": 2500000,
    "CT": 1520000, "DE": 450000, "DC": 340000, "FL": 9800000, "GA": 4400000, "HI": 590000,
    "ID": 740000, "IL": 5400000, "IN": 2900000, "IA": 1400000, "KS": 1300000, "KY": 2000000,
    "LA": 2000000, "ME": 740000, "MD": 2500000, "MA": 2900000, "MI": 4600000, "MN": 2400000,
    "MS": 1300000, "MO": 2800000, "MT": 510000, "NE": 840000, "NV": 1200000, "NH": 640000,
    "NJ": 3700000, "NM": 900000, "NY": 8300000, "NC": 4500000, "ND": 360000, "OH": 5100000,
    "OK": 1700000, "OR": 1700000, "PA": 5600000, "RI": 470000, "SC": 2200000, "SD": 380000,
    "TN": 2900000, "TX": 11000000, "UT": 1100000, "VT": 330000, "WA": 3100000, "WV": 880000,
    "WI": 2700000, "WY": 280000, "PR": 1400000,
}
LOCK = threading.Lock()


def gh(args, timeout=600, binary=False):
    r = subprocess.run(["gh"] + args, capture_output=True, timeout=timeout)
    return r.returncode, (r.stdout if binary else r.stdout.decode("utf-8", "replace")), r.stderr.decode("utf-8", "replace")


def cfg():
    return json.load(open(STEPS_F, encoding="utf-8")).get("steps", {}).get("08") or {}


def plan_map():
    out = {}
    if os.path.exists(PLAN_F):
        for row in csv.DictReader(open(PLAN_F, encoding="utf-8")):
            out[row["layer_id"]] = row
    return out


def state_of(layer, plan):
    r = plan.get(layer) or plan.get(layer.split("@")[0])
    if r and r.get("state"):
        return r["state"]
    if "@" in layer:
        return layer.rsplit("@", 1)[1].rsplit("-", 1)[0] or "未定位"
    return "未定位"


def list_releases(prefixes):
    rels = []
    page = 1
    while page <= 8:
        rc, out, err = gh(["api", "repos/%s/releases?per_page=100&page=%d" % (REPO, page)])
        if rc != 0:
            print("⚠️ 列 release 失败：%s" % err[:120])
            break
        batch = json.loads(out or "[]")
        if not batch:
            break
        rels += batch
        if len(batch) < 100:
            break
        page += 1
    keep = []
    for r in rels:
        tag = r.get("tag_name") or ""
        if not any(tag.startswith(p) for p in prefixes):
            continue
        parts = [a for a in (r.get("assets") or [])
                 if (a.get("name") or "").endswith((".tar.gz", ".ndjson.gz"))]
        if parts:
            keep.append({"tag": tag, "layer": tag.split("-", 2)[-1], "assets": parts,
                         "bytes": sum(a.get("size") or 0 for a in parts)})
    return keep


FULL_FIELDS = ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION")


def _fallback_key(rec):
    """addr_key 只在「门牌号+街道名」都有值时才生成；实测 2/3 的行没有 addr_key。
    这些行用「完整地址串」或「经纬度」做哈希兜底，否则去重等于把它们当透明。"""
    raw = rec.get("raw") or {}
    full = ""
    for f in FULL_FIELDS:
        v = raw.get(f) or raw.get(f.lower()) or raw.get(f.title())
        if v:
            full = str(v).strip().upper()
            break
    if not full:
        lat, lon = rec.get("lat"), rec.get("lon")
        if lat is not None and lon is not None:
            full = "%.5f,%.5f" % (float(lat), float(lon))
    if not full:
        return None
    return "fb:" + hashlib.md5(full.encode("utf-8", "replace")).hexdigest()[:16]


def digests_from_tar(path, tmpdir):
    """从一个 tar.gz 里抠出该层的去重键集合 + 统计（总行 / 无键行）。"""
    keys = set()
    stats = {"rows": 0, "no_key": 0}
    try:
        with tarfile.open(path, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
                if m.name.endswith(".gz"):
                    try:
                        data = gzip.decompress(data)
                    except Exception:
                        continue
                for line in data.splitlines():
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    stats["rows"] += 1
                    k = rec.get("addr_key") or _fallback_key(rec)
                    if k:
                        keys.add(k)
                    else:
                        stats["no_key"] += 1
    except Exception as e:
        print("  ⚠️ 解包失败 %s：%s" % (os.path.basename(path), str(e)[:80]))
    return keys, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    limit = 0
    if "--limit-layers" in argv:
        limit = int(argv[argv.index("--limit-layers") + 1])

    c = cfg()
    prefixes = c.get("tag_prefixes") or ["collect-step"]
    rels = list_releases(prefixes)
    if limit:
        rels = rels[:limit]
    plan = plan_map()
    print("[dedup] %d 个有数据资产的层，合计 %.1f GB" % (len(rels), sum(r["bytes"] for r in rels) / 1024**3))

    # 按州分组，逐州处理（内存只受最大州影响）
    by_state = {}
    for r in rels:
        by_state.setdefault(state_of(r["layer"], plan), []).append(r)

    tmpdir = tempfile.mkdtemp(prefix="dedup-")
    result = {}
    for st in sorted(by_state, key=lambda s: -len(by_state[s])):
        layers = by_state[st]
        keys = set()
        raw = 0
        saw_rows = 0
        no_key = 0
        per_layer = []
        for r in layers:
            tag = r["tag"]
            rc, out, err = gh(["release", "download", tag, "--repo", REPO,
                              "--pattern", "*.tar.gz", "--dir", tmpdir, "--clobber"])
            got = set()
            st_rows = 0
            if rc == 0:
                for fn in os.listdir(tmpdir):
                    if fn.startswith(r["layer"]) and fn.endswith(".tar.gz"):
                        g, stt = digests_from_tar(os.path.join(tmpdir, fn), tmpdir)
                        got |= g
                        st_rows += stt["rows"]
                        no_key += stt["no_key"]
                        os.remove(os.path.join(tmpdir, fn))
            saw_rows += st_rows
            per_layer.append({"layer": r["layer"], "unique": len(got)})
            keys |= got
            raw += len(got)
        result[st] = {"layers": len(layers), "rows_scanned": saw_rows, "rows_no_key": no_key,
                      "layer_unique_sum": raw, "unique": len(keys), "per_layer": per_layer[:5]}
        print("  %s: %d 层 / 层内合计 %s / 州内独立 %s" % (st, len(layers), format(raw, ","), format(len(keys), ",")))

    total_scanned = sum(v["rows_scanned"] for v in result.values())
    total_no_key = sum(v["rows_no_key"] for v in result.values())
    total_raw = sum(v["layer_unique_sum"] for v in result.values())
    total_unique = sum(v["unique"] for v in result.values())
    lines = ["# 三仓采集 · 去重报告（addr_key 精确去重）", "",
             "- 参与层数：**%d**" % len(rels),
             "- 扫描行数：**%s**（其中无任何去重键 %s 行）" % (
                 format(total_scanned, ","), format(total_no_key, ",")),
             "- 层内去重后行数合计：**%s**" % format(total_raw, ","),
             "- 跨层去重后独立地址：**%s**" % format(total_unique, ","),
             "- 重复量：%s（重复率 %.1f%%）" % (format(total_raw - total_unique, ","),
                                       100 * (total_raw - total_unique) / max(total_raw, 1)),
             "", "## 各州独立地址数与真实覆盖率", "",
             "| 州 | 层数 | 层内合计 | 独立地址 | 重复率 | 住房单元 | 真实覆盖率 |",
             "|---|---|---|---|---|---|---|"]
    for st in sorted(result, key=lambda s: -result[s]["unique"]):
        v = result[st]
        hu = HU.get(st)
        dup = 1 - v["unique"] / max(v["layer_unique_sum"], 1)
        cov = "%d%%" % round(100 * v["unique"] / hu) if hu else "—"
        lines.append("| %s | %d | %s | %s | %.0f%% | %s | %s |" % (
            st, v["layers"], format(v["layer_unique_sum"], ","), format(v["unique"], ","),
            dup * 100, format(hu, ",") if hu else "—", cov))
    lines += ["", "## 怎么读这张表", "",
              "- `层内合计` = 每层自己去重后相加（等于忽略跨层重复的口径）",
              "- `独立地址` = 州内把所有层的 addr_key 合并去重后的真实数量",
              "- `真实覆盖率` = 独立地址 ÷ Census 住房单元数（>100% 说明该州有非住宅地址点或跨州数据）"]
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"layers": len(rels), "rows_scanned": total_scanned, "rows_no_key": total_no_key,
               "total_layer_unique": total_raw,
               "total_unique": total_unique, "states": len(result), "detail": result},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"layers": len(rels), "scanned": total_scanned, "no_key": total_no_key,
                      "unique": total_unique, "dup_rate":
                      round(1 - total_unique / max(total_raw, 1), 4), "states": len(result)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
