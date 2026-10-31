# 04b 判定修正 + 取消审计（2026-10-30）

> 本文由 `collect/adjudicate_04b.py` 生成（`--check` 可验证字节一致），数字全部来自
> `collect/ledger/step04b_rebuilt.json`（Release 资产重建）+ `analysis/04b-upstream-evidence-*.json`
> （逐层上游 returnCount 实测）。**没有一行是估的**；每处改判都能落到下面某条证据。

## 零、账本口径约定（先看这一节，别读错文件）

| 文件 | 口径 | 真值来源 | 数字含义 |
|---|---|---|---|
| `collect/${STAGE}_ledger.json`（如 `collect/04b_ledger.json`） | **阶段级** | Release 资产 checkpoint + 上游 returnCount 实测 | 跨 run 合并的全阶段账（04b = 272 层） |
| `collect/ledger/${STAGE}_run<id>.json`（如 `04b_run41092912755.json`） | **单 run 级** | 该 run 的片账本（artifact / git） | 单轮跑到哪、哪几片没跑完（04b 那一轮 = 20 层 / 5 片 / 4 片未完成） |
| `collect/ledger/step<NN>b_rebuilt.json` | 阶段级·重建 | 只读 Release 资产反推 | 逐层 declared vs 实采（本文件的上游） |

**两者数字本来就不同，不许混读**：阶段级 272 层回答「04b 到底采了多少」，
单 run 级回答「那一次 run 有几片被掐」。文档引用时必须写明用的是哪一份。

## 一、集合对账（计划分母 vs 账本 vs 上游取证）

- 计划层数（round1 plan）：**272**
- 账本层数（rebuilt）：**272**
- 计划 − 账本：**0**
- 账本 − 计划：**0**
- 声明行合计（修正后）：**475909773**
- 实采行合计（不变）：**500948263**

> 分母口径说明：04b 的候选集由 `steps.json` 的 `select`（row_count>300000 + 标题正则）
> 与 policy 的 `geom_in=[point,multipoint,socrata,na]` 共同决定，实测为 **320 层**；
> 首轮计划 272 层 = 320 层里**尚未采过的**那批（其余 48 层此前已有 `collect-step04-*` 资产）。
> 因此 272 不是「04b 全部应采」，而是「04b 首轮实际要补的」。二者差额 48 层已核过全部有 tag。

## 二、被取消的 4 片（shard 0/1/3/6）逐层落点

取消动作发生在 **2026-10-30T19:16:05Z**（`gh run cancel 41092912755`），
四个 job 的 `completed_at` 为 19:16:32 / 19:16:34 / 19:16:34 / 19:16:59，同一秒级窗口 → 一次统一取消。
取消时该 SHA 的分片脚本**还没有增量落盘**（`f46589a` 之后才有），所以本地没有半截账本；
下面的完成度一律用 **Release 资产**（`step04b_rebuilt.json`）反推，不猜。

| 片 | 层数 | 已完成 | 半截 | 0 行 | 账本缺失 |
|---|---|---|---|---|---|
| 0 | 4 | 3 | 1 | 0 | 0 |
| 1 | 4 | 4 | 0 | 0 | 0 |
| 3 | 4 | 0 | 0 | 4 | 0 |
| 6 | 4 | 3 | 0 | 1 | 0 |
| **合计** | **16** | **10** | **1** | **5** | **0** |

**结论：取消造成的新增漏账 = 0 层。** 被取消片的 16 层全部能在 272 层账本里找到条目，已完成层的资产都在 Release 上。

逐层明细：

