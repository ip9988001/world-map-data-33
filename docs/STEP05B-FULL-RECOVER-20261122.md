# STEP05B 全量补采 · 收官账（2026-11-21）

## 一、总账

- 阶段：`05b` —— 县市碎片 05b（5,000~300,000 行）
- 计划：586 层 / 声明 32,606,306 行 / 3 片（每片 200 层，unit_rows=100000）
- 账本覆盖：**586 层**（片文件 3 个）
- 逐态：**ok 438** / capped_by_upstream 0 / empty 15 / partial 104 / failed 29 / skipped_done 0
- 片完成度：应有 **3** 片，有账本 3 片，**未完成 0 片**
- 声明行合计：**31,329,742**；实采行合计：**39,843,844**；差额 -8,514,102（-27.176%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 200 | 200 | 2,943,217 | 完成 |
| 1 | 200 | 200 | 7,165,007 | 完成 |
| 2 | 186 | 186 | 29,735,620 | 完成 |

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | 236,871 | 71 | 236,800 | failed | rc=1 err=batch250:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//E |
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 209,203 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,275 | 0 | 207,275 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,275 | 0 | 207,275 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 125,867 | failed | rc=1 err=? |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,400 | 98,914 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Inval |
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
| `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | partial | 251931 | 371391 | 缺口 -47.42%（实采 371391 / 声明 251931）；跨轮：上轮已有 3 个单元包，本轮只补缺口 |
| `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | failed | 236871 | 71 | rc=1 err=batch250:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtm |
| `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | partial | 227847 | 455698 | 缺口 -100.00%（实采 455698 / 声明 227847） |
| `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | partial | 224317 | 448738 | 缺口 -100.05%（实采 448738 / 声明 224317） |
| `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | partial | 219960 | 439750 | 缺口 -99.92%（实采 439750 / 声明 219960） |
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | failed | 209203 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | failed | 207275 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | failed | 207275 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | partial | 192634 | 385198 | 缺口 -99.96%（实采 385198 / 声明 192634） |
| `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | partial | 190252 | 380483 | 缺口 -99.99%（实采 380483 / 声明 190252） |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | failed | 187871 | 2112000 | rc=1 err=query_fail:svcerr:{"code": 500, "message": "Error performing query operation", "details": []};query_fail:svcerr |
| `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | partial | 183836 | 367080 | 缺口 -99.68%（实采 367080 / 声明 183836） |
| `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | partial | 182659 | 365117 | 缺口 -99.89%（实采 365117 / 声明 182659） |
| `qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` | partial | 181471 | 363000 | 缺口 -100.03%（实采 363000 / 声明 181471）；跨轮：上轮已有 2 个单元包，本轮只补缺口 |
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
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | failed | 100314 | 1400 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | failed | 93362 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | partial | 87697 | 174890 | 缺口 -99.43%（实采 174890 / 声明 87697） |
| `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | partial | 84306 | 168433 | 缺口 -99.79%（实采 168433 / 声明 84306） |
| `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 82602 | 165191 | 缺口 -99.98%（实采 165191 / 声明 82602） |
| `cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` | partial | 81784 | 163221 | 缺口 -99.58%（实采 163221 / 声明 81784）；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
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
| `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | partial | 41010 | 81993 | 缺口 -99.93%（实采 81993 / 声明 41010） |
| `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | failed | 40689 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | failed | 39743 | 39503 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
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
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | failed | 23246 | 20570 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | failed | 23241 | 20567 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
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
| `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | failed | 14470 | 6616 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
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
| `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | failed | 9862 | 9602 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0` | partial | 9704 | 19404 | 缺口 -99.96%（实采 19404 / 声明 9704） |
| `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | failed | 9628 | 9101 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
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
| 6 | `g_arcgis_rest_services_Open_Data_Open_Data_1_FeatureServer_2` | 277,250 | 277,250 | 0.00% | ok |
| 7 | `is_rest_services_Address_1424300337393713068_FeatureServer_0` | 274,644 | 274,644 | 0.00% | ok |
| 8 | `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3` | 268,407 | 536,539 | -99.90% | partial |
| 9 | `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | 268,229 | 536,539 | -100.03% | partial |
| 10 | `0yIuqCBxq_arcgis_rest_services_CNO_Addresses_FeatureServer_0` | 267,730 | 267,730 | 0.00% | ok |
| 11 | `oN_arcgis_rest_services_WASD_Addresses_3_23_FeatureServer_52` | 264,398 | 264,398 | 0.00% | ok |
| 12 | `xLqeJd2jOX_arcgis_rest_services_VC_Addresses_FeatureServer_0` | 263,947 | 263,947 | 0.00% | ok |
| 13 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 251,931 | 371,391 | -47.42% | partial |
| 14 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | 236,871 | 71 | 99.97% | failed |
| 15 | `27_Great_Mississippi_Flood_in_Arkansas_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 16 | `_services_Lower_MS_Sediment_Bottleneck_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 17 | `_Mississippi_Flood_in_Arkansas__Final__WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 18 | `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | 227,847 | 455,698 | -100.00% | partial |
| 19 | `MCHD_Environmental_Health_Public_Service_Map_FeatureServer_0` | 226,508 | 226,508 | 0.00% | ok |
| 20 | `ZHFr6zdgNZuVG0_arcgis_rest_services_Address2_FeatureServer_3` | 226,170 | 226,170 | 0.00% | ok |
| 21 | `arcgis_rest_services_Jeffco_Address_Map_WFL1_FeatureServer_1` | 226,170 | 226,170 | 0.00% | ok |
| 22 | `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | 224,317 | 448,738 | -100.05% | partial |
| 23 | `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` | 221,905 | 221,905 | 0.00% | ok |
| 24 | `is_rest_services_Chester_County_PA_Addresses_FeatureServer_0` | 221,873 | 221,873 | 0.00% | ok |
| 25 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | 219,960 | 439,750 | -99.92% | partial |
| 26 | `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 100.00% | failed |
| 27 | `services_CountyServices_Municipal_Addressing_FeatureServer_2` | 207,685 | 207,685 | 0.00% | ok |
| 28 | `services_Zanna_E911_Sites_Within_8min_Buffer_FeatureServer_1` | 207,581 | 207,581 | 0.00% | ok |
| 29 | `i_arcgis_rest_services_Ada_County_Addresses_FeatureServer_13` | 207,396 | 207,396 | 0.00% | ok |
| 30 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,275 | 0 | 100.00% | failed |
| 31 | `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,275 | 0 | 100.00% | failed |
| 32 | `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1` | 204,910 | 204,910 | 0.00% | ok |
| 33 | `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` | 204,910 | 204,910 | 0.00% | ok |
| 34 | `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | 192,634 | 385,198 | -99.96% | partial |
| 35 | `ervices_AddressPts_DamageAssessment_REA_VIEW_FeatureServer_0` | 190,765 | 190,765 | 0.00% | ok |
| 36 | `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | 190,252 | 380,483 | -99.99% | partial |
| 37 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 187,871 | 2,112,000 | -1024.18% | failed |
| 38 | `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | 183,836 | 367,080 | -99.68% | partial |
| 39 | `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | 182,659 | 365,117 | -99.89% | partial |
| 40 | `qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` | 181,471 | 363,000 | -100.03% | partial |
| 41 | `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0` | 181,440 | 362,701 | -99.90% | partial |
| 42 | `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | 179,493 | 358,962 | -99.99% | partial |
| 43 | `rest_services_E911_Addresses_Hamilton_County_FeatureServer_0` | 173,477 | 173,477 | 0.00% | ok |
| 44 | `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0` | 173,381 | 346,745 | -99.99% | partial |
| 45 | `_rest_services_Site_Addresses_FLOCK_10302024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 46 | `_services_Rutherford_Site_Addresses_11012024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 47 | `s_rest_services_Solano_County_Addresses_WFL1_FeatureServer_0` | 171,954 | 171,954 | 0.00% | ok |
| 48 | `j7_arcgis_rest_services_Addresses_GeneralUse_FeatureServer_0` | 169,896 | 169,896 | 0.00% | ok |
| 49 | `QGwSSLC0l_arcgis_rest_services_t07_Addresses_FeatureServer_0` | 168,093 | 168,093 | 0.00% | ok |
| 50 | `arcgis_rest_services_Addresses_Arcade_Labels_FeatureServer_0` | 161,806 | 161,806 | 0.00% | ok |
| 51 | `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` | 158,719 | 317,114 | -99.80% | partial |
| 52 | `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | 158,408 | 316,405 | -99.74% | partial |
| 53 | `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 54 | `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 55 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 56 | `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0` | 156,027 | 312,042 | -99.99% | partial |
| 57 | `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | 155,653 | 310,782 | -99.66% | partial |
| 58 | `rvices_stratmap19_addresspoints_48027_vector_FeatureServer_0` | 150,676 | 150,676 | 0.00% | ok |
| 59 | `is_rest_services_Barry_County_E911_Map_WFL1_FeatureServer_29` | 147,967 | 147,967 | 0.00% | ok |
| 60 | `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | 147,918 | 295,706 | -99.91% | partial |
| 61 | `LmYGD_arcgis_rest_services_DC_Addresses_WFL1_FeatureServer_0` | 144,111 | 144,111 | 0.00% | ok |
| 62 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_FeatureServer_2` | 139,097 | 139,097 | 0.00% | ok |
| 63 | `cgis_rest_services_Indianapolis_IN_Addresses_FeatureServer_0` | 138,941 | 138,941 | 0.00% | ok |
| 64 | `_rest_services_HenricoCountyGIS_05082023_gdb_FeatureServer_0` | 134,041 | 134,041 | 0.00% | ok |
| 65 | `_arcgis_rest_services_city_address_march2025_FeatureServer_0` | 130,386 | 130,386 | 0.00% | ok |
| 66 | `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` | 130,132 | 260,301 | -100.03% | partial |
| 67 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 68 | `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 69 | `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` | 129,693 | 259,369 | -99.99% | partial |
| 70 | `8JRPoNeQjgcLi_arcgis_rest_services_Addresses_FeatureServer_0` | 128,917 | 128,917 | 0.00% | ok |
| 71 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 100.00% | failed |
| 72 | `est_services_Collier_Addresses_Within_3_Mile_FeatureServer_0` | 121,820 | 121,820 | 0.00% | ok |
| 73 | `is_rest_services_Addresses_2015_Boston_BARI__FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 74 | `ervices_64a951f0_b017_11e6_b4e3_22000b8406af_FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 75 | `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0` | 118,128 | 235,365 | -99.25% | partial |
| 76 | `rvices_WCAddresses20251003_gdb_view_Geocivix_FeatureServer_0` | 118,119 | 118,119 | 0.00% | ok |
| 77 | `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 78 | `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 79 | `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 80 | `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0` | 114,589 | 229,361 | -100.16% | partial |
| 81 | `CRg_arcgis_rest_services_SBCnty_Address_Grid_FeatureServer_0` | 114,312 | 114,312 | 0.00% | ok |
| 82 | `4427d57d2827830_rest_services_Base_Addresses_FeatureServer_0` | 113,649 | 113,649 | 0.00% | ok |
| 83 | `rvices_Situs_for_ConsolidatedPrecincts_AGOL_FeatureServer_51` | 112,728 | 112,728 | 0.00% | ok |
| 84 | `GOi6N4Rq5cqFv_arcgis_rest_services_Addresses_FeatureServer_0` | 112,607 | 112,607 | 0.00% | ok |
| 85 | `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0` | 111,350 | 222,652 | -99.96% | partial |
| 86 | `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0` | 110,991 | 221,935 | -99.96% | partial |
| 87 | `McTk2tV5FXPLX_arcgis_rest_services_Addresses_FeatureServer_0` | 110,848 | 110,848 | 0.00% | ok |
| 88 | `V5FXPLX_arcgis_rest_services_Addresses_Units_FeatureServer_0` | 110,120 | 110,120 | 0.00% | ok |
| 89 | `vices_Yuma_911_Data_Roads_and_Addresses_WFL1_FeatureServer_0` | 108,514 | 108,514 | 0.00% | ok |
| 90 | `GEllMqef1LMjj_arcgis_rest_services_Addresses_FeatureServer_0` | 106,530 | 106,530 | 0.00% | ok |
| 91 | `cgis_rest_services_Delaware_County_E911_Data_FeatureServer_0` | 103,591 | 103,591 | 0.00% | ok |
| 92 | `tg2A1_arcgis_rest_services_vw_dist_addresses_FeatureServer_0` | 100,714 | 100,714 | 0.00% | ok |
| 93 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,400 | 98.60% | failed |
| 94 | `r_arcgis_rest_services_Coryell_address_5Mile_FeatureServer_0` | 99,593 | 99,593 | 0.00% | ok |
| 95 | `s_rest_services_NM911_Address_01_2026_SC_Web_FeatureServer_0` | 99,052 | 99,052 | 0.00% | ok |
| 96 | `wbCJ2GMP_arcgis_rest_services_E911calls_2020_FeatureServer_0` | 98,649 | 98,649 | 0.00% | ok |
| 97 | `arcgis_rest_services_NM911_Address_202506_SC_FeatureServer_0` | 98,409 | 98,409 | 0.00% | ok |
| 98 | `F_arcgis_rest_services_NM911_Address_02_2025_FeatureServer_0` | 97,956 | 97,956 | 0.00% | ok |
| 99 | `F_arcgis_rest_services_NM911_Address_10_2024_FeatureServer_0` | 97,603 | 97,603 | 0.00% | ok |
| 100 | `VWAC8iN_arcgis_rest_services_road_centerline_FeatureServer_0` | 97,499 | 97,499 | 0.00% | ok |
| 101 | `st_services_Springfield_address_density_WFL1_FeatureServer_2` | 97,259 | 97,259 | 0.00% | ok |
| 102 | `nQPdJ0azuLyn_arcgis_rest_services_AddressPts_FeatureServer_0` | 97,202 | 97,202 | 0.00% | ok |
| 103 | `_rest_services_NM911_Address_202401_SC_Web_a_FeatureServer_0` | 96,299 | 96,299 | 0.00% | ok |
| 104 | `gis_rest_services_Address_For_WebApp_Locator_FeatureServer_0` | 96,253 | 96,253 | 0.00% | ok |
| 105 | `is_rest_services_NM911_Address_202301_SC_Web_FeatureServer_0` | 95,212 | 95,212 | 0.00% | ok |
| 106 | `is_rest_services_Forsyth_County_GA_Addresses_FeatureServer_0` | 93,990 | 93,990 | 0.00% | ok |
| 107 | `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,362 | 0 | 100.00% | failed |
| 108 | `u0_arcgis_rest_services_Address_OfflineCopy_FeatureServer_21` | 93,230 | 93,230 | 0.00% | ok |
| 109 | `k6RO1_arcgis_rest_services_HudsonCty_AddrPts_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 110 | `arcgis_rest_services_Hudson_County_Addresses_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 111 | `_arcgis_rest_services_BILLING_ACCT_LOCATIONS_FeatureServer_0` | 91,378 | 91,378 | 0.00% | ok |
| 112 | `is_rest_services_AddressValidationTest2_WFL1_FeatureServer_0` | 91,269 | 91,269 | 0.00% | ok |
| 113 | `iJkq4oXsPh_arcgis_rest_services_Addresses_SR_FeatureServer_0` | 88,553 | 88,553 | 0.00% | ok |
| 114 | `mxCAS_arcgis_rest_services_ClermontAddresses_FeatureServer_0` | 88,301 | 88,301 | 0.00% | ok |
| 115 | `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | 87,697 | 174,890 | -99.43% | partial |
| 116 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | 84,306 | 168,433 | -99.79% | partial |
| 117 | `t_services_Katy_ISD_Harris_County_Addresses_FeatureServer_68` | 83,545 | 83,545 | 0.00% | ok |
| 118 | `I64Ui_arcgis_rest_services_WLAddressAndRoads_FeatureServer_0` | 83,223 | 83,223 | 0.00% | ok |
| 119 | `Spu5VOlu_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 83,144 | 83,144 | 0.00% | ok |
| 120 | `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_FeatureServer_0` | 83,101 | 83,101 | 0.00% | ok |
| 121 | `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | 82,602 | 165,191 | -99.98% | partial |
| 122 | `cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` | 81,784 | 163,221 | -99.58% | partial |
| 123 | `jSxUKayj_arcgis_rest_services_911_Addresses_FeatureServer_58` | 81,591 | 81,591 | 0.00% | ok |
| 124 | `C_arcgis_rest_services_Active_Addresses_2025_FeatureServer_0` | 77,324 | 77,324 | 0.00% | ok |
| 125 | `wLs3iGyK80EW_arcgis_rest_services_911Address_FeatureServer_0` | 75,909 | 75,909 | 0.00% | ok |
| 126 | `arcgis_rest_services_modified_JaCo_addresses_FeatureServer_0` | 75,681 | 75,681 | 0.00% | ok |
| 127 | `_arcgis_rest_services_Addresses_USA_combined_FeatureServer_0` | 75,340 | 75,340 | 0.00% | ok |
| 128 | `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0` | 75,051 | 75,046 | 0.01% | ok |
| 129 | `Cz_arcgis_rest_services_HC_MD_Addresses_10mi_FeatureServer_0` | 74,273 | 74,273 | 0.00% | ok |
| 130 | `C0yIuqCBxq_arcgis_rest_services_Address_2024_FeatureServer_0` | 73,380 | 73,380 | 0.00% | ok |
| 131 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 132 | `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 133 | `CXd1_arcgis_rest_services_Fargo_ND_Addresses_FeatureServer_0` | 72,684 | 72,684 | 0.00% | ok |
| 134 | `_pa_us_arcgis_rest_services_Hosted_Addresses_FeatureServer_0` | 72,208 | 72,208 | 0.00% | ok |
| 135 | `3P_arcgis_rest_services_SiteAddresses_public_FeatureServer_0@TX-2` | 71,798 | 71,798 | 0.00% | ok |
| 136 | `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` | 71,260 | 142,442 | -99.89% | partial |
| 137 | `U5257_arcgis_rest_services_Yonkers_Addresses_FeatureServer_0` | 71,097 | 71,097 | 0.00% | ok |
| 138 | `rcgis_rest_services_AddressPts_20230817_WFL1_FeatureServer_0` | 70,830 | 70,830 | 0.00% | ok |
| 139 | `arcgis_rest_services_AddressPt_20240705_WFL1_FeatureServer_0` | 70,586 | 70,586 | 0.00% | ok |
| 140 | `t3XQ_arcgis_rest_services_AddressPt_20230629_FeatureServer_0` | 70,491 | 70,491 | 0.00% | ok |
| 141 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0` | 70,213 | 70,213 | 0.00% | ok |
| 142 | `f_arcgis_rest_services_Killeen_AddressPoints_FeatureServer_0` | 70,199 | 70,199 | 0.00% | ok |
| 143 | `is_rest_services_Building_Permit_Addresssing_FeatureServer_0` | 69,365 | 69,365 | 0.00% | ok |
| 144 | `0gE_arcgis_rest_services_CenCom_Address_View_FeatureServer_0` | 69,075 | 69,075 | 0.00% | ok |
| 145 | `arverLink_Address_Lookup_20250623_PublicView_FeatureServer_0` | 67,699 | 67,699 | 0.00% | ok |
| 146 | `zOpn2_arcgis_rest_services_Streets_Buidlings_FeatureServer_0` | 65,488 | 65,488 | 0.00% | ok |
| 147 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0` | 64,989 | 129,960 | -99.97% | partial |
| 148 | `_rest_services_Randall_County_Addresses_WFL1_FeatureServer_1` | 64,757 | 64,757 | 0.00% | ok |
| 149 | `Tpwo5_arcgis_rest_services_FullAddress032026_FeatureServer_0` | 64,608 | 64,608 | 0.00% | ok |
| 150 | `AQncZQEtBv_arcgis_rest_services_Address_Clip_FeatureServer_0` | 64,333 | 64,333 | 0.00% | ok |
| 151 | `cgis_rest_services_Cedar_Rapids_IA_Addresses_FeatureServer_0` | 63,767 | 63,767 | 0.00% | ok |
| 152 | `AQdtmx0tv46_arcgis_rest_services_Address_Nye_FeatureServer_6` | 63,594 | 63,594 | 0.00% | ok |
| 153 | `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0` | 63,212 | 126,366 | -99.91% | partial |
| 154 | `5jlmVkpxP_arcgis_rest_services_Online911Data_FeatureServer_0` | 63,126 | 63,126 | 0.00% | ok |
| 155 | `dresses_in_City_Limits___ESD9___Web_Map_WFL1_FeatureServer_1` | 62,839 | 62,839 | 0.00% | ok |
| 156 | `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0` | 62,581 | 125,156 | -99.99% | partial |
| 157 | `InLrxvF0A_arcgis_rest_services_AddressR2_gdb_FeatureServer_0` | 60,615 | 60,615 | 0.00% | ok |
| 158 | `WNInLrxvF0A_arcgis_rest_services_Address_gdb_FeatureServer_0` | 60,326 | 60,326 | 0.00% | ok |
| 159 | `s_rest_services_Marathon_County_WI_Addresses_FeatureServer_0` | 59,998 | 59,998 | 0.00% | ok |
| 160 | `vF0A_arcgis_rest_services_AddressSearchLayer_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 161 | `AAWNInLrxvF0A_arcgis_rest_services_TCAddress_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 162 | `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` | 59,831 | 119,500 | -99.73% | partial |
| 163 | `arcgis_rest_services_Tompkins_County_Address_FeatureServer_0` | 59,711 | 59,711 | 0.00% | ok |
| 164 | `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0` | 58,760 | 117,274 | -99.58% | partial |
| 165 | `rcgis_rest_services_MC_Address_Pts_PMG_View1_FeatureServer_0` | 58,269 | 58,269 | 0.00% | ok |
| 166 | `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` | 58,034 | 116,044 | -99.96% | partial |
| 167 | `d1_arcgis_rest_services_Visalia_CA_Addresses_FeatureServer_0` | 57,934 | 57,934 | 0.00% | ok |
| 168 | `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 99.85% | failed |
| 169 | `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | 56,599 | 113,267 | -100.12% | partial |
| 170 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0` | 55,639 | 55,639 | 0.00% | ok |
| 171 | `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` | 54,793 | 54,793 | 0.00% | ok |
| 172 | `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | 54,644 | 109,268 | -99.96% | partial |
| 173 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0` | 52,649 | 52,649 | 0.00% | ok |
| 174 | `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` | 52,368 | 52,368 | 0.00% | ok |
| 175 | `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6` | 52,022 | 52,022 | 0.00% | ok |
| 176 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | 51,423 | 102,815 | -99.94% | partial |
| 177 | `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 100.00% | failed |
| 178 | `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 100.00% | failed |
| 179 | `st_services_A4_Landscape_addressverification_FeatureServer_1` | 49,808 | 49,808 | 0.00% | ok |
| 180 | `com_arcgis_rest_services_CommunityAddressing_FeatureServer_0` | 49,804 | 49,804 | 0.00% | ok |
| 181 | `teAddresses_ecd2ff39fbb34f39a2ec415fd784331b_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 182 | `teAddresses_b786541565b5475593a786a08ba6b3e2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 183 | `sses_public_a000778ae1664a348de916831f1a0ac0_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 184 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 185 | `teAddresses_1809c74f027741ce815587367a5cfd68_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 186 | `teAddresses_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 187 | `teAddresses_25f96256e2164540bc18abbff8a9d5c2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 188 | `sses_public_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 189 | `vN_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 190 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 191 | `d1DIvN_arcgis_rest_services_SiteAddresses__1_FeatureServer_1` | 49,802 | 49,802 | 0.00% | ok |
| 192 | `sses_public_a2522c3dfde94f6da7500df892abf9aa_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 193 | `sses_public_fa4be22034f14c15a3a589dd7009ca64_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 194 | `0JE2L2xUd_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 195 | `sses_public_e7c532395de343e38e58a8463128cfb7_FeatureServer_0` | 49,800 | 49,800 | 0.00% | ok |
| 196 | `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 100.00% | failed |
| 197 | `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0` | 49,100 | 98,176 | -99.95% | partial |
| 198 | `eajjke_arcgis_rest_services_Addresses_Rogers_FeatureServer_0` | 48,889 | 48,889 | 0.00% | ok |
| 199 | `aNxg1PvwI_arcgis_rest_services_All_Addresses_FeatureServer_0` | 48,666 | 48,666 | 0.00% | ok |
| 200 | `cgis_rest_services_NRSA_Address_Locator_WFL1_FeatureServer_8` | 48,634 | 48,634 | 0.00% | ok |
| 201 | `KpsCnqD7H_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 48,448 | 48,448 | 0.00% | ok |
| 202 | `Geezhu2j_arcgis_rest_services_E911_Addresses_FeatureServer_0` | 48,443 | 48,443 | 0.00% | ok |
| 203 | `Ilt_arcgis_rest_services_Clinton_Address_Pts_FeatureServer_0` | 47,510 | 47,510 | 0.00% | ok |
| 204 | `_arcgis_rest_services_BG911_Address_20250501_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 205 | `Bq9hgug_arcgis_rest_services_BG911_Addresses_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 206 | `e_Rollout__Days_of_Service_Per_Address__WFL1_FeatureServer_1` | 46,949 | 46,949 | 0.00% | ok |
| 207 | `st_services_Schools_ChathamSchools_AddressPoints_MapServer_0` | 46,456 | 46,456 | 0.00% | ok |
| 208 | `gis_rest_services_CountyAddress2023_CHE_View_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 209 | `I64Ui_arcgis_rest_services_CountyAddress2023_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 210 | `qTGWY_arcgis_rest_services_JoCo_Site_Address_FeatureServer_1` | 45,019 | 45,019 | 0.00% | ok |
| 211 | `71LO_arcgis_rest_services_Addresses_CivQuest_FeatureServer_0` | 45,012 | 45,012 | 0.00% | ok |
| 212 | `2kwz79KUqUvxC_arcgis_rest_services_Addresses_FeatureServer_0` | 44,833 | 44,833 | 0.00% | ok |
| 213 | `wFbS_arcgis_rest_services_Chemungaddress_pts_FeatureServer_0` | 44,642 | 44,642 | 0.00% | ok |
| 214 | `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` | 43,499 | 86,993 | -99.99% | partial |
| 215 | `_arcgis_rest_services_Addresses_NOT_ELIGIBLE_FeatureServer_0` | 43,411 | 43,411 | 0.00% | ok |
| 216 | `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0` | 43,405 | 86,789 | -99.95% | partial |
| 217 | `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | 43,042 | 86,008 | -99.82% | partial |
| 218 | `s_rest_services_CityAddresses2022bu_CHE_view_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 219 | `4Ui_arcgis_rest_services_CityAddresses2022bu_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 220 | `s_rest_services_Raleigh_Co_EOC_Address_Sites_FeatureServer_0` | 42,165 | 42,165 | 0.00% | ok |
| 221 | `3kMP_arcgis_rest_services_E911AddressforSOMA_FeatureServer_0` | 41,887 | 41,887 | 0.00% | ok |
| 222 | `est_services_NormanResidentialTrashAddresses_FeatureServer_0` | 41,811 | 41,811 | 0.00% | ok |
| 223 | `s_rest_services_Master_Address_List_Aug_2026_FeatureServer_0` | 41,460 | 41,460 | 0.00% | ok |
| 224 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10` | 41,175 | 41,175 | 0.00% | ok |
| 225 | `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | 41,010 | 81,993 | -99.93% | partial |
| 226 | `OU_arcgis_rest_services_Addresses_SIO_Hosted_FeatureServer_0` | 40,752 | 40,752 | 0.00% | ok |
| 227 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | 40,689 | 0 | 100.00% | failed |
| 228 | `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 229 | `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 230 | `1_arcgis_rest_services_Bismarck_ND_Addresses_FeatureServer_0` | 40,568 | 40,568 | 0.00% | ok |
| 231 | `IzAwdHlO_arcgis_rest_services_Address_hosted_FeatureServer_0` | 40,255 | 40,255 | 0.00% | ok |
| 232 | `u6oHu4Z_arcgis_rest_services_SITUS_PUB_CBB_2_FeatureServer_0` | 39,951 | 39,951 | 0.00% | ok |
| 233 | `m_nEIrIdcFpdK28ibf_arcgis_rest_services_E911_FeatureServer_1` | 39,855 | 39,855 | 0.00% | ok |
| 234 | `p_arcgis_rest_services_LAFO_ADDRESS_12_17_13_FeatureServer_0` | 39,847 | 39,847 | 0.00% | ok |
| 235 | `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | 39,743 | 39,503 | 0.60% | failed |
| 236 | `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54` | 39,239 | 39,239 | 0.00% | ok |
| 237 | `rcgis_rest_services_Res_Address_Demographics_FeatureServer_1` | 39,114 | 39,114 | 0.00% | ok |
| 238 | `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` | 38,656 | 77,304 | -99.98% | partial |
| 239 | `d_Waste__Days_of_Service_Per_Address_092424_FeatureServer_52` | 38,389 | 38,389 | 0.00% | ok |
| 240 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address_FeatureServer_0` | 38,345 | 38,345 | 0.00% | ok |
| 241 | `rcgis_rest_services_Daly_City_Addresses_AGOL_FeatureServer_2` | 38,299 | 38,299 | 0.00% | ok |
| 242 | `Ypus4pYH0S_arcgis_rest_services_Site_Address_FeatureServer_4` | 37,961 | 37,961 | 0.00% | ok |
| 243 | `rest_services_CarthageWardsandaddresses_WFL1_FeatureServer_1` | 37,764 | 37,764 | 0.00% | ok |
| 244 | `is_rest_services_Madison_County_KY_Addresses_FeatureServer_1` | 37,446 | 37,446 | 0.00% | ok |
| 245 | `QYTTiP6CrfEsw_arcgis_rest_services_Addresses_FeatureServer_0` | 37,276 | 37,276 | 0.00% | ok |
| 246 | `_arcgis_rest_services_Flagstaff_AZ_Addresses_FeatureServer_0` | 37,174 | 37,174 | 0.00% | ok |
| 247 | `zUpjDtspiBG0j_arcgis_rest_services_E911_Copy_FeatureServer_0` | 37,066 | 37,066 | 0.00% | ok |
| 248 | `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0` | 36,725 | 73,441 | -99.98% | partial |
| 249 | `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_FeatureServer_0` | 36,292 | 36,292 | 0.00% | ok |
| 250 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_FeatureServer_1` | 36,292 | 36,292 | 0.00% | ok |
| 251 | `gT_arcgis_rest_services_USU_Addressing_view_FeatureServer_26` | 36,150 | 36,150 | 0.00% | ok |
| 252 | `ofS_arcgis_rest_services_Taos_E911_Addresses_FeatureServer_0` | 35,970 | 35,970 | 0.00% | ok |
| 253 | `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,810 | 35,810 | 0.00% | ok |
| 254 | `rcgis_rest_services_CTSI_AddressChecker_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 255 | `s_rest_services_CTSI_Address_Check_2023_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 256 | `PlhvQwvs_arcgis_rest_services_E911_Addrs_Pts_FeatureServer_0` | 35,637 | 35,637 | 0.00% | ok |
| 257 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | 35,212 | 70,419 | -99.99% | partial |
| 258 | `fMdTkPeHLCobS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,199 | 35,199 | 0.00% | ok |
| 259 | `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 260 | `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 261 | `arcgis_rest_services_Alexandria_VA_Addresses_FeatureServer_0` | 34,927 | 34,927 | 0.00% | ok |
| 262 | `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0` | 34,840 | 69,679 | -100.00% | partial |
| 263 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | 34,683 | 34,683 | 0.00% | ok |
| 264 | `1p_arcgis_rest_services_ADDRESS_20230403_CoB_FeatureServer_0` | 34,536 | 34,536 | 0.00% | ok |
| 265 | `pMfHt82xFG_arcgis_rest_services_RouteAddress_FeatureServer_0` | 34,495 | 34,495 | 0.00% | ok |
| 266 | `cgis_rest_services_Master_Addresses_for_Grid_FeatureServer_0` | 34,386 | 34,386 | 0.00% | ok |
| 267 | `kOGGtW27pGICf_arcgis_rest_services_Addresses_FeatureServer_0` | 34,063 | 34,063 | 0.00% | ok |
| 268 | `cgis_rest_services_Sarpy_County_NE_Addresses_FeatureServer_1` | 33,980 | 33,980 | 0.00% | ok |
| 269 | `rcgis_rest_services_Essex_Address_Pts_9_9_25_FeatureServer_0` | 33,904 | 33,904 | 0.00% | ok |
| 270 | `WCoI_arcgis_rest_services_20260601_Addresses_FeatureServer_0` | 33,856 | 33,856 | 0.00% | ok |
| 271 | `cgis_rest_services_Franklin_Co_911_Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 272 | `cgis_rest_services_FranklinCoVA_911Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 273 | `1_arcgis_rest_services_Longview_TX_Addresses_FeatureServer_0` | 33,603 | 33,603 | 0.00% | ok |
| 274 | `S1a_arcgis_rest_services_Address_Mailing_Map_FeatureServer_1` | 33,587 | 33,587 | 0.00% | ok |
| 275 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_FeatureServer_0` | 33,215 | 33,215 | 0.00% | ok |
| 276 | `cgis_rest_services_Riley_County_KS_Addresses_FeatureServer_0` | 33,193 | 33,193 | 0.00% | ok |
| 277 | `st_services_Vector_Tile_Site_Address_Labels_FeatureServer_57` | 32,917 | 32,917 | 0.00% | ok |
| 278 | `_arcgis_rest_services_zoningAddressingSearch_FeatureServer_0` | 32,625 | 32,625 | 0.00% | ok |
| 279 | `_org_gisarcweb_rest_services_Base_Base_Addresses_MapServer_0` | 32,622 | 32,622 | 0.00% | ok |
| 280 | `j7VSF_arcgis_rest_services_TemeculaAddresses_FeatureServer_0` | 32,615 | 32,615 | 0.00% | ok |
| 281 | `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0` | 32,353 | 64,689 | -99.95% | partial |
| 282 | `BpZX2wFbS_arcgis_rest_services_911addressing_FeatureServer_0` | 32,197 | 32,197 | 0.00% | ok |
| 283 | `rest_services_Cherokee_Address_Analysis_WFL1_FeatureServer_0` | 32,167 | 32,167 | 0.00% | ok |
| 284 | `VDElDOMEad_arcgis_rest_services_WayneAddress_FeatureServer_0` | 31,980 | 31,980 | 0.00% | ok |
| 285 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses_FeatureServer_0` | 31,520 | 31,520 | 0.00% | ok |
| 286 | `arcgis_rest_services_FranklinCountyAddresses_FeatureServer_0` | 31,516 | 31,516 | 0.00% | ok |
| 287 | `ez8fHeIiDRbgb_arcgis_rest_services_Addresses_FeatureServer_0` | 30,935 | 30,935 | 0.00% | ok |
| 288 | `aLg_arcgis_rest_services_Address_Hemet031325_FeatureServer_0` | 30,879 | 30,879 | 0.00% | ok |
| 289 | `rcgis_rest_services_Buildings_and_Addresses_FeatureServer_17` | 30,856 | 30,856 | 0.00% | ok |
| 290 | `s_rest_services_Rural_Addresses__Label_Only__FeatureServer_0` | 30,747 | 30,747 | 0.00% | ok |
| 291 | `_arcgis_rest_services_EnerGov_Test_Map1_WFL1_FeatureServer_3` | 30,649 | 30,649 | 0.00% | ok |
| 292 | `is_rest_services_Lead_Service_Line_Addresses_FeatureServer_0` | 30,565 | 30,565 | 0.00% | ok |
| 293 | `DgvxltnFwP_arcgis_rest_services_NG911_Layers_FeatureServer_1` | 30,273 | 30,273 | 0.00% | ok |
| 294 | `Mk18pL_arcgis_rest_services_Coffee_Addresses_FeatureServer_0` | 29,524 | 29,524 | 0.00% | ok |
| 295 | `xLBcrikqFM0vkoy_arcgis_rest_services_Address_FeatureServer_0` | 29,507 | 29,507 | 0.00% | ok |
| 296 | `4x6y8cTIstSBE_arcgis_rest_services_Addresses_FeatureServer_0` | 29,448 | 29,448 | 0.00% | ok |
| 297 | `TOM4lipn_arcgis_rest_services_Addresses_2023_FeatureServer_0` | 29,170 | 29,170 | 0.00% | ok |
| 298 | `8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1` | 28,996 | 28,996 | 0.00% | ok |
| 299 | `_arcgis_rest_services_Logan_County_Addresses_FeatureServer_0` | 28,571 | 28,571 | 0.00% | ok |
| 300 | `rcgis_rest_services_Bedford_County_Addresses_FeatureServer_0` | 28,352 | 28,352 | 0.00% | ok |
| 301 | `est_services_Street_Sweeping_Pilot_Addresses_FeatureServer_0` | 28,338 | 28,338 | 0.00% | ok |
| 302 | `rest_services_Hurricane_Ian_Damage_Addresses_FeatureServer_0` | 27,912 | 27,912 | 0.00% | ok |
| 303 | `_arcgis_rest_services_TehamaCounty_NG911_gdb_FeatureServer_8` | 27,565 | 27,565 | 0.00% | ok |
| 304 | `ices_City_of_Cuyahoga_Falls_Addressing_WFL1_FeatureServer_11` | 27,479 | 27,479 | 0.00% | ok |
| 305 | `vices_Campbell_County__VA_Broadband_Map_WFL1_FeatureServer_0` | 27,456 | 27,456 | 0.00% | ok |
| 306 | `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0` | 27,213 | 27,213 | 0.00% | ok |
| 307 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0` | 27,058 | 27,058 | 0.00% | ok |
| 308 | `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` | 26,965 | 26,965 | 0.00% | ok |
| 309 | `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0` | 26,903 | 26,903 | 0.00% | ok |
| 310 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0` | 26,684 | 26,684 | 0.00% | ok |
| 311 | `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` | 26,510 | 26,510 | 0.00% | ok |
| 312 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | 26,410 | 52,891 | -100.27% | partial |
| 313 | `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | 26,410 | 52,891 | -100.27% | partial |
| 314 | `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | 26,320 | 52,635 | -99.98% | partial |
| 315 | `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 26,021 | 26,021 | 0.00% | ok |
| 316 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | 25,834 | 51,668 | -100.00% | partial |
| 317 | `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | 25,817 | 51,608 | -99.90% | partial |
| 318 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0` | 25,582 | 25,582 | 0.00% | ok |
| 319 | `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` | 25,427 | 25,427 | 0.00% | ok |
| 320 | `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20` | 25,367 | 25,367 | 0.00% | ok |
| 321 | `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | 25,091 | 50,069 | -99.55% | partial |
| 322 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1` | 25,081 | 25,081 | 0.00% | ok |
| 323 | `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` | 24,987 | 24,987 | 0.00% | ok |
| 324 | `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` | 24,529 | 24,529 | 0.00% | ok |
| 325 | `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0` | 24,465 | 24,465 | 0.00% | ok |
| 326 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0` | 24,398 | 24,398 | 0.00% | ok |
| 327 | `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` | 24,136 | 24,136 | 0.00% | ok |
| 328 | `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0` | 24,123 | 24,123 | 0.00% | ok |
| 329 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0` | 24,109 | 24,109 | 0.00% | ok |
| 330 | `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` | 24,107 | 24,107 | 0.00% | ok |
| 331 | `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0` | 24,045 | 24,045 | 0.00% | ok |
| 332 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0` | 23,950 | 23,950 | 0.00% | ok |
| 333 | `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | 23,869 | 47,732 | -99.97% | partial |
| 334 | `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54` | 23,859 | 23,859 | 0.00% | ok |
| 335 | `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | 23,819 | 47,237 | -98.32% | partial |
| 336 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | 23,776 | 47,553 | -100.00% | partial |
| 337 | `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | 23,338 | 46,672 | -99.98% | partial |
| 338 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | 11.51% | failed |
| 339 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | 11.51% | failed |
| 340 | `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0` | 23,141 | 23,141 | 0.00% | ok |
| 341 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0` | 23,136 | 23,136 | 0.00% | ok |
| 342 | `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` | 23,106 | 23,106 | 0.00% | ok |
| 343 | `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0` | 22,930 | 22,930 | 0.00% | ok |
| 344 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 345 | `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 22,248 | 44,495 | -100.00% | partial |
| 346 | `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0` | 22,208 | 22,208 | 0.00% | ok |
| 347 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0` | 21,951 | 21,951 | 0.00% | ok |
| 348 | `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` | 21,789 | 21,789 | 0.00% | ok |
| 349 | `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | 21,770 | 43,524 | -99.93% | partial |
| 350 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | 21,721 | 21,721 | 0.00% | ok |
| 351 | `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` | 21,706 | 21,706 | 0.00% | ok |
| 352 | `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 353 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0` | 21,108 | 21,108 | 0.00% | ok |
| 354 | `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` | 21,092 | 21,092 | 0.00% | ok |
| 355 | `arcgis_rest_services_Master_Address_List_New_FeatureServer_0` | 21,055 | 21,055 | 0.00% | ok |
| 356 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0` | 21,006 | 21,006 | 0.00% | ok |
| 357 | `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` | 20,861 | 20,861 | 0.00% | ok |
| 358 | `cgis_rest_services_AddressesWithElectionData_FeatureServer_0` | 20,202 | 20,202 | 0.00% | ok |
| 359 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1` | 20,088 | 20,088 | 0.00% | ok |
| 360 | `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | 20,040 | 40,080 | -100.00% | partial |
| 361 | `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0` | 20,014 | 20,014 | 0.00% | ok |
| 362 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0` | 19,966 | 19,966 | 0.00% | ok |
| 363 | `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` | 19,812 | 19,812 | 0.00% | ok |
| 364 | `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0` | 19,767 | 19,767 | 0.00% | ok |
| 365 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0` | 19,339 | 19,339 | 0.00% | ok |
| 366 | `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` | 19,308 | 19,308 | 0.00% | ok |
| 367 | `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | 19,161 | 38,284 | -99.80% | partial |
| 368 | `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0` | 19,154 | 19,154 | 0.00% | ok |
| 369 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0` | 19,123 | 19,123 | 0.00% | ok |
| 370 | `is_rest_services_Gloucester_County_Addresses_FeatureServer_0` | 19,037 | 19,037 | 0.00% | ok |
| 371 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0` | 18,822 | 18,822 | 0.00% | ok |
| 372 | `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | 18,526 | 37,031 | -99.89% | partial |
| 373 | `RnMdg5KWv_arcgis_rest_services_911_Addresses_FeatureServer_0` | 18,406 | 18,406 | 0.00% | ok |
| 374 | `xkcSkFAjt_arcgis_rest_services_911_Addresses_FeatureServer_0` | 18,332 | 18,332 | 0.00% | ok |
| 375 | `gis_rest_services_Limestone_County_Addresses_FeatureServer_0` | 18,275 | 18,275 | 0.00% | ok |
| 376 | `_arcgis_rest_services_WyomingCountyAddresses_FeatureServer_0` | 18,194 | 18,194 | 0.00% | ok |
| 377 | `rcgis_rest_services_Mailing_Address_Map_WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 378 | `gis_rest_services_Mailing_Address_Map___WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 379 | `gis_rest_services_Mailing_Address_Map_2_WFL1_FeatureServer_1` | 18,090 | 18,090 | 0.00% | ok |
| 380 | `m_x7Yxpfpio5GuQWF2_arcgis_rest_services_E911_FeatureServer_0` | 18,028 | 18,028 | 0.00% | ok |
| 381 | `_rest_services_Oxford_911_Address_View_Layer_FeatureServer_1` | 17,976 | 35,950 | -99.99% | partial |
| 382 | `wY8_arcgis_rest_services_Address_Ranges_WFL1_FeatureServer_0` | 17,908 | 17,908 | 0.00% | ok |
| 383 | `kIrNAR_arcgis_rest_services_E911_Share_Files_FeatureServer_0` | 17,883 | 17,883 | 0.00% | ok |
| 384 | `YdlWlBxzX_arcgis_rest_services_Boone_Address_FeatureServer_0` | 17,833 | 17,833 | 0.00% | ok |
| 385 | `cgis_rest_services_Skokie_Base_Address_View_FeatureServer_33` | 17,731 | 35,462 | -100.00% | partial |
| 386 | `pNK5CvU_arcgis_rest_services_HempV_Addresses_FeatureServer_0` | 17,586 | 17,586 | 0.00% | ok |
| 387 | `meepNh_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 17,584 | 17,584 | 0.00% | ok |
| 388 | `1N7Y1EilGjehZ_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 17,575 | 17,575 | 0.00% | ok |
| 389 | `WuVPEmGK_arcgis_rest_services_Addresses_View_FeatureServer_0` | 17,498 | 17,498 | 0.00% | ok |
| 390 | `is_rest_services_Cottage_Grove_Address_Point_FeatureServer_0` | 17,425 | 17,425 | 0.00% | ok |
| 391 | `is_rest_services_Bureau_County_911_Addresses_FeatureServer_0` | 17,341 | 17,341 | 0.00% | ok |
| 392 | `ysZUz_arcgis_rest_services_Carroll_Addresses_FeatureServer_0` | 17,328 | 34,653 | -99.98% | partial |
| 393 | `cjlmqkA8ypi4T_arcgis_rest_services_Addresses_FeatureServer_0` | 17,308 | 17,308 | 0.00% | ok |
| 394 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 17,301 | 17,326 | -0.14% | ok |
| 395 | `is_rest_services_Master_Address_Database_MAD_FeatureServer_0` | 17,222 | 17,222 | 0.00% | ok |
| 396 | `TymXTmwPsPzPHRU_arcgis_rest_services_Address_FeatureServer_0` | 17,199 | 17,199 | 0.00% | ok |
| 397 | `ces_Pueblo_County_Addresses_Evacuation_Times_FeatureServer_0` | 17,168 | 17,168 | 0.00% | ok |
| 398 | `ces_911_Address_Street_Review_WFL1_view_only_FeatureServer_0` | 16,997 | 17,013 | -0.09% | ok |
| 399 | `So_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 16,929 | 16,929 | 0.00% | ok |
| 400 | `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | 16,730 | 0 | 100.00% | failed |
| 401 | `gis_rest_services_SANGIS_AddressAPN_07312024_FeatureServer_0` | 16,657 | 16,657 | 0.00% | ok |
| 402 | `0_arcgis_rest_services_2022_Sep_01_Addresses_FeatureServer_0` | 16,579 | 16,579 | 0.00% | ok |
| 403 | `0_arcgis_rest_services_Duncanville_Addresses_FeatureServer_0` | 16,574 | 16,574 | 0.00% | ok |
| 404 | `rest_services_Addresses_Clark_County_WI_2019_FeatureServer_0` | 16,569 | 16,569 | 0.00% | ok |
| 405 | `gis_rest_services_GRANT_Address_ClerksOffice_FeatureServer_0` | 16,517 | 16,517 | 0.00% | ok |
| 406 | `aAg05xQLgo7_arcgis_rest_services_WGS_Address_FeatureServer_0` | 16,393 | 16,393 | 0.00% | ok |
| 407 | `4OueTcnj_arcgis_rest_services_just_addresses_FeatureServer_0` | 15,898 | 15,898 | 0.00% | ok |
| 408 | `cgis_rest_services_AtascaderoAddresses082025_FeatureServer_0` | 15,830 | 15,830 | 0.00% | ok |
| 409 | `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-1` | 15,033 | 15,033 | 0.00% | ok |
| 410 | `6Z_arcgis_rest_services_N911_Addresses__View_FeatureServer_0` | 15,024 | 29,989 | -99.61% | partial |
| 411 | `8hGN_arcgis_rest_services_Polk_Addresses_GAC_FeatureServer_0` | 15,015 | 15,015 | 0.00% | ok |
| 412 | `jld0x0gpn_arcgis_rest_services_E911Addresses_FeatureServer_0` | 14,842 | 14,842 | 0.00% | ok |
| 413 | `X_arcgis_rest_services_County_P_Address_View_FeatureServer_0` | 14,758 | 14,758 | 0.00% | ok |
| 414 | `kTU5o6Z_arcgis_rest_services_Addressing_AGOL_FeatureServer_0` | 14,712 | 14,712 | 0.00% | ok |
| 415 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | 54.28% | failed |
| 416 | `C2HwTkBAlth_arcgis_rest_services_Address_gdb_FeatureServer_0` | 14,389 | 14,389 | 0.00% | ok |
| 417 | `rent_Site_Addresses_and_Entrance_Points_view_FeatureServer_0` | 14,361 | 28,710 | -99.92% | partial |
| 418 | `KPa_arcgis_rest_services_overture_address_sd_FeatureServer_0` | 14,350 | 14,350 | 0.00% | ok |
| 419 | `rcgis_rest_services_Newberg_Addresses_2_view_FeatureServer_0` | 14,236 | 28,470 | -99.99% | partial |
| 420 | `ervices_Lee_County_E911_Addresses_and_Roads_FeatureServer_20` | 14,215 | 14,215 | 0.00% | ok |
| 421 | `sses_public_35d07adabaff4ddba616f6f365b8954e_FeatureServer_0` | 14,203 | 14,203 | 0.00% | ok |
| 422 | `_arcgis_rest_services_911_Addresses_Website2_FeatureServer_0` | 14,164 | 28,282 | -99.68% | partial |
| 423 | `8SWPG8KZ6r_arcgis_rest_services_911Addresses_FeatureServer_0` | 13,932 | 13,932 | 0.00% | ok |
| 424 | `arcgis_rest_services_Short_Term_Rentals_WFL1_FeatureServer_1` | 13,863 | 13,863 | 0.00% | ok |
| 425 | `m7axC2dD_arcgis_rest_services_WascoAddresses_FeatureServer_5` | 13,807 | 13,807 | 0.00% | ok |
| 426 | `hP2NPfFE_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 13,677 | 13,677 | 0.00% | ok |
| 427 | `Ia_arcgis_rest_services_County_911_Addresses_FeatureServer_0` | 13,629 | 13,629 | 0.00% | ok |
| 428 | `rcgis_rest_services_Johns_Creek_GA_Addresses_FeatureServer_1` | 13,540 | 13,540 | 0.00% | ok |
| 429 | `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0` | 13,353 | 26,705 | -99.99% | partial |
| 430 | `ELbQdlhsJLcCM_arcgis_rest_services_Addresses_FeatureServer_0` | 13,329 | 13,329 | 0.00% | ok |
| 431 | `kh71mtnDG_arcgis_rest_services_E911addresses_FeatureServer_0` | 13,205 | 13,205 | 0.00% | ok |
| 432 | `aR3VIVeAhJdr_arcgis_rest_services_AddressBPs_FeatureServer_0` | 13,190 | 13,190 | 0.00% | ok |
| 433 | `gis_rest_services_AddressList_Update20250311_FeatureServer_0` | 13,166 | 13,166 | 0.00% | ok |
| 434 | `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | 13,120 | 13,120 | 0.00% | ok |
| 435 | `MJrpz61FbvL5t_arcgis_rest_services_Addresses_FeatureServer_0` | 13,058 | 13,058 | 0.00% | ok |
| 436 | `is_rest_services_Grady_Site_Addresses_Public_FeatureServer_0` | 12,995 | 25,981 | -99.93% | partial |
| 437 | `st_services_VacantResidentialProperties_WFL1_FeatureServer_0` | 12,933 | 12,933 | 0.00% | ok |
| 438 | `dlWlBxzX_arcgis_rest_services_Marion_Address_FeatureServer_1` | 12,896 | 12,896 | 0.00% | ok |
| 439 | `rcgis_rest_services_VT_Data___E911_Landmarks_FeatureServer_0` | 12,867 | 12,867 | 0.00% | ok |
| 440 | `BYQ9pcCt_arcgis_rest_services_e911_pt_txdist_FeatureServer_0` | 12,670 | 12,670 | 0.00% | ok |
| 441 | `m_jOKMO9vKmc98J4JC_arcgis_rest_services_E911_FeatureServer_0` | 12,649 | 12,649 | 0.00% | ok |
| 442 | `cgis_rest_services_Site_Addresses_View_Layer_FeatureServer_0` | 12,642 | 25,281 | -99.98% | partial |
| 443 | `teAddresses_1a8d5e9d05674ad599c70df5dfdd4265_FeatureServer_0` | 12,642 | 25,281 | -99.98% | partial |
| 444 | `teAddresses_176dcf6d135741fcbc3bf17da5aa7aff_FeatureServer_0` | 12,592 | 12,592 | 0.00% | ok |
| 445 | `dlWlBxzX_arcgis_rest_services_Searcy_Address_FeatureServer_0` | 12,573 | 12,573 | 0.00% | ok |
| 446 | `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_FeatureServer_0` | 12,445 | 24,807 | -99.33% | partial |
| 447 | `aAg05xQLgo7_arcgis_rest_services_SiteAddress_FeatureServer_0` | 12,411 | 12,411 | 0.00% | ok |
| 448 | `l_Assessor_parcel_Map_June_06_09_2023_WFL1_FeatureServer_219` | 12,309 | 12,309 | 0.00% | ok |
| 449 | `st_services_Arlington_Addresses_current_view_FeatureServer_0` | 12,284 | 24,570 | -100.02% | partial |
| 450 | `drG_arcgis_rest_services_Arlington_Addresses_FeatureServer_0` | 12,284 | 24,570 | -100.02% | partial |
| 451 | `5n_arcgis_rest_services_City_Limit_Addresses_FeatureServer_0` | 12,152 | 24,296 | -99.93% | partial |
| 452 | `services_BRIC_WRC_Situs_Address_LookUp_Table_FeatureServer_0` | 12,115 | 12,115 | 0.00% | ok |
| 453 | `XhtlWzOFCTkO_arcgis_rest_services_AddressPts_FeatureServer_0` | 11,978 | 11,978 | 0.00% | ok |
| 454 | `wlO_arcgis_rest_services_Master_Address_List_FeatureServer_0` | 11,959 | 11,959 | 0.00% | ok |
| 455 | `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0` | 11,902 | 11,901 | 0.01% | ok |
| 456 | `JE9B_arcgis_rest_services_Newberg_Addresses__FeatureServer_0` | 11,817 | 23,632 | -99.98% | partial |
| 457 | `DdwE7LMrYrEMJ_arcgis_rest_services_Addresses_FeatureServer_1` | 11,801 | 23,585 | -99.86% | partial |
| 458 | `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5` | 11,641 | 11,641 | 0.00% | ok |
| 459 | `arcgis_rest_services_BTV_e911_Address_Layers_FeatureServer_0` | 11,475 | 22,937 | -99.89% | partial |
| 460 | `arcgis_rest_services_PAunderservedstructures_FeatureServer_0` | 11,469 | 11,469 | 0.00% | ok |
| 461 | `Kw_arcgis_rest_services_Situs_Address_Public_FeatureServer_0` | 11,385 | 22,770 | -100.00% | partial |
| 462 | `kFjYDrl_arcgis_rest_services_Address06192026_FeatureServer_0` | 11,221 | 11,221 | 0.00% | ok |
| 463 | `ILCm3hbWNTZLH_arcgis_rest_services_Addresses_FeatureServer_0` | 11,219 | 11,219 | 0.00% | ok |
| 464 | `Us_arcgis_rest_services_OC_Site_Address_2023_FeatureServer_0` | 11,076 | 11,076 | 0.00% | ok |
| 465 | `kFjYDrl_arcgis_rest_services_Address02202025_FeatureServer_0` | 10,821 | 10,821 | 0.00% | ok |
| 466 | `lqccxOHLu_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 10,667 | 10,667 | 0.00% | ok |
| 467 | `t_services_Public_20Notification_20Addresses_FeatureServer_0` | 10,606 | 21,211 | -99.99% | partial |
| 468 | `1mtnDG_arcgis_rest_services_Worth__ADDRESSES_FeatureServer_0` | 10,572 | 10,572 | 0.00% | ok |
| 469 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | 10,564 | 0 | 100.00% | failed |
| 470 | `t_services_Perry_County_Address_Geocode_v1_1_FeatureServer_0` | 10,489 | 10,489 | 0.00% | ok |
| 471 | `4soU_arcgis_rest_services_Site_Addresses_gdb_FeatureServer_0` | 10,465 | 10,465 | 0.00% | ok |
| 472 | `rWTl_arcgis_rest_services_Harrison_Addresses_FeatureServer_0` | 10,330 | 10,330 | 0.00% | ok |
| 473 | `kFjYDrl_arcgis_rest_services_Address11292023_FeatureServer_0` | 10,216 | 10,216 | 0.00% | ok |
| 474 | `FjYDrl_arcgis_rest_services_Address_12102021_FeatureServer_0` | 9,969 | 9,969 | 0.00% | ok |
| 475 | `Qwt3_arcgis_rest_services_Address_Layer_view_FeatureServer_0` | 9,866 | 9,866 | 0.00% | ok |
| 476 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 9,862 | 9,602 | 2.64% | failed |
| 477 | `tkincounty_com_arcgis_rest_services_Full_Address_MapServer_1` | 9,813 | 9,813 | 0.00% | ok |
| 478 | `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0` | 9,704 | 19,404 | -99.96% | partial |
| 479 | `p_arcgis_rest_services_Addresses_Public_View_FeatureServer_0` | 9,672 | 9,672 | 0.00% | ok |
| 480 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 9,628 | 9,101 | 5.47% | failed |
| 481 | `QSIEviNS_arcgis_rest_services_Addresses_2025_FeatureServer_3` | 9,536 | 9,536 | 0.00% | ok |
| 482 | `_server_rest_services_Aspen_AspenEditEnabled_FeatureServer_0` | 9,451 | 9,452 | -0.01% | ok |
| 483 | `s___Pulse_of_OC_Updated_Draft___Site_Address_FeatureServer_0` | 9,420 | 9,420 | 0.00% | ok |
| 484 | `jyn_arcgis_rest_services_Full_Street_Address_FeatureServer_0` | 9,371 | 9,371 | 0.00% | ok |
| 485 | `st_services_Winneshiek_County_Address_Points_FeatureServer_1` | 9,211 | 9,211 | 0.00% | ok |
| 486 | `QpZPT9qY_arcgis_rest_services_TOD_ADDRESS_IN_FeatureServer_0` | 9,149 | 9,149 | 0.00% | ok |
| 487 | `_arcgis_rest_services_Address_Pnts_ElSegundo_FeatureServer_2` | 9,137 | 9,137 | 0.00% | ok |
| 488 | `oXVtxM_arcgis_rest_services_CountyAddresses_FeatureServer_23` | 9,126 | 9,126 | 0.00% | ok |
| 489 | `hAmRP1z50gTbO_arcgis_rest_services_Addresses_FeatureServer_0` | 9,107 | 9,107 | 0.00% | ok |
| 490 | `Sample_NCTECH_Volusia_Situs_Addresss_VRWorld_FeatureServer_0` | 8,990 | 8,990 | 0.00% | ok |
| 491 | `BY6OUzMBTZcz_arcgis_rest_services_Addresses_FeatureServer_15` | 8,951 | 8,951 | 0.00% | ok |
| 492 | `cyjLcCCpGk8Ri_arcgis_rest_services_Addresses_FeatureServer_0` | 8,688 | 8,688 | 0.00% | ok |
| 493 | `sses_public_6332b4b81c614cb4894d5de569a96465_FeatureServer_0` | 8,635 | 8,635 | 0.00% | ok |
| 494 | `VF_arcgis_rest_services_SC_Addressing_2025_7_FeatureServer_0` | 8,586 | 8,586 | 0.00% | ok |
| 495 | `gUZUh16VF_arcgis_rest_services_SC_Addressing_FeatureServer_0` | 8,585 | 8,585 | 0.00% | ok |
| 496 | `Pc_arcgis_rest_services_EL_RENO_911ADDRESSES_FeatureServer_0` | 8,465 | 8,465 | 0.00% | ok |
| 497 | `rcgis_rest_services_OsageCoKS_NG911Addresses_FeatureServer_0` | 8,287 | 8,287 | 0.00% | ok |
| 498 | `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | 8,280 | 16,558 | -99.98% | partial |
| 499 | `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4` | 8,280 | 16,558 | -99.98% | partial |
| 500 | `PSO5BR5eOIggwRH_arcgis_rest_services_Address_FeatureServer_0` | 8,267 | 8,267 | 0.00% | ok |
| 501 | `wu_arcgis_rest_services_CoStafford_Addresses_FeatureServer_0` | 8,246 | 8,246 | 0.00% | ok |
| 502 | `vlQFEpKtV_arcgis_rest_services_DOUGLASCOUNTY_FeatureServer_0` | 8,201 | 8,201 | 0.00% | ok |
| 503 | `R_arcgis_rest_services_Tornado_Addresses_NLR_FeatureServer_0` | 8,182 | 8,182 | 0.00% | ok |
| 504 | `Zk1fY2MHCTEXz_arcgis_rest_services_Addresses_FeatureServer_0` | 8,149 | 8,149 | 0.00% | ok |
| 505 | `resses___Archuleta_County_201411251147175537_FeatureServer_0` | 8,134 | 8,134 | 0.00% | ok |
| 506 | `es_City_Buildings_and_Address_Locations_WFL1_FeatureServer_4` | 7,969 | 7,969 | 0.00% | ok |
| 507 | `1uhbqnOZPx6qT_arcgis_rest_services_Addresses_FeatureServer_0` | 7,888 | 7,888 | 0.00% | ok |
| 508 | `_arcgis_rest_services_Site_Address_Occupants_FeatureServer_0` | 7,886 | 7,886 | 0.00% | ok |
| 509 | `s_rest_services_City_of_Dinuba_Addresses_gdb_FeatureServer_1` | 7,845 | 7,845 | 0.00% | ok |
| 510 | `_services_Address_and_Street_Annotation_view_FeatureServer_0` | 7,836 | 7,836 | 0.00% | ok |
| 511 | `sses_public_e65dd46e9c084cddaedcb94aeea0ed6b_FeatureServer_0` | 7,798 | 15,501 | -98.78% | partial |
| 512 | `DQNT3m6mbJlqZ_arcgis_rest_services_Addresses_FeatureServer_0` | 7,733 | 7,733 | 0.00% | ok |
| 513 | `HRU_arcgis_rest_services_VFAC_Addresses_WFL1_FeatureServer_0` | 7,686 | 7,686 | 0.00% | ok |
| 514 | `s_rest_services_Richland_County_ND_Addresses_FeatureServer_1` | 7,608 | 7,608 | 0.00% | ok |
| 515 | `8nlIDAHxNx4_arcgis_rest_services_911_Address_FeatureServer_0` | 7,566 | 7,566 | 0.00% | ok |
| 516 | `gg5s_arcgis_rest_services_Building_Addresses_FeatureServer_0` | 7,540 | 7,540 | 0.00% | ok |
| 517 | `ses_public_3336c922d00a441e8f588e16c3dc2577_FeatureServer_10` | 7,529 | 7,529 | 0.00% | ok |
| 518 | `ms_arcgis_rest_services_Address_Data_Public_FeatureServer_10` | 7,527 | 7,527 | 0.00% | ok |
| 519 | `cgis_rest_services_Address_Data_Public_view_FeatureServer_10` | 7,527 | 7,527 | 0.00% | ok |
| 520 | `rest_services_Master_Address_Management_WFL1_FeatureServer_0` | 7,506 | 7,506 | 0.00% | ok |
| 521 | `Q24dH_arcgis_rest_services_Addresses__Site__FeatureServer_13` | 7,440 | 7,440 | 0.00% | ok |
| 522 | `0hS_arcgis_rest_services_Address_Road_Update_FeatureServer_0` | 7,370 | 7,370 | 0.00% | ok |
| 523 | `l0FeW1NE_arcgis_rest_services_AddressesWInfo_FeatureServer_0` | 7,364 | 7,364 | 0.00% | ok |
| 524 | `Z_arcgis_rest_services_CityofDemingAddresses_FeatureServer_0` | 7,251 | 7,251 | 0.00% | ok |
| 525 | `rest_services_Pella_Address_Data_Public_View_FeatureServer_2` | 7,242 | 7,242 | 0.00% | ok |
| 526 | `_ArcGIS_rest_services_AddressesE911Macon2022_FeatureServer_0` | 7,242 | 7,242 | 0.00% | ok |
| 527 | `CY2_arcgis_rest_services_Dispatcher_Map_WFL1_FeatureServer_0` | 7,165 | 7,165 | 0.00% | ok |
| 528 | `rest_services_Site_Addresses_06012022_public_FeatureServer_2` | 7,163 | 7,163 | 0.00% | ok |
| 529 | `_Mountlake_Terrace_Washington_Addresses_view_FeatureServer_0` | 7,157 | 7,157 | 0.00% | ok |
| 530 | `ieS2ld_arcgis_rest_services_Searcy_NG911_gdb_FeatureServer_2` | 7,144 | 7,144 | 0.00% | ok |
| 531 | `kttgSmcq6CPonms_arcgis_rest_services_Address_FeatureServer_0` | 6,953 | 6,953 | 0.00% | ok |
| 532 | `_rest_services_E911_Houses_Washington_County_FeatureServer_0` | 6,724 | 6,724 | 0.00% | ok |
| 533 | `M5KB8_arcgis_rest_services_E911_PairwiseClip_FeatureServer_0` | 6,716 | 6,716 | 0.00% | ok |
| 534 | `7Y8pE5CiojuXeU_arcgis_rest_services_NewSitus_FeatureServer_0` | 6,686 | 6,686 | 0.00% | ok |
| 535 | `NuFrQ7kB_arcgis_rest_services_Master_Address_FeatureServer_0` | 6,655 | 6,655 | 0.00% | ok |
| 536 | `SQHJsl5r_arcgis_rest_services_Address_Labels_FeatureServer_0` | 6,588 | 6,588 | 0.00% | ok |
| 537 | `sdIpPb_arcgis_rest_services_Addresses_Splits_FeatureServer_0` | 6,583 | 13,161 | -99.92% | partial |
| 538 | `st_services_Lincoln_City_Addresses_View_Only_FeatureServer_0` | 6,521 | 6,521 | 0.00% | ok |
| 539 | `ater_Meter_Replacement_Addresses_Zone_1_view_FeatureServer_1` | 6,361 | 6,361 | 0.00% | ok |
| 540 | `teAddresses_8548b2fdfac0464392b3fd7620a632d7_FeatureServer_0` | 6,197 | 6,197 | 0.00% | ok |
| 541 | `yHixJV_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 6,184 | 6,184 | 0.00% | ok |
| 542 | `ces_Stillwater_County_Addressing_Layers_2026_FeatureServer_0` | 6,112 | 6,112 | 0.00% | ok |
| 543 | `wVADPEG6iD24f_arcgis_rest_services_Addresses_FeatureServer_0` | 6,031 | 6,031 | 0.00% | ok |
| 544 | `_in_Incident_Address_and_Type_for_Date_Range_FeatureServer_0` | 5,929 | 5,929 | 0.00% | ok |
| 545 | `st_services_Curb_Transition_Magic_Number2027_FeatureServer_0` | 5,896 | 11,808 | -100.27% | partial |
| 546 | `387Pb3S_arcgis_rest_services_LiveAdds_202504_FeatureServer_0` | 5,876 | 5,876 | 0.00% | ok |
| 547 | `Iod9kh71mtnDG_arcgis_rest_services_Addresses_FeatureServer_0` | 5,731 | 5,731 | 0.00% | ok |
| 548 | `dlWlBxzX_arcgis_rest_services_Newton_Address_FeatureServer_0` | 5,730 | 5,730 | 0.00% | ok |
| 549 | `cgis_rest_services_SiteAddresses_public_2020_FeatureServer_1` | 5,655 | 5,655 | 0.00% | ok |
| 550 | `HKRPMgv82EjLQ_arcgis_rest_services_Addresses_FeatureServer_0` | 5,640 | 5,640 | 0.00% | ok |
| 551 | `CRVuK_arcgis_rest_services_Map_View_Address_FeatureServer_42` | 5,634 | 5,634 | 0.00% | ok |
| 552 | `e3_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 5,586 | 5,586 | 0.00% | ok |
| 553 | `unty__GA_Online_911_Addresses_and_Roads_WFL1_FeatureServer_1` | 5,493 | 5,493 | 0.00% | ok |
| 554 | `TjgFX_arcgis_rest_services_addresses_120222a_FeatureServer_0` | 5,409 | 5,410 | -0.02% | ok |
| 555 | `bK6DOd0VbR_arcgis_rest_services_SB_Addresses_FeatureServer_0` | 5,403 | 5,403 | 0.00% | ok |
| 556 | `cgis_rest_services_Administrative_Addressing_FeatureServer_0` | 5,371 | 5,371 | 0.00% | ok |
| 557 | `67TISFO3iTjgFX_arcgis_rest_services_address2_FeatureServer_0` | 5,236 | 5,236 | 0.00% | ok |
| 558 | `esses_In_Refuse_Recycle_Routes_WFL1_July2019_FeatureServer_0` | 5,219 | 5,219 | 0.00% | ok |
| 559 | `g5mTyuNWO5xx6_arcgis_rest_services_Addresses_FeatureServer_0` | 5,168 | 5,168 | 0.00% | ok |
| 560 | `arcgis_rest_services_Hartford_911_Addresses__FeatureServer_0` | 5,108 | 5,108 | 0.00% | ok |
| 561 | `d_Septic_System_Pilot_Project_Addresses_View_FeatureServer_0` | 5,071 | 5,071 | 0.00% | ok |
| 562 | `roY6O3ncx_arcgis_rest_services_MS4_addresses_FeatureServer_0` | 5,060 | 5,060 | 0.00% | ok |
| 563 | `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0` | 5,045 | 10,085 | -99.90% | partial |
| 564 | `is_rest_services_Address_Points_Council_Area_FeatureServer_0` | - | 0 | 0.00% | empty |
| 565 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | - | 0 | 0.00% | empty |
| 566 | `unty_com_arcgis_rest_services_Hosted_Address_FeatureServer_0` | - | 10,876 | 0.00% | empty |
| 567 | `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | - | 0 | 0.00% | empty |
| 568 | `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | - | 0 | 0.00% | empty |
| 569 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | - | 0 | 0.00% | empty |
| 570 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | - | 0 | 0.00% | failed |
| 571 | `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | - | 0 | 0.00% | empty |
| 572 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 573 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | - | 25,659 | 0.00% | empty |
| 574 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | - | 0 | 0.00% | failed |
| 575 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | - | 0 | 0.00% | empty |
| 576 | `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | - | 0 | 0.00% | empty |
| 577 | `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | - | 0 | 0.00% | failed |
| 578 | `county_com_arcgis_rest_services_features_Address_MapServer_0` | - | 0 | 0.00% | failed |
| 579 | `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0` | - | 45,810 | 0.00% | empty |
| 580 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 581 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |
| 582 | `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 583 | `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | - | 0 | 0.00% | empty |
| 584 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | - | 0 | 0.00% | failed |
| 585 | `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | - | 233,572 | 0.00% | empty |
| 586 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | - | 0 | 0.00% | empty |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=05b
python3 collect/full_plan.py --stage 05b --size 200 --out collect/ledger/05b_plan.json
python3 collect/full_shard.py --stage 05b --shard 0 --plan collect/ledger/05b_plan.json
```
