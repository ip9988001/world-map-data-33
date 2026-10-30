#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全国县索引（1° 网格预筛）—— 判县的**唯一口径**，county_assign / intake_33 共用。

为什么需要「全国」而不是「按州」：
  · 层的 `state` 属性会错也会空（实测：肯塔基 911 点层被标成 IN；另一层 state 为空）；
  · 按州索引去判 → 这些层无条件落不了县，UNLOCATED 被彻底虚高，真假缺口混在一起没法解释。

为什么不猜：
  · 判县只用「点本身 + TIGER 县多边形射线法」；bbox 只做网格预筛，命中必须过 PIP。
  · 县界全部来自本地缓存 `analysis/tiger_county/<ST>.json.gz`（50 州 / 3.0MB gzip），不访问上游。
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import county_tiger as CT                     # noqa: E402


def locate(idx, lat, lon):
    """射线法判定。bbox 只做预筛（禁用 bbox 当结论），命中必须过 PIP。"""
    if idx is None or lat is None or lon is None:
        return None
    fast = getattr(idx, "locate", None)
    if callable(fast):
        return fast(lat, lon)
    for fips, e in idx.by_fips.items():
        if not CT.in_bbox(lat, lon, e["bbox"]):
            continue
        if CT.pip(lat, lon, e["geom"]):
            return fips
    return None


class NationalIndex:
    """全国县索引：3,089 个县，fips → {name, bbox, geom}；1° 网格把候选县压到个位数。"""

    def __init__(self, cache_dir: str = "", cell: float = 1.0):
        self.by_fips = {}
        self.grid = {}
        self.cell = cell
        self.states = []
        self.fips2state = {}
        d = cache_dir or os.path.join(ROOT, "analysis", "tiger_county")
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not fn.endswith(".json.gz"):
                continue
            st = fn[:2].upper()
            try:
                idx = CT.fetch_state(st)          # 有本地缓存就只读缓存（不联网）
            except Exception:                     # noqa: BLE001
                continue
            if not idx or not idx.by_fips:
                continue
            self.states.append(st)
            for fips, e in idx.by_fips.items():
                if fips in self.by_fips:
                    continue
                self.by_fips[fips] = e
                self.fips2state[fips[:2]] = st
                self._cells_of(e["bbox"], fips)

    def _cells_of(self, bb, fips):
        lon0, lat0, lon1, lat1 = bb
        if lon0 == lon1 == 0 and lat0 == lat1 == 0:
            return
        for lat in range(int(math.floor(lat0)), int(math.floor(lat1)) + 1):
            for lon in range(int(math.floor(lon0)), int(math.floor(lon1)) + 1):
                self.grid.setdefault((lat, lon), []).append(fips)

    def locate(self, lat: float, lon: float, rings: int = 1):
        if lat is None or lon is None:
            return None
        la, lo = int(math.floor(lat)), int(math.floor(lon))
        seen = set()
        for dy in range(-rings, rings + 1):        # 带一圈邻居格：简化几何容易跨格
            for dx in range(-rings, rings + 1):
                for fips in self.grid.get((la + dy, lo + dx)) or ():
                    if fips in seen:
                        continue
                    seen.add(fips)
                    e = self.by_fips[fips]
                    if not CT.in_bbox(lat, lon, e["bbox"]):
                        continue
                    if CT.pip(lat, lon, e["geom"]):
                        return fips
        return None

    def name_of(self, fips: str) -> str:
        return (self.by_fips.get(fips) or {}).get("name") or ""


_SINGLETON = None


def get_national() -> NationalIndex:
    """进程内单例（几 MB 几何 + 网格，重复建是浪费）。"""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = NationalIndex()
    return _SINGLETON
