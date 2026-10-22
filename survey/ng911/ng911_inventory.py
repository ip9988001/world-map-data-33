#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NG911 / 州级地址数据 —— 全量摸排器（单州模式）
输出 out/<ABBR>.json：一条记录 = 一个数据集/图层，不筛选、不截断。

用法: python3 ng911_inventory.py --state AL [--max-probe 120]
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
UA = {"User-Agent": "ng911-inventory/2.0 (research)"}
GEO = json.load(open(os.path.join(HERE, "us_states.json")))

ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO",
"Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI",
"Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
"Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
"Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ",
"New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
"Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD",
"Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
"West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY","Puerto Rico":"PR"}
NAME = {v: k for k, v in ABBR.items()}
# 州级门户候选域名（自动探测平台类型）
HOSTS = {
 "AL":["data.alabama.gov"],"AK":["data.alaska.gov","gis.alaska.gov"],"AZ":["data.az.gov","geo.az.gov"],
 "AR":["data.arkansas.gov"],"CA":["data.ca.gov","gis.data.ca.gov"],"CO":["data.colorado.gov"],
 "CT":["data.ct.gov"],"DE":["data.delaware.gov","firstmap.delaware.gov"],"DC":["opendata.dc.gov"],
 "FL":["data.florida.gov","geodata.floridagio.gov"],"GA":["data.georgia.gov"],"HI":["data.hawaii.gov"],
 "ID":["data.idaho.gov","gis.idaho.gov"],"IL":["data.illinois.gov"],"IN":["data.in.gov","gisdata.in.gov"],
 "IA":["data.iowa.gov"],"KS":["data.ks.gov"],"KY":["data.kentucky.gov"],"LA":["data.la.gov"],
 "ME":["data.maine.gov","maine.hub.arcgis.com"],"MD":["data.maryland.gov","imap.maryland.gov"],
 "MA":["data.mass.gov","gis.mass.gov"],"MI":["data.michigan.gov"],"MN":["data.mn.gov","gisdata.mn.gov"],
 "MS":["data.ms.gov","gis.ms.gov"],"MO":["data.mo.gov"],"MT":["data.mt.gov","msl.mt.gov"],
 "NE":["data.ne.gov","datacenter.nebraska.gov"],"NV":["data.nv.gov"],"NH":["data.nh.gov","granit.unh.edu"],
 "NJ":["data.nj.gov"],"NM":["data.nm.gov"],"NY":["data.ny.gov"],"NC":["data.nc.gov","nconemap.gov"],
 "ND":["data.nd.gov","gishub.nd.gov"],"OH":["data.ohio.gov","gis.ohio.gov"],"OK":["data.ok.gov"],
 "OR":["data.oregon.gov","geo.oregon.gov"],"PA":["data.pa.gov","pasda.psu.edu"],"RI":["data.ri.gov"],
 "SC":["data.sc.gov","gis.sc.gov"],"SD":["data.sd.gov","gis.sd.gov"],"TN":["data.tn.gov"],
 "TX":["data.texas.gov","data.tx.gov"],"UT":["data.utah.gov","gis.utah.gov"],"VT":["data.vermont.gov"],
 "VA":["data.virginia.gov","vgin.virginia.gov"],"WA":["data.wa.gov"],"WV":["data.wv.gov","map.wv.gov"],
 "WI":["data.wisconsin.gov"],"WY":["data.wy.gov","wyominghub.wygisc.org"],"PR":["data.pr.gov"],
}
Q_AGOL = [
 '(title:"address point" OR title:"address points")',
 '("site address" OR situshub OR "structure address")',
 '("911 address" OR E911 OR NG911 OR "next generation 911")',
 '(address AND (point OR points))',
 '("address range" OR "road centerline" OR centerline)',
 '("parcel" AND address)',
]


import math
def norm_bbox(bb):
    """把 Web Mercator 的 extent 反算成经纬度；已经是经纬度的原样返回"""
    if not bb: return None
    try:
        x1, y1, x2, y2 = [float(v) for v in bb]
    except Exception:
        return None
    if abs(x1) <= 180 and abs(y1) <= 90 and abs(x2) <= 180 and abs(y2) <= 90:
        return [x1, y1, x2, y2]
    R = 6378137.0
    def lon(x): return x / R * 180.0 / math.pi
    def lat(y): return (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * 180.0 / math.pi
    try:
        return [lon(x1), lat(y1), lon(x2), lat(y2)]
    except Exception:
        return None

def get_json(url, tries=2, timeout=25):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)[:120]}
            time.sleep(0.6)

