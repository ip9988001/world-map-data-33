#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量补采 · 收官文档生成器：把分片账本合成一份「逐层 declared vs 实采」的 Markdown。

输入：collect/ledger/<stage>_shard*.json（每片一份，由 full_shard.py 写）
输出：docs/STEP04-FULL-<date>.md（或 step05b/07b/10b 对应的文件名）
规则：只写账本里的事实；差额给出百分比与可能原因分类，绝不美化。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TITLES = {"step04b": ("STEP04", "全州放量（大层 row_count>300,000 全量补采）"),
          "step05b": ("STEP05", "县市碎片（5,000~300,000 行）全量补采"),
          "step07b": ("STEP07", "碎片补齐（1~4,999 行）全量补采"),
          "step10b": ("STEP10", "宗地面层 batch2+（strong/weak 有效层）")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, help="step04b / step05b / step07b / step10b")
    ap.add_argument("--out", default="")
    ap.add_argument("--plan", default="")
    a = ap.parse_args()
    stage = a.stage
    tag, title = TITLES.get(stage, (stage.upper(), stage))
    files = sorted(glob.glob(os.path.join(HERE, "ledger", stage + "_shard*.json")))
    if not files:
        raise SystemExit("没有账本：collect/ledger/%s_shard*.json" % stage)
    recs, meta = [], {}
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        meta.setdefault("shards_total", d.get("shards_total"))
        meta.setdefault("size", d.get("size"))
        meta.setdefault("unit_rows", d.get("unit_rows"))
        recs += d.get("records") or []
    by = {}
    for r in recs:                                  # 同一层出现多次取「最好」的那次
        prev = by.get(r["layer"])
        rank = {"ok": 4, "empty": 3, "skipped_done": 2, "partial": 1, "failed": 0}
        if prev is None or rank.get(r["status"], 0) > rank.get(prev["status"], 0):
            by[r["layer"]] = r
    recs = sorted(by.values(), key=lambda r: -(r.get("declared") or 0))

    cnt = {}
    for r in recs:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    declared = sum((r.get("declared") or 0) for r in recs)
    rows = sum((r.get("rows") or 0) for r in recs)
    gaps = [r for r in recs if (r.get("declared") or 0) > (r.get("rows") or 0)]
    gaps.sort(key=lambda r: ((r.get("declared") or 0) - (r.get("rows") or 0)), reverse=True)
    active = [r for r in recs if r["status"] not in ("skipped_done",)]
    bad = [r for r in recs if r["status"] in ("failed", "partial")]

    plan = {}
    if a.plan and os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8"))

    L = ["# %s 全量补采 · 收官账（%s）" % (tag, datetime.now(timezone.utc).strftime("%Y-%m-%d")), "",
         "## 一、总账", "",
         f"- 阶段：`{stage}` —— {title}",
         f"- 计划：{plan.get('layers_n', '?')} 层 / 声明 {plan.get('declared_rows', 0):,} 行 / "
         f"{plan.get('shards_n', '?')} 片（每片 {plan.get('size', '?')} 层，unit_rows={plan.get('unit_rows', '?')}）",
         f"- 账本覆盖：**{len(recs)} 层**（片文件 {len(files)} 个）",
         f"- 逐态：**ok {cnt.get('ok', 0)}** / empty {cnt.get('empty', 0)} / "
         f"partial {cnt.get('partial', 0)} / failed {cnt.get('failed', 0)} / "
         f"skipped_done {cnt.get('skipped_done', 0)}",
         f"- 声明行合计：**{declared:,}**；实采行合计：**{rows:,}**；"
         f"差额 {declared - rows:,}（{100.0 * (declared - rows) / max(declared, 1):.3f}%）", "",
         "> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。",
         "> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。", ""]

    L += ["## 二、差额最大的 10 层", ""]
    if gaps:
        L += ["| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |", "|---|---|---|---|---|---|"]
        for r in gaps[:10]:
            dcl, rw = (r.get("declared") or 0), (r.get("rows") or 0)
            L.append("| `%s` | %s | %s | %s | %s | %s |"
                     % (r["layer"], f"{dcl:,}", f"{rw:,}", f"{dcl - rw:,}",
                        r["status"], (r.get("reason") or "")[:80]))
    else:
        L.append("**零差额**：所有层实采 == 声明。")
    L += [""]

    L += ["## 三、残缺层清单（failed / partial，逐条原因）", ""]
    if bad:
        L += ["| 层 | 状态 | 声明 | 实采 | 原因 |", "|---|---|---|---|---|"]
        for r in bad:
            L.append("| `%s` | %s | %s | %s | %s |"
                     % (r["layer"], r["status"], r.get("declared"), r.get("rows"),
                        (r.get("reason") or "")[:120]))
    else:
        L.append("**无。** 本阶段没有 failed / partial 层。")
    L += [""]

    L += ["## 四、逐层台账（按声明行数降序）", "",
          "| # | 层 | 声明 | 实采 | 差额% | 状态 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(recs, 1):
        dcl, rw = (r.get("declared") or 0), (r.get("rows") or 0)
        pct = (100.0 * (dcl - rw) / dcl) if dcl else 0.0
        L.append("| %d | `%s` | %s | %s | %.2f%% | %s |"
                 % (i, r["layer"], f"{dcl:,}" if dcl else "-",
                    f"{rw:,}" if rw is not None else "-", pct, r["status"]))
    L += ["", "## 五、复现", "", "```bash",
          "gh workflow run collect-full.yml -f stage=%s" % stage,
          "python3 collect/full_plan.py --stage %s --size %s --out collect/ledger/%s_plan.json"
          % (stage, plan.get("size", 20), stage),
          "python3 collect/full_shard.py --stage %s --shard 0 --plan collect/ledger/%s_plan.json"
          % (stage, stage), "```", ""]

    out = a.out or os.path.join(ROOT, "docs", tag + "-FULL-2026-10-30.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))

    # 汇总账本（单一文件，spec 要求的 collect/step04b_ledger.json）
    led = {"schema": "collect-ledger-agg/v1", "stage": stage, "at":
           datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "layers_n": len(recs), "ok": cnt.get("ok", 0), "empty": cnt.get("empty", 0),
           "partial": cnt.get("partial", 0), "failed": cnt.get("failed", 0),
           "skipped_done": cnt.get("skipped_done", 0),
           "declared": declared, "rows": rows, "gap": declared - rows,
           "plan": {k: plan.get(k) for k in ("layers_n", "declared_rows", "shards_n", "size")},
           "records": recs}
    agg = os.path.join(HERE, stage + "_ledger.json")
    json.dump(led, open(agg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: led[k] for k in ("stage", "layers_n", "ok", "empty", "partial",
                                          "failed", "skipped_done", "declared", "rows")},
                     ensure_ascii=False))
    print("写入 %s 与 %s" % (out, agg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
