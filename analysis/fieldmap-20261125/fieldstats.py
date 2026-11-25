#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字段有效率统计（全局 / 按州 / 按 dialect）+ 闭合汇总，全部从 layer-coverage.csv 算，不重扫数据。"""
from __future__ import annotations
import collections, csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIST = os.environ.get("FM_DIST", "/data/workspace/wmd-fieldmap/dist")


def pct(a, b):
    return round(100.0 * a / b, 2) if b else 0.0


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    def agg(rs):
        mapped = sum(int(r["mapped"] or 0) for r in rs)
        inr = sum(int(r["in_rows"] or 0) for r in rs)
        return {
            "layers": len(rs),
            "layers_mapped": sum(1 for r in rs if int(r["mapped"] or 0) > 0),
            "in_rows": inr,
            "mapped": mapped,
            "dropped_below_c": sum(int(r["dropped_below_c"] or 0) for r in rs),
            "parse_error": sum(int(r["parse_error"] or 0) for r in rs),
            "diff": sum(int(r["diff"] or 0) for r in rs),
            "street_name_ok_pct": pct(sum(int(r["street_ok"] or 0) for r in rs), mapped),
            "house_number_ok_pct": pct(sum(int(r["number_ok"] or 0) for r in rs), mapped),
            "city_ok_pct": pct(sum(int(r["city_ok"] or 0) for r in rs), mapped),
            "zip5_valid_pct": pct(sum(int(r["zip5_ok"] or 0) for r in rs), mapped),
            "zip5_invalid_rows": sum(int(r["zip5_invalid"] or 0) for r in rs),
            "zip5_missing_rows": sum(int(r["zip5_missing"] or 0) for r in rs),
            "coord_ok_pct": pct(sum(int(r["coord_ok"] or 0) for r in rs), mapped),
            "coord_out_of_range_rows": sum(int(r["coord_out_of_range"] or 0) for r in rs),
            "grade": {g: sum(int(r["grade_" + g] or 0) for r in rs) for g in "SABC"},
            "tier_layers": dict(collections.Counter(
                k for r in rs for k, v in (json.loads(r["tier"] or "{}") or {}).items() if int(v or 0) > 0)),
            "tier_rows": dict(sum((collections.Counter({k: int(v or 0) for k, v in
                                                       (json.loads(r["tier"] or "{}") or {}).items()})
                                   for r in rs), collections.Counter())),
            "source_layer_url_layers": sum(1 for r in rs if int(r["mapped"] or 0) > 0
                                          and (r.get("source_layer_kind") == "url")),
            "source_layer_fallback_layers": sum(1 for r in rs if int(r["mapped"] or 0) > 0
                                               and r.get("source_layer_kind") == "layer_id_fallback"),
            "out_bytes": sum(int(r["out_bytes"] or 0) for r in rs),
        }
    dialects = collections.defaultdict(list)
    for r in rows:
        key = r["dialect_id"] + "|" + r["dialect_origin"]
        dialects[key].append(r)
    st_total = os.path.join(DIST, "amend-total.json")
    out = {"global": agg(rows),
           "by_dialect": {k: agg(v) for k, v in sorted(dialects.items(), key=lambda kv: -len(kv[1]))},
           "by_state_null": "信封恒无 state 字段 → 按州分组不可用；state 只从 raw 显式州字段或组合串尾部取"}
    if os.path.isfile(st_total):
        t = json.load(open(st_total, encoding="utf-8"))
        out["global"]["addrkey_v3"] = {
            "rows": t["rows_out"], "key_changed_vs_v1": t["key_changed"],
            "rows_unkeyed": t["key_unkeyed"],
            "unkeyed_pct": pct(t["key_unkeyed"], t["rows_out"]),
            "include_unit": __import__("yaml").safe_load(open(os.path.join(
                ROOT, "engine", "config", "pilot.yaml"), encoding="utf-8"))["addrkey"]["include_unit"],
        }
        out["global"]["house_number_nulled_by_placeholder"] = t["n_null"]
        out["global"]["grade_moves_on_placeholder_fix"] = t["moved"]
        out["global"]["rows_dropped_by_placeholder_fix"] = t["dropped_new"]
    out["notes"] = ("行级质量指标的分母是 mapped（已映射行）；zip5_invalid/missing、coord_out_of_range 是 mapped 内部的细项"
                    "；addrkey_v3 / house_number 占位值修正来自 amend_rewrite.py 的全量重写（键 = engine/outlet_clean.addrkey_v3）")
    json.dump(out, open(os.path.join(HERE, "field-stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out["global"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
