#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 `max_shards` 截断计划 —— **砍片必须喊出来**（W33-036）。

为什么单独立一个模块（2026-10-31 用户定案）：
  旧实现把截断写成 workflow 里的两行 shell：
      `if [ "$MAX" != "0" ] && [ "$N" -gt "$MAX" ]; then N="$MAX"; fi`
  于是 run 41126178216 的 3 片被砍成 2 片，**shard 2 的 6 层静默消失**：
  run 里看不到、账本里没有、看着像「本来就没采到」。这跟「同组 pending 被挤掉」是同一类病
  ——不报错、看着像正常，代价是无法归因。

现在：砍片必须
  ① 打 `::warning::`，完整列出**被砍掉的分片号 + 其中每一层的 id**（不许只报数量）；
  ② 写进 plan artifact：`shards_dropped[]`（逐片层清单）+ `plan_truncated{expected_shards,
     actual_shards, dropped_layers[]}`，让收口时一眼看到「这轮注定漏了谁」；
  ③ `max_shards=0` = 全起，一个不砍；
  ④ 计划本身不动（`shards` / `shards_n` 保持原样）—— 被砍的片在账本里仍然是「该跑没跑」，
     不会被改写成「本来就没有这片」。

用法：
  python3 collect/plan_truncate.py --plan collect/ledger/04b_plan.json --max-shards 2 \
      --github-output "$GITHUB_OUTPUT"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

MAX_MATRIX_JOBS = 250          # GitHub matrix 硬上限 256，留余量


def _sid(s, fallback):
    if isinstance(s, dict) and isinstance(s.get("shard"), int):
        return s["shard"]
    return fallback


def _layers(s):
    if isinstance(s, dict):
        return list(s.get("layers") or [])
    return list(s or [])


def truncate_plan(plan, max_shards, warn=None):
    """把 plan 截到前 `max_shards` 片。返回 (plan, kept, dropped)。

    `warn` 是打印函数（测试注入 list.append 用）；默认打到 stderr。
    纯函数：不读盘、不写盘 —— 单测直接调它。
    """
    warn = warn or (lambda m: print(m, file=sys.stderr))
    shards = list(plan.get("shards") or [])
    expected = len(shards) or int(plan.get("shards_n") or 0)
    try:
        limit = int(max_shards or 0)
    except (TypeError, ValueError):
        limit = 0
    keep_n = expected if limit <= 0 else min(limit, expected)
    kept, dropped = shards[:keep_n], shards[keep_n:]
    dropped_info = []
    for i, s in enumerate(dropped):
        sid = _sid(s, keep_n + i)
        dropped_info.append({"shard": sid, "layers": _layers(s)})
    dropped_layers = [lid for d in dropped_info for lid in d["layers"]]

    plan["shards_dropped"] = dropped_info
    plan["plan_truncated"] = None if not dropped_info else {
        "max_shards": limit,
        "expected_shards": expected,
        "actual_shards": keep_n,
        "dropped_shards": [d["shard"] for d in dropped_info],
        "dropped_layers": dropped_layers,
        "dropped_layers_n": len(dropped_layers),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": ("max_shards 截断：被砍的片**本轮注定不跑**（不是「没采到」）。"
                 "列入 shards_dropped[]，收口文档单列一节，账本 shards_incomplete 里同样会点名。"),
    }

    if dropped_info:
        warn("::warning::max_shards=%d 截断计划：%d 片 → %d 片，**%d 层本轮注定不会跑**"
             % (limit, expected, keep_n, len(dropped_layers)))
        for d in dropped_info:
            warn("::warning::被砍的分片 shard %d（%d 层）：%s"
                 % (d["shard"], len(d["layers"]), ", ".join(d["layers"])))
        warn("::warning::片/层清单已写进 plan 的 shards_dropped[] 与 plan_truncated{}；"
             "要全跑请 max_shards=0")
    if keep_n > MAX_MATRIX_JOBS:
        warn("::warning::片数 %d 超过 matrix 上限余量 %d：GitHub matrix 最多 256 job，"
             "请加大 size 或分轮" % (keep_n, MAX_MATRIX_JOBS))
    return plan, kept, dropped_info


def matrix_of(kept):
    return {"include": [{"shard": _sid(s, i)} for i, s in enumerate(kept)]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True, help="full_plan.py 产出的计划 JSON（原地写回）")
    ap.add_argument("--max-shards", default="0", help="最多跑几片（0 = 全部，一个不砍）")
    ap.add_argument("--out", default="", help="写回路径（默认原地）")
    ap.add_argument("--github-output", default="", help="把 shards= / matrix= 写进 $GITHUB_OUTPUT")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写盘")
    a = ap.parse_args()

    if not os.path.exists(a.plan):
        print("::error::计划不存在：%s（先跑 full_plan.py）" % a.plan, file=sys.stderr)
        return 2
    plan = json.load(open(a.plan, encoding="utf-8"))
    plan, kept, dropped = truncate_plan(plan, a.max_shards)
    m = matrix_of(kept)

    if not a.dry_run:
        out = a.out or a.plan
        json.dump(plan, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("计划已写回 %s（跑 %d 片 / 砍 %d 片）" % (out, len(kept), len(dropped)))
    if a.github_output:
        with open(a.github_output, "a", encoding="utf-8") as f:
            f.write("shards=%d\n" % len(kept))
            f.write("matrix=%s\n" % json.dumps(m))
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ and dropped:
        with open(summ, "a", encoding="utf-8") as f:
            f.write("\n> ⚠️ `max_shards=%s` 截断计划：%d 片 → %d 片，**%d 层本轮注定不会跑**\n\n"
                    % (a.max_shards, plan["plan_truncated"]["expected_shards"],
                       len(kept), plan["plan_truncated"]["dropped_layers_n"]))
            f.write("| 被砍分片 | 层数 | 层 id |\n|---|---|---|\n")
            for d in dropped:
                f.write("| %d | %d | %s |\n" % (d["shard"], len(d["layers"]),
                                                ", ".join("`%s`" % x for x in d["layers"])))
    print(json.dumps({"shards": len(kept), "dropped_shards": [d["shard"] for d in dropped],
                      "dropped_layers_n": len(plan["plan_truncated"]["dropped_layers"])
                      if plan["plan_truncated"] else 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
