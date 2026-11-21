#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05b 缺口账重算：六类互斥、合计恒等于 layers_n（583）。

六类判据（写死，与 05b_gap_list.json 顶部 criteria 一致）：
  ok         已采 且 rows >= expect_live*(1-GAP_TOL)
  partial    已采 且 rows <  expect_live*(1-GAP_TOL)
  missing    未采(rows=null) 但有 expect_live 且没有任何「死/暂时」证据
  unverified 服务已死：404/500/no Query/not supported/TLS 失败/token required（含其他非 429 的 4xx）
  pending    暂时性失败：超时/429/连接重置/撞墙钟
  no_expect  probe 与重探都没拿到 expect（无分母），单列

口径要点：未采层按 expect_live **全额**计入缺口；rows 缺失一律 null，不填 0。
缺口 = Σ(expect_live − rows)，只对「有 expect_live」的层求和。

只读：不采集、不写采集账本、不动判据代码与 GAP_TOL。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(ROOT, "collect", "ledger")
GAP_F = os.path.join(LEDGER, "05b_gap_list.json")
RETRY_F = os.path.join(LEDGER, "05b_plan_probe_retry.json")
DECL_F = os.path.join(LEDGER, "05b_declared_by_layer.json")
MD_F = os.path.join(ROOT, "docs", "ng911-05b", "05b-gap-list.md")
ARTIFACT = os.path.join(LEDGER, "05b_plan.json")        # run 计划 artifact 副本（585 层）
PROBEPLAN = os.path.join(LEDGER, "step05b_plan.json")    # 探针计划（583 层）

DEAD_SIGNS = ("no query", "not supported", "token required", "invalid url", "unsupported",
              "certificate", "ssl", "tls")


def collections_breakdown(recs):
    from collections import Counter
    return Counter(r["class"] for r in recs if not r.get("has_denominator"))


def sha(f):
    return hashlib.sha256(open(f, "rb").read()).hexdigest() if os.path.exists(f) else ""


def probe_verdicts():
    """retry1 + retry2 的逐层判定；retry2 覆盖 retry1。"""
    v = {}
    if os.path.exists(RETRY_F):
        d = json.load(open(RETRY_F, encoding="utf-8"))
        for r in d.get("records") or []:
            v[r["layer"]] = {"verdict": r.get("verdict"), "http": r.get("http_code"),
                             "err": r.get("err") or "", "src": "retry1",
                             "expect_live": r.get("expect_live")}
        for r in (d.get("retry2") or {}).get("records") or []:
            v[r["layer"]] = {"verdict": r.get("verdict"), "http": r.get("http_code"),
                             "err": r.get("err") or "", "src": "retry2",
                             "expect_live": r.get("expect_live")}
    return v


