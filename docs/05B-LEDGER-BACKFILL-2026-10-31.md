# 05b 阶段账本补账（W33-013 尾巴）· 2026-10-31

> 结论：**445 层补回账本**，`layers_n` **2,325 → 2,770**（= 阶段计划层数）。
> 数据全在 Release；补账只读资产，不重采一行。
> 复核：`python3 collect/backfill_05b_ledger.py --plan collect/ledger/05b_plan_stage2770.json --check`
> → 必须 `IDENTICAL`。

## 一、事故形状

run `41123309047` 的 shard **3/8/11/13** 被 350 分钟 cap 掐成 `cancelled`，片账本随 job 一起消失。
但那 4 片共 770 层里，**445 层实际已经跑完**：

- Release tag `collect-step05-<layer>` 存在；
- `<layer>-checkpoint.json` 完整（`done_units` 齐、`unit_uploaded=true`、无残留 `unit_errors`）；
- `done_layers('05')` 判完成 445/445、未完成 0。

结果阶段账本只有 2,325 行，而阶段计划是 2,770 行 —— **少 445 层（19.3%）**。
账本把「数据在、账上没有」的层当成不存在，覆盖率被系统性低估；07b 之类下游读阶段账本判
「上一层是否合格」时也会拿到缺行账本。所以用户 2026-10-31 决定：**先补账，再派 07b**。

## 二、补账口径（只读 Release，不猜）

脚本：`collect/backfill_05b_ledger.py`；判据直接复用 `collect/ledger_rebuild.py::judge()` 的 05b 口径。

| 项 | 口径 |
|---|---|
| 候选层 | 阶段计划 `05b_plan_stage2770.json` 的 2,770 层 − 账本已有 2,325 层 = **445 层** |
| declared | `layer_plan.csv` 经 `worker_core._rows_from_csv/_norm_plan_row` 唯一化后的 `expect`（与采集器同源，避免 `@STATE-n` 层算成 0） |
| rows | checkpoint 的 `unit_rows_seen` 求和（老 checkpoint 无此字段才退回 `unit_rows`） |
| status | `judge()` 四态：`ok` / `empty` / `partial` / `failed`；**failed 不补**（缺资产 / 单元未传 / 残留错误 / tag 不符） |
| 每行标记 | `backfilled_from: "release_assets"`、`reason: "ledger_row_lost_on_cancel"` |
| 每行证据 | `units_done`、`packages[]`（unit 包名）、`evidence{release_tag, checkpoint_asset, checkpoint_sha256, unit_assets[], assets_bytes, first_upload, last_upload, plan_hash, url}` |
| 汇总 | `revisions[]` 追加 `kind=stage_ledger_backfilled, layers=445`（含 `lost_run_id=41123309047`、`lost_shards=[3,8,11,13]`、补账前后 layers_n） |

**一个边界**：`UojyNPhsWOk1W_..._FeatureServer_1` 的 unit 1 计划 0 行、实采 0 行、无 part 文件，
`unit_uploaded=false` 是正常的（没有东西可传）。`judge()` 原判 failed；补账脚本只对
「出问题的单元全部是零行单元」做豁免，其余问题一条不放。

## 三、补账后数字

| 项 | 补账前 | 补账后 |
|---|---|---|
| `layers_n` | 2,325 | **2,770** |
| ok | 2,278 | **2,722** |
| empty | 16 | 16 |
| partial | 7 | **8** |
| failed | 0 | 0 |
| upstream_unstable | 19 | 19 |
| unverified | 4 | 4 |
| missing | 1 | 1 |
| `declared` | 102,789,053 | **143,068,409** |
| `rows` | 101,511,310 | **141,664,792** |
| `gap` | 1,277,743（1.2431%） | **1,403,617（0.9811%）** |

补回 445 层自身：declared 40,279,356 / rows 40,153,482 / gap 133,591（其中 444 层 ok、1 层 partial）。

**为什么 gap 变大 125,874 行**：补回的 445 层不是「零缺口」——其中
`_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` 的 checkpoint 计划只有 118,916 行
（已全部采完），但当前 `layer_plan.csv` 声明 251,639 行，差 52.74%。按 05b 判据这属于
「计划期口径差」，记 `partial` 并保留缺口，不把 13 万行写成 ok。

## 四、复核与防复发

```bash
# 补账幂等（会重下/缓存 checkpoint，逐层比对）
python3 collect/backfill_05b_ledger.py --plan collect/ledger/05b_plan_stage2770.json --check
# 收口文档 / 判类证据幂等
python3 collect/adjudicate_05b.py --check
# 门禁：账本 vs 计划层数（差 >1% 直接 FAIL）
python3 -m unittest collect.tests.test_preflight_dispatch.LedgerPlanConsistency
python3 collect/preflight_dispatch.py --stage 05b --offline --no-write
```

- **W33-013** 已从「未修/尾巴」改为「已修 + 已补账」。
- **W33-041** 新增：preflight **D14** 通用检测 —— 阶段账本 `layers_n` 与 `plan.layers_n`
  差 **>1%** 直接 FAIL。补账前 2,325 vs 2,770 会红；补账后 2,770 vs 2,770 绿。
- 445 层的补账证据：`analysis/05b-backfill-2026-10-31.json`（445 层逐层 rows/units/packages/
  Release 资产与 checkpoint sha256），只读、可重放。
