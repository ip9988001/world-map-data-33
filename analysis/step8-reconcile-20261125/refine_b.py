#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · B 收尾：给 54 层原因表补 `conclusion_detail`（纯离线，不再探上游）。

四类 `conclusion` 保持不变（upstream_empty / upstream_offline / id_drifted / ledger_overclaimed），
但 `ledger_overclaimed` 里混着两种完全不同的情况，必须拆开说清（dispatch 明确要求：
「有 declared 却零资产的，必须写清是上游整层空、还是账本虚记」）：

  never_collected   上游 count 与账本 declared **相等**（±5%）→ 上游好好的、行数也对得上，
                    只是 Release 里根本没有该层的资产 → 采集任务从未执行（或被跳过）
  overclaimed       上游 count 明显 **小于** 账本 declared（>5%）→ 账本虚记
  understated       上游 count 明显 **大于** 账本 declared（>5%）→ 账本少记（采集期数据比现在少）
  no_declared       账本 declared 为空/0，但上游有数 → 账本没记，这次补上了实测

用法：python3 analysis/step8-reconcile-20261125/refine_b.py
"""
from __future__ import annotations

import collections
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def num(v):
    v = (v or "").strip()
    if v in ("", "None"):
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def main():
    p = os.path.join(HERE, "upstream-no-assets.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    detail = collections.Counter()
    for r in rows:
        dec, cnt = num(r["ledger_declared"]), num(r["upstream_count"])
        c = r["conclusion"]
        if c == "ledger_overclaimed":
            if not dec:
                d = "no_declared"
                tx = f"账本没有 declared，上游实测 count={cnt} → 账本没记，不是虚记"
            elif cnt is None:
                d = "probe_failed"
                tx = "上游 count 取不到，无法判虚记"
            elif abs(cnt - dec) <= 0.05 * max(dec, 1):
                d = "never_collected"
                tx = f"上游 count={cnt} 与账本 declared={dec} 一致（±5%）→ 上游健在、Release 无资产 = 采集从未执行/被跳过"
            elif dec > cnt:
                d = "overclaimed"
                tx = f"上游 count={cnt} < 账本 declared={dec}（差 {dec - cnt}）→ 账本虚记"
            else:
                d = "understated"
                tx = f"上游 count={cnt} > 账本 declared={dec}（差 {cnt - dec}）→ 账本少记"
        elif c == "upstream_offline":
            d = "declared_but_unreachable" if dec else "unreachable"
            tx = (f"账本有 declared={dec} 但上游实测拿不到（{r['upstream_err_raw'][:80]}）"
                  if dec else f"上游不可达（{r['upstream_err_raw'][:80]}）")
        elif c == "id_drifted":
            d = "count_differs"
            tx = f"上游 count={cnt} 与账本 declared={dec} 不符（同一 URL 两次快照不一致）"
        else:
            d = "empty"
            tx = "上游可达但 returnCountOnly=0"
        r["conclusion_detail"] = d
        r["conclusion_text"] = tx
        detail[d] += 1
    cols = list(rows[0].keys())
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    summary = {"rows": len(rows),
               "by_conclusion": dict(collections.Counter(r["conclusion"] for r in rows)),
               "by_conclusion_detail": dict(detail),
               "declared_positive": sum(1 for r in rows if (num(r["ledger_declared"]) or 0) > 0),
               "declared_zero": sum(1 for r in rows if num(r["ledger_declared"]) == 0),
               "declared_empty": sum(1 for r in rows if num(r["ledger_declared"]) is None)}
    json.dump(summary, open(os.path.join(HERE, "upstream-no-assets-summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
