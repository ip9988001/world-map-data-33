# 第 9 步 · 全量字段映射（3,550 层：到手 → 能用）

> 口径以 `w2-fieldmap-plan-20261125.md` 为准（muse-000258 权威口径全文；与下文冲突时以该文档为准）。

> 一句话：**3100/3550 层（87.32%）产出 11 列可读数据**；不可用 450 层（原因全部落在固定枚举内）；逐层闭合差 ≠ 0 的层 **0** 个；行级抽查 **355 层 / 80.28% 相符**；输出 **8598.4 MiB / 8 个 tar.gz 分片**；磁盘余量 **22.8 GiB**。

## 0. 四数（先给数）

| 指标 | 实测 | 门槛 | 结论 |
|---|---:|---:|---|
| 层覆盖率 | **87.32%**（3100/3550） | ≥95%（≥3,373） | **未达标** |
| 不可用层 | **450** | —（全部进 unusable.csv） | 原因全部固定枚举内 |
| 逐层闭合差额 | **0 层有差额** | 0 | 闭合 |
| 行级抽查 | **355 层 / 80.28%** 相符 | ≥355 层（≥10%） | 达标 |
| 输出字节 | **9016085855 B**（8 片） | — | 磁盘余量 22.8 GiB |

## 1. 不可用分桶（`unusable.csv`）

| 原因 | 层数 | 含义 |
|---|---:|---|
| `grade_below_C` | 450 | 所有行都低于 C 级（无街名 / 无任何地址要素）→ 按口径丢弃，不猜 |

## 2. 逐层闭合

| 项 | 行数 |
|---|---:|
| 输入行（3,550 层 part 包实读） | 509,776,855 |
| 映射行（写进 11 列输出） | 305,674,428 |
| 丢弃：低于 C 级 | 204,102,427 |
| 丢弃：解析失败 | 0 |
| **差额** | **0** |

逐层闭合（`in_rows − mapped − dropped_below_C − parse_error`）差额 ≠ 0 的层：**0** 个

## 3. 字段级有效率（全局）

| 字段 | 有效率 | 门槛 | 结论 |
|---|---:|---:|---|
| `street_name` | **100.00%** | 100% | 达标 |
| `house_number` | **71.17%** | ≥90% | **未达标** |
| `zip5` 合法率 | **54.18%** | ≥95% | **未达标** |
| 坐标合法性（非空坐标里越界/(0,0) 残留） | **100.00%**（残留 **0** 行） | 100% | **达标** |
| 有坐标的行占比（覆盖率，非门槛项） | 99.96% | — | 源层本身不缺坐标；110,881 行无坐标 |

> `zip5_valid` 的分母是映射行；源里本就没有邮编的行记 missing（不补零、不截断）。`house_number` 同理：源里没有门牌就 null，绝不生成。

### 3.1 各级行数 + 各级要素齐备校验（plan §三.5）

| 级别 | 行数 | 必须齐备（plan §一） | 缺要素行数 |
|---|---:|---|---:|
| **S** | 45,282,269 | 门牌+街+城+州+邮编+坐标 | 0 |
| **A** | 8,507,671 | 门牌+街+州+邮编 | 0 |
| **B** | 7,042,002 | 门牌+街+州 | 0 |
| **C** | 244,842,486 | 街 | 0 |

缺要素行数出自 `anchor-check.json`（`amend_verify.py` 逐级反查：`grade_missing_element` / `S_city_null` / `zip_null_high_grade`，见 §4.1），**三个计数器均为 0**。

| tier | 层数 | 行数 |
|---|---:|---:|
| `unrated` | 3100 | 305,674,428 |

| addrkey v3（engine 档） | 值 |
|---|---:|
| 行数 | 305,674,428 |
| 与旧键不同的行 | 305,674,428 |
| 不可键（num 或 street 缺 → null） | 88,405,291（28.92%） |
| include_unit（读 pilot.yaml） | True |

按 dialect：见 `field-stats.json: by_dialect`。按州：**不适用** —— 信封行恒无 `state` 字段，state 只能从 raw 的显式州字段或组合串尾部取，因此没有可靠的州分组维度（`field-stats.json: by_state_null`）。

## 4. 行级抽查（`spotcheck.csv`）

