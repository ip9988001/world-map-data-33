#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix58 重跑器（muse-000271）：对指定层做 before/after 双跑。

before = 起点提交 4c3a6a3 的 fm_core.py + registry/dialects.v1.yaml（git show 取到 /data/scratch，
         **不复制进仓库**，A/B 口径可复现）；
after  = 本轮工作树的 fm_core.py + dialects.v1.yaml + registry/layer-aliases.v1.yaml。

逐层统计（before/after 同一份统计函数，避免两套口径）：
  in_rows / mapped / dropped_below_c / parse_error / diff / grade 分布
  bad_empty  = mapped 行里 street_name 为空的行数（应 0；grade C 要求 street）
  bad_grade  = mapped 行里 grade 不在 {S,A,B,C} 的行数
  zero_coord = mapped 行里 lat/lon 缺失的行数
  num_ok / zip_ok / state_ok / street_hash / addrkey_hash（哈希=取值序列的 md5，用于 A/B 对比口径是否变化）

用法：
  python3 run_fix58.py --mode after  --layers <csv> --out <jsonl> [--write-rows DIR]
  python3 run_fix58.py --mode before --layers <csv> --out <jsonl>
只读 dist/intake-full/layers/；只写 --out 与（after 模式下的）--write-rows。
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FM = os.path.join(ROOT, "analysis", "fieldmap-20261125")
LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
BASE_COMMIT = "4c3a6a324858d7d14efc2edb35331b0924be6764"
BASE_DIR = "/data/scratch/fix58-baseline"

_G = {}


def _git_show(rel, dst):
    if os.path.isfile(dst):
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as fh:
        subprocess.run(["git", "-C", ROOT, "show", f"{BASE_COMMIT}:{rel}"], stdout=fh, check=True)
    return dst


