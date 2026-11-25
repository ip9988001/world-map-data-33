# 第 8 步 · 账实对账清理（v4 · muse-000247）

> **一句话**：3,550 层「Release 有载荷、本地无目录」的**方法链已跑通并落地了一部分**：逐层拉取 → 四道校验 → 归零该层类别，
> 但**没有拉完** —— 网络实测被限在 **≈2.8 MB/s**（并行提到 6 路也只到 3.4 MB/s，见 §1.2），17.4 GiB 需要 ≈105 分钟纯传输，
> 加上每层 `gh` 逐资产开销，180 分钟内只能完成一部分。本报告按「已拉 N 层 / 未拉 3,550−N 层」如实报，断点续跑随时可用。
> 另外三件事都必须先说清：① **Release 载荷不是本地层目录的形态**（是 part 包，分表要 field-map，而 field-map 不覆盖这 3,550 层）；
> ② **CSV 的 `release_payload_n` 大面积陈旧**（实测 65 片 vs CSV 5 片）；③ **54 层的结论是上游健在、根本没派采集**（0 层「上游整层空」）。

- 工作树 `/data/workspace/wmd-step8-reconcile`，分支 `feat/step8-reconcile-20261125`，基线 **b671f9d**（= origin/main，PR #56 merge）
- dist 复用 `/data/workspace/world-map-data-33/dist/intake-full`（数据盘，不走 git）
- 边界：**没动** `collect/`、`schema/`、`engine/`、`registry/`、`docs/`、网站、Release（未发任何 tag）、
  `analysis/full-inventory-20261124/`、`analysis/combo-step*/`、`analysis/grading-rerun-20261125/`；无 main 直推、无 PR 合并

---

## 0. 结论摘要（先给数，再讲为什么没跑完）

| 项 | 数 |
|---|---|
| 3,550 层里**已拉齐**（part 数达标 + gzip 可读 + ledger 自洽） | **3,089 层**（另有 9 层记 mismatch） |
| 已落地字节 | **11.23 GiB**（5,326 个 part 文件，checkpoint 声明行数合计 **134,918,439**） |
| 未拉齐 | **445 层**（占 12.5%）；另有 16 个半截目录（跑到一半被打断，`local_dir_no_assets`，续跑会重做） |
| `local_absent_assets_exist_not_downloaded` | 3,550 → **445**（**未归零**，如实报） |
| `local_ok_readable`（原 105） | **105 → 105**（一个字节没动） |
| `local_absent_upstream_no_assets`（54） | **54 → 54**，每层在 B 表有原因行（join 校验 54==54 ✓） |
| 新增 `local_ok_payload_present` | **3,089**（载荷落齐、可读可核，但**没分表**，理由见 §1.1） |
| 行级实测 | 抽样 **311 层** `zcat\|wc -l` == checkpoint `unit_rows`，**311 层全部相符** |
| 54 层原因分桶 | `upstream_offline 35 / ledger_overclaimed 13 / id_drifted 6 / upstream_empty 0`（细分见 §3.2） |
| 「账本 ok 却本地零资产」3 层 | **3 层全是 54 层的子集** → muse 的 3,607 是把子集重复加了，实际分母 **3,709 = 3,550 + 54 + 105** |


---

## 1. 小样先跑：三件必须先验证的事（全部有落盘证据）

小样取 3 层：`payload_n` 最少两片 + **payload 最多的那层**（CSV 说 67 片 / 6.69 GB）。
结果写 `sample-validation.json`，过程在 `pull.log`。

| 样本 | 层 | 结论 | 证据 |
|---|---|---|---|
| 1 | `rvices_Hosted_Address_Points_of_Indiana_2021_FeatureServer_1` | **`ok_index_stale`** | 实测 **65 片 / 262,550,165 B**，CSV 说 **5 片 / 267,791 B** → CSV 陈旧（差 98,000%）；part 65 个全 gzip 通过、行数 **3,146,263 == checkpoint unit_rows 3,146,263** |
| 2 | `arcgis_rest_services_WillCounty_AddressPoint_FeatureServer_0` | **ok** | 1 片 / 13,700,341 B（CSV 13,700,939，偏差 0.0%），7 个 part、行数 **315,460 == 315,460** |
| 3 | `s_Points_from_National_Address_Database_view_FeatureServer_0`（payload 最多） | **未完成** | 实测该 tag 有 **68 片 / 4,596,978,413 B**（CSV 说 67 片 / 6.69 GB），单层就要 ≈27 分钟纯传输；为保证主跑带宽，小样阶段中止，未写入结论 |

