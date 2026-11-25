#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · 行级抽样补到 ≥10%（纯本地 zcat，不下载任何东西）。

背景：主跑的行级抽样（`--do_rows` 随机 10% + 字节最大 10 层）实际落在 manifest 里的只有 337 层
（= 9.5%，差额是因为 manifest 分片是「累积重写」且末段被后一轮覆盖，见 REPORT §7 注）。
本脚本把缺口补齐到 ≥355 层（3,550 的 10%），并把逐层证据写 `rowcheck-extra.json` / `rowcheck.log`。

口径不变：层目录里所有 `part-u*.ndjson.gz` 的 `zcat|wc -l` 合计 == 该 tag 的
`release-checkpoint.json` 的 `unit_rows` 合计。checkpoint 缺失或 unit_rows 全 0 的层
单列 `checkpoint_unit_rows_missing`（账本缺陷），不算行级不符。

用法：python3 analysis/step8-reconcile-20261125/rowcheck_sample.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import json
import os
import random
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
TARGET_PCT = 0.10


def done_layers():
    s = set()
    for p in glob.glob(os.path.join(HERE, "pull-manifest-shard-*.json")):
        for r in json.load(open(p, encoding="utf-8"))["records"]:
            if (r.get("checks") or {}).get("rows_match") is not None:
                s.add(r["layer"])
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=TARGET_PCT, help="抽样覆盖率目标（默认 0.10）")
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(open(INV, encoding="utf-8"))
            if r["reconcile_class"] == "local_absent_assets_exist_not_downloaded"]
    have = done_layers()
    prev = []
    pe = os.path.join(HERE, "rowcheck-extra.json")
    if os.path.isfile(pe):                       # 累积：前几批补充抽样的记录不丢
        prev = json.load(open(pe, encoding="utf-8")).get("records") or []
        have |= {x["layer"] for x in prev}
    need = max(0, int(a.target * len(rows)) + 1 - len(have))
    pool = [r for r in rows if r["layer"] not in have]
    random.seed(20261125)
    pick = random.sample(pool, min(need, len(pool)))
    print(f"[plan] 全集 {len(rows)}，已抽样 {len(have)}（{len(have)/len(rows):.1%}），补抽 {len(pick)} 层")
    out, tally = [], collections.Counter()
    t0 = time.time()
    with open(os.path.join(HERE, "rowcheck.log"), "a", encoding="utf-8") as lg:
        lg.write(f"\n=== start {time.strftime('%Y-%m-%dT%H:%M:%SZ')} 补抽 {len(pick)} 层 ===\n")
        for r in pick:
            lid = r["layer"]
            d = os.path.join(DIST, "layers", lid)
            parts = sorted(x for x in os.listdir(d)
                           if x.startswith("part-u") and x.endswith(".ndjson.gz"))
            n = 0
            for x in parts:
                n += subprocess.run(["zcat", os.path.join(d, x)], capture_output=True).stdout.count(b"\n")
            declared, note = None, ""
            cp = os.path.join(d, "release-checkpoint.json")
            if os.path.isfile(cp):
                doc = json.load(open(cp, encoding="utf-8"))
                ur = doc.get("unit_rows") or {}
                declared = sum(int(v or 0) for v in ur.values()) if ur else None
            if declared is None:
                verdict, note = "checkpoint_missing", "无 release-checkpoint.json"
            elif declared == 0:
                verdict, note = "checkpoint_unit_rows_missing", f"unit_rows=0，实测 {n}"
            elif n == declared:
                verdict, note = "pass", ""
            else:
                verdict, note = "fail", f"实测 {n} != 声明 {declared}"
            tally[verdict] += 1
            rec = {"layer": lid, "parts": len(parts), "rows_counted": n, "rows_declared": declared,
                   "verdict": verdict, "note": note}
            out.append(rec)
            lg.write(f"{lid} parts={len(parts)} rows={n}/{declared} {verdict} {note}\n")
            print(f"  {lid[:52]:52s} parts={len(parts):>4d} rows={n}/{declared} {verdict}")
    merged = {x["layer"]: x for x in prev}
    for x in out:
        merged[x["layer"]] = x
    agg = collections.Counter(x["verdict"] for x in merged.values())
    summary = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "denominator": len(rows),
               "already_sampled_before": len(have), "added": len(out),
               "extra_samples_total": len(merged), "extra_by_verdict": dict(agg),
               "coverage_after": round((done_layers() | set(merged)) and len(done_layers() | set(merged)) / len(rows), 4),
               "wall_s": round(time.time() - t0, 1)}
    json.dump({"summary": summary, "records": list(merged.values())},
              open(os.path.join(HERE, "rowcheck-extra.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
