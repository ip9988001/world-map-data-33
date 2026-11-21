# STEP 04b — 全州放量（全量补采）

> **判据卡 v2.1（补采变体）**　工头：`collect/supervisors/step_04b.py`　工人：`.github/workflows/collect-full.yml`（stage=04b）
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
04 是「一次拿大部分人口」的通用放量，历史上有 272 层因 matrix 上限 / 单元没跑完而留在 pending。
04b 只做一件事：**把 `row_count > 300000` 的层补完，一层不留**。
它与 04 的全部差异：

| 差异点 | 04 | 04b |
|---|---|---|
| 已采层 | 重采（幂等覆盖） | `skip_done=true` 直接剔除，只补缺口 |
| 执行方式 | 一层一个 matrix job | 分片：**一片一个 job，片内顺序跑 20 层** |
| Release tag | `collect-step04-<layer>` | 同上（**共用命名空间**，续跑判定才对得上） |

## 输入
`layer_plan.csv` 里 `row_count > 300000` 的层，减去 `done_from = 04` 判为已完成的层
（判定 = Release tag 命中 + 本机 audit；两处都不认，宁可重跑也不漏层）。

## 产出 / 证据
`collect/ledger/04b_plan.json`（分片计划）→ `collect/ledger/step04b_shard<N>.json`（逐片逐层账本）
→ `collect/step04b_ledger.json`（合并）→ `collect-step04-<layer>` Release 资产（part + checkpoint）

证据清单：`report`、`releases`、`checkpoint`、`unit_errors`

## 怎么做
- `collect/full_plan.py` 先切片（默认 20 层/片），片数上限 250（GitHub matrix 硬顶 256，留余量）
- 每片一个 job 调 `collect/full_shard.py`；片内逐层跑 `collect/run_step_04b.py`
- 每层四态之一：`ok` / `empty` / `partial` / `failed`（外加 `skipped_done`），**全部落账**
- `capped_by_upstream`（2026-10-31 新增）：上游改成**服务级 token**（连 `<api>/0?f=json` 都 499，
  `returnCountOnly` / `returnIdsOnly` 同样 499，且连续两轮探测一致）→ 这层**永远采不到更多**。
  账本记：已采行数照旧计入 `rows`；`declared` 置空、另记 `declared_unverifiable`，**不入缺口分母**；
  证据必须带 499 原文 + 探测时间 + 层 id（`analysis/04b-token-499-evidence-*.json`）。
  判据与改判命令见 `collect/adjudicate_04b.py --capped`；preflight E14 只**建议**不改账（改口径要人点头）。
- `upstream_unstable`（2026-10-31 新增）：**可连通、但连续 N 次（默认 3）尝试都超时 / 503 / 返回非 JSON，
  且没有进展**（每次尝试的 rows / 已有单元包数逐次不变）→ 重试收益趋零，停手。
  与另外两个「采不到」严格区分：`capped_by_upstream` = 要 token（永远采不到）；
  `unverified` = 连不上（等网络）；`upstream_unstable` = 连得上但给不出数据（换时间也没用）。
  账本记：`declared` **不动**（行确实没采到，分母与 gap 照算）、逐层 `attempts_n` / `failure_kinds` /
  `attempt_log[]`（每次的时间/类型/耗时）/ `attempts_elapsed_min`；阶段级 `upstream_unstable_layers[]` 出收口表。
  判据来源：`collect/attempt_log.py`（把逐轮 shard/run 账本里的 failed 记录聚成尝试账本，
  失败类型四分类：超时 / 503 / 非 JSON / token）；preflight **D13** 点名并默认剔除，
  `full_plan.py` 不再把它们排进待采队列；要再试必须显式 `--force-unstable-layer <层>`。
  目标：**同一个层不许连续吃掉 3 轮 CI**。
- 单层 3h 硬超时；失败层必须带原因（rc / err / 差额），**不吞错、不 `|| true`**
- 实采与声明差 > 0.2% 记 `partial`：不是失败，但收官文档必须写清是「单元没跑完」还是「计划期口径差」
- 每单元完成即传即删；checkpoint 在 Release 上，重跑只补缺口

## 派单参数（默认值不许随手改）

