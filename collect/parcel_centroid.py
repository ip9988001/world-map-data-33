#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宗地质心 / 投影坐标救回 —— 给「无坐标层」补 latitude/longitude。

背景（2026-10-30 实测，先说结论）：
  · 三仓采集器**只落点几何**：`pilot.py` 只读 `geometry.y/.x`，Polygon 的 `rings` 被丢弃。
    所以宗地层资产里**没有几何**（抽样 7ABWQBGTG_Hutto_Parcels 23,591 行，记录键只有
    add_num/pre_dir/st_name/…/lat/lon/raw，raw 里只有 Shape__Area/Shape__Length）。
  ⇒ 「用宗地几何算质心」在当前资产上**不可行**，只能靠两类可离线证据救回坐标：
      ① 属性里的经纬度列（被范围校验误杀的那种）
      ② 属性里的**投影坐标**列（X/Y、EASTING/NORTHING，单位 ft/m）→ pyproj 转 WGS84

本脚本干三件事：
  1. `--audit`   逐层分类：能救（投影/经纬度） / 无源（geom_missing、no_source），给出覆盖率
  2. `--backfill` 对能量化的层落 `schema/coord-salvage-v1.json`（含 EPSG 判定过程与证据值）
  3. 几何路径的库函数（`polygon_centroid` / `representative_point` / `pip`）留好并单测，
     等下一轮采集打开 `returnCentroid=true`（见 pilot.py 的 PILOT_POLY_CENTROID）即可直接接上

铁律：
  · 投影转换失败 / EPSG 无法唯一定位 → `proj_failed` / `proj_ambiguous`，**不猜**
  · 质心落在凹多边形外 → 用 representative_point（扫描线最宽内区间中点），不用 centroid
  · 空几何 / 退化几何（面积 0、环 <3 点）→ `geom_invalid`
  · 全程离线：只读本地画像 + 本地 TIGER 县界缓存，不访问任何上游

用法：
  python3 collect/parcel_centroid.py --audit                 # 分类 + 覆盖率
  python3 collect/parcel_centroid.py --backfill              # 写 schema/coord-salvage-v1.json
  python3 collect/parcel_centroid.py --selftest              # 几何库单测
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))

try:
    from pyproj import CRS, Transformer
    import pyproj.database as PDB
except Exception:                                    # noqa: BLE001
    CRS = Transformer = PDB = None
try:
    import county_tiger as CT
except Exception:                                    # noqa: BLE001
    CT = None

FM = os.path.join(ROOT, "schema", "field-map-v2.json")
PROF = os.path.join(ROOT, "analysis", "out")
OUT_JSON = os.path.join(ROOT, "schema", "coord-salvage-v1.json")

# ---------------------------------------------------------------- 几何库（纯 stdlib）
def _rings(geom) -> list:
    if not geom:
        return []
    if isinstance(geom, dict):
        return geom.get("rings") or []
    return geom


def _area(ring: list) -> float:
    s = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def polygon_centroid(geom) -> tuple | None:
    """面积加权质心（holes 按有符号面积自动相减）。退化几何返回 None。"""
    rings = _rings(geom)
    if not rings:
        return None
    ax = ay = a = 0.0
    for ring in rings:
        if len(ring) < 3:
            continue
        ar = _area(ring)
        if ar == 0:
            continue
        cx = cy = 0.0
        for i in range(len(ring)):
            x1, y1 = ring[i][0], ring[i][1]
            x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
            cross = x1 * y2 - x2 * y1
            cx += (x1 + x2) * cross
            cy += (y1 + y2) * cross
        cx /= (6.0 * ar)
        cy /= (6.0 * ar)
        ax += cx * ar
        ay += cy * ar
        a += ar
    if a == 0:
        return None
    return (ax / a, ay / a)


def pip(x: float, y: float, ring: list) -> bool:
    """射线法（与 county_tiger.pip 同口径），ring 为 [[x,y],…]。"""
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def inside_geom(x: float, y: float, geom) -> bool:
    hits = [r for r in _rings(geom) if len(r) >= 3 and pip(x, y, r)]
    # 奇偶规则：落在奇数个环里 = 在实心区（外环减洞）
    return bool(len(hits) % 2)


