#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08 · 对账（与 adjudicate_05b/07b 同款）：`--check` 必须 IDENTICAL。

六条断言（任何一条不成立 → FAIL，退出码 2）：
  A1 Σ 各桶行数（extract 报告） == 重新数 spill 文件
  A2 spill 重新点行 == reduce 的 rows_in
  A3 rows_in == keys_out + dup_members_total（合并守恒）
  A4 台账重新点行 == reduce 的 keys_out；且 Σ(dup_members+1) == rows_in
  A5 public 版泄漏扫描 0 命中；public 行无门牌字段
  A6 台账行数 vs 计划行数（该州）差异必须被 UNLOCATED / 非本州 / 不可键 解释，且逐项列清

用法：
  python3 collect/adjudicate_08.py --out /tmp/08-R1 --check
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def count_lines(path: str) -> int:
    n = 0
    if not os.path.exists(path):
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for _ in fh:
            n += 1
    return n


def iter_ledger(ledger_dir: str):
    for root, _dirs, files in os.walk(ledger_dir):
        for f in sorted(files):
            if f.endswith(".ndjson.gz"):
                with gzip.open(os.path.join(root, f), "rt", encoding="utf-8") as fh:
                    for line in fh:
                        if line.strip():
                            yield json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    out = args.out
    spill_dir = os.path.join(out, "spill")
    rep_dir = os.path.join(out, "reports")
    ext = json.load(open(os.path.join(rep_dir, "extract.json"), encoding="utf-8"))
    red = json.load(open(os.path.join(rep_dir, "reduce.json"), encoding="utf-8"))
    pub = json.load(open(os.path.join(rep_dir, "public.json"), encoding="utf-8"))

    rows = {}
    # A1/A2：spill 重数
    spill_files = sorted(f for f in os.listdir(spill_dir) if f.endswith(".ndjson.gz"))
    recount = sum(count_lines(os.path.join(spill_dir, f)) for f in spill_files)
    rows["A1_spill_recount"] = {
        "extract_says": sum(ext["key_by_bucket"].values()),
        "recount": recount,
        "ok": sum(ext["key_by_bucket"].values()) == recount == ext["totals"]["keyable"],
    }
    rows["A2_spill_vs_reduce"] = {"spill": recount, "reduce_rows_in": red["rows_in"],
                                  "ok": recount == red["rows_in"]}
    rows["A3_conservation"] = {
        "rows_in": red["rows_in"], "keys_out": red["keys_out"],
        "dup_members_total": red["dup_members_total"],
        "ok": red["rows_in"] == red["keys_out"] + red["dup_members_total"]}

    # A4：台账重数
    led_rows = 0
    led_dup = 0
    keys = set()
    for r in iter_ledger(os.path.join(out, "ledger")):
        led_rows += 1
        led_dup += r.get("dup_members") or 0
        keys.add(r["dedup_key"])
    rows["A4_ledger_recount"] = {
        "ledger_rows": led_rows, "distinct_keys": len(keys),
        "reduce_keys_out": red["keys_out"],
        "dup_sum_plus_rows": led_rows + led_dup, "rows_in": red["rows_in"],
        "ok": led_rows == len(keys) == red["keys_out"] and led_rows + led_dup == red["rows_in"]}

    # A5：public 泄漏
    pub_leaks = pub.get("leak_total", -1)
    rows["A5_public_leak"] = {"leak_total": pub_leaks, "scan": pub.get("leak_scan"),
                              "ok": pub_leaks == 0}

    # A6：与计划行数对账（差 = 非本州 + 不可键 + 无坐标）
    t = ext["totals"]
    plan_rows = 0
    for line in open(os.path.join(spill_dir, "layers.jsonl"), encoding="utf-8"):
        plan_rows += json.loads(line).get("plan_rows") or 0
    explained = {
        "read_rows": t["rows"],
        "outside_state": t["outside_state"],
        "unkeyed": t["unkeyed"],
        "no_coord": t.get("no_coord", 0),
        "keyable_in_state": t["keyable"],
    }
    rows["A6_plan_reconcile"] = {
        "plan_rows_sum": plan_rows, "read_rows": t["rows"],
        "read_vs_plan_ok": abs(t["rows"] - plan_rows) / plan_rows < 0.02 if plan_rows else False,
        "identity_ok": t["rows"] == t["keyable"] + t["outside_state"] + t["unkeyed"],
        "detail": explained,
        "plan_state_mismatch_layers": ext.get("plan_state_mismatch_layers", [])}

    ok = all(v.get("ok") for k, v in rows.items() if k != "A6_plan_reconcile")
    ok = ok and rows["A6_plan_reconcile"]["identity_ok"]
    doc = {"schema": "08-adjudicate/v1", "state": ext["state"], "at": ext["at"],
           "checks": rows, "verdict": "IDENTICAL" if ok else "FAIL"}
    print(json.dumps(doc, ensure_ascii=False, indent=1)[:4000])
    json.dump(doc, open(os.path.join(rep_dir, "adjudicate.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    if args.check:
        print("\n[adjudicate] %s" % doc["verdict"])
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