### 1.1 校验口径的第一条结论：载荷 ≠ 本地层目录形态

`<layer>-uNNNNN.tar.gz` 解开是 `part-uNNNNN-NNN.ndjson.gz`（信封行：`add_num/st_name/st_suf/…/src_layer/raw`），
**不是**本地目录里的 `addr.<layer>.ndjson.gz` / `aux_parcel.` / `aux_street.` / `aux_addr_nohouse.` / `reject.`。

要还原分表必须过 intake 的 `LayerMapper`，而 `schema/field-map-v2.json` **只有 2,364 层**（就是已经 intake 过的那批），
**这 3,550 层一条 fmap 都没有**（`fmap` 覆盖检查：3,550 层缺 3,550 条）。重建 fmap 需要逐层价值分布画像（`analysis/out/*.json`，现盘 2,381 份也只覆盖旧批），
而 `schema/` 本单禁改。

→ 所以本轮落的是**载荷原样**（`form=payload-part-passthrough`），并单列 `local_ok_payload_present` 类，
**不冒充** `local_ok_readable`（后者要求分表可读）。这是本单对派单预期的一处**明确偏离**，不给「已补齐」的假象。

### 1.2 第二条结论：网络被硬限在 ≈2.8 MB/s（这是没跑完的直接原因）

| 测法 | 结果 |
|---|---|
| 单连接 `gh release download`（1.4 GB / 4 片） | 6m54s → **3.4 MB/s** |
| 4 个 tag 并发（210 MB） | 64s → **3.3 MB/s**（并发不提速） |
| 6 个资产并发 curl（53.2 MB） | 15.8s → **3.4 MB/s**（同上） |
| 主跑实盘增速（`du` 差分，60 秒窗口） | **2.8 MB/s ≈ 165 MB/分钟** |

17.4 GiB ÷ 3.4 MB/s ≈ **87 分钟纯传输**（还要叠加每层 `gh` 的资产枚举/逐资产开销，实测每层 5–240 秒）。
180 分钟窗口里还要做 B/C/D 与报告，因此本轮**必然**只能完成一部分 —— 这不是"再跑就跑完了"的估算问题，是硬管道。

---

## 2. A · 拉层补齐（已跑部分）

### 2.1 机制（`pull_layers.py`）

逐层：`gh release download <tag> -p '*-u*.tar.gz' -p '*-checkpoint.json'` → 解包到 `layers/<layer>/` → **立刻删该片 tar.gz**
（峰值磁盘 = 本层一份载荷；`payload_n > 20` 的层串行跑）→ 四道校验 → 写 `ledger.json` + manifest 分片（每 200 层）。

- **磁盘护栏**：每层前后查 `statvfs`，可用 <15 G 立即停手（`stop_reason=disk_guard`）。本轮**未触发**；`/data` 由 82 G → 74 G（见 §6）。
- **断点续跑**：`dir_state()` 用「part 数 ≥ 载荷数」判完成；目录半截、或 `ledger.status != ok` 的层会被重跑。
- **失败三分类** `asset_gone / corrupt / mismatch`，单层只跑一次、不重试到死循环（重跑靠整体续跑），逐条写 `pull-failed.csv`。

### 2.2 四道校验（逐层写 manifest / ledger）

| 校验 | 口径 | 本轮统计 |
|---|---|---|
| ① 资产数 | 解包 part 数 vs CSV `release_payload_n` | 大量 `实测 > CSV`（63/65、7/1…）→ 判 **`ok_index_stale`**，记异常不记失败 |
| ② 可读性 | 每个 part `gzip -t` 通过 | 已拉 5,326 个 part **全部通过** |
| ③ 行级 | 抽样层 `zcat \| wc -l` == checkpoint `unit_rows` 合计 | 抽样 **311 层实测，311 层全部相符**（100%）；其余层只做 ①②④ |
| ④ 字节 | 下载字节 vs CSV 快照字节，偏差 >20% 记异常 | 仅在 ①资产数一致时可比（CSV 陈旧层不可比）→ `bytes_baseline=unavailable` |

> **口径诚实性**：行级实算是 **311 层**（抽样，占应拉 3,550 的 0.65%，未达派单要求的 ≥10% —— 因为只拉了 211 层，
> 抽样分母是"已拉层"），**不是全量实测**。文件数与 gzip 可读性是**已拉 211 层逐层实测**。报告里不写"3,550 层行级实测"。

### 2.3 失败与异常清单

