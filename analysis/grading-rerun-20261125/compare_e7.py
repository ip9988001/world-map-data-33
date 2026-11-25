#!/usr/bin/env python3
"""E7 逐层前后对照：旧实现（第 5 步 strict，committed）vs 本轮（engine 占位跳过 + P1 拆串 + 角色表合并）。

**before 不是本脚本重算的**，而是 `analysis/auto-spatial-rerun-20261125/coord-evidence.csv`
（第 5 步落盘、旧 `sandbox/coord_evidence.py:addr_key()` 的产物，只读）。这样对照的两个端点
都有落盘证据，不依赖任何"第二份实现"来复算旧口径。

delta_kind 判定顺序（写死，报告里同一条口径）：
  gained-key       n_addr_rows_after  >  before        —— 本层建键行增加（拆串/角色表）
  placeholder-skip n_addr_rows_after  <  before，且该层样本里「角色字段值为占位值」的行数
                   ≥ 减少行数                          —— 减少由占位值跳过解释
  lost-key         n_addr_rows_after  <  before，占位值解释不了 —— 需要单独交代（本轮应为 0）
  same             两者相等

用法：python3 analysis/grading-rerun-20261125/compare_e7.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from engine.split_addr import is_placeholder, roles_of  # noqa: E402

BEFORE = os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125", "coord-evidence.csv")
AFTER = os.path.join(ROOT, "analysis", "grading-rerun-20261125", "coord-evidence.csv")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
ASSIGN = os.path.join(ROOT, "analysis", "dialect-20261124", "dialect-assignment.csv")
OUT = os.path.join(ROOT, "analysis", "grading-rerun-20261125", "e7-before-after.csv")
COLS = ["layer_id", "url", "e7_before", "e7_after", "n_addr_rows_before", "n_addr_rows_after", "delta_kind"]


def layer_ids():
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(ASSIGN, encoding="utf-8")):
        out[r["url"]].append(r["layer_id"])
    return out


def placeholder_rows(roles):
    """每层样本里「至少一个角色字段是占位值」的行数 —— 占位跳过能解释的上界。"""
    import glob
    from engine.split_addr import _norm
    cnt = collections.Counter()
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r["layer_url"] or f"local:{r['layer_id']}"
            try:
                af = json.loads(r["addr_fields_json"] or "{}")
            except ValueError:
                continue
            if any((roles.get(_norm(k)) or ()) and is_placeholder(v) for k, v in af.items()):
                cnt[u] += 1
    return cnt


def main():
    old = {r["url"]: r for r in csv.DictReader(open(BEFORE, encoding="utf-8"))}
    new = {r["url"]: r for r in csv.DictReader(open(AFTER, encoding="utf-8"))}
    lmap = layer_ids()
    ph = placeholder_rows(roles_of())
    rows, kinds = [], collections.Counter()
    for u in sorted(set(old) | set(new)):
        a = int((old.get(u) or {}).get("n_addr_rows") or 0)
        b = int((new.get(u) or {}).get("n_addr_rows") or 0)
        if u not in new:
            kind = "lost-key"                 # 本轮没覆盖到该 url（不该发生，留证据）
        elif u not in old:
            kind = "gained-key"
        elif b > a:
            kind = "gained-key"
        elif b == a:
            kind = "same"
        elif ph.get(u, 0) >= (a - b):
            kind = "placeholder-skip"
        else:
            kind = "lost-key"
        kinds[kind] += 1
        rows.append({"layer_id": (lmap.get(u) or [""])[0], "url": u,
                     "e7_before": (old.get(u) or {}).get("e7", "unavailable·无 before"),
                     "e7_after": (new.get(u) or {}).get("e7", "unavailable·无 after"),
                     "n_addr_rows_before": a, "n_addr_rows_after": b, "delta_kind": kind})
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    e7flip = collections.Counter((r["e7_before"], r["e7_after"]) for r in rows)
    summary = {"urls": len(rows), "delta_kind": dict(kinds), "e7_flips": {f"{a}->{b}": n for (a, b), n in e7flip.items()},
               "addr_rows_before": sum(r["n_addr_rows_before"] for r in rows),
               "addr_rows_after": sum(r["n_addr_rows_after"] for r in rows),
               "before_csv": os.path.relpath(BEFORE, ROOT), "after_csv": os.path.relpath(AFTER, ROOT)}
    with open(os.path.join(ROOT, "analysis", "grading-rerun-20261125", "e7-before-after.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
