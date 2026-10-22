#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并所有产物 → inventory.csv + 清单.md"""
import glob, json, os, re, csv
from collections import defaultdict
from ng911_inventory import state_bbox, ABBR
HERE = os.path.dirname(os.path.abspath(__file__))

def num(v):
    try: return int(v)
    except Exception: return 0

def load(pat):
    rows = []
    for f in sorted(glob.glob(os.path.join(HERE, pat))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        rows += d if isinstance(d, list) else d.get("rows", [])
    return rows

def main():
    rows = load("shard_*.json") + load("portal_*.json")
    BB = {ab: state_bbox(ab) for ab in set(ABBR.values())}
    for r in rows:
        bb, st = r.get("bbox"), r.get("state")
        if bb and st in BB and BB[st]:
            a1,b1,a2,b2 = BB[st]; x1,y1,x2,y2 = bb
            iw = max(0, min(a2,x2)-max(a1,x1)); ih = max(0, min(b2,y2)-max(b1,y1))
            r["cov"] = round(iw*ih/max((a2-a1)*(b2-b1),1e-9), 3)
    seen, uniq = set(), []
    for r in rows:
        k = (str(r.get("api") or r.get("url") or "") + "|" + str(r.get("title") or "")).lower()
        if k in seen: continue
        seen.add(k); uniq.append(r)

    def svc(r):
        u = str(r.get("url") or "")
        if "FeatureServer" in u: return "FeatureServer"
        if "MapServer" in u: return "MapServer"
        if r.get("ch") == "socrata": return "Socrata"
        if r.get("ch") == "ckan": return "CKAN/下载"
        if re.search(r"\.(zip|shp|gdb|geojson|csv|kml)$", u, re.I): return "文件下载"
        return r.get("ch") or "未知"

    def level(r):
        t = (r.get("title") or "").lower()
        if re.search(r"county|parish|borough", t): return "县"
        if re.search(r"\bcity\b|township|village|municipal", t): return "市镇"
        if re.search(r"statewide|state of|ng911|e911 state", t): return "州"
        cov = r.get("cov") or 0
        if cov >= 0.5: return "州(几何判定)"
        if cov >= 0.1: return "区域"
        return "县市/局部"

    cols = ["state","title","provider","level","service","count","geom","cov","api_url",
            "nfields","has_point","has_range","has_unit","has_esn","has_zip","has_community",
            "modified","license","channel","err","fields"]
    with open(os.path.join(HERE, "inventory.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(uniq, key=lambda x: ((x.get("state") or "ZZ"), -num(x.get("count")))):
            flds = ";".join("%s:%s" % (x.get("name"), x.get("type")) for x in (r.get("fields") or [])[:120])
            w.writerow({"state": r.get("state") or "未定位", "title": r.get("title"),
                        "provider": r.get("owner"), "level": level(r), "service": svc(r),
                        "count": r.get("count"), "geom": r.get("geom"), "cov": r.get("cov"),
                        "api_url": r.get("api") or r.get("url"), "nfields": r.get("nfields"),
                        "has_point": r.get("has_point"), "has_range": r.get("has_range"),
                        "has_unit": r.get("has_unit"), "has_esn": r.get("has_esn"),
                        "has_zip": r.get("has_zip"), "has_community": r.get("has_community"),
                        "modified": r.get("modified"), "license": r.get("license"),
                        "channel": r.get("ch"), "err": r.get("err"), "fields": flds})

    by = defaultdict(list)
    for r in uniq:
        by[r.get("state") or "未定位"].append(r)
    lines = ["# NG911 / 州级地址数据 —— 可得性总清单", "",
             "- 生成时间：%s" % __import__("time").strftime("%Y-%m-%d %H:%M UTC", __import__("time").gmtime()),
             "- 记录数（去重后）：%d" % len(uniq),
             "- 有条目州数：%d" % len([k for k in by if k != "未定位"]), ""]
    tot = sorted(by.items())
    lines += ["## 概览", "", "| 州 | 条目 | 已探明要素数合计 | 含全州级 |", "|---|---|---|---|"]
    for st, rs in tot:
        s = sum(num(x.get("count")) for x in rs)
        sw = sum(1 for x in rs if (x.get("cov") or 0) >= 0.5)
        lines.append("| %s | %d | %s | %d |" % (st, len(rs), format(s, ","), sw))
    for st, rs in tot:
        lines += ["", "## %s" % st, "", "| 要素数 | 层级 | 标题 | 提供方 | 类型 | 点/号段/单元 | 覆盖 |", "|---|---|---|---|---|---|---|"]
        for x in sorted(rs, key=lambda y: -num(y.get("count")))[:40]:
            flag = "%s%s%s" % ("点" if x.get("has_point") else "-",
                               "号段" if x.get("has_range") else "",
                               "单元" if x.get("has_unit") else "")
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                format(x["count"], ",") if isinstance(x.get("count"), int) else "-",
                level(x), (x.get("title") or "")[:60].replace("|", "/"),
                (x.get("owner") or "")[:28].replace("|", "/"), svc(x), flag, x.get("cov")))
    open(os.path.join(HERE, "清单.md"), "w").write("\n".join(lines))
    print("csv=%d md_states=%d" % (len(uniq), len(tot)))

if __name__ == "__main__":
    main()
