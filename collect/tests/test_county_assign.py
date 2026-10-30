# -*- coding: utf-8 -*-
"""county_assign 的判据不变量（零网络、零真实资产：全用合成记录）

守的是什么：
  · 坐标三分类必须互斥且完备 —— 落不了县的「一条不漏」全靠这个分类闭合
  · 逐层文件必须叫 rows-<layer_id>.json（评测/汇总按这个 glob 收）
  · 汇总口径 unlocated_total = rows - located = 无坐标 + 投影坐标 + 判不出
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
ROOT = os.path.dirname(COLLECT)
sys.path.insert(0, COLLECT)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import county_assign as C  # noqa: E402


class TestCoordKind(unittest.TestCase):
    def test_envelope_latlon_is_ok(self):
        self.assertEqual(C.coord_kind({"lat": 30.1, "lon": -97.1})[0], "ok")

    def test_raw_lat_lon_is_ok(self):
        self.assertEqual(C.coord_kind({"raw": {"X": -97.1, "Y": 30.1}})[0], "ok")

    def test_no_coord_fields_is_no_coords(self):
        got = C.coord_kind({"raw": {"PARCEL_ID": "R1", "OWNER": "A"}})[0]
        self.assertEqual(got, "no_coords")

    def test_projected_coords_is_proj_failed(self):
        got = C.coord_kind({"raw": {"X_COORD": 2134567.1, "Y_COORD": 10345678.2}})[0]
        self.assertEqual(got, "proj_failed")

    def test_out_of_range_degree_is_proj_failed(self):
        self.assertEqual(C.coord_kind({"raw": {"LAT": 99.0, "LON": -97.0}})[0], "proj_failed")

    def test_string_numbers_are_not_coords(self):
        """字符串经纬不算坐标（采集侧已转数字；这里不猜）"""
        got = C.coord_kind({"raw": {"LATITUDE": "30.1", "LONGITUDE": "-97.1"}})[0]
        self.assertEqual(got, "no_coords")

    def test_classification_is_exclusive(self):
        """四条合成记录 → 四档各一次，加起来必须等于总行数"""
        recs = [{"lat": 30.0, "lon": -97.0},
                {"raw": {"X_COORD": 1.0, "Y_COORD": 2.0}},
                {"raw": {"A": 1}},
                {"raw": {"X": -80.1, "Y": 40.1}}]
        kinds = [C.coord_kind(r)[0] for r in recs]
        self.assertEqual(sum(1 for k in kinds if k == "ok"), 2)
        self.assertEqual(kinds.count("proj_failed"), 1)
        self.assertEqual(kinds.count("no_coords"), 1)


class TestOutputs(unittest.TestCase):
    def test_safe_name_keeps_id_readable(self):
        self.assertEqual(C.safe_name("a/b c"), "a_b_c")
        self.assertEqual(C.safe_name("layer_0"), "layer_0")

    def test_layer_dump_filename(self):
        st = {"layer": "x/y_1", "rows": 0, "located": 0}
        with tempfile.TemporaryDirectory() as td:
            C._dump_layer(st, td)
            self.assertEqual(os.listdir(td), ["rows-x_y_1.json"])

    def test_summary_math_closes(self):
        rows = [
            {"layer": "a", "state": "TX", "status": "ok", "rows": 100, "located": 90,
             "unlocated": 5, "no_coords": 3, "proj_failed": 2, "unlocated_total": 10},
            {"layer": "b", "state": "TX", "status": "no_assets", "rows": 0, "located": 0,
             "unlocated": 0, "no_coords": 0, "proj_failed": 0, "unlocated_total": 0},
        ]
        with tempfile.TemporaryDirectory() as td:
            for r in rows:
                json.dump(r, open(os.path.join(td, "rows-%s.json" % r["layer"]), "w"))
            s = C.write_summary(td, os.path.join(td, "sum.json"))
        self.assertEqual(s["rows"], 100)
        self.assertEqual(s["unlocated_total"], 10)          # rows - located
        self.assertEqual(sum(s["unlocated_breakdown"].values()), 10)   # 三档相加必须闭合
        self.assertEqual(s["layers_by_status"].get("no_assets"), 1)
        self.assertEqual(s["by_state"]["TX"]["layers"], 2)


if __name__ == "__main__":
    unittest.main()
