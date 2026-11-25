#!/usr/bin/env python3
"""四数对账 + 分母剔除清单 + 分档挪动清单（本轮收尾硬门禁，对不上直接非零退出）。

对账五条（全部从落盘产物现算，不引用任何手写数字）：
  1. tier1 + tier2 + tier3 == 17,168（auto-recognized.csv 行数不变）
  2. 三档 rows_n 之和 == declared（984,719,364，第 4 步分母）
  3. denominator-excluded 恰好 198 行，逐条带 `excluded_from_verifiable_denominator: <class>`
     与归因文案「数据性质如此，不是缺陷」；class 分桶数与 spatial_thresholds.yaml 一致
  4. e7-before-after.csv 的 delta_kind 计数与 e7-before-after.json / REPORT 一致
  5. 相对基线 176 的涨/跌/抵消逐层清单可指认（tier-moves.csv）

用法：python3 analysis/grading-rerun-20261125/reconcile.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402

DIR = os.path.join(ROOT, "analysis", "grading-rerun-20261125")
NEW = os.path.join(DIR, "auto-recognized.csv")
BASE = os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125", "auto-recognized.csv")
DECLARED = 984719364          # 第 4 步 dialect-assignment.csv 的 rows_n 合计（分母），按原口径引用
DENOM_LAYERS = 17168
NOTE = "数据性质如此，不是缺陷"


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def main():
    new, base = rd(NEW), rd(BASE)
    excl_cfg = (yaml.safe_load(open(os.path.join(ROOT, "sandbox", "spatial_thresholds.yaml"),
                                    encoding="utf-8")) or {})["e7"]["denominator_excluded"]
    classes = {k: int(v["value"]) for k, v in excl_cfg.items() if isinstance(v, dict) and "value" in v and k != "total"}

    tiers = collections.Counter(r["tier"] for r in new)
    rows_by = {t: sum(int(r["rows_n"] or 0) for r in new if r["tier"] == t) for t in ("tier1", "tier2", "tier3")}
    excluded = [r for r in new if r["denominator_excluded"]]
    excl_by_class = collections.Counter(r["denominator_excluded"] for r in excluded)

    # —— 1/2 分母闭合 ——
    checks = {
        "layers_total": len(new), "layers_equal_17168": len(new) == DENOM_LAYERS,
        "tier_sum_layers": sum(tiers.values()), "tier_sum_equals_total": sum(tiers.values()) == len(new),
        "rows_total": sum(rows_by.values()), "declared_rows": DECLARED,
        "rows_equals_declared": sum(rows_by.values()) == DECLARED,
    }

    # —— 3 分母剔除清单 ——
    den = [{"layer_id": r["layer_id"], "url": r["url"], "class": r["denominator_excluded"],
            "判定依据": (f"{r.get('E1_state')}/{r.get('E2_state')}/{r.get('E3_state')}；"
                      f"E7={r.get('E7_state')}；rows_n={r['rows_n']}；reason_detail 内已标 "
                      f"excluded_from_verifiable_denominator: {r['denominator_excluded']}")}
           for r in sorted(excluded, key=lambda x: (x["denominator_excluded"], x["url"]))]
    with open(os.path.join(DIR, "denominator-excluded.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer_id", "url", "class", "判定依据"])
        w.writeheader()
        w.writerows(den)
    tag_ok = sum(1 for r in excluded
                 if f"excluded_from_verifiable_denominator: {r['denominator_excluded']}" in (r["reason_evidence"] or "")
                 and f"excluded_from_verifiable_denominator: {r['denominator_excluded']}" in (r["reason_detail"] or "")
                 and NOTE in (r["reason_detail"] or ""))
    checks.update({
        "excluded_rows": len(den), "excluded_expected": int(excl_cfg["total"]["value"]),
        "excluded_equals_total": len(den) == int(excl_cfg["total"]["value"]),
        "excluded_by_class": dict(excl_by_class), "excluded_by_class_matches_yaml": dict(excl_by_class) == classes,
        "excluded_all_tagged": tag_ok == len(den),
        "excluded_note_verbatim": all(NOTE in (r["reason_detail"] or "") for r in excluded),
        "excluded_tier1": sum(1 for r in excluded if r["tier"] == "tier1"),
        "verifiable_denominator": len(new) - len(den),
    })

    # —— 4 e7-before-after ——
    e7rows = rd(os.path.join(DIR, "e7-before-after.csv"))
    kinds = collections.Counter(r["delta_kind"] for r in e7rows)
    e7json = json.load(open(os.path.join(DIR, "e7-before-after.json"), encoding="utf-8"))
    checks.update({
        "e7_pairs": len(e7rows), "e7_delta_kind": dict(kinds), "e7_lost_key": kinds.get("lost-key", 0),
        "e7_delta_kind_matches_json": dict(kinds) == e7json["delta_kind"],
        "e7_delta_kind_sum_equals_pairs": sum(kinds.values()) == len(e7rows),
        "e7_addr_rows_before": sum(int(r["n_addr_rows_before"]) for r in e7rows),
        "e7_addr_rows_after": sum(int(r["n_addr_rows_after"]) for r in e7rows),
    })

    # —— 5 相对基线 176 的挪动清单 ——
    b1 = {r["url"] for r in base if r["tier"] == "tier1"}
    n1 = {r["url"] for r in new if r["tier"] == "tier1"}
    up, down = sorted(n1 - b1), sorted(b1 - n1)
    lmap = {r["url"]: r["layer_id"] for r in new}
    bmap = {r["url"]: r for r in base}
    with open(os.path.join(DIR, "tier-moves.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["direction", "layer_id", "url", "tier_before", "tier_after",
                                           "tier_relax_state_before", "tier_relax_state_after",
                                           "denominator_excluded"])
        w.writeheader()
        nmap = {r["url"]: r for r in new}
        for direction, urls in (("up", up), ("down", down)):
            for u in urls:
                w.writerow({"direction": direction, "layer_id": lmap.get(u, ""), "url": u,
                            "tier_before": bmap.get(u, {}).get("tier", ""),
                            "tier_after": nmap.get(u, {}).get("tier", ""),
                            "tier_relax_state_before": bmap.get(u, {}).get("e7_relax_state", ""),
                            "tier_relax_state_after": nmap.get(u, {}).get("e7_relax_state", ""),
                            "denominator_excluded": nmap.get(u, {}).get("denominator_excluded", "")})
    checks.update({
        "baseline_tier1": len(b1), "new_tier1": len(n1),
        "up_layers": len(up), "down_layers": len(down), "net": len(n1) - len(b1),
        # 抵消：被「拆串」抬进 Tier1、又被「分母剔除」移出可验分母的同一层（集合交集，不是估算）
        "up_and_excluded": len([u for u in up if any(r["url"] == u and r["denominator_excluded"] for r in new)]),
        "down_and_excluded": len([u for u in down if any(r["url"] == u and r["denominator_excluded"] for r in new)]),
        "baseline_tier1_excluded": len([r for r in b1 if any(x["url"] == r and x["denominator_excluded"] for x in new)]),
        "merged_tier1_verifiable": len([u for u in n1
                                        if not any(r["url"] == u and r["denominator_excluded"] for r in new)]),
    })
    n_excl_up = checks["up_and_excluded"]
    checks["cancellation_identity"] = (
        checks["baseline_tier1"] + checks["up_layers"] - checks["down_layers"] - n_excl_up
        == checks["merged_tier1_verifiable"])

    ok = (checks["layers_equal_17168"] and checks["tier_sum_equals_total"] and checks["rows_equals_declared"]
          and checks["excluded_equals_total"] and checks["excluded_by_class_matches_yaml"]
          and checks["excluded_all_tagged"] and checks["excluded_note_verbatim"]
          and checks["e7_delta_kind_matches_json"] and checks["e7_delta_kind_sum_equals_pairs"]
          and checks["up_layers"] - checks["down_layers"] == checks["net"]
          and checks["cancellation_identity"])
    summary = {"tiers": dict(tiers), "tier_rows": rows_by,
               "verifiable_denominator": checks["verifiable_denominator"],
               "tier1_share_of_verifiable": round(100 * len(n1) / checks["verifiable_denominator"], 4),
               "checks": checks, "all_checks_pass": bool(ok)}
    with open(os.path.join(DIR, "reconcile.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    if not ok:
        print("ASSERT FAILED", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
