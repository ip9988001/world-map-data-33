#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unit 切片「行数 + 字节」双上限 —— GitHub 单资产 2 GB 的护栏（零网络，全假服务）

守的是什么（2026-10-30 的全局 bug）：
  · 实测 `Offices_of_Physicians` 32.6 KB/行 × 10 万行 = **3.26 GB**，纯按行数切会撞 GitHub 单资产
    2 GB 上限 —— 这个风险对**点层同样存在**（有的层一行几十个字段/超长串），不只是宗地。
  · 正确规则：`unit_rows` 与 `unit_bytes`(1.5 GB) 同时生效，**先到先切**；估算带余量，
    真实落盘字节进检查点（`unit_bytes`），超线进 `unit_bytes_over` 明账，不静默。
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
import pilot          # noqa: E402

BIG_ATTR = "X" * 30000                       # 一行 30 KB（≈ Offices_of_Physicians 的实测量级）


class FakeBigServer:
    """点层假服务：每行 30 KB 属性、可配总行数。"""

    def __init__(self, n=40):
        self.n = n
        self.queries = []

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        if "where" not in q and "outFields" not in q:
            return {"geometryType": "esriGeometryPoint", "maxRecordCount": 2000,
                    "objectIdField": "FID", "definitionExpression": None,
                    "fields": [{"name": "FID"}, {"name": "ADDRNUM"}, {"name": "NOTE"}]}
        self.queries.append(q)
        if q.get("returnCountOnly") == "true":
            import re
            lo = re.search(r"FID>=(\d+)", q.get("where") or "")
            hi = re.search(r"FID<=(\d+)", q.get("where") or "")
            a = int(lo.group(1)) if lo else 1
            b = int(hi.group(1)) if hi else self.n
            return {"count": max(0, min(b, self.n) - a + 1)}
        if "outStatistics" in q:
            return {"features": [{"attributes": {"mn": 1, "mx": self.n}}]}
        if "returnIdsOnly" in q:
            return {"objectIdFieldName": "FID", "objectIds": list(range(1, self.n + 1))}
        import re
        where = q.get("where", "")
        # 区间单元：FID>=lo AND FID<=hi（切分测试必须尊重区间，否则每个单元都拿到全表）
        lo = re.search(r"FID>=(\d+)", where)
        hi = re.search(r"FID<=(\d+)", where)
        a = int(lo.group(1)) if lo else 1
        b = int(hi.group(1)) if hi else self.n
        start = a - 1
        if where.find(">") > -1 and not lo:
            m = re.search(r"FID>(?!=)(\d+)", where)
            start = int(m.group(1)) if m else 0
        if "resultOffset" in q:
            start = max(start, int(q.get("resultOffset") or 0))
        ps = min(int(q.get("resultRecordCount") or 2000), 2000)
        end = min(b, start + ps)
        feats = [self.feat(i) for i in range(start + 1, end + 1)]
        return {"features": feats, "exceededTransferLimit": end < b}

    def feat(self, i):
        return {"attributes": {"FID": i, "ADDRNUM": str(i), "NOTE": BIG_ATTR},
                "geometry": {"x": -97.0 - i / 1e4, "y": 32.0}}


