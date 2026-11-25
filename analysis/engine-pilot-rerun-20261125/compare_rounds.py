"""第 7 步 vs 第 6 步逐列对比 + 差额归因（只读两轮产物，不改任何文件）。

  python3 analysis/engine-pilot-rerun-20261125/compare_rounds.py

输入：analysis/engine-pilot-20261125/{summary.json,<ST>/stats.json}（第 6 步）
      analysis/engine-pilot-rerun-20261125/{summary.json,<ST>/stats.json,tier-moves.csv}（本轮）
      _work/<ST>.sqlite（本轮融合库，用于归因计数；只读打开）
输出：comparison.json（报告里的对比表与归因数都从这里来）
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREV = os.path.join(ROOT, "analysis", "engine-pilot-20261125")
CUR = os.path.join(ROOT, "analysis", "engine-pilot-rerun-20261125")
STATES = ("DE", "NH", "IA")
FIELDS = ("rows_in", "deduped_rows", "dup_rows", "unkeyed_rows", "coord_conflict", "multi_source",
          "with_point", "dropped_low_grade", "dropped_out_of_state")


def load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else {}


def flat(stats):
    out = {k: stats.get(k) for k in FIELDS}
    for g in ("S", "A", "B", "C"):
        out[f"grade_{g}"] = (stats.get("by_grade") or {}).get(g, 0)
    for t in ("tier1", "tier2", "tier3", "unrated"):
        out[f"{t}_rows"] = (stats.get("by_tier") or {}).get(t, 0)
    out["s_with_pos_estimated"] = stats.get("s_with_pos_estimated", None)
    out["pos_estimated_rows"] = stats.get("pos_estimated_rows", None)
    return out


def attribution(state, moved_urls):
    """差额归因：只用本轮融合库中的可复算计数（tier_basis / contributors / point_kind），不猜。"""
    p = os.path.join(CUR, "_work", f"{state}.sqlite")
    out = {"db": os.path.relpath(p, ROOT), "available": os.path.isfile(p)}
    if not out["available"]:
        return out
    db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        q = lambda sql, args=(): db.execute(sql, args).fetchone()[0]  # noqa: E731
        out["rows"] = q("SELECT COUNT(*) FROM fused")
        out["moved_basis_rows"] = 0   # 胜利来源就是被挪动层（tier_basis = url|dialect）
        out["moved_contrib_rows"] = 0  # 被挪动层贡献了（参与去重）但不是胜利来源
        for url, did in moved_urls:
            basis = f"{url}|{did}"
            out["moved_basis_rows"] += q("SELECT COUNT(*) FROM fused WHERE tier_basis=?", (basis,))
            out["moved_contrib_rows"] += q(
                "SELECT COUNT(*) FROM fused WHERE contributors LIKE ? AND tier_basis<>?",
                (f'%"src": "{url}"%', basis))
        out["interp_takeover_rows"] = q(
            "SELECT COUNT(*) FROM fused WHERE pos_estimated=0 AND contributors LIKE '%\"interp\": true%'")
        out["vertex_rows"] = q("SELECT COUNT(*) FROM fused WHERE point_kind='vertex'")
        out["parcel_centroid_rows"] = q("SELECT COUNT(*) FROM fused WHERE point_kind='parcel_centroid'")
        out["interpolated_rows"] = q("SELECT COUNT(*) FROM fused WHERE point_kind='interpolated'")
        out["by_geom_type"] = {g: {"rows": n, "with_point": wp} for g, n, wp in db.execute(
            "SELECT geom_type, COUNT(*), SUM(CASE WHEN lon IS NOT NULL THEN 1 ELSE 0 END) "
            "FROM fused GROUP BY geom_type")}
        out["by_point_kind"] = dict(db.execute(
            "SELECT point_kind, COUNT(*) FROM fused GROUP BY point_kind"))
        out["by_tier_basis_ambiguous"] = q(
            "SELECT COUNT(*) FROM fused WHERE tier_basis LIKE '%|%' AND tier_rank IS NULL")
    finally:
        db.close()
    return out


def main():
    prev_sum, cur_sum = load(os.path.join(PREV, "summary.json")), load(os.path.join(CUR, "summary.json"))
    moves = []
    mp = os.path.join(CUR, "tier-moves.csv")
    if os.path.isfile(mp):
        import csv
        moves = list(csv.DictReader(open(mp, encoding="utf-8")))
    res = {"states": {}, "moves": {"rows": len(moves), "by_state": {}}, "notes": []}
    for m in moves:
        b = res["moves"]["by_state"].setdefault(m["state"], {"layers": 0, "rows_n": 0})
        b["layers"] += 1
        b["rows_n"] += int(m["rows_n"] or 0)
    for st in STATES:
        prev = flat(load(os.path.join(PREV, st, "stats.json")))
        cur = flat(load(os.path.join(CUR, st, "stats.json")))
        keys = sorted(set(prev) | set(cur))
        table = {k: {"prev": prev.get(k), "cur": cur.get(k),
                     "delta": (None if isinstance(prev.get(k), str) or isinstance(cur.get(k), str)
                               else (cur.get(k) or 0) - (prev.get(k) or 0))} for k in keys}
        moved = [(m["url"], m["dialect_id"]) for m in moves if m["state"] == st]
        res["states"][st] = {"table": table, "attribution": attribution(st, moved)}
    res["totals"] = {
        k: {"prev": sum((flat(load(os.path.join(PREV, s, "stats.json"))).get(k) or 0) for s in STATES),
            "cur": sum((flat(load(os.path.join(CUR, s, "stats.json"))).get(k) or 0) for s in STATES)}
        for k in ("rows_in", "deduped_rows", "grade_S", "grade_A", "grade_B", "grade_C", "with_point")}
    res["totals"]["deduped_delta"] = res["totals"]["deduped_rows"]["cur"] - res["totals"]["deduped_rows"]["prev"]
    res["notes"].append("差值只有两类来源：① 分档换了（tier3→tier2 的 20 层，只动 tier 分布与 best_tier）"
                        "② 点位口径（面/线顶点入坐标、真实点优先于插值）——逐州计数见 attribution")
    res["summary_rounds"] = {"prev_generated": prev_sum.get("generated_utc"), "cur_generated": cur_sum.get("generated_utc"),
                             "prev_tiers": (prev_sum.get("tier_tables") or {}), "cur_tiers": (cur_sum.get("tier_tables") or {}),
                             "cur_totals": cur_sum.get("totals"), "unsupported": cur_sum.get("unsupported")}
    out = os.path.join(CUR, "comparison.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(f"wrote {os.path.relpath(out, ROOT)}")
    for st in STATES:
        t = res["states"][st]["table"]
        print(st, {k: (t[k]["prev"], t[k]["cur"], t[k]["delta"]) for k in
                   ("rows_in", "deduped_rows", "grade_S", "grade_A", "grade_B", "with_point")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
