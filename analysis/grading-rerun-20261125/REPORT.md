# 第 9 步 · 分档重跑（组合拳收尾）· 新 registry + 占位跳过 + 分母剔除 198 层 + DEFERRED-B

> **一句话**：把 ③ 遗留的那一行 import 补上以后，E7 真正吃到了「占位跳过 + P1 拆串」——**Tier1 176 → 410 层**（+234，涨 235 / 跌 1），
> 其中**占位跳过 +35 层、P1 拆串 +201 层、engine 角色表合并 −2 层**；分母口径剔除 198 层（P8 22 + P6/P9/P11/P12 176）**一层都没抬 Tier1**，
> 但吃掉了 2 层（这两层正是拆串抬上来、又被剔除移出可验分母的同一批）→ **可验口径 408 层**。
> 四数对账（17,168 / declared 984,719,364 / 198 层逐条归因 / delta_kind 计数）**全部对上**（`reconcile.json: all_checks_pass=true`）。

- 基线：`origin/main = 267de21`（PR #55 merge）；分支 `feat/grading-rerun-20261125`，工作树 `/data/workspace/wmd-grading-rerun`
- 对照基线：`analysis/auto-spatial-relax-20261125/auto-recognized.csv`（第 7 步 E3+E7 放宽，**Tier1 = 176**，本文件**不重算**，只引用）
- 边界：只动 `engine/` + `sandbox/` + 新建 `analysis/grading-rerun-20261125/`；**没动** `registry/`（只读 27 条）、`collect/`、`schema/`、账本、Release、网站；
  `analysis/` 既有产物一个字节没改；无 main 直推、无 PR 合并
- 报告里每个数字都能从 `analysis/grading-rerun-20261125/` 复算（§8 三条命令）

---

## 0. 头牌：四列表格（分开记账，这是本单的核心交付）

| 口径 | Tier1 层数 | 相对 176 | Tier2 | Tier3 | 说明 |
|---|---:|---:|---:|---:|---|
| **列1 基线**（第 7 步 relax，沿用不重算） | **176** | — | 3,343 | 13,649 | `analysis/auto-spatial-relax-20261125/`；Tier1 行数 22,762,695 |
| **列2 仅「拆串变化」**（① 生效，不含剔除） | **410** | **+234**（涨 235 / 跌 1） | 3,109 | 13,649 | 变动清单 `tier-moves.csv`（235 up + 1 down；唯一跌的层 `All_TH_Lots/FeatureServer/0`，E7 clear→hit，拆串让它的键与他源对上了真冲突）；Tier1 行数 27,305,991 |
| **列3 仅「分母剔除」**（② 生效，其余同基线） | **176** | **0**（涨 0 / 跌 0） | 3,145 | 13,649 | 可验分母 17,168 → **16,970**；-198 层原本全在 Tier2（0 层在 Tier1），所以 Tier1 不动 |
| **列4 两者合并** | **408**（可验口径）<br>410（全库列） | **+232**（可验）<br>+234（全库） | 2,913 | 13,649 | 可验分母 16,970；410 − 2（被剔除的 2 层 Tier1）= 408 |

**必须能回答的三问：**

1. **拆串贡献了几层？** **+234 层**（176 → 410）。三段拆解（`attribution.json`，逐段真跑流水线，不是估算）：

   | 段 | 变化 | Tier1 | 增量 |
   |---|---|---:|---:|
   | 基线（旧 impl，registry 角色表，无拆串） | — | 176 | — |
   | A：换 engine impl + 占位跳过 | registry 角色表、**不开拆串** | 211 | **+35** |
   | B：A + P1 拆串 | `addr_key_split` | 412 | **+201**（涨 202 / 跌 1） |
   | C：B + engine 方言表并入角色表 | 本轮正式口径 | **410** | **−2** |

   > C 段那 −2 不是判据变了：engine 表带来 5 个新字段名（`addnofull` / `fullname` / `stnamfull` / `streetfull` / `zip5`），
   > 其中 **`zip5` 让 571 个 url 的键补上了邮编**，与「没有邮编列」的源不再同键 → 2 层 E7 由 clear 掉成 unknown（`n_cmp` 50/46 → 0）。
   > 判据一字未动，是键口径变了；要不要把 zip 纳入键由 muse 定，本轮按派单「两边口径合一」执行并如实报 −2。

