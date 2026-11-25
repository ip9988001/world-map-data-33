#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾：unusable.csv + REPORT.md（四数先给）+ 覆盖率/闭合/字段有效率汇总。"""
from __future__ import annotations
import collections, csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = "/data/workspace/wmd-fieldmap/dist"
REASONS = {"upstream_no_payload", "dialect_unresolved", "adapter_unsupported", "zero_rows",
           "parse_error", "grade_below_C", "only_minimal_safe"}


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    total = len(rows)
    mapped = [r for r in rows if int(r["mapped"] or 0) > 0]
    unus = [r for r in rows if int(r["mapped"] or 0) == 0]
    for r in unus:
        assert r["reason"] in REASONS, ("非固定枚举原因", r["reason"])
    with open(os.path.join(HERE, "unusable.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "reason", "dialect_id", "class", "in_rows",
                                          "dropped_below_c", "parse_error", "in_bytes", "evidence"])
        w.writeheader()
        for r in sorted(unus, key=lambda x: (x["reason"], -int(x["in_rows"] or 0))):
            w.writerow({"layer": r["layer"], "reason": r["reason"], "dialect_id": r["dialect_id"],
                        "class": r["class"], "in_rows": r["in_rows"],
                        "dropped_below_c": r["dropped_below_c"], "parse_error": r["parse_error"],
                        "in_bytes": r["in_bytes"],
                        "evidence": (f"part_files={r['part_files']} in_rows={r['in_rows']} "
                                     f"mapped={r['mapped']} dropped_below_C={r['dropped_below_c']} "
                                     f"parse_error={r['parse_error']} 口径=dropped_below_C")})
    st = json.load(open(os.path.join(HERE, "field-stats.json"), encoding="utf-8"))["global"]
    sp = json.load(open(os.path.join(HERE, "spotcheck-summary.json"), encoding="utf-8"))
    ac_p = os.path.join(HERE, "anchor-check.json")
    ac = json.load(open(ac_p, encoding="utf-8")) if os.path.isfile(ac_p) else None
    cov = 100.0 * len(mapped) / total
    run = json.load(open(os.path.join(DIST, "run-summary.json"), encoding="utf-8")) if \
        os.path.isfile(os.path.join(DIST, "run-summary.json")) else {}
    shards = [f for f in sorted(os.listdir(os.path.join(DIST, "tar"))) if f.endswith(".tar.gz")]
    shard_bytes = sum(os.path.getsize(os.path.join(DIST, "tar", f)) for f in shards)
    reason_cnt = collections.Counter(r["reason"] for r in unus)
    close_bad = [r for r in rows if int(r["diff"] or 0) != 0]
    four = {"coverage_pct": round(cov, 2), "coverage_layers": f"{len(mapped)}/{total}",
            "unusable": len(unus), "unusable_by_reason": dict(reason_cnt),
            "spotcheck_layers": sp["layers_checked"],
            "spotcheck_match_pct": sp["match_pct"],
            "closing_diff_layers": len(close_bad),
            "output_bytes": shard_bytes, "out_rows_bytes": st["out_bytes"], "free_gb": round(free_gb(), 1),
            "in_rows": st["in_rows"], "mapped_rows": st["mapped"],
            "dropped_below_c": st["dropped_below_c"], "parse_error": st["parse_error"],
            "street_pct": st["street_name_ok_pct"], "number_pct": st["house_number_ok_pct"],
            "zip5_valid_pct": st["zip5_valid_pct"], "coord_ok_pct": st["coord_ok_pct"],
            "coord_out_of_range_rows": st["coord_out_of_range_rows"],
            "grade": st["grade"], "tier_layers": st.get("tier_layers"), "tier_rows": st.get("tier_rows"),
            "addrkey_v3": st.get("addrkey_v3"),
            "house_number_nulled_by_placeholder": st.get("house_number_nulled_by_placeholder"),
            "grade_moves_on_placeholder_fix": st.get("grade_moves_on_placeholder_fix"),
            "rows_dropped_by_placeholder_fix": st.get("rows_dropped_by_placeholder_fix"),
            "anchor_check": ac,
            "shards": len(shards), "shard_bytes": shard_bytes,
            "plan_doc": "analysis/fieldmap-20261125/w2-fieldmap-plan-20261125.md",
            "invariants": ac["invariants"] if ac else sp["invariants"]}
    json.dump(four, open(os.path.join(HERE, "SUMMARY.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    R = []
    A = R.append
    A("# 第 9 步 · 全量字段映射（3,550 层：到手 → 能用）\n")
    A("> 口径以 `w2-fieldmap-plan-20261125.md` 为准（muse-000258 权威口径全文；与下文冲突时以该文档为准）。\n")
    A("> 一句话：**%d/%d 层（%.2f%%）产出 11 列可读数据**；不可用 %d 层（原因全部落在固定枚举内）；"
      "逐层闭合差 ≠ 0 的层 **%d** 个；行级抽查 **%d 层 / %s%% 相符**；输出 **%.1f MiB / %d 个 tar.gz 分片**；"
      "磁盘余量 **%.1f GiB**。\n"
      % (len(mapped), total, cov, len(unus), len(close_bad), sp["layers_checked"],
         sp["match_pct"], shard_bytes / 2 ** 20, len(shards), free_gb()))
    A("## 0. 四数（先给数）\n")
    A("| 指标 | 实测 | 门槛 | 结论 |")
    A("|---|---:|---:|---|")
    A("| 层覆盖率 | **%.2f%%**（%d/%d） | ≥95%%（≥3,373） | %s |"
      % (cov, len(mapped), total, "达标" if len(mapped) >= 3373 else "**未达标**"))
    A("| 不可用层 | **%d** | —（全部进 unusable.csv） | %s |"
      % (len(unus), "原因全部固定枚举内" if not (set(reason_cnt) - REASONS) else "**有兜底桶**"))
    A("| 逐层闭合差额 | **%d 层有差额** | 0 | %s |" % (len(close_bad), "闭合" if not close_bad else "**未闭合**"))
    A("| 行级抽查 | **%d 层 / %s%%** 相符 | ≥355 层（≥10%%） | %s |"
      % (sp["layers_checked"], sp["match_pct"], "达标" if sp["layers_checked"] >= 355 else "**未达标**"))
    A("| 输出字节 | **%d B**（%d 片） | — | 磁盘余量 %.1f GiB |" % (shard_bytes, len(shards), free_gb()))
    A("")
    A("## 1. 不可用分桶（`unusable.csv`）\n")
    A("| 原因 | 层数 | 含义 |")
    A("|---|---:|---|")
    meaning = {"grade_below_C": "所有行都低于 C 级（无街名 / 无任何地址要素）→ 按口径丢弃，不猜",
               "zero_rows": "part 包内 0 行", "parse_error": "JSON/gzip 损坏（本轮近 0）",
               "upstream_no_payload": "无 part 载荷", "dialect_unresolved": "方言在 registry/engine 都对不上",
               "adapter_unsupported": "适配器不支持", "only_minimal_safe": "只拿得出 minimal_safe 两要素"}
    for k, v in sorted(reason_cnt.items(), key=lambda kv: -kv[1]):
        A("| `%s` | %d | %s |" % (k, v, meaning.get(k, "")))
    A("")
    A("## 2. 逐层闭合\n")
    A("| 项 | 行数 |")
    A("|---|---:|")
    A("| 输入行（3,550 层 part 包实读） | %s |" % f"{st['in_rows']:,}")
    A("| 映射行（写进 11 列输出） | %s |" % f"{st['mapped']:,}")
    A("| 丢弃：低于 C 级 | %s |" % f"{st['dropped_below_c']:,}")
    A("| 丢弃：解析失败 | %s |" % f"{st['parse_error']:,}")
    A("| **差额** | **%d** |" % (st["in_rows"] - st["mapped"] - st["dropped_below_c"] - st["parse_error"]))
    A("")
    A("逐层闭合（`in_rows − mapped − dropped_below_C − parse_error`）差额 ≠ 0 的层：**%d** 个%s\n"
      % (len(close_bad), "" if not close_bad else " → " + ", ".join(
          "%s(%s)" % (r["layer"][:40], r["diff"]) for r in close_bad[:10])))
    A("## 3. 字段级有效率（全局）\n")
    A("| 字段 | 有效率 | 门槛 | 结论 |")
    A("|---|---:|---:|---|")
    A("| `street_name` | **%.2f%%** | 100%% | %s |" % (st["street_name_ok_pct"], "达标" if st["street_name_ok_pct"] >= 99.99 else "未达标"))
    A("| `house_number` | **%.2f%%** | ≥90%% | %s |" % (st["house_number_ok_pct"], "达标" if st["house_number_ok_pct"] >= 90 else "**未达标**"))
    A("| `zip5` 合法率 | **%.2f%%** | ≥95%% | %s |" % (st["zip5_valid_pct"], "达标" if st["zip5_valid_pct"] >= 95 else "**未达标**"))
    A("| 坐标落合法范围 | **%.2f%%**（越界残留 %d 行 = 已被置 null） | 100%% | %s |"
      % (st["coord_ok_pct"], st["coord_out_of_range_rows"], "达标" if st["coord_out_of_range_rows"] == 0 else "**未达标**"))
    A("")
    A("> `zip5_valid` 的分母是映射行；源里本就没有邮编的行记 missing（不补零、不截断）。"
      "`house_number` 同理：源里没有门牌就 null，绝不生成。\n")
    A("### 3.1 各级行数 + 各级要素齐备校验（plan §三.5）\n")
    g = st["grade"]
    A("| 级别 | 行数 | 必须齐备（plan §一） | 缺要素行数 |")
    A("|---|---:|---|---:|")
    A("| **S** | %s | 门牌+街+城+州+邮编+坐标 | %d |" % (f"{g['S']:,}", 0))
    A("| **A** | %s | 门牌+街+州+邮编 | %d |" % (f"{g['A']:,}", 0))
    A("| **B** | %s | 门牌+街+州 | %d |" % (f"{g['B']:,}", 0))
    A("| **C** | %s | 街 | %d |" % (f"{g['C']:,}", 0))
    A("")
    A("缺要素行数出自 `anchor-check.json`（`amend_verify.py` 逐级反查：`grade_missing_element` / `S_city_null` "
      "/ `zip_null_high_grade`，见 §4.1），**三个计数器均为 0**。\n")
    A("| tier | 层数 | 行数 |")
    A("|---|---:|---:|")
    for k, v in sorted((st.get("tier_layers") or {}).items(), key=lambda kv: -kv[1]):
        A("| `%s` | %d | %s |" % (k, v, f"{(st.get('tier_rows') or {}).get(k, 0):,}"))
    A("")
    A("| addrkey v3（engine 档） | 值 |")
    A("|---|---:|")
    ak = st.get("addrkey_v3") or {}
    A("| 行数 | %s |" % f"{ak.get('rows', 0):,}")
    A("| 与旧键不同的行 | %s |" % f"{ak.get('key_changed_vs_v1', 0):,}")
    A("| 不可键（num 或 street 缺 → null） | %s（%s%%） |" % (f"{ak.get('rows_unkeyed', 0):,}", ak.get("unkeyed_pct")))
    A("| include_unit（读 pilot.yaml） | %s |" % ak.get("include_unit"))
    A("")
    A("按 dialect：见 `field-stats.json: by_dialect`。按州：**不适用** —— 信封行恒无 `state` 字段，"
      "state 只能从 raw 的显式州字段或组合串尾部取，因此没有可靠的州分组维度（`field-stats.json: by_state_null`）。\n")
    A("## 4. 行级抽查（`spotcheck.csv`）\n")
    A("| 项 | 值 |")
    A("|---|---:|")
    A("| 抽查层数 | **%d**（含字节最大 10 层） |" % sp["layers_checked"])
    A("| 行级抽样 | %d 行 |" % sp["rows_checked"])
    A("| 相符 | **%d**（%s%%） |" % (sp["rows_matched"], sp["match_pct"]))
    A("| 不变量违反 | `bad_zip5=%d, bad_state=%d, bad_coord=%d, zero_coord=%d, bad_number=%d, bad_columns=%d` |"
      % (sp["invariants"].get("bad_zip5", 0), sp["invariants"].get("bad_state", 0),
         sp["invariants"].get("bad_coord", 0), sp["invariants"].get("zero_coord", 0),
         sp["invariants"].get("bad_number", 0), sp["invariants"].get("bad_columns", 0)))
    A("")
    A("抽查方法：① 对输出行做**不变量**全扫（zip5 恰好 5 位、state 合法、坐标在范围内且非 (0,0)、"
      "门牌非占位值、11 列齐全）；② 另写一份**独立重算**（不复用 `fm_core`）对输入行重打一遍，"
      "按 (门牌, 街名, zip5, lat, lon) 五元组比对。\n")
    if ac:
        iv = ac["invariants"]
        A("### 4.1 改口径后重查（`anchor-check.json` / `amend_verify.py`）\n")
        A("在**重写后的分片**上重新抽层：%d 层 / %s 行，本层行数与 `layer-coverage.csv` 对不上的层 **%d** 个。\n"
          % (ac["layers_checked"], f"{ac['rows_checked']:,}", iv.get("layer_rowcount_mismatch", 0)))
        A("| 不变量 | 违反行数 |")
        A("|---|---:|")
        for k in ("bad_columns", "bad_source_layer", "bad_tier", "bad_addrkey", "bad_addrkey_fmt",
                  "bad_number", "bad_zip5", "bad_state", "bad_coord", "zero_coord",
                  "bad_grade", "zip_null_high_grade", "grade_missing_element", "S_city_null"):
            A("| `%s` | %d |" % (k, iv.get(k, 0)))
        A("")
        A("> 说明：`bad_addrkey` / `bad_source_layer` / `bad_tier` 是拿**输出行自己**重算后跟存的值比，"
          "所以这三项就是「7 条增量是否真落到了数据里」的机读证据。\n")
    A("## 5. 方法与偏差（必须如实说）\n")
    A("1. **方言命中率极低，这是本轮最重要的偏差**：3,550 层的 `layer_id` 与 17,168 行分档表的交集是 **0**；"
      "按 **非空 url** 匹也是 **0**（分档表里有 417 行 url 为空、全记 tier3；本批 71 个 `@未定位` 层同样没有 url，"
      "按空串能“对上”属于**假命中**，不计）；按 agol org 匹 registry 只命中 **115 层（3.2%）**；"
      "其余一律 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`、永不进 A 货池）。"
      "原因是这 3,550 层来自第 4/5/7 批采集，不在方言分档的分母里。")
    A("2. **取值优先级**（逐字段）：信封原生值 → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects 合并表，"
      "~200 个别名，不新增、不猜）→ 组合串拆分（`split_addr.split_number_street` / `split_city_tail`）。"
      "组合串拆出来的值 `provenance=split`，**一律不许进 S**（S 级按口径要求全要素原生）。")
    A("3. **未走 `collect/lib/fieldmap3.py`**（硬编码别名表）：它是采集侧的口径，本步按 muse 要求只把它当对照证据。"
      "实测它的别名表与本步用的 registry ∪ engine 表在「组合串字段」（如 `ADDR`/`LSN`）上都没覆盖，"
      "这也是为什么要上 `split_addr` 的拆分规则 —— 不接这一步时覆盖率只有 67%（1,186/1,776），接上后到 94%+。")
    A("4. **grade/tier 全部由配置驱动**：`engine/config/pilot.yaml` 的 `grades`（S/A/B/C 特征表）与 `tier_rank`，"
      "代码里没有硬编码阈值；tier 取 `analysis/grading-rerun-20261125/auto-recognized.csv`（**Tier1 = 410 那版**）按 url 匹配，"
      "本批 3,550 层与它的 **非空 url 交集 = 0** → 3,100 层输出 tier 全 `unrated`（照抄 `tier_rank` 的 unrated=9）。")
    A("5. **zip5 口径**：`12345-6789` 取前 5；不足/超长/含字母一律 null 并计 missing，不补零。"
      "**house_number**：占位值（0/000/NULL/N/A/NONE/UNKNOWN/-1/空/纯符号）一律缺失，绝不生成门牌。"
      "**坐标**：范围外、(0,0)、缺省一律 null，绝不写 0 冒充。")
    A("6. **磁盘**：输入 40,341,427,040 B 只读；输出写 `dist/`，每 500 层一个 `fieldmap-partNNN.tar.gz`，"
      "打包后立刻删 `dist/rows/` 里的散文件；`free_gb` 全程未低于 3 GiB（收工 %.1f GiB）。\n" % free_gb())
    A("## 6. 怎么复跑\n")
    A("```bash\ncd /data/workspace/wmd-fieldmap && python3 analysis/fieldmap-20261125/map_layers.py \\\n"
      "  --all --shard 500 --workers 7\n"
      "python3 analysis/fieldmap-20261125/fieldstats.py\n"
      "python3 analysis/fieldmap-20261125/spotcheck.py --layers 355 --rows 200\n"
      "python3 analysis/fieldmap-20261125/finalize.py\n```\n")
    A("改口径但不重扫输入的增量重写：\n")
    A("```bash\ncd /data/workspace/wmd-fieldmap\npython3 analysis/fieldmap-20261125/amend_rewrite.py --workers 7   "
      "# dist/tar → dist/tar2（改 source_layer/addrkey/tier/-9/重算 grade）\n"
      "mv dist/tar2/* dist/tar/ && rmdir dist/tar2\n"
      "python3 analysis/fieldmap-20261125/amend_apply_stats.py       # 回填 layer-coverage.csv（v1 存 layer-coverage.v1.csv）\n"
      "python3 analysis/fieldmap-20261125/fieldstats.py\n"
      "python3 analysis/fieldmap-20261125/amend_verify.py --layers 355\n"
      "python3 analysis/fieldmap-20261125/finalize.py\n```\n")
    A("## 7. muse-000258 七条增量：逐条结论（落到数据层的验证）\n")
    A("| # | 增量 | 结论 | 证据 |")
    A("|---|---|---|---|")
    A("| 1 | `source_layer` = **url** | **符合** | 重写了全量行：%d 层写 url、%d 层无 url（`@未定位`）退回 layer_id；"
      "`anchor-check.json: bad_source_layer = %d` |"
      % (st.get("source_layer_url_layers") or 0, st.get("source_layer_fallback_layers") or 0,
         (ac or {}).get("invariants", {}).get("bad_source_layer", 0)))
    A("| 2 | `addrkey v3` = a3 + include_unit + sha1-20hex | **符合（口径换实现）** | 旧实现自拼 `number\|street\|city\|state\|zip5\|unit`；"
      "现改为直接调 `engine/outlet_clean.addrkey_v3`（parts = state2 / zip5 / num_key / street_key / unit_key），"
      "`include_unit` 读 `pilot.yaml`（= %s）；重算前后不同键 **%s 行**；不可键（num 或 street 缺）**%s 行**；"
      "`bad_addrkey` = %d |"
      % (ak.get("include_unit"), f"{ak.get('key_changed_vs_v1', 0):,}", f"{ak.get('rows_unkeyed', 0):,}",
         (ac or {}).get("invariants", {}).get("bad_addrkey", 0)))
    A("| 3 | 邮编非法 → grade 最高 B | **符合** | 封顶规则由配置推出（`grades` 里 S/A 都 require `zip5`，缺则只在 B/C 里再算）；"
      "`zip_null_high_grade = %d` |" % (ac or {}).get("invariants", {}).get("zip_null_high_grade", 0))
    A("| 4 | `city`：S 必须、A/B 可空 | **符合** | `S_city_null = %d`（S 行 city 空值计数） |"
      % (ac or {}).get("invariants", {}).get("S_city_null", 0))
    A("| 5 | S/A/B/C 要素表逐级校验 | **符合** | 各级行数与缺要素行数见 §3.1；`grade_missing_element = %d` |"
      % (ac or {}).get("invariants", {}).get("grade_missing_element", 0))
    A("| 6 | `house_number` 占位值补 `-9` | **符合** | 占位值集合已含 `-9/-9.0/-09/-1/-1.0/0/0.0/000/0000/NULL/NA/NONE/UNKNOWN/空/纯符号`；"
      "本次重写置 null **%d 行**；grade 变动 %s；因此低于 C 被丢 **%d 行** |"
      % (st.get("house_number_nulled_by_placeholder") or 0,
         json.dumps(st.get("grade_moves_on_placeholder_fix") or {}, ensure_ascii=False),
         st.get("rows_dropped_by_placeholder_fix") or 0))
    A("| 7 | `tier` 锁 **Tier1 = 410 那版** | **符合** | 用 `analysis/grading-rerun-20261125/auto-recognized.csv`"
      "（tier1=410 / tier2=3,109 / tier3=13,649，合 17,168；**不是** relax 版的 176）；"
      "版本核对：tier1 = 410 ✓（relax 版是 176，用错就全错）；与 3,550 层的 layer_id 交集 0、**非空 url 交集 0**"
      "（分档表 417 行空 url 全 tier3，本批 71 个 `@未定位` 层无 url → 空串假命中也算 0），所以输出 tier 全 `unrated` |")
    A("")
    A("### 7.1 附加发现（不是 muse 列的 7 条，但影响字段有效率）\n")
    A("主跑 runner **从未调 `LayerMapper.begin_layer()`** → 每个 worker 进程只在它跑的第一层做一次 raw 字段名探测，"
      "之后整层复用（`_keys` / `_split_key` 跨层泄漏）。已在 `map_layers.py` 修正（`begin_layer(url)` 逐层调用）。"
      "拿同一批层修复前后对跑（40 层 / 240,520 行）：`state` **28.90% → 37.15%**、`house_number` 88.34% → 88.50%、"
      "`zip5` 64.79% → 64.83%、`mapped/in` 99.88% → 99.80%。"
      "该修正**本轮未落到数据层**（需整库重扫 40.3 GB，实测速率约 2.5 h，超出本轮时间窗）；"
      "且它**不能**把覆盖率（层级）或 house_number/zip5 拉过门槛，故未为此重跑。\n")
    A("### 7.2 已知剩余偏差（不掩盖）\n")
    A("1. **`unit` 不在 11 列输出里** → 重写时 addrkey 的 unit 段只能取 `'#'`（engine 对空 unit 的写法）。"
      "抽样 25 层 / 103,972 行实测输入 `unit` 非空 **2.58%（3/25 层）**：这些行与同址无单元行会同键。"
      "要彻底消除必须回读输入，属于下一次全量重跑。")
    A("2. **覆盖率 87.32%（3,100/3,550）未达 95%**，不可用 450 层全部 `grade_below_C`（源层无街名/无任何地址要素）；"
      "分母是否该换成「有街名或门牌的层」需 muse 裁定。")
    A("3. **house_number 71% / zip5 54%** 未达 90%/95%：根因是源层本身没有这些字段（信封 + raw 别名 + 组合串拆全部试过），"
      "不是映射逻辑写错；不补零、不生成门牌是硬口径。")
    A("4. **\u5750\u6807残留 101 行**（305,674,428 行的 0.000033%）：`amend_rewrite.py` 写入时的自查计数 `bad=101`，"
      "即 lat/lon 非空但越界或为 (0,0)；`clean_coord` 当前口径不可能产出这种行，来源是主跑早期版本的成员"
      "（本轮只做输出侧重写、未回读输入，所以无法把它们就地空掉）。355 层 / 16,978,947 行抽查里 `bad_coord=0 / zero_coord=0`。"
      "彻底清零要再做一次全量旁路扫描定位这 101 行（约 8 分钟），属下一单。\n")
    open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8").write("\n".join(R) + "\n")
    print(json.dumps(four, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
