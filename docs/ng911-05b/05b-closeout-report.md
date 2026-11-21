# 05b 收尾报告（reprobe 终态并入后的账本口径快照）

- 报告时刻：2026-11-21（快照口径见下方 provenance）
- 阶段：05b（县市碎片全量补采，583 层）
- 本报告性质：**只是口径快照**，不改写、不替换 gap list v2（见第三节）。派单依据仍是
  [`collect/ledger/05b_gap_list.json`](../../collect/ledger/05b_gap_list.json) +
  [`docs/ng911-05b/05b-gap-list.md`](./05b-gap-list.md)。
- 算式对账与逐层明细见 [`05b-reprobe-reconcile.md`](./05b-reprobe-reconcile.md)；reprobe 过程见 [`05b-reprobe.md`](./05b-reprobe.md)。

---

## 一、主口径（唯一对外数字）

**reprobe 终态并进后的快照**（六类互斥，合计恒等于 583）：

| 类 | 层数 |
|---|---|
| ok | 1 |
| partial | 6 |
| missing | **518** |
| unverified | **21** |
| pending | **37** |
| 合计 | **583** |

> 表下标注：**「reprobe 终态并进后的快照」= gap list v2（583 层）+ reprobe 60 目标的终态判定**，
> 不是 gap list v2 文件本身的内容（文件里仍是 missing 523 / unverified 18 / pending 35）。

### provenance（全部可机检）

| 项 | 值 | 来源 |
|---|---|---|
| reprobe 产物 | `collect/ledger/05b_plan_probe_reprobe.json` | `at=2026-11-21T07:46:52Z` |
| reprobe 规模 | records **60**（resume skipped 2 / new 58） | 同文件 `resume` |
| reprobe 耗时 / 并发 | elapsed **1295.2s** / workers **12** | 同文件 `elapsed_s` / `workers` |
| reprobe 判定 | verdict_counts **alive 2 / unverified 21 / pending 37** | 同文件 `verdict_counts` |
| 基线分类 | gap list v2：ok 1 / partial 6 / missing 523 / unverified 18 / pending 35（583 层） | `collect/ledger/05b_gap_list.json`，`at=2026-11-21T07:52:05Z` |
| 探针实现 | `collect/full_plan.py:_count_one`（未改） | 同文件 `probe_fn` |
| 口令/来源 | retry1 = `05b_plan_probe_retry.json`；url 取自 `layer_plan.csv` | 同文件 `url_source` |

复核命令（只读）：

```bash
python3 - <<'EOF'
import json
rp = json.load(open('collect/ledger/05b_plan_probe_reprobe.json'))
g  = json.load(open('collect/ledger/05b_gap_list.json'))
print(rp['at'], len(rp['records']), rp['elapsed_s'], rp['workers'], rp['resume'], rp['verdict_counts'])
print(g['at'], g['layers_n'], g['summary']['class_counts'])
EOF
```

---

## 二、并进算式（归属写对：这是集合运算，不是桶计数加减）

### 2.1 reprobe 的 60 个目标是谁

```
60 = gap list v2 的 unverified 18 + pending 35 + retry1-alive 7
```

7 层 **retry1-alive** 在 gap list v2 里的归属（按 `05b_gap_list.json` 逐层 `class` 实测）：

