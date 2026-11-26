#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量重扫产物（dist-v2）终检：**逐行全扫**，不是抽样。

两件事：
  A) 逐成员行数 vs `layer-coverage.v2.csv:mapped` → 逐层行数闭合（谁多谁少一目了然）
  B) 逐行不变量：11 列 / zip5 5 位 / state 合法 / 坐标范围且非 (0,0) / 门牌非占位 /
     grade ∈ SABC / 缺 zip5 不许落 S-A / 各级要素齐备 / S 级 city 非空 / addrkey 格式 /
     source_layer 是 url 或退回 layer_id / tier ∈ 枚举

用法：python3 verify_v2.py [--workers 8] [--dist dist-v2]
输出：verify-v2.json + verify-v2-layers.csv（逐层行数与差额）
"""
from __future__ import annotations

import argparse, collections, csv, gzip, json, multiprocessing as mp, os, re, sys, tarfile, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

FIELDS = C.FIELDS
STATES = C.STATES_OK
PH = set(C.PLACEHOLDERS) - {""}
RX_AK = re.compile(r"^a3:[0-9a-f]{20}$")
TIERS = {"tier1", "tier2", "tier3", "unrated"}
GRADES = ("S", "A", "B", "C")


def _scan(job):
    """工人份额：扫全部 tar，只解析 zlib.crc32(成员名) % nworkers == wid 的成员。

    理由：单个 12 GB / 383M 行的 tar 片串行解析要 ~2 h；按成员哈希分给 8 个进程各 ~20 min。
    外层 gz 每进程都要顺序解一遍（~2 min/轮），换来 8 倍行级并行，划算。
    """
    paths, grades, wid, nw = job
    req_zip = {k for k, need in grades.items() if "zip5" in need}
    inv = collections.Counter()
    grade_tot = collections.Counter()
    per = {}
    seen_fields = collections.Counter()
    t0 = time.time()
    for path in paths:
      with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                inv["nonfile_member"] += 1
                continue
            if zlib.crc32(m.name.encode()) % nw != wid:
                continue
            lid = m.name[:-len(".ndjson.gz")]
            rows = 0
            g_l = collections.Counter()
            with gzip.GzipFile(fileobj=tf.extractfile(m)) as gz:
                for line in gz:
                    if not line.strip():
                        continue
                    rows += 1
                    o = json.loads(line)
                    if set(o.keys()) != set(FIELDS):
                        inv["bad_columns"] += 1
                        continue
                    seen_fields["x"] += 1
                    z, s, la, lo = o["zip5"], o["state"], o["lat"], o["lon"]
                    hn, st, city, g = o["house_number"], o["street_name"], o["city"], o["grade"]
                    if z is not None and not (isinstance(z, str) and len(z) == 5 and z.isdigit()):
                        inv["bad_zip5"] += 1
                    if s is not None and s not in STATES:
                        inv["bad_state"] += 1
                    if la is not None or lo is not None:
                        if la is None or lo is None or not (-90.0 <= la <= 90.0) or \
                                not (-180.0 <= lo <= 180.0):
                            inv["bad_coord"] += 1
                        elif la == 0.0 and lo == 0.0:
                            inv["zero_coord"] += 1
                        else:
                            inv["coord_ok"] += 1
                    if hn is not None and str(hn).upper() in PH:
                        inv["bad_number"] += 1
                    if g not in GRADES:
                        inv["bad_grade"] += 1
                        continue
                    if g in req_zip and not z:
                        inv["zip_null_high_grade"] += 1
                    # 各级要素齐备（plan §一）
                    need = grades[g]
                    miss = [k for k in need if not (la is not None and lo is not None
                                                    if k in ("point", "point_any") else
                                                    {"number": hn, "street": st, "city": city,
                                                     "state": s, "zip5": z}.get(k))]
                    if miss:
                        inv["grade_missing_element"] += 1
                    if g == "S" and not city:
                        inv["S_city_null"] += 1
                    ak = o["addrkey"]
                    if ak is None:
                        inv["addrkey_null"] += 1
                    elif not RX_AK.match(ak):
                        inv["bad_addrkey_fmt"] += 1
                    src = o["source_layer"]
                    if not src or not (str(src).startswith("http") or src == lid):
                        inv["bad_source_layer"] += 1
                    if o["tier"] not in TIERS:
                        inv["bad_tier"] += 1
                    g_l[g] += 1
                    grade_tot[g] += 1
                    inv["number_ok"] += bool(hn)
                    inv["street_ok"] += bool(st)
                    inv["city_ok"] += bool(city)
                    inv["zip5_ok"] += bool(z)
                    inv["state_ok"] += bool(s)
            per[lid] = {"rows": rows, "grade": dict(g_l)}
    return {"worker": wid, "inv": dict(inv), "grade": dict(grade_tot),
            "per_layer": per, "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dist", default="/data/workspace/wmd-fieldmap/dist-v2")
    ap.add_argument("--cov", default=os.path.join(HERE, "layer-coverage.v2.csv"))
    a = ap.parse_args()
    tars = [os.path.join(a.dist, "tar", f) for f in
            sorted(os.listdir(os.path.join(a.dist, "tar"))) if f.endswith(".tar.gz")]
    grades = C.load_pilot_cfg()["grades"]
    print(f"[verify] {len(tars)} 片 / {a.workers} workers", flush=True)
    tot = collections.Counter()
    gt = collections.Counter()
    per = {}
    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        for r in pool.imap_unordered(_scan, [(tars, grades, w, a.workers) for w in range(a.workers)]):
            tot.update(r["inv"])
            gt.update(r["grade"])
            per.update(r["per_layer"])
            print(f"[verify] worker {r['worker']} members={len(r['per_layer'])} "
                  f"rows={sum(v['rows'] for v in r['per_layer'].values()):,} {r['secs']}s", flush=True)
    cov = {r["layer"]: r for r in csv.DictReader(open(a.cov, encoding="utf-8"))}
    want = {k for k, v in cov.items() if int(v["mapped"] or 0) > 0}
    got = set(per)
    mism = []
    out_rows = []
    for lid, v in per.items():
        exp = int((cov.get(lid) or {}).get("mapped") or 0)
        if v["rows"] != exp:
            mism.append({"layer": lid, "tar_rows": v["rows"], "csv_mapped": exp,
                         "delta": v["rows"] - exp})
        out_rows.append({"layer": lid, "tar_rows": v["rows"], "csv_mapped": exp,
                         "in_rows": int((cov.get(lid) or {}).get("in_rows") or 0),
                         "dropped_below_c": int((cov.get(lid) or {}).get("dropped_below_c") or 0),
                         "parse_error": int((cov.get(lid) or {}).get("parse_error") or 0),
                         "delta": v["rows"] - exp,
                         "grade_S": v["grade"].get("S", 0), "grade_A": v["grade"].get("A", 0),
                         "grade_B": v["grade"].get("B", 0), "grade_C": v["grade"].get("C", 0)})
    with open(os.path.join(HERE, "verify-v2-layers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "tar_rows", "csv_mapped", "in_rows",
                                          "dropped_below_c", "parse_error", "delta",
                                          "grade_S", "grade_A", "grade_B", "grade_C"])
        w.writeheader()
        for r in sorted(out_rows, key=lambda x: -x["tar_rows"]):
            w.writerow(r)
    doc = {"tars": len(tars), "members_in_tars": len(per), "members_expected": len(want),
            "missing_from_tars": sorted(want - got)[:20], "extra_in_tars": sorted(got - want)[:20],
            "rows_total": sum(v["rows"] for v in per.values()),
            "rows_total_csv_mapped": sum(int(v["mapped"] or 0) for v in cov.values()),
            "layer_rowcount_mismatch": len(mism), "mismatch_detail": mism[:20],
            "grade": {g: gt.get(g, 0) for g in GRADES},
            "invariants": dict(tot),
            "field_pct": {k: round(100.0 * tot.get(k.replace("_pct", "_ok"), 0) /
                                   max(1, sum(v["rows"] for v in per.values())), 2)
                          for k in ("number_pct", "street_pct", "city_pct", "zip5_pct",
                                    "state_pct", "coord_pct")},
            "elapsed_s": round(time.time() - t0, 1),
            "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(doc, open(os.path.join(HERE, "verify-v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: doc[k] for k in ("members_in_tars", "members_expected", "rows_total",
                                          "layer_rowcount_mismatch", "grade", "invariants",
                                          "field_pct", "elapsed_s")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
