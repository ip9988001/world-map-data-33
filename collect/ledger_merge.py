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
  ② `collect/<stage>_ledger.json` 只做**按层并集合并**：以已有阶段账本为底，按 layer_id 覆盖/更新，
     状态取更优者（ok > partial > missing > unverified > empty > failed，同状态取行数大者）；
  ③ **硬保护（2026-11-22 W33-059 改）**：并集合并只增不减，所以不再用「run < 阶段账本 1/2」这种
     体积判据拦小 run ——那会把**所有增量轮次永久挡在门外**（run 44960026303：1426 层 vs 3304 层，
     2852 < 3304 → 拒写，3 层 status=ok 的新记录一行没进聚合账本）。现在只拦「本 run 一条记录都没有」，
     并用两条**不变量**兑底：合并后「阶段账本原有层 ∪ 本轮分片层」一个不许丢（`assert_merge_covers`，
     不满足**直接 raise**）+ 逐层 rows 不许变小（`ckpt_guard`，无实证拒写）；
  ④ `revisions[]` 只追加不替换，每次 run 的增量与时间都留痕（同一 run_id 去重）。

状态优先级说明：`failed` 排在最后，所以「本次 run 把某层跑挂了」**不会**把阶段账本里
已有的 `ok/partial` 降级 —— 这正是 NAD-view 那层（checkpoint 被新切分覆盖）需要的保护。

⑤ **rows 回退不许静默**（2026-10-31 补）：状态优先级 + 取行数大者是「保住进展」的规则，
   副作用是**真丢数据会被永久掩盖** —— 阶段账本里那一层的 rows 从此停在旧值，没人知道
   这次 run 实测只采到更少的行。所以合并时逐层比较 rows：只要 `本次 run rows < 阶段账本 rows`
   就写一条 `regressions[]`（层 / 旧 rows / 新 rows / 差值 / 原因 / 证据路径 / 合并怎么处置），
   并在人读摘要里单独成节。**记录 ≠ 拦截**：能证明是「口径变了/上游真删了」的，把证据路径
   挂到 run 账本的 `row_shrink_evidence: {<layer>: <path>}`（或逐层记录 `regression_reason`）；
   没有证据的回退一律当事故追。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

# 状态优先级：数值越大越「好」。未知状态按 0 处理（永远输给已知状态）。
# capped_by_upstream（2026-10-31 起）= 上游改成服务级 token，本层已尽取：它比 partial 好
#   （partial 还会被续采改写，capped 不会），但比 ok 差（没有可复核的声明）。
#   排序必须让它稳定胜出，否则一次重跑就能把 capped 层降级成 partial/failed。
# 状态优先级：合并两本账时取「更优」的那个（数字越大越优）。
# ★ upstream_unstable（2026-10-31 用户立规）排在 partial **之后**、missing **之前**：
#   「可连通但连续 N 次超时/503/非 JSON、无进展」比「上游有数但未排上」（missing）
#   更接近终结态（已经试过了），但比「半截已采」（partial）差（人家至少采了一部分）。
#   重新编号是故意的：原来一套是 7..1，插一个进去会重叠，rank 只能用浮点或重排；
#   重排更安全（没有浮点比较、也没有两个状态同 rank）。
STATUS_RANK = {
    "ok": 8,
    "capped_by_upstream": 7,
    "partial": 6,
    "upstream_unstable": 5,
    "missing": 4,
    "unverified": 3,
    "empty": 2,
    "failed": 1,
}
COUNT_KEYS = ("ok", "capped_by_upstream", "partial", "upstream_unstable", "missing",
              "unverified", "empty", "failed", "skipped_done")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MergeInvariantError(ValueError):
    """合并不变量被破坏（丢层）。带上 `detail` 供调用方打出可核对的清单。"""


