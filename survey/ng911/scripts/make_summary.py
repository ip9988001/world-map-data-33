#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 layers.json + samples.csv.gz 生成按州汇总的 清单-精简.md（几十 KB）"""
import gzip, csv, json, os, re, collections
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def num(v):
    try: return int(float(v))
    except Exception: return 0
layers = json.load(open(os.path.join(HERE, "layers.json")))
cnt = collections.defaultdict(lambda: {"n": 0, "max": 0, "sw": 0})
for r in layers:
    st = r.get("state") or "未定位"
    cnt[st]["n"] += 1
    cnt[st]["max"] = max(cnt[st]["max"], num(r.get("count")))
samp = collections.defaultdict(lambda: {"s": 0, "addr": 0})
with gzip.open(os.path.join(HERE, "samples.csv.gz"), "rt") as f:
    for r in csv.DictReader(f):
        st = r["state"] or "未定位"
        if r["samples"] and r["samples"] != "[]": samp[st]["s"] += 1
        if re.search(r"\d{2,5}\s+[A-Za-z]", r["samples"] or ""): samp[st]["addr"] += 1
L = ["# NG911 / 州级地址数据 —— 按州汇总（精简）", "",
     "全量清单见 Release 资产 `ng911-raw-*.tar.gz`（含 6 万层明细与样本）。本表只给州级概览。", "",
     "| 州 | 图层数 | 有样本 | 含门牌样本 | 最大单层要素数 |", "|---|---|---|---|---|"]
tot = [0, 0, 0]
for st in sorted(cnt):
    L.append("| %s | %d | %d | %d | %s |" % (st, cnt[st]["n"], samp[st]["s"], samp[st]["addr"],
             format(cnt[st]["max"], ",")))
    if st != "未定位": tot = [tot[0] + cnt[st]["n"], tot[1] + samp[st]["s"], tot[2] + samp[st]["addr"]]
L += ["", "合计（不含未定位）：图层 %d，有样本 %d，含门牌样本 %d" % tuple(tot), ""]
open(os.path.join(HERE, "清单-精简.md"), "w").write("\n".join(L))
print("ok", tot)
