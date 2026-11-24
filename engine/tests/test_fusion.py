"""融合层单测：按 addrkey v3 去重、源优先级、坐标冲突、Tier 取最优、分级落库边界。"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine import outlet_clean as oc  # noqa: E402
from engine.fusion import Fusion  # noqa: E402

CFG = {"priority": {"granit": 10, "nad": 20, "overture": 30, "tiger": 40, "oa": 50, "dialect_layer": 5},
       "tier_rank": {"tier1": 1, "tier2": 2, "tier3": 3, "unrated": 9},
       "grades": {"S": ["number", "street", "city", "state", "zip5", "point"],
                  "A": ["number", "street", "state", "zip5", "point_any"],
                  "B": ["number", "street", "state"],
                  "C": ["street"]},
       "min_grade": "C", "coord_conflict_m": 100,
       "addrkey": {"version": "v3", "include_unit": True}}


def rec(fam, number="58", street="Barbara Drive", city="Alton", state="NH", zip_="03249",
        lon=-71.30, lat=43.47, unit="", precision="address_point", interp=False):
    return oc.clean({"number": number, "street": street, "city": city, "state": state,
                     "zip": zip_, "lon": lon, "lat": lat, "unit": unit, "source_id": fam,
                     "source_family": fam, "id": f"{fam}-1"},
                    {"precision": precision, "is_interpolated": interp})


@pytest.fixture()
def fus(tmp_path):
    f = Fusion(str(tmp_path / "t.sqlite"), CFG)
    yield f
    f.db.close()


def rows(f):
    return {r[0]: r for r in f.db.execute("SELECT addrkey, number, lon, lat, tier, grade, n_sources, "
                                          "source_family, coord_conflict, contributors FROM fused")}


def test_same_address_two_sources_merges_to_one_row(fus):
    fus.add(rec("nad"), "unrated")
    fus.add(rec("oa"), "unrated")
    r = rows(fus)
    assert len(r) == 1
    k = list(r)[0]
    assert r[k][6] == 2 and r[k][7] == "nad"          # 优先级小的保留（nad 20 < oa 50）
    assert len(json.loads(r[k][9])) == 2              # provenance 两条都留


def test_different_address_not_merged(fus):
    fus.add(rec("nad", number="58"), "unrated")
    fus.add(rec("nad", number="60"), "unrated")
    assert len(rows(fus)) == 2


def test_priority_overrides_even_if_later(fus):
    fus.add(rec("oa"), "unrated")
    fus.add(rec("granit", city="ALTON"), "unrated")   # granit 10 < oa 50 → 应替换
    r = rows(fus)
    k = list(r)[0]
    assert r[k][7] == "granit" and r[k][6] == 2


def test_coord_conflict_flagged_but_keeps_priority_source(fus):
    fus.add(rec("nad", lon=-71.30, lat=43.47), "unrated")
    fus.add(rec("oa", lon=-71.31, lat=43.47), "unrated")     # 约 800m 差
    r = rows(fus)
    k = list(r)[0]
    assert r[k][8] == 1                    # coord_conflict=1
    assert abs(r[k][2] + 71.30) < 1e-6     # 仍保留 nad 的坐标


def test_tier_takes_best_contributor(fus):
    fus.add(rec("nad"), "tier3")
    fus.add(rec("oa"), "tier1")
    r = rows(fus)
    assert list(r.values())[0][4] == "tier1"


def test_grade_assigned_and_low_grade_dropped(fus):
    fus.add(rec("nad"), "tier1")                       # S
    fus.add(rec("nad", number="9", street="", city=""), "unrated")   # 只剩 state → X（丢）
    r = rows(fus)
    assert list(r.values())[0][5] == "S"
    assert fus.stats["low_grade"] == 1
    assert len(r) == 1


def test_unkeyed_goes_to_unkeyed_table(fus):
    # 有街名但没门牌 → 不可键（grade C 仍入库），进 unkeyed 表而不是被静默丢弃
    fus.add(rec("nad", number="", city=""), "unrated")
    assert fus.stats["unkeyed"] == 1
    assert fus.db.execute("SELECT COUNT(*) FROM unkeyed").fetchone()[0] == 1
    assert len(rows(fus)) == 0


def test_tier_grade_grid_and_export(fus, tmp_path):
    fus.add(rec("nad"), "tier1")
    fus.add(rec("oa", number="60"), "tier2")
    s = fus.summaries()
    assert s["deduped_rows"] == 2 and s["by_tier_grade"]["tier1"]["S"] == 1
    n = fus.export(str(tmp_path / "g.ndjson.gz"))
    assert n == 2
