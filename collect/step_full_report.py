#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量补采 · 收官文档生成器：把分片账本合成一份「逐层 declared vs 实采」的 Markdown。

输入：collect/ledger/<stage>_shard*.json（每片一份，由 full_shard.py 写）
      collect/ledger/<stage>_plan.json（用来知道「本该有几片」，缺片才算得出未完成片）
输出：docs/STEP04-FULL-<date>.md（或 step05b/07b/10b 对应的文件名）
规则：只写账本里的事实；差额给出百分比与可能原因分类，绝不美化。

★ 2026-10-30 事故：merge 曾因「一片被 cancel → 没有账本 → 脚本 SystemExit」整体 failure，
  于是整轮拿不到任何账。现在改为：缺片 / partial_run 片一律当「未完成片」显式列出并
  计入汇总账本，脚本永远产出部分账本（退出码 0），由 workflow 的闸门决定要不要接续。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)          # 为了 import ledger_merge（同目录）
TITLES = {"step04b": ("STEP04", "全州放量（大层 row_count>300,000 全量补采）"),
          # 片文件名用 04b 前缀（collect/ledger/04b_shardNN.json）+ 汇总账本落 collect/04b_ledger.json，
          # 与 workflow 找的文件名一致；两种写法都认。
          "04b": ("STEP04B", "全州放量 04b（round-2 续跑：36 层 / 9 片）"),
          "05b": ("STEP05B", "县市碎片 05b（5,000~300,000 行）"),
          "07b": ("STEP07B", "碎片补齐 07b（1~4,999 行）"),
          "10b": ("STEP10B", "宗地面层 batch2+ 10b（strong/weak 有效层）"),
          "step05b": ("STEP05", "县市碎片（5,000~300,000 行）全量补采"),
          "step07b": ("STEP07", "碎片补齐（1~4,999 行）全量补采"),
          "step10b": ("STEP10", "宗地面层 batch2+（strong/weak 有效层）")}


def _shard_of(path, led):
    """片号：优先文件里的 shard 字段，回退到文件名尾部的数字。"""
    if isinstance(led.get("shard"), int):
        return led["shard"]
    m = re.search(r"_shard0*(\d+)\.json$", os.path.basename(path))
    return int(m.group(1)) if m else None


def collect_shards(files, plan):
    """返回 (shard_info, expected)：shard_info[片号] = 该片账本摘要；expected = 计划片号列表。"""
    info = {}
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        sid = _shard_of(f, d)
        prev = info.get(sid)
        if prev is None or (d.get("layers_n") or 0) >= (prev.get("layers_n") or 0):
            info[sid] = {"file": os.path.basename(f),
                         "partial_run": bool(d.get("partial_run")),
                         "layers_planned": d.get("layers_planned") or d.get("layers_n") or 0,
                         "layers_n": d.get("layers_n") or 0,
                         "rows": d.get("rows") or 0,
                         "at": d.get("at") or ""}
    if not expected_of(plan):
        return info, sorted(k for k in info if k is not None)
    return info, expected_of(plan)


def expected_of(plan):
    """计划里「本该有哪几片」。

    full_plan.py 写的是 [{"shard":0,"layers":[...]}, ...]；早期/手写计划是 [[layer,...], ...]。
    两种都要认，否则片号对不上、未完成片就漏报。
    """
    shards = plan.get("shards")
    if isinstance(shards, list) and shards:
        out = []
        for i, s in enumerate(shards):
            sid = s.get("shard") if isinstance(s, dict) else None
            out.append(sid if isinstance(sid, int) else i)
        return out
    n = plan.get("shards_n")
    if isinstance(n, int) and n > 0:
        return list(range(n))
    return []


def shard_no_of_file(path):
    """片号只认文件名尾部的 `_shardNN`（plan 里的片号就是这个 NN）。"""
    m = re.search(r"_shard0*(\d+)\.json$", os.path.basename(path))
    return int(m.group(1)) if m else None


