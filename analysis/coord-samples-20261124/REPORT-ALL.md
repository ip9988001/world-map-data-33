# 第 6 步前置 · 坐标样本采集 —— 全量报告（17,168 层）

- 任务：muse-000217 / `task_id=w2-20261124-coord-samples`；分支 `feat/coord-samples-20261124`；基线 `e391d2d`；PR #46（只开不合）
- 本报告所有数字由 `scripts/report_all.py` 从 `summary.json` / `layers-status.csv` / `unavailable.csv` / `samples/*.csv` 现算，可复算命令见 §10
- 本轮只采集：不融合、不分级、不改引擎、不动空间验算模块、`registry/` 零改动


## 0. 对账表

| 项 | 值 | 说明 |
|---|---|---|
| 分母 | **17168** | D1 16,010 远程 + D2 1,158 本地 |
| 逐层清单行数 | **17168** | 差额 **0** |
| 唯一 url | **16752** | 采样主键；D2 多行共享 service url |
| 无 url 行 | 417 | 全 `universe=d2`、`provider_kind=none`；用本地 `layer_dir` 采样，命中 1,158/1,158 |
| 失配 / 落单 | **0** | 未触发 url 交集补齐 |
| 闭合校验 | `13532 + 3210 + 426 = 17168` | 等于分母 17168 → **闭合** |


## 1. 全量结果

| 指标 | 值 | 占 17,168 |
|---|---:|---:|
| ≥50 行（`ok`） | **13532** | 78.8% |
| partial（有坐标但 <50 行） | **3210** | 18.7% |
| unavailable（无几何/死链/拒答） | **426** | 2.5% |
| 有任何坐标的层 | **16742** | 97.5% |
| 采样行数合计 | **738174** | — |
| 采样来源 | arcgis_query 16010, local_ndjson 1158 | — |


## 2. 每州覆盖表

`state` 列取第 4 步的逐层州判定；`未定位` / 空州落 `_UNLOCATED` / `_UNKNOWN` 桶（不是真州）。大桶按层序号切片成 `-partN.csv`，不丢行。

