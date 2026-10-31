#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""07b 收口判官：把 `failed` 按**证据**归到四类，让阶段账本「failed=0」而不是「假装采完了」。

为什么要有它（2026-10-31 用户决定，与 04b 同一套办法）：
  run `41184978867` 3/3 片收工、`shards_incomplete=[]`，但账本里还剩 2 层 `failed`，
  阶段 `gap` 只有 **3,988 行（0.38%）**。为这 3,988 行再烧一轮 CI 不划算，
  但「留一个 failed=30 的账本」和「把 failed 悄悄改成 ok」都不行：
    · 留着 → 每次收口都得人肉解释「这 2 层到底算不算欠账」；
    · 改成 ok → 就是自己灌水（W33-033 / W33-037 都踩过）。
  所以：**按失败证据归四类**，每类给出「层数 / 声明 / 已采 / 缺口 / 下一步」，
  账本 `failed` 归零但缺口一分不少地挂在类目里。

四类的判据（**只看已落账的证据，不猜上游**；判序即判据）：
  · `unverified`       —— 失败是 **404 / HTML 页**：端点没了，无法核实（W33-027），有没行都一样
  · `upstream_unstable`—— 失败是 **单层超时 / 5xx / svcerr**：连得上但给不出数据，重试收益趋零
                          （W33-037 的判据在 07b 的落点）
  · `partial`          —— 其余情况但 `rows > 0`：有数据，缺口 = 声明 − 已采（能补、要补）
  · `missing`          —— `rows == 0` 且**没有上游明确拒绝的证据**（`err=?`）：还值得再试一次

为什么失败证据优先于「有没有行」：某层可能已经抓到 1600 行，但端点对后续分页返回 `svcerr 400`，
那时再排一轮仍会撞同一道墙（W33-037 的无限重试就是这样产生的）。
所以「能不能再拿到东西」比「现在手上有几行」更接近下一步该做什么；行数照旧按层记，
缺口一分不少（`gap_by_class` 逐类算 declared − rows）。

用法：
  # 只看会怎么判（不写盘）
  python3 collect/adjudicate_07b.py --dry-run
  # 落盘：账本 + 分类证据 + 收口文档
  python3 collect/adjudicate_07b.py
  # 自检：同样的输入必须得到同样的账本/证据/文档
  python3 collect/adjudicate_07b.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

SCHEMA_CLS = "collect-gap-classification/v1"
ADJ_KEY = "gap_class"

# 四类的固定顺序（文档表格、buckets 都用它，保证可复现）
CLASSES = ("partial", "upstream_unstable", "unverified", "missing")

RE_TIMEOUT = re.compile(r"单层超时|timed out|timeout|TimeoutError", re.I)
RE_5XX = re.compile(r"svcerr|\bhttp5\d\d\b|Service (Unavailable|Temporarily)|Wait timeout", re.I)
RE_GONE = re.compile(r"http404|\b404\b|<!DOCTYPE html|<div style=", re.I)


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def classify(rec) -> tuple:
    """返回 (class, 一句话理由)。**只读记录字段**，不联网、不看命令行。

    判序（即判据，改顺序就是改结论，改之前先看模块头注释）：
      404/HTML → 超时 → 5xx/svcerr → 有行 → 其余
    """
    rows = int(rec.get("rows") or 0)
    decl = int(rec.get("declared") or 0)
    blob = "%s %s" % (rec.get("reason") or "", rec.get("err") or "")
    if RE_GONE.search(blob):
        return "unverified", "端点 404/HTML 页：服务没了或路径变了，无法核实（W33-027）"
    if RE_TIMEOUT.search(blob):
        return "upstream_unstable", "单层超时：连得上但给不出数据，再试一轮仍是同一个超时"
    if RE_5XX.search(blob):
        return "upstream_unstable", "上游 5xx/svcerr：服务端报错，重试收益趋零"
    if rows > 0:
        if decl and rows >= decl:
            return "partial", ("已采 %s 行 ≥ 声明 %s 行（超采 %s 行），只是状态没收敛——不用再采"
                               % (f"{rows:,}", f"{decl:,}", f"{rows - decl:,}"))
        gap = (decl - rows) if decl else 0
        return "partial", ("有数据（%s 行），缺口 %s 行——能补、要补，不是 failed"
                           % (f"{rows:,}", f"{max(0, gap):,}"))
    return "missing", "0 行且无上游明确拒绝的证据（err=?）——还值得再试一次"


