#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 02 工人 —— 采集器（试点）

一个图层一个 job，只干活不报警。三种形态三套采法：
  FeatureServer / MapServer → keyset 游标翻页（OID 递增），不支持分页则 OID 区间切片
  Socrata                   → /resource/{id}.csv 分页
产出：
  collect/out/<layer>/part-XXXXX.ndjson.gz
  collect/out/<layer>/_manifest.json   （count / rows / diff / elapsed / err）

用法:
  python3 collect/pilot.py --layer ks911 [--limit 500]   # limit 用于 smoke
  python3 collect/pilot.py --list
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, re, sys, time
import urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "collect", "pilot_layers.json")
OUTBASE = os.path.join(ROOT, "collect", "out")
UA = {"User-Agent": "Mozilla/5.0 (compatible; collect-pilot/1.0)"}
CHUNK = 50000          # 每个 part 最多多少行
TARGET_BYTES = 2_000_000


def get_json(url, timeout=60, tries=3):
    last = ""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # 429 / 5xx 退避
            last = str(e)[:120]
            time.sleep(1.5 * (i + 1))
    return {"__error__": last}


# ---------------- 字段归一化 ----------------
F_ADD = ("ADD_NUM", "ADDRNUM", "ADDRESS_NUMBER", "HOUSE_NUM", "HOUSENUM", "STREET_NUM", "ADDR_NO")
F_FULL = ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION")
F_PRE = ("PRE_DIR", "PREDIR", "PRE_DIRECTION")
F_ST = ("ST_NAME", "STREET", "STREET_NAME", "ROAD_NAME", "STR_NAME")
F_SUF = ("ST_SUF", "STTYPE", "STREET_TYPE", "SUFFIX")
F_POST = ("POST_DIR", "POSTDIR")
F_UNIT = ("SUBNUM", "UNIT", "UNIT_NUM", "SUITE", "APT", "BLDG", "UNITID")
F_CITY = ("CITY", "COMMUNITY", "MUNICIPALITY", "POST_CITY", "TOWN", "PLACE")
F_ZIP = ("ZIP", "ZIPCODE", "ZIP_CODE", "POSTAL_CODE", "ZIP5")
F_ESN = ("ESN", "ESN_ID", "ESNID")


def pick(attrs, names):
    up = {k.upper(): k for k in attrs}
    for n in names:
        if n in up:
            return str(attrs[up[n]] or "").strip()
    return ""


def normalize(attrs, lat, lon):
    add = pick(attrs, F_ADD)
    st = pick(attrs, F_ST)
    zipc = pick(attrs, F_ZIP)
    full = pick(attrs, F_FULL)
    if not add and full:
        m = re.match(r"\s*(\d+[\w-]*)", full)
        add = m.group(1) if m else ""
    if not st and full:
        parts = re.sub(r"^\s*\d+[\w-]*\s*", "", full).split(",")
        st = parts[0].strip() if parts else ""
    key = hashlib.md5(("%s|%s|%s" % (add.lower(), st.lower(), zipc)).encode()).hexdigest()[:16] if (add and st) else ""
    return {
        "add_num": add, "pre_dir": pick(attrs, F_PRE), "st_name": st,
        "st_suf": pick(attrs, F_SUF), "post_dir": pick(attrs, F_POST),
        "unit": pick(attrs, F_UNIT), "city": pick(attrs, F_CITY), "zip": zipc,
        "esn": pick(attrs, F_ESN), "lat": lat, "lon": lon, "addr_key": key,
    }


def page_size_for(api):
    """自适应页大小：字段多就少给点，避免响应过大"""
    meta = get_json(api + "?f=json", timeout=25)
    nf = len(meta.get("fields") or [])
    maxrc = int(meta.get("maxRecordCount") or 1000)
    ps = min(maxrc, 2000)
    if nf > 120:
        ps = min(ps, 200)
    elif nf > 60:
        ps = min(ps, 500)
    return ps, maxrc, meta