class UnitBytes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="unitbytes-")
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload, pilot.PROG_DIR,
                      pilot.GEOM_TYPE, pilot.POLY_RINGS, pilot.RINGS_SKIP,
                      pilot.UNIT_BYTES, pilot.UNIT_BYTES_MARGIN, pilot.UNIT_ROWS)
        pilot.OUTBASE = self.tmp
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.CUR.update({"id": "big", "title": "big",
                          "url": "http://fake.local/FeatureServer/0", "svc": "FeatureServer"})
        pilot._upload = lambda files, log=None, tag=None: True
        pilot.RINGS_SKIP = ""

    def tearDown(self):
        (pilot.OUTBASE, cur, gj, up, pilot.PROG_DIR, pilot.GEOM_TYPE, pilot.POLY_RINGS,
         pilot.RINGS_SKIP, pilot.UNIT_BYTES, pilot.UNIT_BYTES_MARGIN, pilot.UNIT_ROWS) = self._orig
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 纯函数：切分规则本身
    def test_plan_units_byte_cap_reproduces_the_bug(self):
        """30 KB/行 × 10 万行：只按行数切会是 1 个 3.26 GB 单元；双上限必须切成多个 ≤1.5 GB"""
        rows, bpr = 100_000, 30_000
        units_old, _ = pilot.plan_units(rows, 1, rows, bytes_per_row=0,
                                        unit_rows=100_000, unit_bytes=1_500_000_000)
        self.assertEqual(len(units_old), 1, "按行数切只出一个单元 —— 正是要修的 bug")
        self.assertGreater(rows * bpr, 2_000_000_000, "这个用例必须真的超过 GitHub 2 GB")

        units, cap = pilot.plan_units(rows, 1, rows, bytes_per_row=bpr,
                                      unit_rows=100_000, unit_bytes=1_500_000_000)
        self.assertGreaterEqual(len(units), 3, "必须切成多个单元，实际 %d" % len(units))
        self.assertLessEqual(cap, int(1.5e9 / (bpr * pilot.UNIT_BYTES_MARGIN)) + 1)
        for lo, hi in units:                      # 每个单元的行数 → 估算字节 ≤ 1.5 GB
            self.assertLessEqual((hi - lo + 1) * bpr, 1_500_000_000)
        self.assertEqual(units[-1][1], rows, "切分必须覆盖到最后一行")

    def test_plan_units_small_rows_keeps_row_cap(self):
        """小行（300 B/行）时字节上限不该干预：仍然按行数切"""
        units, cap = pilot.plan_units(500_000, 1, 500_000, bytes_per_row=300,
                                      unit_rows=100_000, unit_bytes=1_500_000_000)
        self.assertEqual(cap, 100_000)
        self.assertEqual(len(units), 5)

    # ---- 端到端：真跑一次采集，单元按字节切开
    def test_collect_splits_by_bytes(self):
        """2,000 行 × 30 KB（= 60 MB），把上限缩成 1 MB / 500 行 → 必须切成多个 ≤1 MB 的单元"""
        pilot.UNIT_BYTES = 200_000                # 200 KB 上限（等价于 1.5 GB 的缩小版）
        pilot.UNIT_ROWS = 50
        pilot.GEOM_TYPE = "esriGeometryPoint"
        pilot.get_json = FakeBigServer(n=200)
        pilot.collect_arcgis_v2(pilot.CUR["url"], 0, lambda m: None, 2, True)
        ck = json.load(open(pilot._ckpt_path(), encoding="utf-8"))
        ur = ck.get("unit_rows") or {}
        vals = list(ur.values()) if isinstance(ur, dict) else list(ur)
        self.assertGreaterEqual(len(vals), 5, "200 行 × 30 KB 按 200 KB 切，单元数不止 5：%d" % len(vals))
        self.assertEqual(sum(vals), 200, "切分不能丢行：%s" % vals[:8])
        per = ck.get("unit_bytes") or {}
        self.assertTrue(per, "落盘字节必须记账（unit_bytes）")
        self.assertLessEqual(max(per.values()), 200_000 * 1.05,
                             "单元落盘字节超上限：max=%d" % max(per.values()))
        self.assertFalse(ck.get("unit_bytes_over"), "不该有超线单元：%s" % ck.get("unit_bytes_over"))


class NonParcel(unittest.TestCase):
    def setUp(self):
        self._cur = dict(pilot.CUR)
        pilot.CUR.update({"id": "np", "title": "np"})

    def tearDown(self):
        pilot.CUR.clear()
        pilot.CUR.update(self._cur)

    def test_rules(self):
        """非宗地面判别：无 parcel 语义 + （顶点均值 >50 倍中位 或 层名带 buffer/building 等）"""
        # 顶点炸裂（Offices_of_Physicians 实测 2,950 顶点）
        self.assertTrue(pilot.is_non_parcel(2950, names=("0min__Offices_of_Physicians__2016",)))
        # 名称档：Buffer1000 只有 124 顶点，够不上 50 倍中位，但形状明显不是宗地
        self.assertTrue(pilot.is_non_parcel(124, names=("xbY9zhyxPvde_Buffer1000",)))
        self.assertTrue(pilot.is_non_parcel(8, names=("Hosted_Buildings_2024",)))
        # 有 parcel 语义 → 再重也按宗地处理（宁可多存）
        self.assertFalse(pilot.is_non_parcel(2950, names=("Tax_Parcels_2020",)))
        self.assertFalse(pilot.is_non_parcel(800, names=("Situs_Join",)))
        # 普通宗地：都不是
        self.assertFalse(pilot.is_non_parcel(9.9, names=("Parcel_Query",)))

    def test_rings_skipped_marker(self):
        """命中非宗地面 → 不落 rings，改记 `rings_skipped='non_parcel'`（明账，不是静默丢）"""
        orig = pilot.RINGS_SKIP
        try:
            pilot.RINGS_SKIP = "non_parcel"
            rec = pilot.make_rec({"attributes": {"FID": 1},
                                  "geometry": {"rings": [[[-97.0, 32.0], [-96.99, 32.0],
                                                          [-96.99, 32.01], [-97.0, 32.01]]]}},
                                 "esriGeometryPolygon")
            self.assertNotIn("rings", rec)
            self.assertEqual(rec.get("rings_skipped"), "non_parcel")
            self.assertIsNotNone(rec.get("_lat"), "跳过 rings 不影响质心")
        finally:
            pilot.RINGS_SKIP = orig


if __name__ == "__main__":
    unittest.main()
