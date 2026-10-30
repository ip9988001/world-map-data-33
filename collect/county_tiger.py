#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIGER 县界多边形判定（**禁用 bbox**）。

背景（2026-10-30 实测）：用「点落进县的 bbox」来判县会把邻县的地址算进来 ——
GA Clayton 一案里 bbox 命中 235 条、真正落在 Clayton 多边形内的 0 条。
所以 county 一律走 point-in-polygon（射线法，纯标准库，无 shapely 依赖）。

数据来源（二选一，都不碰三仓的地址上游）：
  · 首选：一仓已发布资产 `TIGER-US-<ST>-county-<fips>.geojson`（逐县，按需取）
  · 批量：TIGERweb `State_County/MapServer/1`（州级一次拉全county，落本地缓存）
二仓 `scripts/zcta_fetch.py` 已经在用 TIGERweb，属仓库既有做法。

用法：
  python3 collect/county_tiger.py --build GA,TN,GA...
  python3 collect/county_tiger.py --selftest GA 13151 --tag collect-step04-xxx
  python3 collect/county_tiger.py --probe GA 33.6478 -84.3865
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "analysis", "tiger_county")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) world-map-data-33/intake"}
TIGERWEB = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
            "State_County/MapServer/1/query")

STATE_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08", "CT": "09",
    "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15", "ID": "16", "IL": "17",
    "IN": "18", "IA": "19", "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
    "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29", "MT": "30", "NE": "31",
    "NV": "32", "NH": "33", "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38",
    "OH": "39", "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53", "WV": "54",
    "WI": "55", "WY": "56", "PR": "72", "VI": "78", "GU": "66", "AS": "60", "MP": "69",
}


# ------------------------------------------------------------------ 几何
def _rings(geom: dict) -> list:
    if not geom:
        return []
    t = geom.get("type")
    if t == "Polygon":
        return [geom["coordinates"][0]] if geom.get("coordinates") else []
    if t == "MultiPolygon":
        return [poly[0] for poly in (geom.get("coordinates") or []) if poly]
    return []


def _in_ring(lon: float, lat: float, ring: list) -> bool:
    """射线法：点在环内返回 True。"""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-18) + xi):
            inside = not inside
        j = i
    return inside


def pip(lat: float, lon: float, geom: dict) -> bool:
    for ring in _rings(geom):
        if _in_ring(lon, lat, ring):
            return True
    return False


def bbox_of(geom: dict) -> tuple:
    xs, ys = [], []
    for ring in _rings(geom):
        for pt in ring:
            xs.append(pt[0])
            ys.append(pt[1])
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


def in_bbox(lat: float, lon: float, bb: tuple) -> bool:
    return bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3]


# ------------------------------------------------------------------ 索引
class CountyIndex:
    """一个州的县索引：name→fips、fips→{name,bbox,geom}。"""

    def __init__(self, state: str, feats: list):
        self.state = state.upper()
        self.by_fips: dict[str, dict] = {}
        self.by_name: dict[str, str] = {}
        for f in feats:
            p = f.get("properties") or {}
            fips = str(p.get("GEOID") or (p.get("STATE", "") + p.get("COUNTY", "")))
            fips = "".join(ch for ch in fips if ch.isdigit())
            if len(fips) == 4:            # 有的层给 STATE+COUNTY 拼 4 位
                fips = "0" + fips
            if len(fips) != 5:
                continue
            name = (p.get("BASENAME") or p.get("NAME") or "").strip()
            geom = f.get("geometry") or {}
            self.by_fips[fips] = {"fips": fips, "name": name,
                                  "bbox": bbox_of(geom), "geom": geom}
            self.by_name[_key(name)] = fips

    def __len__(self) -> int:
        return len(self.by_fips)

    def by_name_get(self, name: str) -> str | None:
        return self.by_name.get(_key(name))

    def locate(self, lat: float, lon: float) -> str | None:
        """多边形判定；bbox 只用来快速跳过，命中必须过 PIP。"""
        for fips, e in self.by_fips.items():
            if not in_bbox(lat, lon, e["bbox"]):
                continue
            if pip(lat, lon, e["geom"]):
                return fips
        return None

    def bbox_hits(self, lat: float, lon: float) -> list[str]:
        """**只**返回 bbox 命中（用来量化 bbox 的误判，不得用于生产判定）。"""
        return [fips for fips, e in self.by_fips.items() if in_bbox(lat, lon, e["bbox"])]


def _key(name: str) -> str:
    return "".join(ch for ch in str(name).upper() if ch.isalnum())


