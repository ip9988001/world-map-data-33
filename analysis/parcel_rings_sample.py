#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""20 层宗地 rings 实测 —— 每行 rings 到底多少字节（中位/均值），外推 1,238 层。

和 `parcel_rings_cost.py` 的分工：
  · 那个用**本机已有数据**离线推算（本机没有 rings，所以 v 只能给敏感性表）
  · 这个**抽 20 层真 upstream 取 rings**，把 v 和每行字节数从「假设」变成「实测」

只读：`resultRecordCount=8`、`returnGeometry=true`、`outSR=4326`，不写库、不碰采集账本。
分层抽样：按 `rows_total` 降序取分位点（每档一层），避免全挑大层或全挑小层。

用法：
  python3 analysis/parcel_rings_sample.py            # 人看
  python3 analysis/parcel_rings_sample.py --json     # 机读 + 写 analysis/parcel-rings-sample.json
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_JSON = os.path.join(HERE, "parcel-rings-sample.json")
FIELD_MAP = os.path.join(ROOT, "schema", "field-map-v2.json")

SAMPLE_LAYERS = 20          # 目标层数
MAX_TRIES = 34              # 失败就往后补，最多试这么多层
FEATS = 8                   # 每层取几条要素
TIMEOUT = 25
DECIMALS_SIMPLE = 6         # ②档：6 位小数 ≈ 0.11 m
RDP_EPS = 1e-5              # ②档：RDP 1e-5° ≈ 1.1 m
GB = 1e9


# ------------------------------------------------------------------ 取数
def _get(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "world-map-data/rings-sample"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def sample_layer(url):
    """取一层面层要素，返回 [{rings:[[x,y],...]}...]（已是 4326）。"""
    q = urllib.parse.urlencode({
        "where": "1=1", "outFields": "1", "returnGeometry": "true",
        "outSR": "4326", "resultRecordCount": FEATS, "f": "json",
    }, safe=",*")
    r = _get(url.rstrip("/") + "/query?" + q)
    if "error" in r:
        raise RuntimeError("upstream error: %s" % json.dumps(r["error"], ensure_ascii=False)[:180])
    out = []
    for f in r.get("features", []):
        rings = ((f.get("geometry") or {}).get("rings") or [])
        if rings:
            out.append([[float(p[0]), float(p[1])] for p in rings[0]])
    if not out:
        raise RuntimeError("no rings in response (geometryType 可能不是面)")
    return out


# ------------------------------------------------------------------ 简化
def rdp(pts, eps):
    """Douglas-Peucker（迭代版，点量大也不爆栈）。"""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        norm = (dx * dx + dy * dy) ** 0.5
        best, best_i = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if norm == 0:
                d = ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if d > best:
                best, best_i = d, i
        if best > eps:
            keep[best_i] = True
            stack.append((a, best_i))
            stack.append((best_i, b))
    return [p for p, k in zip(pts, keep) if k]


def ring_json(pts, decimals):
    if decimals is None:
        return json.dumps([[p[0], p[1]] for p in pts], separators=(",", ":"))
    return json.dumps([[round(p[0], decimals), round(p[1], decimals)] for p in pts],
                      separators=(",", ":"))


def gz(text):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6) as g:
        g.write(text.encode())
    return len(buf.getvalue())


# ------------------------------------------------------------------ 主流程
def pick_layers(n=SAMPLE_LAYERS):
    with open(FIELD_MAP, encoding="utf-8") as f:
        layers = json.load(f)["layers"]
    par = [(k, v) for k, v in layers.items() if v.get("src_kind") == "parcel_situs" and v.get("src_layer_url")]
    par.sort(key=lambda kv: -(kv[1].get("rows_total") or 0))
    if len(par) <= n:
        return par
    # 分位点抽样：从头到尾均分，取每档的代表（行数降序 → 大中小都有）
    idx = [round(i * (len(par) - 1) / (n - 1)) for i in range(n)]
    return [par[i] for i in idx]


def measure(n_target=SAMPLE_LAYERS):
    cands = pick_layers(n_target)
    # 失败补位：候选不够就从全表继续往后取
    with open(FIELD_MAP, encoding="utf-8") as f:
        all_par = [(k, v) for k, v in json.load(f)["layers"].items()
                   if v.get("src_kind") == "parcel_situs" and v.get("src_layer_url")]
    all_par.sort(key=lambda kv: -(kv[1].get("rows_total") or 0))
    tried = {k for k, _ in cands}
    queue = list(cands)
    backup = [x for x in all_par if x[0] not in tried]
    rows, errors = [], []
    n_try = 0
    while len(rows) < n_target and (queue or backup) and n_try < MAX_TRIES:
        k, v = queue.pop(0) if queue else backup.pop(0)
        n_try += 1
        try:
            rings = sample_layer(v["src_layer_url"])
        except Exception as e:                                   # 单层失败不影响整体
            errors.append({"layer": k, "err": "%s: %s" % (type(e).__name__, str(e)[:160])})
            continue
        verts = [len(r) for r in rings]
        raw = [ring_json(r, None) for r in rings]
        raw_b = [len(t.encode()) for t in raw]
        simp_pts = [rdp([tuple(p) for p in r], RDP_EPS) for r in rings]
        simp_b = [len(ring_json(r, DECIMALS_SIMPLE).encode()) for r in simp_pts]
        simp_verts = [len(r) for r in simp_pts]
        # gzip：同一层 8 条要素一起压（贴近真实 part 的压缩条件），再摊到每行
        gz_raw_all = gz(",".join(raw))
        gz_simp_all = gz(",".join(ring_json(r, DECIMALS_SIMPLE) for r in simp_pts))
        rows.append({
            "layer": k, "rows_total": v.get("rows_total"), "n_feats": len(rings),
            "v_med": statistics.median(verts), "v_mean": round(statistics.fmean(verts), 2),
            "v_max": max(verts), "n_rings": statistics.median(len(r) for r in rings),
            "raw_b_med": statistics.median(raw_b), "raw_b_mean": round(statistics.fmean(raw_b), 1),
            "raw_b_per_vert": round(statistics.fmean(raw_b) / statistics.fmean(verts), 2),
            "simp_b_med": statistics.median(simp_b), "simp_b_mean": round(statistics.fmean(simp_b), 1),
            "simp_keep_pct": round(100.0 * sum(simp_verts) / sum(verts), 2),
            "gz_raw_per_row": round(gz_raw_all / len(rings), 1),
            "gz_simp_per_row": round(gz_simp_all / len(rings), 1),
            "url": v["src_layer_url"],
        })
        time.sleep(0.2)
    return rows, errors


