#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面层质心契约 —— 「采了行却没坐标」不许再发生（零网络，全用假服务）

守的是什么：
  · 面层（Polygon）采集**每行必有 `_lat`/`_lon`**（算不出就是 null，但键不能缺）——
    2026-10-30 的 1,038 层 geom_missing 就是「键从来没落过」，下游分不清「没坐标」和「没采」
  · 面层的点必须是 representative_point（落在多边形内部），不是丢几何后的 null
  · `raw` 保留 Shape__Area/Shape__Length，`rings`/`paths` 不落盘
  · 点层不受影响，且**不发** returnCentroid（省一次服务端计算）
  · 默认开（PILOT_POLY_CENTROID 不设时为 1）
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
import pilot          # noqa: E402  (同时把 collect/ 塞进 sys.path)
import parcel_centroid as PC  # noqa: E402

# 凹多边形（L 形）：面积质心落在多边形外，只有 representative_point 才保证在内部
L_RING = [[-97.0, 32.0], [-96.999, 32.0], [-96.999, 32.001],
          [-96.9999, 32.001], [-96.9999, 32.002], [-97.0, 32.002]]
SQUARE = [[-97.5, 32.5], [-97.49, 32.5], [-97.49, 32.51], [-97.5, 32.51], [-97.5, 32.5]]


class FakePolyServer:
    """面层假服务：忠实还原 rings + exceededTransferLimit + 元数据里的 geometryType。"""

    def __init__(self, n=6, geom="esriGeometryPolygon"):
        self.n, self.geom = n, geom
        self.queries = []

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        if "where" not in q and "outFields" not in q:      # 元数据（?f=json）
            return {"geometryType": self.geom, "maxRecordCount": 2000,
                    "objectIdField": "FID", "definitionExpression": None,
                    "fields": [{"name": "FID"}, {"name": "ADDRNUM"}]}
        self.queries.append(q)
        if q.get("returnCountOnly") == "true":
            return {"count": self.n}
        if q.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": "FID", "objectIds": list(range(1, self.n + 1))}
        if "objectIds" in q:
            ids = [int(x) for x in q["objectIds"].split(",") if x]
            return {"features": [self.feat(i) for i in ids]}
        if "outStatistics" in q:
            return {"features": [{"attributes": {"mn": 1, "mx": self.n}}]}
        start = int(q.get("resultOffset") or 0)
        if q.get("where", "").find(">") > -1:
            import re
            m = re.search(r"FID>(?!=)(\d+)", q["where"])
            start = int(m.group(1)) if m else 0
        ps = min(int(q.get("resultRecordCount") or 2000), 2000)
        feats = [self.feat(i) for i in range(start + 1, min(self.n, start + ps) + 1)]
        return {"features": feats, "exceededTransferLimit": start + ps < self.n}

    def feat(self, i):
        if self.geom == "esriGeometryPoint":
            return {"attributes": {"FID": i, "ADDRNUM": str(i), "Shape__Area": None},
                    "geometry": {"x": -97.0 - i / 1e4, "y": 38.0}}
        ring = L_RING if i % 2 == 1 else SQUARE
        return {"attributes": {"FID": i, "ADDRNUM": str(i),
                               "Shape__Area": 1270.3984375, "Shape__Length": 145.9},
                "geometry": {"rings": [ring]},
                "centroid": {"x": -96.9995, "y": 32.0005}}     # 服务端质心（可能落在外部）


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="polyctr-")
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload,
                      pilot.PROG_DIR, pilot.GEOM_TYPE, pilot.POLY_CENTROID, pilot.POLY_RINGS)
        pilot.OUTBASE = self.tmp
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.CUR.update({"id": "t", "title": "t",
                          "url": "http://fake.local/FeatureServer/0", "svc": "FeatureServer"})
        # 上传后本地 part 会被 purge —— 所以在 fake upload 里把落盘内容原样读回来
        self.uploaded = []

        def fake_upload(files, log=None, tag=None):
            for f in files:
                if os.path.exists(f):
                    self.uploaded += [json.loads(l) for l in gzip.open(f, "rt")]
            return True

        pilot._upload = fake_upload

    def tearDown(self):
        (pilot.OUTBASE, cur, gj, up, pilot.PROG_DIR,
         pilot.GEOM_TYPE, pilot.POLY_CENTROID, pilot.POLY_RINGS) = self._orig
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def recs(self):
        return self.uploaded

    def run_collect(self, server, workers=2):
        pilot.get_json = server
        return pilot.collect_arcgis_v2(pilot.CUR["url"], 0, lambda m: None, workers, True)


