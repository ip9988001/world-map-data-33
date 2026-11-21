#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1a 第 2 片：采集计划 5 个缺陷的回归测试（muse-000146 第 3–7 项）。

【3】full_plan 计数与列表同源（不在 50 处截断）
【4】dead 判定加复探 + 时间戳（首次 500 → 后续 200 不许判死；3 次全败才 dead）
【5】分页 400 单独归类（400 / 404 / 500 三类计数互不串）
【6】探针 body 解析固化（正常 / 字段改名 / 空体 三种形态）
【7】白名单单一来源（另一条入口不能独立放行层）→ 见 test_layers_single_source.py

全部离线：探针的 HTTP 层用假的 fetch 注入，不碰网络。
"""
from __future__ import annotations

import io
import json
import contextlib
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
sys.path.insert(0, COLLECT)

import full_plan as FP                                    # noqa: E402
from lib import fetch as F                              # noqa: E402


class TestCountBodyParsing(unittest.TestCase):
    """【6】解析固化：三种 body 形态 → count 或 parse_ok 符合预期，不许静默 None。"""

    def test_normal(self):
        r = FP.parse_count_body(b'{"count": 2298}')
        self.assertTrue(r["parse_ok"])
        self.assertEqual(r["count"], 2298)
        self.assertEqual(r["count_path"], "count")
        self.assertEqual(r["body_keys_sig"], "count")
        self.assertEqual(r["reason"], "")

    def test_renamed_field(self):
        # 上游把 count 改名成 total：能解析出来，并且记下命中的是哪条路径
        r = FP.parse_count_body(b'{"total": 7}')
        self.assertTrue(r["parse_ok"])
        self.assertEqual(r["count"], 7)
        self.assertEqual(r["count_path"], "total")

    def test_unknown_field_is_explicit_failure(self):
        r = FP.parse_count_body(b'{"features": []}')
        self.assertFalse(r["parse_ok"])
        self.assertIsNone(r["count"])
        self.assertIn("no_count_field", r["reason"])
        self.assertEqual(r["body_keys_sig"], "features")

    def test_empty_and_html_and_svcerr(self):
        for raw, why in ((b"", "empty_body"), (b"<html>x</html>", "html_body"),
                         (b'{"error":{"message":"Pagination is not supported."}}', "svcerr")):
            r = FP.parse_count_body(raw)
            self.assertFalse(r["parse_ok"], why)
            self.assertIsNone(r["count"])
            self.assertTrue(r["reason"].startswith(why), (r["reason"], why))

    def test_result_shape_has_all_six_keys(self):
        r = FP.parse_count_body(b'{"count": 1}')
        self.assertEqual(set(r), {"count", "count_path", "body_keys_sig", "parse_ok", "reason"})


class TestProbeDeadRetry(unittest.TestCase):
    """【4】dead 必须「复探 N 次全失败」，且带 dead_since + 逐次证据。"""

    def _fetch_seq(self, seq):
        calls = {"n": 0}

        def _f(url, timeout=0):
            status, code, body = seq[min(calls["n"], len(seq) - 1)]
            calls["n"] += 1
            return status, code, body, ""
        return _f

    def test_500_then_200_not_dead(self):
        rec = FP.probe_layer("http://x/0", attempts=3, backoff=(0, 0, 0),
                             fetch=self._fetch_seq([(500, 500, b"boom"), (200, 200, b'{"count": 12}')]),
                             sleep=lambda s: None)
        self.assertTrue(rec["ok"])
        self.assertFalse(rec["dead"])
        self.assertIsNone(rec["dead_since"])
        self.assertEqual(rec["count"], 12)
        self.assertEqual(len(rec["probe_attempts"]), 2)          # 第二次就成功，不再空转
        self.assertEqual(rec["probe_attempts"][0]["kind"], "server_5xx")
        for k in ("at", "attempt", "status", "code", "elapsed_ms"):
            self.assertIn(k, rec["probe_attempts"][0])

    def test_three_500_is_dead_with_timestamp(self):
        rec = FP.probe_layer("http://x/1", attempts=3, backoff=(0, 0, 0),
                             fetch=self._fetch_seq([(500, 500, b"boom")]),
                             sleep=lambda s: None)
        self.assertFalse(rec["ok"])
        self.assertTrue(rec["dead"])
        self.assertRegex(rec["dead_since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(len(rec["probe_attempts"]), 3)
        self.assertEqual([a["attempt"] for a in rec["probe_attempts"]], [1, 2, 3])
        self.assertEqual(rec["probe_attempts"][-1]["kind"], "server_5xx")

    def test_empty_url_is_dead_not_silent(self):
        rec = FP.probe_layer("", attempts=3, fetch=self._fetch_seq([(200, 200, b'{"count":1}')]))
        self.assertTrue(rec["dead"])
        self.assertEqual(rec["reason"], "empty_url")

    def test_count_one_compat_shell(self):
        # plan_probe_retry2.py 直接 import _count_one，语义必须保持 int|None
        c = FP._count_one.__wrapped__ if hasattr(FP._count_one, "__wrapped__") else None
        self.assertIsNone(c)                                  # 没有包装器，就是普通函数
        with mock.patch.object(FP, "probe_layer",
                               return_value={"ok": True, "count": 5}):
            self.assertEqual(FP._count_one("http://x/2", tries=1), 5)
        with mock.patch.object(FP, "probe_layer", return_value={"ok": False, "count": None}):
            self.assertIsNone(FP._count_one("http://x/3", tries=1))


class TestFailureKinds(unittest.TestCase):
    """【5】400（可修）/ 404 / 500（上游坏）三类互不串。"""

    def test_classify(self):
        self.assertEqual(F.classify_failure(400, '{"error":{"message":"Pagination is not supported."}}'),
                         F.KIND_BAD_PAGING)
        self.assertEqual(F.classify_failure(400, "resultOffset out of range"), F.KIND_BAD_PAGING)
        self.assertEqual(F.classify_failure(404, "Service not found"), F.KIND_404)
        self.assertEqual(F.classify_failure(500, "Internal Server Error"), F.KIND_5XX)
        self.assertEqual(F.classify_failure(429, "Too Many Requests"), F.KIND_429)
        self.assertEqual(F.classify_failure(status=200, body='{"error":{"code":-1}}'), F.KIND_SVCERR)

    def test_tally_does_not_cross_count(self):
        results = {
            "L400": {"dead": True, "probe_attempts": [{"kind": F.KIND_BAD_PAGING}]},
            "L404": {"dead": True, "probe_attempts": [{"kind": F.KIND_404}]},
            "L500a": {"dead": True, "probe_attempts": [{"kind": F.KIND_5XX}]},
            "L500b": {"dead": True, "probe_attempts": [{"kind": F.KIND_5XX}]},
        }
        tally = FP._failed_by_kind(results, list(results))
        self.assertEqual(tally[F.KIND_BAD_PAGING], 1)
        self.assertEqual(tally[F.KIND_404], 1)
        self.assertEqual(tally[F.KIND_5XX], 2)
        # 400 不许被算进 404/500
        self.assertEqual(tally[F.KIND_404] + tally[F.KIND_5XX], 3)
        self.assertEqual(sum(tally.values()), 4)

    def test_dead_entries_carry_evidence(self):
        results = {"L1": {"dead": True, "dead_since": "2026-11-22T00:00:00Z",
                          "probe_attempts": [{"at": "2026-11-22T00:00:00Z", "attempt": 1,
                                              "status": 500, "code": 500, "elapsed_ms": 3,
                                              "kind": F.KIND_5XX}],
                          "reason": "probe_failed:server_5xx"}}
        dead = FP._dead_entries(results)
        self.assertEqual(len(dead), 1)
        self.assertEqual(dead[0]["dead_since"], "2026-11-22T00:00:00Z")
        self.assertEqual(dead[0]["attempts_n"], 1)
        self.assertEqual(dead[0]["last_kind"], F.KIND_5XX)

    def test_get_json_attaches_kind(self):
        # 400 的 body 是答案：__error__ 保留原文，另加 __kind__ 分桶
        import urllib.error
        err = urllib.error.HTTPError("http://x", 400, "Bad Request", {},
                                     io.BytesIO(b'{"error":{"message":"Pagination is not supported."}}'))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            r = F.get_json("http://x/query")
        self.assertIn("__error__", r)
        self.assertEqual(r["__kind__"], F.KIND_BAD_PAGING)


class TestPlanListAndCountSameSource(unittest.TestCase):
    """【3】plan json 里 probe_failed 全量，计数 = len；截断只发生在展示层。"""

    def _fake_layers(self, n):
        return [{"id": "L%03d" % i, "url": "http://x/%d" % i, "expect": i} for i in range(n)]

    def test_60_failures_full_list_in_plan(self):
        layers = self._fake_layers(60)
        failed = [r["id"] for r in layers]
        results = {r["id"]: {"url": r["url"], "ok": False, "count": None, "dead": True,
                             "dead_since": "2026-11-22T00:00:00Z",
                             "count_path": None, "body_keys_sig": "html", "parse_ok": False,
                             "reason": "html_body",
                             "probe_attempts": [{"at": "2026-11-22T00:00:00Z", "attempt": 1,
                                                 "status": 200, "code": 200, "elapsed_ms": 1,
                                                 "kind": F.KIND_OTHER}]}
                   for r in layers}
        tmp = tempfile.mkdtemp(prefix="plan3-")
        out = os.path.join(tmp, "plan.json")
        buf = io.StringIO()
        with mock.patch.object(FP, "PROBE_ATTEMPTS", 1), \
                mock.patch.object(FP, "probe_live_counts",
                                  return_value=({}, failed, results)), \
                mock.patch("worker_core.load_policy",
                           return_value={"select": {}, "unit_rows": 1000, "workers": 4,
                                         "tag": "collect-step04-"}), \
                mock.patch("worker_core.select_layers", return_value=layers), \
                contextlib.redirect_stdout(buf):
            rc = FP.main(["--stage", "04", "--size", "20", "--out", out,
                          "--unstable-log", os.path.join(tmp, "none.json")])
        self.assertEqual(rc, 0)
        plan = json.load(open(out, encoding="utf-8"))
        self.assertEqual(len(plan["probe_failed"]), 60)                 # 不再是 50
        self.assertEqual(plan["probe_failed_n"], len(plan["probe_failed"]))
        self.assertEqual(set(plan["probe_failed"]), {r["id"] for r in layers})
        self.assertEqual(plan["probe_dead_n"], 60)
        self.assertTrue(all(x["dead_since"] for x in plan["probe_dead"]))
        self.assertEqual(sum(plan["probe_failed_by_kind"].values()), 60)
        # 展示层才截断，并且要写明「显示前 50 / 共 60」
        shown = json.loads(buf.getvalue().strip().splitlines()[-1])
        self.assertEqual(len(shown["probe_failed"]), 50)
        self.assertEqual(shown["probe_failed_display"], "显示前 50 / 共 60")


if __name__ == "__main__":
    unittest.main()
