# 第 6 步 · 主体融合引擎重写（engine-rewrite-20261125）

- 分支 `feat/engine-rewrite-20261125`，基线 `106899c`（main，PR #47 merge commit）
- 代码：`engine/`（入口 / 出口清洗 / 融合 / 试点 runner + 配置 + 方言扩展表 + 单测 + README）
- 产物：`analysis/engine-pilot-20261125/`（三州分级数据 + 统计 + 复算脚本）
- 只读消费：`registry/dialects.v1.yaml`（冻结）、`sandbox/*`（未改）、`analysis/coord-samples-20261124/`、
  `analysis/auto-spatial-rerun-20261125/`、`collect/lib/addrkey.py`（import，未改）

---

## 1. 设计

```
源 → [inlet 入口] → [outlet_clean 出口] → [fusion 融合] → 分级数据
      3 类适配器     统一 schema + addrkey v3   去重 + 优先级 + Tier×完整度 + provenance
```

### 1.1 入口（`engine/inlet.py`）

| 类别 | 适配器 | 覆盖源 |
|---|---|---|
| 服务型 | `arcgis`（分页 + `outSR=4326` + json） | ArcGIS Query/MapServer 全族（本试点未联网调用，供生产与单测） |
| 落盘型 | `ndjson`（.ndjson/.ndjson.gz）、`zip_csv`（OA 打 zip 的 CSV）、`samples_csv`（坐标样本） | NAD、GRANIT、TIGER 插值、OpenAddresses、方言层样本 |
| 其它源 | `zip_shp`（TIGER addrfeat 街段区间）、`parquet`（Overture，WKB 点解码） | TIGER DE/IA、Overture DE/IA |

方言解析顺序：**registry（第 4 步，冻结）→ engine 扩展表 → unsupported**。
registry 里只有 3 支 `agol-*` 方言；本轮在 `engine/dialects/sources.v1.yaml` 补 6 支源族方言
（`nad-v1`/`oa-v1`/`tiger-addrfeat-v1`/`tiger-interp-v1`/`granit-parcel-v1`/`overture-v1`/`engine-dialect-samples-v1`），
每支写清字段映射、坐标系、精度语义。**方言表里没有的方言、没实现的适配器 → `unsupported.csv` 显式落清单**，
本轮 14 个源全部解析成功（`unsupported` = 0 条），机制由 `engine/tests/test_inlet.py` 的单测守住。

### 1.2 出口（`engine/outlet_clean.py`）

统一 schema：`number / street / post_type / pre_dir / post_dir / unit / city / state / zip5 / lon / lat / precision / is_interpolated`。
归一规则**复用** `collect/lib/addrkey.py`（NFKD 折音 + 后缀全称化 + 方向词保留 + 单元号去前缀），
本模块只补州/邮编/城市/合并地址串解析/坐标合法性/插值标记。

### 1.3 addrkey v3 口径

```
parts = [state(2), zip5, num, street_key(TYPE|CORE|DIR), unit_key]
key   = "a3:" + sha1("\x1f".join(parts)).hexdigest()[:20]        # 23 字符
```
- 版本前缀 `a3:` 固定，**不与 v1/v2 混用**（v1/v2 是无前缀的竖线明文键，字段集也不同）
- `unit` 默认入键（同一栋楼不同单元是不同地址行）；`include_unit: false` 时单元统一记 `#`
- num 或 street 缺 → 不可键 → 进 `unkeyed` 表（不丢弃、不冒充）
- 单测 24 条：前缀/稳定性/缩写等价（`Barbara Drive` == `barbara DR` + `type=DR`）/方向词不许丢/单元开关/占位值/`(0,0)` 与越界/插值标记/分级边界

### 1.4 融合（`engine/fusion.py`）

- **去重**：sqlite 落盘表按 addrkey v3 主键合并，`contributors` 保留全部来源的 provenance（源 id、tier、grade、坐标、精度、是否插值）
- **冲突**：同址多源坐标相差 > `coord_conflict_m`（默认 100m）→ `coord_conflict=1`，保留 `priority` 数值更小源的坐标
- **分档**：取贡献源里最好的 Tier（`tier1 < tier2 < tier3 < unrated`）
- **完整度**：`S/A/B/C` 由 `config/pilot.yaml: grades` 的特征集合判定；低于 `min_grade` 不入库并计数

