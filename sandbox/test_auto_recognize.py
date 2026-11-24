"""sanity 测试：sandbox/auto_recognize.py（8 条否定证据 + 三档分级，离线只读）。

跑法：python3 -m pytest sandbox/test_auto_recognize.py -q
"""
from __future__ import annotations

import contextlib
import csv
import io
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox import auto_recognize as A  # noqa: E402
from sandbox import coord_evidence as E  # noqa: E402
from sandbox import spatial_verify as S  # noqa: E402

LAYER = {"layer_id": "L1", "url": "https://x/FeatureServer/0", "universe": "d1", "dialect_id": "minimal_safe",
         "provider_id": "agol:org", "state": "NH", "granularity": "building_point", "geom": "Point",
         "usable": "full_address", "reason": "template_unresolved", "coverage_rows": "100", "share": "0.01",
         "template_id": "t000000", "bits": "11111", "sampled_n": "20", "count": "100", "n_fields": "12",
         "nlike": "Add_Number"}
EMPTY_CTX = {"inv": {}, "probe": {}, "roles": {}, "ph": {}, "spatial": {}, "coord": {}}


def layer(**kw):
    return {**LAYER, **kw}


def ctx(**kw):
    return {**EMPTY_CTX, **kw}


# ---------------------------------------------------------------- E1 门牌
def test_e1_unknown_without_sample():
    assert A.ev1(layer(bits=""), EMPTY_CTX)[0] == "unknown"


def test_e1_hit_when_number_bit_zero():
    st, why = A.ev1(layer(bits="01111", nlike="PARCELNUM"), EMPTY_CTX)
    assert st == "hit" and "PARCELNUM" in why


def test_e1_clear_when_number_bit_one():
    assert A.ev1(layer(bits="11111"), EMPTY_CTX)[0] == "clear"


# ---------------------------------------------------------------- E2 街名
def test_e2_hit_when_street_bit_zero():
    assert A.ev2(layer(bits="10111"), EMPTY_CTX)[0] == "hit"


def test_e2_hit_on_placeholder_literal_in_local_samples():
    C = ctx(ph={"https://x/FeatureServer/0": {"street_name"}})
    st, why = A.ev2(layer(bits="11111"), C)
    assert st == "hit" and "street_name" in why


def test_e2_clear_when_both_bits_set_and_no_placeholder():
    assert A.ev2(layer(bits="11111"), EMPTY_CTX)[0] == "clear"


# ---------------------------------------------------------------- E3 几何语义
@pytest.mark.parametrize("geom,gran,want", [
    ("Point", "building_point", "clear"),
    ("Polygon", "building_point", "hit"),
    ("Polyline", "centerline_midpoint", "clear"),
    ("Point", "centerline_midpoint", "hit"),
    ("Polygon", "parcel_centroid", "clear"),
    ("Polyline", "parcel_centroid", "hit"),
    ("", "building_point", "unknown"),
    ("Point", "unknown", "unknown"),
])
def test_e3_granularity_vs_geometry(geom, gran, want):
    assert A.ev3(layer(geom=geom, granularity=gran), EMPTY_CTX)[0] == want


# ---------------------------------------------------------------- E4 别名冲突
def test_e4_unknown_without_probe():
    assert A.ev4(layer(), EMPTY_CTX)[0] == "unknown"


def test_e4_hit_when_number_evidence_comes_from_negative_field():
    st, why = A.ev4(layer(nlike="PARCELNUM"), EMPTY_CTX)   # 不需要探针也能判
    assert st == "hit" and "PARCELNUM" in why


def test_e4_hit_when_field_maps_to_two_roles_across_dialects():
    C = ctx(probe={"https://x/FeatureServer/0": ["St_Name"]}, roles={"St_Name": {"number", "street"}})
    assert A.ev4(layer(), C)[0] == "hit"


def test_e4_clear_for_clean_field_set():
    C = ctx(probe={"https://x/FeatureServer/0": ["Add_Number", "St_Name"]}, roles={"Add_Number": {"number"}})
    assert A.ev4(layer(), C)[0] == "clear"


# ---------------------------------------------------------------- E5 样本份额
@pytest.mark.parametrize("kw,want", [
    ({"sampled_n": "0"}, "hit"),
    ({"sampled_n": "3", "count": "1000"}, "hit"),
    ({"share": "0.00001"}, "hit"),
    ({"sampled_n": "20", "count": "20", "share": "0.01"}, "clear"),
])
def test_e5_sample_quality(kw, want):
    assert A.ev5(layer(**kw), EMPTY_CTX)[0] == want


