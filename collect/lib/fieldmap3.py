# -*- coding: utf-8 -*-
"""字段映射 v3 —— 在**已发布记录**上取地址字段，缺失时回落到 `raw`（上游原始属性）。

为什么需要它（实测，见 docs/08-DEDUP-PLAN-DRAFT.md 5.2 #1）：
  采集侧 `collect/lib/schema.py` 的 `F_ADD/F_ST/F_ZIP` 只认 7/5/5 个名字，
  抽的 3 个层里有 2 层 `add_num` 命中率 **0%**：
    · `AddressPts_DamageAssessment_REA_VIEW` → 用的是 `STREET_NUMBER`
    · `WI_NG911_Site_Structure_Address_Points_2` → 用的是 NENA `Add_Number` / `St_Name` / `Post_Code`
  好消息：记录里 `raw` 保留了全部上游属性，所以**不用重采、不用访问上游**就能补全。

设计：先看采集侧已归一化的顶层字段（快、命中率大概率够），再看 `raw`（NENA / TIGER / 各家写法）。
返回里带 `*_src`，用于统计「顶层命中 vs raw 回退」的占比，落进 extract 报告。
"""
from __future__ import annotations

import re

F_ADD = ("ADD_NUM", "ADD_NUMBER", "ADDRNUM", "ADDRESS_NUMBER", "HOUSE_NUM", "HOUSENUM", "STREET_NUM",
         "ADDR_NO", "HOUSE_NBR", "HOUSENBR", "HSN", "BLDG_NUM", "SITUS_NUM", "ADDRNUMB",
         "ADDRESSNUM", "STREETNUMBER", "BUILDING_NUMBER", "PRIMARY_ADDRESS_NUMBER",
         # R1 实测补：锡达拉皮兹那套（HOUSENO / NAME / SUFTYPE）、IA Update（Add_Number / StreetName）
         "HOUSENO", "HOUSE_NO", "HOUSENO_1", "STR_NBR", "STREET_NBR", "ADD_NUMB")
F_ST = ("ST_NAME", "STREET", "STREET_NAME", "ROAD_NAME", "STR_NAME", "FULL_STREET_NAME",
        "LST_NAME", "LABEL", "ADDRESS_STREET",
        "STREETNAME", "ST_NAME_FULL", "STR_NAME_FULL")
F_SUF = ("ST_SUF", "STTYPE", "STREET_TYPE", "SUFFIX", "ST_POS_TYP", "POS_TYP", "STREET_SUFFIX",
         "ROAD_TYPE", "TYPE", "SUFTYPE", "SUF_TYPE", "STN_POSTYP", "STN_POS_TYP")
F_PRE = ("PRE_DIR", "PREDIR", "PRE_DIRECTION", "ST_PRE_DIR", "ST_PREDIR", "STREET_DIRECTION",
         "PRE_DIRECTIONAL", "DIRECTION", "STN_PREDIR", "STN_PRE_DIR")
F_POST = ("POST_DIR", "POSTDIR", "POST_DIRECTION", "ST_POS_DIR", "ST_POSTDIR",
          "POST_DIRECTIONAL", "SUFDIR", "SUF_DIR", "STN_POSDIR", "STN_POS_DIR")
F_UNIT = ("SUBNUM", "UNIT", "UNIT_NUM", "SUITE", "APT", "BLDG", "UNITID", "ADDTL_LOC",
          "ROOM", "UNIT_NO", "UNITNUMBER", "SUITE_NO", "UNITNO", "UNITNO_1")
F_ZIP = ("ZIP", "ZIPCODE", "ZIP_CODE", "POSTAL_CODE", "ZIP5", "POST_CODE", "POSTCODE",
         "ZIP_CODE_5")
F_CITY = ("CITY", "COMMUNITY", "MUNICIPALITY", "POST_CITY", "TOWN", "PLACE", "INC_MUNI",
          "MSAGCOMM", "POST_COMM", "CITY_NAME", "MAIL_CITY")
F_FULL = ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION",
          "FULL_STREET_ADDRESS", "MATCH_ADDR", "ADDRESS_FULL", "FULLADDRESS")
F_LAT = ("LAT", "LATITUDE", "LAT_DD", "Y", "Y_COORD", "YCORD", "LATITUDE_DD")
F_LON = ("LON", "LONG", "LONGITUDE", "LON_DD", "LON_DD83", "X", "X_COORD", "XCORD",
         "LONGITUDE_DD")

NAME_GUARD = ("HOUSENO", "HOUSE_NO", "ADD_NUMBER", "ADD_NUM", "STREET_NUMBER", "HOUSE_NBR",
              "STR_NBR", "HOUSENUM", "HOUSE_NUM")
