# 线层「不采」核定（2026-10-30）

> 三仓 1,946 个 Polyline 层一个都没采（STEP-01 几何白名单直接 skip）。
> 本文件是**可查的账**：逐层把字段清单与 TIGER addrfeat 的 25 字段对齐，写明为什么不采、
> 哪些其实值得补采。**不许默认放弃**。

## 一、基准与证据来源

- TIGER 基准：一仓已发布资产 `tl_2024_10001_addrfeat.zip`（25 字段，dbf 实读）
  `TLID, TFIDL, TFIDR, ARIDL, ARIDR, LINEARID, FULLNAME, LFROMHN, LTOHN, RFROMHN, RTOHN, ZIPL, ZIPR, EDGE_MTFCC, ROAD_MTFCC, PARITYL, PARITYR, PLUS4L, PLUS4R, LFROMTYP, LTOTYP, RFROMTYP, RTOTYP, OFFSETL, OFFSETR`
  → 已含 **号段**（LFROMHN/LTOHN/RFROMHN/RTOHN）、**ZIP+4**（PLUS4L/R）、**号段类型**（LFROMTYP…）、**parity**、**offset**、**MTFCC**、**FULLNAME**
- 线层字段清单：`collect/polygon_probe.json`（23,556 层探针，离线，无需访问上游）
- ⚠ **样本值未取**：线层未采，3 条样本需要一次上游 query，本轮边界禁止 → 判定只用字段清单 + `nfields`；每层 `url` 已入账本，批准后一条 query 即可补证

## 二、总账（1,946 层）

| 结论 | 层数 | 含义 |
|---|---|---|
| `not_worth_collect` | 1879 | 独有字段只有 OIM/几何/道路属性/行政区名 → TIGER 已覆盖号段语义 |
| `worth_collect` | 59 | **有 TIGER 拿不到的独有地址语义字段** → 候选补采（再分 A/B 两档，见第四节） |
| `out_of_scope` | 1 | 非美国数据（PROVINCE/POSTCODE）→ 不在范围 |
| `no_field_evidence` | 0 | 探针没覆盖该层，无法定论（不是「不采」的理由） |

## 三、20 层逐条结论

