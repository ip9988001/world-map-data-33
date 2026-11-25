# 第 8 步 · 账实对账清理（v4 · muse-000247）

> **一句话（2026-11-25 收口版）**：3,550 层「Release 有载荷、本地无目录」**已全部落地**（40.34 GB / 40,341,427,040 B 载荷 + 逐层 `ledger.json`），
> 五数对账 **ok 3,535 + ok_index_stale 14 + checkpoint_unit_rows_missing 1 + mismatch 0 + 半截 0 = 3,550**；
> 对账 after：`local_absent_assets_exist_not_downloaded` **3,550 → 0**，`local_ok_payload_present` **0 → 3,550**，`local_ok_readable` 105 未动，`local_absent_upstream_no_assets` 54（join 54==54 ✓）。
> 三条必须先说清的口径：① **Release 载荷不是本地分表形态**（part 包原样落盘，分表要 field-map，而 field-map 不覆盖这 3,550 层，`schema/` 禁改）；
> ② **CSV 的 `release_payload_n` 大面积陈旧**（14 层实测 tar 数 > CSV，其中 6 层是 tag 内重复上传同名 part）；
> ③ **54 层的结论是上游健在、根本没派采集**（0 层「上游整层空」、0 层「账本虚记」）。

- 工作树 `/data/workspace/wmd-step8-reconcile`，分支 `feat/step8-reconcile-20261125`，基线 **b671f9d**（= origin/main，PR #56 merge）
- dist 复用 `/data/workspace/world-map-data-33/dist/intake-full`（数据盘，不走 git）
- 边界：**没动** `collect/`、`schema/`、`engine/`、`registry/`、`docs/`、网站、Release（未发任何 tag）、
  `analysis/full-inventory-20261124/`、`analysis/combo-step*/`、`analysis/grading-rerun-20261125/`；无 main 直推、无 PR 合并

---

## 0. 结论摘要（先给数，再讲过程）

| 项 | 数 |
|---|---|
| 3,550 层里**已拉齐**（part 数达标 + gzip 可读 + ledger 自洽） | **3,550 层**（ok 3,535 + ok_index_stale 14 + checkpoint_unit_rows_missing 1） |
| 已落地字节 | **40,341,427,040 B ≈ 37.6 GiB**（三阶段合计：11.23 GiB + 21.6 GB + 10.5 GB，与 `final-tally.json` 的字节总数逐位对得上） |
| `local_absent_assets_exist_not_downloaded` | 3,550 → **0** |
| `local_ok_payload_present`（新增类） | 0 → **3,550** |
| `local_ok_readable`（原 105） | **105 → 105**（一个字节没动） |
| `local_absent_upstream_no_assets`（54） | **54 → 54**，每层在 B 表有原因行（join 校验 54==54 ✓） |
| `local_dir_no_assets`（半截目录） | **16 → 0**（续跑把半截目录全部重下） |
| 行级实测 | 抽样 **427 层 = 12.0%** `zcat\|wc -l` vs checkpoint `unit_rows`：425 相符；2 层不符均为**采集侧 checkpoint 覆盖不全**（1 层 `unit_rows=0`、1 层只覆盖部分 unit），非数据缺失（§2.4） |
| 54 层原因分桶 | `upstream_offline 35 / ledger_overclaimed 13 / id_drifted 6 / upstream_empty 0`（细分见 §3.2） |
| 「账本 ok 却本地零资产」3 层 | **3 层全是 54 层的子集** → muse 的 3,607 是把子集重复加了，实际分母 **3,709 = 3,550 + 54 + 105** |

---

## 0.1 断点续跑记录（muse-000252）+ 收口五数（muse-000253）

### 0.1.1 三段跑的时序（都以 `pull.log` 的 `[n/3550]` 序号为准）

