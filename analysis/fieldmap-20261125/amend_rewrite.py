#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 9 步增量：把已发布的 11 列数据按 muse-000258 / w2-fieldmap-plan 逐行改口径（不重扫 40G 输入）。

只改「能从既有输出 + 配置 + 映射表现场重算」的 5 项：
  1) source_layer：layer_id → **url**（层→url 取 analysis/full-inventory-20261124/local-vs-ledger-reconcile.csv）
  2) addrkey：旧实现（number|street|city|state|zip5|unit 自拼 sha1）→ **engine 档 v3**
     `engine/outlet_clean.py:addrkey_v3`，include_unit 读 engine/config/pilot.yaml；num/street 缺 → null
  3) house_number：占位值补 **-9**（含 0.0/-1.0/-9.0/0000/-09）→ 置 null，并**重算 grade**
  4) zip 非法/缺失 → grade 封顶 B：由配置推出（S/A 需要 zip5），逐行复核
  5) tier：改用 **grading-rerun-20261125/auto-recognized.csv（Tier1 = 410 那版）** 按 url 取；未命中 = unrated

输入：dist/tar/fieldmap-part*.tar.gz（成员 = 每层 .ndjson.gz）
输出：dist/tar2/fieldmap-part*.tar.gz（同名同序），校验后删旧片
统计：dist/amend-stats.json + analysis/.../layer-coverage-amend.csv
用法：python3 amend_rewrite.py [--workers 6] [--limit-shards N] [--dry-single MEMBER]
"""
from __future__ import annotations

import argparse, csv, gzip, io, json, multiprocessing as mp, os, sys, tarfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")
TARS = os.path.join(DIST, "tar")
TARS2 = os.path.join(DIST, "tar2")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
COV_OLD = os.path.join(HERE, "layer-coverage.csv")
COV_NEW = os.path.join(HERE, "layer-coverage-amend.csv")
FIELDS = C.FIELDS

_G = {}
REQ_ZIP = None


def _init(cfg):
    grades = cfg["grades"]
    req = {k for k, need in grades.items() if "zip5" in need}
    rest = {k: v for k, v in grades.items() if k not in req}
    _G["grades"] = grades
    _G["rest"] = rest
    _G["include_unit"] = bool((cfg.get("addrkey") or {}).get("include_unit", True))
    _G["ph"] = C.PLACEHOLDERS


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def rewrite_member(job):
    """一个成员（一层）：逐行改口径 → 返回 (name, gzbytes, stats)。"""
    name, payload, url, tier = job
    grades, rest, iu = _G["grades"], _G["rest"], _G["include_unit"]
    lid = name[:-len(".ndjson.gz")]
    src_layer = url or lid          # 无 url 的 71 层（@未定位）退回 layer_id（覆盖表标注）
    st = {"rows_in": 0, "rows_out": 0, "dropped_new": 0, "key_changed": 0, "key_unkeyed": 0,
          "n_null": 0, "num_ok": 0, "street_ok": 0, "city_ok": 0, "state_ok": 0,
          "zip_ok": 0, "zip_null": 0, "coord_ok": 0, "coord_null": 0,
          "grade": {"S": 0, "A": 0, "B": 0, "C": 0}, "moved": {}, "bad": 0}
    moved = st["moved"]
    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as fh:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=1) as out:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                st["rows_in"] += 1
                hn = r["house_number"]
                hn2 = C.clean_number(hn)
                if (hn or "") != hn2:
                    st["n_null"] += 1
                street, city, state, zip5 = r["street_name"], r["city"], r["state"], r["zip5"]
                lat, lon, grade = r["lat"], r["lon"], r["grade"]
                if hn2 != (hn or ""):
                    rec = {"house_number": hn2 or None, "street_name": street, "city": city,
                           "state": state, "zip5": zip5, "lat": lat, "lon": lon, "_interp": False}
                    g = C.grade_of(rec, grades)
                    if g in (set(grades) - set(rest)) and not zip5:
                        g = C.grade_of(rec, rest)
                    k = f"{grade}->{g}"
                    moved[k] = moved.get(k, 0) + 1
                    grade = g
                if grade is None:                       # 变 null（-9 且只靠门牌撑级）→ 丢
                    st["dropped_new"] += 1
                    continue
                ak = C.addrkey_v3(hn2, street, state, zip5, include_unit=iu)
                old_ak = r["addrkey"]
                if ak != (old_ak or ""):
                    st["key_changed"] += 1
                if not ak:
                    st["key_unkeyed"] += 1
                o = {"house_number": hn2 or None, "street_name": street, "city": city, "state": state,
                     "zip5": zip5, "lat": lat, "lon": lon, "source_layer": src_layer,
                     "tier": tier, "grade": grade, "addrkey": ak or None}
                out.write((json.dumps(o, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
                st["rows_out"] += 1
                st["grade"][grade] += 1
                if o["house_number"]:
                    st["num_ok"] += 1
                if street:
                    st["street_ok"] += 1
                if city:
                    st["city_ok"] += 1
                if state:
                    st["state_ok"] += 1
                if zip5:
                    if len(zip5) == 5 and zip5.isdigit():
                        st["zip_ok"] += 1
                    else:
                        st["bad"] += 1
                else:
                    st["zip_null"] += 1
                if lat is not None and lon is not None:
                    if -90 <= lat <= 90 and -180 <= lon <= 180 and not (lat == 0 and lon == 0):
                        st["coord_ok"] += 1
                    else:
                        st["bad"] += 1
                else:
                    st["coord_null"] += 1
    return name, buf.getvalue(), st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit-shards", type=int, default=0)
    a = ap.parse_args()
    cfg = C.load_pilot_cfg()
    inv = {}
    with open(INV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            inv.setdefault(r["layer"], r)
    tiers = C.load_tier_map()
    shards = sorted(f for f in os.listdir(TARS) if f.endswith(".tar.gz"))
    if a.limit_shards:
        shards = shards[:a.limit_shards]
    os.makedirs(TARS2, exist_ok=True)
    print(f"[amend] shards={len(shards)} workers={a.workers} free={free_gb():.1f}G", flush=True)
    allst = {}
    t0 = time.time()
    for sh in shards:
        src = os.path.join(TARS, sh)
        dst = os.path.join(TARS2, sh)
        n_in = n_out = 0
        with tarfile.open(src, "r|gz") as tf, \
                mp.Pool(a.workers, initializer=_init, initargs=(cfg,)) as pool, \
                tarfile.open(dst, "w:gz", compresslevel=1) as ofh:
            pending = []
            for m in tf:
                if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                    continue
                lid = m.name[:-len(".ndjson.gz")]
                url = (inv.get(lid) or {}).get("url") or ""
                job = (m.name, tf.extractfile(m).read(), url, tiers.get(url, "unrated") if url else "unrated")
                n_in += 1
                pending.append((m.name, pool.apply_async(rewrite_member, (job,))))
                while len(pending) > a.workers * 2:          # 有界流水线（不用 imap 的无界预取）
                    nm, ar = pending.pop(0)
                    nm2, gz, st = ar.get()
                    ti = tarfile.TarInfo(nm)
                    ti.size = len(gz)
                    ti.mtime = int(t0)
                    ti.mode = 0o644
                    ofh.addfile(ti, io.BytesIO(gz))
                    allst[nm[:-len(".ndjson.gz")]] = st
                    n_out += 1
            for nm, ar in pending:
                nm2, gz, st = ar.get()
                ti = tarfile.TarInfo(nm)
                ti.size = len(gz)
                ti.mtime = int(t0)
                ti.mode = 0o644
                ofh.addfile(ti, io.BytesIO(gz))
                allst[nm[:-len(".ndjson.gz")]] = st
                n_out += 1
            pending = []
        sz = os.path.getsize(dst)
        print(f"[shard] {sh} members={n_out}/{n_in} {sz/2**30:.2f}GiB free={free_gb():.1f}G "
              f"{time.time()-t0:.0f}s", flush=True)
        if n_out != n_in:
            raise SystemExit(f"成员数不符 {sh}: {n_out} != {n_in}")
        os.unlink(src)                     # 新片校验过成员数才删旧片
    json.dump(allst, open(os.path.join(DIST, "amend-stats.json"), "w"), ensure_ascii=False)
    tot = {"rows_in": 0, "rows_out": 0, "dropped_new": 0, "key_changed": 0, "key_unkeyed": 0,
           "n_null": 0, "num_ok": 0, "street_ok": 0, "city_ok": 0, "state_ok": 0, "zip_ok": 0,
           "zip_null": 0, "coord_ok": 0, "coord_null": 0, "bad": 0,
           "grade": {"S": 0, "A": 0, "B": 0, "C": 0}, "moved": {}}
    for st in allst.values():
        for k in tot:
            if k == "grade":
                for g in tot["grade"]:
                    tot["grade"][g] += st["grade"][g]
            elif k == "moved":
                for kk, vv in st["moved"].items():
                    tot["moved"][kk] = tot["moved"].get(kk, 0) + vv
            else:
                tot[k] += st[k]
    json.dump(tot, open(os.path.join(DIST, "amend-total.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(tot, ensure_ascii=False)[:1200])
    print(f"[amend] done {time.time()-t0:.0f}s free={free_gb():.1f}G")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
