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
    """分档表 → 以 (url, dialect_id) 为主键（layer_id 不唯一，17,168 行只 1,523 个不同值，按它会串层）。

    返回 {"pairs": {(url, dialect_id): row}, "by_url": {url: [dialect_id, ...]}}。
    url 为空的行（417 行）不入表：避免 "" 键把无 url 的源全部染上同一个 tier。
    """
    p = os.path.join(ROOT, cfg["repo"]["tiers"])
    out = {"pairs": {}, "by_url": {}, "path": os.path.relpath(p, ROOT), "rows": 0, "skipped_no_url": 0}
    if not os.path.isfile(p):
        print(f"WARN tier 表缺失：{p} → 全部记 unrated", flush=True)
        return out
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out["rows"] += 1
            url, did = (r.get("url") or "").strip(), (r.get("dialect_id") or "").strip()
            if not url:
                out["skipped_no_url"] += 1
                continue
            out["pairs"][(url, did)] = r
            out["by_url"].setdefault(url, []).append(did)
    return out


def tier_for(url: str, tiers: dict):
    """按 (url, dialect_id) 取实测档位 → (tier, tier_basis, ambiguous)。

    同一 url 出现多个 dialect_id 时不做静默合并：取档位最好的一行，但把 ambiguous 记进统计。
    """
    dids = tiers["by_url"].get(url) or []
    if not dids:
        return "unrated", "", False
    rows = [tiers["pairs"][(url, d)] for d in dids if (url, d) in tiers["pairs"]]
    rank = {"tier1": 1, "tier2": 2, "tier3": 3}
    best = min(rows, key=lambda r: rank.get(r.get("tier") or "", 9))
    return (best.get("tier") or "unrated"), f"{url}|{best.get('dialect_id') or ''}", len(rows) > 1


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
            tier, basis, amb = tier_for(raw.get("source_ref_url") or "", tiers)
            if amb:
                (cnt or {}).setdefault("ambiguous", 0)
                cnt["ambiguous"] += 1
            yield rec, tier, basis, os.path.basename(f)


def write_tier_moves(cfg, states, outdir) -> dict:
    """逐层挪动表：strict（第 5 步）→ relax（第 7 步分档），键 = (url, dialect_id)。

    只列 config 里的州；行数/层数必须能对上「DE 3 / NH 7 / IA 10」这类事实，对不上就是 join 口径错了。
    """
    rel = load_tiers({"repo": {"tiers": cfg["repo"]["tiers"]}})
    strict_path = cfg["repo"].get("tiers_strict") or ""
    out = {"strict_table": strict_path, "relax_table": cfg["repo"]["tiers"], "rows": 0, "by_state": {}}
    if not strict_path or not os.path.isfile(os.path.join(ROOT, strict_path)):
        out["note"] = "tiers_strict 缺失 → 无法做挪动表（unavailable）"
        return out
    strict = load_tiers({"repo": {"tiers": strict_path}})
    rows = []
    for (url, did), r in rel["pairs"].items():
        st = r.get("state") or ""
        if states and st not in states:
            continue
        before = (strict["pairs"].get((url, did)) or {}).get("tier") or ""
        after = r.get("tier") or ""
        if before == after:
            continue
        rows.append({"layer_id": r.get("layer_id") or "", "url": url, "dialect_id": did, "state": st,
                     "rows_n": int(float(r.get("rows_n") or r.get("coverage_rows") or 0)),
                     "tier_before": before, "tier_after": after})
    rows.sort(key=lambda x: (x["state"], -x["rows_n"], x["url"]))
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "tier-moves.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer_id", "url", "dialect_id", "state", "rows_n",
                                          "tier_before", "tier_after"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        b = out["by_state"].setdefault(r["state"], {"layers": 0, "rows_n": 0, "transitions": {}})
        b["layers"] += 1
        b["rows_n"] += r["rows_n"]
        k = f"{r['tier_before']}->{r['tier_after']}"
        b["transitions"][k] = b["transitions"].get(k, 0) + 1
    out["rows"] = len(rows)
    return out


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
        for rec, tier, basis, fname in iter_source_files(src, spec, cfg, tiers, street_sink, cnt):
            if rec["state"] and rec["state"] != state:       # 源里混了别的州（例：Overture 的 MD 行）
                fus.stats["out_of_state"] += 1
                continue
            fus.add(rec, tier, basis)
            n += 1
        in_rows[src["id"]] = n or cnt["range"]
        stats["sources"].append({"id": src["id"], "family": src["family"], "dialect": spec["id"],
                                 "dialect_origin": spec.get("origin"), "adapter": spec.get("adapter"),
                                 "files": len(files), "rows_in": n or cnt["range"],
                                 "tier_basis_ambiguous_rows": cnt.get("ambiguous", 0),
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
    if sums["s_with_pos_estimated"]:
        raise AssertionError(f"[{state}] 估算位置进了 S 级：s_with_pos_estimated="
                             f"{sums['s_with_pos_estimated']}（pos_estimated=true 不许 grade=S）")
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
    if state == "NH":
        from engine.crosscheck import nh_crosscheck
        stats["crosscheck"] = nh_crosscheck(fus, fdir, cfg=cfg)
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
    tier_moves = write_tier_moves(cfg, cfg["states"], outdir)
    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": os.path.relpath(a.config, ROOT),
        "tier_tables": {"relax": {"path": tiers["path"], "rows": tiers["rows"],
                                  "skipped_no_url": tiers["skipped_no_url"],
                                  "pairs": len(tiers["pairs"]), "key": "(url,dialect_id)"},
                        "strict": {"path": cfg["repo"].get("tiers_strict") or ""}},
        "tier_moves": tier_moves,
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
