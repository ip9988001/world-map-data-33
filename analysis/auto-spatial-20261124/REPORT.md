# 第 5 步 · 自动认 + 空间验算接入沙盒（task `w2-20261124-auto-spatial`）

**状态：沙盒结论完成 · 2026-11-24 · 基线 sha `4ed9349`（第 4 步合并后 origin/main）**

> 只做沙盒：不改 `registry/`、不动 `collect/` `schema/` 任何账本、不动 Release/网站、未起任何 collect/采集 run、
> 未融合、未分级、未重写引擎（引擎是第 6 步）、未直推 main（本分支另开 PR，只开不合）。
> 本文件每个数字都能用本目录 CSV + `summarize.py` 复算；取不到的写 `unavailable`，没有估算值。

## 〇、这一轮最硬的一条结论（先看这个）

**Tier 1（自动放行）= 0 层。** 原因不是判据太严，而是**没有坐标样本**：
第 3 步 1,000/1,000 探针配额全部用在 `?f=json` meta 上，只拿到字段名/几何类型/CRS，
**没有采到任何一行的经纬度**；仓库里也没有 `dist/`（本地层只在 fixtures 里留了 3 份 25 行真实样本）。
所以 17,168 层里 **E6（空间验算）全部 `unknown`、E7（源间投票）全部 `unknown`** —— 按三档定义，
「空间验算全绿」这一条对任何一层都无法成立，Tier 1 必然为 0。

这不是本轮的失误，而是**第 6 步的前置条件**：想真正放行任何一层，必须先拿到该层的坐标抽样
（每层 ≥50 行、带 `x/y` 或 `geometry`，落盘到受控目录），否则自动认只能停在 Tier 2，
而 Tier 2 又必须由第 6 步的抽样复核兜底。

---

## 一、8 条否定证据（定义 / 判据来源 / 实测命中）

判据一律是「字段有没有值 / 几何对不对得上」的**证据组合**，全文件不存在 `confidence ≥ x` 这类阈值门控
（`sandbox/test_auto_recognize.py::test_module_has_no_confidence_threshold_gate` 会当场抓违规）。
层级统计 = `auto-recognized.csv`（17,168 行）按 `E*_state` 列复算。

| 编号 | 证据 | 可执行判据（代码位置 + 数据来源列） | 命中层数 | 命中行数 | 未判(unknown) | 不适用(na) | TU 命中层/行 |
|---|---|---|---:|---:|---:|---:|---:|
| ① | 门牌要素缺失/不可解析 | `ev1`：`inventory-remote-uncollected.csv:addr_core_hit[0]=0`（20 行样值里门牌族含数字未过半）；空样品 → unknown | **9,896** | **247,614,330** | 417 | 0 | 6,537 / 75,407,740 |
| ② | 街名要素缺失或占位值 | `ev2`：`addr_core_hit[1]=0`，或 `inventory-local-fields.csv:samples` 里街名/门牌样值出现字面占位值（TBD/UNKNOWN/NULL/N/A/NA/NONE/`-`） | **3** | **55,374** | 417 | 0 | 3 / 55,374 |
| ③ | 几何语义不符 | `ev3`：`dialect-assignment.csv:granularity` ⇄ `inventory:geom` 冲突（building_point/apartment_unit_point→Point，parcel_centroid→Polygon，centerline_midpoint→Polyline，range_interpolation→Point/Polyline） | **482** | **16,991,320** | 12,498 | 0 | 310 / 6,108,551 |
| ④ | 别名冲突未解 | `ev4`：门牌证据落在负向字段族（`fields_number_like` 出现 parcel/route/hwy/phone/lot/unit…），或同名字段在 `registry/dialects.v1.yaml` 里跨方言映射到不同 canonical 要素 | **2,911** | **307,966,031** | 13,443 | 0 | 1,671 / 21,327,565 |
| ⑤ | 样本份额过低/不可代表 | `ev5`：`sampled_n=0`（抽样为空）或 `sampled_n < min(20,count)`（抽样被截断）或层份额 `share < 0.01%` | **1,313** | **256,249,808** | 0 | 0 | 1,017 / 149,611,421 |
| ⑥ | 空间验算不通过 | `ev6`：`spatial-findings.csv` 里该层 verdict≠green；无该层记录 → unknown | **0** | **0** | **17,168** | 0 | 0 / 0 |
| ⑦ | 源间投票冲突 | `ev7`：多源同址解析互斥；第 3 步未产出地址级多源投票 → 恒 unknown | **0** | **0** | **17,168** | 0 | 0 / 0 |
| ⑧ | 上游结构漂移 | `ev8`：层有注册表模板但 `n_fields=0`（字段集对不上）；无模板（`t000000`）→ na | **0** | **0** | 5,584 | 10,720 | 0 / 0 |