2. **剔除贡献了几层？** **0 层**。198 层里 **0 层**原本在 Tier1（基线 198 层全在 Tier2，本轮 196 层 Tier2 + 2 层 Tier1），
   所以「只改分母」不会凭空多出 Tier1；它把可验分母从 17,168 压到 **16,970**，Tier1 占比从 1.03%（176/17,168）抬到 **2.40%**（408/16,970）。

3. **两者有没有互相抵消？抵消多少？** **抵消 2 层**。那 2 层（`RR_Zoning_District/FeatureServer/0` 与
   `RR_Zoning_District__Public_View/FeatureServer/0`，pattern=P6「结构 ID 冒充地址」）是拆串抬进 Tier1 的 235 层之一，
   同属 198 剔除集 → 合并时被移出可验 Tier1。**恒等式**（`reconcile.json: cancellation_identity`）：
   `176 + 235 − 1 − 2 = 408`。

---

## 1. 分母与闭合（全库 17,168 层，行数一个没变）

| 项 | 层数 | 行数 |
|---|---:|---:|
| 分母 | **17,168** | **984,719,364** |
| Tier1 + Tier2 + Tier3 | 410 + 3,109 + 13,649 = **17,168** | 27,305,991 + 135,476,441 + 821,936,932 = **984,719,364** |
| 差额 | **0** | **0** |
| `template_unresolved` 分母 | **11,056** | **297,519,308** |
| active + minimal_safe + unavailable | 346 + 3,756 + 6,954 = **11,056** | 22,930,974 + 136,405,617 + 138,182,717 = **297,519,308** |
| 差额 | **0** | **0** |

`active` 143 → **346**（+203：拆串让 203 层从 minimal_safe 升到 active），`minimal_safe` 3,959 → 3,756，
`unavailable` 6,954 **不变**（没动用 unavailable 兜底）。`minimal_safe` 的硬约束照旧：
只取「门牌+街名」、`addr_core_hit[:2]=="11"`、`a_pool_eligible=false`（`summary.json: minimal_safe_regression` 全绿）。

---

## 2. ① 让 E7 真吃到占位跳过（`sandbox/` 那份副本已删）

### 2.1 改了什么（只有这一处实现）

| 文件 | 改动 | 行数影响 |
|---|---|---|
| `engine/split_addr.py` | 新增 `addr_key_split(af, roles, state)`（addr_key + P1 拆串）、`roles_of(registry_path, engine_dir)`（registry ∪ engine 方言表）、对外别名 `SUFFIX`/`street_norm` | +95 |
| `sandbox/coord_evidence.py` | **删掉**自带的 `roles_of()` / `addr_key()` / `street_norm()` / `SUFFIX`，改成 `from engine.split_addr import ...`，`addr_key = addr_key_split`（对外名不变） | −40/+16 |
| `sandbox/e7_refpool.py` | 它本来就 `from sandbox.coord_evidence import addr_key` → 自动继承新口径；只改了「阈值区段里出现非阈值子段」的取值兼容 | +2/−1 |
| `sandbox/tier_relax.py` | 证据列带上 `excluded_from_verifiable_denominator` 标记（**不改档位**） | +5/−1 |
| FIELDS（18 列） | **一个字段没改**（`url…e7_detail` 原样），`summarize.py` 调用约定不变 | 0 |

验收要求的两条 grep 证据：

```
$ grep -n "from engine.split_addr import\|engine.split_addr" sandbox/coord_evidence.py
18:#   addr_key  = engine.split_addr.addr_key_split（addr_key + P1 拆串）；
23:from engine.split_addr import (SUFFIX, addr_key_split, roles_of,  # noqa: E402
25:addr_key = addr_key_split        # 对外名仍是 addr_key；实现只在 engine/split_addr.py 一份
$ grep -c "def addr_key(\|def roles_of(\|def street_norm(" sandbox/coord_evidence.py
0
```

