#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归：04b 判定修正的桶必须自洽 —— 五类相加 == 层数，且成品账里不许再有 failed。

事故背景（2026-10-30）：`step04b_rebuilt.json` 里 18 层 failed 混了三种完全不同的情况
（上游有数据但 0 行 / 跑到一半 / 上游连不上），"failed=18" 既不能指导重采，
也让闸门无法判断能否接续。改判后必须满足：
  ok + partial + missing + unverified + empty + skipped_done == layers_n
  且 failed == 0（每一层都要有归因，不许留黑洞）
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "collect", "adjudicate_04b.py")


def rec(layer, status, declared, rows, reason=""):
    return {"layer": layer, "tag": "collect-step04-" + layer, "declared": declared,
            "rows": rows, "status": status, "reason": reason, "gap": None, "gap_pct": None,
            "units_done": 1, "parts_ckpt": 1, "bytes": 1, "problems": [], "warn": []}


def ev(layer, verdict, count, http=200, raw="", status="failed"):
    return {"layer": layer, "ledger_status": status, "verdict": verdict,
            "layer_url": "https://x/%s" % layer,
            "probe": {"url": "https://x/%s/query" % layer, "http": http, "count": count,
                      "raw": raw, "err": "" if count is not None else "URLError: timed out"}}


class TestAdjudicate04b(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for d in ("collect/ledger", "docs", "analysis"):
            os.makedirs(os.path.join(self.tmp, d), exist_ok=True)
        shutil.copy(SCRIPT, os.path.join(self.tmp, "collect", "adjudicate_04b.py"))
        self.rebuilt = os.path.join(self.tmp, "collect", "ledger", "rebuilt.json")
        json.dump({"schema": "rebuilt/v1", "layers_n": 5, "records": [
            rec("ok_layer", "ok", 100, 100),
            rec("half_layer", "failed", 100, 40),
            rec("zero_but_alive", "failed", 100, 0),
            rec("gone", "failed", 100, 0),
            rec("unreach", "failed", 100, 0),
        ]}, open(self.rebuilt, "w", encoding="utf-8"), ensure_ascii=False)
        self.evidence = os.path.join(self.tmp, "analysis", "ev.json")
        json.dump({"schema": "04b-upstream-evidence/v1", "generated_at": "2026-10-30T20:00:00Z",
                   "layers": [
                       ev("half_layer", "upstream_alive", 100),
                       ev("zero_but_alive", "upstream_alive", 777),
                       ev("gone", "upstream_gone_404", None, http=200,
                          raw='{"error":{"code":404,"message":"Service not found"}}'),
                       ev("unreach", "upstream_unreachable", None, http=None),
                   ]}, open(self.evidence, "w", encoding="utf-8"), ensure_ascii=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *extra):
        return subprocess.run([sys.executable, os.path.join(self.tmp, "collect", "adjudicate_04b.py"),
                               "--rebuilt", self.rebuilt, "--evidence", self.evidence,
                               "--plan", "/nonexistent", *extra],
                              capture_output=True, text=True, cwd=self.tmp)

    def test_buckets_self_consistent_and_no_failed(self):
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--doc", os.path.join(self.tmp, "docs", "d.md"))
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        self.assertEqual(d["failed"], 0)
        self.assertEqual(d["layers_n"], 5)
        tot = sum(d["buckets"].get(k, 0) for k in
                  ("ok", "partial", "missing", "unverified", "empty", "skipped_done"))
        self.assertEqual(tot, d["layers_n"])
        # 上游活着且 0 行 → missing（真缺口），不许标 empty
        self.assertEqual(d["buckets"].get("missing"), 1)
        self.assertEqual(d["buckets"].get("unverified"), 1)
        self.assertEqual(d["buckets"].get("empty"), 1)      # 只有 esri 404 才算空
        self.assertFalse(d["complete"])

    def test_declared_uses_upstream_count(self):
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        self._run("--out", out)
        d = json.load(open(out, encoding="utf-8"))
        by = {r["layer"]: r for r in d["records"]}
        self.assertEqual(by["zero_but_alive"]["declared"], 777)     # 声明改用上游当前值
        self.assertEqual(by["zero_but_alive"]["status"], "missing")
        self.assertTrue(any(x["layer"] == "zero_but_alive" for x in d["revisions"]))

    def test_check_is_idempotent(self):
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        doc = os.path.join(self.tmp, "docs", "d.md")
        aud = os.path.join(self.tmp, "analysis", "a.json")
        args = ("--out", out, "--doc", doc, "--audit", aud)
        self.assertEqual(self._run(*args).returncode, 0)
        r = self._run(*args, "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("IDENTICAL", r.stdout)


if __name__ == "__main__":
    unittest.main()
