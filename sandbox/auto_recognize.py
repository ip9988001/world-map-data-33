"""自动认（沙盒）：8 条否定证据 + 三档 + 三路分流（active / minimal_safe / unavailable）。
判据全是「字段有没有值 / 几何对不对得上」；全文件不存在任何 confidence 阈值门控。
"""
import argparse, collections, csv, json, os, re, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAL = os.path.join(ROOT, "analysis", "dialect-20261124")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124")
PATTERNS = os.path.join(ROOT, "analysis", "combo-step1-20261125", "patterns.csv")
THRESHOLDS = os.path.join(ROOT, "sandbox", "spatial_thresholds.yaml")
EKEYS, FATAL = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"), ("E1", "E2", "E3", "E8")
EXCLUDED_TAG = "excluded_from_verifiable_denominator"
EXCLUDED_NOTE = "数据性质如此，不是缺陷"      # 归因文案原话（muse 定稿），不许改写成缺陷/失败/不达标
GRAN_REQ = {"building_point": {"point"}, "apartment_unit_point": {"point"}, "parcel_centroid": {"polygon"}, "range_interpolation": {"point", "polyline"}, "centerline_midpoint": {"polyline"}}
NUM_NEG = re.compile(r"parcel|route|hwy|phone|area|bike|juris|district|tract|lot|block|gpid|objectid|fid|globalid|permit|book|page|sheet|sqft|mile|percent|year|capacity|lane|unit")
PLACEHOLDER = {"TBD", "UNKNOWN", "NULL", "N/A", "NA", "NONE", "-"}
MOVE_COLS = ("layer_id", "url", "provider", "granularity", "geom_type", "rows_n", "verdict", "reason_evidence", "reason_detail")
norm = lambda f: re.sub(r"[^a-z0-9]", "", (f or "").lower())


def load_ctx(outdir):
    """一次性只读装载：第 3 步字段事实 ⋈ 探针字段集 ⋈ registry 别名表 ⋈ 空间结论。"""
    inv = {}
    for n in ("inventory-remote-uncollected.csv", "inventory-local-all.csv"):
        for r in csv.DictReader(open(os.path.join(INV, n), encoding="utf-8")):
            inv.setdefault(r["url"], {}).update({
                "bits": r.get("addr_core_hit", ""), "geom": r.get("geom", ""), "sampled_n": r.get("sampled_n", "0"),
                "n_fields": r.get("n_fields") or r.get("fields_n", ""), "nlike": r.get("fields_number_like", ""),
                "count": r.get("count") or r.get("rows", "")})
    probe = {d["url"]: d.get("fields") or [] for d in
             (json.loads(l) for l in open(os.path.join(DIAL, "probe-fields.ndjson"), encoding="utf-8"))}
    roles, ph = collections.defaultdict(set), collections.defaultdict(set)
    for d in yaml.safe_load(open(os.path.join(ROOT, "registry", "dialects.v1.yaml"), encoding="utf-8"))["dialects"]:
        for role in ("number", "street", "unit", "place", "state", "zip"):
            for a in (d.get("template") or {}).get(role + "_aliases") or []:
                roles[a].add(role)
    for r in csv.DictReader(open(os.path.join(INV, "inventory-local-fields.csv"), encoding="utf-8")):
        if r["field"] in ("street_name", "street_full", "house_number", "postal_city") and any(
                t.strip().upper() in PLACEHOLDER for t in re.split(r"[|,]", r.get("samples") or "")):
            ph[r["url"]].add(r["field"])
    sf = os.path.join(outdir, "spatial-findings.csv")
    spatial = {r["key"]: r for r in csv.DictReader(open(sf, encoding="utf-8")) if r["kind"] == "fixture_layer"} if os.path.isfile(sf) else {}
    ce = os.path.join(outdir, "coord-evidence.csv")
    coord = {r["url"]: r for r in csv.DictReader(open(ce, encoding="utf-8"))} if os.path.isfile(ce) else {}
    return {"inv": inv, "probe": probe, "roles": roles, "ph": ph, "spatial": spatial, "coord": coord,
            "excluded_meta": load_exclusions()}


