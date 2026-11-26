#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coord_fix_v2 的单片低内存版（part006 用）：12.2 GB / 355 成员，先前的「整成员进内存」版被 OOM 杀掉。

做法：成员原始字节先流式落到临时文件（不驻内存）→ worker 按**路径**读、分块解压扫描 →
       无命中 → 临时文件原样 ADD 进新 tar；有命中 → 重写成第二个临时文件再 ADD。
       逐成员临时文件用完即删（峰值 ≈ 1~2 个成员，最大 1.4 GB）。

用法：python3 coord_fix_v2_shard.py --shard fieldmap-part006.tar.gz [--workers 4] [--dist ...]
"""
from __future__ import annotations

import argparse, collections, gzip, io, json, multiprocessing as mp, os, shutil, sys, tarfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402
from coord_fix_v2 import NEEDLES, _init, bad_coord  # noqa: E402

_G = {}


def scan(path):
    """返回 (rows, hit)。"""
    rows, hit, tail = 0, False, b""
    with gzip.open(path, "rb") as fh:
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
    return rows, hit


def rewrite(src, dst):
    """逐行精确判坏坐标 → 置 null + 重算 grade；返回 (rows, bad, moved)。"""
    if not _G:
        _init()
    grades, rest_nozip = _G["grades"], _G["rest_nozip"]
    rows = bad = 0
    moved = collections.Counter()
    with gzip.open(src, "rt", encoding="utf-8") as fh, \
            gzip.open(dst, "wb", compresslevel=1) as out:
        for line in fh:
            if not line.strip():
                continue
            rows += 1
            r = json.loads(line)
            if not bad_coord(r["lat"], r["lon"]):
                out.write((line if line.endswith("\n") else line + "\n").encode("utf-8"))
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
            moved[f"{g0}->{g}"] += 1
            bad += 1
            out.write((json.dumps({k: r[k] for k in C.FIELDS}, ensure_ascii=False,
                                  separators=(",", ":")) + "\n").encode("utf-8"))
    return rows, bad, dict(moved)


def work(job):
    name, path, tmpdir = job
    rows, hit = scan(path)
    st = {"rows": rows, "bad": 0, "moved": {}}
    if not hit:
        return name, path, st, True
    out = os.path.join(tmpdir, name + ".fixed")
    r2, bad, moved = rewrite(path, out)
    st.update({"rows": r2, "bad": bad, "moved": moved})
    try:
        os.unlink(path)
    except OSError:
        pass
    return name, out, st, False


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dist", default="/data/workspace/wmd-fieldmap/dist-v2")
    a = ap.parse_args()
    tar_dir, fix_dir = os.path.join(a.dist, "tar"), os.path.join(a.dist, "tar-fix")
    os.makedirs(fix_dir, exist_ok=True)
    tmpdir = os.path.join(fix_dir, ".tmp")
    shutil.rmtree(tmpdir, ignore_errors=True)
    os.makedirs(tmpdir)
    src, dst = os.path.join(tar_dir, a.shard), os.path.join(fix_dir, a.shard)
    for p in (dst,):
        if os.path.exists(p):
            os.unlink(p)
    allst, pending = {}, []
    n_in = n_out = rows_out = 0
    t0 = time.time()
    with tarfile.open(src, "r|gz") as tf, mp.Pool(a.workers, initializer=_init) as pool, \
            tarfile.open(dst, "w:gz", compresslevel=1) as ofh:

        def flush(k):
            nonlocal n_out, rows_out
            while len(pending) > k:
                nm, ar = pending.pop(0)
                nm2, path, st, passthru = ar.get()
                ti = tarfile.TarInfo(nm2)
                ti.size = os.path.getsize(path)
                ti.mtime = int(t0)
                ti.mode = 0o644
                with open(path, "rb") as fh:
                    ofh.addfile(ti, fh)
                os.unlink(path)
                allst[nm2[:-len(".ndjson.gz")]] = st
                n_out += 1
                rows_out += st["rows"]

        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            n_in += 1
            raw = os.path.join(tmpdir, m.name)
            with open(raw, "wb") as fh:
                shutil.copyfileobj(tf.extractfile(m), fh, 1 << 22)
            pending.append((m.name, pool.apply_async(work, ((m.name, raw, tmpdir),))))
            flush(a.workers * 2)
            if n_in % 25 == 0:
                print(f"[{a.shard}] {n_in} members rows_out={rows_out:,} {time.time()-t0:.0f}s "
                      f"free={free_gb():.1f}G", flush=True)
        flush(0)
    sz = os.path.getsize(dst)
    print(f"[shard] {a.shard} members={n_out}/{n_in} rows_out={rows_out:,} {sz/2**30:.2f}GiB "
          f"{time.time()-t0:.0f}s free={free_gb():.1f}G", flush=True)
    if n_out != n_in:
        raise SystemExit(f"成员数不符 {n_out}/{n_in}")
    os.replace(dst, src)
    shutil.rmtree(tmpdir, ignore_errors=True)
    tot = {"rows": rows_out, "bad": 0, "layers_affected": 0, "moved": {}}
    for st in allst.values():
        tot["bad"] += st["bad"]
        tot["layers_affected"] += 1 if st["bad"] else 0
        for k, v in st["moved"].items():
            tot["moved"][k] = tot["moved"].get(k, 0) + v
    out_p = os.path.join(a.dist, f"coord-fix-{a.shard}.json")
    json.dump({"total": tot, "per_layer": {k: v for k, v in allst.items() if v["bad"]}},
              open(out_p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(tot, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
