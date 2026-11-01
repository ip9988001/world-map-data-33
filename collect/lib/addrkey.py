# -*- coding: utf-8 -*-
"""地址键归一化（08 去重口径 v3）—— 纯函数、无 IO、无全局状态。

与二仓 `scripts/gold_coalesce.py` 的差别（三条都是实测出来的硬错，见 docs/08-DEDUP-PLAN-DRAFT.md 2.2）：

  1. Unicode：二仓 `PUNCT=[^A-Z0-9 ]` 把 `CAÑON` 砍成 `CA ON` → 这里先 NFKD 折叠再去重音。
  2. 类型解析：二仓在「type 是独立字段」时会被名字里的后缀词劫持
     （名字 `BRIDLE CREEK` + type `BLVD` → `CREEK|BRIDLE`）→ 这里独立字段优先，缺失才取名字最后一个后缀词。
  3. 方向词：二仓整体丢弃（`E MAIN` 与 `W MAIN` 同键）→ 这里保留，缺失时才允许合并并打 `dir_conflict`。

键形状：
    addr_key = state|county_fips|number|street_key|unit_key
    street_key = TYPE|CORE|DIR
"""
from __future__ import annotations

import re
import unicodedata

# 类型后缀：缩写与全称都映射到同一个规范词（全称，大写比较）
SUFFIX = {
    "RD": "ROAD", "ROAD": "ROAD", "DR": "DRIVE", "DRIVE": "DRIVE",
    "ST": "STREET", "STREET": "STREET", "AVE": "AVENUE", "AV": "AVENUE", "AVENUE": "AVENUE",
    "LN": "LANE", "LANE": "LANE", "CT": "COURT", "COURT": "COURT",
    "CIR": "CIRCLE", "CIRCLE": "CIRCLE", "BLVD": "BOULEVARD", "BOULEVARD": "BOULEVARD",
    "HWY": "HIGHWAY", "HIGHWAY": "HIGHWAY", "PL": "PLACE", "PLACE": "PLACE",
    "WAY": "WAY", "TRL": "TRAIL", "TRAIL": "TRAIL", "TER": "TERRACE", "TERRACE": "TERRACE",
    "PKWY": "PARKWAY", "PARKWAY": "PARKWAY", "PKY": "PARKWAY",
    "EXT": "EXTENSION", "EXTENSION": "EXTENSION", "RUN": "RUN", "GRN": "GREEN", "GREEN": "GREEN",
    "XING": "CROSSING", "CROSSING": "CROSSING", "PATH": "PATH", "CRK": "CREEK", "CREEK": "CREEK",
    "PLZ": "PLAZA", "PLAZA": "PLAZA", "ALY": "ALLEY", "ALLEY": "ALLEY", "LOOP": "LOOP",
    "BND": "BEND", "TPKE": "TURNPIKE", "EXPY": "EXPRESSWAY", "FWY": "FREEWAY",
    "HTS": "HEIGHTS", "JCT": "JUNCTION", "PT": "POINT", "RDG": "RIDGE", "SPG": "SPRING",
    "CV": "COVE", "BRG": "BRIDGE", "CTR": "CENTER", "MNR": "MANOR", "EST": "ESTATES",
    "ESTS": "ESTATES", "SQ": "SQUARE", "VLG": "VILLAGE", "WDS": "WOODS", "GRV": "GROVE",
    "GDN": "GARDEN", "GLN": "GLEN", "KNL": "KNOLL", "ML": "MILL", "STA": "STATION",
    "SMT": "SUMMIT", "VW": "VIEW", "MDW": "MEADOW", "PASS": "PASS", "PIKE": "PIKE",
}

DIRECTION = {
    "N": "N", "S": "S", "E": "E", "W": "W", "NE": "NE", "NW": "NW", "SE": "SE", "SW": "SW",
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW",
}

ORDINAL_WORD = {
    "FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4", "FIFTH": "5", "SIXTH": "6",
    "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9", "TENTH": "10", "ELEVENTH": "11",
    "TWELFTH": "12", "THIRTEENTH": "13", "FOURTEENTH": "14", "FIFTEENTH": "15",
    "SIXTEENTH": "16", "SEVENTEENTH": "17", "EIGHTEENTH": "18", "NINETEENTH": "19",
    "TWENTIETH": "20",
}
ORDINAL_RE = re.compile(r"^(\d+)(ST|ND|RD|TH)$")

