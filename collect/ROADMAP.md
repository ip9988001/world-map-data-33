# ROADMAP — 三仓采集项目（自研模式 v2.1）

> **总目标**：把这个数据源里所有对我们有用的地址信息，完整搬回 Releases。
>
> **唯一的人工节点**：全部七步跑通并通过测试后，推一条企微：
> 「三仓采集项目全流程搭建完成，测试通过，可以全面开搞了」—— 然后停下等人来。

---

## 三个角色（职责边界写死在代码里，不许越界）

| 角色 | 是谁 | 能做什么 | 不能做什么 |
|---|---|---|---|
| **工人** | `collect/run_step_0X.py` + `.github/workflows/worker-0X.yml` | 采集、切单元、传 Release、写 checkpoint | 判验收、推进步号、推企微 |
| **工头** | `collect/supervisor.py` + `collect/supervisors/step_0X.py` | 看活 run、收证据、写 `wake/WAKE.json`、开 Issue **叫醒**大脑 | 比数字判验收、自动推进、写熔断、推企微 |
| **大脑** | 你 + 我（对话里） | 判验收、点火（`--kick`）、写结论（`--review`）、暂停/放开 | 手改数据、跳过判据 |

工头只叫醒，判定权 100% 在大脑。这是 v2 的第一红线，`--entry-check` 第 1/2/3 条就是查它（第 25 条查判据卡漂移）。

---

## 铁律（每步都适用）

1. **参数只有一个来源**：`collect/steps.json`。7 个工人入口读它、7 个工头读它、7 份判据卡是它的镜像。
   改参数只改这一处，改完跑 `python3 collect/check_docs.py` 校验文档没跑偏。
2. **小步快跑**：一次只推一步，判据过了才进下一步；判据由机器判，判不过就停。
3. **本步一停必须叫醒**（干完或干挂都算）：工头落 `collect/wake/WAKE.json` + 开 Issue，
   简报自带**说明书路径 / 判据卡 / 命令模板 / WAKE 绝对路径**四件套 —— 不用到处找文件。
4. **失败自己解决**：重试、换通道、改脚本、删数据自行决定，不请示；两次不解决就记 `blocked.json` 跳过。
5. **验收不通过 = 停住**：`--review fail` 会把账本置 `awaiting_go` 并关单，巡逻不再反复叫醒；
   要重跑必须大脑 `--kick`，点火自动作废上一轮关单。
6. **预算闸门**：Actions 分钟数有硬上限（`budget.minutes_cap`），到 `stop_ratio` 工头自动 `paused`，
   并在下一次简报里写明。7 个工头共用 1 个 cron（`collect-supervisor.yml --tick`），不许加 cron。
7. **通知通道分开**：工头 → Issue + `WAKE.json`；大脑 → 企微。工头代码里出现企微调用就是错（自检第 12 条）。
8. **每步必须推企微**：大脑判完立刻用 `/root/pi-work/sentinel-bot/send_once.mjs` 推一条，格式
   `【三仓项目】第N步 <名称>｜<结果数字>｜<合格/不合格>｜下一步：<步骤名>`。这条是用户判断「有没有在正常干」的唯一依据。

---

## 七个步骤

| # | 名称 | 目标 | 证据清单 | 判据卡 | 工头 | 工人 |
|---|---|---|---|---|---|---|
| 00 | 地基 | 引擎+工头+账本+自检+单测立起来 | selftest, unit_tests, state | `steps/STEP-00.md` | `supervisors/step_00.py` | `worker-00.yml` |
| 01 | 预检 | 6 万层逐个 count，产出 `layer_plan.csv` | layer_plan.csv, count_rate | `steps/STEP-01.md` | `supervisors/step_01.py` | `worker-01.yml` |
| 02 | 试点 8 层 | 三形态 × 三档规模跑通三条通道 | report, releases, checkpoint, short_units | `steps/STEP-02.md` | `supervisors/step_02.py` | `worker-02.yml` |
| 03 | 单州试跑 KS | 整州真实规模验批量/并发/续传 | releases, checkpoint, unit_errors, short_units | `steps/STEP-03.md` | `supervisors/step_03.py` | `worker-03.yml` |
| 04 | 全州放量 | `row_count>300000` 的大层全部搬回 | releases, checkpoint, unit_errors | `steps/STEP-04.md` | `supervisors/step_04.py` | `worker-04.yml` |
| 05 | 县市碎片 | 剩余两万层分批扫完，不留 pending | releases, checkpoint, blocked | `steps/STEP-05.md` | `supervisors/step_05.py` | `worker-05.yml` |
| 06 | 收工 | 汇总覆盖率总表（只出报告，不推企微） | FINAL_REPORT.md | `steps/STEP-06.md` | `supervisors/step_06.py` | `worker-06.yml` |

各步阈值（accept）唯一写在 `steps.json`，判据卡底部的机器块是镜像，不要手改。

---

## 账本

`collect/state.json` —— 唯一进度来源，只记事实，不记判断。

```json
{"current_step":"03","status":"running|awaiting_brain|awaiting_go|paused|finished",
 "awaiting_brain":false,
 "brain_review":{"at":"...","step":"02","verdict":"pass","note":"..."},
 "last_run":{"step":"02","run_id":null,"at":"...","trigger":"brain"},
 "budget":{"minutes_used":0,"minutes_cap":1800,"stop_ratio":0.95},
 "steps":{"02":{"status":"done","metrics":{}}},
 "wake":{"signature":"...","closed":{"verdict":"fail"}}}
```

- `awaiting_brain` —— 工头已经把球踢给大脑（已落 WAKE + 开 Issue）
- `brain_review` —— 大脑最近一次判定（pass / fail + 理由）
- `wake.closed` —— `--review fail` 后关单，同签名证据不再叫醒
- `blocked.json` —— 单独文件，两次不解决就记档跳过，不塞进账本

---

## 自检（随时可跑）

```bash
python3 collect/supervisor.py --entry-check    # 24 条结构红线
python3 collect/check_docs.py                  # steps.json ↔ 7 份判据卡逐字段比对
python3 -m pytest collect/tests -q             # 26 条单测
```
