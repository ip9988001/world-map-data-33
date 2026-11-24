# 全量盘点 · 2026-11-24（task `w2-20261124-full-inventory`）

> 只盘点：不融合、不分级、不重写引擎、不动 Release/账本/网站、未起任何 collect run、未直推 main。
> 本文件随 Phase 进度追加；数字全部来自本目录 CSV/JSON，可逐条复算。

## 〇、口径声明（先看这 6 条，后面所有表都按它读）

1. **基线 = 冻结账本 3,709 层**：`git show f836112:collect/{04b,05b,07b}_ledger.json` → 272 + 2,770 + 667。
   ⚠️ 仓内 **现盘** `collect/*_ledger.json` 已被后续重跑覆盖成 272 + 3,307 + 1,103 = **4,682 层**，
   **不能**用来对 3,709；本文件一律用冻结版（与 `docs/4-7-TOTAL-2026-10-31.md` 同日同源）。
2. **F3（只记口径、代码未改）**：NH 只按**州级合并件**计数 —— GRANIT 用 `raw-US-NH-granit-v1` 合并件
   （601,374 行）、TIGER 用 `raw-US-NH-v1` 合并件（5,870,025 行）；两者各自的 11 行里的**县级片不进任何合计**
   （GRANIT 分县 Σ 601,355 ≠ 州级 601,374；TIGER 分县 Σ 与州级逐位相等），**禁相加**。
3. **本地层 ≠ 原始上游行**：`dist/intake-full/layers/*/addr.*.ndjson.gz` 是 **08 去重索引的规范化中间件**
   （29~30 个 canonical 字段 + `src_layer_url`/`src_layer_id`），**不是原始字段名**。
   因此 Phase 2 的字段级表列的是 canonical 字段；原始字段名只能靠 Phase 3 的远程 meta 拿。
4. **抽样口径**：每层**每表**最多 200 行，`denom` = 该层该表**实际**抽到的行数，逐行写死；
   `nonnull_rate = nonnull / denom`；每行都带 `nonnull_rate_basis=sample200`。**精确全表非空率本轮不做**。
5. **行数来源**：层级表的 `rows` 取该层 `ledger.json` 的 `rows_total`（intake 逐层实读记录），
   `rows_source=intake-ledger rows_total`；取不到写 `unavailable`，不估。
6. **远程未采层 = survey 60,694 层 − 已采层**：survey 去重 url 60,693；已采 url 5,881
   （= 3,709 基线 3,631 个可解析 url ∪ 本地 2,351 个可解析 url）→ **未采 54,812 层**（本轮自己算，未沿用任何估值）。

---

## 一、Phase 0：3,709 口径 ↔ 本地可读层 逐层对账

产物：`local-vs-ledger-reconcile.csv`（**3,709 行，一层一行，每行带 `reconcile_class` + `reason`**）

| 类别 | 层数 | 判定证据 |
|---|---:|---|
| `local_ok_readable` | **105** | `dist/intake-full/layers/<layer>/` 存在且至少一个 `*.ndjson.gz` 非空（`tables` 列给出是哪几张表） |
| `local_absent_assets_exist_not_downloaded` | **3,550** | 2026-11-20 的逐层 release 索引（`.release_index.json`，3,986 层）**有该层载荷资产**（`<layer>-uNNNNN.tar.gz`），但 `dist` 无该层目录 → 只有 Release、没落本地 |
| `local_absent_upstream_no_assets` | **54** | 两份本地索引（11-20 逐层索引 / dist 里 1,426-tag 快照）**都查不到**该层，且账本状态非 ok |
| 合计 | **3,709** | 无第四类，无「其他/杂项」兜底 |

### 1.1 那 54 个「上游本无资产」的逐状态拆分（都是账本自己判的）

| 账本状态 | 层数 | 含义 |
|---|---:|---|
| `upstream_unstable` | 21 | 采集时上游连不上/报错 |
| `empty` | 21 | 上游明确 0 行 |
| `unverified` | 5 | 无法归因 |
| `ok` | **3** | ⚠️ 账本说采到了，但两份索引都没有资产 —— 逐层点名见下 |
| `partial` | 2 | 采到一部分 |
| `missing` | 2 | 计划里有、没有产物 |

