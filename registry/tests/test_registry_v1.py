"""注册表 v1 的离线测试（不联网、不读 dist、不跑扫描）。

跑法：`python3 -m pytest registry/tests -q`

覆盖：
  · 全部 golden cases（真实样值 + 真实上游字段名）
  · 两个插件的自带 golden cases
  · minimal_safe 的硬约束（pool=manual、a_pool_eligible=false，永不进 A 货池）
  · validate.py 的正向 + **反向**（缺 golden case / 缺粒度 / 缺 CRS 必须 exit 1）
  · 分组产物（dialect-assignment.csv）的分母闭合与「无 other/misc 兜底桶」
  · 人工队列按 score 降序、周切片不超 weekly_cap_layers
"""
from __future__ import annotations

import copy
import csv
import os
import subprocess
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.dirname(HERE)
ROOT = os.path.dirname(REG)
YAML_PATH = os.path.join(REG, "dialects.v1.yaml")
DIAL = os.path.join(ROOT, "analysis", "dialect-20261124")
sys.path.insert(0, ROOT)
sys.path.insert(0, REG)
sys.path.insert(0, os.path.join(REG, "plugins"))

import evaluator  # noqa: E402
import validate as validate_mod  # noqa: E402
import split_range  # noqa: E402
import split_unit  # noqa: E402


@pytest.fixture(scope="module")
def reg():
    return evaluator.load_registry(YAML_PATH)


