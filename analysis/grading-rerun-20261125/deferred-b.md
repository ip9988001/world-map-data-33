# DEFERRED-B refinement · 底图视图类非地址层从 Tier1 剔除（结转登记）

- 本轮工作树：`/data/workspace/wmd-grading-rerun`，分支 `feat/grading-rerun-20261125`，基线 `267de21`
- 只读输入：`analysis/auto-spatial-rerun-20261125/`（第 5 步 strict）、`analysis/auto-spatial-relax-20261125/`（第 7 步 relax，Tier1=176）、
  `analysis/grading-rerun-20261125/auto-recognized.csv`（本轮）、`analysis/coord-samples-20261124/samples/*.csv`、`analysis/full-inventory-20261124/`
- 写盘：只有本文件。**没有改任何判据、没有改 `sandbox/` 代码、没有动 registry**——本轮这一节是「登记 + 首个样本走查」，不是「批量执行」。

---

## 0. 一句话

**NH 的 2 层虽然名字里带 `Base_Map` / `BaseMap_View`，但字段集里有真实 `addrnum` + `streetname` + `zip`，抽样 50/50 行全部构得出「门牌+街名+邮编」键、E7 实测 clear —— 它们是地址点层的显示副本，不是非地址层。因此 DEFERRED-B 对 NH 这 2 层的结论是不剔除（保留 Tier1）；同时登记一个新发现：这 2 层是同一份数据的重复发布。**

### 0.1 判据原文来源：`unavailable`（不糊）

结转登记要求「按结转登记六条判据逐条登记（判据原文列全）」。本轮在下列位置**都没有找到**「DEFERRED-B」或该六条判据的原文：

| 检索位置 | 命令 | 结果 |
|---|---|---|
| 全仓库（含 analysis/ docs/ sandbox/） | `grep -rn "DEFERRED-B\|底图\|结转" --include=*.md --include=*.py --include=*.yaml .` | 0 命中 |
| 工作区全部文本 | `grep -rln "DEFERRED-B" /root /data` | 0 命中（除本轮派单原文） |
| 历史会话 | `grep -c "DEFERRED" <session>.jsonl` | 0 |
| 记忆库 | `recall_memory("DEFERRED-B 底图视图类非地址层六条判据 结转登记")` | 无相关条目 |

→ **六条判据的原文：`unavailable`。** 下面的 D1–D6 是**本轮按仓库内可核证据重建的判据条文**（写法照抄本仓库既有判据风格：每条给「条文 / 判定口径 / 数据源 / 可否自动化」），不是原文。等 muse 补原文后，
只需把 D1–D6 换成原文、逐条重跑本文件的表格即可，**机制（判据 → 判定 → 登记）不用改**。

---

## 1. 六条判据（重建版，逐条列全）

> 每条都是「要证成『这一层是底图/视图类非地址层』必须同时满足的必要条件」。判定结果只有三种：
> `满足` / `不满足` / `unavailable`（数据取不到，不用占位值代替）。

### D1 命名角色判据

**条文**：图层名、服务名或图层标题里出现 `base map` / `basemap` / `base layer` / `base mapping` / `reference layer` / `底图` 之一，
**且**该层的用途描述是「供显示/参照」，而不是「发布地址数据」。

- 判定口径：对 `service_name` + 图层 `name` 做小写子串匹配；用途无法从上游文本判定时，本条只作**触发条件**，不作结论依据。
- 数据源：`analysis/full-inventory-20261124/inventory-remote-uncollected.csv` 的 `url` / `title`。
- 可否自动化：是（纯字符串）。
- 说明：本条只回答「**为什么值得查**」，单靠 D1 **永远不能**剔除一层。

### D2 字段语义判据

**条文**：该层字段集里**不存在**「门牌族」或「街名族」字段——按 `engine/split_addr.roles_of()`
（`registry/dialects.v1.yaml` ∪ `engine/dialects/*.yaml`）的 number/street 角色表判定；或者存在但这些字段的样值**全是占位值**
（`engine/split_addr.is_placeholder()`：`"" "-" "NULL" "N/A" "-1" "-999" "0" …`）。

