# STEP 04 — 全州放量

> **判据卡 v2.1**　工头：`collect/supervisors/step_04.py`　工人：`.github/workflows/worker-04.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
把覆盖整州的大层（`row_count > 300000`）全部搬回，这一步一次性拿到大部分人口。

## 输入
`layer_plan.csv` 里 `row_count > 300000` 的层

## 产出 / 证据（工头只递这些事实）
大层 Release 资产 + checkpoint；累计行数对账

证据清单：`releases`、`checkpoint`、`unit_errors`

## 怎么做
- 单元放大到 `unit_rows`（大层切大块，减少往返）
- 每单元完成即传即删；checkpoint 断点续传，run 挂了接着跑
- 覆盖率按「已采行数 / count 之和」实时算

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `total_rows_min` | ≥ 30000000 | 累计实收行数下限 |

## 失败怎么办
单层失败只影响该层，记 failed 继续；同一 host 反复 5xx 就降到 1 并发；额度接近上限时主动停并在简报写明。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 04 --workers 4
python3 collect/supervisor.py --review pass --next 05 --note "..."
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "04",
 "kind": "collect",
 "title": "全州放量",
 "select": {
  "where": "row_count>300000"
 },
 "workers": 4,
 "unit_rows": 1000000,
 "tag": "collect-step04-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "unit_errors"
 ],
 "accept": {
  "total_rows_min": 30000000
 }
}
```
