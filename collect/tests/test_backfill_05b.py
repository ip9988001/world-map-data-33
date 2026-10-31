# -*- coding: utf-8 -*-
"""05b 补账的边界：只补 checkpoint 可证的层，零行单元不许被误判 failed。

锁两条：
  · 三个单元里 unit 1 计划 0 行 / 实采 0 行 / 无包 → `unit_uploaded=false` 正常，整层 ok；
  · 如果未上传的是**有行**的单元 → 仍判 failed，不许拿「零行」当挡箭牌。
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import backfill_05b_ledger as B  # noqa: E402


def _rel(layer):
    return {"tag": "collect-step05-" + layer,
            "created_at": "2026-10-31T02:46:13Z",
            "assets": [
                {"id": 1, "name": layer + "-checkpoint.json", "size": 600,
                 "created_at": "2026-10-31T02:49:15Z"},
                {"id": 2, "name": layer + "-u00000.tar.gz", "size": 14202688,
                 "created_at": "2026-10-31T02:49:14Z"},
                {"id": 3, "name": layer + "-u00002.tar.gz", "size": 1123,
                 "created_at": "2026-10-31T02:47:09Z"},
            ]}


def _ck(layer, zero_unit=1):
    rows = {"0": 250206, "1": 0, "2": 2}
    if zero_unit is None:                 # 让 unit 1 变成「有行但未上传」
        rows = {"0": 250206, "1": 7, "2": 2}
    return {"ver": 2, "tag": "collect-step05-" + layer,
            "unit_rows": rows, "unit_rows_seen": dict(rows),
            "unit_files": {"0": ["part-u00000-000.ndjson.gz"], "1": [],
                           "2": ["part-u00002-000.ndjson.gz"]},
            "unit_uploaded": {"0": True, "1": False, "2": True},
            "done_units": [0, 1, 2], "unit_errors": {},
            "plan_hash": "db4f308cfa29be24", "url": "https://example/FeatureServer/1"}


class ZeroRowUnit(unittest.TestCase):
    LAYER = "UojyNPhsWOk1W_arcgis_rest_services_Addresses_FeatureServer_1"

    def test_zero_row_unit_not_uploaded_is_ok(self):
        j = B.judge_backfill(self.LAYER, 250208, _rel(self.LAYER), _ck(self.LAYER))
        self.assertEqual(j["status"], "ok")
        self.assertIn("零行单元", j["reason"])
        self.assertTrue(any("零行单元" in w for w in j["warn"]))

    def test_nonzero_unit_not_uploaded_still_failed(self):
        j = B.judge_backfill(self.LAYER, 250208, _rel(self.LAYER),
                             _ck(self.LAYER, zero_unit=None))
        self.assertEqual(j["status"], "failed")
        self.assertIn("未上传", j["reason"])

    def test_record_carries_backfill_provenance(self):
        out = B.build_record(self.LAYER, 250208, "FeatureServer",
                             _rel(self.LAYER), _ck(self.LAYER))
        r = out["record"]
        self.assertEqual(r["backfilled_from"], "release_assets")
        self.assertEqual(r["reason"], "ledger_row_lost_on_cancel")
        self.assertEqual(r["units_done"], 3)
        self.assertEqual(r["packages_n"], 2)          # 零行单元没有包，不硬凑
        self.assertTrue(r["evidence"]["checkpoint_sha256"])


if __name__ == "__main__":
    unittest.main()