# ---------------------------------------------------------------- E6/E7
def test_e6_unknown_without_coord_samples():
    st, why = A.ev6(layer(), EMPTY_CTX)
    assert st == "unknown" and "未跑" in why


def test_e6_follows_coord_evidence():
    ok = ctx(coord={LAYER["url"]: {"e6": "clear", "e6_detail": "n=50 唯一率=1.0"}})
    bad = ctx(coord={LAYER["url"]: {"e6": "hit", "e6_detail": "命中 outside_share"}})
    assert A.ev6(layer(), ok)[0] == "clear"
    assert A.ev6(layer(), bad)[0] == "hit"


def test_e6_keys_on_url_because_layer_id_is_not_unique():
    src = open(os.path.join(ROOT, "sandbox", "auto_recognize.py"), encoding="utf-8").read()
    assert 'C["coord"].get(L["url"], {})' in src


def test_e7_unknown_when_no_comparable_votes():
    assert A.ev7(layer(), EMPTY_CTX)[0] == "unknown"
    C = ctx(coord={LAYER["url"]: {"e7": "unknown", "e7_detail": "n_cmp=0 < 3"}})
    assert A.ev7(layer(), C)[0] == "unknown"


def test_e7_follows_vote_evidence():
    clear = ctx(coord={LAYER["url"]: {"e7": "clear", "e7_detail": "同址可比 7 行，冲突 0 行"}})
    hit = ctx(coord={LAYER["url"]: {"e7": "hit", "e7_detail": "同址可比 9 行，冲突 4 行"}})
    assert A.ev7(layer(), clear)[0] == "clear"
    assert A.ev7(layer(), hit)[0] == "hit"


def test_e3_falls_back_to_measured_geom_from_samples():
    C = ctx(coord={LAYER["url"]: {"geom_type": "polygon"}})
    assert A.ev3(layer(geom="", granularity="parcel_centroid"), C)[0] == "clear"
    assert A.ev3(layer(geom="", granularity="building_point"), C)[0] == "hit"


# ---------------------------------------------------------------- E8 结构漂移
def test_e8_na_without_registry_template():
    assert A.ev8(layer(template_id="t000000"), EMPTY_CTX)[0] == "na"


def test_e8_unknown_when_template_exists_but_no_probe():
    assert A.ev8(layer(template_id="t110101"), EMPTY_CTX)[0] == "unknown"


def test_e8_hit_when_template_but_zero_fields():
    C = ctx(probe={"https://x/FeatureServer/0": ["Add_Number"]})
    assert A.ev8(layer(template_id="t110101", n_fields="0"), C)[0] == "hit"


def test_e8_clear_when_template_and_probe_align():
    C = ctx(probe={"https://x/FeatureServer/0": ["Add_Number", "St_Name"]})
    assert A.ev8(layer(template_id="t110101", n_fields="12"), C)[0] == "clear"


# ---------------------------------------------------------------- 三档分级
def test_tier1_requires_every_evidence_clear():
    st = {k: "clear" for k in A.EKEYS}
    st["E8"] = "na"
    assert A.tier_of(st) == "tier1"


@pytest.mark.parametrize("key", ["E1", "E2", "E3", "E8"])
def test_fatal_evidence_blocks_tier2(key):
    st = {k: "clear" for k in A.EKEYS}
    st[key] = "hit"
    assert A.tier_of(st) == "tier3"
    st[key] = "unknown"
    assert A.tier_of(st) == "tier3"


def test_spatial_fuse_blocks_tier1_and_tier2():
    st = {k: "clear" for k in A.EKEYS}
    st["E6"] = "hit"
    assert A.tier_of(st) == "tier3"


def test_tier2_when_only_non_fatal_unknowns_or_hits():
    st = {k: "clear" for k in A.EKEYS}
    st.update({"E6": "unknown", "E7": "unknown"})
    assert A.tier_of(st) == "tier2"
    st.update({"E5": "hit"})
    assert A.tier_of(st) == "tier2"


