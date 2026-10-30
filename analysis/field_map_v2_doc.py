#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 schema/field-map-v2.json 渲染成 docs/FIELD-MAP-V2-2026-10-30.md（纯离线）。"""
from __future__ import annotations

import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "schema", "field-map-v2.json")
DST = os.path.join(ROOT, "docs", "FIELD-MAP-V2-2026-10-30.md")

ORDER = ["house_number", "house_number_suffix", "street_pre_dir", "street_name", "street_post_type",
         "street_post_dir", "street_full", "unit", "postal_city", "municipal_city", "county_name",
         "county_fips", "state_abbr", "zip5", "latitude", "longitude", "addr_type",
         "full_formatted_address", "source_confidence"]


def main() -> int:
    d = json.load(open(SRC, encoding="utf-8"))
    cov = d["coverage"]
    rw = cov["row_weighted"]
    n = cov["layers_profiled"]
    L = d["layers"]
    tf = {t["name"]: t for t in d["target_fields"]}

    out = []
    A = out.append
    A("# 三仓逐层字段 → 二仓 SCHEMA 2.0 主字段 映射 v2（2026-10-30）")
    A("")
    A("> **这不是 schema。** 目标字段名逐字取自二仓 `ip9988001/world-map-data-test` 的 **LOCKED SCHEMA 2.0**，"
      "本表不新增、不改名、不重定义任何规范字段；找不到源列的字段一律留 `null` 并写明原因。")
    A("")
    s = d["schema_ref"]
    A(f"- schema 版本：`{s['schema_version']}` / `{s['status']}` / frozen_at `{s['frozen_at']}`")
    A(f"- 来源：`{s['repo']}` → `{s['path']}`，commit `{s['commit'][:12]}`")
    A(f"- 原样副本：`{s['pinned_copy']}`，sha256 `{s['sha256'][:16]}…`（脚本启动即校验，不符直接退出）")
    A(f"- 映射层数：**{n}**（点层 {cov['by_kind'].get('address_point', 0)} / 宗地层 "
      f"{cov['by_kind'].get('parcel_situs', 0)}），声明行数合计 **{cov['rows_total_declared']:,}**")
    A(f"- 输入：`analysis/out/*.json`（{cov['profile_files']} 份逐层画像，**未重跑摸底**）+ "
      f"`collect/address_layers.csv` / `collect/situs_layers.csv`（层元数据）")
    A(f"- 网络：**无**。未访问上游 ArcGIS/Census，只读既有 Release 分析结果")
    A("")
    A("## 一、19 个目标主字段的覆盖")
    A("")
    A("`层覆盖` = 该字段能指到源列/层元数据/几何的层数占比；`行覆盖` = 这些层的声明行数占比；"
      "`估非空行` = Σ(rows_total × 样本非空率)，是**行级**可得量的近似。")
    A("")
    A("| SCHEMA 字段 | 源列层 | 层元数据 | 规则/派生 | 层覆盖 | 含派生 | 行覆盖 | 估非空行 | 行级估非空 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for t in ORDER:
        x = tf[t]
        r = rw[t]
        A(f"| `{t}` | {x['layers_from_column']} | {x['layers_from_layer_meta']} | {x['layers_rule']} | "
          f"{x['coverage_pct']:.1f}% | {x['coverage_pct_with_derived']:.1f}% | "
          f"{r['row_coverage_pct']:.1f}% | {r['rows_est_nonnull']:,} | "
          f"{r['rows_est_nonnull_pct']:.1f}% |")
    A("")
    A("`addr_type` / `full_formatted_address` / `source_confidence` 没有源列，按 SCHEMA 自身的口径处理：")
    A("")
    A("- `addr_type`：SCHEMA 写「规则重分类」，三仓没有任何 Residential/Commercial 侧证据 → **全部 null**，"
      "并逐层写入 `value_rule`（建议规则：unit 非空 → `Residential (Multi-Unit)`；层标题含 COMMERCIAL/BUSINESS → "
      "`Commercial`；宗地无证据 → `Unknown`；其余 `Residential`）。规则要你点头才落值，本轮不伪造。")
    A("- `full_formatted_address`：纯合成列，逐层标 `derivable=true` 与拼装式："
      "`house_number + ' ' + street_full + ', ' + postal_city + ', ' + state_abbr + ' ' + zip5`"
      "（缺项退化为 `house_number + ' ' + street_full + ', ' + state_abbr`）。不写死值，避免把抽样值当全量。")
    A("- `source_confidence`：按 SCHEMA `grade_rules`，**单层单源只能是 B-Tier**（S/A 需 NAD+TIGER+OA 多源 join）。"
      "逐层写 `proposed_value=B-Tier`。")
    A("")
    A("## 二、留 null 的原因分布（逐字段 Top）")
    A("")
    A("| SCHEMA 字段 | 空层数 | 原因 |")
    A("|---|---|---|")
    for t in ORDER:
        rs = tf[t]["null_reasons"]
        if not rs:
            continue
        top = "；".join(f"{k} ×{v}" for k, v in list(rs.items())[:3])
        A(f"| `{t}` | {tf[t]['layers_null']} | {top} |")
    A("")
    A("口径：**宁愿 null 也不猜**。凡「候选列存在但示例值不像该字段」的（如 `COUNTY=882276` 当县名、"
      "`ZIP5=0` 当 5 位邮编、投影坐标当经纬度），一律拒用并把理由写进该层 `reason`。")
    A("")
    A("## 三、门牌号与街名：原生取列 vs 从整串地址切")
    A("")
    q = Counter((e.get("house_number") or {}).get("quality") for e in L.values()
                if (e.get("house_number") or {}).get("src"))
    zs = [k for k, e in L.items() if (e.get("house_number") or {}).get("zero_share")]
    A(f"- `house_number` 原生列：**{q.get('native', 0)} 层**；从整串地址（ADDRESS/FULLADDR/SITUS_ADDR…）用 "
      f"`^(\\d+[A-Za-z]?)` 切首段：**{q.get('extracted', 0)} 层**（标 `quality=extracted`，下游可分级信任）")
    A(f"- 有 **{len(zs)} 层**的门牌列里 `0` 占比 >5%（`zero_share` 已写入逐层），`0` 是「无门牌号」占位，"
      "SCHEMA 要求保留原写法，但**入 gold 时应按无门牌号处理**")
    A("- 切分时 `street_name` 强制取**同一列**（同一行才对得上），不会出现「号来自 A 列、名来自 B 列」的错配")
    A("")
    A("## 四、state_abbr：为什么这次能到 91.6%")
    A("")
    sc = Counter(e.get("state_src") for e in L.values())
    A(f"- 源层有州列且示例合法：**{sc.get('column', 0)} 层**")
    A(f"- 源层没有州列，取**层元数据**（`collect/*_layers.csv` 的 `state`）：**{sc.get('layer_meta', 0)} 层**")
    A(f"- 两者都没有：**{sc.get(None, 0)} 层**（层标题不含州名，如 `Poland_Addresses_2_view`）")
    A("")
    A("理由：州是**分片作用域属性**，SCHEMA 2.0 自己也写了「县片内实测 100% 等于本州」，"
      "所以用层元数据补 state 不算伪造；v1 把「源层没有 state 列」判成 unusable 是口径错误。")
    A("")
    A("## 五、4 个三仓溯源字段（建议名与取值）")
    A("")
    A("二仓 19 个溯源列（`src_nad_uuid` / `src_oa_hash` / `src_tiger_tlid` / `src_overture_id` …）全部面向 "
      "NAD/TIGER/OA/Overture。三仓是 ArcGIS 点层与宗地层，这些 id 一个都没有 —— 不加这 4 列，地址无法回溯到原始层与原始宗地。")
    A("")
    A("| 建议字段名 | 类型 | 可空 | 取值规则 | 实测覆盖 |")
    A("|---|---|---|---|---|")
    for f in d["provenance_ext"]["fields"]:
        covtxt = f.get("覆盖") or json.dumps(f.get("实测分布"), ensure_ascii=False)
        A(f"| `{f['name']}` | {f['type']} | {'是' if f['nullable'] else '否'} | {f['取值规则']} | {covtxt} |")
    A("")
    A("`src_kind` 取值严格限定在既有枚举 `address_point|parcel_situs|street_line`：三仓本轮只有前两种，"
      "`street_line` 保留待用（不新造枚举值）。")
    A("")
    A("## 六、与 field-map v1 的差异（v1 已停用）")
    A("")
    A("| 项 | v1（`schema/field-map-v1.json`） | v2（本表） |")
    A("|---|---|---|")
    A("| 目标 schema | 自拟 canonical 14 字段 | **二仓 LOCKED SCHEMA 2.0 主字段** |")
    A("| state 来源 | 只认源列 | 源列 → 层元数据 |")
    A(f"| 可用层（门牌+街名+州 齐备） | 595 层 / 24.99% | **{cov['blocking_none']} 层 / "
      f"{100.0 * cov['blocking_none'] / n:.1f}%** |")
    A("| city 语义 | 单个 city | `postal_city` / `municipal_city` **分开**（不混用） |")
    A("| 溯源字段 | 塞进 canonical | 4 个专有溯源列单列提案 |")
    A("")
    A("## 七、账本更正：17 层被两个阶段重复记账")
    A("")
    A(f"`analysis/out` 有 {cov['profile_files']} 份画像，但去重后只有 **{n}** 个 `layer_id` —— "
      f"**{len(cov['duplicate_layer_ids'])} 层**在 `step04` 与 `step05` 各发过一次 Release，`rows_total` 完全相等。")
    A("")
    A(f"- 去重后声明行数 **{cov['rows_total_declared']:,}**")
    A(f"- `docs/INTAKE-YIELD-2026-10-30.md` 的 235,425,902 = {cov['rows_total_declared']:,} + "
      f"重复计入的 **6,343,196**（17 层 × 各自行数），**该文行数口径偏大 6.34M**，结论方向不变")
    A("- 本表按 `layer_id` 去重，只留一条（取抽样最多者），行数不重复计")
    A("")
    A("## 八、缺口清单（下一轮该补什么）")
    A("")
    for t, why in (("county_fips", "只有 8.3% 的行有 FIPS 列；其余需从县分片元数据/roster 注入"),
                   ("zip5", "59.4% 行级可达；其余需 ZCTA 回填（必须标 `zip_source=zcta_derived`）"),
                   ("municipal_city", "23.0%；绝大多数层只有 `CITY`（邮寄城市），v2 语义下不得复用 → 需 tiger places"),
                   ("unit", "5.7% 行级非空，与 SCHEMA 记的 Overture 4.4% 同量级，靠源数据补不动"),
                   ("latitude", "85.1%；缺的几乎全是**宗地层**（Polygon 无点坐标）→ 需几何质心"),
                   ("addr_type", "0%，无源列，需规则重分类（等你点头）")):
        A(f"- `{t}`：{why}")
    A("")
    A("## 八bis、state / county 回填（B 项）")
    A("")
    A("| 口径 | 层数 | 占比 | 说明 |")
    A("|---|---|---|---|")
    A(f"| v1 口径（house_number + street_name + **state 列**） | {cov['usable_v1_state_column_only']} | "
      f"{cov['usable_v1_pct']:.2f}% | 只认源列，所以大批「州只在层元数据里」的层被判不可用 |")
    A(f"| v2（state 按层清单回填后） | {cov['usable_v2_after_state_backfill']} | "
      f"{cov['usable_v2_pct']:.2f}% | 州是分片作用域属性，用层元数据补不算伪造 |")
    A(f"| v3（+ 县可判：层名单县 {cov['county_layer_level']} 层，或逐行 TIGER 多边形判得出） | "
      f"{cov['usable_v3_after_county']} | {cov['usable_v3_pct']:.2f}% | 掉下来的原因是宗地层缺坐标（{cov['county_multi_no_geo']} 层跨多县且无经纬度），需几何质心 |")
    A("")
    A("county 的两条路径：")
    A("")
    n_tiger = sum(1 for e in L.values() if e.get("county_src") == "tiger_layer_name")
    n_col = sum(1 for e in L.values() if e.get("county_src") == "column"
                and e.get("county_scope") == "single")
    A(f"- **层名单县**：{cov['county_layer_level']} 层（源列 {n_col} + 从层 id/url 反查 TIGER {n_tiger} 层）")
    A(f"- **层跨多县**：{cov['county_multi_row_pip']} 层 → county_fips 不能写死，必须逐行判定；其中 "
      f"{cov['county_multi_no_geo']} 层连坐标都没有，属 `geo_missing`")
    A("")
    A("**禁用 bbox 的实证**（`collect/county_tiger.py --selftest GA`，结果落 `analysis/tiger_county/selftest.json`）：")
    A("")
    A("| 检验 | 结果 |")
    A("|---|---|")
    A("| GA 县界顶点 31,386 个做对照 | 14,514 个（46.2%）会同时落进**邻县**的 bbox |")
    A("| GA 真实地址点抽样 2,000 个 | bbox 歧义（≥2 县）**2,000 条 = 100%**；多边形判定失败 **0 条** |")
    A("")
    A("所以 county 一律走射线法 point-in-polygon，bbox 只用来快速跳过候选，**绝不作为判定依据**。")
    A("")
    A("## 九、别名表里的坑（实测踩到，已写进代码注释）")
    A("")
    A("| 字段/列 | 坑 | 处理 |")
    A("|---|---|---|")
    A("| `CITY` | 语义族里最不确定：有的层是 USPS 城市，有的是市政城市 | 进 `postal_city` 但列为**待抽样核验项** |")
    A("| `OWNER_CITY` | 业主邮寄城市，实测值含 `MIAMI, FL 33142-2202` | **不进** `postal_city`（v1 混用过） |")
    A("| `MUNICIPALITY` | 实测含 `Unincorporated Area` | 只进 `municipal_city` |")
    A("| `UNITID` | E911 里常混状态码（`PKG`/`RPDSEC`） | 收，但 `quality=native_weak` |")
    A("| `POSTAL` | 有的层存 ZIP（`29406`），有的存城市名（`GASTONIA`） | ZIP 与 city 两张表都列，靠 5 位/字母校验器按层裁决 |")
    A("| `YEAR_BUILT` / `Ymin` / `LongLabel` / `Placement` | 前缀相似，v1 的正则前缀匹配会误命中 | 一律**全名匹配**，且经纬度要过 US 范围校验 |")
    A("| 门牌列 `0` | 占位值，实测 82 层 `0` 占比 >5% | 保留原值 + 写 `zero_share`，入 gold 当无门牌号 |")
    A("")
    A("## 十、复现")
    A("")
    A("```bash")
    A("python3 analysis/field_map_v2.py     # 生成/覆盖 schema/field-map-v2.json（先校验 SCHEMA 副本 sha256）")
    A("python3 analysis/field_map_v2_doc.py # 生成本文档")
    A("```")
    A("")
    A("逐层字段级取值见 `schema/field-map-v2.json` 的 `layers.<layer_id>`："
      "每个目标字段一项 `{src, nonempty_rate, transform?, quality?, reason?, value_rule?}`。")
    A("")
    open(DST, "w", encoding="utf-8").write("\n".join(out))
    print("wrote", DST, os.path.getsize(DST), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
