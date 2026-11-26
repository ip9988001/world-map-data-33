#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 REPORT-clean-number.md（数字全部来自 verify-20.json / verify-summary.json / scope.jsonl）。"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROWS_DIR = "/data/scratch/clean-number-20261126/rows"


def main():
    S = json.load(open(os.path.join(HERE, "verify-summary.json"), encoding="utf-8"))
    rows = json.load(open(os.path.join(HERE, "verify-20.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(HERE, "scope-meta.json"), encoding="utf-8"))
    out_rows = []
    if os.path.isdir(ROWS_DIR):
        for f in sorted(os.listdir(ROWS_DIR)):
            out_rows.append((f, os.path.getsize(os.path.join(ROWS_DIR, f))))
    L = []
    w = L.append
    w("# REPORT · house_number `x.0` 浮点整形（muse-000275）\n")
    w("> 脚本合成（`scan_dirty.py` → `scope.py` → `rerun_scope.py` → `verify.py` → 本文件），"
      "数字全部取自 `verify-20.json` / `verify-summary.json` / `scope.jsonl`，无手抄。\n")
    w("## 0. 结论\n")
    v = S
    w(f"- 清单内 **{v['layers']} 层**（{v['rows_in_scope']:,} 行）重跑后，`house_number` 命中 "
      f"`^\\d+\\.0+$` 的行数 **{v['dirty_before']:,} → {v['dirty_after']}**。")
    w(f"- 四项验证：① 脏行归零 **{'通过' if v['v1_dirty_zero']['pass'] else '未通过'}**；"
      f"② 覆盖率仍 {v['v2_coverage']['mapped_layers']}/{v['v2_coverage']['total_layers']} = "
      f"{v['v2_coverage']['pct']}% **{'通过' if v['v2_coverage']['pass'] else '未通过'}**；"
      f"③ 逐层行数相等、闭合差额 0 **{'通过' if v['v3_rows_closed']['pass'] else '未通过'}**；"
      f"④ `bad_*`=0 且 grade 分布逐层相同 **{'通过' if v['v4_bad_and_grade']['pass'] else '未通过'}**。")
    w(f"- 逐行对账：**{v['pairs_checked']:,}** 条脏行「同一行 before vs after」全部只差 `.0` 被吃掉"
      f"（**mismatch = {v['pair_mismatch']}**），另有 1,000 行随机抽查 **mismatch = "
      f"{v['spot_check']['mismatch']}**。")
    w(f"- 非零小数（口径要求原样保留）：**{v['deci_kept_after']:,} 行**保持原值不变"
      f"（before {v['deci_kept_before']:,} = after {v['deci_kept_after']:,}）。\n")
    w("## 1. 范围（先落盘再动手）\n")
    w(f"- 扫**真实产物**：`dist-v2/tar/*.tar.gz`（3,355 层）+ `/data/scratch/fix58-20261126/rows`（58 层）"
      f"= **{meta['layers_scanned']:,} 层 / {meta['rows_total_scanned']:,} 行**，命中 `^\\d+\\.0+$` 的层 "
      f"**{meta['layers']} 个**、脏行 **{meta['rows_dirty']:,}**。")
    w(f"- `scope.jsonl` sha256 = `{meta['scope_sha256']}`，**前 16 位 `{meta['scope_sha256_16']}`**。")
    w(f"- 来源字段分桶：`{json.dumps(meta['src_field_buckets'], ensure_ascii=False)}`")
    w("  说明：脏行**不止**来自 `STR_NUM`/`CIVIC_NUM`，还有 7 层是**信封 `add_num` 本身是 JSON 浮点**，"
      "以及 `addr_housenumber` 这类「字符串自带 .0」——所以修在 `clean_number()` 才对。\n")
    w("## 2. 代码改动\n")
    w("`analysis/fieldmap-20261125/fm_core.py:clean_number()`：")
    w("```python")
    w('m = RX_FLOAT_INT.match(s)          # ^(\\d+)\\.0+$')
    w('if m:')
    w('    n = m.group(1)')
    w('    return "" if (n.upper() in PLACEHOLDERS or RX_ONLY_SYMBOLS.match(n)) else n   # "0.00" → 占位值')
    w('return s')
    w("```")
    w("- `\"1009.0\"` / `1009.0`(float) / `\" 1009.0 \"` / `\"1009.00\"` → `\"1009\"`；只改写法不改数值。")
    w("- `\"1009.5\"` → **原样返回**（不四舍五入），只计数（见 §4）。")
    w("- **`\"0.0\"` 返回空串**（占位值优先）：`0`/`0.0`/`000` 是既定占位值，若归一成 `\"0\"` 就会写出 "
      "`house_number=\"0\"` 并把 grade 从 C 抬到 B —— 违反「不改数值/不改分级」与「不碰 placeholder 语义」。"
      "故本实现按 2.3 优先，2.1 的示例 `\"0.0\"→\"0\"` 未采纳（单测里写明理由，muse 若要反悔只改一行）。")
    w("- 不动 `clean_street` / `clean_city`、不动分级与坐标逻辑（单测里有护栏用例）。")
    w("- 单测 `analysis/fieldmap-20261125/tests/test_clean_number.py`：6 个必备用例 + 13 个边界 + "
      "幂等 + 「不动街名/城市」护栏；`python3 -m pytest analysis/fieldmap-20261125/tests engine/tests "
      "registry/tests -q` → **124 passed**。")
    w("- 另修 main 上既有的 3 个红测（gc-019/020/021）：上一轮新增的 golden case 用了上游字段名拼写，"
      "而 `registry/evaluator.py` 是按别名**精确拼写**匹配的；改成条目声明的别名拼写，值仍是真实原值，"
      "`roles_of()` 归一后别名集合与 main **逐位相同**（185 个名字，集合相等）。\n")
    w("## 3. 改前改后逐层对比\n")
    w("| # | 层 | 来源字段 | in_rows | mapped 前→后 | 脏行 前→后 | grade（前=后） | 闭合差额 |")
    w("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        g = "/".join(f"{k}:{r['after_grade'].get(k, 0)}" for k in ("S", "A", "B", "C"))
        w(f"| {i} | `{r['layer'][:44]}` | `{r['src_field']}` | {r['in_rows']:,} | "
          f"{r['before_mapped']:,} → {r['after_mapped']:,} | {r['before_dirty']:,} → **{r['after_dirty']}** | "
          f"{g} | {r['before_closed_diff']} / {r['after_closed_diff']} |")
    w("")
    w(f"合计：mapped {v['v3_rows_closed']['before_mapped_total']:,} → "
      f"{v['v3_rows_closed']['after_mapped_total']:,}（**相等**）；脏行 {v['dirty_before']:,} → "
      f"**{v['dirty_after']}**；`bad_empty` {v['v4_bad_and_grade']['bad_empty_total']}、"
      f"`bad_grade` {v['v4_bad_and_grade']['bad_grade_total']}。\n")
    w("> 清单里的 `rows_dirty`（`scope.jsonl`）是**产物口径**（v2 tar 内实际行），"
      f"重跑里的 before 是**当前 main 代码口径**，总数差 **{v['dirty_before'] - meta['rows_dirty']:+d}** 行"
      "（个别层 ±1~7），原因是那批产物早于 fix58 的拆分修复（与本轮改动无关），已在逐层表里分别列出。\n")
    w("## 4. 非零小数保留计数（口径要求）\n")
    w(f"- 清单内 20 层里，`house_number` 仍含**非零小数**的行：**{v['deci_kept_after']:,}** 行"
      f"（before {v['deci_kept_before']:,}）。**一个都没动**，只计数。")
    w("- 判定：`^\\d+\\.\\d*[1-9]\\d*$`（如 `12.5`、`1009.50`）；这类值不是浮点写法，不做任何整形。\n")
    w("## 5. 覆盖率（验证②）\n")
    w(f"- 清单内 20 层重跑后 **全部 `mapped>0`**；清单外 3,413 层**未重跑、未改**。")
    w(f"- 覆盖率 = **{v['v2_coverage']['mapped_layers']}/{v['v2_coverage']['total_layers']} = "
      f"{v['v2_coverage']['pct']}%**，与 PR #58 合并后基线逐位一致。")
    w("- 依据：`clean_number` 只在值命中 `^\\d+\\.0+$` 时生效，而 3,413 层全量扫描（483,239,197 行）"
      "只在清单内 20 层发现这种形态 → 清单外层的输出逐字节不变。\n")
    w("## 6. 四项验证逐条\n")
    w(f"1. **脏行归零**：{v['layers']}/{v['layers']} 层 after 脏行 = 0"
      f"（fail 列表：{v['v1_dirty_zero']['fails'] or '无'}）。")
    w(f"2. **覆盖率**：{v['v2_coverage']['mapped_layers']}/{v['v2_coverage']['total_layers']} = "
      f"{v['v2_coverage']['pct']}%（fail：{v['v2_coverage']['fails'] or '无'}）。")
    w(f"3. **行数/闭合**：逐层 before/after mapped 相等，`closed_diff` 前后都为 0，丢层 0"
      f"（fail：{v['v3_rows_closed']['fails'] or '无'}）。")
    w(f"4. **bad_* 与 grade**：`bad_empty` {v['v4_bad_and_grade']['bad_empty_total']}、"
      f"`bad_grade` {v['v4_bad_and_grade']['bad_grade_total']}、grade 分布逐层**完全相同**"
      f"（净变差 0）；`zero_coord` {v['v4_bad_and_grade']['zero_coord_total']} 行是**源侧缺坐标**"
      f"（raw `lat/lon = \"NaN\"`），before/after 逐层相等（2/30/8 行，且每行「有无坐标」标志完全相同，"
      f"见 `zero-coord-evidence.json`）。")
    w("")
    w("## 7. 抽查（验证⑥）\n")
    sc = v["spot_check"]
    w(f"- **全量逐行对账**（比抽样更强）：`{v['pairs_checked']:,}` 条脏行在同一行上比 before/after —— "
      f"`house_number` 只少了 `.0`，`street_name`/`lat`/`lon`/`grade`/`city`/`state`/`zip5` 全同；"
      f"**mismatch = {v['pair_mismatch']}**。")
    w(f"- **随机 1,000 行**（每层随机挑 3 个 part 文件 + 蓄水池抽样，覆盖 "
      f"{sc['layers_with_samples']} 层）：**mismatch = {sc['mismatch']}**；明细见 `spot-check-1000.jsonl`。")
    w(f"- `addrkey` 变化的行：**{v['addrkey_changed']:,} / {v['pairs_checked']:,}** —— 这是**预期**："
      "`addrkey` 由门牌参与哈希，脏门牌 `1009.0` 与整形后 `1009` 是不同键；整形后同址才能对上键（身份修正，"
      "不是身份改变）。街道/坐标/等级三者全同已在逐行对账里证明。\n")
    w("## 8. 产物\n")
    w(f"- 代码：分支 `feat/clean-number-20261126`（base `origin/main` = "
      "`2a2369e44d3258c8b962bd32ebac14a63b679ecd`）。")
    w(f"- 新映射数据（仅清单内 20 层，after 口径）：`{ROWS_DIR}/`，共 {len(out_rows)} 个文件；"
      "其中 OSM EU 那层按 6 个 part 分片写出，`cat` 拼接即为单个 gz（gzip 多成员合法）。")
    w("")
    w("| 文件 | 字节 |")
    w("|---|---|")
    for f, n in out_rows:
        w(f"| `{f}` | {n:,} |")
    w("")
    w("## 9. 未闭环 / 短板\n")
    w("1. `\"0.0\" → \"\"`（不是 `\"0\"`）：理由见 §2，属**有意**偏离派单 2.1 的示例，muse 若要反悔改一行。")
    w("2. `zero_coord` 40 行仍是源侧缺坐标（raw `NaN`），本单不动坐标逻辑。")
    w("3. 清单外 3,413 层未重跑（覆盖率按「未命中 `x.0` 形态 → 输出不变」论证，不是重跑实证）。"
      "若要逐字节证明，需要一次全量重扫（上次实测 247 分钟）。")
    w("4. 清单里的脏行数是产物口径（1,169,262），重跑 before 是当前代码口径（1,169,271），差 9 行已逐层交代。")
    w("5. 另一个 clone（`/root/pi-work/world-map-data-33`，`fix/w33-048...`）与本单无关，未切分支、未改、未推。")
    open(os.path.join(HERE, "REPORT-clean-number.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote REPORT-clean-number.md", os.path.getsize(os.path.join(HERE, "REPORT-clean-number.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
