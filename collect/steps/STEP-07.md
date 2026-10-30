# STEP 07 — 碎片补齐

> **判据卡 v2.1（新增环节）**　工头：`collect/supervisors/step_07.py`　工人：`.github/workflows/worker-07.yml`
> 参数唯一来源 `collect/steps.json`；本文件底部机器块是它的镜像，改参数只改 steps.json。

## 目标
把 05 因为行数门槛（<5000 行）排掉的小层补回来 —— 这是完整性，不是放宽口径。

## 输入
`layer_plan.csv` 里 1~4999 行、标题含地址词、未被 02~05 采过的层

## 产出 / 证据
`collect-step07-<layer>` Release（part + checkpoint）；报告进 pilot_report.json

证据清单：`report`、`releases`、`checkpoint`

## 怎么做
- 小层切 10 万行单元，单层基本 1~2 个单元就跑完
- `skip_blocked` 自动跳过 blocked.json 里的层
- 按行数升序：先把最便宜的采完，预算耗尽时损失最小

## 验收判据（机器判；判定权在大脑）
| 指标 | 阈值 |
|---|---|
| `failed_rate_max` | ≤ 0.2 |
| `layers_min` | ≥ 250 |
| `layers_max` | ≤ 1500 |

## 失败怎么办
上游 4xx/5xx 重试 2 次即放弃并记 unit_errors，不堵批次；失败率超 0.2 停手叫人。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 07
python3 collect/supervisor.py --review pass --next 08
python3 collect/supervisor.py --kick 07 --workers 4 --offset 0 --size 120
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告，不判死。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "07",
 "kind": "collect",
 "title": "碎片补齐",
 "select": {
  "mode": "bulk",
  "batch": 120,
  "order": "rows_asc",
  "rows_min": 1,
  "rows_max": 4999,
  "skip_blocked": true,
  "state_exclude": [
   "未定位",
   ""
  ],
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 100000,
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