| 层 | 取消时进度 | 账本状态 | 声明 | 实采 | 说明 |
|---|---|---|---|---|---|
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | half | partial | 97,928,946 | 39,875,268 | 取消时半截 |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | done | failed | 6,297,169 | 6,648,000 | 取消前已完成（资产在 Release） |
| `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | done | ok | 5,573,001 | 5,573,001 | 取消前已完成（资产在 Release） |
| `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | done | ok | 2,485,645 | 2,489,597 | 取消前已完成（资产在 Release） |
| `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | done | failed | 4,939,912 | 7,816,000 | 取消前已完成（资产在 Release） |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | done | ok | 3,618,012 | 3,618,012 | 取消前已完成（资产在 Release） |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | done | ok | 2,220,021 | 2,220,021 | 取消前已完成（资产在 Release） |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | done | ok | 1,369,414 | 1,369,487 | 取消前已完成（资产在 Release） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | none | failed | 302,920 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | none | failed | 388,607 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | none | failed | 6,297,169 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | none | failed | 1,381,118 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `tync_gov_arcgis_rest_services_GISDV_Base_Map_FeatureServer_1` | done | ok | 347,569 | 347,577 | 取消前已完成（资产在 Release） |
| `UGfPrN7o_arcgis_rest_services_Address_Labels_FeatureServer_0` | done | ok | 320,255 | 553,175 | 取消前已完成（资产在 Release） |
| `ricopa_County_Address_Points__Non_Commercial_FeatureServer_0` | done | ok | 1,406,150 | 1,406,138 | 取消前已完成（资产在 Release） |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | none | failed | 302,920 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |

## 三、判定修正（failed → 有实证的五类）

| 状态 | 层数 | 含义 |
|---|---|---|
| ok | 257 | 实采 ≥ 上游当前 returnCount×(1-1%) |
| partial | 4 | 实采 < 上游当前 returnCount×(1-1%) 且 >0 → 定向续采；或分区重复声明（数据已在 survivor 层，见 3.0.2） |
| capped_by_upstream | 1 | 上游改成服务级 token（连 `<api>/0?f=json` 都 499，连探两轮）→ 永远采不到更多；已采行数计入 rows，declared 移出分母记 declared_unverifiable |
| upstream_unstable | 5 | 可连通、但连续 N 次（默认 3）尝试都超时/503/返回非 JSON 且**无进展** → 重试收益趋零；默认从待采队列剔除，`--force-unstable-layer` 才放回 |
| missing | 1 | 上游有数据、本层 0 行 → 必须重采 |
| unverified | 3 | 上游不可达/无响应，本层无数据 → 无法归因（不许当空层） |
| empty | 1 | 上游明确 0 行或服务下线（esri 404） |
| skipped_done | 0 | 计划期已判完成而跳过 |

**failed = 0**（成品账本里不再有「failed」这个状态：每一层要么有资产、要么有明确归因）。

### 3.0 `capped_by_upstream`：上游改口径导致永久不可采

判据：**服务级** token —— 连 `<api>/0?f=json` 都 499，`returnCountOnly` / `returnIdsOnly` 同样 499，
且连续两轮探测一致（间隔 ≥60s）。这种事 HTTP 状态码是 **200**，token 拦在响应体里，
只看 status code 会把它当「服务正常」→ 于是整层 0 行被当成「我们没采」，日复一日徒劳重采。

| 层 | 已采行数（计入 rows） | declared_unverifiable（移出分母） | 探测 | 证据 |
|---|---|---|---|---|
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | 39,875,268 | 97,928,946 | 2 轮 × 3 端点全 499（2026-10-31T00:46:18Z） | `analysis/04b-token-499-evidence-2026-10-31.json` |

分母口径（本节之后的所有百分比都用这个）：

- `rows` = 500,948,263（全部实采，含 capped 层的 39,875,268）
- `declared` = 475,909,773（**不含** capped 层）
- `rows_verifiable` = 458,452,144（与分母同口径的分子 = rows − capped 行数）
- `gap` = declared − rows_verifiable = **17,457,629 行（3.6683%）**
- capped 层的 declared 另记 `declared_unverifiable` = 97,928,946，**永远不进分母**

### 3.0.1 分母口径硬规矩（2026-10-31 用户定：声明值不是永久分母）

> **1）声明值来自 `layer_plan.csv` 的计划期快照，上游会缩水/删数据/改口径。**
> 实测（本账本口径，可复现）：**80 层实采 > 声明，超采合计 3,547,920 行**
> （rebuilt 口径 81 层 / 3,547,930）；全账 `gap` = 17,457,629 行。拿过期声明当分母，
> 覆盖率系统性失真，而且「按声明 / 按可核实」两个百分比天生不可相减。
>
> **2）对外覆盖一律报两个数，禁止只报一个：**
> - **`按声明分母`** = `rows_verifiable ÷ declared`（declared 剔除 capped 层）
> - **`按可核实分母`** = `rows_verifiable ÷ (已刷新层用上游 returnCount + 未刷新层用旧声明)`，同时剔除 capped
> 两个数必须同屏出现并标注 `declared_refreshed_at`（账本顶层；没刷过就写「未刷新」）。
> 单独抛出任何一个数都算无效报表。
>
> **3）刷新是只读 + 人工点头：**
> ```bash
> # 只读：逐层打 returnCount，出「旧声明 / 新声明 / 实采 / 关系」差异表；不改账本
> python3 collect/adjudicate_04b.py --refresh-declared --json-out analysis/04b-declared-refresh-<date>.json
> # 采纳：写前备份 + 追加 revisions[kind=declared_refreshed]
> python3 collect/adjudicate_04b.py --apply-declared-refresh <json> --declared-confirm I-APPROVE-DECLARED-REFRESH
> ```
> 只对 `ok / missing / partial` 且上游可达的层生效；`capped_by_upstream` / `unverified` / `empty` 一律不碰。
> 当前 `declared_refreshed_at` = 未刷新

### 3.0.2 分区重复声明：`declared` 不许把同一批行数两遍（2026-10-31 用户批准）

判据（与 preflight **D12** 同一条）：同一 base 层的 `@<分区>` 层，若 `Σ declared > 1.5 × 该 base 的上游 returnCount`，说明每个分区都继承了整层声明 —— 分母把同一批行数了两遍。
处置：重复分区的 `declared` 置 null（原值留在逐层 `declared_duplicate_partition`，**不抹数**），
`status` 改 `partial`（数据其实在 survivor 那层），survivor 不动。

| 重复分区 | duplicate_of | 分区 declared（原值） | upstream returnCount | Σ分区 declared | 已采（survivor） | 证据 |
|---|---|---|---|---|---|---|
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | 6,297,169 | 6,297,169 | 12,594,338 | 6,648,000 | `analysis/04b-token-499-evidence-2026-10-31.json` |

- 重复声明合计（移出分母、但数字保留）：**6,297,169 行**；`declared` 现在 = 475,909,773（不含它）

**行侧同源重复（`rows_partition_duplicate_est`）——2026-10-31 用户决定：不改 declared**

> 与上面 NC1Map 那种「重复声明」不同：这类是**不同 host 上的同一份镜像**，而且**两个分区都已经实采了**。把其中一个的 `declared` 置 null 会让分母变小、rows 不变→ 覆盖率虚高，等于自己给自己灌水。所以：**declared 全部保留、分母不动**，只在逐层记「行侧同源重复估算」，计入阶段级 `rows_with_partition_dup`，由 **08 的 3 元组去重**把它们吃掉。

| 层 | declared（不动） | 已采行 | rows_partition_duplicate_est | duplicate_source_layer | 依据 |
|---|---|---|---|---|---|
| `rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-2` | 2,078,539 | 2,139,742 | 2,139,242 | `rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-1` | declared 全部保留、分母不动：置 null 只会让分母变小、rows 不变 → 覆盖率虚高。行侧重复由 08（3 元组去重）吃掉。 |
| `rest_services_hennepin_county_address_points_FeatureServer_0@MN-2` | 480,300 | 480,300 | 481,609 | `rest_services_hennepin_county_address_points_FeatureServer_0@MN-1` | 同上：declared 不动，行侧重复交 08 去重。 |

- 行侧同源重复合计（已含在 `rows_with_partition_dup` 里）：**2,620,851 行**

**两处「不许想当然」**（都实测过）：

1. 分区层的 url 必须回 `collect/layer_plan.csv` 按行序取（`<id>@<state>-<k>`，见 `worker_core._rows_from_csv`）。`layer_index()` 按 id 覆盖，只留最后一行 → 会让人误以为两个分区指向同一个 url（`@未定位-1` → `services.gis.nc.gov`，`@未定位-2` → `services.nconemap.gov`）。
2. 同一 base 的两个分区也可能落在**镜像 host 的同一份数据**上：实测 `Maricopa@AZ-1/-2` = 2,139,242 / 2,139,742 行（差 500），`hennepin@MN-1/-2` = 481,609 / 480,300（差 1,309）—— Σ declared 同样 ≈ 2×，但它们**两个分区都已实采**，把其中一个 declared 置 null 等于抹掉真实已采行。所以本次只改 `NC1Map@未定位-1`（重复分区 0 行、survivor 已采 ≥ 全量，改判无损失）；Maricopa / hennepin 的结论与实测计数写进 `analysis/04b-duplicate-partitions-2026-10-31.json` 的 `reviewed[]`，`rows` 侧的同源重复留给 08 去重时统一处理。

**分区重复采样（同源重复行）**：

- `rows_with_partition_dup` = **2,620,851**（这些行的内容与 survivor 同源，跨层去重时会被 3 元组吃掉）
- `rows_verifiable` = rows − rows_capped − rows_with_partition_dup = **458,452,144**
- 铁律：**分区重复由 08（去重）吃掉；08 之前任何对外覆盖率不许包含重复行**。
  重跑分区不阻止（缺数据不能靠去重补，重复能靠去重吃掉），但账上必须分开记，
  否则覆盖率虚高，且没人知道 08 到底要吃掉多少行。
- 重复采样层：`_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` — rows_including_duplicate = 0（duplicate_of `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2`）
- 重复采样层：`rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-2` — rows_including_duplicate = 2,139,242（duplicate_of `rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-1`；declared 未动：2,078,539）
- 重复采样层：`rest_services_hennepin_county_address_points_FeatureServer_0@MN-2` — rows_including_duplicate = 481,609（duplicate_of `rest_services_hennepin_county_address_points_FeatureServer_0@MN-1`；declared 未动：480,300）

### 3.0.3 `upstream_unstable`：上游不稳，重试收益趋零（重试上限 3 次）

判据（与 preflight **D13**、`collect/attempt_log.py` 同一条）：**可连通、但连续 N 次尝试都超时 / 503 / 返回非 JSON，且没有进展**（每次尝试的 rows 与已有单元包数逐次不变）。
与另外两个「采不到」的状态严格分开：

| 状态 | 判据 | 处置 |
|---|---|---|
| `capped_by_upstream` | 服务级 token（连 `/0?f=json` 都 499，连探两轮） | 永远采不到；declared 移出分母 |
| `unverified` | 连不上（超时 / 403 / DNS 解析失败）且无数据 | 等网络/换出口再试，不许当 0 数据 |
| **`upstream_unstable`** | **可连通，但连续 3 次超时/503/非 JSON 且无进展** | **停手：从待采队列剔除，显式 `--force-unstable-layer` 才放回** |

| 层 | 声明 | 已采 | 尝试次数 | 每次失败类型 | 累计耗时（分钟） | 首次 / 末次 |
|---|---|---|---|---|---|---|
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | 6,585,376 | 0 | 3 | 其它 → 其它 → 其它 | 64.6 | 2026-10-30T17:09:02Z / 2026-10-31T01:48:40Z |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | 6,585,376 | 0 | 3 | 其它 → 其它 → 其它 | 64.6 | 2026-10-30T17:41:40Z / 2026-10-31T01:46:08Z |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 4 | 其它 → 其它 → 其它 → 503 | 21.9 | 2026-10-30T16:59:40Z / 2026-10-31T01:30:24Z |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,312 | 0 | 4 | 4xx → 4xx → 4xx → 4xx | 7.7 | 2026-10-30T17:02:09Z / 2026-10-31T01:27:09Z |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | 303,175 | 0 | 4 | 超时 → 超时 → 超时 → 超时 | 285.0 | 2026-10-30T22:21:16Z / 2026-10-31T03:24:47Z |

合计：**5 层 / 15,223,357 行缺口 / 443.8 分钟尝试时间**。这些层不是「不想采」，是上游给不出：本表就是「我们尽力了」的凭据（逐次类型 + 耗时，不是估算）。

失败类型怎么归的（顺序就是判据，不能换）：先 token(499) → 503 → 非 JSON → 超时 → 4xx → DNS/TLS → other。503 的正文里带 «Wait timeout…»，所以必须排在「超时」之前，否则 503 会被误记成超时。

### 3.1 与旧账的差异（逐条）

| 层 | 旧状态 | 新状态 | 旧声明 | 新声明 | 原因 |
|---|---|---|---|---|---|
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | partial | capped_by_upstream | 97,928,946 | 97,928,946 | 服务级 token：连 `<api>/0?f=json` 都 499（2 轮 × 3 端点全 499，最后一次 2026-10-31T01:08:58Z）→ 本层已无法再采、也无法复核声明；已采 39,875,268 行即全部可得 |
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | failed | upstream_unstable | 6,583,495 | 6,585,376 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | failed | upstream_unstable | 6,583,495 | 6,585,376 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | failed | partial | 6,297,169 | - | 分区重复声明：2 个分区共用同一上游 url，Σ declared = 12,594,338 = 2.00× 上游 returnCount 6,297,169；本层那批行已由 `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` 采到 6,648,000 行 → declared 移出分母，原值保留在 declared_duplicate_partition（不是缺口，也不是改口径凑数） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | failed | ok | 6,297,169 | 6,297,169 | 实采 6,648,000 ≥ 上游当前 returnCount 6,297,169×(1-1%) |
| `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | failed | ok | 4,939,912 | 4,939,912 | 实采 7,816,000 ≥ 上游当前 returnCount 4,939,912×(1-1%) |
| `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | ok | partial | 2,485,645 | 2,485,645 | 上游不可达（URLError: <urlopen error timed out>）；实采停在 2,489,597 / 声明 2,485,645 |
| `fn_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | partial | ok | 1,928,880 | 1,254,000 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | failed | unverified | 1,381,118 | 1,381,118 | 上游不可达（URLError: <urlopen error timed out>），本层无数据 → 无法判定，不许当 0 数据 |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | failed | upstream_unstable | 1,381,118 | 1,381,118 | 上游不稳：连续 4 次尝试失败且无进展（其它、其它、其它、503），累计 21.9 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer yil_gov_traditional_rest_services_addressZipCode_MapServer_0` |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | ok | partial | 1,369,414 | 1,369,414 | 上游不可达（URLError: <urlopen error timed out>）；实采停在 1,369,487 / 声明 1,369,414 |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | failed | unverified | 716,472 | 716,472 | 上游不可达（URLError: <urlopen error [Errno -3] Temporary failure in name resolution>），本层无数据 → 无法判定，不许当 0 数据 |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | ok | ok | 525,371 | 525,381 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | failed | unverified | 388,607 | 388,607 | 上游不可达（HTTP 403），本层无数据 → 无法判定，不许当 0 数据 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | failed | upstream_unstable | 368,312 | 368,312 | 上游不稳：连续 4 次尝试失败且无进展（4xx、4xx、4xx、4xx），累计 7.7 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` |
| `_arcgis1_rest_services_FLEXMOBILE_Address_Points_MapServer_0` | failed | empty | 367,002 | 367,002 | upstream_service_gone：上游返回 esri 404 / Service not found |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | failed | missing | 302,920 | 303,175 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | failed | upstream_unstable | 302,920 | 303,175 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |

