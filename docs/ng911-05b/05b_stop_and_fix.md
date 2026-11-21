# 05b 停片收尾账 + 全筛 + 138c05 逐子层 + 四条修法（2026-11-21）

> 口径声明：本文数字全部来自 **run 44865991911（commit 857e08c，计划提交 10e87f5）** 的
> job 日志、artifact、以及各片推到 main 的账本，没有一个数字靠读码推断。
> 本轮**未重跑 05b、未派任何采集 run**。

---

## A · 停片收尾账

### A1 三片各自

| 片 | job id | 起 | 止（cancelled） | 跑时 | 完成层 / 计划层 | ok/empty/partial/failed | 本片 rows | 本片 declared | partial_run |
|---|---|---|---|---|---|---|---|---|---|
| shard 0 | 136730181985 | 04:27:03Z | 04:52:20Z | 25m17s | **134 / 200** | 108 / 3 / 20 / 3 | **1,344,000** | 1,148,613 | true |
| shard 1 | 136730181955 | 04:27:03Z | 04:52:25Z | 25m22s | **77 / 200** | 58 / 2 / 15 / 2 | **2,132,882** | 1,760,643 | true |
| shard 2 | 136730182009 | 04:27:03Z | 04:52:34Z | 25m31s | **14 / 185** | 8 / 0 / 3 / 3 | **742,323** | 737,773 | true |
| **合计** | — | — | — | — | **225 / 585** | 174 / 5 / 38 / 8 | **4,219,205** | 3,647,029 | — |

- 计划口径：**585 层 / 3 片 / size=200 / 声明 32,337,294 行**（`collect/ledger/05b_plan.json` @ `10e87f5`）。
  本 run 只走完 225 层 = 计划的 **38.5%**，rows 4.22M = 声明 32.34M 的 **13.0%**。
- 三片最后一条账本时间（04:42:26 / 04:36:16 / 04:29:50）都早于 cancel 10~23 分钟：
  说明最后那段是**卡在某个单元里被 kill**，不是空转 —— 该单元没写成 record，下次会重采。

### A2 merge 与 run 级账本落点（git sha）

| 对象 | 落点 | 说明 |
|---|---|---|
| shard 0 账本 | commit `36db704` → `collect/ledger/05b_shard00.json` | 片自己 `git push`（cancel 触发 trap 提交，04:52:16Z） |
| shard 1 账本 | commit `6d00fb0` → `collect/ledger/05b_shard01.json` | 04:52:21Z |
| shard 2 账本 | commit `12a6aa3` → `collect/ledger/05b_shard02.json` | 04:52:30Z |
| **run 级合并账本** | **commit `b1582f5` → `collect/ledger/05b_run44865991911.json`** | 04:52:47Z，`schema=collect-ledger-agg/v1`，15,388 行 |
| 计划 | commit `10e87f5` → `collect/ledger/05b_plan.json` | 585 层，权威分母 |

run 级账本摘要（文件内字段原值）：

```
layers_n=1100  ok=1016  partial=39  failed=29  empty=16
declared=42,729,632  rows=42,258,098  gap=471,534
shards_expected=3  shards_reported=21  complete=false  scope=single_run  run_id=44865991911
```

（`shards_reported=21` 是 05b 全阶段 21 片都报过账，不是本次 3 片；`scope=single_run` 只统计本 run 触达的层。）

### A3 merge 闸门结论（原文行）

```
failed=0 partial=8 layers=2770 ok=2722 empty=16 skipped=0 incomplete_shards=0(-)
##[error]05b 账本 complete=false（片齐、failed=0，但仍有 partial/未完成标记）→ 禁止接续 07b
[chain] stage=05b next=07b child_chain=0 decide=stop     reason=chain_off
```

merge job 136736522892：04:52:37Z 起 / **04:52:54Z success**，只做判定**没有产生新 commit**（只上传 `final-05b` artifact）。
→ 当前仓库无 in_progress / queued 的 run。

> 注意两个口径同时存在且都对：
> ① **阶段账本** `collect/05b_ledger.json` 2770 层 / ok 2722 / partial 8（闸门用的就是它）；
> ② **run 级账本** 1100 层 / ok 1016 / partial 39 / failed 29（本 run 触达面）。
> 引用数字必须带口径，不可互串。

