# 全量盘点 · 2026-11-24（task `w2-20261124-full-inventory`）

**状态：Phase 3 已完成（终版）· 2026-11-24**

> 只盘点：不融合、不分级、不重写引擎、不动 Release/账本/网站、未起任何 collect run、未直推 main。
> 本文件为终版（Phase 0–3 全部收口）；数字全部来自本目录 CSV/JSON，可逐条复算。

## 〇、口径声明（先看这 6 条，后面所有表都按它读）

1. **基线 = 冻结账本 3,709 层**：`git show f836112:collect/{04b,05b,07b}_ledger.json` → 272 + 2,770 + 667。
   ⚠️ 仓内 **现盘** `collect/*_ledger.json` 已被后续重跑覆盖成 272 + 3,307 + 1,103 = **4,682 层**，
   **不能**用来对 3,709；本文件一律用冻结版（与 `docs/4-7-TOTAL-2026-10-31.md` 同日同源）。
2. **F3（只记口径、代码未改）**：NH 只按**州级合并件**计数 —— GRANIT 用 `raw-US-NH-granit-v1` 合并件
   （601,374 行）、TIGER 用 `raw-US-NH-v1` 合并件（5,870,025 行）；两者各自的 11 行里的**县级片不进任何合计**
   （GRANIT 分县 Σ 601,355 ≠ 州级 601,374；TIGER 分县 Σ 与州级逐位相等），**禁相加**。
3. **本地层 ≠ 原始上游行**：`dist/intake-full/layers/*/addr.*.ndjson.gz` 是 **08 去重索引的规范化中间件**
   （29~30 个 canonical 字段 + `src_layer_url`/`src_layer_id`），**不是原始字段名**。
   因此 Phase 2 的字段级表列的是 canonical 字段；原始字段名只能靠 Phase 3 的远程 meta 拿。
4. **抽样口径**：每层**每表**最多 200 行，`denom` = 该层该表**实际**抽到的行数，逐行写死；
   `nonnull_rate = nonnull / denom`；每行都带 `nonnull_rate_basis=sample200`。**精确全表非空率本轮不做**。
5. **行数来源**：层级表的 `rows` 取该层 `ledger.json` 的 `rows_total`（intake 逐层实读记录），
   `rows_source=intake-ledger rows_total`；取不到写 `unavailable`，不估。
6. **远程未采层 = survey 60,694 层 − 已采层**：survey 去重 url 60,693；已采 url 5,881
   （= 3,709 基线 3,631 个可解析 url ∪ 本地 2,351 个可解析 url）→ **未采 54,812 层**（本轮自己算，未沿用任何估值）。

---

## 一、Phase 0：3,709 口径 ↔ 本地可读层 逐层对账

产物：`local-vs-ledger-reconcile.csv`（**3,709 行，一层一行，每行带 `reconcile_class` + `reason`**）

| 类别 | 层数 | 判定证据 |
|---|---:|---|
| `local_ok_readable` | **105** | `dist/intake-full/layers/<layer>/` 存在且至少一个 `*.ndjson.gz` 非空（`tables` 列给出是哪几张表） |
| `local_absent_assets_exist_not_downloaded` | **3,550** | 2026-11-20 的逐层 release 索引（`.release_index.json`，3,986 层）**有该层载荷资产**（`<layer>-uNNNNN.tar.gz`），但 `dist` 无该层目录 → 只有 Release、没落本地 |
| `local_absent_upstream_no_assets` | **54** | 两份本地索引（11-20 逐层索引 / dist 里 1,426-tag 快照）**都查不到**该层，且账本状态非 ok |
| 合计 | **3,709** | 无第四类，无「其他/杂项」兜底 |

### 1.1 那 54 个「上游本无资产」的逐状态拆分（都是账本自己判的）

| 账本状态 | 层数 | 含义 |
|---|---:|---|
| `upstream_unstable` | 21 | 采集时上游连不上/报错 |
| `empty` | 21 | 上游明确 0 行 |
| `unverified` | 5 | 无法归因 |
| `ok` | **3** | ⚠️ 账本说采到了，但两份索引都没有资产 —— 逐层点名见下 |
| `partial` | 2 | 采到一部分 |
| `missing` | 2 | 计划里有、没有产物 |