| # | 层 | 州 | 行数 | 字段数 | TIGER 命中 | 独有字段（地址语义） | 独有（其它） | 结论 |
|---|---|---|---|---|---|---|---|---|
| 1 | `ices_Hosted_Road_Centerlines_of_Indiana_2025_Feature` | IN | 569,734 | 6 | 4 | GEOFULLADDRESS | VALID_GEO_ADDRESS | worth_collect |
| 2 | `s_Hosted_Road_Centerlines_of_Indiana_Current_Feature` | IN | 569,734 | 6 | 4 | GEOFULLADDRESS | VALID_GEO_ADDRESS | worth_collect |
| 3 | `ices_Hosted_Road_Centerlines_of_Indiana_2024_Feature` | IN | 566,940 | 6 | 4 | GEOFULLADDRESS | VALID_GEO_ADDRESS | worth_collect |
| 4 | `ices_Hosted_Road_Centerlines_of_Indiana_2023_Feature` | IN | 550,953 | 6 | 4 | GEOFULLADDRESS | ORIG_ADDR | worth_collect |
| 5 | `es_Hosted_Street_Centerlines_of_Indiana_2022_Feature` | IN | 538,370 | 6 | 4 | GEOFULLADDRESS | ORIG_ADDR | worth_collect |
| 6 | `ces_Hosted_Road_Centerlines_of_Indiana_2021_FeatureS` | IN | 525,458 | 6 | 4 | GEOFULLADDRESS | ORIG_ADDR | worth_collect |
| 7 | `rest_services_Solano_County_Road_Centerlines_Feature` | CA | 26,851 | 6 | 3 | FULLADDRES, FULLADDR_L, FULLADDR_1 | — | worth_collect |
| 8 | `qKAFwdGU_arcgis_rest_services_AumentumPublic_Feature` | CA | 26,531 | 6 | 3 | FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL | — | worth_collect |
| 9 | `AFwdGU_arcgis_rest_services_Road_Centerlines_Feature` | CA | 26,526 | 6 | 3 | FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL | — | worth_collect |
| 10 | `ervices_Solano_County_Roads_Centerlines_WFL1_Feature` | CA | 26,319 | 6 | 3 | FULLADDRES, FULLADDR_L, FULLADDR_1 | — | worth_collect |
| 11 | `_arcgis_rest_services_Road_Centerlines_Tiled_Feature` | CA | 26,113 | 6 | 3 | FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL | — | worth_collect |
| 12 | `cgis_rest_services_Road_Centerlines_Apr2024_FeatureS` | CA | 26,104 | 6 | 3 | FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL | — | worth_collect |
| 13 | `p_gov_secure_rest_services_NC1Map_Transportation_Map` | NC | 905,208 | 4 | 4 | — | — | not_worth_collect |
| 14 | `gis_rest_services_NG911_Centerlines_lmlaquid_Feature` | NC | 892,231 | 4 | 4 | — | — | not_worth_collect |
| 15 | `is_rest_services_AZ911_RoadCenterline_Hosted_Feature` | AZ | 651,869 | 4 | 4 | — | — | not_worth_collect |
| 16 | `est_services_AZ_NG911_Road_Centerlines_Tiles_Feature` | AZ | 646,133 | 4 | 4 | — | — | not_worth_collect |
| 17 | `7UzH9fcLVvv_arcgis_rest_services_Roads_AKDOT_Feature` | AK | 26,650 | 1 | 0 | — | ROUTE_LOCATION_CODE | not_worth_collect |
| 18 | `_ArcGIS_rest_services_AKDOT_Routes_Mileposts_Feature` | AK | 25,762 | 1 | 0 | — | ROUTE_LOCATION_CODE | not_worth_collect |
| 19 | `rcgis_rest_services_Existing_AT_Service_2021_Feature` | UT | 16,753 | 2 | 0 | — | COUNTYLOCATION, CITYLOCATION | not_worth_collect |
| 20 | `gOW_arcgis_rest_services_Statewide_Bike_Plan_Feature` | UT | 2,852 | 2 | 0 | — | COUNTYLOCATION, CITYLOCATION | not_worth_collect |

逐层理由（抽样层）：

