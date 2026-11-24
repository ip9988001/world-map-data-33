#!/usr/bin/env python3
"""第 4 步：核心特征方言分组（确定性，可一键复跑）。

输入（只读，全部来自 origin/main 的 `analysis/full-inventory-20261124/`）：
  inventory-remote-uncollected.csv   54,812 层（18 列）
  inventory-local-all.csv            2,364 目录（readable=1 → 1,158 层）
  inventory-local-fields.csv         36,750 字段级行（canonical 字段 + 真实样值）
  probe-fields.ndjson                §五 有界探针（328 请求，真实上游字段名 + CRS + geometryType）
输出（本目录）：
  dialect-assignment.csv  dialect-coverage.csv  manual-queue.csv  dialect.json

分组宇宙（分母写死，不靠 wc -l）：
  D1 远程有地址语义层 = usable ∈ {full_address, no_zip, no_city, road_only} = 16,010
  D2 本地可读层      = readable=1 = 1,158
  D3 观察集          = 远程 empty_shell 25,447（只做 provider 聚类，不做方言判定）
  ⇒ 方言判定分母 = D1 + D2 = 17,168
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124")
OUT = os.path.dirname(os.path.abspath(__file__))

D1_USABLE = ("full_address", "no_zip", "no_city", "road_only")
SHARE_ACTIVE = 0.02
SHARE_MIN = 0.01
WEEKLY_CAP_LAYERS = 200

# ---------------------------------------------------------------- 别名族（按族聚，不按单字段聚）
# 每条规则 = (族, 正则)。正则作用在 norm(field) 上（小写 + 去非字母数字）。
NUM_NEG = re.compile(r"parcel|route|^rt|hwy|phone|bldgarea|bike|juris|district|tract|^lot|block|"
                     r"gpid|objectid|fid|globalid|case|permit|book|page|sheet|area|sqft|mile|"
                     r"range_?(?:low|high)?$|percent|year|capacity|lane|unit_?num")
FAMILIES = [
    ("number", re.compile(r"^(?:l|r)?h(?:ouse)?n(?:um|o|umber)?$|house_?number|hse_?num|add(?:r(?:ess)?)?_?num|"
                          r"addr_?no|st(?:reet)?_?num|site_?addr(?:ess)?_?(?:num)?|bldg_?no|"
                          r"^num$|^number$|^hn$|^no$|^streetno$|^pre_?addr|^addrnum|full_?addr_?num|situs_?num")),
    ("street", re.compile(r"street_?name|^street$|^st$|st_?name|^stname|lst_?name|rd_?name|road_?name|"
                          r"full_?street|street_?full|street_?norm|^road$|^thoroughfare|"
                          r"st_?pre_?dir|st_?post_?dir|st_?type|street_?suffix|street_?prefix|"
                          r"street|situs_?street")),
    ("unit", re.compile(r"^unit|unit_?num|apt|apartment|suite|^ste$|^sub_?addr|^bldg_?unit|^unitid")),
    ("place", re.compile(r"city|town|municipal|postal_?city|place|msag|community|locality|village|"
                         r"borough|postal_?comm")),
    ("state", re.compile(r"^state$|^st_?abbr|state_?abbr|^statecode|^state_?code|^st$")),
    ("zip", re.compile(r"zip|postal_?code|post_?code|postcode|^zip5|^zip_?code|^postal$")),
    ("coord", re.compile(r"^lat|^lon|^x$|^y$|latitude|longitude|geom|shape_?(?:x|y)|point_?x|point_?y")),
]
NUM_NEG_FIELD = re.compile(r"parcel|route|hwy|phone|area|bike|juris|district|tract|lot|block|"
                           r"gpid|objectid|fid|globalid|permit|book|page|sheet|sqft|mile|"
                           r"percent|year|capacity|lane|unit")


def norm(field: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (field or "").lower())


def family_of(field: str) -> str:
    n = norm(field)
    if not n:
        return ""
    if NUM_NEG_FIELD.search(n):
        return ""
    for fam, rx in FAMILIES:
        if rx.search(n):
            return fam
    return ""


def field_families(fields):
    """[(fam, alias)]，保持字段原顺序。"""
    out = []
    for f in fields or []:
        fam = family_of(f)
        if fam:
            out.append((fam, f))
    return out


def template_of(fields):
    """族签名：6 位（number/street/unit/place/state/zip）+ 每族命中的首个别名。"""
    fams = field_families(fields)
    hit = {}
    for fam, alias in fams:
        hit.setdefault(fam, alias)
    bits = "".join("1" if k in hit else "0" for k in ("number", "street", "unit", "place", "state", "zip"))
    return bits, hit


# ---------------------------------------------------------------- provider / geometry
def prov_key(url):
    m = re.match(r"https?://services\d*\.arcgis\.com/([^/]+)", url or "")
    if m:
        return f"agol:{m.group(1)}", "agol"
    m = re.match(r"https?://([^/]+)/arcgis/rest", url or "")
    if m:
        h = m.group(1).lower()
        return f"host:{h}", "host"
    m = re.match(r"https?://([^/]+)", url or "")
    if m:
        h = m.group(1).lower()
        if "socrata" in h or h.endswith(".gov") or h.endswith(".org") or h.endswith(".us"):
            return f"socrata:{h}", "socrata"
        return f"dom:{h}", "dom"
    return "none", "none"


GRAN_RULES = [
    ("apartment_unit_point", re.compile(r"unit|apt|suite|apartment|condo", re.I)),
    ("range_interpolation", re.compile(r"range|interpolat|\bhnr\b|mile_?mark", re.I)),
    ("parcel_centroid", re.compile(r"parcel|situs|taxlot|tax_lot|assessor", re.I)),
    ("centerline_midpoint", re.compile(r"centerline|centreline|street_?center|road_?center|rcl|"
                                       r"street_?name_?only|roadway", re.I)),
    ("building_point", re.compile(r"address_?point|addr_?point|addresses|address_?units?|"
                                  r"911|e911|ng911|point_?address", re.I)),
]


def granularity(geom: str, title: str, svc: str) -> str:
    text = f"{title or ''} {svc or ''}"
    for name, rx in GRAN_RULES:
        if rx.search(text):
            return name
    g = (geom or "").lower()
    if g == "point":
        return "unknown"          # 有点位几何但语义不明 —— 不按 4326/点 硬猜
    return "unknown"


SAMPLE_OK = {
    "housenumber": re.compile(r"^\d{1,6}[A-Za-z]?(?:-\d{1,6})?$"),
    "street": re.compile(r"[A-Za-z]{3,}"),
    "unit": re.compile(r"\S"),
    "city": re.compile(r"[A-Za-z]{2,}"),
    "state": re.compile(r"^[A-Z]{2}$"),
    "zip": re.compile(r"^\d{5}(?:-\d{4})?$"),
}


def pick_sample(role, samples):
    """从真实样值里挑第一个「形态可信」的值；挑不到返回 None（不许拿脏值凑）。"""
    rx = SAMPLE_OK.get(role)
    for s in samples or []:
        v = (s or "").strip()
        if not v:
            continue
        if rx is None or rx.search(v):
            return v
    return None


def load_probe():
    """provider → {fields, sr_epsg, crs_basis, geometryType, url, http}"""
    p = os.path.join(OUT, "probe-fields.ndjson")
    out = {}
    if not os.path.exists(p):
        return out
    for line in open(p, encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        sr = r.get("sr") or {}
        epsg = sr.get("latestWkid") or sr.get("wkid")
        basis = "declared" if epsg else ("declared_wkt" if sr.get("wkt") else "unknown")
        out[r["provider"]] = {"fields": r.get("fields") or [], "epsg": epsg, "crs_basis": basis,
                              "geometryType": r.get("geometryType") or "", "url": r["url"],
                              "http": r.get("http"), "name": r.get("name") or ""}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly-cap", type=int, default=WEEKLY_CAP_LAYERS)
    a = ap.parse_args()

    probe = load_probe()
    rem = list(csv.DictReader(open(os.path.join(INV, "inventory-remote-uncollected.csv"), encoding="utf-8")))
    loc = list(csv.DictReader(open(os.path.join(INV, "inventory-local-all.csv"), encoding="utf-8")))
    local_fields = defaultdict(lambda: defaultdict(list))   # layer_dir → field → [samples]
    layer_of_dir = {}
    for r in csv.DictReader(open(os.path.join(INV, "inventory-local-fields.csv"), encoding="utf-8")):
        samples = [s.strip() for s in (r["samples"] or "").split("|") if s.strip()]
        local_fields[r["layer_dir"]][r["field"]] = {"samples": samples, "nonnull": r["nonnull"],
                                                   "denom": r["denom"], "table": r["table"]}
        layer_of_dir[r["layer_dir"]] = r["layer"]

    layers = []
    for r in rem:
        if r["usable"] in D1_USABLE:
            layers.append({"universe": "d1", "url": r["url"], "usable": r["usable"], "svc": r["svc"],
                           "geom": r["geom"], "title": r["title"], "state": r["state"],
                           "count": r["count"], "src": "inventory-remote-uncollected.csv"})
    for r in loc:
        if r.get("readable") == "1":
            layers.append({"universe": "d2", "url": r["url"], "usable": r["usable"], "svc": r["src_kind"] or "",
                           "geom": r["geom"], "title": r["layer"], "state": r["state"],
                           "count": r["rows"], "src": "inventory-local-all.csv",
                           "layer_dir": r["layer_dir"], "layer": r["layer"]})
    D3 = [r for r in rem if r["usable"] == "empty_shell"]

    # ---- 每层：provider / 模板（远程用自证 fields_number_like，其次借同 provider 探针；本地借同 provider 探针）
    for L in layers:
        pkey, pkind = prov_key(L["url"])
        L["provider_id"], L["provider_kind"] = pkey, pkind
        pr = probe.get(pkey)
        L["probed"] = bool(pr)
        if pr:
            L["template_bits"], L["fam_alias"] = template_of(pr["fields"])
            L["epsg"], L["crs_basis"] = pr["epsg"], pr["crs_basis"]
            L["geometryType"] = pr["geometryType"]
            L["template_evidence"] = "probe:" + pr["url"]
        else:
            # 远程自带 fields_number_like（只覆盖 number 一族）；族签名其余位未知 → 保持 unresolved
            own = [f.strip() for f in (L.get("number_aliases_own") or [])]
            L["template_bits"], L["fam_alias"] = "000000", {}
            L["epsg"], L["crs_basis"] = None, "unknown"
            L["geometryType"] = ""
            L["template_evidence"] = "unavailable"
        L["granularity"] = granularity(L["geometryType"] or L["geom"], L["title"], L["svc"])

    # 远程层若 provider 无探针，但自身 fields_number_like 给了门牌别名 → 记录证据（仍不进注册表）
    for r in rem:
        pass

    # ---- 细组 → 方言（kind + 族签名 + 粒度）
    for L in layers:
        L["group_key"] = (L["provider_kind"], L["template_bits"], L["granularity"])
    rows_total = Counter()
    rows_unavail = Counter()
    for L in layers:
        try:
            c = int(L["count"])
        except (TypeError, ValueError):
            rows_unavail[L["group_key"]] += 1
            L["coverage_rows"] = None
            continue
        L["coverage_rows"] = c
        rows_total[L["group_key"]] += c
    denom_rows = sum(rows_total.values())
    for L in layers:
        L["share"] = (rows_total[L["group_key"]] / denom_rows) if denom_rows else 0.0

    # ---- 哪些组能进注册表：必须有 ≥3 条「真实样值可造 golden case」的本地层
    #      （口径：该层 house_number 与 street_name 都至少有 1 个非空样值 —— minimal_safe 也要这两要素）
    CANON_NUM = ("house_number", "_house_num")
    CANON_ST = ("street_name", "street_full")

    def gc_ready(layer_dir):
        f = local_fields.get(layer_dir) or {}
        num = next((pick_sample("housenumber", f[k]["samples"]) for k in CANON_NUM
                    if f.get(k) and f[k]["samples"]), None)
        st = next((pick_sample("street", f[k]["samples"]) for k in CANON_ST
                   if f.get(k) and f[k]["samples"]), None)
        return bool(num and st)

    sample_layers = defaultdict(int)
    gc_ready_dirs = {d for d in local_fields if gc_ready(d)}
    for L in layers:
        if L["universe"] == "d2" and L["layer_dir"] in gc_ready_dirs:
            sample_layers[L["group_key"]] += 1

    # 进注册表还要求「该组能写出别名」：provider 探针里必须同时认出 number 与 street 两族
    group_aliases = defaultdict(lambda: defaultdict(set))
    for L in layers:
        pr = probe.get(L["provider_id"])
        if not pr:
            continue
        for fam, lst in field_families(pr["fields"]):
            group_aliases[L["group_key"]][fam].add(lst)
    registry_keys = {k for k, n in sample_layers.items()
                     if n >= 3 and group_aliases[k].get("number") and group_aliases[k].get("street")}
    # 两遍收敛：gen_registry 已确认「能出 ≥3 条真实 golden case」的组才留在注册表里
    _approved = os.path.join(OUT, "registry-approved.json")
    if os.path.exists(_approved):
        ok_groups = {tuple(g) for g in json.load(open(_approved, encoding="utf-8"))["groups"]}
        registry_keys &= ok_groups
    aliasless_keys = {k for k, n in sample_layers.items() if n >= 3 and k not in registry_keys}
    longtail_keys = {k for k in rows_total if k not in registry_keys}

    def slug(kind, bits, gran):
        return f"{kind}-t{bits}-{gran.replace('_', '')}"

    # 注册方言 id（确定性排序：先 rows 降序，再 key）
    ordered = sorted(registry_keys, key=lambda k: (-rows_total[k], k))
    used = set()
    dialect_id = {}
    for k in ordered:
        base = slug(*k)
        did, i = base, 2
        while did in used:
            did, i = f"{base}-{i}", i + 1
        used.add(did)
        dialect_id[k] = did

    # 长尾合并：同 kind+签名（不看粒度）→ longtail:<kind>-t<bits>
    lt_map = {}
    for k in sorted(longtail_keys):
        lt = f"longtail:{k[0]}-t{k[1]}"
        lt_map[k] = lt
    lt_stats = defaultdict(lambda: {"layers_n": 0, "rows": 0, "providers": Counter()})

    assign = []
    for L in layers:
        k = L["group_key"]
        if k in dialect_id:
            did = dialect_id[k]
            if L["share"] >= SHARE_ACTIVE:            # ≥2% → 注册表正式规则
                st, reason = "active", ""
            elif L["share"] >= SHARE_MIN:             # 1%~2% → 最小安全 + 人工队列头部
                st, reason = "minimal_safe", ""
            else:                                     # <1% → 最小安全
                st, reason = "minimal_safe", "share_below_1pct"
        elif k in aliasless_keys:
            did, st, reason = "minimal_safe", "manual", "template_unresolved"
        elif k in lt_map:
            did, st = lt_map[k], "minimal_safe"
            reason = "share_below_1pct" if L["share"] < SHARE_MIN else "no_golden_evidence"
        else:
            did, st, reason = "minimal_safe", "manual", "template_unresolved"
        # 覆盖硬约束：粒度/模板不可判 → 一律 manual + 对应 reason
        if L["template_bits"] == "000000":
            did, st, reason = "minimal_safe", "manual", "template_unresolved"
        elif L["granularity"] == "unknown" and did != "minimal_safe":
            st, reason = "manual", "geom_unsupported"
        L.update({"dialect_id": did, "status": st, "reason": reason})
        if did.startswith("longtail:"):
            s = lt_stats[did]
            s["layers_n"] += 1
            s["rows"] += L["coverage_rows"] or 0
            s["providers"][L["provider_id"]] += 1
        assign.append(L)

    # ---- 覆盖表
    cov = defaultdict(lambda: {"layers_n": 0, "rows": 0, "states": Counter(), "svc": Counter(),
                               "geom": Counter(), "gran": Counter(), "epsg": Counter(),
                               "basis": Counter(), "usable": Counter(), "status": Counter(),
                               "unavail": 0, "providers": Counter()})
    for L in assign:
        c = cov[L["dialect_id"]]
        c["layers_n"] += 1
        c["rows"] += L["coverage_rows"] or 0
        if L["coverage_rows"] is None:
            c["unavail"] += 1
        c["states"][L["state"] or "-"] += 1
        c["svc"][L["svc"] or "-"] += 1
        c["geom"][L["geom"] or L["geometryType"] or "-"] += 1
        c["gran"][L["granularity"]] += 1
        c["epsg"][str(L["epsg"] or "unknown")] += 1
        c["basis"][L["crs_basis"]] += 1
        c["usable"][L["usable"]] += 1
        c["status"][L["status"]] += 1
        c["providers"][L["provider_id"]] += 1

    # ---- 落盘：assignment
    cols = ["layer_id", "url", "universe", "dialect_id", "provider_id", "provider_kind", "template_id",
            "granularity", "status", "share", "coverage_rows", "reason", "evidence", "usable", "state"]
    with open(os.path.join(OUT, "dialect-assignment.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for L in sorted(assign, key=lambda x: (x["dialect_id"], x["url"] or x.get("layer", ""))):
            w.writerow({
                "layer_id": L.get("layer") or L["url"].rstrip("/").rsplit("/", 2)[-2] + "/" + L["url"].rstrip("/").rsplit("/", 1)[-1],
                "url": L["url"], "universe": L["universe"], "dialect_id": L["dialect_id"],
                "provider_id": L["provider_id"], "provider_kind": L["provider_kind"],
                "template_id": f"t{L['template_bits']}", "granularity": L["granularity"],
                "status": L["status"], "share": f"{L['share']:.6f}",
                "coverage_rows": "" if L["coverage_rows"] is None else L["coverage_rows"],
                "reason": L["reason"],
                "evidence": (L["template_evidence"] + ("|samples:inventory-local-fields.csv"
                                                       if L["universe"] == "d2" else "")),
                "usable": L["usable"], "state": L["state"]})

    # ---- 落盘：coverage
    with open(os.path.join(OUT, "dialect-coverage.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["dialect_id", "layers_n", "rows", "share", "state_top3", "svc", "geom_types",
                    "point_granularity", "crs_epsg", "crs_basis", "anomaly_rate", "status",
                    "count_unavailable_layers"])
        for did, c in sorted(cov.items(), key=lambda kv: (-kv[1]["rows"], kv[0])):
            bad = c["usable"].get("road_only", 0)
            anom = bad / c["layers_n"] if c["layers_n"] else 0.0
            w.writerow([did, c["layers_n"], c["rows"], f"{c['rows']/denom_rows:.6f}",
                        "|".join(f"{k}:{v}" for k, v in c["states"].most_common(3)),
                        "|".join(f"{k}:{v}" for k, v in c["svc"].most_common()),
                        "|".join(f"{k}:{v}" for k, v in c["geom"].most_common()),
                        "|".join(f"{k}:{v}" for k, v in c["gran"].most_common()),
                        "|".join(f"{k}:{v}" for k, v in c["epsg"].most_common()),
                        "|".join(f"{k}:{v}" for k, v in c["basis"].most_common()),
                        f"{anom:.4f}",
                        "|".join(f"{k}:{v}" for k, v in c["status"].most_common()),
                        c["unavail"]])

    # ---- 落盘：manual queue（score = coverage_rows × anomaly_rate，按周切片，周上限来自参数）
    q = []
    for did, c in cov.items():
        if not (did.startswith("longtail:") or did == "minimal_safe" or
                any(s != "active" for s in c["status"])):
            continue
        rows = c["rows"]
        anom = c["usable"].get("road_only", 0) / c["layers_n"] if c["layers_n"] else 0.0
        reasons = Counter()
        for L in assign:
            if L["dialect_id"] == did and L["reason"]:
                reasons[L["reason"]] += 1
        q.append({"dialect_id": did, "layers_n": c["layers_n"], "coverage_rows": rows,
                  "anomaly_rate": round(anom, 4), "score": round(rows * anom, 1),
                  "reason": "|".join(f"{k}:{v}" for k, v in reasons.most_common()) or "-"})
    q.sort(key=lambda x: (-x["score"], x["dialect_id"]))
    # 按周切片：一个组可以跨多周（不能因为组大就硬塞进一周），下一组从「下一周」开始
    week = 1
    for i, r in enumerate(q, 1):
        span = max(1, -(-r["layers_n"] // a.weekly_cap))     # ceil(layers/cap)
        r["rank"] = i
        r["week"], r["week_end"], r["weeks_spanned"] = week, week + span - 1, span
        week += span
    with open(os.path.join(OUT, "manual-queue.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank", "dialect_id", "layers_n", "coverage_rows",
                                           "anomaly_rate", "score", "reason", "week",
                                           "week_end", "weeks_spanned"])
        w.writeheader()
        w.writerows(q)

    # ---- 落盘：dialect.json
    reg = []
    for k in ordered:
        did = dialect_id[k]
        c = cov[did]
        reg.append({"dialect_id": did, "provider_kind": k[0], "template_bits": k[1],
                    "granularity": k[2], "layers_n": c["layers_n"], "rows": c["rows"],
                    "share": round(c["rows"] / denom_rows, 6),
                    "status": "active" if c["rows"] / denom_rows >= SHARE_ACTIVE else "minimal_safe",
                    "sample_layers": sample_layers[k],
                    "crs_epsg_top": [[e, n] for e, n in c["epsg"].most_common(3)],
                    "crs_basis": [[b, n] for b, n in c["basis"].most_common(2)],
                    "providers": [[p, n] for p, n in c["providers"].most_common()]})
    summary = {
        "schema": "dialects.v1/2026-11-24",
        "denominator": {"d1_remote": sum(1 for L in assign if L["universe"] == "d1"),
                        "d2_local": sum(1 for L in assign if L["universe"] == "d2"),
                        "total": len(assign),
                        "d3_observation": len(D3),
                        "expected_d1": 16010, "expected_d2": 1158, "expected_total": 17168},
        "rows_denominator": denom_rows,
        "count_unavailable_layers": sum(1 for L in assign if L["coverage_rows"] is None),
        "dialects_registered": len(reg),
        "longtail_groups": len(lt_stats),
        "status_counts": dict(Counter(L["status"] for L in assign)),
        "reason_counts": dict(Counter(L["reason"] or "-" for L in assign)),
        "dialect_rows": reg,
        "longtail": [{"group": g, "layers_n": s["layers_n"], "rows": s["rows"],
                      "providers": [[p, n] for p, n in s["providers"].most_common()]}
                     for g, s in sorted(lt_stats.items(), key=lambda kv: -kv[1]["rows"])],
        "weekly_cap_layers": a.weekly_cap,
        "probe": {"requests_n": len(probe), "source": "probe-fields.ndjson"},
        "closure": {"assignment_rows": len(assign),
                    "sum_layers": sum(c["layers_n"] for c in cov.values()),
                    "sum_rows": sum(c["rows"] for c in cov.values())},
    }
    json.dump(summary, open(os.path.join(OUT, "dialect.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(json.dumps({k: summary[k] for k in ("denominator", "rows_denominator",
                                              "count_unavailable_layers", "dialects_registered",
                                              "longtail_groups", "status_counts", "reason_counts",
                                              "closure")}, ensure_ascii=False, indent=1))
    assert len(assign) == 17168, f"分母不闭合: {len(assign)}"
    assert sum(c["layers_n"] for c in cov.values()) == len(assign)
    return 0


if __name__ == "__main__":
    sys.exit(main())
