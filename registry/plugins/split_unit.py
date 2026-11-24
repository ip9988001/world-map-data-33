"""插件：门牌里夹带单元号的拆分（声明式表达不了，才写成插件）。

纯函数、无 IO、无全局状态；自带上 golden cases（由 registry/tests/test_registry_v1.py 跑）。

为什么必须拆：同一个上游字段既可能是 `12` 也可能是 `12A`/`12 #4`（单元门牌）。
不拆 → 门牌与单元混在一列，A 货池的「门牌唯一性」判不了。
"""
from __future__ import annotations

import re

PLUGIN = {
    "id": "split_unit",
    "applies_to": {"role": "housenumber"},
    "rationale": "门牌字段里夹带单元号（12A / 12 #4 / 12 STE 4），不拆则门牌与单元混列",
}

_RX_ATTACH = re.compile(r"^(?P<num>\d{1,6})(?P<unit>[A-Za-z]\d{0,3})$")
_RX_MARK = re.compile(r"^(?P<num>\d{1,6})\s*(?:#|[-/]|STE|SUITE|UNIT|APT|APARTMENT|LOT)\s*"
                      r"(?P<unit>[A-Za-z0-9]{1,6})$", re.I)


def _split(raw: str) -> dict:
    s = (raw or "").strip()
    if not s:
        return {"housenumber": "", "unit": "", "matched": False}
    for rx in (_RX_ATTACH, _RX_MARK):
        m = rx.match(s)
        if m:
            return {"housenumber": m.group("num"), "unit": (m.group("unit") or "").upper(),
                    "matched": True}
    return {"housenumber": s, "unit": "", "matched": False}


def apply(raw: str) -> dict:
    """返回 {housenumber, unit, matched}；拆不出时 unit='' 且 matched=False（不猜）。

    纯数字（"1020"）不会被拆（这是回归测试用例之一）。
    """
    return _split(raw)


# 自带 golden cases（输入值来自 real samples：见 analysis/dialect-20261124/DIALECT-GROUPING-20261124.md）
GOLDEN = [
    {"input": "12A", "expect": {"housenumber": "12", "unit": "A", "matched": True}},
    {"input": "12 #4", "expect": {"housenumber": "12", "unit": "4", "matched": True}},
    {"input": "1020 STE 3", "expect": {"housenumber": "1020", "unit": "3", "matched": True}},
    {"input": "1020", "expect": {"housenumber": "1020", "unit": "", "matched": False}},
]