| 桶（州） | 层数 | ≥50 行 | partial | unavailable | 采样行数 | 文件 |
|---|---:|---:|---:|---:|---:|---|
| _UNLOCATED | 7802 | 6123 | 1573 | 106 | 336853 | `_UNLOCATED-part1.csv`, `_UNLOCATED-part2.csv`, `_UNLOCATED-part3.csv`, `_UNLOCATED-part4.csv`, `_UNLOCATED-part5.csv`, `_UNLOCATED-part6.csv` |
| CA | 1072 | 848 | 223 | 1 | 46325 | `CA.csv` |
| DC | 664 | 653 | 11 | 0 | 32924 | `DC.csv` |
| NY | 632 | 533 | 98 | 1 | 28364 | `NY.csv` |
| FL | 534 | 429 | 105 | 0 | 23488 | `FL.csv` |
| TX | 445 | 381 | 64 | 0 | 20332 | `TX.csv` |
| NC | 416 | 349 | 67 | 0 | 18718 | `NC.csv` |
| _UNKNOWN | 410 | 88 | 14 | 308 | 4640 | `_UNKNOWN.csv` |
| GA | 324 | 271 | 53 | 0 | 14526 | `GA.csv` |
| MA | 303 | 212 | 90 | 1 | 12096 | `MA.csv` |
| MI | 262 | 193 | 64 | 5 | 11034 | `MI.csv` |
| IL | 260 | 203 | 56 | 1 | 11019 | `IL.csv` |
| AZ | 257 | 225 | 32 | 0 | 11726 | `AZ.csv` |
| MD | 253 | 213 | 40 | 0 | 11415 | `MD.csv` |
| NJ | 235 | 179 | 56 | 0 | 10351 | `NJ.csv` |
| VA | 231 | 189 | 42 | 0 | 10165 | `VA.csv` |
| MN | 230 | 188 | 41 | 1 | 10307 | `MN.csv` |
| CO | 222 | 158 | 64 | 0 | 9388 | `CO.csv` |
| OR | 212 | 151 | 61 | 0 | 9139 | `OR.csv` |
| WA | 212 | 171 | 41 | 0 | 9454 | `WA.csv` |
| MO | 189 | 114 | 75 | 0 | 6415 | `MO.csv` |
| UT | 173 | 135 | 37 | 1 | 7370 | `UT.csv` |
| OH | 167 | 139 | 28 | 0 | 7666 | `OH.csv` |
| NM | 150 | 130 | 20 | 0 | 6982 | `NM.csv` |
| OK | 110 | 91 | 19 | 0 | 4902 | `OK.csv` |
| AL | 105 | 86 | 19 | 0 | 4606 | `AL.csv` |
| ID | 105 | 98 | 7 | 0 | 5066 | `ID.csv` |
| LA | 102 | 82 | 20 | 0 | 4614 | `LA.csv` |
| PA | 98 | 85 | 13 | 0 | 4583 | `PA.csv` |
| IN | 86 | 75 | 11 | 0 | 3909 | `IN.csv` |
| ME | 86 | 80 | 6 | 0 | 4105 | `ME.csv` |
| IA | 83 | 69 | 14 | 0 | 3751 | `IA.csv` |
| HI | 78 | 53 | 25 | 0 | 2898 | `HI.csv` |
| AR | 77 | 70 | 7 | 0 | 3644 | `AR.csv` |
| KS | 76 | 54 | 22 | 0 | 3127 | `KS.csv` |
| TN | 65 | 51 | 14 | 0 | 2793 | `TN.csv` |
| CT | 54 | 41 | 13 | 0 | 2246 | `CT.csv` |
| NH | 53 | 41 | 11 | 1 | 2329 | `NH.csv` |
| KY | 46 | 37 | 9 | 0 | 1936 | `KY.csv` |
| DE | 41 | 33 | 8 | 0 | 1876 | `DE.csv` |
| NE | 39 | 31 | 8 | 0 | 1685 | `NE.csv` |
| AK | 33 | 31 | 2 | 0 | 1622 | `AK.csv` |
| MT | 33 | 27 | 6 | 0 | 1371 | `MT.csv` |
| SC | 31 | 26 | 5 | 0 | 1353 | `SC.csv` |
| ND | 29 | 26 | 3 | 0 | 1391 | `ND.csv` |
| WY | 29 | 23 | 6 | 0 | 1199 | `WY.csv` |
| MS | 20 | 19 | 1 | 0 | 966 | `MS.csv` |
| RI | 13 | 12 | 1 | 0 | 609 | `RI.csv` |
| WV | 6 | 6 | 0 | 0 | 300 | `WV.csv` |
| PR | 5 | 1 | 4 | 0 | 97 | `PR.csv` |
| NV | 4 | 3 | 1 | 0 | 199 | `NV.csv` |
| WI | 4 | 4 | 0 | 0 | 200 | `WI.csv` |
| SD | 1 | 1 | 0 | 0 | 50 | `SD.csv` |
| VT | 1 | 1 | 0 | 0 | 50 | `VT.csv` |
| **合计** | **17168** | **13532** | **3210** | **426** | **738174** | 59 个文件 |


## 3. 不可用原因分布（`unavailable.csv`，426 条）

| 原因 | 层数 |
|---|---:|
| `no_coords_in_local_tables` | 308 |
| `no_geometry_in_response` | 112 |
| `rest_error_500` | 2 |
| `exhausted` | 2 |
| `rest_error_400` | 1 |
| `rest_error_499` | 1 |

HTTP 码分布：`—` 310, `200` 116


## 4. 坐标真实性三条（逐行扫 `samples/*.csv`）

| 检查 | 结果 |
|---|---|
| 总行数 | 738174 |
| `wkid` 空值行 | **0**（无留空） |
| `lon=0 且 lat=0` 行 | **0** |
| 越界坐标（\|lon\|>180 或 \|lat\|>90） | **0** |
| 质心替代 / 插值 | **0**（点取 `geometry.x/y`；线/面取 `rings[0][0]`/`paths[0][0]` 真实顶点） |

`wkid` 取值分布（按行）：`4326` 697553, `4326(local field lat/lon)` 40621

`wkid` 取值分布（按层，排除 unavailable）：`4326` 15892, `4326(local field lat/lon)` 850


`geom_type` 分布（按行）：`esriGeometryPoint` 351649, `esriGeometryPolyline` 197332, `esriGeometryPolygon` 146707, `point(lat/lon fields)` 40621, `esriGeometryMultipoint` 1865

> `geom_type` 是响应里的 `geometryType` 原样值 —— 第 4 步 `granularity=unknown` 的 12,218 层，几何语义在这一列落地，第 7 步可直接用。


## 5. 未覆盖层清单

- 未达 50 行的层 = 3636 层，逐层在 `layers-status.csv`（列 `status` / `rows` / `reason`），其中 426 层完全无坐标单列在 `unavailable.csv`。

