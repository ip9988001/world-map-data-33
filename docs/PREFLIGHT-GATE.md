# 派单前核验（preflight gate）—— 跑之前先证明「不该白跑」

> 立规：2026-10-31。用户原话：**每次跑之前先核验有没有 bug/错漏，再决定要不要跑；不要跑了之后一再因为各种原因返工。**
> 落地：`collect/preflight_dispatch.py`（只读）+ workflow `plan` job 第一步 + 本文档。

## 铁律

**没有 preflight 输出的派单，视为无效派单。**

- 门禁不通过（任一 `FAIL`）→ 退出码非 0 → `plan` job 直接红，shard 一个都起不来。
- 派单回执必须贴 preflight 的结论行：`verdict / FAIL n / WARN n`，以及每条 `WARN` 的处置。
- 派单里必须写 **`故障清单已查：<编号列表 | 无>`**（模板见 `docs/DISPATCH-TEMPLATE.md`），没有这行视为无效派单。
- **故障台账唯一真值** = `docs/WORKFLOW-FAILURE-LEDGER.md`（写之前必查、跑后必补；新坑当天补，commit 写 `ledger: +N <类别>`）。
- `WARN` 不拦派单，但**必须写明接受理由**（例如「本机 403 但 CI 可采」）。

## 一、派单前 checklist（16 项）

跑 `python3 collect/preflight_dispatch.py --stage <stage> [--force-layers ...]`，逐项勾。

### A 队列 / 并发

- [ ] **A1** 同 concurrency group（`collect-full-<stage>`）有没有 `pending`？
      → 有 `pending` = **FAIL**（新派单会把它挤掉）；只有 `in_progress` = WARN（会排队，给出预计等待分钟）。
- [ ] **A1b** 上游阶段是否在跑？（05b 在跑 → 它全绿会自动派 07b）
      → WARN：现在手派 07b 会撞同一个 group；要么等它派，要么确认它 `chain=0` 不会自动派。
- [ ] **A2** 其他 stage 的在跑 run 数 → >2 记为 WARN（共享 egress 与上游配额，片失败率升高）。

### B 代码版本

- [ ] **B3** 要派的 `--ref` 与 main 的关键文件 **blob sha 一致**，且 7 项已批准修复齐全
      （`chain_policy` 断链 + `ledger_merge` 阶段账本保护 + `ledger_merge` rows 回退护栏
      + `ckpt_guard` 检查点合并 + `pilot` 备份）。→ 不一致 = **FAIL**，并列出差异文件 / 缺失项。
- [ ] **B3b** main 的 sha 在**已批准版本白名单**（`collect/preflight_dispatch.py::APPROVED_MAIN`）里
      → 在 = **PASS**（证据里写明这个版本批了什么）；不在 = **WARN**（不挡派单，但先把这次合并审一遍
      再加进白名单，否则「main 前进了却没人审」就是漏）。
- [ ] **B4** `chain_policy.py --stage <stage> --dry-run`：04b/05b → `next ∈ {05b,07b}` 且 `child_chain=0`；
      07b/10b → `next=空` 且 `decide=stop`。→ 不符 = **FAIL**（停车线破了）。
- [ ] **B5** 禁止清单：`10b` 需 `--authorize-heavy`（= workflow 的 `authorize_heavy=1`）；
      `08/09/10/几何` 需显式口号（`--authorize-manual`）→ 未授权 = **FAIL**。

### C 账本基线（跑前钉死，跑后才好对比）

- [ ] **C6** 记录三份账本现值：`collect/<stage>_ledger.json`（阶段级）、
      `collect/ledger/<stage>_rebuilt.json`（资产真值）、最近一次 `collect/ledger/<stage>_run<id>.json`。
      各记 `layers_n / ok / partial / missing / unverified / empty / failed / rows`。
- [ ] **C7** 逐层 rows 基线落到 `analysis/rows-baseline-<stage>-<ts>.json`（跑后比对用）。
- [ ] **C8** merge 写入逻辑是否已带「单 run 不得覆盖阶段账本」+「逐层 rows 不许变小」保护
      → 缺失 = **FAIL**（不然跑完账本必被冲）。

### D 数据重叠

- [ ] **D9** `--force-layers` 的目标层 × 在跑 run 的目标层，**交集必须为空**
      → 有交集 = **FAIL**（两个 run 同时写同一层必撞）。在跑 run 的目标层取自它落在 main 上的
      `collect: <stage> 计划（run <id>）` 提交；取不到就报 WARN（不假装无交集）。