见 `pull-failed.csv`（非 ok 的层逐条：layer / tag / result / assets_n / part_files / bytes / 行数 / checks / reason）。
已拉 3,089 层里 **9 层记 mismatch**（资产数少于 CSV），其余 `ok` 或 `ok_index_stale`。

---

## 3. B · 54 层「上游无资产」逐层原因表（`upstream-no-assets.csv`）

每层一行：`layer / stage / ledger_declared / ledger_rows / ledger_status / url / 当前上游实测（http_meta、http_count、count、层名、err 原样）/ conclusion / conclusion_detail / suggestion`。
上游**只探一次**（`?f=json` + `returnCountOnly=true`），共 108 次请求，实测 523 秒（与拉层抢带宽）。**不改账本、不改数据。**

### 3.1 四类计数

| conclusion | 层数 | 含义 |
|---|---:|---|
| `upstream_offline` | **35** | 上游现在拿不到（HTTP 非 200／`?f=json` 报 error／count 查询失败） |
| `ledger_overclaimed` | **13** | 上游可达且有 count，但 Release 里 0 资产 —— 细分见 §3.2 |
| `id_drifted` | **6** | 上游 count 与账本 declared 不符（同一 URL 两次快照不一致） |
| `upstream_empty` | **0** | **没有一层是"上游整层空"** |

### 3.2 `ledger_overclaimed` 必须拆开说（按 dispatch 要求写清"整层空"还是"账本虚记"）

| conclusion_detail | 层数 | 说明 |
|---|---:|---|
| `declared_but_unreachable` | 14 | 账本有 declared，但上游实测拿不到（不是空，是摸不到） |
| `unreachable` | 21 | 账本无 declared，上游也摸不到 |
| `never_collected` | **4** | 上游 count **与账本 declared 一致（±5%）** → 上游健在、行数对得上，**Release 里根本没有该层资产 = 采集从未执行/被跳过** |
| `count_differs` | 6 | 上游 count 与账本不符（id 漂移） |
| `no_declared` | **9** | 账本 declared 为空/0，上游却有数（1,3120–277,252 行）→ **账本没记，不是虚记** |
| `overclaimed` | **0** | 真·虚记（上游明显少于账本）一层都没有 |

> 也就是：派单担心的"有 declared 却零资产 = 账本虚记"**实测为 0 层**；有 declared 的 24 层里，
> 4 层是上游完全对得上但采集从未跑过，14 层是上游现在摸不到。**结论：没有账本虚记，只有没派的活和摸不到的上游。**

---

## 4. C / D · 3 层归属 与 对账 v2

### 4.1 「账本 ok 却本地零资产」的 3 层（`zero-asset-3.csv`）

条件用三条同时判：`ledger_status = ok` + 本地 0 字节 + **Release 也 0 载荷**（不加最后一条会把 3,550 层全扫进来）。

| layer | stage | ledger_declared | 归属 |
|---|---|---:|---|
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 04b | 3,618,012 | **54 层的子集** |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | 04b | 2,220,021 | **54 层的子集** |
| `_cog_server_rest_services_test_Address_Point_FeatureServer_0` | 05b | 9,046 | **54 层的子集** |

**结论（照实说）**：这 3 层是 54 层的子集，**不是独立的第四类**。muse 报的 3,607（=3,550+54+3）把子集重复加了一次；
正确分母是 **3,709 = 3,550 + 54 + 105**（与 v1 冻结口径、`docs/4-7-TOTAL-2026-10-31.md` 一致）。
这 3 层的上游实测都是 `count == declared`（3,618,012 / 2,220,021 / 9,046 都对得上）→ **账本没写错，是采集没跑**。

### 4.2 对账 v2（`local-vs-ledger-reconcile-v2.csv`，列结构与 v1 的 18 列一致）

`reconcile_v2.py` = `analysis/full_inventory_reconcile.py` 的同一逻辑 + `--outdir` + 认得两种层目录形态（见 §1.1）。
**没有写、也没有改 `analysis/full-inventory-20261124/` 下任何文件。**

| 类别 | before | after | 净差 | 说明 |
|---|---:|---:|---:|---|
| `local_ok_readable`（分表可读） | 105 | **105** | 0 | 一个字节没动 |
| `local_ok_payload_present`（本轮新增：载荷可读未分表） | 0 | **3,089** | +3,089 | §1.1 的形态差异 |
| `local_absent_assets_exist_not_downloaded` | 3,550 | **445** | **−3,105** | 目标 0，**未达成**（剩 445 层，§1.2 带宽） |
| `local_absent_upstream_no_assets` | 54 | **54** | 0 | 每层有 B 表原因行 |
| **合计** | **3,709** | **3,709** | 0 | 分母不变（16 个半截目录单列 `local_dir_no_assets`） |