def collect_arcgis(url, limit=0, log=print):
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", url.rstrip("/"))
    api = url.split("?")[0].rstrip("/")
    if m and not m.group(2):
        api += "/0"
    ps, maxrc, meta = page_size_for(api)
    oid_field = meta.get("objectIdField") or meta.get("objectIdFieldName") or "OBJECTID"
    count = int((meta.get("definitionExpression") and 0) or 0)
    cnt = get_json(api + "/query?where=1%3D1&returnCountOnly=true&f=json", timeout=60)
    count = int(cnt.get("count") or 0)
    defexpr = meta.get("definitionExpression") or ""
    where0 = defexpr if defexpr else "1=1"
    log(f"  api={api} count={count} pagesize={ps} defexpr={bool(defexpr)}")

    rows = 0
    last_oid = None
    part_no = 0
    buf = []
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    def flush():
        nonlocal buf, part_no
        if not buf:
            return
        p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for r in buf:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log(f"  part {part_no}: {len(buf)} rows -> {os.path.basename(p)}")
        part_no += 1
        buf = []

    while True:
        where = where0 if last_oid is None else f"{oid_field}>{last_oid}"
        if defexpr:
            where = f"({defexpr}) AND {where}" if last_oid is not None else defexpr
        q = {"where": where, "outFields": "*", "returnGeometry": "true",
             "outSR": "4326", "f": "json", "resultRecordCount": ps,
             "orderByFields": oid_field}
        u = api + "/query?" + urllib.parse.urlencode(q)
        d = get_json(u, timeout=90)
        if "__error__" in d:
            return rows, count, "query_fail:" + d["__error__"], part_no
        feats = d.get("features") or []
        if not feats:
            break
        for ft in feats:
            a = ft.get("attributes") or {}
            g = (ft.get("geometry") or {})
            rec = normalize(a, g.get("y"), g.get("x"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": a})
            buf.append(rec)
            rows += 1
            oid = a.get(oid_field)
            if oid is None:
                for k in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                    if k in a:
                        oid = a[k]
                        break
            if oid is not None:
                last_oid = oid
        if len(buf) >= CHUNK:
            flush()
        if limit and rows >= limit:
            break
        if not d.get("exceededTransferLimit") and len(feats) < ps:
            break
        if last_oid is None:      # 没有 OID 字段，退化为 offset 翻页
            break
        time.sleep(0.15)
    flush()
    return rows, count, "", part_no


def collect_socrata(url, limit=0, log=print):
    m = re.search(r"https?://([^/]+)/d/([a-z0-9]{4}-[a-z0-9]{4})", url)
    if not m:
        return 0, 0, "bad_socrata_url", 0
    host, did = m.group(1), m.group(2)
    cnt = get_json("https://%s/resource/%s.json?$select=count(1)" % (host, did), timeout=60)
    try:
        count = int(list(cnt[0].values())[0])
    except Exception:
        count = 0
    rows = part_no = 0
    buf = []
    step = 20000
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    off = 0
    while True:
        u = "https://%s/resource/%s.json?$limit=%d&$offset=%d" % (host, did, step, off)
        d = get_json(u, timeout=120)
        if not isinstance(d, list) or not d:
            break
        for a in d:
            rec = normalize(a, a.get("latitude"), a.get("longitude"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": a})
            buf.append(rec)
            rows += 1
        off += len(d)
        if len(buf) >= CHUNK:
            p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
            with gzip.open(p, "wt", encoding="utf-8") as f:
                for r in buf:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            log(f"  part {part_no}: {len(buf)} rows")
            part_no += 1
            buf = []
        if limit and rows >= limit:
            break
        if len(d) < step:
            break
    if buf:
        p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for r in buf:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        part_no += 1
    return rows, count, "", part_no


CUR = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(CFG, encoding="utf-8"))
    if a.list:
        for x in cfg:
            print("%-10s %-10s %10s  %s" % (x["id"], x["svc"], x.get("expect"), x["title"][:50]))
        return 0
    L = [x for x in cfg if x["id"] == a.layer]
    if not L:
        print("unknown layer"); return 2
    CUR.update(L[0])
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    t0 = time.time()
    log = lambda m: print("[%s] %s" % (CUR["id"], m), flush=True)
    log("start %s" % CUR["url"][:90])
    if CUR["svc"] in ("FeatureServer", "MapServer"):
        rows, count, err, parts = collect_arcgis(CUR["url"], a.limit, log)
    elif CUR["svc"] == "Socrata":
        rows, count, err, parts = collect_socrata(CUR["url"], a.limit, log)
    else:
        rows, count, err, parts = 0, 0, "unsupported_svc", 0
    elapsed = round(time.time() - t0, 1)
    diff = round(abs(rows - count) / count, 4) if count else None
    man = {"id": CUR["id"], "title": CUR["title"], "url": CUR["url"], "svc": CUR["svc"],
           "count": count, "rows": rows, "parts": parts, "diff": diff,
           "elapsed_s": elapsed, "err": err, "limit": a.limit,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(OUTBASE, CUR["id"], "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(ROOT, "collect", "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "collect", "reports", CUR["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    log("done rows=%d count=%d diff=%s err=%s %.1fs" % (rows, count, diff, err or "-", elapsed))
    return 0 if (rows > 0 and not err) else 1


if __name__ == "__main__":
    raise SystemExit(main())