def representative_point(geom) -> tuple | None:
    """质心在凹多边形外时用的保底点：扫描线找最宽「内部区间」的中点。"""
    rings = _rings(geom)
    if not rings:
        return None
    c = polygon_centroid(geom)
    if c and inside_geom(c[0], c[1], geom):
        return c
    ys, xs = [], []
    for r in rings:
        for pt in r:
            xs.append(pt[0])
            ys.append(pt[1])
    if not xs:
        return None
    best = None
    for frac in (0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.1, 0.9):
        y = min(ys) + (max(ys) - min(ys)) * frac
        # 该 y 上所有边的交点 x
        cut = []
        for r in rings:
            for i in range(len(r)):
                x1, y1 = r[i][0], r[i][1]
                x2, y2 = r[(i + 1) % len(r)][0], r[(i + 1) % len(r)][1]
                if (y1 > y) != (y2 > y):
                    cut.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        cut.sort()
        for i in range(0, len(cut) - 1, 2):
            mid = (cut[i] + cut[i + 1]) / 2.0
            if inside_geom(mid, y, geom):
                if best is None or (cut[i + 1] - cut[i]) > best[0]:
                    best = (cut[i + 1] - cut[i], mid, y)
        if best:
            break
    return (best[1], best[2]) if best else None


# ---------------------------------------------------------------- 投影判定
_CAND_CACHE: dict[str, list] = {}


def state_epsg_candidates(state: str) -> list:
    """该州可能的投影坐标系（只从 pyproj 自带库筛，不联网）。

    口径：PROJECTED_CRS 且 area_of_use 或 name 里出现州名 / 州缩写，
    优先 State Plane（SPCS）与 UTM。ESRI:* 不在 EPSG 库里，故只认 EPSG。
    """
    if not PDB:
        return []
    st = state.upper()
    if st in _CAND_CACHE:
        return _CAND_CACHE[st]
    sys.path.insert(0, os.path.join(ROOT, "analysis"))
    from field_map_v2 import STATE_ABBR                   # noqa: E402
    full = next((k.title() for k, v in STATE_ABBR.items() if v == st), "")
    try:
        infos = PDB.query_crs_info(auth_name="EPSG", pj_types=["PROJECTED_CRS"])
    except Exception:                                     # noqa: BLE001
        infos = []
    out = []
    for i in infos:
        name = (i.name or "").upper()
        area = (i.area_of_use.name if i.area_of_use else "") or ""
        area_u = area.upper()
        # 该州的任何投影坐标系都算候选（EPSG 名多是 "NAD83 / New York Long Island (ftUS)"，
        # 不含 "State Plane" 字样）；是否命中全靠「全部样例点必须转进本州」这一条硬校验。
        if full and full.upper() in area_u:
            out.append(int(i.code))
    _CAND_CACHE[st] = out
    return out


def state_county_bbox(state: str) -> tuple | None:
    """该州所有县的合并 bbox（本地 TIGER 缓存，作为「转换后落在本州」的判据之一）。"""
    if not CT:
        return None
    try:
        idx = CT.fetch_state(state)
    except Exception:                                     # noqa: BLE001
        return None
    boxes = [e["bbox"] for e in idx.by_fips.values()]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def in_box(lat, lon, box) -> bool:
    if not box:
        return False
    w, s, e, n = box
    return w <= lon <= e and s <= lat <= n


def _locate(state: str, lat: float, lon: float):
    """用本州县界多边形判县（禁用 bbox：bbox 会把邻县算进来，已实证 46% 顶点歧义）。"""
    if not CT:
        return None
    try:
        idx = CT.fetch_state(state)
    except Exception:                                     # noqa: BLE001
        return None
    return idx.locate(lat, lon)


def infer_projection(state: str, pairs: list) -> dict:
    """用 2~3 组 (x,y) 反推坐标系。

    判据（硬）：候选必须把**全部**样例点转进该州、且**落进同一个县**；
    多个候选都合格时，只有它们给出的**县集合完全一致**才算等价（否则 proj_ambiguous）。
    只用州 bbox 不够 —— 用错 zone 也能落进州 bbox，实测 ND83 各 zone 之间会混。
    """
    cands = state_epsg_candidates(state)
    if not cands:
        return {"status": "proj_failed", "why": "无可用候选坐标系（缺 pyproj 或州名不匹配）"}
    if not CT:
        return {"status": "proj_failed", "why": "county_tiger 不可用，无法校验转换结果"}
    good = {}
    for code in cands:
        try:
            tr = Transformer.from_crs(CRS.from_epsg(code), CRS.from_epsg(4326), always_xy=True)
        except Exception:                                 # noqa: BLE001
            continue
        fips = []
        bad = False
        for x, y in pairs:
            try:
                lon, lat = tr.transform(x, y)
            except Exception:                             # noqa: BLE001
                bad = True
                break
            if not (15 <= abs(lat) <= 75 and 60 <= abs(lon) <= 180):
                bad = True
                break
            f = _locate(state, lat, lon)
            if not f:
                bad = True
                break
            fips.append(f)
        if not bad and fips:
            good[code] = tuple(fips)
    if not good:
        return {"status": "proj_failed",
                "why": "%d 个候选无一能把全部样例点转进本州县界" % len(cands)}
    sets = set(good.values())
    if len(sets) == 1:
        # 多个代码但落县完全一致（NAD83/NAD27/ftUS/m 变体）→ 等价，取最小代码记账
        return {"status": "ok", "epsg": min(good),
                "epsg_equivalent": sorted(good), "county_fips": list(next(iter(sets)))}
    return {"status": "proj_ambiguous", "why": "候选坐标系落进不同县 → 不猜",
            "by_epsg": {str(k): list(v) for k, v in sorted(good.items())[:6]}}