def build_classification(ledger, attempt_log=None):
    """从阶段账本里挑出 failed/partial 的层，逐层判类。返回证据文档（可直接落盘）。"""
    layers = (attempt_log or {}).get("layers") or {}
    items, counts = [], {c: 0 for c in CLASSES}
    for rec in ledger.get("records") or []:
        st = str(rec.get("status") or "")
        was = str(rec.get("status_before_adjudication") or "")
        # 已改判过的账本要能重新算出同一份结果（--check 幂等）：原始状态记在
        # status_before_adjudication 里，否则第二次跑就看不到那些层了。
        if st not in ("failed", "partial") and was not in ("failed", "partial"):
            continue
        cls, why = classify(rec)
        lid = rec["layer"]
        a = layers.get(lid) or {}
        items.append({
            "layer": lid,
            "from_status": was or st,
            "class": cls,
            "reason": why,
            "rows": rec.get("rows"),
            "declared": rec.get("declared"),
            "elapsed_s": rec.get("elapsed_s"),
            "attempts_n": a.get("attempts_n"),
            "failure_kinds": a.get("kinds") or [],
            "attempts_elapsed_min": a.get("elapsed_min"),
        })
        counts[cls] += 1
    items.sort(key=lambda x: (CLASSES.index(x["class"]), -(x.get("elapsed_s") or 0), x["layer"]))
    return {"schema": SCHEMA_CLS, "stage": "07b", "at": ledger.get("at"),
            "run_id": (ledger.get("last_merge") or {}).get("run_id"),
            "rule": "判序即判据：404/HTML → unverified；超时 / 5xx·svcerr → upstream_unstable；"
                    "其余有行 → partial；0 行且无上游证据 → missing。不猜上游。",
            "counts": counts, "layers_n": len(items), "layers": items}


def apply(ledger, classification):
    """把判类结果写回账本的**逐层状态**并重算汇总。返回新账本（不改入参）。"""
    cls_of = {x["layer"]: x for x in classification["layers"]}
    out = json.loads(json.dumps(ledger))          # 深拷贝，避免调用方看到中间态
    touched = 0
    for rec in out.get("records") or []:
        x = cls_of.get(rec["layer"])
        if not x:
            continue
        before = str(rec.get("status") or "")
        if before not in ("failed", "partial") and str(rec.get("status_before_adjudication") or "") \
                not in ("failed", "partial"):
            raise SystemExit("::error::分类证据点了不该改的层（%s 当前 %s）：只允许改 failed/partial"
                             % (rec["layer"], before))
        if not rec.get("status_before_adjudication"):
            rec["status_before_adjudication"] = before
        rec[ADJ_KEY] = x["class"]
        rec["gap_reason"] = x["reason"]
        rec["status"] = x["class"]
        rec["adjudicated_at"] = classification["at"]
        rec["adjudicated_by"] = "adjudicate_07b.py"
        if x["class"] != before:
            touched += 1
    # 汇总重算（口径：buckets 覆盖全部层级状态，failed 必须是 0）
    recs = out.get("records") or []
    buckets = {c: 0 for c in ("ok", "capped_by_upstream", "partial", "upstream_unstable",
                              "missing", "unverified", "empty", "failed")}
    for r in recs:
        st = str(r.get("status") or "")
        buckets[st] = buckets.get(st, 0) + 1
    for k, v in buckets.items():
        out[k] = v
    out["buckets"] = dict(buckets)
    out["layers_n"] = len(recs)
    out["adjudicated_at"] = classification["at"]
    out["adjudicated_by"] = "adjudicate_07b.py"
    out["adjudicated_layers"] = len(cls_of)
    out["gap_by_class"] = gap_by_class(recs, cls_of)
    return out


