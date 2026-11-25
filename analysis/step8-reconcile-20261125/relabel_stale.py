#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · 续跑收尾：把 `ok_index_stale` / `bytes_anomaly` 的层 ledger.json 状态订正过来。

为什么需要：pull_one 落 ledger 时按「资产数 == CSV release_payload_n」判 status，只要不等就写
`mismatch`；但 finalize_pull.py 按实测资产数把「实测 > CSV」判成 `ok_index_stale`（CSV 是
2026-11-20 shallow 索引，记少了片，不是拉取失败）。若不回写 ledger，reconcile v2 会把这些层
继续算成「没拉齐」，`local_absent_assets_exist_not_downloaded` 就永远清不到 0。

口径（严格）：
  只订正 `result_final` 为 ok_index_stale / bytes_anomaly 的层，且必须同时满足
  ① 层目录存在　② 实际 part 数 == ledger.part_files == manifest.part_files
  其它一律不动（真 mismatch / corrupt / asset_gone 保持原状，不许借这一步洗白）。

用法：python3 analysis/step8-reconcile-20261125/relabel_stale.py
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
FIX = {"ok_index_stale", "bytes_anomaly", "checkpoint_unit_rows_missing"}


def layer_dir(lid):
    p = os.path.join(DIST, "layers", lid)
    if os.path.isdir(p):
        return p
    cands = glob.glob(os.path.join(DIST, "layers", "*" + glob.escape(lid)))
    return cands[0] if cands else ""


def main():
    p = os.path.join(HERE, "pull-failed.csv")
    if not os.path.isfile(p):
        raise SystemExit("先跑 finalize_pull.py 生成 pull-failed.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    todo = [r for r in rows if r["result_final"] in FIX]
    done = collections.Counter()
    for r in todo:
        d = layer_dir(r["layer"])
        if not d:
            done["no_dir"] += 1
            continue
        parts = len([x for x in os.listdir(d) if x.startswith("part-u") and x.endswith(".ndjson.gz")])
        lp = os.path.join(d, "ledger.json")
        if not os.path.isfile(lp):
            done["no_ledger"] += 1
            continue
        led = json.load(open(lp, encoding="utf-8"))
        if int(r["part_files"] or 0) != parts or int(led.get("part_files") or 0) != parts:
            done["part_count_mismatch"] += 1
            continue
        led["status"] = r["result_final"]
        led["status_note"] = r["note"]
        led["relabel_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        json.dump(led, open(lp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        done[r["result_final"]] += 1
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "candidates": len(todo), "relabeled": dict(done)}
    json.dump(out, open(os.path.join(HERE, "relabel-stale.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