# ---------------------------------------------------------------- 逐层分类
LAT_RX = r"^(LAT|LATITUDE|Y_COORD|LAT_DD|POINT_Y|CENTROID_Y|LAT_Y|Y_LAT|LAT_1|Y)$"
LON_RX = r"^(LON|LONG|LNG|LONGITUDE|X_COORD|LON_DD|POINT_X|CENTROID_X|LON_X|LONGITUDE_1|X)$"


def examples_num(f: dict) -> list:
    out = []
    for v in (f.get("ex") or []):
        try:
            out.append(float(v))
        except Exception:                                 # noqa: BLE001
            continue
    return out


def classify(lid: str, ent: dict, prof: dict) -> dict:
    """返回该层的救援结论。四态：salvaged / proj_ok / geom_missing / no_source。"""
    import re
    d = prof.get(lid) or {}
    F = d.get("fields") or {}
    st = (ent.get("state") or d.get("state") or "").upper()
    n = ent.get("rows_total") or 0
    rec = {"layer": lid, "rows": n, "state": st, "kind": ent.get("src_kind"),
           "county_scope": ent.get("county_scope"), "status": "", "why": ""}

    lat_c = [k for k in F if re.match(LAT_RX, k, re.I)]
    lon_c = [k for k in F if re.match(LON_RX, k, re.I)]

    # ① 直接经纬度（含被范围校验误杀的）
    for a in lat_c:
        for b in lon_c:
            la, lo = examples_num(F[a]), examples_num(F[b])
            good = [(y, x) for y, x in zip(la, lo)
                    if 15 <= abs(y) <= 75 and 60 <= abs(x) <= 180]
            if good and len(good) >= min(2, len(la)):
                rec.update(status="salvaged", why="属性里就是经纬度（%s/%s）" % (a, b),
                           lat_col=a, lon_col=b,
                           rate=round((F[a].get("nonempty") or 0) / max(1, F[a].get("n") or 1), 3))
                return rec

    # ② 投影坐标对 → 反推 EPSG
    for a in lat_c:
        for b in lon_c:
            pa = [(x, y) for x, y in zip(examples_num(F[b]), examples_num(F[a]))]
            if len(pa) < 2:
                continue
            if max(abs(x) for x, _ in pa) < 5000 and max(abs(y) for _, y in pa) < 5000:
                continue                                  # 量级不像投影坐标
            inf = infer_projection(st, pa[:3])
            if inf.get("status") == "ok":
                rec.update(status="proj_ok", why="投影坐标 %s/%s → EPSG:%s" % (b, a, inf["epsg"]),
                           x_col=b, y_col=a, epsg=inf["epsg"],
                           rate=round((F[a].get("nonempty") or 0) / max(1, F[a].get("n") or 1), 3))
                return rec
            rec.update(status=inf.get("status", "proj_failed"), why=inf.get("why") or "候选不唯一",
                       x_col=b, y_col=a, epsg_candidates=inf.get("epsg_candidates"))
            return rec

    # ③ 没有坐标列：几何也没落盘（采集器只留点几何）
    if rec["kind"] == "parcel_situs":
        rec.update(status="geom_missing",
                   why="采集器只落点几何，Polygon 的 rings 未持久化 → 无宗地几何可算质心")
    else:
        rec.update(status="no_source", why="既无坐标列也无可用几何")
    return rec


