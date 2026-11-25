# 第 7 步 · 三州试点换新分档全量重跑（muse-000232 / `w2-20261125-pilot-rerun`）

- 分支：`feat/pilot-rerun-20261125`，基线 **`86541b7d`**（= origin/main，PR #48 引擎重写 + PR #49 放宽已合）
- 分档输入：`analysis/auto-spatial-relax-20261125/auto-recognized.csv`
  sha256 = `cc60a834625617c1a3a2a4c171217171a95372441561dabb4f4b93d3d4fb812b`（17,168 行；tier1 176 / tier2 3,343 / tier3 13,649）
- 键改 **(url, dialect_id)**：16,751 个有效 pair（417 行 url 为空，不入表）；`layer_id` 只 1,523 个不同值，**不是主键**
- 产物目录 `analysis/engine-pilot-rerun-20261125/`（**不覆盖**第 6 步的 `analysis/engine-pilot-20261125/`）
- 未动：`registry/`（冻结）、`collect/`、`schema/`、`sandbox/`、任何账本、任何 Release、任何 GitHub Actions；**没有合并 PR**

---

## 0. 头牌（不美化）

| 指标 | 第 6 步 | 本轮 | 差 |
|---|---:|---:|---:|
| 三州输入行 | 14,314,067 | **14,314,067** | 0 |
| 三州去重后 | 6,668,499 | **6,668,499** | **0** |
| S / A / B / C（合计） | 2,057,841 / 4,045,527 / 565,131 / 0 | **2,057,841 / 4,045,527 / 565,131 / 0** | 0 / 0 / 0 / 0 |
| 三州 tier1 | 0 | **0** | 0 |
| `unsupported.csv` | 0 条 | **0 条**（只有表头） | 0 |

**结论：换成放宽后的分档表后，三州入库行数、分级、Tier 分布逐列完全不变。**
这不是没生效，而是两条口径在本轮数据上**确实没有可落地的行**，逐条可复算归因见 §4：

1. **20 层挪动（tier3→tier2）在这三州只贡献 934 行样本，且这 934 行全部低于 C 级（grade X）被丢弃** → 分档换了但没有任何一行带着新档位入库；
2. **几何口径（面/线取真实顶点）在本轮数据上没有触发**：Overture DE/IA 的 WKB 几何 **100% 是 Point**（751,180 / 2,221,590 行实测），而唯二的面/线来源是方言层样本，其 polygon/polyline 行 **全部 grade X**（无街名）→ 入库 0 行；
3. 真实点优先于插值的硬约束在 NH 有 351,378 条相关行，但第 6 步的源优先级（GRANIT 10 < TIGER 40）本来就保住了真实点，所以计数不变。

## 1. 分档输入与三州 tier 分布

| 项 | 值 |
|---|---|
| 分档表行数 / 有效 pair | 17,168 / **16,751**（417 行 url 空 → 不入表） |
| 三州 tier1 层数 | **0**（DE 0 / NH 0 / IA 0；176 层 tier1 全在三州之外，其中 **85 层** state=未定位 —— 派单里写 64，以本表实测 85 为准） |
| 三州 tier2 层数（relax） | DE 7 / NH 7 / IA 19 |
| 三州 tier3 层数（relax） | DE 34 / NH 46 / IA 64 |

**入库行按 tier（`<ST>/stats.json: by_tier`）**

| 州 | tier1 | tier2 | tier3 | unrated | 合计 |
|---|---:|---:|---:|---:|---:|
| DE | 0 | 50 | 0 | 634,986 | 635,036 |
| NH | 0 | 0 | 100 | 4,215,686 | 4,215,786 |
| IA | 0 | 100 | 300 | 1,817,277 | 1,817,677 |
| **合计** | **0** | **150** | **400** | **6,667,949** | **6,668,499** |

### 1.1 逐层挪动表（`tier-moves.csv`，20 行，列 `layer_id,url,dialect_id,state,rows_n,tier_before,tier_after`）

