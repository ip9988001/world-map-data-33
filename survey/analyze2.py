#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2 v2：覆盖率归州 → 分层探针（全州级优先）→ inventory.csv / inventory.md"""
import json, os, re, time, csv, urllib.request
from shapely.geometry import shape, box

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = json.load(open(os.path.join(HERE, "raw.json")))
PC = os.path.join(HERE, "probe_cache.json")
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
DOM = {"data.ny.gov":"NY","health.data.ny.gov":"NY","data.pa.gov":"PA","data.texas.gov":"TX",
 "data.maryland.gov":"MD","data.illinois.gov":"IL","data.nj.gov":"NJ","data.wa.gov":"WA",
 "data.oregon.gov":"OR","data.ct.gov":"CT","data.hawaii.gov":"HI","data.iowa.gov":"IA",
 "data.sc.gov":"SC","data.delaware.gov":"DE","data.colorado.gov":"CO","data.nm.gov":"NM",
 "data.mo.gov":"MO","data.ma.gov":"MA","data.la.gov":"LA","data.az.gov":"AZ","data.va.gov":"VA",
 "data.ky.gov":"KY","data.in.gov":"IN","data.mi.gov":"MI","data.oh.gov":"OH","data.wi.gov":"WI",
 "data.nc.gov":"NC","data.tn.gov":"TN","data.ut.gov":"UT","data.vt.gov":"VT","data.me.gov":"ME",
 "data.nh.gov":"NH","data.ri.gov":"RI","data.alaska.gov":"AK","data.ar.gov":"AR","data.idaho.gov":"ID",
 "data.ks.gov":"KS","data.mt.gov":"MT","data.ne.gov":"NE","data.nv.gov":"NV","data.nd.gov":"ND",
 "data.ok.gov":"OK","data.sd.gov":"SD","data.wv.gov":"WV","data.wy.gov":"WY","data.ga.gov":"GA",
 "data.fl.gov":"FL","data.ca.gov":"CA","data.minnesota.gov":"MN","data.mn.gov":"MN","data.ms.gov":"MS"}

gj = json.load(open(os.path.join(HERE, "us_states.json")))
POLY = {}
for f in gj["features"]:
    nm = f["properties"]["name"]
    if nm in ABBR:
        POLY[nm] = shape(f["geometry"]).buffer(0)

def bbox_of(ext):
    try:
        if isinstance(ext, dict):
            c = ext.get("coordinates")
            (x1, y1), (x2, y2) = c[0], c[1]
        else:
            (x1, y1), (x2, y2) = ext[0], ext[1]
        if abs(x1) > 180 or abs(y1) > 90 or x2 <= x1:
            return None
        return box(x1, y1, x2, y2)
    except Exception:
        return None

GOV = re.compile(r"(state|dept|department|_gis|gis_|gov|authority|emergency|911|e911|ng911|"
                 r"planning|assessor|county|city|university|regional|dot)", re.I)
GOOD = re.compile(r"address\s*point|addresss?\s*pt|site\s*address|structure|situshub|911|e911|ng911|snap", re.I)
BAD = re.compile(r"(sample|test|demo|copy\s*of|tutorial|map\s*notes|template)", re.I)

def score(it, title):
    s = 0
    if GOOD.search(title): s += 60
    if re.search(r"address\s*point", title, re.I): s += 25
    if re.search(r"(centerline|centreline|road\s*center)", title, re.I): s -= 40
    if re.search(r"range", title, re.I): s -= 20
    if GOV.search(it.get("owner") or ""): s += 20
    if it.get("src") == "hub": s += 12
    m = it.get("modified") or 0
    m = m if isinstance(m,(int,float)) else 0
    if m > 1.72e12: s += 20
    elif m > 1.5e12: s += 8
    if BAD.search(title): s -= 90
    return s

cand = {}   # abbr -> [dict]
for src in ("agol", "hub"):
    for it in RAW.get(src, []):
        title = (it.get("title") or "").strip()
        if not title or BAD.search(title):
            continue
        if not re.search(r"address|situshub|structure|e911|911|snap", title, re.I):
            continue
        bb = bbox_of(it.get("extent"))
        hit = None
        if bb is not None:
            best = 0.0
            for nm, g in POLY.items():
                if not g.intersects(bb):
                    continue
                c = g.intersection(bb).area / max(g.area, 1e-9)
                if c > best:
                    best, hit = c, nm
            cov = best
        else:
            cov = 0.0
        if len(title) > 0 and re.search(r"\b(usa|united states|conus|national)\b", title, re.I) and cov > 0.02:
            hit = None
        if hit:
            cand.setdefault(ABBR[hit], []).append(
                {"it": it, "title": title, "cov": round(cov, 3), "score": score(it, title)})