- 判定口径：命中角色表的字段数 = 0，或命中但非占位样值数 = 0。
- 数据源：`analysis/dialect-20261124/probe-fields.ndjson`（探针字段集）、坐标样本 `addr_fields_json`、`inventory-local-fields.csv`（本地样值）。
- 可否自动化：是。

### D3 键可构性判据（本判据是本轮 E7 口径的直接延伸）

**条文**：按 `engine/split_addr.addr_key_split()` 口径，该层抽样行里**构不出任何**「门牌 + 街名 (+ 邮编)」键
（`n_addr_rows = 0`）；且「门牌+街名拼一格」的整串也切不出（`split_number_street` 的 `reason != "ok"`）。

- 判定口径：`analysis/grading-rerun-20261125/coord-evidence.csv` 的 `n_addr_rows = 0` 且样本 `sample_fields` 里没有可切整串。
- 数据源：本轮 `coord-evidence.csv`。
- 可否自动化：是。

### D4 坐标性质判据

**条文**：该层坐标不具备「独立地址点」性质——满足任一：① `geom_type` 是 `polyline`/`polygon` 且无任何地址字段；
② `unique_rate < fuse.min_unique_coord_rate`（0.05，见 `sandbox/spatial_thresholds.yaml`）；
③ `top_point_share > fuse.max_top_point_share`（0.50）。

- 判定口径：直接用 `coord-evidence.csv` 的 `geom_type / unique_rate / top_point_share` 与阈值文件比对（阈值不写在代码里）。
- 可否自动化：是。

### D5 证据链自洽判据

**条文**：E1（门牌族样值）/ E2（街名族样值）判 `clear`，但 E7 判 `unknown` 且其归因是
「本层样本无『门牌+街名』键（n_addr_rows=0）」——即「样值看着有值，但构不出可投票的地址键」，
说明该层提供的是**地址样子的字符串**而不是可对齐的地址记录。

- 判定口径：`E1_state == clear and E2_state == clear and E7_state == unknown and n_addr_rows == 0`。
- 可否自动化：是。

### D6 重复发布判据

**条文**：若该层与另一层的 `rows_n` 相同、字段集相同、抽样样值逐行相同（同 org、同数据、不同显示名），
则它是**同一份数据的显示副本**；处置走去重口径（`analysis/08-dedup-plan-2026-11-01.json` 一系），
**不得**按「底图非地址层」剔除，也不得按缺陷计分。

- 判定口径：`rows_n` 相等 + `sample_fields` 集合相等 + 抽样 `addr_fields_json` 序列相等。
- 可否自动化：是。

### D0 判定合成规则（怎么从六条得出「剔除 / 不剔除」）

```
剔除 ⟺ D1 满足 ∧ (D2 满足 ∨ D3 满足) ∧ D4 满足      # 三条都要有证据，缺一条就是「不剔除」
D5 作交叉校验：D2/D3 判「非地址」但 D5 不成立 → 判 unavailable，不剔除（不许拿一条推断另一条）
D6 独立行使：只影响「怎么处置重复」，不参与剔除判定
```

---

## 2. NH 2 层逐层走查（首个样本，逐条打验证）

层（URL 末尾，完整 URL 见 `denominator-excluded.csv` 同格式）：

- **N1** `services6.arcgis.com/UfXcKlfRMOLiWRIE/.../VW_Base_Map_(View)/FeatureServer/0`（标题 `VW Base Map (View)`，`rows_n=15,007`）
- **N2** `services6.arcgis.com/UfXcKlfRMOLiWRIE/.../pbBaseMap_View/FeatureServer/0`（标题 `pbBaseMap View`，`rows_n=15,007`）

