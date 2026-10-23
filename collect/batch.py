#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用工人：按 plan 文件挑一批图层来搬（STEP 03/04/05 共用）

用法:
  python3 collect/batch.py --plan collect/layer_plan.csv --mode state --state KS [--layer X]
  python3 collect/batch.py --plan collect/layer_plan.csv --mode statewide
  python3 collect/batch.py --plan collect/layer_plan.csv --mode bulk --offset 0 --size 200
  python3 collect/batch.py --list-matrix --mode bulk --size 200   # 给 workflow 生成 matrix
"""
from __future__ import annotations
import argparse, csv, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOOD = {"keyset", "oidsplit", "socrata", "package"}
# 采集只跑「地址相关」的层：普查清单不设限，但搬数据必须挑对东西，
# 否则会把 census block / parcel / permit 也搬回来（那是几十亿行垃圾）
REL = re.compile(r"address|911|situs|structure|situshub|snap|e911", re.I)
JUNK = re.compile(r"parcel|permit|block|centerline|centreline|street\s*range|census|boundary|"
                  r"water|soil|traffic|crime|police|fire\s*department|school|zone", re.I)


def load(plan, only_address=True):
    with open(plan, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("plan") in GOOD]
    if only_address:
        rows = [r for r in rows if REL.search(r["title"] or "") and not JUNK.search(r["title"] or "")]
    return rows


def select(rows, mode, state=None, layer=None, offset=0, size=200):
    if layer:
        return [r for r in rows if r["url"] == layer or r["layer_id"] == layer]
    if mode == "state":
        return [r for r in rows if r["state"] == state]
    if mode == "statewide":
        return [r for r in rows if 300000 <= int(r["row_count"] or 0) <= 20000000]
    big = [r for r in rows if int(r["row_count"] or 0) <= 20000000]
    return big[offset:offset + size]


def to_cfg(r):
    svc = {"FeatureServer": "FeatureServer", "MapServer": "MapServer",
           "Socrata": "Socrata"}.get(r["svc"], "FeatureServer")
    return {"id": (r["state"] + "_" + r["layer_id"])[:60], "svc": svc, "state": r["state"],
            "expect": int(r["row_count"] or 0), "title": r["title"], "url": r["url"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(ROOT, "collect", "layer_plan.csv"))
    ap.add_argument("--mode", default="bulk")
    ap.add_argument("--state")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--layer")
    ap.add_argument("--list-matrix", action="store_true")
    ap.add_argument("--emit-cfg")
    ap.add_argument("--all-titles", action="store_true", help="不按地址关键词过滤")
    a = ap.parse_args()
    rows = load(a.plan, only_address=not a.all_titles)
    sel = select(rows, a.mode, a.state, a.layer, a.offset, a.size)
    if a.list_matrix:
        print(json.dumps([to_cfg(r) for r in sel], ensure_ascii=False))
        return 0
    if a.emit_cfg:
        json.dump([to_cfg(r) for r in sel], open(a.emit_cfg, "w"), ensure_ascii=False, indent=1)
        print("wrote", a.emit_cfg, len(sel))
        return 0
    # 逐个采（矩阵模式下一个 job 只采一个，这里只用于本地调试）
    for cfg in sel:
        json.dump([cfg], open(os.path.join(ROOT, "collect", "pilot_layers.json"), "w"), ensure_ascii=False)
        rc = subprocess.call([sys.executable, os.path.join(ROOT, "collect", "pilot.py"), "--layer", cfg["id"]])
        print(cfg["id"], "rc=", rc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
