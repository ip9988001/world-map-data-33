# 60 个 probe_failed 层重探分诊（2026-11-21）

判定口径（写死在 `collect/ledger/05b_plan_probe_retry.json` 顶部，未中途改）：

- `alive` —— 重探拿到 `returnCountOnly` 正常返回（含 count=0）
- `unverified` —— 服务已死：HTTP 400/403/404/500/502/503、TLS 握手失败、body 含 `no Query` / `not supported` / `token required`
- `pending` —— 一时超时 / 429 / 连接重置等；`expect=null`，进待采、**门禁不判**

> 首轮 60s×3 超出墙钟预算被中止；补探统一 25s×2（超时仍判 `pending`，口径不变）。

| # | 层 | 类 | 依据 | 耗时 ms |
|---|---|---|---|---|
| 1 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | unverified | no_count: {"error":{"code":499,"message":"Token Required","messageCode":"GWM_000 | 511 |
| 2 | `is_rest_services_Address_Points_Council_Area_FeatureServer_0` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 517 |
| 3 | `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 1013 |
| 4 | `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | unverified | no_count: {"error":{"code":500,"message":null,"details":[]}} | 827 |
| 5 | `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | alive | - | 1854 |
| 6 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | alive | - | 1011 |
| 7 | `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | pending | HTTP 403: <!DOCTYPE html> <!--[if lt IE 7]> <html class="no-js ie6 oldie" lang=" | 2238 |
| 8 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | pending | URLError: <urlopen error [Errno 111] Connection refused> | 2693 |
| 9 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | alive | - | 1065 |
| 10 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 321 |
| 11 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | unverified | no_count: {"error":{"code":400,"messageCode":"CONT_0001","message":"Item does no | 525 |
| 12 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | alive | - | 1136 |
| 13 | `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | pending | URLError: <urlopen error timed out> | 52348 |
| 14 | `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0` | pending | URLError: <urlopen error timed out> | 52384 |
| 15 | `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4` | pending | URLError: <urlopen error timed out> | 52396 |
| 16 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | pending | URLError: <urlopen error timed out> | 52532 |
| 17 | `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0` | pending | URLError: <urlopen error timed out> | 52631 |
| 18 | `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 284 |
| 19 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | pending | URLError: <urlopen error timed out> | 52801 |
| 20 | `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | pending | URLError: <urlopen error timed out> | 52810 |
| 21 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | pending | URLError: <urlopen error timed out> | 52436 |
| 22 | `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 410 |
| 23 | `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5` | pending | URLError: <urlopen error timed out> | 53089 |
| 24 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | alive | - | 1051 |
| 25 | `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | alive | - | 1007 |
| 26 | `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | pending | HTTP 403: <!DOCTYPE html> <!--[if lt IE 7]> <html class="no-js ie6 oldie" lang=" | 2245 |
| 27 | `_org_gisarcweb_rest_services_Base_Base_Addresses_MapServer_0` | pending | URLError: <urlopen error timed out> | 52276 |
| 28 | `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 352 |
| 29 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | pending | URLError: <urlopen error timed out> | 53395 |
| 30 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | pending | URLError: <urlopen error timed out> | 53557 |
| 31 | `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54` | pending | URLError: <urlopen error timed out> | 52291 |
| 32 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10` | pending | URLError: <urlopen error timed out> | 52289 |
| 33 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | pending | URLError: <urlopen error timed out> | 52651 |
| 34 | `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0` | pending | URLError: <urlopen error timed out> | 52621 |
| 35 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | pending | URLError: <urlopen error timed out> | 53163 |
| 36 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | pending | URLError: <urlopen error timed out> | 52220 |
| 37 | `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | pending | URLError: <urlopen error timed out> | 52367 |
| 38 | `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | pending | URLError: <urlopen error timed out> | 52297 |
| 39 | `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | pending | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>Access Den | 2291 |
| 40 | `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0` | pending | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>Access Den | 2311 |
| 41 | `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` | pending | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>Access Den | 2274 |
| 42 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0` | pending | HTTP 403: <HTML><HEAD> <TITLE>Access Denied</TITLE> </HEAD><BODY> <H1>Access Den | 2255 |
| 43 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | pending | URLError: <urlopen error timed out> | 52221 |
| 44 | `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | unverified | no_count: {"error":{"code":400,"message":"Invalid URL","details":["Invalid URL"] | 396 |
| 45 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | pending | URLError: <urlopen error timed out> | 52222 |
| 46 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | pending | URLError: <urlopen error timed out> | 52420 |
| 47 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | pending | HTTP 403: <!DOCTYPE html><html lang="en-US"><head><title>Just a moment...</title | 2237 |
| 48 | `g_arcgis_rest_services_Open_Data_Open_Data_1_FeatureServer_2` | unverified | HTTP 502: <!doctype html><html lang="en"><meta charset="UTF-8"><meta content="no | 1169 |
| 49 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | alive | - | 1002 |
| 50 | `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1` | pending | URLError: <urlopen error [Errno -3] Temporary failure in name resolution> | 16144 |
| 51 | `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` | pending | URLError: <urlopen error [Errno -5] No address associated with hostname> | 35185 |
| 52 | `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | pending | URLError: <urlopen error timed out> | 52229 |
| 53 | `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | pending | URLError: <urlopen error timed out> | 52493 |
| 54 | `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | pending | URLError: <urlopen error timed out> | 52229 |
| 55 | `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | pending | URLError: <urlopen error timed out> | 52205 |
| 56 | `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | pending | URLError: <urlopen error timed out> | 52795 |
| 57 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | pending | URLError: <urlopen error timed out> | 53085 |
| 58 | `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | pending | URLError: <urlopen error timed out> | 55812 |
| 59 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0` | pending | URLError: <urlopen error timed out> | 152321 |
| 60 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | pending | wall_cap: 未在 240s 内完成 | 0 |

## 三类计数

- **alive**：7 层
- **unverified**：11 层
- **pending**：42 层
