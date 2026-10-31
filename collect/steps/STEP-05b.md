# STEP 05b — 县市碎片（全量补采）

> **判据卡 v2.1（补采变体）**　工头：`collect/supervisors/step_05b.py`　工人：`.github/workflows/collect-full.yml`（stage=05b）
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**。

## 目标
05 是「县市碎片」的批量扫层（一批 100 层），跑完还剩 2,753 层 pending。
05b 把它一次扫完：`5,000 ~ 300,000` 行的层全部落账，**不留 pending**。

| 差异点 | 05 | 05b |
|---|---|---|
| 一次授权采几批 | `roll.max_per_authorization = 5` | 不分批：分片器自己滚到底 |
| 选层层数 | `batch=100`（一批一批来） | `batch=4000`（一次选满，片内顺序跑） |
| 执行方式 | 一层一个 matrix job | 分片：**一片一个 job，片内顺序跑 200 层** |
| 已采层 | 重采 | `skip_done=true` 剔除 |

## 输入
`layer_plan.csv` 里 5,000 ≤ `row_count` ≤ 300,000、标题含地址词、未被 02~05 采过的层，
减去 `done_from = 05` 判为已完成的层。

## 产出 / 证据
`collect/ledger/05b_plan.json` → `collect/ledger/step05b_shard<N>.json` → `collect/step05b_ledger.json`
→ `collect-step05-<layer>` Release 资产

证据清单：`report`、`releases`、`checkpoint`、`blocked`

## 怎么做
- 切 200 层/片（这一档层小、快，片大才不浪费 job 启动开销）；片数上限 250
- 顺序按 `rows_asc`：先把最便宜的采完，预算耗尽时损失最小
- `skip_blocked` 自动跳过 blocked.json 里的层（这层是结构性坏源，重跑没意义）
- 每层四态落账；失败层带原因；实采与声明差 > 0.2% 记 `partial` 并在收官文档解释

## 派单参数（默认值不许随手改）

| 参数 | 默认 | 为什么 |
|---|---|---|
| `layer_timeout` | **60 分钟** | 挂死一层最多吃掉 60 分钟，剩余预算还能跑别的层。**调大必须给理由，并写进派单回执**：180 分钟 × 1 个挂死层 = 吃掉一半 job 预算（片上限 350 分钟），run `41123309047` 就是这样让 4 片（3/8/11/13）全部跑满 ~5h50m 被 `cancelled`（片账本原文 `job 内单层超时 3h`）—— 见 W33-023（复发×1）。大层要多跑就**分轮续跑**（checkpoint 在，下一轮接着跑），不是把单层上限往上抬 |
| `size` | 按拟合推（见下） | `t(分钟) ≈ 0.15 + 7.92 × 行数(百万)`，拟合自 05b 上一轮 1977 条层记录；按 `rows_asc` 的**末片**（最重）估，单片目标 ≤ 120 分钟、留出「一次 60 分钟超时」的余量 |
| `max_shards` | `0`（全起） | 非 0 会截断尾片：`plan_truncate.py` 必打 `::warning::` 并点名被砍的分片与每一层（W33-036），但**被砍 = 本轮注定没跑** |
| `chain` | `0` | 单跳不级联；07b 的 `NEXT` 为空（2026-10-31 停车线：到 07b 就停，08/10b/几何要口号） |

实测标定（2026-10-31）：`size=50` → 21 片，单片**纯工时**最大 67 分钟、片墙钟最大 215 分钟（3 层各吃满 60 分钟超时）；`size=200 + layer_timeout=180` → 4 片撞 350 分钟全 cancelled。

## 验收判据（机器判；**判定权在大脑**）
| 指标 | 阈值 |
|---|---|
| `failed_rate_max` | ≤ 0.15 |
| `layers_min` | ≥ 80 |
| `layers_max` | ≤ 100 |

> 注：`layers_min/layers_max` 沿用基础步 05 的**单批**口径（一批 100 层）。
> 05b 是整段扫完，实际覆盖层数会远大于 100 —— 判据以账本实测为准，不拿旧区间卡死。

## 失败怎么办
上游 4xx/5xx 重试 2 次即放弃并记 `unit_errors`，不堵批次；失败率超 0.15 停手叫人，
不自动接续下一阶段。

## 命令（照抄）
```bash
python3 collect/full_plan.py --stage 05b --size 200 --out collect/ledger/05b_plan.json
python3 collect/full_shard.py --stage 05b --shard 0 --plan collect/ledger/05b_plan.json --workers 4
python3 collect/step_full_report.py --stage step05b
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告，**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "05b",
 "kind": "collect",
 "title": "县市碎片（全量补采）",
 "select": {
  "mode": "bulk",
  "batch": 4000,
  "order": "rows_asc",
  "rows_min": 5000,
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "rows_max": 300000,
  "skip_done": true,
  "offset": 0
 },
 "workers": 4,
 "unit_rows": 100000,
 "unit_bytes": 1500000000,
 "tag": "collect-step05-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "blocked"
 ],
 "accept": {
  "failed_rate_max": 0.15,
  "layers_min": 80,
  "layers_max": 100
 }
}
```