- [ ] **D10** 本次计划层 × Release 已采层：交集层数必须给出；>0 要说清是**补采**（缺口/半截）不是重复采。
      没有 plan 文件时用行数分档估算（`04b >300k` / `05b 5k~300k` / `07b 1~4999`），并标注 `estimate`。
- [ ] **D11** 目标层是否已有检查点/单元包 → 有就必须先备份（pilot 会自动备份保留 3 代；
      没有 `.bak` 时给出手工备份命令）→ WARN。

### F 已知坑

- [ ] **F16** 本次改动 / 本次派单有没有碰到 `docs/WORKFLOW-FAILURE-LEDGER.md` 里的坑？
      → 门禁自动读台账（`--ledger-category` 指定类别，不写则按 `--ref` 的改动文件推导）+ 输出 `ledger_hits[]`：
      触及**未规避**（关联提交=未修）的条目 = **WARN**（把该条「修法」当规避动作打出来）；
      触及**复发 ≥2 次**的条目 = **FAIL**（同一坑不能第三次踩；确认已规避用 `--ledger-waive W33-011` 显式豁免，豁免写进证据）。

### E 上游可用性（只发 `returnCountOnly`，不取一行数据）

- [ ] **E12** 抽样 ≥5 层打一次计数：返回 0 行的层单独列出（跑了也白跑）。
- [ ] **E13** 403 / 超时 / `Token Required` 单独列出；**不得**因「本机不可达」判死
      （本机 ≠ CI）→ 只 WARN + 附证据。
- [ ] **E14** 声明行数不可复核的层标 `declared_unverifiable`，**不计入分母**；
      其中「服务级 token」（连 `<api>?f=json` 都 499）要点名 —— 这种 CI 也采不到。

产物：
- `analysis/preflight-<stage>-<ts>.json`（逐项 + 证据）
- `analysis/rows-baseline-<stage>-<ts>.json`（跑后比对基线）

## 二、FAIL 处置表（一行一条）

| 项 | FAIL 的处置 |
|---|---|
| A1 同组 pending | 先等/取消那个 pending（`gh run cancel <id>` 需人确认），别硬派 |
| A1b 上游在跑 | 等上游自己派；或确认上游 `chain=0`（不会自动派）后再手派 |
| B3 代码版本不一致 | 把缺的修复合到 `--ref` 上（PR #12 / `chore/ledger-merge-fix`），或改从 main 派 |
| F16 触及复发≥2 的坑 | 先在派单里写清规避动作 + 证据；确认已规避后 `--ledger-waive <编号>`，并把规避方式补进台账「验证方式」列 |
| B3b main 不在白名单 | 先审这次 main 的改动（`git log --oneline <旧sha>..<新sha>`），确认该带上后把 sha 前 7 位 + 一句话加进 `APPROVED_MAIN` |
| B4 接续策略不符 | 修 `collect/chain_policy.py` 的 `NEXT/ALLOWED/CHILD_CHAIN`，跑 `--all --dry-run` 自证 |
| B5 未授权重阶段 | 10b：确认预算后加 `authorize_heavy=1`；08/09/10/几何：先拿口号 |
| C6 账本缺失 | 先跑 `ledger_rebuild.py`（从 Release 资产重建）再派，别在无账本状态下跑 |
| C8 写入保护缺失 | 先合账本保护（`ledger_merge` + `ckpt_guard`），否则跑完账本必被冲 |
| D9 目标层撞车 | 从 `--force-layers` 里去掉正在被写的层，或等那个 run 结束 |
| D10 已采重叠 | 确认是补采：用 `--force-layers` 点名缺口层，不要整片重跑 |
| D11 检查点未备份 | 先 `gh release upload <tag> <layer>-checkpoint.bak-<RUN_ID>.json`（pilot 会自动做） |
| E12 上游 0 行 | 从计划里剔除该层（或标 `empty`），别浪费片位 |
| E13 403/超时 | 只记录证据，先照派；片端再失败才升级（本机 ≠ CI） |
| E14 声明不可复核 | 跑后差额分母剔除该层；服务级 token 的层直接剔或配 token |

## 二之二、已批准版本白名单（`APPROVED_MAIN`）

B3 判「`--ref` 的关键文件与 main 一致」，但 main 自己会前进：主库一合新修复，停在旧 main 上的 ref
就报「不一致」；反过来 main 前进了没人审也是漏。所以把「当前 main 是哪个已审过的版本」写成数据。

