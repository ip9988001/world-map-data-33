"""坐标证据（沙盒）：把第 6 步前置的坐标样本转成 E6（空间验算）/ E7（源间同址投票）/ 实测 geom_type。

只读：analysis/coord-samples-20261124/samples/*.csv（738,174 行）、analysis/tiger_county/*.json.gz、
registry/dialects.v1.yaml（只读）+ engine/dialects/*.yaml（角色表，与 registry 口径合一）。
不联网、不估算、不插值：没坐标或没地址键的层一律 unknown，并在 detail 里写清缺什么。
几何一律按样本里的真实顶点/真实经纬度算（面/线取的是 rings[0][0]/paths[0][0] 的真实顶点，
不是质心，见 analysis/coord-samples-20261124/REPORT-ALL.md §4）。

用法：python3 sandbox/coord_evidence.py --outdir analysis/auto-spatial-rerun-20261125
"""
import argparse, collections, csv, glob, json, math, os, re, sys, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox.spatial_verify import (COUNTY_DIR, boundary_dist_m, load_thresholds,  # noqa: E402
                                    point_in_ring, rings_of)
# ④ 口径统一：角色表与建键**只有 engine 一份实现**，sandbox 不再自带副本。
#   addr_key  = engine.split_addr.addr_key_split（addr_key + P1 拆串）；
#   roles_of  = registry/dialects.v1.yaml ∪ engine/dialects/*.yaml（两数据源合一）；
#   SUFFIX / street_norm 也来自 engine，供 e7_refpool.py 的同一套键归一复用。
# 导出名保持原样（addr_key / roles_of / street_norm / SUFFIX），下游 summarize.py、
# e7_refpool.py、tier_relax.py 的调用约定一个字节不改。
from engine.split_addr import (SUFFIX, addr_key_split, roles_of,  # noqa: E402
                               street_norm)
addr_key = addr_key_split        # 对外名仍是 addr_key；实现只在 engine/split_addr.py 一份

SAMPLES = os.environ.get("COORD_SAMPLES") or os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
THRESHOLDS = os.path.join(ROOT, "sandbox", "spatial_thresholds.yaml")
CELL = 0.5
FIELDS = ("url,state_scope,geom_type,n_coords,n_uniq,unique_rate,top_point_share,outside_share_us,"
          "outside_share_near_boundary,outside_share_declared_state,e6,e6_detail,sample_fields,"
          "n_addr_rows,n_cmp,n_conflict,conflict_share,e7,e7_detail").split(",")


