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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)


def _retry(fn, what, tries=3):
    """扫描类调用一律重试。

    ★ 2026-10-30 实测事故：Releases 扫到第 3 页失败 → 只认出 185 个 tag，剩下 100+ 个
      已采层被当成「没采过」→ 续跑会拿它们全量重采。计划阶段宁可直接失败，
      也不允许「扫不全 → 多采一遍」这种静默浪费（代价是几百小时带宽）。
    """
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            print("⚠ %s 第 %d/%d 次失败：%s" % (what, i + 1, tries, str(e)[:160]), file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-shards", type=int, default=250,
                    help="matrix job 上限 256，留余量")
    ap.add_argument("--force-layers", default="",
                    help="逗号分隔的层 id：**即使已判完成也强制重跑**（补 cancelled 片 / 口径差）")
    a = ap.parse_args()

    from worker_core import load_policy, select_layers   # noqa: E402
    pol = load_policy(a.stage)
    sel = dict(pol.get("select") or {})
    # 计划阶段必须做 skip_done（这是「不重采」的唯一开关）；layers 显式清单不算续采
    sel["skip_done"] = True
    try:
        layers = _retry(lambda: select_layers(a.stage, limit=0, policy=dict(pol, select=sel)),
                        "select_layers(%s)" % a.stage)
    except Exception as e:  # noqa: BLE001
        print("::error::扫 Releases 失败，拒绝「扫不全 → 当没采过」地盲切计划：%s" % str(e)[:200])
        return 4
    # ★ 已采判定要用**基础步**的 tag 命名空间（04b 复用 collect-step04-<layer> 的 tag），
    #   否则 04b 永远判「一层都没采过」→ 全量重采 320 层。
    base = str(pol.get("done_from") or a.stage)
    if base != a.stage:
        try:
            from worker_core import done_layers      # noqa: E402
            done = _retry(lambda: set(done_layers(base)), "done_layers(%s)" % base)
            b0 = len(layers)
            layers = [r for r in layers if r["id"] not in done]
            print("⏭ %s 已有 %d 层完成 → 待采 %d 层" % (base, b0 - len(layers), len(layers)))
        except Exception as e:  # noqa: BLE001
            # 扫不全就不许切计划：盲切的结果是把已采层重采一遍（几百小时带宽）
            print("::error::done_layers(%s) 连试 3 次都失败：%s" % (base, str(e)[:200]))
            return 4
    # ★ 强制重跑名单：done_layers 判「完成」只看 tag+checkpoint，可 cancelled 片里的层
    #   会留下「单元 done_units 标完成、产物没上传」或「计划期口径差」的半截状态 ——
    #   这类层若跟着 skip_done 走，缺口就永久钉死。所以允许显式点名强制重跑，
    #   并且排在**最前**（大层先起跑，早拿到新 checkpoint，不至于又撞 350 分钟上限）。
    forced = [x.strip() for x in a.force_layers.split(",") if x.strip()]
    if forced:
        have = {r["id"] for r in layers}
        try:
            univ_l = _retry(lambda: select_layers(
                a.stage, limit=0, policy=dict(pol, select=dict(sel, skip_done=False))),
                "select_layers(%s, 全量)" % a.stage)
        except Exception as e:  # noqa: BLE001
            print("::error::强制重跑名单无法核对（扫 Releases 失败）：%s" % str(e)[:200])
            return 4
        univ = {r["id"]: r for r in univ_l}
        add = [univ[i] for i in forced if i in univ and i not in have]
        unknown = [i for i in forced if i not in univ]
        if unknown:
            print("⚠️ 强制重跑名单里有 %d 层不在本步选层范围内（已忽略，不静默）：%s"
                  % (len(unknown), ", ".join(unknown[:5])), file=sys.stderr)
        layers = add + layers
        print("★ 强制重跑 %d 层（其中 %d 层原本被判完成）" % (len(add), len(add)))
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
            "forced_layers": forced, "shards": shards}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in plan.items() if k != "shards"}, ensure_ascii=False))
    if len(shards) > a.max_shards:
        print("::error::片数 %d 超过上限 %d" % (len(shards), a.max_shards), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
