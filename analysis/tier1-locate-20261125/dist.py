#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 tier1-unlocated-states.csv 出 state-distribution.json（计数字段全部可从 CSV 复算）。"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "tier1-unlocated-states.csv"), newline="", encoding="utf-8")))

by_state = Counter(r["state_final"] for r in rows)
conf = Counter(r["confidence"] for r in rows)
urls = defaultdict(list)
for r in rows:
    urls[r["state_final"]].append(r["url"])

e1_hit = sum(1 for r in rows if r["e1_states"].strip())
e2_hit = sum(1 for r in rows if r["e2_states"].strip())
e3_geom = sum(1 for r in rows if r["e3_purity"].strip() and r["e3_purity"] != "bbox-only")
e3_vote = sum(1 for r in rows if r["e3_states"].strip() and "不投票" not in r["note"])

out = {
    "input": {
        "file": "tier1-unlocated.csv",
        "n_layers": len(rows),
        "rows_n_sum": sum(int(r["rows_n"]) for r in rows),
    },
    "by_state_final": dict(sorted(by_state.items(), key=lambda kv: (-kv[1], kv[0]))),
    "pilot_states": {k: {"n_layers": by_state.get(k, 0), "urls": urls.get(k, [])} for k in ("DE", "NH", "IA")},
    "unresolved": {"n_layers": by_state.get("unresolved", 0), "urls": urls.get("unresolved", [])},
    "confidence": dict(sorted(conf.items(), key=lambda kv: -kv[1])),
    "multi_state": {"n_layers": sum(1 for r in rows if r["multi_state"] == "true"),
                    "urls": [r["url"] for r in rows if r["multi_state"] == "true"]},
    "path_coverage": {"E1_metadata_hit": e1_hit, "E2_attribute_hit": e2_hit,
                      "E3_geometry_available": e3_geom, "E3_used_in_vote": e3_vote},
    "rows_n_by_state": {},
}
agg = defaultdict(int)
for r in rows:
    agg[r["state_final"]] += int(r["rows_n"])
out["rows_n_by_state"] = dict(sorted(agg.items(), key=lambda kv: -kv[1]))
json.dump(out, open(os.path.join(HERE, "state-distribution.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
