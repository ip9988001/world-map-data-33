#!/usr/bin/env python3
"""Phase 2：本地已采层全量离线盘点（零网络）。

扫 `dist/intake-full/layers/<layer>/` 下所有 `{table}.{layer}.ndjson.gz`（08 去重索引的
规范化中间件，不是原始上游字段），逐层抽样 → 层级表 + 字段级表。

抽样口径（写死，不许含糊）：
  · 每层**每表**最多 200 行（不足 200 全取），`denom` = 该表该层**实际**抽到的行数
  · `nonnull_rate = nonnull / denom`，`nonnull_rate_basis=sample200`
  · 精确全表非空率本轮**不做**（第二轮按需）

输出：
  analysis/full-inventory-20261124/inventory-local-all.csv     层级（一层一行）
  analysis/full-inventory-20261124/inventory-local-fields.csv  字段级（一层一表一字段一行）

用法：
  python3 analysis/full_inventory_local.py --workers 8 [--limit N] [--sample 200]
参数化：--dist 指向任意 intake 目录；不硬编码任何州名/州路径。
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import itertools
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "analysis", "full-inventory-20261124")
DEFAULT_DIST = "/data/workspace/world-map-data-33/dist/intake-full"
RELEASE_INDEX = "/data/workspace/world-map-data-33/collect/.release_index.json"
sys.path.insert(0, os.path.join(REPO, "sandbox"))
import rules  # noqa: E402

BASIS = "sample200"
_CORE = ("number", "street", "city", "state", "zip")


def stage_of(lid: str, idx: dict) -> str:
    for k in ("step10", "step04", "step05", "step07", "step03"):
        if lid in idx.get(k, {}):
            return k
    return "unknown"


def read_sample(path: str, limit: int):
    """流式取前 limit 行（gzip），返回 (rows, bad_lines)。"""
    rows, bad = [], 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
            for line in itertools.islice(f, limit):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    bad += 1
    except Exception as e:  # noqa: BLE001
        return rows, bad, f"read_err:{type(e).__name__}"
    return rows, bad, ""


def typename(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, (list, dict)):
        return type(v).__name__
    return "str"


def nonblank(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        return bool(v)
    return True


def scan_layer(args):
    """一个层目录：抽样 + 汇总。纯本地读，无网络。"""
    d, limit, idx_stage = args
    name = os.path.basename(d)
    files, total_b, errs = {}, 0, []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".ndjson.gz"):
            continue
        p = os.path.join(d, fn)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        total_b += sz
        if sz > 0:
            files[fn.split(".", 1)[0]] = p

    led = {}
    lp = os.path.join(d, "ledger.json")
    if os.path.exists(lp):
        try:
            led = json.load(open(lp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            led = {}

    fields_rows, samples = [], {}
    per_table = {}
    url, state_mode, kind_mode = "", "", ""
    for table, p in files.items():
        rows, bad, err = read_sample(p, limit)
        if err:
            errs.append(f"{table}:{err}")
        per_table[table] = len(rows)
        if not rows:
            continue
        keys = []
        seen = set()
        for r in rows:
            for k in r:
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        stats = []
        for k in keys:
            vals = [r.get(k) for r in rows]
            nb = [v for v in vals if nonblank(v)]
            types = sorted({typename(r.get(k)) for r in rows})
            stats.append({"table": table, "field": k, "types": "|".join(types),
                          "nonnull": len(nb), "denom": len(rows),
                          "rate": round(len(nb) / len(rows), 4) if rows else 0.0,
                          "samples": " | ".join(str(v)[:80] for v in nb[:3])})
        fields_rows.extend(stats)
        samples[table] = rows
        if table == "addr":
            cs = [rules.canonical(r) for r in rows]
            url = url or next((str(r.get("src_layer_url") or "") for r in rows if r.get("src_layer_url")), "")
            st = collections.Counter(str(r.get("state_abbr")) for r in rows if r.get("state_abbr"))
            state_mode = st.most_common(1)[0][0] if st else ""
            kd = collections.Counter(str(r.get("src_kind")) for r in rows if r.get("src_kind"))
            kind_mode = kd.most_common(1)[0][0] if kd else ""

    # 层级判定：优先用 addr 表，其次任何有 canonical 字段的表
    judge_rows = []
    for t in ("addr", "aux_parcel", "aux_addr_nohouse", "aux_street", "reject"):
        if samples.get(t):
            judge_rows = samples[t]
            break
    core_hit, group, cls = "", "", ""
    if judge_rows:
        cs = [rules.canonical(r) for r in judge_rows]
        hit = {f: sum(1 for c in cs if nonblank(c.get(f))) / len(cs) >= 0.5 for f in _CORE}
        core_hit = "".join("1" if hit[f] else "0" for f in _CORE)   # number|street|city|state|zip
        votes = collections.Counter(rules.field_group(r) for r in judge_rows)
        group = votes.most_common(1)[0][0]
        kls = collections.Counter(rules.classify(r) for r in judge_rows)
        cls = kls.most_common(1)[0][0]
    else:
        group = ""          # 无数据文件 → 不是 empty_shell，是「本地不可读」
        cls = ""

    readable = bool(files)
    if not judge_rows:
        group, cls = "sampled_zero_rows", ""
    rows_total = led.get("rows_total")
    return {
        "layer": name, "layer_dir": d, "readable": int(readable),
        "url": url, "source": idx_stage, "state": state_mode, "src_kind": kind_mode,
        "geom": "point" if judge_rows else "",
        "rows": rows_total if rows_total is not None else "",
        "rows_source": "intake-ledger rows_total" if rows_total is not None else "unavailable",
        "fields_n": len({s["field"] for s in fields_rows}),
        "tables": ",".join(sorted(files)),
        "tables_sampled": json.dumps(per_table, ensure_ascii=False),
        "addr_core_hit": core_hit, "class": cls, "usable": group,
        "bytes": total_b,
        "ledger_status": led.get("status", ""), "note": ";".join(errs)[:200],
        "_fields": fields_rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=DEFAULT_DIST)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--sample", type=int, default=200)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 层（灰度）")
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()

    idx = json.load(open(RELEASE_INDEX, encoding="utf-8"))["data"]
    base = os.path.join(a.dist, "layers")
    dirs = [os.path.join(base, n) for n in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, n))]
    if a.limit:
        dirs = dirs[:a.limit]
    os.makedirs(a.outdir, exist_ok=True)
    t0 = time.time()
    tasks = [(d, a.sample, stage_of(os.path.basename(d), idx)) for d in dirs]
    done, layer_rows, fields_rows = 0, [], []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for res in ex.map(scan_layer, tasks, chunksize=4):
            done += 1
            f = res.pop("_fields")
            layer_rows.append(res)
            fields_rows.extend(dict(layer=res["layer"], layer_dir=res["layer_dir"],
                                    url=res["url"], source=res["source"], state=res["state"],
                                    nonnull_rate_basis=BASIS, **x) for x in f)
            if done % 100 == 0:
                print(f"  scanned {done}/{len(dirs)} layers  {time.time()-t0:.0f}s", flush=True)

    readable = [r for r in layer_rows if r["usable"] != "empty_shell" or r["tables"]]
    lc = os.path.join(a.outdir, "inventory-local-all.csv")
    with open(lc, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[k for k in layer_rows[0] if k != "_fields"])
        w.writeheader()
        w.writerows(layer_rows)
    fc = os.path.join(a.outdir, "inventory-local-fields.csv")
    with open(fc, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields_rows[0]) if fields_rows else
                           ["layer", "field"])
        w.writeheader()
        w.writerows(fields_rows)

    summary = {
        "phase": 2, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dist": a.dist, "sample_per_layer_per_table": a.sample, "nonnull_rate_basis": BASIS,
        "dirs_scanned": done, "layers_with_data": sum(1 for r in layer_rows if r["tables"]),
        "layers_empty": sum(1 for r in layer_rows if not r["tables"]),
        "fields_rows": len(fields_rows),
        "class_counts": dict(collections.Counter(r["class"] for r in layer_rows)),
        "usable_counts": dict(collections.Counter(r["usable"] for r in layer_rows if r["readable"])),
        "unreadable_dirs": sum(1 for r in layer_rows if not r["readable"]),
        "source_counts": dict(collections.Counter(r["source"] for r in layer_rows)),
        "state_top": dict(collections.Counter(r["state"] for r in layer_rows).most_common(12)),
        "rows_total_from_ledgers": sum(int(r["rows"]) for r in layer_rows
                                       if str(r["rows"]).isdigit()),
        "wall_s": round(time.time() - t0, 1),
        "outputs": [lc, fc],
    }
    json.dump(summary, open(os.path.join(a.outdir, "_phase2-summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
