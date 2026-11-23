"""Regression tests for the calibration sandbox (stateless rules only)."""
import json
import os

import pytest

import rules


HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


def test_fixtures_exist():
    for n in ("granit_nh_belknap.json", "tiger_nh_interp_33001.json", "nad_de_kent.json"):
        assert len(load(n)) > 0


def test_canonical_maps_aliases():
    c = rules.canonical({"HOUSE_NUMBER": 12, "STREET_NAME": "Main St", "ZIPCODE": "03301",
                         "CITY": "Concord", "STATE": "NH", "longitude": -71.5, "latitude": 43.2})
    assert c["number"] == 12 and c["street"] == "Main St" and c["zip"] == "03301"
    assert c["city"] == "Concord" and c["state"] == "NH"
    assert c["lon"] == -71.5 and c["lat"] == 43.2


def test_canonical_is_pure():
    src = {"number": "5", "street": "Elm"}
    before = dict(src)
    rules.canonical(src)
    assert src == before


def test_street_normalisation():
    assert rules.norm_street("Main St.") == "MAIN STREET"
    assert rules.norm_street("N Main rd") == "NORTH MAIN ROAD"
    assert rules.street_key({"street": "  elm  st "}) == "ELM STREET"


def test_class_S():
    rec = {"number": "10", "street": "Main St", "city": "Concord", "state": "NH",
           "zip": "03301", "lon": -71.5, "lat": 43.2}
    assert rules.classify(rec) == "S"


def test_class_A_missing_zip_and_city():
    assert rules.classify({"number": "10", "street": "Main St"}) == "A"
    assert rules.classify({"number": "10", "street": "Main St", "city": "Concord"}) == "A"


def test_class_B_and_C():
    assert rules.classify({"street": "Main St", "city": "Concord"}) == "B"
    assert rules.classify({"fullname": "River Rd"}) == "C"
    assert rules.classify({}) == "C"


def test_groups():
    assert rules.field_group({"number": "1", "street": "A", "city": "C", "state": "S",
                              "zip": "1", "lon": 1, "lat": 1}) == "full_address"
    assert rules.field_group({"number": "1", "street": "A"}) == "no_zip"
    assert rules.field_group({"number": "1", "street": "A", "zip": "1"}) == "no_city"
    assert rules.field_group({"street": "A"}) == "road_only"
    assert rules.field_group({"foo": "bar"}) == "empty_shell"


def test_nonnull_rate_explicit_denominator():
    recs = [{"number": "1"}, {"number": ""}, {"street": "x"}, {}]
    r = rules.nonnull_rate(recs, "number")
    assert r == {"field": "number", "nonnull": 1, "denom": 4, "rate": 0.25}
    r2 = rules.nonnull_rate(recs, "number", denom=10)
    assert r2["denom"] == 10 and r2["rate"] == 0.1


def test_group_layers_counts():
    layer_records = {
        "L1": [{"number": "1", "street": "A", "city": "C", "state": "S", "zip": "1", "lon": 1, "lat": 1}] * 3,
        "L2": [{"street": "A"}] * 2,
    }
    out = rules.group_layers(layer_records)
    assert out["groups"]["full_address"] == ["L1"]
    assert out["groups"]["road_only"] == ["L2"]
    assert sum(out["counts"].values()) == 2


def test_determinism_on_fixture():
    recs = load("granit_nh_belknap.json")
    a = rules.layer_profile("granit", recs)
    b = rules.layer_profile("granit", recs)
    assert a == b
    assert a["class_mode"] in ("S", "A", "B", "C")


def test_tiger_fixture_is_road_only():
    recs = load("tiger_nh_interp_33001.json")
    prof = rules.layer_profile("tiger", recs)
    # addrfeat-derived rows carry number+street but no city/state/zip columns
    assert prof["class_mode"] in ("A", "B", "C")
    assert prof["nonnull"]["number"] > 0


def test_nad_de_fixture_has_numbers():
    recs = load("nad_de_kent.json")
    prof = rules.layer_profile("nad", recs)
    assert prof["nonnull"]["number"] > 0.5
    assert prof["nonnull"]["street"] > 0.5


def test_number_alias_addr_housenumber():
    """F1: OSM 风格 `addr_housenumber`（Sacramento/Boston 的真实字段）必须被认成门牌。"""
    rec = {"addr_housenumber": "225", "addr_street": "Jibboom Street",
           "addr_city": "Sacramento", "addr_state": "CA", "addr_postcode": "95811"}
    assert rules.canonical(rec)["number"] == "225"
    assert rules.has_number(rec) is True
    assert rules.field_group(rec) != "road_only"
    assert rules.field_group(rec) == "no_zip"  # 缺坐标 → 不是 full_address
    assert rules.classify(rec) == "A"


def test_number_alias_addr_number_upper_wins_over_building():
    """F1: `ADDR_NUMBER`（MD）要认，而且不能被泛化别名 `building` 抢走。"""
    rec = {"ADDR_NUMBER": 1910, "BUILDING": 3, "STREET_NAME": "ELKHART", "STREET_TYPE": "ST",
           "POSTAL_CITY": "SILVER SPRING", "STATE": "MD", "ZIP": "20910"}
    assert rules.canonical(rec)["number"] == 1910
    assert rules.has_number(rec) is True
    assert rules.field_group(rec) != "road_only"
    assert rules.classify(rec) == "A"


def test_number_alias_housenumbe_truncated():
    """F1: 10 字符截断后的 `HOUSENUMBE`（IL）也要认。"""
    rec = {"HOUSENUMBE": "12", "STREETNAME": "COUNTY LINE", "CITY": "CUSTER PARK",
           "STATE": "IL", "ZIP_CODE": "60481"}
    assert rules.canonical(rec)["number"] == "12"
    assert rules.has_number(rec) is True
    assert rules.field_group(rec) != "road_only"


def test_number_alias_does_not_swallow_unit_or_suffix_fields():
    """F1 反向护栏：单元号/号段后缀/记录序号都不许当门牌（否则 road_only 判据反向失真）。"""
    for rec in ({"UNIT_NUM": "5", "STREET_NAME": "Main St", "ZIP": "1"},
                {"ADDRNUMSUF": "A", "STREET_NAME": "Main St", "ZIP": "1"},
                {"ADDR_RECNO": 7, "STREET_NAME": "Main St", "ZIP": "1"},
                {"PREADDRNUM": "9", "STREET_NAME": "Main St", "ZIP": "1"}):
        assert rules.has_number(rec) is False, rec
        assert rules.field_group(rec) == "road_only", rec


def test_no_production_imports():
    src = open(os.path.join(HERE, "rules.py"), encoding="utf-8").read()
    for bad in ("collectors", "gold_fuse", "gold_refiner", "pipeline", "sqlite3"):
        assert bad not in src
