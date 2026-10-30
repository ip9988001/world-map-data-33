#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""语义裁定审计（addr_type / city）—— 只抽真行，不做启发式。

两条裁定（2026-10-30 用户明令，此后不再变）：
  ① addr_type：v1 阶段**一律 `Unknown`**，除非层内存在**明确分类字段**
     （AddrClass / UseCode / LANDUSE 之类）且其取值**能逐值映射**到 SCHEMA 枚举。
     禁止「unit 非空 → Multi-Unit」「标题含 COMMERCIAL → Commercial」这类启发式：
     标题不是逐行语义，无法溯源，会污染下游。
  ② CITY：postal_city 只认「邮件城市」语义的列 + 值校验；municipal_city 只认
     法定市政列。**不确定一律 null**（SCHEMA 允许，配 postal_city_source=null），
     宁可空不可错。

本脚本干的事：
  addr_type  找出所有含「明确分类列」的层，逐层抽 25 行看真实取值分布，
             统计每个取值的映射覆盖率；覆盖率 ≥ COVER_MIN 才给该层出映射表，
             否则该层 addr_type 一律 Unknown（并在证据里写明为什么放弃）。
  city       分层抽取 CITY / POSTAL_CITY / MUNICIPALITY / OWNER_CITY 四种列的
             真值 500 行，算「同名率」「含 ZIP 率」「Unincorporated 率」等命中率，
             产出列白/黑名单 + 值校验规则。

输出：
  schema/addr-type-map-v1.json     逐层 addr_type 映射（value_map + 覆盖率 + 证据）
  schema/city-rules-v1.json        列白/黑名单 + 值规则 + 实测命中率
  analysis/semantic-audit-2026-10-30.json   抽样原始证据（可复核）
  docs/SEMANTIC-AUDIT-2026-10-30.md         人读版

用法：
  python3 analysis/semantic_audit.py both        # 两条都跑（各抽 500 行）
  python3 analysis/semantic_audit.py city --rows 500 --layers 25
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "collect"))
from lib.fetch import get_json                              # noqa: E402
from address_probe import api_of                            # noqa: E402

OUT = os.path.join(HERE, "out")
SCHEMA_DIR = os.path.join(ROOT, "schema")
COVER_MIN = 0.80        # 逐值映射覆盖率下限：达不到就不给该层映射（一律 Unknown）

# ---------------------------------------------------------------- 明确分类列（白名单）
# 只收「语义就是地址/用地分类」的列。CLASS / CLASS_CODE / PROP_TYPE 这类在别处常指
# 税级或区划等级，语义不可证 —— 一律不收（宁可 Unknown）。
CLASS_COLS = [
    r"ADDRCLASS", r"ADDR_CLASS", r"ADDRESS_CLASS", r"ADDR_TYPE", r"ADDRTYPE", r"ADDRESS_TYPE",
    r"USECODE", r"USE_CODE", r"USE_DESC", r"LANDUSE", r"LAND_USE", r"LAND_USE_CODE",
    r"SITUS_USECODE", r"PROPERTY_USE", r"BLDG_TYPE", r"BUILDING_TYPE", r"STRUCTURE_TYPE",
]
CLASS_RX = re.compile(r"^(?:%s)$" % "|".join(CLASS_COLS), re.I)