| 段 | 起（UTC） | 止（UTC） | 序号区间 | 层数 | 字节 | 平均速率 | 备注 |
|---|---|---|---|---:|---:|---:|---|
| 首跑 | 06:39:55 | 07:45:23 | 1–3,096 | 3,096 | 11.23 GiB | ≈2.9 MB/s | 带宽硬限，正常收工（不是崩） |
| 续跑 A | 08:09:09 | 10:09 | 3,090–3,531 | 442 | 21.6 GB | ≈3.0 MB/s | 长尾大层，seq 3,549–3,550 两个 BIG 层未轮到时被收尾 |
| 空转 | 10:09:35 | 10:09:35 | — | 0 | 0 | — | **热改 `pull_layers.py` 打坏脚本** → 起动即 `NameError: name 'BIG_LAYER_ASSETS' is not defined` 秒退（不是网络/磁盘/被杀） |
| 续跑 C | 10:10:09 | 11:21:10 | 3,532–3,550 | 19 | 10.5 GB | ≈2.5 MB/s | 收工 `[done]`，`stop_reason=""`，`free_gb=39.4` |

续跑合计：**08:09:09 → 11:21:10 = 192 分钟，461 层 / 32.1 GB**，平均 ≈2.79 MB/s（仍是带宽硬限 ≈2.8–3.4 MB/s，并发不提速）。
续跑入口打印的跳过证据：`[resume] 已跳过 3531 层（目录 part 数达标 + ledger.json status=ok 且 part_files 一致，双证据）`，
即**没有一层被「跳过」而不满足双证据**；半截目录（9 个有 part、7 个只有 tar/checkpoint）全部重下。

### 0.1.2 五数对账（分母 3,550 = `local_absent_assets_exist_not_downloaded` 全集，以磁盘为唯一事实）

| # | 类 | 层数 | 判据 |
|---|---|---:|---|
| 1 | `ok` | **3,535** | ledger `status=ok` 且 磁盘 part 数 == ledger.part_files |
| 2 | `ok_index_stale` | **14** | 实测 tag 内 `*-u*.tar.gz` 数 **>** CSV `release_payload_n`（CSV 是 2026-11-20 shallow 索引，记少了） |
| 3 | `checkpoint_unit_rows_missing` | **1** | `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0`：844 片 / 2,875 MB 全下齐、gzip 可读，但采集侧 `checkpoint.json` 的 `unit_rows=0`（账本缺陷，实测行数 42,062,000） |
| 4 | `mismatch`（真缺片/行数不符） | **0** | — |
| 5 | 半截目录（part 不达标 / 无 ledger / ledger 与磁盘不一致） | **0** | — |
| | **合计** | **3,550** | 3,535 + 14 + 1 + 0 + 0 = **3,550** ✓ |

逐层证据：`final-tally.csv`（每层 class / ledger_status / part_files / csv_payload_n / bytes），汇总 `final-tally.json`。
**不用 `pull-final.json: layers_in_manifest`（3,396）当分母**：manifest 分片是「累积重写」，末轮 19 条把 `00017` 覆盖，首跑尾部 96 条也没进分片 —— 这个数天生小于 3,550（§7 注）。


---

## 1. 小样先跑：三件必须先验证的事（全部有落盘证据）

小样取 3 层：`payload_n` 最少两片 + **payload 最多的那层**（CSV 说 67 片 / 6.69 GB）。
结果写 `sample-validation.json`，过程在 `pull.log`。

| 样本 | 层 | 结论 | 证据 |
|---|---|---|---|
| 1 | `rvices_Hosted_Address_Points_of_Indiana_2021_FeatureServer_1` | **`ok_index_stale`** | 实测 **65 片 / 262,550,165 B**，CSV 说 **5 片 / 267,791 B** → CSV 陈旧（差 98,000%）；part 65 个全 gzip 通过、行数 **3,146,263 == checkpoint unit_rows 3,146,263** |
| 2 | `arcgis_rest_services_WillCounty_AddressPoint_FeatureServer_0` | **ok** | 1 片 / 13,700,341 B（CSV 13,700,939，偏差 0.0%），7 个 part、行数 **315,460 == 315,460** |
| 3 | `s_Points_from_National_Address_Database_view_FeatureServer_0`（payload 最多） | **未完成** | 实测该 tag 有 **68 片 / 4,596,978,413 B**（CSV 说 67 片 / 6.69 GB），单层就要 ≈27 分钟纯传输；为保证主跑带宽，小样阶段中止，未写入结论 |

