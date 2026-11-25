#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 9 步 runner：3,550 层 → 11 列 ndjson（gzip），每 500 层打一个 fieldmap-part%03d.tar.gz。

只读 `dist/intake-full/layers/`；只写 `dist/rows/` 与 `dist/tar/`；`dist/intake-full` 一个字节都不动。
用法：
  python3 map_layers.py --probe 10            # 体检（前 N 大的层，写 dist/probe.json）
  python3 map_layers.py --all --shard 500 --workers 6
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
TALLY = os.path.join(ROOT, "analysis", "step8-reconcile-20261125", "final-tally.csv")
LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
ROWS = os.path.join(DIST, "rows")
TARS = os.path.join(DIST, "tar")
MIN_FREE = 3 * 1024 ** 3

_G = {}


def _init():
    cfg = C.load_pilot_cfg()
    org2dial, meta, fb = C.load_registry_orgs()
    _G["m"] = C.LayerMapper(cfg, org2dial, meta, C.load_tier_map())
    _G["cfg"] = cfg


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def map_layer(job):
    """单层：读 part 包 → 11 列 gz。返回统计（喂 layer-coverage.csv / 心跳）。"""
    lid, url, cls, in_bytes, tier_hint = job
    if not _G:
        _init()
    m = _G["m"]
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz")) \
        if os.path.isdir(d) else []
    st = {"layer": lid, "url": url, "class": cls, "part_files": len(parts), "in_bytes": in_bytes,
          "in_rows": 0, "mapped": 0, "dropped_below_c": 0, "parse_error": 0, "diff": 0,
          "zip5_ok": 0, "zip5_invalid": 0, "zip5_missing": 0,
          "state_ok": 0, "state_invalid": 0, "coord_ok": 0, "coord_out_of_range": 0, "coord_missing": 0,
          "number_ok": 0, "street_ok": 0, "city_ok": 0,
          "grade": collections.Counter(), "tier": collections.Counter(),
          "out_bytes": 0, "out_file": ""}
    if not parts:
        st["reason"] = "upstream_no_payload"
        st["dialect_id"], st["dialect_origin"], st["a_pool_eligible"] = "minimal_safe", "fallback", False
        return st
    dialect, origin, apool = m.dialect_for(url)
    m.begin_layer(url)          # 逐层重置字段名缓存（不调会把上一层的 raw 键名带到本层）
    tier_hint = m.tier_for(url)
    os.makedirs(ROWS, exist_ok=True)
    op = os.path.join(ROWS, lid + ".ndjson.gz")
    with gzip.open(op, "wb", compresslevel=1) as out:
        for fn in parts:
            try:
                with gzip.open(os.path.join(d, fn), "rt", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if not line.strip():
                            continue
                        st["in_rows"] += 1
                        try:
                            row = json.loads(line)
                        except json.JSONDecodeError:
                            st["parse_error"] += 1
                            continue
                        if not isinstance(row, dict):
                            st["parse_error"] += 1
                            continue
                        rec, reason, full = m.map_row(row)
                        if reason == "below_c":
                            st["dropped_below_c"] += 1
                        elif rec is None:
                            st["parse_error"] += 1
                        else:
                            tier = tier_hint or "unrated"
                            rec["tier"] = tier
                            out.write((json.dumps({k: rec[k] for k in C.FIELDS}, ensure_ascii=False,
                                                  separators=(",", ":")) + "\n").encode("utf-8"))
                            st["mapped"] += 1
                            st["grade"][rec["grade"]] += 1
                            st["tier"][tier] += 1
                            st["number_ok"] += bool(rec["house_number"])
                            st["street_ok"] += bool(rec["street_name"])
                            st["city_ok"] += bool(rec["city"])
                            if rec["zip5"]:
                                st["zip5_ok"] += 1
                            elif full["_zreason"] == "invalid":
                                st["zip5_invalid"] += 1
                            else:
                                st["zip5_missing"] += 1
                            if rec["state"]:
                                st["state_ok"] += 1
                            else:
                                st["state_invalid"] += 1
                            if rec["lat"] is not None:
                                st["coord_ok"] += 1
                            elif full["_creason"] == "out_of_range":
                                st["coord_out_of_range"] += 1
                            else:
                                st["coord_missing"] += 1
            except (OSError, EOFError) as e:
                st["parse_error"] += 1
                st.setdefault("errors", []).append(f"{fn}:{type(e).__name__}")
    st["out_bytes"] = os.path.getsize(op)
    st["out_file"] = os.path.basename(op)
    st["dialect_id"], st["dialect_origin"], st["a_pool_eligible"] = dialect, origin, apool
    st["diff"] = st["in_rows"] - st["mapped"] - st["dropped_below_c"] - st["parse_error"]
    st["grade"] = dict(st["grade"]); st["tier"] = dict(st["tier"])
    if st["mapped"] == 0:
        st["reason"] = "zero_rows" if st["in_rows"] == 0 else "grade_below_C"
        try:
            os.unlink(op)
        except OSError:
            pass
        st["out_bytes"] = 0
        st["out_file"] = ""
    elif st["diff"] != 0:
        st["reason"] = "parse_error"
    return st


def load_jobs():
    inv = {}
    with open(INV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inv.setdefault(r["layer"], r)
    jobs = []
    with open(TALLY, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            i = inv.get(r["layer"]) or {}
            jobs.append((r["layer"], i.get("url") or "", r["class"], int(r["bytes"] or 0), ""))
    return jobs


def write_tar(shard_idx, rows_files):
    os.makedirs(TARS, exist_ok=True)
    p = os.path.join(TARS, f"fieldmap-part{shard_idx:03d}.tar.gz")
    members = [os.path.relpath(f, ROWS) for f in rows_files]
    subprocess.run(["tar", "-czf", p, "-C", ROWS] + members, check=True)
    for f in rows_files:
        os.unlink(f)
    return p, os.path.getsize(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=int, default=0)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--shard", type=int, default=500)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--resume", action="store_true", help="跳过 layer-coverage.csv 里已记录的层")
    ap.add_argument("--only-file", default="", help="只跑这个文件的层（一行一个 layer_id）")
    ap.add_argument("--out-csv", default="", help="把覆盖表写到这个路径（默认 layer-coverage.csv）")
    a = ap.parse_args()
    jobs = load_jobs()
    if a.only_file and os.path.isfile(a.only_file):
        keep = {x.strip() for x in open(a.only_file, encoding="utf-8") if x.strip()}
        jobs = [j for j in jobs if j[0] in keep]
    if a.probe:
        jobs.sort(key=lambda j: -j[3])
        jobs = jobs[:a.probe]
    else:
        # 最大的 2 层先跑（长尾最长，先起跑；同时便于 60 分钟内出 HEALTH 体检），其余小层优先
        jobs.sort(key=lambda j: -j[3])
        head, tail = jobs[:2], jobs[2:]
        tail.sort(key=lambda j: j[3])
        jobs = head + tail
    os.makedirs(ROWS, exist_ok=True)
    os.makedirs(TARS, exist_ok=True)
    out_csv = a.out_csv or os.path.join(HERE, "layer-coverage.csv")
    done_before = []
    if a.resume and os.path.isfile(out_csv):
        with open(out_csv, encoding="utf-8") as fh:
            done_before = list(csv.DictReader(fh))
        _done = {r["layer"] for r in done_before}
        jobs = [j for j in jobs if j[0] not in _done]
        shard_idx = len([f for f in os.listdir(TARS) if f.endswith(".tar.gz")])
        print(f"[resume] 已记录 {len(_done)} 层，待跑 {len(jobs)} 层，分片从 {shard_idx:03d} 续", flush=True)
    mode = "a" if (a.resume and done_before) else "w"
    cols = ["layer", "dialect_id", "dialect_origin", "a_pool_eligible", "class", "part_files",
            "in_rows", "mapped", "dropped_below_c", "parse_error", "diff", "in_bytes", "out_bytes",
            "out_file", "grade_S", "grade_A", "grade_B", "zip5_ok", "zip5_invalid", "zip5_missing",
            "state_ok", "state_invalid", "coord_ok", "coord_out_of_range", "coord_missing",
            "number_ok", "street_ok", "city_ok", "tier", "reason"]
    results, pending, shard, shard_idx = [], [], 0, 0
    t0 = time.time()
    done = 0
    cov_path = os.path.join(HERE, "progress.json")
    with open(out_csv, mode, newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        if mode == "w":
            w.writeheader()
        with mp.Pool(a.workers, initializer=_init) as pool:
            for st in pool.imap_unordered(map_layer, jobs, chunksize=4):
                done += 1
                results.append(st)
                g = st.get("grade") or {}
                row = {k: st.get(k, "") for k in cols}
                row.update({"grade_S": g.get("S", 0), "grade_A": g.get("A", 0), "grade_B": g.get("B", 0),
                            "tier": json.dumps(st.get("tier") or {}, ensure_ascii=False),
                            "a_pool_eligible": st.get("a_pool_eligible")})
                w.writerow(row)
                fh.flush()
                if st.get("out_file") and (st.get("out_bytes") or 0) > 0:
                    pending.append(os.path.join(ROWS, st["out_file"]))
                if len(pending) >= a.shard:
                    p, sz = write_tar(shard_idx, pending)
                    pending = []
                    shard_idx += 1
                    print(f"[shard] {p} {sz/2**20:.1f}MB layers={len(pending)} free={free_gb():.1f}G "
                          f"done={done}/{len(jobs)} {time.time()-t0:.0f}s", flush=True)
                if done % 50 == 0:
                    json.dump({"done": done, "total": len(jobs), "free_gb": round(free_gb(), 1),
                               "elapsed_s": round(time.time() - t0, 1),
                               "mapped": sum(1 for x in results if (x.get("mapped") or 0) > 0),
                               "out_bytes": sum(x.get("out_bytes") or 0 for x in results)},
                              open(cov_path, "w"), ensure_ascii=False)
                    print(f"[{done}/{len(jobs)}] free={free_gb():.1f}G {time.time()-t0:.0f}s", flush=True)
                if free_gb() < 3:
                    print("[stop] free_gb<3 磁盘护栏", flush=True)
                    pool.terminate()
                    break
    if pending:
        p, sz = write_tar(shard_idx, pending)
        print(f"[shard] {p} {sz/2**20:.1f}MB", flush=True)
    json.dump({"layers": len(results), "out_bytes": sum(x.get("out_bytes") or 0 for x in results),
               "in_bytes": sum(x.get("in_bytes") or 0 for x in results),
               "elapsed_s": round(time.time() - t0, 1), "free_gb": round(free_gb(), 1),
               "shards": shard_idx + (1 if pending else 0)},
              open(os.path.join(DIST, "run-summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"layers": len(results), "done": done,
                      "mapped_layers": sum(1 for x in results if (x.get("mapped") or 0) > 0),
                      "out_bytes": sum(x.get("out_bytes") or 0 for x in results),
                      "free_gb": round(free_gb(), 1), "elapsed_s": round(time.time() - t0, 1)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
