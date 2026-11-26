#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归抽样（muse-000271 §四.4）：从「未被新别名命中」的层里分层抽样 ≥200 层。

分层口径（每层只进一个格子）：
  · 州 = rows-census.jsonl 的 state_guess（前 5 行 map_row 的多数票，仅作分层，不作判定）
  · 每州最多 4 层：优先「有 dropped_below_c>0」（split 修复唯一可能动的层）+ in_rows 小的
  · 排除：616 层新别名命中集（另有全量 A/B）、58 层 B 类（不许当自己的回归证据）
  · 单项 in_rows 上限 400k（控制耗时），总量上限 25M 行
输出：jobs-regression.jsonl + 一份选择账（stdout JSON）。
"""
from __future__ import annotations

import collections
import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import split_addr as SA  # noqa: E402

NEW = ("strname strtype strsuffix strsuf feanme featyp sfeanme sfeatyp gcstname streetnm ostreetnm "
       "addressroadname addrsn roadname roadnamesuffix roadtype roadnm roadsuffixdir streetdescription "
       "thoroughfare thorofare landbasedbotblstreetnamesstr sitestreetname sitestreet fullstnm locstnam "
       "locstsuf msagroute stnameps stdstreet propstreet propsuffix civicstreet streettho lstconcat "
       "strnum civicnum").split()
NEWSET = {SA._norm(x) for x in NEW}
MAX_ROWS = 400_000
BUDGET = 25_000_000
PER_STATE = 5


def main():
    cov = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "analysis", "fieldmap-20261125",
                                              "layer-coverage.v2.csv"), encoding="utf-8")):
        cov[r["layer"]] = r
    census = {json.loads(l)["layer_id"]: json.loads(l)
              for l in open(os.path.join(HERE, "rows-census.jsonl"), encoding="utf-8")}
    b58 = {json.loads(l)["layer_id"] for l in open(os.path.join(HERE, "jobs-b58.jsonl"), encoding="utf-8")}
    affected = {json.loads(l)["layer_id"] for l in open(os.path.join(HERE, "jobs-affected.jsonl"),
                                                       encoding="utf-8")}
    rnd = random.Random(20261126)
    pools = collections.defaultdict(list)
    for lid, c in cov.items():
        if lid in affected or lid in b58:
            continue
        n = int(c["in_rows"] or 0)
        if n <= 0 or n > MAX_ROWS:
            continue
        pools[census.get(lid, {}).get("state_guess", "")].append(
            (lid, n, int(c["dropped_below_c"] or 0)))
    picked, total = [], 0
    for st in sorted(pools):
        cand = sorted(pools[st], key=lambda x: (-(x[2] > 0), x[1]))
        head = cand[:2]                                    # 每州：2 个「有丢弃行、最小」的
        rest = [x for x in cand[2:]]
        rnd.shuffle(rest)
        for item in head + rest[:PER_STATE - 2]:
            if total + item[1] > BUDGET:
                continue
            picked.append(item)
            total += item[1]
    out = open(os.path.join(HERE, "jobs-regression.jsonl"), "w", encoding="utf-8")
    for lid, n, d in picked:
        out.write(json.dumps({"layer_id": lid, "url": census.get(lid, {}).get("url", ""),
                              "reason_code": "regression_sample", "in_rows": n,
                              "dropped_below_c": d}, ensure_ascii=False) + "\n")
    out.close()
    states = collections.Counter(census.get(x[0], {}).get("state_guess", "") for x in picked)
    origins = collections.Counter(cov[x[0]]["dialect_origin"] for x in picked)
    kinds = collections.Counter(cov[x[0]]["source_layer_kind"] for x in picked)
    print(json.dumps({"picked": len(picked), "rows": total, "states": dict(states),
                      "states_covered": len([k for k in states if k]),
                      "dialect_origin": dict(origins), "source_layer_kind": dict(kinds),
                      "layers_with_dropped": sum(1 for x in picked if x[2] > 0)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
