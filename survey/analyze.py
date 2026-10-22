#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2：归州 + 打分 + 逐州探针 → inventory.csv / inventory.md"""
import json, os, re, time, urllib.parse, urllib.request
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(HERE, "raw.json")))
PROBE_CACHE_F = os.path.join(HERE, "probe_cache.json")
UA = {"User-Agent": "ng911-probe/1.0"}
ABBR = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO",
"Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI",
"Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
"Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
"Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ",
"New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
"Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD",
"Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
"West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY","Puerto Rico":"PR"}

gj = json.load(open(os.path.join(HERE, "us_states.json")))
POLY, NAME_ABBR = {}, {}
for f in gj["features"]:
    nm = f["properties"]["name"]
    if nm not in ABBR:
        continue
    g = shape(f["geometry"]).buffer(0)
    POLY[nm] = g
    NAME_ABBR[nm] = ABBR[nm]

def get(url, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)[:120]}
            time.sleep(1)
    return {"__error__": "x"}

def states_of(extent):
    """extent 形如 [[minx,miny],[maxx,maxy]] (wkid 4326)"""
    if not extent:
        return [], None
    try:
        (x1, y1), (x2, y2) = extent[0], extent[1]
        if abs(x1) > 180 or abs(y1) > 90:
            return [], None
        bb = box(x1, y1, x2, y2)
        if bb.area <= 0:
            c = bb.centroid
            bb = box(c.x - 0.02, c.y - 0.02, c.x + 0.02, c.y + 0.02)
        hits = []
        for nm, g in POLY.items():
            if g.intersects(bb):
                a = g.intersection(bb).area
                if a > 0:
                    hits.append((a / bb.area, nm))
        hits.sort(reverse=True)
        if not hits:
            return [], None
        top = hits[0]
        return [h[1] for h in hits if h[0] > 0.02], top[1]
    except Exception:
        return [], None

GOV = re.compile(r"(state|dept|department|_gis|gis_|county|city|gov|authority|emergency|911|"
                 r"planning|assessor|it_|_it|university|regional)", re.I)
GOOD = re.compile(r"address\s*point|addresss?\s*pt|site\s*address|structure|911|e911|ng911", re.I)
BAD = re.compile(r"(sample|test|demo|copy\s*of|tutorial|map\s*notes)", re.I)

def score(it, title, owner):
    s = 0
    if GOOD.search(title): s += 60
    if re.search(r"address\s*point", title, re.I): s += 25
    if re.search(r"(range|centerline|centreline|road)", title, re.I): s -= 25
    if GOV.search(owner or ""): s += 20
    if it.get("src") == "hub": s += 15
    m = it.get("modified") or 0
    if m > 1.7e12: s += 20
    elif m > 1.5e12: s += 10
    if BAD.search(title): s -= 80
    return s

# ---------- 归州 ----------
bystate = {}   # nm -> [(score, item, title)]
national = []
for src in ("agol", "hub"):
    for it in RAW.get(src, []):
        title = it.get("title") or ""
        owner = it.get("owner") or ""
        if BAD.search(title):
            continue
        if not re.search(r"address|situshub|structure|e911|911", title, re.I):
            continue
        sns, primary = states_of(it.get("extent"))
        sc = score(it, title, owner)
        if len(sns) > 6 or (not sns and re.search(r"\b(usa|united states|national|conus)\b", title, re.I)):
            national.append((sc, it, title))
        elif primary:
            bystate.setdefault(primary, []).append((sc, it, title))

# ---------- 探针 ----------
def norm(url):
    url = (url or "").split("?")[0].rstrip("/")
    if "/FeatureServer" in url:
        url = url[:url.index("/FeatureServer")] + "/FeatureServer"
    return url