### A4 半截态清单：**0 层**

判定方式（一次脚本跑完，不抽查）：

1. 取本 run 三片账本的 225 条 record；
2. 拉全量 Releases（**4,910 个**，`collect-step05-*` 3,290 个，2026-11-21 拉取）；
3. 对每条 record 算应有 part 数 `ceil(rows / unit_rows=100000)`，与 tag `collect-step05-<layer>` 下
   `-uNNNNN.tar.gz` 资产数比对。

结果：

| 类别 | 层数 | 说明 |
|---|---|---|
| 资产齐全 | **218** | parts == 期望，无一缺失 |
| 无 Release | 7 | **全部是 `empty`/`failed`（rows=0）**，本就不该有产物 |
| 有 Release 但 part 不足 | **0** | — |
| **半截态（标完成但产物没上传）** | **0** | cancelled 片的典型症状**本次没有发生** |

原因：上传是「单元算完成 → 上传 → 记账」的顺序，被 kill 的单元**根本没进 record**，
所以不会出现「账本说好了、产物没到」；代价是该单元下次重采（数据不脏，只是重复下载）。

---

## B · 停片后全筛（rows vs declared，容差 ±0.5%）

全量逐层表（2,719 行）在 **`docs/ng911-05b/05b-done-layers.md`**，此处只给结论与异常层点名。

| 项 | 数 |
|---|---|
| 账本总层数（阶段账本 `collect/05b_ledger.json`） | 2,770 |
| 已完成层（status=ok / skipped_done） | **2,722** |
| ├ 双向 ±0.5% 内（pass） | **2,719** |
| └ 超容差（partial） | **3** |
| 非完成态 | 48（partial 8 / upstream_unstable 19 / empty 16 / unverified 4 / missing 1） |

**结论行：完成层 N=2,722，pass=2,719，partial=3（超容差）。**

### B1 标 ok 但超容差（3 层，全列）

| 层 | declared | rows | 偏差 | 方向 |
|---|---|---|---|---|
| `MiYcWqQVP5NZq_arcgis_rest_services_Addresses_FeatureServer_1` | 13,671 | 13,949 | **+2.034%** | 多采 |
| `g_server_rest_services_vector_Address_Points_FeatureServer_0` | 225,673 | 226,891 | **+0.540%** | 多采 |
| `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | 39,751 | 39,504 | **−0.621%** | **少采（真缺口）** |

### B2 账本 status=partial 的 8 层（全列）

| 层 | declared | rows | 偏差 |
|---|---|---|---|
| `84Po4FBDs_arcgis_rest_services_Address_Point_FeatureServer_0` | 14,616 | 26,616 | +82.10% |
| `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 251,639 | 118,916 | −52.74% |
| `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | −54.28% |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | −11.51% |
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | −11.51% |
| `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 9,861 | 9,602 | −2.63% |
| `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 9,624 | 9,101 | −5.43% |
| `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 17,295 | 17,270 | **−0.14%（在 0.5% 容差内）** |

> 真缺口层 = 7（ellington 那层 0.14% 属上游漂移，可放行）；
> 前 6 层正是 585 计划比 579 快照多出来的 6 层 —— 两条独立证据互相印证。

### B3 138c05 不在 05b 账本里（必须点明）

`collect/05b_ledger.json` 中 `138c05` 命中 **0 次**：它的 2,131 行来自 **07b run 41184978867（2026-10-31）**。
05b 这一轮它被排在 **shard 17**，而 shard 17 属于未执行部分 → 本次对它**没有任何新采集**，
账本里它的状态仍是上一次的 `partial`（2,131 / 2,298）。这也是「585 层计划、05b 阶段账本仍是 2770 层」的原因之一。

---

## C · 138c05 逐子层 + 日志二值核查

### C1 逐子层表（服务 `.../MiddlesexCounty/Base_Layers/MapServer`）

