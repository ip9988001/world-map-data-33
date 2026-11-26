# fix58 · 58 层 B 类修复落地报告（muse-000271）

> 生成物由脚本合成（`make_fix58.py` + `build_report.py`），数字全部取自 `fix58-summary.json` / `fix58-before-after.csv` / 各 `*-b58.jsonl`、`*-affected.jsonl`、`*-regression.jsonl`。口径：只跑 58 层 + 回归抽样，**未做全量重扫**，因此 `REPORT-v2.md` / `SUMMARY-v2.json` 本轮只打 provisional 标记，历史结论数字一个都没改。

## 0. 结论

- 58 层 **全部上映射**（`layers_mapped_after = 58/58`，`layers_still_zero = 0`），逐层闭合差额 0、`bad_empty = 0`、`bad_grade = 0`。
- 新覆盖率 **96.14%**（3413/3550）→ 95% 门禁（需 3373 层）**通过**，且达到测算的 96.14%。
- 可恢复行实得 **3,199,912** 行（报告 §6 测算 3,192,659 行，差 +7,253）。
- 回归：新别名命中集 **615 层全量 A/B**，行数下降的层 **0 层**；未命中集分层抽样 **236 层 / 8,661,332 行**（52 个州/地区），行数下降 **0 层**。
- 唯一没到「零」的指标：`zero_coord = 2` 行（2 层各 1 行），原因是源里坐标本身就是空/`0,0`，映射侧按 muse-000266 口径拒写 `(0,0)`，非映射缺陷。

## 1. 起点核对

- 起点 HEAD = `4c3a6a324858d7d14efc2edb35331b0924be6764`（= PR #58 当时 head），分支 `feat/fieldmap-20261125`，工作树干净。
- `unmapped-classification.csv` 里 `class==B` 正好 58 行，reason 分桶 = `alias_missing_street 38 / split_first_row_only 13 / alias_generic_fieldname_layer_scoped 5 / split_key_beyond_40 1 / derived_geocoder_output 1`，与派单一致。
- 磁盘 free 全程 30G+（护栏 8G 未触发）；无并行映射进程。

## 2. 三处修复

### 2.1 修 1 · 角色表补街名别名（全局，弱源）

`registry/dialects.v1.yaml` 新增**一个别名扩展方言条目** `fix58-alias-ext-v1`（35 条 street + 2 条 number），**没有改动任何既有方言的 template / 别名**（该表里本来就没有 `id: minimal_safe` 的实体条目，`minimal_safe` 是 fallback，角色表由 `roles_of()` 把所有方言的 template 并集而成，所以「补 minimal_safe template」的等价做法就是追加一个 `alias_extension` 条目 —— 与既有 `p7-alias-ext-v1` 同构）。
- 关键设计：新别名标记 `alias_strength: weak`，**只在「强别名与组合串拆分都没给出」时兜底**。第一版把新别名放在拆分之前，回归专项查出 4 层 grade 退化（新别名先把 street 填成不完整街名，把原本靠拆 `FULL_ADDRE` 拿到「门牌+完整街名」(grade A) 的行压成 grade C），改弱源后这 4 层与旧版逐行一致。
- `firstname` / `lastname` / `fullname` 一条没动（仍是既有 street 别名，本轮未触碰）；`NAME` / `TYPE` / `STR` / `PARCEL_LOC` **未进全局表**，只做层级别名；`lst_concat` 按报告 §5 #56 明示入全局表。
- 每条别名的层号出处写在 YAML 行内注释里（= `REPORT-unmapped.md` §5 表行号），回归会逐个别名统计命中层数（见 §5.3）。

### 2.2 修 2 · `map_row` 组合串拆分（`fm_core.py`）