def _load_baseline():
    """基线模块：4c3a6a3 的 fm_core.py（角色表强行指向同提交的 dialects.v1.yaml）。"""
    sys.path.insert(0, FM)
    import importlib.util
    import fm_core as newC
    p = _git_show("analysis/fieldmap-20261125/fm_core.py", os.path.join(BASE_DIR, "fm_core.py"))
    y = _git_show("registry/dialects.v1.yaml", os.path.join(BASE_DIR, "dialects.v1.yaml"))
    spec = importlib.util.spec_from_file_location("fm_core_baseline", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT          # 基线模块按 /data/scratch 推导 ROOT，会把 pilot.yaml / tier 表找错 → 强制指回仓库
    roles = newC.SA.roles_of(y, os.path.join(ROOT, "engine", "dialects"))
    num = {k for k, v in roles.items() if "number" in v}
    st = {k for k, v in roles.items() if "street" in v}
    zp = {k for k, v in roles.items() if "zip" in v}
    mod.load_roles = lambda: {"number": num, "street": st, "zip": zp}
    return mod, newC


def _init(mode):
    if mode == "before":
        mod, _ = _load_baseline()
    else:
        sys.path.insert(0, FM)
        import fm_core as mod
    cfg = mod.load_pilot_cfg()
    o2d, meta, _fb = mod.load_registry_orgs()
    _G["m"] = mod.LayerMapper(cfg, o2d, meta, mod.load_tier_map())
    _G["fields"] = mod.FIELDS
    _G["mode"] = mode


def _h(seq):
    return hashlib.md5("\x1f".join(seq).encode("utf-8")).hexdigest()[:16]


def work(job):
    lid, url, reason = job
    m = _G["m"]
    st = {"layer_id": lid, "reason_code": reason, "in_rows": 0, "mapped": 0, "dropped_below_c": 0,
          "parse_error": 0, "bad_empty": 0, "bad_grade": 0, "zero_coord": 0,
          "num_ok": 0, "street_ok": 0, "zip5_ok": 0, "state_ok": 0, "parts_read": 0,
          "grade": collections.Counter(), "_s": [], "_k": []}
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz")) \
        if os.path.isdir(d) else []
    if _G.get("max_parts"):
        parts = parts[:_G["max_parts"]]
    if not parts:
        st["reason"] = "upstream_no_payload"
        st["grade"] = {}
        return st
    try:
        m.begin_layer(url, lid)
    except TypeError:            # 基线模块的 begin_layer 只吃 url
        m.begin_layer(url)
    st["parts_read"] = len(parts)
    out = None
    wr = _G.get("write_rows")
    if wr:
        os.makedirs(wr, exist_ok=True)
        out = gzip.open(os.path.join(wr, lid + ".ndjson.gz"), "wb", compresslevel=1)
    try:
        for fn in parts:
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
                    rec, rsn, full = m.map_row(row)
                    if rsn == "below_c":
                        st["dropped_below_c"] += 1
                        continue
                    if rec is None:
                        st["parse_error"] += 1
                        continue
                    st["mapped"] += 1
                    st["grade"][rec["grade"]] += 1
                    st["num_ok"] += bool(rec["house_number"])
                    st["street_ok"] += bool(rec["street_name"])
                    st["zip5_ok"] += bool(rec["zip5"])
                    st["state_ok"] += bool(rec["state"])
                    if not rec["street_name"]:
                        st["bad_empty"] += 1
                    if rec["grade"] not in ("S", "A", "B", "C"):
                        st["bad_grade"] += 1
                    if rec["lat"] is None or rec["lon"] is None:
                        st["zero_coord"] += 1
                    if len(st["_s"]) < 400000:
                        st["_s"].append(f"{rec['house_number']}|{rec['street_name']}")
                        st["_k"].append(f"{rec['addrkey']}|{rec['grade']}|{rec['zip5']}|{rec['state']}")
                    if out is not None:
                        rec["source_layer"] = rec["source_layer"] or url or lid
                        rec["tier"] = "unrated" if not rec.get("tier") else rec["tier"]
                        out.write((json.dumps({k: rec[k] for k in _G["fields"]}, ensure_ascii=False,
                                              separators=(",", ":")) + "\n").encode("utf-8"))
    finally:
        if out is not None:
            out.close()
    st["diff"] = st["in_rows"] - st["mapped"] - st["dropped_below_c"] - st["parse_error"]
    st["grade"] = dict(st["grade"])
    st["street_hash"] = _h(st["_s"])
    st["addrkey_hash"] = _h(st["_k"])
    st["n_hashed"] = len(st["_s"])
    st.pop("_s")
    st.pop("_k")
    if st["mapped"] == 0:
        st["reason"] = "grade_below_C" if st["in_rows"] else "zero_rows"
    return st


def load_jobs(csv_path, only=None):
    jobs = []
    if csv_path.endswith(".jsonl"):
        for line in open(csv_path, encoding="utf-8"):
            d = json.loads(line)
            jobs.append((d["layer_id"], d.get("url") or "", d.get("reason_code") or ""))
    else:
        for r in csv.DictReader(open(csv_path, encoding="utf-8")):
            jobs.append((r["layer_id"], r.get("url") or "", r.get("reason_code") or ""))
    if only:
        keep = {x.strip() for x in open(only, encoding="utf-8") if x.strip()}
        jobs = [j for j in jobs if j[0] in keep]
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["before", "after"], required=True)
    ap.add_argument("--jobs", required=True, help="jsonl/csv：含 layer_id[, url][, reason_code]")
    ap.add_argument("--out", required=True)
    ap.add_argument("--write-rows", default="")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("FM_WORKERS", "6")))
    ap.add_argument("--max-parts", type=int, default=0, help="只读每层前 N 个 part（仅用于超大局部的 A/B 抽检）")
    a = ap.parse_args()
    jobs = load_jobs(a.jobs)
    _G["write_rows"] = os.path.join(a.write_rows, "rows") if a.write_rows else ""
    _G["max_parts"] = a.max_parts
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh, \
            mp.Pool(a.workers, initializer=_init, initargs=(a.mode,)) as pool:
        for st in pool.imap_unordered(work, jobs, chunksize=1):
            fh.write(json.dumps(st, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[{a.mode}] {st['layer_id'][:48]:48s} in={st['in_rows']:>9d} mapped={st['mapped']:>9d} "
                  f"drop={st['dropped_below_c']:>9d} {st.get('reason','')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
