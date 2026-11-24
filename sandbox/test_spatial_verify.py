"""sanity 测试：sandbox/spatial_verify.py（离线、只读仓库内 TIGER 县界与 fixtures）。

跑法：python3 -m pytest sandbox/test_spatial_verify.py -q
"""
from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox import spatial_verify as S  # noqa: E402

SQUARE = [[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]


def fixture_rows(spec):
    """测试侧读 fixture（模块里只保留 CLI 内联版，避免重复代码占行数）。"""
    rows = json.load(open(os.path.join(S.FIXTURE_DIR, spec["file"]), encoding="utf-8"))
    return [(float(r[spec["lon_key"]]), float(r[spec["lat_key"]])) for r in rows]
FUSE, P95 = S.load_thresholds()


def county(geoid="99999", ring=None):
    ring = ring or SQUARE
    return {"geoid": geoid, "rings": [ring],
            "bbox": (min(p[0] for p in ring), min(p[1] for p in ring),
                     max(p[0] for p in ring), max(p[1] for p in ring))}


# ---------------------------------------------------------------- 几何
def test_rings_of_polygon_and_multipolygon():
    assert S.rings_of({"type": "Polygon", "coordinates": [SQUARE]}) == [SQUARE]
    assert S.rings_of({"type": "MultiPolygon", "coordinates": [[SQUARE]]}) == [SQUARE]
    assert S.rings_of(None) == []
    assert S.rings_of({"type": "Polygon", "coordinates": [[[0, 0], [1, 1]]]}) == []  # <3 点丢弃


def test_point_in_ring_inside_outside_and_hole_free():
    assert S.point_in_ring(0.0, 0.0, SQUARE) is True
    assert S.point_in_ring(2.0, 0.0, SQUARE) is False
    assert S.point_in_ring(0.0, -3.0, SQUARE) is False


def test_seg_dist_one_degree_latitude_is_110_54_km():
    # 点 (0,0) 到线段 (0,1)-(0,2) 的最近距离 = 1 度纬度
    assert S.seg_dist_m(0.0, 0.0, [0.0, 1.0], [0.0, 2.0]) == pytest.approx(110540.0, rel=1e-9)


def test_seg_dist_uses_cosine_scale_for_longitude():
    # 纬度 60° 处 0.01 度经度 ≈ 111320*cos(60°)*0.01 = 556.6m
    d = S.seg_dist_m(0.01, 60.0, [0.0, 59.5], [0.0, 60.5])
    assert d == pytest.approx(111320.0 * math.cos(math.radians(60.0)) * 0.01, rel=1e-6)


def test_boundary_dist_to_square_edge():
    # 方框内 (0,0) 到最近边（±1 度经度/纬度）约为 110540m（纬度方向最近）
    d = S.boundary_dist_m(0.0, 0.0, [SQUARE])
    assert d == pytest.approx(110540.0, rel=1e-3)


def test_building_outline_distance_is_explicitly_unavailable():
    with pytest.raises(NotImplementedError):
        S.building_outline_dist_m(1, 2)


# ---------------------------------------------------------------- 数据加载
def test_load_counties_nh_has_county_fips_and_bbox():
    counties = S.load_counties("NH")
    assert len(counties) == 10
    geoids = {c["geoid"] for c in counties}
    assert "33001" in geoids and "33015" in geoids
    for c in counties:
        x0, y0, x1, y1 = c["bbox"]
        assert x0 < x1 and y0 < y1
        assert c["rings"] and len(c["rings"][0]) >= 3


def test_load_counties_missing_state_raises():
    with pytest.raises(FileNotFoundError):
        S.load_counties("ZZ")


def test_thresholds_have_value_why_source():
    import yaml
    doc = yaml.safe_load(open(S.THRESHOLDS, encoding="utf-8"))
    assert set(doc["fuse"]) >= {"max_outside_share", "max_cross_boundary_dist_m",
                                "max_top_point_share", "min_unique_coord_rate", "min_sample_rows"}
    for sec in ("fuse", "p95"):
        for name, spec in doc[sec].items():
            assert isinstance(spec["value"], (int, float)), name
            assert spec["why"].strip() and spec["source"].strip(), name
    assert set(doc["unavailable"]) == {"building_outline_distance", "zip_zcta_table"}
    assert FUSE["max_outside_share"] == 0.10 and FUSE["min_sample_rows"] == 3


def test_fixture_manifest_covers_three_sources_with_coords():
    specs = json.load(open(S.MANIFEST, encoding="utf-8"))["fixtures"]
    assert len(specs) == 3
    for spec in specs:
        rows = fixture_rows(spec)
        assert len(rows) == 25
        assert all(isinstance(x, tuple) and len(x) == 2 for x in rows)


# ---------------------------------------------------------------- 熔断判据
def test_verify_layer_green_when_all_inside():
    coords = [(0.1 * i, 0.1) for i in range(5)]
    m = S.verify_layer(coords, [county()], "99999", FUSE)
    assert m["verdict"] == "green" and m["fuse"] == []
    assert m["outside_share"] == 0.0 and m["unique_rate"] == 1.0


def test_verify_layer_fuses_on_outside_share():
    coords = [(0.0, 0.0), (5.0, 5.0), (6.0, 6.0), (0.1, 0.1)]   # 2/4 在外
    m = S.verify_layer(coords, [county()], "99999", FUSE)
    assert "outside_share" in m["fuse"] and m["verdict"] == "fuse"
    assert m["outside_share"] == 0.5
    assert m["max_cross_boundary_dist_m"] > 0


def test_verify_layer_fuses_on_single_point_cluster():
    coords = [(0.0, 0.0)] * 9 + [(0.5, 0.5)]
    m = S.verify_layer(coords, [county()], "99999", FUSE)
    assert m["top_point_share"] == 0.9 and "coord_cluster" in m["fuse"]
    assert "coord_dup" not in m["fuse"]  # 唯一率 0.2 > min_unique_coord_rate 0.05
    assert m["unique_rate"] == 0.2


def test_verify_layer_unavailable_when_sample_too_small():
    m = S.verify_layer([(0.0, 0.0), (0.1, 0.1)], [county()], "99999", FUSE)
    assert m["verdict"] == "unavailable"
    assert "min_sample_rows" in m["note"]


def test_verify_layer_unavailable_when_fips_missing():
    m = S.verify_layer([(0.0, 0.0)] * 3, [county("11111")], "99999", FUSE)
    assert m["verdict"] == "unavailable" and "县界缺" in m["note"]


def test_fixture_layers_are_green_and_inside_declared_county():
    specs = json.load(open(S.MANIFEST, encoding="utf-8"))["fixtures"]
    for spec in specs:
        m = S.verify_layer(fixture_rows(spec), S.load_counties(spec["state"]),
                           spec["county_fips"], FUSE)
        assert m["verdict"] == "green", (spec["name"], m)
        assert m["outside_share"] == 0.0
        assert m["unique_rate"] == 1.0


# ---------------------------------------------------------------- 层内统计离群
def test_null_rate_jumps_flags_layer_where_field_disappears():
    rows = []
    for i in range(12):  # 同字段在 12 层里 11 层满值、1 层为 0
        rows.append({"layer": f"L{i}", "field": "house_number", "rate": "0.0" if i == 3 else "1.0"})
    rows.append({"layer": "L0", "field": "rare_field", "rate": "0.0"})  # 只有 1 层 → 不参判
    jumps = S.null_rate_jumps(rows)
    assert "L3" in jumps and jumps["L3"] == ["house_number"]
    assert len(jumps) == 1


def test_null_rate_jumps_ignores_low_median_field():
    rows = [{"layer": f"L{i}", "field": "sparse", "rate": "0.0" if i else "0.4"} for i in range(12)]
    assert S.null_rate_jumps(rows) == {}


def test_null_rate_jumps_tolerates_missing_values():
    assert S.null_rate_jumps([{"layer": "L", "field": "", "rate": ""}]) == {}


# ---------------------------------------------------------------- CLI 端到端
def test_main_writes_findings_csv(tmp_path, monkeypatch, capsys):
    out = tmp_path / "sf.csv"
    monkeypatch.setattr(sys, "argv", ["spatial_verify.py", "--out", str(out), "--seed", "7"])
    assert S.main() == 0
    assert "null_rate_jump layers=" in capsys.readouterr().out
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    fixtures = [r for r in rows if r["kind"] == "fixture_layer"]
    assert len(fixtures) == 3
    assert all(r["verdict"] == "green" for r in fixtures)
    assert all(r["note"].endswith("building_outline=unavailable") for r in fixtures)
    jumps = [r for r in rows if r["kind"] == "null_rate_jump"]
    assert jumps and len(jumps) == len(S.null_rate_jumps(
        list(csv.DictReader(open(S.LOCAL_FIELDS, encoding="utf-8")))))
    assert list(rows[0]) == list(S.FIELDS)


def test_cli_entrypoint_runs():
    """真 CLI 入口（if __name__ == '__main__'）也要能跑。"""
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "sandbox", "spatial_verify.py"),
                           "--out", os.devnull], capture_output=True, text=True)
    assert proc.returncode == 0 and "wrote" in proc.stdout
