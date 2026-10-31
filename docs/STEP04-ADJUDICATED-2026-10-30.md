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
- 声明行合计（修正后）：**580135888**
- 实采行合计（不变）：**490821547**

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
| 0 | 4 | 1 | 3 | 0 | 0 |
| 1 | 4 | 1 | 0 | 3 | 0 |
| 3 | 4 | 0 | 0 | 4 | 0 |
| 6 | 4 | 3 | 0 | 1 | 0 |
| **合计** | **16** | **5** | **3** | **8** | **0** |

**结论：取消造成的新增漏账 = 0 层。** 被取消片的 16 层全部能在 272 层账本里找到条目，已完成层的资产都在 Release 上。

逐层明细：

| 层 | 取消时进度 | 账本状态 | 声明 | 实采 | 说明 |
|---|---|---|---|---|---|
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | half | partial | 97,928,946 | 39,875,268 | 取消时半截 |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | done | failed | 6,297,169 | 6,648,000 | 取消前已完成（资产在 Release） |
| `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | half | failed | 5,573,001 | 2,773,122 | 取消时半截 |
| `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | half | failed | 2,485,645 | 2,416,763 | 取消时半截 |
| `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | done | failed | 4,939,912 | 7,816,000 | 取消前已完成（资产在 Release） |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | none | failed | 3,618,012 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | none | failed | 2,220,021 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | none | failed | 1,369,414 | 0 | 取消时 0 行（未开始 / 上游一行未返回） |
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
| ok | 253 | 实采 ≥ 上游当前 returnCount×(1-1%) |
| partial | 5 | 实采 < 上游当前 returnCount×(1-1%) 且 >0 → 定向续采 |
| capped_by_upstream | 0 | 上游改成服务级 token（连 `<api>/0?f=json` 都 499，连探两轮）→ 永远采不到更多；已采行数计入 rows，declared 移出分母记 declared_unverifiable |
| missing | 7 | 上游有数据、本层 0 行 → 必须重采 |
| unverified | 6 | 上游不可达/无响应，本层无数据 → 无法归因（不许当空层） |
| empty | 1 | 上游明确 0 行或服务下线（esri 404） |
| skipped_done | 0 | 计划期已判完成而跳过 |

**failed = 0**（成品账本里不再有「failed」这个状态：每一层要么有资产、要么有明确归因）。

### 3.1 与旧账的差异（逐条）

| 层 | 旧状态 | 新状态 | 旧声明 | 新声明 | 原因 |
|---|---|---|---|---|---|
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | failed | missing | 6,583,495 | 6,585,376 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | failed | missing | 6,583,495 | 6,585,376 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | failed | missing | 6,297,169 | 6,297,169 | 上游当前 returnCount=6,297,169，本层 0 行 → 真缺口，必须重采 |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | failed | ok | 6,297,169 | 6,297,169 | 实采 6,648,000 ≥ 上游当前 returnCount 6,297,169×(1-1%) |
| `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | failed | partial | 5,573,001 | 5,573,001 | 实采 2,773,122 / 上游当前 returnCount 5,573,001（差 50.24%） |
| `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | failed | ok | 4,939,912 | 4,939,912 | 实采 7,816,000 ≥ 上游当前 returnCount 4,939,912×(1-1%) |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | failed | missing | 3,618,012 | 3,618,012 | 上游当前 returnCount=3,618,012，本层 0 行 → 真缺口，必须重采 |
| `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | failed | partial | 2,485,645 | 2,485,645 | 上游不可达（URLError: <urlopen error timed out>）；实采停在 2,416,763 / 声明 2,485,645 |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | failed | missing | 2,220,021 | 2,220,021 | 上游当前 returnCount=2,220,021，本层 0 行 → 真缺口，必须重采 |
| `fn_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | partial | ok | 1,928,880 | 1,254,000 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | failed | unverified | 1,381,118 | 1,381,118 | 上游不可达（URLError: <urlopen error timed out>），本层无数据 → 无法判定，不许当 0 数据 |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | failed | unverified | 1,381,118 | 1,381,118 | 上游不可达（URLError: <urlopen error timed out>），本层无数据 → 无法判定，不许当 0 数据 |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | failed | unverified | 1,369,414 | 1,369,414 | 上游不可达（URLError: <urlopen error timed out>），本层无数据 → 无法判定，不许当 0 数据 |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | failed | unverified | 716,472 | 716,472 | 上游不可达（URLError: <urlopen error [Errno -3] Temporary failure in name resolution>），本层无数据 → 无法判定，不许当 0 数据 |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | partial | partial | 525,371 | 525,381 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | failed | unverified | 388,607 | 388,607 | 上游不可达（HTTP 403），本层无数据 → 无法判定，不许当 0 数据 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | failed | unverified | 368,312 | 368,312 | 上游不可达（URLError: <urlopen error timed out>），本层无数据 → 无法判定，不许当 0 数据 |
| `_arcgis1_rest_services_FLEXMOBILE_Address_Points_MapServer_0` | failed | empty | 367,002 | 367,002 | upstream_service_gone：上游返回 esri 404 / Service not found |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | failed | missing | 302,920 | 303,175 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | failed | missing | 302,920 | 303,175 | 声明值改用上游当前 returnCount（证据：2026-10-30T20:08:38Z） |

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
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | 97,928,946 | 97,928,946 | 39,875,268 | 59.28% | 59.28% | partial |
| `fn_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | 1,928,880 | 1,254,000 | 1,254,000 | 34.99% | 0.00% | ok |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | 525,371 | 525,381 | 479,000 | 8.83% | 8.83% | partial |

