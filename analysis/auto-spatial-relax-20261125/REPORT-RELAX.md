# 第 7 步 · E3 + E7 放宽（muse-000226 / `w2-20261125-tier-relax`）

- 分支：`feat/tier-relax-20261125`（基线 **`106899c`** = origin/main，PR #47 merge commit）
- 输入（只读，一个字节没改）：`analysis/auto-spatial-rerun-20261125/`（第 5 步 strict 结果）+ `analysis/coord-samples-20261124/`（738,174 行坐标样本）+ `registry/dialects.v1.yaml`（**冻结**）+ `dist/intake-full/layers/*/addr.*.ndjson.gz`（本地全表，E7 扩参照源）
- 本轮只重算「证据 → 分档 → 挪动表」：**不融合、不分级、不重写引擎、不动 registry/、不起 Actions、不发 Release**
- 报告里每个数字都能从 `analysis/auto-spatial-relax-20261125/` 复算（§9 一条命令）

---

## 0. 头牌结论（不美化）

| 指标 | 第 5 步 strict | 本轮（E3+E7 放宽） | 目标 |
|---|---:|---:|---:|
| **Tier 1 层数** | 30 | **176**（1.03%） | 1,831 |
| **Tier 1 行数** | 1,073,302 | **22,762,695**（2.31%） | 65,131,527 |
| Tier 2 | 1,005 | 3,343 | — |
| Tier 3 | 16,133 | 13,649 | — |
| `active`（挪动表） | 25 | **143** | — |
| `minimal_safe` | 4,077 | 3,959 | 只减不增 |

**Tier1 = 176，比目标 1,831 少 1,655 层（−90.4%）。** 差这么多不是调参能补的，原因只有一条：
**E7 的瓶颈不是参照池大小，而是「门牌 + 街名」键本身构不出来 / 跨源没有同址行。**
本轮把本地全表 1,242,744 行拉进参照池后，E7 由 unknown 转可验的层只有 **336 层**（clear 282 + hit 54），
其中真正因此进 Tier1 的只有 **10 层**（四档里的 `both` 档）。逐证据归因见 §4。

## 1. 两条放宽口径（严格按 REPORT §8，其他判据一律不动）

### 1.1 E3（`--e3-relax on|off`，**默认 off**，`sandbox/spatial_thresholds.yaml: e3_relax`）

| 情形 | 放宽前 | 放宽后 |
|---|---|---|
| `granularity=unknown` **且** 坐标样本有实测 `geom_type` | unknown → 直接 Tier3 | **na**（与 E8「无模板即 na」同理） |
| `granularity=unknown` 但**没有**实测几何 | unknown → Tier3 | unknown → Tier3（**不放过**：没实测就没证据） |
| 粒度已知但与几何冲突（E3 hit） | hit → Tier3 | **仍 hit → Tier3**（E3 仍是 FATAL） |

E3 状态 `unknown → na` 共 **12,065 层**；`--e3-relax off` 时逐层与原 strict 完全一致（§3 末尾断言）。

### 1.2 E7（`sandbox/e7_refpool.py`，判据一字不改）

- 参照池 = **738,174 行坐标样本** + **本地全表每层前 `per_layer_cap=2000` 行**（`dist/intake-full/layers/*/addr.*.ndjson.gz`）
- 判据原样：同址跨源坐标差 **>300m 记冲突**；**n_cmp<3 记 unknown**；冲突占比 >10% 记 hit；**绝不冒充 clear**
- 键归一沿用第 5 步同一个 `addr_key()`（registry 别名 + `street_norm`）；本地全表侧用同一 `street_norm()`，`street_name` 缺时用 `street_full` 去尾部类型词
- **这是采样不是全量**：每层实际取到多少行、是否被截断、跳过的层与原因，逐层在 `e7-refpool-stats.csv`，汇总在 `summary.json: e7_refpool`

## 2. 分母与双闭合（差额全 0）

