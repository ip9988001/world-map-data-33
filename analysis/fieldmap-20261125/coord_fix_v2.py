#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000266 收口：清掉 v2 产物里 107 行「round 后变成 (0,0)」的坐标（其它行一字不动）。

根因：`clean_coord` 旧写法先判 `lat==0 and lon==0` 再 `round(...,7)`；
源层里 `|v| < 5e-7` 的坐标过 round 后就是 0.0 → 输出里出现 (0,0)。
`fm_core.clean_coord` 已改成「先 round 再判」，本脚本把已落盘的数据按同口径补齐：
  · 成员里没有 `"lat":0` 字样 → **原字节直传**（不重压、不改行）
  · 有 → 逐行精确判 `abs(lat)<5e-7 and abs(lon)<5e-7`（或越界/半缺）→ 置 null + 按要素表重算 grade
逐片写 `tar-fix/`，**成员数与行数校验通过后**才 `os.replace` 覆盖旧片（峰值 = 1 旧片 + 1 新片）。

用法：python3 coord_fix_v2.py [--workers 8] [--dist /data/workspace/wmd-fieldmap/dist-v2]
输出：<dist>/coord-fix-stats.json
"""
from __future__ import annotations

import argparse, collections, gzip, io, json, multiprocessing as mp, os, sys, tarfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

_G = {}
NEEDLES = (b'"lat":0,', b'"lat":0.0,', b'"lat":-0,', b'"lat":-0.0,')


def _init():
    cfg = C.load_pilot_cfg()
    grades = cfg["grades"]
    req = {k for k, need in grades.items() if "zip5" in need}
    _G["grades"] = grades
    _G["rest_nozip"] = {k: v for k, v in grades.items() if k not in req}


def bad_coord(lat, lon):
    """与 fm_core.clean_coord 的新口径一致：round 后为 (0,0) 也算坏。"""
    if lat is None and lon is None:
        return False
    if lat is None or lon is None:
        return True
    try:
        la, lo = float(lat), float(lon)
    except (TypeError, ValueError):
        return True
    if not (-90.0 <= la <= 90.0) or not (-180.0 <= lo <= 180.0):
        return True
    return round(la, 7) == 0.0 and round(lo, 7) == 0.0


def work(job):
    name, payload = job
    grades, rest_nozip = _G["grades"], _G["rest_nozip"]
    rows, hit = 0, False
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as fh:
        tail = b""
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            rows += b.count(b"\n")
            win = tail + b
            if any(n in win for n in NEEDLES):
                hit = True
                break
            tail = b[-16:]
    st = {"rows": rows, "bad": 0, "moved": {}}
    if not hit:                                  # 一行都不用改 → 原字节直传
        return name, payload, st, True
    # 精确重写
    rows2 = 0
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as fh, \
            gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=1) as out:
        for line in fh:
            if not line.strip():
                continue
            rows2 += 1
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
            _k = f"{g0}->{g}"
            st["moved"][_k] = st["moved"].get(_k, 0) + 1
            st["bad"] += 1
            out.write(json.dumps({k: r[k] for k in C.FIELDS}, ensure_ascii=False,
                                 separators=(",", ":")).encode() + b"\n")
    st["rows"] = rows2                     # 命中分支的行数以逐行重写时数的为准（快速扫描会提前 break）
    return name, buf.getvalue(), st, False


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dist", default="/data/workspace/wmd-fieldmap/dist-v2")
    a = ap.parse_args()
    tar_dir = os.path.join(a.dist, "tar")
    fix_dir = os.path.join(a.dist, "tar-fix")
    os.makedirs(fix_dir, exist_ok=True)
    allst = {}
    t00 = time.time()
    for sh in sorted(f for f in os.listdir(tar_dir) if f.endswith(".tar.gz")):
        src, dst = os.path.join(tar_dir, sh), os.path.join(fix_dir, sh)
        t0 = time.time()
        n_in = n_out = rows_in = rows_out = 0
        pending = []
        with tarfile.open(src, "r|gz") as tf, \
                mp.Pool(a.workers, initializer=_init) as pool, \
                tarfile.open(dst, "w:gz", compresslevel=1) as ofh:

            def flush(k):
                nonlocal n_out, rows_out
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
                    rows_out += st["rows"]

            for m in tf:
                if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                    continue
                payload = tf.extractfile(m).read()
                n_in += 1
                pending.append((m.name, pool.apply_async(work, ((m.name, payload),))))
                flush(a.workers * 2)
            flush(0)
        sz = os.path.getsize(dst)
        ok = (n_in == n_out)
        print(f"[shard] {sh} members={n_out}/{n_in} rows_out={rows_out:,} "
              f"{sz/2**30:.2f}GiB {time.time()-t0:.0f}s free={free_gb():.1f}G ok={ok}", flush=True)
        if n_out != n_in:
            raise SystemExit(f"成员数不符 {sh}: {n_out}/{n_in}")
        os.replace(dst, src)                  # 校验通过才替换旧片
    tot = {"rows": 0, "bad": 0, "layers_affected": 0, "moved": {}}
    for st in allst.values():
        tot["rows"] += st["rows"]
        tot["bad"] += st["bad"]
        tot["layers_affected"] += 1 if st["bad"] else 0
        for k, v in st["moved"].items():
            tot["moved"][k] = tot["moved"].get(k, 0) + v
    json.dump({"total": tot, "per_layer": {k: v for k, v in allst.items() if v["bad"]},
               "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "elapsed_s": round(time.time() - t00, 1)},
              open(os.path.join(a.dist, "coord-fix-stats.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(tot, ensure_ascii=False))
    print(f"[coord-fix] done {time.time()-t00:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