@pytest.fixture(scope="module")
def doc():
    with open(YAML_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ------------------------------------------------------------------ 结构
def test_schema_and_denominator(doc):
    assert doc["schema"] == "dialects.v1/2026-11-24"
    den = doc["denominator"]
    assert den["d1_remote"] == 16010 and den["d2_local"] == 1158 and den["total"] == 17168
    assert den["d1_remote"] + den["d2_local"] == den["total"]


def test_every_dialect_has_3_to_5_cases(doc):
    by_id = {g["id"]: g for g in doc["golden_cases"]}
    for d in doc["dialects"]:
        assert 3 <= len(d["golden_cases"]) <= 5, d["id"]
        for gid in d["golden_cases"]:
            assert by_id[gid]["dialect_id"] == d["id"]


def test_granularity_and_crs_present(doc):
    for d in doc["dialects"]:
        assert d["geom"]["granularity"] in validate_mod.GRANULARITY_ENUM
        assert d["crs"]["epsg"] not in (None, "")
        assert d["crs"]["basis"] in ("declared", "declared_wkt", "inferred", "unknown")
        assert set(d["mapping"]) == validate_mod.MAPPING_KEYS


# ------------------------------------------------------------------ golden cases
@pytest.mark.parametrize("gc", [pytest.param(g, id=g["id"])
                                for g in yaml.safe_load(open(YAML_PATH, encoding="utf-8"))["golden_cases"]])
def test_golden_case_maps_exactly(reg, gc):
    d = evaluator.dialect_of(reg, gc["dialect_id"])
    assert d is not None
    got = evaluator.map_row(d, gc["input"])
    for k, v in gc["expect"].items():
        assert got.get(k) == v, f"{gc['id']}: {k} 期望 {v!r} 实际 {got.get(k)!r}"


def test_golden_case_inputs_are_real_strings(doc):
    """输入必须是真实样值（非空字符串），且带 source_layer。"""
    for g in doc["golden_cases"]:
        assert g["source_layer"] and os.path.isdir(g["source_layer"]), g["id"]
        assert g["input"], g["id"]
        for k, v in g["input"].items():
            assert isinstance(v, str) and v.strip(), f"{g['id']} 的 {k} 不是真实样值"


# ------------------------------------------------------------------ 插件
@pytest.mark.parametrize("case", split_unit.GOLDEN)
def test_plugin_split_unit(case):
    assert split_unit.apply(case["input"]) == case["expect"]


@pytest.mark.parametrize("case", split_range.GOLDEN)
def test_plugin_split_range(case):
    assert split_range.apply(case["input"]) == case["expect"]


def test_plugin_never_splits_plain_number():
    """回归：纯数字不许被拆成 102/0。"""
    assert split_unit.apply("1020")["unit"] == ""
    assert split_unit.apply("1020")["housenumber"] == "1020"


# ------------------------------------------------------------------ minimal_safe
def test_minimal_safe_unrecognized_input_goes_manual(reg):
    out = evaluator.minimal_safe(reg, {"foo": "bar", "baz": ""})
    assert out["pool"] == "manual"
    assert out["a_pool_eligible"] is False
    assert out["parsed"] == {}


def test_minimal_safe_parses_only_number_and_street(reg):
    out = evaluator.minimal_safe(reg, {"housenumber": "12", "street": "MAIN ST",
                                       "city": "X", "zip": "99999"})
    assert out["pool"] == "manual" and out["a_pool_eligible"] is False
    assert out["parsed"] == {"housenumber": "12", "street": "MAIN ST"}   # 只两要素


def test_decide_unknown_dialect_falls_back(reg):
    out = evaluator.decide(reg, "does-not-exist", {"housenumber": "1", "street": "A ST"})
    assert out["dialect_id"] == "minimal_safe" and out["pool"] == "manual"


def test_decide_active_dialect_a_pool(reg):
    actives = [d for d in reg["dialects"] if d["status"] == "active"]
    assert actives, "v1 至少要有 1 个 active 方言"
    d = actives[0]
    row = {d["template"]["number_aliases"][0]: "1020",
           d["template"]["street_aliases"][0]: "N MAIN ST"}
    out = evaluator.decide(reg, d["id"], row)
    assert out["dialect_id"] == d["id"] and out["pool"] == "a" and out["a_pool_eligible"] is True


# ------------------------------------------------------------------ validate 正/反向
def test_validate_passes_on_real_file():
    assert subprocess.run([sys.executable, os.path.join(REG, "validate.py")],
                          capture_output=True, text=True).returncode == 0


def _dump(tmp_path, d):
    p = tmp_path / "mut.yaml"
    p.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return p


def test_validate_fails_without_golden_cases(doc, tmp_path):
    d = copy.deepcopy(doc)
    d["dialects"][0]["golden_cases"] = []
    p = _dump(tmp_path, d)
    r = subprocess.run([sys.executable, os.path.join(REG, "validate.py"), "--yaml", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "golden_cases 必须 3–5 条" in r.stdout


def test_validate_fails_without_granularity(doc, tmp_path):
    d = copy.deepcopy(doc)
    d["dialects"][0]["geom"]["granularity"] = "somewhere_between"
    p = _dump(tmp_path, d)
    r = subprocess.run([sys.executable, os.path.join(REG, "validate.py"), "--yaml", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "geom.granularity 非法" in r.stdout


def test_validate_fails_without_crs(doc, tmp_path):
    d = copy.deepcopy(doc)
    d["dialects"][0]["crs"] = {"epsg": "unknown"}
    p = _dump(tmp_path, d)
    r = subprocess.run([sys.executable, os.path.join(REG, "validate.py"), "--yaml", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "crs 缺键" in r.stdout


def test_validate_fails_without_fallback(doc, tmp_path):
    d = copy.deepcopy(doc)
    d.pop("fallback")
    p = _dump(tmp_path, d)
    r = subprocess.run([sys.executable, os.path.join(REG, "validate.py"), "--yaml", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "fallback" in r.stdout


def test_validate_fails_on_open_denominator(doc, tmp_path):
    d = copy.deepcopy(doc)
    d["denominator"]["d2_local"] += 1
    p = _dump(tmp_path, d)
    r = subprocess.run([sys.executable, os.path.join(REG, "validate.py"), "--yaml", str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "分母不闭合" in r.stdout


# ------------------------------------------------------------------ 分组产物
def test_assignment_rows_and_no_catch_all_bucket():
    rows = list(csv.DictReader(open(os.path.join(DIAL, "dialect-assignment.csv"), encoding="utf-8")))
    assert len(rows) == 17168
    assert sum(1 for r in rows if r["universe"] == "d1") == 16010
    assert sum(1 for r in rows if r["universe"] == "d2") == 1158
    buckets = {r["dialect_id"] for r in rows}
    for banned in ("other", "misc", "unknown", "unknown_rest"):
        assert banned not in buckets
    reasons = {r["reason"] for r in rows}
    assert reasons <= (set(validate_mod.REASONS) | {""}), reasons
    for r in rows:
        if r["dialect_id"] == "minimal_safe":
            assert r["status"] == "manual"


def test_coverage_sums_match_denominator():
    cov = list(csv.DictReader(open(os.path.join(DIAL, "dialect-coverage.csv"), encoding="utf-8")))
    assert sum(int(r["layers_n"]) for r in cov) == 17168


def test_manual_queue_sorted_and_weekly_cap():
    q = list(csv.DictReader(open(os.path.join(DIAL, "manual-queue.csv"), encoding="utf-8")))
    scores = [float(r["score"]) for r in q]
    assert scores == sorted(scores, reverse=True)
    with open(YAML_PATH, encoding="utf-8") as fh:
        cap = yaml.safe_load(fh)["weekly_cap_layers"]
    # 一个组可跨周（组本来就比周上限大），但 (组层数) 必须 ≤ 周上限 × 它占的周数，且区间不许重叠
    prev_end = 0
    for r in q:
        wk, we = int(r["week"]), int(r["week_end"])
        span = we - wk + 1
        assert span == int(r["weeks_spanned"]) and span >= 1
        assert int(r["layers_n"]) <= cap * span, f"{r['dialect_id']} 层数超过 {cap}×{span} 周"
        assert wk > prev_end, f"{r['dialect_id']} 的周区间与上一组重叠"
        prev_end = we
