# -*- coding: utf-8 -*-
"""intake_full 的硬约束（零网络、零真实资产）

守的三条：
  1. addr 行零缺 house_number / street_name —— 这是页面能建的前提，不许靠「后面再洗」
  2. aux_* 主键与 addr_id **结构上不可能相交**（addr_id 裸 40 位 sha1，aux_key 带 p:/s:/n: 前缀）
  3. 每层对账闭合：rows_total(声明) 与 read(实读)，read = Σ四表 + reject
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
ROOT = os.path.dirname(COLLECT)
sys.path.insert(0, COLLECT)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import intake_33 as I33          # noqa: E402
import intake_full as F          # noqa: E402


class TestStreetNorm(unittest.TestCase):
    def test_reuses_field_map_normalization(self):
        """后缀/方向必须先经 field-map 归一（Street / North 全称），再拼 key —— 不许两套口径。"""
        row = {"street_name": "MAIN", "street_post_type": "st", "street_pre_dir": "n"}
        row = I33.norm_street(dict(row))
        self.assertEqual(row["street_post_type"], "Street")
        self.assertEqual(row["street_pre_dir"], "North")
        self.assertEqual(F.street_norm_key(row), "NORTH MAIN STREET")

    def test_collapses_spaces_and_case(self):
        row = {"street_name": "  oak   park  ", "street_post_type": "Avenue"}
        self.assertEqual(F.street_norm_key(row), "OAK PARK AVENUE")

    def test_empty_street_is_empty_key(self):
        self.assertEqual(F.street_norm_key({}), "")


class TestHelpers(unittest.TestCase):
    def test_house_num_int(self):
        self.assertEqual(F.house_num_int("4123B"), 4123)
        self.assertEqual(F.house_num_int("  77 "), 77)
        self.assertIsNone(F.house_num_int(None))
        self.assertIsNone(F.house_num_int("N/A"))

    def test_source_bucket(self):
        self.assertEqual(F.source_bucket("parcel_situs", "x"), "PARCEL")
        self.assertEqual(F.source_bucket("address_point", "https://a/NG911_Points/0"), "NG911")
        self.assertEqual(F.source_bucket("address_point", "https://a/National_Address_Database/0"), "NAD")
        self.assertEqual(F.source_bucket("address_point", "https://a/Addresses_Hosted/0"), "AGOL")


class TestKeysNeverCollide(unittest.TestCase):
    def test_addr_id_is_bare_sha1_aux_is_prefixed(self):
        """主键格式本身就是不相交的证明：只靠前缀，不靠跑完之后再比对。"""
        row = {"house_number": "100", "street_name": "MAIN", "state_abbr": "TX",
               "county_fips": "48453", "zip5": "78701"}
        aid = I33.addr_id(row)
        self.assertRegex(aid, r"^[0-9a-f]{40}$")
        for p in ("p:", "s:", "n:"):
            self.assertFalse(aid.startswith(p))


class TestLedgerClosure(unittest.TestCase):
    def test_reconcile_flags_missing_rows(self):
        good = {"layer": "a", "status": "ok", "rows_total": 10, "read": 10,
                "tables": {"addr": 8, "aux_parcel": 0, "aux_street": 0,
                           "aux_addr_nohouse": 1, "reject": 1}}
        # 坏账：读了 9 行，四表只落了 8 行（丢 1 行）→ 逐层对账必须响
        bad = {"layer": "b", "status": "ok", "rows_total": 10, "read": 9,
               "tables": {"addr": 8, "aux_parcel": 0, "aux_street": 0,
                          "aux_addr_nohouse": 0, "reject": 0}}
        s = F.summarise([good])
        self.assertTrue(s["reconcile_ok"])
        self.assertTrue(s["read_equals_declared"])
        s2 = F.summarise([good, bad])
        self.assertFalse(s2["reconcile_ok"])          # 9 ≠ 8 → 必须响
        self.assertEqual(s2["layers_unreconciled"], ["b"])
        self.assertFalse(s2["read_equals_declared"])  # 19 ≠ 20 → 必须响

    def test_status_counted(self):
        s = F.summarise([{"status": "no_assets"}, {"status": "ok"}, {"status": "ok"}])
        self.assertEqual(s["layers_by_status"], {"no_assets": 1, "ok": 2})


class TestAddrHardGates(unittest.TestCase):
    """addr 行零缺门牌/街名：从 route() 的判据本身锁死（不允许后面再补洗）。"""

    def _row(self, **kw):
        base = {"house_number": "100", "street_name": "MAIN", "state_abbr": "TX",
                "county_fips": "48453", "latitude": 30.0, "longitude": -97.0}
        base.update(kw)
        return base

    def test_missing_house_never_addr(self):
        self.assertEqual(I33.route(self._row(house_number=None), ["no_house_number"],
                                   "address_point")[0], "aux_addr_nohouse")

    def test_missing_street_never_addr(self):
        self.assertEqual(I33.route(self._row(street_name=None), ["no_street_name"],
                                   "address_point")[0], "reject")

    def test_clean_row_is_addr(self):
        self.assertEqual(I33.route(self._row(), [], "address_point")[0], "addr")

    def test_parcel_never_addr(self):
        self.assertEqual(I33.route(self._row(), [], "parcel_situs")[0], "aux_parcel")


if __name__ == "__main__":
    unittest.main()
