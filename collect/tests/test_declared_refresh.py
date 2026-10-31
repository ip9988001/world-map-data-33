# -*- coding: utf-8 -*-
"""声明分母刷新（`--refresh-declared` / `--apply-declared-refresh`）的契约。

锁四类行为（全部离线：不打上游、不碰真账本）：
  1) 关系判据：实采 > 声明（超采=声明过期）/ 一致 / 欠采（真缺口）/ 上游 0 行
  2) 只读刷新**不写账本**：`refresh_declared()` 只产出建议 JSON（用假 probe 替掉网络）
  3) 采纳必须人工点头：`--declared-confirm` 不对 → 拒绝写盘（SystemExit）
  4) 采纳后账本留痕：`declared_refreshed_at` + `revisions[kind=declared_refreshed]` + 写前备份
  5) 只动 ok/missing/partial：capped / unverified / empty 的 declared 一律不碰
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import adjudicate_04b as A  # noqa: E402


def rec(layer, status, declared, rows):
    return {"layer": layer, "status": status, "declared": declared, "rows": rows,
            "gap": (declared - rows) if declared is not None else None}


def make_ledger(records):
    return {"schema": "collect-ledger-agg/v1", "stage": "04b", "records": records,
            "rows_capped": 0, "declared_unverifiable": 0, "revisions": []}


class Relation(unittest.TestCase):
    def test_over_declared_is_stale_snapshot(self):
        # 实采 120 > 声明 100：声明是过期快照（上游缩水/删数据）
        self.assertTrue(A._relation(120, 100).startswith("超采"))

    def test_within_tolerance_is_consistent(self):
        self.assertEqual(A._relation(100, 100), "一致")
        self.assertEqual(A._relation(99, 100), "一致")          # 1% 容差内

    def test_under_declared_is_real_gap(self):
        self.assertTrue(A._relation(50, 100).startswith("欠采"))

    def test_upstream_zero_invalidates_declaration(self):
        self.assertTrue(A._relation(0, 0).startswith("上游 0 行"))

    def test_unreachable_is_not_classified(self):
        self.assertEqual(A._relation(50, None), "不可复核")


class RefreshIsReadOnly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ledger = os.path.join(self.tmp, "04b_ledger.json")
        self.csv = os.path.join(self.tmp, "layer_plan_clean.csv")
        with open(self.ledger, "w", encoding="utf-8") as f:
            json.dump(make_ledger([
                rec("L_over", "ok", 100, 120), rec("L_short", "missing", 500, 0),
                rec("L_capped", "capped_by_upstream", None, 42),
                rec("L_unver", "unverified", 300, 0), rec("L_empty", "empty", 0, 0)]), f)
        with open(self.csv, "w", encoding="utf-8") as f:
            f.write("layer_id,url\n")
            for l in ("L_over", "L_short", "L_capped", "L_unver", "L_empty"):
                f.write("%s,https://example.invalid/%s/0\n" % (l, l))
        self.before = open(self.ledger, encoding="utf-8").read()

    def _fake_probe(self, url, timeout=25):
        return {"url": url, "http": 200, "count": {"L_over": 110, "L_short": 500}.get(
            url.rsplit("/", 2)[-2], None), "err": "", "elapsed_ms": 1}

    def test_refresh_only_reports_and_never_writes_ledger(self):
        out = os.path.join(self.tmp, "refresh.json")
        with mock.patch.object(A, "probe_return_count", self._fake_probe):
            rep = A.refresh_declared(self.ledger, self.csv, out, quiet=True)
        self.assertEqual(open(self.ledger, encoding="utf-8").read(), self.before)   # 账本没动
        self.assertTrue(os.path.exists(out))
        self.assertEqual(rep["probed_n"], 2)          # 只探 ok/missing/partial（capped/unverified/empty 跳过）
        self.assertEqual(rep["usable_n"], 2)
        self.assertEqual(rep["unreachable_n"], 0)
        self.assertEqual(rep["schema"], "declared-refresh/v1")
        lay = {x["layer"]: x for x in rep["layers"]}
        self.assertTrue(lay["L_over"]["relation"].startswith("超采"))
        self.assertEqual(lay["L_over"]["declared_new"], 110)


class ApplyNeedsHumanConfirm(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ledger = os.path.join(self.tmp, "04b_ledger.json")
        self.report = os.path.join(self.tmp, "refresh.json")
        with open(self.ledger, "w", encoding="utf-8") as f:
            json.dump(make_ledger([
                rec("L_over", "ok", 100, 120), rec("L_capped", "capped_by_upstream", None, 42),
                rec("L_unver", "unverified", 300, 0)]), f)
        with open(self.report, "w", encoding="utf-8") as f:
            json.dump({"at": "2026-10-31T01:00:00Z", "sums": {"declared_old": 100},
                       "layers": [{"layer": "L_over", "declared_new": 110, "relation": "超采（上游缩水）"},
                                  {"layer": "L_capped", "declared_new": 999, "relation": "一致"},
                                  {"layer": "L_unver", "declared_new": 300, "relation": "一致"}]}, f)

    def test_wrong_or_empty_confirm_refuses_to_write(self):
        before = open(self.ledger, encoding="utf-8").read()
        for bad in ("", "yes", "i-approve-declared-refresh"):
            with self.assertRaises(SystemExit):
                A.apply_declared_refresh(self.ledger, self.report, bad)
        self.assertEqual(open(self.ledger, encoding="utf-8").read(), before)

    def test_apply_writes_refresh_marker_and_revision_and_only_touches_allowed_states(self):
        A.apply_declared_refresh(self.ledger, self.report, A.DECLARED_CONFIRM_PHRASE)
        led = json.load(open(self.ledger, encoding="utf-8"))
        by = {r["layer"]: r for r in led["records"]}
        self.assertEqual(by["L_over"]["declared"], 110)
        self.assertEqual(by["L_over"]["declared_src"], "upstream_returnCount 2026-10-31T01:00:00Z")
        self.assertIsNone(by["L_capped"]["declared"])          # capped 不碰
        self.assertEqual(by["L_unver"]["declared"], 300)        # unverified 不碰（declared_new 同值也算不碰）
        self.assertEqual(led["declared_refreshed_at"], "2026-10-31T01:00:00Z")
        rev = [r for r in led["revisions"] if r.get("kind") == "declared_refreshed"]
        self.assertEqual(len(rev), 1)
        self.assertEqual(rev[0]["confirm"], A.DECLARED_CONFIRM_PHRASE)
        self.assertEqual(rev[0]["layers_changed_n"], 1)
        self.assertEqual(rev[0]["per_layer"][0]["declared_before"], 100)
        self.assertEqual(led["declared"], 410)                 # 110 + 0(capped) + 300
        baks = [x for x in os.listdir(self.tmp) if ".bak-" in x]
        self.assertEqual(len(baks), 1)                          # 写前备份


if __name__ == "__main__":
    unittest.main()
