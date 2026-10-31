# STEP04B 全量补采 · 收官账（2026-10-31）

## 一、总账

- 阶段：`04b` —— 全州放量 04b（round-2 续跑：36 层 / 9 片）
- 计划：272 层 / 声明 580,806,486 行 / 14 片（每片 20 层，unit_rows=1000000）
- 账本覆盖：**20 层**（片文件 8 个）
- 逐态：**ok 9** / capped_by_upstream 0 / empty 2 / partial 0 / failed 9 / skipped_done 0
- 片完成度：应有 **14** 片，有账本 8 片，**未完成 6 片**：片号 6, 9, 10, 11, 12, 13
- 声明行合计：**12,587,288**；实采行合计：**8,742,194**；差额 3,845,094（30.547%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 2 | 2 | 3,618,012 | 完成 |
| 1 | 2 | 2 | 0 | 完成 |
| 2 | 2 | 2 | 0 | 完成 |
| 3 | 2 | 2 | 2,000 | 完成 |
| 4 | 2 | 2 | 0 | 完成 |
| 5 | 2 | 2 | 0 | 完成 |
| 6 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 7 | 4 | 4 | 3,080,504 | 完成 |
| 8 | 4 | 4 | 2,041,678 | 完成 |
| 9 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 10 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 11 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 12 | 20 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 13 | 12 | 0 | 0 | 未完成：无账本（片被取消/没启动） |

**未完成片共 6 个，至少 112 层没有任何账本条目**（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 0 | 1,381,118 | failed | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service requ |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 1,381,118 | failed | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service requ |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 714,545 | failed | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0) |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,313 | 0 | 368,313 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | failed | 1381118 | 0 | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service request :Wait timeout for the request exceed |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | failed | 1381118 | 0 | rc=1 err=query_fail:svcerr:{"code": 503, "message": "Error handling service request :Wait timeout for the request exceed |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | failed | 716545 | 2000 | rc=1 err=query_fail:Expecting value: line 1 column 1 (char 0) |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | failed | 368313 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | failed | None | None | job 内单层超时 120 分钟（--layer-timeout） |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | failed | None | None | job 内单层超时 120 分钟（--layer-timeout） |
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | failed | None | None | job 内单层超时 120 分钟（--layer-timeout） |

## 五、逐层台账（按声明行数降序）

| # | 层 | 声明 | 实采 | 差额% | 状态 |
|---|---|---|---|---|---|
| 1 | `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 3,618,012 | 3,618,012 | 0.00% | ok |
| 2 | `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 1,381,118 | 0 | 100.00% | failed |
| 3 | `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 1,381,118 | 0 | 100.00% | failed |
| 4 | `agsext_rest_services_Theme_Based_ODP_SPLIT_6_FeatureServer_1` | 864,423 | 864,423 | 0.00% | ok |
| 5 | `rvices_Address_Points_Search_and_Labels_VIEW_FeatureServer_0` | 784,068 | 784,068 | 0.00% | ok |
| 6 | `Wf5_arcgis_rest_services_MunicipalCodeAppPts_FeatureServer_0` | 724,258 | 724,258 | 0.00% | ok |
| 7 | `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 716,545 | 2,000 | 99.72% | failed |
| 8 | `tyohio_gov_hosting_rest_services_Addressing_LBRS_MapServer_0` | 707,755 | 707,755 | 0.00% | ok |
| 9 | `s_rest_services_msdi_structures_addresses_map_v1_MapServer_0` | 674,469 | 674,469 | 0.00% | ok |
| 10 | `DKC97XHbtyzbfkd_arcgis_rest_services_RKC_Map_FeatureServer_1` | 601,478 | 601,478 | 0.00% | ok |
| 11 | `cgis_rest_services_Master_Address_Repository_FeatureServer_0` | 388,039 | 388,039 | 0.00% | ok |
| 12 | `pG5Xodq0_arcgis_rest_services_Address_Points_FeatureServer_0` | 377,692 | 377,692 | 0.00% | ok |
| 13 | `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 368,313 | 0 | 100.00% | failed |
| 14 | `_arcgis1_rest_services_FLEXMOBILE_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 15 | `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | - | 0 | 0.00% | failed |
| 16 | `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | - | 0 | 0.00% | empty |
| 17 | `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | - | 0 | 0.00% | failed |
| 18 | `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | - | 0 | 0.00% | failed |
| 19 | `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |
| 20 | `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | - | 0 | 0.00% | failed |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=04b
python3 collect/full_plan.py --stage 04b --size 20 --out collect/ledger/04b_plan.json
python3 collect/full_shard.py --stage 04b --shard 0 --plan collect/ledger/04b_plan.json
```
