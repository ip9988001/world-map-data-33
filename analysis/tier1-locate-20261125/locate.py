#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tier1 未定位 85 层 · 三路证据抓取（E1 元数据 / E2 属性样本 / E3 几何）。

只读外部服务，不写任何引擎产物；原始响应全部落 ref/agol/ 便于复核。

用法:
  python3 locate.py e1          # 服务/条目元数据
  python3 locate.py e2          # 属性样本
  python3 locate.py e3          # 几何（bbox + 1000 行采样）
  python3 locate.py e3ref       # 拉 Census 州界参照（500k）
  python3 locate.py all
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref", "agol")
IN = os.path.join(HERE, "tier1-unlocated.csv")
UA = "world-map-data-33/1.0 (+tier1-locate; contact: ops)"
TIMEOUT = 45
RETRY = 3

os.makedirs(REF, exist_ok=True)


def slug(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def fetch(url: str, cache_path: str, force: bool = False) -> dict:
    """GET json with disk cache. Returns {"_http":..,"_url":..,"_err":.., ...payload}."""
    if os.path.exists(cache_path) and not force:
        try:
            return json.load(open(cache_path, encoding="utf-8"))
        except Exception:
            pass
    last = None
    for attempt in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                code = r.status
            try:
                payload = json.loads(raw.decode("utf-8", "replace"))
                if not isinstance(payload, dict):
                    payload = {"_payload": payload}
            except Exception:
                payload = {"_raw_head": raw[:400].decode("utf-8", "replace")}
            out = {"_http": code, "_url": url, **payload}
            json.dump(out, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
            return out
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            body = ""
            try:
                body = e.read()[:300].decode("utf-8", "replace")
            except Exception:
                pass
            if e.code in (400, 403, 404, 498, 499):
                out = {"_http": e.code, "_url": url, "_err": last, "_body": body}
                json.dump(out, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
                return out
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (attempt + 1))
    out = {"_http": None, "_url": url, "_err": last or "failed"}
    json.dump(out, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def rows():
    return list(csv.DictReader(open(IN, newline="", encoding="utf-8")))


# ---------------------------------------------------------------- E1
STATE_NAMES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
]
ABBR = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}
# 易与普通词混淆的缩写：只有在 "…, XX" / "XX 12345" / "XX;" 这类地址形态里才算数
RISKY = {"IN", "OR", "ME", "OK", "DE", "HI", "LA", "MS", "AL", "AR", "CA", "CO", "ID", "MA", "MD", "PA"}

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

TEXT_FIELDS = ["name", "description", "snippet", "title", "tags", "copyrightText", "accessInformation",
               "credits", "owner", "fullName", "orgId", "serviceDescription"]


def texts_of(obj: dict) -> list:
    out = []
    for k in TEXT_FIELDS:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            out.append((k, v.strip()))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    out.append((k, item.strip()))
    return out


def e1_scan(blob: list) -> dict:
    """blob = [(source, text)] -> 命中片段（原文、≤200 字符）+ 州候选 + 机构/县市线索。"""
    hits, states, orgs = [], set(), []
    for src, t in blob:
        low = t.lower()
        for nm in STATE_NAMES:
            for m in re.finditer(re.escape(nm), t, flags=re.I):
                s = t[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")
                hits.append(f"[{src}] …{s[:200]}…")
                states.add(NAME2AB[nm])
                break
        # 独立大写两字母
        for m in re.finditer(r"(?<![A-Za-z])([A-Z]{2})(?![A-Za-z])", t):
            a = m.group(1)
            if a in ABBR:
                ctx = t[max(0, m.start() - 40): m.end() + 40]
                hits.append(f"[{src}] …{ctx[:200]}…")
                states.add(a)
        # *.xx.us 域名（州缩写出现在域名里最可信）
        for m in re.finditer(r"\.([a-z]{2})\.us\b", low):
            a = m.group(1).upper()
            if a in ABBR:
                hits.append(f"[{src}] domain .{a.lower()}.us")
                states.add(a)
        # 机构/县市关键词
        for m in re.finditer(r"([A-Z][A-Za-z' .]{2,40}?)\s+(County|Parish|Borough|Township|City of|Town of)\b", t):
            orgs.append(f"{m.group(1).strip()} {m.group(2)}")
        for m in re.finditer(r"\b(City|Town|Village|Township|Borough) of ([A-Z][A-Za-z' .-]{2,40})", t):
            orgs.append(f"{m.group(1)} of {m.group(2).strip()}")
    return {"states": sorted(states), "hits": hits, "orgs": orgs}


def do_e1() -> None:
    rs = rows()

    def one(r):
        url = r["url"]
        s = slug(url)
        layer = fetch(url + "?f=json", os.path.join(REF, f"{s}_layer.json"))
        svc_url, lid = url.rsplit("/", 1)
        svc = fetch(svc_url + "?f=json", os.path.join(REF, f"{s}_service.json"))
        item, user = {}, {}
        sid = layer.get("serviceItemId") or svc.get("serviceItemId")
        if sid:
            item = fetch(f"https://www.arcgis.com/sharing/rest/content/items/{sid}?f=json",
                         os.path.join(REF, f"item_{sid}.json"))
            owner = item.get("owner")
            if owner:
                user = fetch(f"https://www.arcgis.com/sharing/rest/community/users/{urllib.parse.quote(owner)}?f=json",
                             os.path.join(REF, f"user_{owner}.json"))
        blob = []
        for label, obj in (("layer", layer), ("service", svc), ("item", item), ("user", user)):
            for k, v in texts_of(obj):
                blob.append((f"{label}.{k}", v))
        # 层名/服务名/路径也进 E1 文本池（路径是元数据的一部分，不是 E4）
        blob.append(("url.path", url))
        sc = e1_scan(blob)
        rec = {
            "url": url, "slug": s, "layer_id": r["layer_id"],
            "http_layer": layer.get("_http"), "err_layer": layer.get("_err"),
            "layer_name": layer.get("name"), "serviceItemId": sid,
            "item_title": item.get("title"), "item_owner": item.get("owner"),
            "item_type": item.get("type"),
            "user_fullName": user.get("fullName"), "user_region": user.get("region"),
            "user_description": (user.get("description") or "")[:400],
            "extent": layer.get("extent") or svc.get("fullExtent") or {},
            "e1_states": sc["states"], "e1_hits": sc["hits"][:12], "e1_orgs": sorted(set(sc["orgs"]))[:12],
            "fields": [f.get("name") for f in (layer.get("fields") or [])],
            "geometryType": layer.get("geometryType"),
            "maxRecordCount": layer.get("maxRecordCount"),
        }
        json.dump(rec, open(os.path.join(HERE, "_work", f"e1_{s}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return rec

    os.makedirs(os.path.join(HERE, "_work"), exist_ok=True)
    out = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, rec in enumerate(ex.map(one, rs), 1):
            out.append(rec)
            print(i, rec["e1_states"], rec["layer_name"], "|", rec["item_owner"], flush=True)
    json.dump(out, open(os.path.join(HERE, "_work", "e1_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("E1 done:", len(out), "errors:", sum(1 for x in out if x.get("err_layer")))


# ---------------------------------------------------------------- E2
STATE_FIELD_RE = re.compile(r"^(state|st|statefp|state_?code|state_?abbr|st_?abbr|state_?name|st_?name)$", re.I)
COUNTY_FIELD_RE = re.compile(r"county|parish|borough", re.I)
CITY_FIELD_RE = re.compile(r"^(city|town|place|municipality|postal_?city|city_?name|cityname)$", re.I)
ZIP_FIELD_RE = re.compile(r"zip", re.I)


def pick_fields(fields: list) -> dict:
    st = [f for f in fields if STATE_FIELD_RE.match(f or "")]
    ct = [f for f in fields if COUNTY_FIELD_RE.search(f or "")]
    ci = [f for f in fields if CITY_FIELD_RE.match(f or "")]
    zp = [f for f in fields if ZIP_FIELD_RE.search(f or "")]
    return {"state": st, "county": ct, "city": ci, "zip": zp}


def q(url: str, **params) -> str:
    params.setdefault("f", "json")
    return url + "/query?" + urllib.parse.urlencode(params)


def do_e2() -> None:
    rs = rows()
    e1 = {x["slug"]: x for x in json.load(open(os.path.join(HERE, "_work", "e1_all.json"), encoding="utf-8"))}

    def one(r):
        url = r["url"]
        s = slug(url)
        fields = (e1.get(s) or {}).get("fields") or []
        pf = pick_fields(fields)
        out = {"url": url, "slug": s, "picked": pf, "distinct": {}, "sample_vals": {}}
        # 1) 5 条全字段样本
        sample = fetch(q(url, where="1=1", outFields="*", resultRecordCount=5, returnGeometry="false"),
                       os.path.join(REF, f"{s}_sample.json"))
        feats = sample.get("features") or []
        out["http_sample"] = sample.get("_http")
        out["err_sample"] = sample.get("_err") or (sample.get("error") or {}).get("message")
        out["sample_attrs"] = [f.get("attributes", {}) for f in feats[:5]]
        # 2) state / county / city 字段 distinct
        for kind in ("state", "county", "city"):
            for f in pf[kind][:2]:
                d = fetch(q(url, where="1=1", outFields=f, returnDistinctValues="true",
                            returnGeometry="false", resultRecordCount=200),
                          os.path.join(REF, f"{s}_distinct_{kind}_{f}.json"))
                vals = [str(x.get("attributes", {}).get(f)) for x in (d.get("features") or [])]
                out["distinct"][f"{kind}:{f}"] = vals[:60]
                out.setdefault("http_distinct", {})[f"{kind}:{f}"] = d.get("_http")
        # 3) zip 前缀（弱证据，只记录不投票）
        for f in pf["zip"][:1]:
            d = fetch(q(url, where="1=1", outFields=f, returnDistinctValues="true",
                        returnGeometry="false", resultRecordCount=200),
                      os.path.join(REF, f"{s}_distinct_zip_{f}.json"))
            vals = [str(x.get("attributes", {}).get(f)) for x in (d.get("features") or [])]
            out["distinct"][f"zip:{f}"] = vals[:60]
        json.dump(out, open(os.path.join(HERE, "_work", f"e2_{s}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return out

    out = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        for i, rec in enumerate(ex.map(one, rs), 1):
            out.append(rec)
            nonempty = {k: v for k, v in rec["distinct"].items() if v}
            print(i, rec["url"].split("/services/")[-1][:50], nonempty or "-", flush=True)
    json.dump(out, open(os.path.join(HERE, "_work", "e2_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("E2 done:", len(out))


# ---------------------------------------------------------------- E3
def load_states(path: str) -> dict:
    d = json.load(open(path, encoding="utf-8"))
    out = {}
    for ft in d["features"]:
        nm = (ft.get("properties") or {}).get("name") or (ft.get("properties") or {}).get("NAME")
        g = ft["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out[NAME2AB.get(nm, nm)] = [[(float(p[0]), float(p[1])) for p in ring] for poly in polys for ring in poly]
    return out


def first_point(geom: dict):
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "Point":
        return c
    if t == "MultiPoint" and c:
        return c[0]
    if t == "LineString" and c:
        return c[len(c) // 2]
    if t == "MultiLineString" and c:
        return c[0][len(c[0]) // 2]
    if t == "Polygon" and c and c[0]:
        ring = c[0]
        # 顶点均值（面质心近似；外部面重心命中率足够做州级计票）
        xs = [p[0] for p in ring[:-1]] or [ring[0][0]]
        ys = [p[1] for p in ring[:-1]] or [ring[0][1]]
        return [sum(xs) / len(xs), sum(ys) / len(ys)]
    if t == "MultiPolygon" and c and c[0] and c[0][0]:
        return first_point({"type": "Polygon", "coordinates": c[0]})
    return None


def do_e3() -> None:
    rs = rows()
    BU = load_states(os.path.join(HERE, "..", "..", "survey", "ng911", "us_states.json"))

    def pip(x, y, ring):
        ins = False
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi):
                ins = not ins
            j = i
        return ins

    def which(x, y):
        if not (-180 <= x <= -60 and 15 <= y <= 75):
            return ""
        for st, rings in BU.items():
            for rg in rings:
                if pip(x, y, rg):
                    return st
        return ""

    def one(r):
        url = r["url"]
        s = slug(url)
        out = {"url": url, "slug": s, "bbox4326": None, "n_sampled": 0, "counts": {}, "err": None}
        ext = fetch(q(url, where="1=1", returnExtentOnly="true", outSR=4326),
                    os.path.join(REF, f"{s}_extent4326.json"))
        e = ext.get("extent") or {}
        if {"xmin", "ymin", "xmax", "ymax"} <= set(e):
            out["bbox4326"] = [e["xmin"], e["ymin"], e["xmax"], e["ymax"]]
        else:
            out["err"] = ext.get("err") or (ext.get("error") or {}).get("message") or "no extent"
        gj = fetch(q(url, where="1=1", outFields="*", resultRecordCount=1000, outSR=4326,
                     returnGeometry="true", f="geojson", geometryPrecision=6),
                   os.path.join(REF, f"{s}_geom1000.json"))
        cnt = Counter()
        n = 0
        for ft in (gj.get("features") or []):
            g = ft.get("geometry") or {}
            p = first_point(g)
            if not p:
                continue
            n += 1
            cnt[which(p[0], p[1]) or "OUT"] += 1
        out["n_sampled"] = n
        out["counts"] = dict(cnt)
        if n == 0 and not out["err"]:
            out["err"] = gj.get("err") or (gj.get("error") or {}).get("message") or "no geometry in sample"
        json.dump(out, open(os.path.join(HERE, "_work", f"e3_{s}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return out

    out = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        for i, rec in enumerate(ex.map(one, rs), 1):
            out.append(rec)
            top = sorted(rec["counts"].items(), key=lambda kv: -kv[1])[:3]
            print(i, rec["n_sampled"], top, "err=", rec["err"], flush=True)
    json.dump(out, open(os.path.join(HERE, "_work", "e3_all.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("E3 done:", len(out))


# ---------------------------------------------------------------- E3 ref (Census)
CENSUS_URL = "https://www2.census.gov/geo/tiger/GENZ2024/geojson/cb_2024_us_state_500k.zip"


def do_e3ref() -> None:
    import zipfile
    d = os.path.join(HERE, "ref")
    os.makedirs(d, exist_ok=True)
    zp = os.path.join(d, "cb_2024_us_state_500k.zip")
    if not os.path.exists(zp):
        req = urllib.request.Request(CENSUS_URL, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r, open(zp, "wb") as f:
            f.write(r.read())
    h = hashlib.sha256(open(zp, "rb").read()).hexdigest()
    with zipfile.ZipFile(zp) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".geojson")][0]
        raw = z.read(name)
    gj = json.loads(raw)
    keep = []
    for ft in gj["features"]:
        p = ft["properties"]
        if p.get("STATEFP") in {f"{i:02d}" for i in range(1, 57)}:
            keep.append({"type": "Feature", "properties": {"abbr": p.get("STUSPS"), "name": p.get("NAME"),
                                                           "geoid": p.get("STATEFP")},
                         "geometry": ft["geometry"]})
    outp = os.path.join(d, "cb_2024_us_state_500k.geojson")
    json.dump({"type": "FeatureCollection", "source": CENSUS_URL, "zip_sha256": h, "features": keep},
              open(outp, "w", encoding="utf-8"))
    oh = hashlib.sha256(open(outp, "rb").read()).hexdigest()
    meta = {"source_url": CENSUS_URL, "zip_sha256": h, "geojson": "cb_2024_us_state_500k.geojson",
            "geojson_sha256": oh, "n_features": len(keep), "tier": "500k (1:500,000)"}
    json.dump(meta, open(os.path.join(d, "census-state-500k.meta.json"), "w"), indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("e1", "all"):
        do_e1()
    if what in ("e2", "all"):
        do_e2()
    if what in ("e3ref", "all"):
        do_e3ref()
    if what in ("e3", "all"):
        do_e3()