- 去掉 `not (self._split_tried and not self._split_key)` 短路 → 每行都试；`cand_keys` 从 `list(raw.keys())[:40]` 扩到**全部字段**（`_split_key` 命中后仍只试那一列并即时跳出，保证既有层的行为与耗时不变）。
- 性能：拆分分支只在 `street` 为空时进入；已经映射上的行 `street` 非空 → 不进入，因此既有层耗时不变。最坏情形（这 58 层本身）4 层 A/B 实测：改前 **14.589 s** → 改后 **28.344 s**（**1.94×**，未超 3× 红线；`4 层（SECTO_NBI 530,776 行 / Address_Points_Public_View 115,294 行 / Fontana 77,971 行 / F2rCsQjt0P3e 13,245 行），--workers 4，不写输出行`）。优化措施（不改语义）：`_split_key` 命中后该层只试那一列并即时 `break`。
- 最小复现（脚本现场复算，非手抄）：层 `F2rCsQjt0P3e_arcgis_rest_services_AddressPts_FeatureServer_0`；该层真实首行 raw 的 `LABEL = '3358 K 157 HWY'`（正是 `split_number_street` 判 `ambiguous` 的那条 → 老代码首行就把它置成「整层不再试」）。

| 行 | 改前 | 改后 |
|---|---|---|
| 第 1 行 `3358 K 157 HWY` | below_c    | below_c    |
| 第 2 行 `1952 SWENSON RD` | below_c    | mapped 1952 SWENSON RD A |

> 该层实测：改前 0 行、改后 13,163 / 13,245 行。

### 2.3 修 3 · 层级别名 + 地理编码残留层

新增 `registry/layer-aliases.v1.yaml`（与 `dialects.v1.yaml` 同族、同级），按 `layer_id`/`url` 精确匹配，只对 7 层生效（5 层过泛字段名 + LST_CONCAT 登记 + 地理编码残留层），语义为：
- `street_fields` / `number_fields`：**弱源**，只在原生/强别名/拆分都没给出时按声明顺序拼接（`NAME+TYPE` → `Northview Road`；`STR`+`STR_NUM`）。
- `split_fields` / `drop_values`：`YSp_...Address_type_points`（`derived_geocoder_output`）把 `Street_derived/Street_raw` 排到拆分候选最前，并把 `'<Null>'` 作为该层专属占位值过滤掉 —— 实测只救回 18% 行（27/150 样本可拆），如实报，**没有**把 `'<Null>'` 当街名写进数据。

## 3. 58 层逐层结果