| 项 | 层数 | 行数 |
|---|---:|---:|
| 分母 | **17,168** | **984,719,364** |
| Tier1 + Tier2 + Tier3 | 176 + 3,343 + 13,649 = **17,168** | 22,762,695 + 140,019,737 + 821,936,932 = **984,719,364** |
| 差额 | **0** | **0** |
| `template_unresolved` 分母 | **11,056** | **297,519,308** |
| active + minimal_safe + unavailable | 143 + 3,959 + 6,954 = **11,056** | 20,384,453 + 138,952,138 + 138,182,717 = **297,519,308** |
| 差额 | **0** | **0** |

来源：`summary.json: tiers / moves / checks`（`sandbox/tier_relax.py` 现算，非 0 直接 `exit 2`）。

## 3. Tier1 四档留底（严格 / 只放 E3 / 只放 E7 / 两个都放）

| 档 | 层数 | 行数 | 单独就够的开关 | layer_id 清单 |
|---|---:|---:|---|---|
| `strict`（严格就进） | **30** | 1,073,302 | 不需要放宽 | `tier1-strict.ids` |
| `e3_only`（只放 E3 就够） | **136** | 21,417,014 | E3 | `tier1-e3_only.ids` |
| `e7_only`（只放 E7 就够） | **0** | 0 | E7 | `tier1-e7_only.ids`（空） |
| `both`（两个都得放） | **10** | 272,379 | E3 + E7 | `tier1-both.ids` |
| **和** | **176** | **22,762,695** | | |
| 两个都放时 Tier1 总数 | **176** | **22,762,695** | | `tier1-buckets.csv`（逐层） |
| **断言** | **176 === 176 ✅** | **22,762,695 === 22,762,695 ✅** | | 代码 `checks.buckets_equal_tier1 == true` |

- 四档是「两个都放」Tier1 集合的**划分**（互斥且穷尽），和必须逐位相等 —— 代码里写死断言，不等即轮次失败。
- `e7_only = 0` 是实测结论不是缺失：393 层「只卡 E7」的层，参照池扩到 124 万行后 n_cmp 仍是 0~2（§4），一层都没松动。
- 严格档可复现：`--e3-relax off` 重跑 → Tier1/Tier2/Tier3 = **30 / 1,005 / 16,133**，挪动表 **25 / 4,077 / 6,954**，
  与第 5 步 `auto-recognized.csv` 逐层 tier **完全相同**（17,168/17,168 行一致，见 `checks.strict_reproduced_layers`）。

## 4. 1,831 vs 176：逐证据归因（不许调参凑数）

`summary.json: attribution` 现算。先把「E7 完全可验」假设下的层拆成格子（其余 6 条证据全 clear/na）：

| E3（含放宽） | E7 | 层数 |
|---|---|---:|
| 已 clear | clear（本来就过） | 30 |
| E3 放宽后 na | clear（只靠 E3 就过） | 136 |
| clear | unknown | 393 |
| **E3 放宽后 na** | **unknown** | **1,438** |

`1,831 = 1,438 + 393` —— 这正是 REPORT §8「两个都放 = 1,831」的口径：**它数的是被 E7 挡住的层数**，
不含本来就靠 E3 放宽进 Tier1 的 166 层；同假设下 Tier1 总数本应是 **1,997**。

实算 176 之后，那 1,831 层里没进来的 1,821 层，逐证据拆开：

| 卡在哪 | 层数 | 说明 |
|---|---:|---|
| 样本 + 本地全表都构不出「门牌+街名」键 | **1,340** | 这些层样本字段是组合串（`addr` / `std_addr` / `FULLADDR` / `ARC_Addr_1` …），不在 registry 别名表里 → `addr_key` 返回空，E7 只能 unknown。要解必须**扩 registry 别名或做组合串解析**（registry 本轮冻结，未动） |
| 有键但参照池里没有跨源同址行（n_cmp=0） | **442** | 这些地址在其源的覆盖范围内没有第二个源；本地全表只覆盖 748 个层、且与这 1,831 层**零重叠**（`e7-refpool-stats.csv` 可核） |
| n_cmp=1 | **26** | 差 2 行才够 min_cmp_rows=3 |
| n_cmp=2 | **13** | 差 1 行 |
| **已兑现** | **10** | 四档 `both` |

