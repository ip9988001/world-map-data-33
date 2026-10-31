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

    # ---------------------------------------------------------- capped_by_upstream
    def test_capped_moves_declared_out_of_denominator(self):
        """服务级 token 的层：declared 移出分母（declared_unverifiable），rows 照旧计入。

        用户定口径（2026-10-31）：gap 必须两只脚站同一条船 —— 分母拿走它的声明，
        分子也要拿走它的已采行数（rows_verifiable），否则算出负缺口，看着像「超采」。
        """
        tok = os.path.join(self.tmp, "analysis", "token.json")
        json.dump({"schema": "upstream-token-evidence/v1", "stage": "04b",
                   "generated_at": "2026-10-31T00:46:18Z",
                   "layers": [{"layer": "half_layer", "layer_url": "https://x/half_layer",
                               "verdict": "service_level_token", "all_rounds_token": True,
                               "rounds_n": 2,
                               "rounds": [{"round": 1, "at": "2026-10-31T00:45:17Z",
                                           "probes": {}},
                                          {"round": 2, "at": "2026-10-31T00:46:18Z",
                                           "probes": {}}]}]},
                  open(tok, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--capped-evidence", tok)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        capped = by["half_layer"]
        self.assertEqual(capped["status"], "capped_by_upstream")
        self.assertIsNone(capped["declared"])
        self.assertEqual(capped["declared_unverifiable"], 100)
        self.assertEqual(capped["rows"], 40)                 # 已采行数不吃掉
        self.assertIsNone(capped["gap"])
        self.assertEqual(capped["evidence"]["token_error_code"], 499)
        self.assertEqual(capped["evidence"]["rounds_n"], 2)
        # 聚合：分母不含 capped，分子也扣除它的行数
        self.assertEqual(d["capped_by_upstream"], 1)
        self.assertEqual(d["declared_unverifiable"], 100)
        self.assertEqual(d["rows_capped"], 40)
        self.assertEqual(d["rows_verifiable"], d["rows"] - 40)
        self.assertEqual(d["gap"], d["declared"] - d["rows_verifiable"])
        self.assertEqual(d["declared_kept_in_denominator"], d["declared"] + 100)
        self.assertEqual(len(d["capped_layers"]), 1)

    def test_capped_requires_evidence_two_rounds(self):
        """只有一轮、或 all_rounds_token≠true 的证据不得改判（宁可不动账）。"""
        tok = os.path.join(self.tmp, "analysis", "token_bad.json")
        json.dump({"schema": "upstream-token-evidence/v1", "stage": "04b",
                   "generated_at": "2026-10-31T00:00:00Z",
                   "layers": [{"layer": "half_layer", "verdict": "service_level_token",
                               "all_rounds_token": False, "rounds_n": 1, "rounds": []},
                              {"layer": "unreach", "verdict": "inconclusive",
                               "all_rounds_token": False, "rounds_n": 2, "rounds": []}]},
                  open(tok, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--capped-evidence", tok)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        self.assertEqual(d["capped_by_upstream"], 0)
        self.assertEqual(d["declared_unverifiable"], 0)
        self.assertFalse(d["capped_layers"])

    def test_capped_is_idempotent(self):
        tok = os.path.join(self.tmp, "analysis", "token.json")
        json.dump({"schema": "upstream-token-evidence/v1", "stage": "04b",
                   "generated_at": "2026-10-31T00:46:18Z",
                   "layers": [{"layer": "half_layer", "verdict": "service_level_token",
                               "all_rounds_token": True, "rounds_n": 2, "rounds": []}]},
                  open(tok, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        doc = os.path.join(self.tmp, "docs", "d.md")
        args = ("--out", out, "--doc", doc, "--capped-evidence", tok)
        self.assertEqual(self._run(*args).returncode, 0)
        r = self._run(*args, "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        md = open(doc, encoding="utf-8").read()
        self.assertIn("capped_by_upstream", md)
        self.assertIn("declared_unverifiable", md)


if __name__ == "__main__":
    unittest.main()
