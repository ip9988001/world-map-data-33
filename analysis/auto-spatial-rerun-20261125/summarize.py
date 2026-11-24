#!/usr/bin/env python3
"""本轮汇总：三档 / 三列闭合 / E1–E8 分布 / E6·E7 归位 / geom_type 分项 / 抽样清单 → summary.json。

只读 analysis/auto-spatial-rerun-20261125/{auto-recognized.csv,coord-evidence.csv} 与
analysis/coord-samples-20261124/samples/*.csv；所有数字都能从这两处复算。
"""
import collections, csv, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ART = os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
EKEYS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")
SEED = 20261125
PREV = {"tier1": [0, 0], "tier2": [1123, 92206281], "tier3": [16045, 892513083],
        "active": [0, 0], "minimal_safe": [4102, 159336591], "unavailable": [6954, 138182717]}

rows = list(csv.DictReader(open(os.path.join(ART, "auto-recognized.csv"), encoding="utf-8")))
ev = {r["url"]: r for r in csv.DictReader(open(os.path.join(ART, "coord-evidence.csv"), encoding="utf-8"))}
rsum = lambda rs: sum(int(r["coverage_rows"] or 0) for r in rs)  # noqa: E731
tu = [r for r in rows if r["assign_reason"] == "template_unresolved"]
sampled, filesof = collections.Counter(), {}
for p in glob.glob(os.path.join(SAMPLES, "*.csv")):
    for r in csv.DictReader(open(p, encoding="utf-8")):
        u = r["layer_url"] or f"local:{r['layer_id']}"
        sampled[u] += 1
        filesof.setdefault(u, os.path.basename(p))

out = {"generated_utc": __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
       "seed": SEED,
       "inputs": {"samples": "analysis/coord-samples-20261124/samples/*.csv",
                  "evidence": "analysis/auto-spatial-rerun-20261125/coord-evidence.csv",
                  "recognized": "analysis/auto-spatial-rerun-20261125/auto-recognized.csv"},
       "denominator": len(rows), "rows_total": rsum(rows),
       "tiers": {}, "moves": {}, "previous_round": PREV, "evidences": {}, "by_geom": {},
       "tier1_combos": [], "e6_unknown_reasons": {}, "e7_unknown_reasons": {}}

for t in ("tier1", "tier2", "tier3"):
    rs = [r for r in rows if r["tier"] == t]
    out["tiers"][t] = {"layers": len(rs), "rows": rsum(rs), "pct_layers": round(len(rs) / len(rows) * 100, 2)}
for v in ("active", "minimal_safe", "unavailable"):
    rs = [r for r in tu if r["verdict"] == v]
    out["moves"][v] = {"layers": len(rs), "rows": rsum(rs)}
out["moves"]["_check"] = {"layers": sum(out["moves"][v]["layers"] for v in ("active", "minimal_safe", "unavailable")),
                          "rows": sum(out["moves"][v]["rows"] for v in ("active", "minimal_safe", "unavailable")),
                          "tu_layers": len(tu), "tu_rows": rsum(tu)}
for k in EKEYS:
    out["evidences"][k] = {s: sum(1 for r in rows if r[f"{k}_state"] == s) for s in ("clear", "hit", "unknown", "na")}
for k in ("E6", "E7"):
    out[f"{k.lower()}_unknown_reasons"] = collections.Counter(
        r[f"{k}_detail"].split("（")[0][:60] for r in rows if r[f"{k}_state"] == "unknown").most_common(8)
gt = lambda r: r["geom_type"] or "unknown"  # noqa: E731
for g in sorted({gt(r) for r in rows}):
    rs = [r for r in rows if gt(r) == g]
    out["by_geom"][g] = {"layers": len(rs), "rows": rsum(rs),
                         "e6": {s: sum(1 for r in rs if r["E6_state"] == s) for s in ("clear", "hit", "unknown")},
                         "e7": {s: sum(1 for r in rs if r["E7_state"] == s) for s in ("clear", "hit", "unknown")}}
def all_clear(r, skip=(), e3_na=False):
    """复算：是否 8 条证据全 clear/na（可跳过某条、可把『粒度未知但有实测几何』按 E8 同理记 na）。"""
    for k in EKEYS:
        if k in skip:
            continue
        st = r[f"{k}_state"]
        if e3_na and k == "E3" and st == "unknown" and r["geom_type"]:
            st = "na"
        if st not in ("clear", "na"):
            return False
    return True


def sens(pred):
    rs = [r for r in rows if pred(r)]
    return {"layers": len(rs), "rows": rsum(rs)}


out["sensitivity"] = {
    "e3_unknown_as_na_when_geom_measured": sens(lambda r: all_clear(r, e3_na=True)),
    "e6_e7_both_measured_and_all_clear": sens(lambda r: all_clear(r) if (r["E6_state"] in ("clear", "hit")
                                                                        and r["E7_state"] in ("clear", "hit")) else False),
    "only_e7_unverifiable": sens(lambda r: all_clear(r, skip=("E7",)) and r["E7_state"] == "unknown"),
    "e3_na_and_only_e7_unverifiable": sens(lambda r: all_clear(r, skip=("E7",), e3_na=True) and r["E7_state"] == "unknown"),
}
t1 = [r for r in rows if r["tier"] == "tier1"]
for key, c in collections.Counter((r["granularity"], gt(r)) for r in t1).items():
    out["tier1_combos"].append({"granularity": key[0], "geom_type": key[1], "layers": c,
                                "rows": rsum([r for r in t1 if (r["granularity"], gt(r)) == key]),
                                "evidence": "E1..E6 全 clear、E7 同址投票无冲突、E8 na/clear（见 tier1-evidence.csv）"})
json.dump(out, open(os.path.join(ART, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(os.path.join(ART, "sampling-list.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["layer_id", "url", "state", "geom_type", "seed", "rows_sampled", "tier", "verdict"])
    for r in rows:
        w.writerow([r["layer_id"], r["url"], r["state"], gt(r), SEED, sampled.get(r["url"], 0), r["tier"], r["verdict"]])
# Tier1 逐层放行证据链（哪一层凭什么进 active：证据状态 + 坐标样本文件 + 抽样行号区间）
with open(os.path.join(ART, "tier1-evidence.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["layer_id", "url", "state", "samples_file", "rows_sampled", "row_index_range",
                "geom_type", "granularity"] + [f"{k}_state" for k in EKEYS] +
               ["e6_detail", "e7_detail", "rows_n", "verdict"])
    for r in rows:
        if r["tier"] != "tier1":
            continue
        e = ev.get(r["url"], {})
        n = sampled.get(r["url"], 0)
        w.writerow([r["layer_id"], r["url"], r["state"], filesof.get(r["url"], ""), n,
                    f"0..{n - 1}" if n else "", r["geom_type"], r["granularity"]] +
                   [r[f"{k}_state"] for k in EKEYS] +
                   [e.get("e6_detail", ""), e.get("e7_detail", ""), r["coverage_rows"], r["verdict"]])
print(json.dumps({k: out[k] for k in ("denominator", "rows_total", "tiers", "moves")}, ensure_ascii=False))