### 3.1b 阶段账本的运行级事件（复原 / 合并留痕，只追加不替换）

| 时间 | 类型 | run | 说明 |
|---|---|---|---|
| 2026-10-30T22:34:43Z | stage_ledger_restored | 41121952357 | collect/04b_ledger.json 被单 run 41121952357（定向补采 31 层）的分片汇总覆盖（提交 466a952，layers_n 272→31、shards_expected=3）。已从 466a952^ 的 272 层版本 + collect/ledger/step04b_rebuil |
| 2026-10-31T01:15:56Z | stage_ledger_restored | 41126178216 | collect/04b_ledger.json 被 run 41126178216（22 层计划的 2 片 16 层，head_sha=cb86f42 = 合并前的旧代码）的 merge 直写覆盖。已用**审结快照** collect/ledger/step04b_rebuilt_20261030-committed. |

### 3.2 「13 层上游 0 数据」这个口径被实测推翻

原始交接里把 13 层说成「上游 0 数据」。本机对每层直接打 `returnCountOnly` 的结果是：
**没有任何一层返回 count=0**。

- 13 层上游**活着**并给出非 0 行数（含 SAM_Address_Points ×2、NC1Map@未定位-1、AGOL_NG911、mn_state@未定位-1、rgv911 ×2、NC1Map@未定位-2、NC1Map_Location、LBRS、COTGEO、NG911_Address_Points、NAD）；
- 9 层连不上/超时/403（`unverified`，不能当 0 数据）；
- 只有 1 层是真·服务下线：`_arcgis1_..._FLEXMOBILE_Address_Points_MapServer_0` —— HTTP 200 但 body 是
  `{"error":{"code":404,"message":"Service not found"}}` → 归 `empty`（`upstream_service_gone`）。

