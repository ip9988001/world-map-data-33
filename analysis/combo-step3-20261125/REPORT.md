# 组合拳③：P1 431 层切分 / addr_key 占位跳过 / P3-P8-P10 实测

> **一句话**：P1 切分器在 431 层的真实样本上做到 **331/431 层 ≥95%**、**行级 93.44%**（17,998 行可评估）；
> 占位值跳过让 P7 建键**维持 83 层**、非 P7 **有效键丢失 0 行**（1,250 行「占位值拼出来的垃圾键」被有意剔除）；
> P3 只有 **8/53 层**能靠「尾部 ZIP+州锚定」真切出来（行级 28.97%，低）；P10 的 2 个少字段层是**采集漏字段**；
> 四个数（1,268 / 1,066 / 982 / +1,784）**全部一键复算对上**。
> 所有行级数字都是**采样实测**——可及行 19,224 / rows_n 28,644,662 = **0.063%**，不是全量。

- 基线：`origin/main = 6a3d1216bd987c347e79407215a1e4d50f70a5b7`（PR #54 merge）
- 分支：`feat/combo-step3-split-20261125`，工作树 `/data/workspace/wmd-combo-step3`
- 边界：只动 `engine/` 与 `analysis/`；**没动** registry / collect / schema / 账本 / Releases / 网站；没重跑分档；无 main 直推

---

## 0. 数据可得性（先说清覆盖率，再谈数字）

| 口径 | 值 |
|---|---|
| P1 层数 | **431**（`patterns.csv` 的 `pattern_id=P1`，与组合拳① 逐条对齐，431/431，无缺层） |
| P1 rows_n 合计 | 28,644,662 |
| 可及真实行 | **19,224 行**（coord-samples 抽的 `addr_fields_json` 真实值；其中 17,998 行的目标列有值，1,226 行目标列缺列） |
| 覆盖率 | **0.063%**（19,224 / 28,644,662）—— **绝不等同于已实测 28,644,662 行** |
| 层级分布 | 采样 **363 层** / 全量 **68 层**（这 68 层的样本行数 = rows_n，属小层）/ 零样本 **0 层** |
| 数据源 | `analysis/coord-samples-20261124/samples/*.csv`（59 文件 / 738,174 行）+ `survey/ng911/samples.csv.gz` 兜底 3 条/层；**本轮没有联网抓全量** |

⚠️ 一个「目标列不在样本里」的现象：`patterns.csv` 点名的组合串列，在部分层的坐标样本里根本没被抽到（那层的地址列别名不同），
这类行算 `field_absent`（1,226 行），不计入成功率分子分母，在 `p1-split-perlayer.csv` 的 `field_present_rows` 列可见。

---

## 1. 交付的代码：`engine/split_addr.py`

| 组件 | 作用 |
|---|---|
| `is_placeholder(v)` | 占位缺失值（`-1`/`-9`/`-99`/`-999`/`-9999`/`0`/`NULL`/`NA`/`N/A`/空串/`X`…）判定，**只判整值**，避免误杀 `10 N MAIN ST` |
| `split_number_street(raw)` | P1 切分：输出 `house_number` / `street_name` / `unit` / `reason` / `confidence` |
| `split_city_tail(raw)` | P3：尾部锚定 ZIP5(+4) → 州缩写 → 街名右锚（街道类型词，含 `HWY 220`/`US 71` 这类公路编号吞并）→ 城市 |
| `addr_key(af, roles, state)` | 与 `sandbox/coord_evidence.py:addr_key()` **同契约**，差别只有「占位值跳过 + 不许覆盖真值」 |

覆盖的形态（`engine/tests/test_split_addr.py`，7 个用例全过）：
`12 MAIN ST` / `12A` / `12 B` / `12-14` / `12 1/2` / `123RD` / `4S631`（网格号）/ `N12W34567` /
`601 N CAPITOL AVE` / `123 MAIN ST APT 4`（剥 unit）/ `14090 CO RD A`；
拒绝：`PO BOX`、`RR 2 BOX 45`、`3XX E 12TH ST`、`MAIN ST / OAK AVE`（路口）、纯街名、只有门牌、占位值。

**切不出的行一律进 reject 桶并带 reason 代码**，没有静默丢、没有填空串凑数。

---

## 2. P1 验收（a/b/c）

### a) 成功率（两个口径都报）

| 口径 | 值 |
|---|---|
| **层级**：切分成功率 ≥95% 的层数 | **331 / 431（76.8%）** |
| **行级**：成功行 / 可评估行 | **16,818 / 17,998 = 93.44%** |
| 行级（含 `field_absent` 行一起算） | 16,818 / 19,224 = 87.48% |

