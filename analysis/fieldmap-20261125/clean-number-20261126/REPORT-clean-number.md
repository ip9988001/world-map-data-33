# REPORT · house_number `x.0` 浮点整形（muse-000275）

> 脚本合成（`scan_dirty.py` → `scope.py` → `rerun_scope.py` → `verify.py` → 本文件），数字全部取自 `verify-20.json` / `verify-summary.json` / `scope.jsonl`，无手抄。

## 0. 结论

- 清单内 **20 层**（51,290,901 行）重跑后，`house_number` 命中 `^\d+\.0+$` 的行数 **1,169,271 → 0**。
- 四项验证：① 脏行归零 **通过**；② 覆盖率仍 3413/3550 = 96.14% **通过**；③ 逐层行数相等、闭合差额 0 **通过**；④ `bad_*`=0 且 grade 分布逐层相同 **通过**。
- 逐行对账：**1,169,271** 条脏行「同一行 before vs after」全部只差 `.0` 被吃掉（**mismatch = 0**），另有 1,000 行随机抽查 **mismatch = 0**。
- 非零小数（口径要求原样保留）：**981 行**保持原值不变（before 981 = after 981）。

## 1. 范围（先落盘再动手）

- 扫**真实产物**：`dist-v2/tar/*.tar.gz`（3,355 层）+ `/data/scratch/fix58-20261126/rows`（58 层）= **3,413 层 / 483,239,197 行**，命中 `^\d+\.0+$` 的层 **20 个**、脏行 **1,169,262**。
- `scope.jsonl` sha256 = `9f495a9697af696d87d0b537380f1bc9b9b1c43ba2af367619442de7029aa26e`，**前 16 位 `9f495a9697af696d`**。
- 来源字段分桶：`{"Address_Number(str)": 1, "HouseNumber": 1, "HOUSE_NO": 1, "addr_housenumber(str)": 3, "add_num(env)": 7, "ADDR_NUM(float)": 1, "STREET_NO": 1, "HOUSE": 1, "NUMBER(float)": 1, "NUMBER_": 1, "AddNum": 1, "Number": 1}`
  说明：脏行**不止**来自 `STR_NUM`/`CIVIC_NUM`，还有 7 层是**信封 `add_num` 本身是 JSON 浮点**，以及 `addr_housenumber` 这类「字符串自带 .0」——所以修在 `clean_number()` 才对。

## 2. 代码改动

`analysis/fieldmap-20261125/fm_core.py:clean_number()`：
```python
m = RX_FLOAT_INT.match(s)          # ^(\d+)\.0+$
if m:
    n = m.group(1)
    return "" if (n.upper() in PLACEHOLDERS or RX_ONLY_SYMBOLS.match(n)) else n   # "0.00" → 占位值
return s
```
- `"1009.0"` / `1009.0`(float) / `" 1009.0 "` / `"1009.00"` → `"1009"`；只改写法不改数值。
- `"1009.5"` → **原样返回**（不四舍五入），只计数（见 §4）。
- **`"0.0"` 返回空串**（占位值优先）：`0`/`0.0`/`000` 是既定占位值，若归一成 `"0"` 就会写出 `house_number="0"` 并把 grade 从 C 抬到 B —— 违反「不改数值/不改分级」与「不碰 placeholder 语义」。故本实现按 2.3 优先，2.1 的示例 `"0.0"→"0"` 未采纳（单测里写明理由，muse 若要反悔只改一行）。
- 不动 `clean_street` / `clean_city`、不动分级与坐标逻辑（单测里有护栏用例）。
- 单测 `analysis/fieldmap-20261125/tests/test_clean_number.py`：6 个必备用例 + 13 个边界 + 幂等 + 「不动街名/城市」护栏；`python3 -m pytest analysis/fieldmap-20261125/tests engine/tests registry/tests -q` → **124 passed**。
- 另修 main 上既有的 3 个红测（gc-019/020/021）：上一轮新增的 golden case 用了上游字段名拼写，而 `registry/evaluator.py` 是按别名**精确拼写**匹配的；改成条目声明的别名拼写，值仍是真实原值，`roles_of()` 归一后别名集合与 main **逐位相同**（185 个名字，集合相等）。

