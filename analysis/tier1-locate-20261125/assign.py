#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三路证据 → 定州（规则写死在本文件，方法见 method.md）。

投票只算 E1/E2/E3（E4 只做 tie-break）：
  state_final = 三路里出现次数最多、且出现在 ≥2 路的州
  → 2 路一致 confidence=high；3 路一致 very_high；只有 1 路有线索 medium
  → 多州并列 / 无多数 = unresolved + conflict / none
  → 任一州 E3 覆盖 ≥20% ⇒ multi_state=true
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict

# 禁 shapely / rtree（docs/DEPENDENCY-VERDICT-20261122.md）：几何全部自研，见下方「自研几何」块。

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref")
AGOL = os.path.join(REF, "agol")
WORK = os.path.join(HERE, "_work")
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

NAME2AB = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC",
}
ABBR = set(NAME2AB.values())
# 与普通英文词冲突的缩写，只在地址形态（", XX" / "XX 12345" / "XX;" / "XX)"）里接受
RISKY = {"IN", "OR", "ME", "OK", "DE", "HI", "LA", "MS", "AL", "AR", "CA", "CO", "ID", "MA", "MD", "PA", "OH", "MT"}

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
HTML_RE = re.compile(r"<[^>]{0,400}>")
CSS_RE = re.compile(r"(?:width|height|style|font|color|border|margin|padding|text-align)\s*:\s*[^;\"']{0,40};?", re.I)


def strip_html(t: str) -> str:
    """去掉 HTML 标签/CSS 片段——AGOL item.description 常是整段 HTML 表格，
    里面 style 属性会制造 'ID'/'IN' 这类假州缩写。"""
    t = HTML_RE.sub(" ", t)
    t = CSS_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()
STOP_PHRASES = {
    "Address", "Addresses", "Address Point", "Address Points", "Parcels", "Parcel", "Zoning",
    "Fire", "Police", "Sheriff", "Emergency", "Survey", "Base Map", "Basemap", "Web Map",
    "County", "City", "Town", "Village", "Township", "Borough", "State", "United States",
    "Public", "Private", "Data", "Layer", "View", "Service", "Feature", "Map", "Owner",
}


