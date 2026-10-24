# STEP 00 — 地基

> **判据卡 v2.1**　工头：`collect/supervisors/step_00.py`　工人：`.github/workflows/worker-00.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
把「引擎 + 工头 + 账本 + 自检 + 单测」立起来：后面六步全跑在这套骨架上，骨架不自洽就不许往下走。

## 输入
无（这一步不碰网络、不碰数据源）

## 产出 / 证据（工头只递这些事实）
`collect/supervisor.py`（工头，24 条结构自检）、`collect/worker_core.py`（引擎）、`collect/state.json`（账本）、`collect/tests/`（26 条单测）

证据清单：`selftest`、`unit_tests`、`state`

## 怎么做
- 本步无采集动作。`--entry-check` 逐条核对 v2.1 红线（工头不判验收 / 不自动推进 / 不写熔断 / 简报四件套 / fail 闭环 / steps.json 单源）
- `python3 -m pytest collect/tests -q` 覆盖选层、单元切分、schema 映射、checkpoint 合并
- 账本必须可读写；`awaiting_brain` / `brain_review` / `last_run` / `budget` 四个 v2 字段必须在

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|

## 失败怎么办
自检红哪条就修哪条；单测红了先看 worker_core 的契约有没有被改坏，不许改测试迁就代码。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 00
python3 collect/supervisor.py --review pass --next 01 --note "..."
python3 collect/supervisor.py --entry-check
```

## 卡死阈值
`stall_min = 120` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "00",
 "kind": "bootstrap",
 "title": "地基",
 "evidence": [
  "selftest",
  "unit_tests",
  "state"
 ]
}
```
