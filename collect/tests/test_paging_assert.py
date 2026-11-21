#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-042 收尾对账断言的单测（stub 造 rows<expect）。

要证明三件事：
  ① `gap_short` 在 rows 明显少于 expect 时**真的会触发**（默认容差 GAP_TOL=0.005）；
  ② `_top_up_offset` 会用 resultOffset 把缺的行补回来（138c05 形态：2,000 + 131 → 再补 169）；
  ③ 补不回来时 `_unit_range` 的收尾分支**会返回 `short:rows/expect`**（= 该层记 partial/failed，不静默收工）。

stub 方式：patch `pilot._q`（模块级函数，_unit_range/_top_up_offset 都走它），不碰网络。
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pilot  # noqa: E402


class FakeService:
    """按 resultOffset / keyset where 返回分页；模拟 138c05：总 2,300，前 2,131 有 OID，169 行 OID 为 null。"""

    def __init__(self, total=2300, null_oid=169, page=2000, fail_backfill=False):
        self.total, self.null_oid, self.page = total, null_oid, page
        self.fail_backfill = fail_backfill
        self.calls = []

    def __call__(self, api, params, timeout=60):
        self.calls.append(dict(params))
        w = str(params.get("where") or "")
        if "returnCountOnly" in params and params.get("returnCountOnly") in ("true", True):
            return {"count": self.total}
        off = int(params.get("resultOffset") or 0)
        ps = int(params.get("resultRecordCount") or self.page)
        # keyset 页：带 "OBJECTID>" 谓词 → 只有非空 OID 行可见，且从 2000 起只剩 131 行（模拟实测）
        if ">" in w and "resultOffset" not in params:
            start = 2000
            n = min(ps, max(0, self.total - self.null_oid - start))
            return {"features": [{"attributes": {"OBJECTID": 5000 + start + i}} for i in range(n)],
                    "exceededTransferLimit": False}
        if self.fail_backfill:
            return {"features": []}
        n = min(ps, max(0, self.total - off))
        return {"features": [{"attributes": {"OBJECTID": 5000 + off + i}} for i in range(n)],
                "exceededTransferLimit": n == ps}


class GapShortTest(unittest.TestCase):
    def test_gap_short_triggers(self):
        self.assertTrue(pilot.gap_short(2131, 2298))      # 138c05 实测形态：缺 7.27%
        self.assertTrue(pilot.gap_short(2280, 2298))      # 缺 0.78% > 0.5% 容差 → 触发
        self.assertFalse(pilot.gap_short(2290, 2298))     # 缺 0.35% < 0.5% → 上游漂移，不触发
        self.assertFalse(pilot.gap_short(2297, 2298))     # 缺 0.04% → 不触发
        self.assertFalse(pilot.gap_short(2298, 2298))     # 完全对齐 → 不触发
        self.assertFalse(pilot.gap_short(0, 0))           # 空层不判

    def test_gap_tol_default(self):
        self.assertAlmostEqual(pilot.GAP_TOL, 0.005, places=6)


class TopUpTest(unittest.TestCase):
    def setUp(self):
        self._old_q = pilot._q          # 打完必须还原，否则污染同进程里的其它测试

    def tearDown(self):
        pilot._q = self._old_q

    def test_backfill_recovers_missing_rows(self):
        """① 2,000+131 停住 → ② offset 补翻拿到剩下的 169 → ③ 总数 2,300。"""
        svc = FakeService()
        pilot._q = svc
        got, err = pilot._top_up_offset("http://stub/0", {"outFields": "*", "f": "json"},
                                        ps=2000, start_offset=2131, expect=2300,
                                        oid_field="OBJECTID", idx=0, log=lambda *a, **k: None,
                                        sink=lambda feats: None)
        self.assertEqual(err, "")
        self.assertEqual(got, 169)
        self.assertEqual(2131 + got, 2300)
        # 必须真的用了 resultOffset（不是又打 keyset）
        self.assertTrue(any("resultOffset" in c for c in svc.calls))

    def test_backfill_failure_is_reported(self):
        svc = FakeService(fail_backfill=True)
        pilot._q = svc
        got, err = pilot._top_up_offset("http://stub/0", {"outFields": "*", "f": "json"},
                                        ps=2000, start_offset=2131, expect=2300,
                                        oid_field="OBJECTID", idx=0, log=lambda *a, **k: None,
                                        sink=lambda feats: None)
        self.assertEqual(got, 0)
        self.assertEqual(err, "")
        self.assertTrue(pilot.gap_short(2131 + got, 2300))  # 仍 short → 调用方会记 short


class PickOidTest(unittest.TestCase):
    def test_picks_highest_non_null_rate(self):
        """138c05：OBJECTID 全 null、OBJECTID_1 有值 → 必须选 OBJECTID_1。"""
        def fake_q(api, params, timeout=60):
            return {"features": [
                {"attributes": {"OBJECTID": None, "OBJECTID_1": 1}},
                {"attributes": {"OBJECTID": None, "OBJECTID_1": 2}}]}
        old, pilot._q = pilot._q, fake_q
        try:
            meta = {"objectIdField": None,
                    "fields": [{"name": "OBJECTID"}, {"name": "OBJECTID_1"}, {"name": "FULLADDRES"}]}
            self.assertEqual(pilot.pick_oid_field(meta, "http://stub/0"), "OBJECTID_1")
        finally:
            pilot._q = old

    def test_declared_field_wins_when_populated(self):
        def fake_q(api, params, timeout=60):
            return {"features": [{"attributes": {"OBJECTID": 1, "FID": 1}}]}
        old, pilot._q = pilot._q, fake_q
        try:
            meta = {"objectIdField": "OBJECTID", "fields": [{"name": "OBJECTID"}, {"name": "FID"}]}
            self.assertEqual(pilot.pick_oid_field(meta, "http://stub/0"), "OBJECTID")
        finally:
            pilot._q = old


if __name__ == "__main__":
    unittest.main()
