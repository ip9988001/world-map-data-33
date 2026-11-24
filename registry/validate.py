#!/usr/bin/env python3
"""注册表校验器：YAML 键完整、id 唯一、每方言 ≥3 golden case、枚举合法、fallback 存在、分母闭合。

用法：
  python3 registry/validate.py [--yaml registry/dialects.v1.yaml]
退出码：0 = 通过；1 = 有错（打印每条错误，不改任何文件）。

设计原则：**只有检查，没有修复**。缺一条就 exit 1 —— 让 CI 和人工都不能「凑过去」。
"""
from __future__ import annotations

import argparse
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_YAML = os.path.join(HERE, "dialects.v1.yaml")

SCHEMA = "dialects.v1/2026-11-24"
GRANULARITY_ENUM = {"building_point", "apartment_unit_point", "parcel_centroid",
                    "range_interpolation", "centerline_midpoint", "unknown"}
STATUS_ENUM = {"active", "minimal_safe", "manual"}
REASONS = {"template_unresolved", "share_below_1pct", "alias_conflict", "geom_unsupported",
           "no_golden_evidence"}   # 第 5 个：模板已解析但没有任何真实样值层可做 golden case
MAPPING_KEYS = {"housenumber", "street", "unit", "city", "state", "zip"}
CRS_KEYS = {"epsg", "datum", "basis", "evidence"}
GC_KEYS = {"id", "dialect_id", "source_layer", "input", "expect"}