| # | 层 | in_rows | 修前 | 修后 | 修后 grade | reason | 闭合差额 |
|---|---|---|---|---|---|---|---|
| 1 | `shlD6Twu_arcgis_rest_services_Street_Address_F` | 519,819 | 0 | 519,819 | S:0/A:0/B:0/C:519819 | alias_missing_street | 0 |
| 2 | `est_services_BASE_BASE_NS_CivicAddress_File_UT` | 485,466 | 0 | 485,466 | S:0/A:0/B:0/C:485466 | alias_missing_street | 0 |
| 3 | `gyrE4_arcgis_rest_services_Address_Point_911_F` | 222,405 | 0 | 222,405 | S:0/A:0/B:0/C:222405 | alias_missing_street | 0 |
| 4 | `vt_nz_server_rest_services_OpenData_Property_F` | 209,057 | 0 | 209,057 | S:0/A:0/B:0/C:209057 | alias_missing_street | 0 |
| 5 | `s_com_arcgis_rest_services_GIS_App_GIS_App_BAS` | 117,540 | 0 | 117,537 | S:0/A:0/B:0/C:117537 | alias_generic_fieldname_layer_scoped | 0 |
| 6 | `_rest_services_Dauphin_County_Address_Points_F` | 116,889 | 0 | 116,889 | S:0/A:0/B:0/C:116889 | alias_missing_street | 0 |
| 7 | `gis_rest_services_Address_Points_Public_View_F` | 115,294 | 0 | 111,141 | S:0/A:0/B:0/C:111141 | split_first_row_only | 0 |
| 8 | `5OXNGFDn_arcgis_rest_services_Address_Points_F` | 96,211 | 0 | 95,958 | S:0/A:0/B:0/C:95958 | alias_missing_street | 0 |
| 9 | `v_server_rest_services_Hosted_Address_Points_F` | 89,554 | 0 | 89,554 | S:0/A:83121/B:0/C:6433 | alias_missing_street | 0 |
| 10 | `nH5x_arcgis_rest_services_Address__Elections_F` | 84,437 | 0 | 84,436 | S:0/A:0/B:0/C:84436 | alias_generic_fieldname_layer_scoped | 0 |
| 11 | `land_ca_server_rest_services_civic_addresses_F` | 82,901 | 0 | 82,901 | S:0/A:0/B:0/C:82901 | alias_missing_street | 0 |
| 12 | `Ngd_arcgis_rest_services_Imperial_County_EPL_F` | 88,243 | 0 | 79,319 | S:0/A:0/B:0/C:79319 | alias_missing_street | 0 |
| 13 | `_services_Fontana_Parcels_and_Address_Points_F` | 77,971 | 0 | 76,100 | S:0/A:3/B:0/C:76097 | alias_missing_street | 0 |
| 14 | `QdwKY6yp_arcgis_rest_services_Search_Address_F` | 74,449 | 0 | 74,449 | S:0/A:0/B:0/C:74449 | alias_missing_street | 0 |
| 15 | `arcgis_rest_services_CB_Civic_Addresses_WFL1_F` | 73,856 | 0 | 73,856 | S:0/A:0/B:0/C:73856 | alias_missing_street | 0 |
| 16 | `_rest_services_SECTO_NBI_MASTER_ADDRESS_LIST_F` | 530,776 | 0 | 69,920 | S:0/A:0/B:0/C:69920 | split_first_row_only | 0 |
| 17 | `LNJBeDlAk_arcgis_rest_services_All_Addresses_F` | 56,431 | 0 | 56,431 | S:0/A:0/B:0/C:56431 | alias_missing_street | 0 |
| 18 | `lxcdnZjF_arcgis_rest_services_Voting_Address_F` | 50,821 | 0 | 46,338 | S:0/A:0/B:0/C:46338 | split_first_row_only | 0 |
| 19 | `s_rest_services_Address_to_Alley_ID_Matching_F` | 41,026 | 0 | 41,009 | S:0/A:0/B:0/C:41009 | split_first_row_only | 0 |
| 20 | `KtMulHM03_arcgis_rest_services_Address_Point_F` | 41,533 | 0 | 39,940 | S:0/A:0/B:0/C:39940 | alias_missing_street | 0 |
| 21 | `UHl6XumF_arcgis_rest_services_R_AddressPoint_F` | 33,337 | 0 | 33,337 | S:0/A:0/B:0/C:33337 | alias_missing_street | 0 |
| 22 | `co_columbia_wi_us_server_rest_services_Open_GI` | 32,285 | 0 | 32,285 | S:0/A:32285/B:0/C:0 | alias_missing_street | 0 |
| 23 | `qvET_arcgis_rest_services_Address_Points_GSY_F` | 31,680 | 0 | 31,597 | S:0/A:0/B:0/C:31597 | alias_missing_street | 0 |
| 24 | `cgis_rest_services_Address_20Points_20Mark43_F` | 31,335 | 0 | 31,335 | S:0/A:31332/B:2/C:1 | alias_missing_street | 0 |
| 25 | `gis_rest_services_Parcel_with_addresses_2024_F` | 24,885 | 0 | 24,135 | S:0/A:0/B:0/C:24135 | split_first_row_only | 0 |
| 26 | `is_rest_services_AddressesParcelsUtility2024_F` | 24,883 | 0 | 24,133 | S:0/A:0/B:0/C:24133 | split_first_row_only | 0 |
| 27 | `_services_BaseMap_Parcels_Addresses_Boundary_F` | 24,883 | 0 | 24,133 | S:0/A:0/B:0/C:24133 | split_first_row_only | 0 |
| 28 | `fbh5z_arcgis_rest_services_Code_Address_Data_F` | 22,853 | 0 | 22,852 | S:0/A:0/B:0/C:22852 | alias_missing_street | 0 |
| 29 | `S7cpxnJP_arcgis_rest_services_Address_Points_F` | 20,192 | 0 | 20,192 | S:0/A:0/B:0/C:20192 | alias_generic_fieldname_layer_scoped | 0 |
| 30 | `c71b3d4712db5c4e6a2_rest_services_Accela_Accel` | 19,544 | 0 | 19,229 | S:0/A:0/B:0/C:19229 | alias_missing_street | 0 |
| 31 | `18b4b78b270efb1_rest_services_Accela_Accela_Fe` | 19,544 | 0 | 19,229 | S:0/A:0/B:0/C:19229 | alias_missing_street | 0 |
| 32 | `city_ca_arcgis_rest_services_Public_OpenData_F` | 18,254 | 0 | 18,254 | S:0/A:0/B:0/C:18254 | alias_generic_fieldname_layer_scoped | 0 |
| 33 | `rcgis_rest_services_Address_Points_Only_WFL1_F` | 17,440 | 0 | 17,419 | S:0/A:0/B:0/C:17419 | alias_missing_street | 0 |
| 34 | `luOy5R3S_arcgis_rest_services_ADDRESS_POINTS_F` | 16,416 | 0 | 16,415 | S:0/A:0/B:0/C:16415 | alias_missing_street | 0 |
| 35 | `ygis_rest_services_Public_PowHUB_Landbase_Laye` | 15,738 | 0 | 15,738 | S:15738/A:0/B:0/C:0 | alias_missing_street | 0 |
| 36 | `poec_arcgis_rest_services_AddressPoints_view_F` | 14,614 | 0 | 14,614 | S:0/A:0/B:0/C:14614 | alias_generic_fieldname_layer_scoped | 0 |
| 37 | `YSp_arcgis_rest_services_Address_type_points_F` | 17,698 | 0 | 14,502 | S:0/A:0/B:0/C:14502 | derived_geocoder_output | 0 |
| 38 | `F2rCsQjt0P3e_arcgis_rest_services_AddressPts_F` | 13,245 | 0 | 13,163 | S:0/A:13163/B:0/C:0 | split_first_row_only | 0 |
| 39 | `sQjt0P3e_arcgis_rest_services_Address_Points_F` | 13,235 | 0 | 13,154 | S:0/A:13154/B:0/C:0 | split_first_row_only | 0 |
| 40 | `icQLS_arcgis_rest_services_Address_GSPJ_view_F` | 12,501 | 0 | 12,474 | S:0/A:0/B:0/C:12474 | alias_missing_street | 0 |
| 41 | `est_services_BaseLayers_Address_Access_Point_F` | 12,386 | 0 | 12,381 | S:0/A:0/B:0/C:12381 | alias_missing_street | 0 |
| 42 | `rxOA_arcgis_rest_services_CivicAddressPoints_F` | 12,265 | 0 | 12,256 | S:0/A:0/B:0/C:12256 | alias_missing_street | 0 |
| 43 | `t_services_AC_CivicAddressPoints_Sept14_2021_F` | 11,919 | 0 | 11,915 | S:0/A:0/B:0/C:11915 | alias_missing_street | 0 |
| 44 | `qqHxBiQIog_arcgis_rest_services_Addresses4SG_F` | 14,389 | 0 | 11,532 | S:0/A:11527/B:0/C:5 | split_first_row_only | 0 |
| 45 | `OQp_arcgis_rest_services_Vancouver_Addresses_F` | 10,000 | 0 | 9,882 | S:0/A:0/B:0/C:9882 | alias_missing_street | 0 |
| 46 | `arcgis_rest_services_VOC_Address_Points_view_F` | 6,981 | 0 | 6,981 | S:0/A:0/B:0/C:6981 | alias_missing_street | 0 |
| 47 | `is_rest_services_AV_Parcels_2019_Address_PTS_F` | 7,252 | 0 | 6,693 | S:0/A:6693/B:0/C:0 | split_first_row_only | 0 |
| 48 | `IO5iK52h_arcgis_rest_services_Address_Points_F` | 6,669 | 0 | 6,113 | S:0/A:0/B:0/C:6113 | alias_missing_street | 0 |
| 49 | `est_services_dlcsde_spatial_cadAddressPoints_F` | 5,942 | 0 | 5,941 | S:0/A:0/B:0/C:5941 | alias_missing_street | 0 |
| 50 | `F_arcgis_rest_services_DiamondVale_Addresses_F` | 2,095 | 0 | 2,095 | S:0/A:0/B:0/C:2095 | alias_missing_street | 0 |
| 51 | `_rest_services_Address_Points_Very_High_Fire_F` | 1,347 | 0 | 1,347 | S:0/A:1345/B:0/C:2 | alias_missing_street | 0 |
| 52 | `JuEecY0_arcgis_rest_services_CivicAddressing_F` | 622 | 0 | 588 | S:0/A:0/B:0/C:588 | alias_missing_street | 0 |
| 53 | `est_services_Address_points_black_Feb2019MXD_F` | 6,880 | 0 | 555 | S:0/A:0/B:0/C:555 | alias_missing_street | 0 |
| 54 | `gis_rest_services_STR_October_2023_Addresses_F` | 369 | 0 | 367 | S:0/A:0/B:0/C:367 | split_key_beyond_40 | 0 |
| 55 | `s_4213745___ADDRESS_POINT___FIELD_12_18_2025_F` | 334 | 0 | 330 | S:0/A:0/B:0/C:330 | split_first_row_only | 0 |
| 56 | `9Xs_arcgis_rest_services_AddressPts_OwensTwp_F` | 180 | 0 | 180 | S:0/A:0/B:0/C:180 | alias_missing_street | 0 |
| 57 | `rest_services_E911_Fire_Water_Sources_Review_F` | 41 | 0 | 39 | S:0/A:0/B:0/C:39 | alias_missing_street | 0 |
| 58 | `yFxn_arcgis_rest_services_AddressPointAssign_F` | 3 | 0 | 2 | S:0/A:0/B:0/C:2 | split_first_row_only | 0 |

