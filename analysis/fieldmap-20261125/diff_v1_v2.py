#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1（旧 dist/tar，PR #58 现版）vs v2（dist-v2/tar，全量重扫）逐层对账。

抽 `sample-layers.csv` 的 16 层（muse-000264 用的那批，含 muse 亲核的 7 层漂移层）：
  a. 行数 旧/新
  b. 行数相等 → 位置对齐逐字段比；不等 → 退回 multiset（键 = 除 addrkey 外全字段）
  c. grade 变动矩阵（旧级 → 新级，逐行）
  d. 字段差：state / city / zip5 / house_number / street_name / lat / lon / tier / source_layer / addrkey

用法：python3 diff_v1_v2.py [--workers 8]
输出：diff-v1-v2.json / diff-v1-v2.csv
"""
from __future__ import annotations

import argparse, collections, csv, gzip, json, multiprocessing as mp, os, tarfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
V1 = "/data/workspace/wmd-fieldmap/dist/tar"
V2 = "/data/workspace/wmd-fieldmap/dist-v2/tar"
SAMPLE = os.path.join(HERE, "sample-layers.csv")
TMP = "/tmp/dv1"
FIELDS = ["state", "city", "zip5", "house_number", "street_name", "lat", "lon", "grade", "tier",
          "addrkey", "source_layer"]


def dump_shard(job):
    """旧产物：只按成员名抽样本层，流式扫 8 片，不解全量。"""
    shard, want = job
    os.makedirs(TMP, exist_ok=True)
    n = 0
    with tarfile.open(shard, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            if m.name[:-len(".ndjson.gz")] in want:
                open(os.path.join(TMP, m.name), "wb").write(tf.extractfile(m).read())
                n += 1
    return os.path.basename(shard), n


def dump_v2(shard):
    want = {r["layer_id"] for r in csv.DictReader(open(SAMPLE, encoding="utf-8"))}
    os.makedirs("/tmp/dv2", exist_ok=True)
    n = 0
    with tarfile.open(shard, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            if m.name[:-len(".ndjson.gz")] in want:
                open(os.path.join("/tmp/dv2", m.name), "wb").write(tf.extractfile(m).read())
                n += 1
    return os.path.basename(shard), n


def rows_of(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    want = [r["layer_id"] for r in csv.DictReader(open(SAMPLE, encoding="utf-8"))]
    out = []
    per_layer = []
    fielddiff = collections.Counter()
    gmove = collections.Counter()
    if not all(os.path.isfile(os.path.join(TMP, w + ".ndjson.gz")) for w in want):
        t0 = time.time()
        with mp.Pool(a.workers) as pool:
            for name, n in pool.imap_unordered(dump_shard, [(os.path.join(V1, f), set(want))
                                                            for f in sorted(os.listdir(V1))
                                                            if f.endswith(".tar.gz")]):
                print(f"[dump v1] {name} hit={n} {time.time()-t0:.0f}s", flush=True)
    if not all(os.path.isfile("/tmp/dv2/" + w + ".ndjson.gz") for w in want):
        os.makedirs("/tmp/dv2", exist_ok=True)
        t0d = time.time()
        with mp.Pool(a.workers) as pool:
            for name, n in pool.imap_unordered(dump_v2, [os.path.join(V2, f) for f in
                                                         sorted(os.listdir(V2))
                                                         if f.endswith(".tar.gz")]):
                print(f"[dump v2] {name} hit={n} {time.time()-t0d:.0f}s", flush=True)
    for lid in want:
        p1 = os.path.join(TMP, lid + ".ndjson.gz")
        p2 = os.path.join(V2, lid + ".ndjson.gz")
        p2 = os.path.join("/tmp/dv2", lid + ".ndjson.gz")
        if not (os.path.isfile(p1) and os.path.isfile(p2)):
            per_layer.append({"layer_id": lid, "status": "missing_side",
                              "have_v1": os.path.isfile(p1), "have_v2": os.path.isfile(p2)})
            continue
        A = list(rows_of(p1))
        B = list(rows_of(p2))
        d = collections.Counter()
        gm = collections.Counter()
        if len(A) == len(B):
            method = "positional"
            for x, y in zip(A, B):
                for f in FIELDS:
                    if (x.get(f) or None) != (y.get(f) or None):
                        d[f] += 1
                if x.get("grade") != y.get("grade"):
                    gm[f"{x.get('grade')}->{y.get('grade')}"] += 1
        else:
            method = "multiset"
            key = lambda r: tuple(str(r.get(f)) for f in FIELDS if f != "addrkey")  # noqa: E731
            ca, cb = collections.Counter(key(r) for r in A), collections.Counter(key(r) for r in B)
            only_a = sum((ca - cb).values())
            only_b = sum((cb - ca).values())
            d["rows_only_in_v1"] = only_a
            d["rows_only_in_v2"] = only_b
            d["addrkey"] = sum(1 for x, y in zip(sorted(A, key=key), sorted(B, key=key))
                               if (x.get("addrkey") or None) != (y.get("addrkey") or None))
            ga = collections.Counter(r.get("grade") for r in A)
            gb = collections.Counter(r.get("grade") for r in B)
            for g in ("S", "A", "B", "C"):
                if ga[g] != gb[g]:
                    gm[f"{g}:{ga[g]}->{gb[g]}"] = abs(gb[g] - ga[g])
        fielddiff.update(d)
        gmove.update(gm)
        per_layer.append({"layer_id": lid, "status": "ok", "method": method,
                          "rows_v1": len(A), "rows_v2": len(B),
                          "delta_rows": len(B) - len(A), "diff_by_field": dict(d),
                          "grade_moves": dict(gm),
                          "grade_v1": dict(collections.Counter(r.get("grade") for r in A)),
                          "grade_v2": dict(collections.Counter(r.get("grade") for r in B))})
        print(f"{lid[:56]:56s} {method} {len(A)}->{len(B)} grade_moves={dict(gm)}", flush=True)
    # 样本级 grade 重算矩阵（逐行、positional 层）
    doc = {"layers": len(want), "per_layer": per_layer,
           "agg_diff_by_field": dict(fielddiff), "agg_grade_moves": dict(gmove),
           "rows_v1": sum(p.get("rows_v1", 0) for p in per_layer),
           "rows_v2": sum(p.get("rows_v2", 0) for p in per_layer)}
    json.dump(doc, open(os.path.join(HERE, "diff-v1-v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "diff-v1-v2.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "method", "rows_v1", "rows_v2", "delta_rows",
                                          "grade_moves", "diff_by_field"])
        w.writeheader()
        for p in per_layer:
            w.writerow({"layer": p["layer_id"], "method": p.get("method"),
                        "rows_v1": p.get("rows_v1"), "rows_v2": p.get("rows_v2"),
                        "delta_rows": p.get("delta_rows"),
                        "grade_moves": json.dumps(p.get("grade_moves") or {}, ensure_ascii=False),
                        "diff_by_field": json.dumps(p.get("diff_by_field") or {}, ensure_ascii=False)})
    print(json.dumps({k: doc[k] for k in ("layers", "rows_v1", "rows_v2", "agg_diff_by_field",
                                          "agg_grade_moves")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