**参照池不是瓶颈的证据**（把上限从 2,000 抬到 8,000 的实测）：pool 行数 1.24M → 4.32M（3.5 倍），
E7 clear 只从 1,070 涨到 1,111（+41）、hit 56→157，`only-E7` 那 393 层**一层没变**。
结论：**E7 想再放大，必须动「键能不能构出来」，不是「参照池够不够大」**（下游下一轮再定）。

## 5. E7 扩参照池统计（`summary.json: e7_refpool` + `e7-refpool-stats.csv` 逐层）

| 项 | 数值 |
|---|---:|
| 取样上限（每层前 N 行） | **2,000**（`spatial_thresholds.yaml: e7_refpool.per_layer_cap`） |
| 单行比较上限 | **200**（`max_cmp_per_row`，同键他源行超过 200 行时按固定顺序截断；键桶超 200 行的占 0.4%） |
| 参照池总行数 | **1,242,744**（本地全表；另有 738,174 行坐标样本照旧参与） |
| 覆盖层数（本地全表） | **1,158 个层目录**，其中 **748** 有 addr 行、**741** 能映射回分母 url |
| 被截断的层 | **581**（= 文件行数 ≥ 2,000，只取前 2,000 行，**不是全量**） |
| 跳过的层 | **417**（410 = addr 表为空、7 = 行内无 `src_layer_url` 无法映射，只作他源参照） |
| 覆盖州数 | 51（含 DC；每州行数见 `pool_rows_by_state`） |
| E7 结果（16,742 个 url） | clear **1,070** / hit **110** / unknown **15,562** |
| 由 unknown 转可验 | **336 层**（clear 282 + hit 54） |
| 触发冲突被降档 | hit 56 → 110（新增 54 层被参照池抓出 >300m 跨源冲突） |

## 6. 挪动表（`template_unresolved` 11,056 层）

| verdict | 本轮层数 | 本轮行数 | 第 5 步 |
|---|---:|---:|---:|
| `active` | **143** | 20,384,453 | 25 / 320,583 |
| `minimal_safe` | 3,959 | 138,952,138 | 4,077 / 159,016,008 |
| `unavailable` | 6,954 | 138,182,717 | 6,954 / 138,182,717 |

`active` 143 = 严格档 25 + 靠 E3 放宽 108 + 靠 E7 放宽 10（逐层见 `template-unresolved-moves.csv`）。
`unavailable` 一行未变：卡点仍是 E1（门牌缺失）与无样值，与 E3/E7 无关。

## 7. ③ 老规矩原样保留：无门牌地址仍走 B 货

| 约束 | 本轮状态 | 证据 |
|---|---|---|
| `minimal_safe` 只取「门牌 + 街名」两要素 | **未变** | 3,959 层全部 `addr_core_hit[:2] == "11"`（`checks.minimal_safe_unchanged=true`） |
| `a_pool_eligible=false`（永不进 A 货池） | **未变** | `registry/evaluator.py` L84-86 硬编码，本轮 **0 字节改动**（`git diff --name-only` 全清单见回执） |
| 永不进 S 级、只上网站 | **未变** | 分级是第 6 步的活，本轮不产出分级；`engine/` 未动 |
| `minimal_safe` 不会被「放宽」凭空新增 | **未变** | `new_minimal_safe_not_in_strict = 0`：relaxed 的 3,959 ⊂ strict 的 4,077，差的 118 层全部升 `active` |
| 回归测试 | 新增 | `sandbox/test_tier_relax.py::test_delivered_summary_is_closed` + §9 的 pytest 全绿 |

## 8. 代码与行数账

| 文件 | 行数 | 说明 |
|---|---:|---|
| `sandbox/auto_recognize.py` | 154（**0 改动**） | 约束上限两文件合计 300 行，本轮仍等于 300 |
| `sandbox/spatial_verify.py` | 146（**0 改动**） | 同上 |
| `sandbox/e7_refpool.py` | **207**（新文件） | E7 扩参照池 + 重算 E7；复用 `coord_evidence` 的 `addr_key / street_norm`，不重写判据 |
| `sandbox/tier_relax.py` | **273**（新文件） | E3 开关 + 四档划分 + 挪动表 + 闭合/四档断言；复用 `auto_recognize` 的 `EKEYS/FATAL/load_ctx` |
| `sandbox/test_tier_relax.py` | **134**（新文件） | 12 条：E3 na 边界 4 / E7 取样与 n_cmp<3 4 / 四档求和与交付物自检 4 |
| `sandbox/spatial_thresholds.yaml` | +32 行 | 新增 `e7_refpool.per_layer_cap / max_cmp_per_row`、`e3_relax.default`，各带 value/why/source |