计算过程：`新差额 = (上游当前 returnCount − 实采行数) / 上游当前 returnCount`。
其中 NG911 层旧声明 1,928,880 是计划期快照，上游现在就是 1,254,000，正好等于实采 → 差额归零，
这一层不是「没采全」，是**旧声明过期**。

### 3.4 剩余缺口逐层拆解

账本净缺口 = **89,314,341 行（15.3954%）**，由三块构成（加减号都是账本数字，不是估的）：

- 真缺口（`missing` / `partial` / `unverified`，共 23 层）：**+92,491,234**
- `empty` 层的旧声明（上游 0 行，不是缺口）：**+367,002**（1 层；旧声明不该再进分母）
- 已采超出声明的层（上游后来缩水/声明过期）：**−3,543,895**（78 层）

| 层 | 状态 | 声明 | 实采 | 缺口 | 缺口% | 归因 |
|---|---|---|---|---|---|---|
| `s_Points_from_National_Address_Database_view_FeatureServer_0` | partial | 97,928,946 | 39,875,268 | 58,053,678 | 59.28% | **上游有数据但没采全**（半截） |
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | missing | 6,585,376 | 0 | 6,585,376 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | missing | 6,585,376 | 0 | 6,585,376 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | missing | 6,297,169 | 0 | 6,297,169 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | missing | 3,618,012 | 0 | 3,618,012 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | partial | 5,573,001 | 2,773,122 | 2,799,879 | 50.24% | **上游有数据但没采全**（半截） |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | missing | 2,220,021 | 0 | 2,220,021 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | unverified | 1,381,118 | 0 | 1,381,118 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | unverified | 1,381,118 | 0 | 1,381,118 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | unverified | 1,369,414 | 0 | 1,369,414 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | unverified | 716,472 | 0 | 716,472 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | unverified | 388,607 | 0 | 388,607 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | unverified | 368,312 | 0 | 368,312 | 100.00% | **上游不可达**（未验证，不许当 0） |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | missing | 303,175 | 0 | 303,175 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | missing | 303,175 | 0 | 303,175 | 100.00% | **上游有数据但没采**（本层 0 行） |
| `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | partial | 2,485,645 | 2,416,763 | 68,882 | 2.77% | **上游有数据但没采全**（半截） |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | partial | 525,381 | 479,000 | 46,381 | 8.83% | **上游有数据但没采全**（半截） |
| `t01_rest_services_PlatTracker_PT365_PLAT_MAPPING_MapServer_5` | partial | 315,044 | 310,418 | 4,626 | 1.47% | **上游有数据但没采全**（半截） |
| `a261a66abddf0b_rest_services_PublicMaps_Location_MapServer_1` | ok | 427,533 | 427,338 | 195 | 0.05% | - |
| `tawa_ca_arcgis_rest_services_Address_Information_MapServer_0` | ok | 404,911 | 404,751 | 160 | 0.04% | - |
| `rest_services_Maricopa_County_Address_Points_FeatureServer_0@AZ-1` | ok | 2,139,288 | 2,139,242 | 46 | 0.00% | - |
| `pG5Xodq0_arcgis_rest_services_Address_Points_FeatureServer_0` | ok | 377,722 | 377,692 | 30 | 0.01% | - |
| `ricopa_County_Address_Points__Non_Commercial_FeatureServer_0` | ok | 1,406,150 | 1,406,138 | 12 | 0.00% | - |

> 注：`capped_by_upstream` 层不出现在上表（无分母）；它的 0 行已在 `rows` 里。

## 四、口径提醒

- 行数合计仍是 **490,821,547**（本次不采一行数据，只改判定与声明）。
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
  --out collect/04b_ledger.json \
  --audit analysis/04b-cancel-audit-2026-10-30.json \
  --doc docs/STEP04-ADJUDICATED-2026-10-30.md --check
```