| 州 | 层数 | rows_n 合计 | 迁移 |
|---|---:|---:|---|
| DE | **3** | **19,037** | 3 × tier3→tier2 |
| NH | **7** | **94,715** | 7 × tier3→tier2 |
| IA | **10** | **87,475** | 10 × tier3→tier2 |
| **合计** | **20** | **201,227** | 20 × tier3→tier2 |

与派单给的三组事实（3 / 7 / 10、19,037 / 94,715 / 87,475）**逐个复现**（`summary.json: tier_moves.by_state`）。

## 2. 三条口径落到代码与产物

### 2.1 geom_type：面/线取真实顶点，绝不当质心

| 实现点 | 说明 |
|---|---|
| `engine/inlet.py: wkb_vertex()` | 解 WKB Point / LineString / Polygon / MultiLineString / MultiPolygon（含 Z/M，类型号 %1000）：**点取自身，面取 `rings[0][0]`，线取 `paths[0][0]`**；解不了返回 `(None, None, "")`，不猜 |
| `engine/inlet.py: wkb_geom_type()` | 单独取几何类型名，供逐行 `geom_type` |
| `engine/dialects/sources.v1.yaml: overture-v1` | `geometry: wkb_point` → **`wkb_any`**（面/线也拿坐标，不再整行丢点）；nad/oa/tiger-interp/granit 补 `geom_type` 声明 |
| `engine/outlet_clean.py: geom_type_of / point_kind_of` | `point`→`point`；`polygon/polyline/multipoint`→`vertex`；插值→`interpolated`；GRANIT→`parcel_centroid`；行级实测优先，方言声明兜底，都没有记 `unknown` |
| 导出列 | 每行带 `geom_type`、`point_kind`、`pos_estimated`、`tier_basis`（`<ST>/graded.partNN.ndjson.gz`，26 列） |

**geom_type 分项（`<ST>/stats.json: geom_type_in / by_geom_type`）**

| 州 | 源行数 point / polygon / polyline / multipoint | 入库行（全部 point） | 有点行 |
|---|---|---|---|
| DE | 1,679,706 / 50 / 496 / 50 | 635,036 | 635,036 |
| NH | 6,472,564 / 695 / 450 / 0 | 4,215,786 | 4,215,786 |
| IA | 5,640,814 / 557 / 1,095 / 0 | 1,817,677 | 1,817,677 |

面/线源行入库 0 行，原因是**这些行本身没有街名**（grade X，低于 min_grade C），不是被几何口径丢掉——逐 geom_type 的 grade 分布：polygon 1,302 行、polyline 2,041 行、multipoint 50 行**全部 X**（复算命令见 §9）。

### 2.2 估算值可辨

- NH TIGER 插值：`pos_estimated=true`、`point_kind=interpolated`，**断言 `pos_estimated=true ∧ grade=S` 的行数 = 0**（`stats.json: s_with_pos_estimated=0`；三州都为 0）。该断言写在 `engine/pilot.py`，非 0 直接 `raise AssertionError` 中止该州。
- 插值行 grade 分布（NH）：A 3,790,095 + B 405 = **3,790,500 行，S = 0**。
- GRANIT 地块点：`point_kind=parcel_centroid`、`pos_estimated=false`（源侧声明的地块质心，不是插值）。
  **parcel_centroid 占 NH 入库行 10.09%（425,186 / 4,215,786）**，报告里一律称「地块质心」，不称地址点。

### 2.3 NH 替代脊柱：GRANIT 主 + TIGER 插值补位 + 交叉核对

- 主 / 补位：`priority granit=10 < tiger=40`；**新增硬约束**——真实点/顶点永远优先于插值（`engine/fusion.py: better()`，插值想盖真实点直接拒绝，与优先级无关）。
- 交叉核对（`engine/crosscheck.py` → `NH/crosscheck.json` + `NH/crosscheck-samples.csv`，seed=20261125，200 行抽样带行号）：

