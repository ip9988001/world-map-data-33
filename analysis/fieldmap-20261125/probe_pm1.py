#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""#2 / #9 层的 ±1 行根因取证（样本清单第 2、9 层）。

做法：把 v1（dist/tar）与 v2（dist-v2/tar）该层的行按「除 addrkey 外的全字段」做 multiset 差，
把只在一边出现的行原样打印出来，再回到输入 part 包定位那条源记录，
用 fm_core 现口径重打一遍看它被判成什么（mapped / below_C）。

用法：python3 probe_pm1.py   （依赖 /tmp/dv1、/tmp/dv2 —— diff_v1_v2.py 已抽出样本层）
输出：probe-pm1.json
"""
from __future__ import annotations

import collections, csv, gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

LAYERS = "/data/workspace/world-map-data-33/dist/intake-full/layers"
KEYS = ["house_number", "street_name", "city", "state", "zip5", "lat", "lon", "tier", "grade"]


def rows_of(p):
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def main():
    sample = [r["layer_id"] for r in csv.DictReader(open(os.path.join(HERE, "sample-layers.csv")))]
    cov1 = {r["layer"]: r for r in csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv")))}
    cov2 = {r["layer"]: r for r in csv.DictReader(open(os.path.join(HERE, "layer-coverage.v2.csv")))}
    out = {"layers": []}
    for idx in (2, 9):
        lid = sample[idx - 1]
        p1, p2 = os.path.join("/tmp/dv1", lid + ".ndjson.gz"), os.path.join("/tmp/dv2", lid + ".ndjson.gz")
        if not (os.path.isfile(p1) and os.path.isfile(p2)):
            out["layers"].append({"idx": idx, "layer": lid, "status": "missing_extract"})
            continue
        A = [tuple(str(r.get(k)) for k in KEYS) for r in rows_of(p1)]
        B = [tuple(str(r.get(k)) for k in KEYS) for r in rows_of(p2)]
        ca, cb = collections.Counter(A), collections.Counter(B)
        only1 = list((ca - cb).elements())
        only2 = list((cb - ca).elements())
        c1, c2 = cov1.get(lid, {}), cov2.get(lid, {})
        rec = {"idx": idx, "layer": lid,
               "v1": {"rows": len(A), "in_rows": int(c1.get("in_rows") or 0),
                      "mapped": int(c1.get("mapped") or 0),
                      "dropped_below_c": int(c1.get("dropped_below_c") or 0),
                      "parse_error": int(c1.get("parse_error") or 0),
                      "diff": int(c1.get("diff") or 0)},
               "v2": {"rows": len(B), "in_rows": int(c2.get("in_rows") or 0),
                      "mapped": int(c2.get("mapped") or 0),
                      "dropped_below_c": int(c2.get("dropped_below_c") or 0),
                      "parse_error": int(c2.get("parse_error") or 0),
                      "diff": int(c2.get("diff") or 0)},
               "only_in_v1": [dict(zip(KEYS, x)) for x in only1[:5]], "n_only_v1": len(only1),
               "only_in_v2": [dict(zip(KEYS, x)) for x in only2[:5]], "n_only_v2": len(only2)}
        out["layers"].append(rec)
        print(json.dumps(rec, ensure_ascii=False, indent=1)[:1400], flush=True)
    json.dump(out, open(os.path.join(HERE, "probe-pm1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