def validate(doc) -> list:
    errs = []
    if not isinstance(doc, dict):
        return ["根节点不是 mapping"]

    if doc.get("schema") != SCHEMA:
        errs.append(f"schema 必须是 {SCHEMA}，实际 {doc.get('schema')!r}")

    den = doc.get("denominator") or {}
    for k in ("d1_remote", "d2_local", "total"):
        if not isinstance(den.get(k), int):
            errs.append(f"denominator.{k} 缺失或不是整数")
    if isinstance(den.get("d1_remote"), int) and isinstance(den.get("d2_local"), int) \
            and isinstance(den.get("total"), int):
        if den["d1_remote"] + den["d2_local"] != den["total"]:
            errs.append(f"分母不闭合：{den['d1_remote']} + {den['d2_local']} != {den['total']}")
    if den.get("expected_total") and den.get("total") != den.get("expected_total"):
        errs.append(f"分母与 expected_total 不一致：{den.get('total')} != {den.get('expected_total')}")

    cap = doc.get("weekly_cap_layers")
    if not isinstance(cap, int) or cap <= 0:
        errs.append("weekly_cap_layers 缺失或不是正整数")

    fb = doc.get("fallback") or {}
    if fb.get("dialect_id") != "minimal_safe":
        errs.append("fallback.dialect_id 必须是 minimal_safe")
    if fb.get("pool") != "manual":
        errs.append("fallback.pool 必须是 manual（minimal_safe 永不进 A 货池）")
    if fb.get("a_pool_eligible") is not False:
        errs.append("fallback.a_pool_eligible 必须是 false")
    for r in fb.get("reasons") or []:
        if r not in REASONS:
            errs.append(f"fallback.reasons 出现未定义 reason：{r!r}")

    dialects = doc.get("dialects") or []
    if not dialects:
        errs.append("dialects 为空")
    gcs = doc.get("golden_cases") or []
    gc_by_id = {}
    for g in gcs:
        if not isinstance(g, dict):
            errs.append("golden_cases 里有非 mapping 项")
            continue
        miss = GC_KEYS - set(g)
        if miss:
            errs.append(f"golden case {g.get('id')!r} 缺键 {sorted(miss)}")
        if g.get("id") in gc_by_id:
            errs.append(f"golden case id 重复：{g.get('id')!r}")
        gc_by_id[g.get("id")] = g
        if not g.get("source_layer"):
            errs.append(f"golden case {g.get('id')!r} 缺 source_layer（不许编样值）")
        if not isinstance(g.get("input"), dict) or not g["input"]:
            errs.append(f"golden case {g.get('id')!r} 的 input 为空")
        if not isinstance(g.get("expect"), dict) or not g["expect"]:
            errs.append(f"golden case {g.get('id')!r} 的 expect 为空")
        if isinstance(g.get("expect"), dict):
            if "housenumber" not in g["expect"] or "street" not in g["expect"]:
                errs.append(f"golden case {g.get('id')!r} 的 expect 缺 housenumber/street（minimal_safe 底线）")

    ids = set()
    for d in dialects:
        did = d.get("id")
        if not did:
            errs.append("存在没有 id 的方言")
            continue
        if did in ids:
            errs.append(f"方言 id 重复：{did}")
        ids.add(did)

        prov = d.get("provider") or {}
        if not prov.get("kind"):
            errs.append(f"{did}: 缺 provider.kind")
        tpl = d.get("template") or {}
        for k in ("number_aliases", "street_aliases"):
            if not tpl.get(k):
                errs.append(f"{did}: 缺 template.{k}（minimal_safe 至少需要门牌+街名两族）")
        if not tpl.get("signature"):
            errs.append(f"{did}: 缺 template.signature")

        geom = d.get("geom") or {}
        gran = geom.get("granularity")
        if gran not in GRANULARITY_ENUM:
            errs.append(f"{did}: geom.granularity 非法或缺失：{gran!r}（枚举 {sorted(GRANULARITY_ENUM)}）")
        if not geom.get("type"):
            errs.append(f"{did}: 缺 geom.type")

        crs = d.get("crs") or {}
        miss = CRS_KEYS - set(crs)
        if miss:
            errs.append(f"{did}: crs 缺键 {sorted(miss)}（无证据要写 unknown + basis: unknown，不许默认 4326）")
        if crs.get("epsg") in (None, ""):
            errs.append(f"{did}: crs.epsg 为空（写 unknown 也要显式写）")

        mp = d.get("mapping") or {}
        if set(mp) != MAPPING_KEYS:
            errs.append(f"{did}: mapping 键不完整：{sorted(set(mp))}")

        cov = d.get("coverage") or {}
        for k in ("layers_n", "rows", "share"):
            if k not in cov:
                errs.append(f"{did}: coverage 缺 {k}")

        st = d.get("status")
        if st not in STATUS_ENUM:
            errs.append(f"{did}: status 非法：{st!r}")
        if not isinstance(d.get("a_pool_eligible"), bool):
            errs.append(f"{did}: a_pool_eligible 必须是 bool")
        if d.get("a_pool_eligible") and st != "active":
            errs.append(f"{did}: a_pool_eligible=true 但 status!=active")
        if st == "active" and gran == "unknown":
            errs.append(f"{did}: 粒度 unknown 的方言不许 active")

        refs = d.get("golden_cases") or []
        if not (3 <= len(refs) <= 5):
            errs.append(f"{did}: golden_cases 必须 3–5 条，实际 {len(refs)}")
        for gid in refs:
            g = gc_by_id.get(gid)
            if not g:
                errs.append(f"{did}: golden_cases 引用了不存在的 case {gid!r}")
            elif g.get("dialect_id") != did:
                errs.append(f"{did}: case {gid} 的 dialect_id={g.get('dialect_id')!r} 不匹配")

    for g in gcs:
        if g.get("dialect_id") not in ids:
            errs.append(f"case {g.get('id')!r} 指向不存在的方言 {g.get('dialect_id')!r}")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", default=DEFAULT_YAML)
    a = ap.parse_args(argv)
    if not os.path.exists(a.yaml):
        print(f"FAIL 找不到注册表：{a.yaml}")
        return 1
    with open(a.yaml, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    errs = validate(doc)
    if errs:
        print(f"FAIL {len(errs)} 处问题（{a.yaml}）")
        for e in errs:
            print("  -", e)
        return 1
    print(f"OK {a.yaml}: dialects={len(doc['dialects'])} "
          f"golden_cases={len(doc['golden_cases'])} "
          f"denominator={doc['denominator']['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