_NUM_RE = re.compile(r"^\s*(\d+[0-9A-Za-z\-]*)")
_STRIP_NUM_RE = re.compile(r"^\s*\d+[0-9A-Za-z\-]*\s*")
# 自由文本地址尾巴：`... MARTELLE IA 52305` → 砍掉 `ST ZIP(+4)`
_TAIL_STATE_ZIP = re.compile(r"\s+[A-Z]{2}\s+\d{5}(?:-\d{4})?\s*$", re.I)
_ZIP_ONLY = re.compile(r"\s+\d{5}(?:-\d{4})?\s*$")
# 名字里夹带的单元：`412 3 ST S UNIT D COGGON` → unit=D，名字里去掉
_UNIT_IN_NAME = re.compile(r"(?i)\b(?:APT|APARTMENT|UNIT|STE|SUITE|BLDG|BLDG\.|RM|ROOM|FL|#)\s*"
                           r"([A-Z0-9]{1,6})\b")
_TYPE_TOKENS = None      # 延迟到 addrkey 表导入后初始化


def _norm_key(k) -> str:
    """字段名指纹：去掉大小写与下划线差异 —— `SiteAddress` / `SITE_ADDRESS` / `site_address`
    都是 `SITEADDRESS`。R1 实测：不做这一步，`SiteAddress` 这类驼峰值一个都匹配不上。"""
    return re.sub(r"[^A-Z0-9]", "", str(k).upper())


N_ADD = tuple(_norm_key(x) for x in F_ADD)
N_ST = tuple(_norm_key(x) for x in F_ST)
N_SUF = tuple(_norm_key(x) for x in F_SUF)
N_PRE = tuple(_norm_key(x) for x in F_PRE)
N_POST = tuple(_norm_key(x) for x in F_POST)
N_UNIT = tuple(_norm_key(x) for x in F_UNIT)
N_ZIP = tuple(_norm_key(x) for x in F_ZIP)
N_CITY = tuple(_norm_key(x) for x in F_CITY)
N_FULL = tuple(_norm_key(x) for x in F_FULL)
N_LAT = tuple(_norm_key(x) for x in F_LAT)
N_LON = tuple(_norm_key(x) for x in F_LON)


def norm_raw(raw: dict) -> dict:
    """把 raw 的键一次规范化（每行只做一次，避免每个字段都重扫）。"""
    out = {}
    for k, v in (raw or {}).items():
        kk = _norm_key(k)
        if kk and kk not in out:
            out[kk] = v
    return out


def _pick(up: dict, names) -> str:
    """按优先级取第一个非空；最后允许「ESRI 截断名」前缀匹配（>=8 字符，如 `street_nam`）。"""
    for n in names:
        v = up.get(n)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.upper() not in ("<NULL>", "NULL", "NONE", "N/A", "NA", "UNKNOWN"):
            return s
    for n in names:
        if len(n) < 8:
            continue
        for kk, v in up.items():
            if len(kk) >= 8 and (n.startswith(kk) or kk.startswith(n)):
                s = str(v).strip()
                if s and s.upper() not in ("<NULL>", "NULL", "NONE", "N/A", "NA", "UNKNOWN"):
                    return s
    return ""


def _num_from_full(full: str) -> str:
    m = _NUM_RE.match(full or "")
    return m.group(1) if m else ""


def split_unit_from_name(street: str, unit: str) -> tuple[str, str]:
    """把夹在街名里的单元段剥出来（`MEADOW VIEW DR UNIT B` → `MEADOW VIEW DR` + `B`）。"""
    if not street:
        return street, unit
    m = _UNIT_IN_NAME.search(street)
    if not m:
        return street, unit
    got = m.group(1)
    rest = (street[:m.start()] + " " + street[m.end():]).strip()
    rest = re.sub(r"\s{2,}", " ", rest)
    return rest, (unit or got)


def parse_fulltext(full: str) -> dict:
    """自由文本整串 → 部件。

    `412 3 ST S UNIT D COGGON IA 52305` → num=412, core=`3`, type=ST, dir=S, unit=D
    规则：先剥 unit → 砍 `STATE ZIP` 尾巴 → **截到最后一个街类型词（含右侧方向）**，剩下的当城市残渣丢掉。
    已知不完美：没有类型词的自由文本会把城市留在核心词里 —— 这类行标 `street_src='full'`，
    reduce 侧封顶 `tier=U`，不进「独立源≥2」的判定。
    """
    from lib.addrkey import DIRECTION, SUFFIX
    out = {"num": "", "street": "", "type": "", "pre": "", "post": "", "unit": ""}
    if not full:
        return out
    m = _NUM_RE.match(full)
    if m:
        out["num"] = m.group(1)
    rest = _STRIP_NUM_RE.sub("", full).split(",")[0]
    rest = _TAIL_STATE_ZIP.sub("", rest)
    rest = _ZIP_ONLY.sub("", rest)
    rest, u = split_unit_from_name(rest.strip(), "")
    out["unit"] = u
    toks = [t for t in re.sub(r"[^A-Z0-9 ]+", " ", rest.upper()).split() if t]
    if not toks:
        return out
    idx = -1
    for i in range(len(toks) - 1, -1, -1):
        if toks[i] in SUFFIX:
            idx = i
            break
    if idx == 0 and len(toks) > 1:          # `HWY 1 ...`：类型在最前，保留后一个词当编号
        keep = toks[:2]
        j = 2
    elif idx > 0:
        keep = toks[:idx]                    # 类型词单独放进 type，不留在核心词里
        j = idx + 1
    else:                                    # 没有类型词：全部当核心（城市残渣保留，标 full）
        out["street"] = " ".join(toks)
        return out
    out["type"] = toks[idx]
    if j < len(toks) and toks[j] in DIRECTION:
        out["post"] = DIRECTION[toks[j]]
        j += 1
    if toks and toks[0] in DIRECTION:
        out["pre"] = DIRECTION[toks[0]]
        keep = [t for t in keep if t != toks[0]]
    out["street"] = " ".join(keep)
    return out


