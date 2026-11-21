#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段账本「已完成层」筛查（rows 与 declared 自洽）—— 停片后对账用。

判定：status ∈ {ok, skipped_done} 且 |rows/declared − 1| ≤ tol（默认 0.5%）。
输出：① Markdown 表（给人看）② JSON 清单（给 merge / 后续阶段直接消费）。

用法:
  python3 collect/recon_rows_consistency.py --stage 05b
  python3 collect/recon_rows_consistency.py --stage 05b --tol 0.005 --limit 40
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan(ledger_path: str, tol: float) -> dict:
    d = json.load(open(ledger_path, encoding="utf-8"))
    done, short, other = [], [], []
    for r in (d.get("records") or []):
        try:
            dec = int(r.get("declared") or 0)
            rows = int(r.get("rows") or 0)
        except Exception:                                        # noqa: BLE001
            continue
        st = str(r.get("status") or "").lower()
        rec = {"layer": r.get("layer"), "status": st, "declared": dec, "rows": rows,
               "dev_pct": round(100.0 * (rows - dec) / dec, 4) if dec else None,
               "tag": r.get("tag") or ("collect-step07-" + str(r.get("layer")))}
        if st not in ("ok", "skipped_done"):
            other.append(rec)
            continue
        if dec <= 0:
            other.append(rec)
            continue
        if abs(rows - dec) <= dec * tol:
            done.append(rec)
        else:
            short.append(rec)
    return {"ledger": ledger_path, "stage": d.get("stage"), "tolerance_pct": tol * 100,
            "layers_n": d.get("layers_n"), "ok": d.get("ok"), "partial": d.get("partial"),
            "failed": d.get("failed"), "declared": d.get("declared"), "rows": d.get("rows"),
            "done": done, "short": short, "other": other,
            "done_rows": sum(x["rows"] for x in done),
            "done_declared": sum(x["declared"] for x in done)}


def render_md(res: dict, limit: int = 0) -> str:
    L = []
    L.append("# %s 已完成层筛查（rows 与 declared 自洽，容差 ±%.1f%%）\n" % (res["stage"], res["tolerance_pct"]))
    L.append("- 账本：`%s`" % os.path.relpath(res["ledger"], ROOT))
    L.append("- 账本总量：%s 层 / declared %s 行 / rows %s 行（ok %s / partial %s / failed %s）"
             % (res["layers_n"], f"{res['declared']:,}", f"{res['rows']:,}",
                res["ok"], res["partial"], res["failed"]))
    L.append("- **自洽完成层：%d 层 / %s 行**（declared 合计 %s，偏差 0 视为完全对齐）"
             % (len(res["done"]), f"{res['done_rows']:,}", f"{res['done_declared']:,}"))
    L.append("- 标 ok 但超容差（可疑）：%d 层；非 ok 状态：%d 层\n" % (len(res["short"]), len(res["other"])))
    rows = res["done"] if not limit else res["done"][:limit]
    L.append("| # | 层 | declared | rows | 偏差 | 判定 |")
    L.append("|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        L.append("| %d | `%s` | %s | %s | %+.3f%% | ok |"
                 % (i, r["layer"], f"{r['declared']:,}", f"{r['rows']:,}", r["dev_pct"] or 0.0))
    if limit and len(res["done"]) > limit:
        L.append("\n> 只列前 %d 层，全量见 JSON 清单。" % limit)
    if res["short"]:
        L.append("\n## 标 ok 但偏离容差（必须复采）\n")
        L.append("| 层 | declared | rows | 偏差 |")
        L.append("|---|---|---|---|")
        for r in res["short"][:50]:
            L.append("| `%s` | %s | %s | %+.3f%% |"
                     % (r["layer"], f"{r['declared']:,}", f"{r['rows']:,}", r["dev_pct"] or 0.0))
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="05b")
    ap.add_argument("--ledger", default="")
    ap.add_argument("--tol", type=float, default=0.005, help="相对偏差容差（0.005 = 0.5%%）")
    ap.add_argument("--docs", default="")
    ap.add_argument("--json-out", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    lp = a.ledger or os.path.join(ROOT, "collect", "%s_ledger.json" % a.stage)
    if not os.path.exists(lp):
        print("::error::账本不存在：%s" % lp)
        return 2
    res = scan(lp, a.tol)
    dp = a.docs or os.path.join(ROOT, "docs", "ng911-05b", "%s-done-layers.md" % a.stage)
    jp = a.json_out or os.path.join(ROOT, "collect", "_recon", "20261121", "%s-done-layers.json" % a.stage)
    os.makedirs(os.path.dirname(dp), exist_ok=True)
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    open(dp, "w", encoding="utf-8").write(render_md(res, a.limit))
    json.dump({"schema": "rows-consistency/v1", "stage": res["stage"],
               "tolerance_pct": res["tolerance_pct"],
               "source_ledger": os.path.relpath(lp, ROOT),
               "layers_n": res["layers_n"], "done_n": len(res["done"]),
               "done_rows": res["done_rows"], "done_declared": res["done_declared"],
               "short_n": len(res["short"]), "other_n": len(res["other"]),
               "done": res["done"], "short": res["short"]},
              open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"docs": os.path.relpath(dp, ROOT), "json": os.path.relpath(jp, ROOT),
                      "done_n": len(res["done"]), "done_rows": res["done_rows"],
                      "short_n": len(res["short"]), "other_n": len(res["other"])},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
