# STEP 06 — 收工

> **判据卡 v2.1**　工头：`collect/supervisors/step_06.py`　工人：`.github/workflows/worker-06.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
汇总全部 checkpoint，出覆盖率总表，收工。只出报告，企微由大脑发（工头不碰企微）。

## 输入
全部 Release 里的 `*-checkpoint.json` + `layer_plan.csv`

## 产出 / 证据（工头只递这些事实）
`collect/reports/FINAL_REPORT.md`（覆盖率、分层明细、失败清单、缺口清单）

证据清单：`FINAL_REPORT.md`

## 怎么做
- 逐 checkpoint 累加实收行数，与 count 对账
- 覆盖率 = 实收 / 计划；失败率、空层率、跳过量分列
- 结果只落文件 + 账本，不推任何外部消息

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|

## 失败怎么办
checkpoint 缺失就按 Release 资产重算；资产也缺就标 `unknown` 并列出层名，不许用估算数字凑覆盖率。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 06
python3 collect/supervisor.py --review pass --note "..."
python3 collect/supervisor.py --review pass --note "收工"
```

## 卡死阈值
`stall_min = 120` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "06",
 "kind": "report",
 "title": "收工",
 "evidence": [
  "FINAL_REPORT.md"
 ]
}
```