3 个 `status=ok` 却无资产的层（与 08 文档里点到的 `_cog_server…` 是同一类，另有 2 个新发现）：
- `_cog_server_rest_services_test_Address_Point_FeatureServer_0`（08 文档已记，rows 9,046）
- `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0`
- `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1`（分区层）

⇒ 「账本 rows 是上游计数，不等于下载得到的行」这条再次被证实：**58 层账本有行、本地零资产**（54 + 3 中的重复口径见 CSV，逐行可查）。

### 1.2 `local_absent_assets_exist_not_downloaded`（3,550）按阶段

| 阶段 | 层数 | 说明 |
|---|---:|---|
| 05b | 2,732 | 几乎整阶段未落本地 |
| 07b | 662 | 同上 |
| 04b | 156 | 04b 共 272，其中 105 已可读（占比最高） |

**为什么没下**：intake（2026-10-30）只按当时那份 **1,426 个 tag** 的 Release 快照找资产，
而 08 文档记录的全仓是 **4,908 tag / 10,987 资产** —— 快照不全，于是 1,206 个层目录被写成
`no_assets`（`ledger.json` 里 `err="release 快照里没有该层"`），另有 3,550 层干脆没有目录。

### 1.3 「若要精扫这批层」的成本（【推算】，公式写明）

只有 179 个基线层的资产字节数在本地有记录（dist 快照带 `s` 字段）：Σ 29.55 GB，均值 0.165 GB/层、中位 0.055 GB/层。

- 按**均值**外推 3,550 层 × 0.165 GB ≈ **586 GB**（压缩包，含那个 5.3 GB 的 NAD 全量层，均值被它拉高）
- 按**中位**外推 3,550 层 × 0.055 GB ≈ **197 GB**

**所以现实区间 200–590 GB 压缩包**，解压后按 08 文档实测的 9–24× 膨胀比，磁盘需求 **2–8 TB** —— 本机 `/data` 只剩 110 GB，
**不建议**全量落盘精扫；建议只对「第 3 步要用的候选层」按需拉取。Release 来源：三仓 `collect-step04/05/07-*` 共 3,709 个 tag 里的 3,654 个有载荷资产（11-20 索引）。

### 1.4 本地目录里有 9 个层不在 3,709 基线内

`local_dirs_outside_baseline = 9`（全部可读）：它们是 `@<分区>` 变体目录（如 `…FeatureServer_0@MN-1`、`…@未定位-1`），
属于 08 分区孪生层，账本以 base 层记账 → 不进基线，但 Phase 2 仍扫（逐行可查）。

---

## 二、Phase 1：收第 2 步尾巴

### 2.1 `#9–#15` 七层重探（产物 `dirty-layer-reprobe.json`，共 18 个请求）

| # | 层（截断名） | 本次 count | 账本/快照 | 结论 | 现象 |
|---|---|---:|---|---|---|
| 9 | `paca_wi_us_…_Public_OpenData_MapServer_24`（Waupaca WI） | **28,660** | — / 28,646 | **已恢复** | meta 200、样值 20、`hsn` 门牌 20/20 |
| 10 | `tamonica_gov_server_…_Address_Points_MapServer_0`（Santa Monica） | **57,063** | — / 57,063 | **已恢复** | meta 200、`house`/`street`/`city`/`st`/`zip` 齐 → 标准地址层 |
| 11 | `untywi_gov_vilasgis_…_V4_SiteAddress_MapServer_0`（Vilas WI） | — | — / 48,148 | **仍不稳** | `URLError: timed out`（8s 超时），HTTP 0 |
| 12 | `almbeach_com_…_BaseData_Situs_MapServer_0`（Palm Beach） | **13,120** | — / 13,190 | **已恢复** | `STREET_NO` 20/20、`Address_Full` 齐 |
| 13 | `county_com_…_features_Address_MapServer_0`（Laramie WY） | **45,713** | — / 45,670 | **已恢复** | `bldg_no` 20/20 |
| 14 | `_services_NG911_ReadOnly_…_MapServer_0`（Onslow NC） | — | — / 108,836 | **仍不稳** | `URLError: timed out`，HTTP 0 |
| 15 | `buncombecounty_org_…_opendata_MapServer_2`（Buncombe NC） | — | — / 187,802 | **仍不稳** | `URLError: timed out`，HTTP 0 |

