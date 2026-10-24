# STEP 01 — 预检

> **判据卡 v2.1**　工头：`collect/supervisors/step_01.py`　工人：`.github/workflows/worker-01.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
给全量图层体检一遍，产出一张「每层该怎么搬」的施工图 `layer_plan.csv`，后续所有步骤都从它选层。

## 输入
`survey/ng911/`（普查结果）+ 数据源 API（只调 `count`，不取数据）

## 产出 / 证据（工头只递这些事实）
`collect/layer_plan.csv`（每层：state / layer_id / svc / url / row_count / geom / 采法参数 / skip 原因）

证据清单：`layer_plan.csv`、`count_rate`

## 怎么做
- 按 `shards` 切成 12 份，并行 count；同一域名限速 2 并发
- 空层标 `empty`、几何不支持标 `skip`、count 被拒标 `count_na`（不许猜数字）
- 几何白名单 `point / multipoint / socrata / na`；Polygon/Polyline 直接 skip（带不进地址字段）

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `plan_rows_min` | ≥ 50000 | layer_plan.csv 行数下限 |
| `plan_empty_max` | ≤ 0 | plan 里空值单元格上限 |
| `count_rate_min` | ≥ 0.78 | count 成功率下限 |

## 失败怎么办
429 降并发；count 失败重试 2 次后记 `count_na` 继续，不许卡在全量预检上；count 率低于判据就换第 3 条通道（ids 抽样）补。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 01
python3 collect/supervisor.py --review pass --next 02 --note "..."
```

## 卡死阈值
`stall_min = 180` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "01",
 "kind": "preflight",
 "title": "预检",
 "select": {
  "source": "survey"
 },
 "evidence": [
  "layer_plan.csv",
  "count_rate"
 ],
 "accept": {
  "plan_rows_min": 50000,
  "plan_empty_max": 0,
  "count_rate_min": 0.78
 }
}
```
