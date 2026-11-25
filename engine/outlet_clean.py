"""出口：统一清洗 + addrkey v3（纯函数，无 IO）。

归一规则来源分两层，写清楚是为了不重造轮子也不偷偷改口径：

  1. **复用** `collect/lib/addrkey.py`（仓库既有去重口径 v3）：NFKD 折叠去重音、
     后缀缩写全称化（RD→ROAD）、方向词独立保留（N/S/E/W）、`num_key` 拆数字+单字母后缀、
     `street_key` 输出 `TYPE|CORE|DIR`、`unit_key` 去掉 APT/STE/# 前缀。
     —— 该文件本轮只读 import，一个字节都没改。
  2. **本模块**补：state/zip5/city 规范化、合并地址串解析、坐标合法性与插值标记、
     addrkey v3 的**引擎档**形态（版本前缀 + 摘要），以及完整度分级所需的布尔特征。

addrkey v3（引擎档）口径：
    parts = [state(2), zip5, num, street_key(TYPE|CORE|DIR), unit_key]
    key   = "a3:" + sha1("\\x1f".join(parts)).hexdigest()[:20]
    · 版本前缀 `a3:` 固定，**不与 v1/v2 混用**（v1/v2 键无前缀且字段集不同，见 collect/lib/addrkey.py 注释）
    · unit 默认入键（同一栋楼的不同单元是不同地址行）；`include_unit: false` 时 unit 只用 `unit_key='#'` 占位
    · num 或 street 缺 → 不可键，返回 ""（进 unkeyed，不参与去重，但仍入库并记 C 级）
"""
from __future__ import annotations

import hashlib
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collect.lib.addrkey import SUFFIX, fold, num_key, street_key, unit_key  # noqa: E402  只读复用

ADDRKEY_VERSION = "v3"
ADDRKEY_PREFIX = "a3"
SEP = "\x1f"

_STATE = re.compile(r"^[A-Z]{2}$")
_ZIP5 = re.compile(r"(\d{5})")
_NUMLIKE = re.compile(r"^\s*(\d+[A-Za-z]?)\b")
_PLACEHOLDER = {"", "NONE", "NULL", "NOT STATED", "UNKNOWN", "N/A", "NA", "-", "0"}