| sublayer | 子层名 | 上游 count | 本层声明 | 实采 rows | 差 | 跨页(>2000) | 短页提前 break | 判定 |
|---|---|---|---|---|---|---|---|---|
| **0** | **Address (Units)** | **2,300** | **2,298** | **2,131** | **167（账本口径）/ 169（实时口径）** | **是** | **是（第 2 页只回 131 行）** | **short** |
| 1 | Address | 34,334 | 不在本层范围 | 0 | — | 是 | — | 不采 |
| 2 | Roads | 1,597 | 不在本层范围 | 0 | — | 否 | — | 不采 |
| 3 | Roads (Class) | 119 | 不在本层范围 | 0 | — | 否 | — | 不采 |
| 4 | Non-Agricultural Areas | 122 | 不在本层范围 | 0 | — | 否 | — | 不采 |
| 5 | Municipal Boundary | 10 | 不在本层范围 | 0 | — | 否 | — | 不采 |
| 6 | Lots & Concessions | 6,493 | 不在本层范围 | 0 | — | 是 | — | 不采 |

- 层 id 的 `/0` 决定**只采子层 0**；`/1`、`/6` 虽然也跨页，但不在本层范围，**不构成缺口来源**。
- **缺口 167 全部落在子层 0**；对上游实时 2,300 则是 169，169 恰等于 `OBJECTID IS NULL` 的行数。
- 167 用于账本验收（分母=声明），169 用于上游可核对面（分母=实时 count），**不可互换**。

上游实测（2026-11-21 直打 endpoint）：

| 查询 | count |
|---|---|
| `where=1=1&returnCountOnly=true` | 2,300 |
| `where=OBJECTID IS NULL` | **169** |
| `where=OBJECTID>2131` | **0** |
| `where=OBJECTID_1>2131` | 170 |

### C2 日志二值问题：有没有「keyset 停在 2131/2298 → 切 resultOffset 续翻」这一行？

查的是 138c05 真正被采的那次：**run 41184978867（07b shard 1，2026-10-31）**。

- `grep -c "切 resultOffset"` = **0**
- `grep -c "keyset 停在"` = **0**

**→ 没有这一行。**

日志实际序列（原文行）：

```
[138c05_...]   api=.../MiddlesexCounty/Base_Layers/MapServer/0 count=2298 pagesize=2000 workers=4 strategy=keyset
[138c05_...]   ↑ 已发布 138c05_...-u00000.tar.gz（1 个 part）
[138c05_...] done rows=2131 count=2298 diff=0.0727 err=- 7.8s
[138c05_...] ❌ 数据不齐 rows=2131 count=2298（缺 7.27%）
```

全程 7.8 秒、1 个 part、无任何续翻动作。

**成因结论是否仍成立：成立，且更准确的说法是「两条同时成立」。**

1. **提前收手（直接原因）**：第 2 页非空（131 行）但 `< pagesize` → 命中
   `if not r.get("exceededTransferLimit") and len(feats) < ps: break`，
   而 `if not feats:`（唯一会触发 `mode="offset"` 的分支）**从未进入**。
   所以「代码有能力切 offset」为真，「本次没切」也为真 —— 两者不矛盾。
2. **169 行 keyset 不可达（数据成因）**：`objectIdField`/`objectIdFieldName` 均为 null，
   名字兜底拿到 `OBJECTID`（169 行为 null），keyset 的 `OBJECTID>2131` 匹配 0 行，
   这 169 行**只有 resultOffset 能取到**。

**修法不依赖这条日志**：新逻辑不判断「是否发生过 offset 切换」，而是**无条件对账**
（`rows < expect×(1-GAP_TOL)` 就补翻，补不回落 `short`）—— 无论上游是短页、null 主键还是别的原因，都会被这条断言兜住。

### C3 585 vs 579：差的 6 层（全列，以 585 为准）

| # | 层 | declared | rows | 05b 账本状态 |
|---|---|---|---|---|
| 1 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 251,639 | 118,916 | partial |
| 2 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | partial |
| 3 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | partial |
| 4 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | partial |
| 5 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 9,624 | 9,101 | partial |
| 6 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 9,861 | 9,602 | partial |

6 层全为 MapServer、全在 `partial`、全被 `worker_core._veto_by_ledger`（W33-040）否决拉回；
585 ⊃ 579 无删除。**验收以 `10e87f5` 的 585 为准，579（`/tmp/plan05b.json`，11-20T21:46 量测）作废。**

