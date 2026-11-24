#!/usr/bin/env python3
"""把 Phase 3 的分片 ndjson 合成唯一权威 CSV（分片是 source of truth）。

为什么需要：`full_inventory_remote.py` 运行中按 200 层一批「追加写」CSV，重启/试点重跑会造成
CSV 与分片不一致（试点那 40 行在 shard-00000 里、CSV 因为被删过而漏掉）。本脚本按 url 去重重建整表。

用法：python3 analysis/full_inventory_remote_merge.py [--outdir ...]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "analysis", "full-inventory-20261124")
COLS = ["url", "state", "title", "svc", "geom", "n_fields", "maxRecordCount", "count",
        "count_source", "sampled_n", "fields_number_like", "number_nonnull",
        "addr_core_hit", "usable", "requests_n", "http_meta", "http_sample", "probe_note"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()
    rows, seen = [], set()
    for p in sorted(glob.glob(os.path.join(a.outdir, "inventory-remote-uncollected.shards", "*.ndjson"))):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                u = r.get("url")
                if not u or u in seen:
                    continue
                seen.add(u)
                rows.append(r)
    out = os.path.join(a.outdir, "inventory-remote-uncollected.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    import collections
    print(json.dumps({"rows": len(rows), "shards": len(glob.glob(os.path.join(
        a.outdir, "inventory-remote-uncollected.shards", "*.ndjson"))),
        "usable": dict(collections.Counter(r.get("usable") for r in rows)),
        "requests_total": sum(int(r.get("requests_n") or 0) for r in rows),
        "out": out}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
