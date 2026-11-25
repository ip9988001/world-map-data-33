#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000264 B：坐标残留旁路清零（lat/lon 非空但越界或 (0,0) → null + 按要素表降级）。

做法（不重扫输入、不重扫全量映射）：流式读 `dist/tar` 8 片的成员，逐行只看 lat/lon。
  · 成员里一行坏坐标都没有 → **原字节直传**（不重新压缩，省时间也省字节变化）
  · 有坏坐标 → 重写该成员（置 null + **重算 grade**：S 要求 point，坐标没了必须降到 A/B/C）
逐层统计后回填 `layer-coverage.csv`（另由 coord_apply_stats.py 干）与本 json。

磁盘：旧片校验成员数后才删，峰值 = 旧片 + 新片（约 2×9 GB），free_gb 会盯。
用法：python3 coord_clean.py [--workers 4] [--dry-run]
"""
from __future__ import annotations

import argparse, collections, gzip, io, json, multiprocessing as mp, os, sys, tarfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
TARS = os.path.join(DIST, "tar")
TARS3 = os.path.join(DIST, "tar3")
_G = {}


def _init():
    cfg = C.load_pilot_cfg()
    grades = cfg["grades"]
    req = {k for k, need in grades.items() if "zip5" in need}
    _G["grades"] = grades
    _G["rest_nozip"] = {k: v for k, v in grades.items() if k not in req}


def bad_coord(lat, lon):
    if lat is None and lon is None:
        return False
    if lat is None or lon is None:
        return True
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return True
    return lat == 0.0 and lon == 0.0


def work(job):
    name, payload = job
    grades, rest_nozip = _G["grades"], _G["rest_nozip"]
    st = {"rows": 0, "bad": 0, "grade": collections.Counter(), "moved": {}}
    # Pass A：只数（不存行，内存 = 一个成员）
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as fh:
        for line in fh:
            if not line.strip():
                continue
            st["rows"] += 1
            r = json.loads(line)
            if bad_coord(r["lat"], r["lon"]):
                st["bad"] += 1
    if not st["bad"]:
        return name, payload, st, True          # 原字节直传
    # Pass B：重写
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as fh, \
            gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=1) as out:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if not bad_coord(r["lat"], r["lon"]):
                out.write(line if line.endswith(b"\n") else line + b"\n")
                continue
            r["lat"] = None
            r["lon"] = None
            g0 = r["grade"]
            rec = {"house_number": r["house_number"], "street_name": r["street_name"],
                   "city": r["city"], "state": r["state"], "zip5": r["zip5"],
                   "lat": None, "lon": None, "_interp": False}
            g = C.grade_of(rec, grades)
            if g in (set(grades) - set(rest_nozip)) and not r["zip5"]:
                g = C.grade_of(rec, rest_nozip)
            r["grade"] = g
            st["moved"][f"{g0}->{g}"] = st["moved"].get(f"{g0}->{g}", 0) + 1
            st["grade"][g] = st["grade"].get(g, 0) + 1
            out.write(json.dumps({k: r[k] for k in C.FIELDS}, ensure_ascii=False,
                                 separators=(",", ":")).encode() + b"\n")
    st["grade"] = dict(st["grade"])
    return name, buf.getvalue(), st, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.makedirs(TARS3, exist_ok=True)
    shards = sorted(f for f in os.listdir(TARS) if f.endswith(".tar.gz"))
    t0 = time.time()
    allst = {}
    for sh in shards:
        src, dst = os.path.join(TARS, sh), os.path.join(TARS3, sh)
        if os.path.isfile(dst):                 # 断点续跑
            print(f"[skip] {sh} 已存在", flush=True)
            continue
        n_in = n_out = 0
        b_in = b_out = 0
        pending = []
        with tarfile.open(src, "r|gz") as tf, \
                mp.Pool(a.workers, initializer=_init) as pool, \
                tarfile.open(dst, "w:gz", compresslevel=1) as ofh:

            def flush(k):
                nonlocal n_out, b_out
                while len(pending) > k:
                    nm, ar = pending.pop(0)
                    nm2, data, st, passthru = ar.get()
                    ti = tarfile.TarInfo(nm2)
                    ti.size = len(data)
                    ti.mtime = int(t0)
                    ti.mode = 0o644
                    ofh.addfile(ti, io.BytesIO(data))
                    allst[nm2[:-len(".ndjson.gz")]] = st
                    n_out += 1
                    b_out += len(data)

            for m in tf:
                if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                    continue
                payload = tf.extractfile(m).read()
                n_in += 1
                b_in += len(payload)
                pending.append((m.name, pool.apply_async(work, ((m.name, payload),))))
                flush(a.workers * 2)
            flush(0)
        sz = os.path.getsize(dst)
        print(f"[shard] {sh} members={n_out}/{n_in} in={b_in/2**30:.2f}GiB out={sz/2**30:.2f}GiB "
              f"{time.time()-t0:.0f}s", flush=True)
        if n_out != n_in:
            raise SystemExit(f"成员数不符 {sh}")
    tot = {"rows": 0, "bad": 0, "layers_affected": 0, "moved": {}}
    for st in allst.values():
        tot["rows"] += st["rows"]
        tot["bad"] += st["bad"]
        if st["bad"]:
            tot["layers_affected"] += 1
        for k, v in st["moved"].items():
            tot["moved"][k] = tot["moved"].get(k, 0) + v
    json.dump({"total": tot, "per_layer": {k: v for k, v in allst.items() if v["bad"]}},
              open(os.path.join(DIST, "coord-clean-stats.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(tot, ensure_ascii=False))
    print(f"[coord] done {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