补充说明（都是可复算的，不是判断）：

- **①命中层 = `usable=road_only` 的 10,000 层拆成 9,896 + 103 + 1**：① 命中的 9,896 层，其 `usable`
  **全部**是 `road_only`（`usable` 列复算：road_only 命中 9,896，其他取值命中 0）。剩下的 **104** 层拆成：
  **103 层** `addr_core_hit` 为空（本地读不出，落 `E1 unknown`，其中 103 只是 assignment 记 `road_only`、
  其余 314 层记 `sampled_zero_rows/no_zip/empty_shell`）+ **1 层两个口径打架**
  （`mFK_arcgis_rest_services_SFHA_Address_Points_FeatureServer_0`：本地可读、`addr_core_hit=11110`
  却说 `usable=road_only`，第 3 步本地层 `usable` 与 `addr_core_hit` 不一致的**唯一一例**）。
  本轮一律以 `addr_core_hit` 原位证据为准 —— 这也是第 4 步 `road_only 6,641 vs 复算 6,537` 那 104 层的来源（见 §4 差额第 3 条）。
- **①命中的粒度分布**：unknown 7,394 / centerline_midpoint 1,292 / parcel_centroid 959 / apartment_unit_point 117 /
  building_point 108 / range_interpolation 26 —— 「没有门牌」在线要素与地块质心里最集中。
- **①命中的 provider 分布**：agol 机构前三是 `agol:NuWFvHYDMVmmxMeM` 130 层、`agol:Ezk9fcjSUkeadg6u` 125 层、
  `agol:uFAr0LUPy14bDaLg` 60 层；不是单一上游在拖后腿。
- **②只命中 3 层**：字面占位值只存在于本地层的 `street_name/street_full` 样值里（0 层来自远程——
  远程没有值样本，这本身就是未跑项，见 §7）。
- **④命中 2,911 层里最主要的一类是「门牌候选字段其实是干道号」**：
  `A1_HWY_NUM,A2_HWY_NUM,HWY_NUM`、`ACM_Fut_Num_Lanes`、`TRL_NUM` 这类字段被第 3 步的 `fields_number_like`
  当成门牌族候选，正是第 4 步注册表 `NUM_NEG_FIELD` 想拦的东西 —— 现在有 2,911 层被显式拦下来了。
- **⑤命中 1,313 层 = 1,158 层「抽样为空」+ 155 层「层份额 <0.01%」**：前者全是本地读不出的层（`d2`），
  后者是分母 984,719,364 下层均不足 9.8 万行的极小层。
- **⑧的 na 有 10,720 层**：这些层 `template_id=t000000`（第 4 步判不出模板），**没有模板就谈不上「与模板不一致」**，
  记 na 而不是 unknown，避免把「不知道」伪装成「有问题」。

---

## 二、三档分级（判据是证据组合，不是分数段）

规则（`sandbox/auto_recognize.py::tier_of`，5 行）：

- ①②③⑧ 任一 `hit` **或** `unknown`，或 ⑥ `hit` → **Tier 3**
- 8 条**全** `clear`/`na` → **Tier 1**
- 其余（①②③⑧ 全 clear，只剩 ④⑤⑥⑦ 的 unknown / 可解释 hit）→ **Tier 2**

| 档位 | 层数 | 行数 | 其中 TU 层数 | TU 行数 | 说明 |
|---|---:|---:|---:|---:|---|
| Tier 1 自动放行 | **0** | 0 | 0 | 0 | ⑥⑦ 全 unknown（无坐标、无多源投票）→ 「空间全绿」不可达，见 §0 |
| Tier 2 抽样后放行 | **1,123** | **92,206,281** | 1,043 | 63,983,917 | 门牌+街名齐、粒度与几何相容、无致命证据 |
| Tier 3 强制人工 | **16,045** | **892,513,083** | 10,013 | 233,535,391 | 至少有 1 条致命证据命中或不可判 |
| 合计 | **17,168** | **984,719,364** | **11,056** | **297,519,308** | 与第 4 步分母逐位相等，差额 0 |

