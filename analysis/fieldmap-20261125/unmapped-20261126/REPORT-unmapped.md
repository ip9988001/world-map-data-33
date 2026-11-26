# 195 个未映射层的逐层归因（muse-000269）

> 任务：全量重扫后 3,355/3,550 层映射上、**195 层未上**（覆盖率 94.51%，离 95% 门禁差 18 层）。本单把这 195 层逐层查清，分 A/B/UNKNOWN，给出可修原因与修法。**只查不改**。

## 0. 结论

- **A（不可修 / 非地址）136 层**、**B（地址层但因可修原因没上）58 层**、**UNKNOWN 1 层**，合计 195 = 195。
- B 类里 **38 层在美国境内口径**、20 层在境外（加/新/英/爱/南非/根西等）。
- **B 类全修 → 覆盖率 96.14%（3413/3550）**；**只修美国境内 38 层 → 95.58%（3393/3550）**。两种口径都过 95%（门禁需 ≥18 层，美国境内可修层已有 38 层）。
- 可恢复行数（样本命中率 × 层 in_rows 折算）：全 B 类 **3,192,659 行**，其中美国境内 **1,257,819 行**。
- 三条主线根因（都可在代码里定位、可最小复现）：
  1. **角色表缺街名别名**（38 层）——`registry/dialects.v1.yaml` + `engine/dialects` 合并后只有 148 个归一字段名，NENA 911 系列 `feanme/featyp`、加拿大 `strname/strsuffix`、`roadname`、`street_nm`、`thorofare`、`msag_route` 等常见街名/街型列统统不在表里。
  2. **`fm_core.map_row` 的组合串拆分只在首行试一次**（13 层，另有 1 层是 40 键上限）——首行拆不出就把 `_split_tried` 置真、`_split_key` 留空，之后每行直接跳过 split；因为「首行能拆的层不可能 0 行映射」，这 13 层必然踩中该短路。
  3. **地址在字段名过泛的列里**（5 层，`NAME`+`TYPE`、`STR`、`PARCEL_LOC`、`LST_CONCAT`）——不能进全局最小安全表，只能按 url/org 建层级别名；这 5 层实测补别名后命中率 100%。

## 1. 起点核对与清单闭环

- 工作树 `/data/workspace/wmd-fieldmap`，分支 `feat/fieldmap-20261125`，起点 HEAD `cb2ee3f`（= PR #58 head），`git status` 干净，无其他映射进程在跑。
- `unusable-v2.csv` 195 数据行；`layer-coverage.v2.csv` 里 `mapped==0` 的层 **195** 个。
- 两者交叉核对：`unusable − mapped0` = **0**，`mapped0 − unusable` = **0**。**完全同一批 195 层，零差异**，闭环到 3550 − 3355 = 195。
- 195 层合计 in_rows = **26,530,339 行**（`dropped_below_c` 全部计入，等价于「整层丢弃」）。

## 2. 方法与产物（全部只读，可复跑）

采样：每层取首 + 中两个 `part-u*.ndjson.gz`，各读 150 行，**共 25,465 行**（单 part 文件的层实际 150 行）。判定一律复用生产代码：`fm_core.map_row` 的取值顺序、`split_addr.roles_of` 的角色表、`split_addr.split_number_street` 的拆串实现——本单不另写一套口径。

| 脚本 | 作用 | 产物 |
|---|---|---|
| `scan_unmapped.py` | 逐层字段名集合、每字段非空率、角色命中/近失、组合串可拆性、5 行脱敏样本、地理中位数 | `layers-evidence.jsonl`、`scan-summary.json` |
| `simulate_fix.py` | 三条修复路径逐行模拟（补别名 / split 全字段每行重试 / split 放宽） | `fix-simulation.jsonl` |
| `measure_layer_scoped.py` | 字段名过泛的 6 层，按指定字段实测拼街名命中率 | `layer-scoped-fixes.jsonl` |
| `classify_unmapped.py` | 规则判定 + 人工复核覆盖，落 A/B/UNKNOWN | `unmapped-classification.csv`、`overrides-resolved.json` |
| `make_report.py` | 由上述产物合成本报告（数字不手抄） | `REPORT-unmapped.md` |

复跑顺序：`scan_unmapped.py` → `simulate_fix.py` → `measure_layer_scoped.py` → `classify_unmapped.py` → `make_report.py`。全部只读 `dist/intake-full/layers/` 与 `analysis/fieldmap-20261125/layer-coverage.v2.csv`，**未改任何既有文件**。

## 3. 汇总

