"""地址切分与建键的确定性规则（组合拳③）。

三块内容，全部纯函数、无 IO、无模型：

1. `is_placeholder(v)` —— 占位缺失值（`-1`/`-999`/`-9999`/`0`/`NULL`/`NA`/空串…）不得参与建键。
   这就是组合拳② 772 行 questionable 的根因之一：占位值被当成真门牌/真街名顶掉了原来的键。

2. `split_number_street(raw)` —— P1「门牌+街名拼一格」的切分。输出 `house_number` / `street_name`
   （能拆出单元号时给 `unit`），切不出返回 `reason` 代码，**不猜、不填空串**。

3. `split_city_tail(raw)` —— P3「门牌+街名+城市+州+ZIP 全拼一格」。尾部锚定 ZIP5(+4)、州缩写，
   街名以「街道类型词」为右锚点切；找不到类型词锚点就降 confidence 并给 reason。

4. `addr_key(af, roles, state)` —— 与 `sandbox/coord_evidence.py:addr_key()` **同契约**（返回
   `state|number|street|zip` 字符串，构不出返回空串），差别只在于：占位缺失值一律跳过，
   且**不许覆盖已有真值**。③ 只在 engine 侧落地；`sandbox/` 的副本要由 ④ 换过来（本单边界外）。
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- 占位缺失值
PLACEHOLDERS = {
    "", "-", "--", "n/a", "na", "n.a.", "null", "none", "nil", "unknown", "unk", "tbd",
    "-1", "-1.0", "-9", "-99", "-999", "-9999", "-99999", "999999", "0", "0.0",
    "000000", "00000", "000000000", "99999", "-888", "-8888", "x", "xx", "n/a n/a",
}


def is_placeholder(v) -> bool:
    """占位缺失值判定（只判整值，不做子串匹配 —— 避免把 "10 N MAIN ST" 误杀）。"""
    if v is None:
        return True
    if isinstance(v, (int, float)):
        return float(v) in (-1.0, -9.0, -99.0, -999.0, -9999.0, 0.0)
    s = str(v).strip()
    if not s:
        return True
    low = s.lower()
    if low in PLACEHOLDERS:
        return True
    # "-9999.0" / "0.000000" 这类数值写法
    if re.fullmatch(r"-?\d+(\.0+)?", s):
        try:
            f = float(s)
        except ValueError:
            return False
        return f in (-1.0, -9.0, -99.0, -999.0, -9999.0, 0.0)
    return False


# ---------------------------------------------------------------- 词表
STREET_TYPES = {
    "ST", "STREET", "AVE", "AV", "AVENUE", "RD", "ROAD", "DR", "DRIVE", "LN", "LANE", "CT", "COURT",
    "PL", "PLACE", "BLVD", "BOULEVARD", "WAY", "HWY", "HIGHWAY", "TER", "TERRACE", "CIR", "CIRCLE",
    "PKWY", "PARKWAY", "TRL", "TRAIL", "LOOP", "ALY", "ALLEY", "SQ", "SQUARE", "PIKE", "EXPY", "EXPRESSWAY",
    "RUN", "PATH", "WALK", "BEND", "COVE", "CV", "PASS", "RIDGE", "ROW", "SPUR", "STREET", "TPKE",
    "TURNPIKE", "PLZ", "PLAZA", "XING", "CROSSING", "MNR", "MANOR", "EST", "ESTATE", "ESTATES",
    "HTS", "HEIGHTS", "GDNS", "GARDENS", "ACRES", "ACRE", "PARK", "HOLLOW", "HOLLW", "GLEN", "MEADOW",
    "MDWS", "VW", "VIEW", "POINTE", "PT", "CRK", "CREEK", "FRST", "FOREST", "HBR", "HARBOR", "LANDING",
    "LNDG", "MILL", "SPRING", "SPGS", "SUMMIT", "VLLY", "VALLEY", "VISTA", "BYP", "BYPASS",
}
UNIT_WORDS = {"APT", "APARTMENT", "STE", "SUITE", "UNIT", "BLDG", "BUILDING", "FL", "FLOOR", "RM", "ROOM",
              "LOT", "SPC", "SPACE", "TRLR", "TRAILER", "DEPT", "#"}
DIR_WORDS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "NORTH", "SOUTH", "EAST", "WEST",
             "NORTHEAST", "NORTHWEST", "SOUTHEAST", "SOUTHWEST"}

# 12 / 12A / 12 B / 12-14 / 12 1/2 / 123RD / N12W34567（威斯康星网格号）
HN_RE = re.compile(
    r"^(?P<num>"
    r"[NSEW]\d{1,6}[NSEW]\d{1,6}"                      # N12W34567
    r"|\d{1,3}[NSEW]\d{1,6}"                            # 4S631（威州/伊州网格号）
    r"|\d{1,6}\s+\d/\d"                                # 12 1/2
    r"|\d{1,6}[A-Za-z]?(?:\s?-\s?\d{1,6}[A-Za-z]?)?"   # 12 / 12A / 12-14
    r"|\d{1,6}(?:ST|ND|RD|TH)"                         # 123RD
    r")"
    r"(?:\s+|,\s*)(?P<rest>.+)$", re.I)
POBOX_RE = re.compile(r"^\s*(P\.?\s*O\.?|POST\s+OFFICE)\s*(BOX|B\.?)\s*\d+", re.I)
RR_RE = re.compile(r"^\s*(RR|RURAL\s+ROUTE|RTE|ROUTE)\s*#?\s*\d+\s*(BOX\s*\d+)?", re.I)
MASK_RE = re.compile(r"^\s*(?:\d{0,3})X{2,}|^\s*XX", re.I)
ZIP5_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\s*$")
STATE_RE = re.compile(r"\b([A-Z]{2})\.?\s*$")
US_STATES = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
             "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
             "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
             "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP"}

REASONS = {
    "ok": "切分成功",
    "empty": "空值",
    "placeholder": "占位缺失值（-1/-999/0/NULL…）",
    "po_box": "PO BOX 邮政信箱，不是街道地址",
    "rural_route": "RR/RURAL ROUTE，无街名可切",
    "masked_number": "门牌被打码（3XX / XXXX）",
    "intersection": "路口名（A ST / B AVE），不是单点地址",
    "no_house_number": "没有门牌号（纯街名/街名+城市）",
    "no_street": "只有门牌号，没有街名",
    "ambiguous": "切出的街名仍以数字开头或有 2 个以上门牌候选",
    "bad_street": "街名不含任何字母词",
    "no_street_type_anchor": "P3：找不到街道类型词锚点，无法确定城市边界",
    "no_state_or_zip": "P3：尾部既无 ZIP5 也无州缩写",
}


def _tokens(s):
    return re.findall(r"[A-Za-z0-9#/&\-\.']+", s)


def _strip_unit(rest):
    """把 "MAIN ST APT 4" / "MAIN ST #4" / "MAIN ST STE 200" 的单元号剥出来。"""
    toks = _tokens(rest)
    low = [t.upper().strip(".") for t in toks]
    for i, t in enumerate(low):
        if t in UNIT_WORDS and i > 0:
            unit = " ".join(toks[i:])
            street = " ".join(toks[:i])
            return street, unit
        if t.startswith("#") and i > 0:
            return " ".join(toks[:i]), " ".join(toks[i:])
    return rest, ""


def split_number_street(raw):
    """P1：把「门牌 + 街名」拼一格的值切成两列。

    :return: dict(house_number, street_name, unit, reason, confidence)
             reason != "ok" 时 house_number/street_name 均为空串（调用方必须落 reject 桶）
    """
    if raw is None:
        return {"house_number": "", "street_name": "", "unit": "", "reason": "empty", "confidence": 0.0}
    s = re.sub(r"\s+", " ", str(raw)).strip().strip(",;")
    if not s:
        return {"house_number": "", "street_name": "", "unit": "", "reason": "empty", "confidence": 0.0}
    if is_placeholder(s):
        return {"house_number": "", "street_name": "", "unit": "", "reason": "placeholder", "confidence": 0.0}
    if POBOX_RE.match(s):
        return {"house_number": "", "street_name": "", "unit": "", "reason": "po_box", "confidence": 0.0}
    if RR_RE.match(s):
        return {"house_number": "", "street_name": "", "unit": "", "reason": "rural_route", "confidence": 0.0}
    if MASK_RE.match(s):
        return {"house_number": "", "street_name": "", "unit": "", "reason": "masked_number", "confidence": 0.0}
    # 路口名：两侧都带街道类型词，且用 / 或 & 分隔
    if re.search(r"\s(?:/|&)\s", s):
        left, right = re.split(r"\s(?:/|&)\s", s, maxsplit=1)
        if any(t.upper() in STREET_TYPES for t in _tokens(left)) and \
           any(t.upper() in STREET_TYPES for t in _tokens(right)):
            return {"house_number": "", "street_name": "", "unit": "", "reason": "intersection", "confidence": 0.0}

    # 纯门牌号（没有街名）
    if re.fullmatch(r"\d{1,6}[A-Za-z]?(?:\s?-\s?\d{1,6}[A-Za-z]?)?", s):
        return {"house_number": "", "street_name": "", "unit": "", "reason": "no_street", "confidence": 0.0}

    m = HN_RE.match(s)
    if not m:
        # 以数字开头但不是合法门牌 → 模糊
        if re.match(r"^\s*\d", s):
            return {"house_number": "", "street_name": "", "unit": "", "reason": "ambiguous", "confidence": 0.0}
        return {"house_number": "", "street_name": "", "unit": "", "reason": "no_house_number", "confidence": 0.0}

    num = re.sub(r"\s*-\s*", "-", m.group("num").strip())
    rest = m.group("rest").strip(" ,;")
    # "12 B MAIN ST"：单字母后缀且不是方向词 → 归到门牌；方向词留在街名
    mtok = re.match(r"^([A-Za-z])\s+([A-Za-z0-9].*)$", rest)
    if mtok and mtok.group(1).upper() not in DIR_WORDS:
        nxt = mtok.group(2).split()[0].upper().strip(".")
        if nxt not in STREET_TYPES:
            num, rest = f"{num} {mtok.group(1).upper()}", mtok.group(2)
    street, unit = _strip_unit(rest)
    street = street.strip(" ,;")
    if not street:
        return {"house_number": "", "street_name": "", "unit": "", "reason": "no_street", "confidence": 0.0}
    if re.match(r"^\d", street) and not re.match(r"^\d+(?:ST|ND|RD|TH)\b", street, re.I):
        # 例如 "12 14 MAIN ST" —— 两个门牌候选，切不准
        return {"house_number": "", "street_name": "", "unit": unit, "reason": "ambiguous", "confidence": 0.0}
    toks = [t for t in _tokens(street) if re.search(r"[A-Za-z]", t)]
    if not toks:
        return {"house_number": "", "street_name": "", "unit": unit, "reason": "bad_street", "confidence": 0.0}
    conf = 0.95 if (toks[-1].upper().strip(".") in STREET_TYPES or toks[0].upper() in DIR_WORDS) else 0.85
    return {"house_number": num, "street_name": street, "unit": unit, "reason": "ok", "confidence": conf}


def split_city_tail(raw, city_lexicon=None):
    """P3：把「门牌+街名+城市+州+ZIP」全拼一格的值切成 street / city / state / zip。

    锚定顺序（确定性）：ZIP5(+4) 必须在尾部；其前是州缩写（US 两字母）；街名右锚点是「街道类型词」。
    没有 ZIP 时：只要尾部有州缩写 + 能切出街道类型词，也接受，但 confidence 降到 0.6 并标 reason。
    """
    out = {"house_number": "", "street_name": "", "city": "", "state": "", "zip": "",
           "reason": "ok", "confidence": 0.0}
    if raw is None or not str(raw).strip():
        out["reason"] = "empty"
        return out
    s = re.sub(r"\s+", " ", str(raw)).strip().strip(",;")
    if is_placeholder(s):
        out["reason"] = "placeholder"
        return out

    mz = ZIP5_RE.search(s)
    zip_code = ""
    body = s
    if mz:
        zip_code = mz.group(1)
        body = s[:mz.start()].strip(" ,")
    ms = STATE_RE.search(body)
    state = ""
    if ms and ms.group(1).upper() in US_STATES:
        state = ms.group(1).upper()
        body = body[:ms.start()].strip(" ,")
    if not state and not zip_code:
        # 无州/无 ZIP：只在「能切出街道类型词 + 还有城市尾巴」时接受，且置信度降到 0.4
        toks0 = _tokens(body)
        anchor0 = max([i for i, t in enumerate(toks0) if i > 0 and t.upper().strip(".") in STREET_TYPES] or [-1])
        if anchor0 <= 0 or anchor0 == len(toks0) - 1:
            out["reason"] = "no_state_or_zip"
            return out
        sp0 = split_number_street(" ".join(toks0[:anchor0 + 1]))
        if sp0["reason"] != "ok":
            out["reason"] = "no_state_or_zip"
            return out
        out.update({"house_number": sp0["house_number"], "street_name": sp0["street_name"],
                    "city": " ".join(toks0[anchor0 + 1:]), "state": "", "zip": "",
                    "confidence": 0.4})
        return out
    if not state:
        out["reason"] = "no_state_or_zip"
        return out

    toks = _tokens(body)
    # 右锚点：最后一个街道类型词（必须在门牌之后）
    anchor = -1
    for i, t in enumerate(toks):
        if i == 0:
            continue
        if t.upper().strip(".") in STREET_TYPES:
            anchor = i
    if anchor <= 0:
        out["reason"] = "no_street_type_anchor"
        return out
    end = anchor + 1
    while end < len(toks) and (re.fullmatch(r"\d{1,4}[A-Za-z]?", toks[end]) or
                               toks[end].upper().strip(".") in {"US", "SR", "CR", "FM", "SH", "RT", "RTE", "I"}):
        end += 1
    street_part = " ".join(toks[:end])
    city_part = " ".join(toks[end:])
    sp = split_number_street(street_part)
    if sp["reason"] != "ok":
        out["reason"] = sp["reason"]
        return out
    out["house_number"], out["street_name"] = sp["house_number"], sp["street_name"]
    out["city"], out["state"], out["zip"] = city_part, state, zip_code
    out["confidence"] = 0.9 if zip_code else 0.6
    if not city_part:
        out["reason"] = "no_street_type_anchor"
        out["confidence"] = 0.0
    return out


# ---------------------------------------------------------------- 建键（占位跳过）
def addr_key(af, roles, state):
    """与 sandbox/coord_evidence.py:addr_key() 同契约；差别：占位值跳过、不许覆盖真值。

    :param af: 一行上游记录（dict）
    :param roles: 归一字段名 → 角色集合（number/street/zip），由调用方从 registry 汇总
    :return: "state|number|streetnorm|zip"，构不出返回 ""
    """
    n = s = z = ""
    for k, v in af.items():
        if is_placeholder(v):
            continue
        v = str(v).strip()
        r = roles.get(_norm(k)) or ()
        if not n and "number" in r:
            n = re.sub(r"[^0-9A-Za-z-]", "", v)
        elif not s and "street" in r:
            s = v
        elif not z and "zip" in r:
            m = re.search(r"\b(\d{5})\b", v)
            if m:
                z = m.group(1)
    if n and s:
        return f"{state}|{n}|{_street_norm(s)}|{z}"
    # 兜底：首段门牌 + 含 5 位 zip 的整串（与 sandbox 同规则，但同样跳过占位值）
    for k, v in af.items():
        if is_placeholder(v) or not isinstance(v, str):
            continue
        if "," not in v:
            continue
        m = re.match(r"^\s*(\d+)\s*[A-Za-z]?\s+(.*)$", v.split(",")[0])
        mz = re.search(r"\b(\d{5})\b", v)
        if m and mz:
            return f"{state}|{m.group(1)}|{_street_norm(m.group(2))}|{mz.group(1)}"
    return ""


_SUFFIX = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
           "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "hwy": "highway",
           "pkwy": "parkway", "cir": "circle", "ter": "terrace", "trl": "trail"}


def _norm(f):
    return re.sub(r"[^a-z0-9]", "", (f or "").lower())


def _street_norm(s):
    w = [_SUFFIX.get(x, x) for x in re.findall(r"[a-z0-9]+", (s or "").lower())]
    return "".join(w)
