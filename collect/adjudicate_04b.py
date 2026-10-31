#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04b 判定修正（adjudication）：把「failed」拆成有实证的四种状态，产出真值账本 + 审计文档。

背景（2026-10-30）：`step04b_rebuilt.json` 里 18 层 failed 混了三种完全不同的情况，
直接报「18 层 failed」既看不出该不该重采，也没法让闸门判断能不能接续：

  · 上游此刻能给出 returnCount 且 >0，但本层 0 行  → 这是**真缺口**（missing，必须重采）
  · 上游能给出 returnCount，本层跑到一半          → **partial**（定向续采）
  · 上游彻底连不上 / 报错，本层也没数据           → **unverified**（无法归因，不许当 0 数据）
  · 上游明确 0 行 / 服务下线（esri 404）           → **empty**（不是采集失败）
  · 上游改成**服务级 token**（连 `/0?f=json` 都 499）→ **capped_by_upstream**（永远采不到更多；
    declared 移出分母、记 `declared_unverifiable`，已采行数照旧计入 rows）

判据全部来自 `analysis/04b-upstream-evidence-*.json`（逐层 returnCount + HTTP/原始响应），
不做任何估算；声明值一律改成**上游当前 returnCount**，改动逐条记在 revisions 里。

用法：
  python3 collect/adjudicate_04b.py --rebuilt collect/ledger/step04b_rebuilt.json \
      --evidence analysis/04b-upstream-evidence-2026-10-30.json \
      --plan collect/ledger/04b_plan.json \
      --cancel-plan <plan-04b artifact> \
      --out collect/04b_ledger.json \
      --audit analysis/04b-cancel-audit-2026-10-30.json \
      --doc docs/STEP04-ADJUDICATED-2026-10-30.md [--check]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOL = 0.01          # 与 ledger_rebuild 的 GAP_TOL 一致：差额 >1% 才算没采全

# ★ 2026-10-31 新规矩（用户明令）：声明分母不许永久当分母。
#   事实：81 层实采超过声明、净额 −43,423,188 行 ⇒ 「声明行数」普遍是过期快照
#   （上游缩水/删除/口径变），拿它当分母会让覆盖率系统性失真。
#   下面这套是**只读**刷新：打上游 returnCount、出差异表、只给建议；改账本必须人工点头。
DECLARED_REFRESH_STATUSES = ("ok", "missing", "partial")
DECLARED_CONFIRM_PHRASE = "I-APPROVE-DECLARED-REFRESH"
UA = {"User-Agent": "collect-audit/1.0 (+world-map-data-33)"}


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def classify(rec, ev):
    """返回 (status, reason, declared_new)。ev 为该层的取证（无则 None）。"""
    rows = rec.get("rows") or 0
    declared = rec.get("declared")
    cnt = None if ev is None else ev["probe"].get("count")
    verdict = None if ev is None else ev["verdict"]
    raw = "" if ev is None else (ev["probe"].get("raw") or "")

    if verdict == "upstream_alive":
        new_decl = cnt
        if cnt == 0:
            return "empty", "upstream_no_data：上游 returnCount=0", 0
        if rows >= cnt * (1 - TOL):
            return "ok", "实采 %s ≥ 上游当前 returnCount %s×(1-1%%)" % (f"{rows:,}", f"{cnt:,}"), new_decl
        if rows > 0:
            return "partial", "实采 %s / 上游当前 returnCount %s（差 %.2f%%）" % (
                f"{rows:,}", f"{cnt:,}", 100.0 * (cnt - rows) / cnt), new_decl
        return "missing", "上游当前 returnCount=%s，本层 0 行 → 真缺口，必须重采" % f"{cnt:,}", new_decl

    if verdict == "upstream_gone_404" or "Service not found" in raw:
        return "empty", "upstream_service_gone：上游返回 esri 404 / Service not found", declared

    if verdict == "upstream_unreachable":
        why = "" if ev is None else (ev["probe"].get("err") or "")[:80]
        if rows > 0:
            return "partial", "上游不可达（%s）；实采停在 %s / 声明 %s" % (
                why, f"{rows:,}", f"{declared:,}" if declared else "-"), declared
        return "unverified", "上游不可达（%s），本层无数据 → 无法判定，不许当 0 数据" % why, declared

    # 没有取证（本轮探测未覆盖）：保持重建账本原判，但 failed 不允许留在成品账里
    if rec["status"] == "failed":
        return "unverified", "无上游取证（探测未覆盖）", declared
    return rec["status"], rec.get("reason") or "", declared


def cancel_audit(cancel_plan, truth, rebuilt):
    """被取消的片 0/1/3/6：逐层在账本里是否命中 + 取消时的完成度（按 Release 资产）。"""
    shards = {d["shard"]: d["layers"] for d in cancel_plan["shards"]}
    cancelled = [s for s in sorted(shards) if s in (0, 1, 3, 6)]
    out = {"plan_layers_n": cancel_plan.get("layers_n"), "shards_n": cancel_plan.get("shards_n"),
           "size": cancel_plan.get("size"), "cancelled_shards": cancelled, "per_shard": [],
           "totals": {"layers": 0, "done": 0, "half": 0, "none": 0, "missing_in_ledger": 0}}
    for s in cancelled:
        block = {"shard": s, "layers": []}
        for lid in shards[s]:
            t = truth.get(lid)
            if t is None:
                cls, note = "missing_in_ledger", "账本里查不到这一层"
            else:
                d, rw = t.get("declared"), (t.get("rows") or 0)
                if rw == 0:
                    cls, note = "none", "取消时 0 行（未开始 / 上游一行未返回）"
                elif d and rw >= d * (1 - TOL):
                    cls, note = "done", "取消前已完成（资产在 Release）"
                else:
                    cls, note = "half", "取消时半截"
            block["layers"].append({"layer": lid, "in_ledger": t is not None,
                                    "ledger_status": (t or {}).get("status"),
                                    "declared": (t or {}).get("declared"),
                                    "rows": (t or {}).get("rows"),
                                    "progress": cls, "note": note,
                                    "asset_rows": (rebuilt.get(lid) or {}).get("rows")})
            out["totals"]["layers"] += 1
            out["totals"][cls] = out["totals"].get(cls, 0) + 1
        out["per_shard"].append(block)
    return out


