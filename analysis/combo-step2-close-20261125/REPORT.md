# 组合拳② 收尾：27 条别名并进 registry（走生成链）+ P7 建键 83/321

> 结论：**P7 321 层建键 83/321（目标值达成）**；**非 P7 键丢失 0 行 / 0 条**（coord 695,706 行 + ng911 60,373 层）。
> 旧键被改**实际是 41 层 / 1,024 行**（不是 975 层 —— 975 是「有任何变化」的层数，其中 934 层是纯增益）。
> 这 41 层里 **8 层 improved / 33 层含 questionable（772 行）**，questionable 里 620 行是「新街名取自整串地址列」。数字与清单全部落盘，未放宽任何判据。

- 基线：`origin/main = a259aa8be40257e43d896e4bac5a6d8308ae87a3`（PR #53 merge commit，2026-11-25T03:58:58Z）
- 分支：`feat/combo-step2-registry-20261125`，工作树 `/data/workspace/wmd-combo-step2b`（新建，未复用 step2 工作区）
- 口径：Muse 拍板 (b) 路 —— registry 是分档唯一真源；engine 表只做「别名来源」，由 `gen_registry.py` 生成时合并，不维护第二真源。

---

## 1. 别名补到 27 条（engine 表 → registry 生成物）

- `engine/dialects/sources.v1.yaml` 的 `p7-alias-ext-v1` 从 19 条扩到 **27 条**：19 门牌 + 8 街名（归一化后恰好 27，无重复）。
- 收回上一轮被回归剔除的 8 条：`HouseNumber`、`HOUSE_NO`、`HSE_NUM`、`House`、`HouseNumbe`、`AddressNum`、`STREETNO`、`situs_street`。理由：Muse 新口径不是「差异=0」，而是「0 丢失 + 每处改动须是同语义更完整列名替换」，所以这些别名可以入表，但改动要逐层审计（见 §4）。
- **生成链**：`gen_registry.py` 新增 `engine_alias_extensions()` / `alias_ext_dialect()`，读取 engine 表里 `family: alias_extension` 的条目 → 在 registry 里生成对应方言 `p7-alias-ext-v1`（`provider.kind=alias_extension`、`geom.granularity=unknown`、`status=minimal_safe`、`a_pool_eligible=false`、coverage layers_n=321 / rows=5,520,975），并从 `analysis/combo-step2-close-20261125/p7-samples.csv`（**真实坐标样本行**）生成 4 条 golden case（`gc-015`–`gc-018`）。
- **不改任何既有方言的 template** —— 只扩大别名并集，因此不影响已有层的方言归属判定。
- 稳定性验证：**改动前**先跑一次 `gen_registry.py`，产物与 committed 的 registry 逐字节相同（确定性成立），之后才加合并逻辑。

### 27 ↔ 27 逐条对照（engine 表 vs registry 生成物，全部 ✔）

| # | 别名 | 语义 | engine 表 | registry |
|---|---|---|---|---|
| 1 | `ADDRNUM_1` | 门牌 | ✔ | ✔ |
| 2 | `ADDR_NUMB` | 门牌 | ✔ | ✔ |
| 3 | `ADDR_STR_NBR` | 门牌 | ✔ | ✔ |
| 4 | `ANUMBER` | 门牌 | ✔ | ✔ |
| 5 | `Addr_Number` | 门牌 | ✔ | ✔ |
| 6 | `AddressNum` | 门牌 | ✔ | ✔ |
| 7 | `GM_HSE_NUM` | 门牌 | ✔ | ✔ |
| 8 | `HOUSE_NO` | 门牌 | ✔ | ✔ |
| 9 | `HOUSE_NUMB` | 门牌 | ✔ | ✔ |
| 10 | `HSE_NUM` | 门牌 | ✔ | ✔ |
| 11 | `HSE_NUMB` | 门牌 | ✔ | ✔ |
| 12 | `House` | 门牌 | ✔ | ✔ |
| 13 | `HouseNumbe` | 门牌 | ✔ | ✔ |
| 14 | `HouseNumber` | 门牌 | ✔ | ✔ |
| 15 | `PROPERTYHOUSENUM2` | 门牌 | ✔ | ✔ |
| 16 | `SA_House_N` | 门牌 | ✔ | ✔ |
| 17 | `STREETNO` | 门牌 | ✔ | ✔ |
| 18 | `STREETNUMBER1` | 门牌 | ✔ | ✔ |
| 19 | `addr_numbe` | 门牌 | ✔ | ✔ |
| 20 | `CC_ST_NAME` | 街名 | ✔ | ✔ |
| 21 | `Loc_Street` | 街名 | ✔ | ✔ |
| 22 | `PWA_FULLSTREET` | 街名 | ✔ | ✔ |
| 23 | `SA_Street_` | 街名 | ✔ | ✔ |
| 24 | `STREETALL` | 街名 | ✔ | ✔ |
| 25 | `ST_NAME_COMPLETE` | 街名 | ✔ | ✔ |
| 26 | `Street_Road_Name` | 街名 | ✔ | ✔ |
| 27 | `situs_street` | 街名 | ✔ | ✔ |

