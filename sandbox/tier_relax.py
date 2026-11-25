"""E3/E7 放宽分档（沙盒）：在第 5 步 strict 结果之上，按两个开关重算三档 + 四档留底 + 挪动表。

两条口径（muse-000226 拍板，其余判据一字不改）：
- E3 放宽：granularity=unknown 且坐标样本有实测几何类型（geom_type 非空）→ 记 na（与 E8「无模板即 na」同理）；
  E3 仍是 FATAL：粒度已知却与几何冲突 → 仍记 hit。
- E7 放宽：改用 sandbox/e7_refpool.py 的「坐标样本 + 本地全表前 N 行」参照池结论；判据仍旧
  >300m 记冲突、n_cmp<3 记 unknown、绝不冒充 clear。参照池没覆盖到的 url 一律沿用 strict 结论，不补不猜。

四档：严格 / 只放 E3 / 只放 E7 / 两个都放。四档是「两个都放」Tier1 集合的**划分**，
代码里断言 四档层数之和 == Tier1 层数（同时断言行数），不一致直接非零退出。

用法：python3 sandbox/tier_relax.py --strict analysis/auto-spatial-rerun-20261125
                                   --outdir analysis/auto-spatial-relax-20261125 [--e3-relax on|off]
"""
import argparse, collections, csv, datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402
from sandbox.auto_recognize import EKEYS, FATAL, load_ctx  # noqa: E402

THRESHOLDS = os.path.join(ROOT, "sandbox", "spatial_thresholds.yaml")
BUCKETS = ("strict", "e3_only", "e7_only", "both")
POOLS = {"strict": ("off", "off"), "e3_only": ("on", "off"), "e7_only": ("off", "on"), "both": ("on", "on")}


def load_thresholds(path=THRESHOLDS):
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    return {"e3_default": doc.get("e3_relax", {}).get("default", {}).get("value", "off"),
            "e7_conflict_m": doc["e7"]["max_addr_conflict_m"]["value"],
            "e7_min_cmp": doc["e7"]["min_cmp_rows"]["value"]}


def states_of(r, e3_relax, e7):
    """把 strict 的 E1..E8 状态按两个开关改成四个组合下的状态（其余 6 条一个字节不动）。"""
    st = {k: r[f"{k}_state"] for k in EKEYS}
    det = {k: r.get(f"{k}_detail", "") for k in EKEYS}
    e3 = dict(st)
    if e3_relax and st["E3"] == "unknown" and (r.get("granularity") or "") == "unknown" and (r.get("geom_type") or ""):
        e3["E3"] = "na"
        det["E3"] = f"放宽：granularity=unknown 但几何有实测 geom_type={r['geom_type']} → 按 E8 同理记 na"
    e7s = dict(st)
    row7 = e7.get(r["url"])
    if row7:
        e7s["E7"] = row7["e7"]
        det["E7"] = row7["e7_detail"]
    return e3, e7s, det


def tier_of(st):
    """与 sandbox/auto_recognize.tier_of 同一条判据：①②③⑧ 任一 hit/unknown、或 ⑥ hit → Tier3。"""
    if any(st[k] in ("hit", "unknown") for k in FATAL) or st["E6"] == "hit":
        return "tier3"
    return "tier1" if all(v in ("clear", "na") for v in st.values()) else "tier2"


def move_of(t, st, bits):
    """与 auto_recognize.move_of 同一条判据；bits=addr_core_hit（门牌/街名族样值过半有值）。"""
    if t == "tier1":
        return "active", ""
    block = [k for k in FATAL if st[k] in ("hit", "unknown")] + [k for k in ("E5", "E6", "E7") if st[k] != "clear"]
    return ("minimal_safe" if (bits or "")[:2] == "11" else "unavailable"), ",".join(block)