---

## D · 四条修法落代码

| # | 要求 | 落点 | 做法 |
|---|---|---|---|
| D1 | 收尾硬断言 + 自动补翻，绝不静默 return | `collect/pilot.py:1026-1044`（`_unit_range` 收尾）、`:84`（`_top_up_offset`）、`:44`（`gap_short`） | rows 少于 expect 时先按 `ps` 再用 `max(200, ps//4)` 两轮 **resultOffset 补翻**（共用 `_absorb` 的 OID 跟踪，补翻进来也记账）；仍 short → `return "short:%d/%d"` → 上层记 partial/failed。补翻硬顶 **guard<500 页**（= 500×ps 行，防死循环）。`--limit` 试采不补翻（预期只取前 N 行）。 |
| D2 | 主键探测取「非空率最高」 | `collect/pilot.py:52` `pick_oid_field()`，两处调用点（`collect_arcgis` / `collect_arcgis_v2`） | 候选 `objectIdField/objectIdFieldName` + `OBJECTID/OBJECTID_1/OBJECTID_12/OBJECTID_2/FID/OID` 中存在于 `fields` 的；**一次 `returnGeometry=false` 的 50 行采样**（`outFields=候选列表`），比非空率取最高。成本：**每层 +1 次轻查询**（仅当候选 ≥2 个时发；单候选直接返回，零成本）。失败降级为「声明字段 → 名字序」。 |
| D3 | rows vs expect 门禁（派发前 + 收尾后） | `collect/full_plan.py:45-88,182-193`；`collect/preflight_dispatch.py:966`（D15） | **计划阶段**：`probe_live_counts()` 用 `returnCountOnly` 探上游实时行数（8 线程，失败记 `probe_failed`），写进 plan 的 `expect_by_layer` / `expect_live` / `expect_live_total`，`expect_source=returnCountOnly@plan`（`PLAN_PROBE_COUNT=0` 可关）。**收尾后**：preflight 新增 **D15** 判 `status=ok/skipped_done` 的行 vs **双分母**（账本 `declared` + 计划 `expect_live`），任一被击穿即 **FAIL**；partial/short 只列出不 FAIL。preflight `main()` 有 FAIL 即 `exit 1` → 派发脚本不会硬派。 |
| D4 | GAP_TOL 默认 0.5%、可配置 | `collect/pilot.py:38`、`collect/preflight_dispatch.py:114` | `GAP_TOL = float(os.environ.get("PILOT_GAP_TOL") or "0.005")`；门禁侧 `PREFLIGHT_ROWS_GAP_TOL`（默认 0.005）。两处同源、同默认值。选 0.5% 的理由：上游日常漂移 ±0.x%，卡 0.1% 会把正常层打成 short；138c05 缺 7.27%，0.5% 照样抓。 |

新增单测：

- `collect/tests/test_paging_assert.py`（6 条）：`gap_short` 触发/不触发边界（0.78% 触发、0.35% 不触发）、
  `_top_up_offset` 2,131→2,300 真用 `resultOffset`、补翻失败仍 short、`pick_oid_field` 选非空率最高、声明字段有值时优先。
- `collect/tests/test_preflight_rows_gate.py`（4 条）：ok-but-short → FAIL（138c05 形态）、partial 只列出、
  **live 分母参与判定**（过期快照 declared=2,270 放行 / live=2,300 缺 0.65% → FAIL）、无账本 → WARN。

---

## E · 产物

- 本文（A+B+C+D 合一篇）：`docs/ng911-05b/05b_stop_and_fix.md`
- 逐层筛查表：`docs/ng911-05b/05b-done-layers.md`（2,719 行）+ `collect/_recon/20261121/05b-done-layers.json`
- 逐子层：`docs/ng911-05b/138c05-sublayer-table.md`；成因：`docs/ng911-05b/138c05-cause.md`；585 vs 579：`docs/ng911-05b/585-vs-579.md`
- 代码：`collect/pilot.py` / `collect/full_plan.py` / `collect/preflight_dispatch.py` + 两个测试文件

**05b 未重启。**（本轮只读日志/账本/Releases + 改代码 + 单测，未派任何 run）