所以本次**没有**按「13 层→empty」改，而是按证据分成 `missing`（上游有数、本层 0 行，必须重采）与 `unverified`（上游不可达）。把有数据的层标成 empty 就是改口径凑数，不做。

### 3.3 4 条 partial 的声明重算（不重采）

| 层 | 旧声明 | 上游当前 returnCount | 实采 | 旧差额 | 新差额 | 判定 |
|---|---|---|---|---|---|---|
| `fn_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | 1,928,880 | 1,254,000 | 1,254,000 | 34.99% | 0.00% | ok |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | 525,371 | 525,381 | 525,381 | -0.00% | 0.00% | ok |

计算过程：`新差额 = (上游当前 returnCount − 实采行数) / 上游当前 returnCount`。
其中 NG911 层旧声明 1,928,880 是计划期快照，上游现在就是 1,254,000，正好等于实采 → 差额归零，
这一层不是「没采全」，是**旧声明过期**。

### 3.4 剩余缺口逐层拆解

账本净缺口 = **17,457,629 行（3.6683%）**，由三块构成（加减号都是账本数字，不是估的）：

- 真缺口（`missing` / `partial` / `unverified`，共 15 层）：**+18,017,696**
- `empty` 层的旧声明（上游 0 行，不是缺口）：**+367,002**（1 层；旧声明不该再进分母）
- 已采超出声明的层（上游后来缩水/声明过期）：**−43,423,188**（81 层）

| 层 | 状态 | 声明 | 实采 | 缺口 | 缺口% | 归因 |
|---|---|---|---|---|---|---|
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | upstream_unstable | 6,585,376 | 0 | 6,585,376 | 100.00% | 上游不稳：连续 3 次尝试失败且无进展（其它、其它、其它），累计 64.6 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | upstream_unstable | 6,585,376 | 0 | 6,585,376 | 100.00% | 上游不稳：连续 3 次尝试失败且无进展（其它、其它、其它），累计 64.6 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | unverified | 1,381,118 | 0 | 1,381,118 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | upstream_unstable | 1,381,118 | 0 | 1,381,118 | 100.00% | 上游不稳：连续 4 次尝试失败且无进展（其它、其它、其它、503），累计 21.9 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer yil_gov_traditional_rest_services_addressZipCode_MapServer_0` |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | unverified | 716,472 | 0 | 716,472 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | unverified | 388,607 | 0 | 388,607 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | upstream_unstable | 368,312 | 0 | 368,312 | 100.00% | 上游不稳：连续 4 次尝试失败且无进展（4xx、4xx、4xx、4xx），累计 7.7 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | missing | 303,175 | 0 | 303,175 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | upstream_unstable | 303,175 | 0 | 303,175 | 100.00% | 上游不稳：连续 4 次尝试失败且无进展（超时、超时、超时、超时），累计 285.0 分钟 → 重试收益趋零。默认从待采队列剔除；要再试请显式 `--force-unstable-layer _rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` |
| `t01_rest_services_PlatTracker_PT365_PLAT_MAPPING_MapServer_5` | partial | 315,044 | 310,520 | 4,524 | 1.44% | **上游有数据但没采全**（半截） |
| `a261a66abddf0b_rest_services_PublicMaps_Location_MapServer_1` | ok | 427,533 | 427,338 | 195 | 0.05% | - |
| `tawa_ca_arcgis_rest_services_Address_Information_MapServer_0` | ok | 404,911 | 404,751 | 160 | 0.04% | - |
| `rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-1` | ok | 2,139,288 | 2,139,242 | 46 | 0.00% | - |
| `pG5Xodq0_arcgis_rest_services_Address_Points_FeatureServer_0` | ok | 377,722 | 377,692 | 30 | 0.01% | - |
| `ricopa_County_Address_Points__Non_Commercial_FeatureServer_0` | ok | 1,406,150 | 1,406,138 | 12 | 0.00% | - |