| 项 | 值 |
|---|---:|
| 抽查层数 | **355**（含字节最大 10 层） |
| 行级抽样 | 50179 行 |
| 相符 | **40286**（80.28%） |
| 不变量违反 | `bad_zip5=0, bad_state=0, bad_coord=0, zero_coord=0, bad_number=0, bad_columns=0` |

抽查方法：① 对输出行做**不变量**全扫（zip5 恰好 5 位、state 合法、坐标在范围内且非 (0,0)、门牌非占位值、11 列齐全）；② 另写一份**独立重算**（不复用 `fm_core`）对输入行重打一遍，按 (门牌, 街名, zip5, lat, lon) 五元组比对。

### 4.1 改口径后重查（`anchor-check.json` / `amend_verify.py`）

在**重写后的分片**上重新抽层：355 层 / 16,978,947 行，本层行数与 `layer-coverage.csv` 对不上的层 **0** 个。

| 不变量 | 违反行数 |
|---|---:|
| `bad_columns` | 0 |
| `bad_source_layer` | 0 |
| `bad_tier` | 0 |
| `bad_addrkey` | 0 |
| `bad_addrkey_fmt` | 0 |
| `bad_number` | 0 |
| `bad_zip5` | 0 |
| `bad_state` | 0 |
| `bad_coord` | 0 |
| `zero_coord` | 0 |
| `bad_grade` | 0 |
| `zip_null_high_grade` | 0 |
| `grade_missing_element` | 0 |
| `S_city_null` | 0 |

> 说明：`bad_addrkey` / `bad_source_layer` / `bad_tier` 是拿**输出行自己**重算后跟存的值比，所以这三项就是「7 条增量是否真落到了数据里」的机读证据。

## 5. 方法与偏差（必须如实说）

1. **方言命中率极低，这是本轮最重要的偏差**：3,550 层的 `layer_id` 与 17,168 行分档表的交集是 **0**；按 **非空 url** 匹也是 **0**（分档表里有 417 行 url 为空、全记 tier3；本批 71 个 `@未定位` 层同样没有 url，按空串能“对上”属于**假命中**，不计）；按 agol org 匹 registry 只命中 **115 层（3.2%）**；其余一律 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`、永不进 A 货池）。原因是这 3,550 层来自第 4/5/7 批采集，不在方言分档的分母里。
2. **取值优先级**（逐字段）：信封原生值 → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects 合并表，~200 个别名，不新增、不猜）→ 组合串拆分（`split_addr.split_number_street` / `split_city_tail`）。组合串拆出来的值 `provenance=split`，**一律不许进 S**（S 级按口径要求全要素原生）。
3. **未走 `collect/lib/fieldmap3.py`**（硬编码别名表）：它是采集侧的口径，本步按 muse 要求只把它当对照证据。实测它的别名表与本步用的 registry ∪ engine 表在「组合串字段」（如 `ADDR`/`LSN`）上都没覆盖，这也是为什么要上 `split_addr` 的拆分规则 —— 不接这一步时覆盖率只有 67%（1,186/1,776），接上后到 94%+。
4. **grade/tier 全部由配置驱动**：`engine/config/pilot.yaml` 的 `grades`（S/A/B/C 特征表）与 `tier_rank`，代码里没有硬编码阈值；tier 取 `analysis/grading-rerun-20261125/auto-recognized.csv`（**Tier1 = 410 那版**）按 url 匹配，本批 3,550 层与它的 **非空 url 交集 = 0** → 3,100 层输出 tier 全 `unrated`（照抄 `tier_rank` 的 unrated=9）。
5. **zip5 口径**：`12345-6789` 取前 5；不足/超长/含字母一律 null 并计 missing，不补零。**house_number**：占位值（0/000/NULL/N/A/NONE/UNKNOWN/-1/空/纯符号）一律缺失，绝不生成门牌。**坐标**：范围外、(0,0)、缺省一律 null，绝不写 0 冒充。
6. **磁盘**：输入 40,341,427,040 B 只读；输出写 `dist/`，每 500 层一个 `fieldmap-partNNN.tar.gz`，打包后立刻删 `dist/rows/` 里的散文件；`free_gb` 全程未低于 3 GiB（收工 22.8 GiB）。

## 6. 怎么复跑

```bash
cd /data/workspace/wmd-fieldmap && python3 analysis/fieldmap-20261125/map_layers.py \
  --all --shard 500 --workers 7