**「取字段原值、不猜不补」照旧**：拆串只对**行内真实值**做确定性切分；切不出（`reason != ok`、
`confidence < 0.95`、街名不足 2 个词）一律返回空串，绝不填默认值。占位值（`-1/-999/0/NULL/N/A/…`）一律跳过。

### 2.2 E7 前后对照（`e7-before-after.csv`，16,742 个 url）

| 项 | before（第 5 步 strict，committed） | after（本轮） |
|---|---:|---:|
| E7 clear | 785 | **3,092** |
| E7 hit | 56 | **382** |
| E7 unknown | 15,901 | **13,268** |
| 有键行数合计（`n_addr_rows`） | 98,251 | **343,157** |
| `delta_kind` | — | `same` 8,444 / `gained-key` **8,186** / `placeholder-skip` **112** / `lost-key` **0** |

> `lost-key = 0` 是关键：占位跳过**只剔掉占位值拼出来的垃圾键**，没有误伤任何真键（112 层降键全部由占位行解释）。
> `e7` 逐格翻转：`unknown→clear` 2,311、`unknown→hit` 327、`clear→hit` 4、`hit→clear` 2、`hit→unknown` 3、`clear→unknown` 2。

### 2.3 单测（`sandbox/test_coord_evidence.py`，新增 5 条）

| 用例 | 断言 |
|---|---|
| `test_impl_is_single_source_in_engine` | sandbox 里不再有第二份 `addr_key`/`roles_of`/`street_norm` 定义，且从 `engine.split_addr` 导入 |
| `test_placeholder_layer_rows_are_skipped` | `-1` / `NULL` / `0` / `-999` 作门牌或街名 → 建不出键 |
| `test_normal_layer_key_unchanged` | 非占位值 → 键与旧契约**逐字节一致**（`NH\|12\|mainstreet\|03301`） |
| `test_p1_combined_field_only_builds_key_via_split` | `SITE_ADDR="1049 61ST ST"` 老口径空键、新口径 `CA\|1049\|61ststreet\|90001`；纯街名/编号/信箱一律不建键 |
| `test_placeholder_layer_end_to_end_is_e7_unknown` | 整层占位值 → `n_addr_rows=0` → `e7=unknown`（不冒充 clear） |

跑法结论：`python3 -m pytest sandbox/test_coord_evidence.py sandbox/test_auto_recognize.py -q` → **71 passed**；
`python3 -m pytest engine/tests sandbox -q` → **178 passed**。

---

## 3. ② 分母口径：剔除 198 层（只改分母，不动数据）

### 3.1 口径落在哪里（代码里没有魔法数）

- **`sandbox/spatial_thresholds.yaml` 新增 `e7.denominator_excluded`**：`P8 22 / P6 90 / P9 66 / P11 9 / P12 11 / total 198`，
  每条写 `value / why / source`（写法与本文件既有区段一致）。`why` 的落点全部是「数据性质」而不是「缺陷」：
  区间地址、结构 ID、只有街名、PO BOX、打码/路口名 —— 五类都**造不出单个门牌号键**。
- **`sandbox/auto_recognize.py:load_exclusions()`**：类别与层数**只从 YAML 读**，逐层归属从组合拳① 的
  `analysis/combo-step1-20261125/patterns.csv`（`pattern_id`）读；两边数量不一致直接 `SystemExit`（不静默放过）。
- 被剔除层在 `auto-recognized.csv` 的两列里都带标记：`reason_evidence` 追加
  `excluded_from_verifiable_denominator: <class>`，`reason_detail` 追加同样标记 + 判定依据 + 归因文案
  **「数据性质如此，不是缺陷」**（原话照抄）；另加 `denominator_excluded` 列供机器读。
- **档位不动**：`tier` 仍按 E1–E8 原样算，剔除只影响「可验分母」这个口径（层仍在 17,168 行里，三档仍给）。

### 3.2 落盘清单 `denominator-excluded.csv`（恰好 198 行）