> 注：`capped_by_upstream` 层不出现在上表（无分母）；它的 39,875,268 行已在 `rows` 里。

### 3.5 收口挂账：四类缺口逐类点数（层数 / 行数）

这四类**处置完全不同**，合成一个「缺口」就会天天在同一批层上白跑；所以收口时必须逐类点名，并且同时给三个行数口径（只看层数会被大层骗）。

| 类别 | 层数 | 声明行 | 其中进分母 | 已采行 | 缺口行 | 怎么办 |
|---|---|---|---|---|---|---|
| `capped_by_upstream` | 1 | 97,928,946 | 0 | 39,875,268 | 58,053,678 | 上游要 token，永远采不到；已采多少算多少，declared 移出分母 |
| `upstream_unstable` | 5 | 15,223,357 | 15,223,357 | 0 | 15,223,357 | 连续 N 次超时/503/非 JSON 且无进展 → 停手，不再吃 CI；显式 `--force-unstable-layer` 才放回 |
| `unverified` | 3 | 2,486,197 | 2,486,197 | 0 | 2,486,197 | 连不上（超时/403/DNS）→ 等网络/换出口，不许当 0 数据 |
| `missing` | 1 | 303,175 | 303,175 | 0 | 303,175 | 上游有数、本层 0 行 → 真缺口，还能试但本轮没排上 |
| **合计** | **10** | **115,941,675** | **18,012,729** | **39,875,268** | **76,066,407** | — |