def summarize(rows):
    def col(k):
        return [r[k] for r in rows]

    with open(FIELD_MAP, encoding="utf-8") as f:
        layers = json.load(f)["layers"]
    par = [v for v in layers.values() if v.get("src_kind") == "parcel_situs"]
    n_layers = len(par)
    total_rows = sum(v.get("rows_total") or 0 for v in par)

    v_med = statistics.median(col("v_med"))
    v_mean = round(statistics.fmean(col("v_mean")), 2)
    per_row = {
        "raw_B_med": statistics.median(col("raw_b_med")),
        "raw_B_mean": round(statistics.fmean(col("raw_b_mean")), 1),
        "raw_gz_B_med": statistics.median(col("gz_raw_per_row")),
        "raw_gz_B_mean": round(statistics.fmean(col("gz_raw_per_row")), 1),
        "simp_B_med": statistics.median(col("simp_b_med")),
        "simp_B_mean": round(statistics.fmean(col("simp_b_mean")), 1),
        "simp_gz_B_med": statistics.median(col("gz_simp_per_row")),
        "simp_gz_B_mean": round(statistics.fmean(col("gz_simp_per_row")), 1),
        "bytes_per_vert_raw": round(statistics.fmean(col("raw_b_per_vert")), 2),
    }
    tiers = {}
    for name, key in (("3_raw_uncompressed", "raw_B_mean"), ("3_raw_gzip", "raw_gz_B_mean"),
                      ("2_simplified_gzip", "simp_gz_B_mean")):
        tiers[name] = round(per_row[key] * total_rows / GB, 2)
    keep = round(statistics.fmean(col("simp_keep_pct")), 2)
    return {
        "n_layers_sampled": len(rows), "n_feats_per_layer": FEATS,
        "n_layers_total": n_layers, "rows_total": total_rows,
        "v_vertices_per_parcel_median": v_med, "v_mean": v_mean,
        "per_row_bytes": per_row, "rdp_keep_pct": keep,
        "tier_GB": tiers, "layers": rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="机读 + 落 analysis/parcel-rings-sample.json")
    ap.add_argument("--n", type=int, default=SAMPLE_LAYERS)
    a = ap.parse_args()

    t0 = time.time()
    rows, errors = measure(a.n)
    if not rows:
        print("❌ 一层都没取到，先查网络/上游", file=sys.stderr)
        for e in errors:
            print("  ", e, file=sys.stderr)
        return 1
    s = summarize(rows)
    s["elapsed_s"] = round(time.time() - t0, 1)
    s["errors"] = errors

    if a.json:
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
        print(json.dumps({k: v for k, v in s.items() if k != "layers"}, ensure_ascii=False, indent=1))
        print("→", OUT_JSON)
        return 0

    print("样本 %d 层 / %d 要素每层（失败 %d 层）" % (s["n_layers_sampled"], FEATS, len(errors)))
    print("每宗地顶点数：中位 %s / 均值 %s" % (s["v_vertices_per_parcel_median"], s["v_mean"]))
    print("每行 rings 字节：原始 中位 %s 均值 %s｜gzip 中位 %s 均值 %s"
          % (s["per_row_bytes"]["raw_B_med"], s["per_row_bytes"]["raw_B_mean"],
             s["per_row_bytes"]["raw_gz_B_med"], s["per_row_bytes"]["raw_gz_B_mean"]))
    print("               简化 中位 %s 均值 %s｜gzip 中位 %s 均值 %s（RDP 保留 %.2f%%）"
          % (s["per_row_bytes"]["simp_B_med"], s["per_row_bytes"]["simp_B_mean"],
             s["per_row_bytes"]["simp_gz_B_med"], s["per_row_bytes"]["simp_gz_B_mean"], s["rdp_keep_pct"]))
    print("外推 %d 层 / %d 行：" % (s["n_layers_total"], s["rows_total"]))
    for k, v in s["tier_GB"].items():
        print("  %-20s %.2f GB" % (k, v))
    print("\n逐层：")
    for r in rows:
        print("  %-52s rows=%-9s v中位=%-4s 原始 %6.0f B  gzip %5.1f B  保留 %5.2f%%"
              % (r["layer"][:52], r["rows_total"], r["v_med"], r["raw_b_med"], r["gz_raw_per_row"],
                 r["simp_keep_pct"]))
    for e in errors:
        print("  ⚠", e["layer"], "—", e["err"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
