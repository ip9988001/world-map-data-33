# STEP05B 全量补采 · 收官账（2026-11-22）

## 一、总账

- 阶段：`05b` —— 县市碎片 05b（5,000~300,000 行）
- 计划：577 层 / 声明 31,664,423 行 / 3 片（每片 200 层，unit_rows=100000）
- 账本覆盖：**577 层**（片文件 3 个；已按 plan 作用域排除遗留片 18 个）
- 逐态：**ok 434** / capped_by_upstream 0 / empty 14 / partial 101 / failed 28 / skipped_done 0
- 片完成度：应有 **3** 片，有账本 3 片，**未完成 0 片**
- 声明行合计：**30,398,942**；实采行合计：**37,069,680**；差额 -6,670,738（-21.944%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 200 | 200 | 2,458,675 | 完成 |
| 1 | 200 | 200 | 7,276,367 | 完成 |
| 2 | 177 | 177 | 27,334,638 | 完成 |

## 二之三、遗留片文件（不计入本轮）

> 本轮 plan 只有 **3** 片（片号 0, 1, 2），同目录另有 **18** 个同 stage 前缀的片文件属于更早轮次。merge 作用域按 plan 收窄（W33-058 修）：这些文件**不被读取、不计入任何数字**。以前无条件 glob 会把它们一起吃进来，让层数与行数虚高。

| 遗留片文件 | 片号 | 层数 |
|---|---|---|
| `05b_shard03.json` | 3 | 50 |
| `05b_shard04.json` | 4 | 50 |
| `05b_shard05.json` | 5 | 50 |
| `05b_shard06.json` | 6 | 50 |
| `05b_shard07.json` | 7 | 50 |
| `05b_shard08.json` | 8 | 50 |
| `05b_shard09.json` | 9 | 50 |
| `05b_shard10.json` | 10 | 50 |
| `05b_shard11.json` | 11 | 50 |
| `05b_shard12.json` | 12 | 50 |
| `05b_shard13.json` | 13 | 50 |
| `05b_shard14.json` | 14 | 50 |
| `05b_shard15.json` | 15 | 50 |
| `05b_shard16.json` | 16 | 50 |
| `05b_shard17.json` | 17 | 50 |
| `05b_shard18.json` | 18 | 50 |
| `05b_shard19.json` | 19 | 50 |
| `05b_shard20.json` | 20 | 33 |

**遗留片合计 18 个文件 / 883 层记录**（其中与上面几片重层的会在按层合并时被去重，所以「净增层数」会小于这个数）。这些层属于更早轮次，要采必须单独派单。

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | 236,871 | 71 | 236,800 | failed | rc=1 err=batch250:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//E |
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 209,203 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,275 | 0 | 207,275 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,275 | 0 | 207,275 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 125,867 | failed | rc=1 err=? |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,200 | 99,114 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Inval |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,362 | 0 | 93,362 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 56,800 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 50,911 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 50,423 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0` | partial | 278192 | 555706 | 缺口 -99.76%（实采 555706 / 声明 278192） |
| `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` | partial | 277958 | 555729 | 缺口 -99.93%（实采 555729 / 声明 277958） |
| `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3` | partial | 268407 | 536539 | 缺口 -99.90%（实采 536539 / 声明 268407） |
| `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | partial | 268229 | 536539 | 缺口 -100.03%（实采 536539 / 声明 268229） |
| `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | failed | 236871 | 71 | rc=1 err=batch250:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtm |
| `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | partial | 227847 | 455698 | 缺口 -100.00%（实采 455698 / 声明 227847） |
| `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | partial | 224311 | 448628 | 缺口 -100.00%（实采 448628 / 声明 224311） |
| `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | partial | 219960 | 439750 | 缺口 -99.92%（实采 439750 / 声明 219960） |
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | failed | 209203 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | failed | 207275 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | failed | 207275 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | partial | 192634 | 385198 | 缺口 -99.96%（实采 385198 / 声明 192634） |
| `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | partial | 190252 | 380483 | 缺口 -99.99%（实采 380483 / 声明 190252） |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | failed | 187871 | 662000 | rc=1 err=query_fail:svcerr:{"code": 500, "message": "Error performing query operation", "details": []};query_fail:svcerr |
| `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | partial | 183836 | 367080 | 缺口 -99.68%（实采 367080 / 声明 183836） |
| `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | partial | 182659 | 365117 | 缺口 -99.89%（实采 365117 / 声明 182659） |
| `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0` | partial | 181440 | 362701 | 缺口 -99.90%（实采 362701 / 声明 181440） |
| `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | partial | 179493 | 358962 | 缺口 -99.99%（实采 358962 / 声明 179493） |
| `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0` | partial | 173381 | 346745 | 缺口 -99.99%（实采 346745 / 声明 173381） |
| `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 158719 | 317114 | 缺口 -99.80%（实采 317114 / 声明 158719） |
| `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | partial | 158408 | 316405 | 缺口 -99.74%（实采 316405 / 声明 158408） |
| `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0` | partial | 156027 | 312042 | 缺口 -99.99%（实采 312042 / 声明 156027） |
| `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | partial | 155653 | 310782 | 缺口 -99.66%（实采 310782 / 声明 155653） |
| `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | partial | 147918 | 295706 | 缺口 -99.91%（实采 295706 / 声明 147918） |
| `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` | partial | 130132 | 260301 | 缺口 -100.03%（实采 260301 / 声明 130132） |
| `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | partial | 130102 | 259861 | 缺口 -99.74%（实采 259861 / 声明 130102） |
| `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | partial | 130102 | 259861 | 缺口 -99.74%（实采 259861 / 声明 130102） |
| `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` | partial | 129693 | 259369 | 缺口 -99.99%（实采 259369 / 声明 129693） |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | failed | 125867 | 0 | rc=1 err=? |
| `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0` | partial | 118128 | 235365 | 缺口 -99.25%（实采 235365 / 声明 118128） |
| `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0` | partial | 114589 | 229361 | 缺口 -100.16%（实采 229361 / 声明 114589） |
| `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0` | partial | 111350 | 222652 | 缺口 -99.96%（实采 222652 / 声明 111350） |
| `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0` | partial | 110991 | 221935 | 缺口 -99.96%（实采 221935 / 声明 110991） |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | failed | 100314 | 1200 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | failed | 93362 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | partial | 87697 | 174890 | 缺口 -99.43%（实采 174890 / 声明 87697） |
| `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | partial | 84306 | 168433 | 缺口 -99.79%（实采 168433 / 声明 84306） |
| `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 82602 | 165191 | 缺口 -99.98%（实采 165191 / 声明 82602） |
| `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | partial | 72868 | 145729 | 缺口 -99.99%（实采 145729 / 声明 72868） |
| `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | partial | 72868 | 145729 | 缺口 -99.99%（实采 145729 / 声明 72868） |
| `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` | partial | 71260 | 142442 | 缺口 -99.89%（实采 142442 / 声明 71260） |
| `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0` | partial | 64989 | 129960 | 缺口 -99.97%（实采 129960 / 声明 64989） |
| `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0` | partial | 63212 | 126366 | 缺口 -99.91%（实采 126366 / 声明 63212） |
| `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 62581 | 125156 | 缺口 -99.99%（实采 125156 / 声明 62581） |
| `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 59831 | 119500 | 缺口 -99.73%（实采 119500 / 声明 59831） |
| `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0` | partial | 58760 | 117274 | 缺口 -99.58%（实采 117274 / 声明 58760） |
| `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` | partial | 58034 | 116044 | 缺口 -99.96%（实采 116044 / 声明 58034） |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | failed | 56888 | 88 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | partial | 56599 | 113267 | 缺口 -100.12%（实采 113267 / 声明 56599） |
| `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | partial | 54644 | 109268 | 缺口 -99.96%（实采 109268 / 声明 54644） |
| `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | partial | 51423 | 102815 | 缺口 -99.94%（实采 102815 / 声明 51423） |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | failed | 50911 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | failed | 50423 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | failed | 49374 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0` | partial | 49100 | 98176 | 缺口 -99.95%（实采 98176 / 声明 49100） |
| `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` | partial | 43499 | 86993 | 缺口 -99.99%（实采 86993 / 声明 43499） |
| `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0` | partial | 43405 | 86789 | 缺口 -99.95%（实采 86789 / 声明 43405） |
| `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | partial | 43042 | 86008 | 缺口 -99.82%（实采 86008 / 声明 43042） |
| `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | partial | 41018 | 82028 | 缺口 -99.98%（实采 82028 / 声明 41018） |
| `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | failed | 40689 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` | partial | 38656 | 77304 | 缺口 -99.98%（实采 77304 / 声明 38656） |
| `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 36725 | 73441 | 缺口 -99.98%（实采 73441 / 声明 36725） |
| `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | partial | 35212 | 70419 | 缺口 -99.99%（实采 70419 / 声明 35212） |
| `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` | partial | 34929 | 69851 | 缺口 -99.98%（实采 69851 / 声明 34929） |
| `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0` | partial | 34929 | 69851 | 缺口 -99.98%（实采 69851 / 声明 34929） |
| `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0` | partial | 34840 | 69679 | 缺口 -100.00%（实采 69679 / 声明 34840） |
| `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0` | partial | 32353 | 64689 | 缺口 -99.95%（实采 64689 / 声明 32353） |
| `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | partial | 26320 | 52635 | 缺口 -99.98%（实采 52635 / 声明 26320） |
| `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | partial | 25834 | 51668 | 缺口 -100.00%（实采 51668 / 声明 25834） |
| `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | partial | 25817 | 51608 | 缺口 -99.90%（实采 51608 / 声明 25817） |
| `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | partial | 25091 | 50069 | 缺口 -99.55%（实采 50069 / 声明 25091） |
| `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | partial | 23869 | 47732 | 缺口 -99.97%（实采 47732 / 声明 23869） |
| `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | partial | 23819 | 47237 | 缺口 -98.32%（实采 47237 / 声明 23819） |
| `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | partial | 23776 | 47553 | 缺口 -100.00%（实采 47553 / 声明 23776） |
| `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 23338 | 46672 | 缺口 -99.98%（实采 46672 / 声明 23338） |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | failed | 23246 | 20570 | rc=1 err=? |
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | failed | 23241 | 20567 | rc=1 err=? |
| `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | partial | 22248 | 44495 | 缺口 -100.00%（实采 44495 / 声明 22248） |
| `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | partial | 21770 | 43524 | 缺口 -99.93%（实采 43524 / 声明 21770） |
| `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | partial | 20040 | 40080 | 缺口 -100.00%（实采 40080 / 声明 20040） |
| `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | partial | 19161 | 38284 | 缺口 -99.80%（实采 38284 / 声明 19161） |
| `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | partial | 18526 | 37031 | 缺口 -99.89%（实采 37031 / 声明 18526） |
| `_rest_services_Oxford_911_Address_View_Layer_FeatureServer_1` | partial | 17976 | 35950 | 缺口 -99.99%（实采 35950 / 声明 17976） |
| `cgis_rest_services_Skokie_Base_Address_View_FeatureServer_33` | partial | 17731 | 35462 | 缺口 -100.00%（实采 35462 / 声明 17731） |
| `ysZUz_arcgis_rest_services_Carroll_Addresses_FeatureServer_0` | partial | 17328 | 34653 | 缺口 -99.98%（实采 34653 / 声明 17328） |
| `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | failed | 16730 | 0 | rc=1 err=batch0:http404: <div style="border: 3px solid #4991C5; font:1.5em; font-family:tahoma,calibri,arial; font-weigh |
| `6Z_arcgis_rest_services_N911_Addresses__View_FeatureServer_0` | partial | 15024 | 29989 | 缺口 -99.61%（实采 29989 / 声明 15024） |
| `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | failed | 14470 | 6616 | rc=1 err=? |
| `rent_Site_Addresses_and_Entrance_Points_view_FeatureServer_0` | partial | 14361 | 28710 | 缺口 -99.92%（实采 28710 / 声明 14361） |
| `rcgis_rest_services_Newberg_Addresses_2_view_FeatureServer_0` | partial | 14236 | 28470 | 缺口 -99.99%（实采 28470 / 声明 14236） |
| `_arcgis_rest_services_911_Addresses_Website2_FeatureServer_0` | partial | 14164 | 28282 | 缺口 -99.68%（实采 28282 / 声明 14164） |
| `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0` | partial | 13353 | 26705 | 缺口 -99.99%（实采 26705 / 声明 13353） |
| `is_rest_services_Grady_Site_Addresses_Public_FeatureServer_0` | partial | 12995 | 25981 | 缺口 -99.93%（实采 25981 / 声明 12995） |
| `cgis_rest_services_Site_Addresses_View_Layer_FeatureServer_0` | partial | 12642 | 25281 | 缺口 -99.98%（实采 25281 / 声明 12642） |
| `teAddresses_1a8d5e9d05674ad599c70df5dfdd4265_FeatureServer_0` | partial | 12642 | 25281 | 缺口 -99.98%（实采 25281 / 声明 12642） |
| `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_FeatureServer_0` | partial | 12445 | 24807 | 缺口 -99.33%（实采 24807 / 声明 12445） |
| `st_services_Arlington_Addresses_current_view_FeatureServer_0` | partial | 12284 | 24570 | 缺口 -100.02%（实采 24570 / 声明 12284） |
| `drG_arcgis_rest_services_Arlington_Addresses_FeatureServer_0` | partial | 12284 | 24570 | 缺口 -100.02%（实采 24570 / 声明 12284） |
| `5n_arcgis_rest_services_City_Limit_Addresses_FeatureServer_0` | partial | 12152 | 24296 | 缺口 -99.93%（实采 24296 / 声明 12152） |
| `JE9B_arcgis_rest_services_Newberg_Addresses__FeatureServer_0` | partial | 11817 | 23632 | 缺口 -99.98%（实采 23632 / 声明 11817） |
| `DdwE7LMrYrEMJ_arcgis_rest_services_Addresses_FeatureServer_1` | partial | 11801 | 23585 | 缺口 -99.86%（实采 23585 / 声明 11801） |
| `arcgis_rest_services_BTV_e911_Address_Layers_FeatureServer_0` | partial | 11475 | 22937 | 缺口 -99.89%（实采 22937 / 声明 11475） |
| `Kw_arcgis_rest_services_Situs_Address_Public_FeatureServer_0` | partial | 11385 | 22770 | 缺口 -100.00%（实采 22770 / 声明 11385） |
| `t_services_Public_20Notification_20Addresses_FeatureServer_0` | partial | 10606 | 21211 | 缺口 -99.99%（实采 21211 / 声明 10606） |
| `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | failed | 10564 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | failed | 9862 | 9602 | rc=1 err=? |
| `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0` | partial | 9704 | 19404 | 缺口 -99.96%（实采 19404 / 声明 9704） |
| `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | failed | 9628 | 9101 | rc=1 err=? |
| `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | partial | 8280 | 16558 | 缺口 -99.98%（实采 16558 / 声明 8280） |
| `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4` | partial | 8280 | 16558 | 缺口 -99.98%（实采 16558 / 声明 8280） |
| `sses_public_e65dd46e9c084cddaedcb94aeea0ed6b_FeatureServer_0` | partial | 7798 | 15501 | 缺口 -98.78%（实采 15501 / 声明 7798） |
| `sdIpPb_arcgis_rest_services_Addresses_Splits_FeatureServer_0` | partial | 6583 | 13161 | 缺口 -99.92%（实采 13161 / 声明 6583） |
| `st_services_Curb_Transition_Magic_Number2027_FeatureServer_0` | partial | 5896 | 11808 | 缺口 -100.27%（实采 11808 / 声明 5896） |
| `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 5045 | 10085 | 缺口 -99.90%（实采 10085 / 声明 5045） |
| `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `county_com_arcgis_rest_services_features_Address_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |

