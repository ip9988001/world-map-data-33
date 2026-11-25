#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 registry 的别名扩展方言挑 golden case 用真实样值（不编样值）。

来源：analysis/coord-samples-20261124/samples/*.csv 里 P7 层真实坐标样本行（addr_fields_json）。
条件：该层的门牌列 / 街名列都在本轮 27 条别名里，且值形态成立（门牌纯数字、街名有字母且不含邮编）。
产物：analysis/combo-step2-close-20261125/p7-samples.csv（最多取 5 层 × 1 行，供 gen_registry.py 生成 3–5 条 golden case）
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
ENGINE_YAML = os.path.join(ROOT, "engine", "dialects", "sources.v1.yaml")
PURE_HN = re.compile(r"^\d{1,6}[A-Za-z]?(-[0-9A-Za-z]{1,4})?$")
MAX_CASES = 5


def main():
    entry = [d for d in yaml.safe_load(open(ENGINE_YAML, encoding="utf-8"))["dialects"]
             if d.get("id") == "p7-alias-ext-v1"][0]
    nums = [a.lower() for a in entry["fields"]["number"]]
    sts = [a.lower() for a in entry["fields"]["street"]]

    pairs = {}
    with open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["pattern_id"] == "P7":
                pairs[r["url"]] = r
    p7pairs = {}
    p = os.path.join(HERE, "_p7_pairs.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            p7pairs[r["url"]] = r

    out = []
    per_layer = {}
    for f in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        if len(out) >= MAX_CASES:
            break
        if len(out) >= MAX_CASES:
            break
        for i, r in enumerate(csv.DictReader(open(f, encoding="utf-8"))):
            u = r.get("layer_url") or ""
            if u not in pairs or per_layer.get(u, 0) >= 2:
                continue
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                continue
            low = {k.lower(): (k, v) for k, v in af.items() if v not in (None, "", "null")}
            nk = next((low[a] for a in nums if a in low and PURE_HN.match(str(low[a][1]).strip())), None)
            sk = next((low[a] for a in sts if a in low and re.search(r"[A-Za-z]{2,}", str(low[a][1]))
                       and not re.search(r"\d{5}", str(low[a][1]))), None)
            if not nk or not sk:
                continue
            out.append({"url": u, "layer_id": pairs[u]["layer_id"], "state": r.get("state") or "",
                        "csv_file": os.path.relpath(f, ROOT), "row_index": r.get("row_index") or i,
                        "number_field": nk[0], "number_value": str(nk[1]).strip(),
                        "street_field": sk[0], "street_value": str(sk[1]).strip()})
            per_layer[u] = per_layer.get(u, 0) + 1
            if per_layer[u] >= 2:
                break
    with open(os.path.join(HERE, "p7-samples.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(json.dumps({"golden_sample_rows": len(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
