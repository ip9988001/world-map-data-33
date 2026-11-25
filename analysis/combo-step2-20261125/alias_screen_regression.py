#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② step5：逐别名回归筛查（非 P7 层的旧键不许被改、不许丢）。

对每个候选别名单独加入 ROLES，扫 coord-samples 全量行（13,532 层 / 695,706 非 P7 行）：
  harm = 旧键非空、新键与旧键不同（旧键被改）
  loss = 旧键非空、新键为空（键丢失）
  gain = 旧键空、新键非空（纯增益，pipeline 原本出不了键）
判据：harm=0 且 loss=0 才准进别名表（派单第 4 条 d 项「非 P7 层建键结果不许变化」的硬约束）。
产物：_work/alias_screen.csv + _work/alias_screen.json（汇总）
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_keys as V  # noqa: E402

SAMPLES = V.SAMPLES
WORK = V.WORK


def main():
    extra = V.engine_alias_section()
    R_OLD = V.roles_old()
    p7 = {r["url"] for r in csv.DictReader(open(os.path.join(V.STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"}
    cand = {}
    for role in ("number", "street"):
        for a in extra[role]:
            cand[V.norm(a)] = (role, a)

    stat = {k: {"role": r, "alias": a, "harm": 0, "loss": 0, "gain": 0, "gain_ok": 0,
                "harm_examples": []} for k, (r, a) in cand.items()}
    n_rows = 0
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r.get("layer_url") or ""
            if u in p7:
                continue
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                af = {}
            if not af:
                continue
            n_rows += 1
            st = r.get("state") or ""
            k1 = V.addr_key(af, R_OLD, st)
            present = {V.norm(k) for k in af}
            for n in (present & set(cand)):
                role, alias = cand[n]
                RR = collections.defaultdict(set)
                for k, v in R_OLD.items():
                    RR[k] |= v
                RR[n].add(role)
                k2 = V.addr_key(af, RR, st)
                e = stat[n]
                if k1 and k2 and k2 != k1:
                    e["harm"] += 1
                    if len(e["harm_examples"]) < 3:
                        e["harm_examples"].append({"layer": u, "old": k1, "new": k2})
                elif k1 and not k2:
                    e["loss"] += 1
                elif not k1 and k2:
                    e["gain"] += 1
                    e["gain_ok"] += 1 if V.key_ok(k2) else 0

    rows = []
    for n, e in stat.items():
        rows.append({"role": e["role"], "alias": e["alias"], "norm": n, "harm": e["harm"], "loss": e["loss"],
                     "gain": e["gain"], "gain_ok": e["gain_ok"], "verdict": "keep" if not (e["harm"] or e["loss"]) else "drop",
                     "harm_example": json.dumps(e["harm_examples"][:1], ensure_ascii=False)})
    rows.sort(key=lambda r: (r["verdict"], -r["gain"]))
    with open(os.path.join(WORK, "alias_screen.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    keep = [r for r in rows if r["verdict"] == "keep"]
    json.dump({"non_p7_rows_scanned": n_rows, "candidates": len(rows), "keep": len(keep),
               "drop": len(rows) - len(keep),
               "keep_number": [r["alias"] for r in keep if r["role"] == "number"],
               "keep_street": [r["alias"] for r in keep if r["role"] == "street"],
               "dropped": [{"alias": r["alias"], "role": r["role"], "harm": r["harm"], "loss": r["loss"],
                            "gain": r["gain"]} for r in rows if r["verdict"] == "drop"]},
              open(os.path.join(WORK, "alias_screen.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"non_p7_rows_scanned": n_rows, "keep": len(keep), "drop": len(rows) - len(keep)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
