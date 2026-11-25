#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""改口径后的行级抽查（≥10% 层）：7 条增量 + 11 项不变量的独立复核。

全部在**输出侧**独立重算（不调 fm_core.map_row）：
  · source_layer 必须是该层 url（71 层无 url 的退回 layer_id，需在名单里）
  · tier 必须等于 grading-rerun-20261125 分档表按 url 的结果（未命中 = unrated）
  · addrkey 必须等于 engine/outlet_clean.addrkey_v3(本行字段)（空 = 不可键）
  · house_number 不得是占位值（含 -9）；zip5 恰好 5 位；state 合法；坐标范围内且非 (0,0)
  · 各级要素齐备（S: num+street+city+state+zip+coord；A: num+street+state+zip；B: num+street+state；C: street）
  · zip 空 → grade 不得是 S/A

用法：python3 amend_verify.py --layers 355 [--extract-only]
"""
from __future__ import annotations

import argparse, collections, csv, gzip, io, json, multiprocessing as mp, os, random, re, subprocess, sys, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import fm_core as C   # 只借 STATES_OK / PLACEHOLDERS / load_tier_map
import outlet_clean as OC

TARS = os.environ.get("FM_TAR_DIR", "/data/workspace/wmd-fieldmap/dist/tar")
SC = os.environ.get("SC_DIR2", "/tmp/sc2")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
RX_AK = re.compile(r"^a3:[0-9a-f]{20}$")
RX5 = re.compile(r"^\d{5}$")
NEED = {"S": ["number", "street", "city", "state", "zip5", "coord"],
        "A": ["number", "street", "state", "zip5"],
        "B": ["number", "street", "state"],
        "C": ["street"]}

_G = {}


def _init(tiers):
    _G["tiers"] = tiers


def dump_shard(job):
    """一个分片一趟顺序扫描，只落地被抽到的成员。"""
    shard, want = job
    wrote = 0
    with tarfile.open(shard, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            lid = m.name[:-len(".ndjson.gz")]
            if lid in want:
                data = tf.extractfile(m).read()
                open(os.path.join(SC, m.name), "wb").write(data)
                wrote += 1
    return shard, wrote


def check_layer(lid, url, tier, cap_rows=0, ak_rows=3000):
    """cap_rows>0 时只扫前 cap_rows 行（大层）；addrkey 重算只做前 ak_rows 行（street_key 很贵）。"""
    p = os.path.join(SC, lid + ".ndjson.gz")
    bad = collections.Counter()
    n = 0
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            n += 1
            if set(r.keys()) != set(C.FIELDS):
                bad["bad_columns"] += 1
            if (r["source_layer"] or "") != (url or lid):
                bad["bad_source_layer"] += 1
            if r["tier"] != tier:
                bad["bad_tier"] += 1
            if cap_rows and n > cap_rows:
                bad["layer_truncated_scan"] += 1
                break
            g = r["grade"]
            if g not in NEED:
                bad["bad_grade"] += 1
                continue
            ak = r["addrkey"]
            if n <= ak_rows:
                want_ak = OC.addrkey_v3({"state": r["state"], "zip": r["zip5"], "number": r["house_number"],
                                         "street": r["street_name"]}, include_unit=True)
                if (ak or "") != want_ak:
                    bad["bad_addrkey"] += 1
            if ak and not RX_AK.match(ak):
                bad["bad_addrkey_fmt"] += 1
            hn = r["house_number"]
            if hn is not None and (str(hn).strip().upper() in C.PLACEHOLDERS
                                   or re.match(r"^[^0-9A-Za-z]+$", str(hn))):
                bad["bad_number"] += 1
            if r["zip5"] is not None and not RX5.match(r["zip5"]):
                bad["bad_zip5"] += 1
            if r["state"] is not None and r["state"] not in C.STATES_OK:
                bad["bad_state"] += 1
            la, lo = r["lat"], r["lon"]
            if la is not None or lo is not None:
                if la is None or lo is None or not (-90 <= la <= 90) or not (-180 <= lo <= 180):
                    bad["bad_coord"] += 1
                elif la == 0 and lo == 0:
                    bad["zero_coord"] += 1
            if not r["zip5"] and g in ("S", "A"):
                bad["zip_null_high_grade"] += 1
            feats = {"number": bool(hn), "street": bool(r["street_name"]), "city": bool(r["city"]),
                     "state": bool(r["state"]), "zip5": bool(r["zip5"]),
                     "coord": la is not None and lo is not None}
            if not all(feats[k] for k in NEED[g]):
                bad["grade_missing_element"] += 1
            if g == "S" and not r["city"]:
                bad["S_city_null"] += 1
    return lid, n, dict(bad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", type=int, default=355)
    ap.add_argument("--seed", type=int, default=258)
    a = ap.parse_args()
    random.seed(a.seed)
    cov = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    have = [r for r in cov if int(r["mapped"] or 0) > 0]
    big = sorted(have, key=lambda r: -int(r["out_bytes"] or 0))[:10]      # 最大 10 层必查
    pick = {r["layer"] for r in big}
    rest = [r for r in have if r["layer"] not in pick]
    pick |= {r["layer"] for r in random.sample(rest, min(len(rest), a.layers - len(pick)))}
    inv = {}
    with open(INV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inv.setdefault(r["layer"], r)
    tiers = C.load_tier_map()
    os.makedirs(SC, exist_ok=True)
    shards = [os.path.join(TARS, f) for f in sorted(os.listdir(TARS)) if f.endswith(".tar.gz")]
    jobs = [(s, pick) for s in shards]
    done = set()
    with mp.Pool(min(8, len(shards)), initializer=_init, initargs=(tiers,)) as pool:
        for shard, wrote in pool.imap_unordered(dump_shard, jobs):
            print(f"[dump] {os.path.basename(shard)} wrote={wrote}", flush=True)
    for f in os.listdir(SC):
        done.add(f[:-len(".ndjson.gz")])
    print(f"[dump] 抽出 {len(done)}/{len(pick)} 层", flush=True)
    tot = collections.Counter()
    rows = 0
    layers = 0
    per = []
    cnt_bad_layers = 0
    for lid in sorted(done):
        r = next(x for x in have if x["layer"] == lid)
        url = (inv.get(lid) or {}).get("url") or ""
        tier = tiers.get(url, "unrated") if url else "unrated"
        n_all = int(r["mapped"])
        _, n, bad = check_layer(lid, url, tier, cap_rows=(300000 if n_all > 300000 else 0))
        rows += n
        layers += 1
        if n_all <= 300000 and n != n_all:
            bad["layer_rowcount_mismatch"] = bad.get("layer_rowcount_mismatch", 0) + 1
        for k, v in bad.items():
            tot[k] += v
        if bad:
            cnt_bad_layers += 1
        per.append({"layer": lid, "rows": n, "bad": bad})
    inv_tot = {k: tot.get(k, 0) for k in ("bad_columns", "bad_source_layer", "bad_tier", "bad_addrkey",
                                          "bad_addrkey_fmt", "bad_number", "bad_zip5", "bad_state",
                                          "bad_coord", "zero_coord", "zip_null_high_grade",
                                          "grade_missing_element", "S_city_null",
                                          "layer_rowcount_mismatch", "bad_grade")}
    res = {"layers_checked": layers, "rows_checked": rows, "layers_with_issue": cnt_bad_layers,
           "invariants": inv_tot, "invariant_violations": sum(v for k, v in inv_tot.items()),
           "match_pct": round(100.0 * (rows - sum(v for k, v in inv_tot.items()
                                                 if k != "layer_rowcount_mismatch")) / rows, 4) if rows else 0.0}
    json.dump(res, open(os.path.join(HERE, "anchor-check.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "anchor-check.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "rows", "violations", "detail"])
        w.writeheader()
        for p in per:
            w.writerow({"layer": p["layer"], "rows": p["rows"], "violations": sum(p["bad"].values()),
                        "detail": json.dumps(p["bad"], ensure_ascii=False)})
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