| 判据 | N1 证据 | N1 判定 | N2 证据 | N2 判定 |
|---|---|---|---|---|
| **D1 命名** | 标题 `VW Base Map (View)`、服务名含 `Base_Map`、图层 path 含 `(View)` | **满足**（仅触发） | 标题 `pbBaseMap View`、服务名含 `BaseMap` | **满足**（仅触发） |
| **D2 字段** | 30 字段，含 `addrnum`（number 角色）、`streetname`（street 角色）、`zip`、`st_suffix`、`municipality`、`fulladdr`；样值 `18` / `Elizabeth Ln` / `03079` 均非占位 | **不满足** | 同 N1（字段集、样值逐行一致） | **不满足** |
| **D3 键可构性** | `n_addr_rows = 50`（50/50 抽样行构出键）、`n_cmp = 50`、`n_conflict = 0` | **不满足** | `n_addr_rows = 50`、`n_cmp = 50`、`n_conflict = 0` | **不满足** |
| **D4 坐标性质** | `geom_type=point`、`unique_rate=1.00`、`top_point_share=0.02`（阈值 0.05 / 0.50）、E6 clear | **不满足** | 同上（逐项相同） | **不满足** |
| **D5 证据链** | E1=clear、E2=clear、E7=**clear**（不是 unknown）→ 自洽 | **不满足** | 同 N1 | **不满足** |
| **D6 重复发布** | 与 N2 同 org、`rows_n` 同为 15,007、`sample_fields` 相同、抽样行 `fulladdr` 序列相同 | **满足**（登记为重复发布） | 与 N1 互为副本 | **满足**（登记为重复发布） |
| **D0 合成** | D1 满足，但 D2/D3/D4 全部不满足 | **不剔除，保留 Tier1** | 同 N1 | **不剔除，保留 Tier1** |

**为什么不能只看名字就剔**：这 2 层的 `fulladdr` 是 `18 Elizabeth Ln` / `8 Coburn St` / `32 Henry Taylor St`（Salem, NH, ZIP 03079），
`unique_rate=1.0` 说明 50 个抽样点没有一个是「一个点冒充整层」；E7 有 50 行跨源同址可比且 0 冲突。
把这样的层按「底图」剔掉，等于把真实地址数据从 Tier1 里踢出去。

**本轮实算的位置**：这 2 层都在本轮 Tier1 = 410 的名单里（`analysis/grading-rerun-20261125/auto-recognized.csv`，`tier=tier1`）；
按 D0 结论**不做任何剔除**，所以 §五 的 Tier1 数字不含任何 DEFERRED-B 扣减。若 muse 认为「显示副本只该算一层」，那是 D6 去重口径，
应从分母去重、而不是从这里扣 Tier1 —— 本轮**不擅自执行**，只登记。

---

## 3. 待办（本轮只走首个样本）

| 项 | 状态 |
|---|---|
| D1 触发的候选层全表盘点（名字含 base map / view / base layer 的 Tier1 层） | **部分完成**：本轮 Tier1 名单里按 D1 字符串匹配共 14 层，清单见 §3.1；逐层走查**只做了 NH 2 层**（本单要求） |
| 其余 12 层的 D2–D6 逐层走查 | `unavailable`（本轮未做，不结案、不剔除） |
| 六条判据原文入库（替换 D1–D6 重建版） | `unavailable`，等 muse 提供 |
| D6 去重口径落地 | 不属本单；已登记 N1/N2 为重复发布 |

### 3.1 D1 触发候选（本轮 Tier1=410 内的全部命中，14 层）

D1 字符串匹配 `base[_ ]?map|basemap|base[_ ]?layer|base[_ ]?mapping|reference[_ ]?layer`（不区分大小写）→ **14 层**，
每一层的 `n_addr_rows` 都 > 0（都构得出地址键）。逐条结论见 §2（只做了 NH 2 层），下表其余 12 层**未逐层走查**。