# `@<state>-<n>` 变体后缀（与 worker_core.VAR_SUFFIX_RE 同构；不 import worker_core：
# 它 import 时会读 collect/steps.json，账本合并不该被那个副作用绑住）。
VAR_SUFFIX_RE = re.compile(r"^(?P<base>.+)@(?P<state>[^@]+)-(?P<n>\d+)$")


def norm_layer(lid: str) -> str:
    """层 id 归一：`xxx@未定位-2` → `xxx`（其余原样）。"""
    m = VAR_SUFFIX_RE.match(lid or "")
    return m.group("base") if m else (lid or "")


def layer_key(rec: dict) -> str:
    return str(rec.get("layer") or rec.get("layer_id") or "")


def rank(status) -> int:
    return STATUS_RANK.get(str(status or "").lower(), 0)


def rows_of(rec: dict) -> int:
    try:
        return int(rec.get("rows") or 0)
    except (TypeError, ValueError):
        return 0


def _shrink_evidence(rec: dict, run_led: dict, key: str) -> str:
    """取这一层的回退证据路径：逐层字段优先，其次 run 账本的 row_shrink_evidence 表。"""
    for field in ("regression_evidence", "rows_evidence", "evidence"):
        v = rec.get(field)
        if v:
            return str(v)
    table = (run_led or {}).get("row_shrink_evidence")
    if isinstance(table, dict) and table.get(key):
        return str(table[key])
    return ""


def _shrink_reason(rec: dict, run_led: dict, key: str, outcome: str) -> str:
    for field in ("regression_reason", "shrink_reason"):
        v = rec.get(field)
        if v:
            return str(v)
    table = (run_led or {}).get("row_shrink_reason")
    if isinstance(table, dict) and table.get(key):
        return str(table[key])
    return {
        "took_run_record_status_better": "状态变好但行数变少（合并取了本轮记录）",
        "kept_stage_record_more_rows": "同状态行数变少（合并保留了更大的旧值）",
        "kept_stage_record_status_better": "状态变差且行数变少（合并保留了旧记录）",
    }.get(outcome, outcome)


def row_regressions(base_records, run_records, run_led: dict | None = None,
                    run_id: str = "", at: str = "") -> list:
    """逐层比 rows：本轮 run < 阶段账本 → 一条回退记录（**不静默**）。"""
    base = {layer_key(r): r for r in (base_records or []) if layer_key(r)}
    out = []
    for r in (run_records or []):
        k = layer_key(r)
        cur = base.get(k)
        if not cur:
            continue
        stage_rows, run_rows = rows_of(cur), rows_of(r)
        if run_rows >= stage_rows:
            continue
        sb, sn = cur.get("status"), r.get("status")
        if rank(sn) > rank(sb):
            outcome = "took_run_record_status_better"
        elif rank(sn) == rank(sb):
            outcome = "kept_stage_record_more_rows"
        else:
            outcome = "kept_stage_record_status_better"
        out.append({
            "layer": k,
            "run_id": str(run_id),
            "at": at,
            "stage_rows": stage_rows,
            "run_rows": run_rows,
            "delta": run_rows - stage_rows,
            "stage_status": sb,
            "run_status": sn,
            "merge_outcome": outcome,
            "reason": _shrink_reason(r, run_led or {}, k, outcome),
            "evidence": _shrink_evidence(r, run_led or {}, k),
        })
    return out


