# STEP07B 全量补采 · 收官账（2026-11-21）

## 一、总账

- 阶段：`07b` —— 碎片补齐 07b（1~4,999 行）
- 计划：158 层 / 声明 244,719 行 / 27 片（每片 6 层，unit_rows=100000）
- 账本覆盖：**373 层**（片文件 3 个）
- 逐态：**ok 369** / capped_by_upstream 0 / empty 2 / partial 0 / failed 2 / skipped_done 0
- 片完成度：应有 **27** 片，有账本 3 片，**未完成 24 片**：片号 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26
- 声明行合计：**993,013**；实采行合计：**989,025**；差额 3,988（0.402%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 6 | 6 | 8 | 完成 |
| 1 | 300 | 300 | 685,352 | 完成 |
| 2 | 67 | 67 | 303,665 | 完成 |
| 3 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 4 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 5 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 6 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 7 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 8 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 9 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 10 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 11 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 12 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 13 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 14 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 15 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 16 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 17 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 18 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 19 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 20 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 21 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 22 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 23 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 24 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 25 | 6 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 26 | 2 | 0 | 0 | 未完成：无账本（片被取消/没启动） |

**未完成片共 24 个，至少 140 层没有任何账本条目**（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。

## 二之二、max_shards 截断：本轮注定没跑的片（W33-036）

> 这不是「没采到」，是 **没派**：`max_shards=1` 把 27 片截成 1 片，152 层连 job 都没起。清单同时写在 plan 的 `shards_dropped[]`，账本 `shards_incomplete` 也会点名。要全跑请 `max_shards=0`。