# 逐值映射表（只有这里列出的字面值才会被映射；其余一律 Unknown）
ADDR_TYPE_TOKENS = [
    ("Residential", [
        "RESIDENTIAL", "RES", "RESIDENCE", "RESIDENT", "R", "SFR", "SINGLE FAMILY",
        "SINGLE-FAMILY", "SINGLE FAMILY RESIDENTIAL", "SINGLE FAMILY DWELLING", "1 FAMILY",
        "ONE FAMILY", "HOUSE", "HOMES", "DWELLING", "DWELLING UNIT", "RESIDENTIAL SINGLE FAMILY",
        "RESIDENTIAL 1 FAMILY", "R-1 FAMILY", "MOBILE HOME", "MANUFACTURED HOME",
    ]),
    ("Residential (Multi-Unit)", [
        "MULTI FAMILY", "MULTIFAMILY", "MULTI-FAMILY", "MULTI FAMILY RESIDENTIAL",
        "APARTMENT", "APARTMENTS", "APT", "APARTMENT BUILDING", "CONDO", "CONDOS",
        "CONDOMINIUM", "CONDOMINIUMS", "DUPLEX", "TRIPLEX", "FOURPLEX", "TOWNHOUSE",
        "TOWNHOUSES", "TOWNHOME", "MULTI UNIT", "MULTI-UNIT", "MULTIFAMILY RESIDENTIAL",
        "RESIDENTIAL MULTI FAMILY", "HIGH RISE", "HIGH-RISE",
    ]),
    ("Commercial", [
        "COMMERCIAL", "COMM", "BUSINESS", "RETAIL", "OFFICE", "OFFICES", "INDUSTRIAL",
        "WAREHOUSE", "STORAGE", "HOTEL", "MOTEL", "RESTAURANT", "RETAIL STORE", "STORE",
        "SHOPPING CENTER", "MALL", "MIXED USE", "MIXED-USE", "GOVERNMENT", "PUBLIC",
        "INSTITUTIONAL", "SCHOOL", "CHURCH", "HOSPITAL", "MEDICAL", "GARAGE", "PARKING",
    ]),
]
UNKNOWN_TOKENS = {"", "NONE", "NULL", "NAN", "UNKNOWN", "UNK", "N/A", "NA", "0", "-", "--",
                  "NOT SPECIFIED", "NOTSPECIFIED", "OTHER", "MISC"}

# ---------------------------------------------------------------- CITY 列语义
POSTAL_COLS = [r"POST_CITY", r"POSTAL_CITY", r"POSTALCITY", r"MAIL_CITY", r"MAILING_CITY",
               r"CITY_POSTAL", r"CITY_MAILING", r"POST_OFFICE_CITY", r"PO_CITY", r"POSTAL_TOWN"]
MUNI_COLS = [r"INC_MUNI", r"INCMUNI", r"MUNICIPALITY", r"MUNICIPAL_NAME", r"MUNI_NAME",
             r"MUNICIPAL", r"CITY_OF", r"TOWNSHIP", r"TOWNSHIP_NAME"]
GENERIC_COLS = [r"CITY", r"CITY_NAME", r"CITYNAME", r"PLACE_NAME", r"SITUS_CITY", r"ADDRESS_CITY",
                r"ADDR_CITY", r"POSTAL", r"POSTAL_COMM"]
OWNER_COLS = [r"OWNER_CITY", r"OWNER_CITY_STATE", r"MAIL_CITY_OWNER", r"TAXPAYER_CITY"]
COMMUNITY_COLS = [r"COMMUNITY", r"TOWN", r"VILLAGE", r"HAMLET", r"NEIGHBORHOOD"]

POSTAL_RX = re.compile(r"^(?:%s)$" % "|".join(POSTAL_COLS), re.I)
MUNI_RX = re.compile(r"^(?:%s)$" % "|".join(MUNI_COLS), re.I)
GENERIC_RX = re.compile(r"^(?:%s)$" % "|".join(GENERIC_COLS), re.I)
OWNER_RX = re.compile(r"^(?:%s)$" % "|".join(OWNER_COLS), re.I)
COMMUNITY_RX = re.compile(r"^(?:%s)$" % "|".join(COMMUNITY_COLS), re.I)

