#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重跑清单内 20 层（muse-000275 §3）：一趟同时做 before/after 双映射 + 落 after 产物。

为什么一趟双映射：同一行同时喂给
  · before = `origin/main`(2a2369e) 的 fm_core.py（**未修** clean_number）
  · after  = 工作树的 fm_core.py（**已修**）
这样 ① 行数/grade/闭合差额是同一批行的逐行对比（不是两次跑的近似对比）；
② 能直接对「同一行」做「只改格式、没改身份」抽查；③ 只扫一遍 5,130 万行。

产物：
  --rows-dir DIR/rows/<layer>.ndjson.gz   仅 after（11 列，和 v2 同口径）
  --out rerun-20.jsonl                    每层一行统计（含 before/after 的 dirty 计数、grade、bad_*、抽查）
只读 dist/intake-full/layers/。
"""
from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FM = os.path.join(ROOT, "analysis", "fieldmap-20261125")
sys.path.insert(0, FM)
import fm_core as AFTER  # noqa: E402

LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
BASE_COMMIT = "2a2369e44d3258c8b962bd32ebac14a63b679ecd"      # origin/main（PR #58 merge）
BASE_DIR = "/data/scratch/clean-number-baseline"
DIRTY = re.compile(r"^\d+\.0+$")
DECI = re.compile(r"^\d+\.\d*[1-9]\d*$")     # 非零小数：法保留、只计数
SAMPLE_PER_LAYER = 100

_G = {}


def _baseline():
    p = os.path.join(BASE_DIR, "fm_core.py")
    if not os.path.isfile(p):
        os.makedirs(BASE_DIR, exist_ok=True)
        with open(p, "wb") as fh:
            subprocess.run(["git", "-C", ROOT, "show", f"{BASE_COMMIT}:analysis/fieldmap-20261125/fm_core.py"],
                           stdout=fh, check=True)
    spec = importlib.util.spec_from_file_location("fm_core_before", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    return mod


def _init(rows_dir, url_map):
    mod = _baseline()
    cfg = mod.load_pilot_cfg()
    o2d, meta, _fb = mod.load_registry_orgs()
    tm = mod.load_tier_map()
    _G["before"] = mod.LayerMapper(cfg, o2d, meta, tm)
    cfg2 = AFTER.load_pilot_cfg()
    o2d2, meta2, _fb2 = AFTER.load_registry_orgs()
    _G["after"] = AFTER.LayerMapper(cfg2, o2d2, meta2, tm)
    _G["rows_dir"] = rows_dir
    _G["urls"] = url_map
    _G["fields"] = AFTER.FIELDS


def work(job):
    layer = job["layer"]
    url = _G["urls"].get(layer, "")
    mb, ma = _G["before"], _G["after"]
    for m in (mb, ma):
        try:
            m.begin_layer(url, layer)
        except TypeError:
            m.begin_layer(url)
    d = os.path.join(LAYERS, layer)
    allp = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz"))
    parts = job.get("parts") or allp
    chunk = int(job.get("chunk") or 0)
    st = {"layer": layer, "src_field": job.get("src_field", ""), "parts": len(parts), "chunk": chunk,
          "in_rows": 0, "parse_error": 0,
          "before": {"mapped": 0, "dirty": 0, "grade": collections.Counter(), "deci": 0, "dropped": 0},
          "after": {"mapped": 0, "dirty": 0, "grade": collections.Counter(), "deci": 0, "dropped": 0,
                    "bad_empty": 0, "bad_grade": 0, "zero_coord": 0},
          "pairs": 0, "pair_mismatch": [], "addrkey_changed": 0, "samples": []}
    out = None
    rd = _G["rows_dir"]
    if rd:
        os.makedirs(rd, exist_ok=True)
        suffix = ".ndjson.gz" if not chunk else f".part{chunk:02d}.ndjson.gz"
        out = gzip.open(os.path.join(rd, layer + suffix), "wb", compresslevel=1)
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
                    rb, _r1, _f1 = mb.map_row(row)
                    ra, _r2, _f2 = ma.map_row(row)
                    if rb is None and _r1 == "below_c":
                        st["before"]["dropped"] += 1
                    if ra is None and _r2 == "below_c":
                        st["after"]["dropped"] += 1
                    for tag, rec in (("before", rb), ("after", ra)):
                        s = st[tag]
                        if rec is None:
                            continue
                        s["mapped"] += 1
                        s["grade"][rec["grade"]] += 1
                        hn = rec["house_number"] or ""
                        if DIRTY.match(hn):
                            s["dirty"] += 1
                        if DECI.match(hn):
                            s["deci"] += 1
                        if tag == "after":
                            s["bad_empty"] += 1 if not rec["street_name"] else 0
                            s["bad_grade"] += 1 if rec["grade"] not in ("S", "A", "B", "C") else 0
                            s["zero_coord"] += 1 if (rec["lat"] is None or rec["lon"] is None) else 0
                    # 逐行对账：同一行 before/after 必须只差「.0 被吃掉」
                    hb_ = (rb or {}).get("house_number") or ""
                    if DIRTY.match(hb_):
                        st["pairs"] += 1
                        ha = (ra or {}).get("house_number") or ""
                        ok = (ra is not None and ha == hb_[:hb_.index(".")] 
                              and ra["street_name"] == rb["street_name"]
                              and ra["lat"] == rb["lat"] and ra["lon"] == rb["lon"]
                              and ra["grade"] == rb["grade"] and ra["zip5"] == rb["zip5"]
                              and ra["state"] == rb["state"] and ra["city"] == rb["city"])
                        if not ok:
                            st["pair_mismatch"].append({"before": {k: rb[k] for k in ("house_number",
                                                                                    "street_name", "grade")},
                                                        "after": {k: (ra or {}).get(k) for k in (
                                                            "house_number", "street_name", "grade")}})
                        if (ra or {}).get("addrkey") != rb.get("addrkey"):
                            st["addrkey_changed"] += 1
                        if len(st["samples"]) < SAMPLE_PER_LAYER:
                            st["samples"].append({
                                "before": {"house_number": hb_, "street_name": rb["street_name"],
                                           "lat": rb["lat"], "lon": rb["lon"], "grade": rb["grade"],
                                           "addrkey": rb["addrkey"]},
                                "after": {"house_number": ha, "street_name": ra["street_name"],
                                          "lat": ra["lat"], "lon": ra["lon"], "grade": ra["grade"],
                                          "addrkey": ra["addrkey"]}})
                    if out is not None and ra is not None:
                        ra["source_layer"] = ra["source_layer"] or url or layer
                        ra["tier"] = ra.get("tier") or "unrated"
                        out.write((json.dumps({k: ra[k] for k in _G["fields"]}, ensure_ascii=False,
                                              separators=(",", ":")) + "\n").encode("utf-8"))
    finally:
        if out is not None:
            out.close()
    for tag in ("before", "after"):
        st[tag]["grade"] = dict(st[tag]["grade"])
        st[tag]["closed_diff"] = (st["in_rows"] - st[tag]["mapped"]
                                  - st[tag]["dropped"] - st["parse_error"])
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default=os.path.join(HERE, "scope.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "rerun-20.jsonl"))
    ap.add_argument("--rows-dir", default="/data/scratch/clean-number-20261126")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-rows", action="store_true")
    ap.add_argument("--shards", type=int, default=1, help="把每层 part 按序切成 K 段并行（超大局用）")
    a = ap.parse_args()
    _baseline()          # 先在父进程把基线 fm_core.py 落到磁盘，避免多个 worker 同时写同名文件（曾读到半截）
    jobs = [json.loads(l) for l in open(a.scope, encoding="utf-8")]
    import csv
    urls = {}
    inv = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
    for r in csv.DictReader(open(inv, encoding="utf-8")):
        urls.setdefault(r["layer"], r.get("url") or "")
    if a.shards > 1:
        expanded = []
        for j in jobs:
            lp = sorted(f for f in os.listdir(os.path.join(LAYERS, j["layer"]))
                        if f.startswith("part-u") and f.endswith(".ndjson.gz"))
            k = a.shards
            size = (len(lp) + k - 1) // k
            for i in range(k):
                sl = lp[i * size:(i + 1) * size]
                if sl:
                    expanded.append(dict(j, parts=sl, chunk=i + 1))
            print(f"[shard] {j['layer'][:44]} parts={len(lp)} -> {k} 段", flush=True)
        jobs = expanded
    rd = "" if a.no_rows else os.path.join(a.rows_dir, "rows")
    with open(a.out, "w", encoding="utf-8") as fh, \
            mp.Pool(a.workers, initializer=_init, initargs=(rd, urls)) as pool:
        for st in pool.imap_unordered(work, jobs, chunksize=1):
            fh.write(json.dumps(st, ensure_ascii=False) + "\n")
            fh.flush()
            print(f"[rerun] {st['layer'][:48]:48s} rows={st['in_rows']:>10,} "
                  f"dirty {st['before']['dirty']:>9,}->{st['after']['dirty']:>3} "
                  f"mapped {st['before']['mapped']:>10,}->{st['after']['mapped']:>10,} "
                  f"pairs={st['pairs']:>9,} mismatch={len(st['pair_mismatch'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