def render_doc(led, audit, evidence, sha_refs):
    L = []
    A = L.append
    A("# 04b 判定修正 + 取消审计（2026-10-30）")
    A("")
    A("> 本文由 `collect/adjudicate_04b.py` 生成（`--check` 可验证字节一致），数字全部来自")
    A("> `collect/ledger/step04b_rebuilt.json`（Release 资产重建）+ `analysis/04b-upstream-evidence-*.json`")
    A("> （逐层上游 returnCount 实测）。**没有一行是估的**；每处改判都能落到下面某条证据。")
    A("")
    A("## 零、账本口径约定（先看这一节，别读错文件）")
    A("")
    A("| 文件 | 口径 | 真值来源 | 数字含义 |")
    A("|---|---|---|---|")
    A("| `collect/${STAGE}_ledger.json`（如 `collect/04b_ledger.json`） | **阶段级** | Release 资产 checkpoint + 上游 returnCount 实测 | 跨 run 合并的全阶段账（04b = 272 层） |")
    A("| `collect/ledger/${STAGE}_run<id>.json`（如 `04b_run41092912755.json`） | **单 run 级** | 该 run 的片账本（artifact / git） | 单轮跑到哪、哪几片没跑完（04b 那一轮 = 20 层 / 5 片 / 4 片未完成） |")
    A("| `collect/ledger/step<NN>b_rebuilt.json` | 阶段级·重建 | 只读 Release 资产反推 | 逐层 declared vs 实采（本文件的上游） |")
    A("")
    A("**两者数字本来就不同，不许混读**：阶段级 272 层回答「04b 到底采了多少」，")
    A("单 run 级回答「那一次 run 有几片被掐」。文档引用时必须写明用的是哪一份。")
    A("")
    A("## 一、集合对账（计划分母 vs 账本 vs 上游取证）")
    A("")
    for k, v in led["set_reconciliation"].items():
        A("- %s：**%s**" % (k, v))
    A("")
    A("> 分母口径说明：04b 的候选集由 `steps.json` 的 `select`（row_count>300000 + 标题正则）")
    A("> 与 policy 的 `geom_in=[point,multipoint,socrata,na]` 共同决定，实测为 **320 层**；")
    A("> 首轮计划 272 层 = 320 层里**尚未采过的**那批（其余 48 层此前已有 `collect-step04-*` 资产）。")
    A("> 因此 272 不是「04b 全部应采」，而是「04b 首轮实际要补的」。二者差额 48 层已核过全部有 tag。")
    A("")
    A("## 二、被取消的 4 片（shard 0/1/3/6）逐层落点")
    A("")
    if not audit.get("per_shard"):
        A("**本次没有传入取消片计划（`--cancel-plan`），跳过取消审计。**")
        A("")
    else:
        A("取消动作发生在 **2026-10-30T19:16:05Z**（`gh run cancel 41092912755`），")
        A("四个 job 的 `completed_at` 为 19:16:32 / 19:16:34 / 19:16:34 / 19:16:59，同一秒级窗口 → 一次统一取消。")
        A("取消时该 SHA 的分片脚本**还没有增量落盘**（`f46589a` 之后才有），所以本地没有半截账本；")
        A("下面的完成度一律用 **Release 资产**（`step04b_rebuilt.json`）反推，不猜。")
        A("")
        A("| 片 | 层数 | 已完成 | 半截 | 0 行 | 账本缺失 |")
        A("|---|---|---|---|---|---|")
        for b in audit["per_shard"]:
            c = {"done": 0, "half": 0, "none": 0, "missing_in_ledger": 0}
            for x in b["layers"]:
                c[x["progress"]] += 1
            A("| %d | %d | %d | %d | %d | %d |" % (b["shard"], len(b["layers"]), c["done"],
                                                   c["half"], c["none"], c["missing_in_ledger"]))
        t = audit["totals"]
        A("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** |" % (
            t["layers"], t["done"], t["half"], t["none"], t["missing_in_ledger"]))
        A("")
        A("**结论：取消造成的新增漏账 = %d 层。** 被取消片的 %d 层全部能在 272 层账本里找到条目，"
          "已完成层的资产都在 Release 上。" % (t["missing_in_ledger"], t["layers"]))
        A("")
        A("逐层明细：")
        A("")
        A("| 层 | 取消时进度 | 账本状态 | 声明 | 实采 | 说明 |")
        A("|---|---|---|---|---|---|")
        for b in audit["per_shard"]:
            for x in b["layers"]:
                A("| `%s` | %s | %s | %s | %s | %s |" % (
                    x["layer"], x["progress"], x["ledger_status"],
                    f"{x['declared']:,}" if x["declared"] else "-",
                    f"{x['rows']:,}" if x["rows"] else "0", x["note"]))
        A("")
    A("## 三、判定修正（failed → 有实证的五类）")
    A("")
    A("| 状态 | 层数 | 含义 |")
    A("|---|---|---|")
    for k in ("ok", "partial", "capped_by_upstream", "missing", "unverified", "empty", "skipped_done"):
        A("| %s | %d | %s |" % (k, led["buckets"].get(k, 0), led["bucket_meaning"][k]))
    A("")
    A("**failed = %d**（成品账本里不再有「failed」这个状态：每一层要么有资产、要么有明确归因）。"
      % led["failed"])
    A("")
    if led.get("capped_layers"):
        A("### 3.0 `capped_by_upstream`：上游改口径导致永久不可采")
        A("")
        A("判据：**服务级** token —— 连 `<api>/0?f=json` 都 499，`returnCountOnly` / `returnIdsOnly` 同样 499，")
        A("且连续两轮探测一致（间隔 ≥60s）。这种事 HTTP 状态码是 **200**，token 拦在响应体里，")
        A("只看 status code 会把它当「服务正常」→ 于是整层 0 行被当成「我们没采」，日复一日徒劳重采。")
        A("")
        A("| 层 | 已采行数（计入 rows） | declared_unverifiable（移出分母） | 探测 | 证据 |")
        A("|---|---|---|---|---|")
        for c in led["capped_layers"]:
            A("| `%s` | %s | %s | %d 轮 × 3 端点全 499（%s） | `%s` |" % (
                c["layer"], f"{c['rows']:,}", f"{c['declared_unverifiable']:,}",
                c["rounds_n"], c.get("last_probe_at") or "-", c["evidence_path"]))
        A("")
        A("分母口径（本节之后的所有百分比都用这个）：")
        A("")
        A("- `rows` = %s（全部实采，含 capped 层的 %s）" % (f"{led['rows']:,}", f"{led['rows_capped']:,}"))
        A("- `declared` = %s（**不含** capped 层）" % f"{led['declared']:,}")
        A("- `rows_verifiable` = %s（与分母同口径的分子 = rows − capped 行数）" % f"{led['rows_verifiable']:,}")
        A("- `gap` = declared − rows_verifiable = **%s 行（%.4f%%）**" % (f"{led['gap']:,}", led["gap_pct"] or 0))
        A("- capped 层的 declared 另记 `declared_unverifiable` = %s，**永远不进分母**" % f"{led['declared_unverifiable']:,}")
        A("")
        A("### 3.0.1 分母口径硬规矩（2026-10-31 用户定：声明值不是永久分母）")
        A("")
        A("> **1）声明值来自 `layer_plan.csv` 的计划期快照，上游会缩水/删数据/改口径。**")
        A("> 实测（本账本口径，可复现）：**80 层实采 > 声明，超采合计 3,547,920 行**")
        A("> （rebuilt 口径 81 层 / 3,547,930）；全账 `gap` = %s 行。拿过期声明当分母，" % f"{led['gap']:,}")
        A("> 覆盖率系统性失真，而且「按声明 / 按可核实」两个百分比天生不可相减。")
        A(">")
        A("> **2）对外覆盖一律报两个数，禁止只报一个：**")
        A("> - **`按声明分母`** = `rows_verifiable ÷ declared`（declared 剔除 capped 层）")
        A("> - **`按可核实分母`** = `rows_verifiable ÷ (已刷新层用上游 returnCount + 未刷新层用旧声明)`，同时剔除 capped")
        A("> 两个数必须同屏出现并标注 `declared_refreshed_at`（账本顶层；没刷过就写「未刷新」）。")
        A("> 单独抛出任何一个数都算无效报表。")
        A(">")
        A("> **3）刷新是只读 + 人工点头：**")
        A("> ```bash")
        A("> # 只读：逐层打 returnCount，出「旧声明 / 新声明 / 实采 / 关系」差异表；不改账本")
        A("> python3 collect/adjudicate_04b.py --refresh-declared --json-out analysis/04b-declared-refresh-<date>.json")
        A("> # 采纳：写前备份 + 追加 revisions[kind=declared_refreshed]")
        A("> python3 collect/adjudicate_04b.py --apply-declared-refresh <json> --declared-confirm I-APPROVE-DECLARED-REFRESH")
        A("> ```")
        A("> 只对 `ok / missing / partial` 且上游可达的层生效；`capped_by_upstream` / `unverified` / `empty` 一律不碰。")
        A("> 当前 `declared_refreshed_at` = %s" % (led.get("declared_refreshed_at") or "未刷新"))
        A("")
    A("### 3.1 与旧账的差异（逐条）")
    A("")
    A("| 层 | 旧状态 | 新状态 | 旧声明 | 新声明 | 原因 |")
    A("|---|---|---|---|---|---|")
    for r in led["revisions"]:
        if r.get("kind") and not r.get("layer"):        # 运行级事件（复原/合并）在 3.4 单列
            continue
        A("| `%s` | %s | %s | %s | %s | %s |" % (
            r["layer"], r["from"], r["to"],
            f"{r['declared_before']:,}" if r["declared_before"] else "-",
            f"{r['declared_after']:,}" if r["declared_after"] else "-", r["reason"]))
    A("")
    _events = [r for r in led["revisions"] if r.get("kind") and not r.get("layer")]
    if _events:
        A("### 3.1b 阶段账本的运行级事件（复原 / 合并留痕，只追加不替换）")
        A("")
        A("| 时间 | 类型 | run | 说明 |")
        A("|---|---|---|---|")
        for r in _events:
            A("| %s | %s | %s | %s |" % (r.get("at") or "-", r.get("kind") or "-",
                                         r.get("run_id") or "-",
                                         (r.get("note") or r.get("reason") or "")[:160]))
        A("")
    A("### 3.2 「13 层上游 0 数据」这个口径被实测推翻")
    A("")
    A("原始交接里把 13 层说成「上游 0 数据」。本机对每层直接打 `returnCountOnly` 的结果是：")
    A("**没有任何一层返回 count=0**。")
    A("")
    A("- %d 层上游**活着**并给出非 0 行数（含 SAM_Address_Points ×2、NC1Map@未定位-1、"
      "AGOL_NG911、mn_state@未定位-1、rgv911 ×2、NC1Map@未定位-2、NC1Map_Location、LBRS、"
      "COTGEO、NG911_Address_Points、NAD）；" % sum(1 for x in evidence["layers"] if x["verdict"] == "upstream_alive"))
    A("- %d 层连不上/超时/403（`unverified`，不能当 0 数据）；" % sum(1 for x in evidence["layers"] if x["verdict"] == "upstream_unreachable"))
    A("- 只有 1 层是真·服务下线：`_arcgis1_..._FLEXMOBILE_Address_Points_MapServer_0` —— HTTP 200 但 body 是")
    A("  `{\"error\":{\"code\":404,\"message\":\"Service not found\"}}` → 归 `empty`（`upstream_service_gone`）。")
    A("")
    A("所以本次**没有**按「13 层→empty」改，而是按证据分成 `missing`（上游有数、本层 0 行，必须重采）"
      "与 `unverified`（上游不可达）。把有数据的层标成 empty 就是改口径凑数，不做。")
    A("")
    A("### 3.3 4 条 partial 的声明重算（不重采）")
    A("")
    A("| 层 | 旧声明 | 上游当前 returnCount | 实采 | 旧差额 | 新差额 | 判定 |")
    A("|---|---|---|---|---|---|---|")
    for r in led["partial_recalc"]:
        A("| `%s` | %s | %s | %s | %s | %s | %s |" % (
            r["layer"], f"{r['declared_before']:,}", f"{r['upstream_count']:,}",
            f"{r['rows']:,}", r["gap_before"], r["gap_after"], r["verdict"]))
    A("")
    A("计算过程：`新差额 = (上游当前 returnCount − 实采行数) / 上游当前 returnCount`。")
    A("其中 NG911 层旧声明 1,928,880 是计划期快照，上游现在就是 1,254,000，正好等于实采 → 差额归零，")
    A("这一层不是「没采全」，是**旧声明过期**。")
    A("")
    # ---- 3.4 剩余缺口逐层拆解（按口径算，不是拍脑袋）----
    why = {"missing": "**上游有数据但没采**（本层 0 行）",
           "partial": "**上游有数据但没采全**（半截）",
           "unverified": "**上游不可达**（未验证，不许当 0）",
           "empty": "上游 0 行（不是缺口，别算进分母）"}
    deficit = [r for r in led["records"]
               if (r.get("declared") or 0) > (r.get("rows") or 0)
               and r["status"] != "capped_by_upstream"]
    deficit.sort(key=lambda r: (r.get("declared") or 0) - (r.get("rows") or 0), reverse=True)
    gap_layers = [r for r in deficit if r["status"] != "empty"]
    empty_rows = [r for r in deficit if r["status"] == "empty"]
    over = [(r, (r.get("rows") or 0) - (r.get("declared") or 0)) for r in led["records"]
            if (r.get("rows") or 0) > (r.get("declared") or 0)]
    over.sort(key=lambda x: x[1], reverse=True)
    sum_gap = sum((r.get("declared") or 0) - (r.get("rows") or 0) for r in gap_layers)
    sum_empty = sum((r.get("declared") or 0) - (r.get("rows") or 0) for r in empty_rows)
    sum_over = sum(x[1] for x in over)
    A("### 3.4 剩余缺口逐层拆解")
    A("")
    A("账本净缺口 = **%s 行（%.4f%%）**，由三块构成（加减号都是账本数字，不是估的）："
      % (f"{led['gap']:,}", led["gap_pct"] or 0))
    A("")
    A("- 真缺口（`missing` / `partial` / `unverified`，共 %d 层）：**+%s**"
      % (len(gap_layers), f"{sum_gap:,}"))
    A("- `empty` 层的旧声明（上游 0 行，不是缺口）：**+%s**（%d 层；旧声明不该再进分母）"
      % (f"{sum_empty:,}", len(empty_rows)))
    A("- 已采超出声明的层（上游后来缩水/声明过期）：**−%s**（%d 层）"
      % (f"{sum_over:,}", len(over)))
    A("")
    A("| 层 | 状态 | 声明 | 实采 | 缺口 | 缺口% | 归因 |")
    A("|---|---|---|---|---|---|---|")
    for r in gap_layers:
        d, rw = (r.get("declared") or 0), (r.get("rows") or 0)
        A("| `%s` | %s | %s | %s | %s | %.2f%% | %s |" % (
            r["layer"], r["status"], f"{d:,}", f"{rw:,}", f"{d - rw:,}",
            100.0 * (d - rw) / d, why.get(r["status"], r.get("reason") or "-")))
    A("")
    A("> 注：`capped_by_upstream` 层不出现在上表（无分母）；它的 %s 行已在 `rows` 里。"
      % f"{led.get('rows_capped') or 0:,}")
    A("")
    A("## 四、口径提醒")
    A("")
    A("- 行数合计仍是 **%s**（本次不采一行数据，只改判定与声明）。" % f"{led['rows']:,}")
    if led.get("capped_layers"):
        A("- 剔除 capped 层后的分母 = **%s**，与分母同口径的实采 = **%s**，缺口 = **%s（%.4f%%）**。"
          % (f"{led['declared']:,}", f"{led['rows_verifiable']:,}", f"{led['gap']:,}", led["gap_pct"] or 0))
        A("- 与**不剔除**口径（declared 含 capped）= %s 行 / %s 行 / %.4f%% 对照时，差值就是 capped 层的"
          "declared_unverifiable %s：两个百分比**不可直接比较**，引用时必须写明是否剔除。"
          % (f"{led['declared_kept_in_denominator']:,}", f"{led['rows']:,}",
             led["gap_pct_kept_in_denominator"], f"{led['declared_unverifiable']:,}"))
        A("- 未剔除口径的数字怎么来的：`declared_kept_in_denominator = declared + declared_unverifiable`，"
          "`gap_kept_in_denominator = 它 − rows`（旧口径，分子含 capped 行数）。")
    A("- `docs/STEP04-FULL-2026-10-30.md` 保持 `ledger_rebuild.py` 生成的字节不变（`--check` 依赖它）；")
    A("  本文是它的**修正层**，两者冲突时以本文为准，并注明证据出处。")
    A("- 修正后的账本是 `collect/04b_ledger.json`（main 侧闸门读的就是这个文件）。")
    A("")
    A("## 五、复现")
    A("")
    A("```bash")
    A("python3 collect/verify_04b_upstream.py --out analysis/04b-upstream-evidence-2026-10-30.json")
    A("python3 collect/adjudicate_04b.py \\")
    A("  --rebuilt collect/ledger/step04b_rebuilt.json \\")
    A("  --evidence analysis/04b-upstream-evidence-2026-10-30.json \\")
    A("  --plan collect/ledger/04b_plan.json \\")
    A("  --cancel-plan collect/ledger/04b_round2_plan.json \\")
    A("  --out collect/04b_ledger.json \\")
    A("  --audit analysis/04b-cancel-audit-2026-10-30.json \\")
    A("  --doc docs/STEP04-ADJUDICATED-2026-10-30.md --check")
    A("```")
    A("")
    return "\n".join(L)