| 项 | 值 |
|---|---:|
| 两个源都有的 addrkey | **351,361** |
| 只被插值覆盖的 addrkey | **3,790,500** |
| 有真实点的 addrkey | 425,286 |
| 最小距离 p50 / p90 / p99 / max / 均值 | **98.0 m / 407.1 m / 45,841.0 m / 254,550.6 m / 1,308.0 m** |
| >100 m 占比（= 冲突占比） | **49.23%**（172,989 / 351,361） |
| 冲突行数 | 172,989（provenance 全留，**没有静默丢弃**） |

**这条必须直说**：TIGER 街段插值位置与 GRANIT 地块点在同址上分歧极大（一半超 100 m，p99 已到 45 km 量级），
插值不能当真实点用——这正是本轮把它标成 `pos_estimated/interpolated` 且禁止进 S 的原因。p99/max 的长尾
说明还有「同一街名门牌在不同城镇重复」这类键归一噪声，`NH/crosscheck-samples.csv` 里可按行号逐个查。

## 3. 三州结果与逐列对比（`comparison.json`）

| 州 | 指标 | 第 6 步 | 本轮 | 差额 |
|---|---|---:|---:|---:|
| DE | 输入 / 去重 | 1,742,369 / 635,036 | 1,742,369 / 635,036 | 0 / 0 |
| DE | S / A / B / C | 634,879 / 14 / 143 / 0 | 634,879 / 14 / 143 / 0 | 0 / 0 / 0 / 0 |
| DE | 有点行 / 多源同址 / 冲突 | 635,036 / 519,723 / 6,894 | 635,036 / 519,723 / 6,894 | 0 / 0 / 0 |
| NH | 输入 / 去重 | 6,473,709 / 4,215,786 | 6,473,709 / 4,215,786 | 0 / 0 |
| NH | S / A / B / C | 50 / 3,790,095 / 425,641 / 0 | 50 / 3,790,095 / 425,641 / 0 | 0 / 0 / 0 / 0 |
| NH | 有点行 / 多源同址 / 冲突 | 4,215,786 / 920,951 / 819,849 | 4,215,786 / 920,951 / 819,849 | 0 / 0 / 0 |
| IA | 输入 / 去重 | 6,097,989 / 1,817,677 | 6,097,989 / 1,817,677 | 0 / 0 |
| IA | S / A / B / C | 1,422,912 / 255,418 / 139,347 / 0 | 1,422,912 / 255,418 / 139,347 / 0 | 0 / 0 / 0 / 0 |
| IA | 有点行 / 多源同址 / 冲突 | 1,817,677 / 1,386,229 / 133,485 | 1,817,677 / 1,386,229 / 133,485 | 0 / 0 / 0 |

丢行侧（同为零差）：DE unkeyed 5,437 / low_grade 1,863 / out_of_state 377,823；NH 103,552 / 2,260 / 354,804；
IA 739 / 56,114 / 1,271,283。

## 4. 差额归因（只许两类，逐条落数）

| 归因类 | 本轮实测 | 对行数/分级的影响 |
|---|---|---|
| ① 分档换了（20 层 tier3→tier2） | 这 20 层在三州样本里共 **934 行**（DE 150 / NH 327 / IA 457），逐行判级**全部 X**（无街名，低于 C）→ 计入 `dropped_low_grade`；`moved_basis_rows = 0`（没有任何入库行的 tier_basis 指向这 20 层） | **0 行**（tier 分布也不变：挪动层没有入库行） |
| ② 几何口径改了（面/线顶点、真实点优先于插值） | Overture WKB 实测 **100% Point**（DE 751,180 / IA 2,221,590 行）；面/线样本行 3,393 行全部 grade X；NH 有 351,378 行 provenance 同时含插值与真实点，赢家是真实点（与第 6 步同） | **0 行** |

