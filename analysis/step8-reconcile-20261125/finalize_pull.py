#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · A 收尾：把 manifest 分片汇总成 pull-failed.csv / pull-final.json，并对齐到对账口径。

为什么要这一步：逐层跑的时候①「解包文件数 == CSV release_payload_n」大量不成立，原因不是拉失败，
而是 CSV 的 `release_payload_n` 来自 **2026-11-20 的 shallow 索引**（`how: shallow`），对不少层只记了
前几片。这里按实测资产数区分：
  实测 > CSV   → `ok_index_stale`（拉全了、还比 CSV 多；CSV 侧陈旧，记 anomaly 不记失败）
  实测 < CSV   → `mismatch`（真缺片）
其余：gzip 坏 / tar 坏 → `corrupt`；tag 或资产 404 → `asset_gone`；
     行数（抽样层）与 checkpoint unit_rows 不符 → `mismatch`；
     字节偏差 >20%（仅当资产数与 CSV 一致时才比）→ `bytes_anomaly`（记异常，不改失败结论）。

用法：python3 analysis/step8-reconcile-20261125/finalize_pull.py
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    recs = {}
    for p in sorted(glob.glob(os.path.join(HERE, "pull-manifest-shard-*.json"))):
        for r in json.load(open(p, encoding="utf-8"))["records"]:
            recs[r["layer"]] = r
    # 小样 3 层也算进来（它们与主跑互斥，取并集）
    sp = os.path.join(HERE, "sample-validation.json")
    if os.path.isfile(sp):
        for r in json.load(open(sp, encoding="utf-8")) if False else json.load(open(sp, encoding="utf-8")):
            recs.setdefault(r["layer"], r)

    fixed = []
    for lid, r in recs.items():
        ch = r.get("checks") or {}
        csv_n = int(r.get("assets_n") or 0)
        parts = int(r.get("part_files") or 0)
        res = r.get("result") or ""
        note = ""
        if res in ("ok", "mismatch") and ch.get("assets_n") is False and parts > csv_n:
            res, note = "ok_index_stale", f"实测 {parts} 片 > CSV {csv_n}（CSV 陈旧，非拉取失败）"
        elif res == "ok" and ch.get("bytes_ok") is False:
            res, note = "bytes_anomaly", f"字节偏差 {ch.get('bytes_dev')}（资产数一致才比）"
        elif res == "ok":
            note = "四道校验通过"
        rec = dict(r)
        rec["result_final"] = res
        rec["note"] = note
        fixed.append(rec)

    agg = collections.Counter(x["result_final"] for x in fixed)
    rows_by = dict(agg)
    with open(os.path.join(HERE, "pull-failed.csv"), "w", newline="", encoding="utf-8") as fh:
        cols = ["layer", "tag", "result_final", "assets_n", "part_files", "bytes", "rows_declared",
                "rows_counted", "checks", "reason", "note"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(fixed, key=lambda x: (x["result_final"] != "ok", x["layer"])):
            if r["result_final"] == "ok":
                continue
            w.writerow({**{k: r.get(k, "") for k in cols if k != "checks"},
                        "checks": json.dumps(r.get("checks") or {}, ensure_ascii=False)})
    rowcheck = [x for x in fixed if (x.get("checks") or {}).get("rows_match") is not None]
    summary = {
        "layers_in_manifest": len(fixed),
        "by_result": rows_by,
        "ok_layers": rows_by.get("ok", 0) + rows_by.get("ok_index_stale", 0) + rows_by.get("bytes_anomaly", 0),
        "failed_layers": sum(v for k, v in rows_by.items()
                             if k in ("asset_gone", "corrupt", "mismatch")),
        "rowcheck_layers": len(rowcheck),
        "rowcheck_pass": sum(1 for x in rowcheck if x["checks"]["rows_match"] is True),
        "rowcheck_fail": sum(1 for x in rowcheck if x["checks"]["rows_match"] is False),
        "bytes_checked": sum(1 for x in fixed if "bytes_ok" in (x.get("checks") or {})),
        "bytes_ok": sum(1 for x in fixed if (x.get("checks") or {}).get("bytes_ok") is True),
        "index_stale_layers": rows_by.get("ok_index_stale", 0),
        "total_bytes": sum(int(x.get("bytes") or 0) for x in fixed),
    }
    json.dump(summary, open(os.path.join(HERE, "pull-final.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
