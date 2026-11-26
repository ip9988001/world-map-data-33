#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000269 · 195 层未映射分类（只读既有文件；只写本目录产物）。

输入：layers-evidence.jsonl（scan_unmapped.py）
     fix-simulation.jsonl（simulate_fix.py）
     layer-scoped-fixes.jsonl（measure_layer_scoped.py）
     ../layer-coverage.v2.csv（in_rows）
输出：unmapped-classification.csv（列固定 10 列）
     overrides-resolved.json（本单人工复核覆盖了哪几层、覆盖成什么，便于审计）

判定来源分两段：
  A) 规则判定（可复跑、与证据一一对应）
  B) 人工逐层复核覆盖（OVERRIDES：按 layer_id 子串匹配），只用于「规则判不准」的层；
     每条都写清证据与理由，且不得与证据矛盾。

用法：python3 classify_unmapped.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)
COVERAGE = os.path.join(FM, "layer-coverage.v2.csv")
EVID = os.path.join(HERE, "layers-evidence.jsonl")
SIM = os.path.join(HERE, "fix-simulation.jsonl")
SCOPED = os.path.join(HERE, "layer-scoped-fixes.jsonl")
OUT = os.path.join(HERE, "unmapped-classification.csv")
OUT_OVR = os.path.join(HERE, "overrides-resolved.json")

SPEC_COLS = ["layer_id", "class", "reason_code", "reason_detail", "addr_field_hits",
             "has_combined_addrstring", "sample_hit_rate", "fixable", "fix_plan",
             "est_rows_recoverable"]

# 可安全进全局最小安全表（minimal_safe）的辨识型字段名（normalized 子串）
SAFE_ALIAS = ("strname", "streetname", "streetnm", "stname", "stnm", "roadname", "roadnm",
              "feanme", "sfeanme", "featyp", "sfeatyp", "strtype", "strsuffix", "streettype",
              "streetsuffix", "roadsuffix", "roadtype", "thoroughfare", "thorfare", "thorofare",
              "civicnum", "civnum", "strnum", "streetnum", "streetno", "situsstreet", "sitestreet",
              "streetdescription", "fullstnm", "stpre", "strprefix", "streetraw", "streetderived",
              "msagroute", "civicstreet", "propstreet", "locstnam", "locstsuf", "stdstreet",
              "streettho", "addrsn", "addrst", "lstconcat", "streetnps", "stnam")
PERSON_LIKE = ("firstname", "lastname", "firstandlastname", "fullname")

US_BOXES = [(24.0, 49.4, -125.0, -66.9), (51.0, 71.5, -180.0, -129.0),
            (18.5, 22.5, -161.0, -154.5), (17.5, 18.6, -68.0, -64.5)]
NON_US_HINT = [
    ("爱尔兰", ("secto_nbi", "offaly", "geo_directory", "an post", "community_buildings__address")),
    ("加拿大", ("ns_civic", "nscaf", "civic_addresses_", "_ca_", "canada", "yukon", "castlegar",
              "vancouver", "_coq_", "diamond_vale", "lake_country", "in_civic_address", "ri_civic",
              "vi_civic", "ac_civicaddress", "cb_civic", "woito", "charleroi_addresspt", "kelowna",
              "civicaddressing", "civicaddresspoints", "cadaddresspoints", "gis_app_base",
              "civic_addresses_")),
    ("新西兰", ("nz_server", "search_address_featur", "corax")),
    ("澳大利亚", ("exp_national_address", "pozi_connect", "kaliyeva")),
    ("英国", ("geoyukon_gymap", "salford", "address_point_feature", "all_addresses_feature")),
    ("德国", ("gwc", "glass_waste", "_wgc_")),
    ("奥地利", ("salzburg", "kindergarten", "train_station", "hospital", "castles", "science_city",
              "itzling", "my_address", "myaddress", "walking_distance", "driving_distance",
              "z_gis_addresses", "varjumiskohad", "gymap", "z_gis")),
    ("捷克", ("poc_bytu", "adresni_mista", "zs_sub_poc")),
    ("荷兰", ("buildings_and_addresses", "adresseerbaarobjectstatus")),
    ("印尼", ("rbi_18", "situs_cagar", "bangunan_situs", "peta_situs", "situs_kumitir", "mapang", "situs")),
    ("塞浦路斯", ("chooseyourcyprus", "pyla_geocoding")),
    ("黎巴嫩", ("blat_street_addressing",)),
    ("爱沙尼亚", ("varjumiskohad",)),
    ("南非", ("street_address_featureserver_0",)),
    ("根西", ("address_points_gsy",)),
    ("沙特", ("address_point_feature", "uid_addres")),
    ("特多", ("diamond_vale",)),
]