### 1.1 校验口径的第一条结论：载荷 ≠ 本地层目录形态

`<layer>-uNNNNN.tar.gz` 解开是 `part-uNNNNN-NNN.ndjson.gz`（信封行：`add_num/st_name/st_suf/…/src_layer/raw`），
**不是**本地目录里的 `addr.<layer>.ndjson.gz` / `aux_parcel.` / `aux_street.` / `aux_addr_nohouse.` / `reject.`。

要还原分表必须过 intake 的 `LayerMapper`，而 `schema/field-map-v2.json` **只有 2,364 层**（就是已经 intake 过的那批），
**这 3,550 层一条 fmap 都没有**（`fmap` 覆盖检查：3,550 层缺 3,550 条）。重建 fmap 需要逐层价值分布画像（`analysis/out/*.json`，现盘 2,381 份也只覆盖旧批），
而 `schema/` 本单禁改。

→ 所以本轮落的是**载荷原样**（`form=payload-part-passthrough`），并单列 `local_ok_payload_present` 类，
**不冒充** `local_ok_readable`（后者要求分表可读）。这是本单对派单预期的一处**明确偏离**，不给「已补齐」的假象。

### 1.2 第二条结论：网络被硬限在 ≈2.8 MB/s（这是唯一瓶颈，也是首跑没一次跑完的原因）

| 测法 | 结果 |
|---|---|
| 单连接 `gh release download`（1.4 GB / 4 片） | 6m54s → **3.4 MB/s** |
| 4 个 tag 并发（210 MB） | 64s → **3.3 MB/s**（并发不提速） |
| 6 个资产并发 curl（53.2 MB） | 15.8s → **3.4 MB/s**（同上） |
| 主跑实盘增速（`du` 差分，60 秒窗口） | **2.8 MB/s ≈ 165 MB/分钟** |

17.4 GiB ÷ 3.4 MB/s ≈ **87 分钟纯传输**（还要叠加每层 `gh` 的资产枚举/逐资产开销，实测每层 5–240 秒）。
180 分钟窗口里还要做 B/C/D 与报告，因此本轮**必然**只能完成一部分 —— 这不是"再跑就跑完了"的估算问题，是硬管道。

---

## 2. A · 拉层补齐（3,550/3,550 全量完成）

### 2.1 机制（`pull_layers.py`）

逐层：`gh release download <tag> -p '*-u*.tar.gz' -p '*-checkpoint.json'` → 解包到 `layers/<layer>/` → **立刻删该片 tar.gz**
（峰值磁盘 = 本层一份载荷；`payload_n > 20` 的层串行跑）→ 四道校验 → 写 `ledger.json` + manifest 分片（每 200 层）。

- **磁盘护栏**：每层前后查 `statvfs`，可用 <15 G 立即停手（`stop_reason=disk_guard`）。全程**未触发**；最低点 39.4 G（§6）。
- **断点续跑**（2026-11-25 muse-000252 加固）：`dir_state()` 判完成要**双证据** —— ① 目录里 `part-u*.ndjson.gz` 数 ≥ CSV 载荷数 ② `ledger.json` 在且 `status ∈ {ok, ok_index_stale, bytes_anomaly, checkpoint_unit_rows_missing}` 且 `part_files == 磁盘实际 part 数`。缺一即重下（半截目录因此全部重做，未把「跳过」当「完成」）。
- **分片续写**：manifest 分片号从已有最大值 +1 起（本轮 00015/00016/00017），**未覆写 00000–00014**。
- **失败三分类** `asset_gone / corrupt / mismatch`，单层失败记账继续跑，不因单层异常中断整批。

### 2.2 四道校验（逐层写 manifest / ledger）

