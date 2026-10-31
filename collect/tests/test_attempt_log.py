#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重试上限的契约（2026-10-31 用户立规）。

锁六条行为（全部离线，不联网、不读真账本）：

  1. 失败类型四分类顺序：`token(499)` → `503` → `非 JSON` → `超时`。
     503 的正文里写着 `Wait timeout for the request exceeded`（含 timeout 字样），
     所以 503 必须排在超时之前 —— 否则「上游 503」会被记成「我们超时」，归因就错了。
  2. 同一层连续 3 次失败且**无进展** → `unstable=True`；只要有一次多采到行/多推一个单元包
     （有进展），就**不算** unstable：重试还有收益，不许一刀切停掉。
  3. `partition_queue` 默认剔除 unstable 层；只有显式 `--force-unstable-layer` 能放回去。
  4. 追加模式：片账本被新 run 覆盖后，旧的失败尝试**不许消失**（否则连续次数永远涨不到 3）。
  5. 幂等：同一输入跑两遍字节一致（`--check` 才有意义）。
  6. 「上游 503 但已采到行」不会被误判成无进展 —— 进展指纹取 (rows, prior_units)。
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import attempt_log as A  # noqa: E402


def rec(layer, status="failed", err="", reason="", rc=1, elapsed_s=10, rows=None,
        prior_units=None, at="2026-10-31T01:00:00Z"):
    r = {"layer": layer, "status": status, "err": err, "reason": reason, "rc": rc,
         "elapsed_s": elapsed_s}
    if at:
        r["at"] = at
    if rows is not None:
        r["rows"] = rows
    if prior_units is not None:
        r["prior_units"] = prior_units
    return r


def ledger(path, records, stage="step04b", at="2026-10-31T01:30:00Z", shard=3, run_id=""):
    d = {"schema": "shard", "stage": stage, "at": at, "shard": shard, "records": records}
    if run_id:
        d["run_id"] = run_id
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    return path


class Classify(unittest.TestCase):
    def test_503_wins_over_timeout_word(self):
        # 上游 503 的正文自带 "Wait timeout for the request exceeded"
        k = A.classify_failure('query_fail:svcerr:{"code": 503, "message": "Error handling '
                               'service request :Wait timeout for the request exceeded.", "details": []}')
        self.assertEqual(k, "http_503")

    def test_job_level_timeout(self):
        self.assertEqual(A.classify_failure("", "job 内单层超时 55 分钟（--layer-timeout）", rc=-1,
                                            elapsed_s=3300.1), "timeout")

    def test_non_json(self):
        self.assertEqual(A.classify_failure("query_fail:Expecting value: line 1 column 1 (char 0)"),
                         "non_json")

    def test_token_499(self):
        self.assertEqual(A.classify_failure('query_fail:svcerr:{"code": 499, "message": "Token Required"}'),
                         "token")

    def test_404_and_dns(self):
        self.assertEqual(A.classify_failure("batch0:http404:<!DOCTYPE html"), "http_4xx")
        self.assertEqual(A.classify_failure("URLError: <urlopen error [Errno -3] Temporary failure "
                                            "in name resolution>"), "dns")

    def test_unknown_is_other_not_guessed(self):
        self.assertEqual(A.classify_failure("rc=1 err=?"), "other")


class Summary(unittest.TestCase):
    def test_three_failures_no_progress_is_unstable(self):
        atts = [A.attempt_of(rec("L", err="Expecting value: line 1 column 1", rc=1,
                                 elapsed_s=33, at="2026-10-31T0%d:00:00Z" % i), run="r1")
                for i in (1, 2, 3)]
        s = A.summarize(atts, 3)["L"]
        self.assertEqual(s["attempts_n"], 3)
        self.assertEqual(s["kinds"], ["non_json"] * 3)
        self.assertTrue(s["no_progress"])
        self.assertTrue(s["unstable"])
        self.assertAlmostEqual(s["elapsed_min"], 1.6, places=1)

    def test_two_failures_is_below_cap(self):
        atts = [A.attempt_of(rec("L", reason="job 内单层超时 55 分钟", rc=-1, elapsed_s=3300,
                                 at="2026-10-31T0%d:00:00Z" % i)) for i in (1, 2)]
        self.assertFalse(A.summarize(atts, 3)["L"]["unstable"])

    def test_progress_resets_the_judgement(self):
        """半截层还在推进（rows / prior_units 涨过）→ 不算无进展，重试有收益。"""
        atts = [A.attempt_of(rec("L", err="Expecting value: line 1 column 1", rows=0,
                                 prior_units=0, at="2026-10-31T01:00:00Z")),
                A.attempt_of(rec("L", err="Expecting value: line 1 column 1", rows=0,
                                 prior_units=1, at="2026-10-31T02:00:00Z")),
                A.attempt_of(rec("L", err="Expecting value: line 1 column 1", rows=0,
                                 prior_units=2, at="2026-10-31T03:00:00Z"))]
        s = A.summarize(atts, 3)["L"]
        self.assertEqual(s["attempts_n"], 3)
        self.assertFalse(s["no_progress"])
        self.assertFalse(s["unstable"])

    def test_rows_growth_counts_as_progress(self):
        atts = [A.attempt_of(rec("L", err="Expecting value", rows=r, at="2026-10-31T0%d:00:00Z" % i))
                for i, r in ((1, 0), (2, 100), (3, 200))]
        self.assertFalse(A.summarize(atts, 3)["L"]["unstable"])