class TestPolygonContract(Base):
    def test_poly_every_row_has_lat_lon(self):
        """面层：每行都有 `_lat`/`_lon` 两个键（null 也算有，缺键不行）"""
        self.run_collect(FakePolyServer(n=6))
        recs = self.recs()
        self.assertEqual(len(recs), 6)
        for r in recs:
            self.assertIn("_lat", r)
            self.assertIn("_lon", r)
            self.assertIsNotNone(r["_lat"], "面层行没有纬度：%r" % r.get("raw"))
            self.assertIsNotNone(r["_lon"])

    def test_poly_point_inside_polygon(self):
        """凹多边形的点必须落在内部（服务端面积质心会落在外面）"""
        self.run_collect(FakePolyServer(n=2))          # FID=1→L 形，FID=2→矩形
        recs = {r["raw"]["FID"]: r for r in self.recs()}
        lat, lon = recs[1]["_lat"], recs[1]["_lon"]
        self.assertTrue(PC.inside_geom(lon, lat, [L_RING]),
                        "L 形取点 (%.6f,%.6f) 落在多边形外" % (lon, lat))

    def test_poly_keeps_shape_area_and_simplifies_rings(self):
        """raw 保留 Shape__Area/Length；记录里的 `rings` 是**简化版**（不是上游原样）"""
        self.run_collect(FakePolyServer(n=2))
        for r in self.recs():
            self.assertIn("Shape__Area", r["raw"])
            self.assertIn("Shape__Length", r["raw"])
            self.assertNotIn("rings", r["raw"], "raw 里不许埋原始几何（体积失控）")
            self.assertIn("rings", r)
            # 截位后的坐标必须 ≤ 6 位小数（第 ② 档口径，不是「大概几位」）
            for ring in r["rings"]:
                for x, y in ring:
                    self.assertEqual(round(x, 6), x, "经度没截到 6 位：%r" % x)
                    self.assertEqual(round(y, 6), y, "纬度没截到 6 位：%r" % y)

    def test_poly_every_row_has_rings(self):
        """面层：每行都有 `rings` 键，且是闭合环（退化才是 null）"""
        self.run_collect(FakePolyServer(n=6))
        recs = self.recs()
        self.assertEqual(len(recs), 6)
        for r in recs:
            self.assertIn("rings", r, "面层行缺 rings 键 = 边界又丢了")
            self.assertIsInstance(r["rings"], list)
            self.assertTrue(r["rings"])
            for ring in r["rings"]:
                self.assertGreaterEqual(len(ring), 4, "闭合环至少 4 个点")
                self.assertEqual(ring[0], ring[-1], "环没闭合")

    def test_rings_never_more_vertices_than_raw(self):
        """简化后顶点数 ≤ 原始（简化只能删点，不能造点；唯一例外是上游环没闭合时补一个闭合点）"""
        for i, ring in ((1, L_RING), (2, SQUARE)):
            rec = pilot.make_rec({"attributes": {"FID": i}, "geometry": {"rings": [ring]}},
                                 "esriGeometryPolygon")
            self.assertIsNotNone(rec["rings"])
            closed = ring[0] == ring[-1]
            budget = len(ring) if closed else len(ring) + 1
            self.assertLessEqual(sum(len(r) for r in rec["rings"]), budget)

    def test_densified_edges_are_actually_simplified(self):
        """把正方形的每条边打成 40 个几乎共线的点 → RDP 1e-5° 必须把它们删掉"""
        corners = [(-97.0, 32.0), (-96.99, 32.0), (-96.99, 32.01), (-97.0, 32.01)]
        dense = []
        for k in range(len(corners)):
            x0, y0 = corners[k]
            x1, y1 = corners[(k + 1) % len(corners)]
            for t in range(40):
                dense.append([x0 + (x1 - x0) * t / 40.0, y0 + (y1 - y0) * t / 40.0])
        dense.append(list(dense[0]))
        rec = pilot.make_rec({"attributes": {"FID": 3}, "geometry": {"rings": [dense]}},
                             "esriGeometryPolygon")
        kept = sum(len(r) for r in rec["rings"])
        self.assertLess(kept, len(dense) / 4, "加密边没被简化（%d → %d）" % (len(dense), kept))

    def test_huge_ring_is_capped(self):
        """单行顶点硬上限：某层「缓冲区」几何不把一行写成几 MB（2 GB/资产上限的护栏）"""
        ring = [[-97.0 + i * 1e-6, 32.0 + (0.01 if i % 2 else 0.0)] for i in range(3000)]
        ring.append(list(ring[0]))
        out = PC.simplify_rings({"rings": [ring]}, max_verts=500)
        self.assertIsNotNone(out)
        self.assertLessEqual(sum(len(r) for r in out), 501)
        self.assertEqual(out[0][0], out[0][-1], "抽稀后要重新闭合")
        self.assertEqual(PC.SIMP_MAX_VERTS, 8000, "默认上限 8000 被改了")

    def test_poly_requests_return_centroid(self):
        """面层请求带 returnCentroid=true 与 outSR=4326（本地算不出来时的兜底）"""
        s = FakePolyServer(n=2)
        self.run_collect(s)
        qs = [q for q in s.queries if "outFields" in q]
        self.assertTrue(qs, "没发出任何取数请求")
        for q in qs:
            self.assertEqual(q.get("returnCentroid"), "true")
            self.assertEqual(q.get("outSR"), "4326")
            self.assertEqual(q.get("returnGeometry"), "true")

    def test_lat_lon_mirror_fields(self):
        """`_lat`/`_lon` 必须与 normalize 的 lat/lon 一致（下游两套读法不能打架）"""
        self.run_collect(FakePolyServer(n=4))
        for r in self.recs():
            self.assertEqual(r["_lat"], r["lat"])
            self.assertEqual(r["_lon"], r["lon"])


