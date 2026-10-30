# 补采链闸门 & merge 容错（2026-10-30 立规）

> 起因：run `41019004076`（step04b，14 片 × 20 层 = 272 层）结论 **completed / cancelled** ——
> 10 片 success（0,3,4,5,6,7,8,11,12,13）、**4 片 cancelled（1,2,9,10）**、**merge = failure**。
> 28.6% 的片没跑完，且 merge 一红 → 整轮一行账都拿不到。本文记录两处硬伤的真实原因、修法和闸门判据。

## 一、merge 失败的真实原因（不是「deps 被 cancel 就会失败」这一个原因）

`merge` 用的是 `needs: [plan, shard]` + `if: always()`，本来就能在片被 cancel 后照常启动。
真正让它红的是**脚本层**，一共三条叠加：

| # | 原因 | 事实 | 修法 |
|---|---|---|---|
| 1 | 分片账本文件名对不上 | 首轮 run 用的是 07:15 的 main SHA，`full_shard.py` 当时写 `step04b_shardNN.json`，workflow 找 `04b_shardNN.json`；`upload-artifact` 的 `*_shard${N}.json` 也匹配不到零填充文件名 → 账本**全部静默落空** | `full_shard` 账本名统一 `<stage>_shardNN.json`；artifact 双 pattern；提交步兜底 `ls *_shardNN.json`（commit `48d1a48`） |
| 2 | 缺账本 → 脚本 `SystemExit` | `step_full_report.py` 里 `if not files: raise SystemExit("没有账本")` → merge 整体 failure | 改为：缺片/`partial_run` 片一律记成「未完成片」写进账本与文档，**脚本恒退出 0**（本次） |
| 3 | 全片被 cancel 时 `download-artifact` 也会失败 | `pattern: led-*` 一个都匹配不到时 v4 直接报错 | 该步加 `continue-on-error: true`（本次） |

**结论：是脚本 bug，不是「被 cancel 就必然失败」。** 现在片被 cancel 的后果只剩「账本里多出一行未完成片」。

## 二、cancelled 片必须显式留痕（不许静默）

两处留痕，缺一不可：

1. **分片口径**：`collect/<stage>_ledger.json` 新增字段
   `shards_expected / shards_reported / shards_incomplete[] / shards_incomplete_detail[{shard,cause,layers_planned,layers_n}] / complete`；
   `cause` ∈ `no_ledger`（片被取消或没启动）| `partial_run`（片内没跑完）。
   文档新增「二、片完成度（未完成片显式列出）」表，逐片给 `计划层 / 已记层 / 实采行 / 状态`，
   并写明「未完成片里的层没有账本条目，既不算 ok 也不算 failed」。
2. **资产口径**：`collect/ledger/step<NN>b_rebuilt.json` 的顶层 `cancelled_shards`（逐层含 status/rows/reason）+ 每层 `shard_cancelled` 标记，
   文档 `docs/STEP04-FULL-2026-10-30.md` 的片维度节按轮次列出片号 / job / 覆盖率。

分片口径的文档名带 `-shards` 后缀（`docs/STEP04-FULL-<date>-shards.md`），
与 Release 资产真值文档（`docs/STEP04-FULL-<date>.md`）**分开**，避免分片口径覆盖真值口径。

## 三、自动接续闸门（显式判据，不靠巧合）

`.github/workflows/collect-full.yml` → `merge` job 的「判定 + 自动接续」步，读 `collect/<stage>_ledger.json`，
**任一条件成立即禁止接续下一阶段**（写 `::error::` 注解 + step summary，但不改 merge 结论 —— 账本必须先落地）：

```
incomplete_shards > 0   → ⛔ 有片未完成（片号取自 shards_incomplete）→ 禁止接 05b
failed > 0              → ⛔ 有 failed 层                        → 禁止接 05b
complete == false       → ⛔ 片齐 failed=0 但仍有未完成标记        → 禁止接 05b
```

只有 `片齐 + failed=0 + complete=true + inputs.chain==1` 才 `gh workflow run ... stage=05b`。

- **为什么闸门不能 exit 1**：上一版在 failed>0 时 `exit 1` 把 merge 判红，与「有片被 cancel 也要拿到账」直接冲突。
  现在闸门 exit 0，红的是注解与 summary 里的「禁止接续」这一行，账本和文档始终可下载。
- **04b 现状**：`shards_incomplete` 非空（首轮 4 片 cancelled 的层靠 `force_layers` 续跑补齐，账本以 Release 资产重建），
  所以 04b 未全绿 → 05b 不会自动接。要放 05b，先让 04b 的 `shards_incomplete == []` 且 `failed == 0`。

## 四、复现

```bash
# 1) 单测（含「缺片/partial_run 也必须出账」4 条）
python3 -m unittest collect.tests.test_full_report_tolerance -v

# 2) 用真实分片账本试算（不会覆盖真值文档）
python3 collect/step_full_report.py --stage 04b --plan collect/ledger/04b_plan.json

# 3) 资产口径重建（幂等，--check 必须 IDENTICAL）
python3 collect/ledger_rebuild.py --stage 04b --plan collect/ledger/04b_plan.json \
  --run-id 41019004076,41092912755,41114330819,41116421397 \
  --out collect/ledger/step04b_rebuilt.json \
  --doc docs/STEP04-FULL-2026-10-30.md --check
```