| class | 层数 | 说明 |
|---|---|---|
| A | 136 | 真非地址层 / 采集缺字段 / 口径外点位居多，不可由映射侧修 |
| B | 58 | 地址层，缺别名或 split 缺陷，**可修** |
| UNKNOWN | 1 | `xjrB05UV_arcgis_rest_services_Riv_Co_Add…` sample_too_small |

按 `reason_code` 分桶：

| reason_code | 层数 | 其中 B | 中文 |
|---|---|---|---|
| `non_us_point_or_poi` | 45 | 0 | 口径外（非美国）POI/服务点位 |
| `alias_missing_street` | 38 | 38 | 街名/街型字段不在角色表（补别名即可） |
| `admin_or_survey_table` | 21 | 0 | 调查/行政/报表面板 |
| `no_street_field` | 16 | 0 | 只有门牌号，源里没有街名字段 |
| `label_or_annotation_only` | 14 | 0 | 注记/标注层（Label/TextString/Contents） |
| `not_address_layer` | 14 | 0 | 非地址层（无门牌/街名/可拆串） |
| `split_first_row_only` | 13 | 13 | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| `addr_attrs_not_collected` | 11 | 0 | 地址层，但采集侧地址属性未落盘（需重采） |
| `non_us_dataset_no_usable_field` | 6 | 0 | 口径外数据集，且字段不成美国口径 |
| `grid_range_no_street_name` | 5 | 0 | 网格/街区区间，无街名 |
| `alias_generic_fieldname_layer_scoped` | 5 | 5 | 地址在字段名过泛的列里（只能层级别名） |
| `street_field_all_null` | 2 | 0 | 街名列存在但全空/占位 |
| `intersection_no_number` | 1 | 0 | 路口名，无门牌 |
| `unparseable_concat` | 1 | 0 | 门牌与街名粘死不可拆 |
| `derived_geocoder_output` | 1 | 1 | 地理编码产物列，且多数行为 '<Null>' |
| `split_key_beyond_40` | 1 | 1 | 组合串排在 raw 第 40 个键之后，split 扫不到 |
| `sample_too_small` | 1 | 0 | 样本过小，无法判定 |

A 类按口径分布：美国境内 59 层、奥地利 20 层、未定位 12 层、加拿大 10 层、境外(geo) 8 层、德国 8 层、印尼 7 层、澳大利亚 3 层、捷克 2 层、塞浦路斯 2 层、荷兰 1 层、新西兰 1 层、爱尔兰 1 层、黎巴嫩 1 层、英国 1 层。

## 4. 三条主线根因（代码定位 + 最小复现）

### 4.1 角色表缺街名/街型别名（38 层）

195 层逐层统计：**191 层在 raw 里连一个角色表命中的街名字段都没有**；全部 195 层 `street` 恒空 → `grade_of` 落到 None → 整层 `dropped_below_c`。把 195 层出现过的字段名归一后共 **1,815 个**，其中**只有 32 个**在角色表（148 名）里；**357 个地址类字段名不在表里**。缺的不是冷门列，是这些「一眼就是街名」的列：

- `feanme` / `featyp`（NENA 911 的 FeatureName/Type，2 层共 583 行非空）
- `strname` / `strsuffix` / `strtype`（加拿大 civic address，5 层）
- `roadname` / `roadnm` / `streetname` / `street_nm` / `street_description`
- `sfeanme` / `sfeatyp`（夏威夷 911 变体）
- `msag_route`（新斯科舍 civic address）、`thorofare`（英国型）、`std_street`（温哥华）、`civic_street`（Lake Country）、`propstreet`（密苏里 VOC）、`loc_st_nam`（纽约 WFL1）

即「同一个数据集，门牌列 `st_num` 在表里、街名列 `feanme` 不在表里」——门牌取到、街名取不到，门牌单独不构成地址（grade C 要求 street），于是整层丢弃。

**最小复现**：`gyrE4_arcgis_rest_services_Address_Point_911_FeatureServer_0`（222,405 行）第 1 行 raw：`st_num=7870, feanme=STATE, featyp=ST, Zipcode=36522`。
`roles_of()` 里 `stnum` 命中 number、`feanme`/`featyp` **都不在表里** → street 空 → 丢弃。把 `feanme`+`featyp` 加进 street_aliases 后，该层样本 300/300 全部落到 grade C。

**修法**：`registry/dialects.v1.yaml` 的 `minimal_safe` template 里补 `street_aliases`（不改代码、不改分级口径）。注意这些都是全局生效，宜只收「一眼是街名」的列；`NAME`/`TYPE`/`STR`/`LABEL` 这类过泛名不进全局表，走层级别名（见 4.3）。