def scope_shard_files(files, plan):
    """按「本轮 plan 里有几片就读几片」收窄片文件（W33-058 · merge 作用域缺陷）。

    旧行为无条件 glob `<stage>_shard*.json`，把历次轮次遗留的片文件也吃进 merge：
    05b 实测 plan 只有 3 片、目录里躺着 21 片 → 577 层被冲成 1426 层、37,069,680 行被冲成 75,100,286 行。
    口径：片号 ∈ plan 的片号集合才读，其余一律不读，并逐个打印（不许静默丢）。

    返回 (kept, ignored, unknown, mode)：mode="plan" = 按 plan 收窄；"dir-all" = 无 plan 片号信息，退回旧行为。
    """
    expected = expected_of(plan)
    if not expected:
        return list(files), [], [], "dir-all"
    keep = set(expected)
    kept, ignored, unknown = [], [], []
    for f in files:
        n = shard_no_of_file(f)
        if n is None:
            unknown.append(f)          # 判不出片号：不静默丢，保留并喊出来
            kept.append(f)
        elif n in keep:
            kept.append(f)
        else:
            ignored.append(f)
    if unknown:
        print("::warning::%d 个片文件判不出片号（文件名里没有 _shardNN），已保留读取：%s"
              % (len(unknown), ", ".join(os.path.basename(x) for x in unknown)), flush=True)
    return kept, ignored, unknown, "plan"


def audit_ignored(ignored):
    """审计被排除的遗留片文件（**只在 --audit-ignored 时调用，不参与 merge**）。

    目的仅仅是让收官文档说得出「本轮排除了哪些遗留片、它们各有多少层」，
    数字口径仍是 `layers_n`（与片账本自己写的一致）。"""
    out = []
    for f in ignored:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:                                # noqa: BLE001
            out.append({"file": os.path.basename(f), "shard": shard_no_of_file(f),
                        "layers_n": None})
            continue
        out.append({"file": os.path.basename(f), "shard": _shard_of(f, d),
                    "layers_n": d.get("layers_n") or len(d.get("records") or [])})
    return out


