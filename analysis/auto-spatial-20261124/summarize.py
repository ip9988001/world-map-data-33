"""从沙盒产出的 CSV 复算 REPORT.md 里的每张表（不产生新判据，只做聚合）。

跑法：python3 analysis/auto-spatial-20261124/summarize.py
输出：同目录 summary.json + 终端可粘贴的 markdown 片段
口径：验收指标是**模板覆盖率**（可认层 / 11,056），不再统计「挪进 manual 多少层」。
"""
from __future__ import annotations

import collections
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EKEYS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")
TU_LAYERS, TU_ROWS = 11056, 297519308


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def rows_of(rs, key="coverage_rows"):
    return sum(int(r.get(key) or 0) for r in rs)


def pct(a, b):
    return round(100.0 * a / b, 2) if b else 0.0


def main():
    rows = load("auto-recognized.csv")
    mv = load("template-unresolved-moves.csv")
    un = load("template-unresolved-unavailable.csv")
    spatial = load("spatial-findings.csv")
    tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]

    out = {"layers": len(rows), "rows": rows_of(rows), "tu_layers": len(tu), "tu_rows": rows_of(tu)}

    # ---- 三路分流（三列新表）
    by_v = {v: [r for r in mv if r["verdict"] == v] for v in ("active", "minimal_safe", "unavailable")}
    out["split"] = {v: {"layers": len(rs), "rows": rows_of(rs, "rows_n")} for v, rs in by_v.items()}
    # ---- 模板覆盖率（层 / 行 / provider 三视图）
    rec = by_v["active"] + by_v["minimal_safe"]
    out["coverage"] = {
        "layers": [len(rec), TU_LAYERS, pct(len(rec), TU_LAYERS)],
        "rows": [rows_of(rec, "rows_n"), TU_ROWS, pct(rows_of(rec, "rows_n"), TU_ROWS)],
        "providers_total": len({r["provider"] for r in mv}),
        "providers_recognized": len({r["provider"] for r in rec}),
    }
    per_prov = collections.defaultdict(lambda: {"layers": 0, "recognized": 0, "rows": 0, "recognized_rows": 0})
    for r in mv:
        p = per_prov[r["provider"]]
        p["layers"] += 1
        p["rows"] += int(r["rows_n"] or 0)
        if r["verdict"] != "unavailable":
            p["recognized"] += 1
            p["recognized_rows"] += int(r["rows_n"] or 0)
    out["provider_top"] = [{"provider": k, **v, "coverage_pct": pct(v["recognized"], v["layers"])}
                           for k, v in sorted(per_prov.items(), key=lambda kv: -kv[1]["layers"])[:15]]
    # ---- 三列之和 vs 分母（差额必须为 0）
    out["closure"] = {
        "split_layers": sum(v["layers"] for v in out["split"].values()),
        "split_rows": sum(v["rows"] for v in out["split"].values()),
        "diff_layers": sum(v["layers"] for v in out["split"].values()) - TU_LAYERS,
        "diff_rows": sum(v["rows"] for v in out["split"].values()) - TU_ROWS,
        "unavailable_csv_rows": len(un),
        "unavailable_csv_all_unavailable": all(r["verdict"] == "unavailable" for r in un),
        "verdict_values": sorted({r["verdict"] for r in mv}),
        "manual_verdict_present": any(r["verdict"] == "manual" for r in mv),
    }
    # ---- 上一版「留 manual 10,013 层」的去向对账（旧口径 = tier3）
    old_manual = [r for r in tu if r["tier"] == "tier3"]
    out["reconcile_old_manual"] = {
        "layers": len(old_manual), "rows": rows_of(old_manual),
        "to_minimal_safe": [sum(1 for r in old_manual if r["verdict"] == "minimal_safe"),
                            rows_of([r for r in old_manual if r["verdict"] == "minimal_safe"])],
        "to_unavailable": [sum(1 for r in old_manual if r["verdict"] == "unavailable"),
                           rows_of([r for r in old_manual if r["verdict"] == "unavailable"])],
    }
    # ---- 三档（判据不变，作参考）
    out["tier"] = {t: {"layers": sum(1 for r in tu if r["tier"] == t),
                       "rows": rows_of([r for r in tu if r["tier"] == t])}
                   for t in ("tier1", "tier2", "tier3")}
    # ---- 8 条否定证据（全库 + TU）
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
            "granularity": collections.Counter(r["granularity"] for r in hit).most_common()}
    # ---- 暂不可用的卡点分布（新的 delivery 依据）
    out["unavailable_blockers"] = collections.Counter(r["reason_evidence"] for r in un).most_common(12)
    out["unavailable_missing"] = {
        "缺门牌": sum(1 for r in un if "E1" in r["reason_evidence"]),
        "缺街名": sum(1 for r in un if "E2" in r["reason_evidence"]),
        "无 url/本地读不出(provider=none)": sum(1 for r in un if r["provider"] == "none"),
    }
    # ---- 空间验算
    fx = [r for r in spatial if r["kind"] == "fixture_layer"]
    out["spatial"] = {"fixture_layers": len(fx),
                      "verdicts": collections.Counter(r["verdict"] for r in fx).most_common(),
                      "null_rate_jump_layers": sum(1 for r in spatial if r["kind"] == "null_rate_jump"),
                      "fixtures": [{kk: r[kk] for kk in ("key", "n", "outside_share", "unique_rate",
                                                         "top_point_share", "p50_boundary_dist_m",
                                                         "p95_boundary_dist_m", "verdict")} for r in fx]}
    json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("split", "coverage", "closure", "reconcile_old_manual",
                                          "unavailable_missing")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