| main sha | 批准了什么 |
|---|---|
| `d5b5db2` | 4-7 停车线 + FREEZE/ROLLBACK 口径（本门禁的基线） |
| `f68c002` | `chore/ledger-merge-fix` 合入：单 run 不覆盖阶段账本 + 状态优先级合并（ok>partial>missing>unverified>empty>failed，同状态取行数大者）+ 小 run（<1/2）只写 run 文件 + 复原 04b 阶段账本（22 层→272 层） |
| `3f3c9b9` | rows 回退护栏：合并时逐层比 rows，变小写 `regressions[]`（层/旧/新/原因/证据）并在人读摘要单列一节；**不许静默取大** |

新增白名单条目的唯一姿势：审完那次 merge → 写 sha 前 7 位 + 一句话 → 跑 `test_preflight_dispatch.py`。

## 三、跑后 30 分钟内必做（post-flight）

1. **账本 rows 不许变小**：逐层比 `analysis/rows-baseline-<stage>-<ts>.json` → 任何一层变小都是 P0（要 `regression_reason` + 证据路径）。
2. **片齐全**：`shards_expected == shards_reported`（阶段账本字段 `shards_run_id` 指向本轮）。
3. **阶段账本 `layers_n` 未变（或变大）**：变小 = 被单 run 冲了，立刻回滚（见 `docs/ROLLBACK-20261031.md`）。
4. **`ledger_rebuild --check` 结论**：DIFFERS 必须逐层解释（资产增长 / 检查点被覆盖 / 上游口径变化），不许一句「有差异」了事。

```bash
# post-flight 一屏
python3 collect/ledger_rebuild.py --stage 04b --plan collect/ledger/04b_plan.json \
  --out collect/ledger/step04b_rebuilt.json --doc docs/STEP04-FULL-2026-10-30.md --check
python3 - <<'PY'
import json,glob
b=json.load(open(sorted(glob.glob('analysis/rows-baseline-04b-*.json'))[-1]))
led=json.load(open('collect/04b_ledger.json'))
now={r['layer']:r.get('rows') or 0 for r in led['records']}
shrunk=[(k,v['rows'],now.get(k)) for k,v in b['layers'].items() if k in now and now[k]<v['rows']]
print("行数变小：", shrunk or "无")
print("阶段账本 layers_n：", led['layers_n'])
PY
```

## 四、实现状态（哪些是硬判据、哪些只能 WARN）

| 项 | 状态 | 说明 |
|---|---|---|
| A1 / A1b / A2 | 硬判据（gh） | run 列表带 `head_sha`；stage 靠 plan 提交或 artifact 名（`plan-05b` / `led-05b-7`）推断 |
| B3 | 硬判据（git） | blob sha 比对 + 6 项标记比对；`origin/<ref>` 优先（本地 `main` 可能停在旧 commit） |
| B4 | 硬判据 | 真跑 `chain_policy.py --stage <s> --dry-run` 解析结论 |
| B5 | 硬判据 | 10b / 08 / 09 / 10 / 几何 |
| C6 / C7 | 记录 | 账本缺失只 WARN（07b/10b 本来就没跑过） |
| C8 | 硬判据 | 读 `--ref` 的源码标记，不信「我合过了」 |
| D9 | 硬判据（能取到目标层时） | 取不到在跑 run 的计划 → WARN，绝不假装无交集 |
| D10 | 硬判据（有 plan 时）；估算时标注 | 没有 plan 文件 → 分档估算，标 `estimate(band)` |
| D11 | WARN + 命令 | 只看资产清单（不下载检查点内容），判断有没有 `.bak` |
| E12 | 硬判据 | 抽样 ≥5 层（force 优先，再按分档均匀抽） |
| E13 | **只 WARN** | 本机 ≠ CI，403/超时不算死 |
| E14 | 硬判据（分类）+ WARN | `Token Required` / 非 JSON → `declared_unverifiable`；服务级 token（`?f=json` 也 499）点名 |

## 五、门禁在「当前真实局面」下的输出（2026-10-30T23:46Z）

两份完整产物：`analysis/preflight-07b-20261030T234637Z.json`、`analysis/preflight-10b-20261030T234710Z.json`
（含逐项证据与 rows 基线）。

### 07b — `FAIL (FAIL 2 / WARN 2)`