3 个 `status=ok` 却无资产的层（与 08 文档里点到的 `_cog_server…` 是同一类，另有 2 个新发现）：
- `_cog_server_rest_services_test_Address_Point_FeatureServer_0`（08 文档已记，rows 9,046）
- `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0`
- `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1`（分区层）

⇒ 「账本 rows 是上游计数，不等于下载得到的行」这条再次被证实：**58 层账本有行、本地零资产**（54 + 3 中的重复口径见 CSV，逐行可查）。

### 1.2 `local_absent_assets_exist_not_downloaded`（3,550）按阶段

| 阶段 | 层数 | 说明 |
|---|---:|---|
| 05b | 2,732 | 几乎整阶段未落本地 |
| 07b | 662 | 同上 |
| 04b | 156 | 04b 共 272，其中 105 已可读（占比最高） |

**为什么没下**：intake（2026-10-30）只按当时那份 **1,426 个 tag** 的 Release 快照找资产，
而 08 文档记录的全仓是 **4,908 tag / 10,987 资产** —— 快照不全，于是 1,206 个层目录被写成
`no_assets`（`ledger.json` 里 `err="release 快照里没有该层"`），另有 3,550 层干脆没有目录。

### 1.3 「若要精扫这批层」的成本（【推算】，公式写明）

只有 179 个基线层的资产字节数在本地有记录（dist 快照带 `s` 字段）：Σ 29.55 GB，均值 0.165 GB/层、中位 0.055 GB/层。

- 按**均值**外推 3,550 层 × 0.165 GB ≈ **586 GB**（压缩包，含那个 5.3 GB 的 NAD 全量层，均值被它拉高）
- 按**中位**外推 3,550 层 × 0.055 GB ≈ **197 GB**

**所以现实区间 200–590 GB 压缩包**，解压后按 08 文档实测的 9–24× 膨胀比，磁盘需求 **2–8 TB** —— 本机 `/data` 只剩 110 GB，
**不建议**全量落盘精扫；建议只对「第 3 步要用的候选层」按需拉取。Release 来源：三仓 `collect-step04/05/07-*` 共 3,709 个 tag 里的 3,654 个有载荷资产（11-20 索引）。

### 1.4 本地目录里有 9 个层不在 3,709 基线内

`local_dirs_outside_baseline = 9`（全部可读）：它们是 `@<分区>` 变体目录（如 `…FeatureServer_0@MN-1`、`…@未定位-1`），
属于 08 分区孪生层，账本以 base 层记账 → 不进基线，但 Phase 2 仍扫（逐行可查）。

---

## 二、Phase 1：收第 2 步尾巴

### 2.1 `#9–#15` 七层重探（产物 `dirty-layer-reprobe.json`，共 18 个请求）

| # | 层（截断名） | 本次 count | 账本/快照 | 结论 | 现象 |
|---|---|---:|---|---|---|
| 9 | `paca_wi_us_…_Public_OpenData_MapServer_24`（Waupaca WI） | **28,660** | — / 28,646 | **已恢复** | meta 200、样值 20、`hsn` 门牌 20/20 |
| 10 | `tamonica_gov_server_…_Address_Points_MapServer_0`（Santa Monica） | **57,063** | — / 57,063 | **已恢复** | meta 200、`house`/`street`/`city`/`st`/`zip` 齐 → 标准地址层 |
| 11 | `untywi_gov_vilasgis_…_V4_SiteAddress_MapServer_0`（Vilas WI） | — | — / 48,148 | **仍不稳** | `URLError: timed out`（8s 超时），HTTP 0 |
| 12 | `almbeach_com_…_BaseData_Situs_MapServer_0`（Palm Beach） | **13,120** | — / 13,190 | **已恢复** | `STREET_NO` 20/20、`Address_Full` 齐 |
| 13 | `county_com_…_features_Address_MapServer_0`（Laramie WY） | **45,713** | — / 45,670 | **已恢复** | `bldg_no` 20/20 |
| 14 | `_services_NG911_ReadOnly_…_MapServer_0`（Onslow NC） | — | — / 108,836 | **仍不稳** | `URLError: timed out`，HTTP 0 |
| 15 | `buncombecounty_org_…_opendata_MapServer_2`（Buncombe NC） | — | — / 187,802 | **仍不稳** | `URLError: timed out`，HTTP 0 |

