# 组合拳②：把 P7 的 321 层字段名写进别名表（只开不合）

> 一句话：**按派单的「非 P7 层建键结果不许变化」硬口径，只有 19 个字段名能安全入表，P7 的 321 层里因此只有 24 层建出键**。
> 若允许「旧键被改」，可入表 27 个、P7 能建键 83 层，但非 P7 层会有 975 层的旧键被改写（1,024 行）。
> 严格「差异 = 0」在**全局别名表**这一机制下结构上不可达（任何语义正确的门牌/街名别名，都会让原本出不了键的层开始出键）——这一点需要 Muse 拍板，本 PR 只开不合。

- 基线：`origin/main = a2e3c887294008b7227fb14bb7b5d0e32bc86a83`（= PR #52 merge commit）
- 分支：`feat/combo-step2-alias-20261125`
- 工作树：`/data/workspace/wmd-combo-step2`（从 `origin/main` 新建，未复用 step1 工作区）
- 心跳：`w2-20261125-combo-step2`（qid `2ea7fa58` = md5(`w2-20261125-combo-step2`)[:8]）
- 改动面：`engine/dialects/sources.v1.yaml` 只加一条 `p7-alias-ext-v1`（别名来源）+ 本目录分析产物。**没改** engine 代码、registry、collector、schema、账本、Release、网站，没起 Actions，没重跑分档。

---

## 1. 输入与复算一致性（这一步不重新判 P7）

| 项 | 值 |
|---|---|
| P7 层清单 | `analysis/combo-step1-20261125/patterns.csv`，`pattern_id == P7` → **321 层**（与 step1 报告一致） |
| 判据复用 | 直接 import step1 的 `combo_classify.role_of_field()/classify()`，阈值一个字没改；重跑分类得 **321 层仍全部判 P7，0 层分歧** |
| 真实值来源 | `analysis/coord-samples-20261124/samples/*.csv`（59 文件，**15,293 行 / 321 层**，本目录只取 P7 层的行） |
| 字段名来源 | `survey/ng911/samples.csv.gz`（60,697 层完整字段清单；P7 层 **321/321 命中原生记录**，无一需要 fallback） |
| 层号 | `failed-layers.csv` / `p7-alias-applied.csv` 同时给 `layer_id`（`FeatureServer/N`、`MapServer/N`）与完整 `url`；同一服务的多个层 `layer_id` 相同，**唯一定位一律以 `url` 为准** |

---

## 2. 别名抽取：不是「照抄 classify 的 fields[0]/[1]」

step1 的 `classify()` 是**按列单独**过值形态，多候选时取 schema 顺序第一个 —— 实测把 `TRANUM`、`EMPNUM`、`Number_of_Vehicles` 当成门牌列（`TRANUM|SITUS_SUFF` 这一对出现在 20 层）。
本单改成**行级共同成立**再定列（不放松，只收紧）：同一行里门牌列值形如 `^\d{1,6}[A-Za-z]?$`、街名列有字母且不是纯门牌/邮编，两层同时成立的行占比 ≥0.5 才算该层的「门牌列 + 街名列」。

- 逐层重选后：**198/321 层**有 ≥0.5 的行级成立对（`_work/p7_pairs.csv`）；115 层根本没有成立的对（多为整串地址列 / 业主列 / 只有街名）。
- 由此得到 **61 种字段写法**（门牌 41 + 街名 20）；按 `addr_key()` 的归一规则（去非字母数字、转小写）去重 → **34 种**；再剔掉 registry 里已有的（`ADDRNUM`、`HOUSE_NUM`、`SITUS_NUM`、`STREET`、`ST_NAME`、`STREETNAME`…）→ **27 条候选**。

### 边界过滤（派单第 3 条）

- 名字像业主/邮寄/联系地址 → 不进：`OWN_ADDR1`、`OWN_ADDR2`、`Mailing_Address*`、`MAD_MAIL_ADDR2`、`OwnerAddre` 等，进待定表。
- 整串地址列（`FULLADDR`、`ADDRESS`、`ADDRESS1`、`ADDRESS_LINE1/2`、`FULL_ADDR`、`PRCL_ADDR`、`Site_Street_Address1`…）→ 不进：它们要**切分**，不是别名能解决的，进待定表。
- 修饰列（`STREETSUF`、`ADDR_ST`=HWY/RD、`STREET_TYP`、`ADDR_SF`）→ 不进。
- 区间/起止列（`HOUSENO_R_`、`HOUSENO_R_TO`、`START_NUM`、`BEGNUMB`）→ 不进（P8 型）。
- 结构 ID / 计数（`ROW_NUM`、`BLKNUM_T`、`BLDG_NUM_O`、`STRUCT_NUM`、`NUMB_NONFATAL_INJR`、`CumulativeHouseholds`、`Number_Tra`、`PropertyClassNum`）→ 不进。
- 人工复核剔除 4 条：`V_StName`（值是人名 Michael/Ashton）、`Street_Nam`（值 98% 纯数字）、`STREET_NAM`（有层值纯数字）、`ADDRNUMTT`（TT 含义不明）。

---

