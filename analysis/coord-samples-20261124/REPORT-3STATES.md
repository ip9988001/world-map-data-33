# 第 6 步前置 · 坐标样本采集 —— 三州先行（DE / NH / IA）

- 任务：muse-000217 / `task_id=w2-20261124-coord-samples`
- 分支：`feat/coord-samples-20261124`（基线 `e391d2d` = main，PR #45 merge commit）
- 本轮只采集 + 只写样本与报告：**不融合、不分级、不改引擎、不动空间验算模块、`registry/` 零改动**
- 报告数据全部可由本目录文件复算，复算命令见 §7

---

## 0. 对账表（清单必须闭合到 17,168）

来源：`analysis/dialect-20261124/dialect-assignment.csv`（第 4 步逐层分配表，只读）→
`layers.json`（本目录，`scripts/prep_layers.py` 生成，含每层 `layer_id/url/state/universe/...`）

| 项 | 值 | 说明 |
|---|---|---|
| 分母（`registry/dialects.v1.yaml: denominator`） | **17,168** | D1 16,010 远程 + D2 1,158 本地 |
| 清单行数 | **17,168** | 差额 **0** |
| D1 行数 / 唯一 url | 16,010 / **16,010** | 一族一 url，不合并 |
| D2 行数 / 唯一 url | 1,158 / 742 | D2 大量层共享同一 service url，但各有独立本地落盘目录 |
| 唯一 url 合计 | **16,752** | url 才是采样主键 |
| 无 url 行 | **417** | 全部 `universe=d2` 且 `provider_kind=none`；**不影响采样**：这些层在 `inventory-local-all.csv` 有 `layer_dir`，直接读本地 ndjson（命中 1,158/1,158） |
| 未定位州（`未定位`）/ 空州 | 7,802 / 410 | 第 4 步就这样标，本轮不改口径；落 `samples/_UNLOCATED.csv`、`samples/_UNKNOWN.csv` |
| 失配 / 落单条目 | **0** | 无一条 url 在第 4 步清单与 inventory 之间对不上 |

补齐规则：**没有触发 url 交集补齐**——17,168 行 url 字段无需外部补；几何语义也不靠推断，
每层 `wkid` / `geom_type` 一律取响应里的 `spatialReference` 与 `geometryType` 原样落盘
（第 4 步 `granularity=unknown` 的 12,218 层因此拿到了真实几何语义，见 `layers-status.csv`）。

---

## 1. 三州结果（DE / NH / IA）

`summary-3states.json` ← 由 `samples/{DE,NH,IA}.csv` + `layers-status.csv` 汇总：

| 州 | 层数 | ≥50 行 | partial | unavailable | 采样行数 |
|---|---:|---:|---:|---:|---:|
| DE | 41 | 33 | 8 | 0 | 1,876 |
| NH | 53 | 41 | 11 | 1 | 2,329 |
| IA | 83 | 69 | 14 | 0 | 3,751 |
| **合计** | **177** | **143** | **33** | **1** | **7,956** |

- 覆盖率（≥50 行）：**143 / 177 = 80.8%**；有任何坐标的（≥50 + partial）= 176 / 177 = 99.4%
- 采样来源：`arcgis_query` 165 层（D1）+ `local_ndjson` 12 层（D2 三州本地层）
- partial 全部是「服务本身返回的 feature 数 < 50」或「feature 有但 geometry 为 null」，
  不是我们截断：例如 `features_returned=50` 但只有 48/49 带几何；`features_returned=1` 的服务就 1 行。
  每条 partial 的精确原因写在 `layers-status.csv: reason`。
- 唯一 unavailable：`https://services1.arcgis.com/BkFxaEFNwHqX3tAw/arcgis/rest/services/FS_VCGI_OPENDATA_TABLE_E911_GEONAMES_SP_v1/FeatureServer/0`
  → HTTP 200、`features=50`、`geometryType` 缺失、所有 feature 无 `geometry` 字段（纯属性表）。标 `no_geometry_in_response`，没有补任何假坐标。

---

## 2. 采样口径（可复算）

- D1（远程，16,010 层）：
  `GET <layer>/query?where=1=1&outFields=*&returnGeometry=true&outSR=4326&resultRecordCount=50&f=json`
  （`.../query` 结尾的 url 不再重复拼 `/query`）
- D2（本地，1,158 层）：读 `dist/intake-full/layers/<layer>/addr.*.ndjson.gz` 的
  `latitude`/`longitude` 字段；`addr` 有没有坐标的层退到 `aux_addr_nohouse`（fallback 记在 `layers-status.csv: reason`/`sample_source`）
- 每层目标 50 行；取到 50 → `ok`，不足 → `partial`（写实际条数），
  拿不到任何几何 → `unavailable`（写 reason + http_code + attempts）
- 死链 / 403 / 404：单层最多 3 次，退避 2s / 5s / 10s，然后放弃（不死磕，不重试到天亮）
- 响应里的 `spatialReference.wkid`、`geometryType`、`exceededTransferLimit` 一并落盘：
  `wkid` / `geom_type` 两列在 `samples/*.csv`，`exceeded` 在 extract 原文里