class Queue(unittest.TestCase):
    def test_unstable_is_excluded_by_default(self):
        s = {"a": {"layer": "a", "attempts_n": 3, "unstable": True, "kinds": ["timeout"],
                   "elapsed_min": 165.0},
             "b": {"layer": "b", "attempts_n": 1, "unstable": False, "kinds": ["http_503"],
                   "elapsed_min": 1.0}}
        keep, excluded, back = A.partition_queue(["a", "b", "c"], s)
        self.assertEqual(keep, ["b", "c"])
        self.assertEqual([x["layer"] for x in excluded], ["a"])
        self.assertEqual(excluded[0]["attempts_n"], 3)
        self.assertEqual(back, [])

    def test_force_puts_it_back(self):
        s = {"a": {"layer": "a", "attempts_n": 3, "unstable": True, "kinds": ["timeout"],
                   "elapsed_min": 165.0}}
        keep, excluded, back = A.partition_queue(["a"], s, force=("a",))
        self.assertEqual(keep, ["a"])
        self.assertEqual(excluded, [])
        self.assertEqual(back, ["a"])

    def test_zero_cap_disables_nothing_here_but_empty_summary_is_safe(self):
        self.assertEqual(A.partition_queue(["a"], {}, cap=3)[0], ["a"])


class AppendMode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_history_survives_shard_ledger_overwrite(self):
        """片账本每轮被新 run 覆盖 —— 旧尝试必须能从已有日志里续上，否则永远到不了 3 次。"""
        base = os.path.join(self.tmp, "ledger")
        os.makedirs(base, exist_ok=True)
        p = os.path.join(base, "04b_shard03.json")
        ledger(p, [rec("L", err="Expecting value: line 1 column 1", elapsed_s=33,
                       at="2026-10-31T01:00:00Z")])
        first = A.build(base, "04b", 3)
        self.assertEqual(first["attempts_n"], 1)
        # 新 run 覆盖了同一个片账本（旧失败记录消失）
        ledger(p, [rec("L", err="Expecting value: line 1 column 1", elapsed_s=33,
                       at="2026-10-31T02:00:00Z")])
        second = A.build(base, "04b", 3, prev_attempts=first["attempts"])
        self.assertEqual(second["attempts_n"], 2)
        self.assertEqual(second["kept_from_prev_n"], 1)

    def test_duplicate_records_across_run_and_shard_are_merged(self):
        """run 快照与片账本是逐字节拷贝 → 同一次尝试不许记两遍。"""
        base = os.path.join(self.tmp, "ledger")
        os.makedirs(base, exist_ok=True)
        r = rec("L", err="Expecting value", elapsed_s=33.4, at="")
        ledger(os.path.join(base, "04b_shard03.json"), [r], at="2026-10-31T01:30:00Z")
        ledger(os.path.join(base, "04b_run41155023558.json"), [r], stage="04b",
               at="2026-10-31T01:40:00Z")
        log = A.build(base, "04b", 3)
        self.assertEqual(log["attempts_n"], 1)
        self.assertEqual(log["layers_n"], 1)

    def test_stage_alias_accepted(self):
        """片账本写 step04b、run 快照写 04b —— 两种都认，别把自家账本滤掉。"""
        self.assertTrue(A._stage_ok("step04b", "04b"))
        self.assertTrue(A._stage_ok("04b", "04b"))
        self.assertFalse(A._stage_ok("05b", "04b"))

    def test_build_is_idempotent(self):
        base = os.path.join(self.tmp, "ledger")
        os.makedirs(base, exist_ok=True)
        ledger(os.path.join(base, "04b_shard00.json"),
               [rec("L", reason="job 内单层超时", rc=-1, elapsed_s=3300)])
        a = json.dumps(A.build(base, "04b", 3), ensure_ascii=False, indent=1)
        b = json.dumps(A.build(base, "04b", 3), ensure_ascii=False, indent=1)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