> 合计里的「缺口行」含 capped 的 58,053,678（那部分声明**不在分母**，别拿它算覆盖率）。进分母的四类缺口 = 18,012,729；账本 `gap` = 17,457,629（§3.6），四类比账本**多 555,100** —— 差额是 4 层 `partial` 已经采到的行（它们既不是「0 行」也不是「已停手」，所以不在四类里，但确实抵掉了部分缺口）。

- `capped_by_upstream`（1 层）：`s_Points_from_National_Address_Database_view_FeatureServer_0`
- `upstream_unstable`（5 层）：`cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0`、`s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0`、`yil_gov_traditional_rest_services_addressZipCode_MapServer_0`、`rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5`、`_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0`
- `unverified`（3 层）：`tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63`、`is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0`、`g_rest_services_Basemap_Address_Points_EagleView_MapServer_0`
- `missing`（1 层）：`_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1`

> 口径提醒：「按声明分母」与「按可核实分母」两个覆盖率必须同屏报（见 3.0.1）；四类里的 `capped` 不进分母，其余三类都还在分母里 —— 它们是真缺口，不许隐身。

### 3.6 定稿口径：两个覆盖率 + 四类挂账（同屏，缺一不可）

| 口径 | 分母 | 分子（rows_verifiable） | 覆盖率 | 缺口 | 缺口% |
|---|---|---|---|---|---|
| **按声明分母** | 475,909,773 | 458,452,144 | **96.33%** | 17,457,629 | 3.6683% |
| **按可核实分母** | 476,162,973 | 458,452,144 | **96.28%** | 17,710,829 | 3.7195% |