合计：in_rows **3,698,915**、修后 mapped **3,199,912**、`dropped_below_c` **499,003**、`parse_error` **0**；逐层 `closed_diff` 为 0 的层数 = 58/58。
修前口径交叉校验：58 层在 `layer-coverage.v2.csv` 里的 `mapped` 全为 0，且 `in_rows` 与本次 before 跑完全一致（不一致层数 = 0）。

## 4. 覆盖率

| 口径 | 映射上层数 | 覆盖率 | 过 95% 门禁 |
|---|---|---|---|
| v2 全量重扫（修前） | 3,355 | 94.51% | 否（差 18 层） |
| 本轮（58 层落地） | 3,413 | **96.14%** | 是（需 3,373 层） |

> 注意：分子的 3,413 = 3,355（v2 已映射）+ 58（本轮全部上映射），**不含**未在此轮重跑的任何层。分母 3,550 不变。

## 5. 回归证据（未做全量重扫 —— 明确声明）

全量重扫口径下 3,550 层=5.1 亿行、上次实测 247 分钟（`fullrescan-run.json`），本轮时间盒内跑不完，因此回归证据由两部分组成，**都不是抽样糊弄**：

### 5.1 新别名命中集：全量 A/B（不是抽样）

- 用 `rows-census.jsonl`（3,550 层逐层 raw 字段名并集，只读每个 part 文件首行）穷举出「raw 里含本轮任一新增别名」的层：**615 层**。
- 对这 615 层做 before/after 双跑（before = 起点提交的 `fm_core.py` + 同提交 `dialects.v1.yaml`）：行数下降 **0 层**；行数增加 206 层、共 **+2,649,086 行**；mapped 总量 63,404,997 → 66,054,083。
- 其中 23 层「行数不变但取值变了」，逐层核对后**全部是新增门牌**（`STR_NUM`/`CIVIC_NUM` 两个新门牌别名把 `house_number` 从空补上，grade 只升不降）：grade 净变差的层 **0 层**。
- 超大局 `conemap_gov_secure_rest_services_NC1Map_Location_MapServer_0`（4,206 万行、844 个 part）单独抽检前 25 个 part（1,250,000 行）：before/after 完全一致（mapped、grade、street/addrkey 哈希全同）。