## 3. 改前改后逐层对比

| # | 层 | 来源字段 | in_rows | mapped 前→后 | 脏行 前→后 | grade（前=后） | 闭合差额 |
|---|---|---|---|---|---|---|---|
| 1 | `erycountymd_gov_arcgis_rest_services_General` | `add_num(env)` | 294,680 | 294,680 → 294,680 | 294,680 → **0** | S:0/A:0/B:0/C:294680 | 0 / 0 |
| 2 | `ountymd_gov_arcgis_rest_services_General_BAR` | `add_num(env)` | 294,680 | 294,680 → 294,680 | 294,680 → **0** | S:0/A:0/B:0/C:294680 | 0 / 0 |
| 3 | `land_ca_server_rest_services_civic_addresses` | `STREET_NO` | 82,901 | 82,901 → 82,901 | 82,901 → **0** | S:0/A:0/B:0/C:82901 | 0 / 0 |
| 4 | `v_com_server_rest_services_ACC_Address_Point` | `add_num(env)` | 78,093 | 78,064 → 78,064 | 77,411 → **0** | S:0/A:0/B:77395/C:669 | 0 / 0 |
| 5 | `_gov_host_rest_services_PublicAccess_LandDat` | `add_num(env)` | 73,569 | 73,569 → 73,569 | 73,569 → **0** | S:0/A:0/B:0/C:73569 | 0 / 0 |
| 6 | `rcgis_rest_services_OpenData_General_Referen` | `add_num(env)` | 68,811 | 68,811 → 68,811 | 67,843 → **0** | S:0/A:0/B:67843/C:968 | 0 / 0 |
| 7 | `services_Address_Planning_AddressPoints_Plan` | `add_num(env)` | 56,737 | 56,733 → 56,733 | 56,733 → **0** | S:0/A:56642/B:88/C:3 | 0 / 0 |
| 8 | `countymd_gov_server_rest_services_Public_Pri` | `add_num(env)` | 59,087 | 59,083 → 59,083 | 51,767 → **0** | S:0/A:0/B:0/C:59083 | 0 / 0 |
| 9 | `58c926eb68_rest_services_Public_SiteAddr_Zip` | `HOUSE_NO` | 49,859 | 49,859 → 49,859 | 49,858 → **0** | S:49859/A:0/B:0/C:0 | 0 / 0 |
| 10 | `s_org_server_rest_services_JCAdmin_SITUS_Sta` | `Number` | 43,853 | 43,851 → 43,851 | 43,824 → **0** | S:43237/A:0/B:5/C:609 | 0 / 0 |
| 11 | `s_gscplanning_com_arcgis_rest_services_Addre` | `AddNum` | 32,599 | 30,809 → 30,809 | 30,561 → **0** | S:0/A:30632/B:23/C:154 | 0 / 0 |
| 12 | `rvices_Assessor_Data_Bossier_City_Address_Po` | `NUMBER_` | 23,728 | 23,722 → 23,722 | 23,722 → **0** | S:0/A:0/B:0/C:23722 | 0 / 0 |
| 13 | `leycity_ca_server_rest_services_Maps_Open_Da` | `HOUSE` | 12,321 | 12,320 → 12,320 | 12,316 → **0** | S:0/A:0/B:0/C:12320 | 0 / 0 |
| 14 | `58_rest_services_Clive_Clive_Land_Record_Ser` | `HouseNumber` | 9,257 | 9,257 → 9,257 | 9,198 → **0** | S:9198/A:0/B:0/C:59 | 0 / 0 |
| 15 | `TUCXd1_arcgis_rest_services_OSM_Addresses_NA` | `addr_housenumber(str)` | 15,765,750 | 15,765,731 → 15,765,731 | 109 → **0** | S:0/A:0/B:0/C:15765731 | 0 / 0 |
| 16 | `rdco_org_arcgis_rest_services_Address_Points` | `NUMBER(float)` | 39,604 | 39,594 → 39,594 | 38 → **0** | S:39036/A:1/B:422/C:135 | 0 / 0 |
| 17 | `ervices_AGO_HarrisonCounty_PhysicalAddresses` | `ADDR_NUM(float)` | 105,474 | 105,396 → 105,396 | 33 → **0** | S:0/A:0/B:0/C:105396 | 0 / 0 |
| 18 | `1Hv4I6Qk_arcgis_rest_services_Address_Points` | `Address_Number(str)` | 11,466 | 11,466 → 11,466 | 24 → **0** | S:0/A:0/B:0/C:11466 | 0 / 0 |
| 19 | `N_arcgis_rest_services_OSM_Address_Points_AS` | `addr_housenumber(str)` | 1,458,232 | 1,458,222 → 1,458,222 | 2 → **0** | S:0/A:0/B:0/C:1458222 | 0 / 0 |
| 20 | `N_arcgis_rest_services_OSM_Address_Points_EU` | `addr_housenumber(str)` | 32,730,200 | 32,730,193 → 32,730,193 | 2 → **0** | S:0/A:0/B:0/C:32730193 | 0 / 0 |

