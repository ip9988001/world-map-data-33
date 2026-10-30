#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量补采 · 计划器：把「本步还剩的层」切成片，写成 plan JSON（供 matrix 分片）。

选层口径 = steps.json 里该步的 select（skip_done=true 自动剔除已采层），
切片顺序 = policy 的 order（step04 按声明行数降序；05/07 升序；10 降序）。

用法：
  python3 collect/full_plan.py --stage 04 --size 20 --out collect/ledger/step04b_plan.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-shards", type=int, default=250,
                    help="matrix job 上限 256，留余量")
    a = ap.parse_args()

    from worker_core import load_policy, select_layers   # noqa: E402
    pol = load_policy(a.stage)
    sel = dict(pol.get("select") or {})
    # 计划阶段必须做 skip_done（这是「不重采」的唯一开关）；layers 显式清单不算续采
    sel["skip_done"] = True
    layers = select_layers(a.stage, limit=0, policy=dict(pol, select=sel))
    # ★ 已采判定要用**基础步**的 tag 命名空间（04b 复用 collect-step04-<layer> 的 tag），
    #   否则 04b 永远判「一层都没采过」→ 全量重采 320 层。
    base = str(pol.get("done_from") or a.stage)
    if base != a.stage:
        try:
            from worker_core import done_layers      # noqa: E402
            done = set(done_layers(base))
            b0 = len(layers)
            layers = [r for r in layers if r["id"] not in done]
            print("⏭ %s 已有 %d 层完成 → 待采 %d 层" % (base, b0 - len(layers), len(layers)))
        except Exception as e:  # noqa: BLE001
            print("⚠️ done_layers(%s) 失败：%s" % (base, str(e)[:100]))
    ids = [r["id"] for r in layers]
    shards = [{"shard": i // a.size, "layers": ids[i:i + a.size]}
              for i in range(0, len(ids), a.size)]
    rows_by_id = {r["id"]: (r.get("expect") or 0) for r in layers}
    plan = {"schema": "collect-plan/v1", "stage": a.stage, "size": a.size,
            "layers_n": len(ids), "shards_n": len(shards),
            "declared_rows": sum(rows_by_id.values()),
            "unit_rows": pol.get("unit_rows"), "workers": pol.get("workers"),
            "done_from": str(pol.get("done_from") or a.stage),
            "tag": pol.get("tag"), "order": sel.get("order"),
            "shards": shards}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in plan.items() if k != "shards"}, ensure_ascii=False))
    if len(shards) > a.max_shards:
        print("::error::片数 %d 超过上限 %d" % (len(shards), a.max_shards), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
