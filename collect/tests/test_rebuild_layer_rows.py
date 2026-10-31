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


class RestoreGate(unittest.TestCase):
    """写回 Release 前的硬门禁（2026-10-31 用户要求）：只报警、不写回。"""

    def _built(self, **kw):
        d = {"summary": {"rows": 39875268, "packages": 68, "packages_ok": 68, "packages_bad": []},
             "recheck": {"ok": True, "changed": [], "missing": [], "packages_checked": 68}}
        d.update(kw)
        return d

    def test_gate_passes_on_clean_evidence(self):
        ok, why = R.restore_gate(self._built(expect_rows=39875268, expect_delta=0))
        self.assertTrue(ok, why)

    def test_gate_refuses_without_recheck(self):
        b = self._built()
        b.pop("recheck")
        ok, why = R.restore_gate(b)
        self.assertFalse(ok)
        self.assertIn("--recheck", why)

    def test_gate_refuses_when_fingerprint_not_ok(self):
        b = self._built(recheck={"ok": False, "changed": [{"name": "L-u00000.tar.gz"}],
                                "missing": []})
        ok, why = R.restore_gate(b)
        self.assertFalse(ok)
        self.assertIn("ok=false", why)
        self.assertIn("L-u00000.tar.gz", why)

    def test_gate_refuses_when_expect_delta_nonzero(self):
        b = self._built(expect_rows=39875268, expect_delta=-100)
        ok, why = R.restore_gate(b)
        self.assertFalse(ok)
        self.assertIn("-100", why)

    def test_gate_ignores_expect_when_not_given(self):
        """没给 --expect-rows 就没有「与历史对账」这一步，不能凭空造一个 delta。"""
        ok, _ = R.restore_gate(self._built())
        self.assertTrue(ok)


    def test_main_refuses_and_does_not_call_restore(self):
        """端到端：门禁不过时 main() 必须返回 3 且**不调用** restore_checkpoint。"""
        import json as _json
        import sys as _sys
        import tempfile
        called = []
        old_restore, old_recheck, old_argv = R.restore_checkpoint, R.recheck_assets, _sys.argv
        built = {"summary": {"rows": 1, "packages": 1, "packages_ok": 1, "packages_bad": [],
                             "parts": 1},
                 "recheck": {"ok": False, "changed": [{"name": "x"}], "missing": [],
                            "packages_checked": 1}}
        ev = tempfile.mktemp(suffix=".json")
        _json.dump(built, open(ev, "w"))
        R.restore_checkpoint = lambda *a, **k: called.append(a) or {}
        R.recheck_assets = lambda *a, **k: built["recheck"]
        try:
            _sys.argv = ["x", "--layer", "L", "--tag", "t", "--out", ev, "--from-json", ev,
                         "--restore-checkpoint", "--layer-url", "u", "--run-id", "41126178216"]
            rc = R.main()
        finally:
            R.restore_checkpoint, R.recheck_assets, _sys.argv = old_restore, old_recheck, old_argv
        self.assertEqual(rc, 3)
        self.assertFalse(called, called)
        out = _json.load(open(ev))
        self.assertTrue(out["checkpoint_restore"]["refused"], out["checkpoint_restore"])


if __name__ == "__main__":
    unittest.main()