for it in RAW.get("socrata", []):
    ab = DOM.get((it.get("owner") or "").lower())
    title = it.get("title") or ""
    if ab and re.search(r"address|911|e911|situs|site", title, re.I) and not BAD.search(title):
        cand.setdefault(ab, []).append({"it": it, "title": title, "cov": 0.0, "score": score(it, title) + 5})

# ---------- 探针 ----------
def load_pc():
    return json.load(open(PC)) if os.path.exists(PC) else {}

def get(url, tries=2):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1: return {"__error__": str(e)[:100]}
            time.sleep(0.8)

def probe(url, caches):
    url = (url or "").split("?")[0].rstrip("/")
    if not url: return {"ok": False}
    if url in caches: return caches[url]
    res = {"ok": False, "url": url}
    base = url
    if "/FeatureServer/" in base and re.search(r"/FeatureServer/\d+$", base):
        base = re.sub(r"/\d+$", "/FeatureServer", base)
    if "/MapServer" in base:
        base = base[:base.index("/MapServer")] + "/FeatureServer"
    root = get(base + "?f=json")
    layers = root.get("layers") or []
    pick = None
    for L in layers:
        if re.search(r"address|situshub|structure|point", L.get("name", ""), re.I):
            pick = L; break
    if pick is None and layers: pick = layers[0]
    if pick:
        lj = get("%s/%d?f=json" % (base, pick["id"]))
        if "fields" in lj:
            f = [x["name"].upper() for x in lj["fields"]]
            cnt = get("%s/%d/query?where=1%%3D1&returnCountOnly=true&f=json" % (base, pick["id"]))
            res.update({"ok": True, "layer": pick.get("name"), "geom": lj.get("geometryType"),
                        "count": cnt.get("count"), "nfields": len(f),
                        "point_fields": all(any(k in x for x in f) for k in ("ADD_NUM",)) })
            res["fields"] = ",".join([x for x in f if re.search(r"^(ADD_NUM|ADDRNUM|FULLADD|FULL_ADDR|HOUSE|SUBNUM|UNIT|ST_NAME|STREET|PRE_DIR|ST_SUF|POST_DIR|CITY|COMMUNITY|ZIP|ESN|STATE)", x)][:14])
    caches[url] = res
    return res

caches = load_pc()
rows = []
for nm in sorted(POLY, key=lambda n: ABBR[n]):
    ab = ABBR[nm]
    lst = cand.get(ab, [])
    sw = [c for c in lst if c["cov"] >= 0.55]
    ct = [c for c in lst if c["cov"] < 0.55]
    sw.sort(key=lambda c: (-c["score"], -c["cov"]))
    ct.sort(key=lambda c: -c["score"])
    swp, ctp = [], []
    for c in sw[:3]:
        if c["it"].get("url"):
            p = probe(c["it"]["url"], caches); p["_t"] = c["title"]; p["_cov"] = c["cov"]; p["_o"] = c["it"].get("owner")
            swp.append(p)
    for c in ct[:2]:
        if c["it"].get("url"):
            p = probe(c["it"]["url"], caches); p["_t"] = c["title"]; p["_cov"] = c["cov"]; p["_o"] = c["it"].get("owner")
            ctp.append(p)
    if not swp and not ctp:
        load_pc(); rows.append({"abbr": ab, "state": nm, "verdict": "无", "n": 0, "cand": len(lst)})
        print("%-2s %-22s 无 (cand=%d)" % (ab, nm, len(lst)), flush=True); continue
    b = None
    for p in swp:
        if p.get("ok") and (p.get("count") or 0) > 0:
            b = p; break
    v = "全州"
    if b is None:
        v = "仅县市"
        b = next((p for p in swp + ctp if p.get("ok") and (p.get("count") or 0) > 0), None)
        if b is None:
            v = "未验证"
            b = (swp + ctp)[0]
    rows.append({"abbr": ab, "state": nm, "verdict": v, "n": b.get("count"), "cand": len(lst),
                 "geom": b.get("geom"), "title": b.get("_t"), "url": b.get("url"),
                 "owner": b.get("_o"), "cov": b.get("_cov"), "fields": b.get("fields")})
    print("%-2s %-22s %-5s n=%-9s cov=%-5s %s" % (ab, nm, v, b.get("count"), b.get("_cov"), (b.get("_t") or "")[:48]), flush=True)

json.dump(caches, open(PC, "w"))
json.dump(rows, open(os.path.join(HERE, "result.json"), "w"), indent=1, ensure_ascii=False)
with open(os.path.join(HERE, "inventory.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["abbr","state","verdict","n","cand","geom","cov","title","owner","url","fields"])
    w.writeheader()
    for r in rows: w.writerow(r)
print("ok rows=", len(rows))
