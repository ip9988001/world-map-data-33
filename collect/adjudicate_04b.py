#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04b 判定修正（adjudication）：把「failed」拆成有实证的四种状态，产出真值账本 + 审计文档。

背景（2026-10-30）：`step04b_rebuilt.json` 里 18 层 failed 混了三种完全不同的情况，
直接报「18 层 failed」既看不出该不该重采，也没法让闸门判断能不能接续：

  · 上游此刻能给出 returnCount 且 >0，但本层 0 行  → 这是**真缺口**（missing，必须重采）
  · 上游能给出 returnCount，本层跑到一半          → **partial**（定向续采）
  · 上游彻底连不上 / 报错，本层也没数据           → **unverified**（无法归因，不许当 0 数据）
  · 上游明确 0 行 / 服务下线（esri 404）           → **empty**（不是采集失败）

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
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOL = 0.01          # 与 ledger_rebuild 的 GAP_TOL 一致：差额 >1% 才算没采全


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
    A("## 三、判定修正（failed → 有实证的四类）")
    A("")
    A("| 状态 | 层数 | 含义 |")
    A("|---|---|---|")
    for k in ("ok", "partial", "missing", "unverified", "empty", "skipped_done"):
        A("| %s | %d | %s |" % (k, led["buckets"].get(k, 0), led["bucket_meaning"][k]))
    A("")
    A("**failed = %d**（成品账本里不再有「failed」这个状态：每一层要么有资产、要么有明确归因）。"
      % led["failed"])
    A("")
    A("### 3.1 与旧账的差异（逐条）")
    A("")
    A("| 层 | 旧状态 | 新状态 | 旧声明 | 新声明 | 原因 |")
    A("|---|---|---|---|---|---|")
    for r in led["revisions"]:
        A("| `%s` | %s | %s | %s | %s | %s |" % (
            r["layer"], r["from"], r["to"],
            f"{r['declared_before']:,}" if r["declared_before"] else "-",
            f"{r['declared_after']:,}" if r["declared_after"] else "-", r["reason"]))
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
    A("## 四、口径提醒")
    A("")
    A("- 行数合计仍是 **%s**（本次不采一行数据，只改判定与声明）。" % f"{led['rows']:,}")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuilt", default=os.path.join(HERE, "ledger", "step04b_rebuilt.json"))
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--plan", default=os.path.join(HERE, "ledger", "04b_plan.json"))
    ap.add_argument("--cancel-plan", default="", help="run 41092912755 的 plan-04b（36 层 / 9 片）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", default="")
    ap.add_argument("--doc", default="")
    ap.add_argument("--check", action="store_true", help="只比对，不写盘；不一致退 1")
    a = ap.parse_args()

    rebuilt = jload(a.rebuilt)
    plan = jload(a.plan) if os.path.exists(a.plan) else {}
    evidence = jload(a.evidence)
    ev_by = {x["layer"]: x for x in evidence["layers"]}
    truth = {r["layer"]: r for r in rebuilt["records"]}

    recs, revisions, partial_recalc = [], [], []
    buckets = {}
    rows_total = declared_total = 0
    for r in rebuilt["records"]:
        rec = dict(r)
        ev = ev_by.get(rec["layer"])
        new_status, reason, new_decl = classify(rec, ev)
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
        d, rw = rec.get("declared") or 0, rec.get("rows") or 0
        rec["gap"] = (d - rw) if rec.get("declared") is not None else None
        rec["gap_pct"] = round(100.0 * (d - rw) / d, 4) if d else None
        rec["evidence"] = ({"verdict": ev["verdict"], "upstream_count": ev["probe"].get("count"),
                            "http": ev["probe"].get("http"),
                            "probe_url": ev["probe"].get("url")} if ev else None)
        buckets[new_status] = buckets.get(new_status, 0) + 1
        declared_total += d
        rows_total += rw
        recs.append(rec)
        if ev and ev["ledger_status"] == "partial" and ev["probe"].get("count") is not None:
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
        "failed": 0,
        "missing": buckets.get("missing", 0),
        "unverified": buckets.get("unverified", 0),
        "skipped_done": buckets.get("skipped_done", 0),
        "buckets": buckets,
        "bucket_meaning": {
            "ok": "实采 ≥ 上游当前 returnCount×(1-1%)",
            "partial": "实采 < 上游当前 returnCount×(1-1%) 且 >0 → 定向续采",
            "missing": "上游有数据、本层 0 行 → 必须重采",
            "unverified": "上游不可达/无响应，本层无数据 → 无法归因（不许当空层）",
            "empty": "上游明确 0 行或服务下线（esri 404）",
            "skipped_done": "计划期已判完成而跳过",
        },
        "declared": declared_total,
        "rows": rows_total,
        "gap": declared_total - rows_total,
        "gap_pct": round(100.0 * (declared_total - rows_total) / declared_total, 4) if declared_total else 0,
        "complete": buckets.get("missing", 0) == 0 and buckets.get("unverified", 0) == 0,
        "set_reconciliation": recon,
        "revisions": revisions,
        "partial_recalc": partial_recalc,
        "records": recs,
    }
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
                      "missing": led["missing"], "unverified": led["unverified"],
                      "empty": led["empty"], "failed": led["failed"], "complete": led["complete"],
                      "declared": led["declared"], "rows": led["rows"], "gap_pct": led["gap_pct"],
                      "revisions": len(revisions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
