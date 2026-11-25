"""坐标证据（sandbox/coord_evidence.py）测试：真实顶点、E6/E7 由 unknown 转实测、Tier 归因可复算。

跑法：python3 -m pytest sandbox/test_coord_evidence.py -q
"""
from __future__ import annotations

import csv
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox import auto_recognize as A  # noqa: E402
from sandbox import coord_evidence as E  # noqa: E402

ART = os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125")
HDR = ["layer_url", "layer_id", "state", "provider", "addr_fields_json", "lon", "lat",
       "lon_raw", "lat_raw", "wkid", "geom_type", "row_index", "sample_source"]
NH_INSIDE = [(-71.50, 43.50), (-71.46, 43.20), (-71.47, 43.21)]      # 全部落在 NH 县界内
NH_FAR = [(-71.4951, 43.5014), (-71.4551, 43.2014), (-71.4651, 43.2114)]   # 同址但偏 ~1.5km


def row(url, lon, lat, num, street, zip5="03301", geom="esriGeometryPolygon"):
    return {"layer_url": url, "layer_id": f"L-{url[-1]}", "state": "NH", "provider": "test",
            "addr_fields_json": json.dumps({"HOUSE_NUM": num, "STREET_NAME": street, "ZIP": zip5},
                                           ensure_ascii=False),
            "lon": lon, "lat": lat, "lon_raw": lon, "lat_raw": lat, "wkid": "4326",
            "geom_type": geom, "row_index": 0, "sample_source": "arcgis_query"}