校验：engine 19 门牌 = registry 19 门牌、engine 8 街名 = registry 8 街名（按 `addr_key()` 的归一规则比较集合，差集为空）。

### 复现命令

```bash
python3 analysis/combo-step2-close-20261125/collect_samples.py   # 抽 golden case 真实样值 → p7-samples.csv
python3 analysis/dialect-20261124/gen_registry.py                # engine 表 → registry/dialects.v1.yaml（确定性）
python3 registry/validate.py                                     # OK: dialects=4 golden_cases=18
python3 -m pytest registry/tests engine/tests -q                 # 93 passed
python3 analysis/combo-step2-close-20261125/verify.py            # 三件验收 → 3 份 CSV + _work/summary.json
```

---

## 2. 验收 a：P7 的 321 层 → **83 / 321 建键**

ROLES **只从 `registry/dialects.v1.yaml` 取**（即 E7 的真实取数路径），`addr_key()` 逐字照抄 `sandbox/coord_evidence.py`。

| 项 | 值 |
|---|---|
| 建键成功层 | **83 / 321（25.86%）** ✅ 目标值 83 |
| 样本行 | 15,293 行 → 出键 **3,532 行**，键形合法 **3,362 行** |
| 加别名前（基线 registry） | 0 / 321 |
| 上一轮（别名只在 engine 表、E7 读不到） | 0 / 321（这就是「增益=0」的原因） |
| 失败层 | 238 层，逐层原因在 `p7-rebuild.csv` 的 `reason` 列（整串地址列需切分 / 列名语义不明 / 无样本行） |

逐层明细：`p7-rebuild.csv`（321 行，含 `old_key_rows` / `new_key_rows` / `new_valid_key_rows` / 选出的门牌列与街名列）。

## 3. 验收 b：非 P7 层键丢失 = **0**

| 范围 | 行/条 | 丢失 | 旧键被改 | 纯增益 |
|---|---:|---:|---:|---:|
| coord-samples 非 P7 行（15,914 层） | 695,706 | **0** | 1,024 | 44,683 |
| ng911 全量层（60,373 层 / 83,448 条记录） | 83,448 | **0** | 113 | 1,459 |

`regression-nonP7.csv`：15,914 层逐层 `harm_rows / loss_rows / gain_rows / label`（`no_change` 14,939 / `gain_only` 934 / `improved` 8 / `questionable` 33）。

## 4. 验收 c：旧键被改的对照（1,024 行 / 41 层）

