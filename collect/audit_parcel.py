#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2 审计：本机 collect/parcel_out 逐层数行，与 batch1.csv 的 declared 对账。

只读，不移动/不删除/不改写任何数据文件。产出 collect/parcel_audit.json。

为什么必须真数行而不能信账本：
  · run_parcel_batch.py 的 st["fetched"] 是内存累加，写盘要等 buf>=50000 才 flush。
    进程被杀时，buf 里的行已计入 fetched 但没落盘 → 账本的 34,236,118 可能虚高。
  · 每层实采行数账本完全没有，只有全局合计。
  · 账本 done_layers=1227 与目录数 1239 差 12 层，状态无法从账本裁决。

用法：
  python3 collect/audit_parcel.py                 # 全量审计（4 线程）
  python3 collect/audit_parcel.py --workers 2
  python3 collect/audit_parcel.py --limit 5       # 只审前 5 层（自检用）
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTBASE = os.path.join(HERE, "parcel_out")
BATCH = os.path.join(HERE, "batch1.csv")
SITUS = os.path.join(HERE, "situs_layers.csv")
LEDGER = os.path.join(ROOT, "ops", "parcel_progress.json")
AUDIT = os.path.join(HERE, "parcel_audit.json")

# 与已退役的 run_parcel_batch_local.py 完全一致：目录名 = 非法字符换下划线 + 90 字符截断
def san(lid):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", lid)[:90]


def count_rows(d):
    """数一个层目录下全部 part-*.ndjson.gz 的行数。用 zcat|wc -l（C 实现，比 py 逐行快数倍）。"""
    files = sorted(f for f in os.listdir(d) if f.endswith(".ndjson.gz"))
    if not files:
        return 0, 0
    paths = [os.path.join(d, f) for f in files]
    # 单层 part 数一般 <40，一次 zcat 全给，避免 N 次进程创建
    r = subprocess.run(["bash", "-c", 'zcat -- "$@" 2>/dev/null | wc -l', "_"] + paths,
                       capture_output=True, text=True)
    try:
        return int((r.stdout or "0").strip() or 0), len(files)
    except ValueError:
        return 0, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    batch = list(csv.DictReader(open(BATCH, encoding="utf-8")))
    situs = {r["layer_id"] for r in csv.DictReader(open(SITUS, encoding="utf-8"))}
    print("batch1: %d 层 | situs 字典: %d 层" % (len(batch), len(situs)))

    # ---- 1265 → 1253 的去向：url 补不上的层根本不进入采集 ----
    no_url = [r["layer"] for r in batch if r["layer"] not in situs]
    print("batch1 中 situs 查不到 url 的层: %d" % len(no_url))

    dirs = {}
    if os.path.isdir(OUTBASE):
        for d in os.listdir(OUTBASE):
            dirs[d] = os.path.join(OUTBASE, d)

    tasks = []
    for r in batch:
        lid = r["layer"]
        d = dirs.get(san(lid))
        tasks.append((lid, r, d))
    if a.limit:
        tasks = tasks[:a.limit]

    t0 = time.time()
    result, done = {}, 0
    with ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = {}
        for lid, r, d in tasks:
            if not d or not os.path.isdir(d):
                result[lid] = {"dir": None, "rows": 0, "parts": 0,
                               "declared": int(r["declared"] or 0), "state": r["state"],
                               "grade": r["grade"], "eff": r["eff"], "status": "no_dir"}
                continue
            futs[ex.submit(count_rows, d)] = (lid, r, d)
        for f in as_completed(futs):
            lid, r, d = futs[f]
            rows, parts = f.result()
            decl = int(r["declared"] or 0)
            status = "empty" if parts == 0 or rows == 0 else (
                "complete" if rows >= decl * 0.99 else "partial")
            result[lid] = {"dir": os.path.basename(d), "rows": rows, "parts": parts,
                           "declared": decl, "state": r["state"], "grade": r["grade"],
                           "eff": r["eff"], "status": status,
                           "ratio": round(rows / decl, 4) if decl else None}
            done += 1
            if done % 100 == 0:
                print("  … %d/%d  已用 %.0fs" % (done, len(futs), time.time() - t0), flush=True)

    # ---- 汇总 ----
    have = [v for v in result.values() if v["status"] != "no_dir"]
    cnt = {}
    for v in result.values():
        cnt[v["status"]] = cnt.get(v["status"], 0) + 1
    rows_disk = sum(v["rows"] for v in result.values())
    decl_sum = sum(v["declared"] for v in result.values())
    ledger = {}
    if os.path.exists(LEDGER):
        try:
            ledger = json.load(open(LEDGER, encoding="utf-8"))
        except Exception:
            pass

    extra = [d for d in dirs if d not in {san(x) for x in result}]

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_sec": round(time.time() - t0, 1),
        "batch_layers": len(batch),
        "batch_declared_sum": decl_sum,
        "no_url_in_situs": len(no_url),
        "no_url_layers": no_url,
        "status_count": cnt,
        "rows_on_disk": rows_disk,
        "ledger_fetched": ledger.get("fetched"),
        "ledger_done_layers": ledger.get("done_layers"),
        "ledger_vs_disk_diff": (ledger.get("fetched") or 0) - rows_disk,
        "dirs_on_disk": len(dirs),
        "dirs_not_in_batch": len(extra),
        "gap_rows": decl_sum - rows_disk,
    }
    doc = {"summary": summary, "layers": result, "dirs_not_in_batch": extra[:200]}
    json.dump(doc, open(AUDIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 人读报表 ----
    print("\n" + "=" * 62)
    print("P2 审计结果")
    print("=" * 62)
    print("batch1 层数            %d（其中 situs 无 url：%d）" % (len(batch), len(no_url)))
    print("declared 合计          %s 行" % format(decl_sum, ","))
    print("磁盘实采行数           %s 行" % format(rows_disk, ","))
    print("缺口                   %s 行" % format(summary["gap_rows"], ","))
    print("-" * 62)
    print("状态分布               %s" % cnt)
    print("磁盘目录数             %d（不在 batch1 内：%d）" % (len(dirs), len(extra)))
    print("-" * 62)
    print("账本 fetched           %s" % format(summary["ledger_fetched"] or 0, ","))
    print("账本 done_layers       %s" % summary["ledger_done_layers"])
    print("账本 − 磁盘            %s 行  ← 正数=账本虚高" % format(summary["ledger_vs_disk_diff"], ","))
    print("=" * 62)

    partial = sorted([(k, v) for k, v in result.items() if v["status"] in ("partial", "empty")],
                     key=lambda x: -(x[1]["declared"] - x[1]["rows"]))[:15]
    if partial:
        print("\n缺口最大的 15 个残缺层：")
        for k, v in partial:
            print("  %-58s %s/%s (%.1f%%)  %s" % (
                k[:58], format(v["rows"], ","), format(v["declared"], ","),
                (v["ratio"] or 0) * 100, v["status"]))
    nodir = sorted([(k, v) for k, v in result.items() if v["status"] == "no_dir"],
                   key=lambda x: -x[1]["declared"])
    if nodir:
        print("\n%d 个无目录的层（declared 合计 %s）：" % (
            len(nodir), format(sum(v["declared"] for _, v in nodir), ",")))
        for k, v in nodir[:25]:
            print("  %-58s %s" % (k[:58], format(v["declared"], ",")))
        if len(nodir) > 25:
            print("  … 还有 %d 个" % (len(nodir) - 25))
    print("\n已写出 %s" % AUDIT)


if __name__ == "__main__":
    sys.exit(main())