| retry1-alive 层 | gap list v2 归属 |
|---|---|
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | **partial** |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | **partial** |
| `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | missing |
| `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | missing |
| `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | missing |
| `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | missing |
| `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | missing |

即：**2 层在 partial、5 层在 missing**（不是「7 层都算在 pending 里」）。

### 2.2 reprobe 终态 x gap 类（交叉表，实测）

| reprobe 判定 \ gap v2 类 | unverified 18 | pending 35 | missing 5 | partial 2 | 小计 |
|---|---|---|---|---|---|
| unverified | 18 | 0 | **3** | 0 | 21 |
| pending | 0 | 35 | **2** | 0 | 37 |
| alive | 0 | 0 | 0 | **2** | 2 |
| 小计 | 18 | 35 | 5 | 2 | 60 |

### 2.3 由此得到主口径

| 桶 | 算式 | 结果 |
|---|---|---|
| unverified | 18 + 3（missing 里 3 层转 unverified） | **21** |
| pending | 35 + 2（missing 里 2 层转 pending） | **37** |
| missing | 523 − 3 − 2 = 523 − 5 | **518** |
| partial | 6（Georgina 两层仍 alive 但仍 partial，不加不减） | 6 |
| ok | 1（本批 60 目标里没有 ok → ok 的翻转） | 1 |
| 合计 | 1 + 6 + 518 + 21 + 37 | **583** |

**教训（写死，防复发）**：上一版（000137）得数碰巧对、**归属算反**（把 7 层 retry1-alive 当成
「全部进了 pending」）。本表是**集合运算结果**（谁在谁里面、从哪个桶搬到哪个桶），
不是桶计数加减；三个差额 −5 / +3 / +2 必须能各自指到具体层名（见 2.2 交叉表）。

---

## 三、gap list v2 不覆盖（本报告不改文件）

- 本报告**只是口径快照**，不改写、不替换 gap list v2。
- 派单依据仍是 `collect/ledger/05b_gap_list.json` + `docs/ng911-05b/05b-gap-list.md`（583 层）。
- 自证（**本报告这一笔提交**对这两条路径零改动；输出为空 + sha256 不变）：

```bash
git diff --stat d5a42af b5bc3c6 -- collect/ledger/05b_gap_list.json docs/ng911-05b/05b-gap-list.md
git show d5a42af:collect/ledger/05b_gap_list.json | sha256sum
git show b5bc3c6:collect/ledger/05b_gap_list.json | sha256sum
```

> 实测（2026-11-21）：`diff --stat` 输出为空；gap list json sha256 `8f7cd22e8bd7bf46…`、
> gap-list.md sha256 `8a8e814883c9e7c0…`，提交前后**同值**。
> 另：`collect/ledger/05b_gap_list.json` / `05b-gap-list.md` 上一次内容改动仍是
> `334ee91 recon(05b·段A)`；本次收尾报告只新增 `docs/ng911-05b/05b-closeout-report.md`。

> 现行 gap list v2 文件内容：`at 2026-11-21T07:52:05Z`、`layers_n 583`、
> `class_counts {ok:1, partial:6, missing:523, unverified:18, pending:35, no_expect:0}`——
> 与主口径的差别只在 518/21/37 这三格，且**只存在于本报告的文字里**。

---

## 四、两条判读（随主口径一起走）

### 4.1 `1010` = Cloudflare UA/浏览器签名拦截，不是层死

三层在本次 reprobe 里返 **HTTP 403 `error code: 1010`**（Cloudflare 的「浏览器签名/UA」拦截）：

| 层 | expect_live | 本次判定 | 处置 |
|---|---|---|---|
| `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | 72,868 | unverified | 记账正确，**单独立项收复** |
| `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | 34,683 | unverified | 同上 |
| `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | 72,868 | unverified | 同上 |

- 按 `unverified` 记是**对的**：证据只说明「我们被挡」，不说明「层没了」。
- 收复方式：换出口 / UA / Referer（或走浏览器签名），**不计入永久死层**，也不许当「已死」放弃。

### 4.2 Georgina alive ≠ 补齐

| 层 | rows | expect_live | 缺口 | 判定 |
|---|---|---|---|---|
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 20,567 | 23,241 | −11.50% | partial |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 20,570 | 23,246 | −11.51% | partial |

- reprobe 只拿到 **http 200**（1 try / ~1.1s），**count 未取到** → 无法证明补齐。
- rows 仍比 expect 少约 **11.5%**，**保持 partial**；禁止借 `alive` 转绿。

---

## 五、派单侧现状（只对齐，不改派单）

| 项 | 值 |
|---|---|
| 本轮 force_layers 条数 | **586 = gap list 583 + D15 三层** |
| D15 三层（账本 status=ok 但短采，只有进 force 才会被重采） | `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` 39,504/39,751（−0.62%）；`cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` 81,437/81,772（−0.41%）；`qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` 181,529/181,750（−0.12%） |
| run | **44884914552**，`plan` success，分片 **shards [200, 200, 186]** |
| 计划 artifact | `collect/ledger/05b_plan.json`（`layers_n 586`，提交 `ea41b97 collect: 05b 计划（run 44884914552）`） |

- **gap list 决定派哪些层；reprobe 只改账本口径，不拦派单**（reprobe 在 plan 之前跑完，
  派单仍是 583 + 3，不因 reprobe 结果增删层）。
- D15 的「本轮计划内层豁免」只看 preflight 收到的 `--force-layers`（PR #17，已合入 main），
  这三层在 force 名单里因此不触发 D15 报警——**豁免的是「派单前不许判死」，不是「记绿」**：
  本轮若没采到，收尾照 [六类口径](./05b-gap-list.md) 标 partial/unverified。

---

## 六、未决项

1. **`1010` 三层收复待派**：换出口/UA/Referer 重试（单独立项，不计入永久死层）。
2. **Georgina 两层 count 待取**：需拿到 `returnCountOnly` 才能判是否补齐（现为 http 200 无 count）。
3. **07b / 10b 未动**（停车线，等口令）。

---

## 附：本报告不含的动作（红线自证）

- 未改动 `collect/05b_ledger.json`、`collect/ledger/*.json`（含 gap list v2）；
- 未改动任何判据/容差（`ROWS_GAP_TOL` / `GAP_TOL`）、未改采集脚本与 workflow；
- 未起 run、未发 Release、未动 `main`（本报告走分支 + PR）。
