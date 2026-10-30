# Egress 限额 · 现状实测与硬判据（2026-10-30）

> 目的：把「GitHub 账号 Egress 限额」这条风险从口头担心，变成**可复测的实测数字 + 写死的取舍规则**。
> 只读/只测，不动采集口径，不改账本。

## 零、一句话结论

**当前 egress 未受压**：2026-10-30 21:00–21:11 UTC 实测连续下载 2.0 GB（68 个 Release 资产）
全程 HTTP 200、无 5xx、无中断，平均 ~3.4 MB/s；20:06 / 20:23 那两轮 05b 的「artifact 取不到」
现在**不可复现**。但**配额本身查不到**（见下），所以判据只能靠实测基线 + 通道分层，不能靠「额度还剩多少」。

## 一、为什么查不到「还剩多少」

| 通道 | 结果 |
|---|---|
| `gh api /rate_limit` | `core: 5000，剩余 4872` —— 这是 **API 调用配额**，与 egress 无关，答不了这个问题 |
| `gh api /users/<u>/settings/billing/actions` | `404 Not Found` + `This API operation needs the "user" scope` |
| `gh api /users/<u>/settings/billing/shared-storage` | 同上（404 / 缺 `user` scope） |
| `gh api /settings/billing/usage` | `404` |

→ 结论：**GitHub 没有公开的 egress 余额接口**（对个人账号且当前 token 无 `user` scope），
所以「限额现状」只能用**实测下载行为**推断：能下载、不 5xx、吞吐稳定 ⇒ 未受压。

## 二、05b 两轮红到底红在哪（日志逐字核对）

| run | 时间 | 失败步骤 | 日志原文 |
|---|---|---|---|
| 41120626718 | 20:06 | `actions/download-artifact@v4`（取 plan-05b） | `Unable to download artifact(s): Unable to download and extract artifact: Artifact download failed after 5 retries.` |
| 41122821137 | 20:23 | `gh run download`（取 plan-05b，重试） | `error downloading plan-05b: error extracting zip archive: error extracting "05b_plan.json": openat 05b_plan.json: file exists` |

两件事要分清：

1. **真的下载失败**（41120626718）：8 片并行拉同一个 artifact（190 KB），50 秒后放弃重试 —— 这是
   「同 artifact 并发拉取被限流」的症状，不是数据量问题。**这是 egress 压力的真实症状形态。**
2. **重试逻辑自己撞自己**（41122821137）：重试时 zip 又解到同一目录，文件已存在 → 5 次全撞同一错误。
   这一轮**不是** egress，是我自己的重试写法有 bug（已由 `7ed74c8` 的「走 git，不拉 artifact」绕开）。

⚠️ 诚实说明：`grep -ci egress` 对 41116421397 / 41114330819 / 41119004076 / 41121952357 四个 run
的完整日志 **全 0 命中**；仓库里所有 `Egress` 字样都是**层名**（`..._Egress__FeatureServer_0`），
不是报错。所以「Egress is over the account limit」这句话**在本仓日志里找不到字面出处**。
不再拿它当既定事实，改按下面的实测基线判。

## 三、实测基线（2026-10-30 21:00–21:11 UTC，本机直连）

| 项目 | 体量 | 耗时 | 吞吐 | HTTP |
|---|---|---|---|---|
| Release 资产（checkpoint） | 48 KB | 0.3 s | — | 200 |
| Release 资产（NAD u00000 单包） | 25 MB | 8.6 s | 3.0 MB/s | 200 |
| Release 资产（NAD u00001–u00006） | 150 MB | 41.6 s | 3.6 MB/s | 200 |
| Release 资产（NAD 66 个单元包） | 1.8 GB | 8 m 57 s | 3.4 MB/s | 200（0 次 5xx） |
| Artifact 下载 `plan-05b`（190 KB） | 190 KB | 1.9 s | — | 200 |
| Release create + upload（probe，建后即删） | 1 KB | <2 s | — | 200 |

复测方法（下次照抄）：

```bash
# ① release 资产：拿一个中等包测吞吐（不要拿整层）
time gh release download <tag> --pattern "*-u00000.tar.gz" -D /tmp/egress --clobber
# ② artifact：拿最小的 plan 产物测通道
time gh run download <run_id> -n plan-05b -D /tmp/artsmoke
# ③ 写通道：probe release 建/传/删一次（确认 GITHUB_TOKEN 的 contents:write 还通）
gh release create probe-$(date +%s) --notes tmp /tmp/probe.txt && gh release delete ... --yes --cleanup-tag
```

判据：**出现 5xx / 重试 5 次 / 吞吐掉到 <1 MB/s** ⇒ 判 egress 受压，当轮只许走 git 通道，禁任何批量下载。

## 四、硬判据（写死，后续阶段照此执行）

1. **plan / 片账本 / 报告 一律走 git**（`7ed74c8` 已落地：plan job 提交 `collect/ledger/<stage>_plan.json`
   到 main，shard 用 `git checkout origin/main -- <file>` 取，artifact 只做兜底）。继续执行，不回头。
2. **artifact 只当兜底**：任何「唯一通道是 artifact」的设计都算缺陷（一片取不到 = 整片假红）。
3. **大资产只上传，不在 CI 里反复下载整包**：账本重建按 pinned 资产清单单次下载；禁止
   「每个 shard 都拉一遍全量 checkpoint」这类放大下载。
4. **几何补采押后**：8.3 GB 下行 + 3.15 GB 落盘会二次打穿限额，**等 egress 观测恢复 + 05b 全绿
   再开灰度**。四项实测不变，只是顺序后移（本轮不开、不预跑）。
5. **每次阶段收官前留一次基线**：按上面三条复测命令各跑一遍，把「时间/字节/HTTP」记进本文档表格，
   累积成趋势；有异常先归因再决定放不放量。

## 五、对 05b 后续的影响（当前）

- 05b run `41123309047`（20:27 起）走**git 取计划**，14 片正常推进，main 上已陆续出现
  `collect: 05b 片 01 / 02 / 04 账本` 提交 ⇒ **egress 不是当前瓶颈**。
- 风险窗口在**阶段收官的重建/汇总**：那时会集中下载 Release 资产。规矩是「单次、按清单、不并行拉同一份」，
  且账本先在 git 里落地（`failed=0` 才接续下一阶段），下载失败也不许把已落地的账本拖成假红。