## 3. 回归筛查：逐别名在 695,706 条非 P7 行上单测

这是本单最关键的一步，也是结论被推翻的地方。判据来自派单 4.d：**非 P7 层的建键结果不许变化**。

对 27 条候选逐条单独加入 `ROLES`，扫 coord-samples 全部非 P7 行（13,532 层 / **695,706 行**），统计：

- `harm` = 旧键非空、新键与旧键**不同**（旧键被改）
- `loss` = 旧键非空、新键为空（键丢失）
- `gain` = 旧键空、新键非空（纯增益）

| 判定 | 条数 | 说明 |
|---|---:|---|
| keep（harm=0 且 loss=0） | **19** | 12 门牌 + 7 街名 |
| drop（harm>0） | **8** | 含增益最大的 `HouseNumber`（harm 211 行 / gain 37,330 行） |

被剔除的 8 条（完整数字见 `_work/alias_screen.csv`、`pending-uncertain.csv`）：
`HouseNumber`(211)、`HOUSE_NO`(240)、`HSE_NUM`(150)、`House`(105)、`HouseNumbe`(82)、`AddressNum`(31)、`STREETNO`(27)、`situs_street`(178)。

> harm 的机制：`addr_key()` 是「行内第一个命中角色的字段胜出」。加一个别名后，如果它在该行的字段顺序里排在原来命中的字段前面，就会把键里的门牌/街名换掉。语义上未必更差（例如 `HouseNumber` vs `HOUSE_NUM`），但派单要求「不许变化」，就一律剔除。

---

## 4. 入表的别名（19 条，去重前 61 → 去重后 27 → 回归通过 19）

`engine/dialects/sources.v1.yaml` 新增条目 `p7-alias-ext-v1`（`family: alias_extension`，`adapter: none`，不带几何/精度声明）：

```yaml
number: [ADDRNUM_1, ADDR_NUMB, ADDR_STR_NBR, ANUMBER, Addr_Number, GM_HSE_NUM, HOUSE_NUMB,
         HSE_NUMB, PROPERTYHOUSENUM2, SA_House_N, STREETNUMBER1, addr_numbe]      # 12
street: [CC_ST_NAME, Loc_Street, PWA_FULLSTREET, SA_Street_, STREETALL, ST_NAME_COMPLETE,
         Street_Road_Name]                                                          # 7
```

diff 只含新增行（`git diff` 里没有删除行、没有改既有条目）。

**这 19 条里有 16 条在 coord-samples 非 P7 行上「零命中」**（它们的注入价值只体现在 P7 的 321 层上），3 条产生纯增益：`ANUMBER` 632 行、`HOUSE_NUMB` 536 行、`CC_ST_NAME` 100 行。

---

## 5. 验收 a：P7 的 321 层建键结果

口径：`addr_key()` **逐字照抄** `sandbox/coord_evidence.py`（含那条「首段门牌 + 含 5 位 zip 才兜底解析」的分支），`ROLES` = registry 别名（old） + 本单新增别名（new）。成功 = 该层真实样本行里至少 1 行出「门牌+街名」键。

| 口径 | 建键成功 | 键形合法 | 失败层 |
|---|---:|---:|---:|
| **本 PR 入库的 19 条（严格口径）** | **24 / 321** | 24 / 321 | 297 |
| 对照：27 条全上（含 8 条被回归剔除的） | 83 / 321 | 82 / 321 | 238 |
| 对照：不加任何别名（现状） | 0 / 321 | 0 / 321 | 321 |

- 24 层成功：15,293 条样本行里 **1,066 行**出键，其中 **982 行键形合法**（门牌段是纯门牌、街名段有字母）。
- 逐层明细：`p7-alias-applied.csv`（含 `old_key_rows` / `new_key_rows` / `new_valid_key_rows` / 选出的门牌列与街名列 / 是否命中新别名）。
- 失败清单：`failed-layers.csv`（297 行，每行带 `layer_id` + `url` + 原因）。

失败原因分布（`failed-layers.csv` 的 `reason` 列按类归并）：

| 原因 | 层数 |
|---|---:|
| 该层找不出「门牌列+街名列」组合（列名语义不过白名单，或行级值形态不成立） | 114 |
| 选出的门牌/街名列都进了待定表（业主/邮寄列、整串地址列、区间列、ID 列） | 49 |
| 门牌列在待定表（`STREETNO` 11、`HOUSE_NO` 7、`ROW_NUM` 6、`ROADNUMBER` 5、`BLKNUM_T` 4、`HouseNumber`/`HSE_NUM`/`streetNo` 各 3…） | 93 |
| 街名列是整串地址列（`addr_state` 10、`FULLADDR` 7、`situs_street` 6、`FULL_ADDR` 3、`ADDRESS_LINE1` 2…） | 41 |

> 注意 `addr_state`（列名看着像街名、值是 `TX`/`UT`）这类是 step1 判据的固有噪声：值形态过、语义不对，本单靠白名单挡在门外，没有改判据。

---

## 6. 验收 b：别名表 diff

