#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6c 全库合并：S6 实测层 + S6b 快测层 → 全库可采层清单与预算。"""
from __future__ import annotations
import json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
TH = 0.20          # 有效率门槛
INNER = 0.90       # 层内去重存活
X = 0.85           # 跨层冗余
RPM = 100_000      # 行/分钟

a = json.load(open(os.path.join(HERE, "s6b_eff.json"), encoding="utf-8"))["rows"]
b = json.load(open(os.path.join(HERE, "parcel_yield.json"), encoding="utf-8"))["detail"]

rows = []
for x in b:
    if x["err"] or not x["fetched"]:
        continue
    eff = x["valid"] / x["fetched"]
    decl = x["declared"]
    new = x["uniq_keys"] if decl <= 20000 else int(decl * x["uniq_keys"] / x["fetched"] * X)
    rows.append({"layer": x["layer"], "state": x["state"], "grade": x["grade"], "src": "S6",
                 "declared": decl, "eff": round(eff * 100, 2), "new": new})
for x in a:
    if not x["fetched"]:
        continue
    eff = x["valid"] / x["fetched"]
    decl = x["declared"]
    new = int(decl * eff * INNER * X)
    rows.append({"layer": x["layer"], "state": x["state"], "grade": x["grade"], "src": "S6b",
                 "declared": decl, "eff": round(eff * 100, 2), "new": new})

pick = [r for r in rows if r["eff"] >= TH * 100]
for r in pick:
    r["min"] = round(r["declared"] / RPM, 1)
pick.sort(key=lambda r: -r["eff"])

tot_new = sum(r["new"] for r in pick)
tot_min = sum(r["min"] for r in pick)
tot_decl = sum(r["declared"] for r in pick)
by_state = Counter()
for r in pick:
    by_state[r["state"] or "未定位"] += r["new"]

res = {"tested_all": len(rows), "pick_layers": len(pick),
       "pick_declared": tot_decl, "pick_new": tot_new, "pick_min": tot_min,
       "avg_eff_pct": round(tot_new * 100.0 / max(1, tot_decl), 2),
       "drop_layers": len(rows) - len(pick),
       "drop_declared": sum(r["declared"] for r in rows) - tot_decl,
       "top_states": by_state.most_common(12),
       "top30": [{k: r[k] for k in ("state", "src", "declared", "eff", "new")} for r in pick[:30]]}
json.dump({"summary": res, "pick": pick}, open(os.path.join(HERE, "s6c_merge.json"), "w",
                                               encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "top30"}, ensure_ascii=False, indent=1))
print("--- Top12 层 ---")
for r in pick[:12]:
    print("  %s %-40s %8d行 eff%6.1f%% → %8d" % (r["state"], r["layer"][:40], r["declared"], r["eff"], r["new"]))

open("/tmp/s6b.txt", "w", encoding="utf-8").write("\n".join([
 "✅ 10-P 自研 S6b+S6c · 全库快测与合并完成",
 "",
 "快测 4,933 层 × 300 行（1,095,775 行）",
 "· 有效率 21.7%（远高于抽样的 7.4%）",
 "· 高产出层（≥20%）1,338 层",
 "",
 "全库合并（S6 实测 219 层 + S6b 快测 4,933 层）：",
 "· 达标层 %d 层 / 声明 %s 行" % (len(pick), format(tot_decl, ',')),
 "· 预计净新增 %s 条" % format(tot_new, ','),
 "· 预算约 %d job-分钟（剩余 964）" % tot_min,
 "· 丢弃 %d 层 / %s 行（有效率<20%%）" % (len(rows)-len(pick), format(res['drop_declared'], ',')),
 "",
 "相对已有 4,718 万 = +%.0f%%" % (tot_new*100.0/47182251),
 "Top 州：" + " / ".join("%s %s万" % (k, round(v/1e4)) for k, v in by_state.most_common(6)),
 "",
 "下一步 S7：入册 steps.json + 出最终决策报告"]))
