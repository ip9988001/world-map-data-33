# NG911 远程层补数 + 脏层溯源 + 三州对账（2026-11-24，task `w2-20261124-calib-sandbox-re`）

> 只读盘点补充件。**不做融合、不做分级改动、不改 `sandbox/rules.py`、不动引擎**。
> 本文件是 `calib-inventory-20261123.md` 的增量：后者由 `analysis/calib_assemble.py` 生成（会被重跑覆盖），本文件不会被覆盖。

## 一、`probe_err` 的真因（一句话）

**不是报错。** `calib_ng911_probe.py` 用 `meta.get("count") or meta.get("featureCount")` 取声明行数，而 ArcGIS 的 **图层级** `?f=json` 响应本来就没有 `count` / `featureCount` 键（只有 `maxRecordCount`、`fields`、`geometryType`）。
取到 `None` → `rows` 空 → 脚本仍按 `probe_err=` 模板拼 note，`err` 字段其实是**空串**。15 层的 `meta_http` 全是 **200**，没有一个真失败。

复现证据（`/tmp/calib_remote_probe.json`，本轮 4 请求/层：meta + returnCountOnly + 兜底 returnIdsOnly + 20 条样值）：

- 15/15：`meta_http=200`，`has_count_key=false`，`has_featureCount_key=false`
- 15/15：`count` 由 `query?where=1=1&returnCountOnly=true` 一次拿全（`count_http=200`），**没有一层需要 returnIdsOnly 兜底**
- 15/15：样值 `20/20`，`sample_http=200`

## 二、15 层实采 count + 可用性

`usable` 判据：`full` = 门牌+街名+城市齐（state/zip 视源而定）；`partial` = 是地址层但缺件；`no` = 不是地址层。

| # | state | layer（标题） | rows(returnCountOnly) | n_fields | 门牌/街/城/州/邮 (20 条样值) | usable | 备注 |
|---|---|---|---|---|---|---|---|
| 295 | NH | Fire_Stations | 205 | 18 | 1/1/1/20/1 | **no** | `meta_name=OSM_Amenities_Fire_Stations`；`addr_state` 20/20 = **`VT`**（全州 VT），实为 OSM POI 导入，`non_address_or_mismatch` |
| 297 | VA | Virginia Address Points | 3,881,020 | 33 | 20/20/20/20/20 | full | ADDRNUM/FULLNAME/MUNICIPALITY/STATE/ZIP_5 |
| 298 | CA | OC Addresses 20260811 | 1,180,322 | 14 | 20/20/20/—/20 | full | 城市只有 `CADCityCode` 三字母码，`Jurisdiction`/`Community` 可补 |
| 299 | PA | Address Points | 1,044,844 | 24 | 2/12/0/—/20 | partial | `Address_Number` 只 2/20；`Full_Address` 20/20 但带前导空格、门牌缺；`Municipality` 0/20 |
| 300 | KS | Sacramento County, CA Addresses | 662,634 | 7 | 20/20/20/20/20 | full | `addr_*` 标准 7 字段 |
| 301 | TN | NG911 ESN | 442,066 | 27 | 20/20/20/—/20 | full | `title_mismatch`：实服务名 `Address Points(1-1250)`，标题是 ESN 表 |
| 302 | CO | Site Addresses | 397,598 | 23 | 20/0/20/—/— | partial | `FULLNAME` 空但 `FULLADDR` 20/20（如 `5456 N Eagle St`），无 state/zip 字段 |
| 303 | MA | City of Boston, MA Addresses | 396,923 | 10 | 20/20/20/20/20 | full | `addr_*` 标准 |
| 304 | GA | Address Points | 392,001 | 38 | 20/20/20/20/20 | full | ADDRNUM/FULLNAME/POSTAL_CITY/STATE/ZIPCODE |
| 305 | IL | Address Points_V | 388,335 | 24 | 20/20/20/20/20 | full | 属性带 parcel/tax 字段（地址视图挂在宗地上） |
| 306 | MD | Address Points and CPNs | 300,309 | 38 | 20/20/20/20/20 | full | `title_mismatch`：实服务名 `Address Labels below 4K` |
| 307 | AZ | Address_1424300337393713068 | 274,644 | 13 | 20/20/20/—/— | partial | 无 zip/state 字段 |
| 308 | LA | CNO_Addresses | 267,730 | 34 | 20/20/20/—/— | partial | 无 zip/state 字段 |
| 309 | FL | VC Addresses | 263,947 | 27 | 20/20/20/—/— | partial | 无 zip/state 字段；`FULLADDR` 里含 city/state/zip 文本 |
| 313 | MN | EAS_Addresses | 156,027 | 20 | 20/20/—/—/19 | full | 无 city 字段；邮编 19/20 |

字段映射逐层写在 CSV 的 `fields_mapped=` 里；`nonnull_*` 列已按 20 条样值填好（原来 15 行全空）。