除这两类之外**没有第三种差额来源**：三州 `rows_in / dedup / dup / unkeyed / low_grade / out_of_state / 多源 / 冲突` 全部逐位相同（`comparison.json`）。

## 5. 行数闭合账（本轮新增，`row-account.json`）

第 6 步只给了 5 个丢行计数，没有恒等式。本轮补上并验证差额为 0：

```
rows_in - range_only_rows = low_grade + unkeyed_total + fused_total + dup_rows
DE: 1,680,302 = 1,863 + 6,331 + 876,581 + 795,527 = 1,680,302  → diff 0
NH: 6,473,709 = 2,260 + 103,552 + 4,215,786 + 2,152,111 = 6,473,709 → diff 0
IA: 5,642,466 = 56,114 + 3,427 + 2,253,882 + 3,329,043 = 5,642,466 → diff 0
```

**必须披露的一个既有事实（不是本轮引入）**：DE 241,545 行 + IA 436,205 行 = **677,750 行** OpenAddresses 行
`REGION` 为空 → 它们进了融合库（可与同键行合并），但按州导出时被排除，既不算 out_of_state 也没有单独计数。
本轮把它显式记为 `no_state_fused` / `no_state_unkeyed`（DE 894 / IA 2,688），不再无声消失。
下一步建议：给 OA 空州行做州归属补全（用 county/zip 交叉），或明确写进丢行口径。

## 6. 代码改动（逐文件 diff 统计）

| 文件 | 行数 | 变更 | 说明 |
|---|---:|---|---|
| `engine/inlet.py` | 297 | +60 / −4 | `wkb_vertex / wkb_geom_type`；`wkb_any` 分发；行级 `geom_type` 透传 |
| `engine/outlet_clean.py` | 203 | +41 / −1 | `geom_type_of / point_kind_of / apply_geometry`（口径三项） |
| `engine/fusion.py` | 229 | +82 / −19 | 新列 `geom_type/point_kind/pos_estimated/tier_basis`；真实点优先于插值的硬约束；`by_geom_type / by_point_kind / s_with_pos_estimated` 统计；`add(rec, tier, tier_basis)` |
| `engine/pilot.py` | 272 | +104 / −13 | `(url,dialect_id)` 分档 join + `tier_basis`；S∧插值断言；`tier-moves.csv`；NH 交叉核对挂载；geom_type 统计入 stats |
| `engine/config/pilot.yaml` | 124 | +4 / −3 | `repo.tiers` → 放宽表、`repo.tiers_strict` → 第 5 步表；`outdir` → 本轮目录 |
| `engine/dialects/sources.v1.yaml` | 124 | +8 / −1 | overture `wkb_any`；各源 `geom_type` 声明 |
| `engine/crosscheck.py` | **93（新）** | +93 | NH 交叉核对（距离分布/冲突/覆盖计数 + 抽样 CSV） |
| `engine/tests/test_pilot_rerun.py` | **150（新）** | +150 | 6 条新单测 |

合计：`6 files changed, 263 insertions(+), 38 deletions(-)` + 2 个新文件 243 行。

## 7. 测试

```
python3 -m pytest engine/tests sandbox -q  →  166 passed（第 6 步基线 148 + 本轮新增 6 + 第 7 步分档 12）
```

新增 6 条（要求 ≥5）：
1. `test_tier_join_is_url_plus_dialect`——同 url 两个 dialect_id 各自成项、不互相覆盖；空 url 不入表
2. `test_same_layer_id_different_url_not_merged`——同 layer_id 不同 url 是两层
3. `test_polygon_polyline_take_real_vertex_not_centroid`——面/线取 `rings[0][0]`/`paths[0][0]`，且 ≠ 质心
4. `test_interpolated_never_grade_s`——插值行 `pos_estimated=true / interpolated`，永远不到 S
5. `test_real_point_beats_interpolation_even_if_lower_priority`——真实点即使优先级更低也接管插值，provenance 全留
6. `test_nh_crosscheck_distance_and_conflict_counts`——构造样本上的距离/冲突/覆盖计数

