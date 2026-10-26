#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6b 全库快测：对未抽样的每一层只取 300 行，测真实有效率。"""
from __future__ import annotations
import csv, hashlib, json, os, re, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.fetch import get_json
from lib.schema import normalize

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = 300
OUT = os.path.join(HERE, "s6b_eff.json")


def api_of(url):
    u = url.split("?")[0].rstrip("/")
    if not re.search(r"/(FeatureServer|MapServer)(/\d+)?$", u):
        return u
    if not re.search(r"/\d+$", u):
        u += "/0"
    return u


def run(r):
    st = {"layer": r["layer_id"], "state": r["state"], "grade": r["grade"],
          "declared": int(r["rows"]), "fetched": 0, "valid": 0, "err": ""}
    try:
        api = api_of(r["url"])
        meta = get_json(api + "?f=json", timeout=20)
        if "__error__" in meta:
            st["err"] = "meta"; return st
        oid = meta.get("objectIdField") or meta.get("objectIdFieldName")
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        if not oid:
            oid = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID") if k in fns), "OBJECTID")
        ps = min(int(meta.get("maxRecordCount") or 1000), CAP)
        where = meta.get("definitionExpression") or "1=1"
        q = {"where": where, "outFields": "*", "returnGeometry": "false",
             "f": "json", "resultRecordCount": ps, "orderByFields": oid}
        d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=60)
        if "__error__" in d:
            q.pop("orderByFields")
            d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=60)
            if "__error__" in d:
                st["err"] = "query"; return st
        for ft in (d.get("features") or [])[:CAP]:
            a = ft.get("attributes") or {}
            rec = normalize(a, None, None)
            st["fetched"] += 1
            if rec.get("addr_key"):
                st["valid"] += 1
            else:
                for f in ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION"):
                    v = a.get(f)
                    if v and re.search(r"\d", str(v)):
                        st["valid"] += 1; break
        return st
    except Exception as e:
        st["err"] = type(e).__name__
        return st


def main():
    done = {r["layer_id"] for r in csv.DictReader(open(os.path.join(HERE, "sample200.csv"), encoding="utf-8"))}
    rows = [dict(r) for r in csv.DictReader(open(os.path.join(HERE, "situs_layers.csv"), encoding="utf-8"))
            if r["grade"] in ("strong", "weak") and r["layer_id"] not in done and r["url"]]
    print("[S6b] 待测 %d 层 × %d 行" % (len(rows), CAP), flush=True)
    out = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, st in enumerate(ex.map(run, rows), 1):
            out.append(st)
            if i % 250 == 0:
                ok = [x for x in out if x["fetched"]]
                v = sum(x["valid"] for x in ok); f = sum(x["fetched"] for x in ok)
                print("  %d/%d 有效率 %.1f%%" % (i, len(rows), v * 100.0 / max(1, f)), flush=True)
    json.dump({"rows": out}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    ok = [x for x in out if x["fetched"]]
    v = sum(x["valid"] for x in ok); f = sum(x["fetched"] for x in ok)
    hi = [x for x in ok if x["valid"] * 100.0 / x["fetched"] >= 20]
    print(json.dumps({"tested": len(out), "ok": len(ok), "err": len(out) - len(ok),
                      "fetched": f, "valid": v, "eff_pct": round(v * 100.0 / max(1, f), 2),
                      "hi_eff_layers": len(hi),
                      "hi_eff_declared": sum(x["declared"] for x in hi)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
