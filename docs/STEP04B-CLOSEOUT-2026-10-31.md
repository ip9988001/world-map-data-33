# 04b 收口 checklist（2026-10-31，等 `41126178216` 跑完按序执行）

> 前置：run `41126178216`（`world-map-data-33`，`head_sha=cb86f42`，plan **3 片 / 22 层**，矩阵只起了 **shard 0 + shard 1 = 16 层**）
> 结束后执行。**顺序不许调换**：先复原证据、再比指纹、再活态重算、最后才谈缺口。
>
> 三条不许碰：在跑的 run 不 cancel；`watch07b.sh`（pid 148690）不碰；采集口径不改。

## 0. 分母口径（先读：两个数一起报，禁只报一个）

| 口径 | 算法 | 含义 |
|---|---|---|
| **按声明分母** | `rows_verifiable ÷ declared` | `declared` 剔除 `capped_by_upstream` 层（该层 declared 移入 `declared_unverifiable`，永不进分母） |
| **按可核实分母** | `rows_verifiable ÷ (已刷新层用上游 returnCount + 未刷新层用旧声明)` | 同时剔除 capped，且已 `--apply-declared-refresh` 过的层不再用旧快照 |

两个数必须同屏出现，并带 `declared_refreshed_at`（没刷过就写「未刷新」）。**单独抛一个 = 无效报表。**
依据：`docs/WORKFLOW-FAILURE-LEDGER.md` W33-034 + `docs/STEP04-ADJUDICATED-2026-10-30.md` §3.0.1。

## 1. 守望 v3 复原 NAD-view checkpoint（硬门禁）

```bash
# watcher-v3（pid 171860）自动做，人工复核它的日志
tail -40 /tmp/nad-postrun.log
# 判据：出现 restore 成功行 + `--expect-rows 39875268` delta=0；出现 ::ALARM:: 即停下问人
```
硬门禁：`collect/rebuild_layer_rows.py --restore-checkpoint --recheck --expect-rows 39875268`。
delta≠0 时脚本 **rc=3 且不写回**（没有绕过参数）；备份名 `<layer>-checkpoint.bak-<RUN_ID>-prerestore.json`。

## 2. `ledger_rebuild --check`：**预期 DIFFERS**（不是回归）

```bash
python3 collect/ledger_rebuild.py --stage 04b --check
```
**预期结果：`DIFFERS`，并点名 NAD-view 层。**
原因：输入从「被 `--force-layers` 覆写成 441 B 的坏 checkpoint」换回「Release 上的真 checkpoint」——
**输入变了**，指纹当然变。这不是账本回归，是坏件换真件。**必须把这句话写进日志与收官文档**，
否则下一次看到 DIFFERS 会被当成故障。

## 3. 活态重算 → 应回 `IDENTICAL`，记 digest

```bash
python3 collect/ledger_rebuild.py --stage 04b          # 重算活态产物
python3 collect/ledger_rebuild.py --stage 04b --check  # 应 IDENTICAL
# 记录输出里的 digest（形如 digest=3395a78316db9b0c）
```
`--check` 比的是 `input_fingerprint`（逐层资产名+字节、`ckpt_sha256`、声明行数、asset_evidence），
**不比历史文件字节**。DIFFERS 会点名差几层、哪几层。

## 4. 16 层补采 vs 6 个 missing 层（缺的列清单，别自动再派）

本 run 矩阵只有 2 片（`max_shards` 生效），shard 2（6 层）**没跑**：

| missing 层 | 声明（行） | 本 run 落在 | 跑完后处置 |
|---|---|---|---|
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 3,618,012 | shard 1 | 覆盖到 → 转 ok；没覆盖 → 列清单 |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | 303,175 | shard 1 | 同上 |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | 6,297,169 | shard 1 | 同上（secure：需 token，可能又 failed） |
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | 6,585,376 | **shard 2（未跑）** | 本 run 不会覆盖 |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | 6,585,376 | **shard 2（未跑）** | 本 run 不会覆盖 |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | 303,175 | **shard 2（未跑）** | 本 run 不会覆盖 |

判定命令（跑完后）：
```bash
python3 collect/ledger_rebuild.py --stage 04b            # 资产真值重建
python3 collect/adjudicate_04b.py --rebuilt collect/ledger/step04b_rebuilt.json \
  --evidence analysis/04b-upstream-evidence-2026-10-30.json \
  --plan collect/ledger/04b_plan.json --out collect/04b_ledger.json \
  --capped-evidence analysis/04b-token-499-evidence-2026-10-31.json --check
# 再逐层看 6 个 missing 的 status：覆盖到的自然变 ok/partial，没覆盖的仍 missing
```
**不许自动再派**：定向补跑必须 `chain=0`、一次一条，由人点头。

## 5. 出最终两个口径数 + `failed=0` + `complete` 判词

必须一起给出（缺一不算收口）：

- `failed` = **0**（adjudication 保证：失败一律分到 missing/partial/unverified/empty/capped）
- `按声明分母` 覆盖率 = `rows_verifiable ÷ declared` = **?**
- `按可核实分母` 覆盖率 = `rows_verifiable ÷ (刷新后分母)` = **?**（附 `declared_refreshed_at`）
- `complete` = **成立 / 不成立**，不成立要写「缺什么」（`missing` 层数 + 行数 + `unverified` 层数）
- 决策提示：`complete` 目前定义 = `missing==0 and unverified==0`。capped 层不算未完成（上游永久不可采，已尽取）。

## 6. 收口后（同一天，不许拖）

- 新踩的坑当天补进 `docs/WORKFLOW-FAILURE-LEDGER.md`（含错误原文关键行 + run id + 证据路径）。
- 首轮 `--refresh-declared` 在本 run 收口后执行，**只读**先看差异表；采纳要人点头。
- 账本/plan 层数若被 run 的 merge job 冲小，按守望脚本用审结快照复原并追加 `stage_ledger_restored` 事件。