# 值是「邮件城市」的硬校验：不带数字（含 ZIP/门牌）、不带逗号（"MIAMI, FL 33142-2202"
# 那种是业主整串地址）、不是行政区黑话、长度合理。
CITY_BLACK = {"UNINCORPORATED", "UNINCORPORATED AREA", "UNINC", "UNINC AREA", "NO CITY",
              "NONE", "NULL", "N/A", "NA", "UNKNOWN", "NOT APPLICABLE", "N/A CITY",
              "VARIOUS", "SEE ADDRESS", "SAME", "-", "--", "0", "N A", "CDP", "P O BOX"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- 取层 + 抽样
def profiles() -> list[dict]:
    best = {}
    for f in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        lid = d.get("layer_id")
        if lid and (lid not in best or (d.get("sampled") or 0) > (best[lid].get("sampled") or 0)):
            best[lid] = d
    return list(best.values())


def urls() -> dict:
    import csv
    out = {}
    for name in ("address_layers.csv", "situs_layers.csv"):
        p = os.path.join(ROOT, "collect", name)
        if not os.path.exists(p):
            continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            lid = (r.get("layer_id") or "").strip()
            if lid and lid not in out and r.get("url"):
                out[lid] = r["url"].strip()
    return out


def sample_rows(url: str, n: int) -> list[dict]:
    api = api_of(url)
    meta = get_json(api + "?f=json", timeout=30)
    if "__error__" in meta:
        raise RuntimeError("meta:%s" % str(meta["__error__"])[:80])
    oid = meta.get("objectIdField") or "OBJECTID"
    q = {"where": meta.get("definitionExpression") or "1=1", "outFields": "*",
         "returnGeometry": "false", "f": "json", "resultRecordCount": n,
         "orderByFields": oid}
    d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=60)
    if "__error__" in d:
        q.pop("orderByFields", None)
        d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=60)
    if "__error__" in d:
        raise RuntimeError("query:%s" % str(d["__error__"])[:80])
    return [f.get("attributes") or {} for f in (d.get("features") or [])]


def pick_layers(want, per_col: int, max_layers: int, u: dict) -> list[dict]:
    """按「列名族 × 层」分层取层：同一列名最多 per_col 层，避免一个列名刷满样本。"""
    picked, per = [], {}
    for d in sorted(want, key=lambda x: -(x.get("rows_total") or 0)):
        lid = d["layer_id"]
        if lid not in u:
            continue
        col = d["_col"]
        if per.get(col, 0) >= per_col:
            continue
        per[col] = per.get(col, 0) + 1
        picked.append({"layer_id": lid, "col": col, "url": u[lid],
                       "rows": d.get("rows_total")})
        if len(picked) >= max_layers:
            break
    return picked


# ---------------------------------------------------------------- addr_type
def tok(v) -> str:
    if v is None:
        return ""
    s = re.sub(r"[\s._]+", " ", str(v).strip().upper())
    s = re.sub(r"[^A-Z0-9 /-]", "", s)
    return s.strip()


TOKEN_MAP = {}
for _cls, toks in ADDR_TYPE_TOKENS:
    for t in toks:
        TOKEN_MAP[tok(t)] = _cls


def map_value(v) -> str | None:
    t = tok(v)
    if t in UNKNOWN_TOKENS:
        return "Unknown"
    return TOKEN_MAP.get(t)


