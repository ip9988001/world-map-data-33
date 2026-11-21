#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D15「本轮计划内层豁免」正/反例夹具（离线、可复跑、不碰账本、不碰网络、不起 run）。

W33-046（muse-000134 决定④）要求三条并存：
  a. 无 force                 → 3 层照旧 FAIL（门禁没被削弱）
  b. 3 层全在 force           → PASS，且 detail 明列「豁免 3 层：层名 rows/expect 缺x%」
  c. force 只放 1 层          → 那层豁免，另 2 层仍 FAIL
  +  一个不在 force 里的短层   → 不管名单多长，它照样 FAIL（反例，最关键）

为什么不直接跑 `preflight_dispatch.py`：它会读**真账本**（collect/05b_ledger.json，红线不许动）
并打网络项。本夹具只把 D15 这一项拿出来，用临时账本跑；退出码按 preflight main() 的同一条
规则映射（任一 FAIL → 1）。

用法：python3 collect/tests/fixture_d15_plan_exempt.py
退出码：0 = a/b/c 与反例全部符合预期；2 = 与预期不符（豁免把门禁废了 → 停手、不许合）
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import preflight_dispatch as pf  # noqa: E402

# run 44882397022 · preflight D15 报警三层（账本真值：layer / rows / declared）
SHORT3 = [
    ("arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0", 39504, 39751),
    ("cgis_rest_services_911_Addresses_Public_View_FeatureServer_2", 81437, 81772),
    ("qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0", 181529, 181750),
]
# 反例专用：不在本轮 force 名单里的已采短层（缺 10%，远超 0.1% 容差）
GHOST = ("ghost_not_in_force_arcgis_FeatureServer_0", 900, 1000)


def _ledger(rows):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"schema": "collect-ledger/v1", "stage": "05b", "layers_n": len(rows),
                   "records": [{"layer": l, "status": "ok", "rows": r, "declared": d}
                               for l, r, d in rows]}, f)
    return p


def _run(tag, rows, force, want):
    lp = _ledger(rows)
    try:
        it = pf.judge_rows_vs_expect("05b", lp, "", exempt_layers=force)
    finally:
        os.unlink(lp)
    rc = 1 if it["status"] == "FAIL" else 0        # 与 preflight main() 同一映射
    got = (it["status"], rc,
           sorted(b["layer"] for b in it["short_ok_status"]),
           sorted(b["layer"] for b in it["exempt_in_plan"]))
    ok = got == want
    print("[%s] D15=%s → preflight exit=%d %s" % (tag, it["status"], rc, "✅" if ok else "❌ 与预期不符"))
    print("      detail: %s" % it["detail"])
    if it.get("exempt_in_plan"):
        print("      exempt_in_plan(JSON): %s" % json.dumps(
            [{k: x[k] for k in ("layer", "rows", "declared", "denominator", "gap_pct")}
             for x in it["exempt_in_plan"]], ensure_ascii=False))
    if it.get("short_ok_status"):
        print("      仍报警: %s" % ", ".join("%s %d/%d 缺%.2f%%"
                                          % (b["layer"], b["rows"], b["declared"], b["gap_pct"])
                                          for b in it["short_ok_status"]))
    return ok


def main() -> int:
    l3 = [l for l, _, _ in SHORT3]
    cases = [
        ("a·无 force", list(SHORT3), [], ("FAIL", 1, l3, [])),
        ("b·三层全在 force", list(SHORT3), l3, ("PASS", 0, [], l3)),
        ("c·force 只放 1 层", list(SHORT3), [l3[0]],
         ("FAIL", 1, sorted(l3[1:]), [l3[0]])),
        ("反例·短层不在 force 里", list(SHORT3) + [GHOST], l3,
         ("FAIL", 1, [GHOST[0]], l3)),
    ]
    oks = [_run(*c) for c in cases]
    good = all(oks)
    print("\n结论：%s" % ("✅ a/b/c 与反例全部符合预期 —— 门禁还活着" if good
                       else "❌ 有用例与预期不符（豁免可能把门禁废了）→ 停手，不许合"))
    return 0 if good else 2


if __name__ == "__main__":
    raise SystemExit(main())