## 三、分组分母口径修正（**未改 `grouping.json`**）

`grouping.json` 的 20 层分母 17 里包含 `Fire_Stations`（被判 `empty_shell` / `C`）。但本轮实测：它不是地址层（OSM POI，`addr_state` 全 `VT`，门牌/街名 1/20）。
**建议下一轮把分母 17 → 16**，剔除 `Fire_Stations`。本轮只标 `usable=no / non_address_or_mismatch`，**不动 `grouping.json`**（那是 `rules.py` 的输出，改它等于改分级）。

### 附带发现（规则缺口，同样只报不改）

`grouping.json` 里 `road_only` 的 4 层（`Sacramento County, CA Addresses`、`City of Boston, MA Addresses`、`Address Points_V`、`Address Points and CPNs`）**其实都有门牌字段**（本轮实测 20/20）。原因是 `sandbox/rules.py` 的 `ALIASES["number"]` 只收了 `housenum`/`add_number`/`addrnum`/`address_number` 等，`canonical()` 用**归一化后精确匹配**，于是：

- `addr_housenumber` → `addrhousenumber`（不命中）
- `ADDR_NUMBER` → `addrnumber`（别名只有 `addnumber`/`addressnumber`）
- `HOUSENUMBE` → `housenumbe`（截断，不命中 `housenum`）

⇒ 4 层被误判 `road_only`。修法（下一轮，需 muse 点头后才动引擎）：`_norm_key` 归一后做**前缀包含**匹配，或把这 3 个别名补进 `ALIASES["number"]`。

## 四、15 个脏层：完整可识别层名 + 服务 URL

账本里的层名被**左侧截断**（`ices_GeorginaMap_…`、`st_services_…`、`_services_…` 都是截断残片）。按 `survey/ng911/layers.json` 归一化后**唯一命中**还原（15/15 唯一，脚本在 `dirty-layer-urls.json`）。

