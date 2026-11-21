# 05b 缺口清单（重算版 v2 · 六类互斥）

## 口径（写死）

- **declared 不可得**：run 计划 artifact `plan-05b`（id 14692340122）里没有 `expect_by_layer`，逐层 declared 一律 `null`，**不用总量或筛查产物倒推**。
- **分母 = expect_live**（`returnCountOnly@plan` 探针；重探 alive 回填的标 `retry*-alive`）。
- **缺口 = expect_live − rows**；**未采层按 expect_live 全额计入**，`rows` 记 `null` 不记 `0`。
- GAP_TOL = 0.001（ok/partial 分界，未改动）。
- 六类互斥，条数合计 = `layers_n`。

## declared 两个总数并存（不合并、不抵消）

| 来源文件 | declared_rows | layers_n | sha256 | 生成时间 |
|---|---|---|---|---|
| `collect/ledger/05b_plan.json` | 32337294 | 585 | `d5ff5467b7c1127b` | 2026-11-21T05:11:00Z |
| `collect/ledger/step05b_plan.json` | 32303033 | 583 | `361fc29e4c828c3c` | 2026-11-21T07:19:04Z |

两者相差 34261 行（口径不同：run 计划 585 层 vs 探针计划 583 层 —— skip_done 刷掉 2 层）。**不猜哪份对，也不许把任一数当逐层 declared 用。**

## 六类汇总

| 类 | 层数 | expect_live 合计 | rows 合计 | 缺口合计 | 其中 rows=null |
|---|---|---|---|---|---|
| ok | 1 | 25,367 | 25,367 | 0 | 0 |
| partial | 6 | 227,787 | 58,542 | 169,245 | 0 |
| missing | 523 | 27,255,525 | 0 | 27,255,525 | 523 |
| unverified | 18 | 0 | 0 | 0 | 18 |
| pending | 35 | 0 | 145,788 | 0 | 32 |
| no_expect | 0 | 0 | 0 | 0 | 0 |
| **合计** | **583** | **27,508,679** | **229,697** | **27,424,770** | |

## 三个总数字（自洽）

- expect_live_total = **27,508,679**
- rows_total = **229,697**
- gap_total = **27,424,770**（= expect_live_total 27,508,679 − 有分母层的 rows 83,909；expect_live_total(27508679) - rows_with_expect(83909) = 27424770 = gap_total(27424770) → 自洽）
- 另有 145,788 行来自「无分母」层，已计入 rows_total 但不参与缺口恒等式（rows_total 含 145788 行属于「无分母(no_expect)」层，不参与缺口恒等式）
- 已采层缺口 = **169,245**（rows 有值的层）
- 未采层待采量 = **27,255,525**（rows=null 的层按 expect_live 全额）

> 旧版「总缺口 1,280,025」只算了已采层的缺口，未采层的待采量没算 —— 已废弃。
