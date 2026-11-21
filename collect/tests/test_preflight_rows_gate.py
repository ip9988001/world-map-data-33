#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D15 收尾对账门禁单测（离线，不碰网络）。

要证明四件事：
  ① status=ok 但 rows 少于 declared×(1-0.5%) → FAIL（138c05 形态会被抓）；
  ② status=partial 且 rows 不足 → 只列出，不 FAIL（诚实标注放行）；
  ③ 计划里有 `expect_live`（returnCountOnly）时作为**第二分母**：
     rows=2,290 / live 2,300 → 缺 0.43%（<0.5%）通过；
     rows=2,285 / declared 2,270（过期快照）→ 对 live 缺 0.65% → FAIL（证明 live 分母真的参与判定）；
  ④ 没有账本 → WARN，不假装通过。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import preflight_dispatch as pf  # noqa: E402


def _mkledger(recs):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"schema": "collect-ledger/v1", "stage": "05b",
                   "layers_n": len(recs), "records": recs}, f)
    return p


def _mkplan(live):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"schema": "collect-plan/v1", "stage": "05b",
                   "layers_n": len(live), "expect_live": live,
                   "expect_source": "returnCountOnly@plan"}, f)
    return p


class RowsGateTest(unittest.TestCase):
    def tearDown(self):
        for p in getattr(self, "_tmp", []):
            try:
                os.unlink(p)
            except OSError:
                pass

    def _paths(self, recs, live=None):
        self._tmp = [_mkledger(recs)]
        plan = _mkplan(live) if live is not None else ""
        if plan:
            self._tmp.append(plan)
        return self._tmp[0], plan

    def test_ok_but_short_fails(self):
        lp, pp = self._paths([{"layer": "138c05_x", "status": "ok",
                               "rows": 2131, "declared": 2298}])
        it = pf.judge_rows_vs_expect("05b", lp, pp)
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(it["short_ok_status"][0]["layer"], "138c05_x")
        self.assertAlmostEqual(it["short_ok_status"][0]["gap_pct"], 7.2672, places=3)

    def test_partial_is_noted_not_failed(self):
        lp, pp = self._paths([{"layer": "p1", "status": "partial",
                               "rows": 2131, "declared": 2298}])
        it = pf.judge_rows_vs_expect("05b", lp, pp)
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(len(it["short_other_status"]), 1)

    def test_live_denominator_participates(self):
        # 对 declared 2298 通过（2290/2298=99.65%），对 live 2300 也通过（99.57%）
        lp, pp = self._paths([{"layer": "l1", "status": "ok", "rows": 2290,
                               "declared": 2298}], live={"l1": 2300})
        self.assertEqual(pf.judge_rows_vs_expect("05b", lp, pp)["status"], "PASS")
        # 2285：对过期快照 declared=2270 通过（100.66%），对 live=2300 缺 0.65% > 0.5% → FAIL
        # （快照比实时小 = 02:00 抓的 row_count 落后上游，正是 138c05 的 2,298/2,300 形态）
        lp2, pp2 = self._paths([{"layer": "l1", "status": "ok", "rows": 2285,
                                 "declared": 2270}], live={"l1": 2300})
        it = pf.judge_rows_vs_expect("05b", lp2, pp2)
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(it["short_ok_status"][0]["denominator"], "live")

    def test_no_ledger_warns(self):
        it = pf.judge_rows_vs_expect("05b", "/nonexistent/05b_ledger.json")
        self.assertEqual(it["status"], "WARN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