- 全量行级对照：`old-key-changes.csv`（1,024 行 = 1,024 处 harm，0 处 loss），列含 `layer_id / url / old_key / new_key / old_number_field / new_number_field / old_street_field / new_street_field / old_street_value / new_street_value / label / reason`。
- 判定规则（机械执行，不看「是不是 P7」）：
  1. 新键形态不合法 → `questionable`；
  2. 新街名原值以数字开头 / 含 5 位邮编 / 含逗号（= 整串地址列）→ `questionable`；
  3. 新街名词数比旧少 → `questionable`（含「旧键来自整串地址兜底解析、新键只取街名列缺 type」）；
  4. 旧街名取自整串/组合列、新取自专用街名列 → `improved`；
  5. 旧门牌段不是纯门牌、新键是纯门牌 → `improved`；其余同词数 → `improved`（同语义替换）。

| 标签 | 行数 | 层数 |
|---|---:|---:|
| improved | 252 | 8 |
| questionable | 772 | 33 |

（8 + 33 = 41，无重叠：同一层内若有任一 questionable 行即整层记 questionable 行数另计，故 252 + 772 = 1,024。）

### questionable 的归因（按「新门牌列 / 新街名列」）

| 新门牌列 | 新街名列 | questionable 行数 |
|---|---|---:|
| `HSE_NUM` | `ST_NAME` | 150 |
| `House_No` | `St_Name` | 144 |
| `STREET_NUMBER` | `SITUS_STREET` | 128 |
| `House` | `StreetName` | 105 |
| `HOUSENUMBE` | `STREETNAME` | 82 |
| `Site_Address` | `SITUS_STREET` | 50 |
| `houseNumber` | `streetName` | 50 |
| `HOUSE_NUMBER` | `STREET_NAME` | 49 |
| `House_Number` | `ST_NAME` | 8 |
| `STREETNO` | `STREETNAME` | 2 |
| `house_number` | `street_name` | 2 |
| `HOUSE_NO` | `LASTNAME` | 1 |

**判读**：772 行 questionable 里 **620 行是「新街名的原始值就是整串地址列」**（`situs_street` / `SITUS_STREET`，以及若干早已在 registry 但值不干净的 street 别名），163 行是键形态不合法（门牌 `-1`、街名只有数字等）。**没有一行是键丢失。**

### Top 20 questionable 层（完整清单见 `old-key-changes.csv` 过滤 label=questionable）

