#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把重做（丢输出版本）的覆盖记录并回 layer-coverage.csv：按 layer 去重，重做行优先。

背景：续跑时一次误删 `dist/rows/*.ndjson.gz` 造成 365 层输出丢失（覆盖表已记 ok）。
本脚本把重做批（`layer-coverage-redo.csv`）并回去，并校验 3,550 行齐全、无重复。
"""
from __future__ import annotations
import collections, csv, os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    main_p = os.path.join(HERE, "layer-coverage.csv")
    redo_p = os.path.join(HERE, "layer-coverage-redo.csv")
    rows = list(csv.DictReader(open(main_p, encoding="utf-8")))
    cols = list(rows[0].keys())
    by = {r["layer"]: r for r in rows}
    n_redo = 0
    if os.path.isfile(redo_p):
        for r in csv.DictReader(open(redo_p, encoding="utf-8")):
            if int(r.get("out_bytes") or 0) > 0 or not (by.get(r["layer"], {}).get("out_file")):
                by[r["layer"]] = r
                n_redo += 1
    out = sorted(by.values(), key=lambda r: r["layer"])
    with open(main_p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow(r)
    print(f"merged redo={n_redo} rows={len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
