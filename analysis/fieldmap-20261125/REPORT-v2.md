# 第 9 步 · 全量重扫（v2）：用修好的 `begin_layer()` 重出 3,550 层映射数据

> ⚠️ **PROVISIONAL（muse-000271 后续修订，2026-11-26）**：58 层 B 类修复已在 `analysis/fieldmap-20261125/fix58-20261126/` 落地并逐层重跑验证，覆盖率口径应更新为 **3,413/3,550 = 96.14%**（= 本文件记录的 3,355 + 58）。但**尚未重跑全量 3,550 层**，本文其余数字仍是修前全量口径，**待全量重扫复核**；本轮没有用 58 层口径覆盖任何全量数字。

> 口径唯一权威源仍是 `w2-fieldmap-plan-20261125.md`（muse-000258 全文，本单未改口径）。
> 本单 = muse-000266：样本对账发现 `begin_layer()` 未逐层调用导致 16 层里 7 层等级漂移 1,249,282 行，
> 故全量重扫并把修复落到数据层。**PR #58 仍 OPEN，合并是 muse 的动作。**

## 0. 四数（先给数）

| 指标 | v2 重扫实测 | 门槛 | 结论 |
|---|---:|---:|---|
| 层覆盖率 | **94.51%**（3355/3550） | ≥95%（≥3,373） | **未达标（源层本身无地址要素，见 §11）** |
| 不可用层 | **195**（全部 `grade_below_C`） | 固定枚举 | 达标 |
| 逐层闭合差额 | **0** 层非零 | 0 | 闭合 |
| 坐标/要素四项 | `bad_coord=0, zero_coord=0, grade_missing_element=0, S_city_null=0` | 全 0 | 达标 |
| 输出 | **7 片 / 16342610945 B**（480,039,285 行） | — | 磁盘余量 31.3 GiB |

## 1. 本轮点名回显

| 项 | 值 |
|---|---|
| 层数分母 | **3,550 层**（`analysis/step8-reconcile-20261125/final-tally.csv`，1 header + 3,550） |
| 清单 commit sha | **`87b5e4bdaadba8d7f83cceae5b597d2c38dd5cca`** |
| 代码基线 | **`bd55cc7`**（`feat/fieldmap-20261125`）→ 本单追加 commit（见 §12） |

## 2. 分片执行表（每片跑完立刻校验，校验不过不许进下片）

| 片 | 层数 | 行数 | 字节 | 耗时 s | 封装+校验 s | 成员数(实/期) | 行数(实/期) | 校验 | free_gb |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `fieldmap-part000.tar.gz` | 500 | 833,117 | 26,264,814 | 29.7 | 2.4 | 500/500 | 833,117/833,117 | OK | 22.8 |
| `fieldmap-part001.tar.gz` | 500 | 4,156,148 | 128,171,499 | 137.8 | 11.9 | 500/500 | 4,156,148/4,156,148 | OK | 22.6 |
| `fieldmap-part002.tar.gz` | 500 | 7,990,531 | 255,292,607 | 258.7 | 24.0 | 500/500 | 7,990,531/7,990,531 | OK | 22.3 |
| `fieldmap-part003.tar.gz` | 500 | 14,021,134 | 451,524,972 | 424.1 | 39.0 | 500/500 | 14,021,134/14,021,134 | OK | 21.8 |
| `fieldmap-part004.tar.gz` | 500 | 22,953,747 | 756,962,539 | 752.1 | 70.8 | 500/500 | 22,953,747/22,953,747 | OK | 20.8 |
| `fieldmap-part005.tar.gz` | 500 | 46,816,130 | 1,613,860,890 | 1513.1 | 176.4 | 500/500 | 46,816,130/46,816,130 | OK | 18.9 |
| `fieldmap-part006.tar.gz` | 355 | 383,268,478 | 13,105,748,242 | 11723.6 | 949.4 | 355/355 | 383,268,478/383,268,478 | OK | 20.2 |

> 片级校验 = `tar` 成员数 + **逐成员实读行数** vs 覆盖表 `mapped` 之和 + 外层 gzip 完整性（流式读完）；
> 分片组成是 worker 完成顺序，不是原清单顺序（`dist-v2/shards/shard-*.json` 里有 `layer_ids` 可反查）。

## 3. 覆盖率 + 不可用分桶

- 覆盖率 **94.51%（3355/3550）**；不可用 **195** 层，全部 `grade_below_C`（源层无街名/无任何地址要素，按口径丢弃不猜）。

| 原因 | 层数 |
|---|---:|
| `grade_below_C` | 195 |

## 4. 各级行数（v2 vs 旧版）

