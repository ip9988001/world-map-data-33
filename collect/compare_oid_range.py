#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定向区间补采（--oid-range）· 灰度比对：旧单元 vs 新区间产物，逐行/逐字段对账。

只读，不采数据：把两边已经躺在 Release 上的产物拉下来，按 OBJECTID 对齐后比对：
  ① 行数：旧单元在该区间的行数 vs 新区间行数 vs 上游 returnCount（三段对账）
  ② OID 集合：只在旧 / 只在新 各多少（漏采/多采可证）
  ③ 字段：抽样 N 行逐字段比（默认 1,000 行，可按字段看一致率），不一致的给实例

判据（写死在输出里，不靠感觉）：
  · 行数一致 且 OID 集合一致 且 抽样全字段一致 → verdict=identical → 才允许按区间铺满全层
  · 任一不一致 → verdict=differs → 丢 r2 产物回滚，旧单元不动（旧产物在独立 tag，没被覆盖）

用法：
  python3 collect/compare_oid_range.py --layer <id> --old-tag collect-step04-<id> \
      --lo 1 --hi 999177 --sample 1000 --out analysis/oid-range-gray-<date>.json
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = {"User-Agent": "collect-audit/1.0 (+world-map-data-33)"}
OID_KEYS = ("OBJECTID", "objectid", "ObjectID", "OBJECTID_1", "FID", "OID")


def oid_of(rec):
    raw = rec.get("raw") or {}
    for k in OID_KEYS:
        v = raw.get(k)
        if isinstance(v, int):
            return v
    for k in OID_KEYS:
        v = rec.get(k)
        if isinstance(v, int):
            return v
    return None