def county_index(states):
    """bbo- 网格索引：点落时只测同格候选人；超宽县域进 big 表（阿拉斯加跨经线）。"""
    counties = []
    for st in states:
        p = os.path.join(COUNTY_DIR, f"{st}.json.gz")
        if not os.path.isfile(p):
            continue
        for f in json.load(__import__("gzip").open(p, "rt"))["features"]:
            rings = rings_of(f.get("geometry"))
            if rings:
                pts = [(x[0], x[1]) for x in rings[0]]
                counties.append({"rings": rings, "bbox": (min(p[0] for p in pts), min(p[1] for p in pts),
                                                          max(p[0] for p in pts), max(p[1] for p in pts))})
    grid, big = collections.defaultdict(list), []
    for c in counties:
        x0, y0, x1, y1 = c["bbox"]
        cells = [(i, j) for i in range(int(x0 // CELL), int(x1 // CELL) + 1)
                 for j in range(int(y0 // CELL), int(y1 // CELL) + 1)]
        (big.append(c) if len(cells) > 200 else [grid[k].append(c) for k in cells])
    return grid, big


def inside(lon, lat, idx):
    grid, big = idx
    for c in tuple(grid.get((int(lon // CELL), int(lat // CELL)), ())) + tuple(big):
        x0, y0, x1, y1 = c["bbox"]
        if x0 <= lon <= x1 and y0 <= lat <= y1 and any(point_in_ring(lon, lat, r) for r in c["rings"]):
            return True
    return False


def near_boundary(lon, lat, idx, maxd):
    """越界点到最近县界的距离：只看 3x3 邻格 + bbox+0.05° 预筛，够不着就返回哨兵（省算）。
    用途只判「越界是不是县界裁剪/水面顶点造成的噪声」，不参与其他判据。"""
    grid, big = idx
    i0, j0 = int(lon // CELL), int(lat // CELL)
    best = maxd * 10
    for c in [c for i in (i0 - 1, i0, i0 + 1) for j in (j0 - 1, j0, j0 + 1)
              for c in grid.get((i, j), ())] + big:
        x0, y0, x1, y1 = c["bbox"]
        if x0 - 0.05 <= lon <= x1 + 0.05 and y0 - 0.05 <= lat <= y1 + 0.05:
            best = min(best, boundary_dist_m(lon, lat, c["rings"]))
    return best


def haversine_m(a, b):
    dx = (a[0] - b[0]) * 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, (a[1] - b[1]) * 110540.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125"))
    args = ap.parse_args()
    fuse, _ = load_thresholds()
    doc = yaml.safe_load(open(THRESHOLDS, encoding="utf-8"))["e7"]
    e7t = {k: v["value"] for k, v in doc.items() if isinstance(v, dict) and "value" in v}
    ROLES = roles_of()
    states = sorted(os.path.basename(p)[:2] for p in glob.glob(os.path.join(COUNTY_DIR, "*.json.gz")))
    us_idx = county_index(states)
    st_idx = {s: county_index([s]) for s in states}
    rows, keys, urlkeys, sfields = (collections.defaultdict(list), collections.defaultdict(list),
                                    collections.defaultdict(set), collections.defaultdict(set))
    for p in sorted(glob.glob(os.path.join(os.environ.get("COORD_SAMPLES") or SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r["layer_url"] or f"local:{r['layer_id']}"
            g = r["geom_type"].split("(")[0].replace("esriGeometry", "").lower()
            rows[u].append((float(r["lon"]), float(r["lat"]), r["state"], g))
            af = json.loads(r["addr_fields_json"] or "{}")
            sfields[u] |= set(af)
            k = addr_key(af, ROLES, r["state"])
            if k:
                keys[k].append((u, float(r["lon"]), float(r["lat"])))
                urlkeys[u].add(k)
    out = []
    for u in sorted(rows):
        rs = rows[u]
        coords = [(x, y) for x, y, _, _ in rs]
        n, cnt = len(coords), collections.Counter(coords)
        m = {"url": u, "state_scope": rs[0][2], "geom_type": rs[0][3], "n_coords": n, "n_uniq": len(cnt),
             "sample_fields": "|".join(sorted(sfields[u])),
             "unique_rate": round(len(cnt) / n, 4) if n else 0.0,
             "top_point_share": round(max(cnt.values()) / n, 4) if n else 0.0}
        if n < fuse["min_sample_rows"]:
            m.update(outside_share_us="", outside_share_declared_state="", e6="unknown",
                     e6_detail=f"有效坐标 {n} < min_sample_rows={fuse['min_sample_rows']}（样本不足，不判）")
        else:
            outs = [c for c in coords if not inside(c[0], c[1], us_idx)]
            noisy = sum(1 for c in outs
                        if near_boundary(c[0], c[1], us_idx, fuse["max_cross_boundary_dist_m"])
                        <= fuse["max_cross_boundary_dist_m"])
            m["outside_share_near_boundary"] = round(noisy / n, 4)
            m["outside_share_us"] = round((len(outs) - noisy) / n, 4)
            st = rs[0][2]
            if st in st_idx:
                m["outside_share_declared_state"] = round(
                    sum(1 for c in coords if not inside(c[0], c[1], st_idx[st])) / n, 4)
            else:
                m["outside_share_declared_state"] = ""
            bad = [k for k, hit in (("outside_share", m["outside_share_us"] > fuse["max_outside_share"]),
                                    ("coord_cluster", m["top_point_share"] > fuse["max_top_point_share"]),
                                    ("coord_dup", m["unique_rate"] < fuse["min_unique_coord_rate"])) if hit]
            m.update(e6="hit" if bad else "clear",
                     e6_detail=((f"命中 {','.join(bad)}；" if bad else "未命中任何熔断；") +
                                f"n={n} 唯一率={m['unique_rate']} "
                                f"最热坐标占比={m['top_point_share']} 县界外占比={m['outside_share_us']} "
                                f"（≤{int(fuse['max_cross_boundary_dist_m'])}m 县界裁剪噪声 {m['outside_share_near_boundary']}，"
                                f"声明州外占比={m['outside_share_declared_state'] or 'na'}）"))
        mine = urlkeys[u]
        cmp_n = conf = 0
        addr_rows = sum(1 for k in mine for x in keys[k] if x[0] == u)   # 有地址键的行数（不看他源）
        for k in mine:
            others = [x for x in keys[k] if x[0] != u]
            for (pu, lon, lat) in [x for x in keys[k] if x[0] == u] if others else ():
                cmp_n += 1
                if min(haversine_m((lon, lat), (o[1], o[2])) for o in others) > e7t["max_addr_conflict_m"]:
                    conf += 1
        m.update(n_addr_rows=addr_rows, n_cmp=cmp_n, n_conflict=conf,
                 conflict_share=round(conf / cmp_n, 4) if cmp_n else "")
        if not addr_rows:
            m.update(e7="unknown", e7_detail="本层样本无『门牌+街名』键（n_addr_rows=0）→ 无同址可比")
        elif cmp_n < e7t["min_cmp_rows"]:
            m.update(e7="unknown", e7_detail=f"跨源同址可比值 n_cmp={cmp_n} < min_cmp_rows="
                                             f"{e7t['min_cmp_rows']}（地址键不与他人重合，投不出票）")
        else:
            m.update(e7="hit" if m["conflict_share"] > e7t["max_conflict_share"] else "clear",
                     e7_detail=(f"同址可比 {cmp_n} 行，冲突 {conf} 行（>{e7t['max_addr_conflict_m']}m 记为冲突），"
                                f"冲突占比 {m['conflict_share']}"))
        out.append(m)
    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "coord-evidence.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, restval="")
        w.writeheader()
        w.writerows(out)
    c = collections.Counter((r["e6"], r["e7"]) for r in out)
    print("urls", len(out), "e6", collections.Counter(r["e6"] for r in out),
          "e7", collections.Counter(r["e7"] for r in out), "pairs", dict(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
