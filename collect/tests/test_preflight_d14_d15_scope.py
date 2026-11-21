#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D14 / D15 的「方向」与「历史 vs 本轮」口径锁定（离线，不碰网络、不派单、不改账本）。

W33-047 事故：force-only 补采（run 44958617978 / 44959175837）连派两单，都被
  ❌ D14 阶段账本 3,304 层 / 计划 2,770 层（差 +534，19.28%）
  ❌ D15  3 层历史短采（不在本轮 force 名单）
钉死在 preflight → 4 层真实缺口一层都采不到。本文件锁住这些契约：

  D14 方向：① 账本**多**于计划 → WARN（累积形态，不阻断，direction=ledger_long）；
           ② 账本**少**于计划 >1% → FAIL（W33-013 的 2,325/2,770 事故不许被改坏）；
           ③ 两侧一致 / 1% 以内 → PASS；
           ④ 「账本只有 4 层」这种真漏采照旧 FAIL（补采身份不是免罪符）。
  D15 归属：⑤ 没有声明文件 → 名单外 ok-but-short 照旧 FAIL（fail-closed，一行不放宽）；
           ⑥ 声明文件里按层登记了 reason → 降 WARN，层名/缺口/理由全部留痕；
           ⑦ 只声明了一部分 → 未声明的照旧 FAIL；
           ⑧ 声明缺 reason / 文件坏 → 一个也不认；
           ⑨ 缺口比声明时扩大 >1pp → 仍 FAIL（声明不是永久免死牌）；
           ⑩ force 名单内的层仍走豁免分支、partial/short 仍只列不判。
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import preflight_dispatch as pf  # noqa: E402

SHORT3 = [  # run 44882397022 的 D15 真值（账本原样：layer / rows / declared）
    ("arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0", 39504, 39751),
    ("cgis_rest_services_911_Addresses_Public_View_FeatureServer_2", 81437, 81772),
    ("qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0", 181529, 181750),
]


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = []

    def tearDown(self):
        for p in self._tmp:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _dump(self, obj, suffix=".json"):
        fd, p = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        self._tmp.append(p)
        return p

    def ledger(self, layers_n, records=(), plan_layers=None):
        led = {"schema": "collect-ledger-agg/v1", "stage": "05b",
               "layers_n": layers_n, "records": list(records)}
        if plan_layers is not None:
            led["plan"] = {"layers_n": plan_layers}
        return self._dump(led)

    def plan(self, layers_n, live=None):
        return self._dump({"schema": "collect-plan/v1", "stage": "05b",
                           "layers_n": layers_n, "expect_live": live or {},
                           "expect_source": "returnCountOnly@plan"})

    def ack(self, layers, gap=None, reason="历史遗留，见 run 44931175026", drop_reason=False,
            expires_at="2099-12-31"):
        rows = []
        for lid in layers:
            a = {"layer": lid, "reason": "" if drop_reason else reason,
                 "acked_by": "muse", "acked_at": "2026-11-22",
                 "expires_at": expires_at}
            if gap is not None:
                a["gap_pct"] = gap
            rows.append(a)
        return self._dump({"schema": "d15-ack/v1", "stage": "05b", "acked": rows})

    def short_recs(self, extra=()):
        return [{"layer": l, "status": "ok", "rows": r, "declared": d}
                for l, r, d in list(SHORT3) + list(extra)]


class D14Direction(_Tmp):
    """D14：判据分方向 —— 只对「账本少于计划」判 FAIL。"""

    def test_ledger_long_is_warn_not_fail(self):
        # 真实数字：05b 账本 3,304 层 / 计划 2,770 层 → +534（19.28%）
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(3304, plan_layers=2770))
        self.assertEqual(it["status"], "WARN")
        self.assertEqual(it["direction"], "ledger_long")
        self.assertEqual(it["diff"], 534)
        self.assertAlmostEqual(it["diff_pct"], 19.2779, places=3)
        self.assertIn("累积", it["detail"])

    def test_ledger_short_still_fails(self):
        # W33-013：2,325 / 2,770（少 19.3%）—— 这条绝不许松
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(2325, plan_layers=2770))
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(it["direction"], "ledger_short")
        self.assertEqual(it["diff"], -445)
        self.assertIn("账本比计划少", it["detail"])

    def test_single_layer_miss_fails(self):
        # 少 1 层 / 2,770 = 0.036% < 1% → PASS（容差内）；少 28 层 = 1.01% → FAIL
        self.assertEqual(
            pf.judge_ledger_plan_consistency("05b", self.ledger(2769, plan_layers=2770))["status"],
            "PASS")
        self.assertEqual(
            pf.judge_ledger_plan_consistency("05b", self.ledger(2742, plan_layers=2770))["status"],
            "FAIL")

    def test_balanced_passes(self):
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(2770, plan_layers=2770))
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(it["direction"], "balanced")
        self.assertEqual(it["diff"], 0)

    def test_small_excess_within_tolerance_passes(self):
        # +20 / 2,770 = 0.72% ≤ 1% → PASS，不制造噪音
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(2790, plan_layers=2770))
        self.assertEqual(it["status"], "PASS")

    def test_tiny_ledger_still_fails(self):
        # 「本轮只补 4 层」不能当免罪符：账本层数真的少了照旧 FAIL
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(4, plan_layers=2770))
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(it["direction"], "ledger_short")

    def test_plan_from_file_when_ledger_has_no_plan(self):
        it = pf.judge_ledger_plan_consistency("05b", self.ledger(3304), self.plan(2770))
        self.assertEqual(it["status"], "WARN")
        self.assertNotEqual(it["plan_source"], "ledger.plan")