def load_all() -> tuple:
    fm = json.load(open(FM, encoding="utf-8"))
    # 州：field-map 里可能为空（无 state 列的层），要从层元数据 CSV 补，否则连候选坐标系都选不出来
    import csv
    state_by = {}
    for name in ("address_layers.csv", "situs_layers.csv"):
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            lid = (r.get("layer_id") or "").strip()
            st = (r.get("state") or "").strip().upper()
            if lid and st and st not in ("未定位",) and lid not in state_by:
                state_by[lid] = st
    prof = {}
    for f in glob.glob(os.path.join(PROF, "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:                                 # noqa: BLE001
            continue
        lid = d.get("layer_id")
        if lid and (lid not in prof or (d.get("sampled") or 0) > (prof[lid].get("sampled") or 0)):
            prof[lid] = d
    for lid, d in prof.items():
        d["state"] = d.get("state") or state_by.get(lid) or ""
    return fm, prof


def audit(fm: dict, prof: dict, only_no_geo: bool = True) -> list:
    out = []
    for lid, ent in fm["layers"].items():
        has = bool((ent.get("latitude") or {}).get("src")) or \
            (ent.get("latitude") or {}).get("transform") == "geometry"
        if only_no_geo and has:
            continue
        out.append(classify(lid, ent, prof))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=OUT_JSON)
    a = ap.parse_args()

    if a.selftest or not (a.audit or a.backfill):
        return selftest()

    fm, prof = load_all()
    recs = audit(fm, prof)
    cnt = {}
    for r in recs:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    fixable = [r for r in recs if r["status"] in ("salvaged", "proj_ok")]
    parcel = [r for r in recs if r["kind"] == "parcel_situs"]
    doc = {
        "schema": "coord-salvage/v1",
        "at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "field-map 里 latitude 为空的层",
        "policy": ["投影坐标必须反推 EPSG 且**唯一个**候选能把全部样例点转进本州，否则 proj_failed/proj_ambiguous",
                   "质心落在凹多边形外 → representative_point（扫描线最宽内区间中点）",
                   "空几何/退化几何 → geom_invalid",
                   "几何未落盘 → geom_missing（采集器只留点几何，Polygon rings 被丢弃）"],
        "totals": {"no_geo_layers": len(recs), "status": cnt},
        "parcel_no_geo": len(parcel),
        "fixable": {"layers": len(fixable),
                    "rows": sum(r["rows"] for r in fixable),
                    "detail": fixable},
        "geom_missing_layers": sum(1 for r in recs if r["status"] == "geom_missing"),
        "records": recs,
    }
    json.dump(doc, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"no_geo_layers": len(recs), "status": cnt,
                      "fixable_layers": len(fixable),
                      "fixable_rows": doc["fixable"]["rows"],
                      "parcel_no_geo": len(parcel)}, ensure_ascii=False))
    print("写入 %s" % a.out)
    return 0


def selftest() -> int:
    fails = []

    def ok(cond, msg):
        print(("  ✅ " if cond else "  ❌ ") + msg)
        if not cond:
            fails.append(msg)

    # L 形凹多边形：质心落在多边形外
    L = [[[0, 0], [10, 0], [10, 2], [2, 2], [2, 10], [0, 10]]]
    c = polygon_centroid(L)
    ok(c is not None, "L 形质心可算（%.2f, %.2f）" % c if c else "L 形质心 None")
    ok(not inside_geom(c[0], c[1], L), "L 形质心确实落在多边形外（凹多边形典型）")
    rp = representative_point(L)
    ok(rp is not None and inside_geom(rp[0], rp[1], L),
       "representative_point 落在内部（%.2f, %.2f）" % rp if rp else "rep point None")
    # 凸多边形：质心在内部，直接返回质心
    SQ = [[[0, 0], [4, 0], [4, 4], [0, 4]]]
    ok(representative_point(SQ) == polygon_centroid(SQ), "凸多边形直接用质心")
    # 退化几何
    ok(polygon_centroid([[[0, 0], [1, 1]]]) is None, "环 <3 点 → 退化，返回 None（geom_invalid）")
    ok(polygon_centroid([[[0, 0], [1, 0], [2, 0]]]) is None, "共线环 → 面积 0，返回 None")
    ok(representative_point([]) is None, "空几何 → None")
    # 带洞：外环 CCW + 内环 CW（ArcGIS/shapefile 的绕向约定），面积自动相减
    HOLE = [[[0, 0], [10, 0], [10, 10], [0, 10]], [[4, 4], [4, 6], [6, 6], [6, 4]]]
    c2 = polygon_centroid(HOLE)
    ok(c2 is not None and abs(c2[0] - 5) < 1e-9 and abs(c2[1] - 5) < 1e-9,
       "带洞质心按有符号面积相减（洞 4 个单位被扣掉，质心仍 (5,5)）")
    ok(not inside_geom(c2[0], c2[1], HOLE), "质心落在洞内 → inside_geom=False")
    rp2 = representative_point(HOLE)
    ok(rp2 is not None and inside_geom(rp2[0], rp2[1], HOLE), "带洞 → rep point 落在实心区")

    print()
    if fails:
        print("❌ %d 项未通过" % len(fails))
        return 1
    print("✅ 几何库自测全绿")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
