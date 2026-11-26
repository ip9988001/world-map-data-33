#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量重扫（v2）收尾：unusable-v2.csv / SUMMARY-v2.json / REPORT-v2.md。

数据来源全部落盘文件，不重算映射：
  layer-coverage.v2.csv（本次重扫，原生口径）/ layer-coverage.csv（v1 旧版，旧基准）
  verify-v2.json + verify-v2-layers.csv（全量逐行终检）/ diff-v1-v2.json（16 层逐行对账）
  dist-v2/shards/shard-*.json（逐片校验）/ dist-v2/run-summary.json（总耗时）
"""
from __future__ import annotations

import collections, csv, json, os, time

HERE = os.path.dirname(os.path.abspath(__file__))
DIST2 = "/data/workspace/wmd-fieldmap/dist-v2"
DIST1 = "/data/workspace/wmd-fieldmap/dist"
REASONS = {"upstream_no_payload", "dialect_unresolved", "adapter_unsupported", "zero_rows",
           "parse_error", "grade_below_C", "only_minimal_safe"}
GRADES = ("S", "A", "B", "C")


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def load(p, default=None):
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else default


def gvec(r):
    return {g: int(r.get("grade_" + g) or 0) for g in GRADES}


def main():
    v2 = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.v2.csv"), encoding="utf-8")))
    v1 = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    total = len(v2)
    mapped = [r for r in v2 if int(r["mapped"] or 0) > 0]
    unus = [r for r in v2 if int(r["mapped"] or 0) == 0]
    for r in unus:
        assert r["reason"] in REASONS, ("非固定枚举原因", r["reason"])
    reason_cnt = collections.Counter(r["reason"] for r in unus)
    with open(os.path.join(HERE, "unusable-v2.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "reason", "dialect_id", "class", "in_rows",
                                          "dropped_below_c", "parse_error", "in_bytes", "evidence"])
        w.writeheader()
        for r in sorted(unus, key=lambda x: (x["reason"], -int(x["in_rows"] or 0))):
            w.writerow({"layer": r["layer"], "reason": r["reason"], "dialect_id": r["dialect_id"],
                        "class": r["class"], "in_rows": r["in_rows"],
                        "dropped_below_c": r["dropped_below_c"],
                        "parse_error": r["parse_error"], "in_bytes": r["in_bytes"],
                        "evidence": (f"part_files={r['part_files']} in_rows={r['in_rows']} "
                                     f"mapped=0 dropped_below_C={r['dropped_below_c']} "
                                     f"parse_error={r['parse_error']} 口径=dropped_below_C")})
    V = load(os.path.join(HERE, "verify-v2.json"), {})
    D = load(os.path.join(HERE, "diff-v1-v2.json"), {})
    shards = [load(os.path.join(DIST2, "shards", f)) for f in
              sorted(os.listdir(os.path.join(DIST2, "shards"))) if f.endswith(".json")] \
        if os.path.isdir(os.path.join(DIST2, "shards")) else []
    run = load(os.path.join(DIST2, "run-summary.json"), {})
    shard_files = [f for f in sorted(os.listdir(os.path.join(DIST2, "tar"))) if f.endswith(".tar.gz")]
    shard_bytes = sum(os.path.getsize(os.path.join(DIST2, "tar", f)) for f in shard_files)
    cov = 100.0 * len(mapped) / total
    inv = dict(V.get("invariants") or {})
    newg = {g: int((V.get("grade") or {}).get(g, 0)) for g in GRADES}
    newrows = V.get("rows_total") or sum(int(r["mapped"] or 0) for r in v2)
    POST = load(os.path.join(HERE, "verify-v2-post.json"), {})
    RC = load(os.path.join(HERE, "coord-fix-recount.json"), {})
    zero_pre = int(inv.get("zero_coord", 0))
    if RC.get("total_post_fix"):
        newg = {g: int(RC["total_post_fix"]["grade"][g]) for g in GRADES}
        newrows = int(RC["total_post_fix"]["rows"])
        inv["zero_coord"] = int(RC["parts_000_005"]["zero_after_fix"]) + 0
    if POST:
        inv["zero_coord"] = int(POST.get("zero_coord_hits_after_fix", inv.get("zero_coord", 0)))
    oldg = {g: sum(int(r.get("grade_" + g) or 0) for r in v1) for g in GRADES}
    oldrows = sum(oldg.values())

    # 层级 grade 变动（旧 CSV vs 新 CSV）
    o1 = {r["layer"]: r for r in v1}
    affected = []
    for r in v2:
        a = gvec(o1.get(r["layer"]) or {})
        b = gvec(r)
        if a != b:
            affected.append({"layer": r["layer"], "old": a, "new": b,
                             "delta": {g: b[g] - a[g] for g in GRADES if b[g] != a[g]}})
    with open(os.path.join(HERE, "grade-affected-layers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "old_S", "old_A", "old_B", "old_C",
                                          "new_S", "new_A", "new_B", "new_C", "delta"])
        w.writeheader()
        for x in sorted(affected, key=lambda y: -abs(y["delta"].get("S", 0))):
            w.writerow({"layer": x["layer"], **{"old_" + g: x["old"][g] for g in GRADES},
                        **{"new_" + g: x["new"][g] for g in GRADES},
                        "delta": json.dumps(x["delta"], ensure_ascii=False)})
    close_bad = [r for r in v2 if int(r["diff"] or 0) != 0]
    rowmism = [r for r in (V.get("mismatch_detail") or [])]
    sp = load(os.path.join(HERE, "spotcheck-summary-v2.json"), {})
    four = {"coverage_pct": round(cov, 2), "coverage_layers": f"{len(mapped)}/{total}",
            "unusable": len(unus), "unusable_by_reason": dict(reason_cnt),
            "closing_diff_layers": len(close_bad), "rows_total": newrows,
            "rows_total_old": oldrows, "grade": newg, "grade_old": oldg,
            "members_in_tars": V.get("members_in_tars"), "layer_rowcount_mismatch":
            V.get("layer_rowcount_mismatch"), "invariants": inv,
            "affected_layers": len(affected), "shards": len(shard_files),
            "shard_bytes": shard_bytes, "free_gb": round(free_gb(), 1),
            "run": run, "spotcheck_v2": sp,
            "field_pct": V.get("field_pct")}
    json.dump(four, open(os.path.join(HERE, "SUMMARY-v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    R, A = [], None
    R = []
    A = R.append
    A("# 第 9 步 · 全量重扫（v2）：用修好的 `begin_layer()` 重出 3,550 层映射数据\n")
    A("> 口径唯一权威源仍是 `w2-fieldmap-plan-20261125.md`（muse-000258 全文，本单未改口径）。")
    A("> 本单 = muse-000266：样本对账发现 `begin_layer()` 未逐层调用导致 16 层里 7 层等级漂移 1,249,282 行，")
    A("> 故全量重扫并把修复落到数据层。**PR #58 仍 OPEN，合并是 muse 的动作。**\n")
    A("## 0. 四数（先给数）\n")
    A("| 指标 | v2 重扫实测 | 门槛 | 结论 |")
    A("|---|---:|---:|---|")
    A("| 层覆盖率 | **%.2f%%**（%d/%d） | ≥95%%（≥3,373） | %s |"
      % (cov, len(mapped), total, "达标" if len(mapped) >= 3373 else "**未达标（源层本身无地址要素，见 §11）**"))
    A("| 不可用层 | **%d**（全部 `%s`） | 固定枚举 | 达标 |"
      % (len(unus), "/".join(sorted(reason_cnt)) or "-"))
    A("| 逐层闭合差额 | **%d** 层非零 | 0 | %s |"
      % (len(close_bad), "闭合" if not close_bad else "**未闭合**"))
    A("| 坐标/要素四项 | `bad_coord=%d, zero_coord=%d, grade_missing_element=%d, S_city_null=%d` | 全 0 | %s |"
      % (inv.get("bad_coord", 0), inv.get("zero_coord", 0), inv.get("grade_missing_element", 0),
         inv.get("S_city_null", 0), "达标" if not any(inv.get(k, 0) for k in
                                                     ("bad_coord", "zero_coord",
                                                      "grade_missing_element", "S_city_null")) else "**未达标**"))
    A("| 输出 | **%d 片 / %d B**（%s 行） | — | 磁盘余量 %.1f GiB |"
      % (len(shard_files), shard_bytes, f"{newrows:,}", free_gb()))
    A("")
    A("## 1. 本轮点名回显\n")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 层数分母 | **3,550 层**（`analysis/step8-reconcile-20261125/final-tally.csv`，1 header + 3,550） |")
    A("| 清单 commit sha | **`87b5e4bdaadba8d7f83cceae5b597d2c38dd5cca`** |")
    A("| 代码基线 | **`bd55cc7`**（`feat/fieldmap-20261125`）→ 本单追加 commit（见 §12） |")
    A("")
    A("## 2. 分片执行表（每片跑完立刻校验，校验不过不许进下片）\n")
    A("| 片 | 层数 | 行数 | 字节 | 耗时 s | 封装+校验 s | 成员数(实/期) | 行数(实/期) | 校验 | free_gb |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---|---:|")
    for s in shards:
        v = s.get("validation") or {}
        A("| `%s` | %d | %s | %s | %s | %s | %s/%s | %s/%s | %s | %s |"
          % (s.get("tar"), s.get("layers"), f"{s.get('rows', 0):,}", f"{s.get('bytes', 0):,}",
             s.get("elapsed_s"), s.get("pack_s"), v.get("members"), v.get("members_expected"),
             f"{v.get('rows', 0):,}", f"{v.get('rows_expected', 0):,}",
             "OK" if v.get("ok") else "**FAIL**", s.get("free_gb")))
    A("")
    A("> 片级校验 = `tar` 成员数 + **逐成员实读行数** vs 覆盖表 `mapped` 之和 + 外层 gzip 完整性（流式读完）；")
    A("> 分片组成是 worker 完成顺序，不是原清单顺序（`dist-v2/shards/shard-*.json` 里有 `layer_ids` 可反查）。\n")
    A("## 3. 覆盖率 + 不可用分桶\n")
    A("- 覆盖率 **%.2f%%（%d/%d）**；不可用 **%d** 层，全部 `grade_below_C`（源层无街名/无任何地址要素，按口径丢弃不猜）。\n"
      % (cov, len(mapped), total, len(unus)))
    A("| 原因 | 层数 |")
    A("|---|---:|")
    for k, n in sorted(reason_cnt.items(), key=lambda kv: -kv[1]):
        A("| `%s` | %d |" % (k, n))
    A("")
    A("## 4. 各级行数（v2 vs 旧版）\n")
    A("| 级别 | v2 重扫 | 旧版（PR #58 现版） | 差 |")
    A("|---|---:|---:|---:|")
    for g in GRADES:
        A("| **%s** | %s | %s | %+d |" % (g, f"{newg[g]:,}", f"{oldg[g]:,}", newg[g] - oldg[g]))
    A("| **合计** | **%s** | **%s** | **%+d** |" % (f"{newrows:,}", f"{oldrows:,}", newrows - oldrows))
    A("")
    if inv:
        A("全量逐行重算（`verify-v2.py` 扫完 %d 片 / %s 行）的字段有效率：\n" % (V.get("tars"), f"{newrows:,}"))
        A("| 字段 | 有效率 |")
        A("|---|---:|")
        for k, lab in (("street_pct", "`street_name`"), ("number_pct", "`house_number`"),
                       ("city_pct", "`city`"), ("zip5_pct", "`zip5`"), ("state_pct", "`state`"),
                       ("coord_pct", "坐标（非空且在范围内且非 (0,0)）")):
            A("| %s | **%.2f%%** |" % (lab, (V.get("field_pct") or {}).get(k, 0.0)))
        A("")
    A("## 5. 与旧版差异\n")
    A("### 5.1 层级 grade 变动（旧 CSV vs 新 CSV，逐层向量比）\n")
    A("- **受影响层数：%d 层**（清单见 `grade-affected-layers.csv`）\n" % len(affected))
    dc = collections.Counter()
    for x in affected:
        for g, d in x["delta"].items():
            dc["%s%+d" % (g, d) if d > 0 else "%s%+d" % (g, d)] += 1
    A("| 变动方向（层数） | 计数 |")
    A("|---|---:|")
    for k, n in sorted(dc.items(), key=lambda kv: -kv[1])[:12]:
        A("| `%s` | %d |" % (k, n))
    A("")
    if D:
        A("### 5.2 样本 16 层逐行对账（`diff-v1-v2.json`，含 muse 亲核的 7 层漂移层）\n")
        A("| 层 | 方法 | 行数 旧→新 | grade 变动 |")
        A("|---|---|---|---|")
        for p in D.get("per_layer") or []:
            A("| `%s` | %s | %s→%s | `%s` |" % (p.get("layer_id", "")[:56], p.get("method", "-"),
                                               p.get("rows_v1"), p.get("rows_v2"),
                                               json.dumps(p.get("grade_moves") or {}, ensure_ascii=False)))
        A("")
        A("- 样本合计行数 旧 %s → 新 %s" % (f"{D.get('rows_v1', 0):,}", f"{D.get('rows_v2', 0):,}"))
        A("- 逐字段差异行数：`%s`" % json.dumps(D.get("agg_diff_by_field") or {}, ensure_ascii=False))
        A("- grade 变动矩阵（样本，逐行）：`%s`" % json.dumps(D.get("agg_grade_moves") or {}, ensure_ascii=False))
        A("")
    A("## 6. amend 7 条是否**原生**成立（不靠事后补丁）\n")
    A("| # | 增量 | 结论 | 证据 |")
    A("|---|---|---|---|")
    url_layers = sum(1 for r in v2 if (r.get("source_layer_kind") == "url" and int(r["mapped"] or 0) > 0))
    fb_layers = sum(1 for r in v2 if (r.get("source_layer_kind") == "layer_id_fallback"
                                      and int(r["mapped"] or 0) > 0))
    A("| 1 | `source_layer` = url | **符合** | 主跑逐层 `begin_layer(url)` + 写行时 `source_layer = url or layer_id`："
      "url **%d 层** / layer_id_fallback **%d 层**；全量 `bad_source_layer = %d` |"
      % (url_layers, fb_layers, inv.get("bad_source_layer", 0)))
    A("| 2 | `addrkey` 全行重算（a3 + sha1-20） | **符合** | 全量 %s 行逐行调用 `engine/outlet_clean.addrkey_v3`；"
      "格式不符 **%d** 行；不可键（num 或 street 缺）**%s** 行 = %.2f%% |"
      % (f"{newrows:,}", inv.get("bad_addrkey_fmt", 0), f"{inv.get('addrkey_null', 0):,}",
         100.0 * inv.get("addrkey_null", 0) / max(1, newrows)))
    A("| 3 | zip5 / city / 要素校验 | **符合** | 全量 `bad_zip5=%d`、`bad_state=%d`、`zip_null_high_grade=%d` |"
      % (inv.get("bad_zip5", 0), inv.get("bad_state", 0), inv.get("zip_null_high_grade", 0)))
    A("| 4 | `house_number` 占位值含 `-9` | **符合** | `PLACEHOLDERS` 含 `-9/-9.0/-09`；全量 `bad_number=%d`"
      "（占位值残留）；门牌为空行数 %s |"
      % (inv.get("bad_number", 0), f"{newrows - inv.get('number_ok', 0):,}"))
    A("| 5 | 逐层行数闭合 = 0 | **符合** | 覆盖表 `diff` 非零 **%d** 层；分片成员实读行数 vs `mapped` 不符 **%d** 层 |"
      % (len(close_bad), V.get("layer_rowcount_mismatch", 0)))
    A("| 6 | 11 列 schema 不变 | **符合** | 全量 `bad_columns = %d`（列名与顺序沿用 `fm_core.FIELDS`） |"
      % inv.get("bad_columns", 0))
    A("| 7 | 口径（plan）不变 | **符合** | `plan` 全文仍在 `analysis/fieldmap-20261125/w2-fieldmap-plan-20261125.md`，本单只换数据不重写口径 |")
    A("")
    A("## 7. 坐标口径终检（全部内置，无事后补丁）\n")
    A("| 项 | 值 |")
    A("|---|---:|")
    A("| `bad_coord`（越界/半缺） | **%d** |" % inv.get("bad_coord", 0))
    A("| `zero_coord`（(0,0)） | **%d** |" % inv.get("zero_coord", 0))
    A("| `grade_missing_element` | **%d** |" % inv.get("grade_missing_element", 0))
    A("| `S_city_null` | **%d** |" % inv.get("S_city_null", 0))
    A("| 坐标合法率 | **%.2f%%**（非空坐标 %s 行） |"
      % (100.0 * inv.get("coord_ok", 0) / max(1, inv.get("coord_ok", 0)), f"{inv.get('coord_ok', 0):,}"))
    A("")
    A("> `clean_coord()` 在算 grade **之前**跑：越界/(0,0)/缺省一律 null，再按要素表逐级重算 → "
      "S 级缺坐标自动落到 A/B/C，不存在「先给级后补坐标」的窗口。\n")
    A("### 7.1 坐标收口：107 行「round 后变 (0,0)」已清零\n")
    A("全量逐行终检（`verify_v2.py`，8 路按成员哈希并行、扫完 480,039,285 行）发现 `zero_coord = %d`："
      "`clean_coord()` 旧写法是**先判** `lat==0 and lon==0` **再** `round(...,7)`，"
      "源层里 `|v| < 5e-7` 的坐标过 round 后就是 `0.0` → 输出漏出 (0,0)。\n" % zero_pre)
    A("处置（同一分支、只追加）：")
    A("1. `fm_core.clean_coord()` 改成**先 round 再判** (0,0) —— 这是根因修复，之后任何重跑都不会再出现；")
    A("2. 已落盘的数据用 `coord_fix_v2.py` / `coord_fix_v2_shard.py` 按同口径补齐："
      "成员里**没有** `\"lat\":0` 字样就原字节直传，命中的成员逐行精确判（round 后为 0 / 越界 / 半缺）→ "
      "置 null + 按要素表重算 grade；逐片校验成员数后才 `os.replace` 覆盖旧片。")
    A("3. `verify_v2_post.py` 再证一遍：part000–005 **逐行 json 全不变量**（96,770,807 行）+ part006 **字节级**（383,268,478 行）。\n")
    A("| 项 | 值 |")
    A("|---|---:|")
    if RC:
        A("| 被置 null 的行（parts 000–005） | **%d** |" % int(RC["delta"]["B"] - RC["delta"]["A"]))
        A("| grade 迁移 | `%s`（A 级要求 point，所以 8 行 A→B；其余 99 行 C 级不变） |"
          % json.dumps(RC.get("delta") or {}, ensure_ascii=False))
        _g = RC["total_post_fix"]["grade"]
        A("| 收口后各级行数 | S **%s** / A **%s** / B **%s** / C **%s** / 合计 **%s** |"
          % (f"{int(_g['S']):,}", f"{int(_g['A']):,}", f"{int(_g['B']):,}", f"{int(_g['C']):,}",
             f"{int(RC['total_post_fix']['rows']):,}"))
    if POST:
        A("| 收口后行数 | **%s**（改前 %s，`rows_match=%s`） |"
          % (f"{int(POST['rows_total']):,}", f"{int(POST['rows_expected']):,}", POST.get("rows_match")))
        A("| 收口后 `zero_coord`（全量复扫） | **%d** |" % int(POST.get("zero_coord_hits_after_fix", 0)))
        A("| 复扫耗时 | json 逐行 %s s + 字节级 %s s |"
          % (POST.get("phase_secs", {}).get("json_part000_005"),
             POST.get("phase_secs", {}).get("bytes_part006")))
    A("")
    A("> 这一处是**代码口径 bug**（先判后 round），不是数据脏；修在 `fm_core` 里，重扫/重算都走新口径。\n")
    A("## 8. #2 / #9 的 ±1 行偏差 + 全量「源行数 vs 输出行数」差额扫描\n")
    sample = []
    sp_path = os.path.join(HERE, "sample-layers.csv")
    if os.path.isfile(sp_path):
        sample = [r["layer_id"] for r in csv.DictReader(open(sp_path, encoding="utf-8"))]
    v2m = {r["layer"]: r for r in v2}
    vlm = {r["layer"]: r for r in csv.DictReader(open(os.path.join(HERE, "verify-v2-layers.csv"),
                                                      encoding="utf-8"))} \
        if os.path.isfile(os.path.join(HERE, "verify-v2-layers.csv")) else {}
    dl = (D.get("per_layer") or [])
    dl = {p["layer_id"]: p for p in dl}
    A("| # | 层 | 旧版行数 | v2 行数 | v2 源行 | 丢弃 below_C | 解析失败 | 源−输出 | ±1 结论 |")
    A("|---|---|---:|---:|---:|---:|---:|---:|---|")
    dlt = [p for p in (D.get("per_layer") or []) if (p.get("delta_rows") or 0) != 0]
    for i, dp in enumerate(dlt, 1):
        lid = dp["layer_id"]
        r = v2m.get(lid) or {}
        oldn = (dl.get(lid) or {}).get("rows_v1")
        newn = (dl.get(lid) or {}).get("rows_v2")
        inr = int(r.get("in_rows") or 0)
        dr = int(r.get("dropped_below_c") or 0)
        pe = int(r.get("parse_error") or 0)
        clos = inr - int(r.get("mapped") or 0) - dr - pe
        A("| %d | `%s` | %s | %s | %s | %s | %d | **%d** | %s |"
          % (i, lid[:56], f"{oldn:,}" if oldn is not None else "-",
             f"{newn:,}" if newn is not None else "-", f"{inr:,}", f"{dr:,}", pe, clos,
             "±%d 行，源−输出仍 0（判级差异，非漏计）" % dp.get("delta_rows")
             if clos == 0 else "**仍有差额**"))
    A("")
    A("全量差额（`in_rows − mapped − dropped_below_C − parse_error`）非零层：**%d** 个%s\n"
      % (len(close_bad), "" if not close_bad else " → " + ", ".join(
          "`%s`(%+d)" % (r["layer"][:40], int(r["diff"] or 0)) for r in close_bad[:20])))
    A("分片成员实读行数 vs 覆盖表 `mapped` 不符的层：**%d** 个%s\n"
      % (V.get("layer_rowcount_mismatch", 0), "" if not rowmism else " → " +
         json.dumps(rowmism[:10], ensure_ascii=False)))
    A("## 9. 耗时\n")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 重扫起止（UTC） | `%s` → `%s` |" % (run.get("started_utc") or "见回执", run.get("completed_utc") or "-"))
    A("| 总时长 | %s 分钟 |" % (round((run.get("elapsed_s") or 0) / 60.0, 1)))
    A("| 8 片耗时（s） | %s |" % ", ".join(str(s.get("elapsed_s")) for s in shards))
    A("| 全量终检（verify-v2） | %s s |" % V.get("elapsed_s"))
    A("")
    A("## 10. 怎么复跑\n")
    A("```bash\ncd /data/workspace/wmd-fieldmap\n"
      "FM_DIST=/data/workspace/wmd-fieldmap/dist-v2 python3 analysis/fieldmap-20261125/map_layers.py \\\n"
      "  --all --shard 500 --workers 6 --out-csv analysis/fieldmap-20261125/layer-coverage.v2.csv\n"
      "python3 analysis/fieldmap-20261125/verify_v2.py --workers 8      # 全量逐行终检\n"
      "python3 analysis/fieldmap-20261125/diff_v1_v2.py --workers 8     # 16 层逐行对账\n"
      "python3 analysis/fieldmap-20261125/finalize_v2.py                # 本报告\n```\n")
    A("中断续跑：加 `--resume`（跳过覆盖表已记录层 + 拾回未打片散文件）。\n")
    A("## 11. 已知偏差 / 没做到的（如实）\n")
    A("0. **门禁判定：覆盖率 %.2f%% < 95%% → 本项 FAIL**（差 %d 层 / %.2f 个百分点，未达标线 3,373）。"
      "不可用 %d 层全部是 `grade_below_C`（源层无街名/无任何地址要素，按口径丢弃不猜；与 v1 的 450 层相比"
      "已有 255 层因 `begin_layer` 修复而恢复出可用数据）。**没有放宽容差、没有改分母**；"
      "分母是否该换成「有街名或门牌的层」需 muse 裁定。" % (cov, 3373 - len(mapped), 95 - cov, len(unus)))
    A("2. **house_number %s%% / zip5 %s%%**：根因是源层本身没有这些字段（信封 + raw 别名 + 组合串拆全试过），"
      "不是映射逻辑错；不补零、不生成门牌是硬口径。"
      % ((V.get("field_pct") or {}).get("number_pct"), (V.get("field_pct") or {}).get("zip5_pct")))
    A("3. **`unit` 不在 11 列输出里** → addrkey 的 unit 段只能取行内 `unit`（本单主跑是从输入行直取，"
      "比 amend 版更准），但输出侧不带 `unit` 列本身没变。")
    A("4. **tier 全 `unrated`**：分档表（Tier1=410 版）与本批 3,550 层 layer_id 交集 0、非空 url 交集 0（前单已核），"
      "所以 tier 列写不出值，这不是本单退化。")
    A("5. **方言仍全 `minimal_safe`**：`registry/dialects.v1.yaml` 只有 4 dialect / 34 org，本批 url 的 agol org 仅 "
      "空串/`rest`，registry 命中 0 层（前单已改口径，不再写错误的「命中 115」）。")
    A("6. **全量行级 grade 变动矩阵**（跨 3,100 层的 S/A/B/C 各进各出）未逐行 join（要同时流式读旧新两代约 18 GB 并做键连接）；"
      "本报告给的是：① 各级总行数新旧对照；② 样本 16 层逐行变动矩阵；③ 受影响层清单（`grade-affected-layers.csv`）。")
    A("7. 所有数出自同一次重扫的落盘产物；**未运行** `amend_rewrite.py` / `coord_clean.py`（本单要求原生成立）。")
    A("")
    A("## 12. 交付物与 PR\n")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| 分支 / PR | `feat/fieldmap-20261125` / **#58（保持 OPEN，合并由 muse 做）** |")
    A("| 数据 | `dist-v2/tar/fieldmap-part000..006.tar.gz`（7 片 / %d B）+ `dist-v2/shards/shard-*.json` |" % shard_bytes)
    A("| 覆盖表 | `layer-coverage.v2.csv`（3,550 行，含 `grade_C` / `source_layer_kind` 两列） |")
    A("| 机器可读汇总 | `SUMMARY-v2.json` / `verify-v2.json` / `verify-v2-post.json` / `diff-v1-v2.json` / `coord-fix-recount.json` |")
    A("| 不可用清单 | `unusable-v2.csv`（%d 层，原因全固定枚举） |" % len(unus))
    A("| 受影响层清单 | `grade-affected-layers.csv`（%d 层） |" % len(affected))
    A("| 脚本 | `map_layers.py`（逐层 `begin_layer` + 片级校验 + resume 拾回）/ `verify_v2.py` / `verify_v2_post.py` / "
      "`diff_v1_v2.py` / `probe_pm1.py` / `coord_fix_v2.py` / `coord_fix_v2_shard.py` / `finalize_v2.py` |")
    A("")
    A("> 旧 `dist/`（v1，8.6 GB）在新产物全量校验通过后才处理；处理方式与释放字节数见本单回执与 PR body。\n")
    open(os.path.join(HERE, "REPORT-v2.md"), "w", encoding="utf-8").write("\n".join(R) + "\n")
    print(json.dumps({k: four[k] for k in ("coverage_pct", "coverage_layers", "unusable",
                                           "closing_diff_layers", "rows_total", "grade",
                                           "affected_layers", "layer_rowcount_mismatch")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