def format_regressions_section(regressions, limit: int = 30) -> list:
    """人读摘要里的「rows 回退」一节（markdown 行）。"""
    regs = list(regressions or [])
    if not regs:
        return []
    unexplained = [e for e in regs if not e.get("evidence")]
    by_outcome = {}
    for e in regs:
        k = str(e.get("merge_outcome") or "?")
        by_outcome[k] = by_outcome.get(k, 0) + 1
    L = ["检测到 **%d** 层 rows 回退（其中 %d 层没有证据路径）。" % (len(regs), len(unexplained)),
         "",
         "处置分布（只有 `took_run_record_status_better` 是真的把阶段账本 rows 改小了；"
         "另两类是合并挡住了降级、账本 rows 没变，但本轮确实少采了）："
         + "；".join("`%s` %d 层" % (k, v) for k, v in sorted(by_outcome.items())),
         "",
         "| 层 | 旧 rows | 新 rows | 差额 | 状态 旧→新 | 合并处置 | 原因 | 证据 |",
         "|---|---|---|---|---|---|---|---|"]
    for e in regs[:limit]:
        L.append("| `%s` | %s | %s | %s | %s→%s | %s | %s | %s |" % (
            e.get("layer"), f"{e.get('stage_rows'):,}" if isinstance(e.get("stage_rows"), int) else e.get("stage_rows"),
            f"{e.get('run_rows'):,}" if isinstance(e.get("run_rows"), int) else e.get("run_rows"),
            "{:+,}".format(e.get("delta", 0)),
            e.get("stage_status"), e.get("run_status"),
            e.get("merge_outcome"), e.get("reason") or "-",
            ("`%s`" % e.get("evidence")) if e.get("evidence") else "**缺**"))
    if len(regs) > limit:
        L.append("| … | | | | | | 另 %d 层见 `regressions[]` | |" % (len(regs) - limit))
    return L


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
    """按合并后的逐层记录重算顶层计数（不信任任何一方自报的数字）。

    ★ 分母口径（2026-10-31）：`capped_by_upstream` 层的 `declared` 是 None（另记
      `declared_unverifiable`）。所以这里的 gap 必须与 `adjudicate_04b` 一致：
      `gap = declared − (rows − rows_capped)`，否则分子含 capped 行数、分母不含它的声明，
      会算出个负数缺口，看着像「超采」，其实是两只脚踩在两只船上。
    """
    cnt = {k: 0 for k in COUNT_KEYS}
    declared = rows = rows_capped = declared_unver = rows_dup = 0
    for r in records:
        st = str(r.get("status") or "").lower()
        if st in cnt:
            cnt[st] += 1
        declared += int(r.get("declared") or 0)
        rows += rows_of(r)
        # 分区重复采样（同源重复）与 rows_duplicate[] 的估算行：都在 rows 里，但**不进**可核实分子。
        # 不扣就会让覆盖率虚高 —— 与 adjudicate_04b 的口径必须完全一致。
        rows_dup += int(r.get("rows_partition_duplicate_est") or 0) or (
            rows_of(r) if r.get("partition_duplicate_sampled") else 0)
        if st == "capped_by_upstream":
            rows_capped += rows_of(r)
            declared_unver += int(r.get("declared_unverifiable") or 0)
    cnt["declared"] = declared
    cnt["declared_unverifiable"] = declared_unver
    cnt["rows"] = rows
    cnt["rows_capped"] = rows_capped
    cnt["rows_with_partition_dup"] = rows_dup
    cnt["rows_verifiable"] = rows - rows_capped - rows_dup
    cnt["gap"] = declared - (rows - rows_capped - rows_dup)
    cnt["gap_pct"] = (round(100.0 * (declared - (rows - rows_capped - rows_dup)) / declared, 4)
                      if declared else None)
    cnt["layers_n"] = len(records)
    return cnt


SUSPECT_RATIO_LO, SUSPECT_RATIO_HI = 1.9, 2.1