| 参数 | 默认 | 为什么 |
|---|---|---|
| `layer_timeout` | **60 分钟** | 挂死一层最多吃掉 60 分钟，剩余预算还能跑别的层。**调大必须给理由，并写进派单回执**：180 分钟 × 1 个挂死层 = 吃掉一半 job 预算（片上限 350 分钟），run `41123309047` 就是这样让 4 片（3/8/11/13）全部跑满 ~5h50m 被 `cancelled`（片账本原文 `job 内单层超时 3h`）—— 见 W33-023（复发×1）。大层要多跑就**分轮续跑**（checkpoint 在，下一轮接着跑），不是把单层上限往上抬 |
| `size` | 按拟合推（见下） | `t(分钟) ≈ 0.15 + 7.92 × 行数(百万)`，拟合自 05b 上一轮 1977 条层记录；按 `rows_asc` 的**末片**（最重）估，单片目标 ≤ 120 分钟、留出「一次 60 分钟超时」的余量 |
| `max_shards` | `0`（全起） | 非 0 会截断尾片：`plan_truncate.py` 必打 `::warning::` 并点名被砍的分片与每一层（W33-036），但**被砍 = 本轮注定没跑** |
| `chain` | `0` | 单跳不级联；07b 的 `NEXT` 为空（2026-10-31 停车线：到 07b 就停，08/10b/几何要口号） |

实测标定（2026-10-31）：`size=50` → 21 片，单片**纯工时**最大 67 分钟、片墙钟最大 215 分钟（3 层各吃满 60 分钟超时）；`size=200 + layer_timeout=180` → 4 片撞 350 分钟全 cancelled。

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `total_rows_min` | ≥ 30000000 | 累计实收行数下限 |
| `layers_min` | ≥ 40 | 覆盖层数下限 |
| `layers_max` | ≤ 60 | 覆盖层数上限（超了说明选层口径跑偏） |
| `per_layer_rows_max` | ≤ 5000000 | 单层实收上限（超了说明口径不对） |

## 失败怎么办
单层失败只影响该层（`fail-fast: false`），记 failed 继续；本阶段 failed ≠ 0 就**不自动接续**下一阶段，
停在原地等人看账本。同一 host 反复 5xx 降到 1 并发；额度接近上限时主动停并在简报写明。

## 计划期探针的失败分类（muse-000146 第 3–6 项，2026-11-22）

plan json 里的探针证据是**全量**的（`probe_failed` 与 `probe_failed_n` 同源，展示层才截断并写「显示前 50 / 共 N」）。
失败按 `collect/lib/fetch.py` 的分类计数（`probe_failed_by_kind`），**400 与 404/500 分开算，禁止合并**：

| kind | 含义 | 可修？ | 处置 |
|---|---|---|---|
| `bad_request_paging` | 400 且 body 是分页/参数语义（分页越界、Pagination is not supported、resultOffset 非法） | **可修**（改分页策略/参数） | 进 dead 前先复探；可与 404/500 分开定向修 |
| `bad_request_400` | 400 但与分页无关 | 可修 | 同上 |
| `not_found_404` | 端点没了（esri "Service not found" / HTML 页） | 不可修 | 判 empty / unverified，不再复探 |
| `server_5xx` | 上游服务端坏 | 不可修（重试收益趋零） | 复探 3 次全败才 dead |
| `rate_limited_429` | 限流 | 等一等 | 退避后回到待采 |
| `svcerr` | HTTP 200 但 body 带 `{"error":…}` | 视 message | 落 `reason` |
| `timeout` | 超时/连接异常 | 视情况 | 复探 |

探针每条结果都落 `{layer_id, count, count_path, body_keys_sig, parse_ok, reason}`（解析固化在
`full_plan.parse_count_body`，可单测）；`parse_ok=false` 必须带 `reason`，**不许静默 None**。
dead 项必须带 `dead_since`（UTC）与 `probe_attempts`（逐次 `{at, attempt, status, code, elapsed_ms}`）；
复探成功的层回到待采队列，不留在 dead。

## 命令（照抄）
```bash
python3 collect/full_plan.py --stage 04b --size 20 --out collect/ledger/04b_plan.json
python3 collect/full_shard.py --stage 04b --shard 0 --plan collect/ledger/04b_plan.json --workers 4
python3 collect/step_full_report.py --stage step04b
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "04b",
 "kind": "collect",
 "title": "全州放量（全量补采）",
 "select": {
  "where": "row_count>300000",
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 1000000,
 "unit_bytes": 1500000000,
 "tag": "collect-step04-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "unit_errors"
 ],
 "accept": {
  "total_rows_min": 30000000,
  "layers_min": 40,
  "layers_max": 60,
  "per_layer_rows_max": 5000000
 }
}
```
