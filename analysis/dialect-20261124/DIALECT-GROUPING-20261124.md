# 核心特征方言分组 · 2026-11-24（v4 第五节「第 4 步」）

> 只分组 + 只搭注册表初版：**不融合、不分级、不重写引擎、不动 Release/账本/网站、未起任何 collect run**。
> 输入全部只读复用 `analysis/full-inventory-20261124/`（PR #43 已合入 main，merge `88c2bc0`），**未重跑盘点、未碰 3,709/4,682 账本**。
> 一键复跑：`python3 analysis/dialect-20261124/build_dialects.py` → `python3 analysis/dialect-20261124/gen_registry.py`。

## 〇、口径声明（先看这 5 条）

1. **分母写死在代码里，不用 `wc -l`**：CSV 里 3 条记录的 url 含控制字符被引号包成跨物理行，物理行数会比层数多 3。
   本文件所有层数都取「csv 解析后的记录数」或分片行数。
2. **方言 = (provider 身份, 上游字段命名模板, 几何/点位语义) 三元组**。三元组任一维无证据 → 不注册，进 `minimal_safe`（`status=manual`）。
3. **上游字段名只能来自 `?f=json`**：`inventory-local-fields.csv` 的字段是 stage-08 规范化后的 **canonical 字段**（只有 31 个：
   `house_number/street_name/postal_city/state_abbr/zip5/...`），**不携带上游命名信息**——所以「离线判模板」在这份输入上不可行，必须用 §五 的有界探针。
4. **不许按「美国」默认 4326**：CRS 一律取探针返回的 `spatialReference.wkid/latestWkid`；取不到写 `unknown` + `basis: unknown`。
5. **没有兜底桶**：认不出的层一律 `dialect_id=minimal_safe` 且 `status=manual` + 显式 `reason`；禁止 `other/misc/unknown_rest`（`registry/tests` 里有断言）。

## 一、分母闭合（三块，D3 只做 provider 聚类）

| 块 | 定义 | 层数 | 复算依据 |
|---|---|---|---|
| **D1** 远程有地址语义层 | `usable ∈ {full_address 1,994, no_zip 3,169, no_city 951, road_only 9,896}` | **16,010** | `inventory-remote-uncollected.csv` 逐行计数 |
| **D2** 本地可读层 | `readable=1` | **1,158** | `inventory-local-all.csv` |
| **方言判定分母** | D1 + D2 | **17,168** | `dialect-assignment.csv` 行数 = 17,168（自检 assert） |
| **D3** 观察集（不做方言判定） | 远程 `empty_shell` | **25,447** | 只做 provider 聚类（§六） |

行数分母（`count` 可用的层求和）= **984,719,364**；`count` 缺失 **3 层**（单列，不进分母，`count_unavailable_layers=3`）。

## 二、方法（落到可实现）

1. **provider 身份**：`services<N>.arcgis.com/<org>` → `agol:<org>`；`<host>/arcgis/rest` → `host:<domain>`；
   Socrata 域名 → `socrata:<domain>`；其余 → `dom:<domain>`；无 url（本地 417 个可读层）→ `none`。
2. **模板（别名族签名）**：按族聚、不按单字段聚。六族 = `number|street|unit|place|state|zip`，
   签名 = 6 位 presence（例如 `t110101`）。别名来自探针真实字段名；`situs_num/situs_street`、裸 `street`、`LSt_Name` 这类真实命名都已被覆盖。
   **族内只列真实出现过的别名**（见 YAML `template.*_aliases`），不做同义扩充。
3. **几何/点位语义**：枚举 `building_point|apartment_unit_point|parcel_centroid|range_interpolation|centerline_midpoint|unknown`，
   依据 = 探针 `geometryType` + 标题/服务名关键词（`AddressPoint/Addresses/911` / `Parcel/Situs` / `Centerline` / `Range` / `Unit/Apt`）。
   **只有 Point 几何但标题无关键词 → `unknown`（不猜 building_point）**，这类层落 `geom_unsupported`。
4. **长尾优先级**：`share = 组内 count 合计 / 984,719,364`。`share ≥ 2%` → `active`；`1%–2%` → `minimal_safe`（人工队列头部）；`< 1%` → `minimal_safe`。
5. **极碎合并**：`share < 1%` 且同 (kind + 签名) 的组合并为 `longtail:<kind>-t<bits>`，**逐条 provider 与层数**写在 `dialect.json` 的 `longtail[].providers`。

## 三、§五 有界探针（真的跑了，1,000/1,000 用满）

| 项 | 值 |
|---|---|
| 请求数 `requests_n` | **1,000**（硬上限 1,000；只发 meta `?f=json`，**不取样值、不下载资产**） |
| 轮次 1 | 328 次：`D1 ∩ 有同源本地可读层` 的 provider 各 1 个代表层（要保证能出 golden case） |
| 轮次 2 | 672 次：按 D1 `count` 合计从大到小补探未探 provider（`--mode highcov`），把模板可判率拉高 |
| 覆盖 | 1,000 / 5,080 个 D1 provider；对分母的影响：**6,112 层模板可判**（35.6% of D1+D2），其余 11,056 层 `template_unresolved` |
| 落盘 | `probe-fields.ndjson`（逐层 checkpoint，可续跑）；无重试、8s 超时、并发 8 |

## 四、分组结果（注册表 v1 = 3 个方言，均在 `registry/dialects.v1.yaml`）