### 4.2 `map_row` 的组合串拆分只在首行试一次（13 层）

`fm_core.py:303` 起的代码：

```python
if not street and raw and not (self._split_tried and not self._split_key):
    ...
    self._split_tried = True
    if best: self._split_key = best[0]
```

首行拆不出时 `_split_tried=True` 且 `_split_key` 仍是空串，**第 2 行起该条件恒假 → 整层再也不试 split**。反证：若某层首行能拆，那层首行就会落 grade C、`mapped ≥ 1`，根本不会出现在这 195 层里；所以「0 行映射 + 样本可拆」必然意味着首行踩了短路。

**最小复现**：`F2rCsQjt0P3e_arcgis_rest_services_AddressPts_FeatureServer_0`（13,245 行）字段 `LABEL = "3358 K 157 HWY"` → `split_number_street` 给 num=`3358`、street=`K 157 HWY`、reason=ok、confidence=0.95；但该层的 `LABEL` 不是 raw 的第一个键，且首行未命中 → 整层 0 行。

**修法（两处，同一个函数）**：① 去掉 `_split_tried` 短路，逐行都试；② `cand_keys` 从 `list(raw.keys())[:40]` 扩到全字段（40 键上限只命中 1 层，`gis_rest_services_STR_October_2023_Addresses`（69 个键，样本命中 0.987 vs 首 40 键 0.013），但同属一个缺陷，一起修）。修完这 13 层按样本命中率可恢复约 **605,676 行**。

### 4.3 地址在字段名过泛的列里（5 层）

这 5 层的街名在 `NAME`+`TYPE`（Coquitlam 2 层、Kelowna 1 层）、`STR`（杰克逊维尔海滩）、`PARCEL_LOC`（纽约）、`LST_CONCAT`（明尼苏达 Owens Twp）。这类名字放进全局最小安全表会误伤（`NAME` 可能是人名/场所名/业主名），只能按 url/org 建层级别名。实测：

| 层 | 街名字段 | 门牌字段 | 实测 street 命中 |
|---|---|---|---|
| `s_com_arcgis_rest_services_GIS_App_GIS_App_BASE_MapS` | NAME | CIVIC_TEXT+ADDR_NBR | 100% |
| `nH5x_arcgis_rest_services_Address__Elections_Feature` | NAME | CIVIC_TEXT+ADDR_NBR | 100% |
| `city_ca_arcgis_rest_services_Public_OpenData_Feature` | NAME | CIVIC_TEXT+ADDR_NBR | 100% |
| `S7cpxnJP_arcgis_rest_services_Address_Points_Feature` | PARCEL_LOC | 无（只到 grade C） | 100% |
| `9Xs_arcgis_rest_services_AddressPts_OwensTwp_Feature` | LST_CONCAT | ANUMBER | 100% |
| `poec_arcgis_rest_services_AddressPoints_view_Feature` | STR | STR_NUM | 100% |

## 5. B 类逐层修法（58 层，按可恢复行降序）

