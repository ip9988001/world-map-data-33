# STEP04B 全量补采 · 收官账（2026-10-30）

## 一、总账

- 阶段：`04b` —— 全州放量 04b（round-2 续跑：36 层 / 9 片）
- 计划：18 层 / 声明 40,779,136 行 / 3 片（每片 6 层，unit_rows=1000000）
- 账本覆盖：**31 层**（片文件 7 个）
- 逐态：**ok 20** / empty 2 / partial 0 / failed 9 / skipped_done 0
- 片完成度：应有 **3** 片，有账本 7 片，**未完成 0 片**
- 声明行合计：**28,973,172**；实采行合计：**25,130,079**；差额 3,843,093（13.264%）

> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 6 | 6 | 11,118,520 | 完成 |
| 1 | 6 | 6 | 1,371,487 | 完成 |
| 2 | 4 | 4 | 3,018,600 | 完成 |
| 4 | 4 | 4 | 940,981 | 完成 |
| 5 | 4 | 4 | 3,558,309 | 完成 |
| 7 | 4 | 4 | 3,080,504 | 完成 |
| 8 | 4 | 4 | 2,041,678 | 完成 |

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 1,381,118 | failed | rc=1 err=? |
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 2,000 | 1,379,118 | failed | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service requ |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 714,545 | failed | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0)；跨轮：上轮已有 1 个单元包，本轮只 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,312 | 0 | 368,312 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | failed | 1381118 | 2000 | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service request :Wait timeout for the request exceed |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | failed | 1381118 | 0 | rc=1 err=? |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | failed | 716545 | 2000 | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0)；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | failed | 368312 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | failed | None | None | job 内单层超时 55 分钟（--layer-timeout） |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | failed | None | None | job 内单层超时 55 分钟（--layer-timeout） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | failed | None | None | job 内单层超时 55 分钟（--layer-timeout） |
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | failed | None | 0 | rc=3 err=? |

## 五、逐层台账（按声明行数降序）

| # | 层 | 声明 | 实采 | 差额% | 状态 |
|---|---|---|---|---|---|
| 1 | `UyC7jAmu_arcgis_rest_services_LBRSforLocator_FeatureServer_0` | 5,573,001 | 5,573,001 | 0.00% | ok |
| 2 | `rvices_Hosted_Address_Points_of_Indiana_2021_FeatureServer_1` | 3,146,263 | 3,146,263 | 0.00% | ok |
| 3 | `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_MapServer_0` | 2,489,597 | 2,489,597 | 0.00% | ok |
| 4 | `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | 2,220,021 | 2,220,021 | 0.00% | ok |
| 5 | `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 2,000 | 99.86% | failed |
| 6 | `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 100.00% | failed |
| 7 | `rvices_location_Address_Points_Modifications_FeatureServer_0` | 1,369,487 | 1,369,487 | 0.00% | ok |
| 8 | `rcgis_rest_services_County_37_LBRS_Addresses_FeatureServer_0` | 1,186,185 | 1,186,185 | 0.00% | ok |
| 9 | `st_services_SFDView_E911_Addresses_7_10_2026_FeatureServer_0` | 1,060,594 | 1,060,594 | 0.00% | ok |
| 10 | `wY_arcgis_rest_services_DSUSD_Address_Points_FeatureServer_0` | 938,981 | 938,981 | 0.00% | ok |
| 11 | `agsext_rest_services_Theme_Based_ODP_SPLIT_6_FeatureServer_1` | 864,423 | 864,423 | 0.00% | ok |
| 12 | `rvices_Address_Points_Search_and_Labels_VIEW_FeatureServer_0` | 784,068 | 784,068 | 0.00% | ok |
| 13 | `_arcgis_rest_services_OwnerMailAddressPoints_FeatureServer_0` | 771,821 | 771,821 | 0.00% | ok |
| 14 | `Wf5_arcgis_rest_services_MunicipalCodeAppPts_FeatureServer_0` | 724,258 | 724,258 | 0.00% | ok |
| 15 | `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 99.72% | failed |
| 16 | `tyohio_gov_hosting_rest_services_Addressing_LBRS_MapServer_0` | 707,755 | 707,755 | 0.00% | ok |
| 17 | `s_rest_services_msdi_structures_addresses_map_v1_MapServer_0` | 674,469 | 674,469 | 0.00% | ok |
| 18 | `DKC97XHbtyzbfkd_arcgis_rest_services_RKC_Map_FeatureServer_1` | 601,478 | 601,478 | 0.00% | ok |
| 19 | `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | 525,381 | 525,381 | 0.00% | ok |
| 20 | `ountytx_gov_arcgis_rest_services_AdMas_AdMas_FeatureServer_0` | 412,046 | 412,046 | 0.00% | ok |
| 21 | `cgis_rest_services_Master_Address_Repository_FeatureServer_0` | 388,039 | 388,039 | 0.00% | ok |
| 22 | `pG5Xodq0_arcgis_rest_services_Address_Points_FeatureServer_0` | 377,692 | 377,692 | 0.00% | ok |
| 23 | `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,312 | 0 | 100.00% | failed |
| 24 | `t01_rest_services_PlatTracker_PT365_PLAT_MAPPING_MapServer_5` | 310,520 | 310,520 | 0.00% | ok |
| 25 | `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | - | 0 | 0.00% | failed |
| 26 | `_arcgis1_rest_services_FLEXMOBILE_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 27 | `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | - | 0 | 0.00% | failed |
| 28 | `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | - | 0 | 0.00% | empty |
| 29 | `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | - | 0 | 0.00% | failed |
| 30 | `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | - | 0 | 0.00% | failed |
| 31 | `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=04b
python3 collect/full_plan.py --stage 04b --size 6 --out collect/ledger/04b_plan.json
python3 collect/full_shard.py --stage 04b --shard 0 --plan collect/ledger/04b_plan.json
```