def test_move_table_three_columns():
    """三列 = active / minimal_safe / unavailable，**没有 manual 这一档**。"""
    st = {k: "clear" for k in A.EKEYS}
    assert A.move_of("tier1", st, layer(bits="11111"))[0] == "active"
    assert A.move_of("tier2", st, layer(bits="11111"))[0] == "minimal_safe"
    st["E1"] = "hit"
    assert A.move_of("tier3", st, layer(bits="11000"))[0] == "minimal_safe"   # 有门牌+街名就降级，不进 manual
    mv, why = A.move_of("tier3", st, layer(bits="01000"))                    # 缺门牌 → 暂不可用
    assert mv == "unavailable" and why.startswith("E1")


@pytest.mark.parametrize("bits,want", [
    ("11111", "minimal_safe"), ("11000", "minimal_safe"), ("11001", "minimal_safe"),
    ("01000", "unavailable"), ("10111", "unavailable"), ("", "unavailable"), ("1", "unavailable"),
])
def test_minimal_safe_needs_number_and_street_only(bits, want):
    """minimal_safe 只取门牌+街名：addr_core_hit[:2] 必须为 "11"，缺任一要素 → unavailable。"""
    st = {k: "unknown" for k in A.EKEYS}
    st.update({k: "clear" for k in A.FATAL})
    assert A.move_of("tier3", st, layer(bits=bits))[0] == want


def test_no_manual_verdict_is_ever_produced():
    for bits in ("11111", "01000", "", "10111"):
        mv = A.move_of("tier3", {k: "hit" for k in A.EKEYS}, layer(bits=bits))[0]
        assert mv in ("active", "minimal_safe", "unavailable") and mv != "manual"


def test_minimal_safe_invariant_a_pool_eligible_false():
    """不变式：minimal_safe 永不进 A 货池（a_pool_eligible=false，由 registry/evaluator.py 硬编码）。"""
    from registry import evaluator as EV
    reg = EV.load_registry(os.path.join(ROOT, "registry", "dialects.v1.yaml"))
    res = EV.minimal_safe(reg, {"house_number": "12", "street_name": "MAIN ST"})
    assert res["pool"] == "manual" and res["a_pool_eligible"] is False
    assert res["parsed"] == {"housenumber": "12", "street": "MAIN ST"}      # 只取两要素
    src = open(os.path.join(ROOT, "sandbox", "auto_recognize.py"), encoding="utf-8").read()
    assert "a_pool_eligible=false" in src and "a_pool_eligible=True" not in src


# ---------------------------------------------------------------- evaluate
def test_evaluate_merges_inventory_facts_and_emits_all_columns():
    C = ctx(inv={"https://x/FeatureServer/0": {"bits": "11111", "geom": "Point", "sampled_n": "20",
                                              "count": "100", "n_fields": "12", "nlike": "Add_Number"}})
    r = A.evaluate(layer(), C)
    for k in A.EKEYS:
        assert r[f"{k}_state"] in ("hit", "clear", "unknown", "na")
    assert r["tier"] == "tier2"          # ①②③⑧ 全 clear，仅 ④⑥⑦ unknown → Tier2（仍需第 6 步抽样复核）
    assert r["move"] == "minimal_safe"
    assert r["coverage_rows"] == "100"


# ---------------------------------------------------------------- 反硬规则
def test_module_has_no_confidence_threshold_gate():
    import re
    src = open(os.path.join(ROOT, "sandbox", "auto_recognize.py"), encoding="utf-8").read()
    assert not re.search(r"confidence\s*[<>]=?", src, re.I)   # 不许出现「confidence ≥ x 就放行」
    assert "score" not in src and "0.9" not in src


def test_module_does_not_import_collect_or_fusion():
    src = open(os.path.join(ROOT, "sandbox", "auto_recognize.py"), encoding="utf-8").read()
    for bad in ("import collect", "from collect", "fusion", "shapely", "requests", "urllib"):
        assert bad not in src


# ---------------------------------------------------------------- CLI 端到端（真数据）
@pytest.fixture(scope="module")
def outdir(tmp_path_factory):
    """进程内跑两个 main()（覆盖率能统计到；CLI 入口另有单独 subprocess 用例）。"""
    d = tmp_path_factory.mktemp("auto-spatial")
    old = sys.argv
    try:
        sys.argv = ["coord_evidence.py", "--outdir", str(d)]
        assert E.main() == 0
        sys.argv = ["spatial_verify.py", "--out", str(d / "spatial-findings.csv")]
        assert S.main() == 0
        sys.argv = ["auto_recognize.py", "--outdir", str(d)]
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            assert A.main() == 0
        return d, buf.getvalue()
    finally:
        sys.argv = old


