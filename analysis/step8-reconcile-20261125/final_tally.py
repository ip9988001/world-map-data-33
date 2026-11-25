#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · 收口五数（以磁盘为唯一事实，不靠 manifest 记录条数）。

为什么不用 manifest：manifest 是「每个分片重写累积列表」，最后一轮（19 层）把 00017 覆盖成 19 条，
第一轮尾部 96 条也没进分片，所以 `layers_in_manifest` 永远小于 3,550。收账只能扫磁盘。

分母 3,550 = `analysis/full-inventory-20261124/local-vs-ledger-reconcile.csv` 里
`reconcile_class == local_absent_assets_exist_not_downloaded` 的全部层（第 8 步的工作集）。

分类（每个层必落且只落一类）：
  ok                                  ledger.status=ok 且 part 数三方一致（磁盘=ledger=manifest）
  ok_index_stale                      CSV 索引陈旧（实测 tar 数 > CSV），拉全了
  checkpoint_unit_rows_missing        checkpoint.json unit_rows=0（采集侧账本缺陷），part 齐全可读
  mismatch                            实测 < CSV 或行数不符 → 真缺
  half_dir                            有目录但 part 数不达标 / 无 ledger / ledger 与磁盘不一致 / 无目录
用法：python3 analysis/step8-reconcile-20261125/final_tally.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
OK = {"ok", "ok_index_stale", "bytes_anomaly", "checkpoint_unit_rows_missing"}


def main():
    rows = [r for r in csv.DictReader(open(INV, encoding="utf-8"))
            if r["reconcile_class"] == "local_absent_assets_exist_not_downloaded"]
    tally = collections.Counter()
    per = []
    for r in rows:
        lid = r["layer"]
        d = os.path.join(DIST, "layers", lid)
        parts = 0
        led = {}
        if os.path.isdir(d):
            parts = len([x for x in os.listdir(d)
                         if x.startswith("part-u") and x.endswith(".ndjson.gz")])
            lp = os.path.join(d, "ledger.json")
            if os.path.isfile(lp):
                try:
                    led = json.load(open(lp, encoding="utf-8"))
                except Exception:                                    # noqa: BLE001
                    led = {}
        st = led.get("status") or ""
        if parts > 0 and st in OK and int(led.get("part_files") or 0) == parts:
            cls = st
        elif not os.path.isdir(d) or parts == 0:
            cls = "half_dir"
            st = st or "no_dir"
        elif not led:
            cls = "half_dir"
            st = "no_ledger"
        elif int(led.get("part_files") or 0) != parts:
            cls = "half_dir"
            st = f"ledger_parts_{led.get('part_files')}_disk_{parts}"
        else:
            cls = "mismatch"
        tally[cls] += 1
        per.append({"layer": lid, "class": cls, "ledger_status": st, "part_files": parts,
                    "csv_payload_n": r.get("release_payload_n") or "",
                    "bytes": led.get("bytes") or ""})
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "denominator": len(rows),
           "tally": dict(tally),
           "sum_check": sum(tally.values()),
           "ok_total": tally.get("ok", 0),
           "failed_or_partial": tally.get("mismatch", 0) + tally.get("half_dir", 0)
                                 + tally.get("corrupt", 0) + tally.get("asset_gone", 0),
           "bytes_total": sum(int(x["bytes"] or 0) for x in per)}
    json.dump(out, open(os.path.join(HERE, "final-tally.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "final-tally.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "class", "ledger_status", "part_files",
                                          "csv_payload_n", "bytes"])
        w.writeheader()
        for x in sorted(per, key=lambda y: (y["class"], y["layer"])):
            w.writerow(x)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
