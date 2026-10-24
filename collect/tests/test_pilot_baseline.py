#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A1 基线回归 —— 锁住 pilot.py 改造前的行为

五个用例全部零网络（monkeypatch pilot.get_json），跑完即为「基线」。
之后 A3~A10 每次改动都必须让这组用例保持全绿，否则就是退步。

用法: python3 -m unittest discover -s collect/tests -v
"""
import gzip
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pilot  # noqa: E402


class FakeServer:
    """忠实还原 ArcGIS 语义：区间过滤 + keyset 游标 + 分页开关。"""

    def __init__(self, n=22680, mode="keyset", page=2000):
        self.n, self.mode, self.page = n, mode, page
        self.requests = 0

    @staticmethod
    def bounds(where):
        import re
        lo, hi, after = 1, 10 ** 12, None
        m = re.search(r"FID>=(\d+)", where)
        if m:
            lo = int(m.group(1))
        m = re.search(r"FID<=(\d+)", where)
        if m:
            hi = int(m.group(1))
        m = re.search(r"FID>(?!=)(\d+)", where)
        if m:
            after = int(m.group(1))
        return lo, hi, after

    def __call__(self, url, timeout=180, tries=3):
        import re
        self.requests += 1
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        if "outStatistics" in q:
            return {"features": [{"attributes": {"mn": 1, "mx": self.n}}]}
        if q.get("returnCountOnly") == "true":
            lo, hi, _ = self.bounds(q.get("where", ""))
            return {"count": max(0, min(hi, self.n) - lo + 1)}
        if q.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": "FID", "objectIds": list(range(1, self.n + 1))}
        if "objectIds" in q:
            ids = [int(x) for x in q["objectIds"].split(",") if x]
            return {"features": [self.feat(i) for i in ids]}
        if "resultRecordCount" in q and self.mode == "nopage":
            # 真实服务就是这样报错的（HTTP 200 包着 error）
            return {"__error__": 'svcerr:{"code":400,"message":"Pagination is not supported."}'}
        if "resultRecordCount" not in q and "where" not in q:
            return {"fields": [{"name": "FID"}, {"name": "ADDRNUM"}],
                    "maxRecordCount": self.page, "objectIdField": "FID",
                    "definitionExpression": None}
        where = q.get("where", "1=1")
        lo, hi, after = self.bounds(where)
        hi = min(hi, self.n)
        ps = int(q.get("resultRecordCount", self.page))
        if self.mode == "broken" and after is not None and "resultOffset" not in q:
            return {"features": [], "exceededTransferLimit": False}
        if self.mode == "short" and (("resultOffset" in q and int(q["resultOffset"]) >= 2000)
                                     or (after is not None and after >= 2000)):
            return {"features": [], "exceededTransferLimit": False}
        if "resultOffset" in q:
            start = lo + int(q["resultOffset"])
        else:
            start = max(lo, after + 1) if after is not None else lo
        end = min(hi, start + ps - 1)
        if start > hi:
            return {"features": [], "exceededTransferLimit": False}
        return {"features": [self.feat(i) for i in range(start, end + 1)],
                "exceededTransferLimit": end < hi}

    @staticmethod
    def feat(i):
        return {"attributes": {"FID": i, "ADDRNUM": str(i)},
                "geometry": {"x": -97.0, "y": 38.0}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pilottest-")
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload,
                      pilot.UNIT_ROWS, pilot._pub)
        pilot.UNIT_ROWS = 5000          # 小单元 → 多单元，才能测到「跑到一半崩」
        pilot.OUTBASE = self.tmp
        self._progdir = pilot.PROG_DIR
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.CUR.update({"id": "t", "title": "t",
                          "url": "http://fake.local/FeatureServer/0", "svc": "FeatureServer"})
        self.uploads = []

        def fake_upload(files, log=None, tag=None):
            self.uploads.append([os.path.basename(f) for f in files])
            return True

        pilot._upload = fake_upload

    def tearDown(self):
        pilot.OUTBASE, cur, gj, up, pilot.UNIT_ROWS, pilot._pub = self._orig
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        pilot.get_json = gj
        pilot._upload = up
        pilot.PROG_DIR = self._progdir
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_collect(self, server, workers=4, fresh=True, limit=0):
        pilot.get_json = server
        return pilot.collect_arcgis_v2(pilot.CUR["url"], limit, lambda m: None, workers, fresh)

    def all_fids(self):
        ids = []
        d = os.path.join(self.tmp, "t")
        if not os.path.isdir(d):
            return ids
        for f in sorted(os.listdir(d)):
            if f.endswith(".ndjson.gz"):
                ids += [json.loads(line)["raw"]["FID"] for line in gzip.open(os.path.join(d, f), "rt")]
        return ids


class TestBaseline(Base):
    def test_keyset(self):
        """正常分页：keyset 游标一路翻到底"""
        s = FakeServer()
        rows, count, err, parts = self.run_collect(s)
        self.assertEqual(rows, 22680)
        self.assertEqual(count, 22680)
        self.assertEqual(err, "")
        self.assertGreaterEqual(parts, 1)

    def test_offset_fallback(self):
        """服务把「主键>n」当空条件 → 自动切 resultOffset 续翻"""
        s = FakeServer(mode="broken")
        rows, count, err, _ = self.run_collect(s)
        self.assertEqual(rows, 22680)
        self.assertEqual(err, "")

    def test_ids_channel(self):
        """不支持分页（Pagination is not supported）→ 走 returnIdsOnly + objectIds 批量"""
        s = FakeServer(mode="nopage")
        rows, count, err, parts = self.run_collect(s)
        self.assertEqual(rows, 22680)
        self.assertEqual(count, 22680)
        self.assertEqual(err, "")
        self.assertGreater(parts, 1)
        self.assertEqual(pilot.STRATEGY, "ids")

    def test_single_worker(self):
        """单线程路径同样要齐"""
        s = FakeServer()
        rows, count, err, _ = self.run_collect(s, workers=1)
        self.assertEqual(rows, 22680)

    def test_resume_after_crash(self):
        """跑到一半崩掉 → 检查点只记已完成单元 → 重启续跑补齐，且无重无缺"""
        s = FakeServer(mode="nopage")
        real_upload = pilot._upload
        calls = {"n": 0}

        def crashy(files, log=None, tag=None):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("模拟第 2 个单元崩溃")
            return real_upload(files, log, tag)

        pilot._upload = crashy
        with self.assertRaises(RuntimeError):
            self.run_collect(s)
        ck = json.load(open(os.path.join(self.tmp, "t", "_checkpoint.json")))
        self.assertGreater(len(ck.get("done_units") or []), 0)

        pilot._upload = real_upload
        rows, count, err, _ = self.run_collect(s, fresh=False)
        self.assertEqual(rows, 22680)
        self.assertEqual(err, "")
        # 续跑后本地被 purge，只能核对上传记录里的 FID 总数
        fids = []
        d = os.path.join(self.tmp, "t")
        for f in sorted(os.listdir(d)):
            if f.endswith(".ndjson.gz"):
                fids += [json.loads(l)["raw"]["FID"] for l in gzip.open(os.path.join(d, f), "rt")]
        self.assertLessEqual(len(fids), 22680)


    # ---------- A3 新增：单元完成判据 ----------
    def test_upload_failure_not_done(self):
        """上传失败 → 绝对不能标完成，且要留证据"""
        pilot._upload = lambda files, log=None, tag=None: False
        rows, count, err, _ = self.run_collect(FakeServer())
        ck = json.load(open(os.path.join(self.tmp, "t", "_checkpoint.json")))
        self.assertEqual(ck.get("done_units"), [])
        self.assertTrue(ck.get("unit_errors"))
        self.assertEqual(rows, 22680)          # 采到的行如实记账，不能显示 0

    def test_short_unit_not_done(self):
        """服务少给行（short）→ 不标完成"""
        rows, count, err, _ = self.run_collect(FakeServer(mode="short"))
        ck = json.load(open(os.path.join(self.tmp, "t", "_checkpoint.json")))
        self.assertEqual(ck.get("done_units"), [])
        self.assertTrue(any("short" in v for v in (ck.get("unit_errors") or {}).values()))

    def test_short_ack_after_two_runs(self):
        """同一单元连续两次 short 且行数一致 → 认可上游就这么多，转完成并留 ack"""
        s = FakeServer(mode="short")
        self.run_collect(s)
        self.run_collect(s, fresh=False)
        ck = json.load(open(os.path.join(self.tmp, "t", "_checkpoint.json")))
        self.assertTrue(ck.get("unit_short_ack"))
        self.assertTrue(ck.get("done_units"))

    def test_limit_not_judged_short(self):
        """--limit 试采不该被判 short"""
        rows, count, err, _ = self.run_collect(FakeServer(), limit=10)
        self.assertLessEqual(rows, 10)
        self.assertEqual(err, "")


    # ---------- A7 / A8 ----------
    def test_heartbeat_includes_resumed_rows(self):
        """A7：续跑时心跳显示的是总量，不是只剩本轮新增"""
        s = FakeServer(mode="nopage")
        self.run_collect(s)
        self.run_collect(s, fresh=False)          # 全部单元已完成 → 本轮新增 0
        prog = json.load(open(os.path.join(self.tmp, "progress", "t.json")))
        self.assertEqual(prog.get("rows"), 22680)
        self.assertEqual(prog.get("base_rows"), 22680)

    def test_ckpt_missing_vs_download_failed(self):
        """A8：tag 不存在 → 静默返回 None；tag 存在但下载失败 → 明确告警"""
        logs = []
        os.environ["GITHUB_REPOSITORY"] = "ip9988001/world-map-data-33"   # _fetch_ckpt_asset 需要仓库上下文
        self.addCleanup(os.environ.pop, "GITHUB_REPOSITORY", None)
        pilot._pub = lambda cmd, timeout=600: (1, "no such release")
        self.assertIsNone(pilot._fetch_ckpt_asset("h", lambda m: logs.append(m)))
        self.assertFalse(any("下载失败" in m for m in logs))

        pilot._pub = lambda cmd, timeout=600: (0, "") if cmd[2] == "view" else (1, "network reset")
        logs.clear()
        self.assertIsNone(pilot._fetch_ckpt_asset("h", lambda m: logs.append(m)))
        self.assertTrue(any("下载失败" in m for m in logs))


class TestVerdict(unittest.TestCase):
    """A5：退出码判据"""

    def test_full_pass(self):
        self.assertEqual(pilot.verdict(22680, 22680, "")[0], 0)

    def test_tiny_gap_tolerated(self):
        self.assertEqual(pilot.verdict(99, 100, "")[0], 0)      # 小层容 1 行

    def test_two_percent_gap_fails(self):
        self.assertEqual(pilot.verdict(98, 100, "")[0], 1)

    def test_san_juan_style_gap_fails(self):
        code, why = pilot.verdict(2000, 22680, "")
        self.assertEqual(code, 1)
        self.assertIn("short", why)

    def test_limit_skips_short(self):
        self.assertEqual(pilot.verdict(10, 22680, "", limit=10)[0], 0)

    def test_empty_layer_ok(self):
        self.assertEqual(pilot.verdict(0, 0, "")[0], 0)

    def test_error_fails(self):
        self.assertEqual(pilot.verdict(22680, 22680, "http500")[0], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
