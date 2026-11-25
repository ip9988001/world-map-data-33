#!/usr/bin/env python3
"""从分组产物生成 `registry/dialects.v1.yaml`（确定性；不联网；可一键复跑）。

只读：analysis/dialect-20261124/{dialect.json, dialect-assignment.csv, probe-fields.ndjson}
     analysis/full-inventory-20261124/{inventory-local-all.csv, inventory-local-fields.csv}
写出：registry/dialects.v1.yaml

golden case 的取数规则（不许编）：
  · 值：`inventory-local-fields.csv` 里该层真实样值（house_number / street_name / unit / postal_city /
    state_abbr / zip5 的第一条非空 sample）
  · 字段名：该层 provider 的**真实上游字段名**（`probe-fields.ndjson` 的 `?f=json` 结果，按别名族映射）
  · 必带 `source_layer`（dist 层目录）+ `source_field`（canonical 字段名）
  · 每方言 3–5 条；不足 3 条的方言不会出现在本 YAML（分组脚本已用同一门槛筛过）
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_dialects import pick_sample  # noqa: E402  同一套样值可用性校验

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIAL = os.path.join(ROOT, "analysis", "dialect-20261124")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124")
OUT = os.path.join(ROOT, "registry", "dialects.v1.yaml")
ENGINE_DIR = os.path.join(ROOT, "engine", "dialects")
ALIAS_SAMPLES = os.path.join(ROOT, "analysis", "combo-step2-close-20261125", "p7-samples.csv")

CANON = {"number": ("house_number", "_house_num"), "street": ("street_name", "street_full"),
         "unit": ("unit",), "place": ("postal_city",), "state": ("state_abbr",), "zip": ("zip5",)}
TARGET = {"number": "housenumber", "street": "street", "unit": "unit",
          "place": "city", "state": "state", "zip": "zip"}


def load_probe():
    out = {}
    for line in open(os.path.join(DIAL, "probe-fields.ndjson"), encoding="utf-8"):
        r = json.loads(line)
        out[r["provider"]] = r
    return out


def norm(f):
    return re.sub(r"[^a-z0-9]", "", (f or "").lower())


NUM_NEG = re.compile(r"parcel|route|hwy|phone|area|bike|juris|district|tract|lot|block|gpid|objectid|"
                     r"fid|globalid|permit|book|page|sheet|sqft|mile|percent|year|capacity|lane|unit")
FAM = [
    ("number", re.compile(r"^(?:l|r)?h(?:ouse)?n(?:um|o|umber)?$|house_?number|hse_?num|add(?:r(?:ess)?)?_?num|"
                          r"addr_?no|st(?:reet)?_?num|site_?addr(?:ess)?_?(?:num)?|bldg_?no|"
                          r"^num$|^number$|^hn$|^no$|^streetno$|^pre_?addr|^addrnum|situs_?num")),
    ("street", re.compile(r"street_?name|^street$|^st$|st_?name|^stname|lst_?name|rd_?name|road_?name|"
                          r"full_?street|street_?full|street_?norm|^road$|^thoroughfare|"
                          r"st_?pre_?dir|st_?post_?dir|st_?type|street_?suffix|street_?prefix|"
                          r"street|situs_?street")),
    ("unit", re.compile(r"^unit|unit_?num|apt|apartment|suite|^ste$|^sub_?addr|^bldg_?unit")),
    ("place", re.compile(r"city|town|municipal|postal_?city|place|msag|community|locality|village|"
                         r"borough|postal_?comm")),
    ("state", re.compile(r"^state$|^st_?abbr|state_?abbr|^statecode|^state_?code")),
    ("zip", re.compile(r"zip|postal_?code|post_?code|postcode|^zip5|^zip_?code|^postal$")),
]


def fam_of(field):
    n = norm(field)
    if not n or NUM_NEG.search(n):
        return ""
    for fam, rx in FAM:      # 注意：number 优先，street 次之（order 即优先级）
        if rx.search(n):
            return fam
    return ""


def family_aliases(fields):
    out = defaultdict(list)
    for f in fields or []:
        fam = fam_of(f)
        if fam:
            out[fam].append(f)
    return dict(out)


def engine_alias_extensions():
    """engine/dialects/*.yaml 里 `family: alias_extension` 的条目（别名来源；registry 不重复维护别名）。

    组合拳②（2026-11-25）Muse 口径：registry 是分档唯一真源，engine 表只是「别名来源」，
    生成时合并进来，避免两处各写一份 27 条。合并后 registry 里出现的 id 与 engine 表一致，可逐条对照。
    """
    import glob
    out = []
    for p in sorted(glob.glob(os.path.join(ENGINE_DIR, "*.yaml"))):
        for d in (yaml.safe_load(open(p, encoding="utf-8")) or {}).get("dialects") or []:
            if d.get("family") == "alias_extension":
                out.append(dict(d, _from=os.path.relpath(p, ROOT)))
    return out


def alias_ext_dialect(ext, gid):
    """别名扩展条目 → registry 方言 + 3–5 条真实样值 golden case（样值来自 coord-samples，不编）。"""
    if not os.path.exists(ALIAS_SAMPLES):
        print(f"SKIP {ext['id']}: 缺 {os.path.relpath(ALIAS_SAMPLES, ROOT)}", file=sys.stderr)
        return None, [], gid
    cases, ids = [], []
    for r in list(csv.DictReader(open(ALIAS_SAMPLES, encoding="utf-8")))[:5]:
        gid += 1
        cid = f"gc-{gid:03d}"
        cases.append({"id": cid, "dialect_id": ext["id"],
                      # 该批层是远程 D1 层，dist/ 下没有 layer 目录；样值证据是仓库内 committed 的坐标样本 CSV 目录
                      "source_layer": os.path.dirname(r["csv_file"]) or ".",
                      "source_table": r["csv_file"], "source_row_index": r["row_index"],
                      "source_url": r["url"],
                      "source_fields": {"housenumber": r["number_field"], "street": r["street_field"]},
                      "input": {r["number_field"]: r["number_value"],
                                r["street_field"]: r["street_value"]},
                      "expect": {"housenumber": r["number_value"], "street": r["street_value"]},
                      "expect_flags": ["no_city_ok", "no_zip_ok"]})
        ids.append(cid)
    if len(ids) < 3:
        print(f"SKIP {ext['id']}: golden cases={len(ids)} < 3", file=sys.stderr)
        return None, [], gid
    num, st = list(ext["fields"].get("number") or []), list(ext["fields"].get("street") or [])
    d = {
        "id": ext["id"],
        "provider": {"kind": "alias_extension", "orgs": [], "orgs_total": len(ext.get("source_layers") or []),
                     "note": f"别名扩展（非采集源族）：{ext.get('_from')}:{ext['id']}；"
                             f"由 P7 组 321 层的真实列名去重而来"},
        "template": {"number_aliases": num, "street_aliases": st, "unit_aliases": [],
                     "place_aliases": [], "state_aliases": [], "zip_aliases": [],
                     "signature": f"ext-{len(num)}n-{len(st)}s",
                     "basis": f"{ext.get('_from')}:{ext['id']}（组合拳② 别名扩展，生成时合并，不二次维护）"},
        "geom": {"type": "esriGeometryUnknown", "granularity": "unknown"},
        "crs": {"epsg": "unknown", "datum": "unknown", "basis": "unknown",
                "evidence": "别名扩展条目不带几何/CRS；几何由被赋该方言的源自身声明"},
        "mapping": {k: f"${k}" for k in ("housenumber", "street", "unit", "city", "state", "zip")},
        "coverage": {"layers_n": 321, "rows": 5520975, "share": round(321 / 17168, 6)},
        "anomaly": {"rate": 0.0, "method": "别名来源层已逐层做过值形态校验（门牌纯数字 + 街名有字母）"},
        "status": "minimal_safe",
        "a_pool_eligible": False,
        "golden_cases": ids,
        "notes": "组合拳②：27 条别名（19 门牌 + 8 街名）。只扩大 minimal_safe / E7 的别名并集，"
                 "不改任何既有方言的 template，因此不影响已有层的方言归属。",
    }
    return d, cases, gid


def main():
    d = json.load(open(os.path.join(DIAL, "dialect.json"), encoding="utf-8"))
    probe = load_probe()
    fields_by_layer = defaultdict(dict)
    for r in csv.DictReader(open(os.path.join(INV, "inventory-local-fields.csv"), encoding="utf-8")):
        r["samples"] = [s.strip() for s in (r["samples"] or "").split("|") if s.strip()]
        fields_by_layer[r["layer_dir"]][r["field"]] = r
    url_to_dir = {}
    for r in csv.DictReader(open(os.path.join(INV, "inventory-local-all.csv"), encoding="utf-8")):
        if r.get("readable") == "1" and r["url"].strip():
            url_to_dir[r["url"].rstrip("/")] = r["layer_dir"]
    assign = list(csv.DictReader(open(os.path.join(DIAL, "dialect-assignment.csv"), encoding="utf-8")))
    by_dialect = defaultdict(list)
    for a in assign:
        by_dialect[a["dialect_id"]].append(a)

    dialects, gcs = [], []
    gid = 0
    for row in d["dialect_rows"]:
        did = row["dialect_id"]
        providers = [p for p, n in row["providers"]]
        # 该方言覆盖的 provider 的真实别名（按族合并，去重保序）
        aliases = defaultdict(list)
        epsg = Counter()
        basis = Counter()
        for p, n in row["providers"]:
            pr = probe.get(p)
            if not pr:
                continue
            for fam, lst in family_aliases(pr.get("fields")).items():
                for a in lst:
                    if a not in aliases[fam]:
                        aliases[fam].append(a)
            sr = pr.get("sr") or {}
            e = sr.get("latestWkid") or sr.get("wkid")
            if e:
                epsg[e] += n
                basis["declared"] += n
            elif sr.get("wkt"):
                basis["declared_wkt"] += n
            else:
                basis["unknown"] += n
        # golden cases：本方言里能造样值的本地层（house_number + street_name 都有样值）
        cases = []
        for a in sorted(by_dialect[did], key=lambda x: x["url"]):
            if a["universe"] != "d2":
                continue
            # 通过 url 反查本地目录
            layer_dir = url_to_dir.get(a["url"].rstrip("/"))
            if not layer_dir:
                continue
            f = fields_by_layer.get(layer_dir) or {}
            num_ok = next((pick_sample("housenumber", f[k]["samples"]) for k in CANON["number"]
                           if f.get(k) and f[k]["samples"]), None)
            st_ok = next((pick_sample("street", f[k]["samples"]) for k in CANON["street"]
                          if f.get(k) and f[k]["samples"]), None)
            if not (num_ok and st_ok):
                continue
            pr = probe.get(a["provider_id"])
            if not pr:
                continue
            fa = family_aliases(pr.get("fields"))
            # 别名 ↔ canonical 的配对要「按语义」挑，否则会出现「StreetFull 的值塞进 street」
            ST_STEPS = [("street_name", re.compile(r"street_?name|situs_?street|^street$|^st$")),
                        ("street_full", re.compile(r"street_?full|full_?street|full_?addr"))]
            NUM_STEPS = [("house_number", re.compile(r"h(ouse)?_?num|housenumber|^hn$|situs_?num|"
                                                    r"add(r)?_?num|^number$|^num$")),
                         ("_house_num", re.compile(r".*"))]
            st_alias = st_canon = None
            for canon, rx in ST_STEPS:
                alias = next((a for a in fa.get("street", []) if rx.search(norm(a))), None)
                if alias and any(f.get(canon) and f[canon]["samples"] for _ in (0,)):
                    st_alias, st_canon = alias, canon
                    break
            num_alias = num_canon = None
            for canon, rx in NUM_STEPS:
                alias = next((a for a in fa.get("number", []) if rx.search(norm(a))), None)
                if alias:
                    num_alias, num_canon = alias, canon
                    break
            fam_alias = {"number": num_alias, "street": st_alias}
            fam_canon = {"number": num_canon, "street": st_canon}
            for fam in ("unit", "place", "state", "zip"):
                fam_alias[fam] = (fa.get(fam) or [None])[0]
                fam_canon[fam] = None
            inp, expect, src_fields = {}, {}, {}
            for fam in ("number", "street", "unit", "place", "state", "zip"):
                if not fam_alias.get(fam):
                    continue
                canonical = fam_canon.get(fam) or next(
                    (k for k in CANON[fam] if f.get(k) and f[k]["samples"]), None)
                if not canonical:
                    continue
                val = pick_sample(TARGET[fam], f[canonical]["samples"])
                if val is None:
                    continue
                inp[fam_alias[fam]] = val
                expect[TARGET[fam]] = val
                src_fields[TARGET[fam]] = canonical
            if "housenumber" not in expect or "street" not in expect:
                continue
            gid += 1
            cases.append({"id": f"gc-{gid:03d}", "source_layer": layer_dir, "source_table": "addr",
                          "source_fields": src_fields, "input": inp, "expect": expect,
                          "expect_flags": ["no_city_ok"] if a["usable"] == "no_city" else
                                          (["no_zip_ok"] if a["usable"] == "no_zip" else ["full_ok"])})
            if len(cases) >= 5:
                break
        if len(cases) < 3:
            print(f"SKIP {did}: golden cases={len(cases)} < 3", file=sys.stderr)
            continue
        for c in cases:
            c["dialect_id"] = did
        gcs.extend(cases)
        gran = row["granularity"]
        epsg_top = [[e, n] for e, n in epsg.most_common(3)]
        mapped = {TARGET[f]: ("$" + TARGET[f]) for f in ("number", "street", "unit", "place", "state", "zip")}
        mapped["housenumber"] = "$housenumber"
        dialects.append({
            "id": did,
            "provider": {"kind": row["provider_kind"],
                         "orgs": [[p.split(":", 1)[1], n] for p, n in row["providers"][:15]],
                         "orgs_total": len(row["providers"]),
                         "note": "orgs 只列前 15（层数降序），全量在 analysis/dialect-20261124/dialect.json"},
            "template": {"number_aliases": aliases.get("number", []),
                         "street_aliases": aliases.get("street", []),
                         "unit_aliases": aliases.get("unit", []),
                         "place_aliases": aliases.get("place", []),
                         "state_aliases": aliases.get("state", []),
                         "zip_aliases": aliases.get("zip", []),
                         "signature": f"t{row['template_bits']}",
                         "basis": "probe:?f=json（真实上游字段名，见 analysis/dialect-20261124/probe-fields.ndjson）"},
            "geom": {"type": "esriGeometry" + ({"buildingpoint": "Point"}.get(gran, "Unknown")),
                     "granularity": gran},
            "crs": {"epsg": epsg_top[0][0] if epsg_top else "unknown",
                    "datum": "unknown" if not epsg_top else "declared_by_service",
                    "basis": "declared" if basis.get("declared") else
                             ("declared_wkt" if basis.get("declared_wkt") else "unknown"),
                    "evidence": f"probe spatialReference 分布 {epsg_top}（不做‘美国默认 4326’假设）"},
            "mapping": {k: f"${k}" for k in ("housenumber", "street", "unit", "city", "state", "zip")},
            "coverage": {"layers_n": row["layers_n"], "rows": row["rows"], "share": row["share"]},
            "anomaly": {"rate": round(sum(1 for x in by_dialect[did] if x["usable"] == "road_only")
                                      / max(1, row["layers_n"]), 4),
                        "method": "组内 road_only 层占比（无门牌、只有街名）"},
            "status": row["status"],
            "a_pool_eligible": bool(row["status"] == "active" and len(cases) >= 3),
            "golden_cases": [c["id"] for c in cases],
            "notes": (f"模板签名 {row['template_bits']}（number|street|unit|place|state|zip 依次）; "
                      f"覆盖 provider {len(row['providers'])} 个; 样值层 {row['sample_layers']} 个"),
        })

    # ---- 别名扩展方言（合并 engine 表；registry 唯一真源）----
    for ext in engine_alias_extensions():
        alias_dialect, cases, gid = alias_ext_dialect(ext, gid)
        if alias_dialect:
            dialects.append(alias_dialect)
            gcs.extend(cases)

    json.dump({"groups": [[d["provider"]["kind"], d["template"]["signature"][1:],
                           d["geom"]["granularity"]] for d in dialects],
               "ids": [d["id"] for d in dialects]},
              open(os.path.join(DIAL, "registry-approved.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    doc = {
        "schema": "dialects.v1/2026-11-24",
        "denominator": d["denominator"],
        "weekly_cap_layers": d["weekly_cap_layers"],
        "fallback": {"dialect_id": "minimal_safe", "pool": "manual", "a_pool_eligible": False,
                     "rule": "只取『门牌 + 街名』两要素；任一缺失 → pool=manual，永不进 A 货池",
                     "reasons": ["template_unresolved", "share_below_1pct", "alias_conflict",
                                 "geom_unsupported", "no_golden_evidence"]},
        "dialects": sorted(dialects, key=lambda x: -x["coverage"]["rows"]),
        "golden_cases": sorted(gcs, key=lambda x: x["id"]),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("# 方言注册表 v1（生成物：python3 analysis/dialect-20261124/gen_registry.py）\n")
        fh.write("# 分母 16,010(D1) + 1,158(D2) = 17,168；D3(25,447 empty_shell) 只做 provider 聚类\n")
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, width=120)
    print(json.dumps({"dialects": len(dialects), "golden_cases": len(gcs),
                      "active": sum(1 for x in dialects if x["status"] == "active"),
                      "out": OUT}, ensure_ascii=False))
    return 0 if len(dialects) >= 3 and len(gcs) >= 3 * len(dialects) else 1


if __name__ == "__main__":
    sys.exit(main())
