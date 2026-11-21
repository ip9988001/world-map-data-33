# 07b 收尾 · 2026-11-21（A 口径落盘 / B 138c05 子层 / C PARON 完整性 / D 05b 现状）

## A. 账本口径落盘（只改文档，账本数据一行未动）

**落点**：`collect/README.md` —— 该仓没有独立 LEDGER-SPEC 文件，`README.md` 是唯一讲「三道校验 / 空层 / 重复层」
等账本语义的说明文档，故把口径节插在「## 设计要点」与「## 跑法」之间。

**新增两条规则**（原文）：

1. 覆盖率一律按「有效覆盖」算 = `有行且非 hollow 的层数 ÷ 计划层数`；按 tag 数的「形式覆盖率」只作参考，**不得用于验收**。
2. **hollow（空洞层）**：形式存在（tag + Release 都在）、实质为空 —— 资产只有 checkpoint（几百字节）、`rows=0`、
   `declared>0`。标 `hollow=true` 并**同时保留在缺口清单里，缺口数字不因标 hollow 而变小**。
   已认定 `rcgis_rest_services_Addressing_Addressing_public_MapServer_0`（资产 652B / rows=0 / declared=3,821，
   第 4 个上游死层；首个为 04b 的 3 层）。

**commit**：`a5473ec`（已 push 到默认分支 main）
message：`ledger: 覆盖率口径改为有效覆盖；rcgis_Addressing_Addressing_public_MapServer_0 标 hollow`

**diff 摘要**：仅 `collect/README.md` 一个文件，插入了 `## 账本口径（覆盖率 / hollow）` 一节（8 行，两个 bullet 段），
无删除、无其它文件变更（`git show --stat a5473ec` → 1 file changed, 8 insertions(+)）。

> 未触碰：`collect/07b_ledger.json`（条目、buckets、plan 块全部原样）、未打 tag、未重派 05b、未重跑 138c05。

## B. 138c05 逐子层核（只读断言，未重采）

层：`138c05_rest_services_MiddlesexCounty_Base_Layers_MapServer_0`
端点：`https://utility.arcgis.com/usrsvcs/servers/f4dd79bdd35a456c87c0c20668138c05/rest/services/MiddlesexCounty/Base_Layers/MapServer/0`
（层 id 的 `/0` 指子层 0 = **Address (Units)**；其余 6 个子层不在本层采集范围）
force run `44865629100` 判 success，但 Release 未变：1 分片 / 122,195 B / **2,131 行** vs declared 2,298（缺 167，7.3%）。

| sublayer | 名称 | declared（计划） | 上游 count | 实际可取（分页取回） | 我方实采 | 差额 | 判因 |
|---|---|---|---|---|---|---|---|
| 0 | Address (Units) | 2,298 | 2,300 | **2,300**（2,000 + 300 两页全取回） | 2,131 | **169（7.3%）** | **b) 采集截断**：2,131 = 2,000 + 131，第一页满 2,000 后第二页只拿到 131 就收敛（keyset 游标提前判耗尽）；上游两页都能给全 2,300 行，不是上游少数据 |
| 1 | Address | 不在本层声明 | 34,334 | 34,334（returnIdsOnly=34,334） | 0 | — | c) 其它：层 id 指 `/0`，子层 1 不计入 2,298 声明，本层不采 |
| 2 | Roads | 不在本层声明 | 1,597 | 1,597 | 0 | — | c) 其它：同上，非地址层 + 不在本层范围 |
| 3 | Roads (Class) | 不在本层声明 | 119 | 119 | 0 | — | c) 其它：同上 |
| 4 | Non-Agricultural Areas | 不在本层声明 | 122 | 122 | 0 | — | c) 其它：同上（面层，非地址） |
| 5 | Municipal Boundary | 不在本层声明 | 10 | 10 | 0 | — | c) 其它：同上（面层，非地址） |
| 6 | Lots & Concessions | 不在本层声明 | 6,493 | 6,493 | 0 | — | c) 其它：同上（宗地层，非地址） |

**判因三分结论**：
- a) 上游声明虚高 —— **不成立**：declared 2,298 vs 上游 count 2,300（差 2 行，且方向相反，属计划期快照误差），不是虚高。
- b) 采集截断 —— **成立**（本层唯一真因）。
- c) 其它 —— 其余 6 个子层适用「不在本层采集范围」，不解释缺口。

**字段过滤排除**：子层 0 全量 2,300 行里 `FULLADDRES` 空值仅 **2 行**、`STREET_UNI` 空值 1 行 → 字段过滤最多解释 2 行，
解释不了 169 行。
**服务端上限排除**：`maxRecordCount=2000`，但配套 `resultOffset` 可分页取全 2,300；我方 2,131 行说明第二页只取了 131 行。

> 按要求未重采、未重跑该层；下一步要么改 keyset 收尾判据（第二页短但未空时继续拉一次），要么按 OID 区间兜底补齐 169 行。

## C. PARON 层资产完整性（只读）

层：`_pagis_org_arcgis_rest_services_PARON_Paron_Base_MapServer_0`
tag `collect-step07-_pagis_org_arcgis_rest_services_PARON_Paron_Base_MapServer_0`（created 2026-10-31T08:44:46Z，updated 08:54:11Z）
资产：`*-checkpoint.json`（596 B）+ `*-u00000.tar.gz`（289,730 B）—— 共 2 个，采集产物**只有 1 个包**。

checkpoint 原文（关键字段）：
```
unit_rows: {"0": 2304}      unit_rows_seen: {"0": 2304}      done_units: [0]
unit_uploaded: {"0": true}  unit_package: {"0": "...-u00000.tar.gz"}
unit_files: {"0": ["part-u00000-b00000.ndjson.gz","part-u00000-b00001.ndjson.gz","part-u00000-b00002.ndjson.gz"]}
unit_errors: {}
```
包内实测：3 个 `part-u00000-b0000{0,1,2}.ndjson.gz`，解压后 **2,304 行**（= `unit_rows_seen` = declared 2,304）。

**结论：不要补第 2/3 片。**
- `parts=3` 不是上游 3 个 service，也不是 3 个待传资产，而是**我方 batching 的 3 个 b 分片**，已打进同一个
  `u00000.tar.gz`（`unit_files` 明确列出 3 个 b 文件、`unit_package` 只指这一个包）。
- 层不支持分页，走 OID 区间切片（`layer_plan_clean.csv` 该行 `oidsplit`），单 OID 区间 = 单单元 `0`，`done_units=[0]` 已全完成。
- 那 1 个资产**就是完整合并结果**（3 个 b 分片齐全），行数 **2,304 / 2,304** 与 declared 完全对齐，`unit_errors` 空。
- 账本 `status=ok / parts=3` 与资产事实一致 —— 「Release 只有 1 个资产」是正常形态（1 单元 = 1 包），不是合并未落。

## D. 05b 现状（只查不改）

**run `44865991911`：in_progress**（2026-11-21T04:24:56Z 派，`chain=0`）。
plan 成功：**585 层 / 3 片（size=200）/ 声明 32,337,294 行**；
shard (0)(1)(2) **全部 in_progress**（04:27:03Z 起跑），**0 片失败、0 片取消**；
累计产出行数暂不可得（片账本每片跑完才推 git，当前三片都没结束）。