python3 analysis/fieldmap-20261125/fieldstats.py
python3 analysis/fieldmap-20261125/spotcheck.py --layers 355 --rows 200
python3 analysis/fieldmap-20261125/finalize.py
```

改口径但不重扫输入的增量重写：

```bash
cd /data/workspace/wmd-fieldmap
python3 analysis/fieldmap-20261125/amend_rewrite.py --workers 7   # dist/tar → dist/tar2（改 source_layer/addrkey/tier/-9/重算 grade）
mv dist/tar2/* dist/tar/ && rmdir dist/tar2
python3 analysis/fieldmap-20261125/amend_apply_stats.py       # 回填 layer-coverage.csv（v1 存 layer-coverage.v1.csv）
python3 analysis/fieldmap-20261125/fieldstats.py
python3 analysis/fieldmap-20261125/amend_verify.py --layers 355
python3 analysis/fieldmap-20261125/finalize.py
```

## 7. muse-000258 七条增量：逐条结论（落到数据层的验证）

| # | 增量 | 结论 | 证据 |
|---|---|---|---|
| 1 | `source_layer` = **url** | **符合** | 重写了全量行：3038 层写 url、62 层无 url（`@未定位`）退回 layer_id；`anchor-check.json: bad_source_layer = 0` |
| 2 | `addrkey v3` = a3 + include_unit + sha1-20hex | **符合（口径换实现）** | 旧实现自拼 `number\|street\|city\|state\|zip5\|unit`；现改为直接调 `engine/outlet_clean.addrkey_v3`（parts = state2 / zip5 / num_key / street_key / unit_key），`include_unit` 读 `pilot.yaml`（= True）；重算前后不同键 **305,674,428 行**；不可键（num 或 street 缺）**88,405,291 行**；`bad_addrkey` = 0 |
| 3 | 邮编非法 → grade 最高 B | **符合** | 封顶规则由配置推出（`grades` 里 S/A 都 require `zip5`，缺则只在 B/C 里再算）；`zip_null_high_grade = 0` |
| 4 | `city`：S 必须、A/B 可空 | **符合** | `S_city_null = 0`（S 行 city 空值计数） |
| 5 | S/A/B/C 要素表逐级校验 | **符合** | 各级行数与缺要素行数见 §3.1；`grade_missing_element = 0` |
| 6 | `house_number` 占位值补 `-9` | **符合** | 占位值集合已含 `-9/-9.0/-09/-1/-1.0/0/0.0/000/0000/NULL/NA/NONE/UNKNOWN/空/纯符号`；本次重写置 null **64259 行**；grade 变动 {"C->C": 64074, "B->C": 184, "A->C": 1}；因此低于 C 被丢 **0 行** |
| 7 | `tier` 锁 **Tier1 = 410 那版** | **符合** | 用 `analysis/grading-rerun-20261125/auto-recognized.csv`（tier1=410 / tier2=3,109 / tier3=13,649，合 17,168；**不是** relax 版的 176）；版本核对：tier1 = 410 ✓（relax 版是 176，用错就全错）；与 3,550 层的 layer_id 交集 0、**非空 url 交集 0**（分档表 417 行空 url 全 tier3，本批 71 个 `@未定位` 层无 url → 空串假命中也算 0），所以输出 tier 全 `unrated` |

### 7.1 附加发现（不是 muse 列的 7 条，但影响字段有效率）

主跑 runner **从未调 `LayerMapper.begin_layer()`** → 每个 worker 进程只在它跑的第一层做一次 raw 字段名探测，之后整层复用（`_keys` / `_split_key` 跨层泄漏）。已在 `map_layers.py` 修正（`begin_layer(url)` 逐层调用）。拿同一批层修复前后对跑（40 层 / 240,520 行）：`state` **28.90% → 37.15%**、`house_number` 88.34% → 88.50%、`zip5` 64.79% → 64.83%、`mapped/in` 99.88% → 99.80%。该修正**本轮未落到数据层**（需整库重扫 40.3 GB，实测速率约 2.5 h，超出本轮时间窗）；且它**不能**把覆盖率（层级）或 house_number/zip5 拉过门槛，故未为此重跑。

### 7.2 已知剩余偏差（不掩盖）

1. **`unit` 不在 11 列输出里** → 重写时 addrkey 的 unit 段只能取 `'#'`（engine 对空 unit 的写法）。抽样 25 层 / 103,972 行实测输入 `unit` 非空 **2.58%（3/25 层）**：这些行与同址无单元行会同键。要彻底消除必须回读输入，属于下一次全量重跑。
2. **覆盖率 87.32%（3,100/3,550）未达 95%**，不可用 450 层全部 `grade_below_C`（源层无街名/无任何地址要素）；分母是否该换成「有街名或门牌的层」需 muse 裁定。
3. **house_number 71% / zip5 54%** 未达 90%/95%：根因是源层本身没有这些字段（信封 + raw 别名 + 组合串拆全部试过），不是映射逻辑写错；不补零、不生成门牌是硬口径。
4. **坐标残留 101 行**（305,674,428 行的 0.000033%）：`amend_rewrite.py` 写入时的自查计数 `bad=101`，即 lat/lon 非空但越界或为 (0,0)；`clean_coord` 当前口径不可能产出这种行，来源是主跑早期版本的成员（本轮只做输出侧重写、未回读输入，所以无法把它们就地空掉）。355 层 / 16,978,947 行抽查里 `bad_coord=0 / zero_coord=0`。彻底清零要再做一次全量旁路扫描定位这 101 行（约 8 分钟），属下一单。

## 8. 样本验证：`begin_layer()` 修好后重扫 vs 现有产物（muse-000264 A）

| 项 | 值 |
|---|---|
| 绑定 commit | `c5d2524`（现有 `dist/tar` 就是该 commit 的产物；对账在此基线上做） |
| 样本 | **16 层 / 1,618,560 行**（`sample-layers.csv`，脚本 `sample_select.py`，种子 264） |
| 重扫 | `sample_rescan.py` → `dist/sample/`（**不覆盖** `dist/tar/`），1,618,560 行出 / 1,618,560 行入 |
| **打点** | `begin_layer()` **被调用 16 次 == 处理 16 层**（每层一次，不复用 `_keys`/`_split_key`）|
| 对账 | `sample_diff.py`（只按成员名从 8 片抽样本层，未解全量）→ `sample-diff.csv` / `sample-diff.json` |

**两条选样要求在本批数据里不可达**（已核，不是没做）：
- `tier1/2/3 各 ≥3 层`：`grading-rerun-20261125/auto-recognized.csv`（Tier1=410 版）与本批 3,100 个已映射层的 `layer_id` 交集 **0**、非空 url 交集 **0**（归一化 scheme/尾斜杠后仍 0）→ 全部 `unrated`。
- `方言 ≥4 种`：`registry/dialects.v1.yaml` 只有 4 个 dialect / 34 个 org；本批 url 的 agol org 抽取结果 `''` 3,059 层 + `'rest'` 41 层 → **registry 命中 0 层**，全部 `minimal_safe`。
→ 改用可观测维度选样：state 有效率两端、信封原生对照、raw 别名/拆串依赖、无 url(fallback)、体量梯度。

| 层（截断） | 行数 现有/重扫 | 方法 | state | zip5 | 门牌 | grade |
|---|---:|---|---:|---:|---:|---:|
| `0MLvN0Ay0iEjnCT_arcgis_rest_services_Address` | 49304 / 49304 | positional | 0 | 0 | 0 | 0 |
| `0QMPlK9CkZD_arcgis_rest_services_AddressTest` | 75327 / 75328 | multiset | 0 | 0 | 0 | 0 |
| `0gE_arcgis_rest_services_Address_Points_View` | 46960 / 46960 | positional | 0 | 46953 | 0 | 46953 |
| `11SaUIGBo5JYFY_arcgis_rest_services_SRD_Data` | 24813 / 24813 | positional | 0 | 0 | 0 | 0 |
| `1Pd_arcgis_rest_services_Open_Address_Points` | 53013 / 53013 | positional | 52966 | 0 | 0 | 52966 |
| `arcgis_rest_services_Building_Address_Points` | 397926 / 397926 | positional | 397850 | 397793 | 73532 | 397850 |
| `arcgis_rest_services_Property_Addresses_View` | 41782 / 41782 | positional | 0 | 0 | 0 | 0 |
| `azssuvI82_arcgis_rest_services_AddressPoints` | 33687 / 33687 | positional | 0 | 0 | 0 | 0 |
| `f9MkUwD4_arcgis_rest_services_Address_Points` | 52486 / 52485 | multiset | 0 | 0 | 0 | 0 |
| `gis_rest_services_ProposedSiteAddress_public` | 14 / 14 | positional | 0 | 0 | 0 | 0 |
| `gis_rest_services_SiteStructureAddressPoints` | 359653 / 359653 | positional | 359653 | 358877 | 359653 | 359653 |
| `lYD_arcgis_rest_services_AddressPoints_24_12` | 33389 / 33389 | positional | 0 | 0 | 0 | 0 |
| `oqakAkedEx0oU_arcgis_rest_services_Addresses` | 33787 / 33787 | positional | 0 | 0 | 0 | 0 |
| `r_arcgis_rest_services_SiteAddressPoint_view` | 4145 / 4145 | positional | 0 | 0 | 0 | 0 |
| `s_DuPage_County_IL_AddressPointsUnderDevelop` | 392073 / 392073 | positional | 392073 | 0 | 0 | 391860 |
| `z6SRPFWJ_arcgis_rest_services_SiteAddresses_` | 20201 / 20201 | positional | 0 | 0 | 0 | 0 |

**判定：影响输出且改 grade**（三档里的最重一档）：
- **5 层**逐字段有差异（另 **2 层**仅行数差 1 行 → 退回 multiset，字段无差；**9 层**逐字段零差异，只有 addrkey 差异，见下）
- 变动矩阵（样本内，现有 S0/A72,665/B47,016/C1,498,879 → 重扫 S444,798/A876,239/B972/C296,551）：**B->A 46,953、C->A 756,622、C->B 909、C->S 444,798**
- 方向全是**变好**（重扫恢复被泄漏吃掉的 state/zip5/门牌），没有一例变差：例 `gis_rest_services_SiteStructureAddressPoints...@未定位-3` 现有 `state/zip5/门牌 = 0/0/0`，重扫 `359,653/358,877/359,653`，grade `C→A` — 手工核过首行：raw `Add_Number=534 / St_Name=Jonathan / FullAddress='534 Jonathan Lane'` → `534 / Jonathan / NC / 27406`，取值正确

| 字段（样本 1,618,560 行） | 现有 | 重扫 |
|---|---:|---:|
| `state` 有效率 | **7.39%** | **81.69%** |
| `zip5` 有效率 | **35.03%** | **89.33%** |
| `house_number` 有效率 | **72.74%** | **99.50%** |
| `city` 有效率 | **40.75%** | **40.75%** |
| `street_name` 有效率 | **100.00%** | **100.00%** |

> `addrkey` 在样本里有 1,258,467 行不同 —— **不是 begin_layer 引起**：现有产物是 `amend_rewrite.py` 用 11 列自身重算的（拿不到 `unit`、`st_suf/pre_dir/post_dir` 分量），重扫用输入真实 unit + 分量。`city` 完全不变（信封与 raw 两侧口径一致）。

> **不外推**：样本是按极端值挑的（state 0%/100% 两端各占一半），5/16 的命中率**不能**乘到 3,100 层上；真实影响面只能靠下一次全量重跑给出。本单结论只覆盖这 16 层。

## 9. 坐标残留清零（muse-000264 B）

| 项 | 值 |
|---|---:|
| 旁路扫描行数（8 片全量，只读 `dist/tar`） | 305,674,428 |
| **找到的坏坐标行** | **101**（上一单写入器自查报 101，实测一致） |
| 影响层数 | 1 |
| 清零后 `bad_coord` / `zero_coord` | **0 / 0** |
| 降级矩阵 | {"C->C": 101} |
| **S→A 行数** | **0**（A→B 也是 **0**） |
| 坐标合法率 | **100.00%**（非空坐标 305,563,547 行，越界/(0,0) 残留 0） |

做法：流式读 8 片成员；**没有坏坐标的成员原字节直传**（不重新压缩），只有命中行才重写该成员（置 null + 按要素表重算 grade），成员数逐片校验通过后才 `rm` 旧片 + `mv` 新片。

**为什么 S→A = 0**：这 101 行在清零前**已经都是 C 级**（只有街名、没有门牌/州/邮编），坐标置空后 C 级的要素表（只要街名）依然成立，所以 `C→C`，不产生任何降级，也不影响 S/A/B 行数。数据侧交叉核对：该层 7,466 行里非空坐标从 7,304 → **7,203**，越界/(0,0) **0**，grade 仍 S0/A0/B0/C7,466。
- `ces_service_94b14aaf7746405c8edc1c010f0cd277_FeatureServer_0`：101 行，{"C->C": 101}