def state_bbox(ab):
    for f in GEO["features"]:
        if ABBR.get(f["properties"]["name"]) == ab:
            xs, ys = [], []
            def walk(c):
                if isinstance(c[0], (int, float)): xs.append(c[0]); ys.append(c[1])
                else:
                    for i in c: walk(i)
            walk(f["geometry"]["coordinates"])
            return min(xs), min(ys), max(xs), max(ys)
    return None

def in_state(bbox, sb):
    if not bbox: return False
    x1, y1, x2, y2 = bbox; a1, b1, a2, b2 = sb
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return a1 <= cx <= a2 and b1 <= cy <= b2

def ext_of(it):
    e = it.get("extent")
    try:
        if isinstance(e, dict):
            (x1, y1), (x2, y2) = e["coordinates"][0], e["coordinates"][1]
        else:
            (x1, y1), (x2, y2) = e[0], e[1]
        if abs(x1) > 180 or abs(y1) > 90 or x2 <= x1: return None
        return norm_bbox([x1, y1, x2, y2])
    except Exception:
        return None

# ---------------- 渠道：ArcGIS Online ----------------
def ch_agol(ab, sb):
    bbox = "%f,%f,%f,%f" % sb
    out = []
    for q in Q_AGOL:
        start = 1
        while start <= 300:
            u = ("https://www.arcgis.com/sharing/rest/search?f=json&num=100&start=%d&bbox=%s&q=%s"
                 % (start, bbox, urllib.parse.quote(q + ' AND type:"Feature Service" AND access:public')))
            d = get_json(u)
            if "__error__" in d or not d.get("results"): break
            for it in d["results"]:
                out.append({"ch":"agol","id":it.get("id"),"title":it.get("title") or "",
                            "owner":it.get("owner"),"url":it.get("url"),"modified":it.get("modified"),
                            "snippet":(it.get("snippet") or "")[:200],"bbox":ext_of(it),
                            "tags":it.get("tags") or []})
            if start + 100 > d.get("total", 0): break
            start += 100
            time.sleep(0.15)
    return out

# ---------------- 渠道：ArcGIS Hub ----------------
def ch_hub(ab):
    out = []
    for q in ["address points", "911 address", "site addresses", "NG911"]:
        for page in (1, 2):
            u = ("https://hub.arcgis.com/api/v3/datasets?page[size]=100&page[number]=%d&q=%s"
                 % (page, urllib.parse.quote(q + " " + ab)))
            d = get_json(u)
            if "__error__" in d or not d.get("data"): break
            for it in d["data"]:
                a = it.get("attributes", {})
                out.append({"ch":"hub","id":a.get("id"),"title":a.get("name") or "",
                            "owner":a.get("source") or "","url":a.get("url"),
                            "modified":a.get("modified"),"count":a.get("recordCount"),
                            "bbox":ext_of(a),"license":(a.get("license") or ""),
                            "snippet":""})
            if len(d["data"]) < 100: break
    return out

# ---------------- 渠道：州门户（自动识别平台） ----------------
def detect_platform(host):
    for plat, probe in (
        ("socrata", "https://%s/api/catalog/v1?limit=1&q=address"),
        ("socrata", "https://%s/api/views.json?limit=1"),
        ("ckan", "https://%s/api/3/action/package_search?rows=1&q=address"),
        ("hub", "https://%s/api/v3/datasets?page[size]=1&q=address"),
    ):
        d = get_json(probe % host, tries=1, timeout=15)
        if isinstance(d, dict) and "__error__" not in d:
            if plat == "socrata" and (isinstance(d, list) or d.get("results") is not None): return plat
            if plat == "ckan" and d.get("success"): return plat
            if plat == "hub" and d.get("data") is not None: return plat
    return None