# ---------------------------------------------------------------------------
# 人工复核覆盖（子串 → 结论）。凡规则判不准 / 证据指向别的 reason 的层都在这里，
# 每条都能在 layers-evidence.jsonl 里查到对应证据。
# 字段：(class, reason_code, detail, fixable, est_rate|None, fix_plan)
# ---------------------------------------------------------------------------
OVERRIDES = {
    # ---- A：地址属性根本没落盘（层名像地址层，payload 里没有）----
    "is_rest_services_EXP_national_address_points": (
        "A", "addr_attrs_not_collected",
        "title=EXP_national_address_points（澳洲全国地址点），但落盘 raw 只有 OBJECTID/"
        "address_detail_pid/lga_code/lga_release/state_code + 经纬度；无门牌、无街名、无可拆串 → "
        "不是别名问题，是采集侧字段缺失，需重采（本单只查不改）", "N", None, ""),
    "sidential_Commercial_and_Mixed_Use_Buildings": (
        "A", "addr_attrs_not_collected",
        "title=Building Use (Address Points View), GeoDirectory（爱尔兰）；raw 仅 BUILDING_ID/"
        "BUILDING_USE/OBJECTID，地址属性未落盘", "N", None, ""),
    "rcgis_rest_services_County_37_LBRS_Addresses": (
        "A", "addr_attrs_not_collected",
        "层名含 Addresses，但 raw 仅 FEATUREID/STRUC_TYPE/COUNTY/OBJECTID；地址属性未落盘", "N", None, ""),
    "tK4vdg_arcgis_rest_services_DW_AddressPoints": (
        "A", "addr_attrs_not_collected", "raw 只有 OBJECTID 一个字段（+经纬度）；地址属性未落盘", "N", None, ""),
    "t_services_AddressPoints_forSANITARYSEWERAPP": (
        "A", "addr_attrs_not_collected", "raw 仅 2 个字段（Address_Nu 等）+经纬度；无街名", "N", None, ""),
    # ---- A：只有门牌号，没有街名字段 ----
    "DKC97XHbtyzbfkd_arcgis_rest_services_RKC_Map": (
        "A", "no_street_field", "title=PARCEL SITUS；raw 仅 PID/ZIP_CODE/ZIP_CITY，无门牌无街名", "N", None, ""),
    "FjG9HQX_arcgis_rest_services_Parcel_AdrUnits": (
        "A", "no_street_field", "只有 UNIT_NO/BLD_NO（单元号/楼号），无门牌、无街名", "N", None, ""),
    "WhklwVA3_arcgis_rest_services_Address_Points": (
        "A", "no_street_field", "Address 列装的是门牌号（9855/5131），源里没有街名字段", "N", None, ""),
    "wbhPOszb_arcgis_rest_services_Address_Points": (
        "A", "no_street_field", "raw 仅 AddressNo（门牌号）+OBJECTID", "N", None, ""),
    "ia_wi_us_server_rest_services_Address_points": (
        "A", "no_street_field", "ADDRESSNUM 是门牌号 + ZIP/MCD；无街名字段、无可拆串", "N", None, ""),
    "IQDOsXnGaTxj2_arcgis_rest_services_Addresses": (
        "A", "no_street_field",
        "HOUSE_NUMBER 是门牌；ROAD_NUMBER='N3075' 是乡村路线号、PARCEL_NUMBER 是地块号，都不是街名", "N", None, ""),
    "B5z0_arcgis_rest_services_AddressPoints_view": (
        "A", "no_street_field", "只有 HOUSE_NUM 一个门牌字段", "N", None, ""),
    "XIgKq7Rz_arcgis_rest_services_Address_Points": (
        "A", "no_street_field", "只有 AddNum 一个门牌字段", "N", None, ""),
    "l_arcgis_rest_services_AddressPoints_SP_view": (
        "A", "no_street_field", "只有 AddressNumber 一个门牌字段", "N", None, ""),
    "u_arcgis_rest_services_Address_Map_Base_clip": (
        "A", "no_street_field", "HOUSENUM + NUM_LABEL，无街名字段", "N", None, ""),
    "bc8717c958f1a655_rest_services_ADDRESS_POINT": (
        "A", "no_street_field",
        "Street_No + Full_Addre='KRT - Zone 22 - Street 21 - Building 7'（沙特分区编号式，"
        "不是「号+街名」形态，也不属美国口径）", "N", None, ""),
    "cgis_rest_services_IN_Civic_Address_Points": (
        "A", "no_street_field", "raw 只有 CIVNUM（门牌）+REFNUM/ID 类，无街名字段", "N", None, ""),
    "ervices_RI_Civic_Address_Points": (
        "A", "no_street_field", "raw 只有 CIVNUM（门牌）+REFNUM/ID 类，无街名字段", "N", None, ""),
    "cgis_rest_services_VI_Civic_Address_Points": (
        "A", "no_street_field", "raw 只有 CIVNUM（门牌）+REFNUM/ID 类，无街名字段", "N", None, ""),
    "_rest_services_Corax_Cadastral_Address_Label": (
        "A", "no_street_field", "只有 HOUSE_NUMBER（门牌）+OBJECTID，无街名", "N", None, ""),
    "_server_rest_services_ParcelViewer_Parcel_Extras": (
        "A", "no_street_field", "只有 Ord_Num（地籍序号）等非地址字段，无街名", "N", None, ""),
    # ---- A：街名列存在但全空（payload 里没值）----
    "_arcgis_rest_services_E911_AddressPoints_PUB": (
        "A", "street_field_all_null",
        "街名列 SN 样本 300/300 为空/\"null\"；ST 里装的是街道类型（BOULEVARD/PLACE）、"
        "ADDRESS 装门牌号 → payload 里没有街名值，属上游缺字段", "N", None, ""),
    "xjrB05UV_arcgis_rest_services_Riv_Co_Address": (
        "UNKNOWN", "sample_too_small",
        "整层仅 3 行；街名/门牌字段（St_Name/Add_Number）在 3 行样本里全空，"
        "无法判断是层本身为空还是采集丢值 → 还缺证据：需看该服务全量或源服务字段定义", "N", None, ""),
    # ---- A：注记/标注层 ----
    "UGfPrN7o_arcgis_rest_services_Address_Labels": (
        "A", "label_or_annotation_only", "raw 仅 LABEL（纯门牌号 1051/1056）+OBJECTID，无街名", "N", None, ""),
    "rN7o_arcgis_rest_services_Coq_Address_Labels": (
        "A", "label_or_annotation_only", "raw 仅 LABEL（纯门牌号）+OBJECTID，无街名", "N", None, ""),
    "oEc3tdJ8TphG_arcgis_rest_services_Addresses": (
        "A", "label_or_annotation_only", "只有 textstring_address（纯门牌 908/305）+address_type", "N", None, ""),
    "_ca_server_rest_services_OpenData_OpenData_Land_MapServer_10": (
        "A", "label_or_annotation_only", "只有 TEXTSTRING（纯门牌 3001）", "N", None, ""),
    "xn1R_arcgis_rest_services_Annotation_Address": (
        "A", "label_or_annotation_only", "AnnotationClassID/TextString 注记要素类，值多为纯门牌", "N", None, ""),
    # ---- A：门牌与街名粘在一串且不可拆 ----
    "rcgis_rest_services_911_Trail_Address_Marker": (
        "A", "unparseable_concat",
        "ADDRESS='32181LN'（门牌+步道编号无分隔），TrailName 是步道名不是街名；"
        "split 只从 TrailName 拆出 'Street Trailhead' 这类假街名 → 不可修", "N", None, ""),
    "qxHA_arcgis_rest_services_E911_Intersections": (
        "A", "intersection_no_number",
        "loc = 'Brigantine Dr & Fall Creek Rd'（路口名），无门牌号，源里没有号/街分离字段 → 不是地址点", "N", None, ""),
    # ---- A：网格/区间、编号 ----
    "publicgis1_rest_services_Addressing_AddressRange": (
        "A", "grid_range_no_street_name", "只有 Range='W9300'（街区区间），无街名字段", "N", None, ""),
    "ervices_E911_Location_Address_Grid_27_250130": (
        "A", "grid_range_no_street_name", "网格层（NORTH_27 等），4 行；无街名字段", "N", None, ""),
    # ---- A：调查/行政/报表面板 ----
    "69927fe3de7343b4b5f3dca25d6a16d9": (
        "A", "admin_or_survey_table",
        "Survey123 表单（含 first_and_last_name/email/organization）；"
        "注意：'lastname' 在角色表里被误当 street 别名，会把调查人姓名拆成街名 → 不是地址层", "N", None, ""),
    "s_survey123_991cee66d77d4aa780a066dbde11a260": (
        "A", "admin_or_survey_table",
        "地址纠错上报点；summary 里虽有地址串（可拆），但要素是「报错工单」不是地址", "N", None, ""),
    "2291cde80c3a4ea184021c50fbf324a3": (
        "A", "admin_or_survey_table", "Survey123 地址申请单（right_of_way_name 是被申请的路名，不是已建地址）", "N", None, ""),
    "ces_service_2e4eb9c8d5bf46f996a02a6caf6470ce": (
        "A", "admin_or_survey_table",
        "911 地址证明信申请单；SADD 里确有 19/23 条真实地址可拆，但要素是申请工单 → 不入地址库", "N", None, ""),
    "F_arcgis_rest_services_Address_Point_Request": (
        "A", "admin_or_survey_table", "地址点申请单（Requestor_Name/Reason），15 行", "N", None, ""),
    "0457fe7d655c42378475435a8d85b96c": (
        "A", "admin_or_survey_table", "NG911 标准意见征集表（Requester_name/email）", "N", None, ""),
    "7fdcd38409074303bc3e2ac3850db315": (
        "A", "admin_or_survey_table", "NG911 标准意见征集表（Requester_name/email）", "N", None, ""),
    # ---- A：口径外（非美国）且属性不成形 ----
    "vYeDEj7_arcgis_rest_services_zs_sub_poc_bytu": (
        "A", "non_us_dataset_no_usable_field",
        "捷克「地址点公寓数」层：raw 只有 NAZ_UL（捷克语街名）等 + 无门牌号字段，"
        "且非美国口径（geo=[49.84,18.28]）", "N", None, ""),
    "ZNxUvTUh8_arcgis_rest_services_adresni_mista": (
        "A", "non_us_dataset_no_usable_field",
        "捷克 adresni_mista：字段 cislo_orientacni_*（捷克门牌体系）无美国口径街名", "N", None, ""),
    "arcgis_rest_services_Buildings_and_Addresses": (
        "A", "non_us_dataset_no_usable_field",
        "荷兰 BAG 层：字段为荷兰语（huisnummer/adresseerbaarobjectstatus），非美国口径", "N", None, ""),
    "is_rest_services_Blat_Street_Addressing": (
        "A", "non_us_dataset_no_usable_field", "黎巴嫩 Blat 街区层，只有 Layer 名，无地址属性", "N", None, ""),
    "est_services_PYLA_GEOCODING_ADDRESS": (
        "A", "non_us_dataset_no_usable_field", "塞浦路斯 PYLA（希腊文列名 ΟΝΟΜΑ_ΔΡΟΜΟΥ 等），非美国口径", "N", None, ""),
    "es_CHOOSEYOURCYPRUS_GEOCODING_ADDRESS_POINTS": (
        "A", "non_us_dataset_no_usable_field", "塞浦路斯（希腊文列名），非美国口径", "N", None, ""),
    "mapang": ("A", "non_us_point_or_poi", "印尼 MAPANG 文化点层；split 出的 0.22 是假街名（Nama_Situs 场所名）", "N", None, ""),
    # ---- B：层内定制（字段名过泛，不能进全局表），已实测 ----
    "s_com_arcgis_rest_services_GIS_App_GIS_App_BASE_MapServer_23": (
        "B", "alias_generic_fieldname_layer_scoped",
        "街名在 NAME、街道类型在 TYPE（NAME='Northview', TYPE='Road'），门牌在 CIVIC_TEXT/ADDR_NBR；"
        "字段名过泛不能进全局最小安全表，需按 org/层建方言", "Y", 1.0,
        "为该 org/层建层级别名：street_aliases=[NAME]+[TYPE]，number_aliases=[CIVIC_TEXT,ADDR_NBR]（实测 street 命中 100%）"),
    "nH5x_arcgis_rest_services_Address__Elections": (
        "B", "alias_generic_fieldname_layer_scoped",
        "与上一层同 org 同结构（NAME+TYPE 拼街名，CIVIC_TEXT/ADDR_NBR 门牌）", "Y", 1.0,
        "层级别名：street=[NAME,TYPE]，number=[CIVIC_TEXT,ADDR_NBR]（实测 100%）"),
    "city_ca_arcgis_rest_services_Public_OpenData": (
        "B", "alias_generic_fieldname_layer_scoped",
        "Kelowna CWK Civic Address Points：NAME+TYPE 拼街名（'BOWES RD'），CIVIC_TEXT/ADDR_NBR 门牌", "Y", 1.0,
        "层级别名：street=[NAME,TYPE]，number=[CIVIC_TEXT,ADDR_NBR]（实测 100%）"),
    "S7cpxnJP_arcgis_rest_services_Address_Points": (
        "B", "alias_generic_fieldname_layer_scoped",
        "街名在 PARCEL_LOC（'Broad St'），源里没有门牌字段 → 补别名后只能落 grade C（有街名、无门牌）", "Y", 1.0,
        "层级别名：street=[PARCEL_LOC]（实测 street 命中 100%，grade 只到 C）"),
    "9Xs_arcgis_rest_services_AddressPts_OwensTwp": (
        "B", "alias_missing_street",
        "街名在 LST_CONCAT（'Wakely Rd'，已经拼好的街名串），门牌在 ANUMBER；LST_CONCAT 不在角色表", "Y", 1.0,
        "最小安全表补 street_aliases: lst_concat（实测 100%，ANUMBER 门牌同时非空 100%）"),
    "poec_arcgis_rest_services_AddressPoints_view": (
        "B", "alias_generic_fieldname_layer_scoped",
        "街名在 STR（3 字母列，值 'REPUBLIC'/'TANGLEWOOD'），门牌在 STR_NUM，CITY/ZIP 齐全；"
        "STR 名字太泛不能进全局表", "Y", 1.0,
        "层级别名：street=[STR]，number=[STR_NUM]（实测 100%）"),
    # ---- B：可修但样本命中低（登记清楚，不夸大）----
    "est_services_Address_points_black_Feb2019MXD": (
        "B", "alias_missing_street",
        "组合串在 ADDR_FULL（'49311 RGE RD 75'），但样本只有 20/150 行非空，其余行地址未落盘；"
        "RD_NUM='BLK.30' 是街区号不是门牌", "Y", 0.1067,
        "补 combined 别名 addr_full（走 split）；预计只救 ~11% 行，剩余需重采"),
    "Zw5lplW9PO_arcgis_rest_services_CivicAddress": (
        "A", "label_or_annotation_only",
        "raw 只有 LABEL（纯门牌 10715）+MAP_ID/LABEL_ROT（注记旋转角）；无街名、无门牌独立字段；"
        "split 出的 0.053 来自把 LABEL 拆成 'A' 这类假街名", "N", None, ""),
    "lxcdnZjF_arcgis_rest_services_Voting_Address": (
        "B", "split_first_row_only",
        "整串地址在 ServiceAdd（'9 CHERUB CT'/'43290 N US HWY 550'），样本可拆 0.883；"
        "map_row 的 split 只在首行试过一次且只扫前 40 键 → 整层 0 命中", "Y", 0.8833,
        "修 fm_core.map_row：split 每行都试 + 候选键扩到全字段（与另外 12 层同一根因）"),
    "YSp_arcgis_rest_services_Address_type_points": (
        "B", "derived_geocoder_output",
        "Street_raw/Street_derived/City_derived/Postal_derived 是地理编码产物："
        "Street_derived 只有 27/150 行有值（其余 '<Null>'），Street_raw 里有 'X Apt 424' 这类脏值", "Y", 0.18,
        "补别名 street_derived/street_raw 并走 split；只救 ~18% 行，且需过滤 '<Null>' 占位"),
}


