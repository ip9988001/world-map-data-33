#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自证：schema/field-map-v2.json 严格对应二仓 LOCKED SCHEMA 2.0（rev2）。

跑法：python3 analysis/assert_field_map_v2.py        # 全绿 exit 0，任何一条红 exit 1
检查项：
  1. SCHEMA 固定副本 sha256 与脚本常量一致（防被人改 schema 后偷偷对不上）
  2. SCHEMA rev>=2 且 provenance 含 4 个三仓字段、enums.src_kind 取值一致
  3. field-map 的 19 个目标字段 **逐个** 存在于 SCHEMA primary_fields（不许多、不许改名）
  4. 4 个溯源字段逐个存在于 SCHEMA provenance_fields
  5. 每层都齐 19 + 4 个键；没有 SCHEMA 之外的字段名
  6. 每层引用的源列必须真实存在于该层画像里（`[[...]]` 标记除外）
  7. 层覆盖 ≥ 95%
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PIN = os.path.join(ROOT, "schema", "upstream", "SCHEMA-v2.0.world-map-data-test.json")
FM = os.path.join(ROOT, "schema", "field-map-v2.json")
SHA = "02d5690a3c501fddeae4c338df4c7b62274c498a8a1b59bc54e6823e570ae14c"

TARGETS = ["house_number", "house_number_suffix", "street_pre_dir", "street_name", "street_post_type",
           "street_post_dir", "street_full", "unit", "postal_city", "municipal_city", "county_name",
           "county_fips", "state_abbr", "zip5", "latitude", "longitude", "addr_type",
           "full_formatted_address", "source_confidence"]
PROV = ["src_kind", "src_layer_id", "src_layer_url", "src_parcel_id"]

fails: list[str] = []
warns: list[str] = []


def ok(cond: bool, msg: str) -> None:
    print(("  ✅ " if cond else "  ❌ ") + msg)
    if not cond:
        fails.append(msg)


def main() -> int:
    print("== 1. SCHEMA 固定副本 ==")
    raw = open(PIN, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    ok(got == SHA, "sha256 == %s…（实际 %s…）" % (SHA[:12], got[:12]))
    sc = json.loads(raw)
    ok(sc["schema_version"] == "2.0" and sc["status"] == "LOCKED", "schema_version=2.0 / LOCKED")
    ok(int(sc.get("rev", 0)) >= 2, "rev=%s（≥2，含三仓溯源字段）" % sc.get("rev"))
    prim = [f["name"] for f in sc["primary_fields"]]
    prov = [f["name"] for f in sc["provenance_fields"]]
    ok(len(prim) == 32, "主字段 32 个（实际 %d）" % len(prim))

    print("== 2. 4 个三仓溯源字段在 SCHEMA 里 ==")
    for p in PROV:
        ok(p in prov, "provenance 含 %s" % p)
    sk = next((f for f in sc["provenance_fields"] if f["name"] == "src_kind"), {})
    want = ["address_point", "parcel_situs", "street_line"]
    # SCHEMA 里 provenance 枚举字段沿用 note 写法（与 zip_source 等一致），取值以 enums 为准
    ok(sc.get("enums", {}).get("src_kind") == want,
       "enums.src_kind = address_point|parcel_situs|street_line")
    ok(all(v in (sk.get("note") or "") for v in want), "src_kind 字段 note 里写明三个取值")

    print("== 3. field-map 目标字段逐一对应 ==")
    fm = json.load(open(FM, encoding="utf-8"))
    declared = [t["name"] for t in fm["target_fields"]]
    ok(declared == TARGETS, "target_fields 顺序与约定一致（19 个）")
    for t in TARGETS:
        ok(t in prim, "%s ∈ SCHEMA primary_fields" % t)
    extra = [t for t in declared if t not in prim]
    ok(not extra, "没有 SCHEMA 之外的目标字段（多出：%s）" % extra)
    ok(fm.get("not_a_schema") is True, "文件自述 not_a_schema=true（是映射，不是新 schema）")

    print("== 4. 4 个溯源字段在 field-map 里有逐层取值 ==")
    pnames = [f["name"] for f in fm["provenance_ext"]["fields"]]
    ok(pnames == PROV, "provenance_ext 定义的字段 = %s" % PROV)
    for p in PROV:
        ok(p in prov, "%s ∈ SCHEMA provenance_fields" % p)

    print("== 5. 逐层完整性 / 无自造字段 ==")
    layers = fm["layers"]
    missing_keys = []
    invented = set()
    for lid, e in layers.items():
        for k in TARGETS + PROV:
            if k not in e:
                missing_keys.append((lid, k))
    ok(not missing_keys, "每层都齐 19+4 个键（缺 %d 处）" % len(missing_keys))
    for e in layers.values():
        for k in e:
            if k in PROV or k in ("rows_total", "sampled", "csv", "blocking", "mappable_primary",
                                  "state_src", "county_scope", "county_src"):
                continue
            if k not in TARGETS:
                invented.add(k)
    ok(not invented, "层内没有 SCHEMA 之外的字段名（多出：%s）" % sorted(invented))

    print("== 6. 源列必须真实存在（逐层核对画像） ==")
    prof = {}
    for f in glob.glob(os.path.join(ROOT, "analysis", "out", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        prof[d["layer_id"]] = set((d.get("fields") or {}))

    bad_src = []
    for lid, e in layers.items():
        cols = prof.get(lid)
        if cols is None:
            continue
        for t in TARGETS:
            src = (e.get(t) or {}).get("src")
            if not src or src.startswith("[[") or src == "value_rules." + t:
                continue
            if src not in cols:
                bad_src.append((lid, t, src))
    ok(not bad_src, "所有 src 都是该层真实存在的列（异常 %d 处）" % len(bad_src))

    print("== 7. 覆盖 ==")
    n_files = len(glob.glob(os.path.join(ROOT, "analysis", "out", "*.json")))   # 含 17 层双记账
    cov = fm["coverage"]
    cov_pct = 100.0 * len(layers) / max(1, n_files)
    ok(cov_pct >= 95.0, "层覆盖 %.1f%% ≥95%%（%d/%d 画像文件，去重后 %d 个 layer_id）"
       % (cov_pct, len(layers), n_files, cov["layers_profiled"]))
    ok(cov["layers_profiled"] == len(layers), "coverage 里的层数与 layers 一致")
    print("  ℹ️ usable：v1(只认 state 列) %d（%.2f%%）→ v2(state 回填) %d（%.2f%%）→ v3(+县可判) %d（%.2f%%）"
          % (cov["usable_v1_state_column_only"], cov["usable_v1_pct"],
             cov["usable_v2_after_state_backfill"], cov["usable_v2_pct"],
             cov["usable_v3_after_county"], cov["usable_v3_pct"]))

    print()
    if fails:
        print("❌ %d 项未通过" % len(fails))
        return 1
    print("✅ 全部通过（field-map-v2 与 SCHEMA 2.0 rev2 一一对应）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