def load_exclusions(thresholds=THRESHOLDS, patterns=PATTERNS):
    """可验分母剔除口径（只改分母，不动数据）。

    口径（哪几类被剔除、各类应为多少层）**只从 `sandbox/spatial_thresholds.yaml:
    e7.denominator_excluded` 读**，代码里不出现任何魔法数；逐层归属从组合拳① 的
    `patterns.csv` 读（pattern_id 即类别）。两处数量对不上就直接报错，不静默放过。
    """
    doc = (yaml.safe_load(open(thresholds, encoding="utf-8")) or {}).get("e7", {}).get("denominator_excluded") or {}
    classes = {k: int(v["value"]) for k, v in doc.items() if isinstance(v, dict) and "value" in v and k != "total"}
    by_url, by_class = {}, collections.defaultdict(list)
    for r in csv.DictReader(open(patterns, encoding="utf-8")):
        pid = r["pattern_id"]
        if pid in classes:
            by_url[r["url"]] = {"class": pid, "pattern": r.get("pattern", ""), "fields": r.get("fields", ""),
                                 "rows_n": int(float(r.get("rows_n") or 0)),
                                 "why": (doc[pid] or {}).get("why", "")}
            by_class[pid].append(r["url"])
    for c, want in classes.items():
        got = len(by_class[c])
        if got != want:
            raise SystemExit(f"denominator_excluded 口径不符: {c} yaml={want} patterns.csv={got}")
    total = int((doc.get("total") or {}).get("value") or sum(classes.values()))
    if sum(classes.values()) != total:
        raise SystemExit(f"denominator_excluded total 不符: {total} != {sum(classes.values())}")
    return {"classes": classes, "total": total, "by_url": by_url,
            "by_class": {k: v for k, v in by_class.items()}, "doc": doc}


def ev1(L, C):  # 门牌：addr_core_hit[0] = 20 行样值里门牌族含数字是否过半
    if not L["bits"]:
        return "unknown", "addr_core_hit 空（无样值/不可读层）"
    return ("hit", f"addr_core_hit[0]=0；门牌族候选={L['nlike'] or '-'}") if L["bits"][0] == "0" else ("clear", "")
def ev2(L, C):  # 街名：addr_core_hit[1] + 本地样值占位字面值
    if not L["bits"]:
        return "unknown", "addr_core_hit 空"
    if L["bits"][1] == "0":
        return "hit", "addr_core_hit[1]=0（街名族样值半数以上为空）"
    return ("hit", "样值含占位字面值 " + ",".join(sorted(C["ph"][L["url"]]))) if C["ph"].get(L["url"]) else ("clear", "")
def ev3(L, C):  # 几何语义：granularity ⇄ geom 类型（geom 缺失时用坐标样本实测 geom_type 兜底）
    g, gran = (L["geom"] or "").lower() or C["coord"].get(L["url"], {}).get("geom_type", ""), (L["granularity"] or "unknown")
    if not g or gran == "unknown":
        return "unknown", f"geom={L['geom'] or '缺'} / granularity={gran}（点位语义不可判）"
    return ("clear", "") if g in (GRAN_REQ.get(gran) or set()) else ("hit", f"{gran} 与 geom={g} 冲突")
def ev4(L, C):  # 别名冲突：门牌证据落在负向字段族（parcel/route/phone…）或同名字段跨方言映射到不同要素
    sf = [f for f in (C["coord"].get(L["url"], {}).get("sample_fields") or "").split("|") if f]
    fields, bad = C["probe"].get(L["url"]) or sf or None, set()
    bad |= {f for f in (L["nlike"] or "").split(",") if f and NUM_NEG.search(norm(f))}
    bad |= {f for f in (fields or []) if len(C["roles"].get(f) or ()) > 1}
    if bad:
        return "hit", "门牌族被负向规则命中/跨要素同名字段: " + ",".join(sorted(bad)[:6])
    return ("unknown", "无同源探针字段集、也无坐标样本字段（探针配额 1,000/1,000 已用满）") if fields is None \
        else ("clear", f"{'样本' if C['probe'].get(L['url']) is None else '探针'} {len(fields)} 字段无冲突")
def ev5(L, C):  # 样本份额：抽样为空 / 抽样被截断 / 层份额过低
    n, cnt, share = int(L["sampled_n"] or 0), int(float(L["count"] or 0)), float(L["share"] or 0)
    if n == 0:
        return "hit", "抽样为空（sampled_n=0）"
    if cnt and n < min(20, cnt):
        return "hit", f"抽样被截断 n={n} < min(20,count={cnt})"
    return ("hit", f"层份额 {share} < 0.01%") if share < 1e-4 else ("clear", f"n={n} count={cnt}")
def ev6(L, C):  # 空间验算：只认坐标样本实测结论（coord-evidence.csv；按 url 找，layer_id 不唯一）
    c = C["coord"].get(L["url"], {})
    return (c["e6"], c["e6_detail"]) if c else ("unknown", "该 url 无坐标样本 → 空间验算未跑")
def ev7(L, C):  # 源间同址投票：同址跨源坐标 >300m 记冲突，可比行 <3 记 unknown（投不出票不冒充 clear）
    c = C["coord"].get(L["url"], {})
    return (c["e7"], c["e7_detail"]) if c else ("unknown", "该 url 无坐标样本 → 无源间同址投票")
def ev8(L, C):  # 结构漂移：字段集/类型 ⇄ 注册表模板
    fields, tpl = C["probe"].get(L["url"]), (L["template_id"] or "")
    if tpl in ("", "t000000"):
        return "na", "该层无注册表模板（t000000）→ 无『与模板不一致』可言"
    if fields is None:
        return "unknown", f"模板 {tpl} 存在但无探针字段集，无法比对"
    return ("hit", "n_fields=0 但模板要求字段集") if L["n_fields"] in ("", "0") else ("clear", f"{tpl} 可对齐")