- `ices_Hosted_Road_Centerlines_of_Indiana_2025_FeatureServer_0` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `s_Hosted_Road_Centerlines_of_Indiana_Current_FeatureServer_0` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `ices_Hosted_Road_Centerlines_of_Indiana_2024_FeatureServer_0` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `ices_Hosted_Road_Centerlines_of_Indiana_2023_FeatureServer_8` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `es_Hosted_Street_Centerlines_of_Indiana_2022_FeatureServer_0` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `ces_Hosted_Road_Centerlines_of_Indiana_2021_FeatureServer_15` → **worth_collect**：独有地址语义字段：GEOFULLADDRESS
- `rest_services_Solano_County_Road_Centerlines_FeatureServer_0` → **worth_collect**：独有地址语义字段：FULLADDRES, FULLADDR_L, FULLADDR_1
- `qKAFwdGU_arcgis_rest_services_AumentumPublic_FeatureServer_7` → **worth_collect**：独有地址语义字段：FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL
- `AFwdGU_arcgis_rest_services_Road_Centerlines_FeatureServer_0` → **worth_collect**：独有地址语义字段：FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL
- `ervices_Solano_County_Roads_Centerlines_WFL1_FeatureServer_0` → **worth_collect**：独有地址语义字段：FULLADDRES, FULLADDR_L, FULLADDR_1
- `_arcgis_rest_services_Road_Centerlines_Tiled_FeatureServer_0` → **worth_collect**：独有地址语义字段：FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL
- `cgis_rest_services_Road_Centerlines_Apr2024_FeatureServer_11` → **worth_collect**：独有地址语义字段：FULLADDRESS, FULLADDR_LABEL_ABBRV, FULLADDR_LABEL
- `p_gov_secure_rest_services_NC1Map_Transportation_MapServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `gis_rest_services_NG911_Centerlines_lmlaquid_FeatureServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `is_rest_services_AZ911_RoadCenterline_Hosted_FeatureServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `est_services_AZ_NG911_Road_Centerlines_Tiles_FeatureServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `7UzH9fcLVvv_arcgis_rest_services_Roads_AKDOT_FeatureServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `_ArcGIS_rest_services_AKDOT_Routes_Mileposts_FeatureServer_0` → **not_worth_collect**：除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义
- `rcgis_rest_services_Existing_AT_Service_2021_FeatureServer_0` → **not_worth_collect**：独有仅行政区名（COUNTYLOCATION）：县可由 TIGER 文件自身确定，city 对号段无增益 → 不值得为它重采整层
- `gOW_arcgis_rest_services_Statewide_Bike_Plan_FeatureServer_0` → **not_worth_collect**：独有仅行政区名（COUNTYLOCATION）：县可由 TIGER 文件自身确定，city 对号段无增益 → 不值得为它重采整层

## 四、值得补采的层（全部 59 层，不只抽样）

- **A 档（11 层）：含单元/ESN 等 TIGER 结构上真没有的字段 → 建议补采**
- **B 档（48 层）：只多一个「拼好的整串地址」字段 → 不补**（TIGER 的 FULLNAME+号段可自行拼，没有新语义；补采只为省一次拼接不值）

### A 档（建议补采）

| 层 | 州 | 行数 | 独有字段 |
|---|---|---|---|
| `_arcgis_rest_services_Addresses_to_Romkey_v2_Feature` | MN | 3,550 | FROM_FULL_ADDRESS_UNIT |
| `is_rest_services_Staten_Island_Line_Distance_Feature` | NJ | 322 | TO_SUBADDR |
| `is_rest_services_Staten_Island_Walking_Route_Feature` | NJ | 322 | TO_SUBADDR |
| `Hdf_arcgis_rest_services_TGI_UPDM_Centerline_Feature` | 未定位 | 228 | SAPTECHLOCATION |
| `rest_services_Map_Notes__Points__to_AkronGeo_Feature` | OH | 123 | TO_GEOCODE_BLDG_ADDRESS |
| `s_rest_services_Map_Notes__Points__to_AugGeo_Feature` | OH | 53 | TO_GEOCODE_BLDG_ADDRESS |
| `ervices_BubbleTeaLocations_to_LACBD_distance_Feature` | CA | 23 | FROM_SUBADDR |
| `_Kaartnotities_1__Points__naar_Ambuposten201_Feature` | 未定位 | 1 | TO_SUBADDR |
| `_Notes__Points__to_Stella_Washington_Address_Feature` | KY | 1 | TO_SUBADDR |
| `ces_Ambuposten2017_naar_Kaartnotities__Point_Feature` | 未定位 | 1 | FROM_SUBADDR |
| `es_Ambuposten2017_naar_Kaartnotities__Points_Feature` | 未定位 | 1 | FROM_SUBADDR |

### B 档（不建议补采，仅记账）

共 48 层，独有字段都是 `FULLADDRESS`/`GEOFULLADDRESS`/`FULLADDR_L` 这类拼串列。逐层见 `collect/ledger/line_layers_decision.json`（`tier=B_full_address_only`）。

## 五、结论

1. **不采的结论仍然成立**，但理由从「几何白名单 skip」升级为「字段对比后无增益」——TIGER addrfeat 已覆盖号段/ZIP+4/号段类型/parity/offset/FULLNAME。
2. 有独有字段的是 59 层，但真正值得补采的只有 **A 档 11 层**（单元/ESN，TIGER 结构上真没有）；其余 48 层只是多一个拼好的整串地址列，TIGER 的 FULLNAME+号段能自行拼出 → 不补。
3. 0 层因探针未覆盖**无法定论**，不能计入「不采」——补一次元数据读取即可（账本里已存 url）。
4. 量化：A 档 11 层合计只有 **4,625 行**（占号段类总量不到 0.01%），其中唯一有真实单元语义的是 `Addresses_to_Romkey_v2`（3,550 行，且是地理编码拼接层不是街道层）→ **结论：线层整体不值得补采，A 档留名待有需要时按需单采**。
5. 样本值（3 条/层）本轮未取：需要上游 query，等边界放开后按账本 url 批量补，届时可一并核实号段语义（如 LFROMHN 是否真的存在）。

## 六、复现

```bash
python3 analysis/line_layers_decision.py
```
