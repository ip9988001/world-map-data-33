#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宗地 rings 落盘的存储成本 —— 只出数，不访问上游、不动任何采集。

问题：1,238 个宗地层（36,473,089 行）如果把 `rings` 存下来，要多占多少空间？
      在 GitHub Release（单文件 2GB / 单 Release 1,000 资产）下「存原始 rings」可行吗？

哪些是实测（全部离线，只用本机已有数据）：
  ① 每顶点字节数 —— 本机真实坐标值（dist/intake-full 点层 lat/lon，就是同一批 ArcGIS 服务
     outSR=4326 吐出来的 double）→ json 序列化后的字符数分布，全精度与 6 位小数各一份
  ② gzip 压缩率 —— 两种口径：本机真实环（analysis/tiger_county 县界，真实经纬度数组）；
     以及用真实坐标值拼出的「宗地尺度伪环」（只为量压缩率，不参与字节数）
  ③ 行数 —— schema/field-map-v2.json 的 rows_total（与 collect/parcel_audit.json 的在盘行数
     逐层核对，两者一致：36,473,089）
  ④ ①档（只加质心）的每行增量 —— 用本机真实采集行加 `_lat`/`_lon` 后重新压，与基线对比
  ⑤ 1e-5° 简化（RDP）到底能删多少顶点 —— 在本机真实环上实测，并给出边长分布

唯一无法离线实测的是「每宗地几个顶点 v」（本机只有 Shape__Length/Shape__Area，没有 rings），
所以三档都按 v = 5/8/12/24 给敏感性表 —— 结论不依赖猜 v。

用法：
  python3 analysis/parcel_rings_cost.py            # 人看
  python3 analysis/parcel_rings_cost.py --json     # 机读 + 写 analysis/parcel-rings-cost.json
