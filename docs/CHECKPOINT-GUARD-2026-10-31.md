# force 重跑不许抹掉「完成度证据」——检查点备份 + 按单元合并 + 行数只许涨

> 分支：`fix/force-checkpoint-preserve`（基于 `chore/ledger-merge-fix` `a478570`）
> 事故：2026-10-30 22:23Z，run `41126178216`（04b 16 层补采，`chain=0`）
> 影响层：`s_Points_from_National_Address_Database_view_FeatureServer_0`（NAD view）

---

## 一、事故是什么

| 项 | 值 |
|---|---|
| 覆盖前检查点 | 68 个单元 / `unit_uploaded=true` / **39,875,268 行** |
| 覆盖后检查点 | 441 字节，1 个单元 / 0 行 / `unit_uploaded=false` / `done_units=[0]` |
| Release 里的单元包 | 68 个 `u00000…u00067.tar.gz` **一个都没少**（4.60 GB，最早 16:56Z，最晚 19:42Z） |
| 账本后果 | 该层 `partial(39,875,268)` → `failed(0)`，`ledger_rebuild` 的 rows 少 33.4 M |

根因在 `collect/pilot.py::_fetch_ckpt_asset`：从 Release 取回上一轮检查点后，
只要 `plan_hash` 不同就 `return None`，pilot 于是认为「本层第一次跑」，
新建一份空检查点，收尾时 `gh release upload --clobber` **整份覆盖**。
覆盖的那一刻，68 个单元包还在，但「哪些单元完成、每个单元多少行」的证据没了。
`ledger_rebuild` 与 `step_full_report` 都读检查点口径，于是账本判据力归零。

这不是数据丢失，是**判据丢失**。

## 二、四条规矩（本分支落地）

### 1. force 语义改成「先备份，再按单元合并」

- **备份**（动手之前）：`_checkpoint.bak-<RUN_ID>.json`
  - 本地：`collect/out/<layer>/_checkpoint.bak-<RUN_ID>.json`
  - Release：`<layer>-checkpoint.bak-<RUN_ID>.json`
  - 两处都只保留 **3 代**（`ckpt_guard.KEEP_BACKUPS`），更老的自动清掉。
- **合并不覆盖**（`ckpt_guard.merge_checkpoints`）：
  - 旧单元包名若在 Release 里**仍在且可下载**（`state=uploaded` 且 `size>0`）
    → 保留其 `unit_uploaded=true` 与行数，并标 `legacy_split=true`；
  - 新旧切分不兼容时**两边都记**：`units_new[]` / `units_legacy[]` 分开统计，
    `rows` 按**包名**去重后求和（不按下标对齐、不猜）；
  - 本 run 若用同名包覆盖了旧包 → 记 `dedupe=same_package_name` + `overwritten_by_run`，
    行数取两者较大者，**不双算**；
  - Release 资产清单查不到（`assets=None`）→ 一律按「还在」处理，
    绝不用「不知道」当丢行的理由。
- **包名不被覆盖**（第二道保险）：切分与旧检查点不一致时，本轮单元包名加代际前缀
  `r<planhash8>-`（如 `<layer>-rabcd1234-u00012.tar.gz`），
  这样 `--clobber` 不会把旧的真数据包换成新切的半截包（覆盖了就没有回滚基准）。
  真实资产名记进检查点 `unit_package[str(idx)]`，去重与核对都按它来。

### 2. 一条总规矩：任何重跑都不许让某层 rows 变小

两处闸门，同一个判定函数（`ckpt_guard`）：

| 位置 | 判据 | 变小且无实证时 |
|---|---|---|
| `pilot`（检查点） | 合并后 `rows_after` vs 旧检查点 `rows_before` | 不写检查点，`SystemExit`，full_shard 记 failed |
| `ledger_merge.write_run_and_stage`（阶段账本） | **合并结果**逐层 rows vs 旧阶段账本 | 阶段账本一个字不动，返回 `error`，`step_full_report` 退出码 2 |

「变小」必须带 `regression_reason` + 证据路径（文件必须真实存在）才放行；
放行也要留痕：`ckpt_guard` 写 `row_regression{}`，账本 `revisions[]` 追加
`kind=row_regression_allowed`。CLI 入口：`step_full_report.py --row-shrink-evidence LAYER=PATH`。

**不算变小的情况**：本轮 `status=failed` 且 `rows=0`（没测到，不是测出 0）。
账本合并在这种情况下保留旧行数、旧状态（`pick_better` 状态优先、同状态取行数大者），
既不会把 `partial(39.8M)` 降成 `failed(0)`，也不会因为一次 cancel 就拒绝整阶段合并。

### 3. 从 Release 反推完成度（不重采、不碰上游）

`collect/rebuild_layer_rows.py`：逐包 `gh release download` → tar 解包 →
每个 part `.ndjson.gz` **流式数换行** → 求和 → 落 JSON（含每包行数、part 数、
资产字节、sha256、包号连续性检查）。这是唯一既不看 checkpoint、也不看上游
`returnCount` 的口径（上游当前声明 97,928,946 行，与已采 39.9 M 不可比，不能拿它当分母洗账）。

```bash
python3 collect/rebuild_layer_rows.py \
  --layer s_Points_from_National_Address_Database_view_FeatureServer_0 \
  --tag collect-step04-s_Points_from_National_Address_Database_view_FeatureServer_0 \
  --jobs 8 --expect-rows 39875268 \
  --out analysis/nad-view-rebuild-2026-10-31.json \
  --apply-ledger collect/04b_ledger.json \
  --restore-events analysis/nad-view-ledger-restore-2026-10-31.json
```

### 4. 等稳定再验收

16 层 run 全停后跑 `ledger_rebuild --check`；若仍 DIFFERS，根因大概率就是这层，
用第 3 步产物对齐后复验（结论见本文档末尾「验收」一节）。

## 三、为什么判「合并结果 vs 旧账本」，而不是「本轮 vs 旧账本」

本轮跑挂（`failed/0`）在账本合并里本来就**不会**覆盖旧记录，它没有「测出更小的值」，
只是「这次没测到」。把这种情形也判成回退，会让每一次 cancel 都卡住阶段合并 ——
这正是 2026-10-30 之前那两次「账本停更」的同类风险。

唯一会让阶段账本 rows 真变小的路径是：**更优状态 + 更少行数**
（如 `partial 39,875,268` → `ok 5,000,000`，上游口径变了）。
这一条必须带证据，其余情形一律保留旧值。