EVIDENCES = (ev1, ev2, ev3, ev4, ev5, ev6, ev7, ev8)


def tier_of(st):
    """①②③⑧ 任一 hit/unknown、或 ⑥ hit → Tier3；8 条全 clear/na → Tier1；其余 → Tier2。"""
    if any(st[k] in ("hit", "unknown") for k in FATAL) or st["E6"] == "hit":
        return "tier3"
    return "tier1" if all(v in ("clear", "na") for v in st.values()) else "tier2"


def move_of(t, st, L):
    """三路分流：active（Tier1）/ minimal_safe / unavailable，**没有 manual 这一档**。

    不变式：minimal_safe 只取「门牌号 + 街名」两要素、其余要素留空，要求 addr_core_hit[:2]=="11"；
    缺任一要素 → unavailable（连最小安全解析都取不到）。minimal_safe 永不进 A 货池
    （a_pool_eligible=false，由 registry/evaluator.py 硬编码，不由本模块决定）。
    """
    if t == "tier1":
        return "active", ""
    block = [k for k in FATAL if st[k] in ("hit", "unknown")] + \
            [k for k in ("E5", "E6", "E7") if st[k] != "clear"]
    return ("minimal_safe" if (L["bits"] or "")[:2] == "11" else "unavailable"), ",".join(block)


def evaluate(L, C):
    L = {**L, **C["inv"].get(L["url"], {})}
    ev = {k: f(L, C) for k, f in zip(EKEYS, EVIDENCES)}
    st = {k: v[0] for k, v in ev.items()}
    t = tier_of(st)
    mv, why = move_of(t, st, L)
    det = "; ".join(f"{k}={ev[k][1]}" for k in why.split(",") if k and ev.get(k, ("", ""))[1])
    row = {"layer_id": L["layer_id"], "url": L["url"], "universe": L["universe"], "dialect_id": L["dialect_id"],
           "provider_id": L["provider_id"], "provider": L["provider_id"], "state": L["state"],
           "granularity": L["granularity"], "geom": L["geom"],
           "geom_type": C["coord"].get(L["url"], {}).get("geom_type") or (L["geom"] or "").lower(),
           "usable": L["usable"], "share": L["share"],
           "assign_reason": L["reason"], "coverage_rows": L["coverage_rows"], "rows_n": L["coverage_rows"],
           "tier": t, "move": mv, "verdict": mv, "reason_evidence": why, "reason_detail": det,
           **{f"{k}_state": st[k] for k in EKEYS}, **{f"{k}_detail": ev[k][1] for k in EKEYS if ev[k][1]}}
    ex = (C.get("excluded_meta") or {}).get("by_url", {}).get(L["url"])   # 单测可只造最小 ctx
    if ex:
        # 只加标记与归因文案，**不改 tier、不改判据**：分母口径与分档是两件事
        row["denominator_excluded"] = ex["class"]
        row["reason_evidence"] = ",".join(x for x in (row["reason_evidence"], f"{EXCLUDED_TAG}: {ex['class']}") if x)
        row["reason_detail"] = "; ".join(x for x in (
            row["reason_detail"],
            f"{EXCLUDED_TAG}: {ex['class']}（{ex['pattern']}），字段 {ex['fields'] or '无地址字段'}，"
            f"{ex['why']} → {EXCLUDED_NOTE}") if x)
    else:
        row["denominator_excluded"] = ""
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(ROOT, "analysis", "auto-spatial-20261124"))
    args = ap.parse_args()
    C, outdir = load_ctx(args.outdir), args.outdir
    rows = [evaluate(L, C) for L in csv.DictReader(
        open(os.path.join(DIAL, "dialect-assignment.csv"), encoding="utf-8"))]
    cols = list(dict.fromkeys(k for r in rows for k in r))
    tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]
    mv = [{k: r[k] for k in MOVE_COLS} for r in tu]
    os.makedirs(outdir, exist_ok=True)
    for name, rs, flds in (("auto-recognized.csv", rows, cols), ("template-unresolved-moves.csv", mv, MOVE_COLS),
                           ("template-unresolved-unavailable.csv", [r for r in mv if r["verdict"] == "unavailable"], MOVE_COLS)):
        with open(os.path.join(outdir, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=flds, restval="")
            w.writeheader()
            w.writerows(rs)
    rsum = lambda rs: sum(int(r.get("rows_n") or r.get("coverage_rows") or 0) for r in rs)
    print("layers", len(rows), "rows", rsum(rows), "tu_layers", len(tu), "tu_rows", rsum(tu), "coverage",
          {v: [sum(1 for r in mv if r["verdict"] == v), rsum([r for r in mv if r["verdict"] == v])]
           for v in ("active", "minimal_safe", "unavailable")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
