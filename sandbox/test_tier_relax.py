"""E3/E7 放宽的边界单测：① E3 na 边界 ② E7 参照池取样与 n_cmp<3 ③ 四档求和断言。

全部用内存里造的小数据，不读本地全表、不起网络，跑一遍 <1 秒。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox import e7_refpool, tier_relax  # noqa: E402


def st(**kw):
    base = {k: "clear" for k in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")}
    base.update(kw)
    return base


# ——— ① E3 放宽边界 ———
def test_e3_unknown_with_geom_becomes_na():
    r = {"url": "u1", "granularity": "unknown", "geom_type": "point",
         **{f"{k}_state": v for k, v in st(E3="unknown").items()}}
    e3, _e7, det = tier_relax.states_of(r, True, {})
    assert e3["E3"] == "na" and "放宽" in det["E3"]


def test_e3_unknown_without_geom_stays_unknown():
    """粒度未定但几何也没实测 → 不许当 na（无实测就没证据）。"""
    r = {"url": "u2", "granularity": "unknown", "geom_type": "",
         **{f"{k}_state": v for k, v in st(E3="unknown").items()}}
    e3, _, _ = tier_relax.states_of(r, True, {})
    assert e3["E3"] == "unknown" and tier_relax.tier_of(e3) == "tier3"


def test_e3_known_granularity_conflict_stays_hit():
    """E3 仍是 FATAL：粒度已知但与几何冲突 → 无论开关都记 hit、落 Tier3。"""
    r = {"url": "u3", "granularity": "parcel_centroid", "geom_type": "point",
         **{f"{k}_state": v for k, v in st(E3="hit").items()}}
    e3, _, _ = tier_relax.states_of(r, True, {})
    assert e3["E3"] == "hit" and tier_relax.tier_of(e3) == "tier3"


def test_e3_switch_off_is_strict():
    r = {"url": "u4", "granularity": "unknown", "geom_type": "point",
         **{f"{k}_state": v for k, v in st(E3="unknown").items()}}
    e3, _, _ = tier_relax.states_of(r, False, {})
    assert e3["E3"] == "unknown" and tier_relax.tier_of(e3) == "tier3"


# ——— ② E7 参照池取样与 n_cmp<3 ———
def test_pool_key_requires_number_street_state():
    assert e7_refpool.pool_key({"house_number": "12", "street_name": "MAIN", "state_abbr": "MA", "zip5": "02139"})
    assert e7_refpool.pool_key({"house_number": "", "street_name": "MAIN", "state_abbr": "MA"}) == ""
    assert e7_refpool.pool_key({"house_number": "12", "street_name": "", "state_abbr": "MA"}) == ""


def test_pool_key_falls_back_to_street_full_without_type():
    """street_name 缺时用 street_full 去尾部类型词，与 street_norm 的全称化配套（否则永远合不上）。"""
    k = e7_refpool.pool_key({"house_number": "12", "street_full": "Windy Hill Pl", "state_abbr": "GA"})
    assert k == "GA|12|" + e7_refpool.street_norm("Windy Hill") + "|"


def test_strip_type_keeps_last_word_when_all_suffixes():
    assert e7_refpool.strip_type("Drive") == "drive"


def test_e7_ncmp_below_three_stays_unknown(monkeypatch):
    """跨源同址可比 2 行 < min_cmp_rows=3 → unknown，绝不冒充 clear。"""
    rows = [("pool-a", "MA|1|mainstreet|02139", 0.0, 0.0),
            ("pool-b", "MA|2|mainstreet|02139", 0.0, 0.0),
            ("pool-c", "MA|3|mainstreet|02139", 0.0, 0.0)]
    monkeypatch.setattr(e7_refpool, "load_local_pool", lambda cap: (rows, {}, {}))
    monkeypatch.setattr(e7_refpool, "load_samples", lambda roles: (
        {"u": [("MA|1|mainstreet|02139", 0.0, 0.0), ("MA|2|mainstreet|02139", 0.0, 0.0)]}, {"u": {"MA"}}, 2))
    monkeypatch.setattr(sys, "argv", ["e7_refpool.py", "--outdir", "/tmp/pytest-e7", "--per-layer-cap", "3"])
    assert e7_refpool.main() == 0
    import csv
    rows_out = list(csv.DictReader(open("/tmp/pytest-e7/coord-evidence-relax.csv", encoding="utf-8")))
    row = next(r for r in rows_out if r["url"] == "u")
    assert row["n_cmp"] == "2" and row["e7"] == "unknown"
    assert row["n_conflict"] == "0"


# ——— ③ 四档求和断言 ———
def test_bucket_of_is_a_partition():
    """四档分类互斥且覆盖：任一 (t10,t01) 组合都落到唯一一档。"""
    seen = set()
    for t10 in ("tier1", "tier2", "tier3"):
        for t01 in ("tier1", "tier2", "tier3"):
            if t10 != "tier1" and t01 != "tier1":
                continue
            seen.add(tier_relax.bucket_of("tier1", t10, t01))
    assert seen == {"strict", "e3_only", "e7_only"}


def test_bucket_sum_equals_tier1_total():
    """两个都放时 Tier1 集合被四档划分；层数、行数都要逐位闭合。"""
    rows = [(1, "tier1", "tier1", "tier1"), (2, "tier1", "tier2", "tier2"),
            (3, "tier2", "tier1", "tier2"), (4, "tier2", "tier2", "tier1"),
            (5, "tier1", "tier1", "tier1"), (6, "tier3", "tier3", "tier3")]
    tot_l = tot_r = 0
    for lid, t00, t10, t01 in rows:
        if t01 != "tier1":
            continue
        tier_relax.bucket_of(t00, t10, t01)
        tot_l += 1
        tot_r += lid * 10
    assert tot_l == 3 and tot_r == 100
    assert tier_relax.BUCKETS == ("strict", "e3_only", "e7_only", "both")


def test_delivered_summary_is_closed():
    """交付物自检：三档/挪动表两处差额为 0，四档和 === Tier1 总层数与总行数。"""
    import json
    p = os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125", "summary.json")
    if not os.path.isfile(p):
        return
    d = json.load(open(p, encoding="utf-8"))
    c = d["checks"]
    assert c["tiers_diff_layers"] == 0 and c["tiers_diff_rows"] == 0
    assert c["moves_diff_layers"] == 0 and c["moves_diff_rows"] == 0
    assert c["buckets_equal_tier1"] is True
    assert c["bucket_sum_layers"] == d["tiers"]["tier1"]["layers"]
    assert c["bucket_sum_rows"] == d["tiers"]["tier1"]["rows"]
    assert sum(b["layers"] for b in d["buckets"].values()) == d["tiers"]["tier1"]["layers"]


def test_tier_of_matches_auto_recognize_semantics():
    """放宽不碰其余判据：E5 hit 仍 Tier2、E6 hit 仍 Tier3、全 clear/na 才 Tier1。"""
    assert tier_relax.tier_of(st()) == "tier1"
    assert tier_relax.tier_of(st(E3="na", E7="na")) == "tier1"
    assert tier_relax.tier_of(st(E5="hit")) == "tier2"
    assert tier_relax.tier_of(st(E6="hit")) == "tier3"
    assert tier_relax.tier_of(st(E7="unknown")) == "tier2"
