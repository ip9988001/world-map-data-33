# STEP 07b — 碎片补齐（全量补采）

> **判据卡 v2.1（补采变体）**　工头：`collect/supervisors/step_07b.py`　工人：`.github/workflows/collect-full.yml`（stage=07b）
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**。

## 目标
07 补的是 05 因行数门槛（<5,000 行）排掉的小层，一批 120 层，历史留了 667 层 pending。
07b 一次补完：`1 ~ 4,999` 行的小层 + 软词地址层全部落账。**这是完整性，不是放宽口径。**

| 差异点 | 07 | 07b |
|---|---|---|
| 选层层数 | `batch=120` | `batch=4000`（一次选满） |
| 执行方式 | 一层一个 matrix job | 分片：**一片一个 job，片内顺序跑 670 层**（小层多，片要更大） |
| 已采层 | 重采 | `skip_done=true` 剔除 |

## 输入
`layer_plan.csv` 里 `row_count` 在 1~4,999、标题含地址词、未被 02~07 采过的层，
减去 `done_from = 07` 判为已完成的层。

## 产出 / 证据
`collect/ledger/07b_plan.json` → `collect/ledger/step07b_shard<N>.json` → `collect/step07b_ledger.json`
→ `collect-step07-<layer>` Release 资产

证据清单：`report`、`releases`、`checkpoint`

## 怎么做
- 切 670 层/片；片数上限 250
- 单层切 10 万行单元，绝大多数层 1 个单元就跑完（小层不要切成碎渣）
- 按 `rows_asc`：先采最便宜的
- 每层四态落账；失败层带原因；实采与声明差 > 0.2% 记 `partial`

## 验收判据（机器判；**判定权在大脑**）
| 指标 | 阈值 |
|---|---|
| `failed_rate_max` | ≤ 0.2 |
| `layers_min` | ≥ 250 |
| `layers_max` | ≤ 1500 |

## 失败怎么办
重试 2 次即放弃并记 `unit_errors`；失败率超 0.2 停手叫人，不自动接续。
「声明 1 行、实采 0 行」这类层记 `empty`（不是失败）—— 小层的声明数字本来就常是估的。

## 命令（照抄）
```bash
python3 collect/full_plan.py --stage 07b --size 670 --out collect/ledger/07b_plan.json
python3 collect/full_shard.py --stage 07b --shard 0 --plan collect/ledger/07b_plan.json --workers 4
python3 collect/step_full_report.py --stage step07b
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告，**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "07b",
 "kind": "collect",
 "title": "碎片补齐（全量补采）",
 "select": {
  "mode": "bulk",
  "batch": 4000,
  "order": "rows_asc",
  "rows_min": 1,
  "rows_max": 4999,
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "skip_done": true,
  "offset": 0
 },
 "workers": 4,
 "unit_rows": 100000,
 "unit_bytes": 1500000000,
 "tag": "collect-step07-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint"
 ],
 "accept": {
  "failed_rate_max": 0.2,
  "layers_min": 250,
  "layers_max": 1500
 }
}
```