| # | in_rows | 可恢复行 | 命中率 | reason | 口径 | 层 | 修法 |
|---|---|---|---|---|---|---|---|
| 1 | 485,466 | 414,248 | 0.8533 | `alias_missing_street` | 加拿大 | `est_services_BASE_BASE_NS_CivicAddress_File_UT` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['strname+strsuffix', 'strname']；不改代码，按样本命中率折算行数 |
| 2 | 519,819 | 407,174 | 0.7833 | `alias_missing_street` | 南非 | `shlD6Twu_arcgis_rest_services_Street_Address_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['strname+strtype', 'strname']；不改代码，按样本命中率折算行数 |
| 3 | 530,776 | 302,542 | 0.5700 | `split_first_row_only` | 爱尔兰 | `_rest_services_SECTO_NBI_MASTER_ADDRESS_LIST_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 4 | 222,405 | 222,405 | 1.0000 | `alias_missing_street` | 美国境内 | `gyrE4_arcgis_rest_services_Address_Point_911_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['feanme+featyp']；不改代码，按样本命中率折算行数 |
| 5 | 209,057 | 209,057 | 1.0000 | `alias_missing_street` | 新西兰 | `vt_nz_server_rest_services_OpenData_Property_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname', 'roadnamesuffix']；不改代码，按样本命中率折算行数 |
| 6 | 117,540 | 117,540 | 1.0000 | `alias_generic_fieldname_layer_scoped` | 加拿大 | `s_com_arcgis_rest_services_GIS_App_GIS_App_BAS` | 为该 org/层建层级别名：street_aliases=[NAME]+[TYPE]，number_aliases=[CIVIC_TEXT,ADDR_NBR]（实测 street 命中 100%） |
| 7 | 116,889 | 116,889 | 1.0000 | `alias_missing_street` | 美国境内 | `_rest_services_Dauphin_County_Address_Points_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['feanme+featyp', 'feanme']；不改代码，按样本命中率折算行数 |
| 8 | 115,294 | 99,925 | 0.8667 | `split_first_row_only` | 美国境内 | `gis_rest_services_Address_Points_Public_View_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 9 | 96,211 | 95,893 | 0.9967 | `alias_missing_street` | 美国境内 | `5OXNGFDn_arcgis_rest_services_Address_Points_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['sfeanme+sfeatyp', 'sfeanme']；不改代码，按样本命中率折算行数 |
| 10 | 89,554 | 89,554 | 1.0000 | `alias_missing_street` | 美国境内 | `v_server_rest_services_Hosted_Address_Points_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['strname+strsuf', 'strname']；不改代码，按样本命中率折算行数 |
| 11 | 84,437 | 84,437 | 1.0000 | `alias_generic_fieldname_layer_scoped` | 境外(geo) | `nH5x_arcgis_rest_services_Address__Elections_F` | 层级别名：street=[NAME,TYPE]，number=[CIVIC_TEXT,ADDR_NBR]（实测 100%） |
| 12 | 88,243 | 75,888 | 0.8967 | `alias_missing_street` | 美国境内 | `Ngd_arcgis_rest_services_Imperial_County_EPL_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['gcstname']；不改代码，按样本命中率折算行数 |
| 13 | 82,901 | 75,713 | 0.9133 | `alias_missing_street` | 加拿大 | `land_ca_server_rest_services_civic_addresses_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['streetnm', 'ostreetnm']；不改代码，按样本命中率折算行数 |
| 14 | 74,449 | 74,449 | 1.0000 | `alias_missing_street` | 新西兰 | `QdwKY6yp_arcgis_rest_services_Search_Address_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['addressroadname']；不改代码，按样本命中率折算行数 |
| 15 | 77,971 | 70,696 | 0.9067 | `alias_missing_street` | 美国境内 | `_services_Fontana_Parcels_and_Address_Points_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['addrsn']；不改代码，按样本命中率折算行数 |
| 16 | 73,856 | 64,498 | 0.8733 | `alias_missing_street` | 加拿大 | `arcgis_rest_services_CB_Civic_Addresses_WFL1_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['strname+strsuffix', 'strname']；不改代码，按样本命中率折算行数 |
| 17 | 56,431 | 56,431 | 1.0000 | `alias_missing_street` | 英国 | `LNJBeDlAk_arcgis_rest_services_All_Addresses_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['streetdescription', 'thoroughfare']；不改代码，按样本命中率折算行数 |
| 18 | 50,821 | 44,890 | 0.8833 | `split_first_row_only` | 美国境内 | `lxcdnZjF_arcgis_rest_services_Voting_Address_F` | 修 fm_core.map_row：split 每行都试 + 候选键扩到全字段（与另外 12 层同一根因） |
| 19 | 41,026 | 38,564 | 0.9400 | `split_first_row_only` | 美国境内 | `s_rest_services_Address_to_Alley_ID_Matching_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 20 | 41,533 | 35,440 | 0.8533 | `alias_missing_street` | 英国 | `KtMulHM03_arcgis_rest_services_Address_Point_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['thorofare']；不改代码，按样本命中率折算行数 |
| 21 | 33,337 | 33,337 | 1.0000 | `alias_missing_street` | 美国境内 | `UHl6XumF_arcgis_rest_services_R_AddressPoint_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['landbasedbotblstreetnamesstr']；不改代码，按样本命中率折算行数 |
| 22 | 31,680 | 31,680 | 1.0000 | `alias_missing_street` | 根西 | `qvET_arcgis_rest_services_Address_Points_GSY_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 23 | 31,335 | 31,335 | 1.0000 | `alias_missing_street` | 美国境内 | `cgis_rest_services_Address_20Points_20Mark43_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['sitestreetname']；不改代码，按样本命中率折算行数 |
| 24 | 32,285 | 31,209 | 0.9667 | `alias_missing_street` | 美国境内 | `co_columbia_wi_us_server_rest_services_Open_GI` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['fullstnm']；不改代码，按样本命中率折算行数 |
| 25 | 24,885 | 24,718 | 0.9933 | `split_first_row_only` | 美国境内 | `gis_rest_services_Parcel_with_addresses_2024_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 26 | 24,883 | 24,716 | 0.9933 | `split_first_row_only` | 美国境内 | `is_rest_services_AddressesParcelsUtility2024_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 27 | 24,883 | 24,716 | 0.9933 | `split_first_row_only` | 美国境内 | `_services_BaseMap_Parcels_Addresses_Boundary_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 28 | 22,853 | 22,853 | 1.0000 | `alias_missing_street` | 美国境内 | `fbh5z_arcgis_rest_services_Code_Address_Data_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['strname+strtype', 'strname']；不改代码，按样本命中率折算行数 |
| 29 | 20,192 | 20,192 | 1.0000 | `alias_generic_fieldname_layer_scoped` | 美国境内 | `S7cpxnJP_arcgis_rest_services_Address_Points_F` | 层级别名：street=[PARCEL_LOC]（实测 street 命中 100%，grade 只到 C） |
| 30 | 19,544 | 19,544 | 1.0000 | `alias_missing_street` | 美国境内 | `c71b3d4712db5c4e6a2_rest_services_Accela_Accel` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 31 | 19,544 | 19,544 | 1.0000 | `alias_missing_street` | 美国境内 | `18b4b78b270efb1_rest_services_Accela_Accela_Fe` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 32 | 18,254 | 18,254 | 1.0000 | `alias_generic_fieldname_layer_scoped` | 加拿大 | `city_ca_arcgis_rest_services_Public_OpenData_F` | 层级别名：street=[NAME,TYPE]，number=[CIVIC_TEXT,ADDR_NBR]（实测 100%） |
| 33 | 17,440 | 17,440 | 1.0000 | `alias_missing_street` | 美国境内 | `rcgis_rest_services_Address_Points_Only_WFL1_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['locstnam+locstsuf']；不改代码，按样本命中率折算行数 |
| 34 | 16,416 | 16,416 | 1.0000 | `alias_missing_street` | 美国境内 | `luOy5R3S_arcgis_rest_services_ADDRESS_POINTS_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 35 | 15,738 | 15,738 | 1.0000 | `alias_missing_street` | 美国境内 | `ygis_rest_services_Public_PowHUB_Landbase_Laye` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname+roadtype', 'roadname']；不改代码，按样本命中率折算行数 |
| 36 | 14,614 | 14,614 | 1.0000 | `alias_generic_fieldname_layer_scoped` | 美国境内 | `poec_arcgis_rest_services_AddressPoints_view_F` | 层级别名：street=[STR]，number=[STR_NUM]（实测 100%） |
| 37 | 14,389 | 13,141 | 0.9133 | `split_first_row_only` | 美国境内 | `qqHxBiQIog_arcgis_rest_services_Addresses4SG_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 38 | 13,245 | 12,361 | 0.9333 | `split_first_row_only` | 美国境内 | `F2rCsQjt0P3e_arcgis_rest_services_AddressPts_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 39 | 13,235 | 12,352 | 0.9333 | `split_first_row_only` | 美国境内 | `sQjt0P3e_arcgis_rest_services_Address_Points_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 40 | 12,265 | 12,265 | 1.0000 | `alias_missing_street` | 加拿大 | `rxOA_arcgis_rest_services_CivicAddressPoints_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['msagroute']；不改代码，按样本命中率折算行数 |
| 41 | 12,501 | 12,167 | 0.9733 | `alias_missing_street` | 美国境内 | `icQLS_arcgis_rest_services_Address_GSPJ_view_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['stnameps']；不改代码，按样本命中率折算行数 |
| 42 | 12,386 | 12,138 | 0.9800 | `alias_missing_street` | 美国境内 | `est_services_BaseLayers_Address_Access_Point_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname', 'roadname+roadtype']；不改代码，按样本命中率折算行数 |
| 43 | 11,919 | 11,919 | 1.0000 | `alias_missing_street` | 加拿大 | `t_services_AC_CivicAddressPoints_Sept14_2021_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['msagroute']；不改代码，按样本命中率折算行数 |
| 44 | 10,000 | 9,800 | 0.9800 | `alias_missing_street` | 加拿大 | `OQp_arcgis_rest_services_Vancouver_Addresses_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['stdstreet']；不改代码，按样本命中率折算行数 |
| 45 | 7,252 | 7,058 | 0.9733 | `split_first_row_only` | 美国境内 | `is_rest_services_AV_Parcels_2019_Address_PTS_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 46 | 6,981 | 6,981 | 1.0000 | `alias_missing_street` | 美国境内 | `arcgis_rest_services_VOC_Address_Points_view_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['propstreet+propsuffix', 'propstreet']；不改代码，按样本命中率折算行数 |
| 47 | 5,942 | 5,942 | 1.0000 | `alias_missing_street` | 加拿大 | `est_services_dlcsde_spatial_cadAddressPoints_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['civicstreet']；不改代码，按样本命中率折算行数 |
| 48 | 6,669 | 5,157 | 0.8267 | `alias_missing_street` | 美国境内 | `IO5iK52h_arcgis_rest_services_Address_Points_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['sitestreet']；不改代码，按样本命中率折算行数 |
| 49 | 17,698 | 3,185 | 0.1800 | `derived_geocoder_output` | 美国境内 | `YSp_arcgis_rest_services_Address_type_points_F` | 补别名 street_derived/street_raw 并走 split；只救 ~18% 行，且需过滤 '<Null>' 占位 |
| 50 | 2,095 | 2,095 | 1.0000 | `alias_missing_street` | 境外(geo) | `F_arcgis_rest_services_DiamondVale_Addresses_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['streettho']；不改代码，按样本命中率折算行数 |
| 51 | 1,347 | 1,293 | 1.0000 | `alias_missing_street` | 美国境内 | `_rest_services_Address_Points_Very_High_Fire_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname', 'roadname+roadsuffixdir']；不改代码，按样本命中率折算行数 |
| 52 | 6,880 | 734 | 0.1067 | `alias_missing_street` | 境外(geo) | `est_services_Address_points_black_Feb2019MXD_F` | 补 combined 别名 addr_full（走 split）；预计只救 ~11% 行，剩余需重采 |
| 53 | 622 | 622 | 1.0000 | `alias_missing_street` | 加拿大 | `JuEecY0_arcgis_rest_services_CivicAddressing_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 54 | 369 | 364 | 0.9867 | `split_key_beyond_40` | 美国境内 | `gis_rest_services_STR_October_2023_Addresses_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 55 | 334 | 327 | 0.9800 | `split_first_row_only` | 美国境内 | `s_4213745___ADDRESS_POINT___FIELD_12_18_2025_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |
| 56 | 180 | 180 | 1.0000 | `alias_missing_street` | 美国境内 | `9Xs_arcgis_rest_services_AddressPts_OwensTwp_F` | 最小安全表补 street_aliases: lst_concat（实测 100%，ANUMBER 门牌同时非空 100%） |
| 57 | 41 | 37 | 0.9268 | `alias_missing_street` | 美国境内 | `rest_services_E911_Fire_Water_Sources_Review_F` | registry/dialects.v1.yaml 的 minimal_safe template 补 street_aliases: ['roadname']；不改代码，按样本命中率折算行数 |
| 58 | 3 | 2 | 0.6667 | `split_first_row_only` | 美国境内 | `yFxn_arcgis_rest_services_AddressPointAssign_F` | 修 fm_core.map_row：split 每行都试（去掉 _split_tried 短路）+ 候选键扩到全字段 |

