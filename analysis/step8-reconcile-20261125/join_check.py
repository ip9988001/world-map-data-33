#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · D 的 join 校验：对账 v2 里残留的 `local_absent_upstream_no_assets`
必须与 B 表（`upstream-no-assets.csv`）**一一对应**（多一层少一层都要说清）。

用法：python3 analysis/step8-reconcile-20261125/join_check.py
"""
from __future__ import annotations

import collections
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    v2 = os.path.join(HERE, "local-vs-ledger-reconcile-v2.csv")
    b = os.path.join(HERE, "upstream-no-assets.csv")
    rows = list(csv.DictReader(open(v2, encoding="utf-8")))
    cls = collections.Counter(r["reconcile_class"] for r in rows)
    resid = {r["layer"] for r in rows if r["reconcile_class"] == "local_absent_upstream_no_assets"}
    btab = {r["layer"] for r in csv.DictReader(open(b, encoding="utf-8"))}
    out = {"reconcile_rows": len(rows), "class_counts": dict(cls),
           "residual_layers": len(resid), "b_table_rows": len(btab),
           "only_in_residual": sorted(resid - btab)[:10], "only_in_b_table": sorted(btab - resid)[:10],
           "join_ok": resid == btab}
    json.dump(out, open(os.path.join(HERE, "join-check.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out["join_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
