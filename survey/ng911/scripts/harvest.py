#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全国层面一次性收割线索（不按州限制范围）：AGOL 全库 + Hub + Socrata 目录"""
import json, os, time, urllib.parse
from ng911_inventory import get_json, ext_of

HERE = os.path.dirname(os.path.abspath(__file__))
Q_AGOL = [
 '(title:"address point" OR title:"address points")',
 '("site address" OR situshub OR "structure address")',
 '("911 address" OR E911 OR NG911 OR "next generation 911")',
 '(address AND (point OR points))',
 '("address range" OR "road centerline" OR centerline)',
 '("parcel" AND address)',
 '("address" AND "emergency" AND "service" AND (number OR zone))',
 '("snap" OR "situs" OR "master address")',
]

def agol(q, cap=10000):
    out, start = [], 1
    while start <= cap:
        u = ("https://www.arcgis.com/sharing/rest/search?f=json&num=100&start=%d&q=%s"
             % (start, urllib.parse.quote(q + ' AND type:"Feature Service"')))
        d = get_json(u, timeout=40)
        if "__error__" in d or not d.get("results"): break
        for it in d["results"]:
            out.append({"ch":"agol","id":it.get("id"),"title":it.get("title") or "",
                        "owner":it.get("owner"),"url":it.get("url"),
                        "modified":it.get("modified"),"access":it.get("access"),
                        "bbox":ext_of(it),"tags":it.get("tags") or [],
                        "snippet":(it.get("snippet") or "")[:200]})
        tot = d.get("total", 0)
        if start + 100 > tot: break
        start += 100
        time.sleep(0.1)
    return out

def hub(q, pages=6):
    out = []
    for p in range(1, pages + 1):
        u = ("https://hub.arcgis.com/api/v3/datasets?page[size]=100&page[number]=%d&q=%s"
             % (p, urllib.parse.quote(q)))
        d = get_json(u, timeout=40)
        if "__error__" in d or not d.get("data"): break
        for it in d["data"]:
            a = it.get("attributes", {})
            out.append({"ch":"hub","id":a.get("id"),"title":a.get("name") or "",
                        "owner":a.get("source") or "","url":a.get("url"),
                        "modified":a.get("modified"),"count":a.get("recordCount"),
                        "bbox":ext_of(a),"license":a.get("license") or "","snippet":""})
        if len(d["data"]) < 100: break
    return out

def socrata(q, pages=8):
    out = []
    for p in range(pages):
        u = ("https://api.us.socrata.com/api/catalog/v1?q=%s&limit=100&offset=%d&only=datasets"
             % (urllib.parse.quote(q), p * 100))
        d = get_json(u, timeout=40)
        if "__error__" in d or not d.get("results"): break
        for it in d["results"]:
            r, m = it.get("resource", {}), it.get("metadata", {})
            out.append({"ch":"socrata","id":r.get("id"),"title":r.get("name") or "",
                        "owner":m.get("domain") or "","url":"https://%s/d/%s" % (m.get("domain"), r.get("id")),
                        "modified":r.get("updatedAt"),"bbox":None,
                        "license":m.get("license") or "","snippet":""})
    return out

if __name__ == "__main__":
    allrec = []
    for q in Q_AGOL:
        r = agol(q); print("[agol] %-55s %d" % (q[:55], len(r)), flush=True); allrec += r
    for q in ["address points","911 address","site addresses","address range","NG911","E911","situs","structure address"]:
        r = hub(q); print("[hub] %-30s %d" % (q, len(r)), flush=True); allrec += r
    for q in ["address points","911 address","site addresses","situs","parcel address"]:
        r = socrata(q); print("[socrata] %-25s %d" % (q, len(r)), flush=True); allrec += r
    seen, uniq = set(), []
    for r in allrec:
        k = (str(r.get("url") or "") + "|" + str(r.get("title") or "")).lower()
        if k in seen: continue
        seen.add(k); uniq.append(r)
    json.dump(uniq, open(os.path.join(HERE, "items.json"), "w"), ensure_ascii=False)
    print("TOTAL uniq", len(uniq), flush=True)