def _s(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.upper() in _PLACEHOLDER else s


def state2(v) -> str:
    s = fold(_s(v)).strip().upper()
    return s if _STATE.match(s) else ""


def zip5(v) -> str:
    m = _ZIP5.search(fold(_s(v)))
    return m.group(1) if m else ""


def city_norm(v) -> str:
    s = " ".join(t for t in re.sub(r"[^A-Z0-9 ]+", " ", fold(_s(v)).upper()).split())
    return "" if s.upper() in _PLACEHOLDER else s


def split_combined(v) -> tuple[str, str]:
    """合并地址串 → (门牌, 街名)。只做确定性切分，不猜：`58 BARBARA DRIVE` → (58, BARBARA DRIVE)。"""
    s = _s(v)
    m = _NUMLIKE.match(s)
    if not m:
        return "", s
    return m.group(1), s[m.end():].strip(" ,")


def _strip_type(street: str, post_type: str) -> str:
    """街名末尾已在 post_type 里声明过同一个类型词 → 从街名里去掉，避免 CORE 重复（不改变语义）。"""
    tok = lambda s: SUFFIX.get(re.sub(r"[^A-Z0-9]", "", fold(s or "").upper()),
                               re.sub(r"[^A-Z0-9]", "", fold(s or "").upper()))  # noqa: E731
    toks = street.split()
    if not (post_type and len(toks) > 1):
        return street
    return " ".join(toks[:-1]) if tok(post_type) == tok(toks[-1]) else street


def as_float(v):
    try:
        f = float(str(v).strip())
    except (TypeError, ValueError):
        return None
    return f


def point_ok(lon, lat) -> bool:
    """坐标合法性：(0,0) 与越界一律 False（不许用 0,0 顶替）。"""
    if lon is None or lat is None:
        return False
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return False
    return not (lon == 0 and lat == 0)


def addrkey_v3_parts(rec: dict, include_unit: bool = True) -> list[str]:
    return [state2(rec.get("state")), zip5(rec.get("zip")), num_key(rec.get("number")),
            street_key(rec.get("street"), rec.get("post_type") or "", rec.get("pre_dir") or "",
                       rec.get("post_dir") or ""),
            (unit_key(rec.get("unit")) or "#") if include_unit else "#"]


def addrkey_v3(rec: dict, include_unit: bool = True) -> str:
    parts = addrkey_v3_parts(rec, include_unit)
    if not parts[2] or not parts[3].strip("|"):
        return ""
    return f"{ADDRKEY_PREFIX}:" + hashlib.sha1(SEP.join(parts).encode("utf-8")).hexdigest()[:20]


def clean(raw: dict, spec: dict | None = None, include_unit: bool = True) -> dict:
    """raw（已按方言做字段映射）→ 清洗后的统一 schema 记录（含 addrkey v3 与完整度特征）。"""
    spec = spec or {}
    num, street = _s(raw.get("number")), _s(raw.get("street"))
    if not (num and street) and raw.get("combined"):
        c_num, c_street = split_combined(raw.get("combined"))
        num, street = num or c_num, street or c_street
    rec = {
        "number": num_key(num),
        "street": street,
        "post_type": _s(raw.get("post_type")),
        "pre_dir": _s(raw.get("pre_dir")),
        "post_dir": _s(raw.get("post_dir")),
        "unit": _s(raw.get("unit")),
        "city": city_norm(raw.get("city")),
        "state": state2(raw.get("state")),
        "zip5": zip5(raw.get("zip")),
        "lon": as_float(raw.get("lon")),
        "lat": as_float(raw.get("lat")),
        "precision": spec.get("precision", "unknown"),
        "is_interpolated": bool(spec.get("is_interpolated")) or bool(raw.get("is_interpolated")),
        "source_id": raw.get("source_id", ""),
        "source_family": raw.get("source_family", ""),
        "source_ref": raw.get("source_ref", ""),
        "record_id": _s(raw.get("id")),
        "geom_type_raw": raw.get("geom_type") or "",
    }
    rec["street"] = _strip_type(rec["street"], rec["post_type"])
    rec["point_ok"] = point_ok(rec["lon"], rec["lat"])
    rec["addrkey"] = addrkey_v3(rec, include_unit)
    apply_geometry(rec, raw, spec)
    rec["features"] = {
        "number": bool(rec["number"]),
        "street": bool(rec["street"].strip()),
        "city": bool(rec["city"]),
        "state": bool(rec["state"]),
        "zip5": bool(rec["zip5"]),
        "point": rec["point_ok"] and not rec["is_interpolated"],
        "point_any": rec["point_ok"],
    }
    return rec


def grade_of(features: dict, rules: dict) -> str:
    """按配置里的 S/A/B/C 规则判级：规则里每个 require 项都必须为真；取第一个命中的最高级。

    rules 形如 {"S": ["number","street","city","state","zip5","point"],
                "A": [...], "B": [...], "C": [...]}；空规则 → 不入库（"X"）。
    """
    for g in ("S", "A", "B", "C"):
        need = rules.get(g) or []
        if need and all(features.get(k) for k in need):
            return g
    return "X"


# ---------------------------------------------------------------- 几何口径（第 7 步）
GEOM_TYPES = ("point", "polygon", "polyline", "multipoint", "none", "unknown")
_GEOM_ALIAS = {"esrigeometrypoint": "point", "esrigeometrypolygon": "polygon",
               "esrigeometrypolyline": "polyline", "esrigeometrymultipoint": "multipoint",
               "point(lat/lon fields)": "point", "point": "point", "polygon": "polygon",
               "polyline": "polyline", "multipoint": "multipoint", "none": "none"}


def geom_type_of(v, spec: dict) -> str:
    """行级实测优先（样本/parquet WKB），否则用方言声明；都没有记 unknown（不猜）。"""
    raw = re.sub(r"[^a-z0-9()/ ]", "", str(v or "").strip().lower())
    if raw in _GEOM_ALIAS:
        return _GEOM_ALIAS[raw]
    decl = str((spec or {}).get("geom_type") or "").strip().lower()
    return decl if decl in GEOM_TYPES else ("unknown" if not raw else "unknown")


def point_kind_of(rec: dict) -> str:
    """point / vertex（面线真实顶点）/ interpolated（街段插值）/ parcel_centroid（源侧地块质心）。

    绝不用质心替代面线坐标：面线行的 lon/lat 一定是真实顶点（inlet 取 rings[0][0] / paths[0][0]）。
    """
    if not rec.get("point_ok"):
        return ""
    if rec.get("is_interpolated"):
        return "interpolated"
    if (rec.get("precision") or "") == "parcel_centroid":
        return "parcel_centroid"
    return "vertex" if rec.get("geom_type") in ("polygon", "polyline", "multipoint") else "point"


def apply_geometry(rec: dict, raw: dict, spec: dict) -> dict:
    """把 geom_type / point_kind / pos_estimated 三个口径字段挂到清洗后的记录上。"""
    rec["geom_type"] = geom_type_of(raw.get("geom_type"), spec)
    rec["point_kind"] = point_kind_of(rec)
    rec["pos_estimated"] = bool(rec.get("is_interpolated"))   # 插值位置=估算值（地块质心按源侧声明，不算估算）
    return rec
