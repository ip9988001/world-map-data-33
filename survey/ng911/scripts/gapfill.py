#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补漏：① 无 count 重试 ② AGOL 换排序再翻页 ③ ArcGIS Server 目录探测
产出 gap_*.json，由 gapmerge.py 合并进 layers.json"""
import argparse, csv, gzip, json, os, re, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from ng911_inventory import probe_layer, probe_socrata, get_json, ext_of

UA = {"User-Agent": "Mozilla/5.0 (compatible; ng911-gapfill/1.0)"}

def get(u, t=30):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"__error__": str(e)[:110]}

def load_rows():
    return list(csv.DictReader(gzip.open(os.path.join(HERE, "clean.csv.gz"), "rt")))

# ---------- ① 无 count 重试 ----------
def task_nocount(shard, n):
    rows = [r for r in load_rows() if not str(r["count"] or "").strip()]
    if shard == 0: print("no-count rows:", len(rows), flush=True)
    part = [r for i, r in enumerate(rows) if i % n == shard]
    def one(r):
        u = r["api_url"]
        svc = r["service"]
        try:
            if svc == "Socrata" or "/d/" in u and re.search(r"/d/[a-z0-9]{4}-", u):
                p = probe_socrata(u)
            else:
                p = probe_layer(u)
        except Exception as e:
            p = {"ok": False, "err": str(e)[:100]}
        return {"state": r["state"], "title": r["title"], "provider": r["provider"],
                "api_url": r["api_url"], "count": p.get("count"), "geom": p.get("geom"),
                "nfields": p.get("nfields"), "fields": [f.get("name") for f in (p.get("fields") or [])],
                "ok": p.get("ok"), "err": p.get("err"), "bbox": p.get("bbox")}
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(one, part))
    json.dump(res, open(os.path.join(HERE, "gap_nocount_%d.json" % shard), "w"), ensure_ascii=False)
    print("shard %d: rows=%d ok=%d" % (shard, len(res), sum(1 for x in res if x.get("ok"))), flush=True)

# ---------- ② AGOL 换排序翻页 ----------
Q = ['(title:"address point" OR title:"address points")',
     '("site address" OR situshub OR "structure address")',
     '("911 address" OR E911 OR NG911)',
     '(address AND (point OR points))']
def task_agol(cap=4000):
    known = {re.sub(r"/\d+$", "", (r["api_url"] or "")).lower() for r in load_rows()}
    seen, new = set(), []
    for q in Q:
        for order in ("desc", "asc"):
            start = 1
            while start <= cap:
                u = ("https://www.arcgis.com/sharing/rest/search?f=json&num=100&start=%d"
                     "&sortField=modified&sortOrder=%s&q=%s"
                     % (start, order, urllib.parse.quote(q + ' AND type:"Feature Service"')))
                d = get(u, 40)
                if "__error__" in d or not d.get("results"): break
                for it in d["results"]:
                    url = (it.get("url") or "").lower()
                    key = re.sub(r"/\d+$", "", url)
                    if not url or key in known or key in seen: continue
                    seen.add(key)
                    new.append({"state": "未定位", "title": it.get("title"), "provider": it.get("owner"),
                                "api_url": it.get("url"), "svc": "FeatureServer", "count": None,
                                "mod": it.get("modified"), "bbox": ext_of(it)})
                if start + 100 > d.get("total", 0): break
                start += 100
    print("agol new candidates:", len(new), flush=True)
    def one(r):
        try: p = probe_layer(r["api_url"])
        except Exception as e: p = {"ok": False, "err": str(e)[:100]}
        r.update({"count": p.get("count"), "geom": p.get("geom"), "nfields": p.get("nfields"),
                  "fields": [f.get("name") for f in (p.get("fields") or [])],
                  "ok": p.get("ok"), "err": p.get("err"), "bbox": p.get("bbox") or r.get("bbox")})
        return r
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(one, new))
    json.dump(res, open(os.path.join(HERE, "gap_agol.json"), "w"), ensure_ascii=False)
    print("agol probed ok=%d" % sum(1 for x in res if x.get("ok")), flush=True)

# ---------- ③ ArcGIS Server 目录探测 ----------
def hosts_for(st):
    s = st.lower()
    return [("gis.%s.gov" % s), ("arcgis.%s.gov" % s), ("maps.%s.gov" % s),
            ("geo.%s.gov" % s), ("data.%s.gov" % s), ("opendata.%s.gov" % s),
            ("%s.maps.arcgis.com" % s), ("%s.hub.arcgis.com" % s)]
KEY = re.compile(r"address|situs|situshub|e911|911|centerline|parcel", re.I)

def task_dir(st):
    found, checked = [], []
    for host in hosts_for(st):
        base = "https://%s/arcgis/rest/services?f=json" % host
        d = get(base, 20)
        if "__error__" in d: continue
        checked.append(host)
        folders = [f["name"] for f in (d.get("folders") or [])] + [""]
        for fol in folders[:12]:
            if fol:
                dd = get("https://%s/arcgis/rest/services/%s?f=json" % (host, fol), 20)
            else:
                dd = d
            for s in (dd.get("services") or []):
                nm = s.get("name", "")
                if not KEY.search(nm): continue
                typ = s.get("type", "MapServer")
                url = "https://%s/arcgis/rest/services/%s/%s" % (host, nm, typ)
                try: p = probe_layer(url)
                except Exception as e: p = {"ok": False, "err": str(e)[:80]}
                found.append({"state": st, "title": nm.split("/")[-1], "provider": host,
                              "api_url": url, "svc": typ, "count": p.get("count"),
                              "geom": p.get("geom"), "nfields": p.get("nfields"),
                              "fields": [f.get("name") for f in (p.get("fields") or [])],
                              "ok": p.get("ok"), "err": p.get("err"), "bbox": p.get("bbox")})
    json.dump({"state": st, "checked": checked, "rows": found},
              open(os.path.join(HERE, "gap_dir_%s.json" % st), "w"), ensure_ascii=False)
    print("%s hosts=%s found=%d" % (st, checked, len(found)), flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["nocount", "agol", "dir"])
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--state")
    a = ap.parse_args()
    if a.task == "nocount": task_nocount(a.shard, a.n)
    elif a.task == "agol": task_agol()
    else: task_dir(a.state.upper())