def annotate_rows_suspect(records, *, at: str | None = None, run_id="") -> tuple[list, dict | None]:
    """给「跨代际两代行都被计入」的层打**留档标记**（★ 一个字都不改 rows）。

    ★ 2026-11-22 W33-060（用户裁定「改底账比留错数更糟」）：
      已入库的那批虚高 rows **不回改**，只在记录上加
        `rows_suspect: "legacy_double_count"` + `rows_legacy_kept: rows - declared`
      并留 `rows_suspect_note`。新一轮采完自然覆盖；在此之前任何读账本的人都能看见
      「这层的行数是可疑的、多出来多少」，而不是被静默吞掉。

    判据只用账本自身的算术（`rows/declared ∈ [1.9, 2.1]`），不做上游调用：
      · 双算的签名就是 2.0×（旧代际一整份 + 新代际一整份），实测 101 层全落在这个区间，
        且各层 `rows - declared` 之和 = 7,359,939 ≈ 仿真的 legacy_kept 合计；
      · 上游正常漂移（几百行）的层不会被误标 —— 它们进不了 1.9 档。
    标记是**幂等**的：重复调用不会改变结果，也不会叠加计数。
    """
    at = at or _now()
    out, hit, extra = [], [], 0
    for r in (records or []):
        rr = dict(r)
        declared = int(rr.get("declared") or 0)
        rows = rows_of(rr)
        if declared > 0 and SUSPECT_RATIO_LO <= rows / float(declared) <= SUSPECT_RATIO_HI:
            keep = rows - declared
            rr["rows_suspect"] = "legacy_double_count"
            rr["rows_legacy_kept"] = keep
            rr["rows_suspect_note"] = (
                "旧代际（无 r<hash> 前缀的单元包）+ 新代际两代行都被计入 → %s 行是上一代副本。"
                "rows 字段按用户裁定**不回改**（改底账比留错数更糟），由 W33-060 supersede 修法"
                "在下一轮采集后自然覆盖。" % f"{keep:,}")
            hit.append(rr.get("layer"))
            extra += keep
        elif rr.get("rows_suspect") == "legacy_double_count" and not (
                declared > 0 and SUSPECT_RATIO_LO <= rows / float(declared) <= SUSPECT_RATIO_HI):
            # 已经不再双算（新一轮采完/被 supersede）→ 摘掉标记，别留下过期的指控
            for k in ("rows_suspect", "rows_legacy_kept", "rows_suspect_note"):
                rr.pop(k, None)
        out.append(rr)
    if not hit:
        return out, None
    return out, {
        "kind": "legacy_double_count",
        "layers": len(hit),
        "overcounted_rows": extra,
        "detected_at": at,
        "detected_by": "ledger_merge.annotate_rows_suspect (W33-060)",
        "run_id": str(run_id) if run_id else None,
        "policy": "rows 不回改，只加标记留档（用户裁定 2026-11-22）",
        "fix": "W33-060：merge_checkpoints 对「旧 unit 索引 ⊆ 新」的旧包标 superseded_by、"
               "counted_rows=0；旧 ⊋ 新 的多出单元照计（唯一副本）",
        "note": "下一轮采集/合并后这些层会自然回到单代行数，届时本标记会被摘掉",
    }


def stage_overwrite_allowed(run_layers: int, stage_layers: int, allow: bool = False) -> tuple[bool, str]:
    """阶段账本能不能被本 run 合并（W33-059，2026-11-22 修）。

    ★ 旧判据「run 层数 < 阶段账本 1/2 → 拒写」把**增量轮次永久挡在门外**。
      实测 run 44960026303：run 1426 层、阶段账本 3304 层 → 2852 < 3304 → 拒写，
      于是 3 层 status=ok 的新记录一行没进 `collect/05b_ledger.json`（数据在 run 账本里，
      聚合账本却停在上一轮，闸门还读到上一轮的 shards_incomplete=[2]）。

      1/2 判据是给「覆盖式写入」设计的；而 `merge_stage_ledger` 是**按层并集**，
      永远只增不减（不可能把 3304 层写少）。真正的护栏另有两条且都在：
        ① 并集后**两侧的层一个都不许消失**（`assert_merge_covers`，失败直接 raise）；
        ② 任何一层 rows 不许变小（`ckpt_guard.guard_ledger_rows`，无实证直接拒写）。
      所以这里只拦「本 run 一行记录都没有」这种空转，其余一律允许合并。
    """
    if allow:
        return True, "explicit_allow"
    if not stage_layers:
        return True, "no_stage_ledger_yet"
    if not run_layers:
        return False, "run_has_no_records"
    return True, "union_merge_run_%d_stage_%d" % (run_layers, stage_layers)


