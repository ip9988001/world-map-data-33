# -*- coding: utf-8 -*-
"""probe_service_token 的判定纯逻辑（不联网，probe 打桩）。

事故：2026-10-30 22:23Z 之后 NAD view 层上游改成服务级 token，三端点全返回
HTTP **200** + body `{"error":{"code":499,"message":"Token Required"}}`。
只看 status code 会把「服务正常」写进账，于是这层永远被当成「我们没采」，
每轮重采一遍、永远 0 行。判据必须落在响应体上，且要两轮一致。
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import probe_service_token as P  # noqa: E402


def tok(url):
    return {"url": url, "http": "200", "raw": '{"error":{"code":499,"message":"Token Required"}}',
            "error_code": 499, "error_message": "Token Required", "message_code": "GWM_0003",
            "count": None, "service_level_token": True, "endpoint_ok": False}


def ok(url, count=7):
    return {"url": url, "http": "200", "raw": '{"count":7}', "error_code": None,
            "error_message": None, "message_code": None, "count": count,
            "service_level_token": False, "endpoint_ok": True}


class Verdict(unittest.TestCase):
    def setUp(self):
        self._orig = P.probe

    def tearDown(self):
        P.probe = self._orig

    def test_all_endpoints_499_twice_is_service_token(self):
        P.probe = tok
        r = P.probe_layer("L", "https://x/L/0", rounds=2, gap=0)
        self.assertEqual(r["verdict"], "service_level_token")
        self.assertTrue(r["all_rounds_token"])
        self.assertEqual(r["rounds_n"], 2)
        self.assertIn("服务级 token", r["conclusion"])

    def test_one_readable_endpoint_disqualifies(self):
        """任一端点能读到 count → 不是服务级 token（单次 query 被拦另说）。"""
        calls = {"n": 0}

        def mixed(url):
            calls["n"] += 1
            return ok(url) if url.endswith("?f=json") else tok(url)

        P.probe = mixed
        r = P.probe_layer("L", "https://x/L/0", rounds=2, gap=0)
        self.assertEqual(r["verdict"], "reachable")
        self.assertFalse(r["all_rounds_token"])

    def test_single_round_is_never_enough(self):
        """只跑一轮 → 不能凭空说两轮一致；结论必须留成 inconclusive 或仍按 499 但轮数=1。"""
        P.probe = tok
        r = P.probe_layer("L", "https://x/L/0", rounds=1, gap=0)
        self.assertEqual(r["rounds_n"], 1)
        # 单轮全 499 仍是 service_level_token，但 E14 只在「两轮确认」时才建议改判
        self.assertTrue(r["all_rounds_token"])

    def test_endpoints_shape(self):
        e = P.endpoints("https://x/L/0/")
        self.assertTrue(e["service_metadata"].endswith("/0?f=json"))
        self.assertIn("returnCountOnly=true", e["returnCountOnly"])
        self.assertIn("returnIdsOnly=true", e["returnIdsOnly"])


if __name__ == "__main__":
    unittest.main()