# ------------------------------------------------------------------ 取数
def fetch_state(state: str, force: bool = False) -> CountyIndex:
    st = state.upper()
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "%s.json.gz" % st)
    if os.path.exists(p) and not force:
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            return CountyIndex(st, json.load(fh)["features"])
    fips2 = STATE_FIPS.get(st)
    if not fips2:
        raise SystemExit("未知州码 %r" % st)
    q = {"where": "STATE='%s'" % fips2, "outFields": "GEOID,NAME,BASENAME,STATE",
         "returnGeometry": "true", "outSR": "4326", "f": "geojson",
         "maxAllowableOffset": "0.0005"}
    url = TIGERWEB + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        doc = json.loads(r.read().decode("utf-8"))
    feats = doc.get("features") or []
    if not feats:
        raise SystemExit("TIGERweb 没返回县界：%s（%s）" % (st, str(doc)[:200]))
    with gzip.open(p, "wt", encoding="utf-8") as fh:
        json.dump({"state": st, "source": "TIGERweb State_County/1",
                   "fetched_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "features": feats}, fh)
    return CountyIndex(st, feats)


def county_from_text(text: str, idx: CountyIndex) -> tuple[str, str] | None:
    """从层 id / url / 标题里抠县名 → (name, fips)。抠不到返回 None。"""
    import re
    t = urllib.parse.unquote(str(text))
    cands = re.findall(r"([A-Za-z][A-Za-z' .]{2,28}?)_?county", t, re.I)
    for c in reversed(cands):
        nm = c.strip().lower().replace("_", " ")
        if not nm:
            continue
        fips = idx.by_name_get(nm)
        if fips:
            return idx.by_fips[fips]["name"], fips
    return None


# ------------------------------------------------------------------ CLI
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="逗号分隔州码，拉 TIGERweb 县界到 analysis/tiger_county/")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--selftest", help="州码：跑 bbox vs 多边形对照")
    ap.add_argument("--county", default="", help="selftest 用：县 FIPS（如 13151）")
    ap.add_argument("--tag", default="", help="selftest 用：三仓 Release tag（取真实点做对照）")
    ap.add_argument("--probe", nargs=3, metavar=("ST", "LAT", "LON"))
    a = ap.parse_args()

    if a.build:
        for st in [x.strip().upper() for x in a.build.split(",") if x.strip()]:
            idx = fetch_state(st, a.force)
            print("%s: %d 县" % (st, len(idx)))
        return 0

    if a.probe:
        st, lat, lon = a.probe[0].upper(), float(a.probe[1]), float(a.probe[2])
        idx = fetch_state(st)
        print("PIP:", idx.locate(lat, lon), " bbox 命中:", idx.bbox_hits(lat, lon))
        return 0

    if a.selftest:
        st = a.selftest.upper()
        idx = fetch_state(st)
        print("%s: %d 县，bbox vs 多边形对照" % (st, len(idx)))
        # 1) 几何自证：县自身顶点有多少会落进别的县的 bbox（bbox 必然误判）
        wrong_bbox = 0
        verts = 0
        for fips, e in idx.by_fips.items():
            for ring in _rings(e["geom"]):
                for pt in ring[:400]:
                    verts += 1
                    lon, lat = pt[0], pt[1]
                    if not pip(lat, lon, e["geom"]):
                        continue
                    for other, oe in idx.by_fips.items():
                        if other != fips and in_bbox(lat, lon, oe["bbox"]):
                            wrong_bbox += 1
                            break
        ev = {"state": st, "counties": len(idx), "vertices": verts,
              "bbox_ambiguous_vertices": wrong_bbox,
              "bbox_ambiguous_pct": round(100.0 * wrong_bbox / max(1, verts), 2)}
        print("  顶点 %d 个：多边形判定=本县；其中 %d 个同时落进**别的县**的 bbox（bbox 会误判 %.1f%%）"
              % (verts, wrong_bbox, 100.0 * wrong_bbox / max(1, verts)))
        # 2) 真实地址点对照（可选）
        if a.tag:
            sys.path.insert(0, os.path.join(ROOT, "analysis"))
            from profile import gh_dl, partial_targz_rows  # noqa: E402
            import subprocess
            import tempfile
            n_bbox = n_pip = n = amb = unresolved = 0
            with tempfile.TemporaryDirectory() as td:
                raw = json.loads(subprocess.run(
                    ["gh", "release", "view", a.tag, "--repo", "ip9988001/world-map-data-33",
                     "--json", "assets", "-q", '[.assets[]|select(.name|endswith("tar.gz"))|{n:.name,u:.url}]'],
                    capture_output=True, text=True, timeout=300).stdout or "[]")
                if raw:
                    for ln in partial_targz_rows(sorted(raw, key=lambda x: x["n"])[0]["u"], 3 << 20, 2000):
                        try:
                            rec = json.loads(ln)
                        except Exception:  # noqa: BLE001
                            continue
                        lat, lon = rec.get("lat"), rec.get("lon")
                        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                            continue
                        n += 1
                        hits = idx.bbox_hits(lat, lon)
                        if len(hits) > 1:
                            amb += 1
                        if idx.locate(lat, lon) is None:
                            unresolved += 1
                        target = a.county
                        if target and target in hits:
                            n_bbox += 1
                            if pip(lat, lon, idx.by_fips[target]["geom"]):
                                n_pip += 1
            ev.update({"tag": a.tag, "sampled": n, "bbox_ambiguous_points": amb,
                       "pip_unresolved": unresolved,
                       "bbox_ambiguous_pct_points": round(100.0 * amb / max(1, n), 2)})
            if a.county:
                print("  %s 抽样 %d 点：bbox 判进 %s = %d 条；多边形真的在 %s 内 = %d 条"
                      % (a.tag, n, a.county, n_bbox, a.county, n_pip))
            print("  %s 抽样 %d 点：bbox 歧义（≥2 县）= %d 条（%.1f%%）；多边形判不出县 = %d 条"
                  % (a.tag, n, amb, 100.0 * amb / max(1, n), unresolved))
        os.makedirs(CACHE, exist_ok=True)
        with open(os.path.join(CACHE, "selftest.json"), "w", encoding="utf-8") as fh:
            json.dump(ev, fh, ensure_ascii=False, indent=1)
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
