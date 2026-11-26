# SCOPE · house_number 写成 `x.0` 的脏行清单（muse-000275 §1）

> 生成：`scan_dirty.py`（扫真实产物）→ `scope.py`（回放门牌取值路径定位来源字段）。清单文件 `scope.jsonl`，sha256 见下；**只有清单内的层会被重跑**。

## 怎么来的（不是猜的）

1. `scan_dirty.py` 直接扫**已落盘的真实映射产物**：`dist-v2/tar/fieldmap-part*.tar.gz`（PR #58 合并后的 3,355 层）+ `/data/scratch/fix58-20261126/rows/`（fix58 的 58 层）= **3,413 层 / 483,239,197 行**，用字节正则 `"house_number":"<n>"` 且 `n` 匹配 `^\d+\.0+$` 判定。
2. `scope.py` 对命中层回放 `fm_core` 的门牌取值路径（信封 `add_num` → 强别名 → 组合串拆分 → 弱别名 → 层级别名），定位把 float 带进来的是哪个字段。
3. 清单 = 脏行数 > 0 的层；清单外一律不重跑、不产出新数据。

## 结论

- **20 层**有脏行，脏行合计 **1,169,262**；这些层的总行数 51,288,896（占已映射 4.83 亿行的 10.61%）。
- `scope.jsonl` sha256 = `9f495a9697af696d87d0b537380f1bc9b9b1c43ba2af367619442de7029aa26e`，**前 16 位 = `9f495a9697af696d`**。
- 来源字段分桶：`{"Address_Number(str)": 1, "HouseNumber": 1, "HOUSE_NO": 1, "addr_housenumber(str)": 3, "add_num(env)": 7, "ADDR_NUM(float)": 1, "STREET_NO": 1, "HOUSE": 1, "NUMBER(float)": 1, "NUMBER_": 1, "AddNum": 1, "Number": 1}`

> 注意：脏行的来源**不止** `STR_NUM`/`CIVIC_NUM` 两个新别名，还包括 7 层的**信封 `add_num` 本身就是 JSON 浮点**（采集侧写入）与若干「字符串里自带 `.0`」（如 `addr_housenumber = "1.0"`）。所以修在 `clean_number()` 这一层才对，修别名修不全。

## 清单（按脏行降序）

| # | 层 | 来源字段 | rows_total | rows_dirty | 脏行占比 | 现样例（≤3） |
|---|---|---|---|---|---|---|
| 1 | `erycountymd_gov_arcgis_rest_services_General_BAR_MapServer_0` | `add_num(env)` | 294,680 | 294,680 | 100.00% | 3910.0 / 11606.0 / 11602.0 |
| 2 | `ountymd_gov_arcgis_rest_services_General_BAR_FeatureServer_0` | `add_num(env)` | 294,680 | 294,680 | 100.00% | 3910.0 / 11606.0 / 11602.0 |
| 3 | `land_ca_server_rest_services_civic_addresses_FeatureServer_0` | `STREET_NO` | 82,901 | 82,901 | 100.00% | 427.0 / 9617.0 / 170.0 |
| 4 | `v_com_server_rest_services_ACC_Address_Point_FeatureServer_0` | `add_num(env)` | 78,064 | 77,411 | 99.16% | 497.0 / 103.0 / 475.0 |
| 5 | `_gov_host_rest_services_PublicAccess_LandData_MapServer_1054` | `add_num(env)` | 73,569 | 73,569 | 100.00% | 70.0 / 7415.0 / 7345.0 |
| 6 | `rcgis_rest_services_OpenData_General_Reference_MapServer_100` | `add_num(env)` | 68,811 | 67,843 | 98.59% | 2540.0 / 7615.0 / 7611.0 |
| 7 | `services_Address_Planning_AddressPoints_Planning_MapServer_0` | `add_num(env)` | 56,732 | 56,732 | 100.00% | 4390.0 / 109.0 / 6741.0 |
| 8 | `countymd_gov_server_rest_services_Public_Primary_MapServer_2` | `add_num(env)` | 59,083 | 51,767 | 87.62% | 19775.0 / 44939.0 / 39699.0 |
| 9 | `58c926eb68_rest_services_Public_SiteAddr_ZipCode_MapServer_0` | `HOUSE_NO` | 49,859 | 49,858 | 100.00% | 24570.0 / 24413.0 / 24406.0 |
| 10 | `s_org_server_rest_services_JCAdmin_SITUS_Static__MapServer_0` | `Number` | 43,851 | 43,824 | 99.94% | 2001.0 / 2009.0 / 2110.0 |
| 11 | `s_gscplanning_com_arcgis_rest_services_Addresses_MapServer_0` | `AddNum` | 30,766 | 30,554 | 99.31% | 244.0 / 242.0 / 240.0 |
| 12 | `rvices_Assessor_Data_Bossier_City_Address_Points_MapServer_0` | `NUMBER_` | 23,722 | 23,722 | 100.00% | 1056.0 / 715.0 / 112.0 |
| 13 | `leycity_ca_server_rest_services_Maps_Open_Data_MapServer_182` | `HOUSE` | 12,320 | 12,316 | 99.97% | 4502.0 / 4502.0 / 4510.0 |
| 14 | `58_rest_services_Clive_Clive_Land_Record_Service_MapServer_0` | `HouseNumber` | 9,257 | 9,198 | 99.36% | 14130.0 / 14132.0 / 14134.0 |
| 15 | `TUCXd1_arcgis_rest_services_OSM_Addresses_NA_FeatureServer_0` | `addr_housenumber(str)` | 15,765,731 | 108 | 0.00% | 730.0 / 5660.0 / 9532.0 |
| 16 | `rdco_org_arcgis_rest_services_Address_Points_FeatureServer_0` | `NUMBER(float)` | 39,594 | 38 | 0.10% | 27.0 / 34.0 / 33.0 |
| 17 | `ervices_AGO_HarrisonCounty_PhysicalAddresses_FeatureServer_0` | `ADDR_NUM(float)` | 105,396 | 33 | 0.03% | 310.0 / 2021.0 / 130.0 |
| 18 | `1Hv4I6Qk_arcgis_rest_services_Address_Points_FeatureServer_4` | `Address_Number(str)` | 11,466 | 24 | 0.21% | 63.0 / 64.0 / 65.0 |
| 19 | `N_arcgis_rest_services_OSM_Address_Points_AS_FeatureServer_0` | `addr_housenumber(str)` | 1,458,221 | 2 | 0.00% | 1.0 / 3.0 |
| 20 | `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0` | `addr_housenumber(str)` | 32,730,193 | 2 | 0.00% | 28.0 / 18.0 |

## 交叉核对

- 20 层全部在 `layer-coverage.v2.csv`（或 fix58 的 58 层清单里）且 `mapped>0`；没有未映射层混进清单。
- 脏行数最大的是 `ounty/county…General_BAR` 这一对镜像层（各 294,680 行，全层 100% 脏），机制是信封 `add_num` 为 JSON 浮点（`3910.0`）。
- 与 fix58 的交接：`land_ca_…civic_addresses`（82,901 行，全层 100% 脏）来自本轮 fix58 新上的层，来源字段 `STREET_NO`（JSON 浮点）；其余 19 层属 PR #58 的 3,355 层。

