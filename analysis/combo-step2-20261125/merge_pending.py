#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「语义待定」与「回归不通过」两类别名合成一张待定表：analysis/combo-step2-20261125/pending-uncertain.csv"""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")


def main():
    final = json.load(open(os.path.join(WORK, "alias_final.json")))
    screen = list(csv.DictReader(open(os.path.join(WORK, "alias_screen.csv"), encoding="utf-8")))
    rows = []
    for p in final["pending"]:
        rows.append({"role": p.get("role", ""), "alias": p.get("alias", ""),
                     "as_number_layers": p.get("as_number_layers", ""),
                     "as_street_layers": p.get("as_street_layers", ""),
                     "sample_values": "|".join(p.get("sample_values") or []),
                     "reason": p["reason"]})
    for r in screen:
        if r["verdict"] == "keep":
            continue
        rows.append({"role": r["role"], "alias": r["alias"], "as_number_layers": "", "as_street_layers": "",
                     "sample_values": "",
                     "reason": f"回归不通过：非 P7 层旧键被改 {r['harm']} 行（增益 {r['gain']} 行也不行）"})
    with open(os.path.join(HERE, "pending-uncertain.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["role", "alias", "as_number_layers", "as_street_layers",
                                          "sample_values", "reason"])
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({"pending_rows": len(rows),
                      "semantic": sum(1 for r in rows if "回归不通过" not in r["reason"]),
                      "regression_blocked": sum(1 for r in rows if "回归不通过" in r["reason"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
