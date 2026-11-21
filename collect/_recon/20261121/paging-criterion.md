# 分页收敛判据 · 取证报告（2026-11-21）

> 只读取证：未改动任何 run / 分片 / 断点 / 产物。样本层 = 138c05（MiddlesexCounty Base_Layers MapServer_0）。

## 〇、这次跑批用的代码版本

| 项 | 值 |
|---|---|
| repo / workflow | `ip9988001/world-map-data-33` · `.github/workflows/collect-full.yml` |
| branch / **commit** | `main` · **`857e08c824313f3187642a329d4b3b0d7d835750`**（run `44865991911`，event=workflow_dispatch） |
| 跑批阶段 | 05b（plan 585 层 / 3 片 / size=200 / declared 32,337,294） |
| 采集入口 | `collect/full_shard.py` → `collect/pilot.py`（unit 路径 `_collect_unit`，即 `part-uNNNNN-bbb` 打包） |

判据所在文件：`collect/pilot.py`（下述行号均针对 `857e08c`）。

## 一、分页收敛那几行（原文，未改写）

### 1) 主键解析（判据失守的真正起点）

`collect/pilot.py:47-58`
```python
    oid_field = meta.get("objectIdField") or meta.get("objectIdFieldName")
    if not oid_field:
        # ★ 2026-10-23 san_juan：MapServer 的 objectIdField 为 null，实际主键叫 FID。
        #   原来直接兜底 "OBJECTID" → orderByFields=OBJECTID 报 400 → 只拿到第一页 2000 行。
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        oid_field = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID", "OBJECTID_12")
                          if k in fns), "OBJECTID")
```

### 2) 页大小（pageSize 的来源）

`collect/pilot.py:38-48`
```python
def page_size_for(api):
    """自适应页大小：字段多就少给点，避免响应过大"""
    meta = get_json(api + "?f=json", timeout=25)
    nf = len(meta.get("fields") or [])
    maxrc = int(meta.get("maxRecordCount") or 1000)
    ps = min(maxrc, 2000)
    if nf > 120:
        ps = min(ps, 200)
    elif nf > 60:
        ps = min(ps, 500)
    return ps, maxrc, meta
```

### 3) keyset 翻页 + 收敛判据（unit 路径，05b/07b 实际走这条）

`collect/pilot.py:893-940`
```python
    while True:
        if mode == "keyset":
            w = w0 if last is None else "%s AND %s>%s" % (w0, oid_field, last)
            q = dict(base, where=w, resultRecordCount=ps, orderByFields=oid_field)
        else:
            q = dict(base, resultOffset=off, resultRecordCount=ps, orderByFields=oid_field)
        r = _q(api, q)
        if "__error__" in r:
            flush()
            return rows, files, "query_fail:" + str(r["__error__"])[:160], expect
        feats = r.get("features") or []
        if not feats:
            if rows == 0 and last is None and mode == "keyset":
                q2 = {k: v for k, v in q.items() if k != "orderByFields"}
                r = _q(api, q2)
                feats = r.get("features") or []
            if not feats:
                # keyset 翻不动（服务端把「主键>n」当空条件）但 count 没拿够 → 换 resultOffset 续翻
                if mode == "keyset" and rows > 0 and rows < expect:
                    mode, off = "offset", rows
                    log("  u%d keyset 停在 %d/%d → 切 resultOffset" % (idx, rows, expect))
                    continue
                break
        for ft in feats:
            ...
            oid = at.get(oid_field)
            if oid is None:
                for k in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                    if k in at:
                        oid = at[k]
                        break
            if oid is not None:
                last = oid
        ...
        if limit and rows >= limit:
            break
        if mode == "offset":
            off += len(feats)
        if not r.get("exceededTransferLimit") and len(feats) < ps:
            break
        time.sleep(0.1)
    flush()
    return rows, files, "", expect
```

### 4) legacy 路径的同款判据（对照用）

`collect/pilot.py:90-137`
```python
    while True:
        where = where0 if last_oid is None else f"{oid_field}>{last_oid}"
        ...
        if limit and rows >= limit:
            break
        if not d.get("exceededTransferLimit") and len(feats) < ps:
            break
        if last_oid is None:      # 没有 OID 字段，退化为 offset 翻页
            break
```

## 二、四问四答

**问 1：判据是不是「本页返回条数 < 请求的 pageSize 就 break」？**
**是，但不是裸判据** —— 实际是 `not r.get("exceededTransferLimit") and len(feats) < ps`（`pilot.py:938`）。
即「本页不满 **且** 服务端没置 `exceededTransferLimit`」才停。形状是对的。

