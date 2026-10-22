# ROADMAP — 三仓采集项目（全自动执行）

> **总目标**：把这个数据源里所有对我们有用的地址信息，完整搬回 Releases。
>
> **授权**：本仓库一切动作（增删改、发 Release、删资产、改历史）由执行者自行决定，不问人。
>
> **唯一的人工节点**：全部流程跑通并通过测试后，推一条企微消息：
> 「三仓采集项目全流程搭建完成，测试通过，可以全面开搞了」—— 然后停下等人来。

---

## 铁律（每步都适用）

1. **小步快跑**：一次只推一步，通过验收才进下一步。
2. **不许大步乱跑**：验收判据是机器判的，判不过就停。
3. **本步一停就必须叫醒我**（不管是干完还是干挂了）—— 由 `scripts/herald.py` 负责，
   它必须自带地图：第几步、结果数字、是否达标、下一步是几步、下一步读哪个文件。
4. **失败自己解决**：重试、换方案、改脚本、删数据，全部自行决定，不请示。
5. **预算闸门**：Actions 分钟数有硬上限，接近上限时停止放量并在简报里写明。

---

## 六个步骤

| # | 步骤 | 目标 | 完成判据（机器判） |
|---|---|---|---|
| 00 | 地基 | ROADMAP + 每步纸 + herald + watchdog + 账本 | `state.json` 可读写；herald 自检能开/更新 Issue |
| 01 | 预检 | 6 万层逐个 count，剔除空层，读出采法参数 | `layer_plan.csv` 生成；每层带 `supportsPagination` / `definitionExpression` / 页大小 |
| 02 | 试点 8 层 | 三种形态 × 三档规模跑通 | 8 层全部落盘；对账误差 < 1%；`addr_key` 无缺失；Release 有资产 |
| 03 | 单州试跑 | 挑 KS（104 万点）整州跑通 | 该州所有非空层采完；打包上传即传即删；失败层有记录不是静默丢 |
| 04 | 全州级放量 | 一次覆盖整州的层（估 20~40 个） | 全部采完；累计行数对账通过；覆盖率可算 |
| 05 | 县市碎片放量 | 剩余全部图层 | 全部层状态为 done/empty/failed（无 pending）；失败率 < 15% |
| 06 | 收工 | 汇总 + 覆盖率 + 推企微 | 覆盖率表生成；企微消息发出；`state.json` 标记 `finished` |

---

## 每一步的纸在哪

- `collect/steps/STEP-00.md`
- `collect/steps/STEP-01.md`
- `collect/steps/STEP-02.md`
- `collect/steps/STEP-03.md`
- `collect/steps/STEP-04.md`
- `collect/steps/STEP-05.md`
- `collect/steps/STEP-06.md`

## 账本

`collect/state.json` —— 唯一进度来源。字段：
```json
{"current_step":"02","status":"running","last_run_id":null,
 "steps":{"00":{"status":"done","at":"...","metrics":{}}},
 "budget":{"minutes_used":0,"minutes_cap":1800},
 "last_triggered":{"step":"02","run_id":null}}
```
