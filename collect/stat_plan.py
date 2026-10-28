#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计划池统计器 —— **只读** layer_plan_clean.csv，绝不重跑 plan_clean.py。

为什么单独一个脚本：plan_clean.py 的输入是原始 layer_plan.csv，重跑会覆盖
layer_plan_clean.csv，把 geo-fill 补上的 15,598 层州定位全部抹掉（未定位会从
4,351 弹回 19,949）。2026-10-28 核查时发现这个陷阱，故统计与生成彻底分离。
"""
from __future__ import annotations
import csv, json, collections, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "collect", "layer_plan_clean.csv")
OUT = os.path.join(ROOT, "collect", "plan_clean_report.json")
US = set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT "
         "NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC PR".split())

def main() -> int:
    states = collections.Counter(); rows_by = collections.Counter(); n = 0
    total_rows = 0
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        n += 1
        s = (r.get("state") or "").strip() or "(空)"
        try:
            rc = int(float(r.get("row_count") or 0))
        except Exception:
            rc = 0
        total_rows += rc
        states[s] += 1
        rows_by[s] += rc
    unknown = states.get("未定位", 0) + states.get("(空)", 0)
    rep = {
        "generated_by": "collect/stat_plan.py（只读统计，不改 CSV）",
        "total": n,
        "located": n - unknown,
        "still_unknown": unknown,
        "still_unknown_rows": rows_by.get("未定位", 0),
        "kept_rows": total_rows,
        "located_rate": round((n - unknown) / max(1, n), 4),
        "top_states": states.most_common(10),
        "unknown_by_host": [],
        "note": "数字来自 layer_plan_clean.csv（已含 geo-fill a2a5b27 补州结果）。"
                "禁止用 plan_clean.py 重算——它会读到未补州的原始 CSV。",
    }
    hosts = collections.Counter(); hrows = collections.Counter()
    import urllib.parse as up
    for r in csv.DictReader(open(SRC, encoding="utf-8")):
        if (r.get("state") or "").strip() != "未定位":
            continue
        h = up.urlparse(r.get("url") or "").netloc or "(无url)"
        hosts[h] += 1
        try: hrows[h] += int(float(r.get("row_count") or 0))
        except Exception: pass
    rep["unknown_by_host"] = [{"host": k, "layers": v, "rows": hrows[k]} for k, v in hosts.most_common(10)]
    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("total","located","still_unknown","still_unknown_rows","kept_rows","located_rate")}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
