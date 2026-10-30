# 阶段账本合并护栏 —— 「取更优者」不许掩盖真退化（2026-10-31）

一句话：**保进展靠取优者，`rows` 变小必须点名。**

## 1. 这条护栏补的是什么坑

`collect/ledger_merge.py` 的合并规则是「状态取更优者（ok > partial > missing >
unverified > empty > failed），同状态取行数大者」。这条规则护住了「跑挂不能把已 ok 的层降级」
（NAD-view 那层的形态），但它的副作用是**真丢数据会被永久掩盖**：

- 同状态、行数变少 → 合并保留旧的大值，账本从此看不出这轮少采了 N 行；
- 状态变好、行数变少（唯一真会冲小 rows 的路径，如 `partial 39.8M → ok 5M`）→
  合并**直接取本轮记录**，rows 真的变小，但没有一处单独记「这是一次回退」。

没有这条护栏，将来真丢数据会被账本藏起来，只剩「阶段账本 rows 总数莫名少了几千万」。

## 2. 落点（代码）

| 位置 | 行为 |
|---|---|
| `ledger_merge.row_regressions()` | 合并前逐层比 `rows`：`run rows < stage rows` 就产出一条记录（层 / 旧 rows / 新 rows / delta / 旧状态→新状态 / 合并怎么处置 / 原因 / 证据路径） |
| `ledger_merge.merge_stage_ledger()` | 把本轮回退并进阶段账本 `regressions[]`（**只追加不替换**，同一 `(层, run_id)` 重跑只留最新一条）；同时写 `rows_regressions` / `rows_regressions_unexplained` 两个计数，并在 `revisions[-1]` 留 `rows_regressions` + 层清单 |
| `ledger_merge.write_run_and_stage()` | 把**本轮新增的**回退一起回传给调用方（`res["regressions"]`），别只躺在账本里 |
| `step_full_report.py` | 收官文档新增「七、rows 回退（本次合并检测到，未静默取大）」一节 + stdout `::warning::` |

三种处置（`merge_outcome`）分得很清楚，读的人是知道「账本现在是什么状态」的：

- `kept_stage_record_more_rows` — 同状态，保留旧的大值（账本 rows **没变**，是这轮少采了）；
- `took_run_record_status_better` — 状态更好，取了本轮记录（**账本 rows 真的变小了**）；
- `kept_stage_record_status_better` — 状态更差，保留旧记录（`downgrade_blocked` 同时也会记一条）。

## 3. 怎么给证据（否则按事故追）

回退**不拦截**（拦截会把「一轮 cancel」变成阶段永久卡死），但必须给证据：

```json
// collect/ledger/<stage>_run<RUN_ID>.json
{"row_shrink_evidence": {"<layer_id>": "analysis/<某项上游比对>.json"}}
```

逐层记录里也可以直接写 `evidence` / `regression_evidence` / `reason`（`regression_reason`、
`shrink_reason`），逐层字段优先于 run 账本的表。没有证据 → `rows_regressions_unexplained`
计数 + 文档里「证据」列写 **缺**。

## 4. 单测

`collect/tests/test_ledger_merge.py::RowsRegressionNotSilent`（9 条，全量 208 OK）：

1. 同状态少行 → 合并保留大值，但 `regressions[]` 有一条；
2. `partial 39.8M → ok 5M` → 合并结果真的变小，同时点名（`took_run_record_status_better`）；
3. 状态更差 + 少行 → 也记（与 `downgrade_blocked` 并存）；
4. 行数持平/变大 → 不误报；
5. 新层 → 不算回退；
6. `regressions[]` 只追加、`(层, run_id)` 去重、第二条 run 再退化追加第二条；
7. 证据/原因透传（逐层字段 + `row_shrink_evidence` 表）；
8. 人读摘要节含层 / 旧新 rows / 差额 / **缺** 证据标记；
9. `write_run_and_stage` 真落盘：阶段账本 `regressions[]` 有、`records[].rows` 仍取大值。