def classify(rec, pv):
    rows = rec.get("rows")
    exp = rec.get("expect_live")
    p = pv.get(rec["layer"]) or {}
    if p.get("expect_live") is not None and exp is None:      # 重探 alive 回填
        exp = p["expect_live"]
        rec["expect_live"] = exp
        rec["expect_source"] = p["src"] + "-alive"
    pv_v = p.get("verdict")
    # 优先级：死亡证据 > 暂时性证据 > 数据实况(ok/partial/missing) > 无分母残差
    if pv_v == "unverified" or any(k in (p.get("err") or "").lower() for k in DEAD_SIGNS):
        return "unverified", exp
    if pv_v == "pending":
        return "pending", exp
    if rows is not None:
        return ("no_expect" if exp is None else
                ("ok" if rows >= exp * (1 - TOL) else "partial")), exp
    if exp is None:
        return "no_expect", exp              # 既无分母、也无任何判定证据
    return "missing", exp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=GAP_F)
    a = ap.parse_args()

    g = json.load(open(GAP_F, encoding="utf-8"))
    global TOL
    TOL = float(g.get("gap_tol") or 0.001)
    recs = g["records"]
    pv = probe_verdicts()
    # ★ rows 不许用 0 冒充：账本 parts=0 就是「一片都没落」= 未采 → rows 记 null
    led_f = os.path.join(ROOT, "collect", "05b_ledger.json")
    parts = {}
    if os.path.exists(led_f):
        for lr in json.load(open(led_f, encoding="utf-8")).get("records") or []:
            parts[lr.get("layer")] = int(lr.get("parts") or 0)
    fixed_zero = 0
    for r in recs:
        # 前一轮误抹的真数据回滚（rows_reported_by_ledger>0 表示当时是有数据的）
        if r.get("rows") is None and (r.get("rows_reported_by_ledger") or 0) > 0:
            r["rows"] = r.pop("rows_reported_by_ledger")
            r.pop("rows_fix", None)
            r["rows_note"] = "本轮 parts=0，rows 来自此前修订的已采数据（未清零）"
        if r.get("rows") == 0 and parts.get(r["layer"], 1) == 0:
            r.pop("rows", None)
            r["rows"] = None
            r["rows_fix"] = "账本 parts=0 且 rows=0（本轮一片都没落）→ 视为未采，rows 记 null，不用 0 冒充"
            fixed_zero += 1
        elif r.get("rows") and parts.get(r["layer"], 1) == 0:
            r["rows_note"] = "本轮 parts=0，rows 来自此前修订的已采数据（未清零）"

    order = ["ok", "partial", "missing", "unverified", "pending", "no_expect"]
    agg = {k: {"n": 0, "expect_live": 0, "rows": 0, "gap": 0, "rows_null": 0} for k in order}
    for r in recs:
        cls, exp = classify(r, pv)
        r["class"] = cls
        r["has_denominator"] = (exp is not None)   # expect_live 有值 = true，无值 = false
        rows = r.get("rows")
        r["gap_rows"] = None if exp is None else (exp - (rows or 0))
        r["gap_pct"] = None if (exp is None or not exp) else round(100.0 * ((exp - (rows or 0)) / exp), 3)
        p = pv.get(r["layer"]) or {}
        if cls in ("unverified", "pending"):
            r["evidence"] = "%s: http=%s %s" % (p.get("src") or "none", p.get("http"),
                                                (p.get("err") or "no count")[:140])
        else:
            r.pop("evidence", None)
        A = agg[cls]
        A["n"] += 1
        if exp is not None:
            A["expect_live"] += exp
        if rows is None:
            A["rows_null"] += 1
        else:
            A["rows"] += rows
        if r["gap_rows"] is not None:
            A["gap"] += r["gap_rows"]

    exp_total = sum(A["expect_live"] for A in agg.values())
    rows_total = sum(A["rows"] for A in agg.values())
    gap_total = sum(A["gap"] for A in agg.values())
    rows_with_expect = sum(r["rows"] or 0 for r in recs if r.get("rows") is not None and r.get("expect_live") is not None)
    rows_no_expect = sum(r["rows"] or 0 for r in recs if r.get("rows") is not None and r.get("expect_live") is None)
    gap_collected = sum(r["gap_rows"] or 0 for r in recs if r.get("rows") is not None and r.get("gap_rows") is not None)
    gap_uncollected = sum(r["gap_rows"] or 0 for r in recs if r.get("rows") is None and r.get("gap_rows") is not None)

    g["schema"] = "05b-gap-list/v2"
    g["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    g["criteria"] = {
        "ok": "已采 且 rows >= expect_live*(1-GAP_TOL)",
        "partial": "已采 且 rows < expect_live*(1-GAP_TOL)",
        "missing": "未采(rows=null) 但有 expect_live，且无「服务已死/暂时性」证据",
        "unverified": "服务已死：404/500/no Query/not supported/TLS 失败/token required（含其他非 429 的 4xx）",
        "pending": "暂时性：超时/429/连接重置/撞墙钟",
        "no_expect": "既没有 expect 分母、也没有任何死/暂时性判定证据（残差类，单列）",
        "priority": "互斥优先级：unverified > pending > (ok/partial/missing) > no_expect；"
                    "已采到数据但服务已死的层归 unverified（其 rows 计入 rows_total，因无分母不参与缺口恒等式）",
        "mutual_exclusive": True, "sum_equals": "layers_n（583）",
        "gap_rule": "gap = expect_live - rows；未采层按 expect_live 全额计入；rows 缺失记 null 不记 0",
        "gap_tol": TOL,
    }
    g["summary"] = {
        "layers_n": len(recs),
        "class_counts": {k: agg[k]["n"] for k in order},
        "class_counts_sum": sum(agg[k]["n"] for k in order),
        "class_totals": {k: {"expect_live": agg[k]["expect_live"], "rows": agg[k]["rows"],
                             "gap": agg[k]["gap"], "rows_null": agg[k]["rows_null"]} for k in order},
        "expect_live_total": exp_total,
        "rows_total": rows_total,
        "gap_total": gap_total,
        "gap_collected_layers": gap_collected,
        "gap_uncollected_layers": gap_uncollected,
        "rows_with_expect": rows_with_expect,
        "rows_no_expect": rows_no_expect,
        "reconcile": "expect_live_total(%d) - rows_with_expect(%d) = %d = gap_total(%d) → %s"
                     % (exp_total, rows_with_expect, exp_total - rows_with_expect, gap_total,
                        "自洽" if exp_total - rows_with_expect == gap_total else "不自洽"),
        "rows_note": "rows_total 含 %d 行属于「无分母(no_expect)」层，不参与缺口恒等式" % rows_no_expect,
    }
    g["provenance_declared"] = {
        "why_two_numbers": "两个 declared 总量来自不同计划文件，口径不同（run 计划 585 层 vs 探针计划 583 层），"
                           "**不合并、不抵消、不当 declared 用**",
        "run_plan_artifact": {"file": os.path.relpath(ARTIFACT, ROOT),
                              "declared_rows": json.load(open(ARTIFACT, encoding="utf-8")).get("declared_rows")
                              if os.path.exists(ARTIFACT) else None,
                              "layers_n": json.load(open(ARTIFACT, encoding="utf-8")).get("layers_n")
                              if os.path.exists(ARTIFACT) else None,
                              "sha256": sha(ARTIFACT),
                              "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                     time.gmtime(os.path.getmtime(ARTIFACT)))
                              if os.path.exists(ARTIFACT) else None,
                              "origin": "run 44865991911 的 plan-05b artifact（id 14692340122）落库副本"},
        "probe_plan": {"file": os.path.relpath(PROBEPLAN, ROOT),
                       "declared_rows": json.load(open(PROBEPLAN, encoding="utf-8")).get("declared_rows")
                       if os.path.exists(PROBEPLAN) else None,
                       "layers_n": json.load(open(PROBEPLAN, encoding="utf-8")).get("layers_n")
                       if os.path.exists(PROBEPLAN) else None,
                       "sha256": sha(PROBEPLAN),
                       "mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime(os.path.getmtime(PROBEPLAN)))
                       if os.path.exists(PROBEPLAN) else None,
                       "origin": "collect/full_plan.py 计划期产物（探针阶段所用）"},
        "delta_rows": (json.load(open(ARTIFACT, encoding="utf-8")).get("declared_rows", 0)
                       - json.load(open(PROBEPLAN, encoding="utf-8")).get("declared_rows", 0))
        if os.path.exists(ARTIFACT) and os.path.exists(PROBEPLAN) else None,
        "usage_ban": "declared 逐层不可得（artifact 无 expect_by_layer），任何 declared 总量**不得**当作逐层验收分母",
    }
    # ★ 顶层字段一律从 summary 派生，禁止留第二份常量（muse 2026-11-21 指出的 1,280,025 残留）
    g["total_gap_rows"] = gap_total
    g["total_expect_live"] = exp_total
    g["total_rows"] = rows_total
    g["no_denominator_n"] = sum(1 for r in recs if not r["has_denominator"])
    _nd = collections_breakdown(recs)
    g["no_denominator_note"] = (
        "has_denominator=false 共 %d 层 = unverified %d + pending %d + no_expect %d（差 %d 层）"
        % (sum(_nd.values()), _nd.get("unverified", 0), _nd.get("pending", 0),
           _nd.get("no_expect", 0), sum(_nd.values()) - sum(_nd.values())))
    g["verdict_counts"] = g["summary"]["class_counts"]
    g.pop("attribution_counts", None)

    tmp = a.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(g, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, a.out)

    # ---- 人读文档 ----
    S = g["summary"]
    L = ["# 05b 缺口清单（重算版 v2 · 六类互斥）", "",
         "## 口径（写死）", "",
         f"- **declared 不可得**：run 计划 artifact `plan-05b`（id 14692340122）里没有 `expect_by_layer`，"
         f"逐层 declared 一律 `null`，**不用总量或筛查产物倒推**。",
         f"- **分母 = expect_live**（`returnCountOnly@plan` 探针；重探 alive 回填的标 `retry*-alive`）。",
         f"- **缺口 = expect_live − rows**；**未采层按 expect_live 全额计入**，`rows` 记 `null` 不记 `0`。",
         f"- GAP_TOL = {TOL}（ok/partial 分界，未改动）。",
         "- 六类互斥，条数合计 = `layers_n`。", "",
         "## declared 两个总数并存（不合并、不抵消）", "",
         "| 来源文件 | declared_rows | layers_n | sha256 | 生成时间 |", "|---|---|---|---|---|"]
    for k in ("run_plan_artifact", "probe_plan"):
        d = g["provenance_declared"][k]
        L.append("| `%s` | %s | %s | `%s` | %s |" % (d["file"], d["declared_rows"], d["layers_n"],
                                                      (d["sha256"] or "")[:16], d["mtime"]))
    L += ["", "两者相差 %s 行（口径不同：run 计划 585 层 vs 探针计划 583 层 —— skip_done 刷掉 2 层）。"
          "**不猜哪份对，也不许把任一数当逐层 declared 用。**" % g["provenance_declared"]["delta_rows"], "",
          "## 六类汇总", "", "| 类 | 层数 | expect_live 合计 | rows 合计 | 缺口合计 | 其中 rows=null |",
          "|---|---|---|---|---|---|"]
    for k in order:
        A = S["class_totals"][k]
        L.append("| %s | %d | %s | %s | %s | %d |" % (k, S["class_counts"][k], f"{A['expect_live']:,}",
                                                      f"{A['rows']:,}", f"{A['gap']:,}", A["rows_null"]))
    L.append("| **合计** | **%d** | **%s** | **%s** | **%s** | |"
             % (S["class_counts_sum"], f"{S['expect_live_total']:,}", f"{S['rows_total']:,}", f"{S['gap_total']:,}"))
    L += ["", "## 三个总数字（自洽）", "",
          f"- expect_live_total = **{S['expect_live_total']:,}**",
          f"- rows_total = **{S['rows_total']:,}**",
          f"- gap_total = **{S['gap_total']:,}**（= expect_live_total {S['expect_live_total']:,} − 有分母层的 rows {S['rows_with_expect']:,}；{S['reconcile']}）",
          f"- 另有 {S['rows_no_expect']:,} 行来自「无分母」层，已计入 rows_total 但不参与缺口恒等式（{S['rows_note']}）",
          f"- 已采层缺口 = **{S['gap_collected_layers']:,}**（rows 有值的层）",
          f"- 未采层待采量 = **{S['gap_uncollected_layers']:,}**（rows=null 的层按 expect_live 全额）", "",
          "> 旧版「总缺口 1,280,025」只算了已采层的缺口，未采层的待采量没算 —— 已废弃。", ""]
    open(MD_F, "w", encoding="utf-8").write("\n".join(L))

    print("rows=0 改 null 的层:", fixed_zero)
    print("六类:", S["class_counts"], "sum=", S["class_counts_sum"])
    print("expect_live_total=%d rows_total=%d gap_total=%d" % (S["expect_live_total"], S["rows_total"], S["gap_total"]))
    print("已采层缺口=%d 未采层待采=%d %s" % (S["gap_collected_layers"], S["gap_uncollected_layers"], S["reconcile"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