### 5.2 未命中集分层抽样 A/B

- 样本 **236 层 / 8,661,332 行**，覆盖 **52 个州/地区代码**（含空状态码 5 层），`source_layer_kind` 三类全覆盖（url / layer_id_fallback / n/a）；origination 类型：v2 的 3,550 层 `dialect_origin` 全是 `fallback`（`dialect_id` 全为 `minimal_safe`），即只有 1 种类型，抽样自然全覆盖。
- `in_rows ≤ 400k` 控时；样本里 126 层是「有 dropped_below_c > 0」的层（split 修复唯一可能动到的那类，抽样时每州优先入选）。
- 结果：行数下降 **0 层**；行数增加 16 层（+9,942 行，同样是拆串救回的丢弃行）；取值变动 **0 层**；`bad_empty` 合计 0。

### 5.3 逐别名命中层数（= 误伤面）

见 `fix58-summary.json:regression.alias_hit_census.value_changed_detail` 与 `rows-census.jsonl`；按别名统计的命中层数：

```
别名                 命中层数
roadname                216
strname                 135
roadtype                116
strtype                 106
addrsn                   72
featyp                   42
strnum                   41
strsuffix                39
fullstnm                 31
feanme                   11
civicnum                 11
lstconcat                10
sfeanme                   8
sfeatyp                   8
sitestreet                7
roadnamesuffix            4
locstnam                  4
propstreet                4
streetnm                  3
sitestreetname            3
strsuf                    2
thoroughfare              2
msagroute                 2
civicstreet               2
gcstname                  1
ostreetnm                 1
addressroadname           1
roadnm                    1
roadsuffixdir             1
streetdescription         1
thorofare                 1
landbasedbotblstreetnamesstr      1
locstsuf                  1
stnameps                  1
stdstreet                 1
propsuffix                1
streettho                 1
```