> 为什么给两个行级？`field_absent` 是「目标列没被样本抽到」而不是「切分失败」，把它算进失败会低估切分器；
> 把它排除又会显得好看。两个都给，报告里以 **93.44%（可评估）**为主、87.48%（含缺列）为保守下界。

### b) 失败率与 reason 桶

行级失败 **1,180 / 17,998 = 6.56%**（含缺列口径 2,406 / 19,224 = 12.52%）。分桶：

| reason | 行数 | 含义 | 原始样例 |
|---|---:|---|---|
| `no_house_number` | 799 | 纯街名（数据本身没有门牌） | `TASSAJARA RD`、`BRUSH ST`、`MAIN ST` |
| `po_box` | 237 | 邮政信箱 | `PO BOX 123`、`P O BOX 45` |
| `ambiguous` | 93 | 两个门牌候选 / 切完仍以数字开头 | `12 14 MAIN ST`、`4S631 Naperville Rd`（已修，剩余为真歧义） |
| `intersection` | 25 | 路口名 | `DOUGLAS AVE / JEFFERSON ST` |
| `placeholder` | 19 | 占位缺失值 | `-1`、`0`、`UNKNOWN`、`X` |
| `rural_route` | 6 | RR/RURAL ROUTE | `RR 2 BOX 45` |
| `no_street` | 1 | 只有门牌 | `12` |

完整失败清单（行级，含层/字段/原始值）：`p1-failures.csv`。

### 失败最多的 10 层

| # | 层（url 尾段） | rows_n | 实测行 | 成功 | 成功率 | 主因 | 字段 |
|---|---|---:|---:|---:|---:|---|---|
| 1 | `ODNR_Pacels/FeatureServer/0` | 22 | 22 | 3 | 0.1364 | no_house_number | `ODNR_LocationAddress` |
| 2 | `Duck_River_ACCESS_SITES_v2_view/FeatureServer/0` | 54 | 49 | 7 | 0.1429 | no_house_number | `ADDRESS` |
| 3 | `Streetlight_Parc_OSMZ/FeatureServer/0` | 415 | 50 | 8 | 0.16 | no_house_number | `ADDRESS_1` |
| 4 | `VacantSites_WFL1/FeatureServer/0` | 54 | 50 | 12 | 0.24 | no_house_number | `FullAddress` |
| 5 | `Squaxin_Properties_2025_Parcels/FeatureServer/284` | 235 | 50 | 17 | 0.34 | no_house_number | `Street_Address` |
| 6 | `JST_Properties/FeatureServer/1` | 404 | 50 | 20 | 0.4 | no_house_number | `Address` |
| 7 | `FordRiver_wServiceLocations_PublicView/FeatureServer/0` | 198 | 50 | 20 | 0.4 | no_house_number | `Full_Address` |
| 8 | `TRADOC_USAREC_USACC_Locations_WFL1/FeatureServer/0` | 2022 | 29 | 12 | 0.4138 | field_absent | `Street_Address_2` |
| 9 | `Weather_Map_TRADOC_USAREC_USACC_WFL1/FeatureServer/0` | 2022 | 29 | 12 | 0.4138 | field_absent | `Street_Address_2` |
| 10 | `OpenSpaceParcels/FeatureServer/0` | 130 | 50 | 21 | 0.42 | po_box | `ADDRESS_LI` |

（这 10 层失败几乎都是 `no_house_number`：该层的「组合串」字段其实是街名列或整串地址被抽错列；不是切分规则错。）

### c) 覆盖率表

`p1-coverage.csv`：每层 `rows_n` / `available_rows` / `coverage_pct` / `kind`（全量|采样|零样本）。
汇总：采样 363 层、全量 68 层、零样本 0 层；覆盖率高的是小层（rows_n 小），**大层一律是采样**。

---

## 3. P3 城市黏尾实测（53 层 / 2,238,360 行）

规则：尾部锚定 `ZIP5(-ZIP4)` → 其前州缩写（US 两字母）→ 街名右锚点取**最后一个街道类型词**并吞并其后的公路编号
（`HWY 220`、`US 71`、`CR 135`）；无 ZIP 时只要求州缩写，confidence 降到 0.6；连州缩写都没有时，
只有「能切出街道类型词 + 还有城市尾巴」才接受，confidence 0.4。

| 结果 | 值 |
|---|---|
| **能真切出来的层（≥95% 行切成功）** | **8 / 53** |
| 行级 | 692 / 2,389 = **28.97%**（可评估行） |
| 高置信（ZIP+州，conf 0.9） | 见 `p3-citytail.csv` 的 `conf_0.9` 列 |
| 主因 | `no_state_or_zip`（32 层）→ 值根本没有州/ZIP 尾巴；`no_street_type_anchor`（9 层）→ 街名里没有 `ST/AVE/RD…` 类型词 |

