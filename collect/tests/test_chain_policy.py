#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接续策略（chain_policy）的护栏单测。

为什么必须有：07b 后面原本自动接 10b（宗地 8,116 层 / 20~85 GB），而且接续那行
硬编码 `-f chain=1`，于是「采完就停」这件事完全不成立。这里把三条约束钉成测试：
  ① 07b 的 next 必须是空
  ② 允许清单只放 05b / 07b（写回 10b 会被拦）
  ③ 子 run 的 chain 一律 0（不级联）
"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chain_policy as cp  # noqa: E402


class StopAt07b(unittest.TestCase):
    def test_07b_has_no_next(self):
        self.assertEqual(cp.NEXT["07b"], "")
        v = cp.decide("07b", "1")
        self.assertEqual(v["decide"], "stop")
        self.assertEqual(v["reason"], "no_next_stage")

    def test_allowlist_excludes_10b(self):
        self.assertNotIn("10b", cp.ALLOWED)
        self.assertEqual(sorted(cp.ALLOWED), ["05b", "07b"])

    def test_writes_back_to_10b_is_blocked(self):
        """即便有人把 07b 的 next 改回 10b，决定仍然是 stop。"""
        old = dict(cp.NEXT)
        try:
            cp.NEXT["07b"] = "10b"
            v = cp.decide("07b", "1")
            self.assertEqual(v["decide"], "stop")
            self.assertEqual(v["reason"], "next_not_in_allowlist")
        finally:
            cp.NEXT.clear()
            cp.NEXT.update(old)

    def test_unknown_stage_stops(self):
        v = cp.decide("08", "1")
        self.assertEqual(v["decide"], "stop")
        self.assertEqual(v["reason"], "unknown_stage")


class SingleHop(unittest.TestCase):
    def test_children_never_cascade(self):
        for s in cp.STAGES:
            self.assertEqual(cp.CHILD_CHAIN[s], "0", "%s 的子 run 不许带 chain=1" % s)

    def test_dispatch_cmd_passes_child_chain(self):
        v = cp.decide("04b", "1")
        self.assertEqual(v["decide"], "dispatch")
        self.assertEqual(v["next"], "05b")
        cmd = cp.dispatch_cmd(v, "o/r")
        self.assertIn("-f chain=0", cmd)
        self.assertNotIn("-f chain=1", cmd)

    def test_chain_off_stops(self):
        v = cp.decide("05b", "0")
        self.assertEqual(v["decide"], "stop")
        self.assertEqual(v["reason"], "chain_off")

    def test_05b_to_07b_still_allowed(self):
        v = cp.decide("05b", "1")
        self.assertEqual(v["decide"], "dispatch")
        self.assertEqual(v["next"], "07b")


class HeavyGate(unittest.TestCase):
    def test_10b_needs_explicit_auth(self):
        self.assertFalse(cp.is_heavy_authorized("10b", "0"))
        self.assertTrue(cp.is_heavy_authorized("10b", "1"))

    def test_normal_stages_not_gated(self):
        for s in ("04b", "05b", "07b"):
            self.assertTrue(cp.is_heavy_authorized(s, "0"))


class CliDryRun(unittest.TestCase):
    def test_all_dry_run_dispatches_only_allowed(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cp.main(["--all", "--dry-run"])
        out = buf.getvalue()
        self.assertIn("stage=07b", out)
        # 全表里只允许出现 05b / 07b 两条 dispatch
        self.assertEqual(out.count("DRY:"), 2)
        self.assertIn("-f stage=05b -f chain=0", out)
        self.assertIn("-f stage=07b -f chain=0", out)
        self.assertNotIn("stage=10b -f chain", out)


if __name__ == "__main__":
    unittest.main()
