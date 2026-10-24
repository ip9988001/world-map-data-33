#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 06：汇总 + 覆盖率表（行数 ÷ Census 住房单元数）"""
import glob, json, os, csv, gzip
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 2020 Census 住房单元数（近似值，用于覆盖率分母）
HU = {"AL":2270000,"AK":328000,"AZ":3030000,"AR":1370000,"CA":14300000,"CO":2500000,"CT":1520000,
"DE":450000,"DC":340000,"FL":9800000,"GA":4400000,"HI":590000,"ID":740000,"IL":5400000,"IN":2900000,
"IA":1400000,"KS":1300000,"KY":2000000,"LA":2000000,"ME":740000,"MD":2500000,"MA":2900000,
"MI":4600000,"MN":2400000,"MS":1300000,"MO":2800000,"MT":510000,"NE":840000,"NV":1200000,
"NH":640000,"NJ":3700000,"NM":900000,"NY":8300000,"NC":4500000,"ND":360000,"OH":5100000,
"OK":1700000,"OR":1700000,"PA":5600000,"RI":470000,"SC":2200000,"SD":380000,"TN":2900000,
"TX":11000000,"UT":1100000,"VT":330000,"VA":3500000,"WA":3100000,"WV":880000,"WI":2700000,
"WY":280000,"PR":1400000}

def main():
    ms = []
    for f in glob.glob(os.path.join(ROOT, "collect", "out", "*", "_manifest.json")):
        try:
            ms.append(json.load(open(f, encoding="utf-8")))
        except Exception:
            pass
    by = {}
    for m in ms:
        st = (m.get("id") or "").split("_")[0][:2]
        by.setdefault(st, 0)
        by[st] += m.get("rows") or 0
    lines = ["# 三仓采集 · 最终报告", "",
             f"- 已采图层：{len(ms)}", f"- 总行数：{sum(m.get('rows') or 0 for m in ms):,}", "",
             "| 州 | 已采行数 | 住房单元数 | 覆盖率 |", "|---|---|---|---|"]
    for st in sorted(by):
        hu = HU.get(st)
        cov = f"{by[st]/hu:.0%}" if hu else "—"
        lines.append(f"| {st} | {by[st]:,} | {hu:,} | {cov} |" if hu else f"| {st} | {by[st]:,} | — | — |")
    open(os.path.join(ROOT, "collect", "FINAL_REPORT.md"), "w").write("\n".join(lines))
    json.dump({st: v for st, v in by.items()}, open(os.path.join(ROOT, "collect", "layer_status.json"), "w"))
    print("report ok states=", len(by))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
