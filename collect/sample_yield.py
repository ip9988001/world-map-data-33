#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S5 实测漏斗：抽样 220 层真下载，测 声明→实采→有效地址→去重后净新增。
口径：单层上限 2 万行，总量上限 300 万行（够估比例，不烧带宽）。"""
from __future__ import annotations
import csv, hashlib, json, os, re, sys, time, urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lib.fetch import get_json                     # noqa: E402
from lib.schema import normalize                   # noqa: E402

CAP = 20000
TOTAL_CAP = 3_000_000
OUT_J = os.path.join(HERE, "parcel_yield.json")


def api_of(url):
    u = url.split("?")[0].rstrip("/")
    if not re.search(r"/(FeatureServer|MapServer)(/\d+)?$", u):
        return u
    if not re.search(r"/\d+$", u):
        u += "/0"
    return u


def run_layer(r):
    api = api_of(r["url"])
    t0 = time.time()
    st = {"layer": r["layer_id"], "grp": r["grp"], "state": r["state"], "grade": r["grade"],
          "declared": int(r["rows"]), "fetched": 0, "valid": 0, "geo_only": 0,
          "blank": 0, "pages": 0, "err": "", "keys": []}
    try:
        meta = get_json(api + "?f=json", timeout=25)
        if "__error__" in meta:
            st["err"] = "meta:" + str(meta["__error__"])[:60]; return st
        oid = meta.get("objectIdField") or meta.get("objectIdFieldName")
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        if not oid:
            oid = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID", "OBJECTID_12")
                        if k in fns), "OBJECTID")
        maxrc = int(meta.get("maxRecordCount") or 1000)
        ps = min(maxrc, 2000)
        if len(fns) > 120: ps = min(ps, 200)
        elif len(fns) > 60: ps = min(ps, 500)
        where = meta.get("definitionExpression") or "1=1"
        last, keys = None, []
        while st["fetched"] < CAP:
            w = where if last is None else "%s AND %s>%s" % (where, oid, last) if where != "1=1" else "%s>%s" % (oid, last)
            q = {"where": w, "outFields": "*", "returnGeometry": "true", "outSR": 4326,
                 "f": "json", "resultRecordCount": ps, "orderByFields": oid}
            d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=120)
            if "__error__" in d:
                if st["fetched"] == 0:
                    q.pop("orderByFields"); q["where"] = where
                    d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=120)
                    if "__error__" in d:
                        st["err"] = "query:" + str(d["__error__"])[:60]; return st
                    st["err"] = "no_keyset(offset)"
                else:
                    st["err"] = "query_mid:" + str(d["__error__"])[:40]; break
            feats = d.get("features") or []
            st["pages"] += 1
            if not feats:
                break
            for ft in feats:
                a = ft.get("attributes") or {}
                g = ft.get("geometry") or {}
                rec = normalize(a, g.get("y"), g.get("x"))
                st["fetched"] += 1
                k = rec.get("addr_key") or ""
                if k:
                    st["valid"] += 1; keys.append(k)
                else:
                    fl = ""
                    for f in ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION"):
                        if a.get(f):
                            fl = str(a[f]).strip().upper(); break
                    if fl and re.search(r"\d", fl):
                        st["valid"] += 1
                        keys.append("fb:" + hashlib.md5(fl.encode("utf-8", "replace")).hexdigest()[:16])
                    elif rec.get("lat") is not None and rec.get("lon") is not None:
                        st["geo_only"] += 1
                        keys.append("pt:%.5f,%.5f" % (float(rec["lat"]), float(rec["lon"])))
                    else:
                        st["blank"] += 1
                oidv = a.get(oid)
                if oidv is None:
                    for kk in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                        if kk in a: oidv = a[kk]; break
                if oidv is not None: last = oidv
            if not d.get("exceededTransferLimit") and len(feats) < ps:
                break
            if last is None:
                break
        st["keys"] = keys
        st["sec"] = round(time.time() - t0, 1)
        return st
    except Exception as e:
        st["err"] = type(e).__name__ + ":" + str(e)[:60]
        return st


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "sample200.csv"), encoding="utf-8")))
    print("[S5] 待采 %d 层（单层≤%d 行，总量≤%d）" % (len(rows), CAP, TOTAL_CAP), flush=True)
    out, total = [], 0
    gkeys = set()
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(run_layer, r) for r in rows]
        for i, f in enumerate(futs, 1):
            st = f.result()
            total += st["fetched"]
            gkeys.update(st["keys"])
            st["uniq_keys"] = len(set(st["keys"]))
            out.append(st)
            if i % 20 == 0:
                print("  %d/%d fetched=%d total=%d" % (i, len(rows), total, len(gkeys)), flush=True)

    agg = Counter()
    dec = 0
    for st in out:
        agg["fetched"] += st["fetched"]; agg["valid"] += st["valid"]
        agg["geo_only"] += st["geo_only"]; agg["blank"] += st["blank"]
        agg["err"] += 1 if st["err"] else 0
        agg["layers"] += 1
        if not st["err"]:
            dec += st["declared"]
    f_ = agg["fetched"] or 1
    res = {"layers": agg["layers"], "err_layers": agg["err"],
           "declared_of_ok_layers": dec, "fetched": agg["fetched"],
           "valid": agg["valid"], "geo_only": agg["geo_only"], "blank": agg["blank"],
           "valid_rate": round(agg["valid"] * 100.0 / f_, 2),
           "usable_rate": round((agg["valid"] + agg["geo_only"]) * 100.0 / f_, 2),
           "global_unique_keys": len(gkeys),
           "dedup_rate": round(len(gkeys) * 100.0 / f_, 2),
           "detail": out}
    with open(OUT_J, "w", encoding="utf-8") as fp:
        json.dump(res, fp, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False, indent=1))

    nr = len(gkeys) * 100.0 / f_
    proj = int(dec * nr / 100.0)
    open("/tmp/s5.txt", "w", encoding="utf-8").write("\n".join([
        "✅ 10-P 自研 S5/7 · 实测漏斗完成",
        "",
        "采 %d 层（失败 %d 层），实取 %s 行" % (agg["layers"], agg["err"], format(agg["fetched"], ',')),
        "",
        "漏斗：",
        "· 有效地址（门牌+街道）%s 行 —— %.1f%%" % (format(agg["valid"], ','), agg["valid"]*100.0/f_),
        "· 仅坐标可用 %s 行 —— %.1f%%" % (format(agg["geo_only"], ','), agg["geo_only"]*100.0/f_),
        "· 空地址 %s 行 —— %.1f%%" % (format(agg["blank"], ','), agg["blank"]*100.0/f_),
        "",
        "跨层去重后独立键 %s（去重存活率 %.1f%%）" % (format(len(gkeys), ','), nr),
        "",
        "外推：这批层声明 %s 行 → 预测净新增地址约 %s 条" % (format(dec, ','), format(proj, ','))]))
    return res


if __name__ == "__main__":
    main()
