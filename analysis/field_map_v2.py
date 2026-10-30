#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三仓逐层字段 → 二仓 LOCKED SCHEMA 2.0 主字段 映射（纯离线，不访问任何网络）。

输入（全部已落盘，不重跑值分布摸底）：
  analysis/out/*.json         逐层值分布画像（2381 层，字段名/非空数/示例值/门牌分类）
  collect/address_layers.csv  点层元数据（state / url / rows / geom）
  collect/situs_layers.csv    宗地层元数据（state / url / rows / geom）
  schema/upstream/SCHEMA-v2.0.world-map-data-test.json  二仓 SCHEMA 2.0 原样副本（内容 sha256 校验）

输出：
  schema/field-map-v2.json    逐层映射到 SCHEMA 2.0 主字段 + 4 个三仓溯源字段取值

约束：
  * 本文件**不是** schema，禁止在此定义新的规范字段名；目标名一律取自 SCHEMA 2.0。
  * 找不到源列的字段一律 null，并把原因写进 reason（不猜、不伪造）。
  * 只读：不改 SCHEMA 副本、不访问上游 ArcGIS/Census。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "collect"))
try:
    import county_tiger as CT          # TIGER 县界多边形（禁用 bbox）
except Exception:                      # noqa: BLE001
    CT = None
OUT = os.path.join(HERE, "out")

SCHEMA_PIN = os.path.join(ROOT, "schema", "upstream", "SCHEMA-v2.0.world-map-data-test.json")
SCHEMA_SHA256 = "02d5690a3c501fddeae4c338df4c7b62274c498a8a1b59bc54e6823e570ae14c"  # rev2（+4 三仓溯源字段）

# ---------------------------------------------------------------- 别名表
# 每项 (name_regex, transform, quality)
#   name_regex 对源字段名做**全名**匹配（re.I），避免 YEAR_BUILT/Ymin/Placement 这类前缀误命中
#   transform  取值的加工方式；native = 原样取
F = lambda names, transform="native", quality="native": (r"^(?:%s)$" % names, transform, quality)

HOUSE_NUMBER = [
    F(r"ADDRNUM|ADDRNUMB|ADDRNUMBER|ADDRESS_NUM|ADDRESS_NUMBER|ADDRESSNO|ADDRESS_NO|ADDR_NO|ADDR_NUM|ADDR_NUMBER", "trim"),
    F(r"ADD_NUMBER|ADDNUMBER|ADDNUM|ADDNUM_FULL|ADDNO_FULL|ADD_NUM|ADDNUMB", "trim"),
    F(r"HOUSE_NUM|HOUSE_NUMBER|HOUSE_NO|HOUSENUM|HOUSENO|HSNUM|HSNO|HSENUM|HOUSE|HOUSE_NUMB|HOUSENUMBE|"
      r"HOUSE_NUMBE|HOUSE_NUMB_1", "trim"),
    F(r"ADDR_HN|ADDR_HN_1|ADDR_HOUSENUMBER|ADDR_HOUSE_NUM|HNO|ADDRESS_HN", "trim"),
    F(r"STREET_NUM|STREET_NUMBER|STREETNO|STNUM|STRNUM", "trim"),
    F(r"PREMISE_NUM|PREMISE_NUMBER|PREM_NUM|PRMNUM", "trim"),
    F(r"SITUS_NUM|SITUS_NUMBER|SITUSNO", "trim"),
    F(r"NUMBER|NUM|NUM_1|NO_1", "trim"),
    # 整串地址兜底：SCHEMA 2.0 的 house_number 源写作 nad.Add_Number|AddNo_Full
    F(r"ADDRESS|ADDRESS_FULL|ADDRESS1|ADDRESS_1|ADDRESS_LINE_?1|FULLADDR|FULL_ADDR|FULLADDRESS|FULL_ADDRESS|"
      r"FULL_ADDRE|SITE_ADDR|SITE_ADDRESS|SITEADDR|ADDR|ADDR_FULL|LOCATION_ADDRESS|PROP_ADDR|PROPERTY_ADDRESS",
      "extract_number", "extracted"),
]

HOUSE_NUMBER_SUFFIX = [
    F(r"ADDNUM_SUF|ADDNUM_SUFFIX|ADD_NUM_SUF|ADD_NUM_SUFFIX|ADDRNUM_SUF|ADDR_NUM_SUF|ADDRNUMSUF|ADDNUMSUF|"
      r"ADDRESS_NUMBER_SUFFIX|ADDRESS_NUM_SUF|NUM_SUF|NUM_SUFFIX|STREET_NUM_SUF|UNIT_SUF", "trim", "native"),
    F(r"SUFFIX|SUFIX|SUF", "trim", "native"),
]

STREET_PRE_DIR = [
    F(r"ST_PREDIR|STREET_PREDIR|ST_PRE_DIR|STREET_PRE_DIR|PREDIR|PRE_DIR|PRE_DIRECTION|PRE_DIRECTIONAL|"
      r"PREDIRECTI|PREDIRECTION|PREDIRECTIONAL|ADDR_PREDIR|ADDRPRE_DIR|STN_PREDIR|CLDXF_PREDIRECTIONAL|"
      r"ROADPREDIR|STREET_DIR_PREFIX|PRE_DIRECTIONAL|RD_PREFIX|RD_PREDIR|ROAD_PREFIX|ROAD_PREDIR",
      "norm_dir"),
]

STREET_NAME = [
    F(r"ST_NAME|STNAME|STREET_NAME|STREETNAME|ST_NAM|STNAM|STREET_NAM|STREET_NA|STREET", "trim"),
    F(r"RD_FULLNAME|ROAD_FULLNAME|RD_LABEL|FULL_ROAD_NAME", "strip_type_dir", "extracted"),
    F(r"LABEL_NAME|ADDR_LABEL|FULL_LABEL", "strip_number", "extracted"),
    F(r"ROAD_NAME|ROADNAME|ROAD|THOROUGHFARE|WAY_NAME|STREET_FULL|FULL_STREET_NAME|FULLSTREET|STNAM_FULL|"
      r"FULL_STREET", "strip_type_dir", "extracted"),
    F(r"ADDR_STREET|ADDRSTREET|ADDRESS_STREET|SITUS_STREET|SITE_STREET|STREET_NM|STREETNAME_1|STREET_NAME_1|"
      r"ADDR_SN|ADDRSN|ROAD_LABEL", "trim"),
    F(r"ADDRESS|ADDRESS_FULL|ADDRESS1|ADDRESS_LINE_?1|FULLADDR|FULL_ADDR|FULLADDRESS|FULL_ADDRESS|"
      r"FULL_ADDRE|SITE_ADDR|SITE_ADDRESS|SITEADDR|ADDR|PROP_ADDR|PROPERTY_ADDRESS", "strip_number", "extracted"),
]

STREET_POST_TYPE = [
    F(r"ST_POSTYP|ST_POS_TYP|ST_POS_TYP_1|STREET_POST_TYPE|POSTTYPE|POST_TYPE|ST_TYPE|STTYPE|STRTYPE|STREET_TYPE|"
      r"STREETTYPE|STREET_TYP|STREET_TP|ST_TYP|ST_SUFFIX|STREET_SUFFIX|STREET_SUF|STREET_SUF_1|ST_SUF|STREETSUF|"
      r"ADDR_STREET_SUFFIX|ADDRSTSUF|STREETTYPE_1|RD_TYPE|RD_POSTTYPE|RD_SUFFIX|ROAD_TYPE|ROAD_SUFFIX",
      "norm_post_type"),
]

STREET_POST_DIR = [
    F(r"ST_POSDIR|ST_POST_DIR|STREET_POST_DIR|POSTDIR|POST_DIR|POST_DIRECTION|POST_DIRECTIONAL|POSTDIRECTI|"
      r"ADDR_POSDIR|ADDRPOSDIR|STN_POSDIR|ROADPOSTDIR|CLDXF_POSTDIRECTIONAL", "norm_dir"),
    F(r"SUF_DIR|SUFDIR|SUFFIX_DIR|SUFFIXDIR|SUFFIX_DIRECTIONAL|SUF_DIRECTIONAL", "norm_dir", "native"),
]

STREET_FULL = [
    F(r"STNAM_FULL|ST_NAME_FULL|STREET_FULL|FULL_STREET|FULL_STREET_NAME|FULLSTREET|STREET_FULL_NAME|"
      r"STREET_LABEL|FULL_STNAME|ST_FULLNAME", "trim", "native"),
    F(r"ADDRESS|ADDRESS_FULL|ADDRESS1|ADDRESS_LINE_?1|FULLADDR|FULL_ADDR|FULLADDRESS|FULL_ADDRESS|FULL_ADDRE|"
      r"SITE_ADDR|SITE_ADDRESS|SITEADDR|ADDR|RD_FULLNAME|ROAD_FULLNAME|LABEL_NAME", "strip_number", "extracted"),
]

UNIT = [
    F(r"UNIT_NUM|UNIT_NUMBER|UNIT_NO|UNIT_NUM_1|UNIT_ID|UNITID|UNIT_DES|UNIT_DESIGNATOR|UNIT_DESIG|"
      r"ADDR_UNIT|ADD_UNIT|ADDRESS_UNIT|APT|APT_NUM|APT_NO|APARTMENT|SUITE|STE|ROOM|ROOM_NUM|RM|BLDG_UNIT|"
      r"SITE_UNIT|SITUS_UNIT|SD_UNIT", "trim", "native"),
    F(r"UNIT", "trim", "native"),
]

POSTAL_CITY = [
    F(r"POST_CITY|POSTAL_CITY|MAIL_CITY|MAILING_CITY|SITUS_CITY|ADDRESS_CITY|ADDR_CITY|CITY_POSTAL|"
      r"CITY_MAILING", "trim", "native"),
    # 注意：MUNICIPALITY / TOWN / COMMUNITY / OWNER_CITY **不进** postal_city
    #   - MUNICIPALITY/TOWNSHIP 属 municipal_city（实测含 "Unincorporated Area"）
    #   - OWNER_CITY 是业主邮寄城市（实测含 "MIAMI, FL 33142-2202"），不是房产所在城市
    F(r"CITY|CITY_NAME|CITYNAME|PLACE_NAME|POSTALCITY|POSTAL_TOWN|POSTAL_COMM|POST_OFFICE_CITY|PO_CITY",
      "trim", "native"),
    F(r"POSTAL", "trim", "native"),
]

MUNICIPAL_CITY = [
    F(r"INC_MUNI|INCMUNI|MUNI|MUNI_NAME|MUNICIPALITY|MUNICIPAL_NAME|MUNICIPAL|MUNICIPALITY_NAME|CITY_OF|"
      r"TOWNSHIP|TOWNSHIP_NAME", "trim", "native"),
]

COUNTY_NAME = [
    F(r"COUNTY|COUNTY_NAME|COUNTYNAME|COUNTY_NM|CNTY_NAME|CNTY|COUNTY_NAME_1|CNTY_NM", "norm_county", "native"),
]

COUNTY_FIPS = [
    F(r"COUNTYFIPS|COUNTY_FIPS|COUNTYFP|COUNTY_FP|CNTY_FIPS|STCOFIPS|ST_CNTY_FIPS|FIPS_CODE|FIPSCODE|FIPS_CNTY|"
      r"COUNTY_CODE|CNTY_IS|STCNTY", "norm_fips", "native"),
    F(r"FIPS", "norm_fips", "native"),
]

STATE = [
    F(r"STATE|STATE_ABBR|STATE_ABBREV|STATE_CODE|STATECODE|ST|STATE_ABBR_1|STATE_CD|STATE_CODE_1", "norm_state", "native"),
    F(r"STATE_NAME", "name_to_abbr", "derived"),
]

ZIP5 = [
    F(r"ZIP|ZIPCODE|ZIP_CODE|ZIP_5|ZIP5|POSTAL_CODE|POSTALCODE|POSTCODE|ZCTA|ZCTA5|SITUS_ZIP|ADDRESS_ZIP|"
      r"ADDR_ZIP|MAIL_ZIP|CITY_ZIP|PROP_ZIP|ZIPCODE_1|ZIPCODE_5|POSTAL|POSTAL_CODE|POSTALCODE|ADDR_POSTCODE|"
      r"ADR_ZIP5|PSTLZIP5|SZIP5|ZIP_5|IN_POSTAL", "norm_zip", "native"),
    # POSTAL 列在不同层语义不同（有的存 ZIP 有的存城市名），靠 5 位校验按层裁决
    F(r"POSTAL", "norm_zip", "native"),
]

LATITUDE = [F(r"LATITUDE|LAT|Y|Y_COORD|POINT_Y|LAT_DD|LATITUDE_DEC|CENTROID_Y|LAT_Y|LATITUDE_1|Y_LAT", "trim", "native")]
LONGITUDE = [F(r"LONGITUDE|LON|LNG|LONG|X|X_COORD|POINT_X|LON_DD|LONGITUDE_DEC|CENTROID_X|LON_X|LONGITUDE_1|X_LON", "trim", "native")]

PARCEL_ID = [
    F(r"PARCELID|PARCEL_ID|PARCEL_NUMBER|PARCELNUM|PARCELNUMB|PARCEL_NO|PARCEL_NUM|PARCEL_NUM_1|PARCEL",
      "trim", "native"),
    F(r"APN|APN_1|PIN|PIN_NUM|PIN_1|GEO_PIN|TAXPIN|TAX_PIN|TAXID|TAX_ID|ACCOUNT|ACCT|ACCOUNT_NUM|PARCEL_ACCT|"
      r"PARCEL_ACCOUNT|PID|PID_NUM", "trim", "native"),
]

ALLOWED_SRC_KINDS = ["address_point", "parcel_situs", "street_line"]

# 稀疏字段允许的最低非空率（门牌/街名/zip/city 要求更高）
MIN_RATE = {"default": 0.02}
MIN_RATE_LOW = 0.005

STATE_ABBR = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR", "CALIFORNIA": "CA",
    "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE", "DISTRICT OF COLUMBIA": "DC",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID", "ILLINOIS": "IL",
    "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS", "KENTUCKY": "KY", "LOUISIANA": "LA",
    "MAINE": "ME", "MARYLAND": "MD", "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
    "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
    "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC", "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT", "VERMONT": "VT", "VIRGINIA": "VA",
    "WASHINGTON": "WA", "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
    "PUERTO RICO": "PR", "GUAM": "GU", "VIRGIN ISLANDS": "VI", "AMERICAN SAMOA": "AS",
    "NORTHERN MARIANA ISLANDS": "MP",
}
ABBR = set(STATE_ABBR.values())


# ---------------------------------------------------------------- 工具
def load_profiles() -> tuple[list[dict], dict]:
    """按 layer_id 去重（同层可能在 step04/step05 双账）；返回 (layers, dup_index)。"""
    best: dict[str, dict] = {}
    dup: dict[str, list] = {}
    for f in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        lid = d.get("layer_id")
        if lid in best:
            dup.setdefault(lid, [(best[lid].get("tag"), best[lid].get("sampled"))])
            dup[lid].append((d.get("tag"), d.get("sampled")))
            if (d.get("sampled") or 0) > (best[lid].get("sampled") or 0):
                best[lid] = d
        else:
            best[lid] = d
    return list(best.values()), dup


def load_csv_meta() -> dict:
    """layer_id -> {state, url, rows, geom, csv}"""
    import csv

    meta = {}
    for name in ("address_layers.csv", "situs_layers.csv"):
        p = os.path.join(ROOT, "collect", name)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                lid = (r.get("layer_id") or "").strip()
                if not lid or lid in meta:
                    continue
                meta[lid] = {"state": (r.get("state") or "").strip().upper(),
                             "url": (r.get("url") or "").strip(),
                             "rows": (r.get("rows") or "").strip(),
                             "geom": (r.get("geom") or "").strip(),
                             "csv": name}
    return meta


def rate(f: dict) -> float:
    return (f.get("nonempty") or 0) / max(1, f.get("n") or 1)


def examples(f: dict) -> list:
    return [x for x in (f.get("ex") or []) if x not in (None, "")]


def is_bare_number(field: str, num_fields: dict) -> bool | None:
    """用逐层门牌分类判断该列是不是「裸门牌号」（而不是整串地址）。未知返回 None。"""
    b = num_fields.get(field)
    if not b:
        return None
    tot = sum(b.values())
    if tot < 5:
        return None
    good = sum(b.get(k, 0) for k in ("pure_num", "num_suffix", "range", "zero"))
    return good / tot >= 0.5


def pick(fields: dict, table: list, num_fields: dict | None = None, min_rate: float = 0.02,
         bare_check: bool = False, validator=None):
    """按优先级返回 (src, transform, quality, rate)。全空/不满足校验的候选跳过，继续找下一个。

    bare_check 只对「裸门牌号候选」生效：整串地址（transform=extract_number）本来就会被判为非裸，跳过校验。
    """
    names = list(fields)
    for rx, transform, quality in table:
        r = re.compile(rx, re.I)
        hit = [n for n in names if r.match(n)]
        hit.sort(key=lambda n: -rate(fields[n]))
        for n in hit:
            rt = rate(fields[n])
            if rt < min_rate:
                continue
            if bare_check and transform != "extract_number" and is_bare_number(n, num_fields or {}) is False:
                continue
            if validator is not None and not validator(n):
                continue
            return n, transform, quality, rt
    return None, None, None, 0.0


def norm_dir(v: str) -> str | None:
    m = {"N": "North", "S": "South", "E": "East", "W": "West", "NE": "Northeast", "NW": "Northwest",
         "SE": "Southeast", "SW": "Southwest", "NORTH": "North", "SOUTH": "South", "EAST": "East",
         "WEST": "West", "NORTHEAST": "Northeast", "NORTHWEST": "Northwest", "SOUTHEAST": "Southeast",
         "SOUTHWEST": "Southwest"}
    k = (v or "").strip().upper().replace(".", "")
    if k in m:
        return m[k]
    k2 = {"N E": "NE", "N W": "NW", "S E": "SE", "S W": "SW"}.get(k)
    return m.get(k2) if k2 else None


def norm_post_type(v: str) -> str | None:
    m = {"ST": "Street", "STR": "Street", "STREET": "Street", "AVE": "Avenue", "AV": "Avenue",
         "AVENUE": "Avenue", "RD": "Road", "ROAD": "Road", "DR": "Drive", "DRIVE": "Drive",
         "LN": "Lane", "LANE": "Lane", "BLVD": "Boulevard", "BOULEVARD": "Boulevard",
         "CT": "Court", "COURT": "Court", "CIR": "Circle", "CIRCLE": "Circle", "PL": "Place",
         "PLACE": "Place", "TER": "Terrace", "TERRACE": "Terrace", "PKWY": "Parkway",
         "PARKWAY": "Parkway", "HWY": "Highway", "HIGHWAY": "Highway", "TRL": "Trail",
         "TRAIL": "Trail", "SQ": "Square", "SQUARE": "Square", "WAY": "Way", "LOOP": "Loop",
         "PT": "Point", "POINT": "Point", "PASS": "Pass", "PATH": "Path", "RUN": "Run",
         "XING": "Crossing", "CROSSING": "Crossing", "ALY": "Alley", "ALLEY": "Alley"}
    k = (v or "").strip().upper().rstrip(".")
    return m.get(k)


def norm_zip(v) -> str | None:
    """取前 5 位数字；不足 5 位返回 None（补零＝伪造，4 位多半是源端丢位）。"""
    digits = re.sub(r"\D", "", str(v))
    if len(digits) < 5:
        return None
    return digits[:5]


def norm_fips(v) -> str | None:
    digits = re.sub(r"\D", "", str(v))
    if len(digits) == 4:
        return "0" + digits
    if len(digits) == 5:
        return digits
    return None


def norm_county(v) -> str | None:
    s = str(v).strip()
    if not s or s.isdigit():
        return None
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+COUNTY$", "", s, flags=re.I)
    return s.title() if s.isupper() else s


def has_cand(fields: dict, table: list) -> bool:
    names = list(fields)
    for rx, _t, _q in table:
        r = re.compile(rx, re.I)
        if any(r.match(n) for n in names):
            return True
    return False


def has_letters(f: dict) -> bool:
    return any(re.search(r"[A-Za-z]{2,}", str(x)) for x in examples(f))


def looks_house_number(f: dict) -> bool:
    return any(extract_number(x) for x in examples(f))


def looks_lat(f: dict) -> bool:
    for x in examples(f):
        try:
            v = float(x)
        except Exception:  # noqa: BLE001
            continue
        if 15 <= abs(v) <= 75:
            return True
    return False


def looks_lon(f: dict) -> bool:
    for x in examples(f):
        try:
            v = float(x)
        except Exception:  # noqa: BLE001
            continue
        if 60 <= abs(v) <= 180:
            return True
    return False


def extract_number(v) -> str | None:
    m = re.match(r"\s*(\d+[A-Za-z]?)", str(v))
    return m.group(1) if m else None


def strip_number(v) -> str | None:
    s = re.sub(r"^\s*\d+[A-Za-z]?(?:-\d+)?\s+", "", str(v)).strip()
    # 只有数字/切完啥也不剩 → 不是街名（实测有层的 ADDRESS 只存门牌号）
    if not s or not re.search(r"[A-Za-z]", s):
        return None
    return s


def strip_type_dir(v) -> str | None:
    """从 street_full 里剥掉尾部的类型/方向词，近似 street_name（低置信，标 extracted）。"""
    s = str(v).strip()
    toks = s.split()
    while toks and (norm_post_type(toks[-1]) or norm_dir(toks[-1])):
        toks.pop()
    return " ".join(toks) or None


def norm_state(v) -> str | None:
    s = str(v).strip().upper()
    if len(s) == 2 and s in ABBR:
        return s
    return STATE_ABBR.get(s)


# ---------------------------------------------------------------- TIGER 县界
_IDX: dict = {}


def tiger_index(st: str):
    if not st or CT is None or st not in getattr(CT, "STATE_FIPS", {}):
        return None
    if st not in _IDX:
        try:
            _IDX[st] = CT.fetch_state(st)
        except Exception as e:      # noqa: BLE001
            print("⚠️ TIGER 县界取不到 %s：%s" % (st, str(e)[:80]))
            _IDX[st] = None
    return _IDX[st]


def tiger_county_from_layer(lid: str, url: str, st: str):
    """从层 id/url 反查县：先找 `Xxx_County`，再用「州内县名出现在层名里且唯一」兜底。"""
    idx = tiger_index(st)
    if idx is None:
        return None
    hit = CT.county_from_text(lid + " " + url, idx)
    if hit:
        return hit
    key = CT._key(lid + " " + url)
    cands = [f for f, e in idx.by_fips.items()
             if len(e["name"]) >= 5 and CT._key(e["name"]) in key]
    if len(cands) == 1:
        e = idx.by_fips[cands[0]]
        return (e["name"], e["fips"])
    return None


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "schema", "field-map-v2.json"))
    a = ap.parse_args()

    if not os.path.exists(SCHEMA_PIN):
        raise SystemExit("缺 SCHEMA 2.0 原样副本：%s" % SCHEMA_PIN)
    raw = open(SCHEMA_PIN, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != SCHEMA_SHA256:
        raise SystemExit("SCHEMA 副本 sha256 不符（%s != %s），拒绝继续" % (got, SCHEMA_SHA256))
    schema = json.loads(raw)
    prim = [f["name"] for f in schema["primary_fields"]]

    TARGETS = ["house_number", "house_number_suffix", "street_pre_dir", "street_name",
               "street_post_type", "street_post_dir", "street_full", "unit", "postal_city",
               "municipal_city", "county_name", "county_fips", "state_abbr", "zip5",
               "latitude", "longitude", "addr_type", "full_formatted_address", "source_confidence"]
    missing = [t for t in TARGETS if t not in prim]
    if missing:
        raise SystemExit("目标字段不在 SCHEMA 2.0 主字段里：%s" % missing)

    layers, dup = load_profiles()
    meta = load_csv_meta()
    if not layers:
        raise SystemExit("analysis/out 为空")

    out_layers: dict[str, dict] = {}
    cov = {t: {"with_source": 0, "null": 0, "layer_meta": 0, "derived_const": 0,
               "derived_formula": 0, "reasons": {}} for t in TARGETS}
    kind_n = {}
    meta_hit = 0

    for d in layers:
        lid = d["layer_id"]
        kind = d.get("kind") or ""
        kind_n[kind] = kind_n.get(kind, 0) + 1
        fields = d.get("fields") or {}
        nums = d.get("num_fields") or {}
        m = meta.get(lid) or {}
        if m:
            meta_hit += 1
        ent = {"src_kind": kind if kind in ALLOWED_SRC_KINDS else None,
               "src_layer_id": lid,
               "src_layer_url": m.get("url") or None,
               "src_parcel_id": None,
               "rows_total": d.get("rows_total"),
               "sampled": d.get("sampled"),
               "csv": m.get("csv")}

        def put(name: str, src, transform=None, quality=None, rt=None, reason=None, value_rule=None):
            e = {}
            if src:
                e["src"] = src
            elif reason:
                e["src"] = None
                e["reason"] = reason
            if rt is not None:
                e["nonempty_rate"] = round(rt, 3)
            if transform and transform != "native":
                e["transform"] = transform
            if quality:
                e["quality"] = quality
            if value_rule:
                e["value_rule"] = value_rule
            ent[name] = e if e else {"src": None}
            return e

        # ---- 门牌号（裸列优先，整串地址兜底并标 extracted）
        src, tr, q, rt = pick(fields, HOUSE_NUMBER, nums, 0.02, bare_check=True,
                              validator=lambda n: looks_house_number(fields[n]))
        if src:
            e = put("house_number", src, tr, q, rt)
            b = nums.get(src) or {}
            tot = sum(b.values())
            if tot and b.get("zero", 0) / tot > 0.05:
                e["zero_share"] = round(b["zero"] / tot, 3)
            cov["house_number"]["with_source"] += 1
        else:
            if has_cand(fields, [x for x in HOUSE_NUMBER if x[1] == "extract_number"]):
                why, key = "有整串地址列但示例值切不出首段数字", "整串列切不出门牌号"
            else:
                why, key = "无门牌号列，且无整串地址列", "无门牌号列"
            put("house_number", None, reason=why)
            cov["house_number"]["null"] += 1
            cov["house_number"]["reasons"][key] = cov["house_number"]["reasons"].get(key, 0) + 1

        # ---- 门牌后缀
        src, tr, q, rt = pick(fields, HOUSE_NUMBER_SUFFIX, nums, MIN_RATE_LOW, bare_check=True)
        if src:
            put("house_number_suffix", src, tr, q, rt)
            cov["house_number_suffix"]["with_source"] += 1
        else:
            put("house_number_suffix", None, reason="无后缀列（SCHEMA 记「实测全源 0%」，三仓同样普遍缺）")
            cov["house_number_suffix"]["null"] += 1
            cov["house_number_suffix"]["reasons"]["无后缀列"] = cov["house_number_suffix"]["reasons"].get("无后缀列", 0) + 1

        # ---- 街名前向/后向方向词、类型
        src, tr, q, rt = pick(fields, STREET_PRE_DIR, nums, MIN_RATE_LOW,
                              validator=lambda n: any(norm_dir(x) for x in examples(fields[n])))
        if src:
            put("street_pre_dir", src, tr, q, rt)
            cov["street_pre_dir"]["with_source"] += 1
        else:
            put("street_pre_dir", None, reason="无 pre-dir 列（层内方向词通常已并入街名）")
            cov["street_pre_dir"]["null"] += 1
            cov["street_pre_dir"]["reasons"]["无列"] = cov["street_pre_dir"]["reasons"].get("无列", 0) + 1

        # 若 house_number 来自整串地址列，street_name 必须从同一列切（同一行才对得上）
        sn_table = STREET_NAME
        if ent.get("house_number", {}).get("transform") == "extract_number":
            sn_table = [F(re.escape(ent["house_number"]["src"]), "strip_number", "extracted")] + STREET_NAME
        src, tr, q, rt = pick(fields, sn_table, nums, 0.02)
        if src:
            put("street_name", src, tr, q, rt)
            cov["street_name"]["with_source"] += 1
        else:
            put("street_name", None,
                reason=("有整串地址列但切不出街名" if has_cand(fields, STREET_FULL) else "无街名列"))
            cov["street_name"]["null"] += 1
            cov["street_name"]["reasons"]["无街名列"] = cov["street_name"]["reasons"].get("无街名列", 0) + 1

        src, tr, q, rt = pick(fields, STREET_POST_TYPE, nums, MIN_RATE_LOW,
                              validator=lambda n: any(norm_post_type(x) for x in examples(fields[n])))
        if src:
            put("street_post_type", src, tr, q, rt)
            cov["street_post_type"]["with_source"] += 1
        else:
            put("street_post_type", None, reason="无街名类型列（后缀常已并入街名，需按词表切分）")
            cov["street_post_type"]["null"] += 1
            cov["street_post_type"]["reasons"]["无列"] = cov["street_post_type"]["reasons"].get("无列", 0) + 1

        src, tr, q, rt = pick(fields, STREET_POST_DIR, nums, MIN_RATE_LOW,
                              validator=lambda n: any(norm_dir(x) for x in examples(fields[n])))
        if src:
            put("street_post_dir", src, tr, q, rt)
            cov["street_post_dir"]["with_source"] += 1
        else:
            put("street_post_dir", None, reason="无 post-dir 列（SCHEMA 记「极稀疏」）")
            cov["street_post_dir"]["null"] += 1
            cov["street_post_dir"]["reasons"]["无列"] = cov["street_post_dir"]["reasons"].get("无列", 0) + 1

        src, tr, q, rt = pick(fields, STREET_FULL, nums, 0.02, validator=lambda n: has_letters(fields[n]))
        if src:
            put("street_full", src, tr, q, rt)
            cov["street_full"]["with_source"] += 1
        else:
            put("street_full", None, reason="无整串街名列；可由 street_name+post_type+dirs 合成")
            cov["street_full"]["null"] += 1
            cov["street_full"]["reasons"]["无列"] = cov["street_full"]["reasons"].get("无列", 0) + 1

        # ---- unit
        # unit 值可以是纯数字（如 "12"），不做字母校验，但已在别名表里排除 UNIT_TYPE/UNITS 计数列
        src, tr, q, rt = pick(fields, UNIT, nums, MIN_RATE_LOW)
        if src and re.match(r"^(UNITID|UNIT_ID)$", src, re.I):
            # E911 的 UNITID 常混状态码（实测有 "PKG"/"RPDSEC"），信任度降级
            q = "native_weak"
        if src:
            put("unit", src, tr, q, rt)
            cov["unit"]["with_source"] += 1
        else:
            put("unit", None, reason="无 unit 列（SCHEMA 记 Overture 可补 4.4%）")
            cov["unit"]["null"] += 1
            cov["unit"]["reasons"]["无列"] = cov["unit"]["reasons"].get("无列", 0) + 1

        # ---- city：postal_city 与 municipal_city 严格分开（不许混用）
        src, tr, q, rt = pick(fields, POSTAL_CITY, nums, 0.02, validator=lambda n: has_letters(fields[n]))
        if src:
            put("postal_city", src, tr, q, rt)
            cov["postal_city"]["with_source"] += 1
        else:
            put("postal_city", None, reason="无城市列；USPS 邮件城市需外部权威源，不伪造")
            cov["postal_city"]["null"] += 1
            cov["postal_city"]["reasons"]["无列"] = cov["postal_city"]["reasons"].get("无列", 0) + 1

        src, tr, q, rt = pick(fields, MUNICIPAL_CITY, nums, MIN_RATE_LOW,
                              validator=lambda n: has_letters(fields[n]))
        if src:
            put("municipal_city", src, tr, q, rt)
            cov["municipal_city"]["with_source"] += 1
        else:
            has_city = any(re.match(r"^(CITY|CITY_NAME)$", n, re.I) for n in fields)
            why = ("只有 CITY 列（可能是邮寄城市，v2 语义收紧后不得复用）→ 需 tiger places 回填"
                   if has_city else "无 Inc_Muni/Municipality 列 → 需 tiger places 回填")
            put("municipal_city", None, reason=why)
            cov["municipal_city"]["null"] += 1
            cov["municipal_city"]["reasons"]["需 tiger places 回填"] = \
                cov["municipal_city"]["reasons"].get("需 tiger places 回填", 0) + 1

        # ---- county：源列 → TIGER 县名回填（层 id/url）→ 逐行多边形判定
        c_src, c_tr, c_q, c_rt = pick(fields, COUNTY_NAME, nums, MIN_RATE_LOW,
                                      validator=lambda n: any(norm_county(x) for x in examples(fields[n])))
        f_src, f_tr, f_q, f_rt = pick(fields, COUNTY_FIPS, nums, MIN_RATE_LOW,
                                      validator=lambda n: any(norm_fips(x) for x in examples(fields[n])))
        county_from = None
        if c_src or f_src:
            county_from = "column"
        else:
            hit = None
            if CT is not None:
                hit = tiger_county_from_layer(lid, m.get("url") or "",
                                              (m.get("state") or "").upper())
            if hit:
                county_from = "tiger_layer_name"
                ent["county_name"] = {"src": "[[layer_name→tiger_county]]", "quality": "derived",
                                      "value": hit[0], "fips": hit[1], "reason": None}
                ent["county_name"].pop("reason")
                ent["county_fips"] = {"src": "[[tiger_county.GEOID]]", "quality": "derived",
                                      "value": hit[1]}
                cov["county_name"]["layer_meta"] += 1
                cov["county_fips"]["layer_meta"] += 1
        if county_from == "column":
            if c_src:
                put("county_name", c_src, c_tr, c_q, c_rt)
                cov["county_name"]["with_source"] += 1
            else:
                put("county_name", None, reason="无县名列（FIPS 列有，名可由 TIGER 反查）")
                cov["county_name"]["null"] += 1
                cov["county_name"]["reasons"]["无列"] = cov["county_name"]["reasons"].get("无列", 0) + 1
            if f_src:
                put("county_fips", f_src, f_tr, f_q, f_rt)
                cov["county_fips"]["with_source"] += 1
            else:
                put("county_fips", None, reason="无 FIPS 列（县名有，FIPS 可由 TIGER 反查）")
                cov["county_fips"]["null"] += 1
                cov["county_fips"]["reasons"]["无列"] = cov["county_fips"]["reasons"].get("无列", 0) + 1
        elif county_from != "tiger_layer_name":
            # 层跨多县（州级/多县层）：county 必须逐行用 TIGER 多边形判定，不能在层级别写死
            has_geo = bool((d.get("norm") or {}).get("lat", {}).get("nonempty"))
            why = ("层跨多县 → 逐行 TIGER 多边形判定（禁用 bbox）" if has_geo
                   else "层跨多县且无坐标 → 无法判县（geo_missing）")
            put("county_name", None, reason=why)
            put("county_fips", None, reason=why)
            cov["county_name"]["null"] += 1
            cov["county_fips"]["null"] += 1
            cov["county_name"]["reasons"]["跨多县"] = cov["county_name"]["reasons"].get("跨多县", 0) + 1
            cov["county_fips"]["reasons"]["跨多县"] = cov["county_fips"]["reasons"].get("跨多县", 0) + 1
        ent["county_scope"] = "single" if county_from == "tiger_layer_name" or (
            county_from == "column" and (ent.get("county_fips") or {}).get("src")) else "multi"
        ent["county_src"] = county_from

        # ---- state：列优先，其次层元数据（州是分片作用域属性）
        src, tr, q, rt = pick(fields, STATE, nums, 0.5,
                              validator=lambda n: any(norm_state(x) for x in examples(fields[n])))
        if src:
            put("state_abbr", src, tr, q, rt)
            ent["state_src"] = "column"
            cov["state_abbr"]["with_source"] += 1
        if not src:
            st = m.get("state") or ""
            if norm_state(st):
                # 州是分片作用域属性，层内恒成立（SCHEMA note: 县片内实测 100% 等于本州）
                ent_state = put("state_abbr", "[[layer_meta.state]]", "layer_meta", "layer_meta", 1.0)
                ent_state["scope_const"] = True
                ent_state["value"] = norm_state(st)
                ent["state_src"] = "layer_meta"
                cov["state_abbr"]["layer_meta"] += 1
            else:
                put("state_abbr", None, reason="列与层元数据都没有可用的州码")
                ent["state_src"] = None
                cov["state_abbr"]["null"] += 1
                cov["state_abbr"]["reasons"]["无州码"] = cov["state_abbr"]["reasons"].get("无州码", 0) + 1

        # ---- zip5
        src, tr, q, rt = pick(fields, ZIP5, nums, 0.02,
                              validator=lambda n: any(norm_zip(x) for x in examples(fields[n])))
        if src:
            put("zip5", src, tr, q, rt)
            cov["zip5"]["with_source"] += 1
        else:
            put("zip5", None, reason="无 ZIP 列（ZCTA 回填须标 zcta_derived，不得当原生值）")
            cov["zip5"]["null"] += 1
            cov["zip5"]["reasons"]["无列"] = cov["zip5"]["reasons"].get("无列", 0) + 1

        # ---- lat / lon：列优先，其次 geometry（采集器已归一）
        n = d.get("norm") or {}
        for name, table, norm_key, geo in (("latitude", LATITUDE, "lat", "[[geometry.y]]"),
                                           ("longitude", LONGITUDE, "lon", "[[geometry.x]]")):
            vlat = looks_lat if name == "latitude" else looks_lon
            src, tr, q, rt = pick(fields, table, nums, 0.02, validator=lambda n: vlat(fields[n]))
            if src:
                put(name, src, tr, q, rt)
                cov[name]["with_source"] += 1
            elif (n.get(norm_key) or {}).get("nonempty"):
                r2 = (n[norm_key]["nonempty"] / max(1, n[norm_key]["n"]))
                put(name, geo, "geometry", "geometry", r2)
                cov[name]["with_source"] += 1
            else:
                put(name, None, reason="无坐标列且 geometry 不可用")
                cov[name]["null"] += 1
                cov[name]["reasons"]["无坐标"] = cov[name]["reasons"].get("无坐标", 0) + 1

        # ---- 三仓溯源：src_parcel_id（宗地层专用）
        if kind == "parcel_situs":
            src, tr, q, rt = pick(fields, PARCEL_ID, nums, MIN_RATE_LOW)
            if src:
                ent["src_parcel_id"] = {"src": src, "nonempty_rate": round(rt, 3), "transform": "trim"}
            else:
                ent["src_parcel_id"] = {"src": None, "reason": "宗地层无 parcel id 列（APN/PIN/ParcelID 均缺）"}
        else:
            ent["src_parcel_id"] = None

        # ---- addr_type / full_formatted_address / source_confidence：无源列 → 规则或 null
        put("addr_type", None, reason="无源列，规则见 value_rules.addr_type（本轮不落值）",
            value_rule="value_rules.addr_type")
        cov["addr_type"]["null"] += 1
        cov["addr_type"]["reasons"]["无源列（规则重分类）"] = cov["addr_type"]["reasons"].get("无源列（规则重分类）", 0) + 1

        put("full_formatted_address", None, value_rule="value_rules.full_formatted_address")
        cov["full_formatted_address"]["derived_formula"] += 1
        ent["full_formatted_address"]["derivable"] = True

        put("source_confidence", None, value_rule="value_rules.source_confidence")
        cov["source_confidence"]["derived_const"] += 1
        ent["source_confidence"]["proposed_value"] = "B-Tier"

        # ---- 汇总该层可用性
        blocking = [k for k in ("house_number", "street_name", "state_abbr")
                    if not (ent.get(k) or {}).get("src")]
        ent["blocking"] = blocking
        ent["mappable_primary"] = sum(1 for t in TARGETS if (ent.get(t) or {}).get("src"))
        out_layers[lid] = ent

    doc = {
        "artifact": "field-map/v2",
        "not_a_schema": True,
        "note": "这是逐层字段映射表，不是 schema。所有目标字段名逐字取自二仓 LOCKED SCHEMA 2.0，"
                "本文件不新增、不改名、不重定义任何规范字段。",
        "schema_ref": {
            "repo": "ip9988001/world-map-data-test",
            "path": "schema/SCHEMA.json",
            "schema_version": schema["schema_version"],
            "status": schema["status"],
            "frozen_at": schema["frozen_at"],
            "pinned_copy": "schema/upstream/SCHEMA-v2.0.world-map-data-test.json",
            "sha256": SCHEMA_SHA256,
            "commit": "514f12f",  # rev2 · minor additive（+src_kind/src_layer_id/src_layer_url/src_parcel_id）
            "rev": schema.get("rev"),
        },
        "generated_at": "2026-10-30",
        "sources": {
            "profiles": "analysis/out/*.json（逐层值分布画像，未重跑）",
            "layer_meta": ["collect/address_layers.csv", "collect/situs_layers.csv"],
            "network": "none（只读 GitHub Release 既有资产的结果，未访问上游 ArcGIS/Census）",
        },
        "target_fields": [],
        "provenance_ext": {},
        "value_rules": {},
        "layers": out_layers,
        "coverage": {},
    }

    # ---- 目标字段覆盖统计
    n_layer = len(out_layers)
    for t in TARGETS:
        c = cov[t]
        with_src = c["with_source"] + c["layer_meta"]
        derivable = sum(1 for e in out_layers.values()
                        if (e.get(t) or {}).get("derivable") or (e.get(t) or {}).get("proposed_value"))
        doc["target_fields"].append({
            "name": t,
            "layers_derivable": derivable,
            "schema_type": next(f for f in schema["primary_fields"] if f["name"] == t)["type"],
            "schema_null": next(f for f in schema["primary_fields"] if f["name"] == t)["null"],
            "layers_with_source": with_src,
            "layers_from_column": c["with_source"],
            "layers_from_layer_meta": c["layer_meta"],
            "layers_null": c["null"],
            "layers_rule": c["derived_const"] + c["derived_formula"],
            "coverage_pct": round(100.0 * with_src / max(1, n_layer), 2),
            "coverage_pct_with_derived": round(100.0 * (with_src + derivable) / max(1, n_layer), 2),
            "null_reasons": dict(sorted(c["reasons"].items(), key=lambda x: -x[1])),
        })

    # ---- 4 个三仓溯源字段建议
    src_kind_n = {}
    for e in out_layers.values():
        k = e["src_kind"] or "null"
        src_kind_n[k] = src_kind_n.get(k, 0) + 1
    parcel_with_id = sum(1 for e in out_layers.values()
                         if isinstance(e.get("src_parcel_id"), dict) and e["src_parcel_id"].get("src"))
    url_n = sum(1 for e in out_layers.values() if e.get("src_layer_url"))
    doc["provenance_ext"] = {
        "status": "proposal（需并回二仓 SCHEMA 2.0 的溯源附录；未改动 SCHEMA 本体）",
        "why": "二仓 19 个溯源列面向 NAD/TIGER/OA/Overture，三仓（ArcGIS 点层/宗地层）没有这些 id，"
               "必须用 4 个自有列才可回溯到原始层与原始宗地，否则地址无法审计。",
        "fields": [
            {"name": "src_kind", "type": "enum", "nullable": False,
             "enum": ALLOWED_SRC_KINDS,
             "取值规则": "层几何/来源判定：点层=address_point，宗地层=parcel_situs；street_line 三仓暂无，保留待用",
             "实测分布": src_kind_n},
            {"name": "src_layer_id", "type": "string", "nullable": False,
             "取值规则": "三仓层标识（ArcGIS service 层名规范化），即 Release tag `collect-step<NN>-<layer_id>` 里的那段",
             "覆盖": f"{n_layer}/{n_layer}"},
            {"name": "src_layer_url", "type": "string", "nullable": True,
             "取值规则": "层元数据里的 ArcGIS REST 端点（来自 collect/*_layers.csv，仅记录不访问）",
             "覆盖": f"{url_n}/{n_layer}"},
            {"name": "src_parcel_id", "type": "string", "nullable": True,
             "取值规则": "仅 parcel_situs 层：源层 parcel id 列（ParcelID/APN/PIN/PARCEL_NUMBER…）；点层恒为 null",
             "覆盖": f"{parcel_with_id}/{kind_n.get('parcel_situs', 0)} 宗地层"},
        ],
    }
    doc["value_rules"] = {
        "state_abbr": "列优先（STATE/State/ST…，需 2 位合法州码）；无列时取层元数据 state（州是分片作用域属性，"
                      "SCHEMA 亦记「县片内实测 100% 等于本州」）",
        "zip5": "去非数字后取前 5 位；不足 5 位一律 null（**不左补零**——补零会造出看着合法、实为错误的 0xxxx 邮编）；"
                "ZIP4/Plus4 列不取；ZCTA 回填必须另标 zip_source=zcta_derived",
        "county_name": "取 County/CountyName/CNTY_NAME，去尾部 ' County'，大小写归一；纯数字列视为 FIPS 不当县名",
        "county_fips": "候选列示例值必须是 4~5 位数字（4 位左补 0），否则拒用留 null",
        "street_post_type": "归一为全称（ST→Street, AVE→Avenue…），词表见 VALUE-PROFILE 与 SCHEMA note",
        "street_pre_dir/street_post_dir": "归一为 North/South/East/West/Northeast/Northwest/Southeast/Southwest 全拼",
        "house_number": "裸列优先；只有整串地址时按正则 ^(\\d+[A-Za-z]?) 切首段并标 quality=extracted；"
                        "0 值比例写入 zero_share（SCHEMA 允许原样保留，但下游应视 0 为无门牌号）",
        "unit": "只在有独立 unit 列时取；拆不出则 null（不把 UNIT_TYPE/UNITS 计数当 unit）",
        "addr_type": "无源列 → 全部 null + 建议规则：unit 非空 → Residential (Multi-Unit)；parcel_situs 无证据 → Unknown；"
                      "层标题含 COMMERCIAL/BUSINESS → Commercial；其余 Residential（需上游确认后才落值）",
        "full_formatted_address": "合成：house_number + ' ' + street_full + ', ' + postal_city + ', ' + state_abbr + ' ' + zip5；"
                                  "缺项退化为 house_number + ' ' + street_full + ', ' + state_abbr",
        "source_confidence": "三仓单层单源 → 恒 B-Tier（符合 SCHEMA grade_rules：只有 1 个独立源即 B-Tier；"
                             "S/A 需 NAD+TIGER+OA 多源 join 后才可升级）",
    }
    def _has(e, f):
        return bool((e.get(f) or {}).get("src"))

    def _geo(e):
        return _has(e, "latitude") and _has(e, "longitude")

    u1 = sum(1 for e in out_layers.values()
             if _has(e, "house_number") and _has(e, "street_name") and e.get("state_src") == "column")
    u2 = sum(1 for e in out_layers.values()
             if _has(e, "house_number") and _has(e, "street_name") and (e.get("state_abbr") or {}).get("src"))
    u3 = sum(1 for e in out_layers.values()
             if _has(e, "house_number") and _has(e, "street_name")
             and (e.get("state_abbr") or {}).get("src")
             and (e.get("county_scope") == "single" or _geo(e)))
    total_rows = sum((e.get("rows_total") or 0) for e in out_layers.values())
    row_cov = {}
    for t in TARGETS:
        w = sum((e.get("rows_total") or 0) for e in out_layers.values() if (e.get(t) or {}).get("src"))
        est = sum((e.get("rows_total") or 0) * float((e.get(t) or {}).get("nonempty_rate") or 0)
                  for e in out_layers.values())
        row_cov[t] = {"rows_in_layers_with_source": w,
                      "row_coverage_pct": round(100.0 * w / max(1, total_rows), 2),
                      "rows_est_nonnull": int(est),
                      "rows_est_nonnull_pct": round(100.0 * est / max(1, total_rows), 2)}
    doc["coverage"] = {
        "layers_profiled": n_layer,
        "profile_files": n_layer + len(dup),
        "duplicate_layer_ids": {k: v for k, v in dup.items()},
        "duplicate_note": "同一 layer_id 在两个阶段各发了一个 Release（rows_total 完全一致），"
                          "映射按 layer_id 去重只留一条（取抽样最多者），行数不重复计。",
        "rows_total_declared": total_rows,
        "row_weighted": row_cov,
        "by_kind": kind_n,
        "layer_meta_joined": meta_hit,
        "blocking_none": sum(1 for e in out_layers.values() if not e["blocking"]),
        "blocking_house_number_or_street": sum(1 for e in out_layers.values()
                                              if set(e["blocking"]) & {"house_number", "street_name"}),
        "mappable_primary_avg": round(sum(e["mappable_primary"] for e in out_layers.values()) / max(1, n_layer), 2),
        "usable_v1_state_column_only": u1,
        "usable_v1_pct": round(100.0 * u1 / max(1, n_layer), 2),
        "usable_v2_after_state_backfill": u2,
        "usable_v2_pct": round(100.0 * u2 / max(1, n_layer), 2),
        "usable_v3_after_county": u3,
        "usable_v3_pct": round(100.0 * u3 / max(1, n_layer), 2),
        "county_layer_level": sum(1 for e in out_layers.values() if e.get("county_scope") == "single"),
        "county_multi_row_pip": sum(1 for e in out_layers.values() if e.get("county_scope") == "multi"),
        "county_multi_no_geo": sum(1 for e in out_layers.values()
                                   if e.get("county_scope") == "multi" and not _geo(e)),
        "targets": len(TARGETS),
    }

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote", a.out, os.path.getsize(a.out), "bytes")
    for t in doc["target_fields"]:
        print("%-26s src=%4d meta=%4d null=%4d rule=%4d  %5.1f%%" % (
            t["name"], t["layers_from_column"], t["layers_from_layer_meta"], t["layers_null"],
            t["layers_rule"], t["coverage_pct"]))
    print("blocking_none=", doc["coverage"]["blocking_none"], "avg_mappable=", doc["coverage"]["mappable_primary_avg"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
