# -*- coding: utf-8 -*-
"""`collect/lib/addrkey.py` 的口径单测（20 条对照 + 边界）。

对照表见 `docs/08-DEDUP-PLAN-DRAFT.md` 2.2；这里只钉死行为，不做统计。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import addrkey as AK      # noqa: E402


class StreetKey(unittest.TestCase):
    def test_unicode_kept(self):
        # 二仓 PUNCT 会把 CAÑON 砍成 CA ON（实测）
        self.assertEqual(AK.street_key("CAÑON", "RD"), "ROAD|CANON|")
        self.assertEqual(AK.street_key("Española", "St"), "STREET|ESPANOLA|")

    def test_type_field_wins_over_name_token(self):
        # 二仓实测：BRIDLE CREEK + BLVD → CREEK|BRIDLE
        self.assertEqual(AK.street_key("BRIDLE CREEK", "BLVD"), "BOULEVARD|BRIDLE CREEK|")
        self.assertEqual(AK.street_key("PARK PLACE", "DR"), "DRIVE|PARK PLACE|")
        self.assertEqual(AK.street_key("OAK RUN", "DR"), "DRIVE|OAK RUN|")

    def test_type_from_last_token_when_no_field(self):
        self.assertEqual(AK.street_key("BRIDLE CREEK BLVD"), "BOULEVARD|BRIDLE CREEK|")
        self.assertEqual(AK.street_key("OAK RUN DR"), "DRIVE|OAK RUN|")

    def test_unknown_type_kept(self):
        self.assertEqual(AK.street_key("COUNTY HIGHWAY", "TT"), "TT|COUNTY HIGHWAY|")

    def test_ordinal_same(self):
        self.assertEqual(AK.street_key("3RD", "ST"), AK.street_key("THIRD", "STREET"))
        self.assertEqual(AK.street_key("22nd", "Road"), "ROAD|22|")

    def test_direction_kept(self):
        self.assertNotEqual(AK.street_key("E MAIN", "ST"), AK.street_key("W MAIN", "ST"))
        self.assertEqual(AK.street_key("Oak", "Street", "East"), "STREET|OAK|E")
        self.assertEqual(AK.street_key("E MAIN", "ST", "", "W"), "STREET|MAIN|E+W")
        self.assertEqual(AK.street_key("N MAIN ST"), "STREET|MAIN|N")

    def test_punct_and_space(self):
        self.assertEqual(AK.street_key("O'BRIEN", "AVE"), "AVENUE|O BRIEN|")
        self.assertEqual(AK.street_key("  martin   luther king jr ", "blvd"),
                         "BOULEVARD|MARTIN LUTHER KING JR|")


class NumKey(unittest.TestCase):
    def test_digits(self):
        self.assertEqual(AK.num_key("123"), "123")
        self.assertEqual(AK.num_key(" 123 "), "123")
        self.assertEqual(AK.num_key(123), "123")

    def test_suffix_kept(self):
        self.assertEqual(AK.num_key("123A"), "123A")
        self.assertEqual(AK.num_key("123-45"), "123-45")

    def test_empty(self):
        self.assertEqual(AK.num_key(""), "")
        self.assertEqual(AK.num_key(None), "")


class UnitKey(unittest.TestCase):
    def test_equivalents(self):
        for v in ("APT 5", "#5", "UNIT 5", "STE 5", "SUITE 5", "apt-5", "5"):
            self.assertEqual(AK.unit_key(v), "5", v)

    def test_empty_is_distinct(self):
        self.assertEqual(AK.unit_key(""), "")
        self.assertNotEqual(AK.unit_key(""), AK.unit_key("5"))

    def test_dirty_guard(self):
        # 实测：WI_NG911 层 48.8% 的行 unit 是 L/R/Left/Right（左右侧标志）
        for v in ("L", "R", "Left", "Right", "Y", "N"):
            self.assertEqual(AK.unit_key(v), "", v)

    def test_too_long(self):
        self.assertEqual(AK.unit_key("BUILDING B REAR ENTRANCE"), "")


class AddrKey(unittest.TestCase):
    def test_shape(self):
        k = AK.addr_key("ia", "19113", "412", "STREET|3|S", "D")
        self.assertEqual(k, "IA|19113|412|STREET|3|S|D")

    def test_unkeyable(self):
        self.assertEqual(AK.addr_key("IA", "19113", "", "STREET|3|", ""), "")
        self.assertEqual(AK.addr_key("IA", "19113", "412", "||", ""), "")


if __name__ == "__main__":
    unittest.main()
