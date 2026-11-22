#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-061 回归 —— 「400 Invalid or missing input parameters」根因与大字段剔除

这三组用例锁的都是「改前会错、改后不错」：

  A. `pick_oid_field`（纯函数）
     · 小写 `objectid_1`：改前全大写精确匹配取不到 → 返回 "OBJECTID" → orderByFields=OBJECTID → 服务端
       HTTP 200 + body `{"error":{"code":400,...}}`（实测 k3gis.net / k3gis.com 命中，两层共 101,334 行）
     · 完全没有主键候选：改前 fallback "OBJECTID" 发出去 → 400（实测 vt_nz，209,203 行）
     · 有主键（`esriFieldTypeOID` 或 objectIdField）：改前也能取到，改后不许退化
  B. 无主键时的采集路径：不许有任何一次请求带 orderByFields，必须靠 resultOffset 翻到底
  C. `outFields=*` 被 400：二分剔坏列后必须把其余列采全，并记 dropped_fields

用法: python3 -m unittest discover -s collect/tests -v
"""
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pilot  # noqa: E402


# ---------------------------------------------------------------- A. 纯函数
class TestPickOidField(unittest.TestCase):
    """改前：全大写精确匹配 + 取不到 fallback "OBJECTID"。改后：四级取法 + 取不到返回 ""。"""

    def setUp(self):
        self._orig_q = pilot._q
        pilot._q = lambda api, params, timeout=180: {"features": []}

    def tearDown(self):
        pilot._q = self._orig_q

    def test_a1_lowercase_objectid_1_is_found(self):
        """实测 k3gis.net：fields 里是小写 objectid_1，objectIdField 为 null。"""
        meta = {"objectIdField": None,
                "fields": [{"name": "community", "type": "esriFieldTypeString"},
                           {"name": "objectid_1", "type": "esriFieldTypeInteger"}]}
        self.assertEqual(pilot.pick_oid_field(meta, "http://fake/MapServer/0"), "objectid_1")

    def test_a2_field_type_oid_when_not_declared(self):
        """实测 vt_nz：主键只在 fields[].type 里露脸（StreetAddressID）。"""
        meta = {"objectIdField": None,
                "fields": [{"name": "StreetAddressID", "type": "esriFieldTypeOID"},
                           {"name": "RoadNameFull", "type": "esriFieldTypeString"}]}
        self.assertEqual(pilot.pick_oid_field(meta, "http://fake/MapServer/0"), "StreetAddressID")

    def test_a3_no_key_at_all_returns_empty_not_objectid(self):
        """改前这里返回 "OBJECTID"（一个上游根本不存在的列）→ orderByFields 直接 400。"""
        meta = {"objectIdField": None,
                "fields": [{"name": "a", "type": "esriFieldTypeString"},
                           {"name": "b", "type": "esriFieldTypeInteger"}]}
        got = pilot.pick_oid_field(meta, "http://fake/FeatureServer/0")
        self.assertEqual(got, "")
        self.assertNotEqual(got, "OBJECTID")

    def test_a4_declared_field_case_insensitive(self):
        """objectIdField="ID" 而 fields 里是 "id"（真实大小写）→ 必须回 "id"，不是 "ID"。"""
        meta = {"objectIdField": "ID",
                "fields": [{"name": "id", "type": "esriFieldTypeInteger"},
                           {"name": "x", "type": "esriFieldTypeString"}]}
        self.assertEqual(pilot.pick_oid_field(meta, "http://fake/MapServer/0"), "id")

    def test_a5_declared_but_absent_is_not_sent(self):
        """声明的字段不在 fields 里 → 不许把它发出去（改前会把 declared 直接塞进 orderByFields）。"""
        meta = {"objectIdField": "OBJECTID",
                "fields": [{"name": "a", "type": "esriFieldTypeString"}]}
        self.assertEqual(pilot.pick_oid_field(meta, "http://fake/FeatureServer/0"), "")

    def test_a6_name_heuristic_last_resort(self):
        """既没声明也没 OID 类型，但名字里带 objectid 后缀 → 仍能认出来。"""
        meta = {"objectIdField": None,
                "fields": [{"name": "gs_objectid", "type": "esriFieldTypeInteger"}]}
        self.assertEqual(pilot.pick_oid_field(meta, "http://fake/MapServer/0"), "gs_objectid")


# ---------------------------------------------------------------- B/C. 集成
class FakeBase:
    """忠实还原 ArcGIS 语义（count / 分页开关 / keyset / resultOffset / 400）。"""

    mode = "ok"

    def __init__(self, n=1200, page=200, fields=None, declared=None):
        self.n, self.page = n, page
        self.fields = fields or []
        self.declared = declared
        self.queries = []

    # ---- 元数据 ----
    def meta(self):
        return {"objectIdField": self.declared, "maxRecordCount": self.page,
                "fields": self.fields, "geometryType": "esriGeometryPoint",
                "definitionExpression": None}

    def feat(self, i, keys=None):
        at = {k: ("v%d" % i) for k in (keys or [f["name"] for f in self.fields])}
        # 用整数主键模拟上游 OBJECTID（供 keyset 游标比较）
        for k, v in list(at.items()):
            if k.lower().endswith(("objectid", "objectid_1", "_1")) or k.lower() in ("fid", "oid", "id"):
                at[k] = i
        return {"attributes": at, "geometry": {"x": 1.0, "y": 2.0}}

    @staticmethod
    def _after(oid, where):
        m = re.search(r"%s>(?!=)(-?\d+)" % re.escape(oid), where)
        return int(m.group(1)) if m else None

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries.append(q)
        if "f" in q and len(q) == 1:                     # ?f=json → 元数据
            return self.meta()
        if q.get("returnCountOnly") == "true":
            lo, hi, _ = _bounds_any(q.get("where", ""))
            return {"count": max(0, min(hi or self.n, self.n) - lo + 1)}
        if "outStatistics" in q:
            return {"features": [{"attributes": {"mn": 1, "mx": self.n}}]}
        if q.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": "oid", "objectIds": list(range(1, self.n + 1))}
        if "objectIds" in q:
            ids = [int(x) for x in q["objectIds"].split(",") if x]
            return {"features": [self.feat(i) for i in ids]}
        return self.page_query(q)

    def page_query(self, q):                               # 子类实现
        raise NotImplementedError


def _window(server, q, key):
    ps = int(q.get("resultRecordCount") or server.page)
    off = int(q.get("resultOffset") or 0)
    start = off + 1
    end = min(server.n, off + ps)
    if start > end:
        return {"features": [], "exceededTransferLimit": False}
    return {"features": [server.feat(i, [f["name"] for f in server.fields]) for i in range(start, end + 1)],
            "exceededTransferLimit": end < server.n}


def _bounds(oid, where):
    """解析 where 里的 `oid>=lo` / `oid<=hi` / `oid>last`（keyset 区间的忠实还原）。"""
    lo, hi = 1, None
    m = re.search(r"%s>=(-?\d+)" % re.escape(oid), where or "")
    if m:
        lo = int(m.group(1))
    m = re.search(r"%s<=(-?\d+)" % re.escape(oid), where or "")
    if m:
        hi = int(m.group(1))
    after = FakeBase._after(oid, where or "")
    return lo, hi, after


def _bounds_any(where):
    """不管主键叫什么，只抽出 >= / <= / > 的数值（用于 count 还原）。"""
    lo, hi = 1, None
    m = re.search(r"(\w+)\s*>=\s*(-?\d+)", where or "")
    if m:
        lo = int(m.group(2))
    m = re.search(r"(\w+)\s*<=\s*(-?\d+)", where or "")
    if m:
        hi = int(m.group(2))
    return lo, hi, None


class TestNoOidFieldCollect(FakeBase):
    """无主键层：一次 orderByFields 都不许发，靠 resultOffset 翻完。"""

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries.append(q)
        if "orderByFields" in q:
            # 真实服务就是这样：HTTP 200 包着 error（账本看着像上游的错）
            return {"__error__": 'svcerr:{"code":400,"message":"Invalid or missing input parameters."}'}
        return FakeBase.__call__(self, url, timeout, tries)

    def page_query(self, q):
        return _window(self, q, None)


class TestLowercaseOidCollect(FakeBase):
    """小写 objectid_1：keyset 必须用真实大小写；发 OBJECTID 就是 400。"""

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries.append(q)
        ob = q.get("orderByFields")
        if ob and ob != "objectid_1":
            return {"__error__": 'svcerr:{"code":400,"message":"Invalid or missing input parameters."}'}
        return FakeBase.__call__(self, url, timeout, tries)

    def page_query(self, q):
        ps = int(q.get("resultRecordCount") or self.page)
        lo, hi, after = _bounds("objectid_1", q.get("where", ""))
        hi = self.n if hi is None else min(hi, self.n)
        start = (after + 1) if after is not None else lo
        if "resultOffset" in q:
            start = (after + 1 if after is not None else lo) + int(q["resultOffset"])
        end = min(hi, start + ps - 1)
        if start > end:
            return {"features": [], "exceededTransferLimit": False}
        keys = [f["name"] for f in self.fields]
        return {"features": [self.feat(i, keys) for i in range(start, end + 1)],
                "exceededTransferLimit": end < hi}


class TestBadFieldCollect(FakeBase):
    """outFields=* 被 400（Pvc 的 Assess_Num）：剔除坏列后必须把其余列采全。"""

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries.append(q)
        of = q.get("outFields")
        if of and (of == "*" or "Assess_Num" in of):
            return {"__error__": 'svcerr:{"code":400,"message":"Cannot perform query. '
                                 'Invalid query parameters."}'}
        return FakeBase.__call__(self, url, timeout, tries)

    def page_query(self, q):
        ps = int(q.get("resultRecordCount") or self.page)
        lo, hi, after = _bounds("OBJECTID", q.get("where", ""))
        hi = self.n if hi is None else min(hi, self.n)
        start = (after + 1) if after is not None else lo
        end = min(hi, start + ps - 1)
        if start > end:
            return {"features": [], "exceededTransferLimit": False}
        of = q.get("outFields")
        keys = [f["name"] for f in self.fields] if of in (None, "*") else of.split(",")
        return {"features": [self.feat(i, keys) for i in range(start, end + 1)],
                "exceededTransferLimit": end < hi}


class CollectBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pilotoid-")
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload,
                      pilot.UNIT_ROWS, pilot._pub, pilot.PROG_DIR, pilot._q,
                      pilot.OUT_FIELDS, pilot.DROPPED_FIELDS)
        pilot.OUTBASE = self.tmp
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.UNIT_ROWS = 500
        pilot._pub = lambda *a, **k: True
        self.uploaded_rows = 0

        def fake_upload(files, log=None, tag=None):
            got = 0
            for f in files:
                with gzip.open(f, "rt") as fh:
                    got += sum(1 for line in fh if line.strip())
            self.uploaded_rows += got
            self.uploaded_files = len(files)
            return True

        pilot._upload = fake_upload
        pilot.CUR.update({"id": "t", "title": "t",
                          "url": "http://fake.local/FeatureServer/0", "svc": "FeatureServer"})

    def tearDown(self):
        (pilot.OUTBASE, cur, gj, up, pilot.UNIT_ROWS, pilot._pub, pilot.PROG_DIR,
         pilot._q, pilot.OUT_FIELDS, pilot.DROPPED_FIELDS) = self._orig
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_collect(self, server):
        pilot.get_json = server
        pilot._q = lambda api, params, timeout=180: server(
            api + "/query?" + urllib.parse.urlencode(params), timeout)
        return pilot.collect_arcgis_v2(pilot.CUR["url"], 0, lambda m: None, 2, True)

    def rows_on_disk(self):
        out = []
        d = os.path.join(self.tmp, "t")
        if not os.path.isdir(d):
            return out
        for f in sorted(os.listdir(d)):
            if f.endswith(".ndjson.gz"):
                out += [json.loads(x) for x in gzip.open(os.path.join(d, f), "rt")]
        return out


class TestNoOid(CollectBase):
    def test_b1_no_orderby_anywhere_and_all_rows_collected(self):
        s = TestNoOidFieldCollect(n=1200, page=200,
                                  fields=[{"name": "a", "type": "esriFieldTypeString"},
                                          {"name": "b", "type": "esriFieldTypeInteger"}])
        rows, count, err, parts = self.run_collect(s)
        self.assertEqual(err, "")
        self.assertEqual(count, 1200)
        self.assertEqual(rows, 1200, "无主键必须靠 resultOffset 翻到底，不能 400 掉")
        self.assertFalse([q for q in s.queries if "orderByFields" in q],
                         "没有主键时绝不许发 orderByFields（就是它把整层打成 400）")
        self.assertEqual(self.uploaded_rows, 1200)
        self.assertTrue([q for q in s.queries if "resultOffset" in q], "必须真的用 resultOffset 翻页")


class TestLowercaseOid(CollectBase):
    def test_b2_lowercase_oid_used_verbatim(self):
        s = TestLowercaseOidCollect(n=1200, page=200,
                                    fields=[{"name": "community", "type": "esriFieldTypeString"},
                                            {"name": "objectid_1", "type": "esriFieldTypeInteger"}])
        rows, count, err, parts = self.run_collect(s)
        self.assertEqual(err, "")
        self.assertEqual(rows, 1200)
        self.assertEqual(self.uploaded_rows, 1200)
        obs = {q.get("orderByFields") for q in s.queries if "orderByFields" in q}
        self.assertEqual(obs, {"objectid_1"}, "必须用真实大小写；发 OBJECTID 会 400")


class TestBadField(CollectBase):
    FIELDS = [{"name": "OBJECTID", "type": "esriFieldTypeOID"},
              {"name": "Add_Num", "type": "esriFieldTypeString"},
              {"name": "Street_Name", "type": "esriFieldTypeString"},
              {"name": "Assess_Num", "type": "esriFieldTypeString"},
              {"name": "Zip5", "type": "esriFieldTypeString"}]

    def test_c1_bad_field_dropped_and_rest_collected(self):
        s = TestBadFieldCollect(n=900, page=200, fields=self.FIELDS, declared="OBJECTID")
        rows, count, err, parts = self.run_collect(s)
        self.assertEqual(err, "")
        self.assertEqual(rows, 900, "剔除坏列后必须把其余行采全")
        self.assertEqual(self.uploaded_rows, 900)
        self.assertEqual(pilot.DROPPED_FIELDS, ["Assess_Num"], "坏列必须记进 dropped_fields")
        self.assertEqual(pilot.OUT_FIELDS.count(",") + 1, 4, "剩 4 列（5 列剔 1）")
        ok = [q for q in s.queries if q.get("outFields") not in (None, "*")
              and "Assess_Num" not in q["outFields"]]
        self.assertTrue(ok, "必须用显式列清单重取")

    def test_c2_star_ok_keeps_star(self):
        """没坏列时不许擅自改成显式列清单（不许改变正常层的行为）。"""
        s = TestBadFieldCollect(n=300, page=200,
                                fields=[{"name": "OBJECTID", "type": "esriFieldTypeOID"},
                                        {"name": "Add_Num", "type": "esriFieldTypeString"}],
                                declared="OBJECTID")
        # 把「Assess_Num 才会 400」改成「不会 400」
        orig = s.__class__.__call__

        class Clean(s.__class__):
            def __call__(self, url, timeout=180, tries=3):
                q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
                if q.get("outFields") == "*":
                    s.queries.append(q)
                    return FakeBase.__call__(self, url, timeout, tries)
                return orig(self, url, timeout, tries)

        clean = Clean(n=300, page=200,
                      fields=[{"name": "OBJECTID", "type": "esriFieldTypeOID"},
                              {"name": "Add_Num", "type": "esriFieldTypeString"}],
                      declared="OBJECTID")
        rows, count, err, parts = self.run_collect(clean)
        self.assertEqual(err, "")
        self.assertEqual(rows, 300)
        self.assertEqual(pilot.OUT_FIELDS, "*")
        self.assertEqual(pilot.DROPPED_FIELDS, [])


if __name__ == "__main__":
    unittest.main()