| 项 | 结论 | 说什么 |
|---|---|---|
| A1 | ✅ | 07b 自己的 group 空闲（`collect-full-07b` 按 stage 分组，05b 不占它） |
| **A1b** | ⚠️ | **上游 05b 正在跑（#41123309047）**：它全绿后会自动派 07b → 现在手派会撞同一 group |
| A2 | ✅ | 其他阶段在跑 2 个（阈值 2） |
| **B3** | ❌ | main 缺 4 项已批准修复（`ledger_merge` / `step_full_report` 走合并 / `ckpt_guard` / `pilot` 备份）→ 即两个待合 PR |
| B4 | ✅ | 07b → `next=空 / decide=stop`，停车线正确 |
| B5 | ✅ | 07b 属常规四阶段 |
| **C8** | ❌ | merge 写入保护未生效 → 跑完账本必被冲 |
| C6 | ⚠️ | 07b 三份账本都还不存在（从没跑过），只能记基线为空 |
| D10 | ✅ | 分档估算 27,530 层待采 × 已采 436 层，交集 0 |
| E12/E13/E14 | ✅ | 抽样 7 层：无 0 行、无 403/超时、声明都可复核 |

### 10b — `FAIL (FAIL 3 / WARN 5)`

| 项 | 结论 | 说什么 |
|---|---|---|
| **B5** | ❌ | 10b 是重阶段（宗地 8,116 层 / 20~85 GB），未给 `authorize_heavy` |
| B3 / C8 | ❌ | 同上（缺修复、账本无保护） |
| D10 | ⚠️ | 10b 的层清单在宗地表里、不在 `layer_plan.csv`，估不出 → 明说「无法比对」而不是给个假数 |
| E12/E13/E14 | ⚠️ | 没有可抽样层（force 为空 + 不在分档清单）→ 标「未核」，不假装通过 |

### 顺带查出来的真问题（04b 侧）

`--stage 04b --force-layers <NAD view 层>` 那一次核验发现：**该层上游已经变成服务级 token**
—— 连 `<api>/0?f=json` 都返回 `{"error":{"code":499,"message":"Token Required"}}`，
不是我们这边的 egress 问题。也就是说这层现在**没法再采**（68 个单元包是能拿到的全部），
门禁按规矩把它标成 `declared_unverifiable` / 服务级 token 点名，而不是当成「本机不可达」放行。

## 六、案例（都是真事，用来校准「门禁该不该开口」）

### 案例 1 · D9 真好用：同层 force 直接堵死（2026-10-31）

背景：run `41126178216` 正在写 22 层（2 片）。当时想「顺手 force 重跑 NAD view 那 2 层」，
preflight 一跑就 FAIL：

```
❌ D9  目标层撞车   这 2 层正在被 #41126178216 写（计划层交集 2）→ 现在 force 会两个 job 同 tag 并发
                    upload --clobber，谁后传谁赢，检查点会被打成「1 unit / 0 行」
```

**这就是它存在的意义**：D9 不是「防手滑」，是把 2026-10-30 22:23Z 那次事故的形状
（同一 tag 双写 → checkpoint 被覆盖 → 账本从 partial(39.9M) 掉成 failed(0)）在**派单前**
挡下来。所以 D9 一旦报交集，处置只有两条：从 `--force-layers` 里去掉正在被写的层，
或者等那个 run 结束。**没有「先跑着看看」这个选项。**

实测值：`--force-layers <NAD view 层>` → `FAIL`（交集 2）→ 去掉后 PASS。

### 案例 2 · E14 只建议、不改账：「服务级 499」不该靠人记得（2026-10-31）

同一层上游改成**服务级 token**：`<api>/0?f=json`、`returnCountOnly`、`returnIdsOnly`
三个端点全返回 **HTTP 200** + body `{"error":{"code":499,"message":"Token Required","messageCode":"GWM_0003"}}`。
HTTP 200 是关键 —— 只看状态码的检查会心满意足地说「服务正常」。

E14 现在的硬判据（连续两轮都服务级 499）：

- 打印建议命令（`probe_service_token.py` 出两轮证据 → `adjudicate_04b.py --capped`），
- **但不自动改账本** —— 改口径要人点头，账本只认 `--capped` 这一次显式动作；
- 已采行数照旧计入 `rows`，`declared` 移出分母记 `declared_unverifiable`。

落点：`collect/probe_service_token.py`（探测+证据）、`collect/adjudicate_04b.py --capped`（改判）、
`collect/04b_ledger.json` 的 `capped_by_upstream` 状态与 `capped_layers[]`。