合计：mapped 51,288,941 → 51,288,941（**相等**）；脏行 1,169,271 → **0**；`bad_empty` 0、`bad_grade` 0。

> 清单里的 `rows_dirty`（`scope.jsonl`）是**产物口径**（v2 tar 内实际行），重跑里的 before 是**当前 main 代码口径**，总数差 **+9** 行（个别层 ±1~7），原因是那批产物早于 fix58 的拆分修复（与本轮改动无关），已在逐层表里分别列出。

## 4. 非零小数保留计数（口径要求）

- 清单内 20 层里，`house_number` 仍含**非零小数**的行：**981** 行（before 981）。**一个都没动**，只计数。
- 判定：`^\d+\.\d*[1-9]\d*$`（如 `12.5`、`1009.50`）；这类值不是浮点写法，不做任何整形。

## 5. 覆盖率（验证②）

- 清单内 20 层重跑后 **全部 `mapped>0`**；清单外 3,413 层**未重跑、未改**。
- 覆盖率 = **3413/3550 = 96.14%**，与 PR #58 合并后基线逐位一致。
- 依据：`clean_number` 只在值命中 `^\d+\.0+$` 时生效，而 3,413 层全量扫描（483,239,197 行）只在清单内 20 层发现这种形态 → 清单外层的输出逐字节不变。

## 6. 四项验证逐条

1. **脏行归零**：20/20 层 after 脏行 = 0（fail 列表：无）。
2. **覆盖率**：3413/3550 = 96.14%（fail：无）。
3. **行数/闭合**：逐层 before/after mapped 相等，`closed_diff` 前后都为 0，丢层 0（fail：无）。
4. **bad_* 与 grade**：`bad_empty` 0、`bad_grade` 0、grade 分布逐层**完全相同**（净变差 0）；`zero_coord` 40 行是**源侧缺坐标**（raw `lat/lon = "NaN"`），before/after 逐层相等（2/30/8 行，且每行「有无坐标」标志完全相同，见 `zero-coord-evidence.json`）。

## 7. 抽查（验证⑥）

- **全量逐行对账**（比抽样更强）：`1,169,271` 条脏行在同一行上比 before/after —— `house_number` 只少了 `.0`，`street_name`/`lat`/`lon`/`grade`/`city`/`state`/`zip5` 全同；**mismatch = 0**。
- **随机 1,000 行**（每层随机挑 3 个 part 文件 + 蓄水池抽样，覆盖 17 层）：**mismatch = 0**；明细见 `spot-check-1000.jsonl`。
- `addrkey` 变化的行：**1,169,269 / 1,169,271** —— 这是**预期**：`addrkey` 由门牌参与哈希，脏门牌 `1009.0` 与整形后 `1009` 是不同键；整形后同址才能对上键（身份修正，不是身份改变）。街道/坐标/等级三者全同已在逐行对账里证明。

## 8. 产物

