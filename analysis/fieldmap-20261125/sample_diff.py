#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000264 A3：样本层「重扫（修好 begin_layer）」vs「现有产物（dist/tar）」逐字段对账。

现有产物抽取方式：**只按成员名抽取样本层**（流式扫 8 片，命中才落盘到 dist/sample_existing/），
不解全量、不解包到别处。比较口径：
  a. 行数（等/不等 + 差多少）
  b. 行数相等 → **位置对齐**逐字段比（同层行序 = 输入序 1:1，两边都只丢 below_C）
  c. 行数不等 → 退回 **multiset 比对**（按整行 tuple 计数），并写清为什么不能位置对齐
比对字段：state / city / zip5 / house_number / street_name / lat / lon / grade / tier / addrkey / source_layer
（`unit` 不在 11 列输出里 → 本表不列，见 REPORT 已知偏差）

用法：python3 sample_diff.py [--workers 8]
"""
from __future__ import annotations

import argparse, collections, csv, gzip, json, multiprocessing as mp, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
TARS = os.path.join(DIST, "tar")
SAMPLE = os.path.join(HERE, "sample-layers.csv")
EXIST = os.path.join(DIST, "sample_existing")
NEW = os.path.join(DIST, "sample")
FIELDS = ["state", "city", "zip5", "house_number", "street_name", "lat", "lon", "grade", "tier",
          "addrkey", "source_layer"]


def dump_shard(job):
    shard, want = job
    os.makedirs(EXIST, exist_ok=True)
    n = 0
    import tarfile
    with tarfile.open(shard, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            if m.name[:-len(".ndjson.gz")] in want:
                open(os.path.join(EXIST, m.name), "wb").write(tf.extractfile(m).read())
                n += 1
    return os.path.basename(shard), n


def mask(v):
    """示例打码：门牌只留首末位、街名只留首词。"""
    if v is None:
        return None
    s = str(v)
    if len(s) <= 2:
        return s[0] + "*" * (len(s) - 1)
    return s[0] + "*" * (len(s) - 2) + s[-1]


def cmp_layer(lid):
    pa, pb = os.path.join(EXIST, lid + ".ndjson.gz"), os.path.join(NEW, lid + ".ndjson.gz")
    if not (os.path.isfile(pa) and os.path.isfile(pb)):
        return {"layer_id": lid, "status": "missing_side", "exist": os.path.isfile(pa),
                "rescan": os.path.isfile(pb)}
    A = [json.loads(l) for l in gzip.open(pa, "rt", encoding="utf-8")]
    B = [json.loads(l) for l in gzip.open(pb, "rt", encoding="utf-8")]
    res = {"layer_id": lid, "rows_exist": len(A), "rows_rescan": len(B),
           "rowcount_equal": len(A) == len(B)}
    diff = collections.Counter()
    examples = collections.defaultdict(list)
    if len(A) == len(B):
        res["method"] = "positional"
        for i in range(len(A)):
            a, b = A[i], B[i]
            for f in FIELDS:
                if a.get(f) != b.get(f):
                    diff[f] += 1
                    if len(examples[f]) < 3:
                        examples[f].append({"row": i, "exist": mask(a.get(f)) if f != "latitude" else a.get(f),
                                            "rescan": mask(b.get(f)) if f != "latitude" else b.get(f)})
    else:
        res["method"] = "multiset"
        ca = collections.Counter(tuple(a.get(f) for f in FIELDS) for a in A)
        cb = collections.Counter(tuple(b.get(f) for f in FIELDS) for b in B)
        only_a = ca - cb
        only_b = cb - ca
        diff["rows_only_in_exist"] = sum(only_a.values())
        diff["rows_only_in_rescan"] = sum(only_b.values())
        for tup, cnt in list(only_a.items())[:3]:
            examples["only_exist"].append({"n": cnt, "row": {f: mask(v) for f, v in zip(FIELDS, tup)}})
        for tup, cnt in list(only_b.items())[:3]:
            examples["only_rescan"].append({"n": cnt, "row": {f: mask(v) for f, v in zip(FIELDS, tup)}})
    res["diff_by_field"] = {f: diff.get(f, 0) for f in FIELDS}
    res["diff_by_field"]["rows_only_in_exist"] = diff.get("rows_only_in_exist", 0)
    res["diff_by_field"]["rows_only_in_rescan"] = diff.get("rows_only_in_rescan", 0)
    res["diff_rows"] = max(diff.values()) if diff else 0
    res["examples"] = {k: v for k, v in examples.items() if v}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(SAMPLE, encoding="utf-8")))
    want = {r["layer_id"] for r in rows}
    meta = {r["layer_id"]: r for r in rows}
    shards = [os.path.join(TARS, f) for f in sorted(os.listdir(TARS)) if f.endswith(".tar.gz")]
    with mp.Pool(min(a.workers, len(shards))) as pool:
        for sh, n in pool.imap_unordered(dump_shard, [(s, want) for s in shards]):
            print(f"[dump] {sh} wrote={n}", flush=True)
    got = len([f for f in os.listdir(EXIST) if f.endswith(".ndjson.gz")])
    print(f"[dump] 样本 {got}/{len(want)} 层已从现有分片抽出", flush=True)
    res = [cmp_layer(lid) for lid in sorted(want)]
    out = []
    for r in res:
        m = meta[r["layer_id"]]
        d = r.get("diff_by_field") or {}
        out.append({"layer_id": r["layer_id"], "tier": m["tier"], "dialect": m["dialect"],
                    "rows_exist": r.get("rows_exist"), "rows_rescan": r.get("rows_rescan"),
                    "method": r.get("method"), "diff_rows": r.get("diff_rows"),
                    **{f"diff_{k}": v for k, v in d.items()}})
    cols = ["layer_id", "tier", "dialect", "rows_exist", "rows_rescan", "method", "diff_rows"] + \
           [f"diff_{f}" for f in FIELDS] + ["diff_rows_only_in_exist", "diff_rows_only_in_rescan"]
    with open(os.path.join(HERE, "sample-diff.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow(r)
    agg = collections.Counter()
    for r in res:
        for k, v in (r.get("diff_by_field") or {}).items():
            agg[k] += v
    json.dump({"layers": len(res), "per_layer": res, "agg_diff_by_field": dict(agg),
               "fields_compared": FIELDS,
               "note": "addrkey 差异来自已知偏差：现有产物由 amend_rewrite.py 用 11 列自身重算（无 unit、无 "
                       "st_suf/pre_dir/post_dir 分量），重扫用输入真实 unit + 分量；不是 begin_layer 引起"},
              open(os.path.join(HERE, "sample-diff.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"layers": len(res), "agg": dict(agg),
                      "rowcount_equal_layers": sum(1 for r in res if r.get("rowcount_equal"))},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
