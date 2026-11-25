"""第 7 步口径单测：分档双键 join、同 layer_id 不串层、面线取顶点、插值不进 S、NH 交叉核对。"""
from __future__ import annotations

import csv
import json
import math
import os
import struct
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine import inlet  # noqa: E402
from engine import outlet_clean as oc  # noqa: E402
from engine import pilot  # noqa: E402
from engine.crosscheck import crosscheck_pairs  # noqa: E402
from engine.fusion import Fusion  # noqa: E402

CFG = {"priority": {"dialect_layer": 5, "granit": 10, "nad": 20, "overture": 30, "tiger": 40, "oa": 50},
       "tier_rank": {"tier1": 1, "tier2": 2, "tier3": 3, "unrated": 9},
       "grades": {"S": ["number", "street", "city", "state", "zip5", "point"],
                  "A": ["number", "street", "state", "zip5", "point_any"],
                  "B": ["number", "street", "state"], "C": ["street"]},
       "min_grade": "C", "coord_conflict_m": 100, "addrkey": {"version": "v3", "include_unit": True}}
TIER_COLS = ["layer_id", "url", "dialect_id", "state", "rows_n", "tier", "granularity", "geom_type"]


def write_tiers(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=TIER_COLS)
        w.writeheader()
        w.writerows(rows)
    return str(path)


def test_tier_join_is_url_plus_dialect(tmp_path):
    """① 同一 url 两个 dialect_id 各自成表项，互相不覆盖；tier_for 记为 ambiguous 但不静默合并。"""
    p = write_tiers(tmp_path / "t.csv", [
        {"layer_id": "L0", "url": "https://x/0", "dialect_id": "dA", "state": "DE", "rows_n": "10",
         "tier": "tier2", "granularity": "building_point", "geom_type": "point"},
        {"layer_id": "L0", "url": "https://x/0", "dialect_id": "dB", "state": "DE", "rows_n": "5",
         "tier": "tier3", "granularity": "parcel_centroid", "geom_type": "polygon"},
        {"layer_id": "L1", "url": "", "dialect_id": "dC", "state": "DE", "rows_n": "1",
         "tier": "tier1", "granularity": "building_point", "geom_type": "point"},
    ])
    t = pilot.load_tiers({"repo": {"tiers": p}})
    assert len(t["pairs"]) == 2 and t["skipped_no_url"] == 1     # "" 键不入表
    assert (("https://x/0", "dA") in t["pairs"]) and (("https://x/0", "dB") in t["pairs"])
    tier, basis, amb = pilot.tier_for("https://x/0", t)
    assert tier == "tier2" and basis == "https://x/0|dA" and amb is True
    assert pilot.tier_for("https://x/none", t) == ("unrated", "", False)
    assert pilot.tier_for("", t) == ("unrated", "", False)        # 空 url 不许命中任何层


def test_same_layer_id_different_url_not_merged(tmp_path):
    """② layer_id 不是主键：同 layer_id 不同 url 是两层，分别取自己的档位。"""
    p = write_tiers(tmp_path / "t.csv", [
        {"layer_id": "MapServer/1", "url": "https://a/1", "dialect_id": "d1", "state": "IA", "rows_n": "7",
         "tier": "tier2", "granularity": "x", "geom_type": "point"},
        {"layer_id": "MapServer/1", "url": "https://b/1", "dialect_id": "d2", "state": "IA", "rows_n": "9",
         "tier": "tier3", "granularity": "y", "geom_type": "polygon"},
    ])
    t = pilot.load_tiers({"repo": {"tiers": p}})
    assert len(t["pairs"]) == 2
    assert pilot.tier_for("https://a/1", t)[0] == "tier2"
    assert pilot.tier_for("https://b/1", t)[0] == "tier3"


def _wkb(typ, payload=b""):
    return b"\x01" + struct.pack("<I", typ) + payload


def _poly(rings):
    b = struct.pack("<I", len(rings))
    for r in rings:
        b += struct.pack("<I", len(r)) + b"".join(struct.pack("<dd", *p) for p in r)
    return _wkb(3, b)


def _line(pts):
    return _wkb(2, struct.pack("<I", len(pts)) + b"".join(struct.pack("<dd", *p) for p in pts))