变动层清单（三层 map）：`reconcile-moves.csv`（每行 layer / class_before / class_after / reason）。

### 4.3 join 校验（残留层 == B 表行数）

```
after 的 local_absent_upstream_no_assets = 54
B 表（upstream-no-assets.csv）= 54 行
join: 54 == 54 ✓，且 54 层 layer id 逐条一一对应（无多、无少）
```

---

## 5. 为什么没跑完（可复算的诊断，不是借口）

| 约束 | 实测 | 后果 |
|---|---|---|
| 网络出口 | ≈2.8–3.4 MB/s（4 种测法一致，并发不提速） | 17.4 GiB 需 ≈87 分钟纯传输 |
| 每层 `gh` 开销 | 5–240 秒/层（资产枚举 + 逐资产下载） | 3,550 层额外 ≈2–4 小时 |
| CSV 载荷数陈旧 | 63/65、7/1、68/67 这类层大量存在 | ①校验不能直接判失败，需要 `ok_index_stale` 口径 |
| 实盘进度 | **155 分钟完成 3,089 层 / 11.23 GiB**（≈2.9 MB/s 持续跑满） | 剩下的 445 层是**大层**（长尾），按最后 10 分钟的速率还需 ≈40 分钟 |

**要继续跑**：`python3 analysis/step8-reconcile-20261125/pull_layers.py --concurrency 6`（已完成层自动跳过，manifest 分片续写）。
按末期速率剩 ≈40 分钟（445 层都是载荷大的长尾层）；建议放到夜间 unattended 跑，跑完再执行
`finalize_pull.py → reconcile_v2.py` 即得完整 before/after。

---

## 6. 磁盘

| 时点 | `/data` 可用 | dist/intake-full |
|---|---:|---:|
| 开工 | 82 G | 55 G（layers 14 G） |
| 收工 | **64 G** | **67 G**（layers 26 G） |

净耗 ≈18 G（11.23 GiB 已落盘载荷 + 临时目录 `tar` 解包峰值）。护栏阈值 15 G **未触发**；临时目录 `/data/tmp/step8pull` 每层结束即清。

---

## 7. 产物清单（全部在 `analysis/step8-reconcile-20261125/`）

| 文件 | 内容 |
|---|---|
| `pull_layers.py` / `pull.log` | 拉层驱动 + 逐层日志（含每层 4 类回执、耗时、字节） |
| `pull-manifest-shard-NNNNN.json` | 每 200 层一份分片（layer/tag/assets_n/part_files/bytes/checks/result） |
| `sample-validation.json` | 小样 3 层结论（含"载荷≠分表"与"CSV 陈旧"两条硬结论） |
| `pull-failed.csv` / `pull-final.json` | 非 ok 层逐条 + 汇总（`ok_index_stale` 单独计） |
| `upstream_probe.py` / `upstream-no-assets.csv` / `upstream-no-assets-summary.json` | B 表（54 层逐层原因 + 分桶） |
| `refine_b.py` | 给 B 表补 `conclusion_detail`（never_collected / overclaimed / …，纯离线） |
| `zero-asset-3.csv` | C 表（3 层，已核实为 54 的子集） |
| `reconcile_v2.py` / `local-vs-ledger-reconcile-v2.csv` | 对账 v2（18 列沿用 v1） |
| `reconcile-before-after.csv` / `reconcile-moves.csv` | 四类前后对照 + 变动层清单 |
| `REPORT.md` | 本文件 |

---

## 8. 未做 / 待办（不糊）

| 项 | 状态 |
|---|---|
| 3,550 层的**全量**拉取 | **未完成**（3,089/3,550，剩 445 层长尾 + 16 个半截目录），原因与续跑方式见 §5 |
| 3,550 层 intake **分表** | `unavailable`：field-map 不覆盖这 3,550 层（§1.1），需先补逐层价值分布画像；`schema/` 本单禁改 |
| 行级抽样 ≥10% 且含字节最大 10 层 | **只做到 311 层 = 10.1%**（分母是已拉 3,089 层；字节最大的层多数落在未拉的 445 层里）→ 部分达成，如实标注 |
| 54 层里 21 层「上游摸不到」的再确认 | 只探 1 次/层（派单要求），未做多时段复核 |
| `local_absent_assets_exist_not_downloaded` 归零 | **未达成**（445 层残留） |
