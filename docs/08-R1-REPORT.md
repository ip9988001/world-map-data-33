# 08 · R1 单州端到端报告（IA）· 2026-11-01

> **结论：链路跑通，五项验证全过（`adjudicate_08.py --check` = `IDENTICAL`），但 IA 这次的输入暴露了三个真问题。**
> 机器可读：`analysis/08-r1-IA-2026-11-01.json` · 台账样本：`analysis/08-r1-IA-sample.ndjson`（1,000 行）
> 口径：`layer_plan.csv` 里 `state=IA` 的全部层（9 层 / 15.7 MiB / 370,130 行），不跨州。

---

## 一、跑数结果

| 项 | 值 |
|---|---:|
| 输入层 | 9（全在 05b） |
| 下载 | 15.7 MiB（11 个包） |
| 读入行 | 370,130（= 账本 rows 之和，逐层一致） |
| 判出县 | 370,013 |
| 有坐标但落不进任何县 | 16 |
| 无坐标 | 3 |
| 字段缺失（num/street 都取不到） | 98 |
| **可键（本州）** | **254,837** |
| 因「不跨州」排除 | 115,176（31.1%） |
| **去重后键** | **133,634** |
| 被合并的成员行 | 121,203（**去重率 47.6%**） |
| 县数 | 8 |
| 台账字节 | 1,000 行样本 ≈ 1.0 MB（≈ 1 KB/行） |

**耗时（单机 8 核，串行四步）**：

| 步 | 耗时 |
|---|---:|
| stage1 抽取（下载 + 解压 + 判县 + 分桶） | **87 s** |
| stage2 去重 | 12 s |
| stage3 public/product | 7 s |
| adjudicate `--check` | 2 s |
| **合计** | **108 s** |

吞吐：370,130 行 / 87 s ≈ **4,254 行/秒·进程**（含下载与解压）。与方案里 4,646 行/秒·进程的判县实测同量级，说明 44.7 h·进程的全量预算没被低估。

分级：`B` 123,592 / `U` 10,042 / `A` 0 / `S` 0。

---

## 二、五项验证（逐条给结果）

### ① 同一键必落同片 —— **PASS**

- 桶号 = `blake2b(county_fips) % 64`，8 个县只落进 **7 个桶**（2 个县撞同一桶，正常）。
- `Σ 各桶行数（extract 报告）= 254,837`，**重新点 spill 文件 = 254,837**，`reduce.rows_in = 254,837` 三者相等。
- 桶内行数最不均：min 2 / max 215,041（Cedar Rapids 所在县独占一桶）。全量时这一桶会变成热点 → **桶数 64 对 IA 够用，全量要按县二次分片**（方案 5.2 #2 已写）。
- 守恒：`rows_in(254,837) = keys_out(133,634) + dup_members(121,203)` ✅；台账重数 = 133,634 = 主键去重数 ✅。

### ② `add_num` 命中率与 `raw` 回退 —— **PASS，且证明回退是必需项**

| 来源 | 行数 | 占比 |
|---|---:|---:|
| 顶层 `add_num`（采集侧已归一化） | 120,870 | **32.7%** |
| `raw` 回退（NENA `Add_Number` / `STREET_NUMBER` / `HOUSENO` / `StreetName`…） | 138,247 | **37.4%** |
| 整串地址抠（`SiteAddress` 之类自由文本） | 110,937 | **30.0%** |

- **只靠顶层字段，249,184 行（67.3%）不可键** —— 方案里「2 层 0% 命中」在 IA 上被放大成「5 层 0% 命中」。
- 为救这些行，`raw` 回退表这一轮补了 6 组真实字段名：`Add_Number`（NENA）、`StreetName`/`StN_PosTyp`（IA Update）、`HOUSENO`/`NAME`/`SUFTYPE`（Cedar Rapids 那套）、`house_numb`/`street_nam`（ESRI 截断名，靠前缀匹配救）、`SiteAddress`（自由文本）、`STREET_NUMBER`。
- **字段名匹配改成「去分隔符指纹」**：`SiteAddress` / `SITE_ADDRESS` / `site_address` 归一成 `SITEADDRESS`。不做这一步，驼峰值一个都匹配不上（第一版 R1 就是这么 0 命中的）。

