"""方言注册表的 golden-test 评估器。

⚠️ 本文件**只服务 golden test**：不进生产链路、不许长成引擎。
   - 纯函数：`map_row` / `minimal_safe` / `decide` 不读文件、不联网、无全局状态
   - 唯一的 IO 是 `load_registry()`（测试用），生产链路里由调用方自己读 YAML
   - 不做：去重、实体归并、分词增强、地址标准化、A/B 货判定以外的任何业务逻辑

口径（与 `registry/dialects.v1.yaml` 一一对应）：
   dialect = (provider 身份, 上游字段命名模板, 几何/点位语义)
   mapping 只做「上游别名 → canonical 6 要素」；不做值层面的猜测。
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

GRANULARITY_ENUM = ("building_point", "apartment_unit_point", "parcel_centroid",
                    "range_interpolation", "centerline_midpoint", "unknown")
ROLES = (("number", "housenumber"), ("street", "street"), ("unit", "unit"),
         ("place", "city"), ("state", "state"), ("zip", "zip"))
MINIMAL_SAFE_ID = "minimal_safe"
MINIMAL_SAFE_REASONS = ("template_unresolved", "share_below_1pct", "alias_conflict",
                        "geom_unsupported", "no_golden_evidence")


def load_registry(path: str) -> Dict[str, Any]:
    """读 YAML（测试/构建期用；生产链路不要调它）。"""
    import yaml
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    doc["_by_id"] = {d["id"]: d for d in doc.get("dialects") or []}
    return doc


def dialect_of(registry: Mapping[str, Any], dialect_id: str) -> Optional[Dict[str, Any]]:
    return (registry.get("_by_id") or {}).get(dialect_id)


def map_row(dialect: Mapping[str, Any], row: Mapping[str, Any]) -> Dict[str, str]:
    """按方言的别名表把一行上游记录映射成 canonical 6 要素。

    只做「别名命中 → 取值」；命中不到就不输出该键（**不填默认值、不猜**）。
    """
    tpl = dialect.get("template") or {}
    out: Dict[str, str] = {}
    for role, target in ROLES:
        for alias in tpl.get(f"{role}_aliases") or []:
            if alias in row:
                v = row[alias]
                if v is None:
                    continue
                s = str(v).strip()
                if s:
                    out[target] = s
                    break
    return out


def minimal_safe(registry: Mapping[str, Any], row: Mapping[str, Any]) -> Dict[str, Any]:
    """最小安全解析：**只取门牌 + 街名**。

    - 两要素都命中 → 返回解析结果，但 `pool` 恒为 `manual`、`a_pool_eligible=False`
      （minimal_safe 永不进 A 货池；这是硬约束，不是可配置项）
    - 任一缺失 → `parsed={}` 且 `reason='minimal_safe_incomplete'`
    """
    number_aliases, street_aliases = [], []
    for d in (registry.get("dialects") or []):
        tpl = d.get("template") or {}
        number_aliases += [a for a in (tpl.get("number_aliases") or []) if a not in number_aliases]
        street_aliases += [a for a in (tpl.get("street_aliases") or []) if a not in street_aliases]
    number_aliases += [a for a in ("housenumber", "house_number", "housenum", "hse_num", "num")
                       if a not in number_aliases]
    street_aliases += [a for a in ("street", "street_name", "streetname", "st_name", "road")
                       if a not in street_aliases]

    def first(aliases):
        for a in aliases:
            v = row.get(a)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    num, st = first(number_aliases), first(street_aliases)
    if num and st:
        return {"dialect_id": MINIMAL_SAFE_ID, "pool": "manual", "a_pool_eligible": False,
                "parsed": {"housenumber": num, "street": st}, "reason": "share_below_1pct"}
    return {"dialect_id": MINIMAL_SAFE_ID, "pool": "manual", "a_pool_eligible": False,
            "parsed": {}, "reason": "minimal_safe_incomplete"}


def decide(registry: Mapping[str, Any], dialect_id: str, row: Mapping[str, Any]) -> Dict[str, Any]:
    """对一行记录给出归属结论（golden test 断言用）。

    返回 {dialect_id, status, pool, a_pool_eligible, parsed, reason}
    - 方言不存在 / 粒度 unknown / 记录不是该方言 → 落 minimal_safe（pool=manual）
    """
    d = dialect_of(registry, dialect_id)
    if not d:
        return minimal_safe(registry, row)
    gran = ((d.get("geom") or {}).get("granularity") or "unknown")
    if gran not in GRANULARITY_ENUM or gran == "unknown":
        r = minimal_safe(registry, row)
        r["reason"] = "geom_unsupported"
        return r
    parsed = map_row(d, row)
    if "housenumber" not in parsed or "street" not in parsed:
        r = minimal_safe(registry, row)
        r["reason"] = "template_unresolved"
        return r
    status = d.get("status", "minimal_safe")
    return {"dialect_id": d["id"], "status": status,
            "pool": "a" if status == "active" else "manual",
            "a_pool_eligible": bool(d.get("a_pool_eligible")) and status == "active",
            "parsed": parsed, "reason": ""}


def parse_unit(raw: str) -> Dict[str, str]:
    """门牌里夹带单元号时的最小拆分（"12A" / "12-A" / "12 #4" / "12 STE 4"）。

    纯函数；拆不出就把原值放 housenumber，unit 留空（不猜）。
    注意：纯数字（"1020"）**绝不会**被拆成 102 + 0（只有字母后缀或显式单元标记才拆）。
    """
    from registry.plugins.split_unit import apply as _apply
    r = _apply(raw)
    return {"housenumber": r["housenumber"], "unit": r["unit"]}


def parse_range(raw: str) -> Dict[str, str]:
    """门牌区间的中点（"100-104" → low=100 high=104 housenumber=102）。

    只有明确写出两端的才拆；单值原样返回（不插值、不猜）。
    """
    import re
    s = (raw or "").strip()
    m = re.match(r"^(\d{1,6})\s*-\s*(\d{1,6})$", s)
    if not m:
        return {"housenumber": s, "low": "", "high": "", "kind": "single"}
    lo, hi = int(m.group(1)), int(m.group(2))
    if lo > hi:
        lo, hi = hi, lo
    return {"housenumber": str((lo + hi) // 2), "low": str(lo), "high": str(hi),
            "kind": "range_interpolation"}