def planned_layers_of(plan, sid):
    """某片计划了多少层（缺片时说得出「至少少了多少层」）。"""
    shards = plan.get("shards")
    if not isinstance(shards, list):
        return None
    for i, s in enumerate(shards):
        if isinstance(s, dict):
            key = s.get("shard")
            if (key if isinstance(key, int) else i) == sid:
                return len(s.get("layers") or [])
        elif i == sid:
            return len(s or [])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, help="step04b / step05b / step07b / step10b")
    ap.add_argument("--out", default="")
    ap.add_argument("--plan", default="")
    # ★ 单 run 账本 / 阶段账本分离（2026-10-30 第二次覆盖事故后加）：
    #   本 run 的结果写 collect/ledger/<stage>_run<RUN_ID>.json，阶段账本只做按层合并。
    ap.add_argument("--run-id", default="", help="本次 run id；空则取环境 GITHUB_RUN_ID")
    ap.add_argument("--base-dir", default=HERE, help="账本根目录（默认脚本所在的 collect/；测试用）")
    ap.add_argument("--allow-stage-overwrite", action="store_true",
                    help="显式允许小 run 覆盖阶段账本（默认禁止：run 层数 < 阶段账本的 1/2 时只写 run 文件）")
    ap.add_argument("--row-shrink-evidence", action="append", default=[], metavar="LAYER=PATH",
                    help="某层 rows 允许变小的实证（可重复）：没有它时，任何一层 rows 变小都会"
                         "拒绝写阶段账本并非零退出（2026-10-30 NAD view 被覆盖事故的总闸门）")
    ap.add_argument("--audit-ignored", action="store_true",
                    help="审计被 plan 作用域排除的遗留片文件（列出片号/层数）——只影响收官文档，"
                         "merge 仍然一片都不读（W33-058）")
    a = ap.parse_args()
    stage = a.stage
    tag, title = TITLES.get(stage, (stage.upper(), stage))

    plan = {}
    if a.plan and os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8"))
    else:
        guess = os.path.join(a.base_dir, "ledger", stage + "_plan.json")
        if os.path.exists(guess):
            plan = json.load(open(guess, encoding="utf-8"))

    # ★ W33-058：merge 作用域 = 本轮 plan 的片号集合，不是「目录里有多少片」。
    #   遗留片文件（历史 run 留下的 <stage>_shardNN.json）不计入任何数字，且必须点名。
    files_all = sorted(glob.glob(os.path.join(a.base_dir, "ledger", stage + "_shard*.json")))
    files, ignored_files, unknown_files, shard_scope = scope_shard_files(files_all, plan)
    if ignored_files:
        print("忽略遗留片文件 %d 个：%s"
              % (len(ignored_files), ", ".join(os.path.basename(x) for x in ignored_files)),
              flush=True)
    elif shard_scope == "dir-all":
        print("::warning::无 plan（或 plan 里没有片号），按目录全量读 %d 个片文件，可能吃到遗留片"
              % len(files_all), flush=True)

    if not files and not expected_of(plan):
        raise SystemExit("没有任何片账本、也没有计划文件：无法判断采到什么")
    shard_info, expected = collect_shards(files, plan)
    read_shards = sorted(k for k in shard_info if k is not None)

    recs = []
    meta = {}
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        meta.setdefault("shards_total", d.get("shards_total"))
        meta.setdefault("size", d.get("size"))
        meta.setdefault("unit_rows", d.get("unit_rows"))
        recs += d.get("records") or []

    by = {}
    for r in recs:                                  # 同一层出现多次取「最好」的那次
        prev = by.get(r["layer"])
        rank = {"ok": 5, "capped_by_upstream": 4, "empty": 3, "skipped_done": 2, "partial": 1,
                "failed": 0}
        if prev is None or rank.get(r["status"], 0) > rank.get(prev["status"], 0):
            by[r["layer"]] = r
    recs = sorted(by.values(), key=lambda r: -(r.get("declared") or 0))

    cnt = {}
    for r in recs:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    declared = sum((r.get("declared") or 0) for r in recs)
    rows = sum((r.get("rows") or 0) for r in recs)
    # capped_by_upstream 层的声明不可复核（declared=None）→ 与 adjudicate/ledger_merge 同口径：
    # 分子也要拿掉它的已采行数，否则两个百分比不可比。
    rows_capped = sum((r.get("rows") or 0) for r in recs if r["status"] == "capped_by_upstream")
    declared_unver = sum((r.get("declared_unverifiable") or 0) for r in recs
                         if r["status"] == "capped_by_upstream")
    gaps = [r for r in recs if (r.get("declared") or 0) > (r.get("rows") or 0)]
    gaps.sort(key=lambda r: ((r.get("declared") or 0) - (r.get("rows") or 0)), reverse=True)
    bad = [r for r in recs if r["status"] in ("failed", "partial")]

    # ---- 片完成度：缺片 / partial_run 片 = 未完成片，显式列出，绝不静默 ----
    incomplete, shard_rows = [], []
    #   shard_info 里可能有 None（判不出片号的文件）：它不属于任何「片」，不进完成度表，
    #   已在上面逐个 warning 点名，这里只需别把它当片号去排序（py3 里 None < int 会直接抛）。
    for sid in sorted((set(expected) | set(shard_info)) - {None}):
        si = shard_info.get(sid)
        if si is None:
            planned = planned_layers_of(plan, sid)
            state, lost = "未完成：无账本（片被取消/没启动）", planned
            shard_rows.append((sid, planned, 0, 0, state))
            incomplete.append({"shard": sid, "cause": "no_ledger", "layers_planned": planned})
            continue
        lost = max(0, (si["layers_planned"] or 0) - (si["layers_n"] or 0))
        if si["partial_run"]:
            state = "未完成：片内没跑完（partial_run=true）"
            incomplete.append({"shard": sid, "cause": "partial_run",
                               "layers_planned": si["layers_planned"],
                               "layers_n": si["layers_n"]})
        else:
            state = "完成"
        shard_rows.append((sid, si["layers_planned"], si["layers_n"], si["rows"], state))

    L = ["# %s 全量补采 · 收官账（%s）" % (tag, datetime.now(timezone.utc).strftime("%Y-%m-%d")), "",
         "## 一、总账", "",
         f"- 阶段：`{stage}` —— {title}",
         f"- 计划：{plan.get('layers_n', '?')} 层 / 声明 {plan.get('declared_rows', 0):,} 行 / "
         f"{plan.get('shards_n', '?')} 片（每片 {plan.get('size', '?')} 层，unit_rows={plan.get('unit_rows', '?')}）",
         f"- 账本覆盖：**{len(recs)} 层**（片文件 {len(files)} 个"
         + (f"；已按 plan 作用域排除遗留片 {len(ignored_files)} 个" if ignored_files else "") + "）",
         f"- 逐态：**ok {cnt.get('ok', 0)}** / capped_by_upstream {cnt.get('capped_by_upstream', 0)} / "
         f"empty {cnt.get('empty', 0)} / partial {cnt.get('partial', 0)} / "
         f"failed {cnt.get('failed', 0)} / skipped_done {cnt.get('skipped_done', 0)}",
         f"- 片完成度：应有 **{len(expected)}** 片，有账本 {len(shard_info)} 片，"
         f"**未完成 {len(incomplete)} 片**"
         + (("：片号 " + ", ".join(str(s['shard']) for s in incomplete)) if incomplete else ""),
         f"- 声明行合计：**{declared:,}**；实采行合计：**{rows:,}**；"
         f"差额 {declared - (rows - rows_capped):,}"
         f"（{100.0 * (declared - (rows - rows_capped)) / max(declared, 1):.3f}%）",
         ((("- capped_by_upstream 层：**%d 层**，已采 %s 行计入实采；其声明 %s 行不可复核"
            "（`declared_unverifiable`），不入分母，差额分子也同步扣除它们 → 上面百分比才是同口径的。")
           % (cnt.get("capped_by_upstream", 0), f"{rows_capped:,}", f"{declared_unver:,}"))
          if rows_capped else ""),
         "",
         "> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。",
         "> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。",
         "> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。", ""]

    L += ["## 二、片完成度（未完成片显式列出）", ""]
    if shard_rows:
        L += ["| 片 | 计划层 | 已记层 | 实采行 | 状态 |", "|---|---|---|---|---|"]
        for sid, planned, done, rw, state in shard_rows:
            L.append("| %s | %s | %d | %s | %s |"
                     % ("-" if sid is None else sid,
                        "-" if planned is None else planned, done, f"{rw:,}", state))
        lost_total = sum((i.get("layers_planned") or 0) - (i.get("layers_n") or 0)
                         for i in incomplete)
        if incomplete:
            L += ["", f"**未完成片共 {len(incomplete)} 个，至少 {lost_total} 层没有任何账本条目**"
                      "（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。"]
    else:
        L.append("**无片账本信息。**")
    L += [""]

    # ★ max_shards 截断单列一节（W33-036）：砍片必须可见，不能看着像「本来就没采到」
    trunc = plan.get("plan_truncated") or {}
    if trunc:
        L += ["## 二之二、max_shards 截断：本轮注定没跑的片（W33-036）", "",
              "> 这不是「没采到」，是 **没派**：`max_shards=%s` 把 %d 片截成 %d 片，"
              "%d 层连 job 都没起。清单同时写在 plan 的 `shards_dropped[]`，账本 "
              "`shards_incomplete` 也会点名。要全跑请 `max_shards=0`。"
              % (trunc.get("max_shards"), trunc.get("expected_shards"),
                 trunc.get("actual_shards"), trunc.get("dropped_layers_n")),
              ""]
        L += ["| 被砍分片 | 层数 | 层 id |", "|---|---|---|"]
        for d in plan.get("shards_dropped") or []:
            L.append("| %d | %d | %s |" % (d["shard"], len(d["layers"]),
                                            ", ".join("`%s`" % x for x in d["layers"])))
        L += [""]

    # ★ W33-058：被作用域排除的遗留片文件必须写进文档（不许静默丢）
    if ignored_files:
        legacy = (audit_ignored(ignored_files) if a.audit_ignored else
                  [{"file": os.path.basename(x), "shard": shard_no_of_file(x), "layers_n": None}
                   for x in ignored_files])
        L += ["## 二之三、遗留片文件（不计入本轮）", "",
              "> 本轮 plan 只有 **%d** 片（片号 %s），同目录另有 **%d** 个同 stage 前缀的片文件属于更早轮次。"
              "merge 作用域按 plan 收窄（W33-058 修）：这些文件**不被读取、不计入任何数字**。"
              "以前无条件 glob 会把它们一起吃进来，让层数与行数虚高。"
              % (len(expected), ", ".join(str(x) for x in sorted(expected)), len(ignored_files)), ""]
        if a.audit_ignored:
            tot = sum((x["layers_n"] or 0) for x in legacy)
            L += ["| 遗留片文件 | 片号 | 层数 |", "|---|---|---|"]
            for x in legacy:
                L.append("| `%s` | %s | %s |"
                         % (x["file"], "-" if x["shard"] is None else x["shard"],
                            "-" if x["layers_n"] is None else f"{x['layers_n']:,}"))
            L += ["", "**遗留片合计 %d 个文件 / %s 层记录**（其中与上面几片重层的会在按层合并时被去重，"
                  "所以「净增层数」会小于这个数）。这些层属于更早轮次，要采必须单独派单。"
                  % (len(legacy), f"{tot:,}"), ""]
        else:
            L += ["文件清单：", ""] + ["- `%s`" % x["file"] for x in legacy] + [""]

    L += ["## 三、差额最大的 10 层", ""]
    if gaps:
        L += ["| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |", "|---|---|---|---|---|---|"]
        for r in gaps[:10]:
            dcl, rw = (r.get("declared") or 0), (r.get("rows") or 0)
            L.append("| `%s` | %s | %s | %s | %s | %s |"
                     % (r["layer"], f"{dcl:,}", f"{rw:,}", f"{dcl - rw:,}",
                        r["status"], (r.get("reason") or "")[:80]))
    else:
        L.append("**零差额**：所有层实采 == 声明。")
    L += [""]

    L += ["## 四、残缺层清单（failed / partial，逐条原因）", ""]
    if bad:
        L += ["| 层 | 状态 | 声明 | 实采 | 原因 |", "|---|---|---|---|---|"]
        for r in bad:
            L.append("| `%s` | %s | %s | %s | %s |"
                     % (r["layer"], r["status"], r.get("declared"), r.get("rows"),
                        (r.get("reason") or "")[:120]))
    else:
        L.append("**无。** 本阶段没有 failed / partial 层。")
    L += [""]

    L += ["## 五、逐层台账（按声明行数降序）", "",
          "| # | 层 | 声明 | 实采 | 差额% | 状态 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(recs, 1):
        dcl, rw = (r.get("declared") or 0), (r.get("rows") or 0)
        pct = (100.0 * (dcl - rw) / dcl) if dcl else 0.0
        L.append("| %d | `%s` | %s | %s | %.2f%% | %s |"
                 % (i, r["layer"], f"{dcl:,}" if dcl else "-",
                    f"{rw:,}" if rw is not None else "-", pct, r["status"]))
    L += ["", "## 六、复现", "", "```bash",
          "gh workflow run collect-full.yml -f stage=%s" % stage,
          "python3 collect/full_plan.py --stage %s --size %s --out collect/ledger/%s_plan.json"
          % (stage, plan.get("size", 20), stage),
          "python3 collect/full_shard.py --stage %s --shard 0 --plan collect/ledger/%s_plan.json"
          % (stage, stage), "```", ""]

    # 默认文件名带 `-shards`：与 ledger_rebuild.py 产出的「Release 资产真值」文档
    # （docs/STEP04-FULL-<date>.md）分开，避免分片口径覆盖真值口径。
    out = a.out or os.path.join(ROOT, "docs", tag + "-FULL-2026-10-30-shards.md")

    # ★ 口径备注：与人写的 `<out 去后缀>.notes.md` 并排存放，生成时自动追加 ——
    #   这样 CI 重跑（collect-full.yml 的 merge step）不会把备注冲掉。
    notes = os.path.splitext(out)[0] + ".notes.md"
    if os.path.exists(notes):
        L += ["", open(notes, encoding="utf-8").read().rstrip(), ""]

    # 本次 run 的汇总（内存对象；写盘由 ledger_merge 决定去哪个文件）
    led = {"schema": "collect-ledger-agg/v1", "stage": stage, "at":
           datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "layers_n": len(recs), "ok": cnt.get("ok", 0), "empty": cnt.get("empty", 0),
           "capped_by_upstream": cnt.get("capped_by_upstream", 0),
           "partial": cnt.get("partial", 0), "failed": cnt.get("failed", 0),
           "skipped_done": cnt.get("skipped_done", 0),
           "declared": declared, "rows": rows, "rows_capped": rows_capped,
           "rows_verifiable": rows - rows_capped,
           "declared_unverifiable": declared_unver,
           "gap": declared - (rows - rows_capped),
           "shards_expected": len(expected), "shards_reported": len(shard_info),
           "shards_incomplete": [s["shard"] for s in incomplete],
           "shards_incomplete_detail": incomplete,
           # ★ W33-058：本轮到底读了哪几片、排除了哪些遗留片（谁都能复核）
           "shard_scope": shard_scope,
           "read_shards": read_shards,
           "ignored_shard_files": [os.path.basename(x) for x in ignored_files],
           "unparsable_shard_files": [os.path.basename(x) for x in unknown_files],
           # ★ W33-036：plan 被 max_shards 截断时，把“本轮注定没跑的片/层”写进账本，
           #   收口时一眼看到缺口是谁；没截断则为 None（不干扰旧账对比）。
           "plan_truncated": plan.get("plan_truncated"),
           "shards_dropped": plan.get("shards_dropped") or [],
           "complete": (not incomplete) and cnt.get("failed", 0) == 0,
           "plan": {k: plan.get(k) for k in ("layers_n", "declared_rows", "shards_n", "size")},
           "records": recs}

    # 汇总账本
    # ★ 2026-10-30 第二次事故（run 41121952357 把 272 层阶段账本冲成 31 层）：这里不再直接写
    #   collect/<stage>_ledger.json。改为：① 单 run 结果 → collect/ledger/<stage>_run<RUN_ID>.json；
    #   ② 阶段账本按 layer_id **并集**合并（状态取更优者，同状态取行数大者）；
    #   ③ 并集合并只增不减，所以不再用体积判据拦小 run（W33-059），改用不变量：「原有层一个不许丢」。
    #   详见 collect/ledger_merge.py（带单测）。
    from ledger_merge import write_run_and_stage, format_regressions_section   # noqa: E402
    run_id = a.run_id or os.environ.get("GITHUB_RUN_ID") or "local"
    allow_shrink = {}
    for spec in a.row_shrink_evidence:
        if "=" in spec:
            lay, pth = spec.split("=", 1)
            allow_shrink[lay.strip()] = pth.strip()
    res = write_run_and_stage(stage, led, run_id, base_dir=a.base_dir,
                              allow_stage_overwrite=a.allow_stage_overwrite,
                              allow_shrink=allow_shrink)

    # ★ W33-059（2026-11-22）：阶段账本没并进本轮 → 必须喊出来。
    #   旧行为是静默：run 44960026303 就这样把「3 层 ok + 1 层 empty」锁在 run 账本里，
    #   聚合账本与接续闸门全看成上一轮的内容（闸门报 incomplete_shards=[2]，而本轮一片不缺）。
    if not res.get("stage_written") and not res.get("error"):
        print("::warning::本轮没有并入阶段账本（reason=%s）：%d 层只写了 %s，"
              "聚合账本 %s 仍是上一轮的内容（本轮新增/更新的层不会出现在里面）"
              % (res.get("reason"), led["layers_n"], os.path.basename(res["run_path"]),
                 os.path.basename(res["stage_path"])), flush=True)

    # ★ rows 回退单独成节（2026-10-31）：状态取优者 + 行数取大者会把「真丢数据」掩盖成
    #   「本次没采到那么多」，所以只要本轮某层 rows < 阶段账本 rows，就必须在这里点名。
    regs = res.get("regressions") or []
    if regs:
        L += ["", "## 七、rows 回退（本次合并检测到，未静默取大）", ""]
        L += format_regressions_section(regs)
        L += ["",
              "> 处置：回退不拦截（保进展靠取优者），但**必须点名**。能证明是「口径变了/上游真删了」的，"
              "把证据路径写进 run 账本的 `row_shrink_evidence: {<layer>: <path>}`（或逐层 `regression_reason`）；"
              "无证据的回退一律当事故追。累计视图看 `collect/%s_ledger.json` 的 `regressions[]`。" % stage, ""]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))

    print(json.dumps({k: led[k] for k in ("stage", "layers_n", "ok", "empty", "partial",
                                         "failed", "skipped_done", "declared", "rows",
                                          "shards_expected", "shards_reported",
                                          "read_shards", "ignored_shard_files",
                                          "unparsable_shard_files",
                                          "shards_incomplete", "complete")},
                     ensure_ascii=False))
    print(json.dumps({"run_ledger": res}, ensure_ascii=False))
    if regs:
        print("::warning::rows 回退 %d 层（无证据 %d 层）→ 见 %s 第七节"
              % (len(regs), res.get("rows_regressions_unexplained", 0), out))
    if trunc:
        print("::warning::max_shards=%s 截断：%d 片→%d 片，%d 层本轮注定不跑→见 %s 二之二节"
              % (trunc.get("max_shards"), trunc.get("expected_shards"),
                 trunc.get("actual_shards"), trunc.get("dropped_layers_n"), out))
    print("写入 %s 与 %s" % (out, res["run_path"]))
    if res.get("error"):
        # 行数回退且无实证：阶段账本一个字没动。非零退出，让 workflow 看得见。
        print("::error::阶段账本拒绝写入（行数回退无实证）：%s" % str(res["error"])[:500], flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
