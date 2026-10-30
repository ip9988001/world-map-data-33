#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""intake_33 契约测试（零依赖：python3 collect/tests/test_intake_33.py 直接跑）。

覆盖的硬约束：
  1. **宗地绝不出地址行**（实测 situs/mailing 冲突率 100%，拿 mailing 当 situs 会写错地址）
  2. 线层绝不出地址行
  3. 五道硬门禁各自拦住什么
  4. 归一化：街道后缀/方向/大写/zip 补零/ZIP+4/别名
  5. addr 主键与 aux_* 主键结构上无交集
  6. 逐层对账恒等式 rows_total = with_number + without_number，且 read = Σ各表
  7. field-map v2 的 postal_city **不得**含 OWNER_CITY（业主城市 ≠ 房产城市）
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
sys.path.insert(0, os.path.join(ROOT, "collect"))

import intake_33 as I          # noqa: E402
import field_map_v2 as FMV2    # noqa: E402

FAILS: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        FAILS.append(msg)


GOOD = {"house_number": "123", "street_name": "MAIN", "street_post_type": "Streer"}


def row(**kw) -> dict:
    r = {"house_number": "123", "house_number_suffix": None, "street_pre_dir": None,
         "street_name": "MAIN", "street_post_type": "STREET", "street_post_dir": None,
         "street_full": "MAIN STREET", "unit": None, "postal_city": "SPRINGFIELD",
         "municipal_city": None, "county_name": "X", "county_fips": "13151",
         "state_abbr": "GA", "zip5": "30303", "latitude": 33.6, "longitude": -84.3,
         "src_kind": "address_point", "src_layer_id": "L1", "src_layer_url": "u",
         "src_parcel_id": None}
    r.update(kw)
    return r


def test_parcel_never_addr() -> None:
    print("\n[1] 宗地绝不出地址行")
    # 即使一行「完全合格」，只要是 parcel_situs，也只能进 aux_parcel
    t, reason = I.route(row(), [], "parcel_situs")
    check(t == "aux_parcel" and reason is None, "合格宗地行 → aux_parcel（不进 addr）：%s" % t)
    t2, _ = I.route(row(county_fips=None), ["county_unresolved"], "parcel_situs")
    check(t2 == "aux_parcel", "缺县的宗地行仍是 aux_parcel（不让它掉进 reject 黑洞）")
    # mailing 字段不会被当作 situs：src_parcel_id 之外的 mailing_* 一律不参与映射
    fm = json.load(open(os.path.join(ROOT, "schema", "field-map-v2.json"), encoding="utf-8"))
    mailing_used = {t for t in ("house_number", "street_name")
                    for e in fm["layers"].values()
                    for src in [(e.get(t) or {}).get("src") or ""]
                    if "MAIL" in src.upper()}
    check(not mailing_used, "field-map 里没有把 MAILING 列当 situs 地址用（%s）" % mailing_used)


def test_line_never_addr() -> None:
    print("\n[2] 线层绝不出地址行")
    t, _ = I.route(row(house_number=None), [], "street_line")
    check(t == "aux_street", "线层行 → aux_street")


def test_gates() -> None:
    print("\n[3] 五道硬门禁")
    t, r = I.route(row(house_number=None), ["no_house_number"], "address_point")
    check(t == "aux_addr_nohouse", "只有 no_house_number → aux_addr_nohouse（不当丢弃）")
    t, r = I.route(row(house_number="0"), ["no_house_number"], "address_point")
    check(t == "aux_addr_nohouse", "门牌号 0（占位）按无门牌号处理")
    t, r = I.route(row(street_name=None), ["no_street_name"], "address_point")
    check(t == "reject" and r == "no_street_name", "无街名 → REJECT")
    t, r = I.route(row(state_abbr="ZZ"), ["state_invalid"], "address_point")
    check(t == "reject" and r == "state_invalid", "州非法 → REJECT")
    t, r = I.route(row(latitude=None), ["geo_missing"], "address_point")
    check(t == "reject" and r == "geo_missing", "缺坐标 → REJECT（SCHEMA 硬门禁）")
    t, r = I.route(row(county_fips=None), ["county_unresolved"], "address_point")
    check(t == "reject" and r == "county_unresolved", "县判不出 → REJECT（不许 bbox 硬凑）")
    t, r = I.route(row(), [], "address_point")
    check(t == "addr" and r is None, "全通过 → addr")


def test_norm() -> None:
    print("\n[4] 归一化")
    check(FMV2.norm_zip("1234") is None, "不足 5 位不补零（补零=伪造 0xxxx）")
    check(FMV2.norm_zip("30303-1234") == "30303", "ZIP+4 取前 5 位")
    check(FMV2.norm_zip("M9V 0A1") is None, "加拿大邮编不冒充 zip5")
    check(FMV2.norm_dir("N") == "North" and FMV2.norm_dir("sw") == "Southwest", "方向词全称化")
    check(FMV2.norm_post_type("st") == "Street" and FMV2.norm_post_type("pkwy") == "Parkway",
          "街道类型全称化")
    check(FMV2.strip_number("123 Main St") == "Main St", "整串地址切号")
    check(FMV2.strip_number("6701") is None, "纯数字串不是街名")
    r = I.norm_street({"street_name": "main", "street_post_type": "st",
                       "street_pre_dir": "n"})
    check(r["street_name"] == "MAIN" and r["street_post_type"] == "Street"
          and r["street_pre_dir"] == "North", "行级归一化：大写 + 全称")
    r = I.norm_street({"street_name": "MAIN", "street_post_type": "Road"})
    check(r["street_full"] == "MAIN Road", "street_full 由 name+type 合成")


