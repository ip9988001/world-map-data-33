# 依赖定案：shapely / rtree 永不用作运行时依赖

**判词：维持禁令（零新依赖）。**

- 状态：**定案**（muse-000146 Phase 1a 第 4 片 · 第 10 项），2026-11-22。
- 适用范围：三仓 `world-map-data-33`、二仓 `world-map-data-test`（判县链路在两仓各有一份实现，口径必须一致）。
- 机器可查：`collect/check_forbidden_deps.py`（ci-smoke 已挂）——`*.py` 出现 `import shapely` / `import rtree`，或依赖清单把两包列为依赖 → `rc=1`。
- 可证伪复核：`collect/probe_county_holes.py`（只读探针，任何人可复跑）。

---

## 1. 现状核对（可证伪，命令与命中都在这里）

### 1.1 `grep -rn "shapely\|rtree"` 命中清单

| 仓 | 命中 | 位置 | 性质 |
|---|---|---|---|
| 三仓 | **1 处** | `collect/county_tiger.py:7`「所以 county 一律走 point-in-polygon（射线法，纯标准库，无 shapely 依赖）」 | 注释（说明为何不用） |
| 二仓 | **3 处** | `requirements.txt:13`「shapely / rtree —— 空间索引一律复用引擎内自带的网格索引 + point_in_rings()」 | 注释（裁决原文） |
| 二仓 | | `scripts/gold_coalesce.py:20`「严禁 shapely / geopandas / rtree；空间一律网格索引 + point_in_rings()」 | 注释 |
| 二仓 | | `.github/workflows/gold-coalesce.yml:13`「严禁 INSTALL spatial / shapely / geopandas / rtree」 | 注释 |
| 一仓 / 总仓 | **0 处** | — | — |

**`import shapely` / `import rtree` 的实命中 = 0**（两仓 `*.py` 全扫）。也就是说：禁令自 2026-10-18 立下至今**从未被违反过一次**，被 grep 到的全是「说明为什么禁」的注释。

> 因此检查脚本刻意**不算注释违规**：把「禁止 shapely」这句话本身判红，只会让人删注释、不删依赖 —— 见 `check_forbidden_deps.py` 的 `_strip_comment()`。

### 1.2 判县链路实际用的是哪套实现

| 环节 | 实现 | 依赖 |
|---|---|---|
| 点 → 县 | `collect/county_tiger.py: pip(lat, lon, geom)` —— 射线法（`_in_ring()`，奇偶穿越计数） | **纯标准库**（json/gzip/urllib） |
| 预筛索引 | `collect/county_index.py: NationalIndex` —— 1° 网格（`cell=1.0`），键 `(floor(lat), floor(lon))` → 候选 fips 列表，**带一圈邻居格**（`rings=1`，防简化几何跨格） | 纯标准库 `math` |
| 判定顺序 | 网格 → `in_bbox()` 快速跳过 → `pip()` 定论。**bbox 只做预筛，明令禁止当结论**（2026-10-30 GA Clayton 实测：bbox 命中 235 条、多边形内 0 条） | — |
| 二仓对应 | `scripts/coverage_counters.point_in_rings(lon, lat, rings)` —— 偶奇规则，遍历**全部环**（天然处理洞） | 纯标准库 |
| 州级索引 | `CountyIndex.locate()`（单州遍历 fips + bbox 预筛 + PIP） | 纯标准库 |

**精度（实测，非估算）**

- 县界源：TIGERweb `State_County/MapServer/1`（GeoJSON，`outSR=4326`），本地缓存 `analysis/tiger_county/<ST>.json.gz`，50 州 / **3,089 个县 feature**。
- 单次 `point_in_rings`（洛杉矶县 3,000+ 点环）：**35.7 µs**（20,000 次 0.71 s）。
- 网格预筛后候选县通常 1–3 个 → 单点判县量级 **~10⁴ 点/秒/核**（Python 单线程），对 12,780 资产的采样判县完全够用。