新增单测三组（题目要求的三组全覆盖）：
1. **E3 na 边界**：有实测几何→na；无几何→仍 unknown→Tier3；粒度已知冲突→仍 hit→Tier3；开关 off→严格。
2. **E7 参照池取样与 n_cmp<3**：键必须门牌+街名+州齐；`street_full` 去类型词兜底；n_cmp=2 → unknown（不冒充 clear）。
3. **四档求和断言**：四档互斥穷尽；`sum(四档) === Tier1` 层数与行数；交付物 `summary.json` 自检（两处差额 0、四档和 === Tier1）。

`python3 -m pytest sandbox -q` → **117 passed**（原 105 全绿 + 新增 12）。

## 9. 复算命令

```bash
python3 analysis/auto-spatial-relax-20261125/run_relax.py                 # 全量：参照池 + 分档 + 合并 summary（约 50 秒）
python3 analysis/auto-spatial-relax-20261125/run_relax.py --e3-relax off  # 严格可复现（Tier1 回到 30）
python3 analysis/auto-spatial-relax-20261125/run_relax.py --strict-only    # 只重分档不重算参照池
python3 -m pytest sandbox -q                                              # 117 passed
```

## 10. 交付物

| 文件 | 内容 |
|---|---|
| `auto-recognized.csv` | 17,168 行 × 40 列（strict 全列 + `tier_strict/tier_e3/tier_e7/tier_both/bucket/e3_relax_state/e7_relax_state`） |
| `coord-evidence-relax.csv` | 16,742 行 × 20 列（E6/E7 实测；多 `n_cmp_sample`、`pool_rows`） |
| `e7-refpool-stats.csv` | 1,158 行逐层：`pool_rows/pool_keyed/capped/skip_reason/own_rows_keyed/n_cmp/e7` |
| `e7-refpool-summary.json` | 参照池汇总（总量/覆盖/截断/跳过/按州行数/抽样上限） |
| `summary.json` | 三档、四档、挪动表、两处闭合、`attribution`、`e3`、`e7`、`minimal_safe_regression`、`checks` |
| `tier1-buckets.csv` + `tier1-{strict,e3_only,e7_only,both}.ids` | 四档逐层表 + 四份 id 清单 |
| `tier1-evidence.csv` | 176 层放行证据链（E1–E8 状态 + 放宽后 E3/E7 详情 + 所属档） |
| `template-unresolved-moves.csv` / `-unavailable.csv` | 11,056 行 / 6,954 行 |
| `run_relax.py` | 本目录全部数字的生成脚本 |

## 11. 未做项（如实列）

1. **没碰「门牌+街名」键的构造能力**：1,340 层样本字段是组合地址串，`addr_key` 构不出键。扩别名/做组合串解析会改动 E7 的键口径（strict 基线也会变），本轮明确不做，留给下一轮单独定。
2. **参照池是 head 采样不是全量**：每层前 2,000 行；581 层被截断、410 层 addr 表为空、7 层无 url。全量入池需要重扫 13.5GB gz（估 1 小时+），本轮按 90 分钟预算不跑。
3. **本地全表只覆盖 748 层**，与 E7 阻塞的 1,831 层零重叠 —— 这是 E7 放不动的结构性原因，不是取样参数问题（§4 有 2,000 vs 8,000 的对照）。
4. **未做点落县 FIPS 归属**、**building_outline / ZIP-ZCTA 交叉校验**：仍 unavailable（与第 5 步同）。
5. **未融合、未分级、未重写引擎、未起采集/Actions、未动 registry/ 与任何账本**；PR 只开不合。
