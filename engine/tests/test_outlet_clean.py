"""出口清洗 + addrkey v3 单测（归一、版本前缀、坐标合法性、分级边界）。"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine import outlet_clean as oc  # noqa: E402

GRADES = {"S": ["number", "street", "city", "state", "zip5", "point"],
          "A": ["number", "street", "state", "zip5", "point_any"],
          "B": ["number", "street", "state"],
          "C": ["street"]}


def rec(**kw):
    base = {"number": "58", "street": "Barbara Drive", "city": "Alton", "state": "nh",
            "zip": "03249", "lon": "-71.30", "lat": "43.47", "precision": "address_point"}
    base.update(kw)
    return oc.clean(base, {})


# ---------------------------------------------------------------- 归一
def test_state_and_zip_normalized():
    r = rec(state=" nh ", zip="03249-1234")
    assert r["state"] == "NH" and r["zip5"] == "03249"


@pytest.mark.parametrize("raw", ["None", "NOT STATED", "NULL", "", None, "N/A", "-"])
def test_placeholders_become_empty(raw):
    r = oc.clean({"number": "5", "street": "Main St", "state": "DE", "city": raw, "zip": raw})
    assert r["city"] == "" and r["zip5"] == ""


def test_num_key_keeps_suffix_letter():
    assert oc.clean({"number": "425b", "street": "Main St", "state": "DE"})["number"] == "425B"


def test_split_combined_never_guesses():
    assert oc.split_combined("58 BARBARA DRIVE") == ("58", "BARBARA DRIVE")
    assert oc.split_combined("COUNTY ROAD 12") == ("", "COUNTY ROAD 12")   # 没门牌就不硬拆


def test_combined_field_used_when_no_number():
    r = oc.clean({"combined": "58 BARBARA DRIVE", "state": "NH"})
    assert r["number"] == "58" and r["street"].upper().startswith("BARBARA")


# ---------------------------------------------------------------- addrkey v3
def test_addrkey_v3_prefix_and_stability():
    a = rec()["addrkey"]
    b = rec()["addrkey"]
    assert a == b and a.startswith("a3:") and len(a) == 3 + 20


def test_addrkey_v3_same_address_different_notation():
    a = rec(street="Barbara Drive", state="NH")["addrkey"]
    b = rec(street="  barbara   DR ", post_type="DR", state="NH")["addrkey"]
    assert a == b            # 缩写/大小写/空白归一后同键


def test_addrkey_v3_direction_word_matters():
    a = rec(street="Main St", pre_dir="N")["addrkey"]
    b = rec(street="Main St", pre_dir="S")["addrkey"]
    assert a != b            # 方向词不许被丢掉


def test_addrkey_v3_unit_switch():
    r = rec(unit="APT 5")
    assert oc.addrkey_v3(r, include_unit=True) != oc.addrkey_v3(r, include_unit=False)
    r2 = oc.clean({"number": "58", "street": "Barbara Drive", "state": "NH", "zip": "03249",
                   "lon": "-71.3", "lat": "43.47"}, {}, include_unit=False)
    r3 = oc.clean({"number": "58", "street": "Barbara Drive", "state": "NH", "zip": "03249",
                   "lon": "-71.3", "lat": "43.47", "unit": "UNIT 9"}, {}, include_unit=False)
    assert r2["addrkey"] == r3["addrkey"]      # 关掉单元号后同址合并


def test_addrkey_v3_empty_without_number_or_street():
    assert oc.clean({"street": "Main St", "state": "DE"})["addrkey"] == ""
    assert oc.clean({"number": "5", "state": "DE"})["addrkey"] == ""


def test_no_v1_v2_mixing():
    r = rec()
    assert r["addrkey"].startswith(oc.ADDRKEY_PREFIX + ":") and oc.ADDRKEY_VERSION == "v3"
    assert "|" not in r["addrkey"]           # v1/v2 是竖线拼接的明文键，v3 不允许混用


# ---------------------------------------------------------------- 坐标
def test_point_zero_and_out_of_range_rejected():
    assert oc.point_ok(0.0, 0.0) is False
    assert oc.point_ok(200.0, 10.0) is False
    assert oc.point_ok(-71.3, 43.47) is True
    r = oc.clean({"number": "1", "street": "X", "state": "NH", "lon": "0", "lat": "0"})
    assert r["point_ok"] is False


def test_interpolated_flag_from_spec():
    r = oc.clean({"number": "1", "street": "X", "state": "NH", "lon": "-71.3", "lat": "43.4"},
                 {"precision": "range_interpolation", "is_interpolated": True})
    assert r["is_interpolated"] is True and r["features"]["point"] is False
    assert r["features"]["point_any"] is True     # 插值点不许算真点，但仍是坐标


# ---------------------------------------------------------------- 分级边界
@pytest.mark.parametrize("kw,want", [
    ({}, "S"),
    ({"city": ""}, "A"),
    ({"city": "", "lon": "", "lat": ""}, "B"),
    ({"city": "", "lon": "", "lat": "", "number": ""}, "C"),
    ({"city": "", "lon": "", "lat": "", "number": "", "street": ""}, "X"),
])
def test_grade_boundaries(kw, want):
    assert oc.grade_of(rec(**kw)["features"], GRADES) == want
