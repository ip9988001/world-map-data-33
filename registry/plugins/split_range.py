"""插件：门牌区间 → 插值中点（声明式表达不了，才写成插件）。

纯函数、无 IO、无全局状态；自带上 golden cases。

为什么必须处理：`range_interpolation` 粒度（如 NG911 的 `100-104 MAIN ST`）里，
门牌是一个区间，直接取字符串会让「门牌唯一性」判不了，也会让 HouseNumber 变成 `100-104`。
这里只做**明确写了两端**的区间；没写两端的一律原样返回（不猜）。
"""
from __future__ import annotations

import re

PLUGIN = {
    "id": "split_range",
    "applies_to": {"granularity": "range_interpolation"},
    "rationale": "门牌是区间（100-104），需要 low/high 与中点；不插值就无法与单点门牌比对",
}

_RX = re.compile(r"^(?P<lo>\d{1,6})\s*-\s*(?P<hi>\d{1,6})$")


def apply(raw: str) -> dict:
    """返回 {housenumber, low, high, kind}；非区间时 kind='single' 且 low/high 为空。"""
    s = (raw or "").strip()
    m = _RX.match(s)
    if not m:
        return {"housenumber": s, "low": "", "high": "", "kind": "single"}
    lo, hi = int(m.group("lo")), int(m.group("hi"))
    if lo > hi:
        lo, hi = hi, lo
    return {"housenumber": str((lo + hi) // 2), "low": str(lo), "high": str(hi),
            "kind": "range_interpolation"}


GOLDEN = [
    {"input": "100-104", "expect": {"housenumber": "102", "low": "100", "high": "104",
                                    "kind": "range_interpolation"}},
    {"input": "104 - 100", "expect": {"housenumber": "102", "low": "100", "high": "104",
                                      "kind": "range_interpolation"}},
    {"input": "1001-1001", "expect": {"housenumber": "1001", "low": "1001", "high": "1001",
                                      "kind": "range_interpolation"}},
    {"input": "1020", "expect": {"housenumber": "1020", "low": "", "high": "", "kind": "single"}},
]