def audit_addr_type(rows_per_layer: int, max_layers: int, jobs: int) -> dict:
    prof = profiles()
    u = urls()
    want = []
    for d in prof:
        cols = [n for n in (d.get("fields") or {}) if CLASS_RX.match(n)]
        if not cols:
            continue
        # 取非空率最高的那个明确分类列
        cols.sort(key=lambda n: -((d["fields"][n].get("nonempty") or 0) / max(1, d["fields"][n].get("n") or 1)))
        want.append(dict(d, _col=cols[0]))
    picked = pick_layers(want, per_col=4, max_layers=max_layers, u=u)
    print("[addr_type] 含明确分类列的层 %d，抽样 %d 层 × %d 行"
          % (len(want), len(picked), rows_per_layer), flush=True)

    def work(p):
        try:
            rs = sample_rows(p["url"], rows_per_layer)
            return dict(p, rows=[r.get(p["col"]) for r in rs], err="")
        except Exception as e:                                # noqa: BLE001
            return dict(p, rows=[], err=str(e)[:120])

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        got = list(ex.map(work, picked))

    layers = []
    for g in got:
        vals = [v for v in g["rows"] if v not in (None, "")]
        mapped = [map_value(v) for v in vals]
        hit = sum(1 for m in mapped if m and m != "Unknown")
        cover = hit / len(vals) if vals else 0.0
        dist = {}
        for v, m in zip(vals, mapped):
            dist.setdefault(tok(v), {"n": 0, "as": m})["n"] += 1
        # 逐层映射表：只用该层自己抽到的字面值，不借别层的结论
        vmap = {}
        if vals and cover >= COVER_MIN:
            for v, m in zip(vals, mapped):
                if m and m != "Unknown":
                    vmap[v.strip()] = m
        rec = {"layer_id": g["layer_id"], "col": g["col"], "sampled": len(vals),
               "mapped": hit, "coverage": round(cover, 4),
               "verdict": "map" if vmap else "Unknown",
               "value_map": vmap,
               "top_values": sorted(({"value": k, "n": v["n"], "as": v["as"]}
                                     for k, v in dist.items()), key=lambda x: -x["n"])[:12],
               "err": g["err"]}
        layers.append(rec)

    ok = [r for r in layers if r["verdict"] == "map"]
    print("[addr_type] 抽样成功 %d 层：可映射 %d 层 / 一律 Unknown %d 层"
          % (len(layers), len(ok), len(layers) - len(ok)), flush=True)

    # 全局共识表：≥3 个不同层都命中同一字面值才算「字面值有共识」（供人工复核，
    # 不用于未抽样层 —— 未抽样就是 Unknown；逐层映射以 layers_sampled[].value_map 为准）
    seen = {}
    for r in ok:
        for t in r["top_values"]:
            if t["as"] and t["as"] != "Unknown":
                seen.setdefault(t["value"], set()).add(r["layer_id"])
    table = {v: TOKEN_MAP[v] for v, ls in seen.items() if len(ls) >= 3}

    doc = {
        "schema": "addr-type-map/v1",
        "at": utcnow(),
        "policy": ("v1 一律 Unknown；仅当层内有明确分类列（AddrClass/ADDR_TYPE/UseCode/"
                   "LANDUSE/BLDG_TYPE 等）且抽样 25 行里 ≥80% 的取值能逐值映射到 SCHEMA 枚举时，"
                   "才为该层出映射表。禁止 unit/标题类启发式。"),
        "forbidden_heuristics": ["unit 非空 → Residential (Multi-Unit)",
                                 "层标题含 COMMERCIAL → Commercial",
                                 "source=parcel_situs → Commercial",
                                 "addr_type 继承同州/同服务其它层"],
        "enum": ["Residential", "Residential (Multi-Unit)", "Commercial", "Unknown"],
        "coverage_min": COVER_MIN,
        "value_map": table,
        "value_map_rule": ("逐层映射以 layers_sampled[].value_map 为准（只用该层自抽到的字面值）；"
                           "下表是 ≥3 层共识的参考表；未抽样层一律 Unknown"),
        "unmapped_examples": sorted({t["value"] for r in layers for t in r["top_values"]
                                     if not t["as"] or t["as"] == "Unknown"})[:40],
        "unknown_tokens": sorted(UNKNOWN_TOKENS),
        "layers_sampled": layers,
        "baseline": {"all_layers_value": "Unknown",
                     "note": "未抽样/未达覆盖率的层直接 Unknown，缺省不猜"},
    }
    json.dump(doc, open(os.path.join(SCHEMA_DIR, "addr-type-map-v1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return {"kind": "addr_type", "sampled_layers": len(layers), "mappable": len(ok),
            "value_map": table, "layers": layers}


# ---------------------------------------------------------------- city
def city_class(v) -> str:
    """单个值的语义分类（只做形态判定，不猜城市名真伪）。"""
    if v is None:
        return "empty"
    s = str(v).strip()
    if not s:
        return "empty"
    up = re.sub(r"\s+", " ", s.upper())
    if up in CITY_BLACK:
        return "blacklist"
    if "," in up or ";" in up:                     # "MIAMI, FL 33142-2202"（先判整串地址）
        return "has_punct"
    if re.search(r"\d", up):                       # 含 ZIP/门牌 → 不是干净城市名
        return "has_digit"
    if len(up) > 40:
        return "too_long"
    if not re.match(r"^[A-Z][A-Z .'\-]*$", up):     # 允许 ST. LOUIS / O'FALLON / WINSTON-SALEM
        return "bad_chars"
    return "clean"


def audit_city(rows_per_layer: int, max_layers: int, jobs: int) -> dict:
    prof = profiles()
    u = urls()

    def fam(c):
        if POSTAL_RX.match(c):
            return "postal_named"
        if MUNI_RX.match(c):
            return "municipal_named"
        if OWNER_RX.match(c):
            return "owner_named"
        if COMMUNITY_RX.match(c):
            return "community_named"
        if GENERIC_RX.match(c):
            return "generic_city"
        return None

    cand = []
    for d in prof:
        cols = [(c, fam(c)) for c in (d.get("fields") or {})]
        cols = [(c, f) for c, f in cols if f]
        if not cols:
            continue
        # 优先抽「generic CITY + 另一族并存」的层，这类才能算同名率
        cols.sort(key=lambda cf: (cf[1] != "generic_city", cf[1]))
        cand.append(dict(d, _cols=cols))
    # 分层：generic×25 / postal_named×5 / municipal_named×5 / owner_named×3 / community×3
    quota = {"generic_city": max_layers // 2, "postal_named": 5, "municipal_named": 5,
             "owner_named": 3, "community_named": 3}
    picked, used = [], {}
    for d in sorted(cand, key=lambda x: -(x.get("rows_total") or 0)):
        if d["layer_id"] not in u:
            continue
        for c, f in d["_cols"]:
            if used.get(f, 0) < quota.get(f, 2):
                used[f] = used.get(f, 0) + 1
                picked.append({"layer_id": d["layer_id"], "col": c, "fam": f, "url": u[d["layer_id"]]})
                break
        if len(picked) >= max_layers:
            break
    print("[city] 抽样 %d 层 × %d 行（族分布 %s）"
          % (len(picked), rows_per_layer, used), flush=True)

    def work(p):
        try:
            rs = sample_rows(p["url"], rows_per_layer)
            return dict(p, rows=rs, err="")
        except Exception as e:                                # noqa: BLE001
            return dict(p, rows=[], err=str(e)[:120])

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        got = list(ex.map(work, picked))

    layers, cls_stat, pairs = [], {}, {"same": 0, "diff": 0, "examples": []}
    for g in got:
        if not g["rows"]:
            layers.append({"layer_id": g["layer_id"], "col": g["col"], "fam": g["fam"],
                           "sampled": 0, "err": g["err"]})
            continue
        vals = [r.get(g["col"]) for r in g["rows"]]
        cls = [city_class(v) for v in vals]
        stat = {}
        for c in cls:
            stat[c] = stat.get(c, 0) + 1
        clean = stat.get("clean", 0) / max(1, len(cls))
        for c, n in stat.items():
            cls_stat[c] = cls_stat.get(c, 0) + n
        # 同层另一族列的「同名率」：CITY 与 POSTAL/MAIL_CITY 是否一致
        other = [(c, fam(c)) for c in (g["rows"][0] or {}) if fam(c) and c != g["col"]]
        agree = None
        for oc, of in other:
            if of == "generic_city" and g["fam"] != "generic_city":
                pass
            n_same = n_tot = 0
            for r in g["rows"]:
                a, b = tok(r.get(g["col"])), tok(r.get(oc))
                if not a or not b:
                    continue
                n_tot += 1
                if a == b:
                    n_same += 1
                elif n_tot <= 3:
                    pairs["examples"].append({"layer": g["layer_id"], "col": g["col"],
                                              "other": oc, "a": r.get(g["col"]), "b": r.get(oc)})
            if n_tot >= 10:
                agree = {"other": oc, "other_fam": fam(oc), "rate": round(n_same / n_tot, 3),
                         "n": n_tot}
                pairs["same" if n_same / n_tot >= 0.5 else "diff"] += 1
                break
        layers.append({"layer_id": g["layer_id"], "col": g["col"], "fam": g["fam"],
                       "sampled": len(vals), "clean_rate": round(clean, 3), "classes": stat,
                       "agreement": agree, "err": ""})

    total = sum(sum(v["classes"].values()) for v in layers if v.get("classes"))
    rules = {
        "schema": "city-rules/v1",
        "at": utcnow(),
        "policy": ("postal_city 只收「邮件城市」语义列且值过形态校验；municipal_city 只收法定市政列；"
                   "任何不确定一律 null，且 *_source 同步写 null（SCHEMA 允许 null，宁可空不可错）"),
        "postal_city": {
            "accept_columns": POSTAL_COLS + [r"CITY", r"CITY_NAME", r"CITYNAME", r"PLACE_NAME",
                                            r"SITUS_CITY", r"ADDRESS_CITY", r"ADDR_CITY",
                                            r"POSTALCITY", r"POST_OFFICE_CITY", r"PO_CITY"],
            "reject_columns": OWNER_COLS + MUNI_COLS + COMMUNITY_COLS,
            "value_rules": ["不含数字（ZIP/门牌一律拒）", "不含逗号/分号（整串地址拒）",
                            "不在行政区黑话表（UNINCORPORATED/NONE/CDP 等）", "长度 ≤ 40",
                            "字母开头且仅 A-Z . ' - 空格"],
            "null_when": "值校验不过 or 层内抽样 clean_rate < 0.8 → postal_city=null, "
                         "postal_city_source=null",
            "source_enum": {"native": "nad_post_city", "derived": "place_derived", "null": None},
        },
        "municipal_city": {
            "accept_columns": MUNI_COLS,
            "reject_columns": OWNER_COLS + COMMUNITY_COLS + POSTAL_COLS,
            "value_rules": ["同 postal 的形态校验", "UNINCORPORATED/UNINC. → null（非法定市政）"],
            "source_enum": {"native": "nad_inc_muni", "derived": "tiger_place", "null": None},
        },
        "measured": {
            "rows": total,
            "layers": len([v for v in layers if v.get("sampled")]),
            "class_counts": cls_stat,
            "agreement": {"same_family": pairs["same"], "diff_family": pairs["diff"],
                          "examples": pairs["examples"][:10]},
        },
        "layers": layers,
    }
    json.dump(rules, open(os.path.join(SCHEMA_DIR, "city-rules-v1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return {"kind": "city", "rows": total, "layers": layers, "rules": rules}


# ---------------------------------------------------------------- 文档
def render(ev: dict) -> str:
    L = ["# 语义裁定审计 · addr_type 与 CITY（2026-10-30）", "",
         "> 只抽真行核对，不做启发式。两条裁定的依据与命中率都在这里，"
         "字段映射与 intake 一律按本文件的结论执行。", ""]
    a = ev.get("addr_type")
    if a:
        L += ["## 一、addr_type：v1 一律 `Unknown`，除非明确分类列可映射", "",
              "**禁止的启发式**（本轮明确否掉，永不实现）：", ""]
        L += ["- %s" % x for x in ["unit 非空 → Residential (Multi-Unit)",
                                   "层标题含 COMMERCIAL → Commercial",
                                   "parcel_situs 层 → Commercial",
                                   "addr_type 继承同州/同服务其它层"]]
        L += ["", "**抽样**：%d 层 × 25 行，覆盖明确分类列（AddrClass/ADDR_TYPE/UseCode/"
              "LANDUSE/BLDG_TYPE…）。" % a["sampled_layers"], "",
              "| 层 | 分类列 | 抽样 | 可映射 | 覆盖率 | 裁定 |", "|---|---|---|---|---|---|"]
        for r in a["layers"]:
            L.append("| `%s` | %s | %d | %d | %.0f%% | %s |"
                     % (r["layer_id"], r["col"], r["sampled"], r["mapped"],
                        100 * r["coverage"], r["verdict"]))
        L += ["", "**逐值映射表**（只有表内字面值会映射，其余一律 Unknown）：", "",
              "| 字面值 | → addr_type |", "|---|---|"]
        for k, v in sorted(a["value_map"].items()):
            L.append("| `%s` | %s |" % (k, v))
        L += ["", "→ 未抽样 / 覆盖率 < 80% / 列不在白名单的层：**addr_type = `Unknown`**（缺省不猜）。", ""]
    c = ev.get("city")
    if c:
        r = c["rules"]
        L += ["## 二、CITY：postal_city 与 municipal_city 的判定规则 + 命中率", "",
              "**抽样**：%d 层 / %d 行（generic CITY %d 层、postal 列 %d 层、municipal 列 %d 层、"
              "owner 列 %d 层、community 列 %d 层）。"
              % (r["measured"]["layers"], r["measured"]["rows"],
                 len([x for x in c["layers"] if x.get("fam") == "generic_city"]),
                 len([x for x in c["layers"] if x.get("fam") == "postal_named"]),
                 len([x for x in c["layers"] if x.get("fam") == "municipal_named"]),
                 len([x for x in c["layers"] if x.get("fam") == "owner_named"]),
                 len([x for x in c["layers"] if x.get("fam") == "community_named"])), "",
              "**值的形态命中率**（合计 %d 个样本值）：" % r["measured"]["rows"], "",
              "| 形态 | 计数 | 占比 | 结论 |", "|---|---|---|---|"]
        tot = max(1, r["measured"]["rows"])
        verdict = {"clean": "✅ 可作 postal_city", "has_digit": "❌ 含 ZIP/门牌 → null",
                   "has_punct": "❌ 整串地址 → null", "blacklist": "❌ 行政区黑话 → null",
                   "too_long": "❌ 过长 → null", "bad_chars": "❌ 非法字符 → null",
                   "empty": "— 空值"}
        for k, v in sorted(r["measured"]["class_counts"].items(), key=lambda kv: -kv[1]):
            L.append("| %s | %d | %.1f%% | %s |" % (k, v, 100.0 * v / tot, verdict.get(k, "")))
        L += ["", "**列族的同名率**（同层两列逐行比对，≥50% 视为同族）：", "",
              "| 层 | 主列 | 对比列 | 比对行 | 同名率 |", "|---|---|---|---|---|"]
        for x in c["layers"]:
            if x.get("agreement"):
                ag = x["agreement"]
                L.append("| `%s` | %s | %s | %d | %.0f%% |"
                         % (x["layer_id"], x["col"], ag["other"], ag["n"], 100 * ag["rate"]))
        L += ["", "**判定规则（落进 `schema/city-rules-v1.json`）**：", "",
              "- postal_city 收列白名单：`%s`" % ", ".join(r["postal_city"]["accept_columns"][:12]),
              "- postal_city 拒列：`%s`（业主邮寄城市 / 法定市政 / 社区名都不是邮件城市）"
              % ", ".join(r["postal_city"]["reject_columns"]),
              "- 值校验：%s" % "；".join(r["postal_city"]["value_rules"]),
              "- 不过校验 / 层内 clean_rate < 0.8 → **postal_city = null，postal_city_source = null**",
              "- municipal_city 只收 `%s`；`UNINCORPORATED` 一律 null"
              % ", ".join(r["municipal_city"]["accept_columns"]), ""]
        if r["measured"]["agreement"]["examples"]:
            L += ["**分歧实例（为什么不能混用）**：", ""]
            for e in r["measured"]["agreement"]["examples"]:
                L.append("- `%s`：%s=`%s` vs %s=`%s`"
                         % (e["layer"], e["col"], e["a"], e["other"], e["b"]))
            L += [""]
    L += ["## 三、复现", "", "```bash",
          "python3 analysis/semantic_audit.py both --rows 500 --layers 25", "```", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["addr_type", "city", "both"])
    ap.add_argument("--rows", type=int, default=500, help="city 总行数（addr_type 用 25/层）")
    ap.add_argument("--layers", type=int, default=25)
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    per = max(10, a.rows // max(1, a.layers))
    ev = {}
    if a.what in ("addr_type", "both"):
        ev["addr_type"] = audit_addr_type(rows_per_layer=25, max_layers=40, jobs=a.jobs)
    if a.what in ("city", "both"):
        ev["city"] = audit_city(rows_per_layer=per, max_layers=a.layers, jobs=a.jobs)

    path = os.path.join(HERE, "semantic-audit-2026-10-30.json")
    json.dump(ev, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = os.path.join(ROOT, "docs", "SEMANTIC-AUDIT-2026-10-30.md")
    os.makedirs(os.path.dirname(md), exist_ok=True)
    open(md, "w", encoding="utf-8").write(render(ev))
    print("写入 %s\n写入 %s\n写入 schema/addr-type-map-v1.json / schema/city-rules-v1.json" % (path, md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
