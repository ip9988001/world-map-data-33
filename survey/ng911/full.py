#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""零过滤全量清单：不设白名单/黑名单/阈值/门牌字段要求，一个数据集一条"""
import csv, json, glob, re, collections
def num(v):
    try: return int(float(v))
    except Exception: return 0
rows = list(csv.DictReader(open("clean.csv")))
by = collections.defaultdict(list)
for r in rows: by[r["state"] or "未定位"].append(r)
L = ["# NG911 / 州级地址数据 —— 零过滤全量清单", "",
     "不设白名单、不设黑名单、不设要素数阈值、不要求门牌字段。一个数据集/图层一条记录。",
     "唯一处理：同一 API 端点去重；州归属按图层几何中心点判定（无几何的归「未定位」）。", ""]
tot_known = 0; tot_layers = 0
L += ["| 州 | 记录数 | 已探明要素数合计 | 最大单层 | 最大单层标题 |", "|---|---|---|---|---|"]
for st in sorted(by):
    rs = by[st]
    known = [r for r in rs if num(r["count"]) > 0]
    s = sum(num(r["count"]) for r in rs)
    mx = max(rs, key=lambda r: num(r["count"])) if rs else None
    tot_known += s; tot_layers += len(rs)
    L.append("| %s | %d | %s | %s | %s |" % (st, len(rs), format(s, ","),
             format(num(mx["count"]), ",") if mx else "-", (mx["title"] or "")[:40].replace("|", "/") if mx else "-"))
L += ["", "合计记录 %d 条，已探明要素数合计 %s（含跨州层与重复视图，未做业务清洗）" % (tot_layers, format(tot_known, ",")), ""]
for st in sorted(by):
    L += ["", "## %s (%d 条)" % (st, len(by[st])), "",
          "| 要素数 | 几何 | 字段数 | 标题 | 提供方 | 服务 | 覆盖 | 门牌字段 |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(by[st], key=lambda r: -num(r["count"])):
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            format(num(r["count"]), ",") if num(r["count"]) else "-",
            (r["geom"] or "-").replace("esriGeometry", ""), r["nfields"],
            (r["title"] or "")[:55].replace("|", "/"), (r["provider"] or "")[:26].replace("|", "/"),
            r["service"], r["cov"], r["has_point"]))
open("清单-全量.md", "w").write("\n".join(L))
print("states", len(by), "layers", tot_layers, "sum", format(tot_known, ","))
print("geom:", collections.Counter(r["geom"] for r in rows))
print("service:", collections.Counter(r["service"] for r in rows))
print("has_point:", collections.Counter(r["has_point"] for r in rows))
