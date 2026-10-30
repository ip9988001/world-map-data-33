#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""历史批次「单元体积」明账 —— 按字节切的新规则生效前，哪些单元曾经接近 2 GB。

只读本机 release 快照（`dist/intake-full/release-index.json`，含每个资产的字节数），
不访问上游、不动任何资产。输出 `analysis/unit-size-audit.json` + 人看的表。

判据：一个 `*-uNNNNN.tar.gz` = 一个单元。GitHub 单资产硬上限 2,000,000,000 B；
新规则的目标上限 1,500,000,000 B（1.5 GB）。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SNAP = os.path.join(ROOT, "dist", "intake-full", "release-index.json")
OUT = os.path.join(ROOT, "analysis", "unit-size-audit.json")

HARD = 2_000_000_000
TARGET = 1_500_000_000


def main() -> int:
    if not os.path.exists(SNAP):
        print("❌ 没有本机快照：%s" % SNAP, file=sys.stderr)
        return 1
    snap = json.load(open(SNAP, encoding="utf-8"))
    rows, tags = [], 0
    for tag, assets in (snap.get("map") or {}).items():
        tags += 1
        units = [a for a in assets if str(a.get("n", "")).endswith(".tar.gz") and "-u" in str(a.get("n"))]
        if not units:
            continue
        big = max(units, key=lambda a: a.get("s") or 0)
        tot = sum(a.get("s") or 0 for a in units)
        rows.append({"tag": tag, "units": len(units), "unit_max_b": big.get("s") or 0,
                     "layer_bytes_b": tot,
                     "over_hard": (big.get("s") or 0) >= HARD,
                     "over_target": (big.get("s") or 0) >= TARGET})
    rows.sort(key=lambda r: -r["unit_max_b"])
    over_t = [r for r in rows if r["over_target"]]
    over_h = [r for r in rows if r["over_hard"]]
    res = {"at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
           "snapshot": SNAP, "tags": tags, "units_total": sum(r["units"] for r in rows),
           "hard_cap_b": HARD, "target_cap_b": TARGET,
           "over_target_units": len(over_t), "over_hard_units": len(over_h),
           "top": rows[:20]}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("快照 tag %d 个 / 单元 %d 个" % (tags, res["units_total"]))
    print("超 1.5 GB 单元：%d 个｜超 2 GB 硬上限：%d 个" % (len(over_t), len(over_h)))
    print("%-58s %6s %10s" % ("tag", "units", "max_unit"))
    for r in rows[:12]:
        print("%-58s %6d %8.2f GB%s" % (r["tag"][:58], r["units"], r["unit_max_b"] / 1e9,
                                        "  ⚠>2GB" if r["over_hard"] else
                                        ("  ⚠>1.5GB" if r["over_target"] else "")))
    print("→", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