## 五、逐层台账（按声明行数降序）

| # | 层 | 声明 | 实采 | 差额% | 状态 |
|---|---|---|---|---|---|
| 1 | `jvohPcWJU5ij6_arcgis_rest_services_Addresses_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 2 | `hedVoters_Statewide_withSiteTypeDescription_FeatureServer_32` | 283,974 | 283,974 | 0.00% | ok |
| 3 | `_rest_services_Arapahoe_County_Addresses_gdb_FeatureServer_0` | 281,486 | 281,486 | 0.00% | ok |
| 4 | `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0` | 278,192 | 555,706 | -99.76% | partial |
| 5 | `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` | 277,958 | 555,729 | -99.93% | partial |
| 6 | `is_rest_services_Address_1424300337393713068_FeatureServer_0` | 274,644 | 274,644 | 0.00% | ok |
| 7 | `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3` | 268,407 | 536,539 | -99.90% | partial |
| 8 | `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | 268,229 | 536,539 | -100.03% | partial |
| 9 | `0yIuqCBxq_arcgis_rest_services_CNO_Addresses_FeatureServer_0` | 267,730 | 267,730 | 0.00% | ok |
| 10 | `oN_arcgis_rest_services_WASD_Addresses_3_23_FeatureServer_52` | 264,398 | 264,398 | 0.00% | ok |
| 11 | `xLqeJd2jOX_arcgis_rest_services_VC_Addresses_FeatureServer_0` | 263,947 | 263,947 | 0.00% | ok |
| 12 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | 236,871 | 71 | 99.97% | failed |
| 13 | `27_Great_Mississippi_Flood_in_Arkansas_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 14 | `_services_Lower_MS_Sediment_Bottleneck_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 15 | `_Mississippi_Flood_in_Arkansas__Final__WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 16 | `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | 227,847 | 455,698 | -100.00% | partial |
| 17 | `MCHD_Environmental_Health_Public_Service_Map_FeatureServer_0` | 226,508 | 226,508 | 0.00% | ok |
| 18 | `ZHFr6zdgNZuVG0_arcgis_rest_services_Address2_FeatureServer_3` | 226,170 | 226,170 | 0.00% | ok |
| 19 | `arcgis_rest_services_Jeffco_Address_Map_WFL1_FeatureServer_1` | 226,170 | 226,170 | 0.00% | ok |
| 20 | `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | 224,311 | 448,628 | -100.00% | partial |
| 21 | `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` | 221,905 | 221,905 | 0.00% | ok |
| 22 | `is_rest_services_Chester_County_PA_Addresses_FeatureServer_0` | 221,873 | 221,873 | 0.00% | ok |
| 23 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | 219,960 | 439,750 | -99.92% | partial |
| 24 | `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 100.00% | failed |
| 25 | `services_CountyServices_Municipal_Addressing_FeatureServer_2` | 207,685 | 207,685 | 0.00% | ok |
| 26 | `services_Zanna_E911_Sites_Within_8min_Buffer_FeatureServer_1` | 207,581 | 207,581 | 0.00% | ok |
| 27 | `i_arcgis_rest_services_Ada_County_Addresses_FeatureServer_13` | 207,396 | 207,396 | 0.00% | ok |
| 28 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,275 | 0 | 100.00% | failed |
| 29 | `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,275 | 0 | 100.00% | failed |
| 30 | `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1` | 204,910 | 204,910 | 0.00% | ok |
| 31 | `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` | 204,910 | 204,910 | 0.00% | ok |
| 32 | `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | 192,634 | 385,198 | -99.96% | partial |
| 33 | `ervices_AddressPts_DamageAssessment_REA_VIEW_FeatureServer_0` | 190,765 | 190,765 | 0.00% | ok |
| 34 | `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | 190,252 | 380,483 | -99.99% | partial |
| 35 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 187,871 | 662,000 | -252.37% | failed |
| 36 | `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | 183,836 | 367,080 | -99.68% | partial |
| 37 | `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | 182,659 | 365,117 | -99.89% | partial |
| 38 | `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0` | 181,440 | 362,701 | -99.90% | partial |
| 39 | `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | 179,493 | 358,962 | -99.99% | partial |
| 40 | `rest_services_E911_Addresses_Hamilton_County_FeatureServer_0` | 173,477 | 173,477 | 0.00% | ok |
| 41 | `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0` | 173,381 | 346,745 | -99.99% | partial |
| 42 | `_rest_services_Site_Addresses_FLOCK_10302024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 43 | `_services_Rutherford_Site_Addresses_11012024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 44 | `s_rest_services_Solano_County_Addresses_WFL1_FeatureServer_0` | 171,954 | 171,954 | 0.00% | ok |
| 45 | `j7_arcgis_rest_services_Addresses_GeneralUse_FeatureServer_0` | 169,896 | 169,896 | 0.00% | ok |
| 46 | `QGwSSLC0l_arcgis_rest_services_t07_Addresses_FeatureServer_0` | 168,093 | 168,093 | 0.00% | ok |
| 47 | `arcgis_rest_services_Addresses_Arcade_Labels_FeatureServer_0` | 161,806 | 161,806 | 0.00% | ok |
| 48 | `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` | 158,719 | 317,114 | -99.80% | partial |
| 49 | `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | 158,408 | 316,405 | -99.74% | partial |
| 50 | `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 51 | `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 52 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 53 | `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0` | 156,027 | 312,042 | -99.99% | partial |
| 54 | `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | 155,653 | 310,782 | -99.66% | partial |
| 55 | `rvices_stratmap19_addresspoints_48027_vector_FeatureServer_0` | 150,676 | 150,676 | 0.00% | ok |
| 56 | `is_rest_services_Barry_County_E911_Map_WFL1_FeatureServer_29` | 147,967 | 147,967 | 0.00% | ok |
| 57 | `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | 147,918 | 295,706 | -99.91% | partial |
| 58 | `LmYGD_arcgis_rest_services_DC_Addresses_WFL1_FeatureServer_0` | 144,111 | 144,111 | 0.00% | ok |
| 59 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_FeatureServer_2` | 139,097 | 139,097 | 0.00% | ok |
| 60 | `cgis_rest_services_Indianapolis_IN_Addresses_FeatureServer_0` | 138,941 | 138,941 | 0.00% | ok |
| 61 | `_rest_services_HenricoCountyGIS_05082023_gdb_FeatureServer_0` | 134,041 | 134,041 | 0.00% | ok |
| 62 | `_arcgis_rest_services_city_address_march2025_FeatureServer_0` | 130,386 | 130,386 | 0.00% | ok |
| 63 | `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` | 130,132 | 260,301 | -100.03% | partial |
| 64 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 65 | `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 66 | `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` | 129,693 | 259,369 | -99.99% | partial |
| 67 | `8JRPoNeQjgcLi_arcgis_rest_services_Addresses_FeatureServer_0` | 128,917 | 128,917 | 0.00% | ok |
| 68 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 100.00% | failed |
| 69 | `est_services_Collier_Addresses_Within_3_Mile_FeatureServer_0` | 121,820 | 121,820 | 0.00% | ok |
| 70 | `is_rest_services_Addresses_2015_Boston_BARI__FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 71 | `ervices_64a951f0_b017_11e6_b4e3_22000b8406af_FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 72 | `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0` | 118,128 | 235,365 | -99.25% | partial |
| 73 | `rvices_WCAddresses20251003_gdb_view_Geocivix_FeatureServer_0` | 118,119 | 118,119 | 0.00% | ok |
| 74 | `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 75 | `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 76 | `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 77 | `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0` | 114,589 | 229,361 | -100.16% | partial |
| 78 | `CRg_arcgis_rest_services_SBCnty_Address_Grid_FeatureServer_0` | 114,312 | 114,312 | 0.00% | ok |
| 79 | `4427d57d2827830_rest_services_Base_Addresses_FeatureServer_0` | 113,649 | 113,649 | 0.00% | ok |
| 80 | `rvices_Situs_for_ConsolidatedPrecincts_AGOL_FeatureServer_51` | 112,728 | 112,728 | 0.00% | ok |
| 81 | `GOi6N4Rq5cqFv_arcgis_rest_services_Addresses_FeatureServer_0` | 112,607 | 112,607 | 0.00% | ok |
| 82 | `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0` | 111,350 | 222,652 | -99.96% | partial |
| 83 | `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0` | 110,991 | 221,935 | -99.96% | partial |
| 84 | `McTk2tV5FXPLX_arcgis_rest_services_Addresses_FeatureServer_0` | 110,848 | 110,848 | 0.00% | ok |
| 85 | `V5FXPLX_arcgis_rest_services_Addresses_Units_FeatureServer_0` | 110,120 | 110,120 | 0.00% | ok |
| 86 | `vices_Yuma_911_Data_Roads_and_Addresses_WFL1_FeatureServer_0` | 108,514 | 108,514 | 0.00% | ok |
| 87 | `GEllMqef1LMjj_arcgis_rest_services_Addresses_FeatureServer_0` | 106,530 | 106,530 | 0.00% | ok |
| 88 | `cgis_rest_services_Delaware_County_E911_Data_FeatureServer_0` | 103,591 | 103,591 | 0.00% | ok |
| 89 | `tg2A1_arcgis_rest_services_vw_dist_addresses_FeatureServer_0` | 100,714 | 100,714 | 0.00% | ok |
| 90 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,200 | 98.80% | failed |
| 91 | `r_arcgis_rest_services_Coryell_address_5Mile_FeatureServer_0` | 99,593 | 99,593 | 0.00% | ok |
| 92 | `s_rest_services_NM911_Address_01_2026_SC_Web_FeatureServer_0` | 99,052 | 99,052 | 0.00% | ok |
| 93 | `wbCJ2GMP_arcgis_rest_services_E911calls_2020_FeatureServer_0` | 98,649 | 98,649 | 0.00% | ok |
| 94 | `arcgis_rest_services_NM911_Address_202506_SC_FeatureServer_0` | 98,409 | 98,409 | 0.00% | ok |
| 95 | `F_arcgis_rest_services_NM911_Address_02_2025_FeatureServer_0` | 97,956 | 97,956 | 0.00% | ok |
| 96 | `F_arcgis_rest_services_NM911_Address_10_2024_FeatureServer_0` | 97,603 | 97,603 | 0.00% | ok |
| 97 | `VWAC8iN_arcgis_rest_services_road_centerline_FeatureServer_0` | 97,499 | 97,499 | 0.00% | ok |
| 98 | `st_services_Springfield_address_density_WFL1_FeatureServer_2` | 97,259 | 97,259 | 0.00% | ok |
| 99 | `nQPdJ0azuLyn_arcgis_rest_services_AddressPts_FeatureServer_0` | 97,202 | 97,202 | 0.00% | ok |
| 100 | `_rest_services_NM911_Address_202401_SC_Web_a_FeatureServer_0` | 96,299 | 96,299 | 0.00% | ok |
| 101 | `gis_rest_services_Address_For_WebApp_Locator_FeatureServer_0` | 96,253 | 96,253 | 0.00% | ok |
| 102 | `is_rest_services_NM911_Address_202301_SC_Web_FeatureServer_0` | 95,212 | 95,212 | 0.00% | ok |
| 103 | `is_rest_services_Forsyth_County_GA_Addresses_FeatureServer_0` | 93,990 | 93,990 | 0.00% | ok |
| 104 | `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,362 | 0 | 100.00% | failed |
| 105 | `u0_arcgis_rest_services_Address_OfflineCopy_FeatureServer_21` | 93,230 | 93,230 | 0.00% | ok |
| 106 | `k6RO1_arcgis_rest_services_HudsonCty_AddrPts_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 107 | `arcgis_rest_services_Hudson_County_Addresses_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 108 | `_arcgis_rest_services_BILLING_ACCT_LOCATIONS_FeatureServer_0` | 91,378 | 91,378 | 0.00% | ok |
| 109 | `is_rest_services_AddressValidationTest2_WFL1_FeatureServer_0` | 91,269 | 91,269 | 0.00% | ok |
| 110 | `iJkq4oXsPh_arcgis_rest_services_Addresses_SR_FeatureServer_0` | 88,553 | 88,553 | 0.00% | ok |
| 111 | `mxCAS_arcgis_rest_services_ClermontAddresses_FeatureServer_0` | 88,301 | 88,301 | 0.00% | ok |
| 112 | `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | 87,697 | 174,890 | -99.43% | partial |
| 113 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | 84,306 | 168,433 | -99.79% | partial |
| 114 | `t_services_Katy_ISD_Harris_County_Addresses_FeatureServer_68` | 83,545 | 83,545 | 0.00% | ok |
| 115 | `I64Ui_arcgis_rest_services_WLAddressAndRoads_FeatureServer_0` | 83,223 | 83,223 | 0.00% | ok |
| 116 | `Spu5VOlu_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 83,144 | 83,144 | 0.00% | ok |
| 117 | `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_FeatureServer_0` | 83,101 | 83,101 | 0.00% | ok |
| 118 | `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | 82,602 | 165,191 | -99.98% | partial |
| 119 | `jSxUKayj_arcgis_rest_services_911_Addresses_FeatureServer_58` | 81,591 | 81,591 | 0.00% | ok |
| 120 | `C_arcgis_rest_services_Active_Addresses_2025_FeatureServer_0` | 77,324 | 77,324 | 0.00% | ok |
| 121 | `wLs3iGyK80EW_arcgis_rest_services_911Address_FeatureServer_0` | 75,909 | 75,909 | 0.00% | ok |
| 122 | `arcgis_rest_services_modified_JaCo_addresses_FeatureServer_0` | 75,681 | 75,681 | 0.00% | ok |
| 123 | `_arcgis_rest_services_Addresses_USA_combined_FeatureServer_0` | 75,340 | 75,340 | 0.00% | ok |
| 124 | `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0` | 75,051 | 75,046 | 0.01% | ok |
| 125 | `Cz_arcgis_rest_services_HC_MD_Addresses_10mi_FeatureServer_0` | 74,273 | 74,273 | 0.00% | ok |
| 126 | `C0yIuqCBxq_arcgis_rest_services_Address_2024_FeatureServer_0` | 73,380 | 73,380 | 0.00% | ok |
| 127 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 128 | `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 129 | `CXd1_arcgis_rest_services_Fargo_ND_Addresses_FeatureServer_0` | 72,684 | 72,684 | 0.00% | ok |
| 130 | `_pa_us_arcgis_rest_services_Hosted_Addresses_FeatureServer_0` | 72,208 | 72,208 | 0.00% | ok |
| 131 | `3P_arcgis_rest_services_SiteAddresses_public_FeatureServer_0@TX-2` | 71,798 | 71,798 | 0.00% | ok |
| 132 | `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` | 71,260 | 142,442 | -99.89% | partial |
| 133 | `U5257_arcgis_rest_services_Yonkers_Addresses_FeatureServer_0` | 71,097 | 71,097 | 0.00% | ok |
| 134 | `rcgis_rest_services_AddressPts_20230817_WFL1_FeatureServer_0` | 70,830 | 70,830 | 0.00% | ok |
| 135 | `arcgis_rest_services_AddressPt_20240705_WFL1_FeatureServer_0` | 70,586 | 70,586 | 0.00% | ok |
| 136 | `t3XQ_arcgis_rest_services_AddressPt_20230629_FeatureServer_0` | 70,491 | 70,491 | 0.00% | ok |
| 137 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0` | 70,213 | 70,213 | 0.00% | ok |
| 138 | `f_arcgis_rest_services_Killeen_AddressPoints_FeatureServer_0` | 70,199 | 70,199 | 0.00% | ok |
| 139 | `is_rest_services_Building_Permit_Addresssing_FeatureServer_0` | 69,365 | 69,365 | 0.00% | ok |
| 140 | `0gE_arcgis_rest_services_CenCom_Address_View_FeatureServer_0` | 69,075 | 69,075 | 0.00% | ok |
| 141 | `arverLink_Address_Lookup_20250623_PublicView_FeatureServer_0` | 67,699 | 67,699 | 0.00% | ok |
| 142 | `zOpn2_arcgis_rest_services_Streets_Buidlings_FeatureServer_0` | 65,488 | 65,488 | 0.00% | ok |
| 143 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0` | 64,989 | 129,960 | -99.97% | partial |
| 144 | `_rest_services_Randall_County_Addresses_WFL1_FeatureServer_1` | 64,757 | 64,757 | 0.00% | ok |
| 145 | `Tpwo5_arcgis_rest_services_FullAddress032026_FeatureServer_0` | 64,608 | 64,608 | 0.00% | ok |
| 146 | `AQncZQEtBv_arcgis_rest_services_Address_Clip_FeatureServer_0` | 64,333 | 64,333 | 0.00% | ok |
| 147 | `cgis_rest_services_Cedar_Rapids_IA_Addresses_FeatureServer_0` | 63,767 | 63,767 | 0.00% | ok |
| 148 | `AQdtmx0tv46_arcgis_rest_services_Address_Nye_FeatureServer_6` | 63,594 | 63,594 | 0.00% | ok |
| 149 | `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0` | 63,212 | 126,366 | -99.91% | partial |
| 150 | `5jlmVkpxP_arcgis_rest_services_Online911Data_FeatureServer_0` | 63,126 | 63,126 | 0.00% | ok |
| 151 | `dresses_in_City_Limits___ESD9___Web_Map_WFL1_FeatureServer_1` | 62,839 | 62,839 | 0.00% | ok |
| 152 | `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0` | 62,581 | 125,156 | -99.99% | partial |
| 153 | `InLrxvF0A_arcgis_rest_services_AddressR2_gdb_FeatureServer_0` | 60,615 | 60,615 | 0.00% | ok |
| 154 | `WNInLrxvF0A_arcgis_rest_services_Address_gdb_FeatureServer_0` | 60,326 | 60,326 | 0.00% | ok |
| 155 | `s_rest_services_Marathon_County_WI_Addresses_FeatureServer_0` | 59,998 | 59,998 | 0.00% | ok |
| 156 | `vF0A_arcgis_rest_services_AddressSearchLayer_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 157 | `AAWNInLrxvF0A_arcgis_rest_services_TCAddress_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 158 | `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` | 59,831 | 119,500 | -99.73% | partial |
| 159 | `arcgis_rest_services_Tompkins_County_Address_FeatureServer_0` | 59,711 | 59,711 | 0.00% | ok |
| 160 | `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0` | 58,760 | 117,274 | -99.58% | partial |
| 161 | `rcgis_rest_services_MC_Address_Pts_PMG_View1_FeatureServer_0` | 58,269 | 58,269 | 0.00% | ok |
| 162 | `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` | 58,034 | 116,044 | -99.96% | partial |
| 163 | `d1_arcgis_rest_services_Visalia_CA_Addresses_FeatureServer_0` | 57,934 | 57,934 | 0.00% | ok |
| 164 | `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 99.85% | failed |
| 165 | `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | 56,599 | 113,267 | -100.12% | partial |
| 166 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0` | 55,639 | 55,639 | 0.00% | ok |
| 167 | `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` | 54,793 | 54,793 | 0.00% | ok |
| 168 | `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | 54,644 | 109,268 | -99.96% | partial |
| 169 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0` | 52,649 | 52,649 | 0.00% | ok |
| 170 | `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` | 52,368 | 52,368 | 0.00% | ok |
| 171 | `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6` | 52,022 | 52,022 | 0.00% | ok |
| 172 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | 51,423 | 102,815 | -99.94% | partial |
| 173 | `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 100.00% | failed |
| 174 | `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 100.00% | failed |
| 175 | `st_services_A4_Landscape_addressverification_FeatureServer_1` | 49,808 | 49,808 | 0.00% | ok |
| 176 | `com_arcgis_rest_services_CommunityAddressing_FeatureServer_0` | 49,804 | 49,804 | 0.00% | ok |
| 177 | `teAddresses_ecd2ff39fbb34f39a2ec415fd784331b_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 178 | `teAddresses_b786541565b5475593a786a08ba6b3e2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 179 | `sses_public_a000778ae1664a348de916831f1a0ac0_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 180 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 181 | `teAddresses_1809c74f027741ce815587367a5cfd68_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 182 | `teAddresses_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 183 | `teAddresses_25f96256e2164540bc18abbff8a9d5c2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 184 | `sses_public_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 185 | `vN_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 186 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 187 | `d1DIvN_arcgis_rest_services_SiteAddresses__1_FeatureServer_1` | 49,802 | 49,802 | 0.00% | ok |
| 188 | `sses_public_a2522c3dfde94f6da7500df892abf9aa_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 189 | `sses_public_fa4be22034f14c15a3a589dd7009ca64_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 190 | `0JE2L2xUd_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 191 | `sses_public_e7c532395de343e38e58a8463128cfb7_FeatureServer_0` | 49,800 | 49,800 | 0.00% | ok |
| 192 | `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 100.00% | failed |
| 193 | `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0` | 49,100 | 98,176 | -99.95% | partial |
| 194 | `eajjke_arcgis_rest_services_Addresses_Rogers_FeatureServer_0` | 48,889 | 48,889 | 0.00% | ok |
| 195 | `aNxg1PvwI_arcgis_rest_services_All_Addresses_FeatureServer_0` | 48,666 | 48,666 | 0.00% | ok |
| 196 | `cgis_rest_services_NRSA_Address_Locator_WFL1_FeatureServer_8` | 48,634 | 48,634 | 0.00% | ok |
| 197 | `KpsCnqD7H_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 48,448 | 48,448 | 0.00% | ok |
| 198 | `Geezhu2j_arcgis_rest_services_E911_Addresses_FeatureServer_0` | 48,443 | 48,443 | 0.00% | ok |
| 199 | `Ilt_arcgis_rest_services_Clinton_Address_Pts_FeatureServer_0` | 47,510 | 47,510 | 0.00% | ok |
| 200 | `_arcgis_rest_services_BG911_Address_20250501_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 201 | `Bq9hgug_arcgis_rest_services_BG911_Addresses_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 202 | `e_Rollout__Days_of_Service_Per_Address__WFL1_FeatureServer_1` | 46,949 | 46,949 | 0.00% | ok |
| 203 | `gis_rest_services_CountyAddress2023_CHE_View_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 204 | `I64Ui_arcgis_rest_services_CountyAddress2023_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 205 | `qTGWY_arcgis_rest_services_JoCo_Site_Address_FeatureServer_1` | 45,019 | 45,019 | 0.00% | ok |
| 206 | `71LO_arcgis_rest_services_Addresses_CivQuest_FeatureServer_0` | 45,012 | 45,012 | 0.00% | ok |
| 207 | `2kwz79KUqUvxC_arcgis_rest_services_Addresses_FeatureServer_0` | 44,833 | 44,833 | 0.00% | ok |
| 208 | `wFbS_arcgis_rest_services_Chemungaddress_pts_FeatureServer_0` | 44,642 | 44,642 | 0.00% | ok |
| 209 | `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` | 43,499 | 86,993 | -99.99% | partial |
| 210 | `_arcgis_rest_services_Addresses_NOT_ELIGIBLE_FeatureServer_0` | 43,411 | 43,411 | 0.00% | ok |
| 211 | `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0` | 43,405 | 86,789 | -99.95% | partial |
| 212 | `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | 43,042 | 86,008 | -99.82% | partial |
| 213 | `s_rest_services_CityAddresses2022bu_CHE_view_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 214 | `4Ui_arcgis_rest_services_CityAddresses2022bu_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 215 | `s_rest_services_Raleigh_Co_EOC_Address_Sites_FeatureServer_0` | 42,165 | 42,165 | 0.00% | ok |
| 216 | `3kMP_arcgis_rest_services_E911AddressforSOMA_FeatureServer_0` | 41,887 | 41,887 | 0.00% | ok |
| 217 | `est_services_NormanResidentialTrashAddresses_FeatureServer_0` | 41,811 | 41,811 | 0.00% | ok |
| 218 | `s_rest_services_Master_Address_List_Aug_2026_FeatureServer_0` | 41,460 | 41,460 | 0.00% | ok |
| 219 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10` | 41,175 | 41,175 | 0.00% | ok |
| 220 | `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | 41,018 | 82,028 | -99.98% | partial |
| 221 | `OU_arcgis_rest_services_Addresses_SIO_Hosted_FeatureServer_0` | 40,752 | 40,752 | 0.00% | ok |
| 222 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | 40,689 | 0 | 100.00% | failed |
| 223 | `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 224 | `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 225 | `1_arcgis_rest_services_Bismarck_ND_Addresses_FeatureServer_0` | 40,568 | 40,568 | 0.00% | ok |
| 226 | `IzAwdHlO_arcgis_rest_services_Address_hosted_FeatureServer_0` | 40,255 | 40,255 | 0.00% | ok |
| 227 | `u6oHu4Z_arcgis_rest_services_SITUS_PUB_CBB_2_FeatureServer_0` | 39,951 | 39,951 | 0.00% | ok |
| 228 | `m_nEIrIdcFpdK28ibf_arcgis_rest_services_E911_FeatureServer_1` | 39,855 | 39,855 | 0.00% | ok |
| 229 | `p_arcgis_rest_services_LAFO_ADDRESS_12_17_13_FeatureServer_0` | 39,847 | 39,847 | 0.00% | ok |
| 230 | `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54` | 39,239 | 39,239 | 0.00% | ok |
| 231 | `rcgis_rest_services_Res_Address_Demographics_FeatureServer_1` | 39,114 | 39,114 | 0.00% | ok |
| 232 | `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` | 38,656 | 77,304 | -99.98% | partial |
| 233 | `d_Waste__Days_of_Service_Per_Address_092424_FeatureServer_52` | 38,389 | 38,389 | 0.00% | ok |
| 234 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address_FeatureServer_0` | 38,345 | 38,345 | 0.00% | ok |
| 235 | `rcgis_rest_services_Daly_City_Addresses_AGOL_FeatureServer_2` | 38,299 | 38,299 | 0.00% | ok |
| 236 | `Ypus4pYH0S_arcgis_rest_services_Site_Address_FeatureServer_4` | 37,961 | 37,961 | 0.00% | ok |
| 237 | `rest_services_CarthageWardsandaddresses_WFL1_FeatureServer_1` | 37,764 | 37,764 | 0.00% | ok |
| 238 | `is_rest_services_Madison_County_KY_Addresses_FeatureServer_1` | 37,446 | 37,446 | 0.00% | ok |
| 239 | `QYTTiP6CrfEsw_arcgis_rest_services_Addresses_FeatureServer_0` | 37,276 | 37,276 | 0.00% | ok |
| 240 | `_arcgis_rest_services_Flagstaff_AZ_Addresses_FeatureServer_0` | 37,174 | 37,174 | 0.00% | ok |
| 241 | `zUpjDtspiBG0j_arcgis_rest_services_E911_Copy_FeatureServer_0` | 37,066 | 37,066 | 0.00% | ok |
| 242 | `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0` | 36,725 | 73,441 | -99.98% | partial |
| 243 | `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_FeatureServer_0` | 36,292 | 36,292 | 0.00% | ok |
| 244 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_FeatureServer_1` | 36,292 | 36,292 | 0.00% | ok |
| 245 | `gT_arcgis_rest_services_USU_Addressing_view_FeatureServer_26` | 36,150 | 36,150 | 0.00% | ok |
| 246 | `ofS_arcgis_rest_services_Taos_E911_Addresses_FeatureServer_0` | 35,970 | 35,970 | 0.00% | ok |
| 247 | `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,810 | 35,810 | 0.00% | ok |
| 248 | `rcgis_rest_services_CTSI_AddressChecker_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 249 | `s_rest_services_CTSI_Address_Check_2023_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 250 | `PlhvQwvs_arcgis_rest_services_E911_Addrs_Pts_FeatureServer_0` | 35,637 | 35,637 | 0.00% | ok |
| 251 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | 35,212 | 70,419 | -99.99% | partial |
| 252 | `fMdTkPeHLCobS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,199 | 35,199 | 0.00% | ok |
| 253 | `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 254 | `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 255 | `arcgis_rest_services_Alexandria_VA_Addresses_FeatureServer_0` | 34,927 | 34,927 | 0.00% | ok |
| 256 | `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0` | 34,840 | 69,679 | -100.00% | partial |
| 257 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | 34,683 | 34,683 | 0.00% | ok |
| 258 | `1p_arcgis_rest_services_ADDRESS_20230403_CoB_FeatureServer_0` | 34,536 | 34,536 | 0.00% | ok |
| 259 | `pMfHt82xFG_arcgis_rest_services_RouteAddress_FeatureServer_0` | 34,495 | 34,495 | 0.00% | ok |
| 260 | `cgis_rest_services_Master_Addresses_for_Grid_FeatureServer_0` | 34,386 | 34,386 | 0.00% | ok |
| 261 | `kOGGtW27pGICf_arcgis_rest_services_Addresses_FeatureServer_0` | 34,063 | 34,063 | 0.00% | ok |
| 262 | `cgis_rest_services_Sarpy_County_NE_Addresses_FeatureServer_1` | 33,980 | 33,980 | 0.00% | ok |
| 263 | `rcgis_rest_services_Essex_Address_Pts_9_9_25_FeatureServer_0` | 33,904 | 33,904 | 0.00% | ok |
| 264 | `WCoI_arcgis_rest_services_20260601_Addresses_FeatureServer_0` | 33,856 | 33,856 | 0.00% | ok |
| 265 | `cgis_rest_services_Franklin_Co_911_Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 266 | `cgis_rest_services_FranklinCoVA_911Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 267 | `1_arcgis_rest_services_Longview_TX_Addresses_FeatureServer_0` | 33,603 | 33,603 | 0.00% | ok |
| 268 | `S1a_arcgis_rest_services_Address_Mailing_Map_FeatureServer_1` | 33,587 | 33,587 | 0.00% | ok |
| 269 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_FeatureServer_0` | 33,215 | 33,215 | 0.00% | ok |
| 270 | `cgis_rest_services_Riley_County_KS_Addresses_FeatureServer_0` | 33,193 | 33,193 | 0.00% | ok |
| 271 | `st_services_Vector_Tile_Site_Address_Labels_FeatureServer_57` | 32,917 | 32,917 | 0.00% | ok |
| 272 | `_arcgis_rest_services_zoningAddressingSearch_FeatureServer_0` | 32,625 | 32,625 | 0.00% | ok |
| 273 | `j7VSF_arcgis_rest_services_TemeculaAddresses_FeatureServer_0` | 32,615 | 32,615 | 0.00% | ok |
| 274 | `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0` | 32,353 | 64,689 | -99.95% | partial |
| 275 | `BpZX2wFbS_arcgis_rest_services_911addressing_FeatureServer_0` | 32,197 | 32,197 | 0.00% | ok |
| 276 | `rest_services_Cherokee_Address_Analysis_WFL1_FeatureServer_0` | 32,167 | 32,167 | 0.00% | ok |
| 277 | `VDElDOMEad_arcgis_rest_services_WayneAddress_FeatureServer_0` | 31,980 | 31,980 | 0.00% | ok |
| 278 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses_FeatureServer_0` | 31,520 | 31,520 | 0.00% | ok |
| 279 | `arcgis_rest_services_FranklinCountyAddresses_FeatureServer_0` | 31,516 | 31,516 | 0.00% | ok |
| 280 | `ez8fHeIiDRbgb_arcgis_rest_services_Addresses_FeatureServer_0` | 30,935 | 30,935 | 0.00% | ok |
| 281 | `aLg_arcgis_rest_services_Address_Hemet031325_FeatureServer_0` | 30,879 | 30,879 | 0.00% | ok |
| 282 | `rcgis_rest_services_Buildings_and_Addresses_FeatureServer_17` | 30,856 | 30,856 | 0.00% | ok |
| 283 | `s_rest_services_Rural_Addresses__Label_Only__FeatureServer_0` | 30,747 | 30,747 | 0.00% | ok |
| 284 | `_arcgis_rest_services_EnerGov_Test_Map1_WFL1_FeatureServer_3` | 30,649 | 30,649 | 0.00% | ok |
| 285 | `is_rest_services_Lead_Service_Line_Addresses_FeatureServer_0` | 30,565 | 30,565 | 0.00% | ok |
| 286 | `DgvxltnFwP_arcgis_rest_services_NG911_Layers_FeatureServer_1` | 30,273 | 30,273 | 0.00% | ok |
| 287 | `Mk18pL_arcgis_rest_services_Coffee_Addresses_FeatureServer_0` | 29,524 | 29,524 | 0.00% | ok |
| 288 | `xLBcrikqFM0vkoy_arcgis_rest_services_Address_FeatureServer_0` | 29,507 | 29,507 | 0.00% | ok |
| 289 | `4x6y8cTIstSBE_arcgis_rest_services_Addresses_FeatureServer_0` | 29,448 | 29,448 | 0.00% | ok |
| 290 | `TOM4lipn_arcgis_rest_services_Addresses_2023_FeatureServer_0` | 29,170 | 29,170 | 0.00% | ok |
| 291 | `8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1` | 28,996 | 28,996 | 0.00% | ok |
| 292 | `_arcgis_rest_services_Logan_County_Addresses_FeatureServer_0` | 28,571 | 28,571 | 0.00% | ok |
| 293 | `rcgis_rest_services_Bedford_County_Addresses_FeatureServer_0` | 28,352 | 28,352 | 0.00% | ok |
| 294 | `est_services_Street_Sweeping_Pilot_Addresses_FeatureServer_0` | 28,338 | 28,338 | 0.00% | ok |
| 295 | `rest_services_Hurricane_Ian_Damage_Addresses_FeatureServer_0` | 27,912 | 27,912 | 0.00% | ok |
| 296 | `_arcgis_rest_services_TehamaCounty_NG911_gdb_FeatureServer_8` | 27,565 | 27,565 | 0.00% | ok |
| 297 | `ices_City_of_Cuyahoga_Falls_Addressing_WFL1_FeatureServer_11` | 27,479 | 27,479 | 0.00% | ok |
| 298 | `vices_Campbell_County__VA_Broadband_Map_WFL1_FeatureServer_0` | 27,456 | 27,456 | 0.00% | ok |
| 299 | `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0` | 27,213 | 27,213 | 0.00% | ok |
| 300 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0` | 27,058 | 27,058 | 0.00% | ok |
| 301 | `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` | 26,965 | 26,965 | 0.00% | ok |
| 302 | `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0` | 26,903 | 26,903 | 0.00% | ok |
| 303 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0` | 26,684 | 26,684 | 0.00% | ok |
| 304 | `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` | 26,510 | 26,510 | 0.00% | ok |
| 305 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | 26,410 | 52,891 | -100.27% | partial |
| 306 | `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | 26,410 | 52,891 | -100.27% | partial |
| 307 | `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | 26,320 | 52,635 | -99.98% | partial |
| 308 | `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 26,021 | 26,021 | 0.00% | ok |
| 309 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | 25,834 | 51,668 | -100.00% | partial |
| 310 | `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | 25,817 | 51,608 | -99.90% | partial |
| 311 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0` | 25,582 | 25,582 | 0.00% | ok |
| 312 | `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` | 25,427 | 25,427 | 0.00% | ok |
| 313 | `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20` | 25,367 | 25,367 | 0.00% | ok |
| 314 | `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | 25,091 | 50,069 | -99.55% | partial |
| 315 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1` | 25,081 | 25,081 | 0.00% | ok |
| 316 | `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` | 24,987 | 24,987 | 0.00% | ok |
| 317 | `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` | 24,529 | 24,529 | 0.00% | ok |
| 318 | `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0` | 24,465 | 24,465 | 0.00% | ok |
| 319 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0` | 24,398 | 24,398 | 0.00% | ok |
| 320 | `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` | 24,136 | 24,136 | 0.00% | ok |
| 321 | `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0` | 24,123 | 24,123 | 0.00% | ok |
| 322 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0` | 24,109 | 24,109 | 0.00% | ok |
| 323 | `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` | 24,107 | 24,107 | 0.00% | ok |
| 324 | `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0` | 24,045 | 24,045 | 0.00% | ok |
| 325 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0` | 23,950 | 23,950 | 0.00% | ok |
| 326 | `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | 23,869 | 47,732 | -99.97% | partial |
| 327 | `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54` | 23,859 | 23,859 | 0.00% | ok |
| 328 | `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | 23,819 | 47,237 | -98.32% | partial |
| 329 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | 23,776 | 47,553 | -100.00% | partial |
| 330 | `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | 23,338 | 46,672 | -99.98% | partial |
| 331 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | 11.51% | failed |
| 332 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | 11.51% | failed |
| 333 | `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0` | 23,141 | 23,141 | 0.00% | ok |
| 334 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0` | 23,136 | 23,136 | 0.00% | ok |
| 335 | `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` | 23,106 | 23,106 | 0.00% | ok |
| 336 | `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0` | 22,930 | 22,930 | 0.00% | ok |
| 337 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 338 | `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 22,248 | 44,495 | -100.00% | partial |
| 339 | `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0` | 22,208 | 22,208 | 0.00% | ok |
| 340 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0` | 21,951 | 21,951 | 0.00% | ok |
| 341 | `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` | 21,789 | 21,789 | 0.00% | ok |
| 342 | `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | 21,770 | 43,524 | -99.93% | partial |
| 343 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | 21,721 | 21,721 | 0.00% | ok |
| 344 | `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` | 21,706 | 21,706 | 0.00% | ok |
| 345 | `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 346 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0` | 21,108 | 21,108 | 0.00% | ok |
| 347 | `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` | 21,092 | 21,092 | 0.00% | ok |
| 348 | `arcgis_rest_services_Master_Address_List_New_FeatureServer_0` | 21,055 | 21,055 | 0.00% | ok |
| 349 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0` | 21,006 | 21,006 | 0.00% | ok |
| 350 | `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` | 20,861 | 20,861 | 0.00% | ok |
| 351 | `cgis_rest_services_AddressesWithElectionData_FeatureServer_0` | 20,202 | 20,202 | 0.00% | ok |
| 352 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1` | 20,088 | 20,088 | 0.00% | ok |
| 353 | `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | 20,040 | 40,080 | -100.00% | partial |
| 354 | `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0` | 20,014 | 20,014 | 0.00% | ok |
| 355 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0` | 19,966 | 19,966 | 0.00% | ok |
| 356 | `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` | 19,812 | 19,812 | 0.00% | ok |
| 357 | `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0` | 19,767 | 19,767 | 0.00% | ok |
| 358 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0` | 19,339 | 19,339 | 0.00% | ok |
| 359 | `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` | 19,308 | 19,308 | 0.00% | ok |
| 360 | `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | 19,161 | 38,284 | -99.80% | partial |
| 361 | `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0` | 19,154 | 19,154 | 0.00% | ok |
| 362 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0` | 19,123 | 19,123 | 0.00% | ok |
| 363 | `is_rest_services_Gloucester_County_Addresses_FeatureServer_0` | 19,037 | 19,037 | 0.00% | ok |
| 364 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0` | 18,822 | 18,822 | 0.00% | ok |
| 365 | `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | 18,526 | 37,031 | -99.89% | partial |
| 366 | `RnMdg5KWv_arcgis_rest_services_911_Addresses_FeatureServer_0` | 18,406 | 18,406 | 0.00% | ok |
| 367 | `xkcSkFAjt_arcgis_rest_services_911_Addresses_FeatureServer_0` | 18,332 | 18,332 | 0.00% | ok |
| 368 | `gis_rest_services_Limestone_County_Addresses_FeatureServer_0` | 18,275 | 18,275 | 0.00% | ok |
| 369 | `_arcgis_rest_services_WyomingCountyAddresses_FeatureServer_0` | 18,194 | 18,194 | 0.00% | ok |
| 370 | `rcgis_rest_services_Mailing_Address_Map_WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 371 | `gis_rest_services_Mailing_Address_Map___WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 372 | `gis_rest_services_Mailing_Address_Map_2_WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 373 | `m_x7Yxpfpio5GuQWF2_arcgis_rest_services_E911_FeatureServer_0` | 18,028 | 18,028 | 0.00% | ok |
| 374 | `_rest_services_Oxford_911_Address_View_Layer_FeatureServer_1` | 17,976 | 35,950 | -99.99% | partial |
| 375 | `wY8_arcgis_rest_services_Address_Ranges_WFL1_FeatureServer_0` | 17,908 | 17,908 | 0.00% | ok |
| 376 | `kIrNAR_arcgis_rest_services_E911_Share_Files_FeatureServer_0` | 17,883 | 17,883 | 0.00% | ok |
| 377 | `YdlWlBxzX_arcgis_rest_services_Boone_Address_FeatureServer_0` | 17,833 | 17,833 | 0.00% | ok |
| 378 | `cgis_rest_services_Skokie_Base_Address_View_FeatureServer_33` | 17,731 | 35,462 | -100.00% | partial |
| 379 | `pNK5CvU_arcgis_rest_services_HempV_Addresses_FeatureServer_0` | 17,586 | 17,586 | 0.00% | ok |
| 380 | `meepNh_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 17,584 | 17,584 | 0.00% | ok |
| 381 | `1N7Y1EilGjehZ_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 17,575 | 17,575 | 0.00% | ok |
| 382 | `WuVPEmGK_arcgis_rest_services_Addresses_View_FeatureServer_0` | 17,498 | 17,498 | 0.00% | ok |
| 383 | `is_rest_services_Cottage_Grove_Address_Point_FeatureServer_0` | 17,425 | 17,425 | 0.00% | ok |
| 384 | `is_rest_services_Bureau_County_911_Addresses_FeatureServer_0` | 17,341 | 17,341 | 0.00% | ok |
| 385 | `ysZUz_arcgis_rest_services_Carroll_Addresses_FeatureServer_0` | 17,328 | 34,653 | -99.98% | partial |
| 386 | `cjlmqkA8ypi4T_arcgis_rest_services_Addresses_FeatureServer_0` | 17,308 | 17,308 | 0.00% | ok |
| 387 | `is_rest_services_Master_Address_Database_MAD_FeatureServer_0` | 17,222 | 17,222 | 0.00% | ok |
| 388 | `TymXTmwPsPzPHRU_arcgis_rest_services_Address_FeatureServer_0` | 17,199 | 17,199 | 0.00% | ok |
| 389 | `ces_Pueblo_County_Addresses_Evacuation_Times_FeatureServer_0` | 17,168 | 17,168 | 0.00% | ok |
| 390 | `ces_911_Address_Street_Review_WFL1_view_only_FeatureServer_0` | 16,997 | 17,013 | -0.09% | ok |
| 391 | `So_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 16,929 | 16,929 | 0.00% | ok |
| 392 | `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | 16,730 | 0 | 100.00% | failed |
| 393 | `gis_rest_services_SANGIS_AddressAPN_07312024_FeatureServer_0` | 16,657 | 16,657 | 0.00% | ok |
| 394 | `0_arcgis_rest_services_2022_Sep_01_Addresses_FeatureServer_0` | 16,579 | 16,579 | 0.00% | ok |
| 395 | `0_arcgis_rest_services_Duncanville_Addresses_FeatureServer_0` | 16,574 | 16,574 | 0.00% | ok |
| 396 | `rest_services_Addresses_Clark_County_WI_2019_FeatureServer_0` | 16,569 | 16,569 | 0.00% | ok |
| 397 | `gis_rest_services_GRANT_Address_ClerksOffice_FeatureServer_0` | 16,517 | 16,517 | 0.00% | ok |
| 398 | `aAg05xQLgo7_arcgis_rest_services_WGS_Address_FeatureServer_0` | 16,393 | 16,393 | 0.00% | ok |
| 399 | `4OueTcnj_arcgis_rest_services_just_addresses_FeatureServer_0` | 15,898 | 15,898 | 0.00% | ok |
| 400 | `cgis_rest_services_AtascaderoAddresses082025_FeatureServer_0` | 15,830 | 15,830 | 0.00% | ok |
| 401 | `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-1` | 15,033 | 15,033 | 0.00% | ok |
| 402 | `6Z_arcgis_rest_services_N911_Addresses__View_FeatureServer_0` | 15,024 | 29,989 | -99.61% | partial |
| 403 | `8hGN_arcgis_rest_services_Polk_Addresses_GAC_FeatureServer_0` | 15,015 | 15,015 | 0.00% | ok |
| 404 | `jld0x0gpn_arcgis_rest_services_E911Addresses_FeatureServer_0` | 14,842 | 14,842 | 0.00% | ok |
| 405 | `X_arcgis_rest_services_County_P_Address_View_FeatureServer_0` | 14,758 | 14,758 | 0.00% | ok |
| 406 | `kTU5o6Z_arcgis_rest_services_Addressing_AGOL_FeatureServer_0` | 14,712 | 14,712 | 0.00% | ok |
| 407 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | 54.28% | failed |
| 408 | `C2HwTkBAlth_arcgis_rest_services_Address_gdb_FeatureServer_0` | 14,389 | 14,389 | 0.00% | ok |
| 409 | `rent_Site_Addresses_and_Entrance_Points_view_FeatureServer_0` | 14,361 | 28,710 | -99.92% | partial |
| 410 | `KPa_arcgis_rest_services_overture_address_sd_FeatureServer_0` | 14,350 | 14,350 | 0.00% | ok |
| 411 | `rcgis_rest_services_Newberg_Addresses_2_view_FeatureServer_0` | 14,236 | 28,470 | -99.99% | partial |
| 412 | `ervices_Lee_County_E911_Addresses_and_Roads_FeatureServer_20` | 14,215 | 14,215 | 0.00% | ok |
| 413 | `sses_public_35d07adabaff4ddba616f6f365b8954e_FeatureServer_0` | 14,203 | 14,203 | 0.00% | ok |
| 414 | `_arcgis_rest_services_911_Addresses_Website2_FeatureServer_0` | 14,164 | 28,282 | -99.68% | partial |
| 415 | `8SWPG8KZ6r_arcgis_rest_services_911Addresses_FeatureServer_0` | 13,932 | 13,932 | 0.00% | ok |
| 416 | `arcgis_rest_services_Short_Term_Rentals_WFL1_FeatureServer_1` | 13,863 | 13,863 | 0.00% | ok |
| 417 | `m7axC2dD_arcgis_rest_services_WascoAddresses_FeatureServer_5` | 13,807 | 13,807 | 0.00% | ok |
| 418 | `hP2NPfFE_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 13,677 | 13,677 | 0.00% | ok |
| 419 | `Ia_arcgis_rest_services_County_911_Addresses_FeatureServer_0` | 13,629 | 13,629 | 0.00% | ok |
| 420 | `rcgis_rest_services_Johns_Creek_GA_Addresses_FeatureServer_1` | 13,540 | 13,540 | 0.00% | ok |
| 421 | `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0` | 13,353 | 26,705 | -99.99% | partial |
| 422 | `ELbQdlhsJLcCM_arcgis_rest_services_Addresses_FeatureServer_0` | 13,329 | 13,329 | 0.00% | ok |
| 423 | `kh71mtnDG_arcgis_rest_services_E911addresses_FeatureServer_0` | 13,205 | 13,205 | 0.00% | ok |
| 424 | `aR3VIVeAhJdr_arcgis_rest_services_AddressBPs_FeatureServer_0` | 13,190 | 13,190 | 0.00% | ok |
| 425 | `gis_rest_services_AddressList_Update20250311_FeatureServer_0` | 13,166 | 13,166 | 0.00% | ok |
| 426 | `MJrpz61FbvL5t_arcgis_rest_services_Addresses_FeatureServer_0` | 13,058 | 13,058 | 0.00% | ok |
| 427 | `is_rest_services_Grady_Site_Addresses_Public_FeatureServer_0` | 12,995 | 25,981 | -99.93% | partial |
| 428 | `st_services_VacantResidentialProperties_WFL1_FeatureServer_0` | 12,933 | 12,933 | 0.00% | ok |
| 429 | `dlWlBxzX_arcgis_rest_services_Marion_Address_FeatureServer_1` | 12,896 | 12,896 | 0.00% | ok |
| 430 | `rcgis_rest_services_VT_Data___E911_Landmarks_FeatureServer_0` | 12,867 | 12,867 | 0.00% | ok |
| 431 | `BYQ9pcCt_arcgis_rest_services_e911_pt_txdist_FeatureServer_0` | 12,670 | 12,670 | 0.00% | ok |
| 432 | `m_jOKMO9vKmc98J4JC_arcgis_rest_services_E911_FeatureServer_0` | 12,649 | 12,649 | 0.00% | ok |
| 433 | `cgis_rest_services_Site_Addresses_View_Layer_FeatureServer_0` | 12,642 | 25,281 | -99.98% | partial |
| 434 | `teAddresses_1a8d5e9d05674ad599c70df5dfdd4265_FeatureServer_0` | 12,642 | 25,281 | -99.98% | partial |
| 435 | `teAddresses_176dcf6d135741fcbc3bf17da5aa7aff_FeatureServer_0` | 12,592 | 12,592 | 0.00% | ok |
| 436 | `dlWlBxzX_arcgis_rest_services_Searcy_Address_FeatureServer_0` | 12,573 | 12,573 | 0.00% | ok |
| 437 | `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_FeatureServer_0` | 12,445 | 24,807 | -99.33% | partial |
| 438 | `aAg05xQLgo7_arcgis_rest_services_SiteAddress_FeatureServer_0` | 12,411 | 12,411 | 0.00% | ok |
| 439 | `l_Assessor_parcel_Map_June_06_09_2023_WFL1_FeatureServer_219` | 12,309 | 12,309 | 0.00% | ok |
| 440 | `st_services_Arlington_Addresses_current_view_FeatureServer_0` | 12,284 | 24,570 | -100.02% | partial |
| 441 | `drG_arcgis_rest_services_Arlington_Addresses_FeatureServer_0` | 12,284 | 24,570 | -100.02% | partial |
| 442 | `5n_arcgis_rest_services_City_Limit_Addresses_FeatureServer_0` | 12,152 | 24,296 | -99.93% | partial |
| 443 | `services_BRIC_WRC_Situs_Address_LookUp_Table_FeatureServer_0` | 12,115 | 12,115 | 0.00% | ok |
| 444 | `XhtlWzOFCTkO_arcgis_rest_services_AddressPts_FeatureServer_0` | 11,978 | 11,978 | 0.00% | ok |
| 445 | `wlO_arcgis_rest_services_Master_Address_List_FeatureServer_0` | 11,959 | 11,959 | 0.00% | ok |
| 446 | `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0` | 11,902 | 11,901 | 0.01% | ok |
| 447 | `JE9B_arcgis_rest_services_Newberg_Addresses__FeatureServer_0` | 11,817 | 23,632 | -99.98% | partial |
| 448 | `DdwE7LMrYrEMJ_arcgis_rest_services_Addresses_FeatureServer_1` | 11,801 | 23,585 | -99.86% | partial |
| 449 | `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5` | 11,641 | 11,641 | 0.00% | ok |
| 450 | `arcgis_rest_services_BTV_e911_Address_Layers_FeatureServer_0` | 11,475 | 22,937 | -99.89% | partial |
| 451 | `arcgis_rest_services_PAunderservedstructures_FeatureServer_0` | 11,469 | 11,469 | 0.00% | ok |
| 452 | `Kw_arcgis_rest_services_Situs_Address_Public_FeatureServer_0` | 11,385 | 22,770 | -100.00% | partial |
| 453 | `kFjYDrl_arcgis_rest_services_Address06192026_FeatureServer_0` | 11,221 | 11,221 | 0.00% | ok |
| 454 | `ILCm3hbWNTZLH_arcgis_rest_services_Addresses_FeatureServer_0` | 11,219 | 11,219 | 0.00% | ok |
| 455 | `Us_arcgis_rest_services_OC_Site_Address_2023_FeatureServer_0` | 11,076 | 11,076 | 0.00% | ok |
| 456 | `unty_com_arcgis_rest_services_Hosted_Address_FeatureServer_0` | 10,876 | 10,876 | 0.00% | ok |
| 457 | `kFjYDrl_arcgis_rest_services_Address02202025_FeatureServer_0` | 10,821 | 10,821 | 0.00% | ok |
| 458 | `lqccxOHLu_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 10,667 | 10,667 | 0.00% | ok |
| 459 | `t_services_Public_20Notification_20Addresses_FeatureServer_0` | 10,606 | 21,211 | -99.99% | partial |
| 460 | `1mtnDG_arcgis_rest_services_Worth__ADDRESSES_FeatureServer_0` | 10,572 | 10,572 | 0.00% | ok |
| 461 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | 10,564 | 0 | 100.00% | failed |
| 462 | `t_services_Perry_County_Address_Geocode_v1_1_FeatureServer_0` | 10,489 | 10,489 | 0.00% | ok |
| 463 | `4soU_arcgis_rest_services_Site_Addresses_gdb_FeatureServer_0` | 10,465 | 10,465 | 0.00% | ok |
| 464 | `rWTl_arcgis_rest_services_Harrison_Addresses_FeatureServer_0` | 10,330 | 10,330 | 0.00% | ok |
| 465 | `kFjYDrl_arcgis_rest_services_Address11292023_FeatureServer_0` | 10,216 | 10,216 | 0.00% | ok |
| 466 | `FjYDrl_arcgis_rest_services_Address_12102021_FeatureServer_0` | 9,969 | 9,969 | 0.00% | ok |
| 467 | `Qwt3_arcgis_rest_services_Address_Layer_view_FeatureServer_0` | 9,866 | 9,866 | 0.00% | ok |
| 468 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 9,862 | 9,602 | 2.64% | failed |
| 469 | `tkincounty_com_arcgis_rest_services_Full_Address_MapServer_1` | 9,813 | 9,813 | 0.00% | ok |
| 470 | `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0` | 9,704 | 19,404 | -99.96% | partial |
| 471 | `p_arcgis_rest_services_Addresses_Public_View_FeatureServer_0` | 9,672 | 9,672 | 0.00% | ok |
| 472 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 9,628 | 9,101 | 5.47% | failed |
| 473 | `QSIEviNS_arcgis_rest_services_Addresses_2025_FeatureServer_3` | 9,536 | 9,536 | 0.00% | ok |
| 474 | `_server_rest_services_Aspen_AspenEditEnabled_FeatureServer_0` | 9,451 | 9,452 | -0.01% | ok |
| 475 | `s___Pulse_of_OC_Updated_Draft___Site_Address_FeatureServer_0` | 9,420 | 9,420 | 0.00% | ok |
| 476 | `jyn_arcgis_rest_services_Full_Street_Address_FeatureServer_0` | 9,371 | 9,371 | 0.00% | ok |
| 477 | `st_services_Winneshiek_County_Address_Points_FeatureServer_1` | 9,211 | 9,211 | 0.00% | ok |
| 478 | `QpZPT9qY_arcgis_rest_services_TOD_ADDRESS_IN_FeatureServer_0` | 9,149 | 9,149 | 0.00% | ok |
| 479 | `_arcgis_rest_services_Address_Pnts_ElSegundo_FeatureServer_2` | 9,137 | 9,137 | 0.00% | ok |
| 480 | `oXVtxM_arcgis_rest_services_CountyAddresses_FeatureServer_23` | 9,126 | 9,126 | 0.00% | ok |
| 481 | `hAmRP1z50gTbO_arcgis_rest_services_Addresses_FeatureServer_0` | 9,107 | 9,107 | 0.00% | ok |
| 482 | `Sample_NCTECH_Volusia_Situs_Addresss_VRWorld_FeatureServer_0` | 8,990 | 8,990 | 0.00% | ok |
| 483 | `BY6OUzMBTZcz_arcgis_rest_services_Addresses_FeatureServer_15` | 8,951 | 8,951 | 0.00% | ok |
| 484 | `cyjLcCCpGk8Ri_arcgis_rest_services_Addresses_FeatureServer_0` | 8,688 | 8,688 | 0.00% | ok |
| 485 | `sses_public_6332b4b81c614cb4894d5de569a96465_FeatureServer_0` | 8,635 | 8,635 | 0.00% | ok |
| 486 | `VF_arcgis_rest_services_SC_Addressing_2025_7_FeatureServer_0` | 8,586 | 8,586 | 0.00% | ok |
| 487 | `gUZUh16VF_arcgis_rest_services_SC_Addressing_FeatureServer_0` | 8,585 | 8,585 | 0.00% | ok |
| 488 | `Pc_arcgis_rest_services_EL_RENO_911ADDRESSES_FeatureServer_0` | 8,465 | 8,465 | 0.00% | ok |
| 489 | `rcgis_rest_services_OsageCoKS_NG911Addresses_FeatureServer_0` | 8,287 | 8,287 | 0.00% | ok |
| 490 | `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | 8,280 | 16,558 | -99.98% | partial |
| 491 | `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4` | 8,280 | 16,558 | -99.98% | partial |
| 492 | `PSO5BR5eOIggwRH_arcgis_rest_services_Address_FeatureServer_0` | 8,267 | 8,267 | 0.00% | ok |
| 493 | `wu_arcgis_rest_services_CoStafford_Addresses_FeatureServer_0` | 8,246 | 8,246 | 0.00% | ok |
| 494 | `vlQFEpKtV_arcgis_rest_services_DOUGLASCOUNTY_FeatureServer_0` | 8,201 | 8,201 | 0.00% | ok |
| 495 | `R_arcgis_rest_services_Tornado_Addresses_NLR_FeatureServer_0` | 8,182 | 8,182 | 0.00% | ok |
| 496 | `Zk1fY2MHCTEXz_arcgis_rest_services_Addresses_FeatureServer_0` | 8,149 | 8,149 | 0.00% | ok |
| 497 | `resses___Archuleta_County_201411251147175537_FeatureServer_0` | 8,134 | 8,134 | 0.00% | ok |
| 498 | `es_City_Buildings_and_Address_Locations_WFL1_FeatureServer_4` | 7,969 | 7,969 | 0.00% | ok |
| 499 | `1uhbqnOZPx6qT_arcgis_rest_services_Addresses_FeatureServer_0` | 7,888 | 7,888 | 0.00% | ok |
| 500 | `_arcgis_rest_services_Site_Address_Occupants_FeatureServer_0` | 7,886 | 7,886 | 0.00% | ok |
| 501 | `s_rest_services_City_of_Dinuba_Addresses_gdb_FeatureServer_1` | 7,845 | 7,845 | 0.00% | ok |
| 502 | `_services_Address_and_Street_Annotation_view_FeatureServer_0` | 7,836 | 7,836 | 0.00% | ok |
| 503 | `sses_public_e65dd46e9c084cddaedcb94aeea0ed6b_FeatureServer_0` | 7,798 | 15,501 | -98.78% | partial |
| 504 | `DQNT3m6mbJlqZ_arcgis_rest_services_Addresses_FeatureServer_0` | 7,733 | 7,733 | 0.00% | ok |
| 505 | `HRU_arcgis_rest_services_VFAC_Addresses_WFL1_FeatureServer_0` | 7,686 | 7,686 | 0.00% | ok |
| 506 | `s_rest_services_Richland_County_ND_Addresses_FeatureServer_1` | 7,608 | 7,608 | 0.00% | ok |
| 507 | `8nlIDAHxNx4_arcgis_rest_services_911_Address_FeatureServer_0` | 7,566 | 7,566 | 0.00% | ok |
| 508 | `gg5s_arcgis_rest_services_Building_Addresses_FeatureServer_0` | 7,540 | 7,540 | 0.00% | ok |
| 509 | `ses_public_3336c922d00a441e8f588e16c3dc2577_FeatureServer_10` | 7,529 | 7,529 | 0.00% | ok |
| 510 | `ms_arcgis_rest_services_Address_Data_Public_FeatureServer_10` | 7,527 | 7,527 | 0.00% | ok |
| 511 | `cgis_rest_services_Address_Data_Public_view_FeatureServer_10` | 7,527 | 7,527 | 0.00% | ok |
| 512 | `rest_services_Master_Address_Management_WFL1_FeatureServer_0` | 7,506 | 7,506 | 0.00% | ok |
| 513 | `Q24dH_arcgis_rest_services_Addresses__Site__FeatureServer_13` | 7,440 | 7,440 | 0.00% | ok |
| 514 | `0hS_arcgis_rest_services_Address_Road_Update_FeatureServer_0` | 7,370 | 7,370 | 0.00% | ok |
| 515 | `l0FeW1NE_arcgis_rest_services_AddressesWInfo_FeatureServer_0` | 7,364 | 7,364 | 0.00% | ok |
| 516 | `Z_arcgis_rest_services_CityofDemingAddresses_FeatureServer_0` | 7,251 | 7,251 | 0.00% | ok |
| 517 | `rest_services_Pella_Address_Data_Public_View_FeatureServer_2` | 7,242 | 7,242 | 0.00% | ok |
| 518 | `_ArcGIS_rest_services_AddressesE911Macon2022_FeatureServer_0` | 7,242 | 7,242 | 0.00% | ok |
| 519 | `CY2_arcgis_rest_services_Dispatcher_Map_WFL1_FeatureServer_0` | 7,165 | 7,165 | 0.00% | ok |
| 520 | `rest_services_Site_Addresses_06012022_public_FeatureServer_2` | 7,163 | 7,163 | 0.00% | ok |
| 521 | `_Mountlake_Terrace_Washington_Addresses_view_FeatureServer_0` | 7,157 | 7,157 | 0.00% | ok |
| 522 | `ieS2ld_arcgis_rest_services_Searcy_NG911_gdb_FeatureServer_2` | 7,144 | 7,144 | 0.00% | ok |
| 523 | `kttgSmcq6CPonms_arcgis_rest_services_Address_FeatureServer_0` | 6,953 | 6,953 | 0.00% | ok |
| 524 | `_rest_services_E911_Houses_Washington_County_FeatureServer_0` | 6,724 | 6,724 | 0.00% | ok |
| 525 | `M5KB8_arcgis_rest_services_E911_PairwiseClip_FeatureServer_0` | 6,716 | 6,716 | 0.00% | ok |
| 526 | `7Y8pE5CiojuXeU_arcgis_rest_services_NewSitus_FeatureServer_0` | 6,686 | 6,686 | 0.00% | ok |
| 527 | `NuFrQ7kB_arcgis_rest_services_Master_Address_FeatureServer_0` | 6,655 | 6,655 | 0.00% | ok |
| 528 | `SQHJsl5r_arcgis_rest_services_Address_Labels_FeatureServer_0` | 6,588 | 6,588 | 0.00% | ok |
| 529 | `sdIpPb_arcgis_rest_services_Addresses_Splits_FeatureServer_0` | 6,583 | 13,161 | -99.92% | partial |
| 530 | `st_services_Lincoln_City_Addresses_View_Only_FeatureServer_0` | 6,521 | 6,521 | 0.00% | ok |
| 531 | `ater_Meter_Replacement_Addresses_Zone_1_view_FeatureServer_1` | 6,361 | 6,361 | 0.00% | ok |
| 532 | `teAddresses_8548b2fdfac0464392b3fd7620a632d7_FeatureServer_0` | 6,197 | 6,197 | 0.00% | ok |
| 533 | `yHixJV_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 6,184 | 6,184 | 0.00% | ok |
| 534 | `ces_Stillwater_County_Addressing_Layers_2026_FeatureServer_0` | 6,112 | 6,112 | 0.00% | ok |
| 535 | `wVADPEG6iD24f_arcgis_rest_services_Addresses_FeatureServer_0` | 6,031 | 6,031 | 0.00% | ok |
| 536 | `_in_Incident_Address_and_Type_for_Date_Range_FeatureServer_0` | 5,929 | 5,929 | 0.00% | ok |
| 537 | `st_services_Curb_Transition_Magic_Number2027_FeatureServer_0` | 5,896 | 11,808 | -100.27% | partial |
| 538 | `387Pb3S_arcgis_rest_services_LiveAdds_202504_FeatureServer_0` | 5,876 | 5,876 | 0.00% | ok |
| 539 | `Iod9kh71mtnDG_arcgis_rest_services_Addresses_FeatureServer_0` | 5,731 | 5,731 | 0.00% | ok |
| 540 | `dlWlBxzX_arcgis_rest_services_Newton_Address_FeatureServer_0` | 5,730 | 5,730 | 0.00% | ok |
| 541 | `cgis_rest_services_SiteAddresses_public_2020_FeatureServer_1` | 5,655 | 5,655 | 0.00% | ok |
| 542 | `HKRPMgv82EjLQ_arcgis_rest_services_Addresses_FeatureServer_0` | 5,640 | 5,640 | 0.00% | ok |
| 543 | `CRVuK_arcgis_rest_services_Map_View_Address_FeatureServer_42` | 5,634 | 5,634 | 0.00% | ok |
| 544 | `e3_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 5,586 | 5,586 | 0.00% | ok |
| 545 | `unty__GA_Online_911_Addresses_and_Roads_WFL1_FeatureServer_1` | 5,493 | 5,493 | 0.00% | ok |
| 546 | `TjgFX_arcgis_rest_services_addresses_120222a_FeatureServer_0` | 5,409 | 5,410 | -0.02% | ok |
| 547 | `bK6DOd0VbR_arcgis_rest_services_SB_Addresses_FeatureServer_0` | 5,403 | 5,403 | 0.00% | ok |
| 548 | `cgis_rest_services_Administrative_Addressing_FeatureServer_0` | 5,371 | 5,371 | 0.00% | ok |
| 549 | `67TISFO3iTjgFX_arcgis_rest_services_address2_FeatureServer_0` | 5,236 | 5,236 | 0.00% | ok |
| 550 | `esses_In_Refuse_Recycle_Routes_WFL1_July2019_FeatureServer_0` | 5,219 | 5,219 | 0.00% | ok |
| 551 | `g5mTyuNWO5xx6_arcgis_rest_services_Addresses_FeatureServer_0` | 5,168 | 5,168 | 0.00% | ok |
| 552 | `arcgis_rest_services_Hartford_911_Addresses__FeatureServer_0` | 5,108 | 5,108 | 0.00% | ok |
| 553 | `d_Septic_System_Pilot_Project_Addresses_View_FeatureServer_0` | 5,071 | 5,071 | 0.00% | ok |
| 554 | `roY6O3ncx_arcgis_rest_services_MS4_addresses_FeatureServer_0` | 5,060 | 5,060 | 0.00% | ok |
| 555 | `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0` | 5,045 | 10,085 | -99.90% | partial |
| 556 | `is_rest_services_Address_Points_Council_Area_FeatureServer_0` | - | 0 | 0.00% | empty |
| 557 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | - | 0 | 0.00% | empty |
| 558 | `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | - | 0 | 0.00% | empty |
| 559 | `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | - | 0 | 0.00% | empty |
| 560 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | - | 0 | 0.00% | empty |
| 561 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | - | 0 | 0.00% | failed |
| 562 | `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | - | 0 | 0.00% | empty |
| 563 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 564 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | - | 25,659 | 0.00% | empty |
| 565 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | - | 0 | 0.00% | failed |
| 566 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | - | 0 | 0.00% | empty |
| 567 | `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | - | 0 | 0.00% | empty |
| 568 | `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | - | 0 | 0.00% | failed |
| 569 | `county_com_arcgis_rest_services_features_Address_MapServer_0` | - | 0 | 0.00% | failed |
| 570 | `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0` | - | 45,810 | 0.00% | empty |
| 571 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 572 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |
| 573 | `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 574 | `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | - | 0 | 0.00% | empty |
| 575 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | - | 0 | 0.00% | failed |
| 576 | `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | - | 233,572 | 0.00% | empty |
| 577 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | - | 0 | 0.00% | empty |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=05b
python3 collect/full_plan.py --stage 05b --size 200 --out collect/ledger/05b_plan.json
python3 collect/full_shard.py --stage 05b --shard 0 --plan collect/ledger/05b_plan.json
```


## 附录：口径备注（2026-11-22 复核 · 只解释数字，不改数字）

> 本节由 `docs/STEP05B-FULL-2026-10-30-shards.notes.md` 随文生成时自动追加（`step_full_report.py`
> 会在正文之后拼接同名 `.notes.md`），所以 CI 重跑 merge 不会把这段解释冲掉。

### A. 本文件修订前的数字是「merge 作用域」污染出来的，已作废

旧版本头部写「计划：577 层」，同一段又写「账本覆盖：1426 层（片文件 21 个）」
「声明行合计 68,180,805；实采行合计 75,100,286」—— 这两个数**不是本轮采的**：

- `step_full_report.py` 原先无条件 `glob ledger/05b_shard*.json`，把同目录里属于**更早轮次**的
  shard03..shard20 十八个片文件一起并进了 merge；
- 05b 本轮 plan 只有 **3 片 / 577 层**（`collect/ledger/05b_plan.json`：`shards_n=3`、`layers_n=577`），
  目录里却躺着 21 片 → 1426 − 577 = **849 层是别轮次的**；
- 修法（W33-058）：merge 作用域 = 本轮 plan 的片号集合，片号 ∉ plan 一律不读，并逐个打印；
  run 账本 `collect/ledger/05b_run<RUN_ID>.json` 新增 `read_shards` / `ignored_shard_files` 留痕。

| 口径 | 层数 | 声明行 | 实采行 |
|---|---|---|---|
| 旧（污染，glob 全量读 21 片） | 1,426 | 68,180,805 | 75,100,286 |
| 新（plan 作用域，只读 3 片） | **577** | **30,398,942** | **37,069,680** |

差额来源一句话：旧账本比新账本多算的声明 37,781,863 行 / 实采 38,030,606 行，全部来自
shard03..shard20（849 层净增 + 34 层重层层的取值差异），它们不在本轮 plan 里。
片账本 `shard0/1/2` 的实采行 2,458,675 + 7,276,367 + 27,334,638 = **37,069,680**，
与正文总账一位不差。

### B. 遗留片文件：18 个 / 883 条层记录 / 净增 849 层

shard03..shard20 共 18 个文件，是更早的 **21 片轮次**（`shards_total=21`、`size=50`）的产物，
片账本里合计 **883 条层记录**（17 片 × 50 层 + 1 片 × 33 层）。
其中 **34 层**与本轮 3 片里的层同名（按层合并会去重），所以旧账本的净增正好是 883 − 34 = **849 层**。
这些层不属本轮，要采必须单独派单（`force_layers`），不能靠 merge 混进来。

### C. 声明行两个数为何差 1,265,481（plan 31,664,423 vs 片账本 30,398,942）

两边都是逐层 `returnCount` 之和，差在**快照时间不同**（plan 在 2026-11-21 生成，片账本在采集时又探了一次），
可逐层对齐（577 层两边层集合完全一致，plan 侧逐层值 = `collect/ledger/05b_plan_probe.json`
的 `expect_by_layer`，求和正好 31,664,423）：

| 分类 | 层数 | plan 侧声明 | 片账本声明 | 差（plan − 账本） |
|---|---|---|---|---|
| empty（采集时上游声明 0 行） | 14 | 847,823 | 0 | **+847,823** |
| failed | 28 | 2,151,134 | 1,724,064 | **+427,070** |
| └ 其中 collect 时探针失败、`declared=null` | 8 | 428,427 | 0（不可复核，不入分母） | +428,427 |
| ok | 434 | 21,305,889 | 21,306,590 | −701 |
| partial | 101 | 7,359,577 | 7,368,288 | −8,711 |
| **合计** | **577** | **31,664,423** | **30,398,942** | **+1,265,481** |

即：**847,823（14 层采集时变空）+ 427,070（28 层失败，其中 8 层连声明都探不到）− 9,412（ok/partial 层
采集时 returnCount 已上浮）= 1,265,481**。这不是记账错误，也不是覆盖率缩水，是 plan 快照与采集快照的差。

### D. rows 37,069,680 > declared 30,398,942（+6,670,738）：**已知分页去重缺陷，不是超额完成**

分解（逐层核对，可复算）：

| 分类 | 层数 | 声明 | 实采 | 差 |
|---|---|---|---|---|
| partial | 101 | 7,368,288 | 14,728,222 | **+7,359,934** |
| empty（declared=0） | 3 | 0 | 305,041 | +305,041 |
| failed | 28 | 1,724,064 | 729,815 | −994,249 |
| ok | 434 | 21,306,590 | 21,306,602 | +12 |
| **合计** | **577** | **30,398,942** | **37,069,680** | **+6,670,738** |

- 主体是 **101 个 partial 层，实采/声明比 1.983 ~ 2.003（中位 2.000）**——正是顶补环节分页重复
  （同一批行被连采两遍）造成的，已定位为采集侧缺陷，另一个 PR（`fix/w33-048-variant-merge-and-paging-dedup`）
  在修「按行身份去重」。**修好之前，实采行一律按「含重复行」看待，不得对外声称超额完成。**
- 3 个 empty 层 `declared=0` 但实采 305,041 行（25,659 + 45,810 + 233,572），
  是「声明 0 时上游仍吐行」的账本口径问题，同样等着重采后收敛。
- 28 个 failed 层少采 994,249 行，按口径如实记 failed，不放宽容差。

> 结论：row 侧数字要去重 PR 合入、重采之后才可信；本文件只保证「读哪几片、算哪些层」这一层是对的。
