#!/usr/bin/env python3
"""Phase 0：3,709 层清单（账本口径，冻结于 2026-10-31）↔ 本地可读层 逐层对账。

只读：不下载、不写 dist、不碰 Release。唯一输出是两个新文件：
  analysis/full-inventory-20261124/local-vs-ledger-reconcile.csv
  progress.json（由 --progress 指定，默认 ./progress.json）

冻结口径：`git show f836112:collect/{04b,05b,07b}_ledger.json`（272 + 2,770 + 667 = 3,709，
与 docs/4-7-TOTAL-2026-10-31.md 一致）。注意仓内 `collect/*_ledger.json` 现盘版本已被后续
重跑覆盖（272 + 3,307 + 1,103 = 4,682），**不能**用来对 3,709。

本地侧：`dist/intake-full/layers/<layer>/`，数据文件 `{table}.{layer}.ndjson.gz`；
`ledger.json` 是 intake 自带逐层账（status/err/declared_hint/rows_total）。

匹配键依次为：① layer id 直等；② URL 直等（URL 由 10-23 `collect/layer_plan.csv`
的 layer_id→url 提供，两侧同一张表，避免 id 代际漂移误判）。
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "analysis", "full-inventory-20261124")
FREEZE = "f836112"                      # 2026-10-31 冻结提交（docs/4-7-TOTAL-2026-10-31.md 同日）
STAGES = (("04b", "collect/04b_ledger.json"), ("05b", "collect/05b_ledger.json"),
          ("07b", "collect/07b_ledger.json"))
TAG_PREFIX = {"04b": "collect-step04-", "05b": "collect-step05-", "07b": "collect-step07-"}
TABLES = ("addr", "aux_parcel", "aux_street", "aux_addr_nohouse", "reject")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
# 2026-11-20 的逐层 release 索引（3,986 层、含 assets 名单），比 dist 里那份 1,426 tag 的快照完整得多
RELEASE_INDEX = os.environ.get("RELEASE_INDEX",
                               "/data/workspace/world-map-data-33/collect/.release_index.json")


def git_show(rev_path: str) -> bytes:
    return subprocess.check_output(["git", "-C", REPO, "show", rev_path])


def load_frozen():
    rows = []
    for stage, path in STAGES:
        d = json.loads(git_show(f"{FREEZE}:{path}"))
        recs = d["records"]
        for r in recs:
            rows.append({"stage": stage, "layer": r["layer"], "status": r.get("status") or "",
                         "declared": r.get("declared"), "rows": r.get("rows"),
                         "parts": r.get("parts"), "err": (r.get("err") or "")[:120]})
    return rows


def load_plan():
    """10-23 layer_plan.csv：layer_id -> url（两侧共用的唯一 id→url 字典）。"""
    plan = {}
    with open(os.path.join(REPO, "collect", "layer_plan.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            plan[r["layer_id"]] = {"url": (r.get("url") or "").rstrip("/"), "state": r.get("state"),
                                   "svc": r.get("svc"), "geom": r.get("geom"),
                                   "title": r.get("title")}
    return plan


def scan_local():
    """逐层目录扫描：数据文件（非空）、intake ledger.json、文件名里的 layer id。"""
    base = os.path.join(DIST, "layers")
    dirs = {}
    for name in sorted(os.listdir(base)):
        p = os.path.join(base, name)
        if not os.path.isdir(p):
            continue
        files, tables, lid_from_file, total_b = [], [], None, 0
        for fn in os.listdir(p):
            fp = os.path.join(p, fn)
            try:
                sz = os.path.getsize(fp)
            except OSError:
                continue
            total_b += sz
            if fn.endswith(".ndjson.gz"):
                table, rest = fn.split(".", 1)
                lid = rest[:-len(".ndjson.gz")]
                lid_from_file = lid_from_file or lid
                if sz > 0:
                    tables.append(table)
                    files.append((fn, sz))
        led = {}
        lp = os.path.join(p, "ledger.json")
        if os.path.exists(lp):
            try:
                led = json.load(open(lp, encoding="utf-8"))
            except Exception:  # noqa: BLE001
                led = {}
        dirs[name] = {"dir": name, "data_files": len(files), "tables": tables,
                      "bytes": total_b, "readable": bool(files),
                      "lid_from_file": lid_from_file, "ledger": led}
    return dirs


def main():
    global DIST
    ap = argparse.ArgumentParser()
    ap.add_argument("--progress", default=os.path.join(REPO, "progress.json"))
    ap.add_argument("--dist", default=DIST)
    a = ap.parse_args()
    DIST = a.dist
    os.makedirs(OUTDIR, exist_ok=True)

    frozen = load_frozen()
    plan = load_plan()
    dirs = scan_local()
    snap = json.load(open(os.path.join(DIST, "release-index.json"), encoding="utf-8"))["map"]
    ridx_raw = json.load(open(RELEASE_INDEX, encoding="utf-8"))["data"]
    ridx = {}
    for stage_k, layers in ridx_raw.items():
        for lid, info in layers.items():
            ridx.setdefault(lid, []).append({"stage": stage_k, "assets": info.get("assets") or [],
                                             "complete": info.get("complete"), "tag": info.get("tag")})

    # 本地 → baseline 的两套键
    localset = set(dirs)
    local_by_url = {}
    for name, d in dirs.items():
        u = (plan.get(name) or {}).get("url") or ""
        if u:
            local_by_url[u] = name
    base_urls = {}
    for r in frozen:
        u = (plan.get(r["layer"]) or {}).get("url") or ""
        r["url"] = u
        if u:
            base_urls.setdefault(u, []).append(r["layer"])

    rows = []
    bucket = collections.Counter()
    for r in frozen:
        lid, st, url = r["layer"], r["stage"], r["url"]
        tag = TAG_PREFIX[st] + lid
        tag_in_snap = tag in snap
        snap_assets = snap.get(tag) or []
        names = [x.get("n", "") for x in snap_assets]
        idx_hits = ridx.get(lid) or []
        idx_assets = [a for h in idx_hits for a in h["assets"]]
        idx_bytes = sum(x.get("s", 0) or 0 for x in snap_assets)
        payload = [n for n in names if n.endswith(".tar.gz")]
        merged = [n for n in names if n.endswith(".parquet") or "merged" in n.lower()]
        idx_payload = [a for a in idx_assets if a.endswith(".tar.gz")]
        idx_merged = [a for a in idx_assets if a.endswith(".parquet")]
        dir_hit = lid if lid in localset else local_by_url.get(url, "")
        d = dirs.get(dir_hit) if dir_hit else None
        if d and d["readable"]:
            cls = "local_ok_readable"
            why = f"dir={d['dir']} tables={','.join(d['tables'])} data_files={d['data_files']}"
        elif d and not d["readable"]:
            lerr = (d["ledger"].get("err") or "").strip()
            cls = "local_dir_no_assets"
            why = f"dir={d['dir']} intake_status={d['ledger'].get('status')} err={lerr}"
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
        rows.append({"layer": lid, "stage": st, "status": r["status"], "url": url,
                     "tag": tag, "tag_in_snapshot": tag_in_snap,
                     "release_index_hit": bool(idx_hits),
                     "release_assets_n": len(idx_assets),
                     "release_payload_n": len(idx_payload),
                     "release_bytes_in_dist_snapshot": idx_bytes,
                     "local_dir": d["dir"] if d else "",
                     "local_readable": bool(d and d["readable"]),
                     "local_tables": ",".join(d["tables"]) if d else "",
                     "local_bytes": d["bytes"] if d else 0,
                     "ledger_declared": r["declared"], "ledger_rows": r["rows"],
                     "reconcile_class": cls, "reason": why})

    # 本地目录里不属于 3,709 基线的部分（逐类计数，供 md 用）
    base_ids = {r["layer"] for r in frozen}
    extra = [n for n in dirs if n not in base_ids and local_by_url.get((plan.get(n) or {}).get("url")) != n]
    extra_readable = [n for n in extra if dirs[n]["readable"]]

    out_csv = os.path.join(OUTDIR, "local-vs-ledger-reconcile.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # 远程未采层：survey 60,694 层减去「已采层」
    survey = json.load(open(os.path.join(REPO, "survey", "ng911", "layers.json"), encoding="utf-8"))
    survey_urls = {x["url"].rstrip("/") for x in survey}
    collected_urls = {r["url"] for r in frozen if r["url"]}
    collected_urls |= {u for u in local_by_url}
    remote_uncollected = sorted(survey_urls - collected_urls)

    readable_n = sum(1 for d in dirs.values() if d["readable"])
    prog = {
        "phase": 0,
        "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
              .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_freeze": FREEZE,
        "ledger_layers_total": len(frozen),
        "ledger_layers_by_stage": dict(collections.Counter(r["stage"] for r in frozen)),
        "dist": DIST,
        "local_dirs": len(dirs),
        "local_readable_layers": readable_n,
        "local_dirs_no_assets": len(dirs) - readable_n,
        "local_dirs_outside_baseline": len(extra),
        "local_dirs_outside_baseline_readable": len(extra_readable),
        "baseline_local_readable": len(base_ids & localset),
        "baseline_local_readable_by_url": sum(
            1 for r in rows if r["reconcile_class"] == "local_ok_readable"),
        "reconcile_class_counts": dict(bucket),
        "release_snapshot_tags": len(snap),
        "release_index_layers": len(ridx),
        "release_bytes_known_subset": sum(r["release_bytes_in_dist_snapshot"] for r in rows),
        "survey_layers": len(survey),
        "survey_distinct_urls": len(survey_urls),
        "collected_distinct_urls": len(collected_urls),
        "remote_uncollected_layers": len(remote_uncollected),
        "phase2_plan": {"layers_to_scan": readable_n, "sample_per_layer": 200},
        "phase3_plan": {"layers": len(remote_uncollected), "requests_per_layer": 2,
                        "concurrency_max": 8},
    }
    json.dump(prog, open(a.progress, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"survey_urls": sorted(survey_urls), "collected_urls": sorted(collected_urls)},
              open(os.path.join(OUTDIR, "_url_sets.json"), "w", encoding="utf-8"))
    print(json.dumps(prog, ensure_ascii=False, indent=1))
    print("wrote", out_csv, len(rows), "rows")


if __name__ == "__main__":
    sys.exit(main())
