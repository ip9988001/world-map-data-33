#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 coord_clean.py 的逐层结果回填 layer-coverage.csv（坐标清零后）。

只动受影响层的 grade_S/A/B/C 与 coord_ok/coord_missing；行数、闭合不变（清零不删行）。
moved 矩阵是完整的（每行记了 from->to），所以 新 = 旧 − 出 + 进。
"""
from __future__ import annotations

import collections, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
COV = os.path.join(HERE, "layer-coverage.csv")


def main():
    st = json.load(open(os.path.join(DIST, "coord-clean-stats.json"), encoding="utf-8"))
    per = st["per_layer"]
    rows = list(csv.DictReader(open(COV, encoding="utf-8")))
    fields = list(rows[0].keys())
    n = 0
    for r in rows:
        p = per.get(r["layer"])
        if not p:
            continue
        n += 1
        g = {k: int(r["grade_" + k] or 0) for k in "SABC"}
        for k, v in p["moved"].items():
            a, b = k.split("->")
            if a in g:
                g[a] -= v
            if b in g:
                g[b] += v
        for k in "SABC":
            r["grade_" + k] = g[k]
        # 注意：amend_apply_stats 写进来的 coord_ok 本来就是「非空且在范围内」的行数
        # （那 101 行坏坐标当时被 amend_rewrite 计进 bad，不在 coord_ok 里），所以这里**不再减**，
        # 清零后它们落进 missing；out_of_range 桶清零（数据里已无越界行）。
        cok = int(r["coord_ok"] or 0)
        mapped = int(r["mapped"] or 0)
        cmiss = mapped - cok
        r["coord_ok"] = cok
        r["coord_out_of_range"] = 0
        r["coord_missing"] = cmiss
        assert cmiss >= p["bad"] - 1, (r["layer"], cmiss, p["bad"])
        assert mapped == cok + cmiss, (r["layer"], mapped, cok, cmiss)
    with open(COV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps({"layers_touched": n, "bad_total": st["total"]["bad"],
                      "moved": st["total"]["moved"]}, ensure_ascii=False))
    for lid, p in sorted(per.items()):
        print(f"  {p['bad']:4d} 行  {lid[:56]:56s} {p['moved']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
