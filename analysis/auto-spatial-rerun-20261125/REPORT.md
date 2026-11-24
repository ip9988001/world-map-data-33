# 第 5 步重跑 · 带坐标重认（muse-000221 / `w2-20261125-auto-rerun`）

- 分支：`feat/auto-spatial-rerun-20261125`（基线 **`97523ae`** = main，PR #46 merge commit）
- 输入：`analysis/coord-samples-20261124/`（79 文件 / **738,174** 行坐标样本，只读）+ 第 4 步逐层分配表 + `registry/dialects.v1.yaml`（只读）+ `analysis/tiger_county/*.json.gz`
- 本轮只跑证据与分档：**不融合、不分级、不重写引擎、`registry/` 零改动、未起任何采集**
- 报告里每个数字都能从 `analysis/auto-spatial-rerun-20261125/` 与 `analysis/coord-samples-20261124/` 复算（复算命令 §9）

---

## 0. 头牌结论

| 指标 | 上轮 | 本轮 | 说明 |
|---|---:|---:|---|
| **Tier 1 层数** | **0** | **30** | 占分母 0.17%；1,073,302 行（0.109%） |
| Tier 2 | 1,123 | 1,005 | −118（其中 25 层升 Tier1，其余被 E6 实测降 Tier3） |
| Tier 3 | 16,045 | 16,133 | +88（坐标实测把「说不清」变成「说不通」） |
| E6 unknown | 17,168（全部） | **924**（5.4%） | 14,759 clear + 1,485 hit 实测 |
| E7 unknown | 17,168（全部） | **16,327**（95.1%） | 785 clear + 56 hit 实测；unknown 逐类归因见 §5 |

**Tier1 为什么还是这么少（不美化）**：坐标只解锁了 E6/E7，真正压住 Tier1 的是 **E3（粒度未定 12,498 层）**与 **E7（样本里没有跨源同址可比，13,714 层）**。
本轮**没有改动**任何判据口径，只把「没数据」换成「实测数据」；下面 §8 给了三种口径敏感性，供 muse 决定要不要动规则。

## 1. 分母与闭合

| 项 | 层数 | 行数 |
|---|---:|---:|
| 分母（第 4 步 `dialect-assignment.csv`） | **17,168** | **984,719,364** |
| Tier1 + Tier2 + Tier3 | 30 + 1,005 + 16,133 = **17,168** | 1,073,302 + 85,388,202 + 898,257,860 = **984,719,364** |
| 差额 | **0** | **0** |
| `template_unresolved` 分母 | **11,056** | **297,519,308** |
| active + minimal_safe + unavailable | 25 + 4,077 + 6,954 = **11,056** | 320,583 + 159,016,008 + 138,182,717 = **297,519,308** |
| 差额 | **0** | **0** |

来源：`summary.json: tiers / moves / moves._check`（`summarize.py` 从 `auto-recognized.csv` 现算）。

## 2. 三档（全库 17,168 层）

| 档 | 层数 | 占分母 | 行数 | 占行数 |
|---|---:|---:|---:|---:|
| Tier 1 | 30 | 0.17% | 1,073,302 | 0.109% |
| Tier 2 | 1,005 | 5.85% | 85,388,202 | 8.67% |
| Tier 3 | 16,133 | 93.97% | 898,257,860 | 91.22% |

## 3. 挪动表（`template_unresolved` 11,056 层，三列闭合）

| verdict | 层数 | 行数 | 上轮 |
|---|---:|---:|---:|
| `active` | **25** | 320,583 | 0 |
| `minimal_safe` | 4,077 | 159,016,008 | 4,102 / 159,336,591 |
| `unavailable` | 6,954 | 138,182,717 | 6,954 / 138,182,717 |

- 25 层全部来自上轮 `minimal_safe`（4,102 → 4,077 + 25 = 4,102，**逐位对得上**）
- `unavailable` 一行未变：卡点仍是 E1（门牌缺失 9,896 层）+ 417 层无样值，与坐标无关
- 表头：`layer_id,url,provider,granularity,geom_type,rows_n,verdict,reason_evidence,reason_detail`（`template-unresolved-moves.csv`）
- 暂不可用单表：`template-unresolved-unavailable.csv`（6,954 行，100% 命中 E1）

## 4. Tier 1 释放归因（30 层 / 1,073,302 行）

逐层证据链在 **`tier1-evidence.csv`**（列：`samples_file` + `rows_sampled` + `row_index_range` + `E1..E8_state` + `e6_detail` + `e7_detail`）。

| 粒度 | 实测几何 | 层数 | 行数 |
|---|---|---:|---:|
| `parcel_centroid` | polygon | 23 | 735,262 |
| `apartment_unit_point` | point | 5 | 54,851 |
| `building_point` | point | 1 | 269,175 |
| `centerline_midpoint` | polyline | 1 | 14,014 |

