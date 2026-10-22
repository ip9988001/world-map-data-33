#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NG911 / 州级地址点可得性清点（单文件，无外部写权限需求）
阶段：
  1. ArcGIS Online 全库搜（多方言）+ Hub 开放数据 API + Socrata 目录
  2. 按 extent 与州界多边形相交 → 归州
  3. 每州 top 候选逐个探针：几何类型 / 要素数 / 关键字段
产出：raw.json / inventory.csv / inventory.md
ponytail: 目前上限是"按 extent 归州 + 关键词打分"，人工复核表在 md 里留 TODO 列
"""
import json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw.json")
UA = {"User-Agent": "ng911-probe/1.0 (inventory)"}
STATES_JSON = os.path.join(HERE, "us_states.json")

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            if i == tries - 1:
                return {"__error__": str(e)}
            time.sleep(1.5 * (i + 1))
    return {"__error__": "unreachable"}

def search_agol(q, maxn=1500):
    out, start = [], 1
    while start <= maxn:
        u = ("https://www.arcgis.com/sharing/rest/search?f=json&num=100&start=%d&q=%s"
             % (start, urllib.parse.quote(q)))
        d = get(u)
        if "__error__" in d or not d.get("results"):
            break
        for it in d["results"]:
            out.append({
                "src": "agol", "id": it.get("id"), "title": it.get("title") or "",
                "owner": it.get("owner"), "type": it.get("type"),
                "url": it.get("url"), "modified": it.get("modified"),
                "access": it.get("access"), "extent": it.get("extent"),
                "snippet": (it.get("snippet") or "")[:300],
            })
        if start + 100 > d.get("total", 0):
            break
        start += 100
        time.sleep(0.2)
    return out

def search_hub(q, maxn=800):
    out, page = [], 1
    while len(out) < maxn:
        u = ("https://hub.arcgis.com/api/v3/datasets?page[size]=100&page[number]=%d"
             "&q=%s&fields[datasets]=name,url,source,recordCount,extent,owner,modified,type,slug"
             % (page, urllib.parse.quote(q)))
        d = get(u)
        if "__error__" in d or not d.get("data"):
            break
        for it in d["data"]:
            a = it.get("attributes", {})
            out.append({
                "src": "hub", "id": a.get("id") or it.get("id"), "title": a.get("name") or "",
                "owner": (a.get("source") or ""), "type": a.get("type"),
                "url": a.get("url"), "modified": a.get("modified"),
                "count": a.get("recordCount"), "extent": a.get("extent"),
                "access": "public",
            })
        if len(d["data"]) < 100:
            break
        page += 1
        time.sleep(0.2)
    return out

def search_socrata(q, pages=6):
    out = []
    for p in range(pages):
        u = ("https://api.us.socrata.com/api/catalog/v1?q=%s&limit=100&offset=%d&only=datasets"
             % (urllib.parse.quote(q), p * 100))
        d = get(u)
        if "__error__" in d or not d.get("results"):
            break
        for it in d["results"]:
            r = it.get("resource", {})
            m = it.get("metadata", {})
            out.append({
                "src": "socrata", "id": r.get("id"), "title": r.get("name") or "",
                "owner": m.get("domain") or "", "type": r.get("type"),
                "url": "https://%s/d/%s" % (m.get("domain", ""), r.get("id")),
                "modified": r.get("updatedAt"), "extent": None, "access": "public",
            })
    return out

AGOL_QUERIES = [
    '(title:"address points") AND type:"Feature Service"',
    '(title:"address point") AND type:"Feature Service"',
    '("site address" OR "situshub" OR "structures") AND ("address") AND type:"Feature Service"',
    '("911" AND "address") AND type:"Feature Service"',
    '"E911" AND (type:"Feature Service")',
    '"address range" AND type:"Feature Service"',
    '("snap" OR "NG911" OR "NG9-1-1") AND type:"Feature Service"',
]

def main():
    cache = json.load(open(RAW)) if os.path.exists(RAW) else {}

    # ---- 阶段1：广搜
    if "agol" not in cache:
        rows = []
        for q in AGOL_QUERIES:
            r = search_agol(q)
            print("[agol] %-60s %d" % (q[:60], len(r)), flush=True)
            rows += r
        seen, uniq = set(), []
        for r in rows:
            k = r["id"]
            if k and k not in seen:
                seen.add(k); uniq.append(r)
        cache["agol"] = uniq
        json.dump(cache, open(RAW, "w"))
    print("agol uniq:", len(cache["agol"]))

    if "hub" not in cache:
        hub = []
        for q in ["address points", "911 address", "site addresses", "address range",
                  "NG911", "E911 address"]:
            r = search_hub(q)
            print("[hub] %-30s %d" % (q, len(r)), flush=True)
            hub += r
        cache["hub"] = hub
        json.dump(cache, open(RAW, "w"))
    print("hub:", len(cache["hub"]))

    if "socrata" not in cache:
        soc = []
        for q in ["address points", "911 address", "site addresses", "parcels address"]:
            soc += search_socrata(q)
        cache["socrata"] = soc
        json.dump(cache, open(RAW, "w"))
    print("socrata:", len(cache["socrata"]))

if __name__ == "__main__":
    main()
