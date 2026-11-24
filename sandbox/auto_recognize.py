"""自动认（沙盒）：8 条否定证据 + 三档分级。只读复用第 4 步产物，registry/ 一个字节不改。
判据全是「字段有没有值 / 几何对不对得上」；全文件不存在任何 confidence 阈值门控。
"""
import argparse, collections, csv, json, os, re, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIAL = os.path.join(ROOT, "analysis", "dialect-20261124")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124")
EKEYS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")
FATAL = ("E1", "E2", "E3", "E8")
ENAMES = {"E1": "门牌要素缺失/不可解析", "E2": "街名要素缺失或占位值", "E3": "几何语义不符", "E4": "别名冲突未解",
          "E5": "样本份额过低/不可代表", "E6": "空间验算不通过", "E7": "源间投票冲突", "E8": "上游结构漂移"}
GRAN_REQ = {"building_point": {"point"}, "apartment_unit_point": {"point"}, "parcel_centroid": {"polygon"},
            "range_interpolation": {"point", "polyline"}, "centerline_midpoint": {"polyline"}}  # 粒度→合法几何
NUM_FAM = re.compile(r"hn$|house_?num|housenumber|hse_?num|add(?:r(?:ess)?)?_?num|addr_?no|st(?:reet)?_?num|site_?addr|bldg_?no|^num$|^number$|^no$")
NUM_NEG = re.compile(r"parcel|route|hwy|phone|area|bike|juris|district|tract|lot|block|gpid|objectid|fid|globalid|permit|book|page|sheet|sqft|mile|percent|year|capacity|lane|unit")
PLACEHOLDER = {"TBD", "UNKNOWN", "NULL", "N/A", "NA", "NONE", "-"}
norm = lambda f: re.sub(r"[^a-z0-9]", "", (f or "").lower())


def load_ctx(outdir):
    """一次性只读装载：第 3 步字段事实 ⋈ 探针字段集 ⋈ registry 别名表 ⋈ 空间结论。"""
    inv = {}
    for n in ("inventory-remote-uncollected.csv", "inventory-local-all.csv"):
        for r in csv.DictReader(open(os.path.join(INV, n), encoding="utf-8")):
            inv.setdefault(r["url"], {}).update({
                "bits": r.get("addr_core_hit", ""), "geom": r.get("geom", ""), "sampled_n": r.get("sampled_n", "0"),
                "n_fields": r.get("n_fields") or r.get("fields_n", ""), "count": r.get("count") or r.get("rows", ""),
                "nlike": r.get("fields_number_like", "")})
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
    spatial = {r["key"]: r for r in csv.DictReader(open(sf, encoding="utf-8"))
               if r["kind"] == "fixture_layer"} if os.path.isfile(sf) else {}
    return {"inv": inv, "probe": probe, "roles": roles, "ph": ph, "spatial": spatial}


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
def ev3(L, C):  # 几何语义：granularity ⇄ geom 类型
    g, gran = (L["geom"] or "").lower(), (L["granularity"] or "unknown")
    if not g or gran == "unknown":
        return "unknown", f"geom={L['geom'] or '缺'} / granularity={gran}（点位语义不可判）"
    return ("clear", "") if g in (GRAN_REQ.get(gran) or set()) else ("hit", f"{gran} 与 geom={L['geom']} 冲突")
def ev4(L, C):  # 别名冲突：门牌证据落在负向字段族（parcel/route/phone…）或同名字段跨方言映射到不同要素
    fields, bad = C["probe"].get(L["url"]), set()
    bad |= {f for f in (L["nlike"] or "").split(",") if f and NUM_NEG.search(norm(f))}
    bad |= {f for f in (fields or []) if len(C["roles"].get(f) or ()) > 1}
    if bad:
        return "hit", "门牌族被负向规则命中/跨要素同名字段: " + ",".join(sorted(bad)[:6])
    return ("unknown", "无同源探针字段集（探针配额 1,000/1,000 已用满）") if fields is None \
        else ("clear", f"探针 {len(fields)} 字段无冲突")
def ev5(L, C):  # 样本份额：抽样为空 / 抽样被截断 / 层份额过低
    n, cnt, share = int(L["sampled_n"] or 0), int(float(L["count"] or 0)), float(L["share"] or 0)
    if n == 0:
        return "hit", "抽样为空（sampled_n=0）"
    if cnt and n < min(20, cnt):
        return "hit", f"抽样被截断 n={n} < min(20,count={cnt})"
    return ("hit", f"层份额 {share} < 0.01%") if share < 1e-4 else ("clear", f"n={n} count={cnt}")
def ev6(L, C):  # 空间验算（只认本目录 spatial-findings.csv 的真实结论；按 url 找，layer_id 不唯一）
    f = C["spatial"].get(L["url"])
    if not f:
        return "unknown", "无坐标样本 → 空间验算未跑（第 3 步只探 meta，未采坐标）"
    return ("clear", "") if f["verdict"] == "green" else ("hit", f["note"])
def ev7(L, C):  # 源间投票
    return "unknown", "无多源同址解析结果（第 3 步未产出地址级多源投票）"
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


def move_of(t, st):
    if t == "tier1":
        return "active", ""
    if t == "tier2":
        return "minimal_safe", "门牌+街名齐（addr_core_hit[:2]=11），交 minimal_safe 解析器"
    return "manual", ",".join([k for k in FATAL if st[k] in ("hit", "unknown")] +
                              [k for k in ("E5", "E6", "E7") if st[k] != "clear"])


def evaluate(L, C):
    L = {**L, **C["inv"].get(L["url"], {})}
    ev = {k: f(L, C) for k, f in zip(EKEYS, EVIDENCES)}
    st = {k: v[0] for k, v in ev.items()}
    t = tier_of(st)
    mv, why = move_of(t, st)
    return {"layer_id": L["layer_id"], "url": L["url"], "universe": L["universe"], "dialect_id": L["dialect_id"],
            "provider_id": L["provider_id"], "state": L["state"], "granularity": L["granularity"],
            "geom": L["geom"], "usable": L["usable"], "assign_reason": L["reason"], "share": L["share"],
            "coverage_rows": L["coverage_rows"], "tier": t, "move": mv, "move_reason": why,
            **{f"{k}_state": st[k] for k in EKEYS}, **{f"{k}_detail": ev[k][1] for k in EKEYS if ev[k][1]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(ROOT, "analysis", "auto-spatial-20261124"))
    args = ap.parse_args()
    C, outdir = load_ctx(args.outdir), args.outdir
    rows = [evaluate(L, C) for L in csv.DictReader(
        open(os.path.join(DIAL, "dialect-assignment.csv"), encoding="utf-8"))]
    cols = list(dict.fromkeys(k for r in rows for k in r))
    tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]
    os.makedirs(outdir, exist_ok=True)
    for name, rs in (("auto-recognized.csv", rows), ("template-unresolved-moves.csv", tu)):
        with open(os.path.join(outdir, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, restval="")
            w.writeheader()
            w.writerows(rs)
    rsum = lambda rs: sum(int(r["coverage_rows"] or 0) for r in rs)
    print("layers", len(rows), "rows", rsum(rows), "tu_layers", len(tu), "tu_rows", rsum(tu), "tier",
          {k: [sum(1 for r in rows if r["tier"] == k), rsum([r for r in rows if r["tier"] == k])]
           for k in ("tier1", "tier2", "tier3")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
