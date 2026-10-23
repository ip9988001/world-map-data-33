# 自研模式（Self-Drive Mode）

> **定义**：把我自己当成一个不需要人盯的研发员 —— 拿到总目标，自己拆步骤、自己写脚本、
> 自己跑、自己判验收、自己接着往下做，直到整个项目跑通。

## 一句话

**工人只管干，工头只管看；工人一停手（不管干完还是干砸），工头递上下一步的活；
同一个活连砸三次，工头收摊，不再喊人。**

---

## 进入条件（12 条，全绿才算进得去）

| # | 条件 | 判据 |
|---|---|---|
| 1 | 总图存在 | `collect/ROADMAP.md` 有总目标 + 每步验收判据 |
| 2 | 每步有说明书 | `collect/steps/STEP-00..06.md` 齐全 |
| 3 | 账本可读写 | `collect/state.json` 含 fail_streak / collapsed / attempts / budget |
| 4 | **工人与工头分离** | 采集 workflow 里**不含**任何报警步骤；工头是独立 workflow |
| 5 | 工头能发现"该动没动" | supervisor 查「当前步有没有活着的 run」，没有就宣判 |
| 6 | 工头能发现"卡死" | 单个 run 超过 120 分钟仍在跑 → 判卡死 |
| 7 | 简报自包含 | Issue 正文含：步骤、数字、尝试次数、上次错误、下一步读哪个文件、触发命令、当前 commit |
| 8 | 三振出局 | 同一步连续失败 3 次 → `collapsed=true`，不再巡逻、不再叫人、不重试 |
| 9 | 防重复点火 | supervisor 用 concurrency 锁 + 账本 `last_triggered` 时间窗 |
| 10 | 额度闸门 | 账本记 `minutes_used`，超 80% 减速、超 95% 停止放量 |
| 11 | 改动自检 | 脚本改动先跑 smoke（单层 3 条记录），过了才允许放量 |
| 12 | 自检可验证 | `supervisor.py --dry-run` 输出 READY/BLOCKED 清单，不改任何东西 |

---

## 退出条件（三种）

1. **正常完成**：STEP 06 跑完 → 推企微「可以全面开搞了」→ `status=finished`，等人
2. **三振出局**：同一步连败 3 次 → `collapsed=true`，静默停止
3. **额度耗尽**：`minutes_used ≥ 95% cap` → `status=paused`，静默停止

---

## 角色分工

| 角色 | 文件 | 职责 | 寿命 |
|---|---|---|---|
| 工人 | `.github/workflows/collect-*.yml` | 只干活，不报警 | 干完即死 |
| 工头 | `.github/workflows/collect-supervisor.yml` + `scripts/supervisor.py` | 每 10 分钟巡逻：判验收 / 记账 / 叫人 / 递下一步 | 常驻 |

## 谁叫醒我

工头开 Issue（label=`sentinel-alarm`）→ 本机 `inbox.py` 每 2 分钟轮询（**已接双仓**）→ 唤醒我。
我醒来只做三件事：看结果 → 推企微（哨兵机器人 3fe13dd9，标题带【三仓项目】）→ 发下一个活。