UNIT_PREFIX = re.compile(
    r"^(APT|APARTMENT|STE|SUITE|UNIT|RM|ROOM|#|NO|NUM|LOT|BLDG|BUILDING|FL|FLOOR)\s*[\.\-]?\s*",
    re.I)
# 「不像单元」的值：左右侧标志 / 是否标志 / 空壳
UNIT_BAD = {"L", "R", "LEFT", "RIGHT", "Y", "N", "YES", "NO", "NONE", "NULL", "0"}

_UMLAUT = {"Ø": "O", "ß": "SS", "Æ": "AE", "Œ": "OE", "Đ": "D", "Ł": "L", "Þ": "TH"}
_NON_KEY = re.compile(r"[^A-Z0-9]+")


def fold(s) -> str:
    """NFKD → 去组合符 → 特殊字母映射。保证 `CAÑON` → `CANON` 而不是 `CA ON`。"""
    if s is None:
        return ""
    t = unicodedata.normalize("NFKD", str(s))
    t = "".join(c for c in t if not unicodedata.combining(c))
    for a, b in _UMLAUT.items():
        t = t.replace(a, b)
    return t


def tokens(s) -> list[str]:
    """大写 + 非 [A-Z0-9] 变空格 + 折叠空白。"""
    return [t for t in _NON_KEY.sub(" ", fold(s).upper()).split() if t]


def num_key(v) -> str:
    """门牌号：数字段 + 可选单字母后缀（123A）；123-45 保留连字符；不截断。"""
    s = re.sub(r"[^A-Z0-9\-]+", "", fold(v).upper()) if v is not None else ""
    if not s:
        return ""
    m = re.match(r"^(\d+)([A-Z])?$", s)
    if m:
        return m.group(1) + (m.group(2) or "")
    m = re.match(r"^(\d+)-(\d+)$", s)
    if m:
        return s
    m = re.match(r"^(\d+)", s)          # 兜底：取前导数字
    return m.group(1) if m else ""


def _dir(v) -> str:
    if not v:
        return ""
    t = _NON_KEY.sub("", fold(v).upper())
    return DIRECTION.get(t, "")


def street_key(name, post_type="", pre_dir="", post_dir="") -> str:
    """`TYPE|CORE|DIR`。

    - type：独立字段优先；缺失才取名字**最后一个**后缀词。
    - 未知 type 原样保留（`COUNTY HIGHWAY TT` 的 `TT`），不猜。
    - dir：独立字段优先；名字首词/末词是方向词才提取，避免 `WEST` 这种街名被吞。
    """
    toks = tokens(name)
    d_pre = _dir(pre_dir)
    d_post = _dir(post_dir)

    if not d_pre and toks and toks[0] in DIRECTION:
        d_pre = DIRECTION[toks.pop(0)]
    if not d_post and len(toks) > 1 and toks[-1] in DIRECTION:
        d_post = DIRECTION[toks.pop()]
    if not d_pre and d_post and not pre_dir:      # 只有一个方向且来自字段/末词：归到 pre 位
        pass

    typ = ""
    if post_type:
        p = _NON_KEY.sub("", fold(post_type).upper())
        typ = SUFFIX.get(p, p)                    # 未知类型原样保留
    core = []
    for t in toks:
        t = ORDINAL_WORD.get(t, t)
        t = ORDINAL_RE.sub(r"\1", t)
        core.append(t)
    if not typ and core and core[-1] in SUFFIX:
        typ = SUFFIX[core.pop()]
    d = d_pre + ("+" if d_pre and d_post else "") + d_post
    return "%s|%s|%s" % (typ, " ".join(core), d)


def unit_key(v) -> str:
    """`APT 5` / `#5` / `UNIT 5` / `STE 5` 全部 → `5`；空/脏值 → `''`（无单元）。"""
    s = fold(v).strip() if v is not None else ""
    if not s:
        return ""
    s = UNIT_PREFIX.sub("", s).strip()
    k = _NON_KEY.sub("", s.upper())
    if not k or k in UNIT_BAD:
        return ""
    if len(k) > 6:                                 # 像「备注」不像单元
        return ""
    return k


def unit_raw(v) -> str:
    """保留原始写法（产品版要还原 `APT 5` 而不是 `5`）。"""
    return "" if v is None else str(v).strip()


def addr_key(state, county_fips, num, skey, ukey) -> str:
    """完整键。num 或 street 缺失 → 返回 ''（不可键，进 unkeyed）。"""
    if not num or not skey or not skey.strip("|"):
        return ""
    return "%s|%s|%s|%s|%s" % (
        (state or "").upper(), str(county_fips or ""), num, skey, ukey or "")
