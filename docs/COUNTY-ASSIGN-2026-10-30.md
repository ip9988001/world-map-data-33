# county 逐行判定 · 实现与试算（2026-10-30）

> 本轮的边界：**只做「可启动」状态，不派大批量**。04b 还在跑（8 片 in_progress），
> 所以这里只跑已经对过账的 5 层做验收（30.1 万行全量读完，非抽样），
> 全量入口按分片写好了但没派发（`dry_run` 默认 1）。

## 一、实现（`collect/county_assign.py`）

| 能力 | 做法 |
|---|---|
| 数据源 | 只读三仓已发布资产（`gh release download` → tar.gz → ndjson.gz 流式解压） |
| 县界 | 优先一仓 `TIGER-US-<ST>-county-<fips>.geojson`，否则本地缓存 `analysis/tiger_county/<ST>.json.gz`；**不访问上游** |
| 判定 | 射线法 `pip()`，**bbox 只做预筛、绝不当结论**（已实证 GA 46% 顶点会落进邻县 bbox） |
| 无坐标行 | 计入 `no_coords` → 汇总进 **UNLOCATED**（`unlocated_total = no_coords + unlocated`） |
| 有坐标判不出 | 计入 `unlocated`，同样进 UNLOCATED（不猜、不拿 bbox 顶替） |
| 分片 | `--make-plan --size 40` 生成 `collect/ledger/county_plan.json`（跨县 + 有坐标 + 有门牌/街名）；`--plan --shard N` 单片执行 |
| 续跑 | 每层每单元一个 `collect/progress/county/<layer>/<asset>.done` 标记，重跑只补未完成单元 |
| 超时 | `--max-seconds` 单层软超时；workflow 侧 `timeout-minutes: 350` + `fail-fast: false` + `max-parallel: 8` |
| 入口 | `.github/workflows/county-fill.yml`（**已可启动，未派发**；`dry_run` 默认 `1`，默认派发只打印矩阵） |

计划规模：**858 层 / 22 片（40 层/片）/ 134,380,159 行**（其余 1,506 层是单县层或没有地址字段/坐标）。

## 二、5 层验收（30.1 万行全量）

| # | 层 | 行数 | 判出县 | 无坐标 | UNLOCATED | 参照 | 一致率 |
|---|---|---|---|---|---|---|---|
| 1 | `Gr3P_…ETJ_addresses_WFL1…_1`（TX 点层） | 25,081 | 25,081 | 0 | 0 | `COUNTY` 属性（上游归属） | **25,081/25,081 = 100%** |
| 2 | `8lct5k3LSbyO_…AddressULM…_1`（TX 点层） | 28,996 | 28,993 | 3 | 3 | 内部一致性（同城必同县） | 2 县 48121/48439，**计数闭合** |
| 3 | `7ABWQBGTG_…Hutto_Parcels…_0`（TX 宗地） | 23,591 | 0 | 23,591 | 23,591 | 无坐标层应 100% UNLOCATED | **100% UNLOCATED** ✓ |
| 4 | `cgis_…PacificTime…_17`（WA 宗地） | 211,139 | 0 | 211,139 | 211,139 | 同上 | **100% UNLOCATED** ✓ |
| 5 | `TIGER-US-GA-13151-addrfeat`（GA 线层） | 11,910 | 11,910 | 0 | 0 | 文件名即真值（Clayton 13151） | **11,910/11,910 = 100%** |

**可核对参照 36,991 行 → 一致 36,991 行（100.00%），硬冲突 0。**

### 两类「看似不一致」的实情（都判过，不是糊弄）

1. **ETJ 1 例县界点**：某行属性写 `TRAVIS`，多边形判 `WILLIAMSON`。抖动测试：±22m 仍是 Williamson，
   ±111m 就翻到 Travis → 该地址压在县界上（TIGER 县界 `maxAllowableOffset=0.0005`≈55m 简化 + 地址点 vs 宗地差）。
   规则：差异点抖动 ±0.001° 能落到参照县 → 记 `boundary`，不算硬冲突。
2. **addrfeat 31 段压线**：线段沿线取 5 点，全落邻县；再抖动 ±0.0015°(≈165m) 能回 Clayton →
   同属边界情形。按「沿线任一点 + 抖动命中即一致」处理。

## 三、吞吐与 ETA

实测（含下载 + 解压 + 判县，单进程）：**10,927 行/秒**（288,807 行 / 26.4 秒纯计算时间，
总耗时含下载约 65 秒，取 11.4 千行/秒量级）。

| 口径 | 行数 | 单进程 ETA | 8 片并发 ETA（含 IO ×1.3） |
|---|---|---|---|
| 全库 | 229,082,706 | **5.8 小时** | ≈ 0.95 小时 |
| 计划内（需逐行判县） | 134,380,159 | **3.4 小时** | ≈ 0.55 小时 |

真正的瓶颈是**数据搬运**：实测 75 字节/行 → 计划内约 **10 GB gzip** 要过一遍，
所以实现是「流式解压边读边判 + 按层并发」，不落中间文件；PiP 本身（每核 ~16k 点/秒）不是瓶颈。

## 四、为什么现在不派大批量

1. 04b 还在跑，Release 里的层会**重采/重建**（本轮实测撞到过：`collect-step05-<layer>` 在重采窗口里
   资产列表会短暂变化），此时判县会读到半截数据。
2. 计划里 858 层里有 1,176→858 层的筛选已排除「单县层」与「无门牌/街名层」，但仍有层在 04b 计划内，
   等它们跑完再判才有意义。
3. 派发方式（等边界放开后执行）：
   ```bash
   gh workflow run county-fill.yml -f dry_run=0 -f size=40      # 真跑
   gh workflow run county-fill.yml                              # 默认 dry_run=1，只打印矩阵
   ```

## 五、复现

```bash
/tmp/yv/bin/python collect/county_assign.py --selftest --out /tmp/county-st   # 5 层一致率（需 pyshp）
python3 collect/county_assign.py --make-plan --size 40 --plan collect/ledger/county_plan.json
python3 collect/county_assign.py --plan collect/ledger/county_plan.json --shard 0 --out dist/county
```

账本：`collect/ledger/county_selftest.json`（5 层逐条）、`collect/ledger/county_plan.json`（858 层 / 22 片）。