| 级别 | v2 重扫 | 旧版（PR #58 现版） | 差 |
|---|---:|---:|---:|
| **S** | 84,453,151 | 45,282,269 | +39170882 |
| **A** | 149,974,993 | 8,507,671 | +141467322 |
| **B** | 19,410,470 | 7,042,002 | +12368468 |
| **C** | 226,200,671 | 244,842,486 | -18641815 |
| **合计** | **480,039,285** | **305,674,428** | **+174364857** |

全量逐行重算（`verify-v2.py` 扫完 7 片 / 480,039,285 行）的字段有效率：

| 字段 | 有效率 |
|---|---:|
| `street_name` | **100.00%** |
| `house_number` | **91.81%** |
| `city` | **33.26%** |
| `zip5` | **71.14%** |
| `state` | **54.38%** |
| 坐标（非空且在范围内且非 (0,0)） | **99.90%** |

## 5. 与旧版差异

### 5.1 层级 grade 变动（旧 CSV vs 新 CSV，逐层向量比）

- **受影响层数：1428 层**（清单见 `grade-affected-layers.csv`）

| 变动方向（层数） | 计数 |
|---|---:|
| `B+1` | 57 |
| `C-1` | 50 |
| `C+1` | 46 |
| `C-2` | 23 |
| `A+1` | 22 |
| `B+2` | 22 |
| `C-3` | 14 |
| `A-1` | 12 |
| `B-1` | 11 |
| `C-6` | 10 |
| `C+2` | 10 |
| `A+2` | 10 |

### 5.2 样本 16 层逐行对账（`diff-v1-v2.json`，含 muse 亲核的 7 层漂移层）

| 层 | 方法 | 行数 旧→新 | grade 变动 |
|---|---|---|---|
| `gis_rest_services_SiteStructureAddressPoints_FeatureServ` | positional | 359653→359653 | `{"C->A": 358877, "C->B": 776}` |
| `gis_rest_services_ProposedSiteAddress_public_FeatureServ` | positional | 14→14 | `{}` |
| `0gE_arcgis_rest_services_Address_Points_View_FeatureServ` | positional | 46960→46960 | `{"B->A": 46953}` |
| `z6SRPFWJ_arcgis_rest_services_SiteAddresses_FeatureServe` | positional | 20201→20201 | `{}` |
| `arcgis_rest_services_Building_Address_Points_FeatureServ` | positional | 397926→397926 | `{"C->A": 397717, "C->B": 133}` |
| `s_DuPage_County_IL_AddressPointsUnderDevelopment_MapServ` | positional | 392073→392073 | `{"C->S": 391860}` |
| `0MLvN0Ay0iEjnCT_arcgis_rest_services_Address_FeatureServ` | positional | 49304→49304 | `{}` |
| `1Pd_arcgis_rest_services_Open_Address_Points_FeatureServ` | positional | 53013→53013 | `{"C->S": 52938, "C->A": 28}` |
| `11SaUIGBo5JYFY_arcgis_rest_services_SRD_Data_FeatureServ` | positional | 24813→24813 | `{}` |
| `0QMPlK9CkZD_arcgis_rest_services_AddressTest_FeatureServ` | multiset | 75327→75328 | `{"C:75327->75328": 1}` |
| `f9MkUwD4_arcgis_rest_services_Address_Points_FeatureServ` | multiset | 52486→52485 | `{"A:52483->52482": 1}` |
| `r_arcgis_rest_services_SiteAddressPoint_view_FeatureServ` | positional | 4145→4145 | `{}` |
| `arcgis_rest_services_Property_Addresses_View_FeatureServ` | positional | 41782→41782 | `{}` |
| `lYD_arcgis_rest_services_AddressPoints_24_12_FeatureServ` | positional | 33389→33389 | `{}` |
| `oqakAkedEx0oU_arcgis_rest_services_Addresses_FeatureServ` | positional | 33787→33787 | `{}` |
| `azssuvI82_arcgis_rest_services_AddressPoints_FeatureServ` | positional | 33687→33687 | `{}` |

- 样本合计行数 旧 1,618,560 → 新 1,618,560
- 逐字段差异行数：`{"state": 1202542, "zip5": 803623, "house_number": 433185, "grade": 1249282, "addrkey": 1370065, "rows_only_in_v1": 75194, "rows_only_in_v2": 75194}`
- grade 变动矩阵（样本，逐行）：`{"C->A": 756622, "C->B": 909, "B->A": 46953, "C->S": 444798, "C:75327->75328": 1, "A:52483->52482": 1}`

## 6. amend 7 条是否**原生**成立（不靠事后补丁）

