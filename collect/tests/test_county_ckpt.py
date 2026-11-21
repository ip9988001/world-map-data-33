#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单县 checkpoint 回归（W2-018）：单县中断只重跑该县 + 源指纹变化失效全跑。

跑法：python3 -m unittest discover -s collect/tests -q
或：  python3 collect/tests/test_county_ckpt.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "collect"))

import county_ckpt as CK  # noqa: E402


class InterruptedCounty(unittest.TestCase):
    """3 县，第 2 县中断 → 第二次只处理第 2 县（另两县 0 次调用）。"""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="ckpt-test-")
        self.src = os.path.join(self.tmp, "US-NH.json.gz")
        Path(self.src).write_bytes(b"geometry-v1")
        self.fp = CK.source_fingerprint([self.src])
        self.counties = ["33001", "33003", "33005"]
        self.calls: list[str] = []

    def test_interrupt_then_rerun_only_that_county(self) -> None:
        def work(fips: str):
            self.calls.append(fips)
            if fips == "33003":
                raise RuntimeError("模拟中断：进程被杀 / 上游超时")
            return {"rows": 120}

        s1 = CK.run_counties("NH", self.counties, work, ledger_dir=self.tmp, fingerprint=self.fp)
        self.assertEqual(self.calls, self.counties)
        self.assertEqual((s1["done"], s1["failed"]), (2, 1))
        self.assertIn("33003", s1["fail_reasons"])
        self.assertIn("模拟中断", s1["fail_reasons"]["33003"])

        self.calls.clear()
        s2 = CK.run_counties("NH", self.counties, lambda f: self.calls.append(f) or {"rows": 120},
                             ledger_dir=self.tmp, fingerprint=self.fp)
        self.assertEqual(self.calls, ["33003"], "第二次只该跑第 2 县")
        self.assertEqual(s2["done"], 3)
        self.assertEqual(sorted(s2["skipped"]), ["33001", "33005"])

    def test_failed_never_becomes_done_silently(self) -> None:
        CK.run_counties("NH", ["33011"], lambda f: (_ for _ in ()).throw(ValueError("boom")),
                        ledger_dir=self.tmp, fingerprint=self.fp)
        doc = CK.load("NH", self.tmp)
        rec = doc["counties"]["33011"]
        self.assertEqual(rec["status"], "failed")
        self.assertTrue(rec.get("fail_reason"))

    def test_rows_mismatch_is_failed(self) -> None:
        CK.run_counties("NH", ["33013"], lambda f: {"rows": 3, "expect_rows": 10},
                        ledger_dir=self.tmp, fingerprint=self.fp)
        rec = CK.load("NH", self.tmp)["counties"]["33013"]
        self.assertEqual(rec["status"], "failed")
        self.assertIn("rows_mismatch", rec["fail_reason"])

    def test_counties_and_force_flags(self) -> None:
        CK.run_counties("NH", self.counties, lambda f: {"rows": 1},
                        ledger_dir=self.tmp, fingerprint=self.fp)

        self.calls.clear()
        CK.run_counties("NH", self.counties, lambda f: self.calls.append(f) or {"rows": 1},
                        ledger_dir=self.tmp, fingerprint=self.fp, counties_only=["33005"])
        self.assertEqual(self.calls, ["33005"], "--counties 点名即重跑，且只碰点名县")

        self.calls.clear()
        CK.run_counties("NH", self.counties, lambda f: self.calls.append(f) or {"rows": 1},
                        ledger_dir=self.tmp, fingerprint=self.fp, force=["33001"])
        self.assertEqual(self.calls, ["33001"], "--force-counties 忽略 done 重跑")


class FingerprintInvalidation(unittest.TestCase):
    """源指纹变化 → checkpoint 自动失效，整州重跑（不许拿旧 checkpoint 冒充新数据）。"""

    def test_source_change_invalidates_all(self) -> None:
        tmp = tempfile.mkdtemp(prefix="ckpt-fp-")
        src = os.path.join(tmp, "US-NH.json.gz")
        Path(src).write_bytes(b"v1")
        fp1 = CK.source_fingerprint([src])
        counties = ["33001", "33003", "33005"]
        calls: list[str] = []

        CK.run_counties("NH", counties, lambda f: calls.append(f) or {"rows": 50},
                        ledger_dir=tmp, fingerprint=fp1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(CK.load("NH", tmp)["counties"]["33001"]["status"], "done")

        # 上游重发 / 几何缓存重建 → 指纹变
        Path(src).write_bytes(b"v2-republished")
        fp2 = CK.source_fingerprint([src])
        self.assertNotEqual(fp1, fp2)

        calls.clear()
        CK.run_counties("NH", counties, lambda f: calls.append(f) or {"rows": 50},
                        ledger_dir=tmp, fingerprint=fp2)
        self.assertEqual(sorted(calls), sorted(counties), "指纹变化必须整州重跑")

        doc = CK.load("NH", tmp)
        self.assertIn("invalidated", doc)
        self.assertEqual(doc["fingerprint"], fp2)

    def test_missing_source_also_changes_fingerprint(self) -> None:
        tmp = tempfile.mkdtemp(prefix="ckpt-fp2-")
        src = os.path.join(tmp, "gone.json.gz")
        Path(src).write_bytes(b"x")
        fp1 = CK.source_fingerprint([src])
        os.remove(src)
        self.assertNotEqual(fp1, CK.source_fingerprint([src]), "源文件消失也要让旧 checkpoint 失效")


if __name__ == "__main__":
    unittest.main(verbosity=2)