### ③ 源组投票正确（重发层只算 1 票）—— **PASS**

- `Address_Point_Update_WFL1_14` 与 `Address_Point_Updater_WFL1_14`：各 17,076 行，`dataset_fingerprint` 都是 `8ffcf841e56c72ed` → **折叠成一票，19,900 票被丢弃**（`duplicate_dataset_votes_dropped=19,900`）。
- 台账里每个键 `independent_sources_n = 1`：因为 IA 这 9 层**全部来自 LOCAL_GIS 一组**（没有 NAD / NG911 / 宗地），所以整轮没有 `A` 级。这是输入覆盖的问题，不是逻辑的问题——两源两票的路径由 `collect/tests/test_dedup_reduce.py::test_two_groups_two_votes` 单测覆盖。
- 方向补全：`dir_inferred_keys = 896`（唯一方向时安全补齐并降级），`dir_ambiguous_keys = 137`（同族有 ≥2 个方向，空方向不合并）。
- **215 组重发层清单**（475 层）落在 `analysis/08-duplicate-datasets-2026-11-01.json`。

### ④ public 版无门牌泄漏 —— **PASS（泄漏 0）**

`collect/dedup_public.py` 的五类扫描，最后一次全 0：

| 扫描 | 命中 |
|---|---:|
| `forbidden_field`（public schema 出现 `number`/`unit`/`lat`/`lon`… ） | 0 |
| `non_decade_number`（号段不是 10 的整数倍） | 0 |
| `unit_token`（出现 `APT`/`STE`/`#`/`UNIT`…） | 0 |
| `leading_door_number`（前导整数不属于街名本体） | 0 |
| `small_sample`（`address_count < 3` 的街道页没被屏蔽） | 0 |

- public 产物：街道页 4,936 / 邮编页 57 / 城市页 43（`address_count < 3` 的 1,138 个街道页已屏蔽）。
- product 产物：133,634 行全字段。
- 扫通过程中真抓到过两类问题，已修：
  1. **单元藏在街名里**：`412 3 ST S UNIT D COGGON` → 现在会把 `UNIT D` 剥成 `unit=D`，街名只留 `3 ST S`。
  2. **门牌号被当成街名的误报**：`5 AVENUE COURT`（第五大道）不是门牌 5 → 判据改成「前导整数必须是街名本体首词，否则才算泄漏」，并只对 `street_full`/`city_postal` 生效（否则 `county_fips=19025` 会被误判）。

### ⑤ 行数与该州账本可对账 —— **PASS（差额 100% 可解释）**

```
读入 370,130 = 可键本州 254,837 + 不跨州 115,176 + 落不进县 16 + 无坐标 3 + 字段缺失 98
                  254,837 + 115,176 + 16 + 3 + 98 = 370,130  ✅
读入 370,130 = 账本 rows 之和 370,130（逐层对得上，diff 0）
```

**但差额的主体（115,176 行 / 31.1%）不是数据问题，是清单问题** —— 见下文。

---

## 三、R1 抓到的三个真问题（比数字更重要）

### 3.1 `layer_plan.csv` 的 `state` 列有错，而且错得很彻底

| 层（计划州都写 IA） | PIP 实际所在州 |
|---|---|
| `Planning_GretnaLaVistaAPTP_MapServer_0` | **NE** 13,631（Gretna / La Vista 是奥马哈南郊） |
| `La_Vista_Address_Points___BSA_FeatureServer_0` | **NE** 12,851 |
| `Iowa_County_Address_Points_October_2024` | **WI** 15,876（Iowa County 是威斯康星的一个县，不是爱荷华州！） |
| `2022_Lightbox_Address_Points_Option_A` | **NE** 30,575 / **IN** 1,875 / IA 2,221 |
| `2022_Lightbox_Address_Points_Option_B` | **NE** 38,493 / **IN** 1,875 / IA 3,439 |