| class | 层数 | 判定依据（`why` 摘要） |
|---|---:|---|
| P8 | **22** | 路段门牌区间（from/to addr + 街名、中心线层），一条记录覆盖整段 |
| P6 | **90** | 结构 ID / 地块 ID / 分区号冒充地址（OBJECTID、PID、Zone） |
| P9 | **66** | 只有街名（或街名+城市），全层无门牌列 |
| P11 | **9** | PO BOX / POST OFFICE BOX |
| P12 | **11** | 打码门牌（3XX）或路口名（A ST / B AVE） |
| **合计** | **198** | 22 + 176；`reconcile.json: excluded_by_class_matches_yaml=true` |

每行都带 `layer_id, url, class, 判定依据`；`excluded_all_tagged=true`（198/198 两列都带标记且含原话文案）。
分布：本轮 Tier2 **196 层**、Tier3 **0 层**、Tier1 **2 层**（就是 §0 抵消的那 2 层 P6）。

### 3.3 C 方案（端点当门牌）**未采纳、未实现**

代码里没有「from/to 取端点当门牌」的任何分支；P8 的 `why` 明确写「造不出单个门牌号键 → 剔除」。

---

## 4. ③ P10 不补采 + 采集侧已知问题（单列，不进本轮结论）

### 4.1 P10 决定：**不补采**，按原判记入

| 层 | 形态 | 判定 |
|---|---|---|
| `mdgeodata.md.gov/.../Transportation/MD_RoadCenterlinesComprehensive/MapServer/0` | 道路中心线，远端 `n_fields=19`，快照只见 3 个 | 补采后大概率仍属 P8/P10（中心线 + 区间/编号），**不补** |
| `mdgeodata.md.gov/.../Transportation/MD_RoadCenterlines/MapServer/0` | 同上 | 同上，**不补** |

> 派单说「`n_fields ≤3` 的 7 层」，③ 实测是 **2 层**（`analysis/combo-step3-20261125/p10-crosscheck.csv`）；本轮沿用这个实测数。

### 4.2 采集侧已知问题（**不进本轮结论、不改本轮分数**）

这两层远端 `?f=json` 报 `n_fields=19`、`addr_core_hit=11000`，而本仓库快照只落了 3 个字段
（`RAMP_NUMBER / EXIT_NUMBER / MP_SUFFIX`）→ **采集侧漏字段**，不是上游缺数据。
本条登记为已知问题，处置留给采集侧（补 `outFields` 白名单 / 整层重采），本轮不动 `collect/`。

---

## 5. ④ DEFERRED-B refinement（详见 `deferred-b.md`）

**结论先给**：NH 的 2 层（`VW_Base_Map_(View)/FeatureServer/0`、`pbBaseMap_View/FeatureServer/0`）名字里带 Base Map，
但字段有 `addrnum` + `streetname` + `zip`、抽样 **50/50 行构得出键**、`unique_rate=1.00`、E7 实测 clear（50 行跨源同址、0 冲突）
→ **它们不是非地址层，不剔除，留在 Tier1**。它们彼此是同一份数据的重复发布（15,007 行 ×2），那属 D6 去重口径，不是本节。

- 六条判据（D1–D6）**逐条列全**在 `deferred-b.md` §1，含条文 / 判定口径 / 数据源 / 可否自动化；
  **原判据原文 `unavailable`**（仓库、历史会话、记忆库三处检索均 0 命中，已把检索命令与结果写进 §0.1），
  本轮给的是按仓库可核证据**重建版**，muse 补原文后只需替换条文、机制不用改。
- D1（命名）触发的候选在本轮 Tier1 内共 **14 层**，逐层走查按要求**只做了 NH 2 层**；其余 12 层标 `unavailable`（未结案、不剔除）。
- 因此 §0 的 Tier1 数字**不含任何 DEFERRED-B 扣减**。

---

## 6. ⑤ 重跑与 E1–E8 逐证据变化（只 E7 动，其余 7 条一个字节没变）