def fetch_tag(tag, workdir, log=print):
    """把某个 tag 的单元包拉到本地（已有就跳过）。返回文件列表。"""
    os.makedirs(workdir, exist_ok=True)
    got = [os.path.join(workdir, f) for f in os.listdir(workdir) if f.endswith(".tar.gz")]
    if got:
        log("  使用本地已有产物 %d 个：%s" % (len(got), workdir))
        return sorted(got)
    cmd = ["gh", "release", "download", tag, "--pattern", "*-u*.tar.gz",
           "-D", workdir, "--clobber"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("下载失败：%s\n%s" % (tag, (r.stderr or r.stdout)[-500:]))
    got = [os.path.join(workdir, f) for f in os.listdir(workdir) if f.endswith(".tar.gz")]
    log("  下载 %s：%d 个单元包" % (tag, len(got)))
    return sorted(got)


def iter_records(paths):
    """逐条读 tar.gz 里的 ndjson.gz（不落盘中间产物）。"""
    for p in paths:
        with tarfile.open(p, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                    continue
                fh = tf.extractfile(m)
                if fh is None:
                    continue
                with gzip.open(fh, "rt", encoding="utf-8") as g:
                    for line in g:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except Exception:      # noqa: BLE001
                            continue


def digest(rec):
    return hashlib.md5(json.dumps(rec, sort_keys=True, ensure_ascii=False)
                       .encode()).hexdigest()


def collect_side(paths, lo, hi, keep_records=0):
    """读一侧：返回 (rows, {oid: md5}, {oid: rec}（只留抽样用，最多 keep_records 条）)。"""
    rows, seen, sample = 0, {}, {}
    for rec in iter_records(paths):
        o = oid_of(rec)
        if o is None or o < lo or o > hi:
            continue
        rows += 1
        seen[o] = digest(rec)
        if len(sample) < keep_records:
            sample[o] = rec
    return rows, seen, sample


def flatten(rec, prefix=""):
    out = {}
    for k, v in (rec or {}).items():
        key = prefix + str(k)
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, list):
            out[key] = json.dumps(v, sort_keys=True, ensure_ascii=False)[:400]
        else:
            out[key] = v
    return out


def field_diff(a, b):
    fa, fb = flatten(a), flatten(b)
    keys = sorted(set(fa) | set(fb))
    same = [k for k in keys if fa.get(k) == fb.get(k)]
    diff = [k for k in keys if fa.get(k) != fb.get(k)]
    return same, diff, keys


def upstream_count(url, lo, hi, timeout=60):
    if not url:
        return None
    where = "OBJECTID>=%d AND OBJECTID<=%d" % (lo, hi)
    q = url.rstrip("/") + "/query?" + urllib.parse.urlencode(
        {"where": where, "returnCountOnly": "true", "f": "json"})
    try:
        with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=timeout) as r:
            return int(json.loads(r.read(2000).decode("utf-8", "replace")).get("count"))
    except Exception as e:                             # noqa: BLE001
        return {"err": "%s: %s" % (type(e).__name__, str(e)[:120])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True)
    ap.add_argument("--old-tag", required=True)
    ap.add_argument("--r2-tag", default="", help="默认 = <old-tag>-r2")
    ap.add_argument("--lo", type=int, required=True)
    ap.add_argument("--hi", type=int, required=True)
    ap.add_argument("--sample", type=int, default=1000)
    ap.add_argument("--url", default="", help="层 URL（用于取区间上游 returnCount 做第三方对账）")
    ap.add_argument("--old-dir", default="")
    ap.add_argument("--new-dir", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi = a.lo, a.hi
    r2 = a.r2_tag or (a.old_tag + "-r2")
    log = lambda m: print(m, flush=True)

    log("== 旧单元 ==")
    old_paths = [os.path.join(a.old_dir, f) for f in sorted(os.listdir(a.old_dir))] \
        if a.old_dir and os.path.isdir(a.old_dir) else fetch_tag(a.old_tag, "/tmp/cmp-old-%s" % a.layer, log)
    old_paths = [p for p in old_paths if p.endswith(".tar.gz")]
    old_rows, old_map, old_sample = collect_side(old_paths, lo, hi, keep_records=a.sample)

    log("== 新区间（%s）==" % r2)
    new_paths = [os.path.join(a.new_dir, f) for f in sorted(os.listdir(a.new_dir))] \
        if a.new_dir and os.path.isdir(a.new_dir) else fetch_tag(r2, "/tmp/cmp-new-%s" % a.layer, log)
    new_paths = [p for p in new_paths if p.endswith(".tar.gz")]
    new_rows, new_map, _ = collect_side(new_paths, lo, hi, keep_records=0)

    only_old = sorted(set(old_map) - set(new_map))
    only_new = sorted(set(new_map) - set(old_map))
    common = sorted(set(old_map) & set(new_map))
    same_rows = [o for o in common if old_map[o] == new_map[o]]
    diff_rows = [o for o in common if old_map[o] != new_map[o]]

    # 抽样逐字段比：优先抽「整行 digest 不同」的（最能暴露字段口径差），不够再用相同的补齐
    pick = (diff_rows + same_rows)[:a.sample]
    picked = set(pick)
    detail, field_same, field_diff_cnt = [], {}, {}
    if picked:
        log("== 抽样 %d 行逐字段比 ==" % len(picked))
        new_detail = {}
        for rec in iter_records(new_paths):
            o = oid_of(rec)
            if o in picked:
                new_detail[o] = rec
                if len(new_detail) == len(picked):
                    break
        for o in pick:
            a_rec, b_rec = old_sample.get(o), new_detail.get(o)
            if a_rec is None or b_rec is None:
                detail.append({"oid": o, "note": "抽样行有一侧没读到（在 %d 行抽样窗口外）"
                                                % a.sample})
                continue
            same, diff, keys = field_diff(a_rec, b_rec)
            for k in keys:
                (field_same if k in same else field_diff_cnt)[k] = \
                    (field_same if k in same else field_diff_cnt).get(k, 0) + 1
            if diff and len(detail) < 5:
                detail.append({"oid": o, "diff_fields": diff[:8],
                               "old": {k: flatten(a_rec).get(k) for k in diff[:4]},
                               "new": {k: flatten(b_rec).get(k) for k in diff[:4]}})

    up = upstream_count(a.url, lo, hi) if a.url else None
    ok_rows = (old_rows == new_rows)
    ok_set = (not only_old and not only_new)
    ok_fields = not field_diff_cnt
    if ok_rows and ok_set and ok_fields:
        verdict = "identical"
    elif ok_rows and ok_set:
        verdict = "rows_identical_fields_differ"
    else:
        verdict = "differs"

    out = {
        "schema": "oid-range-gray/v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "layer": a.layer, "oid_range": [lo, hi], "span": hi - lo + 1,
        "old_tag": a.old_tag, "r2_tag": r2,
        "old_unit_files": [os.path.basename(p) for p in old_paths],
        "new_unit_files": [os.path.basename(p) for p in new_paths],
        "upstream_count_in_range": up,
        "old_rows": old_rows, "new_rows": new_rows,
        "rows_equal": ok_rows,
        "oid_common": len(common), "only_old": len(only_old), "only_new": len(only_new),
        "only_old_examples": only_old[:10], "only_new_examples": only_new[:10],
        "row_level_identical": len(same_rows), "row_level_differ": len(diff_rows),
        "sampled": len(pick),
        "field_match": field_same, "field_mismatch": field_diff_cnt,
        "mismatch_examples": detail,
        "verdict": verdict,
        "gate": ("铺满全层" if verdict == "identical" else "停 · 不出 r2 放量，旧单元保持唯一真值"),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in
                      ("verdict", "old_rows", "new_rows", "upstream_count_in_range",
                       "only_old", "only_new", "row_level_differ", "sampled", "gate")},
                     ensure_ascii=False, indent=1))
    print("写入", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