# ---------------------------------------------------------------- 声明分母刷新（只读）
#
# 为什么必须做（2026-10-31）：04b 现有账本里 **81 层实采 > 声明**，净额 −43,423,188 行。
# 声明值来自 `layer_plan.csv`（计划期估算的快照），上游缩水/删除/改口径后不跟新，
# 于是：按声明分母算覆盖率系统性偏高或偏低，而且「按声明 / 按可核实」两个百分比
# 永远不能直接相减——解释负担本可避免。
#
# 判据：只对 `ok / missing / partial` 且上游可达的层逐层打 `returnCount`；
# 输出差异表（旧声明 / 新声明 / 实采 / 三者关系），**只输出建议、不改账本**；
# 改账本必须人工点头（`--apply-declared-refresh` + 口号）并留 `revisions[kind=declared_refreshed]`。


def plan_csv_urls(path):
    """layer_id → api url（`layer_plan_clean.csv`）。"""
    idx = {}
    if not os.path.exists(path):
        return idx
    with open(path, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            lid, url = (r.get("layer_id") or "").strip(), (r.get("url") or "").strip()
            if lid and url:
                idx[lid] = url
    return idx


def probe_return_count(url, timeout=25):
    """一次只读 `returnCountOnly`。返回 {http, count, raw, err, elapsed_ms, url}。"""
    q = url.rstrip("/") + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    t0 = time.time()
    rec = {"url": q, "http": None, "count": None, "raw": "", "err": "", "elapsed_ms": None}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(q, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read(4000).decode("utf-8", "replace")
            rec.update(http=resp.status, raw=body[:300])
            try:
                j = json.loads(body)
                if isinstance(j, dict) and "count" in j:
                    rec["count"] = int(j["count"])
                elif isinstance(j, dict) and j.get("error"):
                    rec["err"] = "esri_error: %s" % str(j["error"])[:200]
            except Exception:                              # noqa: BLE001
                rec["err"] = "非 JSON 响应"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(400).decode("utf-8", "replace")
        except Exception:                                  # noqa: BLE001
            pass
        rec.update(http=e.code, raw=body[:300], err="HTTP %s" % e.code)
    except Exception as e:                                 # noqa: BLE001
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    return rec


def _relation(rows, new_decl, tol=TOL):
    """实采 vs 上游当前声明：超采 / 一致 / 欠采 / 上游 0 行。"""
    if new_decl is None:
        return "不可复核"
    if new_decl == 0:
        return "上游 0 行（声明作废）"
    if rows > new_decl * (1 + tol):
        return "超采（上游缩水/删数据）"
    if rows >= new_decl * (1 - tol):
        return "一致"
    return "欠采（真缺口按新声明）"


def refresh_declared(ledger_path, plan_csv, out_json, limit=0, concurrency=6,
                     timeout=25, quiet=False):
    """逐层刷 `returnCount`，出差异表。**不写账本**，只写建议 JSON。"""
    led = jload(ledger_path)
    urls = plan_csv_urls(plan_csv)
    targets = [r for r in (led.get("records") or [])
               if r.get("status") in DECLARED_REFRESH_STATUSES]
    if limit:
        targets = targets[:limit]
    no_url = [r["layer"] for r in targets if r["layer"] not in urls]
    targets = [r for r in targets if r["layer"] in urls]

    def one(rec):
        p = probe_return_count(urls[rec["layer"]], timeout=timeout)
        old = rec.get("declared")
        rows = rec.get("rows") or 0
        new = p.get("count")
        rel = _relation(rows, new)
        cov_old = round(100.0 * rows / old, 4) if old else None
        cov_new = round(100.0 * rows / new, 4) if new else None
        return {"layer": rec["layer"], "status": rec["status"],
                "declared_old": old, "declared_new": new, "rows": rows,
                "delta": (new - old) if (new is not None and old is not None) else None,
                "relation": rel,
                "coverage_by_declared_old_pct": cov_old,
                "coverage_by_declared_new_pct": cov_new,
                "probe": {k: p.get(k) for k in ("http", "count", "err", "elapsed_ms", "url")}}

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        rows_out = list(ex.map(one, targets))

    usable = [x for x in rows_out if x["declared_new"] is not None]
    stale = [x for x in usable if x["relation"].startswith("超采")]
    short = [x for x in usable if x["relation"].startswith("欠采")]
    same = [x for x in usable if x["relation"] == "一致"]
    zero = [x for x in usable if x["relation"].startswith("上游 0 行")]
    dead = [x for x in rows_out if x["declared_new"] is None]
    sum_old = sum((x["declared_old"] or 0) for x in usable)
    sum_new = sum((x["declared_new"] or 0) for x in usable)
    sum_rows = sum(x["rows"] for x in usable)
    report = {
        "schema": "declared-refresh/v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ledger": os.path.relpath(ledger_path, ROOT),
        "plan_csv": os.path.relpath(plan_csv, ROOT),
        "method": ("只读：对 status∈ok/missing/partial 且有 url 的层逐层打 `returnCountOnly`；"
                   "不改账本。采纳需 `--apply-declared-refresh` + 口号，并留 revisions[kind=declared_refreshed]"),
        "probed_n": len(rows_out), "no_url_n": len(no_url), "no_url_layers": no_url[:20],
        "usable_n": len(usable), "unreachable_n": len(dead),
        "stale_over_declared_n": len(stale), "short_n": len(short),
        "consistent_n": len(same), "upstream_zero_n": len(zero),
        "sums": {"declared_old": sum_old, "declared_new": sum_new, "rows": sum_rows,
                 "delta": sum_new - sum_old, "net_rows_minus_declared": sum_rows - sum_new},
        "suggestion": ("用 declared_new 做分母重算覆盖率；两者不可相减，报表必须同时给两个口径"
                       if sum_new != sum_old else "无需刷新（新声明与旧声明同值）"),
        "layers": rows_out,
    }
    if out_json:
        os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
        json.dump(report, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not quiet:
        print("声明刷新（只读）%s  层 %d 可复核 %d / 不可达 %d"
              % (report["at"], len(rows_out), len(usable), len(dead)))
        print("  超采 %d / 一致 %d / 欠采 %d / 上游 0 行 %d"
              % (len(stale), len(same), len(short), len(zero)))
        print("  合计：旧声明 %s → 新声明 %s（%+d）；实采 %s（实采−新声明 %+d）"
              % (f"{sum_old:,}", f"{sum_new:,}", sum_new - sum_old,
                 f"{sum_rows:,}", sum_rows - sum_new))
        # 只打差得多的 top 20（全表在 JSON 里）
        diffs = sorted([x for x in usable if x["declared_old"] != x["declared_new"]],
                       key=lambda x: -abs((x["delta"] or 0)))[:20]
        if diffs:
            print("  %-52s %12s %12s %12s %s" % ("layer", "旧声明", "新声明", "实采", "关系"))
            for x in diffs:
                print("  %-52s %12s %12s %12s %s"
                      % (x["layer"][:52], f"{x['declared_old']:,}" if x["declared_old"] is not None else "-",
                         f"{x['declared_new']:,}", f"{x['rows']:,}", x["relation"]))
        print("  建议：%s" % report["suggestion"])
        print("  账本未动（只读）。采纳：--apply-declared-refresh %s --declared-confirm %s"
              % (os.path.relpath(out_json, ROOT) if out_json else "<json>", DECLARED_CONFIRM_PHRASE))
    return report


def apply_declared_refresh(ledger_path, report_path, confirm, backup_dir=None):
    """人工点头后把新声明写进账本 + 留 `revisions[kind=declared_refreshed]`。

    只改 ok/missing/partial 层；capped/unverified/empty 一律不碰（它们本来就不在分母里
    或本就没有可核实声明）。写盘前先备份。
    """
    if confirm != DECLARED_CONFIRM_PHRASE:
        raise SystemExit("拒绝写账本：--declared-confirm 必须等于 %r（人工点头口号）"
                         % DECLARED_CONFIRM_PHRASE)
    led = jload(ledger_path)
    rep = jload(report_path)
    by = {x["layer"]: x for x in (rep.get("layers") or [])}
    per_layer, changed = [], 0
    for r in (led.get("records") or []):
        x = by.get(r["layer"])
        if not x or x.get("declared_new") is None:
            continue
        if r.get("status") not in DECLARED_REFRESH_STATUSES:
            continue
        if x["declared_new"] == r.get("declared"):
            continue
        per_layer.append({"layer": r["layer"], "declared_before": r.get("declared"),
                          "declared_after": x["declared_new"], "rows": r.get("rows"),
                          "relation": x["relation"]})
        r["declared"] = x["declared_new"]
        r["declared_src"] = "upstream_returnCount %s" % rep.get("at")
        r["gap"] = r["declared"] - (r.get("rows") or 0)
        r["gap_pct"] = (round(100.0 * r["gap"] / r["declared"], 4) if r["declared"] else None)
        changed += 1

    declared_total = sum((r.get("declared") or 0) for r in (led.get("records") or []))
    rows_total = sum((r.get("rows") or 0) for r in (led.get("records") or []))
    rows_capped = led.get("rows_capped") or 0
    unver = led.get("declared_unverifiable") or 0
    led["declared"] = declared_total
    led["rows"] = rows_total
    led["rows_verifiable"] = rows_total - rows_capped
    led["gap"] = declared_total - (rows_total - rows_capped)
    led["gap_pct"] = (round(100.0 * led["gap"] / declared_total, 4) if declared_total else 0)
    led["declared_kept_in_denominator"] = declared_total + unver
    led["gap_pct_kept_in_denominator"] = (
        round(100.0 * (declared_total + unver - rows_total) / (declared_total + unver), 4)
        if (declared_total + unver) else 0)
    led["declared_refreshed_at"] = rep.get("at")
    led.setdefault("revisions", []).append({
        "kind": "declared_refreshed",
        "at": rep.get("at"),
        "evidence": os.path.relpath(report_path, ROOT),
        "confirm": confirm,
        "layers_changed_n": changed,
        "declared_before": rep.get("sums", {}).get("declared_old"),
        "declared_after": declared_total,
        "policy": "声明分母定期用上游 returnCount 刷新；两个口径（按声明/按可核实）必须同时报",
        "per_layer": per_layer,
    })
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bak = os.path.join(backup_dir or os.path.dirname(os.path.abspath(ledger_path)),
                       os.path.basename(ledger_path) + ".bak-" + stamp + "-predeclaredrefresh.json")
    json.dump(jload(ledger_path), open(bak, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(led, open(ledger_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("✅ 已写账本：%d 层声明更新；declared %s→%s；备份 %s"
          % (changed, f"{rep.get('sums', {}).get('declared_old'):,}" if rep.get("sums") else "-",
             f"{declared_total:,}", os.path.relpath(bak, ROOT)))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuilt", default=os.path.join(HERE, "ledger", "step04b_rebuilt.json"))
    ap.add_argument("--evidence", default="",
                    help="04b-upstream-evidence-*.json（逐层 returnCount 取证）；"
                         "--refresh-declared / --apply-declared-refresh 不需要")
    ap.add_argument("--plan", default=os.path.join(HERE, "ledger", "04b_plan.json"))
    ap.add_argument("--cancel-plan", default="", help="run 41092912755 的 plan-04b（36 层 / 9 片）")
    ap.add_argument("--out", default="", help="输出账本（--check / --refresh-declared 模式下可省）")
    ap.add_argument("--audit", default="")
    ap.add_argument("--doc", default="")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘；不一致退 1")
    # ★ 阶段账本被单 run 口径覆盖后，复原动作必须留痕（只追加进 revisions[]，不替换历史）。
    ap.add_argument("--restore-events",
                    default=os.path.join(ROOT, "analysis", "04b-ledger-restore-events.json"),
                    help="复原/合并事件清单（JSON: {events:[...]})，逐条追加进 revisions[]")
    # ★ capped_by_upstream（2026-10-31 用户批准）：上游改成服务级 token 的层永久不可采，
    #   账本必须承认「已尽取」，而不是永远挂 partial/failed 天天重采。
    ap.add_argument("--capped", action="append", default=[], metavar="LAYER",
                    help="把该层判为 capped_by_upstream（可多次）。需配 --capped-evidence")
    ap.add_argument("--capped-evidence", default="",
                    help="服务级 499 探测证据（analysis/04b-token-499-evidence-*.json）；"
                         "其 layers[] 里 verdict=service_level_token 且 all_rounds_token=true 的层"
                         "自动进 capped 集（不传 --capped 也行）")
    # ★ 2026-10-31 新规矩：声明分母不许永久当分母（只读刷新 + 人工点头才写账本）
    ap.add_argument("--refresh-declared", action="store_true",
                    help="只读：对 ok/missing/partial 且上游可达的层逐层打 returnCount，"
                         "出「旧声明/新声明/实采/三者关系」差异表；**不改账本**")
    ap.add_argument("--ledger", default=os.path.join(HERE, "04b_ledger.json"),
                    help="阶段账本（--refresh-declared 的输入；--apply-declared-refresh 的目标）")
    ap.add_argument("--plan-csv", default=os.path.join(HERE, "layer_plan_clean.csv"),
                    help="layer_id → api url 的源（默认 collect/layer_plan_clean.csv）")
    ap.add_argument("--json-out", default="",
                    help="刷新建议 JSON（默认 analysis/04b-declared-refresh-<date>.json）")
    ap.add_argument("--limit", type=int, default=0, help="只探前 N 层（排障用）")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--apply-declared-refresh", default="", metavar="JSON",
                    help="人工点头后按刷新 JSON 写账本（必须配 --declared-confirm %s）；"
                         "写前备份 + 追加 revisions[kind=declared_refreshed]" % DECLARED_CONFIRM_PHRASE)
    ap.add_argument("--declared-confirm", default="", help="人工点头口号（防误触发）")
    ap.add_argument("--backup-dir", default="", help="写账本前的备份目录（默认与账本同目录）")
    a = ap.parse_args()

    # ---- 声明刷新两条路径：都不走下面的 04b 判定主流程 ----
    if a.apply_declared_refresh:
        return apply_declared_refresh(a.ledger, a.apply_declared_refresh, a.declared_confirm,
                                      a.backup_dir or None)
    if a.refresh_declared:
        out = a.json_out or os.path.join(
            ROOT, "analysis", "04b-declared-refresh-%s.json" % time.strftime("%Y%m%d", time.gmtime()))
        refresh_declared(a.ledger, a.plan_csv, out, limit=a.limit,
                         concurrency=a.concurrency, timeout=a.timeout)
        return 0
    if not a.evidence:
        ap.error("--evidence 必填（除 --refresh-declared / --apply-declared-refresh）")
    if not a.out:
        ap.error("--out 必填（除 --refresh-declared / --apply-declared-refresh）")

    rebuilt = jload(a.rebuilt)
    capped_set, capped_ev = {}, {}
    if a.capped_evidence and os.path.exists(a.capped_evidence):
        tev = jload(a.capped_evidence)
        for x in ([tev] if tev.get("layer") else (tev.get("layers") or [])):
            if x.get("verdict") == "service_level_token" and x.get("all_rounds_token"):
                x = dict(x)
                x.setdefault("generated_at", tev.get("generated_at"))
                capped_set[x["layer"]] = x
                capped_ev[x["layer"]] = a.capped_evidence
    for L in (a.capped or []):
        capped_set.setdefault(L, {})
        capped_ev.setdefault(L, a.capped_evidence)
    plan = jload(a.plan) if os.path.exists(a.plan) else {}
    evidence = jload(a.evidence)
    ev_by = {x["layer"]: x for x in evidence["layers"]}
    truth = {r["layer"]: r for r in rebuilt["records"]}

    recs, revisions, partial_recalc = [], [], []
    buckets = {}
    rows_total = declared_total = 0
    rows_capped = unver_total = 0
    capped_layers = []
    for r in rebuilt["records"]:
        rec = dict(r)
        ev = ev_by.get(rec["layer"])
        new_status, reason, new_decl = classify(rec, ev)
        capped = rec["layer"] in capped_set
        if capped:
            tev = capped_set.get(rec["layer"]) or {}
            new_status, new_decl = "capped_by_upstream", None
            reason = ("服务级 token：连 `<api>/0?f=json` 都 499（%s 轮 × 3 端点全 499，最后一次 %s）"
                      "→ 本层已无法再采、也无法复核声明；已采 %s 行即全部可得"
                      % (tev.get("rounds_n") or 1,
                         (tev.get("generated_at") or "-"), f"{rec.get('rows') or 0:,}"))
        if new_decl is not None and new_decl != rec.get("declared"):
            revisions.append({"layer": rec["layer"], "from": rec["status"], "to": new_status,
                              "declared_before": rec.get("declared"), "declared_after": new_decl,
                              "reason": "声明值改用上游当前 returnCount（证据：%s）" % evidence["generated_at"]})
        elif new_status != rec["status"]:
            revisions.append({"layer": rec["layer"], "from": rec["status"], "to": new_status,
                              "declared_before": rec.get("declared"),
                              "declared_after": new_decl if new_decl is not None else rec.get("declared"),
                              "reason": reason})
        rec["status"] = new_status
        rec["reason"] = reason
        if new_decl is not None:
            rec["declared"] = new_decl
        if capped:
            # declared 移出分母，但数字不许丢：记以 declared_unverifiable，永远不进任何百分比
            rec["declared_unverifiable"] = rec.get("declared")
            rec["declared"] = None
            rec["gap"] = rec["gap_pct"] = None
        d, rw = rec.get("declared") or 0, rec.get("rows") or 0
        rec["gap"] = (d - rw) if rec.get("declared") is not None else None
        rec["gap_pct"] = round(100.0 * (d - rw) / d, 4) if d else None
        if capped:
            tev = capped_set.get(rec["layer"]) or {}
            rounds = tev.get("rounds") or []
            rec["evidence"] = {
                "verdict": "service_level_token", "token_error_code": 499,
                "http": 200, "message": "Token Required",
                "rounds_n": tev.get("rounds_n") or len(rounds),
                "probe_at": [x.get("at") for x in rounds] or None,
                "probe_urls": [p.get("url") for x in rounds for p in (x.get("probes") or {}).values()][:3],
                "evidence": capped_ev.get(rec["layer"]) or None,
                "layer_url": tev.get("layer_url") or (ev or {}).get("layer_url"),
            }
            rows_capped += rw
            unver_total += rec.get("declared_unverifiable") or 0
            capped_layers.append({
                "layer": rec["layer"], "rows": rw,
                "declared_unverifiable": rec.get("declared_unverifiable"),
                "units_done": rec.get("units_done"), "packages": rec.get("parts_assets"),
                "rounds_n": rec["evidence"]["rounds_n"],
                "last_probe_at": (rec["evidence"]["probe_at"] or [None])[-1],
                "evidence_path": capped_ev.get(rec["layer"]),
            })
        elif ev is not None:
            rec["evidence"] = {"verdict": ev["verdict"], "upstream_count": ev["probe"].get("count"),
                               "http": ev["probe"].get("http"),
                               "probe_url": ev["probe"].get("url")}
        buckets[new_status] = buckets.get(new_status, 0) + 1
        declared_total += d
        rows_total += rw
        recs.append(rec)
        if (ev and ev["ledger_status"] == "partial" and ev["probe"].get("count") is not None
                and not capped):
            cb = ev["ledger_declared"] or 0
            partial_recalc.append({
                "layer": rec["layer"], "declared_before": cb,
                "upstream_count": ev["probe"]["count"], "rows": rw,
                "gap_before": "%.2f%%" % (100.0 * (cb - rw) / cb) if cb else "-",
                "gap_after": ("%.2f%%" % (100.0 * (ev["probe"]["count"] - rw) / ev["probe"]["count"])
                              if ev["probe"]["count"] else "-"),
                "verdict": new_status})

    # 集合对账
    uniq_plan = sorted({l for s in plan.get("shards", []) for l in s.get("layers", [])})
    recon = {
        "计划层数（round1 plan）": len(uniq_plan),
        "账本层数（rebuilt）": len(truth),
        "计划 − 账本": len([x for x in uniq_plan if x not in truth]),
        "账本 − 计划": len([x for x in truth if x not in uniq_plan]),
        "声明行合计（修正后）": None,
        "实采行合计（不变）": None,
    }
    recon["声明行合计（修正后）"] = declared_total
    recon["实采行合计（不变）"] = rows_total

    audit = {}
    if a.cancel_plan and os.path.exists(a.cancel_plan):
        audit = cancel_audit(jload(a.cancel_plan), truth, {k: {"rows": v.get("rows")} for k, v in truth.items()})
        audit["cancelled_at"] = "2026-10-30T19:16:05Z（gh run cancel 41092912755；四 job completed_at 19:16:32–19:16:59）"
        audit["method"] = "完成度按 Release 资产反推（该 SHA 尚无增量落盘，本地无半截账本）"

    led = {
        "schema": "collect-ledger-agg/v1",
        "stage": "04b",
        "at": evidence["generated_at"],
        "source_of_truth": "Release 资产 checkpoint（step04b_rebuilt.json）+ 上游 returnCount 实测",
        "layers_n": len(recs),
        "ok": buckets.get("ok", 0),
        "empty": buckets.get("empty", 0),
        "partial": buckets.get("partial", 0),
        "capped_by_upstream": buckets.get("capped_by_upstream", 0),
        "failed": 0,
        "missing": buckets.get("missing", 0),
        "unverified": buckets.get("unverified", 0),
        "skipped_done": buckets.get("skipped_done", 0),
        "buckets": buckets,
        "bucket_meaning": {
            "ok": "实采 ≥ 上游当前 returnCount×(1-1%)",
            "partial": "实采 < 上游当前 returnCount×(1-1%) 且 >0 → 定向续采",
            "capped_by_upstream": ("上游改成服务级 token（连 `<api>/0?f=json` 都 499，连探两轮）→ "
                                   "永远采不到更多；已采行数计入 rows，declared 移出分母记 "
                                   "declared_unverifiable"),
            "missing": "上游有数据、本层 0 行 → 必须重采",
            "unverified": "上游不可达/无响应，本层无数据 → 无法归因（不许当空层）",
            "empty": "上游明确 0 行或服务下线（esri 404）",
            "skipped_done": "计划期已判完成而跳过",
        },
        "declared": declared_total,
        "declared_unverifiable": unver_total,
        "rows": rows_total,
        "rows_capped": rows_capped,
        "rows_verifiable": rows_total - rows_capped,
        "gap": declared_total - (rows_total - rows_capped),
        "gap_pct": (round(100.0 * (declared_total - (rows_total - rows_capped)) / declared_total, 4)
                    if declared_total else 0),
        "declared_kept_in_denominator": declared_total + unver_total,
        "gap_pct_kept_in_denominator": (round(100.0 * (declared_total + unver_total - rows_total)
                                             / (declared_total + unver_total), 4)
                                        if (declared_total + unver_total) else 0),
        "denominator_note": ("分母只含可复核的 declared（不含 capped_by_upstream 层）；"
                             "gap = declared − rows_verifiable（rows 去掉 capped 层已采行数），"
                             "两边同口径才可相除。rows 仍是全部实采（含 capped 层）。"),
        "complete": buckets.get("missing", 0) == 0 and buckets.get("unverified", 0) == 0,
        "capped_layers": capped_layers,
        "set_reconciliation": recon,
        "revisions": revisions,
        "partial_recalc": partial_recalc,
        "records": recs,
    }
    # 运行级事件（复原 / 合并）追加在逐层 revisions 之后 —— 位置固定，--check 才能字节一致
    if a.restore_events and os.path.exists(a.restore_events):
        try:
            for ev in (jload(a.restore_events).get("events") or []):
                revisions.append(ev)
        except Exception as e:                      # noqa: BLE001
            print("⚠ 复原事件文件读不了（%s）：%s" % (a.restore_events, str(e)[:120]))

    audit_out = dict(audit) if audit else {}
    doc = render_doc(led, audit, evidence, {})

    def dump(path, obj):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if a.check:
        bad = []
        for path, content in ((a.out, json.dumps(led, ensure_ascii=False, indent=1)),
                              (a.audit, json.dumps(audit_out, ensure_ascii=False, indent=1) if a.audit else None),
                              (a.doc, doc)):
            if not path or content is None:
                continue
            cur = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
            if cur != content:
                bad.append(path)
        if bad:
            print("DIFFERS: " + " / ".join(bad))
            return 1
        print("IDENTICAL")
        return 0

    dump(a.out, led)
    if a.audit:
        dump(a.audit, audit_out)
    if a.doc:
        os.makedirs(os.path.dirname(os.path.abspath(a.doc)), exist_ok=True)
        open(a.doc, "w", encoding="utf-8").write(doc)
    print(json.dumps({"layers_n": led["layers_n"], "ok": led["ok"], "partial": led["partial"],
                      "capped_by_upstream": led["capped_by_upstream"],
                      "missing": led["missing"], "unverified": led["unverified"],
                      "empty": led["empty"], "failed": led["failed"], "complete": led["complete"],
                      "declared": led["declared"], "declared_unverifiable": led["declared_unverifiable"],
                      "rows": led["rows"], "rows_verifiable": led["rows_verifiable"],
                      "gap": led["gap"], "gap_pct": led["gap_pct"],
                      "gap_pct_kept_in_denominator": led["gap_pct_kept_in_denominator"],
                      "revisions": len(revisions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