| 校验 | 口径 | 最终统计 |
|---|---|---|
| ① 资产数 | tag 内 `*-u*.tar.gz` 数 vs CSV `release_payload_n` | 实测 > CSV（63/65、7/1、68/67…）→ 判 **`ok_index_stale`**，记异常不记失败；实测 < CSV → `mismatch`（**0 层**） |
| ② 可读性 | 每个 part `gzip -t` 通过 | 全部通过（0 层 corrupt；唯一一次 tar 报错在续跑 C 重下后 ok） |
| ③ 行级 | 抽样层 `zcat \| wc -l` == checkpoint `unit_rows` 合计 | 抽样 **427 层 = 12.0%**：425 层相符，2 层不符且原因已定性（§2.4） |
| ④ 字节 | 下载字节 vs CSV 快照字节，偏差 >20% 记异常 | 仅在 ①资产数一致时可比（CSV 陈旧层记 `bytes_baseline=unavailable`）→ `bytes_anomaly` **0 层** |

> **口径诚实性**：行级实算是 **427 层抽样（12.0%）**，不是全量实测。抽样构成为主跑 `--do_rows`（含字节最大 10 层）+ `rowcheck_sample.py` 补抽 88 层（全 pass）。
> 主跑那批里 2 层不符是**采集侧 checkpoint 覆盖不全**，不是数据缺行（逐层说明见 §2.4）。

### 2.3 失败与异常清单

见 `pull-failed.csv`：最终 **15 行**（14 `ok_index_stale` + 1 `checkpoint_unit_rows_missing`），**`mismatch` / `corrupt` / `asset_gone` 均为 0 行**。

### 2.4 15 条非 ok 层逐条复核（muse-000253 要求：逐条贴实测值，不许概括）

判据只有两条：实测 tar 数 **>** CSV → `ok_index_stale`；实测 **<** CSV → 真 `mismatch`。另加 muse 点名的 1 层单列。

