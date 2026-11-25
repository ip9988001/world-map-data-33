#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000264 A2：只重扫 `sample-layers.csv` 里的样本层（≤20 层），输出到 dist/sample/。

打点（本单最关键的证据）：
  · 每个 worker 一个 LayerMapper，每层**必须**调一次 `begin_layer(url)`；
    通过 monkeypatch 计数，返回 `begin_layer_calls`，汇总后必须 == 处理层数（每层一次，不复用缓存）。
  · 每层额外记录 `keys_probed`（该层首行 `_probe_keys()` 探到的 raw 字段名）——
    「代码里写了 ≠ 跑的时候调了」，这两个数就是运行时证据。
  · 同时统计「非信封来源」行数（输出的 state/zip5/house_number/city 与纯信封口径不同 → 必然来自
    raw 角色别名或组合串拆分），这就是 begin_layer 泄漏会打到的面。

用法：python3 sample_rescan.py [--workers 6]
"""
from __future__ import annotations

import argparse, collections, csv, gzip, json, multiprocessing as mp, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

LAYERS = "/data/workspace/world-map-data-33/dist/intake-full/layers"
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
OUTDIR = os.path.join(DIST, "sample")
SAMPLE = os.path.join(HERE, "sample-layers.csv")
_G = {}


def _init():
    cfg = C.load_pilot_cfg()
    org2dial, meta, fb = C.load_registry_orgs()
    m = C.LayerMapper(cfg, org2dial, meta, C.load_tier_map())
    # ---- 打点：包一层计数器 ----
    calls = {"n": 0, "urls": []}
    orig = m.begin_layer

    def wrapped(url=""):
        calls["n"] += 1
        calls["urls"].append(url or "")
        return orig(url)

    m.begin_layer = wrapped
    _G.update(m=m, calls=calls, cfg=cfg)


def scan(job):
    lid, url, tier = job
    if not _G:
        _init()
    m, calls, cfg = _G["m"], _G["calls"], _G["cfg"]
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz")) \
        if os.path.isdir(d) else []
    t0 = time.time()
    before = calls["n"]
    m.begin_layer(url)                      # ← 每层一次，重置 _keys/_split_key/_url
    keys_probed = None
    st = {"layer_id": lid, "url": url, "tier_hint": tier, "part_files": len(parts), "rows_in": 0,
          "rows_out": 0, "dropped_below_c": 0, "parse_error": 0, "split_rows": 0,
          "nonenv_state": 0, "nonenv_zip5": 0, "nonenv_number": 0, "nonenv_city": 0,
          "state_ok": 0, "zip5_ok": 0, "number_ok": 0, "city_ok": 0, "street_ok": 0,
          "grade": collections.Counter(), "tier": collections.Counter(), "seconds": 0.0,
          "begin_layer_calls_this_layer": 0, "keys_probed": {}}
    os.makedirs(OUTDIR, exist_ok=True)
    op = os.path.join(OUTDIR, lid + ".ndjson.gz")
    with gzip.open(op, "wb", compresslevel=1) as out:
        for fn in parts:
            with gzip.open(os.path.join(d, fn), "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    st["rows_in"] += 1
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        st["parse_error"] += 1
                        continue
                    if m._keys is None and isinstance(row.get("raw"), dict):
                        keys_probed = {k: [x for x in v] for k, v in m._probe_keys(row["raw"]).items()}
                        m._keys = keys_probed
                    rec, reason, full = m.map_row(row)
                    if reason == "below_c":
                        st["dropped_below_c"] += 1
                        continue
                    if rec is None:
                        st["parse_error"] += 1
                        continue
                    tier_l = tier
                    rec["tier"] = tier_l
                    out.write((json.dumps({k: rec[k] for k in C.FIELDS}, ensure_ascii=False,
                                          separators=(",", ":")) + "\n").encode())
                    st["rows_out"] += 1
                    st["grade"][rec["grade"]] += 1
                    st["tier"][tier_l] += 1
                    if rec["_prov"] == "split":
                        st["split_rows"] += 1
                    # 非信封来源：与「只用信封字段」的结果不同 → 必来自 raw 别名或拆串
                    if rec["state"] != (C.clean_state(row.get("state") or row.get("st")) or None):
                        st["nonenv_state"] += 1
                    if rec["zip5"] != (C.clean_zip5(row.get("zip"))[0] or None):
                        st["nonenv_zip5"] += 1
                    if rec["house_number"] != (C.clean_number(row.get("add_num")) or None):
                        st["nonenv_number"] += 1
                    if rec["city"] != (C.clean_city(row.get("city")) or None):
                        st["nonenv_city"] += 1
                    st["state_ok"] += bool(rec["state"])
                    st["zip5_ok"] += bool(rec["zip5"])
                    st["number_ok"] += bool(rec["house_number"])
                    st["city_ok"] += bool(rec["city"])
                    st["street_ok"] += bool(rec["street_name"])
    st["seconds"] = round(time.time() - t0, 1)
    st["begin_layer_calls_this_layer"] = calls["n"] - before
    st["keys_probed"] = keys_probed or {}
    st["out_bytes"] = os.path.getsize(op)
    st["grade"] = dict(st["grade"])
    st["tier"] = dict(st["tier"])
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(SAMPLE, encoding="utf-8")))
    jobs = [(r["layer_id"], r["url"], r["tier"] or "unrated") for r in rows]
    os.makedirs(OUTDIR, exist_ok=True)
    t0 = time.time()
    res = []
    with mp.Pool(min(a.workers, len(jobs)), initializer=_init) as pool:
        for st in pool.imap_unordered(scan, jobs):
            res.append(st)
            print(f"[scan] {st['layer_id'][:44]:44s} rows {st['rows_in']:7d}->{st['rows_out']:7d} "
                  f"calls={st['begin_layer_calls_this_layer']} {st['seconds']:6.1f}s", flush=True)
    res.sort(key=lambda x: x["layer_id"])
    tot = {"layers": len(res), "rows_in": sum(r["rows_in"] for r in res),
           "rows_out": sum(r["rows_out"] for r in res),
           "dropped_below_c": sum(r["dropped_below_c"] for r in res),
           "begin_layer_calls": sum(r["begin_layer_calls_this_layer"] for r in res),
           "seconds_wall": round(time.time() - t0, 1),
           "seconds_sum": round(sum(r["seconds"] for r in res), 1)}
    tot["calls_equal_layers"] = tot["begin_layer_calls"] == tot["layers"]
    tot["per_layer"] = res
    json.dump(tot, open(os.path.join(DIST, "sample", "rescan.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in tot.items() if k != "per_layer"}, ensure_ascii=False))
    return 0 if tot["calls_equal_layers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