| 证据 | 基线（relax 口径） | 本轮 | 变化 |
|---|---|---|---|
| E1 | clear 6,855 / hit 9,896 / unknown 1 | 同 | **0** |
| E2 | clear 16,748 / hit 3 / unknown 1 | 同 | **0** |
| E3 | clear 4,188 / hit 482 / unknown 12,082（relax 后 na 12,065） | 同 | **0** |
| E4 | clear 13,388 / hit 2,911 / unknown 453 | 同 | **0** |
| E5 | clear 15,855 / hit 897 | 同 | **0** |
| E6 | clear 14,759 / hit 1,485 / unknown 508 | 同 | **0**（抽样 `coord-evidence.csv` 逐 url 比对：0 翻转） |
| **E7** | clear 1,067 / hit 110 / unknown 15,991 | **clear 3,215 / hit 447 / unknown 13,506** | **+2,148 clear、+337 hit、−2,485 unknown** |
| E8 | clear 864 / na 10,304 / unknown 5,584 | 同 | **0** |

> E6 逐 url 0 翻转是关键的自证：换 impl 只影响建键与占位判定，没有顺手改空间验算。
> E7 剩下的 13,506 层 unknown 的归因（`summary.json: e7.still_unknown_not_tier1`）：
> 无可投票行 6,264 / `n_cmp<3`（有键但跨源同址不足）6,707 / 无坐标样本 535。

---

## 7. ⑥ 两处纠正（照抄结论）

1. **覆盖率**：`19,224 / 28,644,662 = **0.067%**`（此前写的 0.063% 是算错了）。**结论不变**：这仍是**采样**实测，不是全量。
2. **1,268 口径**：已对上是「**19 条别名**下、非 P7 coord 行的纯增益行数」。**27 条别名**下同口径是 **3,532 / 3,362**
   （`analysis/combo-step3-20261125/p7-rebuild-after.csv`）。以后引用**必须带条数前缀**（「19 条下…」/「27 条下…」），不许裸写 1,268。
   本轮也不再引入新的裸数：本文件出现的 E7 数字都是「17,168 层 / 16,742 个有坐标样本的 url」两种口径各自标注。

---

## 8. 四数对账（`reconcile.py`，全部输出贴在此）

```
$ python3 analysis/grading-rerun-20261125/reconcile.py
tiers                     : tier1=410  tier2=3109  tier3=13649        (sum 17168)
tier rows                 : 27305991 + 135476441 + 821936932 = 984719364
verifiable denominator    : 16970   (17168 - 198)
tier1 share of verifiable : 2.416 %
checks:
  layers_equal_17168            : true
  tier_sum_equals_total         : true
  rows_equals_declared          : true      (declared 984,719,364)
  excluded_rows                 : 198       (expected 198)
  excluded_by_class             : {P6:90, P9:66, P8:22, P12:11, P11:9}
  excluded_by_class_matches_yaml: true
  excluded_all_tagged           : true      (198/198 带标记)
  excluded_note_verbatim        : true      (「数据性质如此，不是缺陷」原话)
  excluded_tier1                : 2
  e7_pairs                      : 16742
  e7_delta_kind                 : {same:8444, gained-key:8186, placeholder-skip:112}
  e7_lost_key                   : 0
  e7_delta_kind_matches_json    : true
  e7_delta_kind_sum_equals_pairs: true
  baseline_tier1 176 / new_tier1 410 / up 235 / down 1 / net 234
  up_and_excluded               : 2
  merged_tier1_verifiable       : 408
  cancellation_identity         : true      (176+235-1-2 = 408)
all_checks_pass           : true
```

四条必做对账逐条对上：

1. `tier1+tier2+tier3 = 17,168` ✅（`tier_sum_equals_total`）
2. 三档行数之和 = declared `984,719,364` ✅（`rows_equals_declared`）
3. `denominator-excluded` 198 层逐条有归因 ✅（`excluded_all_tagged` + `excluded_note_verbatim`）
4. `e7-before-after` 的 `delta_kind` 计数与正文一致 ✅（`same 8,444 / gained-key 8,186 / placeholder-skip 112 / lost-key 0`，
   `e7_delta_kind_matches_json` 与 `e7-before-after.json` 完全一致）

---

## 9. 复算命令

