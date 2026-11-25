#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参照数据：州界 / 县名索引 / 地名索引。全部落 ref/，记来源 URL + sha256。

- 州界：TIGERweb State_County/0（maxAllowableOffset=0.002°，约 200m 简化）→ ref/tigerweb-states.geojson.gz
- 对照州界：仓内 survey/ng911/us_states.json（约 1:20m，粗）→ 只记 sha256，不复制
- 县名索引：仓内 analysis/tiger_county/<ST>.json.gz（TIGERweb 派生）→ ref/counties-index.json
- 地名索引：TIGERweb Places_CouSub_ConCity_SubMCD/4（Incorporated Places）+ /5（CDP）
           → ref/places-index.json
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref")
UA = "world-map-data-33/1.0 (+tier1-locate)"
os.makedirs(REF, exist_ok=True)

TW = "https://tigerweb.geo.census.gov/arcgis/rest/services"
STATES_Q = (TW + "/TIGERweb/State_County/MapServer/0/query?"
            + urllib.parse.urlencode({"where": "1=1", "outFields": "STATE,NAME", "returnGeometry": "true",
                                      "outSR": 4326, "geometryPrecision": 5, "maxAllowableOffset": 0.002,
                                      "resultRecordCount": 60, "f": "geojson"}))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))


def fetch_json(url: str, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(county|parish|borough|census area|municipio|city|town|village|township|cdp)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def do_states() -> dict:
    d = fetch_json(STATES_Q)
    feats = [f for f in d["features"] if f["properties"]["STATE"] not in ("60", "66", "69", "72", "78")]
    p = os.path.join(REF, "tigerweb-states.geojson.gz")
    body = json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")).encode()
    with gzip.GzipFile(p, "wb", 9) as f:
        f.write(body)
    meta = {"source_url": STATES_Q, "file": "tigerweb-states.geojson.gz",
            "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
            "n_features": len(feats), "simplify": "maxAllowableOffset=0.002 deg (~200m), outSR=4326",
            "note": "只保留 50 州 + DC（去掉 PR/VI/GU/AS/MP）"}
    print("states:", meta["n_features"], meta["sha256"][:16])
    return meta


def do_counties() -> dict:
    idx: dict = {}
    src = os.path.join(REPO, "analysis", "tiger_county")
    files = sorted(f for f in os.listdir(src) if f.endswith(".json.gz"))
    for fn in files:
        st = fn.split(".")[0]
        d = json.loads(gzip.open(os.path.join(src, fn)).read())
        for ft in d["features"]:
            p = ft["properties"]
            for key in {norm(p.get("BASENAME") or ""), norm(p.get("NAME") or "")}:
                if key:
                    idx.setdefault(key, set()).add(st)
    out = {k: sorted(v) for k, v in sorted(idx.items())}
    p = os.path.join(REF, "counties-index.json")
    json.dump(out, open(p, "w"), separators=(",", ":"), sort_keys=True)
    meta = {"source": "repo:analysis/tiger_county/*.json.gz (51 州, TIGERweb State_County/1 派生)",
            "file": "counties-index.json",
            "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
            "n_names": len(out), "n_files": len(files)}
    print("counties:", meta["n_names"], meta["sha256"][:16])
    return meta


PLACE_LAYERS = [4, 5]
FIPS2AB = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE",
    "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
    "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ", "35": "NM",
    "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}


def do_places() -> dict:
    idx: dict = {}
    got = 0
    for lid in PLACE_LAYERS:
        off = 0
        while True:
            url = (f"{TW}/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/{lid}/query?"
                   + urllib.parse.urlencode({"where": "1=1", "outFields": "NAME,STATE", "returnGeometry": "false",
                                             "resultOffset": off, "resultRecordCount": 2000, "f": "json"}))
            d = fetch_json(url, 120)
            feats = d.get("features") or []
            if not feats:
                break
            for ft in feats:
                a = ft["attributes"]
                nm = a.get("NAME") or ""
                # 去掉 " city"/" town"/" village"/" CDP"/" (balance)" 等后缀
                nm2 = re.sub(r"\s+(city|town|village|CDP|corporation|municipality|borough|urban county|"
                             r"metropolitan government|consolidated government|\(balance\))\s*$", "", nm, flags=re.I)
                nm2 = re.sub(r"\s*\(.*?\)\s*$", "", nm2).strip()
                ab = FIPS2AB.get(str(a.get("STATE", "")).zfill(2))
                if not ab:
                    continue
                for key in {norm(nm), norm(nm2)}:
                    if key:
                        idx.setdefault(key, set()).add(ab)
            got += len(feats)
            off += len(feats)
            if not d.get("exceededTransferLimit"):
                break
    out = {k: sorted(v) for k, v in sorted(idx.items())}
    p = os.path.join(REF, "places-index.json")
    json.dump(out, open(p, "w"), separators=(",", ":"), sort_keys=True)
    meta = {"source": "TIGERweb Places_CouSub_ConCity_SubMCD/4 + /5 (Incorporated Places + CDP)",
            "file": "places-index.json", "n_rows": got, "n_names": len(out),
            "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()}
    print("places:", got, meta["n_names"], meta["sha256"][:16])
    return meta


if __name__ == "__main__":
    meta = {"states": do_states(), "counties": do_counties(), "places": do_places()}
    repo_states = os.path.join(REPO, "survey", "ng911", "us_states.json")
    meta["inrepo_states"] = {"file": "repo:survey/ng911/us_states.json",
                             "sha256": hashlib.sha256(open(repo_states, "rb").read()).hexdigest(),
                             "role": "对照（约 1:20m 粗边界，海岸线外点会判 OUT）"}
    json.dump(meta, open(os.path.join(REF, "refs.meta.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(meta, indent=1, ensure_ascii=False))