## 6. 覆盖率增益测算

| 情形 | 映射上层数 | 覆盖率 | 过 95%？ |
|---|---|---|---|
| 现状（v2 全量重扫） | 3355 | 94.51% | 否（差 18 层） |
| 只修美国境内 38 层 | 3393 | 95.58% | **是** |
| B 类 58 层全修 | 3413 | 96.14% | **是** |

门禁算式：95% × 3,550 = 3,372.5 → 需要 **3,373 层**，即再上 **18 层**。美国境内可修层已有 **38 层**，是门槛的 2.1 倍。

### 6.1 建议优先修的 18 层（按「可恢复行 × 修法确定性」排序）

排序口径：先按 `est_rows_recoverable` 降序（收益），`alias_missing_street` 与 `split_first_row_only` 都是「改一处、全局生效」的低风险修法，优先；层级别名的 5 层放后面。

| 序 | 层 | in_rows | 可恢复行 | reason | 修法 |
|---|---|---|---|---|---|
| 1 | `gyrE4_arcgis_rest_services_Address_Point_911_Featu` | 222,405 | 222,405 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 2 | `_rest_services_Dauphin_County_Address_Points_Featu` | 116,889 | 116,889 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 3 | `gis_rest_services_Address_Points_Public_View_Featu` | 115,294 | 99,925 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 4 | `5OXNGFDn_arcgis_rest_services_Address_Points_Featu` | 96,211 | 95,893 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 5 | `v_server_rest_services_Hosted_Address_Points_Featu` | 89,554 | 89,554 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 6 | `Ngd_arcgis_rest_services_Imperial_County_EPL_Featu` | 88,243 | 75,888 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 7 | `_services_Fontana_Parcels_and_Address_Points_Featu` | 77,971 | 70,696 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 8 | `lxcdnZjF_arcgis_rest_services_Voting_Address_Featu` | 50,821 | 44,890 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 9 | `s_rest_services_Address_to_Alley_ID_Matching_Featu` | 41,026 | 38,564 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 10 | `UHl6XumF_arcgis_rest_services_R_AddressPoint_Featu` | 33,337 | 33,337 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 11 | `cgis_rest_services_Address_20Points_20Mark43_Featu` | 31,335 | 31,335 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 12 | `co_columbia_wi_us_server_rest_services_Open_GIS_Ma` | 32,285 | 31,209 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 13 | `gis_rest_services_Parcel_with_addresses_2024_Featu` | 24,885 | 24,718 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 14 | `is_rest_services_AddressesParcelsUtility2024_Featu` | 24,883 | 24,716 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 15 | `_services_BaseMap_Parcels_Addresses_Boundary_Featu` | 24,883 | 24,716 | `split_first_row_only` | 组合串可拆，但 map_row 只在首行试一次就永久放弃 |
| 16 | `fbh5z_arcgis_rest_services_Code_Address_Data_Featu` | 22,853 | 22,853 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |
| 17 | `S7cpxnJP_arcgis_rest_services_Address_Points_Featu` | 20,192 | 20,192 | `alias_generic_fieldname_layer_scoped` | 地址在字段名过泛的列里（只能层级别名） |
| 18 | `c71b3d4712db5c4e6a2_rest_services_Accela_Accela_Ma` | 19,544 | 19,544 | `alias_missing_street` | 街名/街型字段不在角色表（补别名即可） |