- **收敛情况**：4/7 已恢复且 `count` 与 survey 快照差 ≤0.06%（Waupaca +14、Palm Beach −70、Laramie +43、Santa Monica 完全一致）。
- **仍不稳 3 层**：全部是 **HTTP 0 + 客户端超时**（8 秒），**不是 4xx/5xx**；用更长超时（30s 以上）或换时段可能恢复，
  本轮按纪律不重试放大噪声。⚠️ 提醒：这三层在 2026-11-24 的 survey 快照里 count 非零，说明是**间歇性**不可达，不是下线。

### 2.2 `grouping-v2.json`（URL 唯一键，分母显式 20；原 `grouping.json` 未动）

| 口径 | 分母 | S/A/B/C | full_address | no_zip | no_city | road_only | empty_shell |
|---|---:|---|---:|---:|---:|---:|---:|
| muse 给的基线（= **pre-F1** 规则 + 首样口径） | 20 | 1/9/3/7 | 1 | 5 | 6 | 4 | 4 |
| **本轮实测 pre-F1 复现**（`git show b0a9587:sandbox/rules.py`） | 20 | **1/9/3/7** | **1** | **5** | **6** | **4** | **4** |
| 本轮现规则（F1 已合入 main）+ 首样口径 | 20 | 2/11/2/5 | 2 | 8 | 6 | 1 | 3 |
| 本轮现规则 + 多数票 | 20 | 2/11/2/5 | 2 | 8 | 6 | 2 | 2 |

**结论**：muse 给的基线**能逐位复现**，前提是用 **pre-F1 规则（b0a9587）+ 首条样值定组**。现规则对不上是**F1 的预期结果**，不是 bug：

| 层 | 州 | pre-F1 | 现（F1 后） | 触发别名 |
|---|---|---|---|---|
| Sacramento County, CA Addresses | KS | C / road_only | A / no_zip | `addr_housenumber` |
| City of Boston, MA Addresses | MA | C / road_only | A / no_zip | `addr_housenumber` |
| Address Points and CPNs | MD | B / road_only | S / full_address | `ADDR_NUMBER` |
| Address_1424300337393713068 | AZ | C / empty_shell | C / no_zip | `ADDRESSNUM` |

另：首样口径 vs 多数票只在 **1 层**上不同（PA `…/Q4NxsjNmWBIR4LYH/Address_Points/FeatureServer/0`：首样 `empty_shell`、2/3 样值 `road_only`）→ 两套计数差的那 1 个 `road_only`/`empty_shell` 就是它，未改数迁就。

---

## 三、Phase 2：本地已采层全量离线扫（零网络）

产物：`inventory-local-all.csv`（**2,364 行 = 本地全部层目录**）、`inventory-local-fields.csv`（**36,750 行 = 字段级**）

| 指标 | 值 | 与 Phase 0 自洽性 |
|---|---:|---|
| 扫描目录 | 2,364 | = Phase 0 `local_dirs` |
| 有数据可读 | **1,158** | Phase 0 `local_readable_layers` 同值 ✅ |
| 无可读数据（只有 `ledger.json`） | 1,206 | = intake `no_assets` 1,206 ✅ |
| 层级表行数 | 2,364 | = 1,158 + 1,206，差额逐条可查（`readable` 列） |
| 字段级表行数 | 36,750 | 只对有数据层产生；`(layer,table,field)` 一字段一行 |
| `rows` 合计（来自 ledger.json） | 278,753,145 | 与 intake `intake-progress.json` 的 `rows_total` **完全一致** ✅ |

`usable` 分布（分母 1,158 可读层）：

| usable | 层数 |
|---|---:|
| no_zip | 777 |
| road_only | 104 |
| empty_shell | 1 |
| sampled_zero_rows（可读但抽到 0 行，只有空表/表头） | 276 |
| 合计 | 1,158 |