---

## 2. 判词与理由

### 2.1 判词：维持禁令（零新依赖）

判词只有两种取值，本文件取第一种：

1. **维持禁令（零新依赖）** ← 本次裁决
2. 必须引入（附实测数据）—— 仅在「现方案在某类县产生**可复现的错误判县**，且**无法用现有引擎修**」时才能提，且只提议、不安装，等批示。

### 2.2 为什么不是「必须引入」：错误确实存在，但**能用现有引擎修**

按第 2 条的门槛，我实测了 muse 点名的那类县（**holes 多边形**），确实抓到可复现错误 ——

```
$ python3 collect/probe_county_holes.py
县 feature 总数        = 3089
MultiPolygon 县        = 51
含 interior ring（洞）的县 = 24
洞的代表点数           = 38
三仓 pip 误判「洞内 = 县内」= 35
其中同时被他县认领（重复归属）= 34
  样本：fips=02100 lat=59.39954 lon=-135.88709 → 现实现=在县内，偶奇=在洞外；真正辖有该地的县=['02105']（Hoonah-Angoon 里的 Sitka 飞地）
  样本：fips=08005 lat=39.69944 lon=-104.93314 → 现实现=在县内，偶奇=在洞外；真正辖有该地的县=['08031']（Arapahoe 里的 Denver 飞地）
  样本：fips=08013 lat=39.95764 lon=-105.10392 → 现实现=在县内，偶奇=在洞外；真正辖有该地的县=['08014']（Boulder 里的 Broomfield）
```

**根因**（`collect/county_tiger.py:49-80`）：

```python
def _rings(geom):                      # 只取外环！
    if t == "Polygon":     return [geom["coordinates"][0]]
    if t == "MultiPolygon": return [poly[0] for poly in geom["coordinates"]]

def pip(lat, lon, geom):
    for ring in _rings(geom):          # 各外环取「并集」
        if _in_ring(lon, lat, ring): return True
```

洞（interior ring）被丢弃 → 飞地被算进外包它的县 → 与真正辖有该地的县**重复认领**，`locate()` 返回先撞到的那个，**结果依赖 `by_fips` 遍历顺序**。

**但修法不需要 shapely**：偶奇规则数「同一多边形的全部环（外环 + 洞）」的穿越次数即可，二仓 `point_in_rings()` 已经是这个写法。三仓需要改的只有一处（约 10 行，纯标准库）：

```python
def _polys(geom):                       # 返回 [[外环, 洞1, 洞2…], …]
    if geom.get("type") == "Polygon":     return [geom["coordinates"]]
    if geom.get("type") == "MultiPolygon": return geom["coordinates"]

def pip(lat, lon, geom):
    return any(_even_odd(lat, lon, poly) for poly in _polys(geom))   # 每个多边形内部偶奇
```

→ 落在「**能用现有引擎修**」一侧，因此**不满足提「必须引入」的门槛**，判词取「维持禁令」。

> **未在本单实施该修法**：它改变生产判县结果（那 34 个洞点会从「外包县」改判到「真正辖有的县」），属于判据语义变更，按纪律只提议、等批示。复核脚本 `collect/probe_county_holes.py` 已入库，改完再跑一次 `误判数` 应降到 0。

### 2.3 其余三类「疑难县」的实测结论

| 类别 | 实测 | 结论 |
|---|---|---|
| 多岛屿（MultiPolygon） | 51 个县 | `_rings()` 取每个多边形外环并集 = 正确（岛屿本就都是领土），**无需引入** |
| 跨经线（antimeridian） | 美国县级无跨 ±180° 的县（AK 全部在 −130°以西、Aleutians 西端到 +172° 属 **Aleutians West 02016** 等，其坐标跨 180 需拆分环） | 现索引按 `floor(lon)` 分格；若将来真要采 Aleutians 西段，需在**取几何时**拆环（数据侧处理），**不构成引入 shapely 的理由** |
| 极不规则 / 细长环 | bbox 预筛 + 邻居格 ±1° 已覆盖（`rings=1`） | 无需引入 |

