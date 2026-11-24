# 方言注册表 v1（`dialects.v1`）

一句话：**一个方言 = (provider 身份, 上游字段命名模板, 几何/点位语义) 三元组的稳定组合**。
注册表是**声明式**的（YAML 为主），只有声明式表达不了的才允许写成插件。

```
registry/
  dialects.v1.yaml          # 注册表本体（生成物，见"怎么生成"）
  evaluator.py              # golden-test 专用纯函数评估器（≤250 行，不进生产链路）
  validate.py               # 校验器：缺 golden case / 缺粒度 / 缺 CRS / 分母不闭合 → exit 1
  plugins/split_unit.py     # 插件：门牌里夹带单元号（12A / 12 #4）
  plugins/split_range.py    # 插件：门牌区间 100-104 → low/high/中点
  tests/test_registry_v1.py # pytest：全部 golden case + 插件 + validate 正/反向
```

跑法（全部离线，不联网）：

```bash
python3 registry/validate.py                       # 结构 + 分母闭合
python3 -m pytest registry/tests -q                # golden cases + 插件 + 反向验证
```

## 怎么加一个方言（5 步：从 CSV 证据到 YAML 到 golden case）

### 1. 先拿证据，别先写 YAML

- **上游字段名**只能来自 `?f=json`：`analysis/dialect-20261124/probe_fields.py` 会按 provider 探 1 次 meta，
  结果落 `probe-fields.ndjson`（含 `fields` / `sr` / `geometryType`）。
- **真实样值**只能来自 `inventory-local-fields.csv` 的 `samples`（pipe 分隔）或 dist 抽样。
- 两者都没有 → 这个方言**不许注册**，写进分析报告即可。`validate.py` 不会帮你凑。

### 2. 定别名族（按族聚，不按单字段聚）

六个族：`number | street | unit | place | state | zip`。族签名是 6 位 presence（如 `t110101`）。
新别名要先进 `analysis/dialect-20261124/build_dialects.py` 的 `FAMILIES` 正则（**number 优先于 street**，
`parcelnum/route_num/phone_number` 这类必须落在 `NUM_NEG_FIELD` 里排除），再重跑分组。

### 3. 定几何/点位粒度（枚举，不许自创）

`building_point | apartment_unit_point | parcel_centroid | range_interpolation | centerline_midpoint | unknown`

- 依据只能是：探针 `geometryType` + 标题/服务名关键词（`AddressPoint/Addresses/911`、`Parcel/Situs`、`Centerline`、`Range`、`Unit/Apt`）。
- **只有 Point 几何但标题无关键词 → 写 `unknown`**，且 `a_pool_eligible: false`（不许猜成 building_point）。

### 4. 定坐标系（不许按"美国默认 4326"）

```yaml
crs: {epsg: 2286, datum: declared_by_service, basis: declared, evidence: "probe spatialReference 分布 [[2286, 29], ...]"}
```
无证据写 `{epsg: unknown, datum: unknown, basis: unknown, evidence: "unavailable"}` —— `validate.py` 只要求键在，不要求有值，
但**必须有这个键**，防止悄悄漏掉。

### 5. 写 3–5 条 golden case（真实参数，不许编）

```yaml
- id: gc-0NN
  dialect_id: <你的方言 id>
  source_layer: /data/workspace/world-map-data-33/dist/intake-full/layers/<dir>   # 必须真实存在
  source_table: addr
  source_fields: {housenumber: house_number, street: street_name, zip: zip5}     # canonical 侧
  input: {Number: "181", StreetName: "ALEGRIA", ZipCode: "91024"}                # 上游别名 → 真实样值
  expect: {housenumber: "181", street: "ALEGRIA", zip: "91024"}
  expect_flags: [no_zip_ok]
```

规则：
- `input` 的键必须是**该 provider 探针里真实出现的字段名**，值必须是 `inventory-local-fields.csv` 里真实存在的样值；
- `expect` 至少含 `housenumber` 与 `street`（minimal_safe 的底线）；
- 每条 `source_layer` 必须真实存在（pytest 会 `os.path.isdir` 检查）；
- 少于 3 条 → `validate.py` exit 1，别想合。

### 生成 vs 手改

`dialects.v1.yaml` 是**生成物**：

```bash
python3 analysis/dialect-20261124/build_dialects.py    # 分组 → dialect.json / *.csv
python3 analysis/dialect-20261124/gen_registry.py      # 生成 registry/dialects.v1.yaml
python3 analysis/dialect-20261124/build_dialects.py    # 再跑一遍（两遍收敛：只注册真能出 ≥3 条 case 的组）
```

手改 YAML 会在下一次生成时被覆盖；要改规则请改生成脚本或 `FAMILIES` 正则。

## 兜底（`minimal_safe`）的硬约束

| 约束 | 说明 |
|---|---|
| 只取两要素 | 门牌 + 街名；缺任一 → `parsed={}` + `reason=minimal_safe_incomplete` |
| `pool` 恒为 `manual` | 即使两要素都命中也不进 A 货池 |
| `a_pool_eligible` 恒为 `false` | 硬编码在 `evaluator.minimal_safe()`，没有开关 |
| reason 必填 | `template_unresolved / share_below_1pct / alias_conflict / geom_unsupported / no_golden_evidence` |

`no_golden_evidence` 是 v1 新增的第 5 个 reason：模板已解析但该组没有任何真实样值层（造不出 golden case）——
它不是"认不出"，是"证不了"，所以单列，不与 `template_unresolved` 混。

## 边界（v1 明确不做）

- 不做地址标准化/分词/同义词扩充（那是引擎的事，见第 6 步）；
- 不做实体去重、不做 A/B 货判定（只给 `a_pool_eligible` 这个**前置标记**）；
- `evaluator.py` 不许长成引擎：它的唯一消费者是 `tests/`。