**问 2：有没有拿服务端总数对账？有没有读 `exceededTransferLimit`？**
- `exceededTransferLimit`：**读了**（`:938`，legacy 路径 `:132` 同样读）。
- 服务端总数：**开头取了一次**（`$api/query?where=1=1&returnCountOnly=true` → `expect`/`count`，`:863` 与 `:1001`），
  **但收尾没有对账** —— 函数返回 `(rows, files, "", expect)`，`rows < expect` 时**不报错、不切模式、不重试**（`:942`）。
  唯一的「count 对账」只在 **`feats` 为空** 时才触发切 `resultOffset`（`:911`）；本层第二页拿到了 131 行（非空），
  所以那条兜底**根本没机会触发**。
- 结论：**有 `exceededTransferLimit` 判据，无终局 count 对账**。

**问 3：请求的 pageSize 从哪来？是否恒 ≤ maxRecordCount？逐层实参：**
| 层 | 代码 | 实参 |
|---|---|---|
| 1 | `full_shard.py` → `pilot` 单元线程 | 不传 ps；`unit_rows` 只用于切片，不用于页大小 |
| 2 | `pilot._collect_unit` 开头 | `ps, maxrc, meta = page_size_for(api)`（`:990`） |
| 3 | `page_size_for`（`:38`） | `maxrc = int(meta["maxRecordCount"] or 1000)`；`ps = min(maxrc, 2000)`；字段数 >120 → ≤200，>60 → ≤500 |
| 4 | 请求参数 | `resultRecordCount = ps`（`:896`），**恒 ≤ maxRecordCount** |

138c05 实测：`maxRecordCount=2000`、`fields=6` → `ps = min(2000,2000) = 2000`（未被字段数压到 500/200）。
**所以「ps 大于服务上限」不是本次缺口原因**（ps 恰等于上限，`exceededTransferLimit` 也因此可读）。

## 三、138c05 逐子层：声明 vs 实采 vs 差

服务：`.../MiddlesexCounty/Base_Layers/MapServer`（层 id 的 `/0` = 子层 0）

| sublayer | 名称 | 上游 count（实时） | 实采 rows | 差 | 说明 |
|---|---|---|---|---|---|
| **0** | **Address (Units)** | **2,300** | **2,131** | **169** | 本层在采范围内；缺口即本节结论 |
| 1 | Address | 34,334 | 0 | — | 不在本层范围（层 id 指 `/0`） |
| 2 | Roads | 1,597 | 0 | — | 同上 |
| 3 | Roads (Class) | 119 | 0 | — | 同上 |
| 4 | Non-Agricultural Areas | 122 | 0 | — | 同上 |
| 5 | Municipal Boundary | 10 | 0 | — | 同上 |
| 6 | Lots & Concessions | 6,493 | 0 | — | 同上 |

### 167 与 169 的对账

| 数 | 算法 | 分母 | 判定 |
|---|---|---|---|
| **167** | `declared 2,298 − 实采 2,131` | 计划期声明快照（`layer_plan_clean.csv` 该行 2298） | **账本口径正确值**；`167/2,298 = 7.27%` |
| **169** | `上游实时 count 2,300 − 实采 2,131` | 上游实时 recount（今天） | 算术也对，但**只能配 2,300 作分母**（`169/2,300 = 7.35%`） |

**错的是混用**：把 169 写在 declared=2,298 的同一行里算 7.3%（我上一份回执 B 表就是这么写的），
或写成 `169/2,298`（= 7.35% 与 7.27% 混）。两个数各自成立：
- 对账本/验收 → 用 **167 / 2,298**（声明快照口径，D14/W33-034 的「按声明分母」）；
- 对上游可核实 → 用 **169 / 2,300**（「按可核实分母」）。
两者差 2 行，正是声明快照 2,298 与实时 2,300 的差（不是采集错）。

### 缺口成因：**判据缺陷（keyset 撞空主键），不是上游声明虚高**

实测三条（同一层直接打上游）：

| 查询 | count |
|---|---|
| `where=1=1` | **2,300** |
| `where=OBJECTID IS NULL` | **169** |
| `where=OBJECTID_1>2131` | 170 |
| `where=OBJECTID>2131` | **0** |

- 该 MapServer 的 `objectIdField` / `objectIdFieldName` **都是 null**（元数据实测），代码兜底按「字段名字典序优先级」
  取到 **`OBJECTID`**（`pilot.py:52`），但 **`OBJECTID` 有 169 行是 null**，真实主键是 **`OBJECTID_1`**。
