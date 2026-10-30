# STEP 03 — 单州试跑 KS

> **判据卡 v2.1**　工头：`collect/supervisors/step_03.py`　工人：`.github/workflows/worker-03.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
一个州（KS）的所有地址点层整州跑一遍：验证批量、并发、打包、上传、续传在真实规模下不崩。

## 输入
`layer_plan.csv` 里 `state=KS` 且非 skip 的全部层

## 产出 / 证据（工头只递这些事实）
每层 Release 资产 + checkpoint；`unit_errors` / `short_units` 明细进报告

证据清单：`releases`、`checkpoint`、`unit_errors`、`short_units`

## 怎么做
- 按 host 限速：同一域名 2 并发，arcgis.com 放宽到 8
- 每层独立状态 done / empty / partial / failed，失败层必须有记录（不许静默丢）
- 先灰度 `gray_layers` 层，绿了再放全州

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `done_rate_min` | ≥ 0.85 | 层状态 done 占比下限 |
| `failed_rate_max` | ≤ 0.15 | failed 占比上限 |

## 失败怎么办
429 降并发；磁盘紧就先传后删；某层反复失败标 failed 跳过，不堵整州。

## 命令（照抄）
```bash
python3 collect/supervisor.py --review pass --next 04
python3 collect/supervisor.py --kick 03 --workers 4 --max-layers 20
```

## 卡死阈值
`stall_min = 240` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "03",
 "kind": "collect",
 "title": "单州试跑 KS",
 "select": {
  "state": "KS"
 },
 "workers": 4,
 "unit_rows": 200000,
 "unit_bytes": 1500000000,
 "tag": "collect-step03-{layer}",
 "gate": {
  "gray_layers": 20,
  "limit_mode": "spread"
 },
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "unit_errors",
  "short_units"
 ],
 "accept": {
  "done_rate_min": 0.85,
  "failed_rate_max": 0.15
 }
}
```