def gap_by_class(recs, cls_of):
    """逐类给「层数 / 声明 / 已采 / 缺口」——对外必报四类归因，不许只报一个百分比。"""
    out = {}
    for c in CLASSES:
        mine = [r for r in recs if cls_of.get(r["layer"], {}).get("class") == c]
        declared = sum(int(r.get("declared") or 0) for r in mine)
        rows = sum(int(r.get("rows") or 0) for r in mine)
        out[c] = {"layers_n": len(mine),
                  "declared": declared,
                  "rows": rows,
                  "gap": max(0, declared - rows),
                  "declared_unknown_n": sum(1 for r in mine if not r.get("declared")),
                  "next": {"partial": "下一轮按层续跑（checkpoint 在，只补缺口）",
                           "upstream_unstable": "默认不排；要再试必须 --force-unstable-layer 点名",
                           "unverified": "端点已没了，等形态变化或人工复核，不复派",
                           "missing": "下一轮可直接重排（没有上游拒绝的证据）"}[c]}
    return out


def classify_gap(ledger):
    """阶段 gap 与「逐类缺口之和」对账，差异必须说清（多半来自超采层的负数）。"""
    recs = ledger.get("records") or []
    declared = sum(int(r.get("declared") or 0) for r in recs)
    rows = sum(int(r.get("rows") or 0) for r in recs)
    by_class = sum(v["gap"] for v in (ledger.get("gap_by_class") or {}).values())
    over = sum(max(0, int(r.get("rows") or 0) - int(r.get("declared") or 0)) for r in recs)
    return {"declared": declared, "rows": rows, "gap": max(0, declared - rows),
            "gap_by_class_sum": by_class, "over_collected_rows": over,
            "delta": max(0, declared - rows) - by_class}


