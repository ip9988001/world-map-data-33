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
