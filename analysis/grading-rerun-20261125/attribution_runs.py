#!/usr/bin/env python3
"""①口径的贡献分解：把「拆串变化」拆成三段，逐段跑一遍（结果落 _work/，不进 git）。

三段（每段都在上一段之上加一层，其余判据一字不改）：
  A  占位跳过（impl 换成 engine.addr_key，角色表 = registry 一份，**不开拆串**）
  B  A + P1 拆串（engine.addr_key_split）
  C  B + engine 方言表并入角色表（registry ∪ engine/dialects/*.yaml）= 本轮正式口径

每段跑四段流水线：coord_evidence → auto_recognize → e7_refpool → tier_relax(--e3-relax on)。
变体靠**运行时替换** sandbox 模块的 addr_key / roles_of 实现（sandbox 生产代码里不加诊断开关）。

用法：python3 analysis/grading-rerun-20261125/attribution_runs.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import sandbox.auto_recognize as A                      # noqa: E402
import sandbox.coord_evidence as E                      # noqa: E402
import sandbox.e7_refpool as R                          # noqa: E402
import sandbox.tier_relax as T                          # noqa: E402
from engine.split_addr import addr_key, addr_key_split, roles_of as roles_union  # noqa: E402

WORK = os.path.join(ROOT, "analysis", "grading-rerun-20261125", "_work")
VARIANTS = {
    "A_placeholder_only": (addr_key, "registry"),
    "B_plus_split": (addr_key_split, "registry"),
    "C_plus_engine_roles": (addr_key_split, "union"),
}


def registry_only():
    return roles_union(engine_dir=os.path.join(WORK, "no_such_dir"))


def run(name):
    key_fn, roles_src = VARIANTS[name]
    # 运行时替换：coord_evidence 与 e7_refpool 两边同时换，保证两段口径一致
    for mod in (E, R):
        mod.addr_key = key_fn
        mod.roles_of = registry_only if roles_src == "registry" else roles_union
    out = os.path.join(WORK, name)
    os.makedirs(out, exist_ok=True)

    argv = sys.argv
    try:
        sys.argv = ["coord_evidence.py", "--outdir", out]
        E.main()
        sys.argv = ["auto_recognize.py", "--outdir", out]
        A.main()
        sys.argv = ["e7_refpool.py", "--outdir", out]
        R.main()
        sys.argv = ["tier_relax.py", "--strict", out, "--outdir", out, "--e3-relax", "on"]
        T.main()
    finally:
        sys.argv = argv
    with open(os.path.join(out, "summary.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    tiers = {k: v["layers"] for k, v in s["tiers"].items()}
    print(f"[{name}] tier1={tiers['tier1']} tier2={tiers['tier2']} tier3={tiers['tier3']} "
          f"rows={s['rows_total']} closed={s['checks']['tiers_closed']}")
    return {"variant": name, "tiers": tiers, "rows_total": s["rows_total"],
            "tier1_rows": s["tiers"]["tier1"]["rows"],
            "e7": s["e7"]["flips"], "checks": s["checks"]}


def main():
    res = [run(n) for n in VARIANTS]
    with open(os.path.join(ROOT, "analysis", "grading-rerun-20261125", "attribution.json"), "w",
              encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps([(r["variant"], r["tiers"]["tier1"]) for r in res], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
