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
    a = ap.parse_args()
    stage = a.stage
    tag, title = TITLES.get(stage, (stage.upper(), stage))
    files = sorted(glob.glob(os.path.join(a.base_dir, "ledger", stage + "_shard*.json")))

    plan = {}
    if a.plan and os.path.exists(a.plan):
        plan = json.load(open(a.plan, encoding="utf-8"))
    else:
        guess = os.path.join(a.base_dir, "ledger", stage + "_plan.json")
        if os.path.exists(guess):
            plan = json.load(open(guess, encoding="utf-8"))

    if not files and not expected_of(plan):
        raise SystemExit("没有任何片账本、也没有计划文件：无法判断采到什么")
    shard_info, expected = collect_shards(files, plan)

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
    for sid in sorted(set(expected) | set(shard_info)):
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
         f"- 账本覆盖：**{len(recs)} 层**（片文件 {len(files)} 个）",
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
           "complete": (not incomplete) and cnt.get("failed", 0) == 0,
           "plan": {k: plan.get(k) for k in ("layers_n", "declared_rows", "shards_n", "size")},
           "records": recs}

    # 汇总账本
    # ★ 2026-10-30 第二次事故（run 41121952357 把 272 层阶段账本冲成 31 层）：这里不再直接写
    #   collect/<stage>_ledger.json。改为：① 单 run 结果 → collect/ledger/<stage>_run<RUN_ID>.json；
    #   ② 阶段账本按 layer_id 合并（状态取更优者，同状态取行数大者）；③ 小 run（<1/2）默认不碰阶段账本。
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
                                          "shards_incomplete", "complete")},
                     ensure_ascii=False))
    print(json.dumps({"run_ledger": res}, ensure_ascii=False))
    if regs:
        print("::warning::rows 回退 %d 层（无证据 %d 层）→ 见 %s 第七节"
              % (len(regs), res.get("rows_regressions_unexplained", 0), out))
    print("写入 %s 与 %s" % (out, res["run_path"]))
    if res.get("error"):
        # 行数回退且无实证：阶段账本一个字没动。非零退出，让 workflow 看得见。
        print("::error::阶段账本拒绝写入（行数回退无实证）：%s" % str(res["error"])[:500], flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