放行所依赖的证据组合（每层都一样，四条同时成立）：
1. **E1/E2 clear**：`addr_core_hit[:2] == "11"`（门牌族 + 街名族 20 行样值过半有值）
2. **E3/E4/E5 clear**：粒度 ⇄ 实测几何相符；样本字段无负向族/跨方言同名字段；无抽样截断、份额 ≥0.01%
3. **E6 clear（本轮新增，实测）**：50 个真实坐标全部落在美国县界内（`县界外占比=0.0`），唯一率 ≥0.94，最热坐标占比 ≤0.04
4. **E7 clear（本轮新增，实测）**：同址跨源投票无冲突（例：`同址可比 43 行，冲突 0 行`）
5. **E8 na/clear**：无模板或与模板字段集对齐

原文样例（`tier1-evidence.csv` 第 1 行）：
`City_Owned_Parcels_(View)` → `_UNLOCATED-part4.csv` 行 0..49，polygon/parcel_centroid，
`E1..E7 = clear`，`E8 = na/clear`（30 层里 25 层 E8=na、5 层 clear），`e6_detail=未命中任何熔断；n=50 唯一率=1.0 最热坐标占比=0.02 县界外占比=0.0`。

## 5. E6 / E7 由 unknown 转实测

### 5.1 E6 空间验算（坐标 → 县界点落）

| 状态 | 层数 | 依据 |
|---|---:|---|
| clear | **14,759** | 县界外占比 ≤10%、唯一率 ≥5%、最热坐标占比 ≤50% |
| hit | **1,485** | 其中 1,147 层**全部**坐标在县界外（境外服务/纯海外数据）、215 层 0<县界外占比<1、123 层是「单点填充/重复坐标」类（`tier1-evidence.csv` 与 `coord-evidence.csv` 按 url 可逐层核） |
| unknown | **924** | 该 url 无坐标样本 535 + 有效坐标 1 行 256 + 2 行 133（< `min_sample_rows=3`） |

判据全部来自 `sandbox/spatial_thresholds.yaml`（`max_outside_share 0.10` / `max_top_point_share 0.50` / `min_unique_coord_rate 0.05` / `min_sample_rows 3` / `max_cross_boundary_dist_m 5000`）。
**越界口径**：按美国县界并集判；越界点若距最近县界 ≤5km 记为「县界裁剪噪声」不计入熔断（列 `outside_share_near_boundary`）。声明州外的占比单列 `outside_share_declared_state`（只作第 6 步参考，不参与熔断——第 4 步的州标注本身有跨州错标）。

### 5.2 E7 源间同址投票（地址级多源投票）

| 状态 | 层数 | 依据 |
|---|---:|---|
| clear | **785** | 同址可比 ≥3 行，冲突占比 ≤10% |
| hit | **56** | 同址可比 ≥3 行，冲突占比 >10%（同址跨源坐标相差 >300m） |
| unknown | **16,327** | ① 本层样本无「门牌+街名」键 **13,714** ② 有键但无跨源同址（n_cmp=0）**1,832** ③ 无坐标样本 **535** ④ n_cmp=1 **166** ⑤ n_cmp=2 **80** |

阈值在 `sandbox/spatial_thresholds.yaml: e7`（`max_addr_conflict_m 300` / `max_conflict_share 0.10` / `min_cmp_rows 3`，每条带 value/why/source）。
地址键归一化：注册表别名（`number/street/zip`）+ 合并地址串兜底解析 + 街名后缀展开（st→street 等），全部写进 `coord-evidence.csv: sample_fields` 与 `n_addr_rows`。

## 6. geom_type 分项（几何按实测分开统计，面/线取真实顶点，绝不当质心）

| 实测 geom_type | 层数 | 行数 | E6 clear / hit / unknown | E7 clear / hit / unknown |
|---|---:|---:|---|---|
| point | 9,154 | 654,323,974 | 7,934 / 905 / 315 | 636 / 20 / 8,498 |
| polygon | 3,353 | 167,975,479 | 2,946 / 290 / 117 | 141 / 28 / 3,184 |
| polyline | 4,188 | 91,465,538 | 3,850 / 281 / 57 | 6 / 8 / 4,174 |
| multipoint | 39 | 6,611,384 | 29 / 9 / 1 | 2 / 0 / 37 |
| multiple | 1 | 66,000 | 0 / 0 / 1 | 0 / 0 / 1 |
| 无样本（unknown） | 433 | 64,276,989 | 0 / 0 / 433 | 0 / 0 / 433 |
| **合计** | **17,168** | **984,719,364** | 14,759 / 1,485 / 924 | 785 / 56 / 16,327 |

`geom_type` 来源：坐标样本 `samples/*.csv: geom_type`（第 6 步前置落盘的响应 `geometryType`），缺失时回落第 4 步 `inventory.geom`。

## 7. 代码改动（逐行说明，两模块仍 300 行）

`sandbox/auto_recognize.py` **154 行**（改动前后同数）；`sandbox/spatial_verify.py` **146 行（本轮 0 改动）** → 合计 **300 行**，未超上限。