"""
from __future__ import annotations

import argparse
import glob
import gzip
import io
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_JSON = os.path.join(HERE, "parcel-rings-cost.json")

GB = 1e9                      # 十进制 GB（GitHub 的 2 GB 上限也是十进制：2e9 B）
FILE_CAP = 2_000_000_000      # 单资产上限
ASSET_CAP = 1000              # 单 Release 资产上限
PART_ROWS = 50_000            # pilot 的 part 行数上界（CHUNK）


# ---------------------------------------------------------------- 工具
def _gz_size(text: str) -> int:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as g:
        g.write(text.encode())
    return len(buf.getvalue())


def _ring_text(ring, decimals):
    pts = [[round(float(p[0]), decimals), round(float(p[1]), decimals)] for p in ring]
    return json.dumps(pts, separators=(",", ":"))


# ---------------------------------------------------------------- ① 每顶点字符数
def coordinate_digit_stats(limit=300_000):
    """真实 ArcGIS 4326 坐标值 → json 序化字符数（含负号/小数点/方括号/逗号）。"""
    xs, ys, x6, y6, pts = [], [], [], [], []
    files = sorted(glob.glob(os.path.join(ROOT, "dist", "intake-full", "layers", "*",
                                          "addr.*.ndjson.gz")))
    files += sorted(glob.glob(os.path.join(ROOT, "dist", "intake", "*.ndjson")))[:40]
    for fp in files:
        if len(xs) >= limit:
            break
        op = gzip.open if fp.endswith(".gz") else open
        try:
            with op(fp, "rt", encoding="utf-8") as f:
                for line in f:
                    if len(xs) >= limit:
                        break
                    try:
                        d = json.loads(line)
                    except Exception:                        # noqa: BLE001
                        continue
                    a, b = d.get("latitude"), d.get("longitude")
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        xs.append(len(json.dumps(b)))        # 经度（全精度）
                        ys.append(len(json.dumps(a)))        # 纬度
                        x6.append(len(json.dumps(round(b, 6))))
                        y6.append(len(json.dumps(round(a, 6))))
                        pts.append((float(b), float(a)))
        except Exception:                                    # noqa: BLE001
            continue
    if not xs:
        return None
    # 一个顶点 = [lon,lat] → 1 个 '[' + lon + ',' + lat + ']'
    per_v = [x + y + 3 for x, y in zip(xs, ys)]
    per_v6 = [x + y + 3 for x, y in zip(x6, y6)]
    s = sorted(per_v)
    return {"n": len(per_v),
            "full_median": statistics.median(per_v), "full_mean": round(statistics.fmean(per_v), 2),
            "full_p10": s[len(s) // 10], "full_p90": s[len(s) * 9 // 10],
            "six_dec_median": statistics.median(per_v6),
            "six_dec_mean": round(statistics.fmean(per_v6), 2),
            "six_dec_shrink": round(statistics.median(per_v6) / statistics.median(per_v), 3),
            "_points": pts[:20000]}


# ---------------------------------------------------------------- ② gzip 压缩率
def load_county_rings(limit_rings=4000):
    """本机真实环（县界，GeoJSON，经纬度）。"""
    rings = []
    for fp in sorted(glob.glob(os.path.join(HERE, "tiger_county", "*.json.gz"))):
        try:
            d = json.load(gzip.open(fp, "rt"))
        except Exception:                                    # noqa: BLE001
            continue
        for ft in (d.get("features") or []):
            g = ft.get("geometry") or {}
            if str(g.get("type") or "") != "Polygon":
                continue
            for ring in (g.get("coordinates") or []):
                if len(ring) >= 4:
                    rings.append(ring)
        if len(rings) >= limit_rings:
            break
    return rings[:limit_rings]


def gzip_stats(rings, decimals, tag):
    """把环按「一面一行」写 ndjson 再压（与 part 文件同样的打包方式）。"""
    if not rings:
        return None
    body = "".join('{"rings":[%s]}\n' % _ring_text(r, decimals)[1:-1] for r in rings)
    nv = sum(len(r) for r in rings)
    raw = len(body.encode())
    comp = _gz_size(body)
    return {"tag": tag, "rings": len(rings), "vertices": nv,
            "raw_bytes_per_vertex": round(raw / nv, 2),
            "gz_bytes_per_vertex": round(comp / nv, 2),
            "ratio": round(comp / raw, 4)}


def pseudo_rings(points, v=12, max_rings=4000):
    """用真实坐标值拼「宗地尺度」的伪环（只为量压缩率）。

    取同层相邻点（同县内 → 前几位小数相同，与真实宗地环的数字结构一致），
    每个环 v 个顶点、按 1e-4° 量级偏移 —— 不参与任何字节数口径，只喂 gzip。
    """
    out = []
    for i in range(0, min(len(points), v * max_rings), v):
        chunk = points[i:i + v]
        if len(chunk) < v:
            break
        x0, y0 = chunk[0]
        ring = [[x0 + j * 1.1e-4, y0 + j * 0.9e-4] for j in range(v)]
        ring[-1] = ring[0][:]
        out.append(ring)
    return out


def edge_stats(rings):
    e = []
    for r in rings:
        for i in range(len(r) - 1):
            dx = float(r[i + 1][0]) - float(r[i][0])
            dy = float(r[i + 1][1]) - float(r[i][1])
            e.append((dx * dx + dy * dy) ** 0.5)
    if not e:
        return None
    e.sort()
    return {"n": len(e), "median_deg": round(e[len(e) // 2], 7),
            "p10_deg": round(e[len(e) // 10], 7),
            "under_1e-5_pct": round(100.0 * sum(1 for x in e if x < 1e-5) / len(e), 2)}


# ---------------------------------------------------------------- RDP（1e-5°）
def _seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2) ** 0.5


def rdp(pts, tol):
    """道格拉斯-普克，迭代实现（递归在老环上会爆栈）。"""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        best, idx = -1.0, -1
        for k in range(i + 1, j):
            d = _seg_dist(pts[k], a, b)
            if d > best:
                best, idx = d, k
        if best > tol:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def simplify_stats(rings, tol=1e-5, limit=400):
    before = after = 0
    per_ring = []
    for r in rings[:limit]:
        pts = [(float(p[0]), float(p[1])) for p in r]
        kept = len(rdp(pts, tol))
        before += len(pts)
        after += kept
        per_ring.append(kept / len(pts))
    if not before:
        return None
    per_ring.sort()
    return {"tolerance_deg": tol, "rings": len(per_ring), "vertices_before": before,
            "vertices_after": after, "keep_ratio": round(after / before, 4),
            "median_ring_keep": round(per_ring[len(per_ring) // 2], 4)}


# ---------------------------------------------------------------- ③ 行数
def parcel_rows():
    """宗地层行数：field-map 的 rows_total 与 parcel_audit 在盘行数互相核对。"""
    fm_rows, n_parcel = 0, 0
    fmap = os.path.join(ROOT, "schema", "field-map-v2.json")
    if os.path.exists(fmap):
        d = json.load(open(fmap, encoding="utf-8"))
        for v in (d.get("layers") or {}).values():
            if (v or {}).get("src_kind") == "parcel_situs":
                n_parcel += 1
                fm_rows += int(v.get("rows_total") or 0)
    audit_rows, audit_layers, top = 0, 0, []
    ap = os.path.join(ROOT, "collect", "parcel_audit.json")
    if os.path.exists(ap):
        d = json.load(open(ap, encoding="utf-8"))
        for lid, v in (d.get("layers") or {}).items():
            r = int(v.get("rows") or 0)
            if r > 0:
                audit_layers += 1
                audit_rows += r
                top.append((r, lid))
    top.sort(reverse=True)
    return {"parcel_layers": n_parcel, "rows_field_map": fm_rows,
            "layers_with_assets": audit_layers, "rows_on_disk": audit_rows,
            "agree": fm_rows == audit_rows, "largest_layers": top[:3]}


# ---------------------------------------------------------------- ④ 只加质心的增量
def centroid_increment(sample_rows=20_000):
    """只加 `_lat`/`_lon`：用本机**真实采集行**（collect/out 的 part，含 raw 属性）+ 真实坐标值。

    两个坑先排掉：
      · 行必须是采集落盘格式（1.2 KB/行、带 raw），不能拿 intake 表行（60 B/行）算占比
      · 坐标必须逐行不同 —— 同一个值重复 2 万次会让 gzip 白送一个「几乎免费」的假结论
    """
    parts = sorted(glob.glob(os.path.join(ROOT, "collect", "out", "*", "*.ndjson.gz")))
    rows = []
    for fp in parts:
        with gzip.open(fp, "rt", encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
                if len(rows) >= sample_rows:
                    break
        if len(rows) >= sample_rows:
            break
    coords = []
    for fp in sorted(glob.glob(os.path.join(ROOT, "dist", "intake", "*.ndjson"))):
        with open(fp, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:                        # noqa: BLE001
                    continue
                a, b = d.get("latitude"), d.get("longitude")
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    coords.append((float(a), float(b)))
                if len(coords) >= len(rows):
                    break
        if len(coords) >= len(rows):
            break
    if not rows or len(coords) < len(rows):
        return None

    def size(recs):
        body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
        return len(body.encode()), _gz_size(body)

    def fill(rec, la, lo, dup):
        r2 = dict(rec)
        r2["lat"], r2["lon"] = la, lo                          # 必需字段（宗地层原来是 null）
        if dup:
            r2["_lat"], r2["_lon"] = la, lo                    # 与 NAD 口径同名的第二份
        return r2

    # 甲：宗地层现状（lat/lon 为 null）
    nulled = []
    for r in rows:
        r2 = dict(r)
        r2["lat"] = r2["lon"] = None
        nulled.append(r2)
    n_raw, n_gz = size(nulled)
    # 乙：只填 lat/lon（一份坐标）
    single = [fill(r, la, lo, False) for r, (la, lo) in zip(rows, coords)]
    s_raw, s_gz = size(single)
    # 丙：lat/lon + _lat/_lon（两份坐标，NAD 口径并存）
    dual = [fill(r, la, lo, True) for r, (la, lo) in zip(rows, coords)]
    d_raw, d_gz = size(dual)
    n = len(rows)
    return {"rows": n,
            "null_latlon_bytes_per_row_gz": round(n_gz / n, 2),
            "single_bytes_per_row_gz": round(s_gz / n, 2),
            "dual_bytes_per_row_gz": round(d_gz / n, 2),
            "delta_single_bytes_per_row_gz": round((s_gz - n_gz) / n, 2),
            "delta_dual_bytes_per_row_gz": round((d_gz - n_gz) / n, 2),
            "delta_single_bytes_per_row_raw": round((s_raw - n_raw) / n, 2),
            "delta_dual_bytes_per_row_raw": round((d_raw - n_raw) / n, 2)}


# ---------------------------------------------------------------- 汇总
def tier_table(rows, per_vertex, ratio, vertices=(5, 8, 12, 24)):
    """每行 rings 字节 = v × 每顶点字节；压缩后 = 原始 × 实测压缩率。"""
    out = {}
    for v in vertices:
        raw_row = per_vertex * v
        gz_row = raw_row * ratio
        out[str(v)] = {"raw_bytes_per_row": round(raw_row),
                       "gz_bytes_per_row": round(gz_row),
                       "total_raw_GB": round(rows * raw_row / GB, 2),
                       "total_gz_GB": round(rows * gz_row / GB, 2)}
    return out


# ---------------------------------------------------------------- ⑤ 几何补采估算
# 只算账，不发请求：1,038 个 geom_missing 层补质心要多少次上游调用 / 多少行 / 多久
def backfill_plan(page_cap_default=2000, retry_factor=1.05, payload_per_row=100):
    """输入全部来自本地：coord-salvage-v1.json（哪些层缺几何）+ layer_plan.csv（每层实测页大小）。

    payload_per_row=100 B 是「只要 OID + centroid」的估算：
      {"attributes":{"OBJECTID":123},"centroid":{"x":-97.1234567890123,"y":32.1}}
    """
    import csv

    plan = {}
    plan_f = os.path.join(ROOT, "collect", "layer_plan.csv")
    if os.path.exists(plan_f):
        with open(plan_f, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    plan[row["layer_id"]] = int(float(row.get("pagesize") or 0))
                except Exception:                        # noqa: BLE001
                    plan[row["layer_id"]] = 0
    cs = os.path.join(ROOT, "schema", "coord-salvage-v1.json")
    if not os.path.exists(cs):
        return None
    d = json.load(open(cs, encoding="utf-8"))
    gm = [r for r in (d.get("records") or []) if r.get("status") == "geom_missing"]
    pages = counts = rows = 0
    for r in gm:
        n = int(r.get("rows") or 0)
        lid = r.get("layer") or r.get("src_layer") or r.get("src_layer_id") or ""
        ps = plan.get(lid) or 0
        ps = min(ps, page_cap_default) if ps > 0 else page_cap_default
        rows += n
        pages += -(-n // max(1, ps))                 # ceil
        counts += 1
    req = int((pages + counts) * retry_factor)
    return {"layers": len(gm), "rows": rows, "pages": pages, "count_queries": counts,
            "requests_with_retry": req,
            "payload_per_row_bytes": payload_per_row,
            "est_payload_GB": round(rows * payload_per_row / GB, 2),
            "requests": req}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    coord = coordinate_digit_stats()
    rings = load_county_rings()
    gz_county = gzip_stats(rings, 6, "本机真实县界环（6 位小数）")
    ps = pseudo_rings((coord or {}).get("_points") or [])
    gz_pseudo6 = gzip_stats(ps, 6, "真实坐标值伪环（6 位小数）")
    gz_pseudoF = gzip_stats(ps, 9, "真实坐标值伪环（全精度）")
    edges = edge_stats(rings)
    sim = simplify_stats(rings)
    rows = parcel_rows()
    cen = centroid_increment()
    bf = backfill_plan()

    pv_full = (coord or {}).get("full_median") or 39
    pv_6 = (coord or {}).get("six_dec_median") or 22
    ratio_full = (gz_pseudoF or gz_county or {}).get("ratio") or 0.3
    ratio_6 = (gz_pseudo6 or gz_county or {}).get("ratio") or 0.3
    keep = (sim or {}).get("keep_ratio") or 1.0

    n_rows = rows["rows_field_map"] or rows["rows_on_disk"]
    tier_raw = tier_table(n_rows, pv_full, ratio_full)          # ③ 原始 rings（全精度）
    tier_sim = tier_table(n_rows, pv_6 * keep, ratio_6)        # ② 6 位小数 + 1e-5 RDP

    coord_out = dict(coord or {})
    coord_out.pop("_points", None)               # 采样点不落盘（20k 对，纯噪音）
    doc = {"generated_at": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "coordinate_chars": coord_out, "gzip_county_rings": gz_county,
           "gzip_pseudo_6dec": gz_pseudo6, "gzip_pseudo_full": gz_pseudoF,
           "edge_length_deg": edges, "simplify_1e-5": sim, "rows": rows,
           "centroid_increment": cen,
           "tier_raw_rings": tier_raw, "tier_simplified_rings": tier_sim,
           "backfill_plan": bf,
           "params_used": {"per_vertex_full": pv_full, "per_vertex_6dec": pv_6,
                           "gz_ratio_full": ratio_full, "gz_ratio_6dec": ratio_6,
                           "rdp_keep_ratio": keep},
           "limits": {"single_file_bytes": FILE_CAP, "assets_per_release": ASSET_CAP,
                      "part_rows": PART_ROWS}}
    json.dump(doc, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps(doc, ensure_ascii=False, indent=1))
        return 0

    print("① 每顶点字节（本机真实坐标值 %s 个）" % (coord or {}).get("n"))
    if coord:
        print("   全精度：中位 %s / 均值 %s / p10 %s / p90 %s 字节"
              % (coord["full_median"], coord["full_mean"], coord["full_p10"], coord["full_p90"]))
        print("   6 位小数：中位 %s 字节（缩到 %.0f%%，≈1e-6°=0.11 m，宗地足够）"
              % (coord["six_dec_median"], 100 * coord["six_dec_shrink"]))
    print("② gzip 压缩率")
    for g in (gz_county, gz_pseudo6, gz_pseudoF):
        if g:
            print("   %-28s 原始 %6.1f B/顶点 → 压缩 %5.2f B/顶点（比率 %.2f，%s 顶点）"
                  % (g["tag"], g["raw_bytes_per_vertex"], g["gz_bytes_per_vertex"],
                     g["ratio"], f"{g['vertices']:,}"))
    if edges:
        print("   环边长（度）：中位 %.5f（≈%.0f m）/ p10 %.5f / 小于 1e-5 的边 %.2f%%"
              % (edges["median_deg"], edges["median_deg"] * 111000,
                 edges["p10_deg"], edges["under_1e-5_pct"]))
    if sim:
        print("   RDP 容差 1e-5°：保留顶点 %.2f%%（%s 个环 / %s 个顶点实测）"
              % (100 * sim["keep_ratio"], sim["rings"], f"{sim['vertices_before']:,}"))
    print("③ 行数：%d 个宗地层 / %s 行（field-map rows_total 与在盘行数一致=%s）"
          % (rows["parcel_layers"], f"{n_rows:,}", rows["agree"]))
    if cen:
        print("④ 只加质心实测（本机真实采集行 %d 行，坐标逐行不同）" % cen["rows"])
        print("   lat/lon 为 null 时 %s B/行 → 只填 lat/lon %s B/行（+%s）→ 再存 _lat/_lon %s B/行（+%s）"
              % (cen["null_latlon_bytes_per_row_gz"], cen["single_bytes_per_row_gz"],
                 cen["delta_single_bytes_per_row_gz"], cen["dual_bytes_per_row_gz"],
                 cen["delta_dual_bytes_per_row_gz"]))
    print()
    print("三档存储增量（%s 行；十进制 GB）" % f"{n_rows:,}")
    print("  v/宗地 | ③原始 rings 未压 | ③原始 rings 压缩 | ②简化(6位+1e-5) 压缩 | ①只存质心(一份/两份)")
    cen_gb = (cen or {}).get("delta_single_bytes_per_row_gz", 0) * n_rows / GB
    cen_gb2 = (cen or {}).get("delta_dual_bytes_per_row_gz", 0) * n_rows / GB
    for v in tier_raw:
        print("  v=%-4s | %13.1f GB | %14.2f GB | %19.2f GB | %8.3f / %.3f GB"
              % (v, tier_raw[v]["total_raw_GB"], tier_raw[v]["total_gz_GB"],
                 tier_sim[v]["total_gz_GB"], cen_gb, cen_gb2))
    print()
    print("写入 %s" % OUT_JSON)
    if bf:
        print()
        print("⑤ 几何补采（1,038 个 geom_missing 层，只算账不发请求）")
        print("   %d 层 / %s 行 → 分页 %s 次 + count %s 次 = %s 次请求（含 %.0f%% 重试）"
              % (bf["layers"], f"{bf['rows']:,}", f"{bf['pages']:,}",
                 f"{bf['count_queries']:,}", f"{bf['requests_with_retry']:,}", 5.0))
        print("   只取 OID+centroid ≈ %s B/行 → 总流量 ≈ %.1f GB"
              % (bf["payload_per_row_bytes"], bf["est_payload_GB"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