| # | 层 | 实测 tar / CSV | 盘上 part | 行数（实测/声明） | 判定 |
|---|---|---|---:|---|---|
| 1 | `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | 5 / 5（资产数一致） | **844** | **42,062,000 / 0** | **`checkpoint_unit_rows_missing`**（采集侧 `unit_rows=0`，东西全下齐、gzip 可读——账本缺陷，不是 mismatch） |
| 2 | `s_Points_from_National_Address_Database_view_FeatureServer_0` | **68 / 67** | **816**（4,384 MB） | **39,875,268 / 39,875,268**（相符） | `ok_index_stale`（muse 点名核实：CSV 少记 1 片，行数完全对得上） |
| 3 | `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | 7 / 3 | 112 | 5,573,001 / 5,573,001 | `ok_index_stale` |
| 4 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0` | 6 / 3 | 6 | 279,299 / 279,299 | `ok_index_stale` |
| 5 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 6 / 3 | 8 | 252,475 / 252,475 | `ok_index_stale` |
| 6 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 5 / 1 | 352 | **5,985,871 / 187,871** | `ok_index_stale`（行数不符：checkpoint 只覆盖 1 个 unit，实测反而多 5.8 M 行） |
| 7 | `cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` | 2 / 1 | 2 | 81,784 / 81,784 | `ok_index_stale` |
| 8 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 2 / 1 | 2 | 17,326 / 17,326 | `ok_index_stale` |
| 9 | `qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` | 4 / 2 | 4 | 181,471 / 181,471 | `ok_index_stale` |
|10 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | **3 / 1** | 1 | 23,246 / 23,246 | `ok_index_stale`（tag 内 3 份**同名 part** 重复上传，解包按字典序后者覆盖，保留规范名 `<layer>-u00000.tar.gz`） |
|11 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 3 / 1 | 1 | 9,862 / 9,862 | 同上（重复上传同名 part） |
|12 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 3 / 1 | 1 | 23,241 / 23,241 | 同上 |
|13 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 3 / 1 | 1 | 14,470 / 14,470 | 同上（已 `tar tzf` 实证：3 个 tar 内都是 `part-u00000-000.ndjson.gz`） |
|14 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 2 / 1 | 1 | — / —（checkpoint 无 unit_rows） | 同上 |
|15 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 3 / 1 | 1 | 9,628 / 9,628 | 同上 |

> 重复上传同名 part 的实证（#10–#15 同型）：
> `gh release download <tag> -p '*-u*.tar.gz'` 拿到 `<lid>-f45034968098-u00000.tar.gz`、`<lid>-r72557cf3-u00000.tar.gz`、`<lid>-u00000.tar.gz`，
> `tar tzf` 三个都是 `part-u00000-000.ndjson.gz` → 实测 **tar 数 > CSV** 成立，gzip 可读，行数与 checkpoint 逐位相符。
> 故这 6 层是 **CSV 索引 + 重复上传**两重噪声，不是拉取失败。

**这些重分类不洗白任何真缺失**：`mismatch` 行最终为 0，是因为没有一层的实测 tar 数少于 CSV；只要少一片就会留在 `pull-failed.csv`（上一轮 9 条 `mismatch` 全部属于上述两类之一，无一条是真缺片）。

---

## 3. B · 54 层「上游无资产」逐层原因表（`upstream-no-assets.csv`）

每层一行：`layer / stage / ledger_declared / ledger_rows / ledger_status / url / 当前上游实测（http_meta、http_count、count、层名、err 原样）/ conclusion / conclusion_detail / suggestion`。
上游**只探一次**（`?f=json` + `returnCountOnly=true`），共 108 次请求，实测 523 秒（与拉层抢带宽）。**不改账本、不改数据。**

### 3.1 四类计数

| conclusion | 层数 | 含义 |
|---|---:|---|
| `upstream_offline` | **35** | 上游现在拿不到（HTTP 非 200／`?f=json` 报 error／count 查询失败） |
| `ledger_overclaimed` | **13** | 上游可达且有 count，但 Release 里 0 资产 —— 细分见 §3.2 |
| `id_drifted` | **6** | 上游 count 与账本 declared 不符（同一 URL 两次快照不一致） |
| `upstream_empty` | **0** | **没有一层是"上游整层空"** |

### 3.2 `ledger_overclaimed` 必须拆开说（按 dispatch 要求写清"整层空"还是"账本虚记"）

| conclusion_detail | 层数 | 说明 |
|---|---:|---|
| `declared_but_unreachable` | 14 | 账本有 declared，但上游实测拿不到（不是空，是摸不到） |
| `unreachable` | 21 | 账本无 declared，上游也摸不到 |
| `never_collected` | **4** | 上游 count **与账本 declared 一致（±5%）** → 上游健在、行数对得上，**Release 里根本没有该层资产 = 采集从未执行/被跳过** |
| `count_differs` | 6 | 上游 count 与账本不符（id 漂移） |
| `no_declared` | **9** | 账本 declared 为空/0，上游却有数（1,3120–277,252 行）→ **账本没记，不是虚记** |
| `overclaimed` | **0** | 真·虚记（上游明显少于账本）一层都没有 |

> 也就是：派单担心的"有 declared 却零资产 = 账本虚记"**实测为 0 层**；有 declared 的 24 层里，
> 4 层是上游完全对得上但采集从未跑过，14 层是上游现在摸不到。**结论：没有账本虚记，只有没派的活和摸不到的上游。**

---

## 4. C / D · 3 层归属 与 对账 v2

### 4.1 「账本 ok 却本地零资产」的 3 层（`zero-asset-3.csv`）

条件用三条同时判：`ledger_status = ok` + 本地 0 字节 + **Release 也 0 载荷**（不加最后一条会把 3,550 层全扫进来）。

| layer | stage | ledger_declared | 归属 |
|---|---|---:|---|
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 04b | 3,618,012 | **54 层的子集** |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | 04b | 2,220,021 | **54 层的子集** |
| `_cog_server_rest_services_test_Address_Point_FeatureServer_0` | 05b | 9,046 | **54 层的子集** |

**结论（照实说）**：这 3 层是 54 层的子集，**不是独立的第四类**。muse 报的 3,607（=3,550+54+3）把子集重复加了一次；
正确分母是 **3,709 = 3,550 + 54 + 105**（与 v1 冻结口径、`docs/4-7-TOTAL-2026-10-31.md` 一致）。
这 3 层的上游实测都是 `count == declared`（3,618,012 / 2,220,021 / 9,046 都对得上）→ **账本没写错，是采集没跑**。

### 4.2 对账 v2（`local-vs-ledger-reconcile-v2.csv`，列结构与 v1 的 18 列一致）

`reconcile_v2.py` = `analysis/full_inventory_reconcile.py` 的同一逻辑 + `--outdir` + 认得两种层目录形态（见 §1.1）。
**没有写、也没有改 `analysis/full-inventory-20261124/` 下任何文件。**

| 类别 | before | after | 净差 | 说明 |
|---|---:|---:|---:|---|
| `local_ok_readable`（分表可读） | 105 | **105** | 0 | 一个字节没动 |
| `local_ok_payload_present`（本轮新增：载荷可读未分表） | 0 | **3,550** | +3,550 | §1.1 的形态差异；含 14 层 `ok_index_stale` + 1 层 `checkpoint_unit_rows_missing`（见 §0.1.2） |
| `local_absent_assets_exist_not_downloaded` | 3,550 | **0** | **−3,550** | **已归零** |
| `local_absent_upstream_no_assets` | 54 | **54** | 0 | 每层有 B 表原因行（join 54==54 ✓） |
| `local_dir_no_assets`（半截目录） | 16 | **0** | −16 | 续跑把半截目录全部重下 |
| **合计** | **3,709** | **3,709** | 0 | 分母不变（3,550 + 54 + 105） |

复核命令（三步可重跑，均纯离线）：`finalize_pull.py`（非 ok 重分类）→ `relabel_stale.py`（把 `ok_index_stale` / `checkpoint_unit_rows_missing` 回写进逐层 `ledger.json`）→ `reconcile_v2.py` → `join_check.py`；五数由 `final_tally.py` 扫磁盘算出。
变动层清单（三层 map）：`reconcile-moves.csv`（每行 layer / class_before / class_after / reason）。

### 4.3 join 校验（残留层 == B 表行数）

```
after 的 local_absent_upstream_no_assets = 54
B 表（upstream-no-assets.csv）= 54 行
join: 54 == 54 ✓，且 54 层 layer id 逐条一一对应（无多、无少）
```

---

## 5. 速率与耗时的实盘记录（带宽硬限是唯一瓶颈）

| 约束 | 实测 | 后果 |
|---|---|---|
| 网络出口 | ≈2.8–3.4 MB/s（4 种测法一致，并发不提速） | 40.34 GB 载荷纯传输就需 ≈4 小时 |
| 每层 `gh` 开销 | 5–2,900 秒/层（资产枚举 + 逐资产下载；大层 844–95 片可达 40+ 分钟） | 层数不是瓶颈，**字节**才是 |
| CSV 载荷数陈旧 | 63/65、7/1、68/67 这类层大量存在，6 层 tag 内重复同名 part | ①校验不能直接判失败，需要 `ok_index_stale` 口径 |
| 实盘 | 首跑 155 分钟 / 3,089 层 / 11.23 GiB（≈2.9 MB/s）；续跑 192 分钟 / 461 层 / 32.1 GB（≈2.79 MB/s） | 全程跑在带宽上限，无空闲损失 |

**续跑命令（若将来再需要）**：`python3 analysis/step8-reconcile-20261125/pull_layers.py --concurrency 6`
（双证据跳过已完成层、序号/分片续接、磁盘护栏 15 G）。本轮已 3,550/3,550 试完，**无需再跑**。

---

## 6. 磁盘

| 时点 | `/data` 可用 | dist/intake-full |
|---|---:|---:|
| 开工（首跑） | 82 G | 55 G（layers 14 G） |
| 首跑收工 | 64 G | 67 G |
| 续跑最低点 | 39.4 G | — |
| **收口** | **40 G** | **92 G**（layers 52 G，5,914 个层目录） |

净耗 ≈42 G（40.34 GB 载荷已落盘）。护栏阈值 15 G **未触发**；临时目录 `/data/tmp/step8pull` 每层结束即清。

---

## 7. 产物清单（全部在 `analysis/step8-reconcile-20261125/`）

| 文件 | 内容 |
|---|---|
| `pull_layers.py` / `pull.log` | 拉层驱动 + 逐层日志（序号/结果/part/字节/耗时） |
| `pull-manifest-shard-00000..00017.json` | manifest 分片（layer/tag/assets_n/part_files/bytes/checks/result） |
| `final_tally.py` / `final-tally.json` / `final-tally.csv` | **五数权威源**（扫磁盘，每层一行 class/ledger_status/part_files/csv_payload_n/bytes） |
| `rowcheck_sample.py` / `rowcheck-extra.json` / `rowcheck.log` | 行级抽样补到 12.0%（补抽 88 层，全 pass） |
| `finalize_pull.py` / `pull-failed.csv` / `pull-final.json` | 非 ok 层重分类（`ok_index_stale` / `checkpoint_unit_rows_missing` 单列） |
| `relabel_stale.py` / `relabel-stale.json` | 把重分类结果回写逐层 `ledger.json`（只动 15 层，真 mismatch 不洗白） |
| `pull-summary.json` | 最后一次 pull 进程汇总（19 层那轮）；`pull-tally.json` 是**首跑中途快照（3,089）**，终值只认 `final-tally.json` |
| `upstream_probe.py` / `upstream-no-assets.csv` / `upstream-no-assets-summary.json` | B 表（54 层逐层原因 + 分桶） |
| `refine_b.py` | 给 B 表补 `conclusion_detail`（纯离线） |
| `zero-asset-3.csv` | C 表（3 层，已核实为 54 的子集） |
| `reconcile_v2.py` / `local-vs-ledger-reconcile-v2.csv` | 对账 v2（18 列沿用 v1） |
| `reconcile-before-after.csv` / `reconcile-moves.csv` / `join-check.json` | 四类前后对照 + 变动层清单 + join 校验 |
| `REPORT.md` | 本文件 |

> **manifest 分片的两个坑（自行记下，别拿它当分母）**：① 每片写的是「到目前为止的全部记录」（累积），不是增量；
> ② 末轮 19 条把 `00017` 覆盖成 19 条，首跑尾巴 96 条也没进分片 → `pull-final.json: layers_in_manifest` 永远小于 3,550（现为 3,396）。
> 收账只认磁盘（`final_tally.py`）与 `ledger.json`。另外小样文件 `sample-validation.json` 已不在盘上（未提交前被后续非 `--sample` 运行覆掉），
> 小样 3 层的证据改以 `pull.log` 第 6–7 行的 `[sample n/3]` 行为准（第 3 层为保带宽中途 kill，如实在日志里缺）。

---

## 8. 未做 / 待办（不糊）

| 项 | 状态 |
|---|---|
| 3,550 层的**全量**拉取 | **已完成**（3,550/3,550，40.34 GB，五数对账见 §0.1.2） |
| `local_absent_assets_exist_not_downloaded` 归零 | **达成：3,550 → 0** |
| 3,550 层 intake **分表** | `unavailable`：field-map 不覆盖这 3,550 层（§1.1），需先补逐层价值分布画像；`schema/` 本单禁改。属**另一单**，不在本轮交付内 |
| 行级抽样 ≥10% | **达成 12.0%**（427 层 / 3,550）；其中 2 层不符已定性为采集侧 checkpoint 覆盖不全（§2.4） |
| 字节最大 10 层的行级核对 | 主跑 `--do_rows` 已强制包含（含 68 片 / 4,384 MB 那层，行数 39,875,268 逐位相符） |
| 54 层里 21 层「上游摸不到」的再确认 | 只探 1 次/层（派单要求），未做多时段复核 |
| 小样第 3 层（payload 最多） | 当时为保带宽中途 kill；该层即 `s_Points_from_National_Address_Database_view_FeatureServer_0`，本轮已在主跑里完整拉完并做行级实测（§2.4 #2） |