| 位置 | 改什么 | 为什么 |
|---|---|---|
| L13 `MOVE_COLS` | 增列 `geom_type` | §四.3 要求的挪动表列头 |
| L39-41 `load_ctx` | 读 `coord-evidence.csv` → `C["coord"]` | 坐标实测结论的唯一入口（与 `spatial-findings.csv` 同一机制，只读） |
| L54-57 `ev3` | `geom` 缺失时用样本实测 `geom_type` 兜底；冲突文案改用实测值 | 「几何语义按第 4 步 + 坐标样本实测」 |
| L59-66 `ev4` | 探针字段集缺失时改用样本实测字段集（`sample_fields`） | 探针配额 1,000 已满 → 上轮 13,443 层 E4 unknown；样本字段是真实字段名，判据不变 |
| L75-77 `ev6` | 改读 `coord-evidence.csv` 的 `e6/e6_detail` | E6 从「没跑」变实测 |
| L78-80 `ev7` | 从固定 unknown 改为读 `e7/e7_detail`（投不出票仍 unknown） | E7 从「没产出」变实测 |
| L123 `evaluate` | 输出 `geom_type` | 供挪动表与分项统计 |

新增 `sandbox/coord_evidence.py`（**207 行**，新文件，不计入上述两模块 300 行上限）：
它做「坐标样本 → E6/E7/实测几何」的证据抽取，复用 `spatial_verify.point_in_ring / boundary_dist_m / load_thresholds`，
**没有重写引擎**、不含任何融合/分级/置信度逻辑。`sandbox/spatial_thresholds.yaml` 增 `e7` 三条阈值（各带 value/why/source）。

## 8. 敏感性（口径不动，给 muse 决策用的三组数）

| 假设 | Tier1 层数 | 行数 |
|---|---:|---:|
| 现口径（E3 在「粒度未定」时记 unknown，沿用第 5 步） | **30** | 1,073,302 |
| 只把「粒度未定但几何有实测」按 E8 同理记 `na`（E8 已有先例：无模板→na） | 166 | 22,490,316 |
| E7 完全可验（其余 7 条全 clear，仅 E7 unknown） | 393 | 23,075,724 |
| 上两条同时成立 | 1,831 | 65,131,527 |

结论：**规则不动时 Tier1 = 30**；要放大 Tier1，必须先在下一步决定「粒度未定算不算负证据」与「E7 覆盖怎么提高（扩大参照源）」。这两条都不是本轮能单方面改的。

## 9. 复算命令

```bash
python3 sandbox/coord_evidence.py --outdir analysis/auto-spatial-rerun-20261125   # → coord-evidence.csv
python3 sandbox/auto_recognize.py  --outdir analysis/auto-spatial-rerun-20261125   # → auto-recognized.csv + 两张挪动表
python3 analysis/auto-spatial-rerun-20261125/summarize.py                          # → summary.json + tier1-evidence.csv + sampling-list.csv
python3 -m pytest sandbox -q                                                       # 105 passed
```

## 10. 交接物

| 文件 | 内容 |
|---|---|
| `auto-recognized.csv` | 17,168 行 × 33 列（`E1..E8_state/detail`、`tier`、`move`、`verdict`、`geom_type`…） |
| `coord-evidence.csv` | 16,742 行 × 18 列（E6/E7 实测：`n_coords/unique_rate/top_point_share/outside_share_us/outside_share_near_boundary/outside_share_declared_state/n_cmp/n_conflict/conflict_share/sample_fields`） |
| `template-unresolved-moves.csv` | 11,056 行（9 列，含 `geom_type`） |
| `template-unresolved-unavailable.csv` | 6,954 行（暂不可用单表） |
| `tier1-evidence.csv` | 30 行放行证据链（含坐标样本文件名 + 抽样行号区间） |
| `sampling-list.csv` | 17,168 行（layer_id + url + 种子 20261125 + 抽样行数 + tier/verdict） |
| `summary.json` | 三档 / 三列闭合 / E1–E8 分布 / E6·E7 归因 / geom 分项 / 敏感性 / 上轮对比 |
| `summarize.py` | 上面所有数字的生成脚本 |

## 11. 未跑项（如实列，不美化）

1. **E7 覆盖没有扩大参照源**：仍只用 738,174 行坐标样本互投；13,714 层样本里根本没有门牌+街名键、1,832 层有键但无人同址 → 记 unknown。要提质必须把本地全表（`dist/intake-full/layers/*`）拉进来当参照源，本轮没做（时间）。
2. **跨边界距离（层模式）未算**：没有「声明县」时该项记 na（fixtures 模式仍在算）；本轮用「越界点距最近县界 ≤5km 记噪声」替代。
3. **building_outline_distance / ZIP-ZCTA 交叉校验**：仓库无数据源，仍 `unavailable`（与上轮同）。
4. **未做点落县 FIPS 归属**（只判「在不在美国县界并集内」），因此 `outside_share_declared_state` 仅为诊断列。
5. **未融合、未分级、未写回账本、未改引擎**；`registry/` 一个字节未动；未起任何采集或 Actions。
