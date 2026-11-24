#!/usr/bin/env python3
"""三州试点 runner：DE / NH / IA → 分级数据 + 统计（每行都能从产物复算）。

  python3 engine/pilot.py                 # 跑配置里的全部州
  python3 engine/pilot.py --states DE     # 只跑一个州
  python3 engine/pilot.py --dry-run       # 只体检源与方言，不出数据

产物（默认 analysis/engine-pilot-20261125/）：
  <STATE>/graded.ndjson.gz      去重后分级行（addrkey / tier / grade / lon-lat / provenance）
  <STATE>/stats.json            输入/去重/分级分布/Tier×Grade 网格
  <STATE>/tiger-streets.csv.gz  仅 DE/IA：TIGER 街段区间确认的街名键（区间不出点）
  unsupported.csv               方言/适配器不支持清单（显式、不猜）
  summary.json                  三州合并统计 + 输入文件清单 + 行数闭合
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import inlet, outlet_clean as oc  # noqa: E402
from engine.fusion import Fusion  # noqa: E402


def load_cfg(path):
    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    roots = {k: v for k, v in (cfg.get("roots") or {}).items()}
    repo = os.path.join(ROOT, "analysis")
    roots["repo"] = os.path.dirname(cfg["repo"]["samples"])       # analysis/coord-samples-.../
    cfg["_roots"] = roots
    cfg["_repo_analysis"] = repo
    return cfg


def expand(src, cfg):
    pat = src["glob"].format(**cfg["_roots"])
    return sorted(glob.glob(pat))


def load_tiers(cfg) -> dict:
    """方言层的实测档位：url → tier（来自第 5 步重跑，只读）。"""
    p = os.path.join(ROOT, cfg["repo"]["tiers"])
    out = {}
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("url"):                    # 417 层的 url 为空 → 不入表，避免 "" 键污染全体
                    out[r["url"]] = r.get("tier") or "unrated"
    else:
        print(f"WARN tier 表缺失：{p} → 全部记 unrated", flush=True)
    return out


def iter_source_files(src, spec, cfg, tiers, street_sink=None, cnt=None):
    """一个源可能有多文件；逐文件产出记录。range_only 的源（TIGER 区间）只收街名键。"""
    files = expand(src, cfg)
    for f in files:
        s = {**src, "path": f, "_ref": os.path.basename(f)}
        if src.get("range_only"):
            for raw in inlet.iterate(s, spec):
                rec = oc.clean(raw, spec, cfg["addrkey"]["include_unit"])
                (cnt or {})["range"] = (cnt or {}).get("range", 0) + 1
                if rec["street"]:
                    stt = rec["state"] or src["state"]
                    street_sink.add((stt, oc.street_key(
                        rec["street"], rec["post_type"], rec["pre_dir"], rec["post_dir"])))
            continue
        for raw in inlet.iterate(s, spec):
            rec = oc.clean(raw, spec, cfg["addrkey"]["include_unit"])
            tier = (tiers.get(raw.get("source_ref_url") or "") or "unrated")
            yield rec, tier, os.path.basename(f)


def run_state(state, cfg, registry, engine, tiers, outdir, dry=False):
    srcs = [s for s in cfg["sources"] if s["state"] == state]
    ok, bad = inlet.probe_sources(srcs, registry, engine)
    stats = {"state": state, "sources": [], "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if dry:
        return {"state": state, "supported": [s[0]["id"] for s in ok], "unsupported": bad}, []

    fdir = os.path.join(outdir, state)
    os.makedirs(fdir, exist_ok=True)
    work = os.path.join(outdir, "_work")
    os.makedirs(work, exist_ok=True)
    fus = Fusion(os.path.join(work, f"{state}.sqlite"), cfg)
    street_sink = set()
    in_rows = collections.Counter()
    for src, spec in ok:
        files = expand(src, cfg)
        t0 = time.time()
        n = 0
        cnt = {"range": 0}
        for rec, tier, fname in iter_source_files(src, spec, cfg, tiers, street_sink, cnt):
            if rec["state"] and rec["state"] != state:       # 源里混了别的州（例：Overture 的 MD 行）
                fus.stats["out_of_state"] += 1
                continue
            fus.add(rec, tier)
            n += 1
        in_rows[src["id"]] = n or cnt["range"]
        stats["sources"].append({"id": src["id"], "family": src["family"], "dialect": spec["id"],
                                 "dialect_origin": spec.get("origin"), "adapter": spec.get("adapter"),
                                 "files": len(files), "rows_in": n or cnt["range"],
                                 "range_only": bool(src.get("range_only")),
                                 "secs": round(time.time() - t0, 1)})
        print(f"[{state}] {src['id']:12s} files={len(files):3d} rows={(n or cnt['range']):8d} "
              f"{round(time.time() - t0, 1)}s", flush=True)
        fus.commit()
    fus.commit()
    fus.stats["in_rows"] = sum(in_rows.values())
    n_out = fus.export(os.path.join(fdir, "graded"), state=state, shard_mb=cfg.get("export_shard_mb", 40))
    sums = fus.summaries(state=state)
    tiered = collections.Counter()
    for r in fus.db.execute("SELECT tier, COUNT(*) FROM fused WHERE state=? GROUP BY tier", (state,)):
        tiered[r[0]] = r[1]
    stats.update({"rows_in": fus.stats["in_rows"], "deduped_rows": n_out,
                  "dup_rows": fus.stats["dup"], "coord_conflict": fus.stats["conflict"],
                  "unkeyed_rows": fus.stats["unkeyed"], "dropped_low_grade": fus.stats["low_grade"],
                  "dropped_out_of_state": fus.stats["out_of_state"],
                  "by_tier": dict(tiered), **sums,
                  "tiger_street_keys": len(street_sink),
                  "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    if street_sink:
        with gzip.open(os.path.join(fdir, "tiger-streets.csv.gz"), "wt", encoding="utf-8") as fh:
            fh.write("state,street_key\n")
            for st, sk in sorted(street_sink):
                fh.write(f"{st},{sk}\n")
    with open(os.path.join(fdir, "stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=1)
    fus.db.close()
    return stats, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "engine", "config", "pilot.yaml"))
    ap.add_argument("--states", default="")
    ap.add_argument("--outdir", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = load_cfg(a.config)
    outdir = a.outdir or os.path.join(ROOT, cfg["outdir"])
    os.makedirs(outdir, exist_ok=True)
    states = [s.strip() for s in a.states.split(",") if s.strip()] or cfg["states"]
    registry, engine = inlet.load_registry(), inlet.load_engine_dialects()
    tiers = load_tiers(cfg)
    all_stats, unsupported = [], []
    for st in states:
        st_stats, bad = run_state(st, cfg, registry, engine, tiers, outdir, dry=a.dry_run)
        all_stats.append(st_stats)
        unsupported += bad
    with open(os.path.join(outdir, "unsupported.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["source_id", "family", "dialect", "path", "reason"])
        w.writeheader()
        w.writerows(unsupported)
    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": os.path.relpath(a.config, ROOT),
        "addrkey": {"version": oc.ADDRKEY_VERSION, "prefix": oc.ADDRKEY_PREFIX,
                    "include_unit": cfg["addrkey"]["include_unit"], "hash": cfg["addrkey"]["hash"]},
        "dialects": {"registry": sorted(registry), "engine": sorted(engine)},
        "grades": cfg["grades"], "priority": cfg["priority"], "tier_rank": cfg["tier_rank"],
        "states": all_stats,
        "totals": {
            "rows_in": sum(s.get("rows_in", 0) for s in all_stats),
            "deduped_rows": sum(s.get("deduped_rows", 0) for s in all_stats),
            "dup_rows": sum(s.get("dup_rows", 0) for s in all_stats),
            "unkeyed_rows": sum(s.get("unkeyed_rows", 0) for s in all_stats),
            "coord_conflict": sum(s.get("coord_conflict", 0) for s in all_stats),
            "dropped_low_grade": sum(s.get("dropped_low_grade", 0) for s in all_stats),
            "dropped_out_of_state": sum(s.get("dropped_out_of_state", 0) for s in all_stats),
        },
        "unsupported": len(unsupported),
    }
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary["totals"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