| 方言 | 状态 | 层数 | count 合计 | share | 粒度 | EPSG（探针声明） | golden cases |
|---|---|---|---|---|---|---|---|
| `agol-t110101-buildingpoint` | **active** | 39 | 82,100,352 | **8.34%** | building_point | 2286 | 5 |
| `agol-t110111-buildingpoint` | minimal_safe | 72 | 6,468,377 | 0.66% | building_point | 3857 | 5 |
| `agol-t110000-buildingpoint` | minimal_safe | 12 | 1,789,915 | 0.18% | building_point | 3857 | 4 |

**状态分布（17,168 层）**：`active 39` / `minimal_safe 1,483` / `manual 15,646`。
**reason 分布**：`template_unresolved 11,056` / `geom_unsupported 4,590` / `share_below_1pct 1,379` / `no_golden_evidence 104` / `active 39`。

> `no_golden_evidence`（本轮新增的第 5 个 reason，更精确、不掩盖）：模板已解析但**该组没有任何真实样值层**，
> 造不出 golden case，因此不能进注册表。最大的一条 `longtail:agol-t010110` 有 **37 层 / 2.139 亿行（share 21.7%）**——
> 它是本轮**最大的已知缺口**，已排在人工队列第 2 位。

**长尾合并（67 组，Top 5）**：

| 组 | 层数 | count 合计 | provider 数 |
|---|---|---|---|
| `longtail:agol-t010110` | 37 | 213,931,670 | 3 |
| `longtail:agol-t110111` | 732 | 44,929,590 | 92 |
| `longtail:agol-t010101` | 555 | 31,923,355 | 94 |
| `longtail:agol-t000111` | 333 | 30,531,182 | 53 |
| `longtail:agol-t010000` | 504 | 29,864,182 | 73 |

（全部 67 组的 provider 与层数逐条在 `dialect.json` `longtail[]`，未静默归并。）

## 五、`minimal_safe` 与人工队列

- **minimal_safe 已真实现**（`registry/evaluator.py:minimal_safe`）：只取**门牌 + 街名**两要素；两要素齐也只给 `pool=manual`、
  `a_pool_eligible=False`；缺一个 → `parsed={}` + `reason=minimal_safe_incomplete`。**永不进 A 货池**（有 pytest 断言）。
- **人工队列** `manual-queue.csv`：`score = coverage_rows × anomaly_rate`（anomaly_rate = 组内 `road_only` 占比），
  按 score 降序；周上限来自 YAML `weekly_cap_layers: 200`（代码里取参数 `--weekly-cap`，不写死）；
  一个组可跨周（`week`..`week_end`，`weeks_spanned`），**组层数 ≤ 200 × 周数**，区间不重叠（pytest 断言）。
  队列 70 行，从头算需 ≈ 56 周才轮到最末尾的长尾（这也是「必须缩小 manual 面」的直接理由）。

## 六、D3 观察集（25,447 `empty_shell` 层）：只做 provider 聚类

provider 数 **7,148**；Top10 provider（层数）：`agol:Ezk9fcjSUkeadg6u` 198、`host:services-eu1.arcgis.com` 189、
`agol:KUeKSLlMUcWvuPRM` 146、`agol:jF2q3LPxL7PETdYk` 133、`agol:dXxgdxy3qGTavh0e` 131、`agol:YiULsZbgRKmBtdZN` 128、
`agol:uEH09Hfm70zI2ZxR` 113、`agol:99lidPhWCzftIe9K` 108、`agol:HmwnYiJTBZ4UkySc` 95、`agol:XxIGAEKiEx25pR4u` 86。

**这批层不做方言判定**：`empty_shell` = 探通了但样值里门牌/街名都没打中，可能是面/线要素，也可能是字段名不在识别表里——
在没有 golden case 的前提下判方言会是猜。它们进 D3 只为下一轮「哪些 provider 值得优先补探」提供排序依据。

## 七、证据边界（照实：为什么注册表只有 3 个方言）

1. **4,080 / 5,080 个 D1 provider 没有同源本地可读层** → 无真实样值 → 造不出 golden case → 按硬规则不能注册（只能 `manual`）。
2. **本地 417 个可读层没有 url** → provider 身份未知 → `template_unresolved`。
3. **canonical 字段这条死路**：本地字段表只有 31 个规范化字段名，反推不出上游命名；若不探针，模板只能靠 `fields_number_like`（只有 number 一族，且噪音大：
   `bldgarea/bike_notes/phone_number` 都在里面）。
4. 探针已用满 1,000 次配额（按 muse 的上限），继续提高覆盖率需要放宽请求上限或下载资产——**本轮不做**。

## 八、下一轮建议（给第 5 步）

1. **先打 21.7% 的那个缺口**：`longtail:agol-t010110`（37 层 / 2.14 亿行）只要补 3 层的真实样值（有界下载/取样），就能升成 active 方言。
2. **人工队列按 `week` 派单**，第 1–56 周的活儿全部压在 `minimal_safe`（11,056 层 `template_unresolved`）上：性价比最高的是先对这批做 provider 级去重（5,080 → 实际独立模板数远小于层数）。
3. **`road_only 9,896` 层要单独定策**：它们只有街名没有门牌，A 货池本来就不该收，建议在第 5 步直接按 `no_housenumber` 排除，不要占用人工队列。
4. **CRS 已经可以直接用**：328 个有本地同源的 provider 全是 `basis: declared`，其中 `3857` 占多数 —— 第 5 步的坐标系归一化不必再猜。
5. 插件只写了 `split_unit` / `split_range` 两个；如果第 5 步遇到「门牌 = 楼栋号 + 单元号 + 房间号」三段式，再按 `registry/README.md` 的 5 步加插件，别把逻辑塞进 YAML。