**明确回答**：**x = 8（53 层里 8 层能靠这条规则真切出来）**。剩下 45 层的典型失败：
`848 W COLONIAL CIR DAYTONA BEACH FL 32117`（能切）/ `110 STATE HIGHWAY 220 Lincoln County NM 88345`（street type 是 HIGHWAY，
城市尾巴是县名 → 锚点能切但 city 语义是县）/ 以及大量「无州无 ZIP」的值（`1846 TOWER Chaves County NM 88201` 这类含县名的）；
这批要真做对，需要**城市/县词典**（本地没有），因此本单只能给到「尾部锚定 + 置信度」，不给「全切」的假承诺。

前 12 层样例（按成功率降序）：

| # | 层（url 尾段） | rows_n | 实测行 | 可切 | 不可切 | 成功率 | 主因 |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | `Riverdale_Base_Data/FeatureServer/1` | 20992 | 50 | 50 | 0 | 1.0 |  |
| 2 | `CRA_ArcGIS_Online/FeatureServer/0` | 17929 | 50 | 50 | 0 | 1.0 |  |
| 3 | `Residency_Verification/FeatureServer/0` | 17516 | 50 | 50 | 0 | 1.0 |  |
| 4 | `SD_Permits_Data/FeatureServer/0` | 859 | 50 | 50 | 0 | 1.0 |  |
| 5 | `Opengov_GIS_Service_Permitting_and_Licensing_Public/FeatureServer/897` | 20451 | 50 | 49 | 1 | 0.98 | no_street_type_anchor |
| 6 | `AGOL_Service_LUZoning/FeatureServer/0` | 76085 | 50 | 48 | 2 | 0.96 | no_street_type_anchor |
| 7 | `PARCELS_021524/FeatureServer/1` | 8119 | 50 | 48 | 2 | 0.96 | no_state_or_zip |
| 8 | `PARCELS_021524_VIEW_LAYER/FeatureServer/1` | 8119 | 50 | 48 | 2 | 0.96 | no_state_or_zip |
| 9 | `COFloodTTX18_Incident_Data_Shelter_Status/FeatureServer/0` | 386 | 50 | 46 | 4 | 0.92 | no_street_type_anchor |
| 10 | `Parcels/FeatureServer/0` | 116556 | 50 | 45 | 5 | 0.9 | no_street_type_anchor |
| 11 | `Parcels/FeatureServer/21` | 36400 | 50 | 36 | 14 | 0.72 | no_state_or_zip |
| 12 | `Lansing_Parks_points/FeatureServer/0` | 116 | 50 | 28 | 22 | 0.56 | no_street_type_anchor |

---

## 4. P10 少字段层交叉核（2 层，不是 7 层）

派单说「7 层字段数 ≤3」，实测 `patterns.csv` 里 P10 中 `n_fields ≤ 3` 的只有 **2 层**（两层的 `fields` 都是
`RAMP_NUMBER|EXIT_NUMBER|MP_SUFFIX`，同一服务的两个层）。逐层核对 `inventory-remote-uncollected.csv`：

| 层 | patterns n_fields | 远端 n_fields | 远端 addr_core_hit | 样本行 | 结论 |
|---|---:|---:|---|---:|---|
| `MD_RoadCenterlinesComprehensive/MapServer/0` | 3 | **19** | 11000 | 50 | **采集漏字段**：远端 `?f=json` 报 19 个字段，采集快照只落了 3 个 → 可补采 |
| `MD_RoadCenterlines/MapServer/0` | 3 | **19** | 11000 | 50 | 同上，**采集漏字段** → 可补采 |

明细：`p10-crosscheck.csv`。**没有出现「数据本身没地址」的层**（但这 2 层本身就是道路中心线，补采后大概率仍属 P8/P10，需另判）。

---

## 5. P8 拍板

见 `p8-decision.md`：**建议从 E7 可验分母剔除 22 层**（184,987 行，占缺口 1.64%），区间匹配器单独立项。
**需要 Muse 点头的一条**：分母定义文件（`analysis/auto-spatial-relax-20261125/auto-recognized.csv` 的 E7 归因口径 /
`sandbox/spatial_thresholds.yaml`）要改口径，本单不动。

---

## 6. addr_key 占位跳过（772 行 questionable 的根因之一）

`engine/split_addr.py:addr_key()`：占位值（`-1`/`-999`/`-9999`/`0`/`NULL`/`NA`/`N/A`/空串/`X`…）**不参与建键、也不覆盖真值**。

