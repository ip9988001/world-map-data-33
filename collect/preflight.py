#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 01 采摘机器人 —— 预检（探路队）

给 6 万个图层做体检，产出「每层该怎么搬」的施工单。
每个分片跑一部分，写 plan_<i>.csv；最后由 collect-preflight.yml 的 merge job 合并成 layer_plan.csv。

用法: python3 collect/preflight.py --shard 0 --n 12
"""
import argparse, csv, gzip, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "survey", "ng911", "scripts"))
from ng911_inventory import get_json  # noqa: E402

SRC = os.path.join(ROOT, "survey", "ng911", "clean.csv.gz")
COLS = ["layer_id", "state", "title", "svc", "url", "row_count", "pagination",
        "defexpr", "maxrc", "nfields", "geom", "pagesize", "plan", "note"]


def lid_of(url: str) -> tuple[str, str]:
    u = url.split("?")[0].rstrip("/")
    m = re.search(r"/(FeatureServer|MapServer)(?:/(\d+))?$", u)
    if not m:
        return u, "0"
    base = u[: m.start()] + "/" + m.group(1)
    return base, (m.group(2) or "0")


def one(r):
    url = (r.get("api_url") or "").strip()
    svc = r.get("service") or ""
    out = {"state": r.get("state") or "未定位", "title": r.get("title"),
           "svc": svc, "url": url, "layer_id": "", "row_count": "", "pagination": "",
           "defexpr": "", "maxrc": "", "nfields": "", "geom": "", "pagesize": "", "plan": "", "note": ""}
    if not url:
        out["plan"] = "skip"; out["note"] = "no_url"; return out
    out["layer_id"] = re.sub(r"\W+", "_", url)[-60:]
    if svc in ("FeatureServer", "MapServer"):
        base, lid = lid_of(url)
        meta = get_json("%s/%s?f=json" % (base, lid), timeout=25)
        if "__error__" in meta:
            out["plan"] = "unknown"; out["note"] = "meta_fail:" + meta["__error__"][:40]; return out
        flds = meta.get("fields") or []
        aqc = meta.get("advancedQueryCapabilities") or {}
        pag = aqc.get("supportsPagination")
        if pag is None:
            pag = meta.get("supportsPagination", True)
        out["pagination"] = str(bool(pag)).lower()
        out["defexpr"] = (meta.get("definitionExpression") or "")[:300]
        maxrc = meta.get("maxRecordCount") or 1000
        out["maxrc"] = maxrc
        out["nfields"] = len(flds)
        out["geom"] = (meta.get("geometryType") or "").replace("esriGeometry", "")
        cnt = get_json("%s/%s/query?where=1%%3D1&returnCountOnly=true&f=json" % (base, lid), timeout=40)
        if "__error__" in cnt:
            out["plan"] = "unknown"; out["note"] = "count_fail"; return out
        try:
            n = int(cnt.get("count") or 0)
        except Exception:
            n = 0
        out["row_count"] = n
        if n == 0:
            out["plan"] = "skip"; out["note"] = "empty"; return out
        ps = min(int(maxrc), 2000)
        if len(flds) > 120:
            ps = min(ps, 200)
        elif len(flds) > 60:
            ps = min(ps, 500)
        out["pagesize"] = ps
        out["plan"] = "keyset" if pag else "oidsplit"
        if not pag:
            out["note"] = "服务不支持分页，走OID区间切片"
        return out
    if svc == "Socrata":
        m = re.search(r"https?://([^/]+)/d/([a-z0-9]{4}-[a-z0-9]{4})", url)
        if not m:
            out["plan"] = "unknown"; return out
        host, did = m.group(1), m.group(2)
        v = get_json("https://%s/api/views/%s.json" % (host, did), timeout=25)
        if "__error__" in v:
            out["plan"] = "unknown"; out["note"] = "meta_fail"; return out
        out["nfields"] = len(v.get("columns") or [])
        out["geom"] = "socrata"
        out["pagesize"] = 50000
        out["plan"] = "socrata"
        return out
    out["plan"] = "package"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--n", type=int, default=12)
    a = ap.parse_args()
    rows = list(csv.DictReader(gzip.open(SRC, "rt")))
    part = [r for i, r in enumerate(rows) if i % a.n == a.shard]
    print("shard %d/%d rows=%d" % (a.shard, a.n, len(part)), flush=True)
    with ThreadPoolExecutor(max_workers=10) as ex:
        res = list(ex.map(one, part))
    p = os.path.join(ROOT, "collect", "plan_%d.csv" % a.shard)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        [w.writerow({k: x.get(k, "") for k in COLS}) for x in res]
    from collections import Counter
    print("ok shard=%d plans=%s" % (a.shard, dict(Counter(x["plan"] for x in res))), flush=True)


if __name__ == "__main__":
    main()
