# 三州试点产物（第 6 步 · engine-pilot-20261125）

本目录只有引擎跑出来的数据与统计，**没有手工填的数字**。所有数字可由
`python3 analysis/engine-pilot-20261125/recompute.py` 从下面的产物重算。

| 文件 | 内容 | 复算依据 |
|---|---|---|
| `summary.json` | 三州合并统计 + 配置快照（优先级/分级规则/addrkey 开关）+ 方言表清单 | 引擎写 |
| `unsupported.csv` | 方言/适配器不支持清单（本轮为空 —— 14 个源全部解析成功） | `engine/inlet.py:probe_sources` |
| `<STATE>/graded.ndjson.gz` | 去重后分级行：`addrkey, number, street, ..., lon, lat, precision, is_interpolated, tier, grade, source_id, source_family, n_sources, coord_conflict, contributors` | 引擎写，`recompute.py` 全量扫 |
| `<STATE>/stats.json` | 该州输入/去重/丢弃/分级分布/Tier×Grade 网格/源明细 | 引擎写 |
| `<STATE>/tiger-streets.csv.gz` | 仅 DE/IA：TIGER addrfeat 街段区间确认的 `(state, street_key)`，**区间不出点** | 引擎写 |
| `recompute.py` / `recompute-stats.json` | 复算脚本与复算结果 | 只读上面的文件 |
| `_work/<STATE>.sqlite` | 去重过程库（可断点/可追查），**不进 git** | 引擎写 |

## 目录口径

- 一行 = 一个 addrkey v3（`a3:` 前缀，见 `engine/README.md` 的键口径表）
- `tier` ∈ `tier1/tier2/tier3/unrated`：来自第 5 步实测分档（`analysis/auto-spatial-rerun-20261125/auto-recognized.csv`，
  按 `url` 对齐）；NAD/OA/TIGER/GRANIT/Overture 这些原始档没有分档证据 → `unrated`，不冒充 Tier1
- `grade` ∈ `S/A/B/C`：完整度，规则在 `engine/config/pilot.yaml: grades`
- `contributors`：该 addrkey 下所有源记录的 provenance（源 id、tier、grade、各自坐标、精度、是否插值）
- `coord_conflict=1`：同址多源坐标相差 > `coord_conflict_m`（默认 100m），此时保留 `priority` 更高源的坐标

## 原始输入（只读，不在本仓库内）

| 源 | 路径 | 说明 |
|---|---|---|
| NAD | `/data/scratch/calib-20261123/{de,ia}/NAD-*.ndjson.gz`、`/data/scratch/calib-20261123/nh/NAD-*.ndjson.gz` | 全国地址库切片 |
| OA | `/data/scratch/calib-20261123/{de,ia}/OA-*.zip` | OpenAddresses（zip 内 CSV） |
| TIGER（DE/IA） | `/data/scratch/calib-20261123/{de,ia}/TIGER-*-addrfeat.zip` | 街段+门牌区间，**无点**，只做街道确认 |
| TIGER（NH，已插值） | `/data/workspace/nh-collect-both/TIGER-US-NH-addrfeat-interpolated.ndjson.gz` | 上游已插值，行级 `is_interpolated=true` |
| GRANIT | `/data/workspace/nh-collect-both/GRANIT-US-NH-<fips>-parcel-points.ndjson.gz` | NH 州脊（地块质心） |
| Overture | `/data/scratch/calib-20261123/{de,ia}/OVERTURE-US-*.parquet` | 点几何（WKB）；文件里混有邻州行，按 `address_levels` 过滤 |
| 方言层样本 | `analysis/coord-samples-20261124/samples/{DE,NH,IA}.csv` | 第 6 步前置落盘，逐层 ≤50 行（带实测 Tier） |