- 非 4326 的换算：请求带 `outSR=4326`，实测 16,010 层响应全部回 4326；
  代码仍保留 3857 族（102100/102113/900913）反算分支，公式
  `lon = x/20037508.342789244*180`，`lat = 180/π·(2·atan(exp(y/20037508.342789244·π)) − π/2)`；
  **其它 wkid 一律 `unavailable: wkid_unconvertible:<wkid>`，不出坐标**

列名对照（`samples/<STATE>.csv`）：`addr_fields_json` 里保留服务原字段名（不做归一化重命名），
门牌类似 `HOUSE_NUM|ADDR_NUM|house_number|_house_num`，街名类似 `STREET_ADD|STREET_NAME|street_name|STREETNAME`
——字段名千差万别，这里不硬拆，原样进 JSON，杜绝"拆丢"。

---

## 3. 坐标真实性（三条硬要求）

1. **`wkid` 无空值**：三州 7,956 行 100% 有 `wkid`，取值只有两种：
   `4326`（7,356 行，远程 query）与 `4326(local field lat/lon)`（600 行，D2 本地字段）。无留空。
2. **无 `lon=0 且 lat=0` 行**：三州 0 行（`scripts/build_samples.py` 与采集端都做了 `(0,0)` 过滤，采到即丢）。
3. **无质心 / 无插值**：点要素取 `geometry.x/y`；线/面要素取 `rings[0][0]` / `paths[0][0]` 的
   **真实顶点**（不是质心、不是包络中心）。抽查证据 `spotcheck/SPOTCHECK.md`：
   **9/9 层**的 CSV 值与原始响应首顶点逐位一致（超出"抽查 3 层"要求）。

---

## 4. 断点续跑

- 落盘单元 = `extract/d1_<sha1(url)[:16]>.json`（一层一文件，原子 replace）；
  已存在即跳过，重跑请求数 → 0。
- 三州这 165 个 D1 url 重跑证据：见全量阶段的 `logs/rerun-*.log`（同一脚本第二次执行 `todo: 0`）。
- 只有「3 次尝试全挂」的网络级失败不落盘（下一轮还能重试），业务性失败（403/404/rest_error/无几何）落盘。

---

## 5. 已知偏差 / 口径说明（不吞）

1. **`layer_id` 不是主键**（第 4 步遗留）：17,168 行只有 1,523 个不同 `layer_id`，
   甚至有 `layer_id = "FeatureServer/0"` 这种残值（三州样本里可见）。**采样与对齐一律用 `url`**；
   `layer_id` 仅作展示列。
2. **`state` 列是第 4 步的 provider/服务级判定值**，个别层实际跨州（例：IA 桶里有一条 Larimer/俄亥俄坐标的图层）。
   本轮不修正、不重派州 —— 那是第 4 步口径问题，改了就违反"只采集"。
3. 面/线要素落的是首个真实顶点，对第 7 步"点在县内"判定：面要素顶点位于边界上，
   第 7 步做空间验算时应按 `geom_type` 区分（本条已写进报告，供第 7 步参考）。
4. `samples/_UNLOCATED.csv` / `_UNKNOWN.csv` 是"未定位州/空州"桶，不是真州；全量阶段生成。

---

## 6. 文件清单（本段）；全量报告见 `REPORT-ALL.md`

| 文件 | 内容 |
|---|---|
| `layers.json` | 17,168 层清单（含 `layer_dir`、provider、granularity） |
| `scripts/prep_layers.py` | 生成 `layers.json` |
| `scripts/sample_local.py` | D2 本地 ndjson 采样 |
| `scripts/sample_remote.py` | D1 ArcGIS `/query` 采样（断点续跑、退避、per-host 限流） |
| `scripts/build_samples.py` | extract → `samples/*.csv` + `layers-status.csv` + `unavailable.csv` + `summary*.json` |
| `scripts/spotcheck.py` | CSV ↔ 原始响应抽查 |
| `samples/DE.csv` `samples/NH.csv` `samples/IA.csv` | 一行一采样点，13 列 |
| `summary-3states.json` | 三州汇总（`denominator=17168`） |
| `layers-status.csv` | 逐层状态表；全量阶段收口后为 17,168 行，三州子集用 `build_samples.py --states DE,NH,IA` 复算（`summary-3states.json` 保持三州口径） |
| `unavailable.csv` | 不可用层 + 原因 + HTTP 码 + 尝试次数（三州部分：1 条） |
| `spotcheck/SPOTCHECK.md` | 三州 9 层逐位比对（全量段另有 `SPOTCHECK-ALL.md`，25 层/10 个桶，25/25 一致） |
| `logs/remote-full.log` | 全量采集日志（三州段在里面） |

## 7. 复算命令

```bash
python3 analysis/coord-samples-20261124/scripts/prep_layers.py        # → layers.json
python3 analysis/coord-samples-20261124/scripts/sample_local.py       # → extract/d2_*.json（本地，不联网）
python3 analysis/coord-samples-20261124/scripts/sample_remote.py --workers 12            # → extract/d1_*.json
python3 analysis/coord-samples-20261124/scripts/build_samples.py      # → samples/*.csv + summary.json
python3 analysis/coord-samples-20261124/scripts/build_samples.py --states DE,NH,IA        # → summary-3states.json
python3 analysis/coord-samples-20261124/scripts/spotcheck.py --states DE,NH,IA --n 3
```
