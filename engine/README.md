# engine/ —— 主体融合引擎（第 6 步）

四模块 + 配置 + 单测。只读消费第 4 步方言表、第 5 步分档结果与第 6 步前置坐标样本；
`registry/`、`sandbox/`、`collect/` 一个字节都不改。

```
engine/
├── inlet.py                 入口：3 类适配器 + 方言解析（registry → engine 扩展 → unsupported）
├── outlet_clean.py          出口：统一清洗 + addrkey v3（复用 collect/lib/addrkey.py 的归一）
├── fusion.py                融合：addrkey v3 去重 + 源优先级 + 分档×完整度 + provenance（sqlite 落盘）
├── pilot.py                 试点 runner：DE/NH/IA → analysis/engine-pilot-20261125/
├── config/pilot.yaml        全部阈值：优先级 / 分级规则 / 冲突距离 / addrkey 开关
├── dialects/sources.v1.yaml 5 个源族方言（nad / oa / tiger / granit / overture）+ 方言层样本
└── tests/                   43 条单测（addrkey v3 归一、去重、分级、适配器、方言解析）
```

跑法：

```bash
python3 engine/pilot.py --dry-run            # 体检源与方言，只出 unsupported 清单
python3 engine/pilot.py --states DE          # 单州
python3 engine/pilot.py                      # 配置里的三州
python3 -m pytest engine/tests sandbox -q    # 新引擎单测 + 原有沙盒回归
```

## 一、addrkey v3 口径（去重键）

| 项 | 口径 |
|---|---|
| 版本前缀 | `a3:`（**v1/v2 是竖线拼接的明文键，无前缀；v3 不与它们混用**） |
| 参与字段 | `state(2) \| zip5 \| num \| street_key \| unit_key`，五段用 `\x1f` 连接 |
| state | 两位州码大写；非两位 → 空 |
| zip5 | 取前 5 位数字（`03249-1234` → `03249`）；空/占位 → 空（**不入键，不补 00000**） |
| num | `collect/lib/addrkey.py:num_key`：数字段 + 可选单字母后缀（`425b`→`425B`），`123-45` 保留 |
| street_key | `collect/lib/addrkey.py:street_key` → `TYPE\|CORE\|DIR`：后缀缩写全称化（RD→ROAD）、方向词独立保留（N/S/E/W 不许丢）、序数词归一（SEVENTH→7） |
| unit_key | `collect/lib/addrkey.py:unit_key`：`APT 5`/`#5`/`STE 5` → `5`；`include_unit: false` 时统一记为 `#`（同址合并） |
| hash | `sha1("\x1f".join(parts)).hexdigest()[:20]` → 键长 23 字符 |
| 不可键 | num 或 street 缺 → 返回 `""`，进 `unkeyed` 表（不算丢，只是不参与去重） |
| 归一复用 | 全部复用 `collect/lib/addrkey.py`（仓库既有 v3 归一：NFKD 折音、UTF-8 安全）；本引擎只补 state/zip/城市/合并地址串/坐标校验 |

单测：`engine/tests/test_outlet_clean.py`（24 条），覆盖前缀/稳定性/缩写等价/方向词/单元开关/占位值/0,0 与越界/插值标记/分级边界。

## 二、方言支持矩阵

解析顺序：`registry/dialects.v1.yaml`（冻结只读）→ `engine/dialects/*.yaml` → **unsupported（落清单，不猜）**。

| 方言 id | 来源 | 适配器 | 坐标/精度 | 状态 |
|---|---|---|---|---|
| `agol-t110101-buildingpoint` | registry（第 4 步） | `arcgis` / `ndjson` | 服务返回几何 | registry 命中 |
| `agol-t110111-buildingpoint` | registry | `arcgis` / `ndjson` | 同上 | registry 命中 |
| `agol-t110000-buildingpoint` | registry | `arcgis` / `ndjson` | 同上 | registry 命中 |
| `nad-v1` | engine | `ndjson` | address_point | engine |
| `oa-v1` | engine | `zip_csv` | address_point | engine |
| `tiger-addrfeat-v1` | engine | `zip_shp` | **street_range（无点，不插值）** | engine |
| `tiger-interp-v1` | engine | `ndjson` | range_interpolation（`is_interpolated=true`） | engine |
| `granit-parcel-v1` | engine | `ndjson` | parcel_centroid（地块质心，源侧声明） | engine |
| `overture-v1` | engine | `parquet` | address_point（WKB 解码，非点几何不给坐标） | engine |
| `engine-dialect-samples-v1` | engine | `samples_csv` | 逐行 geom_type | engine |
| 其它任意 | — | — | — | **unsupported**（`dialect_not_defined:*` / `adapter_not_implemented:*`） |

适配器三类（`inlet.ADAPTERS`）：服务型 `arcgis`（分页 + `outSR=4326` + json）；
落盘型 `ndjson` / `zip_csv` / `samples_csv`；其它源 `zip_shp` / `parquet`。
方言表里没有的方言或没实现的适配器 → `unsupported.csv` 逐条列，不静默丢。

## 三、分档 × 完整度（全部可配，代码无硬编码）

- **分档（Tier）**：来自第 5 步重跑实测（`analysis/auto-spatial-rerun-20261125/layers-status.csv`）。
  融合后一条记录取「贡献源里最好的档」：`tier1 < tier2 < tier3 < unrated`（`tier_rank` 可配）。
  无 Tier 证据的原始源（NAD/OA/TIGER/GRANIT/Overture）记 `unrated`，**不冒充 Tier1**。
- **完整度（S/A/B/C）**：`config/pilot.yaml: grades` 每级给一组必须为真的特征，从 S 往 C 依次试：
  `S` 全要素 + 真实点；`A` 有点但缺城市或点来自插值；`B` 门牌+街名+州但无点；`C` 仅街名。
  低于 `min_grade` 的行不入库并计数（`dropped_low_grade`）。
- **冲突**：同一 addrkey 多源坐标相差 > `coord_conflict_m`（默认 100m）→ 记 `coord_conflict=1`，
  保留 `priority` 更高（数值更小）的源坐标，`contributors` 里保留全部来源与各自坐标。

改规则只改 `engine/config/pilot.yaml`（或换一份 config 传给 `--config`），引擎代码不动 ——
用户后定放宽 E3/E7 时，只需换分档输入重跑。