- **收敛情况**：4/7 已恢复且 `count` 与 survey 快照差 ≤0.06%（Waupaca +14、Palm Beach −70、Laramie +43、Santa Monica 完全一致）。
- **仍不稳 3 层**：全部是 **HTTP 0 + 客户端超时**（8 秒），**不是 4xx/5xx**；用更长超时（30s 以上）或换时段可能恢复，
  本轮按纪律不重试放大噪声。⚠️ 提醒：这三层在 2026-11-24 的 survey 快照里 count 非零，说明是**间歇性**不可达，不是下线。

### 2.2 `grouping-v2.json`（URL 唯一键，分母显式 20；原 `grouping.json` 未动）

| 口径 | 分母 | S/A/B/C | full_address | no_zip | no_city | road_only | empty_shell |
|---|---:|---|---:|---:|---:|---:|---:|
| muse 给的基线（= **pre-F1** 规则 + 首样口径） | 20 | 1/9/3/7 | 1 | 5 | 6 | 4 | 4 |
| **本轮实测 pre-F1 复现**（`git show b0a9587:sandbox/rules.py`） | 20 | **1/9/3/7** | **1** | **5** | **6** | **4** | **4** |
| 本轮现规则（F1 已合入 main）+ 首样口径 | 20 | 2/11/2/5 | 2 | 8 | 6 | 1 | 3 |
| 本轮现规则 + 多数票 | 20 | 2/11/2/5 | 2 | 8 | 6 | 2 | 2 |

**结论**：muse 给的基线**能逐位复现**，前提是用 **pre-F1 规则（b0a9587）+ 首条样值定组**。现规则对不上是**F1 的预期结果**，不是 bug：

| 层 | 州 | pre-F1 | 现（F1 后） | 触发别名 |
|---|---|---|---|---|
| Sacramento County, CA Addresses | KS | C / road_only | A / no_zip | `addr_housenumber` |
| City of Boston, MA Addresses | MA | C / road_only | A / no_zip | `addr_housenumber` |
| Address Points and CPNs | MD | B / road_only | S / full_address | `ADDR_NUMBER` |
| Address_1424300337393713068 | AZ | C / empty_shell | C / no_zip | `ADDRESSNUM` |

另：首样口径 vs 多数票只在 **1 层**上不同（PA `…/Q4NxsjNmWBIR4LYH/Address_Points/FeatureServer/0`：首样 `empty_shell`、2/3 样值 `road_only`）→ 两套计数差的那 1 个 `road_only`/`empty_shell` 就是它，未改数迁就。

---

## 三、Phase 2：本地已采层全量离线扫（零网络）

产物：`inventory-local-all.csv`（**2,364 行 = 本地全部层目录**）、`inventory-local-fields.csv`（**36,750 行 = 字段级**）

| 指标 | 值 | 与 Phase 0 自洽性 |
|---|---:|---|
| 扫描目录 | 2,364 | = Phase 0 `local_dirs` |
| 有数据可读 | **1,158** | Phase 0 `local_readable_layers` 同值 ✅ |
| 无可读数据（只有 `ledger.json`） | 1,206 | = intake `no_assets` 1,206 ✅ |
| 层级表行数 | 2,364 | = 1,158 + 1,206，差额逐条可查（`readable` 列） |
| 字段级表行数 | 36,750 | 只对有数据层产生；`(layer,table,field)` 一字段一行 |
| `rows` 合计（来自 ledger.json） | 278,753,145 | 与 intake `intake-progress.json` 的 `rows_total` **完全一致** ✅ |

`usable` 分布（分母 1,158 可读层）：

| usable | 层数 |
|---|---:|
| no_zip | 777 |
| road_only | 104 |
| empty_shell | 1 |
| sampled_zero_rows（可读但抽到 0 行，只有空表/表头） | 276 |
| 合计 | 1,158 |