def ch_portal(ab):
    recs, meta = [], []
    for host in HOSTS.get(ab, []):
        plat = detect_platform(host)
        meta.append({"host": host, "platform": plat})
        if plat == "socrata":
            for q in ("address", "911", "e911", "situs", "site address"):
                for off in (0, 100):
                    u = ("https://%s/api/catalog/v1?q=%s&limit=100&offset=%d&only=datasets"
                         % (host, urllib.parse.quote(q), off))
                    d = get_json(u)
                    if "__error__" in d or not d.get("results"): break
                    for it in d["results"]:
                        r, m = it.get("resource", {}), it.get("metadata", {})
                        recs.append({"ch":"socrata","id":r.get("id"),"title":r.get("name") or "",
                                     "owner":m.get("domain") or host,
                                     "url":"https://%s/d/%s" % (host, r.get("id")),
                                     "modified":r.get("updatedAt"),"bbox":None,"snippet":"",
                                     "license":(m.get("license") or "")})
        elif plat == "ckan":
            for q in ("address point", "911 address", "site address"):
                u = ("https://%s/api/3/action/package_search?rows=100&q=%s" % (host, urllib.parse.quote(q)))
                d = get_json(u)
                if "__error__" in d or not d.get("result"): continue
                for p in d["result"].get("results", []):
                    for res in p.get("resources", []):
                        recs.append({"ch":"ckan","id":res.get("id"),"title":p.get("title") or "",
                                     "owner":p.get("organization",{}).get("title") if isinstance(p.get("organization"),dict) else host,
                                     "url":res.get("url"),"modified":res.get("last_modified"),
                                     "bbox":None,"snippet":(res.get("format") or ""),
                                     "license":p.get("license_title") or ""})
        elif plat == "hub":
            for q in ("address points", "911 address"):
                u = ("https://%s/api/v3/datasets?page[size]=100&q=%s" % (host, urllib.parse.quote(q)))
                d = get_json(u)
                if "__error__" in d or not d.get("data"): continue
                for it in d["data"]:
                    a = it.get("attributes", {})
                    recs.append({"ch":"hub","id":a.get("id"),"title":a.get("name") or "",
                                 "owner":a.get("source") or host,"url":a.get("url"),
                                 "modified":a.get("modified"),"count":a.get("recordCount"),
                                 "bbox":ext_of(a),"snippet":"","license":a.get("license") or ""})
    return recs, meta

# ---------------- 探针 ----------------
F_POINT = ("ADD_NUM","ADDRNUM","ADDRESS_NUMBER","FULLADDR","FULL_ADDR","HOUSE_NUM","HOUSENUM",
           "STREET_NUM","SITUS","ADDR_NUM","MAILING_ADDR","ADDRESS")
F_RANGE = ("HASLOW","HASHIGH","LFROM","LTO","LOW","HIGH","ODD_EVEN","FROMADDR","TOADDR")
F_UNIT  = ("SUBNUM","UNIT","SUITE","APT","UNITID","SUB_ADDR","UNIT_NUM","BLDG")
F_ESN   = ("ESN","ESN_ID","ESNID","ESN_LEFT","ESN_RIGHT")
F_ZIP   = ("ZIP","ZIPCODE","ZIP_CODE","POSTAL_CODE","ZIP5")
F_COMM  = ("CITY","COMMUNITY","MUNICIPALITY","POST_CITY","CITYNAME","TOWN","PLACE")

def probe_layer(url):
    url = (url or "").split("?")[0].rstrip("/")
    if not url: return {"ok": False, "err": "no url"}
    base = url
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", base)
    if m:
        base = base[:m.start()] + "/" + m.group(1)
    root = get_json(base + "?f=json", timeout=20)
    if "__error__" in root:
        return {"ok": False, "err": root["__error__"]}
    layers = root.get("layers") or []
    pick = None
    for L in layers:
        if re.search(r"address|situshub|structure|911|site", L.get("name", ""), re.I):
            pick = L; break
    if pick is None and layers: pick = layers[0]
    if not pick: return {"ok": False, "err": "no layers"}
    lj = get_json("%s/%d?f=json" % (base, pick["id"]), timeout=20)
    if "fields" not in lj:
        return {"ok": False, "err": "no fields", "base": base}
    fields = [{"name": f["name"], "type": f.get("type")} for f in lj["fields"]]
    up = [f["name"].upper() for f in fields]
    cnt = get_json("%s/%d/query?where=1%%3D1&returnCountOnly=true&f=json" % (base, pick["id"]), timeout=30)
    ext = lj.get("extent")
    bb = None
    try:
        bb = norm_bbox([ext["xmin"], ext["ymin"], ext["xmax"], ext["ymax"]])
    except Exception:
        pass
    return {"ok": True, "api": "%s/%d" % (base, pick["id"]), "layer": pick.get("name"),
            "geom": lj.get("geometryType"), "count": cnt.get("count"), "fields": fields,
            "bbox": bb,
            "has_point": any(x in up for x in F_POINT),
            "has_range": any(x in up for x in F_RANGE),
            "has_unit": any(x in up for x in F_UNIT),
            "has_esn": any(x in up for x in F_ESN),
            "has_zip": any(x in up for x in F_ZIP),
            "has_community": any(x in up for x in F_COMM),
            "nfields": len(fields)}

