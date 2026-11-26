#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""坐标收口后的「全量再证」（muse-000266 收口用，分两段，都是全量）：

背景：`coord_fix_v2.py` 只应改 107 行（lat/lon round 后为 0 → null，并按要素表重算 grade）。
它按片处理：part000–005 已按片校验后替换，part006 走低内存版（实测 0 行命中、行数一致）。

A 段（json 全不变量，逐行）：part000–005 共 6 片 / 96.7M 行 —— 被改写的片必须重新逐行验。
B 段（字节级，不解 JSON）：part006 12.2 GB / 383M 行 —— 该片只有 passthrough（未改行），
   只需证：行数不变、`(0,0)` 残留 0、各级行数与改前一致（`"grade":"X"` 计数）。

用法：python3 verify_v2_post.py [--workers 8]
输出：verify-v2-post.json
"""
from __future__ import annotations

import argparse, collections, gzip, json, multiprocessing as mp, os, re, sys, tarfile, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

FIELDS = C.FIELDS
STATES = C.STATES_OK
PH = set(C.PLACEHOLDERS) - {""}
RX_AK = re.compile(r"^a3:[0-9a-f]{20}$")
TIERS = {"tier1", "tier2", "tier3", "unrated"}
ZERO = (b'"lat":0,', b'"lat":0.0,', b'"lat":-0,', b'"lat":-0.0,')


def _scan(job):
    paths, wid, nw, mode = job
    st = collections.Counter()
    st["rows"] = 0
    if mode == "json":
        grades = C.load_pilot_cfg()["grades"]
        req_zip = {k for k, need in grades.items() if "zip5" in need}
    t0 = time.time()
    for path in paths:
        with tarfile.open(path, "r|gz") as tf:
            for m in tf:
                if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                    continue
                if zlib.crc32(m.name.encode()) % nw != wid:
                    continue
                lid = m.name[:-len(".ndjson.gz")]
                with gzip.GzipFile(fileobj=tf.extractfile(m)) as gz:
                    if mode == "json":
                        for line in gz:
                            if not line.strip():
                                continue
                            st["rows"] += 1
                            o = json.loads(line)
                            if set(o.keys()) != set(FIELDS):
                                st["bad_columns"] += 1
                                continue
                            z, s, la, lo, g = o["zip5"], o["state"], o["lat"], o["lon"], o["grade"]
                            if z is not None and not (len(z) == 5 and z.isdigit()):
                                st["bad_zip5"] += 1
                            if s is not None and s not in STATES:
                                st["bad_state"] += 1
                            if la is None and lo is None:
                                st["coord_null"] += 1
                            elif la is None or lo is None or not (-90 <= la <= 90) or \
                                    not (-180 <= lo <= 180):
                                st["bad_coord"] += 1
                            elif la == 0 and lo == 0:
                                st["zero_coord"] += 1
                            else:
                                st["coord_ok"] += 1
                            if g not in ("S", "A", "B", "C"):
                                st["bad_grade"] += 1
                                continue
                            st["grade_" + g] += 1
                            if g in req_zip and not z:
                                st["zip_null_high_grade"] += 1
                            if g == "S" and not o["city"]:
                                st["S_city_null"] += 1
                            if o["house_number"] is not None and str(o["house_number"]).upper() in PH:
                                st["bad_number"] += 1
                            if o["addrkey"] is not None and not RX_AK.match(o["addrkey"]):
                                st["bad_addrkey_fmt"] += 1
                            src = o["source_layer"]
                            if not src or not (str(src).startswith("http") or src == lid):
                                st["bad_source_layer"] += 1
                            if o["tier"] not in TIERS:
                                st["bad_tier"] += 1
                    else:                                   # 字节级
                        tail = b""
                        while True:
                            b = gz.read(1 << 22)
                            if not b:
                                break
                            st["rows"] += b.count(b"\n")
                            st["lat_null"] += b.count(b'"lat":null')
                            win = tail + b
                            st["zero_hits"] += sum(win.count(n) for n in ZERO)
                            for gch in (b"S", b"A", b"B", b"C"):
                                st["grade_" + gch.decode()] += win.count(b'"grade":"' + gch + b'"')
                            tail = b[-16:]
    out = dict(st)
    out["worker"] = wid
    out["secs"] = round(time.time() - t0, 1)
    return out


def run(tars, workers, mode):
    tot = collections.Counter()
    t0 = time.time()
    with mp.Pool(workers) as pool:
        for r in pool.imap_unordered(_scan, [(tars, w, workers, mode) for w in range(workers)]):
            tot.update({k: v for k, v in r.items() if isinstance(v, int)})
    return tot, round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dist", default="/data/workspace/wmd-fieldmap/dist-v2")
    a = ap.parse_args()
    tdir = os.path.join(a.dist, "tar")
    allt = [os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.endswith(".tar.gz")]
    big = [t for t in allt if t.endswith("part006.tar.gz")]
    small = [t for t in allt if t not in big]
    pre = json.load(open(os.path.join(HERE, "verify-v2.json"), encoding="utf-8"))
    print(f"[post-A] json 逐行: {len(small)} 片", flush=True)
    A, ta = run(small, a.workers, "json")
    print(f"[post-A] done {ta}s rows={A['rows']:,}", flush=True)
    print(f"[post-B] 字节级: {len(big)} 片", flush=True)
    B, tb = run(big, a.workers, "bytes")
    print(f"[post-B] done {tb}s rows={B['rows']:,} zero={B['zero_hits']}", flush=True)
    grade = {g: A.get("grade_" + g, 0) + B.get("grade_" + g, 0) for g in ("S", "A", "B", "C")}
    rows = A["rows"] + B["rows"]
    doc = {"rows_total": rows, "rows_expected": pre["rows_total"],
            "rows_match": rows == pre["rows_total"],
            "zero_coord_hits_after_fix": B["zero_hits"],
            "part000_005_invariants": {k: v for k, v in A.items()
                                       if k.startswith(("bad_", "zero_", "coord_", "S_", "zip_null"))},
            "part006_bytescan": {"rows": B["rows"], "zero_hits": B["zero_hits"],
                                 "lat_null_rows": B.get("lat_null", 0)},
            "grade_after_fix": grade, "grade_before_fix": pre["grade"],
            "grade_delta": {g: grade[g] - pre["grade"][g] for g in grade},
            "phase_secs": {"json_part000_005": ta, "bytes_part006": tb},
            "elapsed_s": round(ta + tb, 1),
            "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(doc, open(os.path.join(HERE, "verify-v2-post.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: doc[k] for k in ("rows_total", "rows_expected", "rows_match",
                                          "zero_coord_hits_after_fix", "part000_005_invariants",
                                          "grade_after_fix", "grade_delta", "phase_secs")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
