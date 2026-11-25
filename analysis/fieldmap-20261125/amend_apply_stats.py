#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 amend_rewrite.py 的逐层重算结果合并回 layer-coverage.csv（v2），并保留 v1 供对比。

- in_rows 不变（没重读输入）；mapped = 重写后实际写出行数；dropped_below_c += 本次新增丢弃
- 逐层闭合恒等式重算：in_rows - mapped - dropped - parse_error = 0
- 输出端拿不到「zip 非法 vs 缺失」的区分 → 用旧比例回推，误差按 dropped_new 量级（<0.1%）
- 新增 grade_C 列（plan §三.5 要求「各级行数」，旧表只有 S/A/B）
用法：python3 amend_apply_stats.py
"""
from __future__ import annotations
import collections, csv, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
COV = os.path.join(HERE, "layer-coverage.csv")
COV_V1 = os.path.join(HERE, "layer-coverage.v1.csv")
TARS = os.path.join(DIST, "tar")

COLS = ["layer", "dialect_id", "dialect_origin", "a_pool_eligible", "class", "part_files",
        "in_rows", "mapped", "dropped_below_c", "parse_error", "diff", "in_bytes", "out_bytes",
        "out_file", "grade_S", "grade_A", "grade_B", "grade_C", "zip5_ok", "zip5_invalid",
        "zip5_missing", "state_ok", "state_invalid", "coord_ok", "coord_out_of_range",
        "coord_missing", "number_ok", "street_ok", "city_ok", "tier", "reason", "source_layer_kind"]


def _ls_tar(path):
    out = subprocess.run(["tar", "-tvzf", path], capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 6 and parts[-1].endswith(".ndjson.gz"):
            d[parts[-1][:-len(".ndjson.gz")]] = int(parts[2])
    return d


def member_sizes():
    """新分片里每个成员的实际字节数（tar -tvzf，8 片并行）。"""
    import multiprocessing as mp
    paths = [os.path.join(TARS, f) for f in sorted(os.listdir(TARS)) if f.endswith(".tar.gz")]
    sz = {}
    with mp.Pool(min(8, len(paths))) as pool:
        for d in pool.imap_unordered(_ls_tar, paths):
            sz.update(d)
    return sz


def main():
    if not os.path.isfile(COV_V1):
        shutil.copy2(COV, COV_V1)
    old = list(csv.DictReader(open(COV_V1, encoding="utf-8")))
    st = json.load(open(os.path.join(DIST, "amend-stats.json"), encoding="utf-8"))
    sizes = member_sizes()
    sys.path.insert(0, HERE)
    import fm_core as C
    tiers = C.load_tier_map()
    inv = {}
    with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "analysis", "full-inventory-20261124",
                           "local-vs-ledger-reconcile.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inv.setdefault(r["layer"], r)
    out = []
    missing = 0
    for r in old:
        lid = r["layer"]
        n = st.get(lid)
        row = {c: r.get(c, "") for c in COLS}
        if n is None:                       # 不可用层（无输出）：原样保留
            row["grade_C"] = ""
            row["source_layer_kind"] = "n/a"
            out.append(row)
            continue
        old_map = int(r["mapped"] or 0)
        mapped = n["rows_out"]
        dropped = int(r["dropped_below_c"] or 0) + n["dropped_new"]
        inr = int(r["in_rows"] or 0)
        pe = int(r["parse_error"] or 0)
        url = (inv.get(lid) or {}).get("url") or ""
        tier = tiers.get(url, "unrated") if url else "unrated"
        row.update({
            "mapped": mapped, "dropped_below_c": dropped,
            "diff": inr - mapped - dropped - pe,
            "out_bytes": sizes.get(lid, 0), "out_file": lid + ".ndjson.gz",
            "grade_S": n["grade"]["S"], "grade_A": n["grade"]["A"],
            "grade_B": n["grade"]["B"], "grade_C": n["grade"]["C"],
            "zip5_ok": n["zip_ok"], "zip5_missing": 0, "zip5_invalid": 0,
            "state_ok": n["state_ok"], "state_invalid": mapped - n["state_ok"],
            "coord_ok": n["coord_ok"], "coord_missing": 0, "coord_out_of_range": 0,
            "number_ok": n["num_ok"], "street_ok": n["street_ok"], "city_ok": n["city_ok"],
            "tier": json.dumps({tier: mapped}, ensure_ascii=False),
            "source_layer_kind": "url" if url else "layer_id_fallback",
        })
        # zip：valid 已知，剩下 zip_null 按旧 invalid/missing 比例摊（误差 <0.1%）
        old_null = int(r["zip5_invalid"] or 0) + int(r["zip5_missing"] or 0)
        znull = n["zip_null"]
        if old_null:
            z_inv = round(znull * int(r["zip5_invalid"] or 0) / old_null)
        else:
            z_inv = 0
        row["zip5_invalid"] = z_inv
        row["zip5_missing"] = znull - z_inv
        # 坐标：越界行数按旧值封顶
        cnull = n["coord_null"]
        oor = min(int(r["coord_out_of_range"] or 0), cnull)
        row["coord_out_of_range"] = oor
        row["coord_missing"] = cnull - oor
        out.append(row)
        if mapped == 0 and old_map > 0:
            missing += 1
    with open(COV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for row in out:
            w.writerow(row)
    bad = [r for r in out if r["mapped"] not in ("", 0) and int(r["diff"] or 0) != 0]
    print(json.dumps({"layers": len(out), "mapped_layers": sum(1 for r in out if int(r["mapped"] or 0) > 0),
                      "closure_diff_nonzero": len(bad), "layers_lost": missing,
                      "sum_mapped": sum(int(r["mapped"] or 0) for r in out)}, ensure_ascii=False))
    if bad:
        print("差额非零样例", [(r["layer"], r["diff"]) for r in bad[:5]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
