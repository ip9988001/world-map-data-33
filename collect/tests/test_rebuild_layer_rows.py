# -*- coding: utf-8 -*-
"""从 Release 单元包反推完成度 —— 测量口径与「证据是否还成立」的指纹复检。

事故：2026-10-30 22:23Z 检查点被 force 重跑覆盖成 0 行，68 个单元包还在。
本文件锁两件事：
  ① 包号连续性检查（缺号要能说出来，不能把 68 当成 69）；
  ② 指纹复检：测量期间若有别的 run 在同 tag 上用同名包 --clobber，
     (size, createdAt) 会变 → 证据失效、必须重测，不许拿旧行数洗账。
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import rebuild_layer_rows as R  # noqa: E402


class UnitGaps(unittest.TestCase):
    def test_no_gap(self):
        pkgs = [{"unit": i} for i in range(3)]
        self.assertEqual(R._unit_gaps(pkgs), [])

    def test_gap_is_reported(self):
        pkgs = [{"unit": 0}, {"unit": 2}, {"unit": 5}]
        self.assertEqual(R._unit_gaps(pkgs), [1, 3, 4])

    def test_ignores_packages_without_unit(self):
        self.assertEqual(R._unit_gaps([{"unit": None}, {"unit": 1}]), [0])


class RecheckAssets(unittest.TestCase):
    def setUp(self):
        self.built = {"packages": [
            {"name": "L-u00000.tar.gz", "asset_size": 100, "asset_created_at": "T1"},
            {"name": "L-u00001.tar.gz", "asset_size": 200, "asset_created_at": "T1"}]}

    def _patch(self, assets):
        R.list_assets = lambda tag, repo: assets

    def test_identical_fingerprint_is_valid(self):
        self._patch([{"name": "L-u00000.tar.gz", "size": 100, "createdAt": "T1"},
                     {"name": "L-u00001.tar.gz", "size": 200, "createdAt": "T1"}])
        out = R.recheck_assets(self.built, "tag", "repo", log=lambda m: None)
        self.assertTrue(out["ok"])
        self.assertEqual((out["changed"], out["missing"]), ([], []))

    def test_overwritten_package_invalidates_evidence(self):
        self._patch([{"name": "L-u00000.tar.gz", "size": 100, "createdAt": "T2"},   # 被重传
                     {"name": "L-u00001.tar.gz", "size": 200, "createdAt": "T1"}])
        out = R.recheck_assets(self.built, "tag", "repo", log=lambda m: None)
        self.assertFalse(out["ok"])
        self.assertEqual(out["changed"][0]["name"], "L-u00000.tar.gz")
        self.assertEqual(out["changed"][0]["now_created_at"], "T2")

    def test_missing_package_invalidates_evidence(self):
        self._patch([{"name": "L-u00001.tar.gz", "size": 200, "createdAt": "T1"}])
        out = R.recheck_assets(self.built, "tag", "repo", log=lambda m: None)
        self.assertFalse(out["ok"])
        self.assertEqual(out["missing"], ["L-u00000.tar.gz"])


if __name__ == "__main__":
    unittest.main()
