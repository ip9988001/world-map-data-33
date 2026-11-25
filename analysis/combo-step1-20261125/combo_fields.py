#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""step2：给 1,340 层装配「字段名 + 样例值」（全本地，不抓网）。

两个本地源：
  1) survey/ng911/samples.csv.gz  —— 41,662 层的完整字段名列表 + 3 条原始记录（覆盖 1,340/1,340）
  2) analysis/coord-samples-20261124/samples/*.csv —— 管线当时抽的坐标样本，
     addr_fields_json 里是地址类字段的真实值（61,918 行 / 1,340 层，平均 46 行/层）

产物：_work/per_layer.json（逐层：fields / ng911_samples / coord_values / rows_n / sample_rows）
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
WORK = os.path.join(HERE, "_work")
MAXVAL = 40          # 每字段最多留多少个不同的真实值


def main():
    tgt = {r["url"]: r for r in csv.DictReader(open(os.path.join(WORK, "target_layers.csv"), encoding="utf-8"))}
    per = {u: {"url": u, "layer_id": r["layer_id"], "rows_n": int(r["rows_n"]), "state": r["state"],
               "fields": [], "ng911_samples": [], "coord_values": collections.defaultdict(list),
               "coord_rows": 0, "ng911_hit": False}
           for u, r in tgt.items()}

    # 1) ng911：字段名列表 + 3 条原始记录
    with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            u = r.get("url") or ""
            if u not in per:
                continue
            rec = per[u]
            rec["ng911_hit"] = True
            rec["fields"] = [f.strip() for f in (r.get("fields") or "").split(";") if f.strip()]
            try:
                rec["ng911_samples"] = json.loads(r.get("samples") or "[]")[:3]
            except Exception:
                rec["ng911_samples"] = []
            rec["ng911_title"] = r.get("title") or ""
            rec["ng911_svc"] = r.get("svc") or ""
            rec["ng911_geom"] = r.get("geom") or ""

    # 2) coord samples：地址类字段的真实值
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r.get("layer_url") or ""
            rec = per.get(u)
            if not rec:
                continue
            rec["coord_rows"] += 1
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                continue
            for k, v in af.items():
                v = v if isinstance(v, str) else str(v)
                v = re.sub(r"\s+", " ", v).strip()
                if not v or v.lower() in ("null", "none"):
                    continue
                vals = rec["coord_values"][k]
                if v not in vals and len(vals) < MAXVAL:
                    vals.append(v)
                if k not in rec["fields"]:
                    rec["fields"].append(k)

    out = {}
    for u, rec in per.items():
        rec["coord_values"] = dict(rec["coord_values"])
        out[u] = rec
    json.dump(out, open(os.path.join(WORK, "per_layer.json"), "w"), ensure_ascii=False)
    ok = sum(1 for r in out.values() if r["ng911_hit"])
    nv = sum(1 for r in out.values() if r["coord_values"])
    print(json.dumps({"layers": len(out), "ng911_hit": ok, "with_coord_values": nv,
                      "fields_total": sum(len(r["fields"]) for r in out.values()),
                      "coord_rows_total": sum(r["coord_rows"] for r in out.values())}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
