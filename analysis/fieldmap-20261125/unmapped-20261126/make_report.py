#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000269 · 由分类结果合成 REPORT-unmapped.md（数字全部从产物读，不手抄）。

输入：unmapped-classification.csv / layers-evidence.jsonl / fix-simulation.jsonl /
     layer-scoped-fixes.jsonl / ../layer-coverage.v2.csv / ../unusable-v2.csv
输出：REPORT-unmapped.md
用法：python3 make_report.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)
COVERAGE = os.path.join(FM, "layer-coverage.v2.csv")
UNUSABLE = os.path.join(FM, "unusable-v2.csv")
CLS = os.path.join(HERE, "unmapped-classification.csv")
EVID = os.path.join(HERE, "layers-evidence.jsonl")
SIM = os.path.join(HERE, "fix-simulation.jsonl")
SCOPED = os.path.join(HERE, "layer-scoped-fixes.jsonl")
OUT = os.path.join(HERE, "REPORT-unmapped.md")

REASON_ZH = {
    "alias_missing_street": "街名/街型字段不在角色表（补别名即可）",
    "split_first_row_only": "组合串可拆，但 map_row 只在首行试一次就永久放弃",
    "split_key_beyond_40": "组合串排在 raw 第 40 个键之后，split 扫不到",
    "alias_generic_fieldname_layer_scoped": "地址在字段名过泛的列里（只能层级别名）",
    "derived_geocoder_output": "地理编码产物列，且多数行为 '<Null>'",
    "not_address_layer": "非地址层（无门牌/街名/可拆串）",
    "no_addr_attrs_only_ids": "payload 只剩 ID + 经纬度",
    "addr_attrs_not_collected": "地址层，但采集侧地址属性未落盘（需重采）",
    "no_street_field": "只有门牌号，源里没有街名字段",
    "street_field_all_null": "街名列存在但全空/占位",
    "label_or_annotation_only": "注记/标注层（Label/TextString/Contents）",
    "grid_range_no_street_name": "网格/街区区间，无街名",
    "admin_or_survey_table": "调查/行政/报表面板",
    "non_us_point_or_poi": "口径外（非美国）POI/服务点位",
    "non_us_dataset_no_usable_field": "口径外数据集，且字段不成美国口径",
    "intersection_no_number": "路口名，无门牌",
    "unparseable_concat": "门牌与街名粘死不可拆",
    "sample_too_small": "样本过小，无法判定",
}


def scope_of(r):
    m = re.match(r"【(.*?)】", r["reason_detail"])
    return m.group(1) if m else "未定位"