def _scope(lid, ev):
    low = lid.lower()
    for tag, keys in NON_US_HINT:
        for k in keys:
            if k in low:
                return tag
    g = ev.get("geo_median")
    if not g:
        return None
    la, lo = g
    for a, b, c, d in US_BOXES:
        if a <= la <= b and c <= lo <= d:
            return "美国境内"
    return "境外(geo)"


def find_override(lid):
    hits = [(k, v) for k, v in OVERRIDES.items() if k.lower() in lid.lower()]
    if len(hits) > 1:                      # 取最长（最具体）匹配
        hits.sort(key=lambda kv: -len(kv[0]))
    return hits[0] if hits else (None, None)


def main():
    evs = {json.loads(l)["layer_id"]: json.loads(l) for l in open(EVID, encoding="utf-8")}
    sims = {json.loads(l)["layer_id"]: json.loads(l) for l in open(SIM, encoding="utf-8")}
    scoped = {}
    if os.path.isfile(SCOPED):
        for l in open(SCOPED, encoding="utf-8"):
            r = json.loads(l)
            scoped[r["layer_id"]] = r
    cov = {r["layer"]: r for r in csv.DictReader(open(COVERAGE, encoding="utf-8"))}

    rows, resolved = [], []
    for lid, ev in evs.items():
        s = sims[lid]
        in_rows = int(cov[lid]["in_rows"])
        scope = _scope(lid, ev)
        rh = ev["role_hits"]

        addrhits = []
        if rh["number"]:
            addrhits.append("number=" + "|".join(rh["number"][:4]))
        if rh["street"]:
            addrhits.append("street=" + "|".join(rh["street"][:4]))
        if rh["zip"]:
            addrhits.append("zip=" + "|".join(rh["zip"][:3]))
        if ev["near_miss"]:
            addrhits.append("near_miss=" + "|".join(ev["near_miss"][:6]))
        if s["split_fields"]:
            addrhits.append("split_hit=" + "|".join(list(s["split_fields"])[:3]))
        addr_field_hits = "; ".join(addrhits) if addrhits else "—(无地址类字段名)"
        has_comb = "Y" if (s["v2_split_all"] > 0 or s["v3_loose"] > 0) else "N"

        v1, v2, v3 = s["v1_alias_rate"], s["v2_split_all_rate"], s["v3_loose_rate"]
        best = max(v1, v2, v3)
        split_is_addr = any(re.search(r"addr|street|stname|road|site|label|civic|full|usps",
                                     f) for f in s["split_fields"])
        alias_safe = [f for f in s["alias_fields"]
                      if any(p in f for p in SAFE_ALIAS)
                      and not any(pn in f for pn in PERSON_LIKE)]
        alias_generic = [f for f in s["alias_fields"] if not any(p in f for p in SAFE_ALIAS)]

        cls, reason, detail, fixable, plan, est = "A", "", "", "N", "", 0

        # ---------- 1) 人工复核覆盖优先 ----------
        key, ovr = find_override(lid)
        if ovr:
            cls, reason, detail, fixable, rate, plan = ovr
            est = int(in_rows * rate) if (fixable == "Y" and rate) else 0
            if fixable == "Y" and rate:
                best = rate
            resolved.append({"layer_id": lid, "matched_override_key": key, "class": cls,
                             "reason_code": reason})
        # ---------- 2) 规则判定 ----------
        elif v1 >= 0.15 and alias_safe:
            cls, reason = "B", "alias_missing_street"
            detail = (f"街名/街型字段存在但不在角色表（148 名）里：{alias_safe[:3]}；"
                      f"现状 street 恒空 → grade=None → 整层丢弃；补别名后 street 有值即落 grade C 起")
            uniq = list(dict.fromkeys(f.split("+")[0] + ("+" + f.split("+")[1] if "+" in f and f.split("+")[1] else "")
                                      for f in alias_safe))[:3]
            fixable, plan, est = "Y", (f"registry/dialects.v1.yaml 的 minimal_safe template 补 "
                                       f"street_aliases: {uniq}；不改代码，按样本命中率折算行数"), int(in_rows * v1)
        elif v2 >= 0.15 and split_is_addr:
            cls = "B"
            reason = "split_key_beyond_40" if s["v1_first40_rate"] < 0.02 else "split_first_row_only"
            why = ("组合串排在 raw 第 40 个键之后，map_row 只扫 list(raw.keys())[:40] → 扫不到"
                   if s["v1_first40_rate"] < 0.02 else
                   "map_row 的 split 分支首行拆不出就置 _split_tried 且 _split_key 空，此后每行直接跳过 → "
                   "整层只在第 1 行试过一次")
            detail = (f"组合地址串可拆：{list(s['split_fields'])[:3]}，样本可拆率 {v2:.3f}；根因={why}")
            fixable = "Y"
            plan = ("修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段")
            est = int(in_rows * v2)
        elif v3 >= 0.15:
            cls, reason = "B", "split_too_strict"
            detail = f"「号 + 街名」形态明确但 split_number_street 判 ambiguous/bad_street，样本 {v3:.3f}"
            fixable, plan, est = "Y", "split_number_street 增放宽规则或在 map_row 加兜底（单层定制）", int(in_rows * v3)
        elif alias_generic and best >= 0.15:
            cls, reason = "B", "alias_generic_fieldname_layer_scoped"
            detail = (f"地址在字段名过泛的列里（{alias_generic[:3]}），不能进全局最小安全表；"
                      f"样本命中 {best:.3f}")
            fixable, plan, est = "Y", "按 url/org 建层级别名（不进 minimal_safe）", int(in_rows * best)
        elif best >= 0.02:
            cls, reason = "B", ("alias_missing_street" if v1 >= v2 else "split_low_yield")
            detail = f"可修但样本命中率仅 {best:.3f}，收益小、且部分命中可能来自非地址属性"
            fixable, plan, est = "Y", "同上修法，优先级最低", int(in_rows * best)
        else:
            has_num = bool(rh["number"]) and any(
                ev["raw_key_stats"].get(k, {}).get("nonempty", 0) > 0 for k in rh["number"])
            has_street_named = bool(rh["street"])
            nk = ev["n_raw_keys"]
            if ev["sample_rows"] == 0:
                reason, detail = "no_payload_rows", "part-u 读到 0 行"
            elif has_street_named:
                reason = "street_field_all_null"
                detail = f"街名字段在角色表里但样本值恒空/占位：{rh['street'][:3]}"
            elif has_num:
                reason = "no_street_field"
                detail = (f"有门牌字段（{rh['number'][:3]}）但源里没有街名字段、也没有可拆组合串 → "
                          f"grade C 需要 street，门牌单独不成立")
            elif nk <= 3:
                reason = "addr_attrs_not_collected"
                detail = (f"raw 仅 {nk} 个非地址字段（{list(ev['raw_key_stats'])[:3]}）+经纬度；"
                          f"采集侧没有门牌/街名属性 → 需重采（不在本单可修范围）")
            elif re.search(r"add_?(ns|ew)|hundred_block|address_range|\brange\b", lid.lower()) or \
                    any("RANGE" in f.upper() for f in ev["raw_key_stats"]):
                reason = "grid_range_no_street_name"
                detail = "字段是网格/街区区间（ADD_NS/ADD_EW/ADD_RANGE/Range），无街名字段"
            elif re.search(r"label|annotation|textstring|contents|\bshape", lid.lower()) or \
                    any(str(f).lower() in ("label", "textstring", "contents", "shape__", "element",
                                           "fontname") for f in ev["raw_key_stats"]):
                reason = "label_or_annotation_only"
                detail = "字段是注记/标注（Label/TextString/Contents/Shape），值多为纯门牌或要素文字"
            elif re.search(r"survey|_results|fieldworker|stakeholder|contact|fee|psap|deployment|"
                           r"performance|report|accurac|workshop|interest|comment|grid", lid.lower()):
                reason = "admin_or_survey_table"
                detail = "字段为人员/邮箱/调查/统计类（survey123 / PSAP / 收费 / 报表）"
            elif scope and scope != "美国境内":
                reason = "non_us_point_or_poi"
                detail = (f"口径外（{scope}）POI/服务类点位：字段是场所名/结果表，"
                          f"非美国地址口径，且行数极少")
            else:
                reason = "not_address_layer"
                detail = "无门牌字段、无街名字段、无可拆组合串（样本 0 命中）；美国境内点位层"
            fixable, plan, est = "N", "", 0

        rows.append({
            "layer_id": lid, "class": cls, "reason_code": reason,
            "reason_detail": f"【{scope or '未定位'}】{detail}",
            "addr_field_hits": addr_field_hits, "has_combined_addrstring": has_comb,
            "sample_hit_rate": f"{best:.4f}", "fixable": fixable,
            "fix_plan": plan, "est_rows_recoverable": est,
        })

    rows.sort(key=lambda r: (r["class"], -int(cov[r["layer_id"]]["in_rows"])))
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SPEC_COLS)
        w.writeheader()
        w.writerows(rows)
    with open(OUT_OVR, "w", encoding="utf-8") as fh:
        json.dump({"overrides_total": len(OVERRIDES), "resolved": resolved,
                   "unused_override_keys": sorted(set(OVERRIDES) - {r["matched_override_key"] for r in resolved})},
                  fh, ensure_ascii=False, indent=1)

    print("class:", dict(collections.Counter(r["class"] for r in rows)))
    print("reason:", dict(collections.Counter(r["reason_code"] for r in rows)))
    b = [r for r in rows if r["class"] == "B"]
    print(f"B={len(b)}  可恢复行={sum(r['est_rows_recoverable'] for r in b):,}")
    print("overrides resolved:", len(resolved), "unused:",
          sorted(set(OVERRIDES) - {r["matched_override_key"] for r in resolved}))


if __name__ == "__main__":
    main()
