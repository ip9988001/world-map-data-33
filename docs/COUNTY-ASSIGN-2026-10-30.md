# 逐行判县 · 全量实跑（2026-10-30）

> 本文件的数字**全部由 `collect/county_assign.py --summary --doc` 从逐层 `rows-<layer>.json` 渲染**，不手抄；复现命令见文末。

> 一句话：**248,721,878 行里 230,703,654 行（92.76%）落到具体县**，UNLOCATED 18,018,224 行（7.24%）三档闭合；`state_anomaly` **255 层**（134,294,015 行），`suspect_layer` **88 层**。

## 一、口径（固定，不随层变）

| 项 | 口径 |
|---|---|
| 县索引 | **全美 3,089 县一次加载**（本地 `analysis/tiger_county/<ST>.json.gz`），`1°` 网格预筛 → 命中必须过射线法 PIP |
| 层的州 | **以 `layer_plan.csv`/层清单为准**；属性州（数据里的 STATE 列）只做校验 |
| 属性州冲突 | 记 `state_anomaly`（层/属性值/清单值/行数），**不参与过滤** |
| 跨州溢出 | **合法**。点落在邻县/邻州照判，不因「州不符」改判（宗地跨县是真实情况） |
| 不能判 | 落 `UNLOCATED`，且必须拆成三档相加：无坐标 / 投影坐标 / 判不出 |
| 可疑层 | 一层 UNLOCATED 占比 > 50% → `suspect_layer`（进人工复核，不自动丢） |
| 县界精度 | bbox 只做网格预筛，绝不当结论（已实证 GA 县界 46% 顶点会落进邻县 bbox） |

## 二、覆盖（目标 vs 可判 vs 实跑）

| 口径 | 层数 | 行数 | 说明 |
|---|---|---|---|
| 目标（field-map v2 **声明口径**） | 2,364 | 229,082,706 | 2,364 层 = 1,238 宗地 + 1,126 点层 |
| **本轮可判（有 Release 资产）** | **1,158** | **204,612,201** | 计划 `county_plan_all.json` |
| ├ 已跑完（status=ok） | 1,158 | 248,721,878 | 覆盖率 92.76% |
| └ **无资产（记账，不算 unlocated）** | 1,206 | 24,470,505 | 宗地 10b 未跑，资产不在本仓 |

无资产层按类型：

| kind | 层 | 行 |
|---|---|---|
| parcel_situs | 1,206 | 24,470,505 |

状态分布：ok 1158

> ⚠️ **实际读入 248,721,878 行 ≠ 计划声明 204,612,201 行（+21.6%）**：声明值来自 `layer_plan.csv` 的 `row_count`（计划期估算），实测大层普遍低估 —— 全部差额（+44,109,677 行）来自 8 个层，最大一个是全国 NAD 汇总层（声明 3,197 万 / 实际 7,594 万）。统计一律以**实际读入**为准。

## 三、UNLOCATED 总量与占比

| 指标 | 值 |
|---|---|
| 总行数 | 248,721,878 |
| 判出县行数 | 230,703,654 |
| **覆盖率** | **92.7557%** |
| **UNLOCATED 合计** | **18,018,224（7.2443%）** |
| ├ 无坐标（no_coords） | 9,622,183 |
| ├ 投影坐标（proj_failed） | 744,612 |
| └ 有坐标但落不进任何县 | 7,651,429 |

逐层断言 `unlocated_total == no_coords + proj_failed + outside_any_county`（落不了县的一条不漏）。

### UNLOCATED 最大的 5 层（成因逐条）

| # | 层 | 州 | 行数 | UNLOCATED | 占比 | 无坐标 | 投影 | 判不出 | 主因 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `es_WAEVCP_Public_Composite_Score_Parcel_View` | WA | 3,266,900 | 3,266,900 | 100.00% | 3,266,900 | 0 | 0 | 几何未落盘，属性也无经纬度（宗地层老口径：rings 未持久化） |
| 2 | `gis_rest_services_SAMS_NAD_2025_Address_List` | ? | 1,040,301 | 1,040,080 | 99.98% | 0 | 0 | 1,040,080 | 坐标有值但落在美国县界之外（服务端 outSR 错或坐标脏） |
| 3 | `Parcels_Within_500m_From_ParksandGreenspaces` | TX | 1,008,227 | 1,008,227 | 100.00% | 1,008,227 | 0 | 0 | 几何未落盘，属性也无经纬度（宗地层老口径：rings 未持久化） |
| 4 | `s_2026_SOE_GENERAL_USE_MAP___POST_CNG_WFL1_F` | FL | 793,729 | 793,729 | 100.00% | 793,729 | 0 | 0 | 几何未落盘，属性也无经纬度（宗地层老口径：rings 未持久化） |
| 5 | `g_server_rest_services_Hosted_Buildings_2024` | MI | 774,560 | 774,560 | 100.00% | 774,560 | 0 | 0 | 几何未落盘，属性也无经纬度（宗地层老口径：rings 未持久化） |

> 成因列由三档里最大的那一项判定：无坐标 = 采集时几何没落盘；投影坐标 = 属性里是 X/Y（easting/northing）但没反推 EPSG（**不猜**）；判不出 = 有 WGS84 坐标却落在所有县多边形之外（服务端 outSR 没生效或坐标脏）。

## 四、state_anomaly 全量清单（255 层 / 134,294,015 行）

**按类型拆开看**（判县一行都没被过滤，这些只是记账）：

| 类型 | 层数 | 行数 | 其中州不符行数 | 含义 |
|---|---|---|---|---|
| `conflict` | 79 | 7,558,684 | 7,381,419 | 属性州 ≠ 清单州（层标错州） |
| `geo_conflict` | 108 | 80,633,561 | 80,609,753 | 清单州 ≠ 绝大多数行所在县的州（清单错或跨州大层） |
| `list_missing` | 68 | 46,101,770 | 0 | 清单没有州（`未定位`/空），属性或几何能看出州 |

