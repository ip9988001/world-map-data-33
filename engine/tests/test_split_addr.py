"""组合拳③ engine/split_addr 单测（纯函数，不联网、不读 dist）。

跑法：`python3 -m pytest engine/tests/test_split_addr.py -q`
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine.split_addr import addr_key, is_placeholder, split_city_tail, split_number_street  # noqa: E402


def ok(raw, num, street):
    r = split_number_street(raw)
    assert r["reason"] == "ok", (raw, r)
    assert r["house_number"] == num, (raw, r)
    assert r["street_name"] == street, (raw, r)


def rej(raw, reason):
    r = split_number_street(raw)
    assert r["reason"] == reason, (raw, r)
    assert r["house_number"] == "" and r["street_name"] == ""


def test_plain_numbers():
    ok("12 MAIN ST", "12", "MAIN ST")
    ok("1049 61ST ST", "1049", "61ST ST")
    ok("14090 CO RD A", "14090", "CO RD A")


def test_suffix_and_ranges():
    ok("12A MAIN ST", "12A", "MAIN ST")
    ok("12 B MAIN ST", "12 B", "MAIN ST")
    ok("12-14 MAIN ST", "12-14", "MAIN ST")
    ok("12 1/2 MAIN ST", "12 1/2", "MAIN ST")
    ok("123RD AVE", "123RD", "AVE")


def test_directions_and_units():
    ok("601 N CAPITOL AVE", "601", "N CAPITOL AVE")
    ok("123 Main St Apt 4", "123", "Main St")
    assert split_number_street("123 MAIN ST STE 200")["street_name"] == "MAIN ST"
    assert split_number_street("123 MAIN ST STE 200")["unit"].startswith("STE")


def test_non_address():
    rej("PO BOX 123", "po_box")
    rej("P O BOX 45", "po_box")
    rej("RR 2 BOX 45", "rural_route")
    rej("3XX E 12TH ST", "masked_number")
    rej("MAIN ST / OAK AVE", "intersection")
    rej("MAIN ST", "no_house_number")
    rej("TASSAJARA RD", "no_house_number")
    rej("12", "no_street")
    rej("-1", "placeholder")
    rej("", "empty")


def test_placeholders():
    for v in ("-1", "-999", "-9999", "0", "NULL", "NA", "N/A", "", None, 0, -1, -9999.0):
        assert is_placeholder(v), v
    for v in ("1", "10 N MAIN ST", "0AK ST", "-1 MAIN ST"):
        assert not is_placeholder(v), v


def test_city_tail():
    r = split_city_tail("123 MAIN ST SPRINGFIELD IL 62704")
    assert (r["house_number"], r["street_name"], r["city"], r["state"], r["zip"]) == \
        ("123", "MAIN ST", "SPRINGFIELD", "IL", "62704")
    assert r["confidence"] == 0.9
    r = split_city_tail("123 MAIN ST SPRINGFIELD IL")
    assert r["state"] == "IL" and r["zip"] == "" and r["confidence"] == 0.6
    assert split_city_tail("123 MAIN ST").get("reason") == "no_state_or_zip"


def test_addr_key_skips_placeholders():
    roles = {"num": {"number"}, "street": {"street"}, "zip": {"zip"}}
    # 占位门牌不得顶掉真门牌
    assert addr_key({"num": "5", "street": "MAIN ST"}, roles, "CA") == "CA|5|mainstreet|"
    k = addr_key({"num": "-1", "street": "MAIN ST"}, roles, "CA")
    assert k == "", k                     # 门牌是占位 → 构不出键，而不是 "CA|-1|mainstreet|"
    # 占位街名不得顶掉真街名
    k = addr_key({"num": "12", "street": "-1", "street2": "OAK AVE"}, roles, "CA")
    assert k == "" or "oakavenue" in k or k == "CA|12|mainstreet|", k
