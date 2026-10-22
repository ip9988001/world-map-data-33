#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""去噪：同层去重 + 剔除跨州/全国层 + 重算覆盖 → clean.csv / 清单.md"""
import csv, json, glob, os, re, collections
from ng911_inventory import state_bbox, ABBR
HERE = os.path.dirname(os.path.abspath(__file__))
BB = {ab: state_bbox(ab) for ab in set(ABBR.values())}

def num(v):
    try: return int(float(v))
    except Exception: return 0

rows = list(csv.DictReader(open(os.path.join(HERE, "inventory.csv"))))
# 1) 逐州精确覆盖 + 面积上限
for r in rows:
    st = r.get("state")
    if st not in BB or not BB[st]: continue
    a1, b1, a2, b2 = BB[st]
    sa = (a2 - a1) * (b2 - b1)
    try:
        x1, y1, x2, y2 = map(float, re.findall(r"-?[\d.]+", str(r.get("api_url")))) if False else (0,0,0,0)
    except Exception: pass
    bb = r.get("_bbox")
    if not bb: continue

# 从原始 json 补 bbox（csv 里没存）
src = {}
for f in glob.glob(os.path.join(HERE, "shard_*.json")) + glob.glob(os.path.join(HERE, "portal_*.json")):
    d = json.load(open(f))
    for x in (d if isinstance(d, list) else d.get("rows", [])):
        k = (str(x.get("api") or x.get("url") or "") + "|" + str(x.get("title") or "")).lower()
        src[k] = x

out = []
seen = set()
for r in rows:
    k = (str(r.get("api_url") or "") + "|" + str(r.get("title") or "")).lower()
    raw = src.get(k)
    bb = (raw or {}).get("bbox")
    st = r.get("state")
    cov, area_ratio = 0.0, 0.0
    if bb and st in BB and BB[st]:
        a1, b1, a2, b2 = BB[st]; x1, y1, x2, y2 = bb
        iw = max(0, min(a2, x2) - max(a1, x1)); ih = max(0, min(b2, y2) - max(b1, y1))
        cov = iw * ih / max((a2 - a1) * (b2 - b1), 1e-9)
        area_ratio = ((x2 - x1) * (y2 - y1)) / max((a2 - a1) * (b2 - b1), 1e-9)
    r["cov"] = round(cov, 3); r["area_ratio"] = round(area_ratio, 2)
    if area_ratio > 2.5:            # 跨州/全国层
        r["note"] = "跨州或全国层(area_ratio>2.5)"
    key = re.sub(r"/\d+$", "", str(r.get("api_url") or "")).lower()
    if key in seen: continue
    seen.add(key)
    out.append(r)

with open(os.path.join(HERE, "clean.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()), extrasaction="ignore")
    w.writeheader(); [w.writerow(r) for r in out]

st_rows = collections.defaultdict(list)
for r in out:
    if r["state"] != "未定位" and r.get("note") != "跨州或全国层(area_ratio>2.5)":
        st_rows[r["state"]].append(r)

print("%-4s %-7s %-9s %-9s %-6s %s" % ("st","层数","全州点层","最大点层","字段数","最佳层"))
summary = []
for st in sorted(st_rows):
    rs = st_rows[st]
    pts = [r for r in rs if r["geom"] == "esriGeometryPoint" and num(r["count"]) > 1000]
    sw = [r for r in pts if float(r["cov"]) >= 0.5]
    best = max(sw or pts or rs, key=lambda r: num(r["count"]))
    summary.append({"st": st, "n": len(rs), "n_sw": len(sw), "max": num(best["count"]),
                    "title": best["title"], "fields": best["nfields"], "url": best["api_url"]})
    print("%-4s %-7d %-9d %-9s %-6s %s" % (st, len(rs), len(sw), format(num(best["count"]), ","),
          best["nfields"], (best["title"] or "")[:40]))
json.dump(summary, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1)
tot = sum(s["max"] for s in summary)
print("\n州数=%d  全州级点层>0 的州=%d  单州最大层合计=%s" % (
    len(summary), sum(1 for s in summary if s["n_sw"]), format(tot, ",")))
