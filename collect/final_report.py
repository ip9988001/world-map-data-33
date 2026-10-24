#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 06：汇总 + 覆盖率表（实收行数 ÷ 2020 Census 住房单元数）

数据源：`collect/pilot_report.json`（工人每层写一条 manifest，报告 job 增量合并）
       + `collect/layer_plan.csv`（layer_id → state / title / 声明 count）

2026-10-24 改：老版本读 `collect/out/*/_manifest.json` —— 那是本机临时目录，
Actions 上跑完就删（即传即删），所以永远读到 0 层。真实来源是 checkpoint 汇总。
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT_F = os.path.join(HERE, "pilot_report.json")
PLAN_F = os.path.join(HERE, "layer_plan.csv")
OUT_MD = os.path.join(HERE, "reports", "FINAL_REPORT.md")
OUT_JSON = os.path.join(HERE, "layer_status.json")

# 2020 Census 住房单元数（近似值，覆盖率分母）
HU = {
    "AL": 2270000, "AK": 328000, "AZ": 3030000, "AR": 1370000, "CA": 14300000, "CO": 2500000,
    "CT": 1520000, "DE": 450000, "DC": 340000, "FL": 9800000, "GA": 4400000, "HI": 590000,
    "ID": 740000, "IL": 5400000, "IN": 2900000, "IA": 1400000, "KS": 1300000, "KY": 2000000,
    "LA": 2000000, "ME": 740000, "MD": 2500000, "MA": 2900000, "MI": 4600000, "MN": 2400000,
    "MS": 1300000, "MO": 2800000, "MT": 510000, "NE": 840000, "NV": 1200000, "NH": 640000,
    "NJ": 3700000, "NM": 900000, "NY": 8300000, "NC": 4500000, "ND": 360000, "OH": 5100000,
    "OK": 1700000, "OR": 1700000, "PA": 5600000, "RI": 470000, "SC": 2200000, "SD": 380000,
    "TN": 2900000, "TX": 11000000, "UT": 1100000, "VT": 330000, "VA": 3500000, "WA": 3100000,
    "WV": 880000, "WI": 2700000, "WY": 280000, "PR": 1400000,
}


def state_of(layer_id, plan):
    """层 → 州。先在 plan 里按 id 精确找，再退回到去掉 @state-n 后缀找。"""
    r = plan.get(layer_id)
    if r:
        return r.get("state") or "未定位"
    base = layer_id.split("@")[0]
    r = plan.get(base)
    if r:
        return r.get("state") or "未定位"
    if "@" in layer_id:                       # id@KS-5 这种，后缀就是州
        tail = layer_id.split("@", 1)[1]
        return tail.split("-")[0] or "未定位"
    return "未定位"


def main():
    rep = json.load(open(REPORT_F, encoding="utf-8"))
    plan = {}
    if os.path.exists(PLAN_F):
        for row in csv.DictReader(open(PLAN_F, encoding="utf-8")):
            plan[row["layer_id"]] = row

    per_state = {}
    per_layer = []
    for m in (rep.get("detail") or []):
        lid = m.get("id")
        if not lid:
            continue
        st = state_of(lid, plan)
        rows = m.get("rows") or 0
        per_state[st] = per_state.get(st, 0) + rows
        per_layer.append({"id": lid, "state": st, "rows": rows, "count": m.get("count"),
                          "diff": m.get("diff"), "err": m.get("err") or ""})

    total = sum(per_state.values())
    failed = [x for x in per_layer if x["err"] or not x["rows"]]
    covered = [st for st in per_state if st in HU]
    lines = [
        "# 三仓采集 · 最终报告",
        "",
        "- 生成时间：%s" % __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "- 已采图层：**%d**" % len(per_layer),
        "- 实收行数：**%s**" % format(total, ","),
        "- 声明行数合计：%s" % format(sum((x["count"] or 0) for x in per_layer), ","),
        "- 对账：worst_diff = **%s**（报告口径）" % rep.get("worst_diff"),
        "- 失败/零行层：%d" % len(failed),
        "- 覆盖州/属地：%d（有 Census 分母的 %d 个）" % (len(per_state), len(covered)),
        "",
        "## 覆盖率（实收行数 ÷ 住房单元数）",
        "",
        "| 州 | 实收行数 | 住房单元数 | 覆盖率 |",
        "|---|---|---|---|",
    ]
    for st in sorted(per_state, key=lambda s: -per_state[s]):
        hu = HU.get(st)
        cov = f"{per_state[st]/hu:.0%}" if hu else "—"
        lines.append("| %s | %s | %s | %s |" % (st, format(per_state[st], ","), format(hu, ",") if hu else "—", cov))
    lines += ["", "## 失败/零行层（%d）" % len(failed), ""]
    lines += ["- `%s` %s" % (x["id"], (x["err"] or "rows=0")[:80]) for x in failed[:50]] or ["- 无"]
    lines += ["", "## 缺口说明", "",
              "- `blocked.json` 里的层是主动跳过的（上游下线 / 通道不支持），不是静默丢",
              "- 本报告只统计**已采到行**的层；未采的层不计入覆盖率分母之外的口径"]

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"total_rows": total, "layers": len(per_layer), "failed": len(failed),
               "states": {st: per_state[st] for st in per_state},
               "coverage": {st: round(per_state[st] / HU[st], 3) for st in per_state if st in HU}},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"layers": len(per_layer), "total_rows": total, "states": len(per_state),
                      "failed": len(failed), "report": "collect/reports/FINAL_REPORT.md"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