- 代码：分支 `feat/clean-number-20261126`（base `origin/main` = `2a2369e44d3258c8b962bd32ebac14a63b679ecd`）。
- 新映射数据（仅清单内 20 层，after 口径）：`/data/scratch/clean-number-20261126/rows/`，共 25 个文件；其中 OSM EU 那层按 6 个 part 分片写出，`cat` 拼接即为单个 gz（gzip 多成员合法）。

| 文件 | 字节 |
|---|---|
| `1Hv4I6Qk_arcgis_rest_services_Address_Points_FeatureServer_4.ndjson.gz` | 395,440 |
| `58_rest_services_Clive_Clive_Land_Record_Service_MapServer_0.ndjson.gz` | 245,340 |
| `58c926eb68_rest_services_Public_SiteAddr_ZipCode_MapServer_0.ndjson.gz` | 1,989,237 |
| `N_arcgis_rest_services_OSM_Address_Points_AS_FeatureServer_0.ndjson.gz` | 32,071,748 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part01.ndjson.gz` | 178,111,545 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part02.ndjson.gz` | 174,742,170 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part03.ndjson.gz` | 173,828,012 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part04.ndjson.gz` | 177,137,257 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part05.ndjson.gz` | 178,780,439 |
| `N_arcgis_rest_services_OSM_Address_Points_EU_FeatureServer_0.part06.ndjson.gz` | 176,979,454 |
| `TUCXd1_arcgis_rest_services_OSM_Addresses_NA_FeatureServer_0.ndjson.gz` | 565,624,848 |
| `_gov_host_rest_services_PublicAccess_LandData_MapServer_1054.ndjson.gz` | 2,524,051 |
| `countymd_gov_server_rest_services_Public_Primary_MapServer_2.ndjson.gz` | 2,157,187 |
| `ervices_AGO_HarrisonCounty_PhysicalAddresses_FeatureServer_0.ndjson.gz` | 3,518,782 |
| `erycountymd_gov_arcgis_rest_services_General_BAR_MapServer_0.ndjson.gz` | 11,330,332 |
| `land_ca_server_rest_services_civic_addresses_FeatureServer_0.ndjson.gz` | 3,035,431 |
| `leycity_ca_server_rest_services_Maps_Open_Data_MapServer_182.ndjson.gz` | 285,420 |
| `ountymd_gov_arcgis_rest_services_General_BAR_FeatureServer_0.ndjson.gz` | 11,340,465 |
| `rcgis_rest_services_OpenData_General_Reference_MapServer_100.ndjson.gz` | 1,403,812 |
| `rdco_org_arcgis_rest_services_Address_Points_FeatureServer_0.ndjson.gz` | 1,447,685 |
| `rvices_Assessor_Data_Bossier_City_Address_Points_MapServer_0.ndjson.gz` | 798,274 |
| `s_gscplanning_com_arcgis_rest_services_Addresses_MapServer_0.ndjson.gz` | 1,036,794 |
| `s_org_server_rest_services_JCAdmin_SITUS_Static__MapServer_0.ndjson.gz` | 1,471,052 |
| `services_Address_Planning_AddressPoints_Planning_MapServer_0.ndjson.gz` | 2,369,523 |
| `v_com_server_rest_services_ACC_Address_Point_FeatureServer_0.ndjson.gz` | 3,272,637 |

## 9. 未闭环 / 短板

1. `"0.0" → ""`（不是 `"0"`）：理由见 §2，属**有意**偏离派单 2.1 的示例，muse 若要反悔改一行。
2. `zero_coord` 40 行仍是源侧缺坐标（raw `NaN`），本单不动坐标逻辑。
3. 清单外 3,413 层未重跑（覆盖率按「未命中 `x.0` 形态 → 输出不变」论证，不是重跑实证）。若要逐字节证明，需要一次全量重扫（上次实测 247 分钟）。
4. 清单里的脏行数是产物口径（1,169,262），重跑 before 是当前代码口径（1,169,271），差 9 行已逐层交代。
5. 另一个 clone（`/root/pi-work/world-map-data-33`，`fix/w33-048...`）与本单无关，未切分支、未改、未推。