### 1.5 参数化（关键：用户改规则不用改引擎）

`engine/config/pilot.yaml` 里全是你可改的东西：`priority`（源权威顺序）、`tier_rank`、
`grades`（S/A/B/C 各需要哪些特征为真）、`min_grade`、`coord_conflict_m`、`addrkey.include_unit`。
代码里没有硬编码的分档/分级阈值。**放宽 E3/E7 规则时，只需换分档输入（`auto-recognized.csv`）重跑**，
`python3 engine/pilot.py --config other.yaml`。

## 2. 三州试点结果

> 数字全部来自 `analysis/engine-pilot-20261125/recompute-stats.json`（由 `recompute.py` 只读产物重算），
> 明细见同目录 `<STATE>/stats.json` 与 `<STATE>/graded.ndjson.gz`。

### 2.1 去重前后（输入 → addrkey v3 去重后）

| 州 | 输入行数 | 去重后 | 合并掉 | 多源同址 | unkeyed | 低于 min_grade 丢弃 | 跨州丢弃 | 有坐标 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DE | 1,742,369 | 635,036 | 795,527 | 519,723 | 5,437 | 1,863 | 377,823 | 635,036 |
| NH | 6,473,709 | 4,215,786 | 2,152,111 | 920,951 | 103,552 | 2,260 | 354,804 | 4,215,786 |
| IA | 6,097,989 | 1,817,677 | 3,329,043 | 1,386,229 | 739 | 56,114 | 1,271,283 | 1,817,677 |
| **合计** | **14,314,067** | **6,668,499** | **6,276,681** | — | 109,728 | 60,237 | 2,003,910 | **6,668,499** |

- 「多源同址」= 该 addrkey 有 ≥2 个源贡献（DE 81.8% / NH 21.8% / IA 76.3%）：三州能做到多源互证的地址都拿到了
- 「跨州丢弃」来自源文件本身混入邻州行（DE：NAD OUTOFSTATE 188,922 + Overture 188,901；NH：NAD 那份其实全是 MA/ME/VT 残片；IA：NAD/OA/Overture 混入邻州）—— 按 row 的 `state` 过滤，不是丢数据
- `unkeyed`（缺门牌或街名，不可键）单列入库，不参与去重：NH 103,552 行（GRANIT 无门牌的地块）、DE 5,437、IA 739

### 2.2 完整度 S/A/B/C

| 州 | S | A | B | C | 说明 |
|---|---:|---:|---:|---:|---|
| DE | 634,879 (99.98%) | 14 | 143 | 0 | NAD/Overture/OA 都带 city+zip+真实点 → 几乎全 S |
| NH | 50 | 3,790,095 (89.9%) | 425,641 | 0 | A 级主力是 TIGER 插值点（`point` 特征为假）+ GRANIT 无邮编 → 落到 B |
| IA | 1,422,912 (78.3%) | 255,418 | 139,347 | 0 | NAD/Overture 带 zip+点 → S；OA 缺城市/邮编 → B |

### 2.3 分档 × 完整度

| 州 | tier1 | tier2 | tier3 | unrated |
|---|---|---|---|---|
| DE | 0 | **50（S）** | 0 | 634,986（S 634,829 / A 14 / B 143） |
| NH | 0 | 0 | **100（S 50 / B 50）** | 4,215,686（A 3,790,095 / B 425,591） |
| IA | 0 | **100（B）** | **300（S 150 / B 150）** | 1,817,277（S 1,422,762 / A 255,418 / B 139,097） |

Tier 只可能来自「方言层贡献」的那条 provenance（原始档没有 E1–E8 实测）；三州合计 **550 行带实测档位**
（tier2 150 + tier3 400），其余 6,667,949 行是 `unrated`。**Tier1 = 0 是结构性的**，见 §3.1。

### 2.4 每州输入源