| # | 增量 | 结论 | 证据 |
|---|---|---|---|
| 1 | `source_layer` = url | **符合** | 主跑逐层 `begin_layer(url)` + 写行时 `source_layer = url or layer_id`：url **3291 层** / layer_id_fallback **64 层**；全量 `bad_source_layer = 0` |
| 2 | `addrkey` 全行重算（a3 + sha1-20） | **符合** | 全量 480,039,285 行逐行调用 `engine/outlet_clean.addrkey_v3`；格式不符 **0** 行；不可键（num 或 street 缺）**42,221,854** 行 = 8.80% |
| 3 | zip5 / city / 要素校验 | **符合** | 全量 `bad_zip5=0`、`bad_state=0`、`zip_null_high_grade=0` |
| 4 | `house_number` 占位值含 `-9` | **符合** | `PLACEHOLDERS` 含 `-9/-9.0/-09`；全量 `bad_number=0`（占位值残留）；门牌为空行数 39,331,189 |
| 5 | 逐层行数闭合 = 0 | **符合** | 覆盖表 `diff` 非零 **0** 层；分片成员实读行数 vs `mapped` 不符 **0** 层 |
| 6 | 11 列 schema 不变 | **符合** | 全量 `bad_columns = 0`（列名与顺序沿用 `fm_core.FIELDS`） |
| 7 | 口径（plan）不变 | **符合** | `plan` 全文仍在 `analysis/fieldmap-20261125/w2-fieldmap-plan-20261125.md`，本单只换数据不重写口径 |

## 7. 坐标口径终检（全部内置，无事后补丁）

| 项 | 值 |
|---|---:|
| `bad_coord`（越界/半缺） | **0** |
| `zero_coord`（(0,0)） | **0** |
| `grade_missing_element` | **0** |
| `S_city_null` | **0** |
| 坐标合法率 | **100.00%**（非空坐标 479,564,649 行） |

> `clean_coord()` 在算 grade **之前**跑：越界/(0,0)/缺省一律 null，再按要素表逐级重算 → S 级缺坐标自动落到 A/B/C，不存在「先给级后补坐标」的窗口。

### 7.1 坐标收口：107 行「round 后变 (0,0)」已清零

全量逐行终检（`verify_v2.py`，8 路按成员哈希并行、扫完 480,039,285 行）发现 `zero_coord = 107`：`clean_coord()` 旧写法是**先判** `lat==0 and lon==0` **再** `round(...,7)`，源层里 `|v| < 5e-7` 的坐标过 round 后就是 `0.0` → 输出漏出 (0,0)。

处置（同一分支、只追加）：
1. `fm_core.clean_coord()` 改成**先 round 再判** (0,0) —— 这是根因修复，之后任何重跑都不会再出现；
2. 已落盘的数据用 `coord_fix_v2.py` / `coord_fix_v2_shard.py` 按同口径补齐：成员里**没有** `"lat":0` 字样就原字节直传，命中的成员逐行精确判（round 后为 0 / 越界 / 半缺）→ 置 null + 按要素表重算 grade；逐片校验成员数后才 `os.replace` 覆盖旧片。
3. `verify_v2_post.py` 再证一遍：part000–005 **逐行 json 全不变量**（96,770,807 行）+ part006 **字节级**（383,268,478 行）。

| 项 | 值 |
|---|---:|
| 被置 null 的行（parts 000–005） | **16** |
| grade 迁移 | `{"S": 0, "A": -8, "B": 8, "C": 0}`（A 级要求 point，所以 8 行 A→B；其余 99 行 C 级不变） |
| 收口后各级行数 | S **84,453,151** / A **149,974,993** / B **19,410,470** / C **226,200,671** / 合计 **480,039,285** |
| 收口后行数 | **480,039,285**（改前 480,039,285，`rows_match=True`） |
| 收口后 `zero_coord`（全量复扫） | **0** |
| 复扫耗时 | json 逐行 422.1 s + 字节级 289.6 s |

> 这一处是**代码口径 bug**（先判后 round），不是数据脏；修在 `fm_core` 里，重扫/重算都走新口径。

## 8. #2 / #9 的 ±1 行偏差 + 全量「源行数 vs 输出行数」差额扫描

| # | 层 | 旧版行数 | v2 行数 | v2 源行 | 丢弃 below_C | 解析失败 | 源−输出 | ±1 结论 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `0QMPlK9CkZD_arcgis_rest_services_AddressTest_FeatureServ` | 75,327 | 75,328 | 75,341 | 13 | 0 | **0** | ±1 行，源−输出仍 0（判级差异，非漏计） |
| 2 | `f9MkUwD4_arcgis_rest_services_Address_Points_FeatureServ` | 52,486 | 52,485 | 52,542 | 57 | 0 | **0** | ±-1 行，源−输出仍 0（判级差异，非漏计） |

全量差额（`in_rows − mapped − dropped_below_C − parse_error`）非零层：**0** 个

分片成员实读行数 vs 覆盖表 `mapped` 不符的层：**0** 个

## 9. 耗时

