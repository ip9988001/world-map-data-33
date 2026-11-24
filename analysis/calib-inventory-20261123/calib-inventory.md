# 校准集逐层盘点（329 条）

| 州 | 源 | 层数 |
|---|---|---|
| — | NG911(dirty) | 15 |
| AR | NG911 | 1 |
| AZ | NG911 | 1 |
| CA | NG911 | 1 |
| CO | NG911 | 1 |
| DE | NAD | 4 |
| DE | NG911 | 1 |
| DE | OA | 5 |
| DE | OVERTURE | 1 |
| DE | TIGER | 3 |
| FL | NG911 | 1 |
| GA | NG911 | 1 |
| IA | NAD | 100 |
| IA | NG911 | 1 |
| IA | OA | 58 |
| IA | OVERTURE | 1 |
| IA | TIGER | 99 |
| IL | NG911 | 1 |
| KS | NG911 | 1 |
| LA | NG911 | 1 |
| MA | NG911 | 1 |
| MD | NG911 | 1 |
| MN | NG911 | 1 |
| NH | GRANIT | 11 |
| NH | NAD | 1 |
| NH | NG911 | 1 |
| NH | TIGER-addrfeat | 11 |
| OH | NG911 | 1 |
| PA | NG911 | 1 |
| TN | NG911 | 1 |
| VA | NG911 | 1 |
| WA | NG911 | 1 |

合计 **329** 条（local 299 / remote 15 / ledger 15）

## 分组输出（NG911 20 层）

| 组 | 层数 |
|---|---|
| full_address | 2 |
| no_zip | 8 |
| no_city | 6 |
| no_number | 0 |
| road_only | 2 |
| empty_shell | 2 |

## 分层输出（S/A/B/C）

| 级别 | 层数 |
|---|---|
| A | 11 |
| B | 2 |
| C | 5 |
| S | 2 |

分组分母（url 唯一键）= **20** 层；组/层按 url 归并，层名仅供人读

## 20 层 NG911 逐层（url 为键）

| # | 州 | 层名 | class | group | url |
|---|---|---|---|---|---|
| 1 | AR | Address Points | A | no_city | `https://services1.arcgis.com/zsny8x7Yh9eajjke/arcgis/rest/services/Address_Points/FeatureServer/0` |
| 2 | GA | Address Points | A | no_city | `https://services2.arcgis.com/IxVN2oUE9EYLSnPE/arcgis/rest/services/SiteAddressPointsOD/FeatureServer/0` |
| 3 | MN | EAS_Addresses | A | no_city | `https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/EAS_Addresses/FeatureServer/0` |
| 4 | CA | OC Addresses 20260811 | A | no_city | `https://services7.arcgis.com/vhU7TaevMOAtV9Qd/arcgis/rest/services/OC_Addresses_20260811/FeatureServer/0` |
| 5 | DE | SUSS Address Points | A | no_city | `https://services1.arcgis.com/jjVcwHv9AQEq3DH3/arcgis/rest/services/SUSS_Address_Points/FeatureServer/132` |
| 6 | LA | CNO_Addresses | A | no_zip | `https://services2.arcgis.com/LJwIycC0yIuqCBxq/arcgis/rest/services/CNO_Addresses/FeatureServer/0` |
| 7 | MA | City of Boston, MA Addresses | A | no_zip | `https://services6.arcgis.com/Do88DoK2xjTUCXd1/arcgis/rest/services/Boston_MA_Addresses/FeatureServer/0` |
| 8 | KS | Sacramento County, CA Addresses | A | no_zip | `https://services6.arcgis.com/Do88DoK2xjTUCXd1/arcgis/rest/services/Sacramento_County_CA_Addresses/FeatureServer/0` |
| 9 | WA | Site Address Points Spokane County Map View | A | no_zip | `https://services3.arcgis.com/9UdSzuxhN4jGcI9p/arcgis/rest/services/Site_Address_Points_Spokane_County_Map_View/FeatureServer/0` |
| 10 | FL | VC Addresses | A | no_zip | `https://services2.arcgis.com/2rIG17xLqeJd2jOX/arcgis/rest/services/VC_Addresses/FeatureServer/0` |
| 11 | VA | Virginia Address Points | A | no_zip | `https://vginmaps.vdem.virginia.gov/arcgis/rest/services/VA_Base_Layers/VA_Address_Points/FeatureServer/0` |
| 12 | PA | Address Points | B | road_only | `https://services2.arcgis.com/Q4NxsjNmWBIR4LYH/arcgis/rest/services/Address_Points/FeatureServer/0` |
| 13 | IL | Address Points_V | B | road_only | `https://services.arcgis.com/fGsbyIOAuxHnF97m/arcgis/rest/services/Address_Points_V/FeatureServer/0` |
| 14 | IA | 2022 Lightbox Address Points Option B | C | empty_shell | `https://services9.arcgis.com/WGUfikw6ahcG09qY/arcgis/rest/services/2022_Lightbox_Address_Points_Option_B/FeatureServer/0` |
| 15 | NH | Fire_Stations | C | empty_shell | `https://services4.arcgis.com/ZFghKabnNJcV4IUj/arcgis/rest/services/OSM_Amenities_Fire_Stations/FeatureServer/0` |
| 16 | TN | NG911 ESN | C | no_city | `https://services7.arcgis.com/uFAr0LUPy14bDaLg/arcgis/rest/services/Nashville_110623B_WFL1/FeatureServer/0` |
| 17 | AZ | Address_1424300337393713068 | C | no_zip | `https://services3.arcgis.com/0OPQIK59PJJqLK0A/arcgis/rest/services/Address_1424300337393713068/FeatureServer/0` |
| 18 | CO | Site Addresses | C | no_zip | `https://services7.arcgis.com/piPfTFmrV9d1DIvN/arcgis/rest/services/SiteAddresses_public_84b35cee615045ffbebd93e11cdb072e/FeatureServer/0` |
| 19 | OH | Address Points | S | full_address | `https://services6.arcgis.com/beDkVEXisjZZmkuZ/arcgis/rest/services/Address_Points/FeatureServer/0` |
| 20 | MD | Address Points and CPNs | S | full_address | `https://services2.arcgis.com/gEFt9c3jUfWMXCEP/arcgis/rest/services/Address_Points_and_CPNs_Update/FeatureServer/3` |
