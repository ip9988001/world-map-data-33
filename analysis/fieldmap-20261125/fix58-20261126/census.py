#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归普查（muse-000271 §四.4/§四.5）：3,550 层逐层取「raw 字段名并集 + 州代理值」。

为什么这样取：
  · 新别名只能影响「raw 里存在该字段」的层 → 用字段名并集能**穷举**出受别名影响的层（不用抽样）；
  · 州信息用来给抽样回归做分层（不是判定口径）；
  · 只读每个 part 文件的第 1 行（ArcGIS 分页同 schema），加上前 5 行跑 map_row 取 state 多数票。

输出：rows-census.jsonl  每层一行 {layer_id, n_parts, n_keys, keys, state_guess, state_hits, sample_url}
只读 dist/intake-full/layers/。（census 自身不改任何数据）
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FM = os.path.join(ROOT, "analysis", "fieldmap-20261125")
sys.path.insert(0, FM)
LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
COV = os.path.join(FM, "layer-coverage.v2.csv")

_G = {}


def _init():
    import fm_core as C
    cfg = C.load_pilot_cfg()
    o2d, meta, _fb = C.load_registry_orgs()
    _G["m"] = C.LayerMapper(cfg, o2d, meta, C.load_tier_map())
    _G["C"] = C


def work(job):
    lid, url = job
    C = _G["C"]
    m = _G["m"]
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz")) \
        if os.path.isdir(d) else []
    keys, states = set(), collections.Counter()
    n = 0
    for i, fn in enumerate(parts):
        want = 5 if i == 0 else 1      # 第一个 part 取前 5 行，其余 part 只取首行（同 schema）
        got = 0
        try:
            with gzip.open(os.path.join(d, fn), "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
                    keys |= set(raw.keys())
                    if n < 5:                      # 前 5 行取州（代理值，不参与判定）
                        n += 1
                        try:
                            rec, _r, _f = m.map_row(row)
                        except Exception:          # noqa: BLE001
                            rec = None
                        st = (row.get("state") or row.get("st")
                              or ((rec or {}).get("state")) or "")
                        st = str(st).strip().upper()
                        if len(st) == 2 and st.isalpha():
                            states[st] += 1
                        else:
                            for k in ("State", "STATE", "StateAbbr", "STATE_ABBR", "State_raw"):
                                v = raw.get(k)
                                if isinstance(v, str) and len(v.strip()) == 2 and v.strip().isalpha():
                                    states[v.strip().upper()] += 1
                                    break
                    got += 1
                    if got >= want:
                        break
        except (OSError, EOFError):
            pass
    return {"layer_id": lid, "url": url, "n_parts": len(parts), "n_keys": len(keys),
            "keys": sorted(keys), "state_guess": (states.most_common(1)[0][0] if states else ""),
            "state_hits": sum(states.values())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    jobs = []
    for r in csv.DictReader(open(COV, encoding="utf-8")):
        jobs.append((r["layer"], ""))
    inv = {}
    p = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
    for r in csv.DictReader(open(p, encoding="utf-8")):
        inv.setdefault(r["layer"], r.get("url") or "")
    jobs = [(lid, inv.get(lid, "")) for lid, _ in jobs]
    with open(a.out, "w", encoding="utf-8") as fh, mp.Pool(a.workers, initializer=_init) as pool:
        done = 0
        for st in pool.imap_unordered(work, jobs, chunksize=4):
            fh.write(json.dumps(st, ensure_ascii=False) + "\n")
            done += 1
            if done % 200 == 0:
                print(f"[census] {done}/{len(jobs)}", flush=True)
    print(json.dumps({"layers": len(jobs), "out": a.out}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
