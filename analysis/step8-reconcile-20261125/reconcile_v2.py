#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · D：账实对账 v2（复制 `analysis/full_inventory_reconcile.py` 的同一逻辑 + `--outdir`）。

与 v1 的唯一差别（都写在 REPORT §D 里）：
  ① `scan_local()` 认得两种层目录形态：
       - intake 分表：`addr|aux_parcel|aux_street|aux_addr_nohouse|reject.<layer>.ndjson.gz`（v1 的形态）
       - 本轮拉齐的载荷原样：`part-uNNNNN-NNN.ndjson.gz` + `ledger.json`（form=payload-part-passthrough）
     后者判 `local_ok_payload_present`（**可读、行数可核，但没分表**），绝不冒充 `local_ok_readable`。
  ② 输出目录可指定（默认本目录），**绝不写 analysis/full-inventory-20261124/**。

用法：python3 analysis/step8-reconcile-20261125/reconcile_v2.py
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REPO = ROOT
OUTDIR = HERE
FREEZE = "f836112"
STAGES = (("04b", "collect/04b_ledger.json"), ("05b", "collect/05b_ledger.json"),
          ("07b", "collect/07b_ledger.json"))
TAG_PREFIX = {"04b": "collect-step04-", "05b": "collect-step05-", "07b": "collect-step07-"}
TABLES = ("addr", "aux_parcel", "aux_street", "aux_addr_nohouse", "reject")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
RELEASE_INDEX = os.environ.get("RELEASE_INDEX",
                               "/data/workspace/world-map-data-33/collect/.release_index.json")
COLS = ["layer", "stage", "status", "url", "tag", "tag_in_snapshot", "release_index_hit",
        "release_assets_n", "release_payload_n", "release_bytes_in_dist_snapshot",
        "local_dir", "local_readable", "local_tables", "local_bytes",
        "ledger_declared", "ledger_rows", "reconcile_class", "reason"]


def git_show(rev_path):
    return subprocess.check_output(["git", "-C", REPO, "show", rev_path])


def load_frozen():
    rows = []
    for stage, path in STAGES:
        d = json.loads(git_show(f"{FREEZE}:{path}"))
        for r in d["records"]:
            rows.append({"stage": stage, "layer": r["layer"], "status": r.get("status") or "",
                         "declared": r.get("declared"), "rows": r.get("rows"), "err": (r.get("err") or "")[:120]})
    return rows


def load_plan():
    plan = {}
    with open(os.path.join(REPO, "collect", "layer_plan.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            plan[r["layer_id"]] = {"url": (r.get("url") or "").rstrip("/"), "state": r.get("state")}
    return plan


def scan_local(dist):
    """逐层目录：分表形态（intake）与载荷原样形态（本轮）分开算。"""
    base = os.path.join(dist, "layers")
    dirs = {}
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name)
        if not os.path.isdir(p):
            continue
        files, tables, parts, total_b, lid_from_file = [], [], [], 0, None
        for fn in os.listdir(p):
            fp = os.path.join(p, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            total_b += sz
            if fn.startswith("part-u") and fn.endswith(".ndjson.gz"):
                if sz > 0:
                    parts.append(fn)
                    files.append((fn, sz))
                continue
            if fn.endswith(".ndjson.gz"):
                table, rest = fn.split(".", 1)
                lid_from_file = lid_from_file or rest[:-len(".ndjson.gz")]
                if sz > 0:
                    tables.append(table)
                    files.append((fn, sz))
        led = {}
        lp = os.path.join(p, "ledger.json")
        if os.path.exists(lp):
            try:
                led = json.load(open(lp, encoding="utf-8"))
            except Exception:                                        # noqa: BLE001
                led = {}
        dirs[name] = {"dir": name, "data_files": len(files), "tables": tables, "parts": parts,
                      "bytes": total_b, "readable": bool(files) and bool(tables),
                      # 载荷形态要 **ledger.json 在 + part 数达标** 才算拉齐（半截目录不算，
                      # 否则「拉了一半」会被当成「已补齐」——这是最容易自欺的一步）
                      "payload_ok": bool(parts) and bool(led) and led.get("status") == "ok"
                                    and int(led.get("part_files") or 0) == len(parts),
                      "lid_from_file": lid_from_file, "ledger": led}
    return dirs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=OUTDIR)
    ap.add_argument("--dist", default=DIST)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    frozen, plan, dirs = load_frozen(), load_plan(), scan_local(a.dist)
    snap = json.load(open(os.path.join(a.dist, "release-index.json"), encoding="utf-8"))["map"]
    ridx_raw = json.load(open(RELEASE_INDEX, encoding="utf-8"))["data"]
    ridx = {}
    for stage_k, layers in ridx_raw.items():
        for lid, info in layers.items():
            ridx.setdefault(lid, []).append({"stage": stage_k, "assets": info.get("assets") or [],
                                             "complete": info.get("complete"), "tag": info.get("tag")})
    localset = set(dirs)
    local_by_url = {}
    for name, d in dirs.items():
        u = (plan.get(name) or {}).get("url") or ""
        if u:
            local_by_url[u] = name
    rows, bucket = [], collections.Counter()
    for r in frozen:
        lid, st = r["layer"], r["stage"]
        url = (plan.get(lid) or {}).get("url") or ""
        tag = TAG_PREFIX[st] + lid
        tag_in_snap = tag in snap
        snap_assets = snap.get(tag) or []
        names = [x.get("n", "") for x in snap_assets]
        idx_hits = ridx.get(lid) or []
        idx_assets = [x for h in idx_hits for x in h["assets"]]
        idx_bytes = sum(x.get("s", 0) or 0 for x in snap_assets)
        payload = [n for n in names if n.endswith(".tar.gz")]
        merged = [n for n in names if n.endswith(".parquet") or "merged" in n.lower()]
        idx_payload = [x for x in idx_assets if x.endswith(".tar.gz")]
        idx_merged = [x for x in idx_assets if x.endswith(".parquet")]
        dir_hit = lid if lid in localset else local_by_url.get(url, "")
        d = dirs.get(dir_hit) if dir_hit else None
        if d and d["readable"]:
            cls = "local_ok_readable"
            why = f"dir={d['dir']} tables={','.join(d['tables'])} data_files={d['data_files']}"
        elif d and d["payload_ok"]:
            # 本轮拉齐：part 包原样落盘（可读、行数可核），但没走 intake 分表
            led = d["ledger"] or {}
            cls = "local_ok_payload_present"
            why = (f"dir={d['dir']} form=payload-part-passthrough parts={len(d['parts'])} "
                   f"rows_total={led.get('rows_total')} bytes={d['bytes']}（未分表：该层无 field-map 条目）")
        elif d and not d["readable"]:
            cls = "local_dir_no_assets"
            why = f"dir={d['dir']} intake_status={(d['ledger'] or {}).get('status')}"
        elif idx_payload:
            cls = "local_absent_assets_exist_not_downloaded"
            why = (f"2026-11-20 release 索引有该层 {len(idx_payload)} 个载荷资产"
                   f"（{idx_payload[0][:60]}…），dist 无该层目录 → 只有 Release、没下到本地")
        elif idx_merged and not idx_payload:
            cls = "local_absent_merged_only"
            why = f"release 索引只有 merged/parquet 资产：{','.join(idx_merged)[:80]}"
        elif idx_hits and not idx_assets:
            cls = "local_absent_release_empty"
            why = f"release 索引有 tag={idx_hits[0]['tag']} 但 0 资产（账本 status={r['status']}）"
        elif tag_in_snap and payload:
            cls = "local_absent_tag_ok_not_ingested"
            why = f"tag={tag} 有 {len(payload)} 个载荷资产（仅见于 dist 快照），dist 无该层目录"
        elif tag_in_snap:
            cls = "local_absent_empty_release"
            why = f"tag={tag} 在 dist 快照里但 0 载荷资产（账本 status={r['status']}）"
        else:
            cls = "local_absent_upstream_no_assets"
            why = (f"两份本地索引（11-20 逐层索引 {len(ridx)} 层 / dist 快照 {len(snap)} tag）都查不到该层"
                   f"，账本 status={r['status']} err={r['err'][:60]} → 上游无资产")
        bucket[cls] += 1
        rows.append({"layer": lid, "stage": st, "status": r["status"], "url": url, "tag": tag,
                     "tag_in_snapshot": tag_in_snap, "release_index_hit": bool(idx_hits),
                     "release_assets_n": len(idx_assets), "release_payload_n": len(idx_payload),
                     "release_bytes_in_dist_snapshot": idx_bytes,
                     "local_dir": d["dir"] if d else "", "local_readable": bool(d and d["readable"]),
                     "local_tables": ",".join((d["tables"] if d else []) or []),
                     "local_bytes": d["bytes"] if d else 0,
                     "ledger_declared": r["declared"], "ledger_rows": r["rows"],
                     "reconcile_class": cls, "reason": why})
    out_csv = os.path.join(a.outdir, "local-vs-ledger-reconcile-v2.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    # —— before/after 四类对照 ——
    v1 = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
    before = collections.Counter(x["reconcile_class"] for x in csv.DictReader(open(v1, encoding="utf-8")))
    after = bucket
    moves = []
    b1 = {x["layer"]: x["reconcile_class"] for x in csv.DictReader(open(v1, encoding="utf-8"))}
    for r in rows:
        if b1.get(r["layer"]) != r["reconcile_class"]:
            moves.append(r)
    mv_csv = os.path.join(a.outdir, "reconcile-moves.csv")
    with open(mv_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["layer", "stage", "class_before", "class_after", "reason"])
        w.writeheader()
        for r in moves:
            w.writerow({"layer": r["layer"], "stage": r["stage"],
                        "class_before": b1.get(r["layer"], ""), "class_after": r["reconcile_class"],
                        "reason": r["reason"][:200]})
    classes = sorted(set(before) | set(after))
    with open(os.path.join(a.outdir, "reconcile-before-after.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["reconcile_class", "before", "after", "net", "move_list"])
        w.writeheader()
        for c in classes:
            w.writerow({"reconcile_class": c, "before": before.get(c, 0), "after": after.get(c, 0),
                        "net": after.get(c, 0) - before.get(c, 0),
                        "move_list": os.path.basename(mv_csv) if before.get(c) != after.get(c) else ""})
    print(json.dumps({"before": dict(before), "after": dict(after), "moves": len(moves),
                      "rows": len(rows), "out": out_csv}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