- 新增条目 1 条（`p7-alias-ext-v1`），新增别名 **19 条**（12 门牌 + 7 街名），**0 删除、0 修改**。
- 去重前：61 种写法（41 门牌 + 20 街名）；按 `addr_key` 归一规则去重后 34；剔除 registry 已有 7 种 → 27 候选；回归剔除 8 → **19 入表**。

## 7. 验收 c：待定表

`pending-uncertain.csv` 共 **98 条**：语义待定 90（整串地址列/业主邮寄列/区间列/ID 列/名字不明确的纯数字列）+ **回归不通过 8**。每条带 `reason`。

## 8. 验收 d：回归对照（**未达标，如实上报**）

范围：coord-samples 全部非 P7 行（13,532 层 / 695,706 行）+ `survey/ng911` 全量层（60,373 层 / 83,448 条原始记录，×3 条/层）。

| 口径 | 非 P7 差异行 | 差异层 | 旧键被改 | 键丢失 | 纯增益 | ng911 差异层 | ng911 旧键被改 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 严格口径（19 条入库） | **1,268** | 26 | **0** | **0** | 1,268（1,229 合法） | 109 | **0** |
| 对照（27 条全上） | 45,707 | 975 | 1,024 | 0 | 44,683 | 547 | 113 |

- **「差异 = 0」没有做到**（1,268 行 / 26 层）。这 1,268 条全部是 `旧键空 → 新键非空` 的纯增益，没有一条旧键被改或丢失（`assert_no_key_overwrite: true`）。
- 结构性原因：别名表是**全局**的（`sandbox/coord_evidence.py:roles_of()` 把 registry 所有方言的别名取并集；`engine/inlet.py` 同理按方言取）。任何语义正确的门牌/街名别名，只要别的层里恰好有这个列名 + 一个街名/门牌列，那层就会开始出键 —— 这是「别名扩展」的定义，不是 bug。要让「非 P7 层一字不变」成立，只能：
  1. **接受「只增不改」口径**（0 旧键被改 / 0 键丢失 / 纯增益单列），或
  2. **把别名绑定到 P7 这 321 层**（按层赋 `dialect_id=p7-alias-ext-v1`，需要改采集/分档侧赋值逻辑 —— 本单明令禁止），或
  3. 改 `addr_key()` 的匹配优先级（「行内第一个命中」→「名字最长/最具体者胜」）—— 也是代码改动，超出本单范围。
- 本 PR 没有自己放宽这条：**入库的是 19 条，报告同时给出 27 条的对照数字**，等 Muse 选 1/2/3。

## 9. 与本轮目标（Tier1 176 → ？）的关系

**这 19 条别名目前不会直接抬高 Tier1**，原因要说清：

- E7 证据（`sandbox/coord_evidence.py:roles_of()`）**只读** `registry/dialects.v1.yaml`，不读 `engine/dialects/*.yaml`。本单按派单把别名写进 engine 表，作用面是 `engine/inlet.py:map_row`（按方言映射）。
- 要让 E7 吃到这 19 条，需要二选一（都不在本单授权内）：
  1. 在 `sandbox/coord_evidence.py:roles_of()` 里追加载入 engine 表（改 code）；
  2. 由 `registry/evaluator.py` 的「全局别名池」合并 engine 表（改 registry 侧逻辑/重新生成 registry）。
- 即便追加载入，本口径下 P7 只有 24 层能出键；对照口径 83 层。相对 1,340 层缺口（Tier1 1,831 期望 vs 176 现状），这一支最多补 24~83 层，**远不足以填平缺口**——大头仍在 P1/P5（切分/拼列，597 层）与整串地址列。

---

## 10. 复算（全本地、无网络，约 1 分钟）

```bash
cd analysis/combo-step2-20261125
python3 alias_extract.py                  # step1 口径复算：321 层 / 0 分歧（_work/p7_fields.csv）
python3 alias_pairs.py                    # 行级共同成立重选列（_work/p7_pairs.csv，198 层有对）
python3 alias_select.py                   # 白名单 / 待定（_work/alias_final.json，61 写法 → 27 候选）
python3 alias_screen_regression.py        # 逐别名回归（_work/alias_screen.csv，19 keep / 8 drop）
python3 verify_keys.py                    # 验收 a+b+d（321 层 / 两处回归）
ALIAS_PROFILE=all python3 verify_keys.py   # 对照口径：27 条全上（会重写下面三个 CSV 为对照结果，最后再用默认口径跑一遍）
python3 merge_pending.py                  # 合成 pending-uncertain.csv（98 条）
```

产物：`REPORT.md`、`p7-alias-applied.csv`（321 行）、`failed-layers.csv`（297 行）、`pending-uncertain.csv`（98 行）、5 个脚本；`_work/` 被 `.gitignore` 忽略（中间件）。

## 11. 未做 / 不越界声明

- 没改 `registry/dialects.v1.yaml`（sha256 与基线一致）、没改 `engine/*.py`、没改 collector/schema/账本/Release/网站，没起 Actions，没重跑分档。
- 没有把「整串地址列」当街名加进别名表（那是切分路线，属组合拳后续步骤）。
- 没有为了让 321 层的数字好看而放宽任何阈值：24/321 就是严格口径下的真实结果。