## 6. 新别名误伤专项结论

- **行数下降的层：0 层**（命中集全量 615 层 + 抽检 236 层 + 超大局抽检，全部为 0）。
- 取值变化只发生在「新增门牌别名补空」这一种情形，且 grade 净变差 0 层；第一版弱/强顺序错导致的 4 层 grade 退化已在落地前发现并修掉（见 §2.1）。
- 遗留的小瑕疵（如实报，不在本单修）：`STR_NUM` 这类字段在源里是 JSON 数字时，`house_number` 会写成 `1009.0` 这种带 `.0` 的形式（既有 `clean_number()` 的老行为，对既有层影响一致）。改它会动到既有 3,355 层的取值，超出本单红线，留作后续单。

## 7. 未闭环项与短板

1. **未做全量重扫**：覆盖率 96.14% 是「3,355 + 58」的算术结果，58 层的行数是本轮实跑，已映射的 3,355 层沿用 v2 口径未重跑。`REPORT-v2.md` / `SUMMARY-v2.json` 已标 provisional。
2. `zero_coord = 2` 行（Dauphin 1 行、rxOA 1 行）：源坐标缺失/`0,0`，按 muse-000266 口径拒写，非缺陷。
3. 拆分命中率与报告估算有偏差（有的层高于估算，如 `BASE_NS_CivicAddress` 85.3%→100%、`shlD6Twu` 78.3%→100%；有的低于估算，如爱尔兰 `SECTO_NBI` 57%→13.2%），报告 §5 的命中率是 150–300 行样本外推，本轮给出的是**整层实跑**。
4. 报告 §9 已写的口径问题照旧：境外 20 层里 3 层国别仍未逐个确认；跨层镜像数据按层计（覆盖率口径正确）。
5. 层级别名是「按层硬编码」，长期应推广成「按 org/模板自动推断」，本单只按报告 §4.3 的 6 层 + 1 层落地。

