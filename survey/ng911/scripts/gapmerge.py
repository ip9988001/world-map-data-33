#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 gap_*.json 合并进 layers.json，重算 清单-精简.md"""
import glob, json, os, re, collections
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def num(v):
    try: return int(float(v))
    except Exception: return 0
layers = json.load(open(os.path.join(HERE, "layers.json")))
idx = {}
for r in layers:
    idx[re.sub(r"/\d+$", "", str(r.get("url") or "")).lower()] = r
added = updated = 0
for f in glob.glob(os.path.join(HERE, "gap_*.json")):
    d = json.load(open(f))
    rows = d if isinstance(d, list) else d.get("rows", [])
    for r in rows:
        url = r.get("api_url") or r.get("url")
        if not url: continue
        k = re.sub(r"/\d+$", "", url).lower()
        if k in idx:
            t = idx[k]
            if num(r.get("count")) > 0:
                t["count"] = r["count"]; t["geom"] = r.get("geom") or t.get("geom")
                t["nfields"] = r.get("nfields") or t.get("nfields")
                if r.get("bbox"): t["bbox"] = r["bbox"]
                updated += 1
        else:
            layers.append({"state": r.get("state") or "未定位", "title": r.get("title"),
                           "provider": r.get("provider"), "url": url, "svc": r.get("svc") or "FeatureServer",
                           "geom": r.get("geom"), "count": r.get("count"), "cov": None,
                           "nfields": r.get("nfields"), "has_point": None,
                           "provider_x": None, "license": None, "fields": r.get("fields") or [],
                           "bbox": r.get("bbox")})
            idx[k] = layers[-1]; added += 1
json.dump(layers, open(os.path.join(HERE, "layers.json"), "w"), ensure_ascii=False)
print("layers=%d added=%d updated=%d" % (len(layers), added, updated))