def write_samples(d, name, rows):
    with open(os.path.join(d, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HDR)
        w.writeheader()
        w.writerows(rows)


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    """造 6 个 url 的样本：冲突对 / 一致对 / 孤例 / 境外坐标，跑一遍 coord_evidence.main()。"""
    d = tmp_path_factory.mktemp("coord")
    ad = ["12 Main St", "34 Elm St", "56 Oak St"]
    rows = []
    for i, (lon, lat) in enumerate(NH_INSIDE):          # 两个源同址且一致
        rows += [row("https://t/A/0", lon, lat, str(10 + i), ad[i]),
                 row("https://t/B/0", lon, lat, str(10 + i), ad[i])]
    clash = ["78 Pine Rd", "90 Cedar Rd", "11 Birch Rd"]
    for i, (lon, lat) in enumerate(NH_FAR):             # 两个源同址但差 ~1.5km → 冲突
        rows += [row("https://t/C/0", NH_INSIDE[i][0], NH_INSIDE[i][1], str(70 + i), clash[i]),
                 row("https://t/D/0", lon, lat, str(70 + i), clash[i])]
    for i, (lon, lat) in enumerate(NH_INSIDE):          # 孤例：无跨源可比
        rows += [row("https://t/F/0", lon, lat, str(90 + i), f"{90 + i} Lone Rd")]
    for lon, lat in [(-30.0, 40.0), (-31.0, 41.0), (-32.0, 42.0)]:   # 大西洋里 → 境外
        rows += [row("https://t/G/0", lon, lat, "1", "Ocean Way", geom="esriGeometryPoint")]
    write_samples(d, "NH.csv", rows)
    old = sys.argv
    try:
        sys.argv = ["coord_evidence.py", "--outdir", str(d)]
        os.environ["COORD_SAMPLES"] = str(d)
        assert E.main() == 0
    finally:
        sys.argv = old
        os.environ.pop("COORD_SAMPLES", None)
    return {r["url"]: r for r in csv.DictReader(open(d / "coord-evidence.csv", encoding="utf-8"))}, d


def test_polygon_rows_keep_real_vertices_and_never_centroid(evidence):
    ev, _ = evidence
    r = ev["https://t/A/0"]
    got = {(round(float(x), 6), round(float(y), 6)) for x, y in NH_INSIDE}
    cen = (round(sum(p[0] for p in NH_INSIDE) / 3, 6), round(sum(p[1] for p in NH_INSIDE) / 3, 6))
    assert r["geom_type"] == "polygon"                     # 面要素按面记，几何语义来自样本
    assert int(r["n_coords"]) == 3 and float(r["unique_rate"]) == 1.0
    assert cen not in got and len(got) == 3                # 三个真实顶点互不相同，且都不是质心
    src = open(os.path.join(ROOT, "sandbox", "coord_evidence.py"), encoding="utf-8").read()
    assert "centroid" not in src and "point_in_ring" in src


def test_e6_turns_from_unknown_to_measured(evidence):
    ev, _ = evidence
    assert ev["https://t/A/0"]["e6"] == "clear"            # 县界内 → 实测 clear
    assert ev["https://t/G/0"]["e6"] == "hit"              # 大西洋 → 越界命中
    assert float(ev["https://t/G/0"]["outside_share_us"]) == 1.0
    assert "no_coords" not in json.dumps(ev["https://t/A/0"])   # 不再是 unknown 糊过去


def test_e7_vote_conflict_clear_and_unknown(evidence):
    ev, _ = evidence
    assert ev["https://t/C/0"]["e7"] == "hit" and int(ev["https://t/C/0"]["n_cmp"]) == 3
    assert ev["https://t/D/0"]["e7"] == "hit"              # 冲突双向可见
    assert ev["https://t/A/0"]["e7"] == "clear"            # 同址一致 → 无冲突
    assert float(ev["https://t/C/0"]["conflict_share"]) == 1.0
    assert ev["https://t/F/0"]["e7"] == "unknown"          # 没有跨源同址 → 投不出票
    assert "n_cmp=0" in ev["https://t/F/0"]["e7_detail"]


def test_e6_e7_reach_auto_recognize_end_to_end(evidence):
    ev, d = evidence
    C = {"inv": {}, "probe": {}, "roles": {}, "ph": {}, "spatial": {},
         "coord": {u: r for u, r in ev.items()}}
    L = {"layer_id": "x", "url": "https://t/G/0", "universe": "d1", "dialect_id": "d", "provider_id": "p",
         "state": "NH", "granularity": "parcel_centroid", "geom": "", "usable": "", "reason": "template_unresolved",
         "coverage_rows": "10", "share": "0.01", "template_id": "t000000", "bits": "11111", "sampled_n": "20",
         "count": "20", "n_fields": "3", "nlike": ""}
    st = A.ev6(L, C)
    assert st[0] == "hit" and "outside_share" in st[1]      # E6 从 unknown 变实测命中
    assert A.ev7(L, C)[0] == "unknown"                      # 该 url 无同址票 → 仍 unknown（不冒充 clear）


@pytest.mark.skipif(not os.path.isfile(os.path.join(ART, "auto-recognized.csv")), reason="未跑全量")
def test_tier_attribution_is_recomputable():
    rows = list(csv.DictReader(open(os.path.join(ART, "auto-recognized.csv"), encoding="utf-8")))
    assert len(rows) == 17168
    for r in rows:                                          # 逐层重算：证据状态 → 档位，必须一致
        st = {k: r[f"{k}_state"] for k in A.EKEYS}
        assert A.tier_of(st) == r["tier"]
    t1 = [r for r in rows if r["tier"] == "tier1"]
    assert t1 and all(r["E6_state"] == "clear" for r in t1)  # Tier1 不许有未验空间
    assert all(r[f"{k}_state"] in ("clear", "na") for r in t1 for k in A.EKEYS)
    sm = json.load(open(os.path.join(ART, "summary.json"), encoding="utf-8"))
    assert sm["tiers"]["tier1"]["layers"] == len(t1)


@pytest.mark.skipif(not os.path.isfile(os.path.join(ART, "auto-recognized.csv")), reason="未跑全量")
def test_coord_evidence_covers_every_sampled_url():
    ev = {r["url"]: r for r in csv.DictReader(
        open(os.path.join(ART, "coord-evidence.csv"), encoding="utf-8"))}
    rows = list(csv.DictReader(open(os.path.join(ART, "auto-recognized.csv"), encoding="utf-8")))
    need = {r["url"] for r in rows if r["E6_state"] != "unknown" or r["E7_state"] != "unknown"}
    assert need <= set(ev)                                  # 每条实测结论都能追到坐标证据行
    assert sum(1 for r in ev.values() if r["e6"] == "clear") > 0
    assert sum(1 for r in ev.values() if r["e7"] == "hit") > 0


# ---------------------------------------------------------------- ④ 口径统一（2026-11-25）
def test_impl_is_single_source_in_engine():
    """sandbox 里不许再出现第二份 addr_key 实现，且必须从 engine.split_addr 导入。"""
    src = open(os.path.join(ROOT, "sandbox", "coord_evidence.py"), encoding="utf-8").read()
    assert "engine.split_addr" in src
    assert "def addr_key(" not in src and "def roles_of(" not in src
    assert "def street_norm(" not in src


def test_placeholder_layer_rows_are_skipped():
    """占位值层：门牌/街名是 -1 / NULL / 0 这类占位值时，必须判 skip（建不出键），不许拿占位值拼垃圾键。"""
    R = E.roles_of()
    for af in ({"HOUSE_NUM": "-1", "STREET_NAME": "MAIN ST"},
               {"HOUSE_NUM": "12", "STREET_NAME": "NULL", "ZIP": "03301"},
               {"addrnum": "0", "streetname": "ELM ST"},
               {"addrnum": "-999", "streetname": "-999", "zip": "00000"}):
        assert E.addr_key(af, R, "NH") == "", af


def test_normal_layer_key_unchanged():
    """正常层：非占位值的键必须与旧契约逐字节一致（换 impl 不放宽、也不改写法）。"""
    R = E.roles_of()
    assert E.addr_key({"HOUSE_NUM": "12", "STREET_NAME": "Main St", "ZIP": "03301"}, R, "NH") == \
        "NH|12|mainstreet|03301"
    assert E.addr_key({"HOUSE_NUM": "12A", "STREET_NAME": "Elm Road"}, R, "NH") == "NH|12A|elmroad|"
    assert E.addr_key({"STREET_NAME": "Elm Rd"}, R, "NH") == ""      # 缺门牌 → 仍构不出


def test_p1_combined_field_only_builds_key_via_split():
    """P1 形态：单字段「门牌+街名」整串 —— 老口径构不出键，新口径拆串后建键（这就是「拆串变化」的来源）。"""
    from engine.split_addr import addr_key as plain
    R = E.roles_of()
    af = {"SITE_ADDR": "1049 61ST ST", "ZIP": "90001"}
    assert plain(af, R, "CA") == ""
    assert E.addr_key(af, R, "CA") == "CA|1049|61ststreet|90001"
    for junk in ("TASSAJARA RD", "11145-0", "P O BOX 55"):          # 纯街名 / 编号 / 信箱 → 一律不建键
        assert E.addr_key({"SITE_ADDR": junk, "ZIP": "90001"}, R, "CA") == "", junk


def test_placeholder_layer_end_to_end_is_e7_unknown(tmp_path):
    """整层占位值 → n_addr_rows=0 → E7 unknown（不是 clear 冒充「无冲突」）。"""
    d = tmp_path / "ph"
    d.mkdir()
    rows = [dict(row("https://t/P/0", lon, lat, "-1", "MAIN ST")) for lon, lat in NH_INSIDE]
    write_samples(d, "PH.csv", rows)
    old = sys.argv
    try:
        sys.argv = ["coord_evidence.py", "--outdir", str(d)]
        os.environ["COORD_SAMPLES"] = str(d)
        assert E.main() == 0
    finally:
        sys.argv = old
        os.environ.pop("COORD_SAMPLES", None)
    ev = {r["url"]: r for r in csv.DictReader(open(d / "coord-evidence.csv", encoding="utf-8"))}
    r = ev["https://t/P/0"]
    assert int(r["n_addr_rows"]) == 0
    assert r["e7"] == "unknown" and "无『门牌+街名』键" in r["e7_detail"]