# ---------------------------------------------------------------- refs
def load_norm(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"^\s*(city|town|village|township|borough|county|parish)\s+of\s+", " ", s)
    s = re.sub(r"\b(county|parish|borough|census area|municipio)\b", " ", s)
    s = re.sub(r"\b(city|town|village|township|cdp)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- 自研几何（纯标准库）
# 裁决：docs/DEPENDENCY-VERDICT-20261122.md —— shapely / rtree 永不用作运行时依赖。
# 口径与 collect/county_tiger.py（射线法 pip）+ collect/county_index.py（bbox 预筛）一致。
# 数据结构：polys = [ [外环, 洞环...], ... ]，环 = [(x, y), ...]（首尾点只留一个）。


def _clean_ring(ring) -> list | None:
    """环点清洗：非数值/NaN 直接判废；<4 点（含闭合点）或 <3 个不同顶点 = 退化环 → None。"""
    raw = list(ring or [])
    if len(raw) < 4:
        return None
    out = []
    for p in raw:
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            return None
        if x != x or y != y:                       # NaN
            return None
        if out and out[-1][0] == x and out[-1][1] == y:
            continue                                # 连续重复点
        out.append((x, y))
    if len(out) >= 2 and out[0] == out[-1]:
        out = out[:-1]                              # 去掉闭合点
    if len(out) < 3 or len(set(out)) < 3:
        return None
    return out


def _load_geom(g: dict) -> list:
    """GeoJSON geometry → polys；外环退化则丢整个多边形，洞环退化则丢该洞。"""
    if not isinstance(g, dict):
        return []
    t, c = g.get("type"), g.get("coordinates") or []
    if t == "Polygon":
        raw_polys = [c]
    elif t == "MultiPolygon":
        raw_polys = c
    else:
        return []
    polys = []
    for raw in raw_polys or []:
        rings = []
        for i, ring in enumerate(raw or []):
            r = _clean_ring(ring)
            if r is None:
                if i == 0:                          # 外环不够 3 点 → 跳过该多边形
                    rings = []
                    break
                continue                            # 洞环退化 → 丢洞，保留外环
            rings.append(r)
        if rings:
            polys.append(rings)
    return polys


def _bbox(polys) -> tuple | None:
    """外环整体包围盒。只当粗筛用（永不误排除）；AK 的阿留申环跨 ±180，
    其 bbox 会横跨 359°，因此**不参与**面积/占比判断。"""
    xs, ys = [], []
    for rings in polys:
        for x, y in rings[0]:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _pip(polys, x: float, y: float) -> bool:
    """偶奇射线法。遍历该州**全部环**（外环 + 洞环）：穿外环一次进、穿洞环一次出，天然处理洞。"""
    inside = False
    for rings in polys:
        for ring in rings:
            n = len(ring)
            j = n - 1
            for i in range(n):
                xi, yi = ring[i]
                xj, yj = ring[j]
                if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
    return inside


def _seg_dist(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _dist_to_rings(polys, x: float, y: float) -> float:
    """点到州界（各环各线段）的最小距离，单位 = 度（与 buffer(0.002) 同口径）。"""
    best = float("inf")
    for rings in polys:
        for ring in rings:
            n = len(ring)
            j = n - 1
            for i in range(n):
                xi, yi = ring[i]
                xj, yj = ring[j]
                d = _seg_dist(x, y, xj, yj, xi, yi)
                if d < best:
                    best = d
                j = i
    return best


def _ring_area_centroid(ring):
    """扇形三角化：返回 (有向面积, 质心x, 质心y)；退化为 (0,0,0)。"""
    x0, y0 = ring[0]
    a = cx = cy = 0.0
    for i in range(1, len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        sa = ((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0
        a += sa
        cx += sa * (x0 + x1 + x2) / 3.0
        cy += sa * (y0 + y1 + y2) / 3.0
    if a == 0.0:
        return (0.0, 0.0, 0.0)
    return (a, cx / a, cy / a)


def _centroid(polys):
    """按环面积加权求质心：外环权重取正、洞环取负，多面累加；总面积 ≈ 0 → None。"""
    tot = sx = sy = 0.0
    for rings in polys:
        for i, ring in enumerate(rings):
            a, cx, cy = _ring_area_centroid(ring)
            if a == 0.0:
                continue
            w = abs(a) * (1.0 if i == 0 else -1.0)
            tot += w
            sx += w * cx
            sy += w * cy
    if abs(tot) < 1e-12:
        return None
    return (sx / tot, sy / tot)


def _ring_signed_area(ring) -> float:
    return _ring_area_centroid(ring)[0]


def _clip_ring(ring, xmin: float, ymin: float, xmax: float, ymax: float) -> list:
    """Sutherland–Hodgman：用矩形四条边逐边裁环。"""
    pts = list(ring)

    def clip(ps, keep, inter):
        if not ps:
            return []
        out = []
        prev = ps[-1]
        prev_in = keep(prev)
        for cur in ps:
            cur_in = keep(cur)
            if cur_in:
                if not prev_in:
                    out.append(inter(prev, cur))
                out.append(cur)
            elif prev_in:
                out.append(inter(prev, cur))
            prev, prev_in = cur, cur_in
        return out

    def ix(a, b, xv):
        d = b[0] - a[0]
        t = 0.0 if d == 0.0 else (xv - a[0]) / d
        return (xv, a[1] + t * (b[1] - a[1]))

    def iy(a, b, yv):
        d = b[1] - a[1]
        t = 0.0 if d == 0.0 else (yv - a[1]) / d
        return (a[0] + t * (b[0] - a[0]), yv)

    pts = clip(pts, lambda p: p[0] >= xmin, lambda a, b: ix(a, b, xmin))
    pts = clip(pts, lambda p: p[0] <= xmax, lambda a, b: ix(a, b, xmax))
    pts = clip(pts, lambda p: p[1] >= ymin, lambda a, b: iy(a, b, ymin))
    pts = clip(pts, lambda p: p[1] <= ymax, lambda a, b: iy(a, b, ymax))
    return pts if len(pts) >= 3 else []


def _rect_area_in_polygon(polys, xmin: float, ymin: float, xmax: float, ymax: float) -> float:
    """矩形 ∩ 多边形 的面积（外环裁剪面积 − 洞环裁剪面积，逐面累加，负数截 0）。"""
    tot = 0.0
    for rings in polys:
        for i, ring in enumerate(rings):
            clipped = _clip_ring(ring, xmin, ymin, xmax, ymax)
            if not clipped:
                continue
            a = abs(_ring_signed_area(clipped))
            tot += a if i == 0 else -a
    return tot if tot > 0 else 0.0


def load_state_geoms(primary=True) -> dict:
    """primary=True → TIGERweb 200m 简化；False → 仓内 1:20m（对照）。"""
    if primary:
        d = json.loads(gzip.open(os.path.join(REF, "tigerweb-states.geojson.gz")).read())
        key, name_key = "STATE", "NAME"
    else:
        d = json.load(open(os.path.join(REPO, "survey", "ng911", "us_states.json"), encoding="utf-8"))
        key, name_key = None, "name"
    out = {}
    for ft in d["features"]:
        p = ft["properties"]
        nm = p[name_key]
        ab = NAME2AB.get(nm) if name_key == "name" else fips2ab(p["STATE"])
        if not ab:
            continue
        polys = _load_geom(ft["geometry"])
        if not polys:
            continue
        out[ab] = polys
    return out


FIPS2AB = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE",
    "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
    "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM",
    "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}


def fips2ab(f: str) -> str:
    return FIPS2AB.get(str(f).zfill(2), "")


# ---------------------------------------------------------------- text mining
def texts_from(objs) -> list:
    out = []
    for label, obj, keys in objs:
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                out.append((f"{label}.{k}", v.strip()))
            elif isinstance(v, list):
                for it in v:
                    if isinstance(it, str) and it.strip():
                        out.append((f"{label}.{k}", it.strip()))
    return out


def explicit_states(blob) -> tuple[set, list]:
    st, hits = set(), []
    for src, t in blob:
        t_clean = strip_html(EMAIL_RE.sub(" ", t))
        for nm, ab in NAME2AB.items():
            m = re.search(r"(?<![A-Za-z])" + re.escape(nm) + r"(?![A-Za-z])", t_clean, flags=re.I)
            if m:
                st.add(ab)
                hits.append(f"[{src}] …{t_clean[max(0, m.start()-50):m.end()+50]}…")
        for m in re.finditer(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", t_clean):
            a = m.group(1)
            if a not in ABBR:
                continue
            ctx = t_clean[max(0, m.start() - 30): m.end() + 30]
            if a in RISKY:
                # 易混缩写只认地址形态：", XX" 或 "XX 12345"
                win = t_clean[max(0, m.start() - 2):m.end() + 7]
                if not (re.search(r",\s*" + a + r"\b", win) or re.search(r"\b" + a + r"\s+\d{5}", win)):
                    continue
            st.add(a)
            hits.append(f"[{src}] …{ctx}…")
        for m in re.finditer(r"\.([a-z]{2})\.us\b", t.lower()):
            a = m.group(1).upper()
            if a in ABBR:
                st.add(a)
                hits.append(f"[{src}] domain .{a.lower()}.us")
    return st, hits


PHRASE_RE = re.compile(r"\b([A-Z][A-Za-z'\.\-]+(?:\s+(?:of\s+|the\s+)?[A-Z][A-Za-z'\.\-]+){0,3})\b")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]{4,30}")


def gazetteer_states(blob, places: dict, counties: dict, limit: int = 6) -> tuple[set, list, set]:
    """县名/地名 → 候选州。返回 (证据州集, 命中记录, 因同名过多被弃用的州集)。
    >limit 个同名的（Washington/Lincoln/Springfield 这类）只记录不投票。"""
    st, hits, dropped = set(), [], set()
    seen = set()
    for src, t in blob:
        t = strip_html(t)
        # ElSegundo / MinongGIS / GrandForksGIS → 拆驼峰，避免粘连导致漏检
        t = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t)
        for m in PHRASE_RE.finditer(t):
            ph = m.group(1).strip()
            if ph in STOP_PHRASES or len(ph) < 4:
                continue
            cand = None
            multiword = False
            # 短语尾部常粘上 ". This" 之类的词（正则会吞掉点号后的首词）→ 逐级截短再查
            words = re.sub(r"[\.,;:]$", "", ph).split()
            for nn in range(len(words), 0, -1):
                key = norm(" ".join(words[:nn]))
                if not key or (ph, key) in seen:
                    continue
                cand = counties.get(key) or places.get(key)
                if cand:
                    seen.add((ph, key))
                    multiword = nn >= 2   # 用原短语词数，别用归一化后的（"City of Boston" 归一化后只剩 1 词）
                    break
            if not cand:
                continue
            # 单字地名同名多州的（Harper / Falls / Tyler 这类）噪声太大，不作证据
            if len(cand) > 1 and not multiword:
                continue
            if len(cand) > limit:
                dropped |= set(cand)
                hits.append(f"[{src}] {ph} → 同名 {len(cand)} 州（不作为证据）")
                continue
            st |= set(cand)
            hits.append(f"[{src}] {ph} → {'/'.join(sorted(cand))}")
    return st, hits, dropped


# ---------------------------------------------------------------- E3
def ensure_geom() -> None:
    """ref/agol/*_geom1000.json 体积大（80MB），仓里存 ref/geom1000.tar.gz，用前解压。"""
    tar = os.path.join(REF, "geom1000.tar.gz")
    if not os.path.exists(tar):
        return
    have = {f for f in os.listdir(AGOL) if f.endswith("_geom1000.json")}
    if len(have) >= 80:
        return
    import tarfile
    with tarfile.open(tar) as tf:
        tf.extractall(AGOL)


def geom_stats(slug: str, S: dict, which: str):
    """返回 (sample_shares, purity, n, bbox_shares)。"""
    p = os.path.join(AGOL, f"{slug}_geom1000.json")
    shares, n = {}, 0
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        cnt = Counter()
        for ft in d.get("features") or []:
            g = ft.get("geometry") or {}
            pt = rep_point(g)
            if not pt:
                continue
            n += 1
            cnt[which_state(pt[0], pt[1], S) or "OUT"] += 1
        if n:
            shares = {k: v / n for k, v in cnt.items() if k != "OUT"}
            shares["_OUT"] = cnt.get("OUT", 0) / n
    bs = {}
    ep = os.path.join(AGOL, f"{slug}_extent4326.json")
    if os.path.exists(ep):
        e = (json.load(open(ep, encoding="utf-8")) or {}).get("extent") or {}
        if {"xmin", "ymin", "xmax", "ymax"} <= set(e):
            xmin, ymin, xmax, ymax = e["xmin"], e["ymin"], e["xmax"], e["ymax"]
            rect_area = (xmax - xmin) * (ymax - ymin)
            if rect_area > 0:
                for ab, polys in S.items():
                    inter = _rect_area_in_polygon(polys, xmin, ymin, xmax, ymax)
                    if inter > 0:
                        bs[ab] = inter / rect_area
    purity = max([v for k, v in shares.items() if k != "_OUT"], default=0.0)
    return shares, purity, n, bs


def rep_point(g: dict):
    t = g.get("type")
    c = g.get("coordinates")
    if t == "Point":
        return c
    if t == "MultiPoint" and c:
        return c[0]
    if t == "Point" and c is None:
        return None
    if t == "LineString" and c:
        return c[len(c) // 2]
    if t == "MultiLineString" and c and c[0]:
        return c[0][len(c[0]) // 2]
    if t == "Polygon" and c and c[0]:
        pt = _centroid(_load_geom(g))
        if pt:
            return [pt[0], pt[1]]
        ring = c[0]
        xs = [p[0] for p in ring[:-1]] or [ring[0][0]]
        ys = [p[1] for p in ring[:-1]] or [ring[0][1]]
        return [sum(xs) / len(xs), sum(ys) / len(ys)]
    if t == "MultiPolygon" and c and c[0] and c[0][0]:
        pt = _centroid(_load_geom(g))
        if pt:
            return [pt[0], pt[1]]
        return rep_point({"type": "Polygon", "coordinates": c[0]})
    return None


_GEOM: dict = {}          # id(S) → [(ab, polys, bbox)]，保持 S 的插入顺序（结果确定性）


def _state_index(S: dict) -> list:
    """按 S 建索引：只算一次 bbox 预筛，之后复用（S / S20 两份各自缓存）。"""
    key = id(S)
    idx = _GEOM.get(key)
    if idx is None:
        idx = []
        for ab, polys in S.items():
            bb = _bbox(polys)
            if bb:
                idx.append((ab, polys, bb))
        _GEOM[key] = idx
    return idx


def which_state(x: float, y: float, S: dict) -> str:
    if not (-180 <= x <= -60 and 15 <= y <= 75):
        return ""
    idx = _state_index(S)
    for ab, polys, (x0, y0, x1, y1) in idx:
        if x0 <= x <= x1 and y0 <= y <= y1 and _pip(polys, x, y):
            return ab
    # 近岸/边界点：容差 0.002°（原点在州界外侧 0.002° 内仍归该州；外扩 bbox 预筛后再算点到环距离）
    for ab, polys, (x0, y0, x1, y1) in idx:
        if x0 - 0.002 <= x <= x1 + 0.002 and y0 - 0.002 <= y <= y1 + 0.002 \
                and _dist_to_rings(polys, x, y) < 0.002:
            return ab
    return ""


# ---------------------------------------------------------------- E2
BAD_STATE_FIELDS = {"st_name", "stname", "st_num", "stnum", "street", "streetname", "st_prefixdir",
                    "st_postdir", "st_pretyp", "st_postyp", "prefixdir", "suffixdir"}


def e2_states(rec: dict, places: dict, counties: dict) -> tuple[set, list, str, int]:
    """返回 (投票用州集, 命中记录, 备注, 该路候选集大小)。"""
    st, hits = set(), []
    broad = ""
    distinct = rec.get("distinct") or {}
    n_cand = 0
    for k, vals in distinct.items():
        kind, field = k.split(":", 1)
        if field.lower() in BAD_STATE_FIELDS:
            continue
        if kind == "state":
            codes = set()
            for v in vals:
                v = (v or "").strip()
                if len(v) == 2 and v.upper() in ABBR:
                    codes.add(v.upper())
                elif v.title() in NAME2AB:
                    codes.add(NAME2AB[v.title()])
            if len(codes) > 3:
                # 该字段含 >3 个州 ⇒ 多州/邮寄地址集合，不能当单州证据
                broad = f"E2 字段 {field} 含 {len(codes)} 州（多州口径，不作单州证据）"
                hits.append(f"[distinct {field}] {sorted(codes)[:8]}…")
                n_cand = max(n_cand, len(codes))
                continue
            st |= codes
            if codes:
                hits.append(f"[distinct {field}] {sorted(codes)}")
                n_cand = max(n_cand, len(codes))
        elif kind in ("county", "city"):
            cs = set()
            for v in vals:
                v = (v or "").strip()
                if not v:
                    continue
                cands = (counties.get(norm(v)) if kind == "county" else places.get(norm(v))) or []
                if 1 <= len(cands) <= 6:
                    cs |= set(cands)
                    hits.append(f"[distinct {field}] {v} → {'/'.join(cands)}")
            if len(cs) > 3:
                broad = f"E2 {kind} 字段 {field} 跨 {len(cs)} 州（多州口径）"
                n_cand = max(n_cand, len(cs))
                continue
            st |= cs
            n_cand = max(n_cand, len(cs))
    # 地址串里的 ", XX 12345"
    for attrs in rec.get("sample_attrs") or []:
        for k, v in attrs.items():
            if not isinstance(v, str):
                continue
            m = re.search(r",\s*([A-Z]{2})[\s,]+\d{5}", v)
            if m and m.group(1) in ABBR:
                st.add(m.group(1))
                hits.append(f"[sample {k}] {v[:80]} → {m.group(1)}")
            # 属性值里的地名/县名（Dorchester / Kiawah / Hedgesville 这类）
            w = v.strip()
            place_field = bool(re.search(r"city|town|muni|place|communit|hood|village|parish|county|"
                                         r"msag|locality|jurisdic", k, re.I))
            if place_field and 4 <= len(w) <= 40 and re.fullmatch(r"[A-Za-z][A-Za-z' .\-]+", w):
                cand = places.get(norm(w)) or counties.get(norm(w))
                if cand and len(cand) == 1:
                    st.add(next(iter(cand)))
                    hits.append(f"[sample {k}] {w} → {next(iter(cand))}")
                    n_cand = max(n_cand, 1)
    if st:
        n_cand = max(n_cand, len(st))
    return st, hits, broad, n_cand


# ---------------------------------------------------------------- main
def main(write: bool = True) -> None:
    ensure_geom()
    rows = list(csv.DictReader(open(os.path.join(HERE, "tier1-unlocated.csv"), newline="", encoding="utf-8")))
    e1 = {x["slug"]: x for x in json.load(open(os.path.join(WORK, "e1_all.json"), encoding="utf-8"))}
    e2 = {x["slug"]: x for x in json.load(open(os.path.join(WORK, "e2_all.json"), encoding="utf-8"))}
    places = load_norm(os.path.join(REF, "places-index.json"))
    counties = load_norm(os.path.join(REF, "counties-index.json"))
    S = load_state_geoms(True)
    S20 = load_state_geoms(False)
    over = {}
    for ovp in (os.path.join(HERE, "overrides.json"), os.path.join(WORK, "overrides.json")):
        if os.path.exists(ovp):
            over = json.load(open(ovp, encoding="utf-8"))
            break

    out = []
    for r in rows:
        from locate import slug as mkslug  # 同一路径规则
        s = mkslug(r["url"])
        rec1 = e1.get(s) or {}
        rec2 = e2.get(s) or {}
        # --- E1 文本池：item/service/user 描述与标题（不含 layer.name，layer.name 归 E4）
        blob1 = []
        for fname, label, keys in [
            (f"{s}_layer.json", "layer", ["description", "copyrightText"]),
            (f"{s}_service.json", "service", ["serviceDescription", "description", "copyrightText", "name"]),
        ]:
            p = os.path.join(AGOL, fname)
            if os.path.exists(p):
                blob1 += texts_from([(label, json.load(open(p, encoding="utf-8")), keys)])
        item_path = None
        for fn in os.listdir(AGOL):
            if fn.startswith("item_") and rec1.get("serviceItemId") and rec1["serviceItemId"] in fn:
                item_path = os.path.join(AGOL, fn)
        if item_path:
            blob1 += texts_from([("item", json.load(open(item_path, encoding="utf-8")),
                                  ["title", "snippet", "description", "accessInformation"])])
        owner = rec1.get("item_owner")
        if owner:
            blob1.append(("item.owner", owner))
        up = os.path.join(AGOL, f"user_{owner}.json") if owner else None
        if up and os.path.exists(up):
            blob1 += texts_from([("user", json.load(open(up, encoding="utf-8")),
                                  ["fullName", "description"])])
        e1_explicit, e1_hits = explicit_states(blob1)
        e1_gaz, e1_gaz_hits, e1_dropped = gazetteer_states(blob1, places, counties)
        e1_strong = set(e1_explicit)
        e1_weak = set(e1_gaz) - e1_strong
        # --- E4：layer 名 + url 路径（弱证据，只做 tie-break）
        blob4 = [(("layer.name"), str(rec1.get("layer_name") or "")), ("url.path", r["url"])]
        e4_explicit, e4_hits = explicit_states(blob4)
        e4_gaz, e4_gaz_hits, _e4d = gazetteer_states(blob4, places, counties)

        # --- E3
        shares, purity, n, bs = geom_stats(s, S, which_state)
        shares20, purity20, n20, _ = geom_stats(s, S20, which_state)
        e3 = {k: v for k, v in shares.items() if k != "_OUT" and v >= 0.05}
        e3 = dict(sorted(e3.items(), key=lambda kv: -kv[1]))
        e3b = {k: v for k, v in bs.items() if v >= 0.05}
        e3b = dict(sorted(e3b.items(), key=lambda kv: -kv[1]))
        # 投票门槛：最高占比 <20% ⇒ 该层几何是散的，不作为单州证据（只记录）
        top_sample = next(iter(e3.values()), 0.0)
        top_bbox = next(iter(e3b.values()), 0.0)
        e3_set = set()
        if top_sample >= 0.20:
            e3_set |= set(e3)
        if top_bbox >= 0.20 and top_sample < 0.20:
            e3_set |= set(e3b)
        dispersed = (n or bs) and not e3_set
        method = []
        if n:
            method.append(f"sample(n={n})")
        if bs:
            method.append("bbox4326")
        # --- 投票
        e2s, e2_hits, e2_broad, e2_n = e2_states(rec2, places, counties)
        e1v = set(e1_strong) or set(e1_weak)
        paths = {"E1": e1v, "E2": set(e2s), "E3": set(e3_set)}
        cnt = Counter()
        for v in paths.values():
            for st_ in v:
                cnt[st_] += 1
        best = max(cnt.values()) if cnt else 0
        cands = sorted([k for k, v in cnt.items() if v == best]) if best else []
        # 跨州层判定：口径 = 采样点落州占比（无采样才退 bbox）。
        # ≥2 州各 ≥20% ⇒ 跨州；最高占比 <50% 且 ≥3 州各 ≥5% ⇒ 散列跨州。
        # bbox 比州界大（矩形外扩），不能拿来判跨州，只在 e3_states 里展示。
        cov_src = e3 if n else e3b
        big = [k for k, v in cov_src.items() if v >= 0.20]
        spread = sorted({k for k, v in cov_src.items() if v >= 0.05})
        multi = (len(big) >= 2) or (top_sample < 0.50 and len(spread) >= 3)
        top_e3 = next(iter(e3), "") or next(iter(e3b), "")
        final, conf = "unresolved", "none"
        note = []
        if best >= 2 and len(cands) == 1:
            final, conf = cands[0], ("very_high" if best == 3 else "high")
        elif multi and top_e3:
            # 规则 5：跨州层，取 E3 占比最大的州；两路以上一致仍给 high
            final = top_e3
            conf = "high" if top_e3 in cands and best >= 2 else "medium"
            note.append("跨州层：取几何占比最大州（规则 5）")
        elif best >= 2 and len(cands) > 1:
            t = (e4_explicit or e4_gaz) & set(cands)
            if len(t) == 1:
                final, conf = t.pop(), "high"
                note.append("E4 tie-break（layer 名/url 路径）")
            else:
                final, conf = "unresolved", "conflict"
                note.append("多州并列：" + "/".join(cands))
        elif best == 1 and len(cands) == 1:
            final, conf = cands[0], "medium"
        elif best == 1 and len(cands) > 1:
            if top_sample >= 0.50:
                final, conf = top_e3, "medium"
                others = [f"{p}={sorted(v)[:4]}" for p, v in paths.items() if p != "E3" and v]
                note.append("仅几何一路有线索，按采样最高占比取（≥50%）"
                            + (f"；与 {'; '.join(others)} 不一致（已按几何定）" if others else ""))
            else:
                final, conf = "unresolved", "conflict"
                note.append("单路多州并列：" + "/".join(cands[:8]))
        if dispersed:
            note.append(f"几何散：采样最高 {top_sample*100:.1f}% / bbox 最高 {top_bbox*100:.1f}%（<20% 不投票）")
            if conf == "unresolved" and not cands:
                conf = "none"
        covered = sorted({k for k, v in cov_src.items() if v >= 0.05})
        bbox_extra = [k for k, v in e3b.items() if v >= 0.20 and k not in covered]
        if bbox_extra:
            note.append("bbox 另含 " + "/".join(sorted(bbox_extra)) + "（矩形外扩，不作跨州判据）")
        if e1_weak:
            note.append(f"E1 走县名/地名映射 {len(e1_weak)} 州")
        if e1_gaz_hits:
            note.append("; ".join(e1_gaz_hits[:2]))
        if e2_broad:
            note.append(e2_broad)
        if e2_n > 3:
            note.append(f"E2 候选 {e2_n} 州（宽口径，一致性为弱一致）")
        if shares.get("_OUT"):
            note.append(f"采样点 OUT {shares['_OUT']*100:.1f}%（州界外/水域/几何为空；n={n}）")
        if n and purity20 < purity - 0.05:
            note.append(f"对照(1:20m 粗界) 纯度 {purity20*100:.1f}%")
        rec = {
            "layer_id": r["layer_id"], "url": r["url"], "dialect_id": r["dialect_id"], "rows_n": r["rows_n"],
            "state_before": r["state"],
            "e1_states": "|".join(sorted(e1_strong or e1_weak)),
            "e1_evidence": (e1_hits + e1_gaz_hits)[:3] and " || ".join((e1_hits + e1_gaz_hits)[:3])[:400] or "",
            "e2_states": "|".join(sorted(e2s)),
            "e2_evidence": " || ".join(e2_hits[:3])[:400],
            "e3_states": "|".join(f"{k}:{v*100:.1f}%" for k, v in list(e3.items())[:5])
                          + ("; bbox→" + "|".join(f"{k}:{v*100:.1f}%" for k, v in list(e3b.items())[:5]) if e3b else ""),
            "e3_purity": f"{purity*100:.1f}%" if n else ("bbox-only" if bs else ""),
            "e3_method": "+".join(method),
            "e4_states": "|".join(sorted(e4_explicit or e4_gaz)),
            "state_final": final, "confidence": conf,
            "multi_state": "true" if multi else "false",
            "states_covered": "|".join(covered),
            "note": "; ".join(note)[:400],
        }
        if s in over:
            o = over[s]
            rec["state_final"] = o["state_final"]
            rec["confidence"] = o["confidence"]
            rec["note"] = (rec["note"] + " ; 人工复核：" + o["why"]).strip(" ;")[:400]
        out.append(rec)
        if not write:
            print(json.dumps({k: rec[k] for k in ("url", "e1_states", "e2_states", "e3_states", "e4_states",
                                                 "state_final", "confidence")}, ensure_ascii=False))

    if write:
        cols = ["layer_id", "url", "dialect_id", "rows_n", "state_before", "e1_states", "e1_evidence",
                "e2_states", "e2_evidence", "e3_states", "e3_purity", "e3_method", "e4_states",
                "state_final", "confidence", "multi_state", "states_covered", "note"]
        p = os.path.join(HERE, "tier1-unlocated-states.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(out)
        print("wrote", p, len(out))
        # 详细工作件（含 20m 对照、bbox 明细）
        json.dump(out, open(os.path.join(WORK, "states_detail.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(write="--dry" not in sys.argv)