| 州 | 源 | 方言 | 适配器 | 文件 | 输入行 | 耗时 |
|---|---|---|---:|---:|---:|---:|
| DE | nad | `nad-v1` | ndjson | 4 | 562,290 | 154s |
| DE | oa | `oa-v1` | zip_csv | 5 | 553,848 | 130s |
| DE | tiger | `tiger-addrfeat-v1` | zip_shp | 3 | 62,067（街段区间，不出点） | 6s |
| DE | overture | `overture-v1` | parquet | 1 | 562,288 | 194s |
| DE | dialect | `engine-dialect-samples-v1` | samples_csv | 1 | 1,876 | 0.1s |
| NH | granit | `granit-parcel-v1` | ndjson | 10 | 601,355 | 122s |
| NH | tiger | `tiger-interp-v1` | ndjson | 1 | 5,870,025（上游插值） | 1,249s |
| NH | nad | `nad-v1` | ndjson | 1 | 0（该文件全是邻州残片，按州过滤） | 38s |
| NH | dialect | `engine-dialect-samples-v1` | samples_csv | 1 | 2,329 | 0.2s |
| IA | nad | `nad-v1` | ndjson | 100 | 1,586,226 | 473s |
| IA | oa | `oa-v1` | zip_csv | 58 | 2,466,617 | 529s |
| IA | tiger | `tiger-addrfeat-v1` | zip_shp | 99 | 455,523（街段区间，不出点） | 45s |
| IA | overture | `overture-v1` | parquet | 1 | 1,585,872 | 426s |
| IA | dialect | `engine-dialect-samples-v1` | samples_csv | 1 | 3,751 | 0.3s |

### 2.5 坐标一致性（同址多源）

| 州 | 同址坐标冲突行（>100m） | 占比 | 主因 |
|---|---:|---:|---|
| DE | 6,894 | 1.1% | NAD 与 Overture 门牌点微差 |
| NH | 819,849 | 19.4% | **GRANIT 地块质心 vs TIGER 街段插值点**：一个是地块中心、一个在街道中心线上，差 100m+ 是口径差不是错 |
| IA | 133,485 | 7.3% | NAD/OA/Overture 门牌点 vs 街区位置 |

冲突行一律保留 `priority` 更高源的坐标，`contributors` 里两条坐标都留档，第 7 步可按县界+距离分位裁决。


## 3. 已知限制（不美化）

1. **试点三州没有 Tier1 层**：第 5 步的 30 个 Tier1 层全部落在「未定位州」桶（21）+ TX(6)+CA(2)+IL(1)，
   DE/NH/IA 的最好是 Tier2（DE 4 层、IA 9 层、NH 0 层）。所以试点里 `S/A/B/C × Tier1` 全 0 是**结构性**结果，
   不是引擎丢数 —— 想看到 Tier1 行，试点州要换成 TX 或补一轮 Tier1 层的坐标样本。
2. **原始档没有分档证据**：NAD/OA/TIGER/GRANIT/Overture 在 registry 里没有对应层，也没有 E1–E8 实测，
   因此一律记 `unrated`（占试点行的绝大多数），**没有冒充 Tier1/2/3**。
   分档只可能来自「方言层贡献」的那一条 provenance。
3. **DE 无州脊、IA 无门牌点**：DE 没有 GRANIT（GRANIT 只覆盖 VT/NH），IA 的 TIGER 只有 addrfeat 街段区间
   （无门牌点）。IA 的点来自 NAD/OA/Overture，TIGER 只用来确认街名（`<STATE>/tiger-streets.csv.gz`，**区间不出点、不插值**）。
4. **TIGER NH 是上游插值**：`is_interpolated=true` 的行最高只能到 A 级（`point` 特征为假），不会被算成真实点。
5. **arcgis 适配器本轮未联网跑**：试点全部吃落盘数据；分页/坐标系逻辑有单测，但没有线上实测记录。
6. **`coord_conflict` 只标记不裁决语义**：冲突保留高优先级源坐标，哪一方对需要第 7 步做地址级复核。
7. **未做**：跨州同址合并（试点按州分库）、邮编↔城市交叉校验（仓库无 ZCTA 表）、建筑轮廓距离（无数据源）、
   `unkeyed` 行的二次解析（只入库不解析）。

## 4. 下一步建议

1. **把分档证据补齐到试点州**：给 DE/NH/IA 的 Tier2 层补 50 行以上坐标样本 → E3/E7 可测 → 才有 Tier1 可放。
2. **TIGER 门牌点**：IA 想出 B 级以上，需要 addrfeat 的插值产物（上游已有 NH 的做法）；本轮故意不做，避免造点。
3. **打通服务型入口**：`arcgis` 适配器上线跑一次真层，验证分页与 `outSR` 行为。
4. **冲突裁决**：`coord_conflict=1` 的行（DE 6,894 / IA 见产物）建议第 7 步按县界点落 + 距离分位做裁决。
