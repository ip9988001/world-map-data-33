#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二轮：未定位归位 + 逐层取样（3 条样本记录）"""
import json, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "ng911-sample/1.0"}

def get(u, tries=2, t=25):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1: return {"__error__": str(e)[:100]}
            import time; time.sleep(0.6)

def sample(r):
    u = str(r["url"]).split("?")[0]
    out = dict(r); out["samples"] = []; out["fields"] = []
    try:
        if r["svc"] == "FeatureServer":
            base = re.sub(r"/\d+$", "", u)
            api = u if re.search(r"/\d+$", u) else u + "/0"
            f = get(api + "?f=json")
            if "fields" in f:
                out["fields"] = [x["name"] for x in f["fields"]]
                q = ("%s/query?where=1%%3D1&outFields=*&returnGeometry=false"
                     "&resultRecordCount=3&f=json" % api)
                d = get(q)
                for ft in (d.get("features") or [])[:3]:
                    out["samples"].append(ft.get("attributes"))
        elif r["svc"] == "Socrata":
            m = re.search(r"https?://([^/]+)/d/([a-z0-9]{4}-[a-z0-9]{4})", u)
            if m:
                host, did = m.group(1), m.group(2)
                v = get("https://%s/api/views/%s.json" % (host, did))
                out["fields"] = [c.get("fieldName") for c in v.get("columns", [])]
                d = get("https://%s/resource/%s.json?$limit=3" % (host, did))
                if isinstance(d, list): out["samples"] = d[:3]
    except Exception as e:
        out["err"] = str(e)[:100]
    return out

if __name__ == "__main__":
    shard, n = int(sys.argv[1]), int(sys.argv[2])
    layers = json.load(open(os.path.join(HERE, "layers.json")))
    part = [x for i, x in enumerate(layers) if i % n == shard]
    print("shard %d/%d layers=%d" % (shard, n, len(part)), flush=True)
    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(sample, part))
    json.dump(res, open(os.path.join(HERE, "samp_%d.json" % shard), "w"), ensure_ascii=False)
    print("ok=%d" % sum(1 for x in res if x["samples"]), flush=True)
