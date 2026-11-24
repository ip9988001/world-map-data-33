"""从沙盒产出的 CSV 复算 REPORT.md 里的每张表（不产生新判据，只做聚合）。

跑法：python3 analysis/auto-spatial-20261124/summarize.py
输出：同目录 summary.json（表结构）+ 终端可粘贴的 markdown 片段
"""
from __future__ import annotations

import collections
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EKEYS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rows_of(rs):
    return sum(int(r["coverage_rows"] or 0) for r in rs)


def main():
    rows = load("auto-recognized.csv")
    tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]
    spatial = load("spatial-findings.csv")
    out = {"layers": len(rows), "rows": rows_of(rows), "tu_layers": len(tu), "tu_rows": rows_of(tu)}

    # ---- 三档
    out["tier"] = {t: {"layers": sum(1 for r in rows if r["tier"] == t),
                       "rows": rows_of([r for r in rows if r["tier"] == t]),
                       "tu_layers": sum(1 for r in tu if r["tier"] == t),
                       "tu_rows": rows_of([r for r in tu if r["tier"] == t])}
                   for t in ("tier1", "tier2", "tier3")}
    # ---- 挪动表
    out["move"] = {m: {"layers": sum(1 for r in rows if r["move"] == m),
                       "rows": rows_of([r for r in rows if r["move"] == m]),
                       "tu_layers": sum(1 for r in tu if r["move"] == m),
                       "tu_rows": rows_of([r for r in tu if r["move"] == m])}
                   for m in ("active", "minimal_safe", "manual")}
    # ---- 8 条否定证据
    out["evidence"] = {}
    for k in EKEYS:
        hit = [r for r in rows if r[f"{k}_state"] == "hit"]
        out["evidence"][k] = {
            "hit_layers": len(hit), "hit_rows": rows_of(hit),
            "unknown_layers": sum(1 for r in rows if r[f"{k}_state"] == "unknown"),
            "na_layers": sum(1 for r in rows if r[f"{k}_state"] == "na"),
            "tu_hit_layers": sum(1 for r in tu if r[f"{k}_state"] == "hit"),
            "tu_hit_rows": rows_of([r for r in tu if r[f"{k}_state"] == "hit"]),
            "provider_top": collections.Counter(r["provider_id"] for r in hit).most_common(5),
            "granularity": collections.Counter(r["granularity"] for r in hit).most_common(),
            "sample_detail": sorted({r[f"{k}_detail"] for r in hit if r.get(f"{k}_detail")})[:3]}
    # ---- TU 留 manual 的卡点
    out["tu_blockers"] = collections.Counter(r["move_reason"] for r in tu if r["move"] == "manual").most_common()
    # ---- Tier2 样例
    out["tier2_samples"] = [{kk: r[kk] for kk in ("layer_id", "provider_id", "state", "granularity", "geom",
                                                  "usable", "share", "coverage_rows", "move_reason")}
                            for r in tu if r["tier"] == "tier2"][:5]
    # ---- 空间验算
    fx = [r for r in spatial if r["kind"] == "fixture_layer"]
    out["spatial"] = {"fixture_layers": len(fx),
                      "verdicts": collections.Counter(r["verdict"] for r in fx).most_common(),
                      "null_rate_jump_layers": sum(1 for r in spatial if r["kind"] == "null_rate_jump"),
                      "fixtures": [{kk: r[kk] for kk in ("key", "n", "outside_share", "unique_rate",
                                                         "top_point_share", "p50_boundary_dist_m",
                                                         "p95_boundary_dist_m", "verdict")} for r in fx]}
    # ---- 抽样清单（第 5 步抽样/全扫范围，落盘备查）
    slist = [{"layer_id": f["key"], "kind": "fixture_layer", "n_rows": f["n"], "seed": 20261124,
              "note": "真实样本，逐行坐标全部参与空间验算"} for f in fx]
    lf = os.path.join(os.path.dirname(HERE), "full-inventory-20261124", "inventory-local-fields.csv")
    seen = {}
    for r in csv.DictReader(open(lf, encoding="utf-8")):
        seen.setdefault(r["layer"], set()).add(r["denom"])
    slist += [{"layer_id": k, "kind": "local_layer_field_table", "n_rows": max(v), "seed": 0,
               "note": "字段级全表（非抽样）参与 null 率突变检测"} for k, v in sorted(seen.items())]
    slist += [{"layer_id": f"registry_layer:{r['layer_id']}", "kind": "registry_layer",
               "n_rows": 0, "seed": 20261124, "note": "无坐标样本 → 空间验算未跑（不计入抽样）"}
              for r in rows[:0]]
    with open(os.path.join(HERE, "sampling-list.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer_id", "kind", "n_rows", "seed", "note"])
        w.writeheader()
        w.writerows(slist)
    out["sampling"] = {"fixture_layers": len(fx), "local_layers": len(seen), "total": len(slist)}
    # ---- 闭合断言（差额必须为 0，写进报告）
    out["closure"] = {
        "tier_layers": sum(v["layers"] for v in out["tier"].values()),
        "tier_rows": sum(v["rows"] for v in out["tier"].values()),
        "move_layers": sum(v["layers"] for v in out["move"].values()),
        "move_rows": sum(v["rows"] for v in out["move"].values()),
        "tu_move_layers": sum(v["tu_layers"] for v in out["move"].values()),
        "tu_move_rows": sum(v["tu_rows"] for v in out["move"].values()),
        "tu_blocked_layers": sum(n for _, n in out["tu_blockers"]),
    }
    json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