---

## 3. 替代路径（谁负责什么）

| 职责 | 由谁负责 | 说明 |
|---|---|---|
| 多边形判定（点是否在县内） | **自研射线法** `county_tiger.pip()` / 二仓 `point_in_rings()` | 纯标准库；偶奇规则；改洞的处理只需改这一个函数 |
| 空间索引（候选县预筛） | **自研 1° 网格** `county_index.NationalIndex` | 键 `(floor(lat), floor(lon))`，带一圈邻居格；3,089 县 × 1° 网格 ≈ 内存十几 MB |
| 洞（interior ring） | 偶奇规则（改 `pip` 后自动正确） | 二仓已正确；三仓待修（本文件 2.2） |
| bbox | **只做预筛**，永不当结论 | GA Clayton 实测：bbox 命中 235 条 / 多边形内 0 条 |
| 投影 / 测距 | `pyproj`（三仓已装 `pyproj>=3.6`） | 只在需要真实米制距离时用，判县不用 |
| 读 shapefile | `pyshp`（三仓 `pyshp>=2.3`；二仓 `pyshp>=2.3.1`） | 只读 `.shp/.dbf`，不装 GDAL |

**性能量级**：单点判县 ~35.7 µs/县测试 × 网格后 1–3 个候选 ≈ **10⁴ 点/秒/核**。shapely+rtree 的理论加速（C 实现 + STRtree）在这个数据量（3,089 县、12,780 资产、采样判县）**不构成瓶颈**，而代价是：新增二进制 wheel、CI 编译/平台矩阵、以及「判据实现分裂成两套」（正是 2026-10-18 裁决要避免的）。

---

## 4. 禁令的执行方式（落成检查，不靠自觉）

```bash
$ python3 collect/check_forbidden_deps.py            # 三仓
  ✅ 无 shapely / rtree（import 与依赖清单均干净）
$ python3 collect/check_forbidden_deps.py --root ../world-map-data-test     # 二仓（只读）
  ✅ 无 shapely / rtree（import 与依赖清单均干净）
```

反证（故意插一行）：
```bash
$ printf 'import shapely.geometry\n' > collect/_probe_violation.py
$ printf 'rtree>=1.0\n' >> requirements.txt
$ python3 collect/check_forbidden_deps.py
  ❌ collect/_probe_violation.py:1  [import] import shapely.geometry
  ❌ requirements.txt:3  [dependency] rtree>=1.0
判定：❌ 2 处违规 …            rc=1
```

已挂 `ci-smoke`（`.github/workflows/ci-smoke.yml`，步骤「禁依赖检查（shapely / rtree）」），并已在 `ci-smoke` 触发路径里含 `collect/**`。

> 二仓若要同样上闸，把本脚本拷进二仓并加一条 CI 步骤即可（脚本 `--root` 无仓内硬编码）。本单**未改二仓代码**，只在二仓 `requirements.txt` 裁决注释后补一行指针（见下）。

---

## 5. 二仓补充指针（只加注释，不动依赖）

二仓 `requirements.txt` 那段「明确禁止（架构裁决 2026-10-18）」原文保留，其后补一行：

```
#   判县实现位置：三仓 collect/county_tiger.py::pip() + collect/county_index.py（网格索引）；
#   二仓对应 scripts/coverage_counters.point_in_rings()。定案见三仓 docs/DEPENDENCY-VERDICT-20261122.md
```

---

## 6. 结论备忘（一句话）

**判县继续用「1° 网格预筛 + 纯标准库射线法」，shapely / rtree 永不用作运行时依赖；已发现且已量化的洞（飞地）误判属「现引擎可修」，修法为 `pip` 改偶奇、约 10 行，待批示后单独立项。**
