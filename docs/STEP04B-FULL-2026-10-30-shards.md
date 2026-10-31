# STEP04B 全量补采 · 收官账（2026-10-31）

## 一、总账

- 阶段：`04b` —— 全州放量 04b（round-2 续跑：36 层 / 9 片）
- 计划：272 层 / 声明 580,806,486 行 / 14 片（每片 20 层，unit_rows=1000000）
- 账本覆盖：**35 层**（片文件 7 个）
- 逐态：**ok 21** / empty 3 / partial 0 / failed 11 / skipped_done 0
- 片完成度：应有 **14** 片，有账本 7 片，**未完成 7 片**：片号 3, 6, 9, 10, 11, 12, 13
- 声明行合计：**30,444,161**；实采行合计：**26,599,068**；差额 3,845,093（12.630%）

> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 8 | 8 | 11,999,683 | 完成 |
| 1 | 8 | 8 | 1,959,313 | 完成 |
| 2 | 4 | 4 | 3,018,600 | 完成 |
| 3 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 4 | 4 | 4 | 940,981 | 完成 |
| 5 | 4 | 4 | 3,558,309 | 完成 |
| 6 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 7 | 4 | 4 | 3,080,504 | 完成 |
| 8 | 4 | 4 | 2,041,678 | 完成 |
| 9 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 10 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 11 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 12 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 13 | 12 | 0 | 0 | 未完成：无账本（片被取消/没启动） |

**未完成片共 7 个，至少 132 层没有任何账本条目**（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 0 | 1,381,118 | failed | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service requ |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 1,381,118 | failed | rc=1 err=? |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 714,545 | failed | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0)；跨轮：上轮已有 1 个单元包，本轮只 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,312 | 0 | 368,312 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | failed | 1381118 | 0 | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service request :Wait timeout for the request exceed |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | failed | 1381118 | 0 | rc=1 err=? |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | failed | 716545 | 2000 | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0)；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | failed | 368312 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | failed | None | None | job 内单层超时 55 分钟（--layer-timeout）；跨轮：上轮已有 4 个单元包，本轮只补缺口 |
| `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | failed | None | None | job 内单层超时 55 分钟（--layer-timeout）；跨轮：上轮已有 5 个单元包，本轮只补缺口 |
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
| 5 | `ricopa_County_Address_Points__Non_Commercial_FeatureServer_0` | 1,406,138 | 1,406,138 | 0.00% | ok |
| 6 | `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 0 | 100.00% | failed |
| 7 | `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 100.00% | failed |
| 8 | `rvices_location_Address_Points_Modifications_FeatureServer_0` | 1,369,487 | 1,369,487 | 0.00% | ok |
| 9 | `rcgis_rest_services_County_37_LBRS_Addresses_FeatureServer_0` | 1,186,185 | 1,186,185 | 0.00% | ok |
| 10 | `st_services_SFDView_E911_Addresses_7_10_2026_FeatureServer_0` | 1,060,594 | 1,060,594 | 0.00% | ok |
| 11 | `wY_arcgis_rest_services_DSUSD_Address_Points_FeatureServer_0` | 938,981 | 938,981 | 0.00% | ok |
| 12 | `agsext_rest_services_Theme_Based_ODP_SPLIT_6_FeatureServer_1` | 864,423 | 864,423 | 0.00% | ok |
| 13 | `rvices_Address_Points_Search_and_Labels_VIEW_FeatureServer_0` | 784,068 | 784,068 | 0.00% | ok |
| 14 | `_arcgis_rest_services_OwnerMailAddressPoints_FeatureServer_0` | 771,821 | 771,821 | 0.00% | ok |
| 15 | `Wf5_arcgis_rest_services_MunicipalCodeAppPts_FeatureServer_0` | 724,258 | 724,258 | 0.00% | ok |
| 16 | `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 99.72% | failed |
| 17 | `tyohio_gov_hosting_rest_services_Addressing_LBRS_MapServer_0` | 707,755 | 707,755 | 0.00% | ok |
| 18 | `s_rest_services_msdi_structures_addresses_map_v1_MapServer_0` | 674,469 | 674,469 | 0.00% | ok |
| 19 | `DKC97XHbtyzbfkd_arcgis_rest_services_RKC_Map_FeatureServer_1` | 601,478 | 601,478 | 0.00% | ok |
| 20 | `UGfPrN7o_arcgis_rest_services_Address_Labels_FeatureServer_0` | 553,175 | 553,175 | 0.00% | ok |
| 21 | `ountytx_gov_arcgis_rest_services_AdMas_AdMas_FeatureServer_0` | 412,046 | 412,046 | 0.00% | ok |
| 22 | `cgis_rest_services_Master_Address_Repository_FeatureServer_0` | 388,039 | 388,039 | 0.00% | ok |
| 23 | `pG5Xodq0_arcgis_rest_services_Address_Points_FeatureServer_0` | 377,692 | 377,692 | 0.00% | ok |
| 24 | `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,312 | 0 | 100.00% | failed |
| 25 | `tync_gov_arcgis_rest_services_GISDV_Base_Map_FeatureServer_1` | 347,577 | 347,577 | 0.00% | ok |
| 26 | `s_Points_from_National_Address_Database_view_FeatureServer_0` | - | 0 | 0.00% | empty |
| 27 | `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-2` | - | 0 | 0.00% | failed |
| 28 | `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0` | - | 0 | 0.00% | failed |
| 29 | `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | - | 0 | 0.00% | failed |
| 30 | `_arcgis1_rest_services_FLEXMOBILE_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 31 | `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | - | 0 | 0.00% | failed |
| 32 | `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | - | 0 | 0.00% | empty |
| 33 | `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | - | 0 | 0.00% | failed |
| 34 | `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | - | 0 | 0.00% | failed |
| 35 | `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=04b
python3 collect/full_plan.py --stage 04b --size 20 --out collect/ledger/04b_plan.json
python3 collect/full_shard.py --stage 04b --shard 0 --plan collect/ledger/04b_plan.json
```
