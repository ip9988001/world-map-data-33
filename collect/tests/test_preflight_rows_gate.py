#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D15 收尾对账门禁单测（离线，不碰网络）。

要证明四件事：
  ① status=ok 但 rows 少于 declared×(1-0.5%) → FAIL（138c05 形态会被抓）；
  ② status=partial 且 rows 不足 → 只列出，不 FAIL（诚实标注放行）；
  ③ 计划里有 `expect_live`（returnCountOnly）时作为**第二分母**：
     rows=2,299 / live 2,300 → 缺 0.04%（<0.1%）通过；
     rows=2,296 / declared 2,270（过期快照）→ 对 live 缺 0.17% → FAIL（证明 live 分母真的参与判定）；
  ④ 没有账本 → WARN，不假装通过。
  ⑤ 本轮计划内层豁免（W33-046）：force 名单里的层不因 D15 报警，但必须明细可审；
     不在名单里的照旧 FAIL；名单空 → 一人不赦（fail-closed）。
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
        # 对 declared 2298 通过（2299/2298），对 live 2300 也通过（99.96% ≥ 99.9%）
        lp, pp = self._paths([{"layer": "l1", "status": "ok", "rows": 2299,
                               "declared": 2298}], live={"l1": 2300})
        self.assertEqual(pf.judge_rows_vs_expect("05b", lp, pp)["status"], "PASS")
        # 2296：对过期快照 declared=2270 通过（101.1%），对 live=2300 缺 0.17% > 0.1% → FAIL
        # （快照比实时小 = 02:00 抓的 row_count 落后上游，正是 138c05 的 2,298/2,300 形态）
        lp2, pp2 = self._paths([{"layer": "l1", "status": "ok", "rows": 2296,
                                 "declared": 2270}], live={"l1": 2300})
        it = pf.judge_rows_vs_expect("05b", lp2, pp2)
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(it["short_ok_status"][0]["denominator"], "live")

    def test_no_ledger_warns(self):
        it = pf.judge_rows_vs_expect("05b", "/nonexistent/05b_ledger.json")
        self.assertEqual(it["status"], "WARN")


