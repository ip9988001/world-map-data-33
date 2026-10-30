# 04b · `missing 7` 与 `unverified 6` 的取证（2026-10-30）

> 原则：`missing` 必须是「上游有 N 行 / 本层 0 行」的**证据链**，`unverified` 必须是
> **跨时段重复观测**（一次超时只能算噪声）。两者都不许互相顶替，更不许归到 `empty`。

## 一、`missing 7` —— 上游活着，本层 0 行（= 真缺口，必须重采）

证据文件：`analysis/04b-missing-evidence-2026-10-30.json`
方法：`GET <layer_url>/query?where=1=1&returnCountOnly=true&f=json`（只读上游，不采数据）

| 层 | 上游 returnCount（实测） | 账本 declared | 账本 rows | Release 单元包 | 原片结局 |
|---|---|---|---|---|---|
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | 6,585,376 | 6,585,376 | 0 | 0 | 片 7 / failure |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | 6,585,376 | 6,585,376 | 0 | 0 | 片 9 / cancelled |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | 6,297,169 | 6,297,169 | 0 | 0 | 片 2 / cancelled |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 3,618,012 | 3,618,012 | 0 | 0 | 片 1 / cancelled |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | 2,220,021 | 2,220,021 | 0 | 0 | 片 1 / cancelled |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | 303,175 | 303,175 | 0 | 0 | 片 10 / cancelled |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | 303,175 | 303,175 | 0 | 0 | 片 2 / cancelled |
| **合计** | **25,912,304** | **25,912,304** | **0** | **0** | — |

三点结论：

1. **上游全活**，且返回行数与 `layer_plan.csv` 的声明值**逐层完全相等**（7/7 相等，无一例外）
   ⇒ 这 25,912,304 行不是「上游没数据」，是**我们一行都没采到**。
2. **Release 上零资产**（`parts_assets=0`），所以不是「采了没上传」，是**压根没采**：
   6 层挂在 `cancelled` 片（另 1 层在 failure 片），与「片被掐成 cancelled → 整片零痕迹」的历史事故同源。
3. **它们已在跑**：定向 run `41121952357`（feat/gold-intake，20:17 起，未取消）的 plan 是 3 片 × 6 层，
   正好覆盖这 7 层 + 6 层 unverified + `FLEXMOBILE`。跑完按 `ledger_rebuild --check` 复验。

## 二、`unverified 6` —— 3 轮跨时段重测（当前已完成 2 轮）

证据文件：`analysis/unverified-04b-2026-10-30.json`（脚本 `collect/retest_unverified.py --append`，
**间隔 < 30 分钟会被脚本自己拒绝追加**，所以「三次同秒」这种假重测不可能发生）

| 轮次 | 时间（UTC） | 距上轮 |
|---|---|---|
| 轮 1 | 2026-10-30T20:57:34Z | — |
| 轮 2 | 2026-10-30T21:29:08Z | 31.6 分钟 |
| 轮 3 | 待跑（>= 21:59Z） | — |

| 层 | 轮次 | 可达次数 | HTTP / 错误 | 当前判定 |
|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 2 | 0 | 超时 / 超时 | pending_rounds |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 2 | 0 | 超时 / 超时 | pending_rounds |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | 2 | 0 | 超时 / 超时 | pending_rounds |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 2 | 0 | 超时 / 超时 | pending_rounds |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | 2 | 0 | **403 / 403** | pending_rounds |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 2 | 0 | 超时 / 超时 | pending_rounds |

判据（写死在脚本里）：

- 3 轮全不可达 → 账本**保持 `unverified`**，文档写「上游不可达，未验证，非空层」；
- 任一轮可达 → 变 `alive`，按上游行数重判（有数但本层 0 行 ⇒ `missing`，必须重采）；
- 这 6 层**不进缺口分母**，单列「不确定行数区间」：`low = 0`，`high = 5,605,041`
  （声明值之和，来自 `layer_plan.csv`，未经上游确认，只能当上界）。
  ⇒ 84.51% 这类比例既不被它们稀释、也不被它们抬高。
- 另注意 `EagleView` 是**连上但被拒（403）**，与「超时」不是一回事：它说明**服务活着、只是不给我们读**，
  更要留在 `unverified` 而不是 `empty`。

## 三、顺带查出的一处「声明值本身不可验证」

`partial` 里最大的那层 `s_Points_from_National_Address_Database_view_FeatureServer_0`
（账本：declared 97,928,946 / rows 39,875,268 / 缺口 58,053,678）本轮重探上游返回：

```
HTTP 200  {"error":{"code":499,"message":"Token Required","messageCode":"GWM_0003"}}
```

即**该服务现在要 token 才给读**（已不是公开可查层）。这意味着：

- 它的 `declared`（9792.9 万）**无法再复核**，不能继续拿它当「我们欠 58M 行」的证据；
- 也不该因此把它改判 `empty` 或 `ok`（那是拿口径凑数）；
- 正确去向是 `unverified`（上游不可验证），并单列进「不确定行数区间」，等拿到 token 再判。

其余 `partial` 4 层里，两层的声明值已被上游确认（`LBRSforLocator` 5,573,001 = 声明；
`COTGEO` 525,381 = 声明 ⇒ 缺口 2,799,879 / 46,381 是真缺口，且两层都在定向 run 的 plan 里）；
另两层的上游本轮超时（`Ky_911_Site_Structure`、`PlatTracker`），需并入 `unverified` 重测队列。

## 四、04b 是否 `complete` 的判词

**不成立。**

缺口 `89,314,341` 行可拆成四块，缺什么就一目了然：

| 块 | 行数 | 现状 | 补齐条件 |
|---|---|---|---|
| `missing 7` | 25,912,304 | 上游全活、本层 0 行（证据齐全） | 定向 run `41121952357` 跑完并落账 |
| `partial` 可验证缺口 | 2,846,260（LBRS 2,799,879 + COTGEO 46,381） | 上游确认有数、本层短采 | 同上（两层都在定向 run 的 plan 里） |
| `partial` 声明不可验证 | 58,053,678（NAD view 层） | 上游 499 Token Required | 拿到 token 重验声明；否则改判 `unverified`、移出分母 |
| `unverified 6` | 声明 5,605,041（**不计入分母**） | 2/3 轮不可达 | 第 3 轮 + 判定 |
| `empty 1` | 367,002 | 上游 0 行 / 服务 404 | 无需补（口径正确） |

⇒ **complete 成立需要三件事同时到位**：
① 定向 run `41121952357` 跑完且这 9 层（7 missing + 2 partial）全部 `ok` 或给出上游确证的短采理由；
② NAD view 层拿到 token 复核声明值（或按 `unverified` 移出分母并写进文档）；
③ 6 层 `unverified` 走完 3 轮重测并给出终判。