class TestPointLayerUnaffected(Base):
    def test_point_layer_has_lat_lon(self):
        self.run_collect(FakePolyServer(n=3, geom="esriGeometryPoint"))
        recs = self.recs()
        self.assertEqual(len(recs), 3)
        for r in recs:
            self.assertIsNotNone(r["_lat"])
            self.assertEqual(r["_lat"], r["lat"])

    def test_point_layer_does_not_send_return_centroid(self):
        s = FakePolyServer(n=2, geom="esriGeometryPoint")
        self.run_collect(s)
        for q in [q for q in s.queries if "outFields" in q]:
            self.assertNotIn("returnCentroid", q)


class TestDegenerateAndDefault(Base):
    def test_degenerate_ring_still_has_keys(self):
        """退化几何（环 <3 点）→ 值是 null，但键必须在（否则下游分不清没采/没坐标）"""
        rec = pilot.make_rec({"attributes": {"FID": 9},
                              "geometry": {"rings": [[[-97.0, 32.0], [-97.0, 32.0]]]}},
                             "esriGeometryPolygon")
        self.assertIn("_lat", rec)
        self.assertIsNone(rec["_lat"])
        self.assertIn("rings", rec, "退化也要有键（null），不能直接不生键")
        self.assertIsNone(rec["rings"], "退化几何 → rings=null，不猜、不拿 bbox 代替")

    def test_default_rings_is_on(self):
        """PILOT_POLY_RINGS 未设置时默认开（第 ② 档拍定的就是默认落简化 rings）"""
        self.assertIs(pilot.POLY_RINGS, True)

    def test_point_layer_has_no_rings_key(self):
        """点层不受影响：既不落 rings，也不白占字节"""
        rec = pilot.make_rec({"attributes": {"FID": 12}, "geometry": {"x": -97.0, "y": 32.0}},
                             "esriGeometryPoint")
        self.assertNotIn("rings", rec)
        self.assertIsNotNone(rec["_lat"])

    def test_polyline_has_no_rings_key(self):
        """线层：`paths` 不冒充 `rings`（只落中点坐标）"""
        rec = pilot.make_rec({"attributes": {"FID": 13},
                              "geometry": {"paths": [[[-97.0, 32.0], [-96.99, 32.01]]]}},
                             "esriGeometryPolyline")
        self.assertNotIn("rings", rec)

    def test_projected_geometry_is_not_guessed(self):
        """outSR 没生效（坐标是投影值）→ 不猜，落 null"""
        rec = pilot.make_rec({"attributes": {"FID": 10},
                              "geometry": {"rings": [[[2100000, 300000], [2100100, 300000],
                                                      [2100100, 300100]]]}},
                             "esriGeometryPolygon")
        self.assertIsNone(rec["_lat"])
        self.assertIsNone(rec["_lon"])

    def test_default_is_on(self):
        """PILOT_POLY_CENTROID 未设置时默认开"""
        self.assertIs(pilot.POLY_CENTROID, True)

    def test_polyline_gets_midpoint(self):
        """线层没有面积，取最长 path 中点（同样落 _lat/_lon）"""
        rec = pilot.make_rec({"attributes": {"FID": 11},
                              "geometry": {"paths": [[[-97.0, 32.0], [-96.99, 32.01],
                                                      [-96.98, 32.02]]]}},
                             "esriGeometryPolyline")
        self.assertAlmostEqual(rec["_lat"], 32.01, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
