# HEALTH · 第 9 步字段映射体检（10 层，含最大的）

口径：`dialect` = registry 按 agol org 命中 / fallback=minimal_safe；`闭合` = 输入行 − 映射行 − dropped_below_C − parse_error（必须 0）；字段命中率的分母是**映射行**。

| # | layer | 输入 B | in_rows | mapped | dropped<C | 闭合差 | street% | number% | zip5 合法% | 坐标% | grade S/A/B | dialect |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| 1 | `s_Points_from_National_Address_Database_view_F` | 4384.0 | 39,875,268 | 39,874,279 | 989 | 0 | 100.0 | 100.0 | 97.7 | 100.0 | 38948700/0/925579 | minimal_safe/fallback |
| 2 | `arcgis_rest_services_national_address_points_F` | 1435.0 | 15,949,543 | 15,949,543 | 0 | 0 | 100.0 | 0.0 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 3 | `_secure_rest_services_AddressNC_NC1Map_Address` | 1368.6 | 8,873,500 | 8,873,500 | 0 | 0 | 100.0 | 100.0 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 4 | `OJ5P6ngMu_arcgis_rest_services_AddressPoints_F` | 646.7 | 3,758,585 | 3,758,557 | 28 | 0 | 100.0 | 99.9 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 5 | `_rest_services_Statewide_LBRS_Address_Points_F` | 553.5 | 5,573,001 | 5,565,875 | 7,126 | 0 | 100.0 | 99.0 | 99.9 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 6 | `FO4fjN9P_arcgis_rest_services_Address_Points_F` | 525.7 | 11,349,117 | 11,339,058 | 10,059 | 0 | 100.0 | 72.8 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 7 | `UyC7jAmu_arcgis_rest_services_LBRSforLocator_F` | 435.4 | 5,573,001 | 5,565,875 | 7,126 | 0 | 100.0 | 99.0 | 99.9 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 8 | `st_services_eGIS_Addressing_ADDRESS_POINTSv2_F` | 372.4 | 2,693,332 | 928,332 | 1,765,000 | 0 | 100.0 | 0.0 | 100.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 9 | `rest_services_AGOL_MassGIS_Master_Address_Poin` | 360.4 | 3,716,441 | 3,716,441 | 0 | 0 | 100.0 | 99.9 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |
| 10 | `_services_AGOL_MassGIS_Master_Address_Points_F` | 360.3 | 3,716,441 | 3,716,441 | 0 | 0 | 100.0 | 99.9 | 0.0 | 100.0 | 0/0/0 | minimal_safe/fallback |

## 结论

- 10 层闭合差全部为 0、11 列全部齐全：是
- dialect 命中：registry 0/10，其余 minimal_safe（本批 3,550 层不在 17,168 分档分母内，url/layer_id 命中 0、org 命中 115）
- 解析失败原因：见 `layer-coverage.csv` 的 `parse_error` 列（本轮 gzip/JSON 损坏几乎为 0）
- dropped_below_C 集中在「非地址层」（POI/服务层，如 Nearest Kindergarten、玻璃回收点）：这类层的 raw 里没有门牌+街名，按口径**不许猜**，如实丢弃并计入 unusable。
