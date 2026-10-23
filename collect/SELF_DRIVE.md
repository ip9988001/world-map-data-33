# 自研模式（Self-Drive）— v2 摘要

> **当前有效版本：v2**（2026-10-24 落地）。完整施工图在 [`SELF-DRIVE-v2.md`](SELF-DRIVE-v2.md)。
> 本文只是随身速查卡，与本文件冲突时以 `SELF-DRIVE-v2.md` 为准。

## 一句话

**工人只干活，工头只叫醒，大脑才判验收。**
工人一停手（干完或干砸都一样），工头把**证据**打包好叫醒大脑；
判通过、判不通过、要不要补跑、要不要跳过 —— 全是大脑的决定，脚本不碰。

## 三个角色的边界（越界即事故）

| 角色 | 谁 | 只准做的事 | 绝对不准 |
|---|---|---|---|
| 工人 | `.github/workflows/collect-*.yml` + `run_step_0X.py` | 采集、落证据、传 Release、写 `_manifest.json` | 判合格 / 报警 / 推企微 / 决定跳层 |
| 工头 | `collect/supervisor.py`（GitHub cron `*/10`）+ `ops/patrol_kick.sh`（本机 cron `*/15`） | ① 看有没有活 run ② 没活 run 就写 `collect/wake/WAKE.json` + 开 Issue 叫醒 ③ 记事实账 | 比数字判验收 / 推进 `current_step` / 自己点火下一步 / 写 `fail_streak` `collapsed` / 推企微 |
| 大脑 | 我 | 判验收、下令点火、写 `brain_review`、记 `blocked.json`、向老板汇报 | 让脚本代替判断 |

## 工头的四个口令（只有大脑能用）

```bash
python3 collect/supervisor.py --once          # 巡逻一轮（CI 用；只叫醒，不判）
python3 collect/supervisor.py --dry-run       # 只看证据，一个字节都不写
python3 collect/supervisor.py --entry-check   # 18 条结构自检，READY/BLOCKED
python3 collect/supervisor.py --kick 02 --layers de_suss,san_juan --workers 8   # 点火
python3 collect/supervisor.py --review pass --note "..." --next 03              # 写验收
python3 collect/supervisor.py --pause "原因" / --resume                          # 暂停/放开
```

## 失败分型：两次不解决就记档跳过

| 第几次 | 动作 |
|---|---|
| 第 1 次 | 改脚本重跑 |
| 第 2 次 | 先把原始证据（HTTP 码 / `error.message` / `count vs rows`）写进 `collect/blocked.json`，**再**改 |
| 第 3 次 | **禁止再改**。该层/该步标 `blocked`，带着缺口往下走，结尾在报告里列清楚 |

v1 的「三振出局 → collapsed 收摊」**已废止**：收摊是决定，账本只记事实。

## 通知通道（不许混）

| 通道 | 用途 | 谁发 | 到哪 |
|---|---|---|---|
| 内部唤醒 | 叫醒大脑 | 工头 | Issue（label `sentinel-alarm`）→ 本机 `inbox.py` 轮询 → 唤醒 |
| 企微汇报 | 向老板报进度 | **大脑** | 企微，只在「一步跑完 / 需要决策」时发 |

**工头不碰企微。老板收到的每一条都应该是大脑在说话。**

## 硬规则（今天踩出来的）

1. 禁止 `|| true` 静默吞错（`git push || true` 让报告消失、工头读旧账误判）
2. 禁止让脚本判「合格/不合格」
3. 禁止用单一数字判空壳（`<2KB` ≠ 坏）
4. 禁止用会混邻州的 `count` 判「有没有数据」
5. 任何 `git push` 都要 fetch+rebase+retry，失败显式 `exit 1`
6. 一次改多处必须先用 1~2 个单元灰度，再放量
7. 跳过/收摊必须留 `blocked.json` 证据，否则等于假装没发生过
8. 浅克隆（`fetch-depth: 1`）里 `git rebase` 无法重放 → report job 必须 `fetch-depth: 0`

## 断点续传（v2.1 · 2026-10-24）

**粒度 = 单元（默认 50 万行）**，单元一完成就打包上传，不等整个 job 跑完。

| 环节 | 做法 |
|---|---|
| 切分 | keyset 层按 OID 区间切成 N 个单元；无分页服务（`Pagination is not supported`）按 `returnIdsOnly` 的 batch 分组切单元。切分必须**确定**，否则续不上 |
| 发布 | 每个单元完成 → `tar` → `gh release upload <tag> <layer>-uNNNNN.tar.gz --clobber` |
| 检查点 | `collect/out/<layer>/_checkpoint.json` 记 `plan_hash / done_units / unit_rows / unit_uploaded`，**同时作为资产传到同一个 tag** |
| 跨 run 恢复 | 新 run 起来先看本地有无检查点 → 没有就 `gh release download <layer>-checkpoint.json` 捞回来；`plan_hash` 不符则作废（绝不硬续） |
| 幂等 | 单元文件名固定 `part-u{单元号}-{序号}`，tar 名固定 `<layer>-u{单元号}`，重跑用 `--clobber` 覆盖，不会重复堆资产 |
| 已传即删 | 上传成功立刻删本地 part，省 runner 磁盘（STEP03 放量必须） |
| tag 固定不带 run_number | `collect-pilot-<layer>`，这样换一次 run 还能接上 |

验证方式（mock，不起 workflow）：模拟第 3 个单元崩掉 → 断言检查点只记了已完成的单元 → 重启后跳过已完成单元继续 →
最终**总行数 == count、FID 无重无缺**。keyset / ids 两条通道都通过。

想看进度不用等：`collect/progress/<layer>.json` 每 20 秒刷新、每 3 分钟推仓库。

## 命脉监控

pi 跑在 DS 的 key 上，余额耗尽 = 直接失能。所以余额检查**由本机 cron 做**（`ops/ds_balance.py`，每 30 分钟），
不能靠我自己查。低于 ¥5 → 企微连推 3 次 → 充值后自动复位。