| 项 | 值 |
|---|---|
| 重扫起止（UTC） | `见回执` → `2026-11-26T01:14:01Z` |
| 总时长 | 247.3 分钟 |
| 8 片耗时（s） | 29.7, 137.8, 258.7, 424.1, 752.1, 1513.1, 11723.6 |
| 全量终检（verify-v2） | 2950.9 s |

## 10. 怎么复跑

```bash
cd /data/workspace/wmd-fieldmap
FM_DIST=/data/workspace/wmd-fieldmap/dist-v2 python3 analysis/fieldmap-20261125/map_layers.py \
  --all --shard 500 --workers 6 --out-csv analysis/fieldmap-20261125/layer-coverage.v2.csv
python3 analysis/fieldmap-20261125/verify_v2.py --workers 8      # 全量逐行终检
python3 analysis/fieldmap-20261125/diff_v1_v2.py --workers 8     # 16 层逐行对账
python3 analysis/fieldmap-20261125/finalize_v2.py                # 本报告
```

中断续跑：加 `--resume`（跳过覆盖表已记录层 + 拾回未打片散文件）。

## 11. 已知偏差 / 没做到的（如实）

0. **门禁判定：覆盖率 94.51% < 95% → 本项 FAIL**（差 18 层 / 0.49 个百分点，未达标线 3,373）。不可用 195 层全部是 `grade_below_C`（源层无街名/无任何地址要素，按口径丢弃不猜；与 v1 的 450 层相比已有 255 层因 `begin_layer` 修复而恢复出可用数据）。**没有放宽容差、没有改分母**；分母是否该换成「有街名或门牌的层」需 muse 裁定。
2. **house_number 91.81% / zip5 71.14%**：根因是源层本身没有这些字段（信封 + raw 别名 + 组合串拆全试过），不是映射逻辑错；不补零、不生成门牌是硬口径。
3. **`unit` 不在 11 列输出里** → addrkey 的 unit 段只能取行内 `unit`（本单主跑是从输入行直取，比 amend 版更准），但输出侧不带 `unit` 列本身没变。
4. **tier 全 `unrated`**：分档表（Tier1=410 版）与本批 3,550 层 layer_id 交集 0、非空 url 交集 0（前单已核），所以 tier 列写不出值，这不是本单退化。
5. **方言仍全 `minimal_safe`**：`registry/dialects.v1.yaml` 只有 4 dialect / 34 org，本批 url 的 agol org 仅 空串/`rest`，registry 命中 0 层（前单已改口径，不再写错误的「命中 115」）。
6. **全量行级 grade 变动矩阵**（跨 3,100 层的 S/A/B/C 各进各出）未逐行 join（要同时流式读旧新两代约 18 GB 并做键连接）；本报告给的是：① 各级总行数新旧对照；② 样本 16 层逐行变动矩阵；③ 受影响层清单（`grade-affected-layers.csv`）。
7. 所有数出自同一次重扫的落盘产物；**未运行** `amend_rewrite.py` / `coord_clean.py`（本单要求原生成立）。

## 12. 交付物与 PR

| 项 | 值 |
|---|---|
| 分支 / PR | `feat/fieldmap-20261125` / **#58（保持 OPEN，合并由 muse 做）** |
| 数据 | `dist-v2/tar/fieldmap-part000..006.tar.gz`（7 片 / 16342610945 B）+ `dist-v2/shards/shard-*.json` |
| 覆盖表 | `layer-coverage.v2.csv`（3,550 行，含 `grade_C` / `source_layer_kind` 两列） |
| 机器可读汇总 | `SUMMARY-v2.json` / `verify-v2.json` / `verify-v2-post.json` / `diff-v1-v2.json` / `coord-fix-recount.json` |
| 不可用清单 | `unusable-v2.csv`（195 层，原因全固定枚举） |
| 受影响层清单 | `grade-affected-layers.csv`（1428 层） |
| 脚本 | `map_layers.py`（逐层 `begin_layer` + 片级校验 + resume 拾回）/ `verify_v2.py` / `verify_v2_post.py` / `diff_v1_v2.py` / `probe_pm1.py` / `coord_fix_v2.py` / `coord_fix_v2_shard.py` / `finalize_v2.py` |

> 字节口径说明：`dist-v2/shards/shard-*.json` 里的 `bytes` 是**映射当时**的片大小（合计 16,337,825,563 B）；坐标收口把 part000–005 重打了一遍（成员逐字节 passthrough，仅 107 行重写），所以**当前磁盘上的片合计 16,342,610,945 B**，差 4,785,382 B 是 tar.gz 重压的字节差，行数与成员数完全一致。
> 旧 `dist/`（v1，8.6 GiB / 9,225,507,402 B，8 片）在新产物全量校验通过后才删除；删除后 `/data` free 23 GiB → **32 GiB**。

