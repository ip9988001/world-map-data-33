#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段账本合并 —— 「单 run 账本不许覆盖阶段账本」。

## 为什么需要这个文件

2026-10-30 同一类事故发生了**两次**：`merge` job 把「本次 run 的分片账本汇总」直接写成
`collect/<stage>_ledger.json`。于是

- `41092912755`（04b round2，20 层）把 272 层的阶段账本冲成 20 层；
- `41121952357`（04b 定向补采，31 层）又把 272 层冲成 31 层（`shards_expected=3`）。

上一次只改了**历史文件名**（`04b_run41092912755.json`），写入逻辑一行没动 → 原地复发。
本文件是那行逻辑的替换：

  ① 单 run 的结果一律写 `collect/ledger/<stage>_run<RUN_ID>.json`（`scope=single_run`）；
  ② `collect/<stage>_ledger.json` 只做**按层合并**：以已有阶段账本为底，按 layer_id 覆盖/更新，
     状态取更优者（ok > partial > missing > unverified > empty > failed，同状态取行数大者）；
  ③ **硬保护**：本次 run 的 layers_n 小于阶段账本 layers_n 的 1/2 → 只写单 run 文件，
     不碰阶段文件（除非显式 allow_stage_overwrite=True）；
  ④ `revisions[]` 只追加不替换，每次 run 的增量与时间都留痕（同一 run_id 去重）。

状态优先级说明：`failed` 排在最后，所以「本次 run 把某层跑挂了」**不会**把阶段账本里
已有的 `ok/partial` 降级 —— 这正是 NAD-view 那层（checkpoint 被新切分覆盖）需要的保护。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

# 状态优先级：数值越大越「好」。未知状态按 0 处理（永远输给已知状态）。
STATUS_RANK = {
    "ok": 6,
    "partial": 5,
    "missing": 4,
    "unverified": 3,
    "empty": 2,
    "failed": 1,
}
COUNT_KEYS = ("ok", "partial", "missing", "unverified", "empty", "failed", "skipped_done")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def layer_key(rec: dict) -> str:
    return str(rec.get("layer") or rec.get("layer_id") or "")


def rank(status) -> int:
    return STATUS_RANK.get(str(status or "").lower(), 0)


def rows_of(rec: dict) -> int:
    try:
        return int(rec.get("rows") or 0)
    except (TypeError, ValueError):
        return 0


def pick_better(cur: dict, new: dict) -> tuple[dict, str]:
    """两层记录取「更优者」：状态优先，同状态取行数大者。返回 (winner, how)。"""
    rc, rn = rank(cur.get("status")), rank(new.get("status"))
    if rn > rc:
        return new, "new_status_better"
    if rn < rc:
        return cur, "keep_status_better"
    if rows_of(new) > rows_of(cur):
        return new, "new_more_rows"
    return cur, "keep_more_rows"


def merge_records(base_records, run_records):
    """按 layer_id 合并；返回 (merged_records, stats)。base 的顺序保留，新层追加在后。"""
    out = [dict(r) for r in (base_records or [])]
    idx = {layer_key(r): i for i, r in enumerate(out)}
    stats = {"added": 0, "updated": 0, "kept": 0, "downgrade_blocked": []}
    for r in (run_records or []):
        k = layer_key(r)
        if not k:
            continue
        if k not in idx:
            idx[k] = len(out)
            out.append(dict(r))
            stats["added"] += 1
            continue
        cur = out[idx[k]]
        win, how = pick_better(cur, r)
        if win is r:
            out[idx[k]] = dict(r)
            stats["updated"] += 1
        else:
            stats["kept"] += 1
            if rank(r.get("status")) < rank(cur.get("status")):
                stats["downgrade_blocked"].append(
                    {"layer": k, "stage_status": cur.get("status"), "run_status": r.get("status")})
    return out, stats


def recount(records):
    """按合并后的逐层记录重算顶层计数（不信任任何一方自报的数字）。"""
    cnt = {k: 0 for k in COUNT_KEYS}
    declared = rows = 0
    for r in records:
        st = str(r.get("status") or "").lower()
        if st in cnt:
            cnt[st] += 1
        declared += int(r.get("declared") or 0)
        rows += rows_of(r)
    cnt["declared"] = declared
    cnt["rows"] = rows
    cnt["gap"] = declared - rows
    cnt["gap_pct"] = round(100.0 * (declared - rows) / declared, 4) if declared else None
    cnt["layers_n"] = len(records)
    return cnt


def stage_overwrite_allowed(run_layers: int, stage_layers: int, allow: bool = False) -> tuple[bool, str]:
    """硬保护：小 run 不许覆盖大阶段账本。"""
    if allow:
        return True, "explicit_allow"
    if not stage_layers:
        return True, "no_stage_ledger_yet"
    if run_layers * 2 < stage_layers:
        return False, "run_layers_%d_lt_half_of_stage_%d" % (run_layers, stage_layers)
    return True, "run_big_enough"


