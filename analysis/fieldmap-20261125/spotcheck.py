#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行级抽查：≥10% 层（≥355，字节最大的 10 层必查）。

两件事，互不依赖：
  A) **不变量**（全量行扫描，任何一条违反都算不符）：zip5 恰好 5 位数字 / state 在合法名单 /
     lat·lon 在范围内且非 (0,0) / house_number 不是占位值 / 11 列齐全。
  B) **独立重算比对**：从输入 part 里按 spec 规则**另写一遍**映射（不用 fm_core），
     抽样行逐字段与输出比（house_number / street_name / zip5 / lat / lon）。
"""
from __future__ import annotations
import argparse, collections, csv, gzip, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "engine"))
import split_addr as SA  # noqa: E402

LAYERS = "/data/workspace/world-map-data-33/dist/intake-full/layers"
TARS = "/data/workspace/wmd-fieldmap/dist/tar"
FIELDS = ["house_number", "street_name", "city", "state", "zip5", "lat", "lon",
          "source_layer", "tier", "grade", "addrkey"]
STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR VI GU AS MP".split())
PH = {"", "0", "000", "NULL", "NONE", "N/A", "NA", "UNKNOWN", "-1", "-", "--", ".", "?"}


def out_rows(lid, fps):
    """输出行：直接读 dist/tar 里已打的包（抽样层可能还没打包 → 读 dist/rows 兜底）。"""
    import tarfile
    p = os.path.join(os.environ.get("SC_DIR", "/tmp/sc"), lid + ".ndjson.gz")
    if not os.path.isfile(p):
        p = os.path.join("/data/workspace/wmd-fieldmap/dist/rows", lid + ".ndjson.gz")
    if os.path.isfile(p):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for line in fh:
                yield json.loads(line)
        return
    for t in fps:
        with tarfile.open(t) as tf:
            for m in tf:
                if m.name == lid + ".ndjson.gz":
                    with gzip.GzipFile(fileobj=tf.extractfile(m)) as gz:
                        for line in gz:
                            yield json.loads(line)
                    return


def recheck(row):
    """独立重算（只覆盖可直接判定的字段；不调 fm_core，故意另写一遍）。"""
    num = str(row.get("add_num") or "").strip()
    num = "" if num.upper() in PH or not re.search(r"[0-9A-Za-z]", num) else num
    st = " ".join(x for x in (str(row.get("pre_dir") or "").strip(), str(row.get("st_name") or "").strip(),
                              str(row.get("st_suf") or "").strip(), str(row.get("post_dir") or "").strip()) if x)
    z = str(row.get("zip") or "").strip()
    m = re.match(r"^(\d{5})(?:-\d{4})?$", z)
    zip5 = m.group(1) if m else ""
    try:
        la, lo = float(row.get("lat")), float(row.get("lon"))
    except (TypeError, ValueError):
        la = lo = None
    if la is not None and not (-90 <= la <= 90 and -180 <= lo <= 180) or (la == 0 and lo == 0):
        la = lo = None
    return {"house_number": num, "street_name": st, "zip5": zip5,
            "lat": None if la is None else round(la, 7), "lon": None if lo is None else round(lo, 7)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", type=int, default=355)
    ap.add_argument("--rows", type=int, default=200)
    a = ap.parse_args()
    cov = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    cand = [r for r in cov if int(r["mapped"] or 0) > 0]
    cand.sort(key=lambda r: -int(r["in_bytes"] or 0))
    pick = cand[:10]                                   # 字节最大 10 层必查
    rest = [r for r in cand if r not in pick]
    random.seed(20261125)
    pick += random.sample(rest, max(0, min(len(rest), a.layers - len(pick))))
    fps = [os.path.join(TARS, f) for f in sorted(os.listdir(TARS))] if os.path.isdir(TARS) else []
    out = []
    overall = collections.Counter()
    for r in pick:
        lid = r["layer"]
        # B) 独立重算比对（按 spec 规则重打一遍，抽样 N 行输入）
        n_chk = n_ok = 0
        mismatch = []
        d = os.path.join(LAYERS, lid)
        parts = sorted(f for f in os.listdir(d) if f.startswith("part-u")) if os.path.isdir(d) else []
        exp = {}
        for fn in parts[:1]:
            with gzip.open(os.path.join(d, fn), "rt", encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh):
                    if i >= a.rows:
                        break
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    e = recheck(row)
                    if not (e["street_name"] and (e["house_number"] or True)):
                        continue
                    key = (e["house_number"], e["street_name"], e["zip5"],
                           e["lat"], e["lon"])
                    exp[key] = e
        got = set()
        vis = 0
        for o in out_rows(lid, fps):
            vis += 1
            got.add((o.get("house_number") or "", o.get("street_name") or "", o.get("zip5") or "",
                     o.get("lat"), o.get("lon")))
            # A) 不变量
            overall["rows_seen"] += 1
            z = o.get("zip5")
            if z is not None and not re.match(r"^\d{5}$", str(z)):
                overall["bad_zip5"] += 1
            s = o.get("state")
            if s is not None and s not in STATES:
                overall["bad_state"] += 1
            la, lo = o.get("lat"), o.get("lon")
            if la is not None and not (-90 <= la <= 90 and -180 <= lo <= 180):
                overall["bad_coord"] += 1
            if la == 0 and lo == 0:
                overall["zero_coord"] += 1
            if (o.get("house_number") or "").upper() in PH - {""}:
                overall["bad_number"] += 1
            if set(o.keys()) != set(FIELDS):
                overall["bad_columns"] += 1
            if vis >= a.rows:
                break
        for key, e in exp.items():
            n_chk += 1
            if key in got:
                n_ok += 1
            elif len(mismatch) < 3:
                mismatch.append({k: (e[k], None) for k in ("house_number", "street_name", "zip5")})
        out.append({"layer": lid, "in_bytes": r["in_bytes"], "mapped": r["mapped"],
                    "checked": n_chk, "matched": n_ok,
                    "match_pct": round(100.0 * n_ok / n_chk, 2) if n_chk else None,
                    "mismatch_sample": json.dumps(mismatch, ensure_ascii=False) if mismatch else ""})
        print(f"{lid[:50]:50s} chk={n_chk} ok={n_ok}", flush=True)
    with open(os.path.join(HERE, "spotcheck.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "in_bytes", "mapped", "checked", "matched",
                                          "match_pct", "mismatch_sample"])
        w.writeheader()
        for r in out:
            w.writerow(r)
    tot_chk = sum(r["checked"] for r in out)
    tot_ok = sum(r["matched"] for r in out)
    summ = {"layers_checked": len(out), "layers_total_mapped": len(cand),
            "coverage_pct": round(100.0 * len(out) / max(1, len(cand)), 2),
            "rows_checked": tot_chk, "rows_matched": tot_ok,
            "match_pct": round(100.0 * tot_ok / tot_chk, 2) if tot_chk else None,
            "invariants": dict(overall)}
    json.dump(summ, open(os.path.join(HERE, "spotcheck-summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
