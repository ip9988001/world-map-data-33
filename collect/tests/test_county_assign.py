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


class TestStatePolicy(unittest.TestCase):
    """州口径（2026-10-30 裁定）：清单州为准，属性州只做校验，跨州溢出合法。"""

    def test_norm_state_variants(self):
        self.assertEqual(C.norm_state("Kentucky"), "KY")
        self.assertEqual(C.norm_state("KY"), "KY")
        self.assertEqual(C.norm_state(" ky "), "KY")
        self.assertEqual(C.norm_state("KY 911"), "KY")
        self.assertEqual(C.norm_state("未定位"), "")
        self.assertEqual(C.norm_state(None), "")
        self.assertEqual(C.norm_state("ZZ"), "")

    def test_conflict_uses_list_state_as_authority(self):
        """肯塔基层被清单标成 IN、数据里是 KY → 记 conflict，但清单值仍是 IN（不改判）"""
        a = C.state_verdict("ces_Ky_911_x", "IN", "KY", "KY", rows=1659731, rows_off=1659731)
        self.assertEqual(a["kind"], "conflict")
        self.assertEqual(a["list_state"], "IN")
        self.assertEqual(a["attr_state"], "KY")
        self.assertEqual(a["rows"], 1659731)

    def test_list_missing_is_anomaly(self):
        a = C.state_verdict("x", "", "KY", "KY", rows=10, rows_off=0)
        self.assertEqual(a["kind"], "list_missing")

    def test_geo_conflict_when_dominant_county_state_differs(self):
        a = C.state_verdict("x", "IN", "", "KY", rows=100, rows_off=100)
        self.assertEqual(a["kind"], "geo_conflict")

    def test_cross_state_spillover_is_not_anomaly(self):
        """清单/属性/县多边形三者一致时无 anomaly（哪怕有跨州行，见 rows_off_state）"""
        self.assertEqual(C.state_verdict("x", "KY", "KY", "KY", rows=100, rows_off=7), {})

    def test_attr_state_sampled_from_named_column(self):
        """属性州取自 field-map 点名的真实列；元数据型 [[layer_meta.state]] 不算数据列"""
        p = C.StateProbe("x", {"state_abbr": {"src": "State"}})
        for v in ("Kentucky", "KY", "Kentucky", ""):
            p.feed({"raw": {"State": v}})
        self.assertEqual(p.top(), "KY")
        self.assertEqual(p.col, "State")
        p2 = C.StateProbe("y", {"state_abbr": {"src": "[[layer_meta.state]]"}})
        p2.feed({"raw": {"OBJECTID": 1}})
        self.assertEqual(p2.top(), "")

    def test_geo_top_state(self):
        self.assertEqual(C.geo_top_state({"21": 100, "18": 5}), "KY")
        self.assertEqual(C.geo_top_state({}), "")


class TestResumeContract(unittest.TestCase):
    def test_old_verdict_is_not_done(self):
        """v2 结果（没有 verdict_ver）不算完成 —— 口径变了必须复核"""
        self.assertFalse(C.is_done({"status": "ok"}))
        self.assertFalse(C.is_done({"status": "ok", "verdict_ver": 2}))
        self.assertFalse(C.is_done({"status": "ok", "verdict_ver": C.VERDICT_VER,
                                    "max_seconds_hit": True}))
        self.assertFalse(C.is_done({"status": "partial", "verdict_ver": C.VERDICT_VER}))
        self.assertTrue(C.is_done({"status": "ok", "verdict_ver": C.VERDICT_VER}))

    def test_suspect_threshold(self):
        """UNLOCATED 占比 > 50% 才是 suspect；边界值 50% 不算"""
        self.assertEqual(C.SUSPECT_UNLOC_PCT, 50.0)


class TestSnapshot(unittest.TestCase):
    def test_assets_of_reads_snapshot_without_api(self):
        """快照命中时不许打 API（1,158 层 × 4 tag = 4,600 次会撞配额）"""
        import tempfile
        d = tempfile.mkdtemp()
        fp = os.path.join(d, "release-snapshot.json")
        json.dump({"map": {"collect-step10-L1": [{"n": "L1-u00000.tar.gz", "u": "", "s": 1}]}},
                  open(fp, "w"))
        old = (C.SNAPSHOT_F, C._SNAP["m"])
        try:
            C.SNAPSHOT_F, C._SNAP["m"] = fp, None
            self.assertEqual(len(C.assets_of("collect-step10-L1")), 1)
            self.assertEqual(C.assets_of("collect-step10-nope"), [])
        finally:
            C.SNAPSHOT_F, C._SNAP["m"] = old
            import shutil
            shutil.rmtree(d, ignore_errors=True)