def merge_stage_ledger(stage: str, base: dict | None, run_led: dict, run_id: str,
                       at: str | None = None, note: str = "") -> tuple[dict, dict]:
    """返回 (merged_stage_ledger, stats)。base 为空时等价于「首次建账」。"""
    at = at or _now()
    base = dict(base or {})
    merged_recs, stats = merge_records(base.get("records") or [], run_led.get("records") or [])
    cnt = recount(merged_recs)
    out = dict(base)                       # 保留阶段的额外字段（buckets/source_of_truth/...）
    out.update({
        "schema": base.get("schema") or "collect-ledger-agg/v1",
        "stage": stage,
        "at": at,
        "scope": "stage",
        "layers_n": cnt["layers_n"],
        "declared": cnt["declared"],
        "rows": cnt["rows"],
        "gap": cnt["gap"],
        "gap_pct": cnt["gap_pct"],
        "records": merged_recs,
        "last_merge": {"run_id": run_id, "at": at, "stats": stats},
    })
    for k in COUNT_KEYS:
        out[k] = cnt[k]
    # 片口径四件套是**本轮 run 的**（闸门读它判「本轮有没有片没跑完」），
    # 所以每次合并都改成最新 run 的值，并用 shards_run_id 标明是哪一轮的口径；
    # 想查历史片完成度看 revisions[]（只追加不替换）。
    for k in ("shards_expected", "shards_reported", "shards_incomplete",
              "shards_incomplete_detail"):
        out[k] = run_led.get(k)
    out["shards_run_id"] = str(run_id)
    # 「阶段是否收官」按合并后的逐层状态判，不看某一 run 的片数
    # 「阶段是否收官」只看合并后的逐层状态：必须有层、且没有 partial/missing/unverified/empty 之外的坏状态。
    # 不看某一 run 的片数（片口径记在 last_merge / revisions 里），否则一次缺片就永久把阶段判成未完成；
    # 但「一层都没记到」时必须判未完成（全片被 cancel 的情形）。
    bad = [r for r in merged_recs
           if str(r.get("status") or "").lower() not in ("ok", "empty", "skipped_done")]
    out["complete"] = bool(merged_recs) and (not bad) and cnt["failed"] == 0
    out["buckets"] = {k: cnt[k] for k in COUNT_KEYS if k != "skipped_done"}

    revs = list(base.get("revisions") or [])
    entry = {
        "kind": "stage_merge",
        "at": at,
        "run_id": str(run_id),
        "run_layers_n": run_led.get("layers_n"),
        "run_shards_expected": run_led.get("shards_expected"),
        "run_shards_reported": run_led.get("shards_reported"),
        "run_shards_incomplete": run_led.get("shards_incomplete"),
        "run_ok": run_led.get("ok"), "run_failed": run_led.get("failed"),
        "run_rows": run_led.get("rows"),
        "stage_layers_before": base.get("layers_n"), "stage_layers_after": cnt["layers_n"],
        "records_added": stats["added"], "records_updated": stats["updated"],
        "records_kept": stats["kept"],
        "downgrades_blocked": len(stats["downgrade_blocked"]),
        "note": note or "单 run 结果按层合并进阶段账本（状态取更优者，同状态取行数大者）",
    }
    # 同一 run_id 只留最新一条（重跑同 run 不重复记账）
    revs = [r for r in revs if not (r.get("kind") == "stage_merge" and str(r.get("run_id")) == str(run_id))]
    revs.append(entry)
    out["revisions"] = revs
    return out, stats


def write_run_and_stage(stage: str, run_led: dict, run_id: str, base_dir: str,
                        allow_stage_overwrite: bool = False, note: str = "") -> dict:
    """写单 run 账本（总是）+ 合并阶段账本（受硬保护）。返回可打印的摘要。"""
    at = _now()
    os.makedirs(os.path.join(base_dir, "ledger"), exist_ok=True)
    run_led = dict(run_led, scope="single_run", run_id=str(run_id), at=at)
    run_path = os.path.join(base_dir, "ledger", "%s_run%s.json" % (stage, run_id))
    json.dump(run_led, open(run_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    stage_path = os.path.join(base_dir, "%s_ledger.json" % stage)
    base = None
    if os.path.exists(stage_path):
        try:
            base = json.load(open(stage_path, encoding="utf-8"))
        except Exception:                                   # noqa: BLE001
            base = None
    run_layers = int(run_led.get("layers_n") or 0)
    stage_layers = int((base or {}).get("layers_n") or 0)
    ok, why = stage_overwrite_allowed(run_layers, stage_layers, allow_stage_overwrite)
    res = {"run_path": run_path, "stage_path": stage_path, "run_layers_n": run_layers,
           "stage_layers_before": stage_layers, "stage_written": False, "reason": why}
    if not ok:
        res["note"] = ("单 run 只有 %d 层，小于阶段账本 %d 层的 1/2 → 只写单 run 文件，"
                       "阶段账本不动（要覆盖请显式 --allow-stage-overwrite）" % (run_layers, stage_layers))
        return res
    merged, stats = merge_stage_ledger(stage, base, run_led, run_id, at=at, note=note)
    json.dump(merged, open(stage_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    res.update({"stage_written": True, "stage_layers_after": merged["layers_n"],
                "stage_ok": merged["ok"], "stage_partial": merged["partial"],
                "stage_failed": merged["failed"], "stage_complete": merged["complete"],
                "stats": stats})
    return res