| # | 层 | 类型 | 清单值 | 属性值 | 县多边形州 | 行数 | 州不符行数 |
|---|---|---|---|---|---|---|---|
| 1 | `UCXd1_arcgis_rest_services_USA_NAD_Addresses_Feature` | geo_conflict | ID | （无州列） | TX | 75,937,418 | 75,932,001 |
| 2 | `aIfH92NqI_arcgis_rest_services_AddressNC_v1_FeatureS` | list_missing | （空） | NC | NC | 5,703,287 | 0 |
| 3 | `2bbc_rest_services_AGOL_MAD_AGOL_R2R_ADDRPTS_Feature` | list_missing | （空） | MA | MA | 3,623,798 | 0 |
| 4 | `ces_Ky_911_Site_Structure_Address_Points_gdb_Feature` | list_missing | （空） | KY | KY | 2,489,939 | 0 |
| 5 | `ces_Ky_911_Site_Structure_Address_Points_WGS84WM_Map` | conflict | IN | KY | KY | 2,416,763 | 2,416,592 |
| 6 | `rest_services_Maricopa_County_Address_Points_Feature` | list_missing | （空） | （无州列） | AZ | 2,139,242 | 0 |
| 7 | `vzKRJ_arcgis_rest_services_AddressPoint_GIO_FeatureS` | list_missing | （空） | （无州列） | AZ | 1,567,568 | 0 |
| 8 | `KUeVR_arcgis_rest_services_COH_SiteAddresses_Feature` | list_missing | （空） | TX | TX | 1,550,454 | 0 |
| 9 | `arcgis_rest_services_PSU_PEMA_ADDRESS_POINTS_Feature` | list_missing | （空） | PA | PA | 1,321,760 | 0 |
| 10 | `t_services_GISLibrary_VWAddressPointsCommons_Feature` | list_missing | （空） | MN | MN | 1,295,755 | 0 |
| 11 | `st_services_Address_Points_SAMs_Lite_1030896_Feature` | conflict | CA | NV | NV | 1,068,846 | 1,068,807 |
| 12 | `gis_rest_services_SAMS_NAD_2025_Address_List_Feature` | list_missing | （空） | WV | VA | 1,040,301 | 0 |
| 13 | `rest_services_NYS_Address_Points_Boroughs_v1_Feature` | list_missing | （空） | NY | NY | 967,362 | 0 |
| 14 | `i9Bag_arcgis_rest_services_LeadAddressPoints_Feature` | list_missing | （空） | （无州列） | NY | 919,884 | 0 |
| 15 | `ces_AddressDataManagement_SBC_Site_Addresses_Feature` | list_missing | （空） | （无州列） | CA | 872,232 | 0 |
| 16 | `is_rest_services_Sheriff_Address_Points_view_Feature` | list_missing | （空） | （无州列） | CA | 806,677 | 0 |
| 17 | `s_rest_services_Maine_E911_Addresses_Feature_Feature` | list_missing | （空） | ME | ME | 801,786 | 0 |
| 18 | `s_rest_services_AddressesForHeatAppOnly_2022_Feature` | list_missing | （空） | （无州列） | FL | 769,181 | 0 |
| 19 | `s_rest_services_Maine_E911_Addresses_Feature_Feature` | list_missing | （空） | ME | ME | 746,521 | 0 |
| 20 | `aps_raleighnc_gov_arcgis_rest_services_Addresses_Map` | list_missing | （空） | NC | NC | 719,661 | 0 |
| 21 | `MP_arcgis_rest_services_NG911_Address_Points_Feature` | list_missing | （空） | FL | FL | 712,005 | 0 |
| 22 | `NARefyPVtAeuJPU_arcgis_rest_services_Address_Feature` | list_missing | （空） | CA | CA | 711,028 | 0 |
| 23 | `gov_server_rest_services_MasterAddressPoints_Feature` | list_missing | （空） | NC | NC | 679,114 | 0 |
| 24 | `ov_arcgis_rest_services_CountyData_MasterAddress_Map` | list_missing | （空） | NC | NC | 679,114 | 0 |
| 25 | `arcgis_rest_services_Address_Points_20260709_Feature` | list_missing | （空） | （无州列） | TX | 667,289 | 0 |
| 26 | `est_services_Addressing_Addressing_AddressPoints_Map` | list_missing | （空） | PA | PA | 664,977 | 0 |
| 27 | `arcgis_rest_services_Address_Points_20260710_Feature` | list_missing | （空） | （无州列） | TX | 662,742 | 0 |
| 28 | `rest_services_Sacramento_County_CA_Addresses_Feature` | geo_conflict | KS | （无州列） | CA | 662,634 | 662,632 |
| 29 | `f6d6e8_rest_services_CoSA_BrowseSAStoryMapLayers_Map` | list_missing | （空） | TX | TX | 622,970 | 0 |
| 30 | `erenceLayers_CWD_Service_Area_Address_Points_Feature` | list_missing | （空） | OH | OH | 614,934 | 0 |
| 31 | `_rest_services_Site_Structure_Address_Points_Feature` | list_missing | （空） | NV | NV | 559,467 | 0 |
| 32 | `83377937711d_rest_services_DSM_Pub_CIPP_Viewer_MapSe` | list_missing | （空） | NY | NY | 543,816 | 0 |
| 33 | `Oy_arcgis_rest_services_Address_Lookup1_WFL1_Feature` | conflict | IL | MO | MO | 542,647 | 542,645 |
| 34 | `rjguNyOy_arcgis_rest_services_Address_Points_Feature` | conflict | IL | MO | MO | 542,647 | 542,645 |
| 35 | `STLCO_NG911_Schema_Attributes_081326_gdb_zip_Feature` | conflict | IL | MO | MO | 538,285 | 538,283 |
| 36 | `wake_gov_arcgis_rest_services_Property_Addresses_Map` | list_missing | （空） | （无州列） | NC | 527,756 | 0 |
| 37 | `iUWhdA_arcgis_rest_services_OCAddressLocator_Feature` | list_missing | （空） | （无州列） | FL | 512,950 | 0 |
| 38 | `ZzfsFsB5_arcgis_rest_services_Address_Points_Feature` | list_missing | （空） | GA | GA | 490,319 | 0 |
| 39 | `st_services_Milwaukee_County_Address_Points_FeatureS` | list_missing | （空） | （无州列） | WI | 485,485 | 0 |
| 40 | `5_arcgis_rest_services_OpenDataAddressPoints_Feature` | list_missing | （空） | （无州列） | FL | 483,733 | 0 |
| 41 | `rest_services_hennepin_county_address_points_Feature` | list_missing | （空） | （无州列） | MN | 481,609 | 0 |
| 42 | `arcgis_rest_services_LOCATION_address_points_Feature` | list_missing | （空） | （无州列） | TX | 466,362 | 0 |
| 43 | `toncounty_gov_arcgis_rest_services_Public_Safety_Map` | list_missing | （空） | TX | TX | 431,210 | 0 |
| 44 | `_services_FACILITY_AddressPoints_E911domains_Feature` | list_missing | （空） | （无州列） | RI | 420,441 | 0 |
| 45 | `1ubjUPmd_arcgis_rest_services_Address_Points_Feature` | list_missing | （空） | WA | WA | 416,174 | 0 |
| 46 | `_rest_services_ODC_CITY_LOC_ADDRESSPUBLIC_P_FeatureS` | list_missing | （空） | （无州列） | CO | 415,981 | 0 |
| 47 | `egis_ri_gov_hosting_rest_services_E911_e911Sites_Map` | list_missing | （空） | RI | RI | 408,892 | 0 |
| 48 | `KSwyTBcwN_arcgis_rest_services_AddressPoints_Feature` | list_missing | （空） | TX | TX | 395,965 | 0 |
| 49 | `tyga_gov_hosted_rest_services_Address_Points_Feature` | list_missing | （空） | GA | GA | 391,896 | 0 |
| 50 | `9EYLSnPE_arcgis_rest_services_Address_Points_Feature` | list_missing | （空） | GA | GA | 389,884 | 0 |
| 51 | `E_arcgis_rest_services_AddressingData_Public_Feature` | list_missing | （空） | （无州列） | GA | 389,172 | 0 |
| 52 | `arcgis_rest_services_Site_Address_Points_IPS_Feature` | list_missing | （空） | GA | GA | 388,841 | 0 |
| 53 | `GptQt_arcgis_rest_services_Address_Points_RG_Feature` | list_missing | （空） | （无州列） | PA | 374,426 | 0 |
| 54 | `is_rest_services_ParcelViewer_AddressPoints2_Feature` | list_missing | （空） | MO | MO | 374,142 | 0 |
| 55 | `ClqmipKpmFK_arcgis_rest_services_FBC_ADDRESS_Feature` | list_missing | （空） | TX | TX | 362,521 | 0 |
| 56 | `y_SiteStructureAddressPoint_point_SP_v1_VIEW_Feature` | list_missing | （空） | VT | VT | 354,563 | 0 |
| 57 | `SCdqoXK_arcgis_rest_services_OpenDataAddress_Feature` | list_missing | （空） | TN | TN | 351,307 | 0 |
| 58 | `9xEgP_arcgis_rest_services_Zanna_E911_Sites_FeatureS` | geo_conflict | NH | （无州列） | VT | 346,678 | 346,651 |
| 59 | `d1_arcgis_rest_services_Vermont_US_Addresses_Feature` | geo_conflict | NH | （无州列） | VT | 342,507 | 342,482 |
| 60 | `nF97m_arcgis_rest_services_Address_Points_RE_Feature` | list_missing | （空） | IL | IL | 341,779 | 0 |
| 61 | `gis_rest_services_ShelbyTN_Addresses_AGOHost_Feature` | conflict | AR | TN | TN | 341,685 | 341,678 |
| 62 | `auma_Centers_for_VT_E911_Site_Locations_WFL1_Feature` | conflict | NH | VT | VT | 341,074 | 341,048 |
| 63 | `net_server_rest_services_Hosted_AddressPoint_Feature` | list_missing | （空） | FL | FL | 334,331 | 0 |
| 64 | `rcgis_rest_services_Lake_County_IL_Addresses_Feature` | geo_conflict | KS | （无州列） | IL | 325,394 | 325,394 |
| 65 | `P_arcgis_rest_services_Transit_Addresses_New_Feature` | list_missing | （空） | （无州列） | TX | 317,258 | 0 |
| 66 | `rGr3P_arcgis_rest_services_Transit_Addresses_Feature` | list_missing | （空） | （无州列） | TX | 317,258 | 0 |
| 67 | `uYNYH_arcgis_rest_services_TRANSPO_MAFDAP_PV_Feature` | list_missing | （空） | WA | WA | 308,176 | 0 |
| 68 | `_gov_arcgis_rest_services_GeneralUse_LandRecords_Map` | list_missing | （空） | CO | CO | 306,770 | 0 |
| 69 | `rest_services_Sarasota_County_Address_Points_Feature` | list_missing | （空） | FL | FL | 301,910 | 0 |
| 70 | `hedVoters_Statewide_withSiteTypeDescription_FeatureS` | conflict | MA | RI | RI | 283,974 | 283,959 |
| 71 | `arcgis_rest_services_Nightly_OpenData_Update_Feature` | conflict | CA | NV | NV | 268,132 | 267,893 |
| 72 | `is_rest_services_Chester_County_PA_Addresses_Feature` | geo_conflict | KS | （无州列） | PA | 221,873 | 221,870 |
| 73 | `services_Zanna_E911_Sites_Within_8min_Buffer_Feature` | geo_conflict | NH | （无州列） | VT | 207,581 | 207,571 |
| 74 | `couver_us_arcgis_rest_services_common_BasemapPUB_Map` | geo_conflict | OR | （无州列） | WA | 182,458 | 182,458 |
| 75 | `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_Feature` | conflict | GA | SC | SC | 158,395 | 158,388 |
| 76 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_Feature` | geo_conflict | NH | （无州列） | VT | 139,097 | 139,080 |
| 77 | `cgis_rest_services_Infrastructure_Transportation_Map` | geo_conflict | AL | （无州列） | FL | 129,759 | 129,747 |
| 78 | `_services_Infrastructure_Transportation_Sheriffs_Map` | geo_conflict | AL | （无州列） | FL | 129,759 | 129,747 |
| 79 | `GEllMqef1LMjj_arcgis_rest_services_Addresses_Feature` | geo_conflict | OK | （无州列） | TX | 106,530 | 106,500 |
| 80 | `VWAC8iN_arcgis_rest_services_road_centerline_Feature` | conflict | NY | PA | PA | 97,499 | 97,490 |
| 81 | `is_rest_services_Forsyth_County_GA_Addresses_Feature` | geo_conflict | KS | （无州列） | GA | 93,990 | 93,989 |
| 82 | `mxCAS_arcgis_rest_services_ClermontAddresses_Feature` | geo_conflict | KY | （无州列） | OH | 88,301 | 88,301 |
| 83 | `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_Feature` | geo_conflict | KY | （无州列） | OH | 83,101 | 83,101 |
| 84 | `CXd1_arcgis_rest_services_Fargo_ND_Addresses_Feature` | geo_conflict | KS | （无州列） | ND | 72,684 | 72,684 |
| 85 | `_pa_us_arcgis_rest_services_Hosted_Addresses_Feature` | conflict | NY | PA | PA | 72,208 | 72,205 |
| 86 | `3P_arcgis_rest_services_SiteAddresses_public_Feature` | list_missing | （空） | （无州列） | TX | 71,798 | 0 |
| 87 | `is_rest_services_Building_Permit_Addresssing_Feature` | conflict | LA | MS | MS | 69,365 | 69,361 |
| 88 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_Feature` | geo_conflict | NC | （无州列） | SC | 64,971 | 64,958 |
| 89 | `_rest_services_Randall_County_Addresses_WFL1_Feature` | conflict | OK | TX | TX | 64,757 | 64,757 |
| 90 | `cgis_rest_services_Cedar_Rapids_IA_Addresses_Feature` | geo_conflict | KS | （无州列） | IA | 63,767 | 63,767 |
| 91 | `AQdtmx0tv46_arcgis_rest_services_Address_Nye_Feature` | geo_conflict | CA | （无州列） | NV | 63,594 | 63,592 |
| 92 | `s_rest_services_Marathon_County_WI_Addresses_Feature` | geo_conflict | KS | （无州列） | WI | 59,998 | 59,998 |
| 93 | `d1_arcgis_rest_services_Visalia_CA_Addresses_Feature` | geo_conflict | KS | （无州列） | CA | 57,934 | 57,934 |
| 94 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_Feature` | conflict | ID | MT | MT | 52,649 | 52,648 |
| 95 | `BvD2F_arcgis_rest_services_COG_StreetAddress_Feature` | geo_conflict | LA | （无州列） | MS | 51,392 | 51,392 |
| 96 | `st_services_A4_Landscape_addressverification_Feature` | geo_conflict | AL | （无州列） | FL | 49,808 | 49,795 |
| 97 | `com_arcgis_rest_services_CommunityAddressing_Feature` | geo_conflict | IA | （无州列） | IL | 49,804 | 49,804 |
| 98 | `0JE2L2xUd_arcgis_rest_services_SiteAddresses_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 99 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 100 | `sses_public_33e99042997a472fa1a25a8b6f4465cf_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 101 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 102 | `sses_public_a2522c3dfde94f6da7500df892abf9aa_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 103 | `teAddresses_33e99042997a472fa1a25a8b6f4465cf_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 104 | `teAddresses_b786541565b5475593a786a08ba6b3e2_Feature` | geo_conflict | MO | （无州列） | IL | 49,802 | 49,802 |
| 105 | `sses_public_e7c532395de343e38e58a8463128cfb7_Feature` | geo_conflict | MO | （无州列） | IL | 49,800 | 49,800 |
| 106 | `aNxg1PvwI_arcgis_rest_services_All_Addresses_Feature` | conflict | ID | MT | MT | 48,666 | 48,666 |
| 107 | `s_rest_services_Raleigh_Co_EOC_Address_Sites_Feature` | conflict | VA | WV | ? | 42,165 | 0 |
| 108 | `1_arcgis_rest_services_Bismarck_ND_Addresses_Feature` | geo_conflict | KS | （无州列） | ND | 40,568 | 40,568 |
| 109 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_Feature` | geo_conflict | IN | IN | KY | 36,292 | 32,566 |
| 110 | `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_Feature` | geo_conflict | IN | IN | KY | 36,292 | 32,566 |
| 111 | `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_Feature` | conflict | NY | PA | PA | 35,810 | 35,788 |
| 112 | `arcgis_rest_services_Alexandria_VA_Addresses_Feature` | geo_conflict | DC | （无州列） | VA | 34,927 | 34,925 |
| 113 | `cgis_rest_services_Sarpy_County_NE_Addresses_Feature` | geo_conflict | IA | （无州列） | NE | 33,980 | 33,980 |
| 114 | `1_arcgis_rest_services_Longview_TX_Addresses_Feature` | geo_conflict | KS | （无州列） | TX | 33,603 | 33,603 |
| 115 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_Feature` | conflict | VA | WV | VA | 33,215 | 0 |
| 116 | `rest_services_Cherokee_Address_Analysis_WFL1_Feature` | geo_conflict | NC | （无州列） | SC | 32,167 | 32,166 |
| 117 | `VDElDOMEad_arcgis_rest_services_WayneAddress_Feature` | conflict | KY | WV | ? | 31,980 | 0 |
| 118 | `aLg_arcgis_rest_services_Address_Hemet031325_Feature` | conflict | CA | PA | CA | 30,879 | 0 |
| 119 | `rcgis_rest_services_Buildings_and_Addresses_FeatureS` | conflict | MA | RI | RI | 30,856 | 30,856 |
| 120 | `DgvxltnFwP_arcgis_rest_services_NG911_Layers_Feature` | conflict | AL | FL | FL | 30,273 | 30,271 |
| 121 | `arcgis_rest_services_Wellington_FL_Addresses_Feature` | geo_conflict | KS | （无州列） | FL | 27,213 | 27,213 |
| 122 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_Feature` | conflict | MN | WI | WI | 27,058 | 27,058 |
| 123 | `arcgis_rest_services_Hinesville_GA_Addresses_Feature` | geo_conflict | KS | （无州列） | GA | 26,965 | 26,965 |
| 124 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapS` | geo_conflict | MD | （无州列） | VA | 25,823 | 25,822 |
| 125 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_Feature` | geo_conflict | ID | （无州列） | MT | 25,659 | 25,659 |
| 126 | `_arcgis_rest_services_Shawano_Addresses_2026_Feature` | conflict | MI | WI | WI | 25,427 | 25,413 |
| 127 | `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_Feature` | geo_conflict | IL | （无州列） | KY | 24,465 | 24,464 |
| 128 | `TlITuys_arcgis_rest_services_WyboSiteAddress_Feature` | conflict | MD | VA | VA | 24,136 | 24,136 |
| 129 | `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_Feature` | conflict | AL | FL | FL | 23,334 | 23,334 |
| 130 | `h_arcgis_rest_services_AddressesJuly26B_WFL1_Feature` | geo_conflict | AL | （无州列） | FL | 21,789 | 21,789 |
| 131 | `arcgis_rest_services_Jasper_County_Addresses_Feature` | geo_conflict | GA | （无州列） | SC | 21,594 | 21,594 |
| 132 | `l9_arcgis_rest_services_svcBndryAddress_view_Feature` | geo_conflict | IN | （无州列） | KY | 20,088 | 20,088 |
| 133 | `rcgis_rest_services_Sioux_Falls_SD_Addresses_Feature` | geo_conflict | MN | （无州列） | SD | 19,812 | 19,812 |
| 134 | `_arcgis_rest_services_Wyoming_SAMB_Addresses_Feature` | conflict | VA | WV | ? | 19,767 | 0 |
| 135 | `rcgis_rest_services_Facility_Sites_E911_Clip_Feature` | conflict | MA | RI | RI | 19,154 | 19,152 |
| 136 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_Feature` | conflict | IA | IL | IL | 18,822 | 18,822 |
| 137 | `_arcgis_rest_services_WyomingCountyAddresses_Feature` | conflict | NY | PA | PA | 18,194 | 18,193 |
| 138 | `gis_rest_services_Mailing_Address_Map_2_WFL1_Feature` | conflict | MD | VA | VA | 18,090 | 18,090 |
| 139 | `gis_rest_services_Mailing_Address_Map___WFL1_Feature` | conflict | MD | VA | VA | 18,090 | 18,090 |
| 140 | `rcgis_rest_services_Mailing_Address_Map_WFL1_Feature` | conflict | MD | VA | VA | 18,090 | 18,090 |
| 141 | `kIrNAR_arcgis_rest_services_E911_Share_Files_Feature` | conflict | MO | TN | TN | 17,883 | 17,882 |
| 142 | `cjlmqkA8ypi4T_arcgis_rest_services_Addresses_Feature` | conflict | OH | WV | ? | 17,308 | 0 |
| 143 | `So_arcgis_rest_services_SiteAddresses_public_Feature` | geo_conflict | MO | （无州列） | AR | 16,929 | 16,929 |
| 144 | `rest_services_Addresses_Clark_County_WI_2019_Feature` | conflict | MN | WI | WI | 16,569 | 16,568 |
| 145 | `s_rest_services_Addressing_Addressing_public_Feature` | list_missing | （空） | MN | MN | 15,033 | 0 |
| 146 | `C2HwTkBAlth_arcgis_rest_services_Address_gdb_Feature` | geo_conflict | CA | （无州列） | NV | 14,389 | 14,389 |
| 147 | `ervices_Lee_County_E911_Addresses_and_Roads_FeatureS` | geo_conflict | KY | （无州列） | VA | 14,215 | 14,212 |
| 148 | `sses_public_35d07adabaff4ddba616f6f365b8954e_Feature` | geo_conflict | MO | （无州列） | OK | 14,203 | 14,203 |
| 149 | `kh71mtnDG_arcgis_rest_services_E911addresses_Feature` | geo_conflict | FL | （无州列） | GA | 13,205 | 13,205 |
| 150 | `MJrpz61FbvL5t_arcgis_rest_services_Addresses_Feature` | conflict | MD | VA | VA | 13,058 | 13,058 |
| 151 | `is_rest_services_Grady_Site_Addresses_Public_Feature` | geo_conflict | FL | （无州列） | GA | 12,986 | 12,986 |
| 152 | `rcgis_rest_services_VT_Data___E911_Landmarks_Feature` | conflict | NH | VT | VT | 12,867 | 12,819 |
| 153 | `BYQ9pcCt_arcgis_rest_services_e911_pt_txdist_Feature` | geo_conflict | LA | （无州列） | MS | 12,670 | 12,669 |
| 154 | `m_jOKMO9vKmc98J4JC_arcgis_rest_services_E911_Feature` | conflict | NH | VT | VT | 12,649 | 12,601 |
| 155 | `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_Feature` | conflict | NC | TN | TN | 12,362 | 12,356 |
| 156 | `arcgis_rest_services_PAunderservedstructures_Feature` | geo_conflict | NY | （无州列） | PA | 11,469 | 11,466 |
| 157 | `arcgis_rest_services_BTV_e911_Address_Layers_Feature` | geo_conflict | NY | （无州列） | VT | 11,462 | 11,462 |
| 158 | `rWTl_arcgis_rest_services_Harrison_Addresses_Feature` | conflict | CT | NY | NY | 10,330 | 10,330 |
| 159 | `KcOCt7Lxga2AytI_arcgis_rest_services_Address_Feature` | geo_conflict | MO | （无州列） | OK | 9,700 | 9,005 |
| 160 | `s___Pulse_of_OC_Updated_Draft___Site_Address_Feature` | geo_conflict | AZ | （无州列） | CA | 9,420 | 9,420 |
| 161 | `cyjLcCCpGk8Ri_arcgis_rest_services_Addresses_Feature` | conflict | MD | VA | VA | 8,688 | 8,688 |
| 162 | `s_rest_services_Addressing_Addressing_public_Feature` | list_missing | （空） | MN | MN | 8,278 | 0 |
| 163 | `vlQFEpKtV_arcgis_rest_services_DOUGLASCOUNTY_Feature` | geo_conflict | IA | （无州列） | NE | 8,201 | 8,199 |
| 164 | `DQNT3m6mbJlqZ_arcgis_rest_services_Addresses_Feature` | conflict | MA | RI | RI | 7,733 | 7,733 |
| 165 | `s_rest_services_Richland_County_ND_Addresses_Feature` | geo_conflict | MN | （无州列） | ND | 7,608 | 7,608 |
| 166 | `0hS_arcgis_rest_services_Address_Road_Update_Feature` | geo_conflict | MD | （无州列） | VA | 7,370 | 7 |
| 167 | `CY2_arcgis_rest_services_Dispatcher_Map_WFL1_Feature` | geo_conflict | IL | （无州列） | MO | 7,165 | 7,165 |
| 168 | `_rest_services_E911_Houses_Washington_County_Feature` | conflict | NY | VT | VT | 6,724 | 6,724 |
| 169 | `M5KB8_arcgis_rest_services_E911_PairwiseClip_Feature` | conflict | MA | RI | RI | 6,716 | 6,716 |
| 170 | `wVADPEG6iD24f_arcgis_rest_services_Addresses_Feature` | geo_conflict | MI | （无州列） | MN | 6,031 | 6,031 |
| 171 | `_in_Incident_Address_and_Type_for_Date_Range_Feature` | geo_conflict | MO | （无州列） | AR | 5,929 | 5,929 |
| 172 | `e3_arcgis_rest_services_SiteAddresses_public_Feature` | geo_conflict | MO | （无州列） | OR | 5,586 | 5,586 |
| 173 | `esses_In_Refuse_Recycle_Routes_WFL1_July2019_Feature` | conflict | MD | VA | VA | 5,219 | 5,218 |
| 174 | `arcgis_rest_services_Hartford_911_Addresses__Feature` | geo_conflict | NH | （无州列） | VT | 5,108 | 5,107 |
| 175 | `roY6O3ncx_arcgis_rest_services_MS4_addresses_Feature` | geo_conflict | NC | （无州列） | SC | 5,060 | 5,056 |
| 176 | `sses_public_e6294e415150477cabab0e6e58c126a2_Feature` | geo_conflict | MO | （无州列） | AK | 4,534 | 4,534 |
| 177 | `Ll1tVX_arcgis_rest_services_RPZ_Address_Pt_2_Feature` | geo_conflict | DC | （无州列） | MD | 4,488 | 4,488 |
| 178 | `vOamkQCWQM5KB8_arcgis_rest_services_E911_SLR_Feature` | conflict | MA | RI | RI | 4,360 | 4,360 |
| 179 | `cgis_rest_services_Shrewsbury_Address_Points_Feature` | conflict | IL | MO | MO | 4,204 | 4,204 |
| 180 | `t_services_Shamokin_Address_Points_June_2019_Feature` | geo_conflict | NY | （无州列） | PA | 4,146 | 4,146 |
| 181 | `Find_Locations_in_Address_Points_herndon_va2_Feature` | list_missing | （空） | VA | VA | 4,132 | 0 |
| 182 | `bNao4Cfr_arcgis_rest_services_address_points_Feature` | conflict | NJ | PA | PA | 3,907 | 3,907 |
| 183 | `s_Find_Locations_in_Address_Points_centrvle2_Feature` | conflict | MD | VA | VA | 3,835 | 3,835 |
| 184 | `8Ri_arcgis_rest_services_Secondary_Addresses_Feature` | conflict | MD | VA | VA | 3,764 | 3,764 |
| 185 | `_rest_services_Site_Structure_Address_Points_Feature` | list_missing | （空） | WA | WA | 3,582 | 0 |
| 186 | `4XSFR9wSzw_arcgis_rest_services_ADDRESS_DATA_Feature` | geo_conflict | LA | （无州列） | MS | 3,371 | 3,369 |
| 187 | `p1M_arcgis_rest_services_SnowPlowedAddresses_Feature` | geo_conflict | MD | （无州列） | VA | 3,046 | 3,046 |
| 188 | `ices_Barre_City_Infill_Housing_Analysis_WFL1_Feature` | conflict | NH | VT | VT | 2,983 | 2,983 |
| 189 | `est_services_CaseStudySchuylerMcAuliffe_WFL1_Feature` | conflict | NY | VT | VT | 2,968 | 2,968 |
| 190 | `cgis_rest_services_AddressPoints_Provisional_Feature` | geo_conflict | MI | （无州列） | MN | 2,926 | 2,923 |
| 191 | `m2tY5bzqz10C_arcgis_rest_services_E911Points_Feature` | geo_conflict | NY | （无州列） | VT | 2,923 | 2,923 |
| 192 | `sses_public_f42ca5814db04f79a8d83bc0f50b5212_Feature` | geo_conflict | MO | （无州列） | IL | 2,493 | 2,493 |
| 193 | `_rest_services_COAHOMA_COUNTY_ADDRESS_POINTS_Feature` | conflict | AR | MS | MS | 2,464 | 2,463 |
| 194 | `gis_rest_services_Seneca_Nation_NY_Addresses_Feature` | geo_conflict | KS | （无州列） | NY | 2,253 | 2,253 |
| 195 | `rest_services_Hinesburg_Planning_Zoning_WFL1_Feature` | conflict | NY | VT | VT | 2,092 | 2,092 |
| 196 | `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_Map` | list_missing | （空） | （无州列） | FL | 2,000 | 0 |
| 197 | `ze4GYYo_arcgis_rest_services_Addresses_No_BB_Feature` | geo_conflict | MD | （无州列） | VA | 1,780 | 1 |
| 198 | `tVX_arcgis_rest_services_RPZ_Address_Points2_Feature` | geo_conflict | DC | （无州列） | MD | 1,579 | 1,579 |
| 199 | `mc98J4JC_arcgis_rest_services_MH_e911Addison_Feature` | conflict | NY | VT | ? | 1,270 | 0 |
| 200 | `YDMVmmxMeM_arcgis_rest_services_Crash_Points_Feature` | list_missing | （空） | （无州列） | NC | 1,234 | 0 |
| 201 | `s_rest_services_Addressing_Addressing_public_Feature` | list_missing | （空） | MN | MN | 1,205 | 0 |
| 202 | `4JC_arcgis_rest_services_Rutland_County_E911_Feature` | conflict | NY | VT | VT | 1,171 | 1,170 |
| 203 | `CDFVQ_arcgis_rest_services_Address_Points_C2_Feature` | geo_conflict | NJ | （无州列） | PA | 1,146 | 1,146 |
| 204 | `est_services_New_Mexico_State_Univ_Addresses_Feature` | geo_conflict | KS | （无州列） | NM | 1,077 | 1,077 |
| 205 | `cgis_rest_services_Rubbertown_Addresses_WFL1_Feature` | geo_conflict | IN | （无州列） | KY | 978 | 69 |
| 206 | `w5d_arcgis_rest_services_Calais_VT_Resources_Feature` | conflict | NH | VT | VT | 978 | 978 |
| 207 | `QGbyiuCh_arcgis_rest_services_Address_Points_Feature` | geo_conflict | NJ | （无州列） | NY | 931 | 931 |
| 208 | `ces_Residential_Address_Points_for_Analysis_FeatureS` | geo_conflict | MN | （无州列） | WI | 902 | 902 |
| 209 | `iyTV6_arcgis_rest_services_NASP_Address_view_Feature` | geo_conflict | IN | （无州列） | KY | 735 | 735 |
| 210 | `arcgis_rest_services_Biosolid_Site_Addresses_Feature` | geo_conflict | MD | （无州列） | VA | 696 | 696 |
| 211 | `ices_map_services_MAP_ANR_ANRATLASFPR_WM_NOCACHE_Map` | geo_conflict | NY | （无州列） | VT | 693 | 692 |
| 212 | `_GIS_Participant_Addresses_2019_deidentified_Feature` | geo_conflict | AR | （无州列） | NC | 689 | 689 |
| 213 | `WofKfQhH_arcgis_rest_services_Address_Points_Feature` | geo_conflict | NC | （无州列） | SC | 621 | 621 |
| 214 | `nLN_arcgis_rest_services_1920_Address_Points_Feature` | geo_conflict | IA | （无州列） | NE | 553 | 552 |
| 215 | `CIe16u6G_arcgis_rest_services_Address_Points_Feature` | conflict | IA | NE | NE | 522 | 522 |
| 216 | `est_services_HoustonMap_Planning_and_Development_Map` | list_missing | （空） | （无州列） | TX | 509 | 0 |
| 217 | `_Find_Locations_in_Address_Points_filt_radon_Feature` | conflict | MD | VA | VA | 492 | 492 |
| 218 | `rvices_Find_Locations_in_Address_Points_filt_Feature` | conflict | MD | VA | VA | 492 | 492 |
| 219 | `Aa0SJxRv_arcgis_rest_services_NG911_Template_Feature` | conflict | MO | MN | MN | 478 | 478 |
| 220 | `cgis_rest_services_Property_Address_Features_Feature` | geo_conflict | MI | （无州列） | MN | 431 | 431 |
| 221 | `qdjIQw4R1_arcgis_rest_services_GP_AddressPts_Feature` | conflict | MI | MN | MN | 385 | 385 |
| 222 | `ZN_arcgis_rest_services_Town_Preference_WFL1_Feature` | conflict | NY | VT | VT | 348 | 348 |
| 223 | `_rest_services_Grayton_Parcels_and_Addresses_Feature` | geo_conflict | AL | （无州列） | FL | 281 | 281 |
| 224 | `JSry_arcgis_rest_services_Route_3_Addressing_Feature` | geo_conflict | MN | （无州列） | WI | 187 | 187 |
| 225 | `Wzi_arcgis_rest_services_NCRPO_MCD_Addresses_Feature` | geo_conflict | NY | （无州列） | PA | 161 | 161 |
| 226 | `s_rest_services_MS4_sites_Addresses_OFFICIAL_Feature` | conflict | NJ | NY | NY | 158 | 158 |
| 227 | `services_Fairfield_Blythewood_Address_Points_Feature` | geo_conflict | GA | （无州列） | SC | 154 | 154 |
| 228 | `9_arcgis_rest_services_NG911_Web_layers_WFL1_Feature` | geo_conflict | IL | （无州列） | KY | 145 | 145 |
| 229 | `est_services_AddressPoints_E911Transfercalls_Feature` | conflict | NC | SC | SC | 107 | 107 |
| 230 | `_arcgis_rest_services_1940_Address_Points_JG_Feature` | conflict | IA | NE | NE | 100 | 100 |
| 231 | `rest_services_Copy_of_Site_Addresses_3_28_24_Feature` | geo_conflict | CA | （无州列） | NV | 94 | 94 |
| 232 | `on_Meeting_Using_GIS_to_Facilitate_the_NG911_Feature` | conflict | AR | MS | MS | 90 | 90 |
| 233 | `7ueLg_arcgis_rest_services_0_Sites_Addresses_Feature` | conflict | KS | CA | CA | 86 | 84 |
| 234 | `services_NCI_CancerCenter_Address_spring2025_Feature` | conflict | AZ | CA | CA | 77 | 75 |
| 235 | `hr_arcgis_rest_services_NCI_Center_Addresses_Feature` | conflict | AZ | CA | CA | 73 | 72 |
| 236 | `is_rest_services_NCI_Cancer_Center_Addresses_Feature` | conflict | AZ | CA | CA | 73 | 72 |
| 237 | `1oVm_arcgis_rest_services_WCD_Site_Addresses_Feature` | geo_conflict | NY | （无州列） | PA | 71 | 71 |
| 238 | `_arcgis_rest_services_1920_Address_Points_JG_Feature` | conflict | IA | NE | NE | 63 | 63 |
| 239 | `arcgis_rest_services_ltar_address_p_geocoded_Feature` | conflict | KS | OH | OH | 59 | 59 |
| 240 | `123_4848a2717d344d119d250f258af86bea_results_Feature` | geo_conflict | MO | （无州列） | OH | 33 | 33 |
| 241 | `arcgis_rest_services_HWY_160_Address_Markers_Feature` | geo_conflict | NC | （无州列） | TN | 31 | 31 |
| 242 | `st_services_NewSiteFinityParks2AGOL4EELsView_Feature` | list_missing | （空） | （无州列） | FL | 22 | 0 |
| 243 | `services_Memphis_Synagogues_Addresses_202603_Feature` | conflict | AR | TN | TN | 21 | 21 |
| 244 | `s_Lodgings___Hotels__Inns__BnBs__E911_Data__FeatureS` | conflict | NY | VT | VT | 15 | 15 |
| 245 | `_rest_services_CatoctinSpeedDating_Addresses_Feature` | geo_conflict | MD | （无州列） | VA | 11 | 11 |
| 246 | `_arcgis_rest_services_Vulnerable_e911_sites__Feature` | conflict | MA | RI | RI | 9 | 9 |
| 247 | `teAddresses_1fda33ac1a5a463cabffde7c226afa69_Feature` | geo_conflict | MO | （无州列） | VA | 4 | 4 |
| 248 | `WodG9Kll_arcgis_rest_services_Address_Points_Feature` | geo_conflict | NJ | （无州列） | NY | 2 | 2 |
| 249 | `esses_field_1dc5c3405972470c9380408c90f4a4f5_Feature` | geo_conflict | MO | （无州列） | GA | 2 | 2 |
| 250 | `is_rest_services_79_Greenwich_address_points_Feature` | conflict | NJ | NY | NY | 2 | 2 |
| 251 | `lxt6cnCY2_arcgis_rest_services_siteaddresses_Feature` | geo_conflict | IL | （无州列） | MO | 2 | 2 |
| 252 | `teAddresses_1dc5c3405972470c9380408c90f4a4f5_Feature` | list_missing | （空） | （无州列） | GA | 2 | 0 |
| 253 | `est_services_SiteAddressPin_view_13268052057_Feature` | geo_conflict | MT | （无州列） | WA | 1 | 1 |
| 254 | `est_services_SiteAddressPin_view_13268481226_Feature` | geo_conflict | MT | （无州列） | WA | 1 | 1 |
| 255 | `teAddresses_fc0cc9ec7e5a47b1a4b4ad7a1eb2f9e0_Feature` | geo_conflict | CT | （无州列） | MA | 1 | 1 |

类型说明：`conflict` = 属性州 ≠ 清单州（层标错州）；`list_missing` = 清单没有州（`未定位`/空）但数据能看出州；`geo_conflict` = 清单州与「绝大多数行所在的县」所属州不同。

> 口径提醒：这些层**没有被过滤掉任何一行**。清单州只用于命名与统计，判县只看坐标落在哪个县；所以「肯塔基层被标成 IN」在旧实现里会把 490 万行整层假判成 UNLOCATED，现在只是记账。

## 五、suspect_layer（UNLOCATED > 50%）与复核建议

| # | 层 | 州 | 行数 | 判出县 | UNLOCATED | 占比 | 无坐标 | 投影 | 判不出 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `es_WAEVCP_Public_Composite_Score_Parcel_View` | WA | 3,266,900 | 0 | 3,266,900 | 100.00% | 3,266,900 | 0 | 0 |
| 2 | `gis_rest_services_SAMS_NAD_2025_Address_List` | ? | 1,040,301 | 221 | 1,040,080 | 99.98% | 0 | 0 | 1,040,080 |
| 3 | `Parcels_Within_500m_From_ParksandGreenspaces` | TX | 1,008,227 | 0 | 1,008,227 | 100.00% | 1,008,227 | 0 | 0 |
| 4 | `s_2026_SOE_GENERAL_USE_MAP___POST_CNG_WFL1_F` | FL | 793,729 | 0 | 793,729 | 100.00% | 793,729 | 0 | 0 |
| 5 | `g_server_rest_services_Hosted_Buildings_2024` | MI | 774,560 | 0 | 774,560 | 100.00% | 774,560 | 0 | 0 |
| 6 | `bBQScMtY_arcgis_rest_services_Street_Numbers` | NV | 675,006 | 0 | 675,006 | 100.00% | 675,006 | 0 | 0 |
| 7 | `rvices_SECTO_NBI_MASTER_ADDRESS_LIST__ATTACH` | ? | 530,776 | 0 | 530,776 | 100.00% | 0 | 0 | 530,776 |
| 8 | `rcgis_rest_services_municipal_address_points` | NY | 526,790 | 0 | 526,790 | 100.00% | 0 | 0 | 526,790 |
| 9 | `o_ca_arcgis_rest_services_cot_geospatial27_F` | NY | 525,381 | 0 | 525,381 | 100.00% | 0 | 0 | 525,381 |
| 10 | `_arcgis_rest_services_TO_addresspoints_Merge` | NY | 516,566 | 0 | 516,566 | 100.00% | 0 | 0 | 516,566 |
| 11 | `services_Address_Points__2249626704383450755` | ? | 496,450 | 0 | 496,450 | 100.00% | 0 | 0 | 496,450 |
| 12 | `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT` | NY | 479,000 | 0 | 479,000 | 100.00% | 0 | 0 | 479,000 |
| 13 | `ova_Scotia_Civic_Address_File___Civic_Points` | ? | 463,470 | 0 | 463,470 | 100.00% | 0 | 0 | 463,470 |
| 14 | `rkmaps_ca_arcgis_rest_services_OpenData_Loca` | ? | 431,970 | 0 | 431,970 | 100.00% | 0 | 0 | 431,970 |
| 15 | `e_Exposure_Forecast_Values_by_Parcel_Address` | ? | 419,850 | 0 | 419,850 | 100.00% | 0 | 0 | 419,850 |
| 16 | `La03VQ_arcgis_rest_services_Parcel_Addresses` | ? | 408,995 | 0 | 408,995 | 100.00% | 0 | 0 | 408,995 |
| 17 | `tawa_ca_arcgis_rest_services_Address_Informa` | ? | 404,751 | 0 | 404,751 | 100.00% | 0 | 0 | 404,751 |
| 18 | `6zC_arcgis_rest_services_parcel_file_current` | MI | 377,940 | 0 | 377,940 | 100.00% | 377,940 | 0 | 0 |
| 19 | `WClLJZr3s_arcgis_rest_services_YorkAddresses` | NY | 365,389 | 0 | 365,389 | 100.00% | 0 | 0 | 365,389 |
| 20 | `zfsFsB5_arcgis_rest_services_Tax_Parcels2018` | GA | 354,952 | 0 | 354,952 | 100.00% | 354,952 | 0 | 0 |
| 21 | `ntymd_gov_arcgis_rest_services_GDX_buildings` | MD | 347,176 | 0 | 347,176 | 100.00% | 0 | 347,176 | 0 |
| 22 | `arcgis_rest_services_Poland_Addresses_2_view` | ? | 301,951 | 0 | 301,951 | 100.00% | 0 | 0 | 301,951 |
| 23 | `rest_services_Existing_Land_Use__10_category` | WA | 245,376 | 0 | 245,376 | 100.00% | 245,376 | 0 | 0 |
| 24 | `Buildable_Lands_Inventory__Update_June_2022_` | WA | 245,074 | 0 | 245,074 | 100.00% | 0 | 245,074 | 0 |
| 25 | `is_rest_services_Zoning_Initiation_Date_WFL1` | GA | 243,950 | 0 | 243,950 | 100.00% | 243,950 | 0 | 0 |
| 26 | `rcgis_rest_services_Property_Information_gdb` | MD | 238,314 | 0 | 238,314 | 100.00% | 238,314 | 0 | 0 |
| 27 | `ouCfPzTlPw_arcgis_rest_services_Demo_Parcels` | LA | 222,082 | 0 | 222,082 | 100.00% | 222,082 | 0 | 0 |
| 28 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address` | NY | 219,790 | 0 | 219,790 | 100.00% | 0 | 0 | 219,790 |
| 29 | `cgis_rest_services_AGOL_Parcels_PacificTime_` | WA | 211,139 | 0 | 211,139 | 100.00% | 211,139 | 0 | 0 |
| 30 | `services_CountyServices_Municipal_Addressing` | AL | 207,685 | 0 | 207,685 | 100.00% | 207,685 | 0 | 0 |
| 31 | `gis_rest_services_KC_Parcels__Open_Data_View` | MO | 202,980 | 0 | 202,980 | 100.00% | 202,980 | 0 | 0 |
| 32 | `9ZtPWOn_arcgis_rest_services_ValueComparison` | WA | 192,607 | 0 | 192,607 | 100.00% | 192,607 | 0 | 0 |
| 33 | `y3Y2xxSi397ufGR_arcgis_rest_services_Parcels` | PA | 188,799 | 0 | 188,799 | 100.00% | 188,799 | 0 | 0 |
| 34 | `est_services_SpokaneParcelsTEST_CovenantJoin` | WA | 140,812 | 0 | 140,812 | 100.00% | 2 | 140,810 | 0 |
| 35 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs` | OR | 55,639 | 0 | 55,639 | 100.00% | 55,639 | 0 | 0 |
| 36 | `fsFsB5_arcgis_rest_services_Tax_Parcels_2025` | GA | 49,999 | 0 | 49,999 | 100.00% | 49,999 | 0 | 0 |
| 37 | `fsFsB5_arcgis_rest_services_Tax_Parcels_2024` | GA | 48,418 | 0 | 48,418 | 100.00% | 48,418 | 0 | 0 |
| 38 | `zfsFsB5_arcgis_rest_services_Tax_Parcels2020` | GA | 46,001 | 0 | 46,001 | 100.00% | 46,001 | 0 | 0 |
| 39 | `fsFsB5_arcgis_rest_services_Tax_Parcels_2023` | GA | 45,517 | 0 | 45,517 | 100.00% | 45,517 | 0 | 0 |
| 40 | `m_AQDHTHDrZzfsFsB5_arcgis_rest_services_2022` | GA | 42,231 | 0 | 42,231 | 100.00% | 42,231 | 0 | 0 |
| 41 | `s_rest_services_Raleigh_Co_EOC_Address_Sites` | VA | 42,165 | 0 | 42,165 | 100.00% | 0 | 0 | 42,165 |
| 42 | `is_rest_services_Public_View_Site_Addresses_` | NY | 40,584 | 0 | 40,584 | 100.00% | 0 | 0 | 40,584 |
| 43 | `q_arcgis_rest_services_Site_Addresses_Public` | NY | 40,584 | 0 | 40,584 | 100.00% | 0 | 0 | 40,584 |
| 44 | `zfsFsB5_arcgis_rest_services_Tax_Parcels2021` | GA | 39,445 | 0 | 39,445 | 100.00% | 39,445 | 0 | 0 |
| 45 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address` | NY | 38,345 | 0 | 38,345 | 100.00% | 0 | 1 | 38,344 |
| 46 | `zfsFsB5_arcgis_rest_services_Tax_Parcels2017` | GA | 38,265 | 0 | 38,265 | 100.00% | 38,265 | 0 | 0 |
| 47 | `QYTTiP6CrfEsw_arcgis_rest_services_Addresses` | NY | 37,276 | 0 | 37,276 | 100.00% | 0 | 1 | 37,275 |
| 48 | `arcgis_rest_services_OpenNewmarket_Addresses` | NY | 34,922 | 0 | 34,922 | 100.00% | 0 | 0 | 34,922 |
| 49 | `s_rest_services_OPENNewmarket_Address_3_view` | NY | 34,922 | 0 | 34,922 | 100.00% | 0 | 0 | 34,922 |
| 50 | `yvfv_arcgis_rest_services_Mercer_SiteAddress` | VA | 33,215 | 36 | 33,179 | 99.89% | 0 | 0 | 33,179 |
| 51 | `VDElDOMEad_arcgis_rest_services_WayneAddress` | KY | 31,980 | 0 | 31,980 | 100.00% | 0 | 0 | 31,980 |
| 52 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses` | NY | 31,520 | 0 | 31,520 | 100.00% | 0 | 0 | 31,520 |
| 53 | `s_rest_services_Fayette_County_911_Addresses` | VA | 24,529 | 0 | 24,529 | 100.00% | 0 | 0 | 24,529 |
| 54 | `7ABWQBGTG_arcgis_rest_services_Hutto_Parcels` | TX | 23,591 | 0 | 23,591 | 100.00% | 23,591 | 0 | 0 |
| 55 | `Zm_arcgis_rest_services_Aurora_Address_view_` | NY | 20,861 | 0 | 20,861 | 100.00% | 0 | 0 | 20,861 |
| 56 | `_arcgis_rest_services_Wyoming_SAMB_Addresses` | VA | 19,767 | 0 | 19,767 | 100.00% | 0 | 0 | 19,767 |
| 57 | `cjlmqkA8ypi4T_arcgis_rest_services_Addresses` | OH | 17,308 | 0 | 17,308 | 100.00% | 0 | 0 | 17,308 |
| 58 | `0hS_arcgis_rest_services_Address_Road_Update` | MD | 7,370 | 7 | 7,363 | 99.91% | 0 | 0 | 7,363 |
| 59 | `ater_Meter_Replacement_Addresses_Zone_1_view` | NY | 6,361 | 0 | 6,361 | 100.00% | 0 | 0 | 6,361 |
| 60 | `yHixJV_arcgis_rest_services_Master_Addresses` | NY | 6,184 | 0 | 6,184 | 100.00% | 6,184 | 0 | 0 |
| 61 | `cgis_rest_services_SiteAddresses_public_2020` | VA | 5,655 | 0 | 5,655 | 100.00% | 0 | 0 | 5,655 |
| 62 | `Site_Structure_Address_Points__External_View` | WA | 4,316 | 0 | 4,316 | 100.00% | 0 | 0 | 4,316 |
| 63 | `rcgis_rest_services_Site_Addresses_NK_Public` | NY | 4,302 | 0 | 4,302 | 100.00% | 0 | 0 | 4,302 |
| 64 | `st_services_Town_of_Sidney_Address_Data_WFL1` | WA | 4,144 | 0 | 4,144 | 100.00% | 0 | 0 | 4,144 |
| 65 | `9JX5q_arcgis_rest_services_Site_Addresses_CM` | NY | 4,140 | 0 | 4,140 | 100.00% | 0 | 0 | 4,140 |
| 66 | `X5q_arcgis_rest_services_DD_Addresses_Public` | NY | 4,054 | 0 | 4,054 | 100.00% | 0 | 0 | 4,054 |
| 67 | `Xa_arcgis_rest_services_SiteAddresses_public` | MO | 3,904 | 0 | 3,904 | 100.00% | 0 | 0 | 3,904 |
| 68 | `for_Municipal_District_of_Saint_Stephen_WFL1` | ME | 3,829 | 0 | 3,829 | 100.00% | 0 | 0 | 3,829 |
| 69 | `N_arcgis_rest_services_Master_Address_Points` | MA | 3,772 | 0 | 3,772 | 100.00% | 3,772 | 0 | 0 |
| 70 | `cgis_rest_services_Address_Points_Index_WFL1` | NY | 3,736 | 0 | 3,736 | 100.00% | 0 | 0 | 3,736 |
| 71 | `cgis_rest_services_Site_Addresses_OSM_Public` | NY | 3,617 | 0 | 3,617 | 100.00% | 0 | 0 | 3,617 |
| 72 | `_rest_services_E911Roads_flowlines_intersect` | NM | 2,413 | 0 | 2,413 | 100.00% | 2,413 | 0 | 0 |
| 73 | `ze4GYYo_arcgis_rest_services_Addresses_No_BB` | MD | 1,780 | 1 | 1,779 | 99.94% | 0 | 0 | 1,779 |
| 74 | `mc98J4JC_arcgis_rest_services_MH_e911Addison` | NY | 1,270 | 0 | 1,270 | 100.00% | 1,270 | 0 | 0 |
| 75 | `_arcgis_rest_services_AddresspointsDuplicate` | NY | 1,154 | 0 | 1,154 | 100.00% | 1,154 | 0 | 0 |
| 76 | `rcgis_rest_services_Hanover_NG911_Exceptions` | VA | 1,007 | 0 | 1,007 | 100.00% | 1,007 | 0 | 0 |
| 77 | `cgis_rest_services_Rubbertown_Addresses_WFL1` | IN | 978 | 69 | 909 | 92.94% | 0 | 909 | 0 |
| 78 | `est_services_SOS_StreetPostalCodeFinder_E911` | NY | 730 | 0 | 730 | 100.00% | 730 | 0 | 0 |
| 79 | `cgis_rest_services_911_Addresses_in_Snowshoe` | VA | 322 | 0 | 322 | 100.00% | 0 | 0 | 322 |
| 80 | `rcgis_rest_services_Address_Points_in_Buffer` | NY | 251 | 0 | 251 | 100.00% | 0 | 251 | 0 |
| 81 | `cnmA9U_arcgis_rest_services_CollegeAddresses` | MI | 25 | 0 | 25 | 100.00% | 0 | 0 | 25 |
| 82 | `is_rest_services_OntarioColleges_GeocodeAddr` | MI | 25 | 0 | 25 | 100.00% | 0 | 0 | 25 |
| 83 | `rest_services_OntarioColleges_GeocodeAddress` | MI | 25 | 0 | 25 | 100.00% | 0 | 0 | 25 |
| 84 | `services_McDowell_Dilapidated_Addresses_WFL1` | VA | 25 | 0 | 25 | 100.00% | 0 | 0 | 25 |
| 85 | `t_services_DBO_OntarioCollege_GeocodeAddress` | MI | 25 | 0 | 25 | 100.00% | 0 | 0 | 25 |
| 86 | `etPostalCodeFinder_PostalCodeAggregated_E911` | NY | 12 | 0 | 12 | 100.00% | 12 | 0 | 0 |
| 87 | `ostalCodeFinder_MunicipalityAggregation_E911` | NY | 2 | 0 | 2 | 100.00% | 2 | 0 | 0 |
| 88 | `a0SJxRv_arcgis_rest_services_Minnesota_NG911` | MN | 1 | 0 | 1 | 100.00% | 1 | 0 | 0 |

**复核建议（按三档分流，不要一刀切）**：
1. `no_coords` 为主 → 采集侧几何没落盘。这批就是 `geom_missing`／面层未带质心的层：走 `--geom-backfill` 全量几何补采（**1,238 层宗地层全部**，方案与成本见 `docs/PARCEL-GEOMETRY-OPTIONS-2026-10-30.md` 第五节），补完重判。
2. `proj_failed` 为主 → 属性里是投影坐标。走 `collect/parcel_centroid.py --audit` 的 EPSG 反推（已救回 5 层 / 479,123 行），**不唯一就记 `proj_ambiguous`，不猜**。
3. `outside_any_county` 为主 → 坐标有值但不在美国境内：先查 `outSR` 是否生效、再查该层是不是「演示/测试层」或边界数据。这类层建议**整层标记不可用**，不进地址库。

## 六、分州覆盖

| 州 | 层 | 行数 | 判出县 | UNLOCATED | 覆盖率 |
|---|---|---|---|---|---|
| ID | 19 | 77,437,201 | 77,431,671 | 5,530 | 99.99% |
| ? | 77 | 49,559,983 | 45,050,101 | 4,509,882 | 90.90% |
| CA | 93 | 12,743,505 | 12,743,489 | 16 | 100.00% |
| VA | 53 | 11,212,701 | 11,085,484 | 127,217 | 98.86% |
| IN | 17 | 9,662,574 | 9,660,591 | 1,983 | 99.98% |
| FL | 67 | 9,257,205 | 8,453,034 | 804,171 | 91.31% |
| AZ | 26 | 8,334,060 | 8,333,975 | 85 | 100.00% |
| WA | 30 | 6,010,545 | 1,700,173 | 4,310,372 | 28.29% |
| NM | 34 | 4,903,462 | 4,900,928 | 2,534 | 99.95% |
| OR | 33 | 4,886,617 | 4,830,783 | 55,834 | 98.86% |
| TX | 48 | 4,353,149 | 3,320,998 | 1,032,151 | 76.29% |
| NJ | 13 | 3,914,649 | 3,914,545 | 104 | 100.00% |
| NY | 73 | 3,895,428 | 947,608 | 2,947,820 | 24.33% |
| UT | 17 | 3,412,007 | 3,411,984 | 23 | 100.00% |
| IL | 36 | 3,184,767 | 3,184,737 | 30 | 100.00% |
| ME | 15 | 3,135,306 | 3,131,365 | 3,941 | 99.87% |
| GA | 44 | 3,133,541 | 2,222,344 | 911,197 | 70.92% |
| OH | 22 | 2,944,572 | 2,926,919 | 17,653 | 99.40% |
| KS | 25 | 2,802,846 | 2,802,778 | 68 | 100.00% |
| AR | 22 | 2,792,247 | 2,792,149 | 98 | 100.00% |
| MN | 30 | 2,433,546 | 2,431,355 | 2,191 | 99.91% |
| CO | 42 | 1,985,516 | 1,985,471 | 45 | 100.00% |
| AL | 28 | 1,680,025 | 1,472,130 | 207,895 | 87.62% |
| MI | 22 | 1,489,874 | 337,068 | 1,152,806 | 22.62% |
| NH | 10 | 1,411,522 | 1,411,407 | 115 | 99.99% |
| MD | 28 | 1,248,584 | 653,936 | 594,648 | 52.37% |
| TN | 10 | 1,186,420 | 1,186,396 | 24 | 100.00% |
| NC | 33 | 1,184,860 | 1,184,806 | 54 | 100.00% |
| MA | 22 | 1,113,035 | 1,109,261 | 3,774 | 99.66% |
| PA | 8 | 1,084,893 | 896,084 | 188,809 | 82.60% |

（只列行数前 30 州；全州数据见 `analysis/county-assign-summary.json`）

## 七、耗时与吞吐

| 指标 | 值 |
|---|---|
| 逐层耗时合计 | 53,536 秒（≈14.9 小时·进程） |
| 单进程吞吐 | 4,646 行/秒（实测，均值） |
| 并发 | 按层多进程（本机 8 进程；不占 GitHub runner） |

### 断点续跑实测

| 项 | 值 |
|---|---|
| 第一次启动 | 跑 14.0 秒后强杀（SIGKILL，模拟会话超时 code=143） |
| 已落盘层 | 2 层（`rows-<layer>.json`） |
| 重启后 | 跳过 2 层，只跑剩余的 4 层 |
| 结论 | 重启后跳过已完成 2 层（= kill 前的 2 层），只跑剩余 4 层；行数相加 243726 == 6 层真实总行数 243726；已完成层 rows-*.json 重写数 0 |

## 八、抽样 20 层明细（按行数降序）

| # | 层 | 州 | 行数 | 判出县 | UNLOCATED | 无坐标 | 投影 | 判不出 | 县数 | 州不符 | 行/秒 | 可疑 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `UCXd1_arcgis_rest_services_USA_NAD_Addre` | ID | 75,937,418 | 75,932,023 | 5,395 | 0 | 0 | 5,395 | 2015 | 75,932,001 | 12,550 |  |
| 2 | `aIfH92NqI_arcgis_rest_services_AddressNC` | ? | 5,703,287 | 5,703,031 | 256 | 0 | 0 | 256 | 126 | 0 | 5,330 |  |
| 3 | `s_rest_services_VA_Base_Layers_VA_Addres` | VA | 3,881,020 | 3,880,771 | 249 | 0 | 0 | 249 | 139 | 73 | 3,974 |  |
| 4 | `st_services_VA_Base_Layers_VA_Address_Po` | VA | 3,881,020 | 3,880,771 | 249 | 0 | 0 | 249 | 139 | 73 | 3,761 |  |
| 5 | `gis_rest_services_AZ911_AddressPoints_Ho` | AZ | 3,735,462 | 3,735,418 | 44 | 0 | 0 | 44 | 17 | 1,063 | 3,930 |  |
| 6 | `king_Water_Systems_by_Address_in_New_Jer` | NJ | 3,697,833 | 3,697,730 | 103 | 0 | 0 | 103 | 24 | 50 | 5,537 |  |
| 7 | `2bbc_rest_services_AGOL_MAD_AGOL_R2R_ADD` | ? | 3,623,798 | 3,623,719 | 79 | 0 | 0 | 79 | 23 | 0 | 4,774 |  |
| 8 | `ces_Hosted_Address_Points_of_Indiana_Cur` | IN | 3,326,690 | 3,326,296 | 394 | 0 | 0 | 394 | 96 | 15 | 3,382 |  |
| 9 | `rvices_Hosted_Address_Points_of_Indiana_` | IN | 3,313,192 | 3,312,800 | 392 | 0 | 0 | 392 | 103 | 71 | 4,561 |  |
| 10 | `es_WAEVCP_Public_Composite_Score_Parcel_` | WA | 3,266,900 | 0 | 3,266,900 | 3,266,900 | 0 | 0 | 0 | 0 | 3,124 | ⚠️ |
| 11 | `ces_Ky_911_Site_Structure_Address_Points` | ? | 2,489,939 | 2,489,769 | 170 | 0 | 0 | 170 | 126 | 0 | 4,612 |  |
| 12 | `ces_Ky_911_Site_Structure_Address_Points` | IN | 2,416,763 | 2,416,593 | 170 | 0 | 0 | 170 | 126 | 2,416,592 | 4,773 |  |
| 13 | `g5s_arcgis_rest_services_Tidewater_addre` | VA | 2,181,621 | 2,181,585 | 36 | 0 | 0 | 36 | 60 | 25 | 5,521 |  |
| 14 | `rest_services_Maricopa_County_Address_Po` | ? | 2,139,242 | 2,139,242 | 0 | 0 | 0 | 0 | 2 | 0 | 5,700 |  |
| 15 | `JJqLK0A_arcgis_rest_services_NG911_Addre` | AZ | 2,078,539 | 2,078,539 | 0 | 0 | 0 | 0 | 2 | 0 | 5,456 |  |
| 16 | `U_arcgis_rest_services_Oregon_Address_Po` | OR | 1,942,377 | 1,942,315 | 62 | 0 | 0 | 62 | 39 | 14 | 4,113 |  |
| 17 | `es_us_mn_state_mngeo_loc_addresses_zip9_` | MN | 1,929,626 | 1,929,474 | 152 | 0 | 0 | 152 | 71 | 1 | 4,890 |  |
| 18 | `vzKRJ_arcgis_rest_services_AddressPoint_` | ? | 1,567,568 | 1,567,568 | 0 | 0 | 0 | 0 | 3 | 0 | 6,071 |  |
| 19 | `KUeVR_arcgis_rest_services_COH_SiteAddre` | ? | 1,550,454 | 1,550,434 | 20 | 0 | 0 | 20 | 8 | 0 | 2,600 |  |
| 20 | `gov_gisweb01_rest_services_EGIS_HOUSTON_` | TX | 1,549,689 | 1,549,669 | 20 | 0 | 0 | 20 | 8 | 0 | 2,092 |  |

## 九、复现

```bash
# 1) 一次拉全量 release 快照（约 15 次 gh api，避免逐层 4,600 次撞配额）
python3 - <<'PY'  # 见 /tmp/mk_snapshot.sh → analysis/county/release-snapshot.json
PY

# 2) 建全量计划（只排有资产的层，行数升序）
python3 collect/county_assign.py --make-plan --size 60 --plan collect/ledger/county_plan_all.json

# 3) 全量跑（后台 + 断点续跑；每层落 rows-<layer>.json，单元落 .done）
nohup setsid python3 collect/county_assign.py --plan collect/ledger/county_plan_all.json \
      --concurrency 8 --out analysis/tiger_county > collect/logs/county-all.log 2>&1 &

# 4) 汇总 + 渲染本文档
python3 collect/county_assign.py --summary --plan collect/ledger/county_plan_all.json \
      --doc docs/COUNTY-ASSIGN-2026-10-30.md
```