| # | 账本层名（截断） | 真州 | 服务标题 | URL 尾段 | 实采 | 声明 | survey count | geom | nf |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | NY | SiteAddressPoint_Labels | `maps.georgina.ca/…/GeorginaMap_W84/SiteAddressPoint_Labels_W84/MapServer/0` | 20,570 | 23,246 | 23,246 | Point | 41 |
| 2 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | NY | Georgina - Site Address Point W84 | `maps.georgina.ca/…/GeorginaMap_W84/SiteAddressPoint_W84/MapServer/0` | 20,567 | 23,241 | 23,241 | Point | 41 |
| 3 | `84Po4FBDs_arcgis_rest_services_Address_Point_FeatureServer_0` | 未定位 | Address Point | `services5.arcgis.com/GrsHGJ284Po4FBDs/…/Address_Point/FeatureServer/0` | 26,616 | 14,616 | 14,616 | Point | 40 |
| 4 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 未定位 | Addresses | `gis.centrewellington.ca/server/rest/services/Parcels_Public/MapServer/1` | 17,270 | 17,295 | 17,295 | Point | 13 |
| 5 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | MI | Town of Tecumseh Address Points | `gisweb.tecumseh.ca/…/OpenDataMAP_InfraZonePropBound_Layers/MapServer/33` | 9,602 | 9,861 | （survey 无 count） | — | — |
| 6 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 未定位 | Address Points (Enterprise Portal) | `gis.co.richland.wi.us/…/RichlandCo_GIS_Public/MapServer/6` | 9,101 | 9,624 | 9,614 | Point | 30 |
| 7 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | MN | Address Points | `gis.co.polk.mn.us/…/Addressing/AddressPoints/MapServer/0` | 6,616 | 14,470 | 14,470 | Point | 21 |
| 8 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 未定位 | Address Points County wide | `gisportal.co.burlington.nj.us/hosting/…/NWS_AddressPoints_Nstreets_centerlines/MapServer/0` | 118,916 | 251,639 | 251,639 | Point | 111 |
| 9 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | 未定位 | Addresses | `public1.co.waupaca.wi.us/…/Public/OpenData/MapServer/24` | — | — | 28,646 | Point | 25 |
| 10 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | 未定位 | Address Points | `gis.santamonica.gov/server/rest/services/Address_Points/MapServer/0` | — | — | 57,063 | Point | 13 |
| 11 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | 未定位 | Site Address | `maps.vilascountywi.gov/…/V4/SiteAddress/MapServer/0` | — | — | 48,148 | Point | 75 |
| 12 | `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | 未定位 | Situs | `gis.townofpalmbeach.com/…/BaseData/Situs/MapServer/0` | — | — | 13,190 | Point | 42 |
| 13 | `county_com_arcgis_rest_services_features_Address_MapServer_0` | 未定位 | Address Points | `maps.laramiecounty.com/…/features/Address/MapServer/0` | — | — | 45,670 | Point | 59 |
| 14 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | 未定位 | NG911 Addressing Layers | `gismaps.onslowcountync.gov/server/rest/services/NG911_ReadOnly/NG911_Addressing_Layers/MapServer/0` | — | — | 108,836 | Point | 52 |
| 15 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 未定位 | Buncombe County, NC - Addresses | `gis.buncombecounty.org/arcgis/rest/services/opendata/MapServer/2` | — | — | 187,802 | Point | 10 |

三条读法：

1. **#3 实采 > 声明**（26,616 > 14,616，+82%）：声明是过期快照，典型「分母不许永久当分母」。
2. **#5/#6 声明与 survey 不一致**：#5 账本 9,861、survey 无 count；#6 账本 9,624 != survey 9,614（漂 10 行）⇒ 这两个 declared 来源不同批次。
3. **#9–#15 标 `upstream_unstable` 但 survey 里有非零 count**（1.3 万 ~ 18.8 万）⇒ 「上游不稳」是**采集时刻**的瞬时状态，不是服务永久下线；下一轮可以直接重探（本轮未探，只读口径）。

## 五、三州五源对账（muse 口径 vs 实测 — 差额全部解释到件）

口径差一条：**muse 数「资产文件数」，本仓 CSV 只数「可承载地址的图层」**（元数据 json、边界面文件不入层）。

### DE（25 个资产）

| 源 | muse 口径 | 实测 | 差额 | 原因 |
|---|---|---|---|---|
| NAD | 6 | 4 | +2 | muse 含 `NAD-US-DE-columns.json` + `NAD-US-DE-layer-metadata.json` 两个元数据件；实测 4 = 3 县 ndjson（10001/10003/10005）+ 1 个 `OUTOFSTATE`（188,922 行） |
| OA | 5 | 5 | 0 | 一致（dover / newark / kent / new_castle / sussex） |
| TIGER | 10 | 3 | +7 | muse 数全部 10 个 TIGER 文件；实测只计 3 个 `addrfeat`（唯一带 `LFROMHN/LTOHN` 门牌字段的层）。7 个被排除：`county-10001/10003/10005.geojson`、`place-dover.geojson`、`places.zip`、`state.geojson`、`zcta.geojson`（面/边界，无门牌属性） |
| OVERTURE | 1 | 1 | 0 | 一致 |

25 = 6 + 5 + 10 + 1 + MANIFEST/STATUS/RELEASE_NOTES(3)。

### IA（364 个资产）

| 源 | muse 口径 | 实测 | 差额 | 原因 |
|---|---|---|---|---|
| NAD | 102 | 100 | +2 | 实测 = 99 县 ndjson + 1 个 `OUTOFSTATE`（635,561 行）；muse 另加 `columns.json` + `layer-metadata.json` |
| OA | 58 | 58 | 0 | 一致（58 个县级 OA zip） |
| TIGER | 200 | 99 | +101 | muse = 99 `addrfeat` + 99 `county-<fips>.geojson` + `places.zip` + `state.geojson`；实测只计 99 个 addrfeat。排除 101 = 99 个县界 + places 面 + state 面 |
| OVERTURE | 1 | 1 | 0 | 一致 |

364 = 102 + 200 + 58 + 1 + 3。

### NH（本地 DuckDB 全扫复核，非账本抄写）

| 源 | 实测（本地全扫） | 来源 | 说明 |
|---|---|---|---|
| GRANIT 地块点 | **601,374** | `duckdb 1.1.3` 读 `GRANIT-US-NH-parcel-points.ndjson.gz`（州级合并件）`count(*)` | CSV 里 11 行 = 1 州级合并件 + 10 个分县片；**分县片 Σ = 601,355**（比州级少 19 行，0.003%），二者是同一批数据，**不得相加**（相加得 1,202,729 = 双计） |
| TIGER addrfeat 插值 | **5,870,025** | `duckdb` 读 `tiger/TIGER-US-NH-addrfeat-interpolated-33001..33019` 十片 Σ + 州级 `TIGER-US-NH-addrfeat-interpolated.ndjson.gz` | 十片 Σ = 5,870,025 = 州级件行数，逐位相等；同样**不得相加**（相加 11,740,050 = 双计） |
| NAD | 354,804 | `NAD-US-NH-OUTOFSTATE.ndjson.gz` | 只有 OUTOFSTATE 一个件（NAD 服务本身不含 NH，前轮已证） |
| NG911 | 205（无效） | `OSM_Amenities_Fire_Stations` | 见第二节 295 行，不进分母 |

复核命令（本轮实跑，7.8s）：

```
duckdb> select count(*) from read_json_auto('GRANIT-US-NH-parcel-points.ndjson.gz');           -- 601374
duckdb> select count(*) from read_json_auto('tiger/TIGER-US-NH-addrfeat-interpolated-*.ndjson.gz');  -- 5870025
```
