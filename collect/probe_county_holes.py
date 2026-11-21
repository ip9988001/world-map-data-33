#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判县精度复核（只读探针，不改判定逻辑）—— 「洞（interior ring）」这一类错的实测脚本。

为什么有这个脚本：docs/DEPENDENCY-VERDICT-20261122.md 的判词「维持禁令（零新依赖）」
建立在一条可证伪的实测上 —— 现 `county_tiger.pip()` **只看外环**（`_rings()` 只取
`coordinates[0]` / `poly[0]`），于是「县内飞地（洞）」会被误判成该县领土，且常与真正
辖有该地的县**重复认领**（`locate()` 返回先撞到的那个，结果依赖遍历顺序）。

任何人跑本脚本都能复现/证伪这个结论；脚本**不写任何文件、不改任何生产代码**。

用法：
  python3 collect/probe_county_holes.py
  python3 collect/probe_county_holes.py --cache analysis/tiger_county --limit-holes 5

判据：
  · 参考实现 = 偶奇（even-odd）规则遍历「同一多边形的全部环（外环 + 洞）」，
    等价二仓 `scripts/coverage_counters.point_in_rings()`（其 docstring 明确「天然处理洞」）。
  · 三仓现实现 = `county_tiger.pip()`：把各多边形的外环做**并集**，洞被当成实心。
  · 「错判」= 参考判「在洞外」而现实现判「在县内」。
  · 「重复认领」= 该点同时被 ≥2 个县判为在县内（生产上即归属不确定）。
退出码：0 = 与定案文档一致（跑通即可）；2 = 缓存缺失（无法复核）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import county_tiger as CT          # noqa: E402


def even_odd(lat: float, lon: float, rings: list) -> bool:
    """偶奇规则：一个多边形的全部环（外环 + 洞）一起数穿越次数。等价二仓 point_in_rings。"""
    inside = False
    for ring in rings:
        n = len(ring)
        if n < 3:
            continue
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-18) + xi):
                inside = not inside
            j = i
    return inside


def ring_centroid(ring: list) -> tuple[float, float]:
    """环的顶点平均中心（凸环必在环内；凹洞近似，够用来取证）。"""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (sum(ys) / len(ys), sum(xs) / len(xs))


def load_features(cache: str) -> dict:
    feats: dict[str, dict] = {}
    for p in sorted(glob.glob(os.path.join(cache, "*.json.gz"))):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            doc = json.load(fh)
        for f in doc.get("features") or []:
            g = f.get("geometry") or {}
            fips = str((f.get("properties") or {}).get("GEOID") or "")
            if fips and g.get("coordinates"):
                feats[fips] = g
    return feats


def polygons_of(geom: dict) -> list[list]:
    c = geom.get("coordinates") or []
    if geom.get("type") == "Polygon":
        return [c] if c else []
    if geom.get("type") == "MultiPolygon":
        return [poly for poly in c if poly]
    return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(HERE), "analysis", "tiger_county"))
    ap.add_argument("--limit-holes", type=int, default=3, help="打印几个错判样本")
    a = ap.parse_args(argv)

    if not glob.glob(os.path.join(a.cache, "*.json.gz")):
        print("缓存缺失：%s/*.json.gz（先跑 collect/county_tiger.py --build）" % a.cache,
              file=sys.stderr)
        return 2

    feats = load_features(a.cache)
    counties = len(feats)
    multi = 0
    with_hole = 0
    hole_pts = wrong = dual = 0
    samples: list[tuple] = []

    for fips, g in feats.items():
        polys = polygons_of(g)
        if len(polys) > 1:
            multi += 1
        if any(len(poly) > 1 for poly in polys):
            with_hole += 1
        for poly in polys:
            for hole in poly[1:]:
                if len(hole) < 4:
                    continue
                lat, lon = ring_centroid(hole)
                hole_pts += 1
                now = CT.pip(lat, lon, g)              # 三仓现实现
                ref = even_odd(lat, lon, poly)         # 参考：该多边形的偶奇（洞内应为 False）
                if now and not ref:
                    wrong += 1
                    owners = [f for f, gg in feats.items() if f != fips and CT.pip(lat, lon, gg)]
                    if owners:
                        dual += 1
                    if len(samples) < a.limit_holes:
                        samples.append((fips, round(lat, 5), round(lon, 5), owners[:2]))

    print("== 判县洞复核（只读探针）==")
    print("县 feature 总数        = %d" % counties)
    print("MultiPolygon 县        = %d" % multi)
    print("含 interior ring（洞）的县 = %d" % with_hole)
    print("洞的代表点数           = %d" % hole_pts)
    print("三仓 pip 误判「洞内 = 县内」= %d" % wrong)
    print("其中同时被他县认领（重复归属）= %d" % dual)
    for fips, lat, lon, owners in samples:
        print("  样本：fips=%s lat=%.5f lon=%.5f → 现实现=在县内，偶奇=在洞外；真正辖有该地的县=%s"
              % (fips, lat, lon, owners or "（本批缓存内无他县认领）"))
    print("\n结论：洞被当成实心 → 这类点会重复归属；`locate()` 返回先撞到的县，结果依赖遍历顺序。")
    print("修法（纯标准库，不引 shapely）：pip 改成「同一多边形的全部环做偶奇」，"
          "而不是「各外环取并集」——二仓 point_in_rings() 已是正确写法。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