- partial 的共同原因：服务 `resultRecordCount` 之外的总量本来就 <50，或返回的 feature 里部分 `geometry` 为 null。没有人为截断，也没有为凑数重复取同一要素。

- 完全无坐标的三种典型：① 纯属性表（`geometryType` 缺失）② `/query` 未开且返回 JSON 错误 ③ 域名死链/403。三种都如实标 unavailable，**没填 0,0、没用质心、没插值**。


## 6. 断点续跑

落盘单元 `extract/d1_<sha1(url)[:16]>.json`，原子 replace；已存在即跳过。全量收口后连跑 3 次 `sample_remote.py` 验证：第 1/2 次只剩 2 层网络级超时，第 3 次 `todo=0`、0 秒、0 请求。

`logs/rerun-1.log`：
```
{"d1_layers": 16010, "todo": 2, "skipped_cached": 16008}
{"finished": 2, "tally": {"unavailable": 2}, "elapsed_s": 120}
```

`logs/rerun-4.log`：
```
{"d1_layers": 16010, "todo": 0, "skipped_cached": 16010}
{"finished": 0, "tally": {}, "elapsed_s": 0}
```


## 7. 已知偏差（不吞）

1. `layer_id` 不是主键（第 4 步遗留）：17,168 行只有 1,523 个不同 `layer_id`，存在 `FeatureServer/0` 这类残值 → 采样/对齐一律用 `url`。

2. `state` 是第 4 步 provider/服务级判定，个别层实际跨州；本轮不修正（改了就超出"只采集"）。

3. 面/线要素落首个真实顶点：面要素顶点在边界上，第 7 步做空间验算时按 `geom_type` 区分处理。

4. D2 本地层的坐标来自 `dist/intake-full` 落盘的 `latitude/longitude` 字段（真实字段值），不是重新联网取 —— 这类层 417 行甚至没有 url。


## 8. 三州先行报告的对应关系

`REPORT-3STATES.md` 是本轮第①段的报告（DE/NH/IA 177 层），其数字与这里 §2 表中三行完全一致：DE 41 层 / 33+8+0、NH 53 层 / 41+11+1、IA 83 层 / 69+14+0，合计 177 层 / 7,956 行（`summary-3states.json` 为三州口径的同一份汇总，`denominator` 恒为 17,168）。

坐标抽查两份：`spotcheck/SPOTCHECK.md`（三州 9 层，第①段）与 `spotcheck/SPOTCHECK-ALL.md`（DE/NH/IA/CA/NY/TX/DC/WI/NV/PR 共 25 层，全量段），两份都是 CSV ↔ 原始响应首顶点逐位比对，结果 100% 一致。


## 9. 交付物清单

| 文件 | 内容 |
|---|---|
| `layers.json` | 17,168 层清单（`layer_id/url/state/universe/provider/granularity/layer_dir`） |
| `samples/*.csv` | 59 个文件 / 738174 行，每行一采样点，13 列 |
| `layers-status.csv` | 17,168 行逐层状态（`status`/`rows`/`wkid`/`geom_type`/`reason`）|
| `unavailable.csv` | 426 层不可用 + reason + http_code + attempts |
| `summary.json` | `denominator=17168` + 三列闭合 + `by_state` |
| `summary-3states.json` | 三州子集（177 层 / 7,956 行） |
| `REPORT-3STATES.md` / `REPORT-ALL.md` | 两份报告 |
| `scripts/` | `prep_layers` / `sample_local` / `sample_remote` / `build_samples` / `spotcheck` / `report_all` |
| `logs/` | 全量采集日志 + 3 次续跑日志 |
| `spotcheck/` | 两份逐位比对表 |

原始响应缓存（约 729MB）在采集机 `/data/coord-work-20261124/cache/`，按 `sha1(url)[:16].json.gz` 命名，**未提交进仓库**；抽查脚本可随时复算。


## 10. 复算命令

```bash
python3 analysis/coord-samples-20261124/scripts/prep_layers.py     # → layers.json
python3 analysis/coord-samples-20261124/scripts/sample_local.py    # → extract/d2_*.json
python3 analysis/coord-samples-20261124/scripts/sample_remote.py --workers 12  # → extract/d1_*.json
python3 analysis/coord-samples-20261124/scripts/build_samples.py   # → samples/*.csv + summary.json
python3 analysis/coord-samples-20261124/scripts/spotcheck.py --states DE,NH,IA --n 3
python3 analysis/coord-samples-20261124/scripts/report_all.py      # → REPORT-ALL.md
```
