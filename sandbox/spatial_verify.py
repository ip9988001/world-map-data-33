"""空间验算（沙盒）：行政边界点落判定 + 跨边界距离 + 层内统计离群。
只读 analysis/tiger_county/*.json.gz（TIGERweb 州县界 51 州 / 3.0MB / fetched 2026-10-30）；
不联网、不调地理编码、不写 DB；缺数据一律显式 unavailable（不估算、不填占位值）。
"""
import argparse, collections, csv, gzip, json, math, os, statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COUNTY_DIR = os.path.join(ROOT, "analysis", "tiger_county")
FIXTURE_DIR = os.path.join(ROOT, "sandbox", "fixtures")
MANIFEST = os.path.join(FIXTURE_DIR, "spatial_manifest.json")
THRESHOLDS = os.path.join(ROOT, "sandbox", "spatial_thresholds.yaml")
LOCAL_FIELDS = os.path.join(ROOT, "analysis", "full-inventory-20261124", "inventory-local-fields.csv")
FIELDS = ("kind,key,n,unique_rate,top_point_share,outside_share,max_cross_boundary_dist_m,"
          "p50_boundary_dist_m,p95_boundary_dist_m,fuse,verdict,note").split(",")


def rings_of(geom):
    t, c = (geom or {}).get("type"), (geom or {}).get("coordinates") or []
    if t == "Polygon":
        return [r for r in c if len(r) >= 3]
    return [r for poly in c for r in poly if len(r) >= 3] if t == "MultiPolygon" else []
def point_in_ring(lon, lat, ring):
    inside = False  # 射线法（奇偶规则）；经纬度当平面用，县界尺度与球面无差别
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside
def seg_dist_m(lon, lat, a, b):
    kx, ky = math.cos(math.radians(lat)) * 111320.0, 110540.0
    px, py, qx, qy = (lon - a[0]) * kx, (lat - a[1]) * ky, (b[0] - a[0]) * kx, (b[1] - a[1]) * ky
    t = 0.0 if qx * qx + qy * qy == 0 else max(0.0, min(1.0, (px * qx + py * qy) / (qx * qx + qy * qy)))
    return math.hypot(px - t * qx, py - t * qy)
def boundary_dist_m(lon, lat, rings):
    return min(seg_dist_m(lon, lat, r[i], r[(i + 1) % len(r)]) for r in rings for i in range(len(r)))
def building_outline_dist_m(*_a, **_k):
    raise NotImplementedError("no building footprint source in repo")


def load_counties(state):
    path = os.path.join(COUNTY_DIR, f"{state}.json.gz")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"county geometry missing: {path}（未跑，不估）")
    out = []
    for f in json.load(gzip.open(path, "rt"))["features"]:
        rings = rings_of(f.get("geometry"))
        if rings:
            pts = [(p[0], p[1]) for p in rings[0]]
            out.append({"geoid": f["properties"].get("GEOID"), "rings": rings,
                        "bbox": (min(p[0] for p in pts), min(p[1] for p in pts),
                                 max(p[0] for p in pts), max(p[1] for p in pts))})
    return out  # bbox 只用于快速排除；精确判定靠 point_in_ring


def load_thresholds(path=THRESHOLDS):
    import yaml
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    return ({k: v["value"] for k, v in doc["fuse"].items()}, {k: v["value"] for k, v in doc["p95"].items()})