```bash
# ① 四数对账（~3 秒；含 198 层归因、delta_kind、抵消恒等式）
python3 analysis/grading-rerun-20261125/reconcile.py

# ② E7 前后对照（~17 秒；重建 e7-before-after.csv/.json）
python3 analysis/grading-rerun-20261125/compare_e7.py

# ③ ①口径的三段分解（~8 分钟：A/B/C 各跑一遍 coord_evidence→auto_recognize→e7_refpool→tier_relax）
python3 analysis/grading-rerun-20261125/attribution_runs.py   # 变体产物落 _work/，已删；重跑即可重建

# ④ 全链路重跑（~4 分钟）
python3 sandbox/coord_evidence.py --outdir analysis/grading-rerun-20261125      # ~100s
python3 sandbox/auto_recognize.py  --outdir analysis/grading-rerun-20261125      # ~3s
python3 sandbox/e7_refpool.py      --outdir analysis/grading-rerun-20261125      # ~74s
python3 sandbox/tier_relax.py --strict analysis/grading-rerun-20261125 \
        --outdir analysis/grading-rerun-20261125 --e3-relax on                   # ~6s

# ⑤ 单测
python3 -m pytest sandbox/test_coord_evidence.py sandbox/test_auto_recognize.py -q   # 71 passed
python3 -m pytest engine/tests sandbox -q                                            # 178 passed
```

---

## 10. 没做 / 卡点 / `unavailable`（不糊）

| 项 | 状态 |
|---|---|
| DEFERRED-B 六条判据**原文** | `unavailable`（仓库、历史会话、记忆库三处检索 0 命中，检索命令见 `deferred-b.md` §0.1）；本轮给重建版 D1–D6 |
| DEFERRED-B 其余 12 层逐层走查 | `unavailable`（本单只要求 NH 2 层首批走查），未结案、未剔除 |
| `zip` 是否该纳入地址键 | **未决**（engine 表 `zip5` 让 571 个 url 键变严格，代价 −2 层 Tier1）；本轮按「两边口径合一」执行，等 muse 拍 |
| zip/ZCTA 交叉校验 | `unavailable`（仓库内无 ZCTA 表，`spatial_thresholds.yaml: unavailable` 已登记） |
| 2 层 MD 道路中心线的漏字段 | 记为**采集侧已知问题**，本轮**不补采、不重算**（§4.2） |
| 全量（非采样）地址行级复核 | `unavailable`：本轮仍是抽样口径（19,224 行可及 / 28,644,662 行 = 0.067%） |

---

## 11. 验收标准自查（逐条给证据）

| # | 验收标准 | 证据 | 结论 |
|---|---|---|---|
| 1 | `engine.split_addr` 在 `sandbox/coord_evidence.py` 有命中，且 sandbox 无第二份 `addr_key` | `grep -n` 输出见 §2.1；`test_impl_is_single_source_in_engine` 断言 `def addr_key(` 不在 sandbox 源码里 | ✅ |
| 2 | `pytest sandbox/test_coord_evidence.py sandbox/test_auto_recognize.py` 全绿 | 71 passed（含新增 5 条）；`pytest engine/tests sandbox` 178 passed | ✅ |
| 3 | `auto-recognized.csv` 17,169 行（含表头） | `wc -l` = 17,169；`reconcile.json: layers_equal_17168=true` | ✅ |
| 4 | `denominator-excluded.csv` 恰好 198 行，分桶 P8 22 / 其余 176 | 表头 1 + 198 数据行；分桶见 §3.2，`excluded_by_class_matches_yaml=true` | ✅ |
| 5 | 四数对账输出贴进 REPORT（含 checks 布尔） | §8 全文 | ✅ |
| 6 | 报数四列表格完整 + 抵消解释 | §0（列1–列4 + 三问 + 恒等式 176+235−1−2=408） | ✅ |
| 7 | 边界：不动 collect/schema/账本/Release/网站、不动 `analysis/` 既有产物、不直推 main、不合 PR、不改 registry | `git status` 只列出 7 个 `engine/`+`sandbox/` 文件与新建目录；`git diff --name-only` 无 `registry/`、`collect/`、`schema/` | ✅ |