def probe_socrata(url):
    m = re.search(r"https?://([^/]+)/d/([a-z0-9]{4}-[a-z0-9]{4})", url or "")
    if not m: return {"ok": False, "err": "socrata url"}
    host, did = m.group(1), m.group(2)
    v = get_json("https://%s/api/views/%s.json" % (host, did), timeout=20)
    if "__error__" in v: return {"ok": False, "err": v["__error__"]}
    cols = [{"name": c.get("fieldName"), "type": c.get("dataTypeName")} for c in v.get("columns", [])]
    up = [c["name"].upper() for c in cols if c["name"]]
    cnt = get_json("https://%s/resource/%s.json?$select=count(1)" % (host, did), timeout=30)
    n = None
    try: n = list(cnt[0].values())[0]
    except Exception: pass
    return {"ok": True, "api": "https://%s/resource/%s.json" % (host, did), "layer": v.get("name"),
            "geom": "socrata", "count": n, "fields": cols, "bbox": None,
            "has_point": any(x in up for x in F_POINT), "has_range": any(x in up for x in F_RANGE),
            "has_unit": any(x in up for x in F_UNIT), "has_esn": any(x in up for x in F_ESN),
            "has_zip": any(x in up for x in F_ZIP), "has_community": any(x in up for x in F_COMM),
            "nfields": len(cols)}

def level_of(title, cov):
    t = title.lower()
    if re.search(r"\bstatewide\b|state of|全州", t): return "州"
    if re.search(r"county|parish|borough", t): return "县"
    if re.search(r"\bcity\b|township|village|municipal", t): return "市镇"
    if cov >= 0.6: return "州(疑似全州)"
    if cov >= 0.15: return "区域"
    return "县市/局部"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--max-probe", type=int, default=250)
    a = ap.parse_args()
    ab = a.state.upper()
    sb = state_bbox(ab)
    if not sb:
        print("bad state"); return
    os.makedirs(OUT, exist_ok=True)

    recs = ch_agol(ab, sb)
    print("[%s] agol raw=%d" % (ab, len(recs)), flush=True)
    hres, meta = ch_portal(ab)
    recs += [r for r in hres]
    print("[%s] portal raw=%d meta=%s" % (ab, len(hres), meta), flush=True)

    # 归并去重（同 url 合并渠道信息）
    bykey, uniq = {}, []
    for r in recs:
        k = (str(r.get("url") or "") + "|" + str(r.get("title"))).lower()
        if k in bykey:
            bykey[k].setdefault("chs", [bykey[k]["ch"]]).append(r["ch"])
            continue
        bykey[k] = r; uniq.append(r)

    # 空间过滤：AGOL 有 bbox 的，中心点必须落在本州
    REL = re.compile(r"address|911|e911|situs|site|parcel|structure|centerline", re.I)
    keep = []
    for r in uniq:
        if not r["ch"].startswith("agol") and not REL.search(r.get("title") or ""):
            continue
        if r["ch"].startswith("agol") and r.get("bbox") and not in_state(r["bbox"], sb):
            continue
        keep.append(r)
    print("[%s] uniq=%d keep=%d" % (ab, len(uniq), len(keep)), flush=True)

    todo = [r for r in keep if r.get("url")][:a.max_probe]
    def run(r):
        u = str(r.get("url") or "")
        if r["ch"].startswith("socrata") or "/d/" in u and re.search(r"/d/[a-z0-9]{4}-", u):
            p = probe_socrata(u)
        else:
            p = probe_layer(u)
        out = dict(r)
        if r["ch"].startswith("agol"):
            bb = p.get("bbox") or r.get("bbox")
        else:
            bb = p.get("bbox")
        out["bbox"] = bb
        cov = 0.0
        if bb:
            a1, b1, a2, b2 = sb
            x1, y1, x2, y2 = bb
            iw = max(0, min(a2, x2) - max(a1, x1)); ih = max(0, min(b2, y2) - max(b1, y1))
            cov = round((iw * ih) / max((a2 - a1) * (b2 - b1), 1e-9), 3)
        out["cov"] = cov
        out["level"] = level_of(r.get("title", ""), cov)
        out.update({k: v for k, v in p.items() if k != "bbox"})
        return out

    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(run, todo))
    a1, b1, a2, b2 = sb
    def overlaps(r):
        bb = r.get("bbox")
        if not bb: return True
        x1, y1, x2, y2 = bb
        return not (x2 < a1 or x1 > a2 or y2 < b1 or y1 > b2)
    before = len(rows)
    rows = [r for r in rows if overlaps(r)]
    print("[%s] geo-filter %d -> %d" % (ab, before, len(rows)), flush=True)

    json.dump({"state": ab, "name": NAME.get(ab), "bbox": sb, "portals": meta, "rows": rows},
              open(os.path.join(OUT, ab + ".json"), "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for r in rows if r.get("ok"))
    print("[%s] done rows=%d ok=%d" % (ab, len(rows), ok), flush=True)

if __name__ == "__main__":
    main()