这 18 层合计可恢复 **1,087,324 行**（占美国境内 B 类可恢复行的 86.4%）；这 18 层全部落地即 ≥ 95.00%（实际只需其中任意 18 层中的全部，即总数达到 3,373 层）。

其中**改一处别名表就能救的**（不需要碰代码）：

- 美国境内 `alias_missing_street` 共 22 层，合计 916,694 行；这批只需要在 `registry/dialects.v1.yaml` 加 `street_aliases` 条目。
- 美国境内 `split_first_row_only` 共 12 层，合计 302,770 行；只需改 `fm_core.map_row` 一处短路。

## 7. A 类分桶证据（136 层）

| reason_code | 层数 | 典型判别证据 |
|---|---|---|
| `non_us_point_or_poi` | 45 | 40+ 个奥地利萨尔茨堡「最近 X 到我的地址」服务层（1–3 行）、印尼文化点（`Nama_Situs`）、爱沙尼亚避难所等；字段是场所名/结果表 |
| `admin_or_survey_table` | 21 | Survey123 表单（`first_and_last_name`/`email`/`organization`）、PSAP 部署点、911 收费表、报表；要素不是地址 |
| `no_street_field` | 16 | 只有门牌（`HOUSE_NUM`/`AddNum`/`CIVNUM`/`AddressNo`/`HOUSE_NUMBER`），源里没有街名列、也没有可拆串 |
| `label_or_annotation_only` | 14 | `LABEL`/`TextString`/`Contents`/`Shape` 注记层，值多为纯门牌 |
| `not_address_layer` | 14 | CAD/DXF 元数据（`DocName`/`Linetype`/`Layer`）、学生统计、绿化树种、POI 点位等 |
| `addr_attrs_not_collected` | 11 | 层名就是 Address/Address Points，但落盘 raw 只剩 `OBJECTID`/`*_pid`/`lga_code`/`BUILDING_ID` 等 ID + 经纬度 → 需重采 |
| `non_us_dataset_no_usable_field` | 6 | 捷克/荷兰/塞浦路斯/黎巴嫩数据集，字段是本国门牌体系，不合美国口径 |
| `grid_range_no_street_name` | 5 | `ADD_NS`/`ADD_EW`/`ADD_RANGE`/`Range` 网格区间，16,800N × 24,600E 这种交叉编号，没有街名 |
| `street_field_all_null` | 2 | 街名列在角色表里（`St_Name`/`SN`/`STREET_ID`）但样本全空 |
| `intersection_no_number` | 1 | `loc = "Brigantine Dr & Fall Creek Rd"` 路口名，无门牌 |
| `unparseable_concat` | 1 | `ADDRESS = "32181LN"` 门牌+步道号无分隔 |