## 8. 复跑

```bash
cd analysis/fieldmap-20261125/fix58-20261126
python3 run_fix58.py --mode before --jobs jobs-b58.jsonl --out before-b58.jsonl   # 31 s
python3 run_fix58.py --mode after  --jobs jobs-b58.jsonl --out after-b58.jsonl --write-rows /data/scratch/fix58-20261126  # 88 s
python3 census.py --out rows-census.jsonl                                         # 4 s（3,550 层字段名并集）
python3 run_fix58.py --mode before --jobs jobs-affected.jsonl --out before-affected.jsonl      # 40 min（含 4,206 万行的层，已单独抽检替代）
python3 run_fix58.py --mode after  --jobs jobs-affected.jsonl --out after-affected.jsonl       # 23 min
python3 select_regression.py   # → jobs-regression.jsonl（236 层 / 8.66M 行）
python3 run_fix58.py --mode before --jobs jobs-regression.jsonl --out before-regression.jsonl  # 2m48s
python3 run_fix58.py --mode after  --jobs jobs-regression.jsonl --out after-regression.jsonl   # 2m51s
python3 make_fix58.py   # → fix58-before-after.csv + fix58-summary.json
python3 build_report.py # → REPORT-fix58.md + REPORT-v2/SUMMARY-v2 的 provisional 标记
```

边界：只读 `dist/intake-full/layers/`、`layer-coverage.v2.csv`；基线代码/别名表用 `git show 4c3a6a3:…` 取到 `/data/scratch/fix58-baseline/`（**不进仓库**）；输出行只写到 `/data/scratch/fix58-20261126/`。
## 9. 产物清单（字节数=写本报告时现场 stat）

| 文件 | 字节 | 用途 |
|---|---|---|
| `after-affected.jsonl` | 281,334 | 新别名命中集 615 层 after |
| `after-b58.jsonl` | 26,098 | 58 层 after 逐层统计（含 street/addrkey 哈希） |
| `after-miss-partial.jsonl` | 467 | 同上 after |
| `after-regression.jsonl` | 108,268 | 抽样回归 236 层 after |
| `before-affected.jsonl` | 270,744 | 新别名命中集 615 层 before |
| `before-b58.jsonl` | 25,296 | 58 层 before（4c3a6a3 基线代码）逐层统计 |
| `before-miss-partial.jsonl` | 467 | 4,206 万行的 conemap 层前 25 part 抽检 before |
| `before-regression.jsonl` | 108,247 | 抽样回归 236 层 before |
| `build_report.py` | 23,365 | 生成本报告 + v2 的 provisional 标记 |
| `census.py` | 4,880 | 字段名并集普查 |
| `fix58-before-after.csv` | 8,362 | 58 层逐层 before/after（派单要求的 11 列） |
| `fix58-summary.json` | 10,567 | 58 层验收 + 覆盖率 + 回归证据汇总（机器可读） |
| `jobs-affected.jsonl` | 140,985 | 616 层新别名命中清单 |
| `jobs-b58.jsonl` | 15,153 | 58 层作业清单（layer_id/url/reason） |
| `jobs-regression.jsonl` | 62,672 | 236 层抽样清单 |
| `make_fix58.py` | 10,918 | 汇总 CSV/JSON |
| `perf-ab.json` | 502 | 拆分修复的性能 A/B（4 层，1.94×） |
| `rows-census.jsonl` | 2,484,717 | 3,550 层 raw 字段名并集 + 州代理值（回归取面用） |
| `run_fix58.py` | 9,054 | before/after 双跑器 |
| `select_regression.py` | 4,126 | 分层抽样选择器 |
| `REPORT-fix58.md` | 本文件（脚本生成） | 人读报告 |