def probe(url):
    key = url
    cache = json.load(open(PROBE_CACHE_F)) if os.path.exists(PROBE_CACHE_F) else {}
    if key in cache:
        return cache[key]
    res = {"url": key, "ok": False}
    base = norm(url)
    if base:
        root = get(base + "?f=json")
        layers = root.get("layers") or []
        pick = None
        for L in layers:
            if re.search(r"address|situshub|structure|point", L.get("name", ""), re.I):
                pick = L; break
        if pick is None and layers:
            pick = layers[0]
        if pick:
            lid = pick["id"]
            lj = get("%s/%d?f=json" % (base, lid))
            if "fields" in lj:
                flds = [f["name"].upper() for f in lj["fields"]]
                cnt = get("%s/%d/query?where=1%%3D1&returnCountOnly=true&f=json" % (base, lid))
                res.update({
                    "ok": True, "layer": pick.get("name"), "lid": lid,
                    "geom": lj.get("geometryType"),
                    "count": cnt.get("count"),
                    "fields": flds,
                    "has_range": any(f in flds for f in ("HASLOW","HASHIGH","LFROM","LTO","LOW","HIGH","ODD_EVEN")),
                    "has_addnum": any(f in flds for f in ("ADD_NUM","ADDRNUM","ADDRESS_NUMBER","FULLADDR","FULL_ADDR","HOUSE_NUM","HOUSENUM","STREET_NUM","SITUS")),
                    "has_unit": any(f in flds for f in ("SUBNUM","UNIT","SUITE","APT","UNITID","SUB_ADDR")),
                    "has_esn": any(f in flds for f in ("ESN","ESN_ID","ESNID")),
                    "has_zip": any(f in flds for f in ("ZIP","ZIPCODE","ZIP_CODE","POSTAL_CODE")),
                    "has_city": any(f in flds for f in ("CITY","COMMUNITY","MUNICIPALITY","POST_CITY","CITYNAME")),
                })
    cache[key] = res
    json.dump(cache, open(PROBE_CACHE_F, "w"))
    return res

rows = []
names = sorted(POLY, key=lambda n: NAME_ABBR[n])
for nm in names:
    cands = sorted(bystate.get(nm, []), key=lambda x: -x[0])[:4]
    best = None
    probes = []
    for sc, it, title in cands:
        if not it.get("url"):
            continue
        p = probe(it["url"])
        p["_title"] = title; p["_owner"] = it.get("owner"); p["_mod"] = it.get("modified"); p["_sc"] = sc
        p["_extent"] = it.get("extent")
        probes.append(p)
        if p.get("ok") and p.get("geom") == "esriGeometryPoint" and (p.get("count") or 0) > 1000:
            best = p; break
    if best is None:
        for p in probes:
            if p.get("ok") and (p.get("count") or 0) > 0:
                best = p; break
    sp = POLY[nm]
    for p in probes:
        ext = p.get("_extent")
        cov = 0.0
        try:
            (x1, y1), (x2, y2) = ext[0], ext[1]
            if abs(x1) <= 180 and abs(y1) <= 90 and x2 > x1:
                cov = sp.intersection(box(x1, y1, x2, y2)).area / sp.area
        except Exception:
            cov = 0.0
        p["_cov"] = round(cov, 3)
    st = [p for p in probes if p.get("_cov", 0) >= 0.5 and p.get("ok")]
    st.sort(key=lambda p: (-(p.get("geom") == "esriGeometryPoint"), -(p.get("count") or 0), -p.get("_cov", 0)))
    rows.append({
        "state": nm, "abbr": NAME_ABBR[nm], "n_cand": len(bystate.get(nm, [])),
        "best": best, "statewide": (st[0] if st else None), "probes": probes,
    })
    sw = rows[-1]["statewide"] or {}
    print("%-2s %-20s cand=%-3d 全州=%-42s n=%s" % (NAME_ABBR[nm], nm[:20], len(bystate.get(nm, [])),
          ((sw.get("_title") or "-")[:42]), sw.get("count")), flush=True)

nat = [{"score": s, "title": t, "url": i.get("url"), "owner": i.get("owner"), "src": i.get("src")}
       for s, i, t in sorted(national, key=lambda x: -x[0])[:25]]
json.dump({"rows": rows, "national": nat}, open(os.path.join(HERE, "result.json"), "w"), indent=1)
print("done")