**Tier 2 ≠ 可以上线**：它只是「值得抽样复核」的候选池。Tier 2 的 1,123 层在本轮的 `move` 一律是
`minimal_safe`（manual 池、`a_pool_eligible=false`），不放 A 货池。理由：空间与多源两条证据仍然缺，
且第 6 步才是引擎。

### Tier 2 样例（5 层，5 个不同 provider / 4 个州，且 `layer_id` 在本库内唯一）

| layer_id | provider_id | 州 | granularity / geom | usable | share | 行数 | 判定理由 |
|---|---|---|---|---|---:|---:|---|
| `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | `host:ags.myokaloosa.com` | AL | building_point / point | no_zip | 0.668% | 129,741 | ①② 齐（`addr_core_hit=11001`）、③ 相容、⑧ t000000→na；只有 ④⑥⑦ unknown |
| `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | `socrata:arcgis.eriecounty.oh.gov` | OH | building_point / point | no_zip | 1.45% | 42,966 | 同上，抽样 20 行满额，无别名冲突命中；⑤ 命中的是「层份额极低」这条可解释项 |
| `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | `socrata:cotinter.leoncountyfl.gov` | FL | building_point / point | no_zip | 1.45% | 157,864 | 抽样满额、字段无冲突、粒度相容；⑥ 未跑 |
| `tyga_gov_hosted_rest_services_Address_Points_FeatureServer_0` | `socrata:dcgis.dekalbcountyga.gov` | GA | building_point / point | no_zip | 1.45% | 391,817 | 同上；可达样本量最大的一档 |
| `es_us_mn_state_mngeo_loc_addresses_zip9_open_FeatureServer_0` | `socrata:enterprise.gisdata.mn.gov` | MN | building_point / point | no_zip | 1.45% | 1,929,626 | 同上；**全库 192 万行的大层，也是只差 ⑥ 的一档** |

> ⚠️ **`layer_id` 不是主键**（本轮新发现）：17,168 行只有 **1,523** 个不同 `layer_id`，
> `FeatureServer/0` 一个值就覆盖 **11,740** 行；`url` 也只有 16,752 个不同值（差 416 行）。
> 第 4 步的「层」实际是「层实例（url × 方言）」，**不是**唯一 id。因此本轮 `ev6` 查找空间结论**按 `url`**
> （`C["spatial"].get(L["url"])`），不按 `layer_id`；上面 5 个样例也挑了 `layer_id` 在本库唯一的层，
> 避免引用歧义。第 6 步做逐层映射时必须用 `url(+dialect)` 做键，这条单列成待办。

---

## 三、空间验算（`sandbox/spatial_verify.py`）

### 3.1 证据源

| 证据源 | 状态 | 数据 |
|---|---|---|
| 行政边界/几何 | **已跑** | `analysis/tiger_county/*.json.gz`，51 州 3.0MB，TIGERweb `State_County/1`，fetched 2026-10-30 |
| 建筑轮廓距离 | **未跑（无数据源）** | 仓库内没有 building footprint 图层；`building_outline_dist_m()` 显式 `NotImplementedError`，绝不返回假数 |
| 邮编表/ZCTA | **未跑（未接入）** | 仓库内无 ZCTA 表；代码里**没有** zip-table 参数（阈值 YAML 里已如实写明），留第 6 步先定来源 |
| 源间投票 | **未跑（无输入）** | 第 3 步没产出地址级多源解析结果 → ⑦ 恒 unknown |
| 坐标行级样本 | **仅 fixtures** | `sandbox/fixtures/` 三份真实样本各 25 行，共 75 行，均有经纬度 |

### 3.2 判据与算法（可复算，不依赖联网）

- **点落判定**：射线法（奇偶规则）`point_in_ring`，经纬度直接当平面（县界尺度下与球面判定一致）。
- **跨边界距离**：只对「落在声明县界**外**」的行量距，点到县界顶线段的最近距离；
  按纬度余弦缩放（`kx=111320·cos(lat)`，`ky=110540`），段长 <100km 时误差 <1%。
- **县内到界距离**：只进 P95 相对判据，**不参与熔断**（否则县中心点会被误杀）。
- **层内统计离群**：坐标唯一率、单一坐标占比（坐标聚集）、字段非空率突变（某字段在层内整体变 0）。

### 3.3 阈值（写进 `sandbox/spatial_thresholds.yaml`，每条带数值 + 理由 + 来源）

| 类型 | 项 | 值 | 取值理由 | 来源 |
|---|---|---:|---|---|
| 熔断 | `max_outside_share` | 0.10 | 越界行占比 >10% 更可能是「声明县错」而非个别脏坐标，留 10% 容差给县界裁剪误差与飞地 | 无外部标定，冷启动值，待第 6 步用真实样本重标 |
| 熔断 | `max_cross_boundary_dist_m` | 5,000 m | 越界 5km 已超出「县界裁剪/坐标精度」可解释范围 | TIGER 顶点精度 ~1e-4°≈11m，5km = 450 倍 |
| 熔断 | `max_top_point_share` | 0.50 | 过半行同一坐标 = 整层被单点填充（未地理编码的占位质心），空间证据不可用 | fixtures 实测 ≤0.04，留足余量 |
| 熔断 | `min_unique_coord_rate` | 0.05 | 与上一条同源（聚集），两条一起钉死伪坐标层 | fixtures 实测唯一率 = 1.0 |
| 不判 | `min_sample_rows` | 3 | 有效坐标 <3 行不判熔断也不判绿，记 unavailable | 统计最小可判样本 |
| P95 | `boundary_dist_mult` | 3.0 | 层内 P95 到界距离 > 3×P50 → 相对异常（少数点飘远） | 无外部标定，冷启动值 |

### 3.4 实测触发

| 项 | 实测 |
|---|---|
| 3 个 fixture 层结论 | **全部 `green`**：`outside_share=0.0`、`unique_rate=1.0`、`top_point_share=0.04`（25 行 25 个唯一坐标） |
| 熔断红线命中 | **0 层 / 0 项**（3 层全绿；17,168 注册表层未跑，不是「通过」） |
| P95 相对异常命中 | **0 层**（granit p95 9,430.7 vs 3×p50 27,753；nad 7,905.8 vs 7,983；tiger 5,962.3 vs 17,829，均未越线） |
| 层内 null 率突变 | **645 / 882 层（73.1%）触发，涉 1,565 个字段层** —— 触发面很大，说明「字段在该层整体变 0」是本地层的普遍现象（多为 `house_number`/`full_formatted_address`/`_house_num` 整列空），不是孤例 |

fixture 明细（`spatial-findings.csv` 前 3 行）：

| 层 | 行数 | outside_share | p50 到界距离 | p95 到界距离 | 结论 |
|---|---:|---:|---:|---:|---|
| granit_nh_belknap（GRANIT，声明 33001） | 25 | 0.0 | 9,251.2 m | 9,430.7 m | green |
| nad_de_kent（NAD，声明 10001=Kent） | 25 | 0.0 | 2,661.0 m | 7,905.8 m | green |
| tiger_nh_interp_33001（TIGER 插值，声明 33001） | 25 | 0.0 | 5,943.3 m | 5,962.3 m | green |

### 3.5 只跑抽样，不全量扫

- **抽样范围**：3 个 fixture 层（75 行，全部逐行参与空间验算）+ 882 个本地层的字段级全表（36,750 行，参与 null 率突变检测）。
- **抽样清单**：`sampling-list.csv`（885 行：3 fixture + 882 本地层），列 `layer_id/kind/n_rows/seed`，抽样种子 `20261124`。
- **耗时**（本机实测）：`spatial_verify.py` **0.32 s**，`auto_recognize.py` **1.69 s**，`pytest sandbox` **5.0 s** ——
  远低于「单次全量 ≤15 分钟」的上限；**没有任何一步扫 2.97 亿行**。
- **没跑的**：17,168 个注册表层的坐标级空间验算（无坐标样本）。

---

## 四、11,056 层 template_unresolved 挪动表（**只是沙盒结论**）

本轮不写回任何账本、不改 CSV 生产口径；结论只落在 `template-unresolved-moves.csv`。

| 列 | 层数 | 行数 | 占比（行） | 依据 |
|---|---:|---:|---:|---|
| 可认 → `active` | **0** | **0** | 0% | 需 Tier 1，而 Tier 1 被 ⑥⑦ 的 unknown 硬卡（§0）——**不许硬挪** |
| 可降级 → `minimal_safe` | **1,043** | **63,983,917** | 21.5% | Tier 2 且 `addr_core_hit[:2]=11`（门牌+街名齐），可交 `registry/evaluator.py::minimal_safe` 解析器；`pool=manual`、`a_pool_eligible=false` 不变 |
| 留 `manual` | **10,013** | **233,535,391** | 78.5% | 至少 1 条致命证据命中或不可判，见下「卡点分布」 |
| **合计** | **11,056** | **297,519,308** | 100% | 与第 4 步 TU 分母**逐位相等**，差额 **0 层 / 0 行** |

### 卡点分布（留 manual 的 10,013 层，按证据组合；层数合计 10,013）

| 证据组合 | 层数 | 读法 |
|---|---:|---|
| `E1,E3,E6,E7` | 5,019 | 既没门牌、粒度也没定（unknown），空间未跑 —— 最大的单一卡点，实为「road_only + granularity unknown」叠加 |
| `E3,E6,E7` | 2,741 | 有门牌但粒度 unknown（第 4 步没定点位语义） |
| `E1,E6,E7` | 1,490 | 粒度已知但没门牌（线要素/地块层） |
| `E1,E2,E3,E5,E6,E7` | 417 | 本地读不出（`sampled_zero_rows` 276 / `road_only` 103 / `no_zip` 37 / `empty_shell` 1，全为 `d2`） |
| `E8,E5,E6,E7` | 286 | 有模板但 `n_fields=0` 且抽样为空 —— 结构漂移实锤 |
| `E1,E3,E8,E6,E7` | 20 | 三重叠加 |
| 其余 6 种组合 | 40 | 见 CSV `move_reason` 列 |
| **合计** | **10,013** | 与上表 manual 列一致 |

### 差额解释（逐条，不许四舍五入）

1. **TU 行数**：`minimal_safe 63,983,917 + manual 233,535,391 = 297,519,308` —— 与 `dialect-coverage.csv` 里
   `minimal_safe` 组的 297,519,308 **完全相等**，差额 0。
2. **TU 层数**：`1,043 + 10,013 = 11,056` —— 与 `dialect-coverage.csv` 的 `layers_n=11056` 相等，差额 0。
3. **第 4 步遗留的口径小差（104 层）本轮已定位，不影响挪动表**：
   `dialect-assignment.csv` 里 TU 层有 `usable=road_only` 6,641 层，而按 `addr_core_hit[0]=0` 复算是 6,537 层，
   差 **104** 层；这 104 层的 `inventory` 记录是 `sampled_zero_rows` 且 `addr_core_hit` 为空
   （第 4 步按 provider 借用探针把 `road_only` 继承下来了）。本轮一律以 `addr_core_hit` 原位证据为准，
   这 104 层落进 `E1 unknown`（与另外 313 层合计 417 层，全部为本地区 `d2` 读不出层），**最终都进 manual**，
   所以挪动表三列之和不受影响。

---

## 五、附带修正（muse-000215 决定①：人工队列口径文字）

`analysis/dialect-20261124/manual-queue.csv` 的真实口径是：

- **70 条 / 17,129 层**（`layers_n` 求和）/ 902,619,012 行（`coverage_rows` 求和）；
- 最后一条 `rank=70` 的 `week_end = 141` —— **尾巴是第 141 周**；
- 第 1 条（`minimal_safe`，11,056 层）`week=1 / week_end=56`，**第 2 条**的 `week_end` 才是 56 → 以此类推递增；
- 因此此前记录里写的「排到第 57 周」是**错的**（那是第 2 条的 `week_end`，不是队尾）。

同时更正口径：**200 层/周只是护栏**（`registry/dialects.v1.yaml: weekly_cap_layers: 200`），
属后台清理节奏，**不在关键路径**；`template_unresolved` 的 11,056 层由第 5/6 步**程序化**啃
（本轮已给出 1,043 层可降级 / 10,013 层卡点明细），不靠人工 200 层/周去推。

`registry/` 本轮**一个字节未改**（`git status --porcelain registry/` 为空）。

---

## 六、交付物与复算

| 文件 | 行数 / 内容 |
|---|---|
| `sandbox/auto_recognize.py` | **148 行**：8 条证据 + 三档 + 挪动判定（无状态、纯函数优先、不联网、不写 DB） |
| `sandbox/spatial_verify.py` | **146 行**：点落判定 / 跨边界距离 / 层内离群 / 阈值加载 |
| 合计 | **294 行**（200–300 区间内，守 300 行硬上限；`wc -l` 可验） |
| `sandbox/spatial_thresholds.yaml` | 每条阈值带 `value/why/source` + 显式 `unavailable` 清单 |
| `sandbox/fixtures/spatial_manifest.json` | 3 份 fixture 的坐标列名 / 声明 county_fips / 来源 / 抓取日 |
| `sandbox/test_auto_recognize.py` | 47 用例 |
| `sandbox/test_spatial_verify.py` | 21 用例 |
| `analysis/auto-spatial-20261124/summarize.py` | 报告全部表格的复算脚本（只聚合，不加判据） |
| `analysis/auto-spatial-20261124/auto-recognized.csv` | 17,168 行 × 31 列（含 `E1..E8_state` 与 `*_detail`） |
| `analysis/auto-spatial-20261124/template-unresolved-moves.csv` | 11,056 行（TU 子集，同列） |
| `analysis/auto-spatial-20261124/spatial-findings.csv` | 648 行（3 fixture + 645 null 率突变层） |
| `analysis/auto-spatial-20261124/sampling-list.csv` | 885 行抽样清单（含种子） |
| `analysis/auto-spatial-20261124/summary.json` | 上述所有表的机器可读版（含闭合断言） |

**测试与覆盖率**：`python3 -m pytest sandbox -q` → **86 passed / 0 failed**（47 auto + 21 spatial + 18 既有 `test_rules.py`）；
`coverage` 实测（`--include=sandbox/auto_recognize.py,sandbox/spatial_verify.py`）→
**213 语句 / 未覆盖 3 / 覆盖率 99%**（未覆盖的 3 行是两个 `if __name__` 入口与 null 率分支的 `else`）。

**复算命令**（全部离线，只读）：

```bash
python3 sandbox/spatial_verify.py --out analysis/auto-spatial-20261124/spatial-findings.csv
python3 sandbox/auto_recognize.py --outdir analysis/auto-spatial-20261124
python3 analysis/auto-spatial-20261124/summarize.py          # 复算本文件所有表
python3 -m pytest sandbox -q
```

---

## 七、未跑项（如实标注，不估算）

| 项 | 为什么没跑 | 缺什么才能跑 |
|---|---|---|
| 17,168 个注册表层的空间验算 | 无坐标行级样本（第 3 步只探 meta；探针配额 1,000/1,000 已满） | 每层 ≥50 行 `x/y` 或 `geometry` 抽样（需先获批配额与落盘空间） |
| 建筑轮廓距离 | 仓库内无 building footprint 图层 | 引入 footprint 数据源（体积大，须先批） |
| 邮编/ZCTA 交叉校验 | 仓库内无 ZCTA 表，本轮有意不联网 | 先定数据来源与许可，再落 `sandbox/fixtures/`（≤5MB 小样本可先做单测） |
| 源间投票（⑦） | 无地址级多源解析结果 | 第 6 步产出同址多源候选后再判 |
| 远程层的街名占位值扫描（②的后半条） | 第 3 步只持久化了计数，没持久化值样本 | 值样本落盘后才能扫字面值 |
| `minimal_safe` 1,043 层的实跑解析 | 本轮只做判定，不执行解析器 | 第 6 步接引擎时跑，且必须守 `pool=manual` |

## 八、给第 6 步的三条硬建议

1. **先补坐标抽样，别先放宽规则**：Tier 1 的天花板是 0，唯一解法是每层 ≥50 行带坐标的真样本；
   拿到之后 ⑥ 才能从 unknown 变 clear/hit，Tier 1 才可能出现。放宽 E1–E8 只会制造假放行。
2. **E3（粒度 unknown）是最大的人工成本项**：12,498 层 unknown，其中 7,394 层同时没门牌。
   建议第 6 步先按「有 geom 类型 + 有坐标」把 granularity 重新定出来（几何类型 + 点位密度就能定大半），
   这一条能一次消掉 2,741 + 1,490 两档卡点。
3. **1,043 层可降级是现成收益**：门牌+街名齐、粒度相容、无别名冲突，只要第 6 步能给它们
   `minimal_safe` 解析 + 坐标复核，就能从 manual 池里挪出一批可用地址（仍不进 A 货池）。