`addr_core_hit`（`number|street|city|state|zip` 五项是否过半非空）Top：`11110` 418 层（缺 zip）、`11010` 359 层（缺 city+zip）、`01010` 56 层（无门牌）、`01110` 47 层。
**没有一层命中 `11111`** —— 这是 08 索引的已知事实：规范化后的 `zip5` 覆盖率低，所以 `full_address` 在本地层里是 0 层。
这正是「本地中间件不能代替原始层字段」的直接证据（见口径声明第 3 条）。

`source` 分布：`unknown` 1,928 / `step07` 285 / `step04` 151 / `step05` 0 —— 只有 436 层能在 11-20 逐层索引里对上 stage，
`unknown` 的大头正是 Phase 0 里那 1,206 个 `no_assets` 目录（它们没有 tag 可查）。

---

## 四、Phase 3：远程未采层 2 请求极速盘点（**已完成 · 终版**）

产物：`inventory-remote-uncollected.csv`（54,812 数据行 / unique url 54,812）+ `inventory-remote-uncollected.shards/`（275 个 ndjson，54,812 行 / unique url 54,812）+ `progress.json`（`phase3_live.done = 54,812`）。

### 4.0 总账

| 项 | 值 |
|---|---|
| 计划 / 已扫 | **54,812 / 54,812 = 100%** |
| ok | **41,570** |
| fail | **13,355** |
| 落盘层数（三处一致） | 分片 54,812 行 = unique url 54,812；CSV 54,812 数据行 = unique url 54,812；`progress.json` done 54,812 |
| 耗时 | 06:06:56Z → 09:55:38Z = **13,722 s（3 小时 49 分）**，其中 1 次看门狗重启 |
| 平均速率 | 全程 38,572 层 / 13,722 s = **2.81 层/s**；重启后末段 **3.87 层/s**（`progress.json.phase3.rate_layers_per_s`） |

> 上一版按前 240 层估的「9–11 小时」偏保守：survey 按 url 字母序排，**前半段恰好是死站密集区**（死站 8s 就放弃、
> 不发第二请求，但仍是「一层一层排队」），后半段大量层能正常返回 meta，请求变多反而吞吐更高 → 实际 3.8 小时跑完。

### 4.1 为什么 `ok 41,570` 比「ok 层的实际条数」多 113（必须解释清楚）

**结论口径**：看门狗重启后，同一批层被二次探活，ok 计数重复记录，故 ok 合计比层数多 113 条；
**落盘数据本身没有重复、没有脏数据**（CSV / 分片 / 进度三处层数均为 54,812）。

自证四步（都可在本目录复算）：

1. **落盘零重复**：分片 54,812 行，`unique url = 54,812`；CSV 54,812 数据行，`unique url = 54,812`。两个口径都看不到重复行。
2. **两个来源的 ok 差 113**：`progress.json` 的 `phase3.ok = 41,570`；CSV 里满足脚本同一判据（`http_meta==200 or http_sample==200`）的行 = **41,457**；差 **113**。
3. **fail 两侧一分不差**：CSV 非 200 行 = **13,355** = `progress.json` 的 `fail`。→ 113 只落在 ok 计数上，不是层数问题。
4. **113 的量级与「未落盘缓冲」吻合**：分片按 **200 层**一批落盘。`supervisor.log` 记录 `2026-11-24T09:12:26Z restart #1 reason=dead done=44953/54812`——进程被杀时，最多 200 层**已经探活、但还没写进分片**；重启进程按分片续跑，把这批**没落盘的层重新探了一遍**，而重启时读入的**累计基**（`progress.json.phase3.ok`）已经把上一轮这批算过一次 → 计数 +113，落盘仍是 1 层 1 行。

⇒ 等式闭合：`41,570 − 113 = 41,457`（落盘真实成功层）= `41,457 + 13,355 = 54,812`（层数）。
**下次若还要「ok 与层数严格相等」，做法是把 ok/fail 一律从分片重算，不接受进程内计数器。**

### 4.2 `fail 13,355` 的拆分（先交代 `url_shape` 列的事）