class D15HistoryAck(_Tmp):
    """D15：历史缺口靠**显式声明**降 WARN，未声明的一行不让。"""

    def test_no_ack_file_keeps_failing(self):
        it = pf.judge_rows_vs_expect("05b", self.ledger(3, self.short_recs()), "")
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual(len(it["short_ok_status"]), 3)
        self.assertEqual(it["historical_short_ok_status"], [])

    def test_acked_layers_become_warn_with_trail(self):
        lp = self.ledger(3, self.short_recs())
        ap = self.ack([l for l, _, _ in SHORT3])
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=ap)
        self.assertEqual(it["status"], "WARN")
        self.assertEqual(it["short_ok_status"], [])
        hist = it["historical_short_ok_status"]
        self.assertEqual([h["layer"] for h in hist], [l for l, _, _ in SHORT3])
        self.assertEqual(hist[0]["rows"], 39504)
        self.assertEqual(hist[0]["declared"], 39751)
        self.assertIn("历史遗留", hist[0]["ack_reason"])
        self.assertIn("已声明", it["detail"])
        self.assertIn("LAWRENCEGIS", it["detail"])          # 层名进 detail
        self.assertIn("缺0.62%", it["detail"])              # 缺口进 detail
        self.assertEqual(it["d15_ack_path"], ap)

    def test_partial_ack_leaves_rest_failing(self):
        lp = self.ledger(3, self.short_recs())
        ap = self.ack([SHORT3[0][0]])
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=ap)
        self.assertEqual(it["status"], "FAIL")
        self.assertEqual([b["layer"] for b in it["short_ok_status"]],
                         [SHORT3[1][0], SHORT3[2][0]])
        self.assertEqual([h["layer"] for h in it["historical_short_ok_status"]], [SHORT3[0][0]])

    def test_ack_without_reason_is_ignored(self):
        lp = self.ledger(1, self.short_recs()[:1])
        ap = self.ack([SHORT3[0][0]], drop_reason=True)
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=ap)
        self.assertEqual(it["status"], "FAIL")

    def test_broken_ack_file_fails_closed(self):
        lp = self.ledger(1, self.short_recs()[:1])
        fd, p = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("{not json")
        self._tmp.append(p)
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=p)
        self.assertEqual(it["status"], "FAIL")

    def test_worsened_gap_still_fails(self):
        # 声明时缺 0.62%，现在缺 5%（同一层）→ 声明不覆盖，照旧 FAIL
        lp = self.ledger(1, [{"layer": SHORT3[0][0], "status": "ok",
                              "rows": 37763, "declared": 39751}])
        ap = self.ack([SHORT3[0][0]], gap=0.6214)
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=ap)
        self.assertEqual(it["status"], "FAIL")
        self.assertTrue(it["short_ok_status"][0].get("ack_worsened"))
        self.assertAlmostEqual(it["short_ok_status"][0]["ack_gap_pct"], 0.6214, places=4)

    def test_ack_and_force_together(self):
        # force 名单里的层 → 豁免明细；声明过的 → 历史明细；两者互不吞并
        lp = self.ledger(4, self.short_recs(extra=[("forced1", 10, 100)]))
        ap = self.ack([l for l, _, _ in SHORT3])
        it = pf.judge_rows_vs_expect("05b", lp, "", exempt_layers=["forced1"], ack_path=ap)
        self.assertEqual(it["status"], "WARN")
        self.assertEqual([e["layer"] for e in it["exempt_in_plan"]], ["forced1"])
        self.assertEqual(len(it["historical_short_ok_status"]), 3)

    def test_ack_does_not_touch_partial(self):
        rec = dict(SHORT3[0][0] and {"layer": SHORT3[0][0], "status": "partial",
                                     "rows": 39504, "declared": 39751})
        lp = self.ledger(1, [rec])
        ap = self.ack([SHORT3[0][0]])
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=ap)
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(len(it["short_other_status"]), 1)
        self.assertEqual(it["historical_short_ok_status"], [])

    def test_expired_ack_is_ignored(self):
        # 声明带 expires_at；过期 = 不认（防「声明一次、永久免检」）
        lp = self.ledger(1, self.short_recs()[:1])
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=self.ack([SHORT3[0][0]],
                                                                    expires_at="2020-01-01"))
        self.assertEqual(it["status"], "FAIL")
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=self.ack([SHORT3[0][0]],
                                                                    expires_at="2099-01-01"))
        self.assertEqual(it["status"], "WARN")

    def test_ack_without_expires_at_is_ignored(self):
        lp = self.ledger(1, self.short_recs()[:1])
        it = pf.judge_rows_vs_expect("05b", lp, "", ack_path=self.ack([SHORT3[0][0]],
                                                                    expires_at=None))
        self.assertEqual(it["status"], "FAIL")

    def test_default_ack_path_sits_next_to_ledger(self):
        lp = self.ledger(0, [])
        acked, p = pf.load_d15_ack("05b", lp)
        self.assertEqual(acked, {})
        self.assertEqual(os.path.dirname(p), os.path.dirname(lp))
        self.assertTrue(p.endswith("05b_d15_ack.json"))


class VerdictShape(unittest.TestCase):
    def test_warn_only_does_not_block_dispatch(self):
        # 派单只看 FAIL：WARN 不得让 rc!=0
        self.assertEqual(pf.verdict_of([{"id": "D14", "status": "WARN"},
                                        {"id": "D15", "status": "WARN"}]),
                         "PASS_WITH_WARNINGS")
        self.assertEqual(pf.verdict_of([{"id": "D14", "status": "PASS"},
                                        {"id": "D15", "status": "FAIL"}]), "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=1)
