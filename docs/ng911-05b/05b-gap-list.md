# 05b 缺口清单（2026-11-21 · 只读摸底）

- **declared 源**：`run 44865991911` 的 `plan-05b` artifact（id 14692340122，sha256 `d5ff5467…`）**没有 `expect_by_layer`** → `declared_source=unavailable`；
  **分母 = expect_live**（计划期 `returnCountOnly` 实测）。不用总量/筛查产物倒推逐层 declared。
- **分子 = 实采 rows**（`collect/05b_ledger.json`）；账本没有的层 `rows=null`，**不填 0 冒充**。
- 判定：`ok` / `partial`（账本已标 partial）/ `short`（有行但不足或未采）/ `unverified`（服务已死）/ `pending`（暂时性失败，expect 未知、门禁不判）。

## 汇总

| 项 | 值 |
|---|---|
| 计划剩余层数 | **583** |
| declared 合计 | **不可得**（artifact 无逐层 declared） |
| expect_live 合计 | **27,508,679** 行（530/583 层有分母） |
| 实采 rows 合计 | **229,697** 行 |
| **预期缺口行数** | **1,280,025** 行 |
| 五类判定 | ok 1 / partial 4 / short 525 / unverified 11 / pending 42 |
| 归因 | missing 514 / short 15 / upstream_dead 11 / transient 42 / ok 1 |

> **585 → 583**：585 是 run 的完整计划；`full_plan` 默认 `skip_done=true` 刷掉 2 层已结论层（`_cog_…test_Address_Point_FeatureServer_0` 已 ok 9,046/9,046；`_com_geoserver_…Public_GIS_Data_FeatureServer_0` 已判 empty）→ 583 进探针。
> **585 → 579** 是另一条线：579 是 2026-11-20 过期量测快照，比 585 少 6 层（全为 partial、被 W33-040 否决拉回），见 `585-vs-579.md`。两条不冲突：585 ⊃ 579，585 −2(已结论) = 583。

## 缺口最大的 20 层（按缺口行数降序）

| # | 层 | expect_live | rows | 缺口 | 缺比 | 判定 | 归因 |
|---|---|---|---|---|---|---|---|
| 1 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | 279,299 | 0 | 279,299 | 100.0% | short | short |
| 2 | `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 209,203 | 100.0% | short | short |
| 3 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,275 | 0 | 207,275 | 100.0% | short | short |
| 4 | `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,275 | 0 | 207,275 | 100.0% | short | short |
| 5 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,600 | 98,714 | 98.405% | short | short |
| 6 | `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 56,800 | 99.845% | short | short |
| 7 | `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 50,911 | 100.0% | short | short |
| 8 | `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 50,423 | 100.0% | short | short |
| 9 | `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 49,374 | 100.0% | short | short |
| 10 | `st_services_Schools_ChathamSchools_AddressPoints_MapServer_0` | 46,456 | 0 | 46,456 | 100.0% | short | short |
| 11 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | 10,564 | 0 | 10,564 | 100.0% | short | short |
| 12 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | 7,854 | 54.278% | partial | short |
| 13 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | 2,676 | 11.512% | partial | short |
| 14 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | 2,674 | 11.506% | partial | short |
| 15 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 9,628 | 9,101 | 527 | 5.474% | partial | short |

## 不可判层（unverified + pending，全部 53 层）

| 层 | 判定 | 归因 | 依据 |
|---|---|---|---|
| `is_rest_services_Address_Points_Council_Area_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4` | pending | transient | URLError: <urlopen error timed out> |
| `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":499,"message":"Token Required","m |
| `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | pending | transient | URLError: <urlopen error timed out> |
| `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5` | pending | transient | URLError: <urlopen error timed out> |
| `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | pending | transient | URLError: <urlopen error timed out> |
| `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | pending | transient | URLError: <urlopen error timed out> |
| `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":500,"message":null,"details":[]}} |
| `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | pending | transient | URLError: <urlopen error timed out> |
| `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | pending | transient | URLError: <urlopen error [Errno 111] Connection refused> |
| `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | pending | transient | HTTP 403: <!DOCTYPE html> <!--[if lt IE 7]> <html class="no- |
| `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"messageCode":"CONT_0001","me |
| `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | pending | transient | URLError: <urlopen error timed out> |
| `_org_gisarcweb_rest_services_Base_Base_Addresses_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54` | pending | transient | URLError: <urlopen error timed out> |
| `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | pending | transient | URLError: <urlopen error timed out> |
| `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10` | pending | transient | URLError: <urlopen error timed out> |
| `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | pending | transient | HTTP 403: <!DOCTYPE html> <!--[if lt IE 7]> <html class="no- |
| `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | pending | transient | URLError: <urlopen error timed out> |
| `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | pending | transient | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD>< |
| `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0` | pending | transient | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD>< |
| `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` | pending | transient | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD>< |
| `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0` | pending | transient | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD>< |
| `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | pending | transient | wall_cap: 未在 240s 内完成 |
| `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1` | pending | transient | URLError: <urlopen error [Errno -3] Temporary failure in nam |
| `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` | pending | transient | URLError: <urlopen error [Errno -5] No address associated wi |
| `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | unverified | upstream_dead | no_count: {"error":{"code":400,"message":"Invalid URL","deta |
| `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | pending | transient | HTTP 403: <!DOCTYPE html><html lang="en-US"><head><title>Jus |
| `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | pending | transient | URLError: <urlopen error timed out> |
| `g_arcgis_rest_services_Open_Data_Open_Data_1_FeatureServer_2` | unverified | upstream_dead | HTTP 502: <!doctype html><html lang="en"><meta charset="UTF- |

> 完整 583 层明细见 `collect/ledger/05b_gap_list.json`。
