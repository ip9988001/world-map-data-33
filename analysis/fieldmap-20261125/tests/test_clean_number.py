#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`fm_core.clean_number()` 的浮点整形单测（muse-000275 §2.4）。

6 个必备用例：「1009.0」/「1009」/「1009.5」/ 1009.0(float) /「0.0」/「 1009.0 」，
外加若干边界（多位零小数、float 0.0、占位值不变、非浮点串不动）。

口径（与实现注释一致）：
  · 只改写法不改数值：`1009.0` → `1009`；
  · 非零小数原样保留（不四舍五入）；
  · `0.0` 仍按**占位值**判缺失（返回空串）—— 占位语义优先，不能凭空造出 house_number="0"。
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)
sys.path.insert(0, FM)

import fm_core as C  # noqa: E402


@pytest.mark.parametrize("raw,expect", [
    ("1009.0", "1009"),          # ① 字符串整数浮点
    ("1009", "1009"),            # ② 干净整数不动
    ("1009.5", "1009.5"),        # ③ 非零小数原样保留（不四舍五入）
    (1009.0, "1009"),            # ④ JSON 浮点（float）
    ("0.0", ""),                 # ⑤ 占位值优先 → 缺失（见模块注释）
    (" 1009.0 ", "1009"),        # ⑥ 前后空白
])
def test_clean_number_six_required(raw, expect):
    assert C.clean_number(raw) == expect


@pytest.mark.parametrize("raw,expect", [
    ("1009.00", "1009"),         # 多位零小数
    ("1009.000", "1009"),
    (1009.0, "1009"),
    (0.0, ""),                   # float 0.0 同样是占位值
    ("0.00", ""),
    ("1009.50", "1009.50"),      # 末位非零 → 保留原样
    ("0.5", "0.5"),              # 纯小数不是门牌，但也不是浮点整形对象 → 原样
    ("-1", ""),                  # 既有占位值语义不变
    ("NULL", ""),
    ("12 1/2", "12 1/2"),        # 带分数门牌不动
    ("N12W34567", "N12W34567"),  # 网格门牌不动
    ("1009.0A", "1009.0A"),      # 脏尾巴不动（不是纯浮点写法）
    (None, ""),
])
def test_clean_number_edges(raw, expect):
    assert C.clean_number(raw) == expect


def test_clean_number_is_idempotent():
    for v in ("1009.0", "1009.5", "0.0", " 1009.0 ", 1009.0):
        once = C.clean_number(v)
        assert C.clean_number(once) == once


def test_clean_number_leaves_street_and_city_untouched():
    """只改门牌：clean_street / clean_city 的行为一点不动（回归护栏）。"""
    assert C.clean_street("N", "MAIN", "ST", "") == "N MAIN ST"
    assert C.clean_city("Citronelle") == "Citronelle"
    assert C.clean_street(None, "1.0", None, None) == "1.0"   # 街名不做浮点整形