- 9 层里有 **5 层**（55.6%）的计划州与实际州不符；其中 3 层是 100% 在别的州。
- **后果**：如果 08 按「计划州」筛选（方案初稿就是这么写的），IA 会静默丢掉 31% 的行，而 WI/NE 的真实地址会被永远漏掉。
- **已改**：`dedup_extract.py` 一律用全国县索引（3,089 县）PIP 判县，`state` 由 `county_fips` 反推，计划州只做校验；不符就写进 `plan_state_mismatch_layers` 并在报告里点名。
- **待办**：这批层的 `state` 要回写 `layer_plan.csv`（属采集侧口径，本轮不动，见 W33 台账）。

### 3.2 「两套不同的字段命名」是常态，不是例外

见第二节 ②：顶层命中 32.7%、`raw` 37.4%、自由文本 30.0%。**没有一层是「顶层就够」的**。

### 3.3 自由文本地址会污染街名核心词

`SiteAddress = "2069 HWY 1 MARTELLE IA 52305"` → 砍掉 `STATE ZIP` 后剩 `HWY 1 MARTELLE`（城市名残留在核心词里）。

- 已做的：剥 unit、砍尾部 `STATE ZIP`、截到最后一个街类型词（含右侧方向）。`412 3 ST S UNIT D COGGON IA 52305` → `num=412, core=3, type=ST, dir=S, unit=D` ✅
- 做不到的：**没有类型词**的自由文本，城市名会留在核心词里。这类行标 `street_src=full` + `flags=street_from_fulltext`，`tier` 封顶 `U`（IA 里 10,042 条，7.5%），并且**不进「独立源≥2」的判定**。
- 判定依据写死：**宁可不合并，也不编造**。

---

## 四、台账样本（3 行，完整 35 字段见 `analysis/08-r1-IA-sample.ndjson`）

```json
{"dedup_key":"IA|19025|3344|AVENUE|ADAMS||","state":"IA","county_fips":"19025",
 "county_name":"Calhoun","number":"3344","street_core":"ADAMS","street_type":"AVENUE",
 "street_full":"ADAMS AVENUE","zip5":"50538","city_postal":"UNINCORPORATED",
 "src_kinds":["LOCAL_GIS"],"src_layers_n":1,"independent_sources_n":1,
 "src_group_votes":{"LOCAL_GIS":1},"tier":"B","dup_members":0,"flags":[],
 "first_seen":"2026-10-31T00:03:34Z","last_seen":"2026-10-31T00:03:34Z"}
```

- `dedup_key` 7 段：`state|county|num|TYPE|CORE|DIR|unit`（street_key 自带两个 `|`）。

---

## 五、R1 的边界（对外讲的时候必须带）

1. **IA 这 9 层全部是 LOCAL_GIS 一组** → 没有任何键达到 `independent_sources_n ≥ 2`，所以**没有 A 级、没有 S 级**。R1 只验证了「单源去重 + 重发层折叠」，**没验证跨源投票**（单测验证）。
2. **没挂 TIGER 号段校验**（按拍板排在 R3）→ 没有 `tiger_verify`、没有 S 级。**R1/R2 阶段的产物不许对外讲「号段可信度」。**
3. 只跑了 `state=IA` 的 9 层，**没有**跑全国性的 `未定位` 层（NAD 75.9M、OSM EU 32.7M 等）→ IA 的台账**不是**爱荷华的全部地址，只是「计划州=IA 的那 9 层里的爱荷华地址」。
4. 台账输出目前是 `ndjson.gz`（环境无 pyarrow）。方案里写的 parquet+zstd 推迟到 R3，体积结论（10–22 GB）仍是推算。

---

## 六、下一步

| 轮 | 建议 | 理由 |
|---|---|---|
| **R2** | 挑一个**同时有 NAD + NG911 + LOCAL_GIS 覆盖**的州（推荐 **CO** 或 **NC**：CO 在 04b 有 NAD/AGOL 多层，NC 有三套 NC1Map 重发层） | 只有这种州才能验证「跨源投票 → A 级」与「重发层折叠」在真实数据上的组合 |
| R2 附带 | 把 `layer_plan.csv` 里 5 个州标错的层回写（另开采集侧单） | 否则按州派单会继续漏 |
| **R3** | 20 片 + 64 桶全量 + TIGER 号段分级 | 方案 5.3 |
