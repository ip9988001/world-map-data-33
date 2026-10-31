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
        # 重试上限判据在 collect/attempt_log.py（同目录模块）：单文件分发会 import 失败、
        # 整条 upstream_unstable 判据静默失效 —— 测试里必须一并带上，才能真跑到那条分支。
        shutil.copy(os.path.join(ROOT, "collect", "attempt_log.py"),
                    os.path.join(self.tmp, "collect", "attempt_log.py"))
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


    # ---------------------------------------------------------- 分区重复声明
    def _dup_fixture(self):
        """`P@X-1`（0 行）+ `P@X-2`（100 行）各写全量 declared 100 → 重复计数。"""
        json.dump({"schema": "rebuilt/v1", "layers_n": 2, "records": [
            rec("P@X-1", "failed", 100, 0),
            rec("P@X-2", "failed", 100, 100),
        ]}, open(self.rebuilt, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"schema": "04b-upstream-evidence/v1", "generated_at": "2026-10-31T02:00:00Z",
                   "layers": [ev("P@X-1", "upstream_alive", 100),
                              ev("P@X-2", "upstream_alive", 100)]},
                  open(self.evidence, "w", encoding="utf-8"), ensure_ascii=False)
        spec = os.path.join(self.tmp, "analysis", "04b-duplicate-partitions-2026-10-31.json")
        json.dump({"schema": "04b-duplicate-partitions/v1", "stage": "04b",
                   "groups": [{"base_layer": "P", "partitions": ["P@X-1", "P@X-2"],
                               "upstream_return_count": 100, "sum_declared": 200,
                               "ratio": 2.0, "duplicate_layers": ["P@X-1"],
                               "duplicate_sampled": ["P@X-1"],
                               "survivor": "P@X-2", "survivor_rows": 100,
                               "decided_status": "partial",
                               "evidence": {"upstream_probe": "analysis/ev.json"}}]},
                  open(spec, "w", encoding="utf-8"), ensure_ascii=False)
        return spec

    def test_duplicate_partition_moves_declared_out_but_keeps_number(self):
        self._dup_fixture()
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        doc = os.path.join(self.tmp, "docs", "d.md")
        r = self._run("--out", out, "--doc", doc)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        dup = by["P@X-1"]
        self.assertEqual(dup["status"], "partial")          # 不是 missing：数据在 survivor 里
        self.assertIsNone(dup["declared"])                   # 移出分母
        self.assertEqual(dup["declared_duplicate_partition"]["declared_before"], 100)   # 数字不丢
        self.assertEqual(dup["declared_duplicate_partition"]["sum_declared"], 200)
        self.assertEqual(dup["declared_duplicate_partition"]["duplicate_of"], "P@X-2")
        self.assertIsNone(dup["gap"])
        # 聚合：declared 只剩 survivor 的 100；重复声明的 100 单列，不进分母
        self.assertEqual(d["declared"], 100)
        self.assertEqual(d["declared_duplicate_partition"], 100)
        self.assertEqual(d["missing"], 0)
        self.assertEqual(d["partial"], 1)
        self.assertEqual(d["rows_with_partition_dup"], 0)    # 这层 0 行
        self.assertEqual(d["rows_verifiable"], d["rows"] - d["rows_capped"] - d["rows_with_partition_dup"])
        md = open(doc, encoding="utf-8").read()
        self.assertIn("分区重复声明", md)
        self.assertIn("08", md)                              # 去重口径写在文档里

    def test_duplicate_partition_sampling_is_counted_separately(self):
        """分区层若真采到行：进 rows_with_partition_dup，不进 rows_verifiable（防覆盖率虚高）。"""
        self._dup_fixture()
        json.dump({"schema": "rebuilt/v1", "layers_n": 2, "records": [
            rec("P@X-1", "failed", 100, 100),     # 重复采样 100 行
            rec("P@X-2", "failed", 100, 100),
        ]}, open(self.rebuilt, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        self.assertTrue(by["P@X-1"]["partition_duplicate_sampled"])
        self.assertEqual(by["P@X-1"]["rows_including_duplicate"], 100)
        self.assertEqual(d["rows"], 200)
        self.assertEqual(d["rows_with_partition_dup"], 100)
        self.assertEqual(d["rows_verifiable"], 100)
    # ---------------------------------------------------------- upstream_unstable / 重试上限
    def _attempt_fixture(self, layer, n=3, kind="non_json", elapsed_s=33.4):
        """给某层写 n 次失败尝试（无进展）—— 与 collect/attempt_log.py 的产物同结构。"""
        atts = []
        for i in range(n):
            atts.append({"layer": layer, "at": "2026-10-31T0%d:10:00Z" % (i + 1),
                         "at_src": "record", "kind": kind, "rc": 1, "elapsed_s": elapsed_s,
                         "rows": 0, "prior_units": 0, "run": "41155023558", "shard": 3,
                         "source": "04b_shard03.json", "err": "Expecting value: line 1 column 1"})
        p = os.path.join(self.tmp, "analysis", "04b-attempt-log.json")
        json.dump({"schema": "collect-attempt-log/v1", "stage": "04b", "cap": 3,
                   "at": atts[-1]["at"], "sources": [], "attempts_n": len(atts),
                   "layers_n": 1, "unstable_n": 1, "unstable": [],
                   "attempts": atts, "layers": {}}, open(p, "w", encoding="utf-8"),
                  ensure_ascii=False)
        return p

    def test_three_failures_flip_to_upstream_unstable(self):
        """连续 3 次超时/503/非 JSON 且无进展 → upstream_unstable；**declared 不许动**。"""
        self._attempt_fixture("zero_but_alive", n=3)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        doc = os.path.join(self.tmp, "docs", "d.md")
        r = self._run("--out", out, "--doc", doc, "--max-attempts", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        lay = by["zero_but_alive"]
        self.assertEqual(lay["status"], "upstream_unstable")
        self.assertEqual(lay["declared"], 777)              # 分母不动：行确实没采到
        self.assertEqual(lay["attempts_n"], 3)
        self.assertEqual(lay["failure_kinds"], ["non_json"] * 3)
        self.assertEqual(len(lay["attempt_log"]), 3)        # 逐次留痕
        self.assertEqual(d["upstream_unstable"], 1)
        self.assertEqual(d["retry_cap"]["applied_n"], 1)
        self.assertEqual(d["gap_by_class"]["upstream_unstable"]["layers_n"], 1)
        self.assertEqual(d["gap_by_class"]["upstream_unstable"]["gap_rows"], 777)
        md = open(doc, encoding="utf-8").read()
        self.assertIn("upstream_unstable", md)
        self.assertIn("累计耗时", md)                        # 收口表：层/声明/次数/类型/耗时
        self.assertIn("四类缺口", md)

    def test_below_cap_keeps_missing(self):
        self._attempt_fixture("zero_but_alive", n=2)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--max-attempts", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        self.assertEqual(by["zero_but_alive"]["status"], "missing")   # 还有重试价值
        self.assertEqual(by["zero_but_alive"]["attempts_n"], 2)       # 但尝试事实照记
        self.assertEqual(d["upstream_unstable"], 0)

    def test_force_unstable_layer_keeps_it_retryable(self):
        """「仍要试」必须显式点名：点名后不改判，但落进 retry_cap.forced_back。"""
        self._attempt_fixture("zero_but_alive", n=3)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--max-attempts", "3",
                      "--force-unstable-layer", "zero_but_alive")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        self.assertEqual(by["zero_but_alive"]["status"], "missing")
        self.assertEqual(d["retry_cap"]["forced_back"], ["zero_but_alive"])

    def test_max_attempts_zero_disables_the_rule(self):
        self._attempt_fixture("zero_but_alive", n=3)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--max-attempts", "0")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        self.assertEqual(by["zero_but_alive"]["status"], "missing")
        self.assertEqual(d["upstream_unstable"], 0)

    def test_missing_attempt_log_does_not_break_the_ledger(self):
        """尝试账本不存在 → 整条判据失效，但账本照常产出（不许因此少一层）。"""
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        r = self._run("--out", out, "--attempt-log", os.path.join(self.tmp, "nope.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        self.assertEqual(d["layers_n"], 5)
        self.assertIn("disabled", json.dumps(d["retry_cap"], ensure_ascii=False))

    # ---------------------------------------------------------- 行侧同源重复（不改 declared）
    def test_rows_duplicate_est_keeps_declared_and_counts_separately(self):
        """Maricopa/Hennepin 口径：declared 全部保留，只把行侧重复估算单列。"""
        # 两个分区**都已实采**（各 100 行）、都写全量 declared（不是重复声明）→ 不进 groups[]，
        # 只进 rows_duplicate[]。这正是 Maricopa/Hennepin 的形态。
        json.dump({"schema": "rebuilt/v1", "layers_n": 2, "records": [
            rec("P@X-1", "failed", 100, 100),
            rec("P@X-2", "failed", 100, 100),
        ]}, open(self.rebuilt, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"schema": "04b-upstream-evidence/v1", "generated_at": "2026-10-31T02:00:00Z",
                   "layers": [ev("P@X-1", "upstream_alive", 100),
                              ev("P@X-2", "upstream_alive", 100)]},
                  open(self.evidence, "w", encoding="utf-8"), ensure_ascii=False)
        spec = os.path.join(self.tmp, "analysis", "04b-duplicate-partitions-2026-10-31.json")
        json.dump({"schema": "04b-duplicate-partitions/v1", "stage": "04b",
                   "groups": [], "reviewed": [],
                   "rows_duplicate": [{"layer": "P@X-2", "source_layer": "P@X-1",
                                       "rows_partition_duplicate_est": 100,
                                       "basis": "镜像 host 同一份数据",
                                       "note": "declared 不动"}]},
                  open(spec, "w", encoding="utf-8"), ensure_ascii=False)
        out = os.path.join(self.tmp, "collect", "04b_ledger.json")
        doc = os.path.join(self.tmp, "docs", "d.md")
        r = self._run("--out", out, "--doc", doc)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.load(open(out, encoding="utf-8"))
        by = {x["layer"]: x for x in d["records"]}
        surv = by["P@X-2"]
        self.assertEqual(surv["declared"], 100)                    # 分母不动
        self.assertEqual(surv["status"], "ok")
        self.assertEqual(surv["rows_partition_duplicate_est"], 100)
        self.assertEqual(surv["duplicate_source_layer"], "P@X-1")
        self.assertEqual(d["declared"], 200)
        self.assertEqual(d["rows"], 200)                            # rows 不改
        self.assertEqual(d["rows_with_partition_dup"], 100)         # 单列
        self.assertEqual(d["rows_verifiable"], 100)                 # 不算进可核实分子
        md = open(doc, encoding="utf-8").read()
        self.assertIn("rows_partition_duplicate_est", md)
        self.assertIn("08", md)


if __name__ == "__main__":
    unittest.main()