def bucket_of(t00, t10, t01):
    """四档划分：只按「哪个开关单独就够」归类；四档并集 = 两个都放时的 Tier1（断言保证）。"""
    if t10 == "tier1" and t01 == "tier1":
        return "strict"
    if t10 == "tier1":
        return "e3_only"
    return "e7_only" if t01 == "tier1" else "both"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", default=os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125"))
    ap.add_argument("--outdir", default=os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125"))
    ap.add_argument("--e3-relax", choices=("on", "off"), default=None)
    args = ap.parse_args()
    th = load_thresholds()
    e3_on = (args.e3_relax or th["e3_default"]) == "on"
    ctx = load_ctx(args.strict)                                    # 只读：拿 addr_core_hit（bits）
    rows = list(csv.DictReader(open(os.path.join(args.strict, "auto-recognized.csv"), encoding="utf-8")))
    rp = os.path.join(args.outdir, "coord-evidence-relax.csv")
    e7 = {r["url"]: r for r in csv.DictReader(open(rp, encoding="utf-8"))} if os.path.isfile(rp) else {}
    if not e7:
        print(f"WARN: {rp} 缺 → E7 一律沿用 strict（E7 放宽实际未生效）", file=sys.stderr)

    recs = []
    for r in rows:
        r["tier_orig"] = r["tier"]
        e3, e7s, det = states_of(r, True, e7)
        s0 = {k: r[f"{k}_state"] for k in EKEYS}
        t00 = tier_of(s0)                                       # strict 列永远按 strict 口径算
        t10, t01, t11 = tier_of(e3), tier_of(e7s), tier_of({**e3, "E7": e7s["E7"]})
        bits = (ctx["inv"].get(r["url"], {}) or {}).get("bits", "")
        final = t11 if e3_on else t01                            # --e3-relax off → 只放 E7，可复现严格档
        mv, why = move_of(final, {**e3, "E7": e7s["E7"]}, bits)
        recs.append({**r, "tier_strict": t00, "tier_e3": t10, "tier_e7": t01, "tier_both": t11,
                     "tier": final, "bucket": bucket_of(t00, t10, t01) if final == "tier1" else "",
                     "e3_relax_state": e3["E3"], "e7_relax_state": e7s["E7"],
                     "move": mv, "verdict": mv,
                     # 证据列：保留 strict 阶段的「可验分母剔除」标记（只加标记，不改档位）
                     "reason_evidence": ",".join(x for x in (why, (
                         f"excluded_from_verifiable_denominator: {r['denominator_excluded']}"
                         if r.get("denominator_excluded") else "")) if x),
                     "reason_detail": r.get("reason_detail", ""),
                     "relax_detail": f"E3: {det['E3']} | E7: {det['E7']}" if (det["E3"] or det["E7"]) else ""})

    # —— 闭合与四档断言（硬约束，不过就非零退出）——
    rows_n = lambda rs: sum(int(r.get("rows_n") or r.get("coverage_rows") or 0) for r in rs)
    tiers = {t: [r for r in recs if r["tier"] == t] for t in ("tier1", "tier2", "tier3")}
    bkt = {b: [r for r in recs if r["bucket"] == b] for b in BUCKETS}
    tu = [r for r in recs if r["assign_reason"] == "template_unresolved"]
    moves = {v: [r for r in tu if r["move"] == v] for v in ("active", "minimal_safe", "unavailable")}
    # —— ③ 老规矩回归：minimal_safe 只取门牌+街名、永不进 A 货池、只上网站（本轮不改） ——
    strict_mv = os.path.join(args.strict, "template-unresolved-moves.csv")
    strict_ms = {r["url"] for r in csv.DictReader(open(strict_mv, encoding="utf-8"))
                 if r["verdict"] == "minimal_safe"} if os.path.isfile(strict_mv) else set()
    ms = {r["url"] for r in moves["minimal_safe"]}
    ms_bits_ok = sum(1 for r in moves["minimal_safe"] if ((ctx["inv"].get(r["url"], {}) or {}).get("bits") or "")[:2] == "11")
    ms_reg = {"layers": len(moves["minimal_safe"]), "rows": rows_n(moves["minimal_safe"]),
              "strict_layers": len(strict_ms), "promoted_to_active": len(strict_ms - ms),
              "new_minimal_safe_not_in_strict": len(ms - strict_ms),
              "bits_11_all": ms_bits_ok == len(moves["minimal_safe"]),
              "a_pool_eligible": "false（registry/evaluator.py L84-86 硬编码，本轮未改一个字节）",
              "unchanged": len(ms - strict_ms) == 0 and ms_bits_ok == len(moves["minimal_safe"])}

    sum_b = sum(len(v) for v in bkt.values())
    sum_br = sum(rows_n(v) for v in bkt.values())
    checks = {
        "tiers_layers": sum(len(v) for v in tiers.values()), "tiers_rows": rows_n(recs),
        "tiers_diff_layers": sum(len(v) for v in tiers.values()) - len(rows),
        "tiers_diff_rows": rows_n(recs) - rows_n(rows),
        "moves_layers": sum(len(v) for v in moves.values()), "moves_rows": rows_n(tu),
        "tu_layers": len(tu), "tu_rows": rows_n(tu),
        "bucket_sum_layers": sum_b, "bucket_sum_rows": sum_br,
        "tier1_layers": len(tiers["tier1"]), "tier1_rows": rows_n(tiers["tier1"]),
        "buckets_equal_tier1": sum_b == len(tiers["tier1"]) and sum_br == rows_n(tiers["tier1"]),
        "strict_reproduced_layers": sum(1 for r in recs if r["tier_strict"] == r["tier_orig"]),
    }
    checks["moves_diff_layers"] = checks["moves_layers"] - checks["tu_layers"]
    checks["moves_diff_rows"] = checks["moves_rows"] - checks["tu_rows"]
    checks["tiers_closed"] = checks["tiers_diff_layers"] == 0 and checks["tiers_diff_rows"] == 0
    checks["moves_closed"] = checks["moves_diff_layers"] == 0 and checks["moves_diff_rows"] == 0
    checks["minimal_safe_unchanged"] = ms_reg["unchanged"] and ms_reg["bits_11_all"]
    if not (checks["tiers_closed"] and checks["moves_closed"] and checks["buckets_equal_tier1"]):
        print("ASSERT FAILED", json.dumps(checks, ensure_ascii=False), file=sys.stderr)
        return 2

    os.makedirs(args.outdir, exist_ok=True)
    extra = ["relax_detail", "tier_strict", "tier_e3", "tier_e7", "tier_both", "bucket", "e3_relax_state", "e7_relax_state",
             "tier_orig"]
    cols = list(dict.fromkeys(list(rows[0].keys()) + extra))
    with open(os.path.join(args.outdir, "auto-recognized.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(recs)
    mv_cols = "layer_id,url,provider,granularity,geom_type,rows_n,tier_strict,tier_both,bucket,verdict,reason_evidence,reason_detail,relax_detail".split(",")
    for name, rs in (("template-unresolved-moves.csv", tu), ("template-unresolved-unavailable.csv", moves["unavailable"])):
        with open(os.path.join(args.outdir, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=mv_cols, restval="")
            w.writeheader()
            w.writerows([{k: r.get(k, "") for k in mv_cols} for r in rs])
    b_cols = "layer_id,url,bucket,rows_n,granularity,geom_type,tier_strict,tier_e3,tier_e7,tier_both," \
             "granularity_state,E3_state,E7_state,reason".split(",")
    with open(os.path.join(args.outdir, "tier1-buckets.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=b_cols, restval="")
        w.writeheader()
        w.writerows([{**{k: r[k] for k in b_cols if k in r},
                      "granularity_state": r["granularity"], "E3_state": r["e3_relax_state"],
                      "E7_state": r["e7_relax_state"],
                      "reason": f"E3={r['E3_detail']} | E7={r['E7_detail']}"} for r in tiers["tier1"]])
    for b in BUCKETS:
        with open(os.path.join(args.outdir, f"tier1-{b}.ids"), "w", encoding="utf-8") as fh:
            fh.writelines(r["layer_id"] + "\n" for r in bkt[b])
    ev_cols = "layer_id,url,bucket,rows_n,granularity,geom_type," + ",".join(
        f"{k}_state" for k in EKEYS) + ",E3_detail,E7_detail"
    with open(os.path.join(args.outdir, "tier1-evidence.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ev_cols.split(","), restval="")
        w.writeheader()
        w.writerows([{**{k: r.get(k, "") for k in ev_cols.split(",")},
                      "E3_detail": r["e3_relax_state"] + " | " + r.get("E3_detail", ""),
                      "E7_detail": e7.get(r["url"], {}).get("e7_detail", r.get("E7_detail", ""))}
                     for r in tiers["tier1"]])

    # —— 归因：把「E7 完全可验」假设下能进 Tier1 的层逐证据拆开（不许拿 1,831 当挡箭牌） ——
    cell = collections.Counter()
    hyp = []
    for r in recs:
        st = {k: r[f"{k}_state"] for k in EKEYS}
        rest = {k: v for k, v in st.items() if k not in ("E3", "E7")}
        if any(v not in ("clear", "na") for v in rest.values()):
            continue
        a = "E3_na" if r["e3_relax_state"] == "na" else st["E3"]
        cell[f"E3={a}|E7={r['E7_state']}"] += 1
        if r["e3_relax_state"] in ("na", "clear") and st["E7"] == "unknown":
            hyp.append(r["url"])
    blocked = collections.Counter()
    for u in hyp:
        m = next(r for r in recs if r["url"] == u)
        d = e7.get(u)
        if m["tier"] == "tier1":
            blocked["已进 Tier1（E7 放宽兑现）"] += 1
        elif not d:
            blocked["E7 unknown：无坐标样本"] += 1
        elif not int(d.get("n_addr_rows") or 0):
            blocked["E7 unknown：样本/本地全表都构不出门牌+街名键"] += 1
        elif int(d.get("n_cmp") or 0) < th["e7_min_cmp"]:
            blocked[f"E7 unknown：n_cmp={int(d['n_cmp'])} < {th['e7_min_cmp']}"] += 1
        else:
            blocked["E7 unknown：其他"] += 1
    attribution = {
        "hypothetical_both_relax_tier1": len(hyp),
        "achieved": len(tiers["tier1"]),
        "blocked": dict(blocked),
        "combo_cells_rest_clear": dict(cell),
        "note": "1,831 = 1,438(E3 未定+E7 未定) + 393(仅 E7 未定)，是「E7 完全可验」假设下**被 E7 挡住的层数**，"
                "不含本来就靠 E3 放宽进 Tier1 的 166 层；同假设下 Tier1 总数应为 1,997。实算 176 → E7 放宽只兑现 10 层，"
                "其余按上面 blocked 逐证据归因（不含调参）。"}
    target = 1831
    n1 = len(tiers["tier1"])
    newly_verifiable = [r["url"] for r in recs if r["E7_state"] == "unknown" and r["url"] in e7
                        and e7[r["url"]]["e7"] in ("clear", "hit")]
    e3_flip = sum(1 for r in recs if r["e3_relax_state"] == "na" and r["E3_state"] == "unknown")
    unk7 = collections.Counter()
    for r in recs:
        if r["tier"] == "tier1" or r["e7_relax_state"] != "unknown":
            continue
        d = e7.get(r["url"], {})
        if not d:
            unk7["无坐标样本（url 不在坐标样本里）"] += 1
        elif not int(d.get("n_addr_rows") or 0):
            unk7["无可投票行（样本 0 行 + 本地全表无 addr 行 / 无门牌+街名键）"] += 1
        elif int(d.get("n_cmp") or 0) < th["e7_min_cmp"]:
            unk7[f"n_cmp<{th['e7_min_cmp']}（有键但跨源同址行不足）"] += 1
        else:
            unk7["其他"] += 1
    summary = {
        "generated_utc": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"strict_dir": os.path.relpath(args.strict, ROOT), "relax_evidence": os.path.relpath(rp, ROOT),
                   "thresholds": "sandbox/spatial_thresholds.yaml"},
        "e3_relax_default": args.e3_relax or th["e3_default"], "denominator": len(recs), "rows_total": rows_n(recs),
        "tiers": {t: {"layers": len(v), "rows": rows_n(v), "pct_layers": round(100 * len(v) / len(recs), 2)}
                  for t, v in tiers.items()},
        "buckets": {b: {"layers": len(bkt[b]), "rows": rows_n(bkt[b]),
                        "granularity": dict(collections.Counter(r["granularity"] for r in bkt[b])),
                        "e3_off_e7_off": sum(1 for r in bkt[b] if r["tier_strict"] == "tier1"),
                        "e3_on_e7_off": sum(1 for r in bkt[b] if r["tier_e3"] == "tier1"),
                        "e3_off_e7_on": sum(1 for r in bkt[b] if r["tier_e7"] == "tier1")} for b in BUCKETS},
        "moves": {v: {"layers": len(rs), "rows": rows_n(rs)} for v, rs in moves.items()},
        "checks": checks,
        "target_1831": {"target": target, "actual": n1, "diff": n1 - target,
                        "pct_diff": round(100 * (n1 - target) / target, 2),
                        "beyond_5pct": abs(n1 - target) > 0.05 * target},
        "e3": {"unknown_to_na_layers": e3_flip,
               "detail": "granularity=unknown 且有实测 geom_type 的层记 na；E3 仍 FATAL"},
        "e7": {"evaluated_urls": len(e7), "newly_verifiable_layers": len(newly_verifiable),
               "resolved_any_layers": sum(1 for r in e7.values() if r["e7"] in ("clear", "hit")),
               "flips": dict(collections.Counter(
                   f"{r['E7_state']}->{e7[r['url']]['e7']}" for r in recs if r["url"] in e7)),
               "still_unknown_not_tier1": dict(unk7),
               "detail": f"参照池 = 738,174 行坐标样本 + 本地全表每层前 N 行；冲突线 {th['e7_conflict_m']}m、"
                         f"min_cmp_rows={th['e7_min_cmp']}"},
        "minimal_safe_regression": ms_reg, "attribution": attribution,
        "demoted_by_e7_relax": [r["layer_id"] for r in recs if r["tier_strict"] == "tier1" and r["tier_both"] != "tier1"],
    }
    with open(os.path.join(args.outdir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"tiers": {t: len(v) for t, v in tiers.items()}, "buckets": {b: len(v) for b, v in bkt.items()},
                      "moves": {v: len(rs) for v, rs in moves.items()}, "checks": checks,
                      "target": {"want": target, "got": n1}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