| # | 层（url 尾段） | 行数 | 旧键 → 新键（样例） | 主因 |
|---|---|---:|---|---|
| 1 | `ComDev_Data_TEST/FeatureServer/1` | 50 | `FL|5765|sw72ndstreet|33143` → `FL|5765|72nd|33143` | 整串地址列 |
| 2 | `ComDev_Test/FeatureServer/1` | 50 | `FL|6480|manorlane|33143` → `FL|6480|manor|33143` | 整串地址列 |
| 3 | `PayoffPace_SpatialJoin3/FeatureServer/0` | 50 | `_UNLOCATED|17941|tramontodrive|17941` → `_UNLOCATED|-1|1|90272` | 形态不合法 |
| 4 | `ReverseMortgag_G_SpatialJoin3/FeatureServer/0` | 50 | `_UNLOCATED|735|mountainviewstreet|91001` → `_UNLOCATED|-1|1|91001` | 形态不合法 |
| 5 | `missed_all_parcel_1/FeatureServer/125` | 50 | `_UNLOCATED|2924|ridgeview|92105` → `_UNLOCATED|2924RIDGEVIEWSanDiegoCA92105|ridgeview|92105` | 形态不合法 |
| 6 | `ComDev_Data_v2/FeatureServer/1` | 50 | `_UNLOCATED|6241|sw61ststreet|33143` → `_UNLOCATED|6241|61st|33143` | 整串地址列 |
| 7 | `Multiple_Accounts/FeatureServer/2` | 50 | `_UNLOCATED|2304|halptroadbsitka|99835` → `_UNLOCATED|2304|halibutpoint|` | 整串地址列 |
| 8 | `pm_occupancy/FeatureServer/0` | 49 | `IN|3414|portlandplz|40212` → `IN|3414|portland|40212` | 整串地址列 |
| 9 | `CountyParcelCondoAIO_10kft/FeatureServer/0` | 45 | `CA|23923|cortecajan|92562` → `CA|23923|23923cortecajan|92562` | 整串地址列 |
| 10 | `Township_Roads_WFL1/FeatureServer/1` | 43 | `IL|16319|boulevardplaceunit103plainfield|16319` → `IL|16319|boulevard|60544` | 整串地址列 |
| 11 | `Will_County_Dataset_view/FeatureServer/8` | 39 | `_UNLOCATED|11400|cindydriveplainfield|11400` → `_UNLOCATED|11400|cindy|60585` | 整串地址列 |
| 12 | `Barstow_Enterprise_Permitting_Licensing_GIS_20261020_WFL1/FeatureServer/0` | 36 | `CA|116|whitestreet|92311` → `CA|116|white|92311` | 整串地址列 |
| 13 | `Barstow_Enterprise_Permitting___Licensing_GIS_20260508_WFL1/FeatureServer/0` | 36 | `CA|116|whitestreet|92311` → `CA|116|white|92311` | 整串地址列 |
| 14 | `Barstow_Enterprise_Permitting___Licensing_GIS_20260521_WFL1/FeatureServer/0` | 36 | `CA|116|whitestreet|92311` → `CA|116|white|92311` | 整串地址列 |
| 15 | `Map_WFL1/FeatureServer/0` | 36 | `CA|116|whitestreet|92311` → `CA|116|white|92311` | 整串地址列 |
| 16 | `Affected_Residents_Parcels_5K_03192026/FeatureServer/111` | 33 | `CA|41851|kalmia|92362` → `CA|41851|41851kalmiastreet|92362` | 整串地址列 |
| 17 | `Various_Zoning_Parcels/FeatureServer/5` | 23 | `CA|35875|c|` → `CA|35875|42086cstreet|` | 整串地址列 |
| 18 | `RockHill_SPAC/FeatureServer/0` | 8 | `_UNLOCATED|-|55|29702` → `_UNLOCATED|14469|55|29702` | 形态不合法 |
| 19 | `NORCO_PARCELS/FeatureServer/29` | 7 | `_UNLOCATED|1220|partridge|92880` → `_UNLOCATED|1220|1220wpartridgeavenue|92880` | 整串地址列 |
| 20 | `San_Diego_Promise_Zone_Community_Assets_v2_WFL1/FeatureServer/0` | 5 | `CA|2438|street|92102` → `CA|-1|1|` | 形态不合法 |

> 说明：这张表就是「Muse 新口径下需要人工过一眼」的部分。典型两种：① `CA|23923|cortecajan|` → `CA|23923|23923cortecajan|`（新街名列把门牌又抄了一遍）；② `FL|5765|sw72ndstreet|` → `FL|5765|72nd|`（新街名列缺 type 后缀）。前者说明 `situs_street` 这类列本质是整串地址，后者说明「街名 + type 分列」需要拼列 —— 两者都指向组合拳下一段的**切分/拼列**，不是别名表能修好的。

---

## 5. 越界声明（逐项）

| 目录/资产 | 是否动过 |
|---|---|
| `registry/`（`dialects.v1.yaml` 由生成链重写；`validate.py` 未改） | 只重生成 YAML |
| `engine/dialects/sources.v1.yaml` | 27 条别名同步（19 → 27） |
| `analysis/`（`dialect-20261124/gen_registry.py`、`registry-approved.json`、`combo-step2-close-20261125/`） | 生成器加合并逻辑 + 本轮产物 |
| `collect/`、`schema/`、账本 ledger、`Releases`、网站 | **一行未动** |
| 全量分档重跑 | **未跑**（按派单要求，等 ③ 之后统一重跑） |
| `main` 直推 | **无**（只开 PR） |

## 6. 产物清单

- `REPORT.md`（本文）
- `p7-rebuild.csv`（321 行）、`regression-nonP7.csv`（15,914 行）、`old-key-changes.csv`（1,024 行）
- `p7-samples.csv`（golden case 真实样值 4 行）、`collect_samples.py`、`verify.py`
- `_work/summary.json`（断言值：`assert_p7_83=true`、`assert_loss_zero=true`）
