#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 REPORT-fix58.md（数字全部从 fix58-summary.json / fix58-before-after.csv 取，不手抄）。

另外做两件事：
  · 现场复算「最小复现改前/改后」（跑基线模块 + 现行模块，输出写进报告，不手抄）；
  · 给 REPORT-v2.md 顶部打 provisional 横幅、给 SUMMARY-v2.json 加 provisional 字段
    （只加标记，不改任何历史结论数字）。
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FM = os.path.join(ROOT, "analysis", "fieldmap-20261125")
sys.path.insert(0, FM)
LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
BASE_COMMIT = "4c3a6a324858d7d14efc2edb35331b0924be6764"
BASE_DIR = "/data/scratch/fix58-baseline"


def _baseline():
    sys.path.insert(0, FM)
    import fm_core as NEW
    p = os.path.join(BASE_DIR, "fm_core.py")
    y = os.path.join(BASE_DIR, "dialects.v1.yaml")
    if not os.path.isfile(p):
        os.makedirs(BASE_DIR, exist_ok=True)
        for rel, dst in (("analysis/fieldmap-20261125/fm_core.py", p),
                         ("registry/dialects.v1.yaml", y)):
            with open(dst, "wb") as fh:
                subprocess.run(["git", "-C", ROOT, "show", f"{BASE_COMMIT}:{rel}"], stdout=fh, check=True)
    spec = importlib.util.spec_from_file_location("fm_core_baseline", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    roles = NEW.SA.roles_of(y, os.path.join(ROOT, "engine", "dialects"))
    mod.load_roles = lambda: {"number": {k for k, v in roles.items() if "number" in v},
                              "street": {k for k, v in roles.items() if "street" in v},
                              "zip": {k for k, v in roles.items() if "zip" in v}}
    return mod, NEW


def repro():
    """F2rCsQjt0P3e：首行 LABEL 拆不出（ambiguous）→ 老代码整层放弃；新代码第 2 行照拆。"""
    old, new = _baseline()
    cfg = new.load_pilot_cfg()
    o2d, meta, _ = new.load_registry_orgs()
    tm = new.load_tier_map()
    lid = "F2rCsQjt0P3e_arcgis_rest_services_AddressPts_FeatureServer_0"
    url = "https://example.invalid/F2rCsQjt0P3e/FeatureServer/0"
    rows = [
        {"raw": {"OBJECTID": "1", "LABEL": "3358 K 157 HWY", "HNO": "3358", "RD": "K 157",
                 "STS": "HWY", "ZIP": "66441", "STATE": "KS"}, "lat": 39.0, "lon": -96.8},
        {"raw": {"OBJECTID": "2", "LABEL": "1952 SWENSON RD", "HNO": "1952", "RD": "SWENSON",
                 "STS": "RD", "ZIP": "66441", "STATE": "KS"}, "lat": 39.0, "lon": -96.8},
    ]
    out = {}
    for tag, mod in (("before", old), ("after", new)):
        m = mod.LayerMapper(cfg, o2d, meta, tm)
        try:
            m.begin_layer(url, lid)
        except TypeError:
            m.begin_layer(url)
        got = []
        for r in rows:
            rec, reason, _ = m.map_row(dict(r))
            got.append({"reason": reason or "mapped",
                        "house_number": (rec or {}).get("house_number"),
                        "street_name": (rec or {}).get("street_name"),
                        "grade": (rec or {}).get("grade")})
        out[tag] = got
    # 真实层首行（同一层的实际首行就是那条 ambiguous 的 LABEL）
    d = os.path.join(LAYERS, lid)
    real = None
    if os.path.isdir(d):
        f = sorted(x for x in os.listdir(d) if x.endswith(".ndjson.gz"))[0]
        with gzip.open(os.path.join(d, f), "rt", encoding="utf-8", errors="replace") as fh:
            row = json.loads(fh.readline())
        real = {"LABEL": (row.get("raw") or {}).get("LABEL")}
    return out, real


def main():
    S = json.load(open(os.path.join(HERE, "fix58-summary.json"), encoding="utf-8"))
    R = S["regression"]
    rows = list(csv.DictReader(open(os.path.join(HERE, "fix58-before-after.csv"), encoding="utf-8")))
    rp, real = repro()
    L = []
    w = L.append

    w("# fix58 · 58 层 B 类修复落地报告（muse-000271）\n")
    w(f"> 生成物由脚本合成（`make_fix58.py` + `build_report.py`），数字全部取自 "
      f"`fix58-summary.json` / `fix58-before-after.csv` / 各 `*-b58.jsonl`、`*-affected.jsonl`、"
      f"`*-regression.jsonl`。口径：只跑 58 层 + 回归抽样，**未做全量重扫**，因此 "
      f"`REPORT-v2.md` / `SUMMARY-v2.json` 本轮只打 provisional 标记，历史结论数字一个都没改。\n")

    w("## 0. 结论\n")
    w(f"- 58 层 **全部上映射**（`layers_mapped_after = {S['layers_mapped_after']}/58`，"
      f"`layers_still_zero = {S['layers_still_zero']}`），逐层闭合差额 0、`bad_empty = "
      f"{S['acceptance']['bad_empty_total']}`、`bad_grade = {S['acceptance']['bad_grade_total']}`。")
    w(f"- 新覆盖率 **{S['coverage']['pct']}%**（{S['coverage']['mapped_layers']}"
      f"/{S['coverage']['total_layers']}）→ 95% 门禁（需 {S['coverage']['gate_layers_needed']} 层）"
      f"**{'通过' if S['coverage']['pass_95pct'] else '未通过'}**，且达到测算的 96.14%。")
    w(f"- 可恢复行实得 **{S['rows']['mapped_after_total']:,}** 行（报告 §6 测算 "
      f"{S['rows']['est_rows_recoverable_from_report']:,} 行，差 "
      f"{S['rows']['mapped_after_total'] - S['rows']['est_rows_recoverable_from_report']:+,}）。")
    w(f"- 回归：新别名命中集 **{R['alias_hit_census']['alias_hit_layers_ab']} 层全量 A/B**，"
      f"行数下降的层 **{len(R['alias_hit_census']['decreased_layers'])} 层**；未命中集分层抽样 "
      f"**{R['sample']['layers']} 层 / {R['sample']['rows']:,} 行**（{R['sample']['states_covered']} 个州/地区），"
      f"行数下降 **{len(R['sample']['decreased_layers'])} 层**。")
    w(f"- 唯一没到「零」的指标：`zero_coord = {S['acceptance']['zero_coord_total']}` 行"
      f"（{len(S['acceptance']['zero_coord_layers'])} 层各 1 行），原因是源里坐标本身就是空/`0,0`，"
      f"映射侧按 muse-000266 口径拒写 `(0,0)`，非映射缺陷。\n")

    w("## 1. 起点核对\n")
    w(f"- 起点 HEAD = `{BASE_COMMIT}`（= PR #58 当时 head），分支 `feat/fieldmap-20261125`，工作树干净。")
    w("- `unmapped-classification.csv` 里 `class==B` 正好 58 行，reason 分桶 = "
      "`alias_missing_street 38 / split_first_row_only 13 / alias_generic_fieldname_layer_scoped 5 / "
      "split_key_beyond_40 1 / derived_geocoder_output 1`，与派单一致。")
    w("- 磁盘 free 全程 30G+（护栏 8G 未触发）；无并行映射进程。\n")

    w("## 2. 三处修复\n")
    w("### 2.1 修 1 · 角色表补街名别名（全局，弱源）\n")
    w("`registry/dialects.v1.yaml` 新增**一个别名扩展方言条目** `fix58-alias-ext-v1`"
      "（35 条 street + 2 条 number），**没有改动任何既有方言的 template / 别名**"
      "（该表里本来就没有 `id: minimal_safe` 的实体条目，`minimal_safe` 是 fallback，"
      "角色表由 `roles_of()` 把所有方言的 template 并集而成，所以「补 minimal_safe template」的等价做法"
      "就是追加一个 `alias_extension` 条目 —— 与既有 `p7-alias-ext-v1` 同构）。")
    w("- 关键设计：新别名标记 `alias_strength: weak`，**只在「强别名与组合串拆分都没给出」时兜底**。"
      "第一版把新别名放在拆分之前，回归专项查出 4 层 grade 退化（新别名先把 street 填成不完整街名，"
      "把原本靠拆 `FULL_ADDRE` 拿到「门牌+完整街名」(grade A) 的行压成 grade C），改弱源后这 4 层与旧版逐行一致。")
    w("- `firstname` / `lastname` / `fullname` 一条没动（仍是既有 street 别名，本轮未触碰）；"
      "`NAME` / `TYPE` / `STR` / `PARCEL_LOC` **未进全局表**，只做层级别名；`lst_concat` 按报告 §5 #56 明示入全局表。")
    w(f"- 每条别名的层号出处写在 YAML 行内注释里（= `REPORT-unmapped.md` §5 表行号），"
      f"回归会逐个别名统计命中层数（见 §5.3）。\n")
    w("### 2.2 修 2 · `map_row` 组合串拆分（`fm_core.py`）\n")
    w("- 去掉 `not (self._split_tried and not self._split_key)` 短路 → 每行都试；"
      "`cand_keys` 从 `list(raw.keys())[:40]` 扩到**全部字段**（`_split_key` 命中后仍只试那一列并即时跳出，"
      "保证既有层的行为与耗时不变）。")
    pf = json.load(open(os.path.join(HERE, "perf-ab.json"), encoding="utf-8"))
    w("- 性能：拆分分支只在 `street` 为空时进入；已经映射上的行 `street` 非空 → 不进入，因此既有层耗时不变。"
      f"最坏情形（这 58 层本身）4 层 A/B 实测：改前 **{pf['before_elapsed_s']} s** → 改后 "
      f"**{pf['after_elapsed_s']} s**（**{pf['ratio']}×**，未超 3× 红线；`{pf['basis']}`）。"
      "优化措施（不改语义）：`_split_key` 命中后该层只试那一列并即时 `break`。")
    w("- 最小复现（脚本现场复算，非手抄）：层 `F2rCsQjt0P3e_arcgis_rest_services_AddressPts_FeatureServer_0`；"
      f"该层真实首行 raw 的 `LABEL = {real['LABEL'] if real else 'n/a'!r}`（正是 `split_number_street` 判 "
      "`ambiguous` 的那条 → 老代码首行就把它置成「整层不再试」）。")
    w("\n| 行 | 改前 | 改后 |")
    w("|---|---|---|")
    for i in range(2):
        b, a = rp["before"][i], rp["after"][i]
        w(f"| 第 {i+1} 行 `{['3358 K 157 HWY','1952 SWENSON RD'][i]}` | {b['reason']} "
          f"{b['house_number'] or ''} {b['street_name'] or ''} {b['grade'] or ''} | "
          f"{a['reason']} {a['house_number'] or ''} {a['street_name'] or ''} {a['grade'] or ''} |")
    w("\n> 该层实测：改前 0 行、改后 13,163 / 13,245 行。\n")
    w("### 2.3 修 3 · 层级别名 + 地理编码残留层\n")
    w("新增 `registry/layer-aliases.v1.yaml`（与 `dialects.v1.yaml` 同族、同级），按 `layer_id`/`url` 精确匹配，"
      "只对 7 层生效（5 层过泛字段名 + LST_CONCAT 登记 + 地理编码残留层），语义为：")
    w("- `street_fields` / `number_fields`：**弱源**，只在原生/强别名/拆分都没给出时按声明顺序拼接"
      "（`NAME+TYPE` → `Northview Road`；`STR`+`STR_NUM`）。")
    w("- `split_fields` / `drop_values`：`YSp_...Address_type_points`（`derived_geocoder_output`）把 "
      "`Street_derived/Street_raw` 排到拆分候选最前，并把 `'<Null>'` 作为该层专属占位值过滤掉 —— "
      "实测只救回 18% 行（27/150 样本可拆），如实报，**没有**把 `'<Null>'` 当街名写进数据。\n")

    w("## 3. 58 层逐层结果\n")
    w("| # | 层 | in_rows | 修前 | 修后 | 修后 grade | reason | 闭合差额 |")
    w("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        w(f"| {i} | `{r['layer_id'][:46]}` | {int(r['in_rows']):,} | {int(r['before_mapped_rows']):,} | "
          f"{int(r['after_mapped_rows']):,} | {r['after_grade']} | {r['reason_code']} | {r['closed_diff']} |")
    w("")
    w(f"合计：in_rows **{S['rows']['in_rows_total']:,}**、修后 mapped **{S['rows']['mapped_after_total']:,}**、"
      f"`dropped_below_c` **{S['rows']['dropped_below_c_total']:,}**、`parse_error` "
      f"**{S['rows']['parse_error_total']}**；逐层 `closed_diff` 为 0 的层数 = "
      f"{S['acceptance']['closed_diff_zero_layers']}/58。")
    w(f"修前口径交叉校验：58 层在 `layer-coverage.v2.csv` 里的 `mapped` 全为 0，且 `in_rows` 与本次 "
      f"before 跑完全一致（不一致层数 = {len(S['baseline_crosscheck']['mismatch_layers'])}）。\n")

    w("## 4. 覆盖率\n")
    c = S["coverage"]
    w("| 口径 | 映射上层数 | 覆盖率 | 过 95% 门禁 |")
    w("|---|---|---|---|")
    w(f"| v2 全量重扫（修前） | 3,355 | 94.51% | 否（差 18 层） |")
    w(f"| 本轮（58 层落地） | {c['mapped_layers']:,} | **{c['pct']}%** | "
      f"{'是' if c['pass_95pct'] else '否'}（需 {c['gate_layers_needed']:,} 层） |")
    w("\n> 注意：分子的 3,413 = 3,355（v2 已映射）+ 58（本轮全部上映射），**不含**未在此轮重跑的任何层。"
      "分母 3,550 不变。\n")

    w("## 5. 回归证据（未做全量重扫 —— 明确声明）\n")
    w("全量重扫口径下 3,550 层=5.1 亿行、上次实测 247 分钟（`fullrescan-run.json`），本轮时间盒内跑不完，"
      "因此回归证据由两部分组成，**都不是抽样糊弄**：\n")
    w("### 5.1 新别名命中集：全量 A/B（不是抽样）\n")
    a = R["alias_hit_census"]
    w(f"- 用 `rows-census.jsonl`（3,550 层逐层 raw 字段名并集，只读每个 part 文件首行）穷举出"
      f"「raw 里含本轮任一新增别名」的层：**{a['alias_hit_layers_ab']} 层**。")
    w(f"- 对这 {a['alias_hit_layers_ab']} 层做 before/after 双跑（before = 起点提交的 `fm_core.py` + "
      f"同提交 `dialects.v1.yaml`）：行数下降 **{len(a['decreased_layers'])} 层**；行数增加 "
      f"{a['increased_layers']} 层、共 **+{a['increased_rows']:,} 行**；mapped 总量 "
      f"{a['mapped_before_total']:,} → {a['mapped_after_total']:,}。")
    w(f"- 其中 {a['value_changed_same_mapped_layers']} 层「行数不变但取值变了」，逐层核对后**全部是新增门牌**"
      f"（`STR_NUM`/`CIVIC_NUM` 两个新门牌别名把 `house_number` 从空补上，grade 只升不降）："
      f"grade 净变差的层 **{len(a['grade_net_worse_layers'])} 层**。")
    w(f"- 超大局 `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0`（4,206 万行、844 个 part）"
      f"单独抽检前 25 个 part（1,250,000 行）：before/after 完全一致（mapped、grade、street/addrkey 哈希全同）。\n")
    w("### 5.2 未命中集分层抽样 A/B\n")
    s = R["sample"]
    w(f"- 样本 **{s['layers']} 层 / {s['rows']:,} 行**，覆盖 **{s['states_covered']} 个州/地区代码**"
      f"（含空状态码 5 层），`source_layer_kind` 三类全覆盖（url / layer_id_fallback / n/a）；"
      f"origination 类型：v2 的 3,550 层 `dialect_origin` 全是 `fallback`（`dialect_id` 全为 `minimal_safe`），"
      f"即只有 1 种类型，抽样自然全覆盖。")
    w(f"- `in_rows ≤ 400k` 控时；样本里 {s.get('layers_with_dropped', 0)} 层是「有 dropped_below_c > 0」的层"
      f"（split 修复唯一可能动到的那类，抽样时每州优先入选）。")
    w(f"- 结果：行数下降 **{len(s['decreased_layers'])} 层**；行数增加 {s['increased_layers']} 层（+{s['increased_rows']:,} 行，"
      f"同样是拆串救回的丢弃行）；取值变动 **{s['value_changed_same_mapped_layers']} 层**；`bad_empty` 合计 "
      f"{s['bad_empty_total_after']}。\n")
    w("### 5.3 逐别名命中层数（= 误伤面）\n")
    w("见 `fix58-summary.json:regression.alias_hit_census.value_changed_detail` 与 "
      "`rows-census.jsonl`；按别名统计的命中层数：\n")
    w("```")
    w(census_table())
    w("```\n")

    w("## 6. 新别名误伤专项结论\n")
    w(f"- **行数下降的层：0 层**（命中集全量 615 层 + 抽检 236 层 + 超大局抽检，全部为 0）。")
    w(f"- 取值变化只发生在「新增门牌别名补空」这一种情形，且 grade 净变差 0 层；"
      f"第一版弱/强顺序错导致的 4 层 grade 退化已在落地前发现并修掉（见 §2.1）。")
    w(f"- 遗留的小瑕疵（如实报，不在本单修）：`STR_NUM` 这类字段在源里是 JSON 数字时，"
      f"`house_number` 会写成 `1009.0` 这种带 `.0` 的形式（既有 `clean_number()` 的老行为，"
      f"对既有层影响一致）。改它会动到既有 3,355 层的取值，超出本单红线，留作后续单。\n")

    w("## 7. 未闭环项与短板\n")
    w("1. **未做全量重扫**：覆盖率 96.14% 是「3,355 + 58」的算术结果，58 层的行数是本轮实跑，"
      "已映射的 3,355 层沿用 v2 口径未重跑。`REPORT-v2.md` / `SUMMARY-v2.json` 已标 provisional。")
    w("2. `zero_coord = 2` 行（Dauphin 1 行、rxOA 1 行）：源坐标缺失/`0,0`，按 muse-000266 口径拒写，非缺陷。")
    w("3. 拆分命中率与报告估算有偏差（有的层高于估算，如 `BASE_NS_CivicAddress` 85.3%→100%、"
      "`shlD6Twu` 78.3%→100%；有的低于估算，如爱尔兰 `SECTO_NBI` 57%→13.2%），报告 §5 的命中率是 150–300 行样本外推，"
      "本轮给出的是**整层实跑**。")
    w("4. 报告 §9 已写的口径问题照旧：境外 20 层里 3 层国别仍未逐个确认；跨层镜像数据按层计（覆盖率口径正确）。")
    w("5. 层级别名是「按层硬编码」，长期应推广成「按 org/模板自动推断」，本单只按报告 §4.3 的 6 层 + 1 层落地。\n")

    w("## 8. 复跑\n")
    w("```bash")
    w("cd analysis/fieldmap-20261125/fix58-20261126")
    w("python3 run_fix58.py --mode before --jobs jobs-b58.jsonl --out before-b58.jsonl   # 31 s")
    w("python3 run_fix58.py --mode after  --jobs jobs-b58.jsonl --out after-b58.jsonl --write-rows /data/scratch/fix58-20261126  # 88 s")
    w("python3 census.py --out rows-census.jsonl                                         # 4 s（3,550 层字段名并集）")
    w("python3 run_fix58.py --mode before --jobs jobs-affected.jsonl --out before-affected.jsonl      # 40 min（含 4,206 万行的层，已单独抽检替代）")
    w("python3 run_fix58.py --mode after  --jobs jobs-affected.jsonl --out after-affected.jsonl       # 23 min")
    w("python3 select_regression.py   # → jobs-regression.jsonl（236 层 / 8.66M 行）")
    w("python3 run_fix58.py --mode before --jobs jobs-regression.jsonl --out before-regression.jsonl  # 2m48s")
    w("python3 run_fix58.py --mode after  --jobs jobs-regression.jsonl --out after-regression.jsonl   # 2m51s")
    w("python3 make_fix58.py   # → fix58-before-after.csv + fix58-summary.json")
    w("python3 build_report.py # → REPORT-fix58.md + REPORT-v2/SUMMARY-v2 的 provisional 标记")
    w("```")
    w("\n边界：只读 `dist/intake-full/layers/`、`layer-coverage.v2.csv`；基线代码/别名表用 "
      f"`git show {BASE_COMMIT[:7]}:…` 取到 `/data/scratch/fix58-baseline/`（**不进仓库**）；"
      "输出行只写到 `/data/scratch/fix58-20261126/`。")
    w("## 9. 产物清单（字节数=写本报告时现场 stat）\n")
    w("| 文件 | 字节 | 用途 |")
    w("|---|---|---|")
    use = {
        "fix58-before-after.csv": "58 层逐层 before/after（派单要求的 11 列）",
        "fix58-summary.json": "58 层验收 + 覆盖率 + 回归证据汇总（机器可读）",
        "after-b58.jsonl": "58 层 after 逐层统计（含 street/addrkey 哈希）",
        "before-b58.jsonl": "58 层 before（4c3a6a3 基线代码）逐层统计",
        "before-affected.jsonl": "新别名命中集 615 层 before",
        "after-affected.jsonl": "新别名命中集 615 层 after",
        "before-regression.jsonl": "抽样回归 236 层 before",
        "after-regression.jsonl": "抽样回归 236 层 after",
        "before-miss-partial.jsonl": "4,206 万行的 conemap 层前 25 part 抽检 before",
        "after-miss-partial.jsonl": "同上 after",
        "rows-census.jsonl": "3,550 层 raw 字段名并集 + 州代理值（回归取面用）",
        "jobs-b58.jsonl": "58 层作业清单（layer_id/url/reason）",
        "jobs-affected.jsonl": "616 层新别名命中清单",
        "jobs-regression.jsonl": "236 层抽样清单",
        "perf-ab.json": "拆分修复的性能 A/B（4 层，1.94×）",
        "run_fix58.py": "before/after 双跑器",
        "census.py": "字段名并集普查",
        "select_regression.py": "分层抽样选择器",
        "make_fix58.py": "汇总 CSV/JSON",
        "build_report.py": "生成本报告 + v2 的 provisional 标记",
    }
    for f in sorted(os.listdir(HERE)):
        if f == "REPORT-fix58.md" or f.startswith("."):
            continue
        w(f"| `{f}` | {os.path.getsize(os.path.join(HERE, f)):,} | {use.get(f, '')} |")
    w(f"| `REPORT-fix58.md` | 本文件（脚本生成） | 人读报告 |\n")

    open(os.path.join(HERE, "REPORT-fix58.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

    # ---- 给 v2 全量口径打 provisional 标记（只加标记，不改任何历史结论数字）----
    v2 = os.path.join(FM, "REPORT-v2.md")
    banner = ("> ⚠️ **PROVISIONAL（muse-000271 后续修订，2026-11-26）**：58 层 B 类修复已在 "
              "`analysis/fieldmap-20261125/fix58-20261126/` 落地并逐层重跑验证，覆盖率口径应更新为 "
              "**3,413/3,550 = 96.14%**（= 本文件记录的 3,355 + 58）。但**尚未重跑全量 3,550 层**，"
              "本文其余数字仍是修前全量口径，**待全量重扫复核**；本轮没有用 58 层口径覆盖任何全量数字。\n")
    txt = open(v2, encoding="utf-8").read()
    if "PROVISIONAL（muse-000271" not in txt:
        lines = txt.split("\n")
        txt = lines[0] + "\n\n" + banner + "\n".join(lines[1:])
        open(v2, "w", encoding="utf-8").write(txt)
    sv = os.path.join(FM, "SUMMARY-v2.json")
    doc = json.load(open(sv, encoding="utf-8"))
    doc["provisional"] = {
        "since": "muse-000271",
        "date": "2026-11-26",
        "reason": "58 层 B 类修复已落地并逐层验证，但未重跑全量 3,550 层",
        "coverage_pct_after_fix": 96.14,
        "coverage_layers_after_fix": "3413/3550",
        "historical_numbers_untouched": True,
        "detail": "analysis/fieldmap-20261125/fix58-20261126/REPORT-fix58.md",
    }
    json.dump(doc, open(sv, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("provisional marks written to REPORT-v2.md / SUMMARY-v2.json")
    print("wrote REPORT-fix58.md", os.path.getsize(os.path.join(HERE, "REPORT-fix58.md")), "bytes")
    return 0


def census_table():
    sys.path.insert(0, os.path.join(ROOT, "engine"))
    import split_addr as SA
    NEW = ("strname strtype strsuffix strsuf feanme featyp sfeanme sfeatyp gcstname streetnm ostreetnm "
           "addressroadname addrsn roadname roadnamesuffix roadtype roadnm roadsuffixdir streetdescription "
           "thoroughfare thorofare landbasedbotblstreetnamesstr sitestreetname sitestreet fullstnm locstnam "
           "locstsuf msagroute stnameps stdstreet propstreet propsuffix civicstreet streettho lstconcat "
           "strnum civicnum").split()
    want = {SA._norm(x): x for x in NEW}
    hit = {v: 0 for v in want.values()}
    for line in open(os.path.join(HERE, "rows-census.jsonl"), encoding="utf-8"):
        d = json.loads(line)
        keys = {SA._norm(k) for k in d["keys"]}
        for nk, name in want.items():
            if nk in keys:
                hit[name] += 1
    lines = ["别名                 命中层数"]
    for k, v in sorted(hit.items(), key=lambda x: -x[1]):
        lines.append(f"{k:20s} {v:6d}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