- 于是 keyset 的 where 是 `1=1 AND OBJECTID>last`：**null 行永远不满足任何 `OBJECTID>n`** → 这 169 行在任何一页都取不到。
- 实采 2,131 = 2,300 − 169（非空 OBJECTID 行数）—— 数字严丝合缝。
- `d12 报的「6 组子层重复声明」与本层无关**：本层只采子层 0，重复声明是别层的 `@分区` 形态；且实时 count 2,300 > 声明 2,298，
  方向与「虚高」相反。**上游没有虚高**。
- 收敛判据 `not exceededTransferLimit and len(feats) < ps` 本身没误判（第二页确实只有 131 行、也没置 exceeded），
  **但它挡不住「where 条件本身漏了一整类行」** —— 因为漏掉的行根本不在返回结果里，任何页级判据都看不见。
  唯一能发现的是终局 `rows(2,131) vs expect(2,298)` 对账，而这段代码收尾**没有对账**（`:942`）。

## 四、05b 计划 579 vs 585（以计划提交 `10e87f5` 为唯一权威）

`collect/ledger/05b_plan.json` 版本史：

| commit | 时点 | layers_n | shards | size | declared_rows |
|---|---|---|---|---|---|
| `49e5bd7` | 2026-10-31 收官 | 2,770 | 14 | 200 | 144,741,233 |
| `e4bf61f` | run 41167836540 | 1,033 | 21 | 50 | 42,193,734 |
| **`10e87f5`** | **run 44865991911（本次）** | **585** | **3** | **200** | **32,337,294** |

**579** 的出处：`/tmp/plan05b.json`（2026-11-20T21:46 本机 `full_plan.py --stage 05b` 实测，579 层 / 3 片 / declared 32,005,223），
即**上一轮量出来的待采数**，不是任何一次提交的 plan。

两版逐层比对：`585 ⊃ 579`（无删除），**多出 6 层**，全为 **MapServer** 类型：

| # | 层名 | 在哪一版 | 为什么 |
|---|---|---|---|
| 1 | `_services_NWS_AddressPoints_Nstreets_centerlines_MapServer_0` | 仅 585 | 11-20 时不在待采集（未进 05b 选层结果），本轮 plan 纳入 |
| 2 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 仅 585 | 同上（Labels 层，11-20 未选中） |
| 3 | `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` | 仅 585 | 同上（`Layers_33`，子层号越界形态 11-20 未入选） |
| 4 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 仅 585 | 同上（与 #2 同服务另一子层） |
| 5 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 仅 585 | 同上 |
| 6 | `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6` | 仅 585 | 同上 |

**差异成因**：两版之间 05b 的选层口径（`layer_plan_clean.csv` + `skip_done` + 上游 unstable 剔除）没变，
差异来自**计划期重算**：本轮 `full_plan.py` 重扫 Releases 时这 6 层尚未满足「已采」判据（tag/checkpoint 不齐），
而 11-20 那次量测把它们算作已采（口径差 → 少 6 层）。**以 `10e87f5` 的 585 为准**，579 作废（它是量测快照，不是计划）。
declared 增量 332,071 行即这 6 层之和。

## 五、05b 当前状态（只读）

- run `44865991911`：**in_progress**（2026-11-21T04:24:56Z 起，`chain=0`）。
- plan 成功：**585 层 / 3 片 / size=200 / 声明 32,337,294 行**。
- shard (0)(1)(2)：**全部 in_progress**（04:27:03Z 起跑），**0 片失败、0 片取消**。
- 已完成层数/当前层：片账本每片跑完才落 git，三片都未结束 → 暂不可得（不做推测）。
- page_size 与 maxRecordCount 对照（样本 138c05）：`maxRecordCount=2000` / `fields=6` → `ps=2000`，**ps = maxRecordCount**，
  未被字段数阈值压小。

## 六、一句话判定

**立刻停片修判据，别让它跑完。** 判据形状没错，错在 `pilot.py:52` 按字段名挑主键拿到全 null 的 `OBJECTID`
（真实主键 `OBJECTID_1`），使含 null 主键的行在 keyset 下**永久不可达**，而收尾（`:942`）没有 `rows vs expect` 对账——
同一 commit `857e08c` 的 05b 三片还在跑，每层只要存在 null 主键就会静默少采，跑完再补等于白跑一轮（本例 7.3%）。
修法三件套：① 主键探测改成「取非空率最高的候选字段」而不是字段名优先级；② 收尾 `rows < expect×(1-GAP_TOL)` 时切
`resultOffset` 续翻并落 `partial`；③ 对 `OBJECTID IS NULL` 有行的层强制走 offset 或 `objectIds` 分批。