CSV 的实际列只有 18 个：`url, state, title, svc, geom, n_fields, maxRecordCount, count, count_source, sampled_n,
fields_number_like, number_nonnull, addr_core_hit, usable, requests_n, http_meta, http_sample, probe_note`
—— **没有 `url_shape` 列**（全仓 `grep -rn url_shape` 零命中，merge 脚本的 `COLS` 里也没有）。
所以「url_shape 拆分」是按 **url 路径形态现推**的等价口径；推完与 Muse 给的 **8,365 逐位吻合**，因此可以当作同一口径用：

| url_shape（按 url 路径形态派生） | fail 条数 | 说明 |
|---|---|---|
| **Socrata 门户/数据集页** `…/d/<id>` | **8,817** | 其中 **HTTP 404 = 8,365（= Muse 的 8,365，逐位对上）**；其余 452 = 406 Not Acceptable 203 + 超时 122 + 临时解析失败 108 + DNS 13 + Errno-5 3 + 503 2 + 403 1 |
| Socrata 数据集 API `…/resource/<id>.json` | 1,720 | 400 = 1,660、超时 49、403 = 4、临时解析失败 5、断连 1、404 = 1 |
| 非 Socrata（ArcGIS / CKAN / hub / 文件） | 2,818 | FeatureServer 1,478 + CKAN/下载 739 + MapServer 470 + hub 124 + agol 3 + 文件下载 3 + 空 1 |
| **合计** | **13,355** | 与 `progress.json` 的 `fail` 一致 |

**这 8,365 条属「门户页形态」，不代表数据源缺失**：它们是各市 Socrata 站点的**数据集浏览页 HTML 路径**（`data.xxx.gov/d/<id>`），
不是 Socrata 数据 API。拿它当 ArcGIS REST 端点去探 `?f=json`，必然 404 —— 404 是**探针打错门**，不是层消失。
同一批数据集的真正入口是 `/resource/<id>.json`（该形态 1,720 条里 1,660 条是 400 Bad Request，属参数/口径不对，换个查询参数大概率能救）。

**剩余 4,990 条**（= 13,355 − 8,365）= Socrata 其余 2,172（数据集 API 1,720 + 门户页非 404 的 452）+ 非 Socrata 2,818，按失败原因归类：

| 失败原因（`probe_note` 归类） | 条数 |
|---|---|
| HTTP 404（端点不存在 / 已下线 / 路径错） | 8,395 |
| HTTP 400 Bad Request（Socrata API 参数/口径不对，**最可能可救**） | 2,001 |
| 超时（meta 8s 超时，**未判死**，只代表这次没应答） | 1,146 |
| HTTP 401 / 403（需 token 或被拒） | 596 |
| URL 非法（含控制字符，survey 抓取时带入） | 518 |
| HTTP 406 Not Acceptable | 209 |
| Temporary failure in name resolution | 141 |
| UnicodeEncodeError（url 含非 ASCII 字符） | 121 |
| DNS 不存在（域名已废 / 内网名如 `*.local:6080`） | 111 |
| 连接被拒 / 被重置 | 54 |
| HTTP 5xx（500/502/503） | 36 |
| Errno -5 No address associated with hostname | 12 |
| HTTP 202（异步未完成，不算失败） | 10 |
| HTTP 572 / 521 / Errno 101 / worker TypeError | 5 |
| **合计** | **13,355** |

### 4.3 可用性七类合计 54,812（与 Muse 核过的一致）

| `usable` | 层数 | 含义 |
|---|---|---|
| `empty_shell` | 25,447 | 探通了，但样值里没有门牌也没有街名（多为面/线要素、或字段名不在识别表里） |
| `unreachable` | 13,354 | 两请求全失败（= fail 的主体） |
| `road_only` | 9,896 | 有街名、无门牌 |
| `no_zip` | 3,169 | 有门牌+街名+城市+州，缺邮编 |
| `full_address` | 1,994 | 门牌+街名+城市+州+邮编 五要素齐 |
| `no_city` | 951 | 有门牌+街名，缺城市 |
| `worker_error` | 1 | 单层解析异常（`worker_err:TypeError`） |
| **合计** | **54,812** | 与总账逐位一致（无「其他」「未知」桶，不留兜底） |

