#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定向区间补采（--oid-range）的三条硬约束单测。

为什么要有它：区间补采是「只加一个参数」的改动，但踩错就会伤到历史资产：
  ① 产物必须落 `<原tag>-r2`，不许和旧单元抢同一个 Release（抢了就 --clobber 覆盖，
     覆盖了就没有比对基准，「不一致就回滚」变成空话）；
  ② 后缀必须幂等（重复跑不会变成 -r2-r2）；
  ③ `plan_units` 的切分逻辑不许因为多了区间参数而变 —— 区间拼接必须覆盖 [lo,hi] 全域、
     无缝无洞，否则「覆盖可证」就是嘴上说说。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pilot  # noqa: E402


class TagR2(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        pilot.CUR.clear()
        pilot.CUR.update({"id": "nd_layer", "title": "t", "url": "https://x/0"})
        pilot.OID_RANGE = None
        os.environ.pop("PILOT_RELEASE_TAG", None)

    def tearDown(self):
        pilot.OID_RANGE = None
        os.environ.clear()
        os.environ.update(self._env)

    def test_plain_tag_without_range(self):
        os.environ["PILOT_RELEASE_TAG"] = "collect-step04-nd_layer"
        self.assertEqual(pilot._tag(), "collect-step04-nd_layer")

    def test_range_appends_r2(self):
        os.environ["PILOT_RELEASE_TAG"] = "collect-step04-nd_layer"
        pilot.OID_RANGE = (1, 100)
        self.assertEqual(pilot._tag(), "collect-step04-nd_layer-r2")

    def test_suffix_is_idempotent(self):
        os.environ["PILOT_RELEASE_TAG"] = "collect-step04-nd_layer-r2"
        pilot.OID_RANGE = (1, 100)
        self.assertEqual(pilot._tag(), "collect-step04-nd_layer-r2")


class RangeCovers(unittest.TestCase):
    """区间切片可证：拼接 = [lo,hi] 全域，无缝、无洞、不多切。"""

    def _check(self, count, lo, hi, unit_rows):
        units, cap = pilot.plan_units(count, lo, hi, unit_rows=unit_rows, kind="range")
        self.assertEqual(units[0][0], lo)
        self.assertEqual(units[-1][1], hi)
        for a, b in zip(units, units[1:]):
            self.assertEqual(a[1] + 1, b[0], "区间之间出现洞：%s → %s" % (a[1], b[0]))
        self.assertEqual(sum(b - a + 1 for a, b in units), hi - lo + 1)
        self.assertEqual(cap, unit_rows)
        return units

    def test_single_interval_is_one_unit(self):
        units = self._check(1_000_000, 1, 1_000_000, 1_000_000)
        self.assertEqual(len(units), 1)

    def test_splits_without_gaps(self):
        units = self._check(2_500_000, 500, 2_500_499, 1_000_000)
        self.assertEqual(len(units), 3)

    def test_tiny_range(self):
        units = self._check(3, 7, 9, 1_000_000)
        self.assertEqual(units, [(7, 9)])


class VerdictUsesRangeCount(unittest.TestCase):
    """区间补采的分母是「区间内行数」：不许拿去和全层行数比（否则 1M 行永远判 short）。"""

    def test_range_short_not_triggered(self):
        code, short = pilot.verdict(1_000_000, 1_000_000, "")
        self.assertEqual((code, short), (0, ""))

    def test_range_short_triggered(self):
        code, _short = pilot.verdict(900_000, 1_000_000, "")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