| 验收项 | 结果 |
|---|---|
| P7 321 层建键层数 | 83 → **83（未掉）** ✅ |
| P7 出键行数 | 3,532 → **3,520**（−12 行：这 12 行的旧键完全由占位值拼出来，本就该没有键） |
| 非 P7 **有效键**丢失 | **0 行** ✅（`key_form_ok(k1)` 为真的旧键，一条没丢） |
| 非 P7 旧键为占位值拼出、本轮被剔除 | 1,250 行（**有意剔除**，不是丢失；其中 1,238 行旧键形态本就不合法） |
| 非 P7 harm / gain | 1,021 / 44,499 |
| 772 行 questionable 逐行处置 | 复算命中 **769 / 772**（3 行未复现 = 0.39%，见下）→ **improved 106 行 / 仍 questionable 663 行 / 转差 0 行** |

逐行处置：`placeholder-fix.csv`（列：layer / url / `key_before_c3` / `key_after_c3` / `baseline_key` / `label_before` / `label_after` / `transition`）。

**没修掉的那部分要说清**：663 行仍 questionable，根因不是占位值，而是「新街名列本身就是整串地址列」
（`situs_street` 等）与「街名 + type 分列需拼列」——这两条要靠切分/拼列路线，不属占位值修复。

**3 行未复现**：用 PR #54 的 `old-key-changes.csv` 反向核对时，769 行可复现、3 行在本次逐行重算里 `k1 == k2`（未产生 harm），
差异 0.39%，未进一步定位（不隐瞒）。

---

## 7. 四数对账（Muse 点名）

| 数 | 口径 | 怎么算 | 实算 | 对上？ |
|---|---|---:|---:|---|
| **1,268** | 组合拳②「严格口径（**19 条别名**）下，**非 P7** coord 行的**纯增益**行数」（旧键空 → 新键非空） | `reconcile_four.py`：registry@a2e3c88 + engine@ebe6a14 的 19 条别名 → 扫 695,706 行非 P7，数 `not k1 and k2` | **1,268** | ✅ |
| **1,066** | 同口径下 **P7 321 层**「出键行数」合计 | 同一脚本：P7 层逐行 `k2` 非空计数（样本 15,293 行） | **1,066** | ✅ |
| **982** | 同口径下 P7「键形合法行数」合计（门牌纯数字 + 街名有字母） | 同一脚本 `key_form_ok(k2)` | **982** | ✅ |
| **+1,784** | PR #53 的**增行数**（与任何语义无关，纯 git 统计） | `git diff --numstat a2e3c88 ebe6a14` 增列求和（删行 = 0） | **1,784** | ✅ |

**唯一需要点明的口径错位**：1,066 / 982 是**19 条别名**（PR #53 严格口径）下的数字；
PR #54 把别名补到 27 条后，同口径重跑变成 **3,532 / 3,362 行**（`p7-rebuild-after.csv`）。
两者不是矛盾，是**别名集合不同**——引用时必须带「19 条 / 27 条」前缀。

复现：`python3 analysis/combo-step3-20261125/reconcile_four.py`（25 秒，全本地）。

---

## 8. 产物与复算

```
analysis/combo-step3-20261125/
├── REPORT.md                 # 本文
├── p1-split-perlayer.csv     # 431 层逐层（含 field_present_rows / evaluable / success_rate / top_reason）
├── p1-failures.csv           # 行级失败清单（层/字段/原始值/reason）
├── p1-coverage.csv           # 覆盖率：rows_n vs available_rows vs kind
├── p3-citytail.csv           # 53 层：可切/不可切/置信度/失败样例
├── p10-crosscheck.csv        # 少字段层 vs 远端 n_fields
├── p8-layers.csv             # 22 层区间层清单
├── p8-decision.md            # 拍板建议
├── placeholder-fix.csv       # 772 行 questionable 逐行处置
├── run_split.py / verify_placeholder.py / reconcile_four.py
└── _work/                     # 中间件（.gitignore）
engine/split_addr.py           # 切分 + 占位跳过 + addr_key（同契约）
engine/tests/test_split_addr.py# 7 个单测
```

复算（全本地、无网络，约 1.5 分钟）：

```bash
python3 -m pytest engine/tests/test_split_addr.py -q          # 7 passed
python3 analysis/combo-step3-20261125/run_split.py            # P1/P3/P8/P10 实测
python3 analysis/combo-step3-20261125/verify_placeholder.py   # 占位修复三项验收
python3 analysis/combo-step3-20261125/reconcile_four.py       # 四数对账
```

## 9. 未做 / 不越界

- 没有改 `sandbox/coord_evidence.py`（`addr_key` 本体在 sandbox，本单边界只到 `engine/`）——
  **要让 E7 真吃到占位跳过，需 ④ 把 `roles_of()/addr_key()` 换成 `engine.split_addr.addr_key()`**，这是一行 import 的事，但按边界本单不动。
- 没有改 registry、collect、schema、账本、Releases、网站；没有重跑全量分档；没有直推 main。
- P3 没有伪造「全切」结论：8/53 就是实测结果，剩下 45 层的根因（无州/ZIP、含县名、无街道类型词）已逐层列出。
