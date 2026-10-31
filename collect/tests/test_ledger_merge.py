#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段账本合并的护栏单测（对应 2026-10-30 第二次「单 run 账本覆盖阶段账本」事故）。

三条硬约束：
  ① 单 run（小 run）不得覆盖阶段账本 —— 31 层不许把 272 层冲掉；
  ② 同一层不同状态按优先级合并：ok > partial > missing > unverified > empty > failed，
     同状态取行数大者（所以「这次跑挂了」不会把已有的 ok/partial 降级）；
  ③ revisions[] 只追加不替换（同一 run_id 去重，不重复记账）。
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ledger_merge as lm  # noqa: E402


def _rec(layer, status, rows=0, declared=1000):
    return {"layer": layer, "status": status, "declared": declared, "rows": rows}


def _stage(n=272, status="ok"):
    recs = [_rec("layer_%03d" % i, status, 1000) for i in range(n)]
    return {"schema": "collect-ledger-agg/v1", "stage": "04b", "layers_n": n,
            "ok": n if status == "ok" else 0, "partial": 0, "failed": 0,
            "declared": 1000 * n, "rows": 1000 * n, "complete": status == "ok",
            "records": recs, "revisions": []}


def _run(n=31):
    return {"schema": "collect-ledger-agg/v1", "stage": "04b", "layers_n": n,
            "ok": 0, "failed": n, "shards_expected": 3, "shards_reported": 3,
            "shards_incomplete": [],
            "records": [_rec("layer_%03d" % i, "failed", 0) for i in range(n)]}