def test_polygon_polyline_take_real_vertex_not_centroid():
    """③ 面/线取真实顶点（rings[0][0] / paths[0][0]），既不是质心也不是「不给坐标」。"""
    ring = [(10.0, 20.0), (12.0, 20.0), (12.0, 22.0), (10.0, 22.0), (10.0, 20.0)]
    lon, lat, kind = inlet.wkb_vertex(_poly([ring]))
    assert (lon, lat, kind) == (10.0, 20.0, "polygon")
    assert (round(sum(p[0] for p in ring[:-1]) / 4, 3), round(sum(p[1] for p in ring[:-1]) / 4, 3)) != (lon, lat)
    assert inlet.wkb_vertex(_line([(1.5, 2.5), (3.5, 4.5)])) == (1.5, 2.5, "polyline")
    r = oc.clean({"number": "1", "street": "Main", "state": "NH", "lon": "10.0", "lat": "20.0",
                  "geom_type": "esriGeometryPolygon"}, {"precision": "mixed"})
    assert (r["geom_type"], r["point_kind"], r["pos_estimated"]) == ("polygon", "vertex", False)
    r2 = oc.clean({"number": "1", "street": "Main", "state": "NH", "lon": "10.0", "lat": "20.0"},
                  {"precision": "mixed"})
    assert r2["geom_type"] == "unknown" and r2["point_kind"] == "point"     # 没实测几何也不许丢坐标


def test_interpolated_never_grade_s(tmp_path):
    """④ 插值位置 pos_estimated=true、point_kind=interpolated，且永远拿不到 S（S 只认真实点）。"""
    f = Fusion(str(tmp_path / "s.sqlite"), CFG)
    rec = oc.clean({"number": "58", "street": "Barbara Drive", "city": "Alton", "state": "NH", "zip": "03249",
                    "lon": -71.3, "lat": 43.47, "source_id": "nh_tiger", "source_family": "tiger"},
                   {"precision": "range_interpolation", "is_interpolated": True})
    assert rec["pos_estimated"] is True and rec["point_kind"] == "interpolated"
    assert f.grade(rec) == "A"
    f.add(rec, "tier2", "u|d")
    s = f.summaries()
    assert s["s_with_pos_estimated"] == 0 and s["pos_estimated_rows"] == 1
    assert s["by_point_kind"].get("interpolated") == 1
    f.db.close()


def test_real_point_beats_interpolation_even_if_lower_priority(tmp_path):
    """④b 插值永不能盖掉真实点：先入 TIGER 插值(40)，后来的 OA 真实点(50) 必须替换它。"""
    f = Fusion(str(tmp_path / "p.sqlite"), CFG)
    interp = oc.clean({"number": "9", "street": "Elm St", "city": "Alton", "state": "NH", "zip": "03249",
                       "lon": -71.30, "lat": 43.47, "source_id": "nh_tiger", "source_family": "tiger"},
                      {"precision": "range_interpolation", "is_interpolated": True})
    real = oc.clean({"number": "9", "street": "Elm St", "city": "Alton", "state": "NH", "zip": "03249",
                     "lon": -71.3009, "lat": 43.4709, "source_id": "oa", "source_family": "oa"},
                    {"precision": "address_point"})
    f.add(interp, "tier2", "u|d")
    f.add(real, "tier2", "u|d")
    row = f.db.execute("SELECT source_family, pos_estimated, point_kind, n_sources, contributors FROM fused").fetchone()
    assert row[0] == "oa" and row[1] == 0 and row[2] == "point" and row[3] == 2
    assert len(json.loads(row[4])) == 2            # 冲突/被盖掉的 provenance 都留着
    f.db.close()


def test_nh_crosscheck_distance_and_conflict_counts():
    """⑤ 交叉核对：同 addrkey 下 GRANIT 点 vs TIGER 插值点的最小距离、>100m 冲突、只插值覆盖数。"""
    def prov(fam, lon, lat, interp=False):
        return json.dumps([{"src": f"nh_{fam}", "fam": fam, "lon": lon, "lat": lat, "interp": interp,
                            "pos_estimated": interp}])
    near = prov("granit", -71.30, 43.47) + prov("tiger", -71.3009, 43.4709, True)   # ≈110m? 见下断言
    rows = [
        ("k1", json.dumps(json.loads(prov("granit", -71.30, 43.47)) + json.loads(prov("tiger", -71.30, 43.47, True)))),
        ("k2", json.dumps(json.loads(prov("granit", -71.30, 43.47)) + json.loads(prov("tiger", -71.33, 43.47, True)))),
        ("k3", prov("tiger", -71.30, 43.47, True)),
        ("k4", prov("granit", -71.30, 43.47)),
    ]
    r = crosscheck_pairs(rows, 100.0)
    assert r["both_sources_keys"] == 2 and r["only_interpolated_keys"] == 1 and r["real_point_keys"] == 3
    assert r["compared_keys"] == 2 and r["conflict_keys"] == 1 and r["conflict_share"] == 0.5
    d_k2 = 0.03 * 111320.0 * math.cos(math.radians(43.47))     # 经度差 0.03° ≈ 2.4km
    assert r["dist_max_m"] == pytest.approx(d_k2, rel=0.02) and r["dist_p50_m"] < 3000
    assert near  # 仅为可读性保留构造用变量
