# STEP 05 — 县市碎片

> **判据卡 v2.1**　工头：`collect/supervisors/step_05.py`　工人：`.github/workflows/worker-05.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
剩余两万多个县市碎片层，分批全自动扫完，不留 pending。

## 输入
`layer_plan.csv` 中除已完成外的全部层（`mode=bulk`）

## 产出 / 证据（工头只递这些事实）
全部层状态为 `done / empty / failed` 三选一，无 `pending`；`blocked.json` 记录跳过原因

证据清单：`releases`、`checkpoint`、`blocked`

## 怎么做
- 按批 `batch` 层一组推进，一批绿了再起下一批（`max_per_authorization` 控授权轮次）
- 单元 `unit_rows`（碎片层小，切小单元避免空转）
- 失败率实时统计，超阈值就停手叫醒大脑，不许硬顶

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `failed_rate_max` | ≤ 0.15 | failed 占比上限 |
| `pending_max` | ≤ 0 | 剩余 pending 层数上限 |

## 失败怎么办
403/超时重试 2 次；仍失败记 blocked 跳过；失败率超判据 → 停手写简报，等大脑定是换通道还是整体放弃。

## 命令（照抄）
```bash
python3 collect/supervisor.py --review pass --next 06
python3 collect/supervisor.py --kick 05 --workers 4 --offset 0 --size 100
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "05",
 "kind": "collect",
 "title": "县市碎片",
 "select": {
  "mode": "bulk",
  "batch": 100,
  "order": "rows_asc",
  "rows_min": 5000,
  "skip_blocked": true,
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "title_exclude": "fire|nfirs|response|parcel|zone|district|boundary|hydrant|business|poi|of interest|europe|canada|mexico|bus stop|shelter|parking|traffic|crash|collision|permit|school|hospital|station|cell ?tower|antenna|solar|weather|flood|watershed|trail|park\\b|bridge|billboard|licen|inspection|vacant|demolition",
  "rows_max": 500000,
  "state_exclude": [
   "未定位",
   ""
  ],
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 100000,
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