class SingleRunCannotOverwriteStage(unittest.TestCase):
    def test_31_layers_does_not_touch_272_layer_stage(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ledger"))
            json.dump(_stage(272), open(os.path.join(d, "04b_ledger.json"), "w"))
            res = lm.write_run_and_stage("04b", _run(31), "41121952357", base_dir=d)
            self.assertFalse(res["stage_written"])
            self.assertEqual(res["reason"], "run_layers_31_lt_half_of_stage_272")
            # 阶段账本一个字节都没动
            stage = json.load(open(os.path.join(d, "04b_ledger.json")))
            self.assertEqual(stage["layers_n"], 272)
            self.assertEqual(stage["ok"], 272)
            self.assertEqual(stage["revisions"], [])
            # 单 run 文件必须写出来（scope=single_run + 片口径三件套）
            run = json.load(open(os.path.join(d, "ledger", "04b_run41121952357.json")))
            self.assertEqual(run["scope"], "single_run")
            self.assertEqual(run["layers_n"], 31)
            self.assertEqual(run["shards_expected"], 3)
            self.assertEqual(run["shards_reported"], 3)
            self.assertEqual(run["shards_incomplete"], [])

    def test_big_enough_run_merges(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ledger"))
            json.dump(_stage(10), open(os.path.join(d, "04b_ledger.json"), "w"))
            res = lm.write_run_and_stage("04b", _run(8), "R2", base_dir=d)
            self.assertTrue(res["stage_written"])
            stage = json.load(open(os.path.join(d, "04b_ledger.json")))
            self.assertEqual(stage["layers_n"], 10)     # 8 层按 layer_id 并入 + 2 层保留，取并集
            self.assertEqual(stage["failed"], 0)        # 这 8 层阶段账本里是 ok，本次跑挂不许降级
            self.assertEqual(stage["ok"], 10)

    def test_explicit_allow_overrides_guard(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ledger"))
            json.dump(_stage(272), open(os.path.join(d, "04b_ledger.json"), "w"))
            res = lm.write_run_and_stage("04b", _run(31), "R3", base_dir=d,
                                        allow_stage_overwrite=True)
            self.assertTrue(res["stage_written"])
            self.assertEqual(res["reason"], "explicit_allow")


class StatusPriority(unittest.TestCase):
    def test_order_is_ok_partial_missing_unverified_empty_failed(self):
        order = ["ok", "partial", "missing", "unverified", "empty", "failed"]
        ranks = [lm.rank(s) for s in order]
        self.assertEqual(ranks, sorted(ranks, reverse=True))
        self.assertEqual(len(set(ranks)), len(ranks))

    def test_capped_sits_between_ok_and_partial(self):
        """capped_by_upstream 比 partial 好、比 ok 差：它不会被续采改写，但也没有可复核的声明。

        排序必须让它稳定胜出，否则一次重跑就能把 capped 层降级回 partial/failed。
        """
        self.assertGreater(lm.rank("capped_by_upstream"), lm.rank("partial"))
        self.assertLess(lm.rank("capped_by_upstream"), lm.rank("ok"))
        merged, _ = lm.merge_records([_rec("a", "capped_by_upstream", 39_875_268)],
                                     [_rec("a", "partial", 1_000)])
        self.assertEqual(merged[0]["status"], "capped_by_upstream")


class RecountCappedSemantics(unittest.TestCase):
    """recount 必须与 adjudicate_04b 同口径：分母不含 capped 层，分子也扣它的行数。"""

    def test_gap_is_like_for_like(self):
        recs = [{"layer": "normal", "status": "ok", "declared": 100, "rows": 100},
                {"layer": "short", "status": "missing", "declared": 60, "rows": 10},
                {"layer": "capped", "status": "capped_by_upstream", "declared": None,
                 "declared_unverifiable": 500, "rows": 300}]
        c = lm.recount(recs)
        self.assertEqual(c["capped_by_upstream"], 1)
        self.assertEqual(c["declared"], 160)                 # 500 不在分母
        self.assertEqual(c["declared_unverifiable"], 500)
        self.assertEqual(c["rows"], 410)                     # 实采全算
        self.assertEqual(c["rows_capped"], 300)
        self.assertEqual(c["rows_verifiable"], 110)
        self.assertEqual(c["gap"], 50)                       # 160 − 110，不是 160 − 410
        self.assertGreater(c["gap"], 0)                      # 不许出现“负缺口”
        self.assertEqual(c["gap_pct"], 31.25)

    def test_no_capped_layer_keeps_old_semantics(self):
        c = lm.recount([{"layer": "a", "status": "ok", "declared": 100, "rows": 100},
                        {"layer": "b", "status": "missing", "declared": 60, "rows": 0}])
        self.assertEqual(c["gap"], 60)
        self.assertEqual(c["rows_capped"], 0)
        self.assertEqual(c["declared_unverifiable"], 0)

    def test_better_status_wins_regardless_of_order(self):
        merged, stats = lm.merge_records(
            [_rec("a", "partial", 500)],
            [_rec("a", "ok", 100)])          # 行数更小但状态更好 → 必须赢
        self.assertEqual(merged[0]["status"], "ok")
        self.assertEqual(merged[0]["rows"], 100)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(stats["kept"], 0)

    def test_worse_status_never_downgrades(self):
        merged, stats = lm.merge_records(
            [_rec("a", "partial", 39_875_268)],
            [_rec("a", "failed", 0)])        # 本次跑挂（NAD-view checkpoint 被覆盖就是这个形态）
        self.assertEqual(merged[0]["status"], "partial")
        self.assertEqual(merged[0]["rows"], 39_875_268)
        self.assertEqual(stats["kept"], 1)
        self.assertEqual(stats["downgrade_blocked"][0]["run_status"], "failed")

    def test_same_status_larger_rows_wins(self):
        merged, stats = lm.merge_records(
            [_rec("a", "ok", 100)], [_rec("a", "ok", 200)])
        self.assertEqual(merged[0]["rows"], 200)
        self.assertEqual(stats["updated"], 1)
        merged2, stats2 = lm.merge_records(
            [_rec("a", "ok", 300)], [_rec("a", "ok", 200)])
        self.assertEqual(merged2[0]["rows"], 300)
        self.assertEqual(stats2["kept"], 1)

    def test_counts_are_recounted_not_trusted(self):
        out, _ = lm.merge_stage_ledger("04b", _stage(4, "ok"), _run(2), "R")
        self.assertEqual(out["ok"], 4)       # 2 层新增也是 ok（run 里没有那两层）
        self.assertEqual(out["layers_n"], 4)
        self.assertEqual(out["declared"], 4000)


class ShardViewFollowsLatestRun(unittest.TestCase):
    def test_shards_incomplete_reflects_latest_run_not_stale(self):
        base = _stage(4)
        base["shards_incomplete"] = [0, 1, 2, 3]      # 上一轮全片未完成
        run = _run(4)
        run["shards_incomplete"] = []
        out, _ = lm.merge_stage_ledger("04b", base, run, "R_NEW")
        self.assertEqual(out["shards_incomplete"], [])   # 闸门看的是本轮
        self.assertEqual(out["shards_run_id"], "R_NEW")
        self.assertTrue(out["complete"])


class RevisionsAppendOnly(unittest.TestCase):
    def test_revisions_are_appended_not_replaced(self):
        base = _stage(4)
        base["revisions"] = [{"kind": "stage_merge", "run_id": "OLD", "note": "首次"}]
        out1, _ = lm.merge_stage_ledger("04b", base, _run(4), "R1")
        out2, _ = lm.merge_stage_ledger("04b", out1, _run(4), "R2")
        ids = [r.get("run_id") for r in out2["revisions"]]
        self.assertEqual(ids, ["OLD", "R1", "R2"])
        self.assertEqual(out2["revisions"][0]["note"], "首次")

    def test_same_run_id_does_not_duplicate(self):
        base = _stage(4)
        out1, _ = lm.merge_stage_ledger("04b", base, _run(4), "R1")
        out2, _ = lm.merge_stage_ledger("04b", out1, _run(4), "R1")
        ids = [r.get("run_id") for r in out2["revisions"]]
        self.assertEqual(ids, ["R1"])

    def test_revision_carries_run_and_stage_shape(self):
        base = _stage(4)
        out, _ = lm.merge_stage_ledger("04b", base, _run(4), "R9")
        ev = out["revisions"][-1]
        for k in ("kind", "at", "run_id", "run_layers_n", "run_shards_expected",
                  "run_shards_reported", "run_shards_incomplete",
                  "stage_layers_before", "stage_layers_after"):
            self.assertIn(k, ev)


class RowsRegressionNotSilent(unittest.TestCase):
    """状态优先 + 取行数大者的副作用：真退化会被永久掩盖 → 必须逐层写 regressions[]。"""

    def test_same_status_fewer_rows_is_recorded(self):
        merged, _ = lm.merge_records([_rec("a", "ok", 500)], [_rec("a", "ok", 300)])
        regs = lm.row_regressions([_rec("a", "ok", 500)], [_rec("a", "ok", 300)],
                                  run_id="R1", at="T")
        self.assertEqual(merged[0]["rows"], 500)          # 仍然保进展（取大者）
        self.assertEqual(len(regs), 1)                    # 但不静默
        self.assertEqual(regs[0]["stage_rows"], 500)
        self.assertEqual(regs[0]["run_rows"], 300)
        self.assertEqual(regs[0]["delta"], -200)
        self.assertEqual(regs[0]["merge_outcome"], "kept_stage_record_more_rows")

    def test_better_status_with_fewer_rows_is_recorded(self):
        # 唯一真会冲小 rows 的路径：partial 39.8M → ok 5M
        base = [_rec("nad", "partial", 39_875_268)]
        run = [_rec("nad", "ok", 5_000_000)]
        out, _ = lm.merge_stage_ledger("04b", {"records": base, "layers_n": 1}, 
                                       {"records": run, "layers_n": 1}, "R2", at="T")
        self.assertEqual(out["records"][0]["status"], "ok")
        self.assertEqual(out["records"][0]["rows"], 5_000_000)   # 合并结果确实变小了
        self.assertEqual(out["rows_regressions"], 1)            # 所以必须留账
        self.assertEqual(out["regressions"][0]["merge_outcome"], "took_run_record_status_better")
        self.assertEqual(out["regressions"][0]["delta"], 5_000_000 - 39_875_268)
        self.assertEqual(out["rows_regressions_unexplained"], 1)

    def test_worse_status_fewer_rows_is_recorded_too(self):
        out, _ = lm.merge_stage_ledger("04b", {"records": [_rec("a", "ok", 900)], "layers_n": 1},
                                       {"records": [_rec("a", "failed", 0)], "layers_n": 1}, "R3")
        self.assertEqual(out["records"][0]["rows"], 900)
        self.assertEqual(out["regressions"][0]["merge_outcome"], "kept_stage_record_status_better")

    def test_growth_or_equal_is_not_a_regression(self):
        regs = lm.row_regressions([_rec("a", "ok", 100), _rec("b", "ok", 100)],
                                  [_rec("a", "ok", 100), _rec("b", "ok", 200)], run_id="R")
        self.assertEqual(regs, [])
        out, _ = lm.merge_stage_ledger("04b", {"records": [_rec("a", "ok", 100)], "layers_n": 1},
                                       {"records": [_rec("a", "ok", 300)], "layers_n": 1}, "R4")
        self.assertEqual(out["regressions"], [])
        self.assertEqual(out["rows_regressions"], 0)

    def test_new_layers_are_not_regressions(self):
        regs = lm.row_regressions([], [_rec("brand_new", "ok", 10)], run_id="R")
        self.assertEqual(regs, [])

    def test_regressions_are_append_only_keyed_by_layer_and_run(self):
        base = {"records": [_rec("a", "ok", 500)], "layers_n": 1}
        r1 = {"records": [_rec("a", "ok", 300)], "layers_n": 1}
        out1, _ = lm.merge_stage_ledger("04b", base, r1, "R1")
        self.assertEqual(out1["rows_regressions"], 1)
        # 同一 run 再合一次 → 不重复记账
        out2, _ = lm.merge_stage_ledger("04b", out1, r1, "R1")
        self.assertEqual(out2["rows_regressions"], 1)
        # 新 run 再退化 → 追加第二条，历史不丢
        out3, _ = lm.merge_stage_ledger("04b", out2, {"records": [_rec("a", "ok", 100)],
                                                       "layers_n": 1}, "R2")
        self.assertEqual(out3["rows_regressions"], 2)
        self.assertEqual([e["run_id"] for e in out3["regressions"]], ["R1", "R2"])
        self.assertEqual(out3["revisions"][-1]["rows_regressions"], 1)

    def test_evidence_and_reason_pass_through(self):
        rec = _rec("a", "ok", 10)
        rec["regression_reason"] = "upstream 删了 3 个 county"
        rec["evidence"] = "analysis/upstream-diff-20261101.json"
        out, _ = lm.merge_stage_ledger("04b", {"records": [_rec("a", "ok", 50)], "layers_n": 1},
                                       {"records": [rec], "layers_n": 1, "scope": "single_run"}, "R5")
        e = out["regressions"][0]
        self.assertEqual(e["reason"], "upstream 删了 3 个 county")
        self.assertEqual(e["evidence"], "analysis/upstream-diff-20261101.json")
        self.assertEqual(out["rows_regressions_unexplained"], 0)
        # 也可从 run 账本的 row_shrink_evidence 表里取
        regs = lm.row_regressions([_rec("a", "ok", 50)], [_rec("a", "ok", 10)],
                                  {"row_shrink_evidence": {"a": "/tmp/ev.json"}}, run_id="R6")
        self.assertEqual(regs[0]["evidence"], "/tmp/ev.json")

    def test_human_section_lists_layer_old_new_and_missing_evidence(self):
        regs = lm.row_regressions([_rec("nad", "partial", 39_875_268)],
                                  [_rec("nad", "ok", 5_000_000)], run_id="R7")
        lines = lm.format_regressions_section(regs)
        text = "\n".join(lines)
        self.assertIn("层 rows 回退", text)
        self.assertIn("-34,875,268", text)
        self.assertIn("nad", text)
        self.assertIn("39,875,268", text)
        self.assertIn("5,000,000", text)
        self.assertIn("**缺**", text)
        self.assertIn("took_run_record_status_better", text)     # 处置分布要说清哪类是真空寸

    def test_write_run_and_stage_persists_regressions_and_returns_them(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "ledger"))
            json.dump(_stage(4), open(os.path.join(d, "04b_ledger.json"), "w"))
            run = {"layers_n": 4, "ok": 4, "failed": 0, "shards_expected": 1,
                   "shards_reported": 1, "shards_incomplete": [],
                   "records": [_rec("layer_%03d" % i, "ok", 1000) for i in range(4)]}
            run["records"][2] = _rec("layer_002", "ok", 10)      # 这一层 rows 回退
            res = lm.write_run_and_stage("04b", run, "R8", base_dir=d)
            self.assertTrue(res["stage_written"])
            self.assertEqual(res["rows_regressions"], 1)
            self.assertEqual(res["regressions"][0]["layer"], "layer_002")
            stage = json.load(open(os.path.join(d, "04b_ledger.json")))
            self.assertEqual(stage["rows_regressions"], 1)
            self.assertEqual(stage["records"][2]["rows"], 1000)   # 合并仍取更大值
            self.assertEqual(stage["regressions"][0]["run_rows"], 10)


if __name__ == "__main__":
    unittest.main()