- 两个数**不可直接相减**：声明值是计划期快照，上游会缩水/删数据/改口径；相差的 253,200 行就是刷新差异。
- 可核实口径的 `declared_refreshed_at` = **2026-10-31T01:03:54Z**（223 层被上游 returnCount 替换）
- 分母与分子同口径：分子 = rows − rows_capped − rows_with_partition_dup = 458,452,144

## 四、口径提醒

- 行数合计仍是 **500,948,263**（本次不采一行数据，只改判定与声明）。
- 其中**同源重复**（分区重复采样）= **2,620,851**，单列 `rows_with_partition_dup`，不进覆盖率分子。
- 剔除 capped 层后的分母 = **475,909,773**，与分母同口径的实采 = **458,452,144**，缺口 = **17,457,629（3.6683%）**。
- 与**不剔除**口径（declared 含 capped）= 580,135,888 行 / 500,948,263 行 / 13.6498% 对照时，差值就是 capped 层的declared_unverifiable 97,928,946：两个百分比**不可直接比较**，引用时必须写明是否剔除。
- 未剔除口径的数字怎么来的：`declared_kept_in_denominator = declared + declared_unverifiable + declared_duplicate_partition`（任何 declared 都不剔，包括分区重复声明），`gap_kept_in_denominator = 它 − rows`（旧口径，分子含 capped 行数与重复行）。
- `docs/STEP04-FULL-2026-10-30.md` 保持 `ledger_rebuild.py` 生成的字节不变（`--check` 依赖它）；
  本文是它的**修正层**，两者冲突时以本文为准，并注明证据出处。
- 修正后的账本是 `collect/04b_ledger.json`（main 侧闸门读的就是这个文件）。

## 五、复现

```bash
python3 collect/verify_04b_upstream.py --out analysis/04b-upstream-evidence-2026-10-30.json
python3 collect/adjudicate_04b.py \
  --rebuilt collect/ledger/step04b_rebuilt.json \
  --evidence analysis/04b-upstream-evidence-2026-10-30.json \
  --plan collect/ledger/04b_plan.json \
  --cancel-plan collect/ledger/04b_round2_plan.json \
  --duplicate-partitions analysis/04b-duplicate-partitions-2026-10-31.json \
  --capped-evidence analysis/04b-token-499-evidence-2026-10-31.json \
  --attempt-log analysis/04b-attempt-log.json --max-attempts 3 \
  --declared-refresh analysis/04b-declared-refresh-2026-10-31.json \
  --out collect/04b_ledger.json \
  --audit analysis/04b-cancel-audit-2026-10-30.json \
  --doc docs/STEP04-ADJUDICATED-2026-10-30.md --check
```