def assert_no_layer_lost(base_records, merged_records):
    """并集合并的硬后置条件（旧名，保留兼容）：阶段账本原有的层一个不许消失。"""
    return assert_merge_covers(base_records, [], merged_records)


def assert_merge_covers(base_records, run_records, merged_records):
    """★ 硬后置条件（W33-059）：合并结果必须**覆盖两侧的层集合**，不满足直接 raise。

    校验两件事（按 base id 归一后比，见 `norm_layer`）：
      ① 阶段账本原有的层一个没丢（并集合并不该丢层）；
      ② **本轮分片 records 里的层全部进去了** —— 这正是 run 44960026303 丢的那个东西：
         3 层 status=ok 在 run 账本里、却不在聚合账本里（旧逻辑直接把整次合并跳过了）。

    为什么“归一”：W33-048 起 `@<state>-<n>` 变体在采集侧就归并成一个 base id
    （`worker_core.merge_layer_variants`），所以 base 里可能还留着旧变体 id（`xxx@未定位-2`），
    而本轮写的是 base id（`xxx`）——两边归一后才能公平比对。

    不满足时抛 `MergeInvariantError`（`write_run_and_stage` **不捕获**，让它冒到调用方非零退出），
    而不是打 warning 了事：丢层是 bug，不是提示。
    """
    merged = {norm_layer(layer_key(r)) for r in (merged_records or []) if layer_key(r)}
    lost_base = sorted({norm_layer(layer_key(r)) for r in (base_records or []) if layer_key(r)}
                       - merged)
    lost_run = sorted({norm_layer(layer_key(r)) for r in (run_records or []) if layer_key(r)}
                      - merged)
    if lost_base or lost_run:
        e = MergeInvariantError(
            "合并后丢层：阶段账本丢 %d 层、本轮分片丢 %d 层（并集合并不该丢层）：%s"
            % (len(lost_base), len(lost_run), ", ".join((lost_base + lost_run)[:5])))
        e.detail = {"lost_from_stage": lost_base, "lost_from_run": lost_run}  # type: ignore[attr-defined]
        raise e
    return True


def merge_stage_ledger(stage: str, base: dict | None, run_led: dict, run_id: str,
                       at: str | None = None, note: str = "") -> tuple[dict, dict]:
    """返回 (merged_stage_ledger, stats)。base 为空时等价于「首次建账」。"""
    at = at or _now()
    base = dict(base or {})
    merged_recs, stats = merge_records(base.get("records") or [], run_led.get("records") or [])
    # ★ W33-060：合并后重新打「跨代际双算」留档标记（base 里带的旧标记若已不再双算会被摘掉）
    merged_recs, suspect = annotate_rows_suspect(merged_recs, at=at, run_id=run_id)
    cnt = recount(merged_recs)
    # ★ rows 回退：合并前先逐层比一次（取更优者会把它掩盖掉，必须先记下来）
    regs_new = row_regressions(base.get("records") or [], run_led.get("records") or [],
                              run_led, run_id, at)
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
    if suspect:
        out["rows_suspect"] = suspect
    else:
        out.pop("rows_suspect", None)
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

    # regressions[] 只追加不替换；同一 (层, run) 重跑不再重复记（留最新一条）
    regs_prev = list(base.get("regressions") or [])
    new_keys = {(str(e.get("layer")), str(e.get("run_id"))) for e in regs_new}
    merged_regs = [e for e in regs_prev
                   if (str(e.get("layer")), str(e.get("run_id"))) not in new_keys] + regs_new
    out["regressions"] = merged_regs
    out["rows_regressions"] = len(merged_regs)
    out["rows_regressions_unexplained"] = len([e for e in merged_regs if not e.get("evidence")])

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
        "rows_regressions": len(regs_new),
        "rows_regressions_layers": [e["layer"] for e in regs_new],
        "note": note or "单 run 结果按层合并进阶段账本（状态取更优者，同状态取行数大者）",
    }
    # 同一 run_id 只留最新一条（重跑同 run 不重复记账）
    revs = [r for r in revs if not (r.get("kind") == "stage_merge" and str(r.get("run_id")) == str(run_id))]
    revs.append(entry)
    out["revisions"] = revs
    return out, stats