| 被砍分片 | 层数 | 层 id |
|---|---|---|
| 1 | 6 | `_arcgis_rest_services_Site_Address_Locations_FeatureServer_0`, `6GqBWodG9Kll_arcgis_rest_services_Addresses__FeatureServer_0`, `OMMISSIONER_PCT_PUBLIC_WORKS_ADDRESSES_point_FeatureServer_0`, `_rest_services_2025_Waste_Disposal_Addresses_FeatureServer_0`, `ZHUggYYSp_arcgis_rest_services_Address_types_FeatureServer_0`, `HFr6zdgNZuVG0_arcgis_rest_services_NG911_CFS_FeatureServer_0` |
| 2 | 6 | `_arcgis_rest_services_Vulnerable_e911_sites__FeatureServer_0`, `YG1DOsR_arcgis_rest_services_HS_Plan_D_WFL1_FeatureServer_14`, `_rest_services_CatoctinSpeedDating_Addresses_FeatureServer_1`, `_arcgis_rest_services_Address_Location_Point_FeatureServer_0`, `Ep4y_arcgis_rest_services_CAW_Address_Points_FeatureServer_0`, `_arcgis_rest_services_SU_Address_Layer_DRAFT_FeatureServer_0` |
| 3 | 6 | `D4lF0F_arcgis_rest_services_PCBAddressBlocks_FeatureServer_0`, `VDPqdJ5_arcgis_rest_services_UC_Address_Grid_FeatureServer_0`, `_rest_services_Jay_Cooke_Trailhead_Addresses_FeatureServer_0`, `RealEstate_ACParcels_Outcome25address_points_FeatureServer_0`, `XdLKOfIXex_arcgis_rest_services_KHSD_Address_FeatureServer_0`, `_arcgis_rest_services_Mission_Site_Addresses_FeatureServer_0` |
| 4 | 6 | `_rest_services_ATW_Address_Points_2_5_Higher_FeatureServer_0`, `WXituM_arcgis_rest_services_Town_Owned_Situs_FeatureServer_0`, `123_4848a2717d344d119d250f258af86bea_results_FeatureServer_0`, `V_arcgis_rest_services_Crisis_Site_Addresses_FeatureServer_0`, `Property_Profile___No_Site_Address___10_2025_FeatureServer_0`, `_arcgis_rest_services_1920_Address_Points_JG_FeatureServer_0` |
| 5 | 6 | `CcMPHO_arcgis_rest_services_CERT_Team_Public_FeatureServer_0`, `1oVm_arcgis_rest_services_WCD_Site_Addresses_FeatureServer_0`, `Thf3DKUv_arcgis_rest_services_Address_Points_FeatureServer_0`, `7ueLg_arcgis_rest_services_0_Sites_Addresses_FeatureServer_0`, `IOcEYxoF_arcgis_rest_services_lead_addresses_FeatureServer_0`, `ckkXVBh_arcgis_rest_services_ParkOPS_Address_FeatureServer_0` |
| 6 | 6 | `_arcgis_rest_services_1940_Address_Points_JG_FeatureServer_0`, `_rest_services_NG911_PSAPs_GDH_Weekly_Report_FeatureServer_0`, `Iuq_arcgis_rest_services_Address_Points_DSSD_FeatureServer_0`, `O_arcgis_rest_services_NG9111PSAPPointValues_FeatureServer_0`, `_arcgis_rest_services_Remote_Address_Points_FeatureServer_10`, `P2WNA_arcgis_rest_services_Potomac_Addresses_FeatureServer_0` |
| 7 | 6 | `NA_arcgis_rest_services_Cottonwood_Addresses_FeatureServer_0`, `P2WNA_arcgis_rest_services_Peroria_Addresses_FeatureServer_0`, `9_arcgis_rest_services_NG911_Web_layers_WFL1_FeatureServer_0`, `3YBzBoefRGq66_arcgis_rest_services_Addresses_FeatureServer_0`, `Wzi_arcgis_rest_services_NCRPO_MCD_Addresses_FeatureServer_0`, `00ea7p7i0U_arcgis_rest_services_E911CallDATA_FeatureServer_1` |
| 8 | 6 | `On_arcgis_rest_services_CW_Points_w_Address_FeatureServer_12`, `JSry_arcgis_rest_services_Route_3_Addressing_FeatureServer_0`, `PPO6ob_arcgis_rest_services_StudyAreaAddress_FeatureServer_0`, `NqI_arcgis_rest_services_ng911_primary_psaps_FeatureServer_0`, `X_arcgis_rest_services_Alpena_Address_Points_FeatureServer_0`, `J_arcgis_rest_services_LACDBG_Address_Points_FeatureServer_0` |
| 9 | 6 | `_rest_services_Grayton_Parcels_and_Addresses_FeatureServer_0`, `_rest_services_Vacation_Rental_Address_Layer_FeatureServer_0`, `_gov_server_rest_services_Address_Points_602_FeatureServer_1`, `I88qiQGw_arcgis_rest_services_Address_Points_FeatureServer_0`, `xt6cnCY2_arcgis_rest_services_Site_Addresses_FeatureServer_2`, `ZN_arcgis_rest_services_Town_Preference_WFL1_FeatureServer_0` |
| 10 | 6 | `EXz_arcgis_rest_services_Evac_Address_Points_FeatureServer_0`, `CKH_arcgis_rest_services_MCRC_Address_Points_FeatureServer_0`, `SFO3iTjgFX_arcgis_rest_services_Address_Join_FeatureServer_0`, `Aa0SJxRv_arcgis_rest_services_NG911_Template_FeatureServer_0`, `OMrvu25KcUX35_arcgis_rest_services_Addresses_FeatureServer_0`, `_Find_Locations_in_Address_Points_filt_radon_FeatureServer_0` |
| 11 | 6 | `ajG76dg_arcgis_rest_services_HPOAddresses__1_FeatureServer_0`, `_rest_services_SC_Address_Grid_Intersections_FeatureServer_0`, `_arcgis_rest_services_IQA_grantees_Addresses_FeatureServer_0`, `CIe16u6G_arcgis_rest_services_Address_Points_FeatureServer_0`, `0ij_arcgis_rest_services_FWP_Lands_Addresses_FeatureServer_0`, `WofKfQhH_arcgis_rest_services_Address_Points_FeatureServer_0` |
| 12 | 6 | `_arcgis_rest_services_Westside_AddressPoints_FeatureServer_0`, `_GIS_Participant_Addresses_2019_deidentified_FeatureServer_0`, `Dta5_arcgis_rest_services_MaineE911Addresses_FeatureServer_0`, `_rest_services_DPZ_Curbs_2006_points_address_FeatureServer_0`, `Km_arcgis_rest_services_SmartGovSubAddresses_FeatureServer_0`, `Hpm8mHFz_arcgis_rest_services_Addresses_view_FeatureServer_0` |
| 13 | 6 | `YH0_arcgis_rest_services_Site_Address_Points_FeatureServer_0`, `2YfaSvieL_arcgis_rest_services_Yurok_Address_FeatureServer_0`, `Hyco_Boat_Docks_with_Parcel_and_Address_Data_FeatureServer_0`, `QGbyiuCh_arcgis_rest_services_Address_Points_FeatureServer_0`, `3oxsPnVw4fnW9_arcgis_rest_services_Addresses_FeatureServer_1`, `RTu_arcgis_rest_services_Sample_Addresses_bd_FeatureServer_0` |
| 14 | 6 | `37YZHYH0_arcgis_rest_services_Address_Points_FeatureServer_0`, `rcgis_rest_services_New_911_Address_Requests_FeatureServer_0`, `CDFVQ_arcgis_rest_services_Address_Points_C2_FeatureServer_0`, `QE7iy_arcgis_rest_services_Addresses_Mar2024_FeatureServer_0`, `_arcgis_rest_services_AddresspointsDuplicate_FeatureServer_0`, `5IxwbSz_arcgis_rest_services_AddressesOnline_FeatureServer_0` |
| 15 | 6 | `4JC_arcgis_rest_services_Rutland_County_E911_FeatureServer_0`, `YDMVmmxMeM_arcgis_rest_services_Crash_Points_FeatureServer_0`, `FwVI_arcgis_rest_services_9_1_1_Site_Address_FeatureServer_1`, `GtVEXzaX_arcgis_rest_services_Address_Point2_FeatureServer_0`, `Dl4j6iT0i_arcgis_rest_services_AddressPoints_FeatureServer_0`, `ASGpv7gPaTEUL_arcgis_rest_services_Addresses_FeatureServer_1` |
| 16 | 6 | `HgyUvYRWd_arcgis_rest_services_AddressPoints_FeatureServer_0`, `_arcgis_rest_services_Cesar_Chavez_Addresses_FeatureServer_0`, `W9xjDnZ35_arcgis_rest_services_911_Addresses_FeatureServer_0`, `GAlRIIIg_arcgis_rest_services_Address_Points_FeatureServer_0`, `DlIH33l3_arcgis_rest_services_Address_Points_FeatureServer_0`, `DCrBlhlg_arcgis_rest_services_EnochAddresses_FeatureServer_0` |
| 17 | 6 | `ocEBv1Ip_arcgis_rest_services_Address___View_FeatureServer_0`, `138c05_rest_services_MiddlesexCounty_Base_Layers_MapServer_0`, `XcE_arcgis_rest_services_911Address_20141030_FeatureServer_0`, `Blhlg_arcgis_rest_services_UtahAddressPoints_FeatureServer_0`, `Blhlg_arcgis_rest_services_RHUEnochAddresses_FeatureServer_0`, `UaBfRSxc_arcgis_rest_services_Address_Points_FeatureServer_0` |
| 18 | 6 | `GTj4xmYDtu_arcgis_rest_services_911addresses_FeatureServer_0`, `YDtu_arcgis_rest_services_PHYSICAL_ADDRESSES_FeatureServer_0`, `_rest_services_E911Roads_flowlines_intersect_FeatureServer_0`, `6FlIW_arcgis_rest_services_NP_Address_Points_FeatureServer_0`, `_rest_services_COAHOMA_COUNTY_ADDRESS_POINTS_FeatureServer_0`, `Fx_arcgis_rest_services_Anna_ETJ_Addresses_FeatureServer_157` |
| 19 | 6 | `aiian_Gardens_CA_Master_Address_Table__View_FeatureServer_10`, `Klwi2PRa_arcgis_rest_services_Address_Points_FeatureServer_0`, `4C5C_arcgis_rest_services_address_points_apb_FeatureServer_0`, `U4FaQtqrjGWfU_arcgis_rest_services_Addresses_FeatureServer_0`, `HoWNZ_arcgis_rest_services_Village_Addresses_FeatureServer_0`, `_services_Parcel_and_Address_Data_Civic_Plus_FeatureServer_1` |
| 20 | 6 | `YeF6EBJ1_arcgis_rest_services_Addresses_View_FeatureServer_0`, `SpUPMP3Z_arcgis_rest_services_Address_Points_FeatureServer_0`, `J7UaClOw_arcgis_rest_services_Address_Points_FeatureServer_0`, `4XSFR9wSzw_arcgis_rest_services_ADDRESS_DATA_FeatureServer_0`, `F_arcgis_rest_services_AddressPoints01312025_FeatureServer_0`, `CjdNui_arcgis_rest_services_addresses_030317_FeatureServer_0` |
| 21 | 6 | `HtVstUaG_arcgis_rest_services_Address_Points_FeatureServer_0`, `akSFUjJ_arcgis_rest_services_Address_Points_FeatureServer_15`, `_arcgis_rest_services_Sheridan_Addresses_gdb_FeatureServer_0`, `_rest_services_Practice_Topographic_Basins_Sewer_MapServer_2`, `_rest_services_Site_Structure_Address_Points_FeatureServer_0@WA-5`, `WsOS_arcgis_rest_services_wlv_address_points_FeatureServer_0` |
| 22 | 6 | `DiwEHErgACQrcA3_arcgis_rest_services_Address_FeatureServer_0`, `8Ri_arcgis_rest_services_Secondary_Addresses_FeatureServer_0`, `N_arcgis_rest_services_Master_Address_Points_FeatureServer_0`, `rcgis_rest_services_Addressing_Addressing_public_MapServer_0`, `3ECP25Sn_arcgis_rest_services_Address_Points_FeatureServer_0`, `Xa_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 23 | 6 | `_arcgis_rest_services_Juno_Address_Points_DC_FeatureServer_0`, `_arcgis_rest_services_E911_Addresses_4_2024_FeatureServer_23`, `4aPlhvQwvs_arcgis_rest_services_TEST_Service_FeatureServer_0`, `0DY_arcgis_rest_services_Snohomish_Addresses_FeatureServer_0`, `X5q_arcgis_rest_services_DD_Addresses_Public_FeatureServer_0`, `TpEhyQB_arcgis_rest_services_Addresses_91024_FeatureServer_0` |
| 24 | 6 | `Find_Locations_in_Address_Points_herndon_va2_FeatureServer_0@MD-1`, `9JX5q_arcgis_rest_services_Site_Addresses_CM_FeatureServer_0`, `NT3_arcgis_rest_services_E911_JUNE_ADDRESSES_FeatureServer_0`, `Site_Structure_Address_Points__External_View_FeatureServer_3`, `0DY_arcgis_rest_services_EnerGov_AddrParcels_FeatureServer_0`, `Ll1tVX_arcgis_rest_services_RPZ_Address_Pt_2_FeatureServer_0` |
| 25 | 6 | `61POPssw_arcgis_rest_services_Address_Points_FeatureServer_0`, `QvjiKhzBVQV7V_arcgis_rest_services_SITUS_PTS_FeatureServer_0`, `HNk0Cmg2csuv9p_arcgis_rest_services_Energov3_FeatureServer_0`, `WYow3ofS_arcgis_rest_services_Address___Town_FeatureServer_4`, `_arcgis_rest_services_Richland_AddressPt2022_FeatureServer_0`, `_arcgis_rest_services_LevellandAddressPoints_FeatureServer_0` |
| 26 | 2 | `_arcgis_rest_services_Energov_Address_Points_FeatureServer_0`, `S9sE3M9RybT_arcgis_rest_services_Address_Pts_FeatureServer_0` |

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `rcgis_rest_services_Addressing_Addressing_public_MapServer_0` | 3,821 | 0 | 3,821 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `138c05_rest_services_MiddlesexCounty_Base_Layers_MapServer_0` | 2,298 | 2,131 | 167 | failed | rc=1 err=? |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `rcgis_rest_services_Addressing_Addressing_public_MapServer_0` | failed | 3821 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `138c05_rest_services_MiddlesexCounty_Base_Layers_MapServer_0` | failed | 2298 | 2131 | rc=1 err=? |

## 五、逐层台账（按声明行数降序）

| # | 层 | 声明 | 实采 | 差额% | 状态 |
|---|---|---|---|---|---|
| 1 | `CK8921_arcgis_rest_services_AddressPoints_IW_FeatureServer_0` | 4,995 | 4,995 | 0.00% | ok |
| 2 | `ler_ca_server_rest_services_OpenData_opCommunity_MapServer_0` | 4,929 | 4,929 | 0.00% | ok |
| 3 | `4ofcdQP6p_arcgis_rest_services_Flood_Address_FeatureServer_0` | 4,915 | 4,915 | 0.00% | ok |
| 4 | `ecEOR9md_arcgis_rest_services_UnitAddressing_FeatureServer_0` | 4,894 | 4,894 | 0.00% | ok |
| 5 | `gis_rest_services_Address_Pnts_Parcel_2023_FeatureServer_319@未定位-1` | 4,892 | 4,892 | 0.00% | ok |
| 6 | `WKKHPp01_arcgis_rest_services_ACOG_Addresses_FeatureServer_0` | 4,887 | 4,887 | 0.00% | ok |
| 7 | `_arcgis_rest_services_Address_Points__Public_FeatureServer_0` | 4,759 | 4,759 | 0.00% | ok |
| 8 | `est_services_Stone_Mills_Civic_Address__View_FeatureServer_0` | 4,746 | 4,746 | 0.00% | ok |
| 9 | `_arcgis_rest_services_Fairview_MAF_20230104a_FeatureServer_0` | 4,740 | 4,740 | 0.00% | ok |
| 10 | `gis_rest_services_Public_Addresses__2023_01__FeatureServer_0` | 4,735 | 4,735 | 0.00% | ok |
| 11 | `g_arcgis_rest_services_AddressPts_WestStPaul_FeatureServer_0` | 4,733 | 4,733 | 0.00% | ok |
| 12 | `uY4HWfZxU_arcgis_rest_services_Rural_Address_FeatureServer_0` | 4,727 | 4,727 | 0.00% | ok |
| 13 | `rcgis_rest_services_E911_Address_Mile_Radius_FeatureServer_0` | 4,726 | 4,726 | 0.00% | ok |
| 14 | `d9VRQ_arcgis_rest_services_RDNAddressPoints_FeatureServer_21` | 4,710 | 4,710 | 0.00% | ok |
| 15 | `1U29in_arcgis_rest_services_Addresses_Points_FeatureServer_0` | 4,709 | 4,709 | 0.00% | ok |
| 16 | `U_arcgis_rest_services_Rural_Address12092023_FeatureServer_0` | 4,696 | 4,696 | 0.00% | ok |
| 17 | `rest_services_Service_Points_For_LCR_Mailing_FeatureServer_8` | 4,694 | 4,694 | 0.00% | ok |
| 18 | `Et4zjtFEdDXhrEP_arcgis_rest_services_Address_FeatureServer_0` | 4,693 | 4,693 | 0.00% | ok |
| 19 | `8OU9btpe_arcgis_rest_services_Address_Points_FeatureServer_0` | 4,687 | 4,687 | 0.00% | ok |
| 20 | `h_Address_Points_Taxable_20260805_PublicView_FeatureServer_5` | 4,684 | 4,684 | 0.00% | ok |
| 21 | `aIE7_arcgis_rest_services_Addresses__Public_FeatureServer_30` | 4,676 | 4,676 | 0.00% | ok |
| 22 | `rcgis_rest_services_Master_Address_20221008_FeatureServer_30` | 4,676 | 4,676 | 0.00% | ok |
| 23 | `cgis_rest_services_KScoHP_NG911AddressPoints_FeatureServer_0` | 4,667 | 4,667 | 0.00% | ok |
| 24 | `rcgis_rest_services_AddressPoints_PublicView_FeatureServer_0` | 4,646 | 4,646 | 0.00% | ok |
| 25 | `77e641a_rest_services_City_Public_Community_Data_MapServer_4` | 4,629 | 4,629 | 0.00% | ok |
| 26 | `s_rest_services_PHU_CK_SecondaryZone_Address_FeatureServer_0` | 4,614 | 4,614 | 0.00% | ok |
| 27 | `AZFykW_arcgis_rest_services_Property_Address_FeatureServer_0` | 4,594 | 4,594 | 0.00% | ok |
| 28 | `0ij_arcgis_rest_services_Dawson_Address_view_FeatureServer_0` | 4,593 | 4,593 | 0.00% | ok |
| 29 | `MuT9vmGH9G_arcgis_rest_services_MP_Addresses_FeatureServer_0` | 4,590 | 4,590 | 0.00% | ok |
| 30 | `2E8_arcgis_rest_services_NG911CoreData2_view_FeatureServer_0` | 4,574 | 4,574 | 0.00% | ok |
| 31 | `gis_rest_services_Parcel_and_Address__public_FeatureServer_0` | 4,570 | 4,570 | 0.00% | ok |
| 32 | `PwCGj_arcgis_rest_services_Address_Point2018_FeatureServer_0` | 4,560 | 4,560 | 0.00% | ok |
| 33 | `CGj_arcgis_rest_services_Address_Point_2019_FeatureServer_52` | 4,556 | 4,556 | 0.00% | ok |
| 34 | `LVX_arcgis_rest_services_Master_Address_List_FeatureServer_0` | 4,551 | 4,551 | 0.00% | ok |
| 35 | `is_rest_services_SnoqualmieAddressPointsView_FeatureServer_0` | 4,551 | 4,551 | 0.00% | ok |
| 36 | `BPKmkH93_arcgis_rest_services_Address_Points_FeatureServer_0` | 4,506 | 4,506 | 0.00% | ok |
| 37 | `KmkH93_arcgis_rest_services_Parcel_Addresses_FeatureServer_0` | 4,506 | 4,506 | 0.00% | ok |
| 38 | `tyFKxRSMm_arcgis_rest_services_AddressPoints_FeatureServer_0` | 4,489 | 4,489 | 0.00% | ok |
| 39 | `gis_rest_services_Address_Pnts_Parcel_2023_FeatureServer_378` | 4,477 | 4,477 | 0.00% | ok |
| 40 | `arcgis_rest_services_POINT_ADDRESSES__VIEWER_FeatureServer_0` | 4,472 | 4,472 | 0.00% | ok |
| 41 | `8NkV_arcgis_rest_services_Napoleon_Addresses_FeatureServer_0` | 4,463 | 4,463 | 0.00% | ok |
| 42 | `rest_services_Public_View_of_NG911_Core_Data_FeatureServer_1` | 4,459 | 4,459 | 0.00% | ok |
| 43 | `arcgis_rest_services_Lake01_TL_Addresspoints_FeatureServer_0` | 4,444 | 4,444 | 0.00% | ok |
| 44 | `g_arcgis_rest_services_Nevada_Address_Points_FeatureServer_0` | 4,430 | 4,430 | 0.00% | ok |
| 45 | `cgis_rest_services_Avon_Address_Points_view_FeatureServer_49` | 4,424 | 4,424 | 0.00% | ok |
| 46 | `J78Sz_arcgis_rest_services_AddressPts_public_FeatureServer_1` | 4,403 | 4,403 | 0.00% | ok |
| 47 | `m4psKuX_arcgis_rest_services_Belen_Addresses_FeatureServer_1` | 4,392 | 4,392 | 0.00% | ok |
| 48 | `nbj4gzYoKe_arcgis_rest_services_Address_NENA_FeatureServer_3` | 4,359 | 4,359 | 0.00% | ok |
| 49 | `kpr4c1bMs_arcgis_rest_services_AddressPoints_FeatureServer_0` | 4,359 | 4,359 | 0.00% | ok |
| 50 | `4hYHAFVZ_arcgis_rest_services_NFO_Addressing_FeatureServer_0` | 4,354 | 4,354 | 0.00% | ok |
| 51 | `ces_Hydrants_and_Infrastructure_Map_features_FeatureServer_3` | 4,345 | 4,345 | 0.00% | ok |
| 52 | `arcgis_rest_services_SpartaAddressesSept2024_FeatureServer_2` | 4,341 | 4,341 | 0.00% | ok |
| 53 | `xv_arcgis_rest_services_Broadwater_Addresses_FeatureServer_2` | 4,337 | 4,337 | 0.00% | ok |
| 54 | `s_rest_services_HBAddressSamrtGov010524_view_FeatureServer_6` | 4,325 | 4,325 | 0.00% | ok |
| 55 | `UtLqxf_arcgis_rest_services_SiteAddressPoint_FeatureServer_0` | 4,297 | 4,297 | 0.00% | ok |
| 56 | `rcgis_rest_services_E911_SEPTEMBER_ADDRESSES_FeatureServer_0` | 4,292 | 4,292 | 0.00% | ok |
| 57 | `vices_EnerGOV_Parcel_Addresses_Service_Layer_FeatureServer_0` | 4,288 | 4,288 | 0.00% | ok |
| 58 | `_rest_services_Civic_Address_Points__NF_View_FeatureServer_0` | 4,280 | 4,280 | 0.00% | ok |
| 59 | `oqghsj9nd_arcgis_rest_services_AddressPoints_FeatureServer_0` | 4,275 | 4,275 | 0.00% | ok |
| 60 | `qU3t_arcgis_rest_services_ZoneCOMM_Addresses_FeatureServer_0` | 4,260 | 4,260 | 0.00% | ok |
| 61 | `XEiBhI5L5n_arcgis_rest_services_GW_Addresses_FeatureServer_0` | 4,247 | 4,247 | 0.00% | ok |
| 62 | `9IFXMrlCe_arcgis_rest_services_AddressPoints_FeatureServer_0` | 4,245 | 4,245 | 0.00% | ok |
| 63 | `dJq_arcgis_rest_services_Address_Points_view_FeatureServer_2` | 4,234 | 4,234 | 0.00% | ok |
| 64 | `OhlGTdJq_arcgis_rest_services_Address_Points_FeatureServer_2` | 4,234 | 4,234 | 0.00% | ok |
| 65 | `l_arcgis_rest_services_AddressPoints_SP_view_FeatureServer_0` | 4,189 | 4,189 | 0.00% | ok |
| 66 | `fwTB_arcgis_rest_services_Election_Addresses_FeatureServer_0` | 4,176 | 4,176 | 0.00% | ok |
| 67 | `rcgis_rest_services_Municipal_Addresses_2025_FeatureServer_2` | 4,165 | 4,165 | 0.00% | ok |
| 68 | `zUpYwtVC_arcgis_rest_services_Addresses_test_FeatureServer_5` | 4,164 | 4,164 | 0.00% | ok |
| 69 | `eG7_arcgis_rest_services_AddressPointsMERGED_FeatureServer_0` | 4,161 | 4,161 | 0.00% | ok |
| 70 | `perty_AddressPointsMERGED_Feature_Layer_View_FeatureServer_0` | 4,161 | 4,161 | 0.00% | ok |
| 71 | `r_arcgis_rest_services_SiteAddressPoint_view_FeatureServer_0` | 4,157 | 4,157 | 0.00% | ok |
| 72 | `sE3M9RybT_arcgis_rest_services_911Addressing_FeatureServer_0` | 4,153 | 4,153 | 0.00% | ok |
| 73 | `JheIun5o_arcgis_rest_services_Address_Points_FeatureServer_0` | 4,080 | 4,080 | 0.00% | ok |
| 74 | `vfD9wl7S_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 4,064 | 4,064 | 0.00% | ok |
| 75 | `4nF4r65G_arcgis_rest_services_Address_Points_FeatureServer_0` | 4,053 | 4,053 | 0.00% | ok |
| 76 | `arcgis_rest_services_Address_Points_09292026_FeatureServer_0` | 4,043 | 4,043 | 0.00% | ok |
| 77 | `rcgis_rest_services_NYCHA_Building_Entrances_FeatureServer_0` | 4,015 | 4,015 | 0.00% | ok |
| 78 | `soO4nWXrJNri_arcgis_rest_services_Addressing_FeatureServer_0` | 4,010 | 4,010 | 0.00% | ok |
| 79 | `arcgis_rest_services_Beaverhead_Address_WFL1_FeatureServer_0` | 4,008 | 4,008 | 0.00% | ok |
| 80 | `gis_rest_services_Address_Pnts_Parcel_2023_FeatureServer_373@未定位-1` | 4,006 | 4,006 | 0.00% | ok |
| 81 | `6yYcthteBp2Ec_arcgis_rest_services_Addresses_FeatureServer_0` | 4,004 | 4,004 | 0.00% | ok |
| 82 | `is_rest_services_DeletedSiteAddresses_011425_FeatureServer_0` | 3,985 | 3,985 | 0.00% | ok |
| 83 | `4_arcgis_rest_services_Address_Points_Zoning_FeatureServer_0` | 3,975 | 3,975 | 0.00% | ok |
| 84 | `gNoStWpd6_arcgis_rest_services_Address_Point_FeatureServer_1` | 3,962 | 3,962 | 0.00% | ok |
| 85 | `GZhi_arcgis_rest_services_GranbyAddresses_VW_FeatureServer_5` | 3,960 | 3,960 | 0.00% | ok |
| 86 | `mD23fAgi_arcgis_rest_services_Address_Points_FeatureServer_0` | 3,960 | 3,960 | 0.00% | ok |
| 87 | `services_North_Area_Unincorporated_Addresses_FeatureServer_2` | 3,949 | 3,949 | 0.00% | ok |
| 88 | `1qJNo_arcgis_rest_services_JB_Address_Points_FeatureServer_0` | 3,921 | 3,921 | 0.00% | ok |
| 89 | `fTGm_arcgis_rest_services_Civic_Address_view_FeatureServer_0` | 3,918 | 3,918 | 0.00% | ok |
| 90 | `rcgis_rest_services_AddressPoints___CivicRec_FeatureServer_0` | 3,917 | 3,917 | 0.00% | ok |
| 91 | `ces_service_dbfa9a29ee544e5480a5d62cf850ef04_FeatureServer_0` | 3,911 | 3,911 | 0.00% | ok |
| 92 | `_rest_services_Address_Zone_Joi_SpatialJoin_FeatureServer_11` | 3,889 | 3,889 | 0.00% | ok |
| 93 | `_Address_Points_for_Dos_Palos_TRA_Analysis_FeatureServer_113` | 3,888 | 3,888 | 0.00% | ok |
| 94 | `O_arcgis_rest_services_Pontiac_AddressPoints_FeatureServer_0` | 3,867 | 3,867 | 0.00% | ok |
| 95 | `N_arcgis_rest_services_Lab2Part2Presentation_FeatureServer_0` | 3,850 | 3,850 | 0.00% | ok |
| 96 | `st_services_NG911_ACE_Field_Edits_Host_AGOL_FeatureServer_22` | 3,832 | 3,832 | 0.00% | ok |
| 97 | `bY8hC_arcgis_rest_services_AU_AddressPoints_FeatureServer_17` | 3,821 | 3,821 | 0.00% | ok |
| 98 | `rcgis_rest_services_Addressing_Addressing_public_MapServer_0` | 3,821 | 0 | 100.00% | failed |
| 99 | `O3qhR0j8kvKI_arcgis_rest_services_911Address_FeatureServer_0` | 3,816 | 3,816 | 0.00% | ok |
| 100 | `hR0j8kvKI_arcgis_rest_services_Address_Layer_FeatureServer_0` | 3,759 | 3,759 | 0.00% | ok |
| 101 | `FNt_arcgis_rest_services_MerrittCivicAddress_FeatureServer_1` | 3,716 | 3,716 | 0.00% | ok |
| 102 | `_rest_services_Public_View_Addresses_Updated_FeatureServer_0` | 3,705 | 3,705 | 0.00% | ok |
| 103 | `dZXxL3_arcgis_rest_services_Public_NG911Data_FeatureServer_0` | 3,705 | 3,705 | 0.00% | ok |
| 104 | `__Parking_Restrictions_in_District_12___12A_FeatureServer_16` | 3,656 | 3,656 | 0.00% | ok |
| 105 | `gis_rest_services_Addington_Highlands_civics_FeatureServer_0` | 3,641 | 3,641 | 0.00% | ok |
| 106 | `st_services_Current_16_Buffer_Address_Points_FeatureServer_1` | 3,630 | 3,630 | 0.00% | ok |
| 107 | `4nLa_arcgis_rest_services_Corrales_Addresses_FeatureServer_0` | 3,629 | 3,629 | 0.00% | ok |
| 108 | `k_arcgis_rest_services_clc_SiteAddressPoints_FeatureServer_0` | 3,615 | 3,615 | 0.00% | ok |
| 109 | `gis_rest_services_Address_Points_Public_View_FeatureServer_0@未定位-3` | 3,602 | 3,602 | 0.00% | ok |
| 110 | `pr4c1bMs_arcgis_rest_services_Address_Points_FeatureServer_0` | 3,588 | 3,588 | 0.00% | ok |
| 111 | `_arcgis_rest_services_MonoParcelAddressPoint_FeatureServer_0` | 3,562 | 3,562 | 0.00% | ok |
| 112 | `cgis_rest_services_Findlay_AddressPt_202205_FeatureServer_32` | 3,561 | 3,561 | 0.00% | ok |
| 113 | `arcgis_rest_services_WestDundeeAddressPoints_FeatureServer_3` | 3,557 | 3,557 | 0.00% | ok |
| 114 | `fm3E_arcgis_rest_services_911_Address_Points_FeatureServer_0` | 3,511 | 3,511 | 0.00% | ok |
| 115 | `Ksox8qZD_arcgis_rest_services_Address_Points_FeatureServer_0` | 3,509 | 3,509 | 0.00% | ok |
| 116 | `ervices_BTMA_Address_Pnts_Water_Service_List_FeatureServer_0` | 3,491 | 3,491 | 0.00% | ok |
| 117 | `Bzu9iB_arcgis_rest_services_MF_AddressPoints_FeatureServer_0` | 3,470 | 3,470 | 0.00% | ok |
| 118 | `kx4_arcgis_rest_services_Address_Point_2019_FeatureServer_25` | 3,470 | 3,470 | 0.00% | ok |
| 119 | `NPkx4_arcgis_rest_services_Address_Point2018_FeatureServer_1` | 3,469 | 3,469 | 0.00% | ok |
| 120 | `ODTaNPkx4_arcgis_rest_services_Address_Point_FeatureServer_1` | 3,466 | 3,466 | 0.00% | ok |
| 121 | `7HYFU2ja_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_0` | 3,460 | 3,460 | 0.00% | ok |
| 122 | `pL_arcgis_rest_services_Commercial_Addresses_FeatureServer_0` | 3,454 | 3,454 | 0.00% | ok |
| 123 | `t_services_Castlegar_Address_20240607_2_view_FeatureServer_0` | 3,441 | 3,441 | 0.00% | ok |
| 124 | `est_services_Castlegar_Address_20240607_view_FeatureServer_0` | 3,441 | 3,441 | 0.00% | ok |
| 125 | `01KI_arcgis_rest_services_Parcels_Loris_Area_FeatureServer_0` | 3,398 | 3,398 | 0.00% | ok |
| 126 | `est_services_PYLA_GEOCODING_ADDRESS_08122017_FeatureServer_0` | 3,391 | 3,391 | 0.00% | ok |
| 127 | `Site_Address_Points_LDFP_2023_06_27_11_51_07_FeatureServer_1` | 3,374 | 3,374 | 0.00% | ok |
| 128 | `nUTzaIE7_arcgis_rest_services_Master_Address_FeatureServer_0` | 3,360 | 3,360 | 0.00% | ok |
| 129 | `rcgis_rest_services_AddressPoints_Monona2025_FeatureServer_0` | 3,325 | 3,325 | 0.00% | ok |
| 130 | `s_rest_services_Site_Structure_Address_Point_FeatureServer_2` | 3,318 | 3,318 | 0.00% | ok |
| 131 | `ess_Points_covering_Banner_Elk_Fire_District_FeatureServer_0` | 3,318 | 3,318 | 0.00% | ok |
| 132 | `UYXbI694_arcgis_rest_services_Address_Points_FeatureServer_0` | 3,292 | 3,292 | 0.00% | ok |
| 133 | `est_services_Address_Pnts_Parcel_2023_view_FeatureServer_319` | 3,259 | 3,259 | 0.00% | ok |
| 134 | `gis_rest_services_Address_Pnts_Parcel_2023_FeatureServer_319@未定位-3` | 3,259 | 3,259 | 0.00% | ok |
| 135 | `mtUxY8ZhqLsSC_arcgis_rest_services_Addresses_FeatureServer_0` | 3,251 | 3,251 | 0.00% | ok |
| 136 | `43COC93RA9a8_arcgis_rest_services_Addresses_FeatureServer_17` | 3,249 | 3,249 | 0.00% | ok |
| 137 | `rcgis_rest_services_Curbside_Addressing_WFL1_FeatureServer_0` | 3,233 | 3,233 | 0.00% | ok |
| 138 | `YUowSG4eci6_arcgis_rest_services_AddressView_FeatureServer_0` | 3,177 | 3,177 | 0.00% | ok |
| 139 | `gis_rest_services_Address_Zoning_Subdivision_FeatureServer_0` | 3,156 | 3,156 | 0.00% | ok |
| 140 | `ElDOMEad_arcgis_rest_services_Ohio_AddressFZ_FeatureServer_1` | 3,153 | 3,153 | 0.00% | ok |
| 141 | `pfo53l6Z3lemr_arcgis_rest_services_Addresses_FeatureServer_0` | 3,151 | 3,151 | 0.00% | ok |
| 142 | `is_rest_services_Union_County_E911_Addresses_FeatureServer_1` | 3,139 | 3,139 | 0.00% | ok |
| 143 | `st_services_Avalon_Address_Pnts_Parcel_2022_FeatureServer_68` | 3,128 | 3,128 | 0.00% | ok |
| 144 | `ttsKYgtiQ_arcgis_rest_services_Civic_Address_FeatureServer_0` | 3,105 | 3,105 | 0.00% | ok |
| 145 | `t_services_Address_Points_Lead_and_Copper_FeatureServer_1393` | 3,101 | 3,101 | 0.00% | ok |
| 146 | `rcgis_rest_services_Address_Pnts_Parcel_2022_FeatureServer_3` | 3,097 | 3,097 | 0.00% | ok |
| 147 | `ervices_Coraopolis_Address_Pnts_Parcel_2022_FeatureServer_31` | 3,091 | 3,091 | 0.00% | ok |
| 148 | `BRBK569Y_arcgis_rest_services_Address_Points_FeatureServer_0` | 3,085 | 3,085 | 0.00% | ok |
| 149 | `cgis_rest_services_Address_Points_PublicView_FeatureServer_0` | 3,085 | 3,085 | 0.00% | ok |
| 150 | `ywVY8PeJe_arcgis_rest_services_AddressPoints_FeatureServer_0` | 3,059 | 3,059 | 0.00% | ok |
| 151 | `NcB5m8L_arcgis_rest_services_Addresses_Adapt_FeatureServer_1` | 3,028 | 3,028 | 0.00% | ok |
| 152 | `is_rest_services_Inverness_Address_Points_FeatureServer_1470` | 2,999 | 2,999 | 0.00% | ok |
| 153 | `5OMMkmC_arcgis_rest_services_Addressing_View_FeatureServer_0` | 2,991 | 2,991 | 0.00% | ok |
| 154 | `6gk_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 2,970 | 2,970 | 0.00% | ok |
| 155 | `m_ALaxfASMULIJ1PP6_arcgis_rest_services_E911_FeatureServer_0` | 2,968 | 2,968 | 0.00% | ok |
| 156 | `services_Sidewalk_Replacement_Address_Points_FeatureServer_0` | 2,963 | 2,963 | 0.00% | ok |
| 157 | `ces_SiteStructureAddressPoints_ScotlandCoMO_FeatureServer_20` | 2,962 | 2,962 | 0.00% | ok |
| 158 | `_arcgis_rest_services_Address_Point_Labeling_FeatureServer_3` | 2,946 | 2,946 | 0.00% | ok |
| 159 | `k9_arcgis_rest_services_SharkeyMS_addressing_FeatureServer_0` | 2,933 | 2,933 | 0.00% | ok |
| 160 | `sNlTJPVD_arcgis_rest_services_Address_Points_FeatureServer_0` | 2,916 | 2,916 | 0.00% | ok |
| 161 | `PVD_arcgis_rest_services_Address_Points_View_FeatureServer_0` | 2,916 | 2,916 | 0.00% | ok |
| 162 | `rcgis_rest_services_Richland_Address_Points_FeatureServer_20` | 2,910 | 2,910 | 0.00% | ok |
| 163 | `08OCMdvg_arcgis_rest_services_SLRD_ADDRESSES_FeatureServer_0` | 2,873 | 2,873 | 0.00% | ok |
| 164 | `rtUP3FpWpuez_arcgis_rest_services_Addresses_FeatureServer_55` | 2,860 | 2,860 | 0.00% | ok |
| 165 | `FpWpuez_arcgis_rest_services_Address_Points_FeatureServer_55` | 2,825 | 2,825 | 0.00% | ok |
| 166 | `is_rest_services_WestCOG_Muni_parcel_Address_FeatureServer_0` | 2,776 | 2,776 | 0.00% | ok |
| 167 | `T5uDOHD_arcgis_rest_services_wti_address_pts_FeatureServer_0` | 2,775 | 2,775 | 0.00% | ok |
| 168 | `PPFTeMAr_arcgis_rest_services_Address_Points_FeatureServer_1` | 2,773 | 2,773 | 0.00% | ok |
| 169 | `SYzCSB2pQ16E_arcgis_rest_services_Addresses_FeatureServer_24` | 2,740 | 2,740 | 0.00% | ok |
| 170 | `m_fxB2C8mQfjMb1848_arcgis_rest_services_E911_FeatureServer_0` | 2,737 | 2,737 | 0.00% | ok |
| 171 | `gis_rest_services_AS_Address_Points_no_join_FeatureServer_44` | 2,725 | 2,725 | 0.00% | ok |
| 172 | `arcgis_rest_services_Mineral_Point_Addresses_FeatureServer_0` | 2,714 | 2,714 | 0.00% | ok |
| 173 | `t_services_BrisAddressPoints_Zoning_03062024_FeatureServer_1` | 2,690 | 2,690 | 0.00% | ok |
| 174 | `arcgis_rest_services_BrisAddressPoints_NAD83_FeatureServer_3` | 2,674 | 2,674 | 0.00% | ok |
| 175 | `rcgis_rest_services_Roanoke_Address_RES_view_FeatureServer_4` | 2,667 | 2,667 | 0.00% | ok |
| 176 | `_services_Sheridan_County_911_Addresses_view_FeatureServer_1` | 2,657 | 2,657 | 0.00% | ok |
| 177 | `0YZpJFyP_arcgis_rest_services_Address_Lookup_FeatureServer_0` | 2,650 | 2,650 | 0.00% | ok |
| 178 | `qnURg_arcgis_rest_services_Addressing_Viewer_FeatureServer_0` | 2,642 | 2,642 | 0.00% | ok |
| 179 | `fbL3D_arcgis_rest_services_ColvilleAddresses_FeatureServer_0` | 2,638 | 2,638 | 0.00% | ok |
| 180 | `54AuTB2R6_arcgis_rest_services_Address_Point_FeatureServer_0` | 2,632 | 2,632 | 0.00% | ok |
| 181 | `is_rest_services_Leaf_Pickup_Route_Addresses_FeatureServer_6` | 2,631 | 2,631 | 0.00% | ok |
| 182 | `is_rest_services_MD_of_Taber_Address_Points_FeatureServer_30` | 2,618 | 2,618 | 0.00% | ok |
| 183 | `bO_arcgis_rest_services_Address_Points_2021_FeatureServer_25` | 2,607 | 2,607 | 0.00% | ok |
| 184 | `W0YZpJFyP_arcgis_rest_services_Rural_Address_FeatureServer_0` | 2,598 | 2,598 | 0.00% | ok |
| 185 | `Dhk1zQOJdo_arcgis_rest_services_AptAddresses_FeatureServer_0` | 2,586 | 2,586 | 0.00% | ok |
| 186 | `edEx0oU_arcgis_rest_services_Anthony_Address_FeatureServer_0` | 2,569 | 2,569 | 0.00% | ok |
| 187 | `_gov_arcgis_rest_services_OpenData_ReferenceData_MapServer_0` | 2,565 | 2,565 | 0.00% | ok |
| 188 | `Jazuv_arcgis_rest_services_CoP_AddressPoints_FeatureServer_0` | 2,559 | 2,559 | 0.00% | ok |
| 189 | `ervices_WTB_E911_Points___Elevation_Extract_FeatureServer_15` | 2,547 | 2,547 | 0.00% | ok |
| 190 | `Xmi76IiY_arcgis_rest_services_Public_Address_FeatureServer_0` | 2,542 | 2,542 | 0.00% | ok |
| 191 | `3RA9a8_arcgis_rest_services_Addresses_Clip_FeatureServer_207` | 2,540 | 2,540 | 0.00% | ok |
| 192 | `gis_rest_services_DestroyedLahaina_Addresses_FeatureServer_0` | 2,524 | 2,524 | 0.00% | ok |
| 193 | `rest_services_OZ_Multi_Family_Address_Points_FeatureServer_0` | 2,493 | 2,493 | 0.00% | ok |
| 194 | `b276f_rest_services_PCS_PCS_Civic_Addresses_FeatureServer_15` | 2,493 | 2,493 | 0.00% | ok |
| 195 | `M2ce1oen_arcgis_rest_services_Address_Point_FeatureServer_25` | 2,467 | 2,467 | 0.00% | ok |
| 196 | `est_services_Address_Points_Hydrant_Flushing_FeatureServer_0` | 2,464 | 2,464 | 0.00% | ok |
| 197 | `HNLrSsWf5_arcgis_rest_services_ILA2022to2026_FeatureServer_0` | 2,462 | 2,462 | 0.00% | ok |
| 198 | `DNCbkC_arcgis_rest_services_AddressesService_FeatureServer_0` | 2,439 | 2,439 | 0.00% | ok |
| 199 | `rcgis_rest_services_SDL___Address_Point_View_FeatureServer_0` | 2,434 | 2,434 | 0.00% | ok |
| 200 | `Csd4eCZt_arcgis_rest_services_City_Addresses_FeatureServer_0` | 2,402 | 2,402 | 0.00% | ok |
| 201 | `61ac03_rest_services_Bowen_ReadOnly_Cadastre_FeatureServer_2` | 2,397 | 2,397 | 0.00% | ok |
| 202 | `_FACILITYe911_SitesInnundated__PairwiseClip1_FeatureServer_0` | 2,381 | 2,381 | 0.00% | ok |
| 203 | `vn_arcgis_rest_services_AddressPoints_Morrow_FeatureServer_0` | 2,373 | 2,373 | 0.00% | ok |
| 204 | `s_rest_services_AddressPointsFrom2021Parcels_FeatureServer_0` | 2,367 | 2,367 | 0.00% | ok |
| 205 | `_rest_services_Address_Points_in_Food_Desert_FeatureServer_0` | 2,365 | 2,365 | 0.00% | ok |
| 206 | `_pagis_org_arcgis_rest_services_PARON_Paron_Base_MapServer_0` | 2,304 | 2,304 | 0.00% | ok |
| 207 | `138c05_rest_services_MiddlesexCounty_Base_Layers_MapServer_0` | 2,298 | 2,131 | 7.27% | failed |
| 208 | `8dX_arcgis_rest_services_AddressTest_Service_FeatureServer_0` | 2,292 | 2,292 | 0.00% | ok |
| 209 | `s_rest_services_AGISO_Address_Points_Public_FeatureServer_36` | 2,289 | 2,289 | 0.00% | ok |
| 210 | `1gq_arcgis_rest_services_All_Addresses_Types_FeatureServer_0` | 2,288 | 2,288 | 0.00% | ok |
| 211 | `ieDs18m_arcgis_rest_services_Service_Address_FeatureServer_0` | 2,269 | 2,269 | 0.00% | ok |
| 212 | `_arcgis_rest_services_AddressPoints2026_view_FeatureServer_0` | 2,255 | 2,255 | 0.00% | ok |
| 213 | `0cQdmjH_arcgis_rest_services_Address_Points_FeatureServer_23` | 2,253 | 2,253 | 0.00% | ok |
| 214 | `_arcgis_rest_services_New_Fairview_Addresses_FeatureServer_1` | 2,250 | 2,250 | 0.00% | ok |
| 215 | `_rest_services_Walton_County_Address_Points_FeatureServer_15` | 2,250 | 2,250 | 0.00% | ok |
| 216 | `rcgis_rest_services_CAMS_Address_Points_2023_FeatureServer_0` | 2,240 | 2,240 | 0.00% | ok |
| 217 | `g_arcgis_rest_services_Countryside_Addresses_FeatureServer_4` | 2,232 | 2,232 | 0.00% | ok |
| 218 | `w8d2q0_arcgis_rest_services_Address_Points_FeatureServer_124` | 2,222 | 2,222 | 0.00% | ok |
| 219 | `kGh_arcgis_rest_services_EDCO_Address_Points_FeatureServer_0` | 2,221 | 2,221 | 0.00% | ok |
| 220 | `nIYaaSv3_arcgis_rest_services_Address_Points_FeatureServer_0` | 2,210 | 2,210 | 0.00% | ok |
| 221 | `ces_suwannee_address_a_ae_zones_nobuffer_pts_FeatureServer_0` | 2,204 | 2,204 | 0.00% | ok |
| 222 | `8_arcgis_rest_services_Vulnerable_E911_Sites_FeatureServer_0` | 2,191 | 2,191 | 0.00% | ok |
| 223 | `_arcgis_rest_services_Residential_Addresses__FeatureServer_0` | 2,177 | 2,177 | 0.00% | ok |
| 224 | `t_arcgis_rest_services_HainesAddressesOnline_FeatureServer_0` | 2,150 | 2,150 | 0.00% | ok |
| 225 | `st_services_SiteStructureAddressPoints_NG911_FeatureServer_0` | 2,138 | 2,138 | 0.00% | ok |
| 226 | `rvices_PanguitchLake_DamInundation_Addresses_FeatureServer_0` | 2,122 | 2,122 | 0.00% | ok |
| 227 | `4_arcgis_rest_services_TarentumAddressPoints_FeatureServer_0` | 2,121 | 2,121 | 0.00% | ok |
| 228 | `gis_rest_services_Eureka_Address_Points_2025_FeatureServer_0` | 2,108 | 2,108 | 0.00% | ok |
| 229 | `_UG_Owned_Parcels_Address_Corrected_Geocoded_FeatureServer_0` | 2,108 | 2,108 | 0.00% | ok |
| 230 | `rcgis_rest_services_AddressPoints_Commercial_FeatureServer_0` | 2,102 | 2,102 | 0.00% | ok |
| 231 | `F_arcgis_rest_services_DiamondVale_Addresses_FeatureServer_0` | 2,095 | 2,095 | 0.00% | ok |
| 232 | `5S6ormOiLNm_arcgis_rest_services_911_Address_FeatureServer_0` | 2,066 | 2,066 | 0.00% | ok |
| 233 | `gis_rest_services_Address_Pnts_Parcel_2023_FeatureServer_373@未定位-2` | 1,998 | 1,998 | 0.00% | ok |
| 234 | `rcgis_rest_services_Address_Pnts_Parcel_2022_FeatureServer_5` | 1,989 | 1,989 | 0.00% | ok |
| 235 | `services_Site_Structure_Address_Points_view_FeatureServer_33` | 1,987 | 1,987 | 0.00% | ok |
| 236 | `rest_services_Site_Structure_Address_Points_FeatureServer_33` | 1,987 | 1,987 | 0.00% | ok |
| 237 | `gis_rest_services_SiteStructureAddressPoint_FeatureServer_33` | 1,987 | 1,987 | 0.00% | ok |
| 238 | `6_arcgis_rest_services_Nome_Street_Addresses_FeatureServer_0` | 1,967 | 1,967 | 0.00% | ok |
| 239 | `ces_Master_Address_Points__Public_View_Layer_FeatureServer_3` | 1,959 | 1,959 | 0.00% | ok |
| 240 | `DOMEad_arcgis_rest_services_Wetzel_AddressFZ_FeatureServer_1` | 1,951 | 1,951 | 0.00% | ok |
| 241 | `KW_arcgis_rest_services_Ward_Address_Changes_FeatureServer_0` | 1,949 | 1,949 | 0.00% | ok |
| 242 | `iKgvCF8FFVXnViG_arcgis_rest_services_Address_FeatureServer_0` | 1,947 | 1,947 | 0.00% | ok |
| 243 | `DOMEad_arcgis_rest_services_Marion_AddressFZ_FeatureServer_1` | 1,942 | 1,942 | 0.00% | ok |
| 244 | `FVXnViG_arcgis_rest_services_Parcels_Address_FeatureServer_0` | 1,939 | 1,939 | 0.00% | ok |
| 245 | `s_rest_services_Address_Points_Info_20260916_FeatureServer_0` | 1,935 | 1,935 | 0.00% | ok |
| 246 | `KoSXWzxRMkz_arcgis_rest_services_Addresses_FeatureServer_401` | 1,920 | 1,920 | 0.00% | ok |
| 247 | `gis_rest_services_Addresses_Mapped_2021_CAMS_FeatureServer_0` | 1,919 | 1,919 | 0.00% | ok |
| 248 | `DOMEad_arcgis_rest_services_Brooke_AddressFZ_FeatureServer_1` | 1,899 | 1,899 | 0.00% | ok |
| 249 | `y9AZK02r2ZNA_arcgis_rest_services_GIS_Layers_FeatureServer_1` | 1,876 | 1,876 | 0.00% | ok |
| 250 | `kHpm8mHFz_arcgis_rest_services_ADDRESS_POINT_FeatureServer_0` | 1,871 | 1,871 | 0.00% | ok |
| 251 | `est_services_EDCOUCH_PROPOSED_ADDRESS_POINTS_FeatureServer_1` | 1,869 | 1,869 | 0.00% | ok |
| 252 | `_arcgis_rest_services_EDCOUCH_ADDRESS_POINTS_FeatureServer_0` | 1,865 | 1,865 | 0.00% | ok |
| 253 | `gis_rest_services_Addresses_Mapped_2022_CAMS_FeatureServer_0` | 1,825 | 1,825 | 0.00% | ok |
| 254 | `arcgis_rest_services_Prescott_Address_Points_FeatureServer_0` | 1,817 | 1,817 | 0.00% | ok |
| 255 | `is_rest_services_AddressPoints_ReadOnly_view_FeatureServer_0` | 1,812 | 1,812 | 0.00% | ok |
| 256 | `rcgis_rest_services_Vulnerable_E911_Sites_np_FeatureServer_0` | 1,788 | 1,788 | 0.00% | ok |
| 257 | `k5uIyuDun_arcgis_rest_services_AddressPoints_FeatureServer_0` | 1,788 | 1,788 | 0.00% | ok |
| 258 | `PwyQh4Za_arcgis_rest_services_Address_Points_FeatureServer_0` | 1,784 | 1,784 | 0.00% | ok |
| 259 | `4b6fClBS_arcgis_rest_services_Address___View_FeatureServer_0` | 1,777 | 1,777 | 0.00% | ok |
| 260 | `est_services_Master_Civic_Addresses_20260729_FeatureServer_0@未定位-1` | 1,744 | 1,744 | 0.00% | ok |
| 261 | `est_services_Master_Civic_Addresses_20260729_FeatureServer_0@未定位-2` | 1,744 | 1,744 | 0.00% | ok |
| 262 | `rest_services_Master_Civic_Addresses_May2026_FeatureServer_0` | 1,743 | 1,743 | 0.00% | ok |
| 263 | `st_services_Master_Civic_Addresses_May2026v2_FeatureServer_0` | 1,743 | 1,743 | 0.00% | ok |
| 264 | `MEad_arcgis_rest_services_Harrison_AddressFZ_FeatureServer_1` | 1,733 | 1,733 | 0.00% | ok |
| 265 | `ces_Broadband_Constituent_Provided_Addresses_FeatureServer_0` | 1,718 | 1,718 | 0.00% | ok |
| 266 | `dnILAITEP_arcgis_rest_services_Address_Point_FeatureServer_2` | 1,702 | 1,702 | 0.00% | ok |
| 267 | `Jw_arcgis_rest_services_SiteAddresses_public_FeatureServer_6` | 1,701 | 1,701 | 0.00% | ok |
| 268 | `arcgis_rest_services_KellyTownshipAddresses_FeatureServer_85` | 1,686 | 1,686 | 0.00% | ok |
| 269 | `IyI_arcgis_rest_services_Address_Pnts_2022_FeatureServer_150` | 1,684 | 1,684 | 0.00% | ok |
| 270 | `cgis_rest_services_Fort_Riley_Address_Points_FeatureServer_0` | 1,683 | 1,683 | 0.00% | ok |
| 271 | `9_arcgis_rest_services_Address_Points_Public_FeatureServer_0` | 1,676 | 1,676 | 0.00% | ok |
| 272 | `is_rest_services_Public_NG911_Core_Data_View_FeatureServer_0` | 1,675 | 1,675 | 0.00% | ok |
| 273 | `zaX_arcgis_rest_services_NYC_Local_Addresses_FeatureServer_7` | 1,620 | 1,620 | 0.00% | ok |
| 274 | `services_VillageAddressPoint_PublicViewLayer_FeatureServer_0` | 1,617 | 1,617 | 0.00% | ok |
| 275 | `b27c6c0658_rest_services_Site_Address_Points_FeatureServer_6` | 1,601 | 1,601 | 0.00% | ok |
| 276 | `3kMP_arcgis_rest_services_EligibleOnly_BEAD1_FeatureServer_0` | 1,597 | 1,597 | 0.00% | ok |
| 277 | `HZWpWI9KS_arcgis_rest_services_AddressPoints_FeatureServer_0` | 1,590 | 1,590 | 0.00% | ok |
| 278 | `w4LCPgUE_arcgis_rest_services_Address_Points_FeatureServer_0` | 1,582 | 1,582 | 0.00% | ok |
| 279 | `nBvEU67JUL8y_arcgis_rest_services_SWCBC_Data_FeatureServer_1` | 1,571 | 1,571 | 0.00% | ok |
| 280 | `fu37yT_arcgis_rest_services_SiteAddressPoint_FeatureServer_1` | 1,558 | 1,558 | 0.00% | ok |
| 281 | `IzSmbRcIgiSLppy_arcgis_rest_services_Address_FeatureServer_0` | 1,556 | 1,556 | 0.00% | ok |
| 282 | `Hy2o_arcgis_rest_services_Bradley_Addressing_FeatureServer_0` | 1,536 | 1,536 | 0.00% | ok |
| 283 | `_rest_services_ADDRESSES_IN_TENNIS_AREA_2026_FeatureServer_0` | 1,525 | 1,525 | 0.00% | ok |
| 284 | `s_rest_services_Jekyll_Addresses_for_FEMAcrs_FeatureServer_0` | 1,490 | 1,490 | 0.00% | ok |
| 285 | `123_a809bf1b562d48db9dfe2c90e0171fd0_results_FeatureServer_0` | 1,487 | 1,487 | 0.00% | ok |
| 286 | `ces_service_6b41a57ebd9d46af952f1886eb3ac91d_FeatureServer_0` | 1,487 | 1,487 | 0.00% | ok |
| 287 | `s_rest_services_100_Mile_House_Address_Point_FeatureServer_0` | 1,478 | 1,478 | 0.00% | ok |
| 288 | `JNFGptQt_arcgis_rest_services_Addressing_PSU_FeatureServer_0` | 1,466 | 1,466 | 0.00% | ok |
| 289 | `9pLl1tVX_arcgis_rest_services_RPZ_Address_Pt_FeatureServer_0` | 1,446 | 1,446 | 0.00% | ok |
| 290 | `Ead_arcgis_rest_services_Marshall_Address_FZ_FeatureServer_1` | 1,441 | 1,441 | 0.00% | ok |
| 291 | `0ZN6Uo0_arcgis_rest_services_Berlin_Base_Map_FeatureServer_1` | 1,436 | 1,436 | 0.00% | ok |
| 292 | `is_rest_services_UtilityAddress_SiteGeocode_FeatureServer_27` | 1,436 | 1,436 | 0.00% | ok |
| 293 | `_rest_services_WI_SSAP_11_2025_MasterAddress_FeatureServer_0` | 1,434 | 1,434 | 0.00% | ok |
| 294 | `s_rest_services_Address_Data_Management_view_FeatureServer_0` | 1,425 | 1,425 | 0.00% | ok |
| 295 | `t_services_Katonah_V16_Buffer_Address_Points_FeatureServer_1` | 1,425 | 1,425 | 0.00% | ok |
| 296 | `arcgis_rest_services_Address_Data_Management_FeatureServer_0` | 1,425 | 1,425 | 0.00% | ok |
| 297 | `6x_arcgis_rest_services_Commercial_Addresses_FeatureServer_2` | 1,399 | 1,399 | 0.00% | ok |
| 298 | `ces_service_774d6c84e7254bbca94f33e55197c59d_FeatureServer_0` | 1,395 | 1,395 | 0.00% | ok |
| 299 | `ces_City_of_Carnation_Addresses_For_SmartGov_FeatureServer_0` | 1,394 | 1,394 | 0.00% | ok |
| 300 | `is_rest_services_Blat_Street_Addressing_WFL1_FeatureServer_1` | 1,370 | 1,370 | 0.00% | ok |
| 301 | `nee_county_911_address_points_aezones_rivers_FeatureServer_0` | 1,370 | 1,370 | 0.00% | ok |
| 302 | `Ead_arcgis_rest_services_Doddridge_AddressFZ_FeatureServer_1` | 1,368 | 1,368 | 0.00% | ok |
| 303 | `_rest_services_Address_Points_Very_High_Fire_FeatureServer_0` | 1,347 | 1,347 | 0.00% | ok |
| 304 | `rest_services_District_of_Clearwater_Address_FeatureServer_1` | 1,322 | 1,322 | 0.00% | ok |
| 305 | `dPQE7iy_arcgis_rest_services_DundeeAddresses_FeatureServer_0` | 1,306 | 1,306 | 0.00% | ok |
| 306 | `yWb5_arcgis_rest_services_Historic_Addresses_FeatureServer_0` | 1,283 | 1,283 | 0.00% | ok |
| 307 | `st_services_AddressManagement_AddressManager_FeatureServer_0` | 1,265 | 1,265 | 0.00% | ok |
| 308 | `s_rest_services_Addressing_AddressManagement_FeatureServer_0` | 1,265 | 1,265 | 0.00% | ok |
| 309 | `er_2022_LES_Camp_Participant_Addresses_view_FeatureServer_39` | 1,260 | 1,260 | 0.00% | ok |
| 310 | `services_AOI_E911_2024_Commercial_100yrSLR2_FeatureServer_82` | 1,234 | 1,234 | 0.00% | ok |
| 311 | `cgis_rest_services_Student_Address_Locations_FeatureServer_0` | 1,233 | 1,233 | 0.00% | ok |
| 312 | `teAddresses_b6621a983dc8419ea5a4f8d3eb11a342_FeatureServer_0` | 1,220 | 1,220 | 0.00% | ok |
| 313 | `_rest_services_FHSZ_Address_Points_Selection_FeatureServer_1` | 1,208 | 1,208 | 0.00% | ok |
| 314 | `_services_AOI_E911_2024_Commercial_50yrSLR1_FeatureServer_81` | 1,196 | 1,196 | 0.00% | ok |
| 315 | `4B7m3xu6_arcgis_rest_services_Wheeler07_E911_FeatureServer_0` | 1,196 | 1,196 | 0.00% | ok |
| 316 | `2Mh_arcgis_rest_services_Property_Addresses__FeatureServer_0` | 1,182 | 1,182 | 0.00% | ok |
| 317 | `x7SOeX2vv_arcgis_rest_services_NEW_ADDRESSES_FeatureServer_0` | 1,176 | 1,176 | 0.00% | ok |
| 318 | `rcgis_rest_services_Village_of_Chase_Address_FeatureServer_1` | 1,164 | 1,164 | 0.00% | ok |
| 319 | `vices_Authorized_Short_Term_Rental_Addresses_FeatureServer_0` | 1,155 | 1,155 | 0.00% | ok |
| 320 | `_6_26_23_Address_Points_Tax_Lot_Address_Only_FeatureServer_0` | 1,136 | 1,136 | 0.00% | ok |
| 321 | `ng_Authority_Unit_Address_Points_Public_View_FeatureServer_1` | 1,119 | 1,119 | 0.00% | ok |
| 322 | `_arcgis_rest_services_Cordova_Address_Points_FeatureServer_0` | 1,111 | 1,111 | 0.00% | ok |
| 323 | `rest_services_District_of_Logan_Lake_Address_FeatureServer_1` | 1,109 | 1,109 | 0.00% | ok |
| 324 | `s_Site_Addresses_within_1000_of_Dominion_ROW_FeatureServer_0` | 1,102 | 1,102 | 0.00% | ok |
| 325 | `uoQUZ_arcgis_rest_services_Public_AddressPts_FeatureServer_0` | 1,101 | 1,101 | 0.00% | ok |
| 326 | `arcgis_rest_services_1377_000_Address_Points_FeatureServer_0` | 1,093 | 1,093 | 0.00% | ok |
| 327 | `services_City_of_Canton_Commercial_Addresses_FeatureServer_0` | 1,092 | 1,092 | 0.00% | ok |
| 328 | `aD4l_arcgis_rest_services_SI_Address_Points_FeatureServer_24` | 1,091 | 1,091 | 0.00% | ok |
| 329 | `IrBQUeN_arcgis_rest_services_Arena_Addresses_FeatureServer_0` | 1,089 | 1,089 | 0.00% | ok |
| 330 | `rcgis_rest_services_CLPPP_Outreach_Addresses_FeatureServer_0` | 1,075 | 1,075 | 0.00% | ok |
| 331 | `_services_SWF_Local_Residents_Area_Addresses_FeatureServer_0` | 1,068 | 1,068 | 0.00% | ok |
| 332 | `Y7V8UHl6XumF_arcgis_rest_services_BC_Address_FeatureServer_0` | 1,047 | 1,047 | 0.00% | ok |
| 333 | `ad_arcgis_rest_services_Monongalia_AddressFZ_FeatureServer_1` | 1,037 | 1,037 | 0.00% | ok |
| 334 | `rvices_Resort_Municipality_Sun_Peaks_Address_FeatureServer_1` | 1,034 | 1,034 | 0.00% | ok |
| 335 | `31gq_arcgis_rest_services_Address_Selection1_FeatureServer_0` | 1,028 | 1,028 | 0.00% | ok |
| 336 | `arcgis_rest_services_ED_AddressPoints_Keller_FeatureServer_0` | 1,023 | 1,023 | 0.00% | ok |
| 337 | `ESEUr5jw_arcgis_rest_services_BBA_Addresses_FeatureServer_65` | 999 | 999 | 0.00% | ok |
| 338 | `2OG_arcgis_rest_services_High_Risk_Addresses_FeatureServer_0` | 992 | 992 | 0.00% | ok |
| 339 | `kedEx0oU_arcgis_rest_services_NMSU_Addresses_FeatureServer_0` | 989 | 989 | 0.00% | ok |
| 340 | `mKoNl0E6_arcgis_rest_services_Address_Points_FeatureServer_3` | 979 | 979 | 0.00% | ok |
| 341 | `0KIvKRHGQ21ksm_arcgis_rest_services_Map_WFL1_FeatureServer_0` | 971 | 971 | 0.00% | ok |
| 342 | `2_arcgis_rest_services_Yurok_Address_Offline_FeatureServer_9` | 962 | 962 | 0.00% | ok |
| 343 | `_to_Buffer_of_Guelph_Single_Addresses___copy_FeatureServer_0@未定位-2` | 941 | 941 | 0.00% | ok |
| 344 | `es_Lake_Stevens_Multifamily_Addresses_Points_FeatureServer_0` | 941 | 941 | 0.00% | ok |
| 345 | `gis_rest_services_Sands_Point_Address_Points_FeatureServer_0` | 930 | 930 | 0.00% | ok |
| 346 | `dison_com_arcgis_rest_services_Public_OPEN_DATA_MapServer_26` | 929 | 929 | 0.00% | ok |
| 347 | `s_rest_services_District_of_Barriere_Address_FeatureServer_1` | 898 | 898 | 0.00% | ok |
| 348 | `ation_Static_Point_PSAP911_ServiceAddresses_FeatureServer_60` | 891 | 891 | 0.00% | ok |
| 349 | `MJMFp00W0CZ2tFbf_arcgis_rest_services_AptNos_FeatureServer_2` | 888 | 888 | 0.00% | ok |
| 350 | `t_services_Coordinate_vs_Address_Points_WFL1_FeatureServer_0` | 886 | 886 | 0.00% | ok |
| 351 | `j_arcgis_rest_services_Assessment_Addresses_FeatureServer_52` | 861 | 861 | 0.00% | ok |
| 352 | `edEx0oU_arcgis_rest_services_Mesilla_Address_FeatureServer_0` | 852 | 852 | 0.00% | ok |
| 353 | `gis_rest_services_Address_Points_Public_View_FeatureServer_0@未定位-1` | 851 | 851 | 0.00% | ok |
| 354 | `vQRLjoru_arcgis_rest_services_AddressPtsView_FeatureServer_2` | 836 | 836 | 0.00% | ok |
| 355 | `_arcgis_rest_services_Meade_Co_E911_Hydrants_FeatureServer_0` | 824 | 824 | 0.00% | ok |
| 356 | `cgis_rest_services_OpenCases_byAddressPoints_FeatureServer_1` | 822 | 822 | 0.00% | ok |
| 357 | `lDOMEad_arcgis_rest_services_Tyler_AddressFZ_FeatureServer_1` | 814 | 814 | 0.00% | ok |
| 358 | `arcgis_rest_services_WVAddressPoints_TylerFZ_FeatureServer_0` | 814 | 814 | 0.00% | ok |
| 359 | `R_arcgis_rest_services_Guelph_Addresses_WFL1_FeatureServer_0` | 811 | 811 | 0.00% | ok |
| 360 | `cgis_rest_services_WaterMeterAddressesJoined_FeatureServer_1` | 809 | 809 | 0.00% | ok |
| 361 | `is_rest_services_Village_of_Ashcroft_Address_FeatureServer_1` | 809 | 809 | 0.00% | ok |
| 362 | `rvices_Caliente_Site_Address_Points_Viewing_FeatureServer_20` | 797 | 797 | 0.00% | ok |
| 363 | `0p_arcgis_rest_services_Address_Biltmoreway_FeatureServer_14` | 795 | 795 | 0.00% | ok |
| 364 | `services_OpenCases_byAddressPoints_Feb142023_FeatureServer_0` | 784 | 784 | 0.00% | ok |
| 365 | `U67JUL8y_arcgis_rest_services_Searsmont_E911_FeatureServer_0` | 783 | 783 | 0.00% | ok |
| 366 | `Npbr2SGIhQvrH_arcgis_rest_services_Addresses_FeatureServer_0` | 2 | 2 | 0.00% | ok |
| 367 | `WodG9Kll_arcgis_rest_services_Address_Points_FeatureServer_0` | 2 | 2 | 0.00% | ok |
| 368 | `a0SJxRv_arcgis_rest_services_Minnesota_NG911_FeatureServer_0` | 1 | 1 | 0.00% | ok |
| 369 | `IvN_arcgis_rest_services_ProposedSiteAddress_FeatureServer_0` | 1 | 1 | 0.00% | ok |
| 370 | `_Property_Profile___No_Site_Address___1_2026_FeatureServer_0` | 1 | 1 | 0.00% | ok |
| 371 | `_rest_services_E911_Origin_Point_NAD27_V2501_FeatureServer_0` | 1 | 1 | 0.00% | ok |
| 372 | `rcgis_rest_services_New_911_Address_Requests_FeatureServer_0` | - | 0 | 0.00% | empty |
| 373 | `ocEBv1Ip_arcgis_rest_services_Address___View_FeatureServer_0` | - | 0 | 0.00% | empty |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=07b
python3 collect/full_plan.py --stage 07b --size 6 --out collect/ledger/07b_plan.json
python3 collect/full_shard.py --stage 07b --shard 0 --plan collect/ledger/07b_plan.json
```
