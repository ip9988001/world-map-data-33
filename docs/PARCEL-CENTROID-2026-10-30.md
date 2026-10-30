# 宗地质心补齐 · 实测结论（2026-10-30）

> 结论先写：**「用宗地几何算质心」在当前已采资产上不可行** —— 三仓采集器只落点几何，
> Polygon 的 `rings` 从未写盘。本轮把能离线救的坐标全救了（5 层 / 479,123 行），
> 并已把采集侧改成**默认带质心**（`PILOT_POLY_CENTROID` 默认开）：面层每行落 `_lat`/`_lon`，
> 新采层不会再出现「有行无坐标」。几何是否落盘的成本另见
> `docs/PARCEL-GEOMETRY-OPTIONS-2026-10-30.md`（三档实测 + 推荐）。

## 一、为什么几何路径走不通（两条硬证据）

1. **代码层**：`collect/pilot.py` 三处取几何都只读 `geometry.y/.x` ——
   ```python
   g = ft.get("geometry") or {}
   rec = normalize(at, g.get("y"), g.get("x"))     # rings 在此被丢弃
   ```
   全仓 `grep -n "rings" collect/*.py` = 0 命中；`normalize()` 签名只有 `(attrs, lat, lon)`。
2. **资产层**：抽 `collect-step10-7ABWQBGTG_…_Hutto_Parcels_…_0` 的 `u00000.tar.gz`
   （23,591 行）逐记录看键名：
   ```
   add_num, pre_dir, st_name, st_suf, post_dir, unit, city, zip, esn,
   lat, lon, addr_key, src_layer, src_title, raw
   ```
   `lat/lon` 全 null，`raw` 里只有 `Shape__Area=35876.58` / `Shape__Length=838.67`，
   **没有 rings、没有 X/Y 属性列**。

⇒ 无坐标的 1,060 个宗地层里，**几何类救回为 0**；卡点是「采集时没落几何」，不是「质心算法不对」。

## 二、能救的两类（离线、不访问上游）

| 类型 | 判据 | 结果 |
|---|---|---|
| 属性本就是经纬度（被范围校验误杀） | 列名 LAT/LON 族 + 样例值落在 US 范围 | 1 层（CA，非空率仅 0.5%） |
| 属性是**投影坐标** | X/Y、EASTING/NORTHING… 量级 >5,000 → pyproj 反推 EPSG | **4 层** |

投影反推的判据是硬的（不猜）：
- 候选集 = pyproj 库里 `area_of_use` 含本州名的全部 EPSG 投影 CRS；
- 候选必须把**全部样例点**转进 WGS84 US 范围、且**落进同一个县**（TIGER 多边形，禁用 bbox）；
- 多个候选都合格时，只有它们给出的**县完全一致**才接受（NAD83/NAD27/ftUS/m 变体属同类），
  否则记 `proj_ambiguous`；
- 一个候选都不行 → `proj_failed`。

实测救回：`MD EPSG:2248`（GDX buildings 347,176 行 + Gaithersburg 35,112 行）、
`NC EPSG:2264`（Parcels 7,973 行）、`DE EPSG:2260`（Parcels 83,148 行）。

## 三、坐标覆盖率

| 口径 | 层数 | 说明 |
|---|---|---|
| field-map 里 latitude 为空的层 | 1,074 | 其中宗地 1,060 / 点层几何异常 14 |
| **本轮救回** | **5** | proj_ok 4 + attr_latlon 1；合计 479,123 行 |
| `geom_missing`（几何从未落盘） | 1,038 | 全是宗地层，只能重采 |
| `no_source`（既无坐标列也无几何） | 14 | 缓冲区/演示层 |
| `proj_ambiguous` | 9 | 候选坐标系落进不同县 → 不猜 |
| `proj_failed` | 8 | 无候选能转进本州县界 |

**992 层（跨县无坐标）口径：坐标覆盖 3/992**（另 2 层救回的不在跨县集里）。

## 四、usable / 县可判 前后对比

| 口径 | 前 | 后 | 变化 |
|---|---|---|---|
| usable v1（只认 state 列） | 587（24.83%） | 587（24.83%） | 0 |
| usable v2（+state 回填） | 1,820（76.99%） | 1,820（76.99%） | 0 |
| **usable v3（+县可判）** | **984（41.62%）** | **986（41.71%）** | **+2** |
| `county_multi_no_geo`（跨县且无坐标） | 992 | 989 | −3 |
| latitude 层覆盖 | 1,290 / 54.6% | 1,294 / 54.7% | +4 |

（usable v3 只 +2 而 county_multi_no_geo −3，差别在 1 层是宗地但缺地址字段，本来就不算 usable。）

## 五、解卡路径（**已启用**）

1. **采集侧（已默认开）**：`collect/pilot.py` 的 `PILOT_POLY_CENTROID` **默认 = 1** —— 面层查询自动加
   `returnCentroid=true`（ArcGIS 原生服务端质心，`outSR=4326` 即 WGS84），并**优先**用返回的 `rings`
   在本地算 `representative_point`（凹多边形/带洞才用扫描线中点），算不出来才退回服务端质心；
   每行落 `_lat`/`_lon`（与 NAD 口径同名）。rings 本身仍不落盘（成本见
   `docs/PARCEL-GEOMETRY-OPTIONS-2026-10-30.md`）。
   效果：**下次采宗地时直接带坐标**，无需二次计算、无需下几何。
   回归保护：`collect/tests/test_pilot_centroid_contract.py`（11 条）+ `--entry-check` 第 29 条
   （面层步骤必须在 steps.json 里声明 `poly_centroid=true`，且 pilot 默认值必须是开）。
2. **计算侧**：`collect/parcel_centroid.py` 的几何库已就绪并单测（10 条）：
   - `polygon_centroid`（环有符号面积，洞自动相减）
   - `representative_point`（**质心落在凹多边形外**时用扫描线最宽内区间中点 —— L 形自测通过）
   - `pip` / `inside_geom`（奇偶规则，洞判在内）
   - 退化（环 <3 点、面积 0、空几何）→ 返回 None，调用方记 `geom_invalid`
3. 两者接上后，这批层自动进入「行级多边形判县」，不需要再开新路径。

## 六、复现

```bash
python3 collect/parcel_centroid.py --selftest        # 几何库 10 条自测
python3 collect/parcel_centroid.py --audit --backfill  # 逐层分类 + 写 schema/coord-salvage-v1.json
python3 analysis/field_map_v2.py                     # 读 coord-salvage 覆盖 lat/lon
```

证据文件：`schema/coord-salvage-v1.json`（逐层 status + EPSG + 落县 + 证据列）。