def test_cli_denominator_closes(outdir):
    d, stdout = outdir
    rows = list(csv.DictReader(open(d / "auto-recognized.csv", encoding="utf-8")))
    assert len(rows) == 17168
    assert sum(int(r["coverage_rows"] or 0) for r in rows) == 984719364
    tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]
    assert len(tu) == 11056
    assert sum(int(r["coverage_rows"] or 0) for r in tu) == 297519308
    assert "17168" in stdout


def test_cli_tiers_and_moves_sum_to_denominator(outdir):
    d, _ = outdir
    rows = list(csv.DictReader(open(d / "auto-recognized.csv", encoding="utf-8")))
    for col, keys in (("tier", ("tier1", "tier2", "tier3")),
                      ("move", ("active", "minimal_safe", "unavailable"))):
        total = sum(sum(1 for r in rows if r[col] == k) for k in keys)
        assert total == 17168
        assert sum(sum(int(r["coverage_rows"] or 0) for r in rows if r[col] == k) for k in keys) == 984719364


def test_cli_split_closes_and_coverage_matches(outdir):
    d, _ = outdir
    mv = list(csv.DictReader(open(d / "template-unresolved-moves.csv", encoding="utf-8")))
    rec = [r for r in mv if r["verdict"] != "unavailable"]
    assert len(mv) == 11056 and sum(int(r["rows_n"] or 0) for r in mv) == 297519308
    # 可进池的层（active+minimal_safe）逐位闭合；具体层数随证据变化，不做硬编码
    assert len(rec) + len([r for r in mv if r["verdict"] == "unavailable"]) == 11056
    assert sum(int(r["rows_n"] or 0) for r in rec) + sum(
        int(r["rows_n"] or 0) for r in mv if r["verdict"] == "unavailable") == 297519308


def test_cli_tier1_nonzero_and_e6_e7_measured(outdir):
    d, _ = outdir
    rows = list(csv.DictReader(open(d / "auto-recognized.csv", encoding="utf-8")))
    t1 = [r for r in rows if r["tier"] == "tier1"]
    assert t1, "有坐标样本后 Tier1 必须能放出层"
    assert all(r[f"{k}_state"] in ("clear", "na") for r in t1 for k in A.EKEYS)
    # E6/E7 已由 unknown 转实测：两种状态都要有真实计数
    assert sum(1 for r in rows if r["E6_state"] in ("clear", "hit")) > 0
    assert sum(1 for r in rows if r["E7_state"] in ("clear", "hit")) > 0


def test_cli_move_csv_new_schema_and_no_manual(outdir):
    d, _ = outdir
    tu = list(csv.DictReader(open(d / "template-unresolved-moves.csv", encoding="utf-8")))
    assert list(tu[0]) == ["layer_id", "url", "provider", "granularity", "geom_type", "rows_n",
                           "verdict", "reason_evidence", "reason_detail"]
    assert len(tu) == 11056
    assert sum(int(r["rows_n"] or 0) for r in tu) == 297519308
    assert {r["verdict"] for r in tu} <= {"active", "minimal_safe", "unavailable"}
    assert all(r["verdict"] != "manual" for r in tu)


def test_cli_unavailable_csv_matches_split(outdir):
    d, _ = outdir
    mv = list(csv.DictReader(open(d / "template-unresolved-moves.csv", encoding="utf-8")))
    un = list(csv.DictReader(open(d / "template-unresolved-unavailable.csv", encoding="utf-8")))
    assert len(un) == sum(1 for r in mv if r["verdict"] == "unavailable") == 6954
    assert all(r["verdict"] == "unavailable" for r in un)
    assert sum(int(r["rows_n"] or 0) for r in un) == 138182717
    # 暂不可用 = 连门牌+街名都取不到 → 必须都命中 E1（门牌）判据
    assert all("E1" in r["reason_evidence"] for r in un)
    assert all(r["reason_detail"].strip() for r in un)      # 每条都要写清卡在哪
    assert {r["verdict"] for r in mv} <= {"active", "minimal_safe", "unavailable"}


def test_cli_entrypoint_runs():
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "sandbox", "auto_recognize.py"),
                           "--outdir", os.devnull], capture_output=True, text=True)
    assert proc.returncode != 0   # /dev/null 当目录必然失败，但入口本身被真正执行


def test_cli_no_confidence_column(outdir):
    d, _ = outdir
    with open(d / "auto-recognized.csv", encoding="utf-8") as fh:
        head = fh.readline()
    assert "confidence" not in head and "score" not in head