**下一轮可用的候选池（本轮只给数，不采集）**：
- 门牌 + 街名齐（五要素或四要素）**6,114 层** = `full_address` 1,994 + `no_zip` 3,169 + `no_city` 951；
- 再加「只有街名」的 `road_only` 9,896 层 → **16,010 层有街名**；
- 这 6,114 / 16,010 才是「第 3 步采集通道选择」的真正输入；`empty_shell` 25,447 层建议**先不做地址采集**（字段识别没打中，不等于上游没有——要原始字段名得回 Phase 3 的 `?f=json` 逐层看）。

### 4.4 采集纪律（本轮参数，照实记录）

- 每层 2 请求（meta `?f=json` + 20 条样值），`count` 取不到才补第 3 请求；`requests_n` 逐层落盘可核
- 并发 **8**；单层超时 meta **8 s** / sample **15 s**；**meta 失败即跳过 sample**（死站单层成本 28 s → 8 s）
- 429/5xx 才退避重试 1 次（1 s/3 s）；**超时/断连不重试**（避免 3 倍白等）
- 每 200 层：写 `shard-NNNNN.ndjson` + 追加 CSV + 刷 `progress.json`；**分片是唯一 source of truth**，
  `full_inventory_remote_merge.py` 可按 url 去重重建整表（本轮 CSV 与分片最终已一致：54,812 / 54,812）
- 零写入上游、零下载资产（只要 metadata + 20 条样值）

### 4.5 三次进程事件（不停产，但全部留痕）

| 时点（UTC） | 事件 | 处置 | 证据 |
|---|---|---|---|
| 03:08:27Z | 首轮后台进程**静默死亡**（无 traceback、无 OOM、日志停在 `16000/54772`） | 06:07Z 手工续跑（靠分片跳过已完成 url，零重采） | `progress.json` 停机时 `done=16240`；`run.log` |
| 06:07Z | 续跑启动，补 30 s 心跳 + 累计基 + `RLock`（探针逻辑零改动） | pid 583907，60 s 查活存活 | `run.log` 第 1–2 行 `todo=38572 already_done=16240` |
| 09:12:26Z | 第二次静默死亡（`done=44953`） | **看门狗自动拉起**（`full_inventory_supervise.sh`，60 s 轮询） | `supervisor.log: restart #1 reason=dead` |

**层数口径的坑（顺手记下，避免下次误判）**：CSV 物理行数比层数多，是因为
① 表头 1 行；② 个别 url 含控制字符被 csv 引号包成**跨物理行**
（例：`montgomeryplans.org/arcgis4/…/MapServer/13`）。所以「已探层」一律取
`unique url` 或分片行数，**不要用 `wc -l` 直接当层数**。

---

## 五、下一轮建议（按性价比排序）

1. **先别全量落盘**：3,550 层要 200–590 GB 压缩包 / 2–8 TB 解压，本机只剩 110 GB。建议只对「第 3 步候选」拉层（按 URL 直取，不走 Release）。
2. **补一份完整 release 快照**（`gh api` 全量 4,908 tag）→ 可把 3,550 层从「未下载」进一步细分为「有分片/只有 merged/只有 checkpoint」，并把 1,206 个 `no_assets` 假阴性纠正。
3. **采集通道选择**（Phase 3 已给出输入）：直接用 6,114 层（门牌+街名齐）做第一批候选；Socrata 那 1,720 条 `/resource/<id>.json` 换成 Socrata 正规查询（`$limit`/`$where`）再探一次，比按 ArcGIS REST 探有效得多。
4. **本地中间件不要当原始层用**：要原始字段名，必须走 Phase 3 的 `?f=json` 或按需拉分片；`zip5` 缺失是规范化口径问题（08 索引只在 addr 表里尽力补），不是上游没有。
5. **7 个脏层**里 3 个（Vilas / Onslow / Buncombe）建议下次探针用 60s 超时 + 2 次换时段，别用 8s 就判死（本轮 1,146 条超时同理，属「这次没应答」，不是「层不存在」）。
6. **ok/fail 一律从分片重算**：进程内计数器在重启后会重复计数（本轮多 113），落盘永远干净、计数器不保证。

---

> 终版快照：Phase 3 已完成 **54,812 / 54,812（100%）**，分片/CSV/进度三处层数一致，`ok 41,570 / fail 13,355`（ok 含 113 条重启重复计数，落盘真实 ok 41,457）。
