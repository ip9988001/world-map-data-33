#!/usr/bin/env python3
"""抽查：把 samples/<STATE>.csv 里的行，对回原始响应（cache/<sha1>.json.gz）。
证明坐标是响应里原样的几何，不是质心/插值/补零。

  python3 spotcheck.py --states DE,NH,IA --n 3
输出 spotcheck/SPOTCHECK.md
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("COORD_CACHE", "/data/coord-work-20261124/cache")
OUT = os.path.join(ROOT, "spotcheck")


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def first_geom(j):
    for ft in j.get("features") or []:
        g = (ft or {}).get("geometry") or {}
        if g.get("y") is not None:
            return g["x"], g["y"], "point"
        for k in ("rings", "paths"):
            if g.get(k):
                return g[k][0][0][0], g[k][0][0][1], k
        if g.get("points"):
            return g["points"][0][0], g["points"][0][1], "points"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", default="DE,NH,IA")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lines, hits = [], 0
    for st in [s.strip() for s in a.states.split(",") if s.strip()]:
        p = os.path.join(ROOT, "samples", f"{st}.csv")
        if not os.path.exists(p):
            continue
        rows = [r for r in csv.DictReader(open(p)) if r["sample_source"] == "arcgis_query"]
        seen, picked = set(), []
        for r in rows:
            if r["layer_url"] in seen:
                continue
            seen.add(r["layer_url"])
            picked.append(r)
        for r in picked[:a.n]:
            gz = os.path.join(CACHE, key_of(r["layer_url"]) + ".json.gz")
            if not os.path.exists(gz):
                lines.append(f"| {st} | {r['layer_url']} | cache 缺失 | — | — |")
                continue
            j = json.load(gzip.open(gz, "rt"))
            fg = first_geom(j)
            ok = (fg and abs(fg[0] - float(r["lon_raw"])) < 1e-7
                  and abs(fg[1] - float(r["lat_raw"])) < 1e-7)
            hits += bool(ok)
            lines.append(
                f"| {st} | {r['layer_url']} | `{os.path.basename(gz)}` | "
                f"{fg[0]:.9f}, {fg[1]:.9f} ({fg[2]}) | "
                f"{float(r['lon_raw']):.9f}, {float(r['lat_raw']):.9f} | {'✅ 一致' if ok else '❌ 不一致'} |")
    with open(os.path.join(OUT, "SPOTCHECK.md"), "w") as f:
        f.write("# 坐标真实性抽查（CSV ↔ 原始响应）\n\n")
        f.write("原始响应缓存在采集机 `/data/coord-work-20261124/cache/<sha1(url)[:16]>.json.gz`，")
        f.write("未提交进仓库（体积原因）；校验方式：`scripts/spotcheck.py --states DE,NH,IA --n 3`。\n\n")
        f.write("| 州 | layer_url | 原始响应 | 响应首个几何顶点 | CSV lon_raw/lat_raw | 结论 |\n")
        f.write("|---|---|---|---|---|---|\n")
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"checked": len(lines), "matched": hits}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