# ---------------------------------------------------------------------------
# W33-046（muse-000134 决定④）：D15「本轮计划内层豁免」
#   权威来源 = 本次派单的 --force-layers（不是仓里的旧 *_plan.json）
#   a 无 force → 照旧 FAIL / b 三层全在 force → PASS 且明列豁免 / c force 只放一层 → 另两层仍 FAIL
# ---------------------------------------------------------------------------
class InPlanExemptTest(unittest.TestCase):
    # run 44882397022 · preflight D15 报警三层（账本真值：layer / rows / declared，一字未改）
    SHORT3 = [
        ("arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0", 39504, 39751),
        ("cgis_rest_services_911_Addresses_Public_View_FeatureServer_2", 81437, 81772),
        ("qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0", 181529, 181750),
    ]

    def tearDown(self):
        for p in getattr(self, "_tmp", []):
            try:
                os.unlink(p)
            except OSError:
                pass

    def _ledger(self, extra=()):
        recs = [{"layer": l, "status": "ok", "rows": r, "declared": d}
                for l, r, d in list(self.SHORT3) + list(extra)]
        self._tmp = [_mkledger(recs)]
        return self._tmp[0]

    def test_a_no_force_still_fails(self):
        """a. 没给 force 名单 → 三层照旧全 FAIL（门禁未被削弱）。"""
        lp = self._ledger()
        it = pf.judge_rows_vs_expect("05b", lp, "")
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(len(it["short_ok_status"]), 3)
        self.assertEqual(it["exempt_in_plan"], [])
        for lid, _, _ in self.SHORT3:
            self.assertIn(lid[:36], it["detail"])

    def test_a2_empty_force_is_fail_closed(self):
        """a'. force 传了但解析为空（空串 / 全逗号）→ 一个人也不豁免。"""
        lp = self._ledger()
        for empty in ("", " , ,, ", None, []):
            it = pf.judge_rows_vs_expect("05b", lp, "", exempt_layers=empty)
            self.assertEqual(it["status"], "FAIL", "exempt=%r 不该放行" % (empty,))
            self.assertEqual(len(it["short_ok_status"]), 3)
            self.assertEqual(it["exempt_in_plan"], [])

    def test_b_all_in_force_passes_and_lists_them(self):
        """b. 三层全在 force → PASS，且 detail 与 JSON 字段都把豁免层写明白（不许人间蒸发）。"""
        lp = self._ledger()
        force = [l for l, _, _ in self.SHORT3]
        it = pf.judge_rows_vs_expect("05b", lp, "", exempt_layers=force)
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(it["short_ok_status"], [])
        self.assertEqual(it["exempt_source"], "force_layers")
        self.assertEqual([x["layer"] for x in it["exempt_in_plan"]], force)
        self.assertIn("本轮计划内豁免 3 层", it["detail"])
        for x in it["exempt_in_plan"]:
            self.assertIn(x["layer"][:40], it["detail"])     # 层名进 detail
            self.assertIn("缺%.2f%%" % x["gap_pct"], it["detail"])  # 缺口进 detail
            self.assertEqual(x["exempt"], "in_force_layers")
        # 豁免只影响 D15 报警，不给人“记绿”：status/rows/缺口 原样留着
        l1 = [x for x in it["exempt_in_plan"] if x["layer"] == force[0]][0]
        self.assertEqual((l1["status"], l1["rows"], l1["declared"]), ("ok", 39504, 39751))
        self.assertAlmostEqual(l1["gap_pct"], 0.6214, places=3)

    def test_c_partial_force_keeps_others_failing(self):
        """c. force 只放 1 层 → 这一层豁免，另 2 层仍 FAIL（豁免不能无限扩张）。"""
        lp = self._ledger()
        it = pf.judge_rows_vs_expect("05b", lp, "", exempt_layers=[self.SHORT3[0][0]])
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual([x["layer"] for x in it["exempt_in_plan"]], [self.SHORT3[0][0]])
        left = [b["layer"] for b in it["short_ok_status"]]
        self.assertEqual(left, [self.SHORT3[1][0], self.SHORT3[2][0]])
        self.assertIn("不在本轮 force 名单里", it["detail"])

    def test_out_of_force_layer_still_fails(self):
        """反例（最关键）：已采短层不在 force 名单 → 不管名单里有多少别的层，它照样 FAIL。"""
        ghost = ("ghost_not_in_force_arcgis_FeatureServer_0", 900, 1000)   # 缺 10%
        lp = self._ledger(extra=[ghost])
        it = pf.judge_rows_vs_expect("05b", lp, "",
                                     exempt_layers=[l for l, _, _ in self.SHORT3])
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual([b["layer"] for b in it["short_ok_status"]], [ghost[0]])
        self.assertAlmostEqual(it["short_ok_status"][0]["gap_pct"], 10.0, places=3)
        self.assertEqual(len(it["exempt_in_plan"]), 3)
        self.assertIn("ghost_not_in_force", it["detail"])

    def test_partial_status_not_affected_by_exempt(self):
        """口径不变：partial/short 本来就只列不判，且不会被计入“豁免”名单。"""
        lp, pp = self._paths([{"layer": "p1", "status": "partial",
                               "rows": 2131, "declared": 2298}])
        it = pf.judge_rows_vs_expect("05b", lp, pp, exempt_layers=["p1"])
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(len(it["short_other_status"]), 1)
        self.assertEqual(it["exempt_in_plan"], [])

    def _paths(self, recs, live=None):
        self._tmp = [_mkledger(recs)]
        plan = _mkplan(live) if live is not None else ""
        if plan:
            self._tmp.append(plan)
        return self._tmp[0], plan

    def test_live_denominator_exempt_uses_live(self):
        """双分母照旧：对 live 击穿的层，豁免明细里的分母写 live（不是 declared）。"""
        lp, pp = self._paths([{"layer": "l1", "status": "ok", "rows": 2296,
                               "declared": 2270}], live={"l1": 2300})
        it = pf.judge_rows_vs_expect("05b", lp, pp, exempt_layers=["l1"])
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(it["exempt_in_plan"][0]["denominator"], "live")
        self.assertEqual(it["exempt_in_plan"][0]["expect_live"], 2300)



if __name__ == "__main__":
    unittest.main(verbosity=2)