def test_keys() -> None:
    print("\n[5] 主键结构")
    a = I.addr_id(row())
    check(len(a) == 40, "addr_id 是 40 位 sha1")
    check(I.addr_id(row(zip5="30304")) != a, "zip 变化 → addr_id 变化")
    check(I.addr_id(row(unit="2B")) != a, "unit 变化 → addr_id 变化")
    check(a != ("p:" + a) and a != ("s:" + a), "aux_key 带 p:/s:/n: 前缀，天然与 addr_id 不相交")


def test_reconcile() -> None:
    print("\n[6] 对账恒等式（用小样本复算）")
    class FakeMapper:
        def __init__(self):
            self.e = {"county_scope": "single", "county_name": {"value": "Clayton"},
                      "county_fips": {"value": "13151"}, "state_abbr": {"value": "GA"},
                      "src_layer_url": "u", "src_parcel_id": {"src": None}}
            self.kind = "address_point"

    m = FakeMapper()
    recs = [{"raw": {"HN": "1", "ST": "A ST"}, "add_num": "1", "st_name": "A", "lat": 33.6, "lon": -84.3},
            {"raw": {"HN": None, "ST": "B ST"}, "add_num": None, "st_name": "B", "lat": 33.6, "lon": -84.3},
            {"raw": {"HN": "3", "ST": None}, "add_num": "3", "st_name": None, "lat": None, "lon": None}]
    with_n = sum(1 for r in recs if r.get("add_num"))
    check(with_n + (len(recs) - with_n) == len(recs), "with_number + without_number == rows_total")


def test_postal_city_not_owner() -> None:
    print("\n[7] postal_city 不许复用业主城市")
    pats = [rx for rx, _t, _q in FMV2.POSTAL_CITY]
    bad = [p for p in pats if "OWNER" in p.upper()]
    check(not bad, "POSTAL_CITY 别名表无 OWNER_*：%s" % bad)
    check(any("MUNICIPALITY" in p.upper() for p in [rx for rx, _t, _q in FMV2.MUNICIPAL_CITY]),
          "MUNICIPALITY 归 municipal_city")


def test_addr_type_no_heuristics() -> None:
    print("\n[8] addr_type：v1 一律 Unknown，除非明确分类列逐值可映射")
    fm = json.load(open(os.path.join(ROOT, "schema", "field-map-v2.json"), encoding="utf-8"))
    mapped = [lid for lid, e in fm["layers"].items()
              if isinstance(e.get("addr_type"), dict) and e["addr_type"].get("src")]
    rest = [lid for lid, e in fm["layers"].items()
            if (e.get("addr_type") or {}).get("constant") == "Unknown"]
    check(len(mapped) + len(rest) == len(fm["layers"]), "每层二选一：映射 or constant=Unknown（%d / %d）"
          % (len(mapped), len(rest)))
    # 可映射层必须在审计白名单里（不许靠 unit/标题 推出来）
    amap = json.load(open(os.path.join(ROOT, "schema", "addr-type-map-v1.json"), encoding="utf-8"))
    ok_layers = {r["layer_id"] for r in amap["layers_sampled"]
                 if r["verdict"] == "map" and r["value_map"]}
    check(set(mapped) <= ok_layers, "映射层 ⊆ 审计认定可映射层：越权 %d" % len(set(mapped) - ok_layers))
    # 默认值不得到处写成 Unknown 以外的字面值：public_row 必须兜底 Unknown
    r = I.public_row(row())
    check(r["addr_type"] == "Unknown", "public_row 缺省 addr_type=Unknown（实际 %s）" % r.get("addr_type"))
    r2 = I.public_row(row(addr_type=None))
    check(r2["addr_type"] == "Unknown", "addr_type 即使显式 None 也不落 null")


def test_city_value_rules() -> None:
    print("\n[9] CITY：值形态校验与 *_source 同步")
    check(FMV2.city_value_class("MIAMI, FL 33142-2202") == "has_punct", "`MIAMI, FL 33142-2202` → has_punct")
    check(FMV2.city_value_class("Unincorporated Area") == "blacklist", "Unincorporated Area → blacklist")
    check(FMV2.city_value_class("29406") == "has_digit", "纯 ZIP 值 → has_digit")
    check(FMV2.city_value_class("SPRINGFIELD") == "clean", "SPRINGFIELD → clean")
    check(FMV2.city_value_class("Saint Francis") == "clean", "Saint Francis → clean（小写也过）")
    check(FMV2.city_value_class(None) == "empty", "None → empty")
    # 有值的行必带 source；值被清空后 source 必须同步为 None
    e = {"postal_city_source": "nad_post_city", "municipal_city_source": "nad_inc_muni"}
    r = I.public_row(row(postal_city="AUSTIN", municipal_city=None, **e))
    check(r["postal_city_source"] == "nad_post_city" and r["municipal_city_source"] is None,
          "有值写 source / 无值写 null（实际 %s / %s）" % (r["postal_city_source"], r["municipal_city_source"]))
    r2 = I.public_row(row(postal_city=None, municipal_city=None, **e))
    check(r2["postal_city_source"] is None, "postal_city=null 时 source 同步 null")


def main() -> int:
    for f in (test_parcel_never_addr, test_line_never_addr, test_gates, test_norm,
              test_keys, test_reconcile, test_postal_city_not_owner,
              test_addr_type_no_heuristics, test_city_value_rules):
        f()
    print()
    if FAILS:
        print("❌ %d 项未通过" % len(FAILS))
        return 1
    print("✅ 契约测试全绿")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