# ---------------- 收口文档 ----------------
def render_doc(led, cls, run_id=""):
    g = led.get("gap_by_class") or {}
    dec = int(led.get("declared") or 0)
    rws = int(led.get("rows") or 0)
    gap = int(led.get("gap") or 0)
    pct = (gap / dec * 100) if dec else 0.0
    L = []
    A = L.append
    A("# STEP-07b 收口（2026-10-31）")
    A("")
    A("> 本文件由 `collect/adjudicate_07b.py` 从阶段账本 + 尝试账本**直接生成**，不许手改。")
    A("> 复核：`python3 collect/adjudicate_07b.py --check` → 必须 `IDENTICAL`。")
    A("")
    bf = next((r for r in (led.get("revisions") or [])
               if r.get("kind") == "stage_ledger_backfilled"), None)
    A("- 阶段账本：`collect/07b_ledger.json`（run `%s`%s）"
      % (run_id or (led.get("last_merge") or {}).get("run_id") or "-",
         "，含补账 %s 层" % bf.get("layers") if bf else ""))
    A("- 尝试账本：`analysis/07b-attempt-log.json`；判类证据：`analysis/07b-gap-classification-2026-10-31.json`")
    if bf:
        A("- 补账证据：`%s`（cancel 片账本丢失，按 Release 资产补回）" % bf.get("evidence"))
    A("")
    A("## 一、一句话结论")
    A("")
    A("> 07b **片全齐**（`shards_incomplete=%s`，%s/%s 片），**层不齐**：%d 层归入四类挂账，"
      "`failed` 归零。阶段缺口 **%s 行（%.2f%%）**，全部可归因到下面四类，没有「不知去向」的行。"
      % (json.dumps(led.get("shards_incomplete") or [], ensure_ascii=False),
         led.get("shards_reported"), led.get("shards_expected"),
         len(cls.get("layers") or []), f"{gap:,}", pct))
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 片 | `shards_expected=%s` / `shards_reported=%s` / `shards_incomplete=%s` |"
      % (led.get("shards_expected"), led.get("shards_reported"),
         json.dumps(led.get("shards_incomplete") or [], ensure_ascii=False)))
    A("| 层 | `layers_n=%s`（ok %s / empty %s / partial %s / upstream_unstable %s / unverified %s / missing %s / failed **%s**） |"
      % (led.get("layers_n"), led.get("ok"), led.get("empty"), led.get("partial"),
         led.get("upstream_unstable"), led.get("unverified"), led.get("missing"), led.get("failed")))
    A("| 行 | 声明 **%s** / 已采 **%s** / 缺口 **%s**（%.2f%%） |" % (f"{dec:,}", f"{rws:,}", f"{gap:,}", pct))
    A("")
    A("## 二、缺口的四类归因（对外必报这张表，不许只报百分比）")
    A("")
    A("| 类目 | 层数 | 声明 | 已采 | 缺口 | 下一步 |")
    A("|---|---|---|---|---|---|")
    name = {"partial": "`partial` 有数据但不足声明",
            "upstream_unstable": "`upstream_unstable` 上游给不出数据",
            "unverified": "`unverified` 端点已没了",
            "missing": "`missing` 没采到、无上游拒绝证据"}
    for c in CLASSES:
        v = g.get(c) or {}
        A("| %s | %s | %s | %s | %s | %s |" % (name[c], v.get("layers_n", 0),
                                              f'{v.get("declared", 0):,}',
                                              f'{v.get("rows", 0):,}',
                                              f'{v.get("gap", 0):,}', v.get("next", "")))
    A("| **合计** | **%s** | **%s** | **%s** | **%s** | |"
      % (len(cls.get("layers") or []),
         f'{sum((g.get(c) or {}).get("declared", 0) for c in CLASSES):,}',
         f'{sum((g.get(c) or {}).get("rows", 0) for c in CLASSES):,}',
         f'{sum((g.get(c) or {}).get("gap", 0) for c in CLASSES):,}'))
    A("")
    rec = classify_gap(led)
    A("对账：阶段 `gap` %s = 逐类缺口之和 %s + 差额 %s。"
      % (f'{rec["gap"]:,}', f'{rec["gap_by_class_sum"]:,}', f'{rec["delta"]:,}'))
    A("差额的来源是**超采层**（`rows > declared` 合计 %s 行）与**声明未知层**（超时/404 的层拿不到 "
      "`returnCount`，`declared` 记 0）—— 两者反方向抵消，所以逐类之和不会正好等于阶段 gap。"
      % f'{rec["over_collected_rows"]:,}')
    A("")
    if bf:
        bf_recs = [r for r in (led.get("records") or []) if r.get("backfilled_from")]
        A("## 二之二、补账（W33-013 尾巴：cancel 片账本随 job 丢失）")
        A("")
        A("- 来源：Release 资产（`ledger_rebuild.judge` 同一套 07b 判据），证据 `%s`" % bf.get("evidence"))
        A("- 补回 **%s 层**：`layers_n` **%s → %s**；逐层状态 %s。"
          % (bf.get("layers"), bf.get("layers_n_before"), bf.get("layers_n_after"),
             " / ".join("%s %d" % (s, sum(1 for r in bf_recs if r.get("status") == s))
                        for s in ("ok", "empty", "partial", "failed"))))
        A("- 只补 checkpoint 可证的层：`failed`（缺资产 / 单元未传 / 残留错误 / tag 不符）一律不补；"
          "每行带 `backfilled_from=release_assets`、`reason=ledger_row_lost_on_cancel`、"
          "`packages[]` 与 `evidence`（tag / 资产名 / sha256）。")
        A("- 口径：declared 与采集器同源（`layer_plan.csv` 唯一化后的 `expect`），"
          "rows = Σ`unit_rows_seen`；445 层里 1 层达到 checkpoint 计划但当前声明更高 → 记 `partial`"
          "（不把 13 万行缺口写成 ok）。")
        A("")
    A("## 三、逐层清单（层 / 原状态 / 类目 / 尝试次数 / 失败类型 / 累计耗时 / 行 / 理由）")
    A("")
    A("| 层 | 原状态 | 类目 | 尝试 | 失败类型 | 累计耗时(分) | rows | 声明 | 理由 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for x in cls.get("layers") or []:
        A("| `%s` | %s | **%s** | %s | %s | %s | %s | %s | %s |"
          % (x["layer"], x["from_status"], x["class"], x.get("attempts_n") or 0,
             "/".join(x.get("failure_kinds") or []) or "-",
             round(float(x.get("attempts_elapsed_min") or 0), 1),
             f'{x["rows"]:,}' if x.get("rows") is not None else "-",
             f'{x["declared"]:,}' if x.get("declared") else "-", x["reason"]))
    A("")
    A("## 四、下一步（用户 2026-10-31 决定）")
    A("")
    A("1. **07b 不再追**：%s 行不值得再烧一轮 CI。要补只能显式点名（`--force-layers` 或下一轮分批）。"
      % f"{gap:,}")
    A("2. 四类里只有 `partial`（%s 层 / %s 行缺口）值得续跑——checkpoint 在，只补缺口。"
      % ((g.get("partial") or {}).get("layers_n", 0), f'{(g.get("partial") or {}).get("gap", 0):,}'))
    A("3. `upstream_unstable`（%s 层）默认不进待采队列；要再试必须 `--force-unstable-layer` 点名。"
      % (g.get("upstream_unstable") or {}).get("layers_n", 0))
    A("4. `unverified`（%s 层）端点已经没了，等形态变化或人工复核，**不复派**。"
      % (g.get("unverified") or {}).get("layers_n", 0))
    A("5. 4-7 停车线：07b 是最后一站；**不许自动接 08 / 10b / 几何**。")
    A("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=os.path.join(ROOT, "collect", "07b_ledger.json"))
    ap.add_argument("--attempt-log", default=os.path.join(ROOT, "analysis", "07b-attempt-log.json"))
    ap.add_argument("--out-classification",
                    default=os.path.join(ROOT, "analysis", "07b-gap-classification-2026-10-31.json"))
    ap.add_argument("--doc", default=os.path.join(ROOT, "docs", "STEP07B-FINAL-2026-10-31.md"))
    ap.add_argument("--run-id", default="")
    ap.add_argument("--dry-run", action="store_true", help="只打印判类结果，不写盘")
    ap.add_argument("--check", action="store_true", help="只比对现有账本/证据/文档，不一致退 1")
    a = ap.parse_args()

    led = jload(a.ledger)
    log = jload(a.attempt_log) if os.path.exists(a.attempt_log) else {}
    cls = build_classification(led, log)
    new = apply(led, cls)
    doc = render_doc(new, cls, a.run_id)

    if a.dry_run:
        print(json.dumps({"counts": cls["counts"], "gap_by_class": new["gap_by_class"],
                          "buckets": new["buckets"]}, ensure_ascii=False, indent=1))
        return 0

    if a.check:
        bad = []
        if json.dumps(led, ensure_ascii=False, indent=1, sort_keys=False) != \
           json.dumps(new, ensure_ascii=False, indent=1, sort_keys=False):
            for r_old, r_new in zip(led.get("records") or [], new.get("records") or []):
                if json.dumps(r_old, ensure_ascii=False) != json.dumps(r_new, ensure_ascii=False):
                    bad.append("record %s: %s → %s" % (r_old.get("layer"), r_old.get("status"),
                                                       r_new.get("status")))
            bad.append("summary differs")
        cur_doc = open(a.doc, encoding="utf-8").read() if os.path.exists(a.doc) else ""
        if cur_doc != doc:
            bad.append("doc differs: %s" % a.doc)
        if os.path.exists(a.out_classification):
            cur_cls = jload(a.out_classification)
            if json.dumps(cur_cls, ensure_ascii=False, sort_keys=True) != \
               json.dumps(cls, ensure_ascii=False, sort_keys=True):
                bad.append("classification differs")
        if bad:
            print("::error::不一致（%d 处）：%s" % (len(bad), "; ".join(bad[:5])), file=sys.stderr)
            return 1
        print("IDENTICAL：账本 / 判类证据 / 收口文档 三者与重算一致")
        return 0

    json.dump(new, open(a.ledger, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(a.out_classification) or ".", exist_ok=True)
    json.dump(cls, open(a.out_classification, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(a.doc) or ".", exist_ok=True)
    open(a.doc, "w", encoding="utf-8").write(doc)
    print(json.dumps({"counts": cls["counts"], "buckets": new["buckets"],
                      "gap_by_class": new["gap_by_class"]}, ensure_ascii=False, indent=1))
    print("✅ 写盘：%s / %s / %s" % (a.ledger, a.out_classification, a.doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
