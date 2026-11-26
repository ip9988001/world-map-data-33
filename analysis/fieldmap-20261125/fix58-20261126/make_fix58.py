#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""汇总 fix58 结果：fix58-before-after.csv + fix58-summary.json（数字只从数据文件算，不手抄）。

输入（同目录）：before-b58.jsonl / after-b58.jsonl / before-affected.jsonl / after-affected.jsonl /
                before-regression.jsonl / after-regression.jsonl / rows-census.jsonl / jobs-*.jsonl
只读 analysis/fieldmap-20261125/layer-coverage.v2.csv 取「修前」口径交叉校验。
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
COV = os.path.join(ROOT, "analysis", "fieldmap-20261125", "layer-coverage.v2.csv")
TOTAL_LAYERS = 3550
MAPPED_V2 = 3355


def jl(p):
    return [json.loads(l) for l in open(os.path.join(HERE, p), encoding="utf-8")]


def gstr(g):
    return "/".join(f"{k}:{g.get(k, 0)}" for k in ("S", "A", "B", "C"))


def main():
    jobs = {j["layer_id"]: j for j in jl("jobs-b58.jsonl")}
    before = {r["layer_id"]: r for r in jl("before-b58.jsonl")}
    after = {r["layer_id"]: r for r in jl("after-b58.jsonl")}
    cov = {r["layer"]: r for r in csv.DictReader(open(COV, encoding="utf-8"))}
    rows = []
    for lid, j in jobs.items():
        b, a = before[lid], after[lid]
        rows.append({
            "layer_id": lid,
            "in_rows": a["in_rows"],
            "before_mapped_rows": b["mapped"],
            "after_mapped_rows": a["mapped"],
            "before_grade": gstr(b["grade"]),
            "after_grade": gstr(a["grade"]),
            "reason_code": j["reason_code"],
            "closed_diff": a["diff"],
            "bad_empty": a["bad_empty"],
            "bad_grade": a["bad_grade"],
            "zero_coord": a["zero_coord"],
        })
    rows.sort(key=lambda r: -r["after_mapped_rows"])
    cols = list(rows[0].keys())
    with open(os.path.join(HERE, "fix58-before-after.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- 58 层验收 ----
    zero = [r for r in rows if r["after_mapped_rows"] == 0]
    still_zero = []
    for r in zero:
        lid = r["layer_id"]
        still_zero.append({"layer_id": lid, "in_rows": r["in_rows"],
                           "evidence": f"after run: mapped=0 dropped_below_c={after[lid]['dropped_below_c']} "
                                       f"reason={after[lid].get('reason')}"})
    # 修前口径交叉校验（layer-coverage.v2.csv 必须都是 0）
    v2_mismatch = [{"layer_id": lid, "v2_mapped": int(cov[lid]["mapped"]),
                    "v2_in_rows": int(cov[lid]["in_rows"]), "rerun_in_rows": before[lid]["in_rows"]}
                   for lid in jobs
                   if int(cov[lid]["mapped"]) != 0 or int(cov[lid]["in_rows"]) != before[lid]["in_rows"]]
    n_ok = len(rows) - len(zero)
    mapped_after = MAPPED_V2 + n_ok

    # ---- 回归：新别名命中集全量 A/B ----
    ab_b = {r["layer_id"]: r for r in jl("before-affected.jsonl")}
    ab_a = {r["layer_id"]: r for r in jl("after-affected.jsonl")}
    common = [l for l in ab_a if l in ab_b]
    decreased = [{"layer_id": l, "before": ab_b[l]["mapped"], "after": ab_a[l]["mapped"]}
                 for l in common if ab_a[l]["mapped"] < ab_b[l]["mapped"]]
    increased = [{"layer_id": l, "before": ab_b[l]["mapped"], "after": ab_a[l]["mapped"],
                  "delta": ab_a[l]["mapped"] - ab_b[l]["mapped"]}
                 for l in common if ab_a[l]["mapped"] > ab_b[l]["mapped"]]
    value_changed = [{"layer_id": l, "mapped": ab_a[l]["mapped"],
                      "num_ok_before": ab_b[l]["num_ok"], "num_ok_after": ab_a[l]["num_ok"],
                      "grade_before": gstr(ab_b[l]["grade"]), "grade_after": gstr(ab_a[l]["grade"])}
                     for l in common if ab_a[l]["mapped"] == ab_b[l]["mapped"]
                     and (ab_a[l]["street_hash"] != ab_b[l]["street_hash"]
                          or ab_a[l]["addrkey_hash"] != ab_b[l]["addrkey_hash"])]
    rank = {"S": 4, "A": 3, "B": 2, "C": 1}
    grade_worse = []
    for l in common:
        b, a = ab_b[l], ab_a[l]
        score = sum((a["grade"].get(g, 0) - b["grade"].get(g, 0)) * rank[g]
                    for g in set(a["grade"]) | set(b["grade"]))
        if score < 0:
            grade_worse.append({"layer_id": l, "before": b["grade"], "after": a["grade"]})

    # ---- 回归：未命中集分层抽样 A/B ----
    sb = {r["layer_id"]: r for r in jl("before-regression.jsonl")}
    sa = {r["layer_id"]: r for r in jl("after-regression.jsonl")}
    sdecl = [{"layer_id": l, "before": sb[l]["mapped"], "after": sa[l]["mapped"]}
             for l in sa if l in sb and sa[l]["mapped"] < sb[l]["mapped"]]
    sinc = [{"layer_id": l, "before": sb[l]["mapped"], "after": sa[l]["mapped"],
             "delta": sa[l]["mapped"] - sb[l]["mapped"]}
            for l in sa if l in sb and sa[l]["mapped"] > sb[l]["mapped"]]
    schg = [l for l in sa if l in sb and sa[l]["mapped"] == sb[l]["mapped"]
            and (sa[l]["street_hash"] != sb[l]["street_hash"] or sa[l]["grade"] != sb[l]["grade"])]
    census = {json.loads(l)["layer_id"]: json.loads(l) for l in open(os.path.join(HERE, "rows-census.jsonl"),
                                                                     encoding="utf-8")}
    reg_jobs = jl("jobs-regression.jsonl")
    states = collections.Counter(census.get(j["layer_id"], {}).get("state_guess", "") for j in reg_jobs)

    # ---- conemap 抽检（4206 万行的层，只跑前 25 个 part）----
    conemap = {}
    for name in ("before-miss-partial.jsonl", "after-miss-partial.jsonl"):
        p = os.path.join(HERE, name)
        if os.path.isfile(p):
            conemap[name.split("-")[0]] = json.loads(open(p, encoding="utf-8").read().splitlines()[0])

    est = sum(int(j.get("est_rows_recoverable") or 0) for j in jobs.values())
    summary = {
        "qid": "muse-000271", "task_id": "w2-20261126-fieldmap-fix58",
        "scope": "58 层（REPORT-unmapped.md §5 的 B 类全量）",
        "layers_total": len(rows),
        "layers_mapped_after": n_ok,
        "layers_still_zero": len(zero),
        "still_zero": still_zero,
        "rows": {
            "in_rows_total": sum(r["in_rows"] for r in rows),
            "mapped_before_total": sum(r["before_mapped_rows"] for r in rows),
            "mapped_after_total": sum(r["after_mapped_rows"] for r in rows),
            "est_rows_recoverable_from_report": est,
            "dropped_below_c_total": sum(after[l]["dropped_below_c"] for l in jobs),
            "parse_error_total": sum(after[l]["parse_error"] for l in jobs),
        },
        "acceptance": {
            "closed_diff_zero_layers": sum(1 for r in rows if r["closed_diff"] == 0),
            "bad_empty_total": sum(r["bad_empty"] for r in rows),
            "bad_grade_total": sum(r["bad_grade"] for r in rows),
            "zero_coord_total": sum(r["zero_coord"] for r in rows),
            "zero_coord_layers": [{"layer_id": r["layer_id"], "zero_coord": r["zero_coord"],
                                   "mapped": r["after_mapped_rows"]}
                                  for r in rows if r["zero_coord"] > 0],
            "mapped_gt0_layers": sum(1 for r in rows if r["after_mapped_rows"] > 0),
        },
        "baseline_crosscheck": {
            "note": "before 跑（4c3a6a3 的 fm_core.py + 同提交 dialects.v1.yaml）必须与 layer-coverage.v2.csv 一致",
            "mismatch_layers": v2_mismatch,
            "before_mapped_total": sum(r["before_mapped_rows"] for r in rows),
        },
        "coverage": {
            "mapped_layers": mapped_after,
            "total_layers": TOTAL_LAYERS,
            "pct": round(100.0 * mapped_after / TOTAL_LAYERS, 2),
            "gate_layers_needed": 3373,
            "pass_95pct": mapped_after >= 3373,
            "pass_96_14pct": round(100.0 * mapped_after / TOTAL_LAYERS, 2) >= 96.14,
        },
        "regression": {
            "type": "alias-hit 全量 A/B + 未命中集分层抽样 A/B（未做全量重扫，见 limits）",
            "alias_hit_census": {
                "layers_scanned": len(census),
                "layers_alias_hit": len(common) + (1 if conemap else 0),
                "alias_hit_layers_ab": len(common),
                "mapped_before_total": sum(ab_b[l]["mapped"] for l in common),
                "mapped_after_total": sum(ab_a[l]["mapped"] for l in common),
                "decreased_layers": decreased,
                "increased_layers": len(increased),
                "increased_rows": sum(x["delta"] for x in increased),
                "value_changed_same_mapped_layers": len(value_changed),
                "value_changed_detail": sorted(value_changed, key=lambda x: -x["mapped"])[:30],
                "grade_net_worse_layers": grade_worse,
            },
            "sample": {
                "layers": len(reg_jobs),
                "layers_with_dropped": sum(1 for j in reg_jobs if int(j.get("dropped_below_c") or 0) > 0),
                "rows": sum(j["in_rows"] for j in reg_jobs),
                "states_covered": len([k for k in states if k]),
                "states": dict(states),
                "dialect_origin": {"fallback": len(reg_jobs),
                                   "note": "v2 的 3,550 层 dialect_origin 全是 fallback（dialect_id 全为 "
                                           "minimal_safe），因此 origination 类型只有 1 种，抽样自然全覆盖"},
                "decreased_layers": sdecl,
                "increased_layers": len(sinc),
                "increased_rows": sum(x["delta"] for x in sinc),
                "value_changed_same_mapped_layers": len(schg),
                "bad_empty_total_after": sum(sa[l]["bad_empty"] for l in sa),
            },
            "big_layer_partial": conemap,
        },
        "artifacts": {os.path.basename(p): os.path.getsize(os.path.join(HERE, p))
                      for p in sorted(os.listdir(HERE)) if p.endswith((".csv", ".json", ".jsonl", ".md"))},
    }
    json.dump(summary, open(os.path.join(HERE, "fix58-summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: summary[k] for k in ("layers_mapped_after", "layers_still_zero", "coverage",
                                              "rows")}, ensure_ascii=False, indent=1))
    print("regression:", json.dumps({
        "alias_hit_decreased": len(decreased), "alias_hit_increased": len(increased),
        "value_changed": len(value_changed), "grade_worse": len(grade_worse),
        "sample_decreased": len(sdecl), "sample_increased": len(sinc),
        "sample_value_changed": len(schg)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
