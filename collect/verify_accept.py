#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""accept 判据比对器 —— **只陈述事实，不判合格**。

为什么要有它：2026-10-28 核查发现 metrics 只写不读，accept 判据没有任何消费者，
等于「验收数字落盘了但没人看」。本工具补上消费端。

铁律（对齐 L0 第 1 条）：本工具只输出「实测值 vs 判据阈值」的事实算式，
**终判权仍归大脑**。所以最后一行是 SATISFIED / VIOLATE 的键名清单，不是 pass/fail。
"""
from __future__ import annotations
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S_F = os.path.join(ROOT, "collect", "state.json")
C_F = os.path.join(ROOT, "collect", "steps.json")

# accept 键 -> metrics 键 的别名（判据卡用「对象_方向」，账本用实测名）
ALIAS = {
    "plan_rows": "rows", "plan_empty": "plan_empty", "with_rows": "with_rows",
    "diff": "worst_diff", "done_rate": "done_rate", "failed_rate": "failed_rate",
    "states": "states", "per_layer_rows": "per_layer_rows", "eff": "eff",
    "pick_layers": "pick_layers", "budget_min": "budget_min",
}

def main() -> int:
    st = json.load(open(S_F, encoding="utf-8"))
    cfg = json.load(open(C_F, encoding="utf-8"))
    steps = sys.argv[1:] or sorted(cfg.get("steps") or {})
    bad = 0
    for k in steps:
        prof = (cfg.get("steps") or {}).get(k) or {}
        acc = prof.get("accept") or {}
        met = ((st.get("steps") or {}).get(k) or {}).get("metrics") or {}
        print(f"\n=== STEP {k} {prof.get('title','')} ===")
        if not acc:
            print("  该步无 accept 判据（无从比对）"); continue
        if not met:
            print("  ❌ 无 metrics（证据缺失，不可比对）"); bad += 1; continue
        viol = []
        for key, thr in acc.items():
            m = re.search(r"_(min|max)$", key)
            base = key[: m.start()] if m else key
            val = met.get(ALIAS.get(base, base), met.get(key))
            if val is None:
                print(f"  ⚠️ {key:<18} 判据={thr:<10} 实测=缺  → 无据可比")
                viol.append(base); continue
            if m and m.group(1) == "min":
                ok = val >= thr; op = "≥"
            elif m and m.group(1) == "max":
                ok = val <= thr; op = "≤"
            else:
                ok = val == thr; op = "="
            flag = "✅" if ok else "❌"
            print(f"  {flag} {key:<18} 判据 {op} {thr:<10} 实测 {val}")
            if not ok:
                viol.append(key)
        bad += bool(viol)
    print("\n" + ("SATISFIED：全部判据有据且满足" if not bad else f"VIOLATE：{bad} 步存在不满足/无据（终判归大脑）"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
