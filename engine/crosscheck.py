"""NH 交叉核对：同 addrkey 下 GRANIT 地块点 vs TIGER 街段插值点的距离分布与冲突计数。

只看融合表里的 provenance（`contributors`），不重新读源、不改库、不静默丢行：
  · 两国源都有的 addrkey：算 GRANIT 点与每个 TIGER 插值点的最小球面距离
  · 冲突 = 距离 > coord_conflict_m（默认 100m，取自 config，代码里不硬编码）
  · 只被插值覆盖的 addrkey：没有真实点/顶点贡献者，只有插值
  · 插值行一律 pos_estimated=true / point_kind=interpolated，且断言不进 S 级（由 pilot 校验）

产物：`<STATE>/crosscheck.json`（汇总）+ `<STATE>/crosscheck-samples.csv`（种子 + 行号可复现的抽样）。
"""
from __future__ import annotations

import csv
import json
import math
import os
import random


def _d(a, b) -> float:
    dx = (a[0] - b[0]) * 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, (a[1] - b[1]) * 110540.0)


def _q(sorted_vals, p: float) -> float:
    if not sorted_vals:
        return 0.0
    return round(sorted_vals[min(len(sorted_vals) - 1, max(0, math.ceil(p * len(sorted_vals)) - 1))], 1)


def crosscheck_pairs(rows, conflict_m: float = 100.0):
    """rows: 可迭代的 (addrkey, contributors_json) → 统计 + 每个 key 的最小距离明细。"""
    both, only_interp, real_keys, pairs = 0, 0, 0, []
    dists = []
    for idx, (key, prov_json) in enumerate(rows):
        try:
            provs = json.loads(prov_json or "[]")
        except (ValueError, TypeError):
            continue
        g = [(p.get("lon"), p.get("lat")) for p in provs
             if p.get("family", p.get("fam")) == "granit" and p.get("lon") is not None]
        t = [(p.get("lon"), p.get("lat")) for p in provs
             if p.get("family", p.get("fam")) == "tiger" and p.get("interp") and p.get("lon") is not None]
        has_real = any(p.get("lon") is not None and not p.get("interp") and not p.get("pos_estimated")
                       for p in provs)
        real_keys += int(has_real)
        if not has_real and t:
            only_interp += 1
        if g and t:
            both += 1
            best = min(_d(a, b) for a in g for b in t)
            dists.append(best)
            pairs.append({"key": key, "idx": idx, "granit": g[0], "tiger": t[0],
                          "dist_m": round(best, 1), "conflict": best > conflict_m})
    dists.sort()
    over = sum(1 for d in dists if d > conflict_m)
    return {"both_sources_keys": both, "only_interpolated_keys": only_interp, "real_point_keys": real_keys,
            "compared_keys": len(dists), "conflict_m": conflict_m, "conflict_keys": over,
            "conflict_share": round(over / len(dists), 4) if dists else None,
            "dist_p50_m": _q(dists, 0.50), "dist_p90_m": _q(dists, 0.90), "dist_p99_m": _q(dists, 0.99),
            "dist_max_m": round(dists[-1], 1) if dists else 0.0,
            "dist_mean_m": round(sum(dists) / len(dists), 1) if dists else 0.0,
            "over_100m_share": round(over / len(dists), 4) if dists else None,
            "_pairs": pairs}


def nh_crosscheck(fus, outdir: str, cfg: dict | None = None, seed: int = 20261125, sample_n: int = 200):
    """从融合表取 provenance 做交叉核对，写 crosscheck.json + crosscheck-samples.csv。"""
    conflict_m = float((cfg or {}).get("coord_conflict_m", 100))
    rows = fus.db.execute("SELECT addrkey, contributors FROM fused ORDER BY addrkey").fetchall()
    res = crosscheck_pairs(rows, conflict_m)
    pairs = res.pop("_pairs")
    total = fus.db.execute("SELECT COUNT(*) FROM fused").fetchone()[0]
    parcel = fus.db.execute("SELECT COUNT(*) FROM fused WHERE point_kind='parcel_centroid'").fetchone()[0]
    interp_rows = fus.db.execute("SELECT COUNT(*) FROM fused WHERE pos_estimated=1").fetchone()[0]
    res.update({"rows_fused": total, "parcel_centroid_rows": parcel,
                "parcel_centroid_share": round(parcel / total, 4) if total else None,
                "interpolated_rows": interp_rows,
                "interpolated_share": round(interp_rows / total, 4) if total else None,
                "seed": seed, "sample_n": sample_n, "note": "距离=GRANIT 点与 TIGER 插值点在同 addrkey 下的最小球面距离；冲突行 provenance 保留，未丢弃"})
    os.makedirs(outdir, exist_ok=True)
    rnd = random.Random(seed)
    picked = rnd.sample(pairs, min(sample_n, len(pairs)))
    with open(os.path.join(outdir, "crosscheck-samples.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["seed", "scan_row_index", "addrkey", "granit_lon", "granit_lat", "tiger_lon", "tiger_lat",
                    "dist_m", "conflict_over_conflict_m"])
        for p in sorted(picked, key=lambda x: x["idx"]):
            w.writerow([seed, p["idx"], p["key"], p["granit"][0], p["granit"][1], p["tiger"][0], p["tiger"][1],
                        p["dist_m"], int(bool(p["conflict"]))])
    with open(os.path.join(outdir, "crosscheck.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return res