def write_run_and_stage(stage: str, run_led: dict, run_id: str, base_dir: str,
                        allow_stage_overwrite: bool = False, note: str = "",
                        allow_shrink: dict | None = None) -> dict:
    """写单 run 账本（总是）+ 合并阶段账本（受硬保护）。返回可打印的摘要。

    ★ 额外的总闸门（`collect/ckpt_guard.py`）：**任何一层 rows 都不得变小**。
      变小必须带 `regression_reason` + 证据路径（`allow_shrink={layer: evidence_path}`），
      否则阶段账本不写、返回 `error`（调用方非零退出）——宁可不写，也不把少 33.4M 行的账盖上去。"""
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
        res["note"] = ("本 run 没有可合并的层记录（layers_n=%d）→ 只写单 run 文件，阶段账本不动"
                       % run_layers)
        return res
    merged, stats = merge_stage_ledger(stage, base, run_led, run_id, at=at, note=note)
    # ---- 硬后置条件（W33-059）：合并结果必须覆盖「阶段账本原有层 ∪ 本轮分片层」 ----
    #   ★ 这里**故意不 catch**：丢层是 bug，必须冒到调用方非零退出（FAIL），
    #     而不是转成一条 res["error"] 或 warning 让流程继续往下走。
    assert_merge_covers((base or {}).get("records") or [],
                        run_led.get("records") or [],
                        merged.get("records") or [])
    # ---- 总闸门（ckpt_guard）：合并后**逐层 rows 不许比阶段账本小** ----
    #   判「合并结果 vs 旧账本」，不是「本轮 vs 旧账本」：
    #     · 本轮 failed/0 行 = 没测到，不是测出 0 —— pick_better 已保留旧值，不算回退；
    #     · 只有「更优状态但行数更少」（例如 partial 39.8M → ok 5M）才会真的把 rows 冲小，
    #       这种必须有 regression_reason + 证据路径，否则拒绝写阶段账本、非零退出。
    regs = []
    try:
        from ckpt_guard import guard_ledger_rows                # noqa: E402
        regs = guard_ledger_rows((base or {}).get("records") or [],
                                 merged.get("records") or [],
                                 stage=stage, run_id=run_id, allow_shrink=allow_shrink)
    except Exception as e:                                      # noqa: BLE001
        detail = getattr(e, "detail", {}) or {}
        res.update({"stage_written": False, "reason": "row_regression_without_evidence",
                    "error": str(e), "regressions": detail.get("regressions") or []})
        return res
    if regs:
        merged.setdefault("revisions", []).append({
            "kind": "row_regression_allowed", "at": at, "run_id": str(run_id),
            "note": "行数变小但带实证（regression_reason + evidence），放行并留痕",
            "regressions": regs})
    json.dump(merged, open(stage_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    res.update({"stage_written": True, "stage_layers_after": merged["layers_n"],
                "stage_ok": merged["ok"], "stage_partial": merged["partial"],
                "stage_failed": merged["failed"], "stage_complete": merged["complete"],
                "stats": stats, "row_regressions_allowed": len(regs)})
    # rows 回退（本次合并新记的）跟着摘要一起回传给调用方，别只躺在账本里
    regs_run = [e for e in (merged.get("regressions") or [])
                if str(e.get("run_id")) == str(run_id)]
    res.update({"regressions": regs_run, "rows_regressions": len(regs_run),
                "rows_regressions_unexplained": len([e for e in regs_run if not e.get("evidence")]),
                "rows_regressions_total": len(merged.get("regressions") or [])})
    return res
