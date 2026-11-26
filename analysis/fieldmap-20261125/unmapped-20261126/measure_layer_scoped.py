#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000269 · 层内定制修法测算（只读）。

有些层的地址在**字段名过泛**的列里（NAME/TYPE/STR/LABEL…），不能进全局最小安全表，
只能按层/按 org 建方言。这里对这些层单独测算「按指定字段拼 street/number 后」的行命中率，
供 unmapped-classification.csv 的 sample_hit_rate / est_rows_recoverable 使用。

采样口径与 scan_unmapped.py 完全一致（首 + 中 part 文件各 150 行）。
输出：layer-scoped-fixes.jsonl

用法：python3 measure_layer_scoped.py
"""
from __future__ import annotations

import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FM))
sys.path.insert(0, FM)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import split_addr as SA   # noqa: E402

LAYERS = os.environ.get("INTAKE_LAYERS",
                        "/data/workspace/world-map-data-33/dist/intake-full/layers")
OUT = os.path.join(HERE, "layer-scoped-fixes.jsonl")
ROWS = 150

# 层订制：(layer_id, 街名字段, 街型/后缀字段, 门牌字段, 说明)
CASES = [
    ("s_com_arcgis_rest_services_GIS_App_GIS_App_BASE_MapServer_23",
     ["NAME"], ["TYPE"], ["CIVIC_TEXT", "ADDR_NBR"], "NAME+TYPE 拼街名"),
    ("nH5x_arcgis_rest_services_Address__Elections_FeatureServer_0",
     ["NAME"], ["TYPE"], ["CIVIC_TEXT", "ADDR_NBR"], "NAME+TYPE 拼街名（同 org 的另一层）"),
    ("city_ca_arcgis_rest_services_Public_OpenData_FeatureServer_0",
     ["NAME"], ["TYPE"], ["CIVIC_TEXT", "ADDR_NBR"], "NAME+TYPE 拼街名（Kelowna CWK）"),
    ("S7cpxnJP_arcgis_rest_services_Address_Points_FeatureServer_0",
     ["PARCEL_LOC"], [], [], "街名在 PARCEL_LOC，源里无门牌字段"),
    ("9Xs_arcgis_rest_services_AddressPts_OwensTwp_FeatureServer_0",
     ["LST_CONCAT"], [], ["ANUMBER"], "街名在 LST_CONCAT"),
    ("poec_arcgis_rest_services_AddressPoints_view_FeatureServer_0",
     ["STR"], [], ["STR_NUM"], "街名在 STR（3 字母缩写列）"),
]


def sample(lid, n=ROWS):
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".gz"))
    rows = []
    for fp in [parts[0], parts[len(parts) // 2]]:
        with gzip.open(os.path.join(d, fp), "rt", encoding="utf-8", errors="replace") as fh:
            c = 0
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
                c += 1
                if c >= n:
                    break
    return rows


def main():
    out = []
    for lid, sn, tn, nn, note in CASES:
        rows = sample(lid)
        hit = with_num = 0
        ex = None
        for r in rows:
            raw = r.get("raw") if isinstance(r.get("raw"), dict) else {}
            vals = [str(raw.get(k)).strip() for k in sn
                    if raw.get(k) is not None and str(raw.get(k)).strip()
                    and not SA.is_placeholder(str(raw.get(k)))]
            typs = [str(raw.get(k)).strip() for k in tn
                    if raw.get(k) is not None and str(raw.get(k)).strip()
                    and not SA.is_placeholder(str(raw.get(k)))]
            street = " ".join(vals[:2] + typs[:1]).strip()
            if street:
                hit += 1
                if any(str(raw.get(k) or "").strip() and
                       not SA.is_placeholder(str(raw.get(k))) for k in nn):
                    with_num += 1
                if ex is None:
                    ex = {"street": street, "num_sample": {k: raw.get(k) for k in nn}}
        n = len(rows) or 1
        rec = {"layer_id": lid, "note": note, "rows": len(rows),
               "street_hit_rate": round(hit / n, 4), "with_number_rate": round(with_num / n, 4),
               "street_fields": sn, "type_fields": tn, "number_fields": nn, "example": ex}
        out.append(rec)
        print(f"{lid[:58]:<58} street={rec['street_hit_rate']:.3f} num={rec['with_number_rate']:.3f} {note}")
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