## 8. 产物清单

| 文件 | 内容 |
|---|---|
| `summary.json` | 三州合并统计 + 分档表信息 + `tier_moves`（20 行三组数）+ 闭合 |
| `tier-moves.csv` | 20 行逐层挪动表 |
| `unsupported.csv` | **0 条**（仅表头；本轮全部源/方言均支持） |
| `row-account.json` | 逐州行数闭合恒等式 + `no_state_*` 披露 |
| `comparison.json` | 与第 6 步逐列对比 + 归因计数（`moved_basis_rows` 等） |
| `<ST>/graded.partNN.ndjson.gz` | 26 列分级行（含 `geom_type/point_kind/pos_estimated/tier_basis/contributors`） |
| `<ST>/stats.json` | 输入/去重/多源/冲突/Tier×Grade/by_grade/with_point/geom_type 分项/`s_with_pos_estimated` |
| `<ST>/tiger-streets.csv.gz` | DE 62,067 / IA 455,523 条街段区间确认的街名键 |
| `NH/crosscheck.json` + `crosscheck-samples.csv` | 交叉核对汇总 + 200 行抽样（seed 20261125，带行号） |
| `compare_rounds.py` / `row_account.py` | 上面两张表与闭合账的生成脚本 |

## 9. 复算命令

```bash
python3 engine/pilot.py                                              # 三州全量（本轮实测约 70 分钟）
python3 -m pytest engine/tests sandbox -q                            # 166 passed
python3 analysis/engine-pilot-rerun-20261125/row_account.py          # 行数闭合账（需 _work/*.sqlite）
python3 analysis/engine-pilot-rerun-20261125/compare_rounds.py       # 与第 6 步对比 + 归因
```

面/线样本为何 0 入库（§2.1 末）复算：
```bash
python3 - <<'EOF'
import csv,json,collections,yaml,sys; sys.path.insert(0,'.')
from engine import outlet_clean as oc
g=yaml.safe_load(open('engine/config/pilot.yaml'))['grades']
c=collections.Counter()
for st in ('DE','NH','IA'):
  for r in csv.DictReader(open(f'analysis/coord-samples-20261124/samples/{st}.csv')):
    af=json.loads(r['addr_fields_json'] or '{}')
    rec=oc.clean({"number":af.get('house_number') or '',"street":af.get('street_full') or af.get('street_name') or '',
                  "city":af.get('postal_city') or '',"state":r['state'],"zip":af.get('zip5') or '',
                  "lon":r['lon'],'lat':r['lat'],'geom_type':r['geom_type']},{"precision":"mixed"})
    c[(rec['geom_type'],oc.grade_of(rec['features'],g))]+=1
print(sorted(c.items()))
EOF
```

## 10. 未跑项 / 拿不到的数（如实列）

1. **没有可入库的面/线行**：三州的面/线只出现在方言层坐标样本里，且全部无街名（grade X）。顶点解析路径由单测覆盖，但**本轮数据上 0 行入库**——不是口径没实现。
2. **Overture DE/IA 全为 Point**（实测），所以「非点几何不给坐标」这个缺口在本轮三州数据的**数值影响为 0**；修的是代码能力，不是这三州的数。
3. **OA 空州 677,750 行**（DE 241,545 / IA 436,205）未做州归属补全，只在导出口径外单列。
4. NH 交叉核对的长尾（p99 45.8 km / max 254.6 km）只做了分布与冲突计数，**没有逐键判定谁对**（无第三方真值）；需要真值才能定性。
5. 未做点落县 FIPS 归属、ZIP-ZCTA 交叉校验（仍 unavailable，与第 6 步同）。
6. 未改 `registry/`、未动 `collect/schema/sandbox`、未写账本、未发 Release、未起 Actions、未合并任何 PR。