| # | 层（URL `…/rest/services/` 之后） | rows_n | n_addr_rows | geom | unique_rate | 字段（抽样） |
|---|---|---:|---:|---|---:|---|
| 1 | `VW_Base_Map_(View)/FeatureServer/0` **（NH·已走查）** | 15,007 | 50 | point | 1.00 | addrnum, fulladdr, streetname, zip |
| 2 | `pbBaseMap_View/FeatureServer/0` **（NH·已走查）** | 15,007 | 50 | point | 1.00 | 同上（与 #1 逐行相同） |
| 3 | `AUT_AGOL_BASEMAP_DATA/FeatureServer/1082516610` | 19,997 | 49 | point | 1.00 | GL_HSE_NUM, GM_HSE_NUM, PO_ZIP |
| 4 | `AUT_AGOL_BASEMAP_DATA_Public/FeatureServer/1082516610` | 19,997 | 49 | point | 1.00 | 同上（疑似重复发布） |
| 5 | `CUDBasemapVTC20220220/FeatureServer/1` | 165,453 | 50 | point | 1.00 | ADDRAUTH, ADDRCLASS, ADDRNUM |
| 6 | `Basemap2024_WFL1/FeatureServer/27` | 31,444 | 50 | point | 1.00 | ADDRESS, SITENUMBER, SITECITY |
| 7 | `JohnsCreekBasemap_Vector_No_labels/FeatureServer/40` | 32,494 | 50 | point | 1.00 | FullAddr, PostType, StreetID |
| 8 | `EnerGovBaseMap/FeatureServer/0` | 25,660 | 50 | point | 1.00 | ADDRNUM, FULLADDR, MUNICIPALITY |
| 9 | `BasemapFeatureService_ReadOnl/FeatureServer/0` | 11,529 | 50 | point | 1.00 | ADDRNUM, FULLADDR |
| 10 | `zMoonTownshipOverallBaseMapping/FeatureServer/1` | 13,382 | 50 | point | 1.00 | ADDR_NUM, ADDRESS_ID, ADDRESS_TY |
| 11 | `FAR2025_Basemap/FeatureServer/0` | 1,344 | 50 | point | 1.00 | NUMBER, STREET |
| 12 | `OnlineBasemap_view/FeatureServer/7` | 19,034 | 50 | point | 1.00 | ADDRNUM, FULLADDR, MUNI |
| 13 | `Base_Layers_View/FeatureServer/5` | 11,538 | 41 | point | 0.98 | Add_Number, AddNum_Suf, Full_Addr |
| 14 | `GIS/Collector_Base_Layers_GIS_STAGE/FeatureServer/0` | 37,938 | 50 | point | 1.00 | MSAG_COMMUNITY, POST_COM… |

**共性（只作观察，不作结论）**：14 层全是 `point`、`unique_rate ≥ 0.98`、`n_addr_rows ≥ 41` —— 名字叫底图，装的都是地址点。
另有 2 组疑似重复发布：`#1/#2`（15,007×2）与 `#3/#4`（19,997×2），处理权在 D6 去重口径，不在本节。

---

## 4. 复算

```bash
# 本文件所有数字的出处（只读，约 20 秒）
python3 - <<'EOF'
import csv
u = ['https://services6.arcgis.com/UfXcKlfRMOLiWRIE/arcgis/rest/services/VW_Base_Map_(View)/FeatureServer/0',
     'https://services6.arcgis.com/UfXcKlfRMOLiWRIE/arcgis/rest/services/pbBaseMap_View/FeatureServer/0']
ce = {r['url']: r for r in csv.DictReader(open('analysis/grading-rerun-20261125/coord-evidence.csv'))}
ar = {r['url']: r for r in csv.DictReader(open('analysis/grading-rerun-20261125/auto-recognized.csv'))}
for x in u:
    print(x.split('/services/')[-1], ar[x]['tier'],
          {k: ce[x][k] for k in ('n_addr_rows', 'n_cmp', 'unique_rate', 'top_point_share', 'e7', 'sample_fields')})
EOF
```