需要提醒的一点：A 类里有 **11 层 `addr_attrs_not_collected` 合计 18,777,313 行**（含 15.06M 行的 `EXP_national_address_points`、2.28M 行的爱尔兰 GeoDirectory、1.19M 行的 `County_37_LBRS_Addresses`）。这些层**名字都是地址层**，但落盘 payload 里没有地址属性——这不是映射侧能修的，属**采集侧字段缺失**，要重采才救得回来（本单红线不允许重采）。若 muse 要按「可采到的地址层」重算分母，这批层才是争议点，而不是 B 类。

## 8. 附带发现（不在本单任务内，供裁定参考）

1. **角色表把 `firstname` / `lastname` / `fullname` 当 street 别名**（`roles_of()` 结果里 street 组含这三项）。方向相反的 bug：任何带「姓名字段」的层，都可能把**人名**当街名写进 `street_name` 并落 grade C。本单的 `123_69927fe3de7343b4b5f3dca25d6a16d9_results`（Survey123 表单）就是被这条误判成「可修 B」，人工复核时按「人名不是地址」压回 A。**建议另行核查已入库数据里是否有人名当街名的行**（本单只查不改，未做该统计）。
2. `unusable-v2.csv` 里按 `dropped_below_c` 排序，前几名其实是**非地址层或采集缺字段**（澳洲地址点 15.06M、爱尔兰 GeoDirectory 2.28M、County_37_LBRS 1.19M），拿「丢弃行数」当质量指标会误导——真正的判别依据是「层里有没有街名/门牌字段」。
3. 40 键上限与首行短路是**同一个函数里的两个独立缺陷**，只修一个都救不全 14 层。