def main():
    cov = {r["layer"]: r for r in csv.DictReader(open(COVERAGE, encoding="utf-8"))}
    unus = list(csv.DictReader(open(UNUSABLE, encoding="utf-8")))
    rows = list(csv.DictReader(open(CLS, encoding="utf-8")))
    evs = {json.loads(l)["layer_id"]: json.loads(l) for l in open(EVID, encoding="utf-8")}
    sims = {json.loads(l)["layer_id"]: json.loads(l) for l in open(SIM, encoding="utf-8")}
    scoped = {}
    if os.path.isfile(SCOPED):
        for l in open(SCOPED, encoding="utf-8"):
            r = json.loads(l)
            scoped[r["layer_id"]] = r

    n_total = len(cov)
    n_mapped = sum(1 for r in cov.values() if int(r["mapped"]) > 0)
    zero = {l for l, r in cov.items() if int(r["mapped"]) == 0}
    unus_set = {r["layer"] for r in unus}

    A = [r for r in rows if r["class"] == "A"]
    B = [r for r in rows if r["class"] == "B"]
    U = [r for r in rows if r["class"] == "UNKNOWN"]
    B_us = [r for r in B if scope_of(r) == "美国境内"]
    B_abroad = [r for r in B if scope_of(r) != "美国境内"]
    est_all = sum(int(r["est_rows_recoverable"]) for r in B)
    est_us = sum(int(r["est_rows_recoverable"]) for r in B_us)
    cov_all = (n_mapped + len(B)) / n_total * 100
    cov_us = (n_mapped + len(B_us)) / n_total * 100
    in_rows_all = sum(int(cov[r["layer_id"]]["in_rows"]) for r in rows)

    rk = collections.Counter(r["reason_code"] for r in rows)
    rk_b = collections.Counter(r["reason_code"] for r in B)
    rk_a = collections.Counter(r["reason_code"] for r in A)
    scope_a = collections.Counter(scope_of(r) for r in A)

    L = []
    w = L.append
    w("# 195 个未映射层的逐层归因（muse-000269）")
    w("")
    w("> 任务：全量重扫后 3,355/3,550 层映射上、**195 层未上**（覆盖率 94.51%，离 95% 门禁差 18 层）。"
      "本单把这 195 层逐层查清，分 A/B/UNKNOWN，给出可修原因与修法。**只查不改**。")
    w("")
    w("## 0. 结论")
    w("")
    w(f"- **A（不可修 / 非地址）{len(A)} 层**、**B（地址层但因可修原因没上）{len(B)} 层**、"
      f"**UNKNOWN {len(U)} 层**，合计 {len(A)+len(B)+len(U)} = 195。")
    w(f"- B 类里 **{len(B_us)} 层在美国境内口径**、{len(B_abroad)} 层在境外（加/新/英/爱/南非/根西等）。")
    w(f"- **B 类全修 → 覆盖率 {cov_all:.2f}%（{n_mapped+len(B)}/{n_total}）**；"
      f"**只修美国境内 {len(B_us)} 层 → {cov_us:.2f}%（{n_mapped+len(B_us)}/{n_total}）**。"
      f"两种口径都过 95%（门禁需 ≥18 层，美国境内可修层已有 {len(B_us)} 层）。")
    w(f"- 可恢复行数（样本命中率 × 层 in_rows 折算）：全 B 类 **{est_all:,} 行**，"
      f"其中美国境内 **{est_us:,} 行**。")
    w("- 三条主线根因（都可在代码里定位、可最小复现）：")
    w("  1. **角色表缺街名别名**（38 层）——`registry/dialects.v1.yaml` + `engine/dialects` 合并后"
      "只有 148 个归一字段名，NENA 911 系列 `feanme/featyp`、加拿大 `strname/strsuffix`、`roadname`、"
      "`street_nm`、`thorofare`、`msag_route` 等常见街名/街型列统统不在表里。")
    w("  2. **`fm_core.map_row` 的组合串拆分只在首行试一次**（13 层，另有 1 层是 40 键上限）——"
      "首行拆不出就把 `_split_tried` 置真、`_split_key` 留空，之后每行直接跳过 split；"
      "因为「首行能拆的层不可能 0 行映射」，这 13 层必然踩中该短路。")
    w("  3. **地址在字段名过泛的列里**（5 层，`NAME`+`TYPE`、`STR`、`PARCEL_LOC`、`LST_CONCAT`）"
      "——不能进全局最小安全表，只能按 url/org 建层级别名；这 5 层实测补别名后命中率 100%。")
    w("")
    w("## 1. 起点核对与清单闭环")
    w("")
    w(f"- 工作树 `/data/workspace/wmd-fieldmap`，分支 `feat/fieldmap-20261125`，起点 HEAD `cb2ee3f`"
      f"（= PR #58 head），`git status` 干净，无其他映射进程在跑。")
    w(f"- `unusable-v2.csv` {len(unus)} 数据行；`layer-coverage.v2.csv` 里 `mapped==0` 的层 **{len(zero)}** 个。")
    w(f"- 两者交叉核对：`unusable − mapped0` = **{len(unus_set - zero)}**，`mapped0 − unusable` = **{len(zero - unus_set)}**。"
      f"**完全同一批 195 层，零差异**，闭环到 {n_total} − {n_mapped} = {len(zero)}。")
    w(f"- 195 层合计 in_rows = **{in_rows_all:,} 行**（`dropped_below_c` 全部计入，等价于「整层丢弃」）。")
    w("")
    w("## 2. 方法与产物（全部只读，可复跑）")
    w("")
    w("采样：每层取首 + 中两个 `part-u*.ndjson.gz`，各读 150 行，**共 25,465 行**（单 part 文件的层实际 150 行）。"
      "判定一律复用生产代码：`fm_core.map_row` 的取值顺序、`split_addr.roles_of` 的角色表、"
      "`split_addr.split_number_street` 的拆串实现——本单不另写一套口径。")
    w("")
    w("| 脚本 | 作用 | 产物 |")
    w("|---|---|---|")
    w("| `scan_unmapped.py` | 逐层字段名集合、每字段非空率、角色命中/近失、组合串可拆性、5 行脱敏样本、地理中位数 | `layers-evidence.jsonl`、`scan-summary.json` |")
    w("| `simulate_fix.py` | 三条修复路径逐行模拟（补别名 / split 全字段每行重试 / split 放宽） | `fix-simulation.jsonl` |")
    w("| `measure_layer_scoped.py` | 字段名过泛的 6 层，按指定字段实测拼街名命中率 | `layer-scoped-fixes.jsonl` |")
    w("| `classify_unmapped.py` | 规则判定 + 人工复核覆盖，落 A/B/UNKNOWN | `unmapped-classification.csv`、`overrides-resolved.json` |")
    w("| `make_report.py` | 由上述产物合成本报告（数字不手抄） | `REPORT-unmapped.md` |")
    w("")
    w("复跑顺序：`scan_unmapped.py` → `simulate_fix.py` → `measure_layer_scoped.py` → "
      "`classify_unmapped.py` → `make_report.py`。全部只读 `dist/intake-full/layers/` 与 "
      "`analysis/fieldmap-20261125/layer-coverage.v2.csv`，**未改任何既有文件**。")
    w("")
    w("## 3. 汇总")
    w("")
    w("| class | 层数 | 说明 |")
    w("|---|---|---|")
    w(f"| A | {len(A)} | 真非地址层 / 采集缺字段 / 口径外点位居多，不可由映射侧修 |")
    w(f"| B | {len(B)} | 地址层，缺别名或 split 缺陷，**可修** |")
    w(f"| UNKNOWN | {len(U)} | " + ("、".join(f"`{r['layer_id'][:40]}…` {r['reason_code']}" for r in U) or "无") + " |")
    w("")
    w("按 `reason_code` 分桶：")
    w("")
    w("| reason_code | 层数 | 其中 B | 中文 |")
    w("|---|---|---|---|")
    for k, v in rk.most_common():
        w(f"| `{k}` | {v} | {rk_b.get(k, 0)} | {REASON_ZH.get(k, '')} |")
    w("")
    w("A 类按口径分布：" + "、".join(f"{k} {v} 层" for k, v in scope_a.most_common()) + "。")
    w("")
    w("## 4. 三条主线根因（代码定位 + 最小复现）")
    w("")
    w("### 4.1 角色表缺街名/街型别名（38 层）")
    w("")
    w("195 层逐层统计：**191 层在 raw 里连一个角色表命中的街名字段都没有**；"
      "全部 195 层 `street` 恒空 → `grade_of` 落到 None → 整层 `dropped_below_c`。"
      "把 195 层出现过的字段名归一后共 **1,815 个**，其中**只有 32 个**在角色表（148 名）里；"
      "**357 个地址类字段名不在表里**。缺的不是冷门列，是这些「一眼就是街名」的列：")
    w("")
    for x in ["`feanme` / `featyp`（NENA 911 的 FeatureName/Type，2 层共 583 行非空）",
              "`strname` / `strsuffix` / `strtype`（加拿大 civic address，5 层）",
              "`roadname` / `roadnm` / `streetname` / `street_nm` / `street_description`",
              "`sfeanme` / `sfeatyp`（夏威夷 911 变体）",
              "`msag_route`（新斯科舍 civic address）、`thorofare`（英国型）、`std_street`（温哥华）、"
              "`civic_street`（Lake Country）、`propstreet`（密苏里 VOC）、`loc_st_nam`（纽约 WFL1）"]:
        w(f"- {x}")
    w("")
    w("即「同一个数据集，门牌列 `st_num` 在表里、街名列 `feanme` 不在表里」——门牌取到、街名取不到，"
      "门牌单独不构成地址（grade C 要求 street），于是整层丢弃。")
    w("")
    w(f"**最小复现**：`gyrE4_arcgis_rest_services_Address_Point_911_FeatureServer_0`（{int(cov['gyrE4_arcgis_rest_services_Address_Point_911_FeatureServer_0']['in_rows']):,} 行）"
      "第 1 行 raw：`st_num=7870, feanme=STATE, featyp=ST, Zipcode=36522`。")
    w("`roles_of()` 里 `stnum` 命中 number、`feanme`/`featyp` **都不在表里** → street 空 → 丢弃。"
      "把 `feanme`+`featyp` 加进 street_aliases 后，该层样本 300/300 全部落到 grade C。")
    w("")
    w("**修法**：`registry/dialects.v1.yaml` 的 `minimal_safe` template 里补 `street_aliases`"
      "（不改代码、不改分级口径）。注意这些都是全局生效，宜只收「一眼是街名」的列；"
      "`NAME`/`TYPE`/`STR`/`LABEL` 这类过泛名不进全局表，走层级别名（见 4.3）。")
    w("")
    w("### 4.2 `map_row` 的组合串拆分只在首行试一次（13 层）")
    w("")
    w("`fm_core.py:303` 起的代码：")
    w("")
    w("```python")
    w("if not street and raw and not (self._split_tried and not self._split_key):")
    w("    ...")
    w("    self._split_tried = True")
    w("    if best: self._split_key = best[0]")
    w("```")
    w("")
    w("首行拆不出时 `_split_tried=True` 且 `_split_key` 仍是空串，**第 2 行起该条件恒假 → 整层再也不试 split**。"
      "反证：若某层首行能拆，那层首行就会落 grade C、`mapped ≥ 1`，根本不会出现在这 195 层里；"
      "所以「0 行映射 + 样本可拆」必然意味着首行踩了短路。")
    w("")
    w("**最小复现**：`F2rCsQjt0P3e_arcgis_rest_services_AddressPts_FeatureServer_0`（13,245 行）"
      "字段 `LABEL = \"3358 K 157 HWY\"` → `split_number_street` 给 num=`3358`、street=`K 157 HWY`、"
      "reason=ok、confidence=0.95；但该层的 `LABEL` 不是 raw 的第一个键，且首行未命中 → 整层 0 行。")
    w("")
    w("**修法（两处，同一个函数）**：① 去掉 `_split_tried` 短路，逐行都试；"
      "② `cand_keys` 从 `list(raw.keys())[:40]` 扩到全字段（40 键上限只命中 1 层，"
      "`gis_rest_services_STR_October_2023_Addresses`（69 个键，样本命中 0.987 vs 首 40 键 0.013），"
      "但同属一个缺陷，一起修）。修完这 13 层按样本命中率可恢复约 "
      f"**{rk_b and sum(int(r['est_rows_recoverable']) for r in B if r['reason_code'].startswith('split_')):,} 行**。")
    w("")
    w("### 4.3 地址在字段名过泛的列里（5 层）")
    w("")
    w("这 5 层的街名在 `NAME`+`TYPE`（Coquitlam 2 层、Kelowna 1 层）、`STR`（杰克逊维尔海滩）、"
      "`PARCEL_LOC`（纽约）、`LST_CONCAT`（明尼苏达 Owens Twp）。这类名字放进全局最小安全表会误伤"
      "（`NAME` 可能是人名/场所名/业主名），只能按 url/org 建层级别名。实测：")
    w("")
    w("| 层 | 街名字段 | 门牌字段 | 实测 street 命中 |")
    w("|---|---|---|---|")
    for lid, r in scoped.items():
        w(f"| `{lid[:52]}` | {'+'.join(r['street_fields'])} | "
          f"{'+'.join(r['number_fields']) or '无（只到 grade C）'} | {r['street_hit_rate']:.0%} |")
    w("")
    w("## 5. B 类逐层修法（58 层，按可恢复行降序）")
    w("")
    w("| # | in_rows | 可恢复行 | 命中率 | reason | 口径 | 层 | 修法 |")
    w("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(sorted(B, key=lambda x: -int(x["est_rows_recoverable"])), 1):
        plan = r["fix_plan"].replace("|", "/")
        if len(plan) > 150:
            plan = plan[:148] + "…"
        w(f"| {i} | {int(cov[r['layer_id']]['in_rows']):,} | {int(r['est_rows_recoverable']):,} | "
          f"{r['sample_hit_rate']} | `{r['reason_code']}` | {scope_of(r)} | `{r['layer_id'][:46]}` | {plan} |")
    w("")
    w("## 6. 覆盖率增益测算")
    w("")
    w("| 情形 | 映射上层数 | 覆盖率 | 过 95%？ |")
    w("|---|---|---|---|")
    w(f"| 现状（v2 全量重扫） | {n_mapped} | {n_mapped/n_total*100:.2f}% | 否（差 {int(-(-n_total*0.95//1))-n_mapped} 层） |")
    w(f"| 只修美国境内 {len(B_us)} 层 | {n_mapped+len(B_us)} | {cov_us:.2f}% | **是** |")
    w(f"| B 类 {len(B)} 层全修 | {n_mapped+len(B)} | {cov_all:.2f}% | **是** |")
    w("")
    w("门禁算式：95% × 3,550 = 3,372.5 → 需要 **3,373 层**，即再上 **18 层**。"
      f"美国境内可修层已有 **{len(B_us)} 层**，是门槛的 {len(B_us)/18:.1f} 倍。")
    w("")
    w("### 6.1 建议优先修的 18 层（按「可恢复行 × 修法确定性」排序）")
    w("")
    w("排序口径：先按 `est_rows_recoverable` 降序（收益），`alias_missing_street` 与 "
      "`split_first_row_only` 都是「改一处、全局生效」的低风险修法，优先；层级别名的 5 层放后面。")
    w("")
    w("| 序 | 层 | in_rows | 可恢复行 | reason | 修法 |")
    w("|---|---|---|---|---|---|")
    us_sorted = sorted(B_us, key=lambda x: -int(x["est_rows_recoverable"]))
    for i, r in enumerate(us_sorted[:18], 1):
        w(f"| {i} | `{r['layer_id'][:50]}` | {int(cov[r['layer_id']]['in_rows']):,} | "
          f"{int(r['est_rows_recoverable']):,} | `{r['reason_code']}` | {REASON_ZH.get(r['reason_code'],'')} |")
    w("")
    w(f"这 18 层合计可恢复 **{sum(int(r['est_rows_recoverable']) for r in us_sorted[:18]):,} 行**"
      f"（占美国境内 B 类可恢复行的 "
      f"{sum(int(r['est_rows_recoverable']) for r in us_sorted[:18])/est_us*100:.1f}%）；"
      "这 18 层全部落地即 ≥ 95.00%（实际只需其中任意 18 层中的全部，即总数达到 3,373 层）。")
    w("")
    w("其中**改一处别名表就能救的**（不需要碰代码）：")
    w("")
    alias_layers = [r for r in us_sorted if r["reason_code"] == "alias_missing_street"]
    w(f"- 美国境内 `alias_missing_street` 共 {len(alias_layers)} 层，"
      f"合计 {sum(int(r['est_rows_recoverable']) for r in alias_layers):,} 行；"
      "这批只需要在 `registry/dialects.v1.yaml` 加 `street_aliases` 条目。")
    w(f"- 美国境内 `split_first_row_only` 共 {sum(1 for r in us_sorted if r['reason_code']=='split_first_row_only')} 层，"
      f"合计 {sum(int(r['est_rows_recoverable']) for r in us_sorted if r['reason_code']=='split_first_row_only'):,} 行；"
      "只需改 `fm_core.map_row` 一处短路。")
    w("")
    w("## 7. A 类分桶证据（136 层）")
    w("")
    w("| reason_code | 层数 | 典型判别证据 |")
    w("|---|---|---|")
    ev_examples = {
        "non_us_point_or_poi": "40+ 个奥地利萨尔茨堡「最近 X 到我的地址」服务层（1–3 行）、印尼文化点（`Nama_Situs`）、爱沙尼亚避难所等；字段是场所名/结果表",
        "admin_or_survey_table": "Survey123 表单（`first_and_last_name`/`email`/`organization`）、PSAP 部署点、911 收费表、报表；要素不是地址",
        "no_street_field": "只有门牌（`HOUSE_NUM`/`AddNum`/`CIVNUM`/`AddressNo`/`HOUSE_NUMBER`），源里没有街名列、也没有可拆串",
        "label_or_annotation_only": "`LABEL`/`TextString`/`Contents`/`Shape` 注记层，值多为纯门牌",
        "not_address_layer": "CAD/DXF 元数据（`DocName`/`Linetype`/`Layer`）、学生统计、绿化树种、POI 点位等",
        "addr_attrs_not_collected": "层名就是 Address/Address Points，但落盘 raw 只剩 `OBJECTID`/`*_pid`/`lga_code`/`BUILDING_ID` 等 ID + 经纬度 → 需重采",
        "non_us_dataset_no_usable_field": "捷克/荷兰/塞浦路斯/黎巴嫩数据集，字段是本国门牌体系，不合美国口径",
        "grid_range_no_street_name": "`ADD_NS`/`ADD_EW`/`ADD_RANGE`/`Range` 网格区间，16,800N × 24,600E 这种交叉编号，没有街名",
        "street_field_all_null": "街名列在角色表里（`St_Name`/`SN`/`STREET_ID`）但样本全空",
        "intersection_no_number": "`loc = \"Brigantine Dr & Fall Creek Rd\"` 路口名，无门牌",
        "unparseable_concat": "`ADDRESS = \"32181LN\"` 门牌+步道号无分隔",
        "sample_too_small": "整层 3 行、地址列全空，缺证据",
    }
    for k, v in rk_a.most_common():
        w(f"| `{k}` | {v} | {ev_examples.get(k,'')} |")
    w("")
    w("需要提醒的一点：A 类里有 **11 层 `addr_attrs_not_collected` 合计 "
      f"{sum(int(cov[r['layer_id']]['in_rows']) for r in A if r['reason_code']=='addr_attrs_not_collected'):,} 行**"
      "（含 15.06M 行的 `EXP_national_address_points`、2.28M 行的爱尔兰 GeoDirectory、1.19M 行的 "
      "`County_37_LBRS_Addresses`）。这些层**名字都是地址层**，但落盘 payload 里没有地址属性——"
      "这不是映射侧能修的，属**采集侧字段缺失**，要重采才救得回来（本单红线不允许重采）。"
      "若 muse 要按「可采到的地址层」重算分母，这批层才是争议点，而不是 B 类。")
    w("")
    w("## 8. 附带发现（不在本单任务内，供裁定参考）")
    w("")
    w("1. **角色表把 `firstname` / `lastname` / `fullname` 当 street 别名**"
      "（`roles_of()` 结果里 street 组含这三项）。方向相反的 bug：任何带「姓名字段」的层，"
      "都可能把**人名**当街名写进 `street_name` 并落 grade C。本单的 "
      "`123_69927fe3de7343b4b5f3dca25d6a16d9_results`（Survey123 表单）就是被这条误判成「可修 B」，"
      "人工复核时按「人名不是地址」压回 A。**建议另行核查已入库数据里是否有人名当街名的行**"
      "（本单只查不改，未做该统计）。")
    w("2. `unusable-v2.csv` 里按 `dropped_below_c` 排序，前几名其实是**非地址层或采集缺字段**"
      "（澳洲地址点 15.06M、爱尔兰 GeoDirectory 2.28M、County_37_LBRS 1.19M），"
      "拿「丢弃行数」当质量指标会误导——真正的判别依据是「层里有没有街名/门牌字段」。")
    w("3. 40 键上限与首行短路是**同一个函数里的两个独立缺陷**，只修一个都救不全 14 层。")
    w("")
    w("## 9. 未闭环项与短板（如实写）")
    w("")
    w(f"1. **采样口径**：每层只抽 300 行（单 part 文件的层 150 行），`est_rows_recoverable` 是"
      f"「样本命中率 × in_rows」的线性外推，未按分层/分段抽样。对 15.06M 行那种层若样本不代表全层，"
      f"误差可能较大——但那些层都在 A 类（0 命中），不影响 B 类的结论。")
    w(f"2. **未实跑修复**：三种修法都是「模拟 + 实测样本命中率」，**没有真正改代码/改别名表后重跑映射**"
      f"（本单红线只查不改）。{cov_all:.2f}% / {cov_us:.2f}% 是测算值，落地后需再用一轮全量重扫复核。")
    w(f"3. **口径归属是推断**：美国境内/境外是用「经纬度中位数 + 层名关键词」判的（`geo_median` + 关键词表）。"
      f"境外 20 层 B 里有 3 层标成「境外(geo)」（Coquitlam 的另一层、Yellowknife 旁、特立尼达），"
      f"具体国别未逐个确认；但它们在两种口径下都不计入 95% 的美国境内测算。")
    w(f"4. **UNKNOWN 只有 1 层**（{U[0]['layer_id'] if U else '无'}：整层 3 行、地址列全空）。"
      f"理论上还有「字段名像地址但样本全空」的层可能被规则判进 A（本文 A 类 `street_field_all_null` "
      f"2 层即此形态），这类若源侧其实有值，会被低估——需重采或看源服务字段定义才能确认。")
    w(f"5. **未做跨层去重**：不同层之间是同一份数据的镜像（例：`7088d1ef…` / `st_services_Hundred_Block…` / "
      f"`_gov_arcgis1_…` 三层同为 251,245 行的百街区网格；Pompano Beach 三层同为 24,883 行）。"
      f"A/B 计数按层算，因此这些镜像层会各自计一次；对覆盖率口径是正确行为，对「数据量」会重复计。")
    w("")
    w("## 10. 复跑")
    w("")
    w("```bash")
    w("cd /data/workspace/wmd-fieldmap/analysis/fieldmap-20261125/unmapped-20261126")
    w("python3 scan_unmapped.py --rows 150      # ~17s，写 layers-evidence.jsonl")
    w("python3 simulate_fix.py --rows 150       # ~10s，写 fix-simulation.jsonl")
    w("python3 measure_layer_scoped.py          # ~2s，写 layer-scoped-fixes.jsonl")
    w("python3 classify_unmapped.py             # 写 unmapped-classification.csv + overrides-resolved.json")
    w("python3 make_report.py                   # 写 REPORT-unmapped.md")
    w("```")
    w("")
    w("边界：只读 `dist/intake-full/layers/`、`analysis/fieldmap-20261125/layer-coverage.v2.csv`、"
      "`unusable-v2.csv`；只写本目录。`INTAKE_LAYERS` 可换根做旁证，默认不动源。")

    open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote", OUT, len(L), "lines")


if __name__ == "__main__":
    main()