def verify_layer(coords, counties, declared_fips, fuse):
    """越界只对『声明县』判；跨边界距离只对越界行量；县内点到界距离只进 P95 相对判据。"""
    n, cnt = len(coords), collections.Counter(coords)
    m = {"n": n, "unique_rate": round(len(cnt) / n, 4) if n else 0.0,
         "top_point_share": round(max(cnt.values()) / n, 4) if n else 0.0, "outside_share": 0.0,
         "max_cross_boundary_dist_m": 0.0, "p50_boundary_dist_m": 0.0, "p95_boundary_dist_m": 0.0, "fuse": []}
    if n < fuse["min_sample_rows"]:
        return {**m, "verdict": "unavailable", "note": f"有效坐标 {n} < min_sample_rows"}
    declared = [c for c in counties if c["geoid"] == declared_fips]
    if not declared:
        return {**m, "verdict": "unavailable", "note": f"县界缺 {declared_fips}（未跑，不估）"}
    rings, inside, cross, dists = declared[0]["rings"], 0, [], []
    for lon, lat in coords:
        hit = any(point_in_ring(lon, lat, r) for r in rings)
        inside += hit
        (dists if hit else cross).append(boundary_dist_m(lon, lat, rings))
    ds = sorted(dists)
    m.update({"outside_share": round((n - inside) / n, 4),
              "max_cross_boundary_dist_m": round(max(cross) if cross else 0.0, 1),
              "p50_boundary_dist_m": round(statistics.median(ds) if ds else 0.0, 1),
              "p95_boundary_dist_m": round(ds[min(len(ds) - 1, math.ceil(0.95 * len(ds)) - 1)] if ds else 0.0, 1)})
    m["fuse"] = [k for k, bad in (
        ("outside_share", m["outside_share"] > fuse["max_outside_share"]),
        ("cross_boundary_dist", m["max_cross_boundary_dist_m"] > fuse["max_cross_boundary_dist_m"]),
        ("coord_cluster", m["top_point_share"] > fuse["max_top_point_share"]),
        ("coord_dup", m["unique_rate"] < fuse["min_unique_coord_rate"])) if bad]
    m["verdict"], m["note"] = ("fuse", "命中 " + ",".join(m["fuse"])) if m["fuse"] else ("green", "")
    return m


def null_rate_jumps(rows):
    """层内字段分布突变：同一字段层间中位非空率 ≥0.9、某层该字段 rate==0 → {layer: [field]}。"""
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("rate") and r.get("field"):
            by[r["field"]].append((r["layer"], float(r["rate"])))
    jumps = collections.defaultdict(list)
    for field, pairs in by.items():
        if len(pairs) >= 10 and statistics.median(x[1] for x in pairs) >= 0.9:
            for layer, rate in pairs:
                if rate == 0.0:
                    jumps[layer].append(field)
    return dict(jumps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis", "auto-spatial-20261124", "spatial-findings.csv"))
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--p95-mult", type=float, default=3.0)
    args = ap.parse_args()
    fuse, p95t = load_thresholds()
    out = []
    for spec in json.load(open(MANIFEST, encoding="utf-8"))["fixtures"]:
        rows = json.load(open(os.path.join(FIXTURE_DIR, spec["file"]), encoding="utf-8"))
        coords = [(float(r[spec["lon_key"]]), float(r[spec["lat_key"]])) for r in rows
                  if isinstance(r.get(spec["lon_key"]), (int, float)) and isinstance(r.get(spec["lat_key"]), (int, float))]
        m = verify_layer(coords, load_counties(spec["state"]), spec["county_fips"], fuse)
        rel = m["n"] >= fuse["min_sample_rows"] and m["p95_boundary_dist_m"] > args.p95_mult * max(
            m["p50_boundary_dist_m"], 1e-9)
        m["fuse_text"] = "|".join(m["fuse"]) or ("p95_relative" if rel else "")
        out.append(["fixture_layer", spec["name"], m["n"], m["unique_rate"], m["top_point_share"],
                    m["outside_share"], m["max_cross_boundary_dist_m"], m["p50_boundary_dist_m"],
                    m["p95_boundary_dist_m"], m["fuse_text"], m["verdict"],
                    f"coords={len(coords)}/{len(rows)} declared_fips={spec['county_fips']} "
                    f"building_outline=unavailable {m['note']}".strip()])
    jumps = {}
    if os.path.isfile(LOCAL_FIELDS):
        with open(LOCAL_FIELDS, encoding="utf-8") as fh:
            jumps = null_rate_jumps(list(csv.DictReader(fh)))
        out += [["null_rate_jump", l, len(fs), "", "", "", "", "", "", "null_rate_jump", "fuse",
                 "字段层内整体缺失: " + ",".join(sorted(fs)[:8])]
                for l, fs in sorted(jumps.items(), key=lambda kv: -len(kv[1]))]
        print(f"null_rate_jump layers={len(jumps)} fields={sum(len(v) for v in jumps.values())}")
    else:
        print("null_rate_jump: unavailable (inventory-local-fields.csv 缺)")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(FIELDS)
        w.writerows(out)
    print("wrote", args.out, "rows", len(out), "seed", args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
