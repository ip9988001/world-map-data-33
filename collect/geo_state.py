#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2b：文本判不出州的层，取 1 条 feature 强制 outSR=4326，用州界多边形反查。"""
from __future__ import annotations
import csv, json, os, urllib.request, urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CSVF = os.path.join(HERE, "situs_layers.csv")
UA = "world-map-data-33/1.0 (+probe)"

STJ = json.load(open(os.path.join(os.path.dirname(HERE), "survey/ng911/us_states.json"), encoding="utf-8"))
BU = {}
for ft in STJ["features"]:
    nm = ft["properties"]["name"]
    g = ft["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    BU[nm] = [[(float(p[0]), float(p[1])) for p in ring] for poly in polys for ring in poly]

NAME2AB = {}
for nm, ab in [("Alabama","AL"),("Alaska","AK"),("Arizona","AZ"),("Arkansas","AR"),("California","CA"),
 ("Colorado","CO"),("Connecticut","CT"),("Delaware","DE"),("Florida","FL"),("Georgia","GA"),("Hawaii","HI"),
 ("Idaho","ID"),("Illinois","IL"),("Indiana","IN"),("Iowa","IA"),("Kansas","KS"),("Kentucky","KY"),
 ("Louisiana","LA"),("Maine","ME"),("Maryland","MD"),("Massachusetts","MA"),("Michigan","MI"),
 ("Minnesota","MN"),("Mississippi","MS"),("Missouri","MO"),("Montana","MT"),("Nebraska","NE"),
 ("Nevada","NV"),("New Hampshire","NH"),("New Jersey","NJ"),("New Mexico","NM"),("New York","NY"),
 ("North Carolina","NC"),("North Dakota","ND"),("Ohio","OH"),("Oklahoma","OK"),("Oregon","OR"),
 ("Pennsylvania","PA"),("Rhode Island","RI"),("South Carolina","SC"),("South Dakota","SD"),
 ("Tennessee","TN"),("Texas","TX"),("Utah","UT"),("Vermont","VT"),("Virginia","VA"),("Washington","WA"),
 ("West Virginia","WV"),("Wisconsin","WI"),("Wyoming","WY"),("District of Columbia","DC")]:
    NAME2AB[nm] = ab


def pip(x, y, ring):
    ins = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi):
            ins = not ins
        j = i
    return ins


def which_state(x, y):
    if not (-180 <= x <= -60 and 15 <= y <= 72):
        return ""
    for nm, rings in BU.items():
        for r in rings:
            if pip(x, y, r):
                return NAME2AB.get(nm, "")
    return ""


def first_pt(geom):
    t = geom.get("type")
    c = geom.get("coordinates")
    if t == "Point": return c
    if t in ("LineString",): return c[0] if c else None
    if t == "Polygon": return c[0][0] if c and c[0] else None
    if t in ("MultiPoint",): return c[0] if c else None
    if t in ("MultiLineString",): return c[0][0] if c and c[0] else None
    if t in ("MultiPolygon",): return c[0][0][0] if c and c[0] and c[0][0] else None
    return None


QS = {"where": "1=1", "outFields": "*", "resultRecordCount": 1,
      "outSR": 4326, "f": "geojson", "returnGeometry": "true"}


def extract(g):
    if not g:
        return None
    if "x" in g and "y" in g:
        return [g["x"], g["y"]]
    if isinstance(g.get("type"), str):
        return first_pt(g)
    if g.get("rings"):
        return g["rings"][0][0]
    if g.get("paths"):
        return g["paths"][0][0]
    return None


def one(r):
    u = r.get("url", "")
    if not u:
        return r, "", "nourl"
    q = u.rstrip("/") + "/query?" + urllib.parse.urlencode(QS)
    try:
        req = urllib.request.Request(q, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            j = json.loads(resp.read().decode("utf-8", "replace"))
        fe = j.get("features") or []
        if not fe:
            return r, "", "nofeat"
        g = fe[0].get("geometry") or {}
        pt = extract(g)
        if not pt or pt[0] is None:
            return r, "", "nogeom"
        ab = which_state(float(pt[0]), float(pt[1]))
        return r, ab, "geo" if ab else "outside"
    except Exception as e:
        return r, "", "err:" + type(e).__name__


def main():
    import sys
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    dry = "--dry" in sys.argv
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8")))
    todo = [r for r in rows if r["state"] == "未定位" and r.get("url")]
    if limit:
        todo = todo[:limit]
    print("[geo] 待判定 %d 层" % len(todo), flush=True)
    stat = Counter(); fixed_rows = 0; fixed = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, (r, ab, src) in enumerate(ex.map(one, todo), 1):
            stat[src] += 1
            if ab:
                r["state"] = ab; r["state_src"] = "geo_" + src
                fixed += 1; fixed_rows += int(r["rows"])
            if i % 500 == 0:
                print("  %d/%d fixed=%d" % (i, len(todo), fixed), flush=True)

    fn = ["layer_id","state","state_src","geom","rows","grade","reason","nfields","fields_hit","url"]
    if not dry:
        with open(CSVF, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(rows)

    unk = [r for r in rows if r["state"] == "未定位"]
    unk_rows = sum(int(r["rows"]) for r in unk if r["grade"] in ("strong", "weak"))
    st = Counter(); sr = Counter()
    for r in rows:
        if r["grade"] == "strong" and r["state"] != "未定位":
            st[r["state"]] += int(r["rows"])
    out = {"todo": len(todo), "fixed": fixed, "fixed_rows": fixed_rows, "src": dict(stat),
           "still_unknown_layers": len(unk), "still_unknown_rows_sw": unk_rows,
           "states_strong": len(st), "strong_rows_known": sum(st.values()),
           "top": st.most_common(10)}
    json.dump(out, open(os.path.join(HERE, "geo_state.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    open("/tmp/s2b.txt", "w", encoding="utf-8").write("\n".join([
        "✅ 10-P 自研 S2b/7 · 州归属补完",
        "",
        "剩余 4,359 层：每层取 1 条要素强制转经纬度，用州界多边形判州",
        "· 补上 %d 层 / %s 行" % (fixed, format(fixed_rows, ",")),
        "· 仍判不出 %d 层（%s 行）" % (len(unk), format(unk_rows, ",")),
        "",
        "strong 层现覆盖 %d 州 / %s 亿行" % (len(st), round(sum(st.values())/1e8, 2)),
        "Top: " + " / ".join("%s %s万" % (k, round(v/1e4)) for k, v in st.most_common(6)),
        "",
        "下一步 S3：可采清单定稿（对齐已有 47 州 + 去重口径）"]))


if __name__ == "__main__":
    main()
