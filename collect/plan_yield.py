#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 产出曲线：按层实测有效率外推，算 Top-N 层的「净新增地址 / 预算分钟」。"""
from __future__ import annotations
import csv, json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = 20000
ROWS_PER_MIN = 100_000     # 沿用三仓实测吞吐（84.2M 行 / 836 job-分钟）
XSURV = 0.85               # 跨层再打 15% 冗余（实测全样本 17.04% 已含层内去重）

d = json.load(open(os.path.join(HERE, "parcel_yield.json"), encoding="utf-8"))
meta = {r["layer_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "situs_layers.csv"), encoding="utf-8"))}

layers = []
for x in d["detail"]:
    if x["err"] or not x["fetched"]:
        continue
    decl, fet = x["declared"], x["fetched"]
    rate = x["valid"] / fet
    if decl <= CAP:
        new, valid = x["uniq_keys"], x["valid"]
    else:
        new, valid = int(decl * x["uniq_keys"] / fet * XSURV), int(decl * rate)
    m = meta.get(x["layer"], {})
    layers.append({"layer": x["layer"], "state": x["state"], "grade": x["grade"],
                   "declared": decl, "fetched": fet, "valid": valid, "new": new,
                   "eff": round(new * 100.0 / max(1, decl), 2),
                   "min": round(decl / ROWS_PER_MIN, 1)})

layers.sort(key=lambda r: -r["eff"])
tot_new = sum(r["new"] for r in layers)
tot_min = sum(r["min"] for r in layers)
tot_decl = sum(r["declared"] for r in layers)
hi = [r for r in layers if r["eff"] >= 20]
zero = [r for r in layers if r["eff"] == 0]

curve = []
for n in (50, 100, 200, 500, 1000, len(layers)):
    sl = layers[:n]
    curve.append({"top": n, "new": sum(r["new"] for r in sl),
                  "min": round(sum(r["min"] for r in sl), 0),
                  "decl": sum(r["declared"] for r in sl)})

res = {"layers_ok": len(layers), "total_new": tot_new, "total_min": tot_min,
       "total_declared": tot_decl, "avg_eff": round(tot_new * 100.0 / max(1, tot_decl), 2),
       "hi_eff_layers": len(hi), "hi_eff_new": sum(r["new"] for r in hi),
       "zero_layers": len(zero), "zero_decl": sum(r["declared"] for r in zero),
       "curve": curve,
       "top20": [{k: r[k] for k in ("state", "grade", "declared", "eff", "new")} for r in layers[:20]],
       "detail": layers}
json.dump(res, open(os.path.join(HERE, "plan_yield.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(json.dumps({k: v for k, v in res.items() if k not in ("detail", "top20")}, ensure_ascii=False, indent=1))
print("--- Top10 层 ---")
for r in layers[:10]:
    print("  %s %-38s 声明%8d eff%6.1f%% → %8d 条" % (r["state"], r["layer"][:38], r["declared"], r["eff"], r["new"]))
print("--- 零产出层 ---")
print("  %d 层 / 声明 %s 行（白采）" % (len(zero), format(sum(r["declared"] for r in zero), ",")))