def _street_from_full(full: str) -> str:
    """自由文本整串 → 街名。

    已知不完美：`2069 HWY 1 MARTELLE IA 52305` 里的**城市名**会留在核心词里
    （我们只砍 `STATE ZIP` 尾巴，不猜城市边界）。这类行标 `street_src='full'`，
    下游 `tier` 封顶 B，并且不进「独立源≥2」的判定。
    """
    if not full:
        return ""
    rest = _STRIP_NUM_RE.sub("", full)
    head = rest.split(",")[0]
    head = _TAIL_STATE_ZIP.sub("", head)
    head = _ZIP_ONLY.sub("", head)
    return head.strip()


def _coord(up: dict, names) -> float | None:
    for n in names:
        v = up.get(n)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except ValueError:
                continue
    return None


def extract_addr(rec: dict) -> dict:
    """一条记录 → 归一化后的地址部件。

    返回键：num / street / type / pre / post / unit / zip / city / lat / lon
            + num_src / street_src（'top' | 'raw' | 'full' | ''）用于命中率统计
    """
    raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else {}
    up = norm_raw(raw) if raw else {}

    # --- 顶层（采集侧已归一化）
    num = str(rec.get("add_num") or "").strip()
    num_src = "top" if num else ""
    street = str(rec.get("st_name") or "").strip()
    street_src = "top" if street else ""
    stype = str(rec.get("st_suf") or "").strip()
    pre = str(rec.get("pre_dir") or "").strip()
    post = str(rec.get("post_dir") or "").strip()
    unit = str(rec.get("unit") or "").strip()
    zipc = str(rec.get("zip") or "").strip()
    city = str(rec.get("city") or "").strip()

    # --- raw 回退（NENA / TIGER / 各家）
    if not num:
        num = _pick(up, N_ADD)
        num_src = "raw" if num else ""
    if not street:
        street = _pick(up, N_ST)
        street_src = "raw" if street else ""
    if not stype:
        stype = _pick(up, N_SUF)
    if not pre:
        pre = _pick(up, N_PRE)
    if not post:
        post = _pick(up, N_POST)
    if not unit:
        unit = _pick(up, N_UNIT)
    if not zipc:
        zipc = _pick(up, N_ZIP)
    if not city:
        city = _pick(up, N_CITY)

    # --- 形状兜底：`{HOUSENO, NAME, SUFTYPE}` 这类（NAME 是街名）
    if not street and up:
        if "NAME" in up and any(g in up for g in NAME_GUARD):
            v = str(up.get("NAME") or "").strip()
            if v:
                street, street_src = v, "shape"

    # --- 最后一招：整串地址里抠（自由文本）
    if (not num) or (not street) or (not stype):
        full = _pick(up, N_FULL)
        if full:
            p = parse_fulltext(full)
            if not num and p["num"]:
                num, num_src = p["num"], "full"
            if not street and p["street"]:
                street, street_src = p["street"], "full"
            if not stype and p["type"]:
                stype = p["type"]
            if not pre and p["pre"]:
                pre = p["pre"]
            if not post and p["post"]:
                post = p["post"]
            if not unit and p["unit"]:
                unit = p["unit"]

    # --- 名字里夹带的单元（结构化层也会出现：`123 MAIN ST APT 4`）
    if unit is None:
        unit = ""
    street, unit = split_unit_from_name(street, unit)

    # --- 城市残渣：名字尾巴正好是城市名就砍掉
    if street and city:
        tail = " " + city.strip().upper()
        if street.upper().endswith(tail):
            street = street[: len(street) - len(city.strip())].strip()

    lat = rec.get("_lat") if isinstance(rec.get("_lat"), (int, float)) else rec.get("lat")
    lon = rec.get("_lon") if isinstance(rec.get("_lon"), (int, float)) else rec.get("lon")
    lat = float(lat) if isinstance(lat, (int, float)) else None
    lon = float(lon) if isinstance(lon, (int, float)) else None
    if lat is None or lon is None:
        la = _coord(up, N_LAT)
        lo = _coord(up, N_LON)
        if la is not None and lo is not None and 15 <= abs(la) <= 75 and 60 <= abs(lo) <= 180:
            lat, lon = la, lo

    return {
        "num": num, "num_src": num_src,
        "street": street, "street_src": street_src,
        "type": stype, "pre": pre, "post": post,
        "unit": unit, "zip": re.sub(r"\D", "", zipc)[:5],
        "city": city, "lat": lat, "lon": lon,
    }
