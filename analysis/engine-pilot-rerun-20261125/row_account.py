"""行数闭合账：把「输入行 → 导出/合并/丢弃」逐项对上，任何差额必须为 0。

第 6 步只报了 deduped/dup/unkeyed/low_grade/out_of_state 五个数，没给出恒等式；
本轮补一张能逐位相加的账（尤其把「州为空 → 在库里但按州导出时被排除」的行显式列出来，
不再让它无声消失）。

  python3 analysis/engine-pilot-rerun-20261125/row_account.py     # → row-account.json

数据来源：analysis/engine-pilot-rerun-20261125/_work/<ST>.sqlite（融合库，gitignore，可由 pilot.py 重跑再生）
          + <ST>/stats.json（源行数/去重/丢行计数）
恒等式：rows_in - range_only_rows == low_grade + unkeyed_total + fused_total + dup_rows
        其中 fused_total = exported_rows + no_state_fused，unkeyed_total = unkeyed_exported + no_state_unkeyed
"""
import json
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CUR = os.path.join(ROOT, "analysis", "engine-pilot-rerun-20261125")


def one(state):
    st = json.load(open(os.path.join(CUR, state, "stats.json"), encoding="utf-8"))
    p = os.path.join(CUR, "_work", f"{state}.sqlite")
    out = {"state": state, "db": os.path.relpath(p, ROOT), "db_available": os.path.isfile(p)}
    range_rows = sum(s.get("rows_in", 0) for s in st.get("sources", []) if s.get("range_only"))
    out["rows_in"] = st.get("rows_in")
    out["range_only_rows"] = range_rows
    out["low_grade"] = st.get("dropped_low_grade")
    out["dup_rows"] = st.get("dup_rows")
    out["unkeyed_rows_reported"] = st.get("unkeyed_rows")
    out["out_of_state_rows"] = st.get("dropped_out_of_state")
    out["exported_rows"] = st.get("deduped_rows")
    if not out["db_available"]:
        out["note"] = "融合库不在（unavailable）；恒等式无法在此机器之外复算"
        return out
    db = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    q = lambda s, a=(): db.execute(s, a).fetchone()[0]  # noqa: E731
    out["fused_total"] = q("SELECT COUNT(*) FROM fused")
    out["fused_state"] = dict(db.execute("SELECT state, COUNT(*) FROM fused GROUP BY state"))
    out["unkeyed_total"] = q("SELECT COUNT(*) FROM unkeyed")
    out["unkeyed_state"] = dict(db.execute("SELECT state, COUNT(*) FROM unkeyed GROUP BY state"))
    out["no_state_fused"] = out["fused_state"].get("", 0)
    out["no_state_unkeyed"] = out["unkeyed_state"].get("", 0)
    db.close()
    lhs = out["rows_in"] - out["range_only_rows"]
    rhs = out["low_grade"] + out["unkeyed_total"] + out["fused_total"] + out["dup_rows"]
    out["check"] = {"lhs": lhs, "rhs": rhs, "diff": lhs - rhs,
                    "identity": "rows_in - range_only_rows = low_grade + unkeyed_total + fused_total + dup_rows"}
    out["no_state_note"] = ("州为空的行仍在库里（可与同键行合并），但按州导出时被排除："
                            f"fused {out['no_state_fused']} 行 + unkeyed {out['no_state_unkeyed']} 行")
    return out


def main():
    res = {s: one(s) for s in ("DE", "NH", "IA")}
    res["totals"] = {k: sum(v.get(k, 0) for s, v in res.items() if isinstance(v, dict) and k in v)
                     for k in ("rows_in", "range_only_rows", "low_grade", "dup_rows", "exported_rows",
                               "fused_total", "unkeyed_total", "no_state_fused", "no_state_unkeyed")}
    res["totals"]["check"] = {"diff": sum(v.get("check", {}).get("diff", 0) for s, v in res.items()
                                          if isinstance(v, dict))}
    with open(os.path.join(CUR, "row-account.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    for s in ("DE", "NH", "IA"):
        print(s, res[s].get("check"), res[s].get("no_state_fused"), res[s].get("no_state_unkeyed"))
    print("totals", res["totals"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
