# 语义裁定审计 · addr_type 与 CITY（2026-10-30）

> 只抽真行核对，不做启发式。两条裁定的依据与命中率都在这里，字段映射与 intake 一律按本文件的结论执行。

## 一、addr_type：v1 一律 `Unknown`，除非明确分类列可映射

**禁止的启发式**（本轮明确否掉，永不实现）：

- unit 非空 → Residential (Multi-Unit)
- 层标题含 COMMERCIAL → Commercial
- parcel_situs 层 → Commercial
- addr_type 继承同州/同服务其它层

**抽样**：40 层 × 25 行，覆盖明确分类列（AddrClass/ADDR_TYPE/UseCode/LANDUSE/BLDG_TYPE…）。

| 层 | 分类列 | 抽样 | 可映射 | 覆盖率 | 裁定 |
|---|---|---|---|---|---|
| `st_services_VA_Base_Layers_VA_Address_Points_FeatureServer_0` | ADDRCLASS | 0 | 0 | 0% | Unknown |
| `s_rest_services_VA_Base_Layers_VA_Address_Points_MapServer_0` | ADDRCLASS | 0 | 0 | 0% | Unknown |
| `es_us_mn_state_mngeo_loc_addresses_zip9_open_FeatureServer_0` | addrclass | 25 | 0 | 0% | Unknown |
| `KUeVR_arcgis_rest_services_COH_SiteAddresses_FeatureServer_0` | addrtype | 4 | 4 | 100% | map |
| `g_arcgis_rest_services_ADDRESS_POINTS_062526_FeatureServer_1` | ADDRESS_TYPE | 1 | 0 | 0% | Unknown |
| `g_arcgis_rest_services_ADDRESS_POINTS_022426_FeatureServer_1` | ADDRESS_TYPE | 1 | 0 | 0% | Unknown |
| `g_arcgis_rest_services_ADDRESS_POINTS_030926_FeatureServer_1` | ADDRESS_TYPE | 1 | 0 | 0% | Unknown |
| `g_arcgis_rest_services_ADDRESS_POINTS_021026_FeatureServer_1` | ADDRESS_TYPE | 1 | 0 | 0% | Unknown |
| `bBQScMtY_arcgis_rest_services_CC_PARCELS_SHP_FeatureServer_1` | LANDUSE | 25 | 0 | 0% | Unknown |
| `PLlPw_arcgis_rest_services_Situs_20Addresses_FeatureServer_0` | ADDR_TYPE | 25 | 0 | 0% | Unknown |
| `arcgis_rest_services_ParcelsJoin_SpatialJoin_FeatureServer_0` | ADDR_TYPE | 25 | 0 | 0% | Unknown |
| `rest_services_Pinellas_SiteAddressPoint_view_FeatureServer_0` | ADDRCLASS | 0 | 0 | 0% | Unknown |
| `ccH_arcgis_rest_services_SiteAddress20231227_FeatureServer_0` | ADDRCLASS | 0 | 0 | 0% | Unknown |
| `s_2026_SOE_GENERAL_USE_MAP___POST_CNG_WFL1_FeatureServer_118` | USE_CODE | 0 | 0 | 0% | Unknown |
| `rjguNyOy_arcgis_rest_services_Address_Points_FeatureServer_2` | ADDRTYPE | 25 | 0 | 0% | Unknown |
| `Oy_arcgis_rest_services_Address_Lookup1_WFL1_FeatureServer_0` | ADDRTYPE | 25 | 0 | 0% | Unknown |
| `o_ca_arcgis_rest_services_cot_geospatial27_FeatureServer_101` | ADDRESS_CLASS | 25 | 0 | 0% | Unknown |
| `services_Address_Points__2249626704383450755_FeatureServer_0` | LANDUSE | 25 | 25 | 100% | map |
| `fD_arcgis_rest_services_COTGEO_ADDRESS_POINT_FeatureServer_0` | ADDRESS_CLASS | 25 | 0 | 0% | Unknown |
| `vuFjG9HQX_arcgis_rest_services_Parcel_Labels_FeatureServer_0` | USE_DESC | 25 | 0 | 0% | Unknown |
| `vuFjG9HQX_arcgis_rest_services_Parcel_Test_3_FeatureServer_0` | USE_DESC | 25 | 0 | 0% | Unknown |
| `tawa_ca_arcgis_rest_services_Address_Information_MapServer_0` | ADDRTYPE | 25 | 0 | 0% | Unknown |
| `es_WAEVCP_Public_Composite_Score_Parcel_View_FeatureServer_1` | usecode | 25 | 0 | 0% | Unknown |
| `rps6zC_arcgis_rest_services_Parcel_File_2023_FeatureServer_1` | use_code | 0 | 0 | 0% | Unknown |
| `6zC_arcgis_rest_services_parcel_file_current_FeatureServer_0` | use_code | 25 | 0 | 0% | Unknown |
| `is_rest_services_ParcelViewer_AddressPoints2_FeatureServer_0` | AddrType | 0 | 0 | 0% | Unknown |
| `ntymd_gov_arcgis_rest_services_GDX_buildings_FeatureServer_0` | BLDG_TYPE | 0 | 0 | 0% | Unknown |
| `P_arcgis_rest_services_Transit_Addresses_New_FeatureServer_0` | ADDR_TYPE | 25 | 25 | 100% | map |
| `rGr3P_arcgis_rest_services_Transit_Addresses_FeatureServer_0` | ADDR_TYPE | 25 | 25 | 100% | map |
| `rest_services_Address_Points_and_CPNs_Update_FeatureServer_3` | BLDG_TYPE | 0 | 0 | 0% | Unknown |
| `_rest_services_Arapahoe_County_Addresses_gdb_FeatureServer_0` | Bldg_Type | 24 | 0 | 0% | Unknown |
| `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | BUILDING_TYPE | 0 | 0 | 0% | Unknown |
| `HQX_arcgis_rest_services_Parcels_for_Aerials_FeatureServer_0` | USE_DESC | 25 | 0 | 0% | Unknown |
| `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | Addr_Type | 0 | 0 | 0% | Unknown |
| `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` | Bldg_Type | 25 | 0 | 0% | Unknown |
| `is_rest_services_CMB_QSCF_Registered_Parcels_FeatureServer_0` | LANDUSE | 25 | 0 | 0% | Unknown |
| `0ba_rest_services_Auditor_StarkCountyParcels_FeatureServer_0` | LAND_USE_CODE | 25 | 0 | 0% | Unknown |
| `_arcgis_rest_services_Full_Text_Index_Search_FeatureServer_0` | use_code | 25 | 0 | 0% | Unknown |
| `sessing_PROPERTY_ASSESSMENT_PARCEL_JOIN_FY26_FeatureServer_0` | BLDG_TYPE | 25 | 0 | 0% | Unknown |
| `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | AddrType | 0 | 0 | 0% | Unknown |

**逐值映射表**（只有表内字面值会映射，其余一律 Unknown）：

| 字面值 | → addr_type |
|---|---|
| `COMMERCIAL` | Commercial |

→ 未抽样 / 覆盖率 < 80% / 列不在白名单的层：**addr_type = `Unknown`**（缺省不猜）。

## 二、CITY：postal_city 与 municipal_city 的判定规则 + 命中率

**抽样**：28 层 / 560 行（generic CITY 15 层、postal 列 5 层、municipal 列 5 层、owner 列 2 层、community 列 3 层）。

**值的形态命中率**（合计 560 个样本值）：

| 形态 | 计数 | 占比 | 结论 |
|---|---|---|---|
| clean | 448 | 80.0% | ✅ 可作 postal_city |
| empty | 65 | 11.6% | — 空值 |
| blacklist | 47 | 8.4% | ❌ 行政区黑话 → null |

**列族的同名率**（同层两列逐行比对，≥50% 视为同族）：

| 层 | 主列 | 对比列 | 比对行 | 同名率 |
|---|---|---|---|---|
| `es_us_mn_state_mngeo_loc_addresses_zip9_open_FeatureServer_0` | post_city | inc_muni | 20 | 0% |
| `gis_rest_services_SAMS_NAD_2025_Address_List_FeatureServer_2` | Post_City | MUNICIPALITY | 20 | 100% |
| `6zC_arcgis_rest_services_parcel_file_current_FeatureServer_0` | taxpayer_city | neighborhood | 20 | 0% |

**判定规则（落进 `schema/city-rules-v1.json`）**：

- postal_city 收列白名单：`POST_CITY, POSTAL_CITY, POSTALCITY, MAIL_CITY, MAILING_CITY, CITY_POSTAL, CITY_MAILING, POST_OFFICE_CITY, PO_CITY, POSTAL_TOWN, CITY, CITY_NAME`
- postal_city 拒列：`OWNER_CITY, OWNER_CITY_STATE, MAIL_CITY_OWNER, TAXPAYER_CITY, INC_MUNI, INCMUNI, MUNICIPALITY, MUNICIPAL_NAME, MUNI_NAME, MUNICIPAL, CITY_OF, TOWNSHIP, TOWNSHIP_NAME, COMMUNITY, TOWN, VILLAGE, HAMLET, NEIGHBORHOOD`（业主邮寄城市 / 法定市政 / 社区名都不是邮件城市）
- 值校验：不含数字（ZIP/门牌一律拒）；不含逗号/分号（整串地址拒）；不在行政区黑话表（UNINCORPORATED/NONE/CDP 等）；长度 ≤ 40；字母开头且仅 A-Z . ' - 空格
- 不过校验 / 层内 clean_rate < 0.8 → **postal_city = null，postal_city_source = null**
- municipal_city 只收 `INC_MUNI, INCMUNI, MUNICIPALITY, MUNICIPAL_NAME, MUNI_NAME, MUNICIPAL, CITY_OF, TOWNSHIP, TOWNSHIP_NAME`；`UNINCORPORATED` 一律 null

**分歧实例（为什么不能混用）**：

- `es_us_mn_state_mngeo_loc_addresses_zip9_open_FeatureServer_0`：post_city=`Not stated` vs inc_muni=`Saint Francis`
- `6zC_arcgis_rest_services_parcel_file_current_FeatureServer_0`：taxpayer_city=`DETROIT` vs neighborhood=`NW Goldberg`
- `6zC_arcgis_rest_services_parcel_file_current_FeatureServer_0`：taxpayer_city=`DETROIT` vs neighborhood=`LaSalle Gardens`

## 三、复现

```bash
python3 analysis/semantic_audit.py both --rows 600 --layers 30

# 本轮实测 560 行 / 28 层（少数层已死链，故略少于请求的全数）
```