`addr_core_hit`（`number|street|city|state|zip` 五项是否过半非空）Top：`11110` 418 层（缺 zip）、`11010` 359 层（缺 city+zip）、`01010` 56 层（无门牌）、`01110` 47 层。
**没有一层命中 `11111`** —— 这是 08 索引的已知事实：规范化后的 `zip5` 覆盖率低，所以 `full_address` 在本地层里是 0 层。
这正是「本地中间件不能代替原始层字段」的直接证据（见口径声明第 3 条）。

`source` 分布：`unknown` 1,928 / `step07` 285 / `step04` 151 / `step05` 0 —— 只有 436 层能在 11-20 逐层索引里对上 stage，
`unknown` 的大头正是 Phase 0 里那 1,206 个 `no_assets` 目录（它们没有 tag 可查）。

---

## 四、Phase 3：远程未采层 2 请求极速盘点（**进行中，可续跑**）

- 计划层数 **54,772**（54,812 − 试点已扫 40）
- 每层 2 请求（meta + 20 条样值），count 取不到才补第 3 请求（`requests_n` 逐层记录）
- 并发 8、单层超时：meta 8s / sample 15s；**meta 失败即跳过 sample**（死站单层成本 28s→8s）
- 429/5xx 才退避重试（1 次），超时/断连不重试（避免 3 倍白等）
- 每 200 层落 checkpoint：`inventory-remote-uncollected.shards/shard-NNNNN.ndjson` + 追加 CSV + 刷新 `progress.json`
- 续跑：启动时读所有分片，跳过已完成 url

**实测速率（两段）**：
- 试点 40 层：24.9 s → **1.61 层/s**（这批里死站少）
- 全量开跑后前 240 层：约 8 min → **0.50 层/s**，其中 `unreachable` **177/240 = 74%**
  （survey 是按 url 字母序排的，开头这段恰好是 `URL: https://storymaps…`、`ags1.wgxtreme.com` 这类死站/非 ArcGIS 条目；
  失败层只会花 8 秒 meta 超时即放弃，不再发 sample 请求）

⇒ **按 0.5 层/s 全量要 ≈ 30 小时；按字母序后半段的活站比例（试点段 20% 存活）乐观值仍有 ≈ 9–10 小时**。
两种都属于「20 小时截止线」边缘，因此本轮**不追求跑完**：按 200 层一批落 checkpoint，随时可续，
已扫结果随时可用（`inventory-remote-uncollected.csv` 由分片重建，见 §4.1）。

### 4.1 CSV 与分片的关系（避免「CSV 看起来少了」的误判）

`full_inventory_remote.py` 运行中按 200 层一批**追加**写 CSV；重启/试点重跑会与分片产生偏差。
**分片 `shards/shard-NNNNN.ndjson` 是唯一 source of truth**，`full_inventory_remote_merge.py` 按 url 去重重建整表
（本轮已跑一次：240 行 = 试点 40 + 首批 200，`requests_n` 合计 361，`usable`：unreachable 177 / empty_shell 53 /
road_only 8 / full_address 1 / no_zip 1）。

---

## 五、下一轮建议（按性价比排序）

1. **先别全量落盘**：3,550 层要 200–590 GB 压缩包 / 2–8 TB 解压，本机只剩 110 GB。建议只对「第 3 步候选」拉层（按 URL 直取，不走 Release）。
2. **补一份完整 release 快照**（`gh api` 全量 4,908 tag）→ 可把 3,550 层从「未下载」进一步细分为「有分片/只有 merged/只有 checkpoint」，并把 1,206 个 `no_assets` 假阴性纠正。
3. **Phase 3 跑完后**：54,812 层里能用地址五要素的层会成为「未采候选池」，可与 3,709 已采层做 URL 去重，直接给第 3 步定采集通道。
4. **本地中间件不要当原始层用**：要原始字段名，必须走 Phase 3 的 `?f=json` 或按需拉分片；`zip5` 缺失是规范化口径问题（08 索引只在 addr 表里尽力补），不是上游没有。
5. **7 个脏层**里 3 个（Vilas / Onslow / Buncombe）建议下次探针用 60s 超时 + 2 次换时段，别用 8s 就判死。


> Phase 3 提交时点快照：已扫 **240** 层（分片行数），计划 54,772，剩余 54532；作业仍在后台运行，checkpoint 可续。
