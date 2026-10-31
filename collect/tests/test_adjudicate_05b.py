# -*- coding: utf-8 -*-
"""05b 收口判官单测：failed → 四类挂账，`failed` 归零但缺口一分不少。

守的事故（2026-10-31）：run `41167836540` 21/21 片收工、`shards_incomplete=[]`，
账本里还剩 30 层 failed、阶段 gap 只有 1,277,743 行（1.24%）。为这点行数再烧一轮 CI
不划算，但「留着 failed=30」和「悄悄改成 ok」都不行 —— 前者每次都要人肉解释，
后者是灌水。所以按证据归四类，并把每一类的层数/声明/已采/缺口摆出来。
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import adjudicate_05b as A  # noqa: E402


def rec(layer, status="failed", rows=None, declared=None, reason="", err="", elapsed=None):
    return {"layer": layer, "status": status, "rows": rows, "declared": declared,
            "reason": reason, "err": err, "elapsed_s": elapsed}


def ledger(*recs, **kw):
    d = {"schema": "collect-ledger-agg/v1", "stage": "05b", "at": "2026-10-31T08:19:39Z",
         "ledger_note": "test",
         "last_merge": {"run_id": "41167836540"}, "records": list(recs)}
    d.update(kw)
    return d


class Classify(unittest.TestCase):
    def test_404_wins_over_rows(self):
        """有 88 行但端点是 HTML 404 → unverified（端点没了，再试也拿不到下一页）"""
        c, why = A.classify(rec("x", rows=88, declared=56888,
                                err='batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML'))
        self.assertEqual(c, "unverified")
        self.assertIn("404", why)

    def test_timeout_is_unstable(self):
        c, why = A.classify(rec("x", reason="job 内单层超时 60 分钟（--layer-timeout）",
                                elapsed=3600))
        self.assertEqual(c, "upstream_unstable")

    def test_svcerr_is_unstable(self):
        c, _ = A.classify(rec("x", err='query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters"}'))
        self.assertEqual(c, "upstream_unstable")

    def test_rows_without_hard_refusal_is_partial(self):
        c, why = A.classify(rec("x", rows=9602, declared=9861, err="?"))
        self.assertEqual(c, "partial")
        self.assertIn("259", why)                    # 缺口 9861-9602

    def test_over_collected_partial_says_no_more_work(self):
        c, why = A.classify(rec("x", rows=26616, declared=14616))
        self.assertEqual(c, "partial")
        self.assertIn("超采", why)

    def test_zero_rows_without_evidence_is_missing(self):
        c, _ = A.classify(rec("x", rows=0, declared=125648, err="?"))
        self.assertEqual(c, "missing")


class Apply(unittest.TestCase):
    def setUp(self):
        self.led = ledger(
            rec("ok1", status="ok", rows=5000, declared=5000),
            rec("empty1", status="empty", rows=0, declared=0),
            rec("t1", reason="job 内单层超时 60 分钟（--layer-timeout）", elapsed=3600),
            rec("g1", err='batch0:http404:<!DOCTYPE html PUBLIC'),
            rec("p1", rows=9101, declared=9624, err="?"),
            rec("m1", rows=0, declared=125648, err="?"),
            failed=1, partial=0, ok=1, empty=1, layers_n=6,
            declared=152897, rows=14101, gap=137896,
            shards_expected=1, shards_reported=1, shards_incomplete=[])
        self.cls = A.build_classification(self.led)

    def test_failed_becomes_zero_and_buckets_add_up(self):
        out = A.apply(self.led, self.cls)
        self.assertEqual(out["failed"], 0)
        self.assertEqual(out["upstream_unstable"], 1)
        self.assertEqual(out["unverified"], 1)
        self.assertEqual(out["partial"], 1)
        self.assertEqual(out["missing"], 1)
        self.assertEqual(out["ok"], 1)
        self.assertEqual(out["empty"], 1)
        self.assertEqual(sum(out["buckets"].values()), out["layers_n"])

    def test_rows_and_declared_never_change(self):
        """收口只能改状态，不许动行数/声明 —— 否则就是自己把缺口改小了"""
        out = A.apply(self.led, self.cls)
        b, a = sorted(self.led["records"], key=lambda r: r["layer"]), \
            sorted(out["records"], key=lambda r: r["layer"])
        for x, y in zip(b, a):
            self.assertEqual(x.get("rows"), y.get("rows"))
            self.assertEqual(x.get("declared"), y.get("declared"))
        self.assertEqual(sum(int(r.get("rows") or 0) for r in out["records"]),
                         sum(int(r.get("rows") or 0) for r in b))

    def test_ok_and_empty_records_untouched(self):
        out = A.apply(self.led, self.cls)
        for r in out["records"]:
            if r["layer"] in ("ok1", "empty1"):
                self.assertNotIn("gap_class", r)
                self.assertNotIn("status_before_adjudication", r)

    def test_reclassify_is_idempotent(self):
        """--check 要能重算同一份结果：第二次跑必须看到同一批层（靠 status_before_adjudication）"""
        once = A.apply(self.led, self.cls)
        cls2 = A.build_classification(once)
        twice = A.apply(once, cls2)
        self.assertEqual(json.dumps(twice, sort_keys=True, ensure_ascii=False),
                         json.dumps(once, sort_keys=True, ensure_ascii=False))
        self.assertEqual(len(cls2["layers"]), len(self.cls["layers"]))
        self.assertEqual(sorted(x["from_status"] for x in cls2["layers"]),
                         sorted(x["from_status"] for x in self.cls["layers"]))

    def test_gap_by_class_keeps_every_row(self):
        out = A.apply(self.led, self.cls)
        g = out["gap_by_class"]
        self.assertEqual(g["partial"]["gap"], 523)               # 9624-9101
        self.assertEqual(g["missing"]["gap"], 125648)            # 0 行
        # 超时/404 两层的 declared 是 None → 记 0，缺口为 0（不虚构）
        self.assertEqual(g["upstream_unstable"]["declared_unknown_n"], 1)

    def test_refuses_to_touch_non_failed_layer(self):
        bad = A.build_classification(self.led)
        bad["layers"].append({"layer": "ok1", "from_status": "ok", "class": "missing",
                              "reason": "x", "rows": 5000, "declared": 5000,
                              "attempts_n": 0, "failure_kinds": []})
        with self.assertRaises(SystemExit):
            A.apply(self.led, bad)


class Doc(unittest.TestCase):
    def test_doc_reports_both_numbers_and_four_classes(self):
        led = ledger(rec("t1", reason="job 内单层超时 60 分钟"), rec("p1", rows=1, declared=3))
        cls = A.build_classification(led)
        out = A.apply(led, cls)
        doc = A.render_doc(out, cls, "41167836540")
        for must in ("`upstream_unstable`", "`partial`", "`unverified`", "`missing`",
                     "对外必报这张表", "adjudicate_05b.py --check"):
            self.assertIn(must, doc, must)
        self.assertIn("failed **0**", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