## 9. 未闭环项与短板（如实写）

1. **采样口径**：每层只抽 300 行（单 part 文件的层 150 行），`est_rows_recoverable` 是「样本命中率 × in_rows」的线性外推，未按分层/分段抽样。对 15.06M 行那种层若样本不代表全层，误差可能较大——但那些层都在 A 类（0 命中），不影响 B 类的结论。
2. **未实跑修复**：三种修法都是「模拟 + 实测样本命中率」，**没有真正改代码/改别名表后重跑映射**（本单红线只查不改）。96.14% / 95.58% 是测算值，落地后需再用一轮全量重扫复核。
3. **口径归属是推断**：美国境内/境外是用「经纬度中位数 + 层名关键词」判的（`geo_median` + 关键词表）。境外 20 层 B 里有 3 层标成「境外(geo)」（Coquitlam 的另一层、Yellowknife 旁、特立尼达），具体国别未逐个确认；但它们在两种口径下都不计入 95% 的美国境内测算。
4. **UNKNOWN 只有 1 层**（xjrB05UV_arcgis_rest_services_Riv_Co_Address_FeatureServer_0：整层 3 行、地址列全空）。理论上还有「字段名像地址但样本全空」的层可能被规则判进 A（本文 A 类 `street_field_all_null` 2 层即此形态），这类若源侧其实有值，会被低估——需重采或看源服务字段定义才能确认。
5. **未做跨层去重**：不同层之间是同一份数据的镜像（例：`7088d1ef…` / `st_services_Hundred_Block…` / `_gov_arcgis1_…` 三层同为 251,245 行的百街区网格；Pompano Beach 三层同为 24,883 行）。A/B 计数按层算，因此这些镜像层会各自计一次；对覆盖率口径是正确行为，对「数据量」会重复计。

## 10. 复跑

```bash
cd /data/workspace/wmd-fieldmap/analysis/fieldmap-20261125/unmapped-20261126
python3 scan_unmapped.py --rows 150      # ~17s，写 layers-evidence.jsonl
python3 simulate_fix.py --rows 150       # ~10s，写 fix-simulation.jsonl
python3 measure_layer_scoped.py          # ~2s，写 layer-scoped-fixes.jsonl
python3 classify_unmapped.py             # 写 unmapped-classification.csv + overrides-resolved.json
python3 make_report.py                   # 写 REPORT-unmapped.md
```

边界：只读 `dist/intake-full/layers/`、`analysis/fieldmap-20261125/layer-coverage.v2.csv`、`unusable-v2.csv`；只写本目录。`INTAKE_LAYERS` 可换根做旁证，默认不动源。
