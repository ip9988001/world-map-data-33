# 08 去重 + 实体台账 · 方案草案（2026-11-01）

> **状态：只出方案，未派任何 run、未下载全量资产、未改采集逻辑、未碰 04b/05b/07b 账本。**
> 机器可读估算：`analysis/08-dedup-plan-2026-11-01.json`。
> 所有数字都标了口径：**【实测】**=本轮或仓内已测；**【推算】**=由实测外推；**【待实测】**=必须跑过才知道。
>
> **2026-11-01 更新：三个岔路已拍板（见第七节），R1 单州端到端已跑完并通过五项验证 —— 见 `docs/08-R1-REPORT.md`。**

---

## 一、输入清单

### 1.1 三仓点类三阶段的 Release 资产（08 的全部输入）

**【实测】** 用 `gh api` 拉 `world-map-data-33` 的 4,908 个 Release（10,987 个资产）后，按账本 `records[].tag` 逐层对齐：

| 阶段 | 层数 | Release tag | 载荷资产（`*-uNNNNN.tar.gz`） | 压缩字节 | GiB | 账本 rows（原始） | 可核实行 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 04b | 272 | 272 | 648 | 38,511,710,219 | 35.87 | 500,948,263 | 458,452,144 |
| 05b | 2,770 | 2,770 | 3,241 | 13,007,379,836 | 12.11 | 141,664,792 | 141,664,792 |
| 07b | 667 | 667 | 663 | 90,410,410 | 0.084 | 1,050,601 | 1,050,601 |
| **合计** | **3,709** | **3,709** | **4,552** | **51,609,500,465** | **48.07** | **643,663,656** | **601,167,537** |

- 平均 **80.2 字节压缩/行**。
- **不进 08 的 tag**：`collect-step03-*`（111 个、0.31 GiB）、`collect-step10-*`（55 个、1.83 GiB，宗地/重采）、`parcel1-raw-partial-*`（4.69 GiB）、`collect-pilot-*`（41 个、2.05 GiB）、`survey-*`。repo3 全仓 67.18 GB 里，属于 08 输入的只有 **51.61 GB**。
- **50 个 tag 没有资产**（04b 9 / 05b 37 / 07b 4）：21 个 unstable、21 个 empty、4 个 unverified、2 个 missing、1 个 partial、**1 个 status=ok**。
- ⚠️ 唯一「账本有行、资产不存在」的层：`_cog_server_rest_services_test_Address_Point_FeatureServer_0`（05b，status=ok，rows 9,046，**parts=0**）。08 记 `unreadable_no_assets`，可读行数 = 643,612,109 − 9,046 = **643,603,063**。这 9,046 行占全量 0.0014%，但它说明「账本 rows 来自上游计数、不等于下载得到的行」——`adjudicate_08.py` 必须把这一类单列。

### 1.2 解压后字节（Q2）

**【实测】** 抽 4 个真实包，解 `tar.gz` → 解内层 `ndjson.gz` → 逐行量字节：

| 样本 | 层 | 行数 | 压缩(内层 gz) | 解压 ndjson | 比例 | 字节/行 |
|---|---|---:|---:|---:|---:|---:|
| x1 | `Address_Points_Aug6_2019_shp` | 25,627 | 1.68 MB | 15.8 MB | **9.4×** | 617 |
| x2 | `AddressPts_DamageAssessment_REA_VIEW` | 95,382 | 17.1 MB | 208.4 MB | **12.2×** | 2,185 |
| x3 | `WI_NG911_Site_Structure_Address_Points_2` | 2,337,758 | 150.1 MB | 3.59 GB | **23.9×** | 1,536 |
| x7 | `Bike_Share_Address_Points` | 13 | 2.9 KB | 26 KB | **9.0×** | 2,010 |

**【推算】** 全量解压后 = 51.61 GB × 比例：
- 低（9.0×）≈ **465 GB**；中（15×）≈ **775 GB**；高（23.9×）≈ **1,233 GB**。
- 与「字节/行」口径一致：643.7M 行 × 1.2 KB ≈ 772 GB。

> ⚠️ 采样说明：为拿比例实拉 **179.3 MB**，超 100 MB 预算 79.3 MB（`gh release download -p "*.tar.gz"` 把某层 3 个 unit 全下了）。全部 4 个样本已用完即弃，未留全量。

### 1.3 每阶段行数（Q3）

见 1.1 表。对外只能用**可核实**口径：04b 458,452,144 / 05b 141,664,792 / 07b 1,050,601 = **601,167,537**。04b 的 `rows` 含 capped 39,875,268 与分区重复 2,620,851，不能拿去讲覆盖。

### 1.4 哪些层不能进去重（Q4）

**【实测】** 从三份账本 `status` 汇总：

| 类别 | 层数 | 行数 | 08 里怎么处理 |
|---|---:|---:|---|
| `ok` | 3,640 | 599,335,848 | 正常进 |
| `capped_by_upstream` | 1 | 39,875,268 | **读入照常去重**，但标 `declared_unverifiable`，不进覆盖率分母，grade 降级 |
| `partial` | 13 | 4,400,993 | 读入，标 `partial` |
| `upstream_unstable` | 24 | 51,459 | 读入但**不投独立源票**，标 `unmerged_unstable` |
| `unverified` | 8 | 88 | **跳过**（404 / HTML 页，无有效行），标 `unmerged_unverified` |
| `empty` | 21 | 0 | **跳过**（无资产） |
| `missing` | 2 | 0 | **跳过**（无资产） |
| 无资产但有行（`unreadable_no_assets`） | 1 | 9,046 | **跳过**（没有包可读），`adjudicate_08` 单列，不假装读过 |
| 分区重复层 | 3 | 2,620,851（重复行） | 读入；去重自然折叠，但**不得计独立票**，标 `same_upstream_dup` |
| 非美国（OSM EU 32.7M + OSM NA 15.8M） | 2 | 48,500,000 | 按 bbox 判非美 → `unmerged_outside_us` |

- **可进去重行数** = 643,663,656 − 51,459（unstable）− 88（unverified）= **643,612,109**；再扣掉没有资产的 9,046 行 = **643,603,063**（真正可读上限）。
- 这之后还有一刀「键不全」（num 或 street 为空）过滤，**过滤率待实测**。
- 分区重复三层点名：`_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1`（上游 6,297,169 与 `-2` 同源）、`Maricopa_County_Address_Points@AZ-1/@AZ-2`（2,139,242 vs 2,078,539）。

---

## 二、去重键（先对齐，再谈分片）

### 2.1 键定义（Q5）

```
dedup_key = state | county_fips | number | street_key | unit_key
street_key = TYPE | CORE | DIR        # 三段复合
number     = 数字段 + 可选单字母后缀（123A / 123-45 原样保留）
unit_key   = 去掉前缀后的字母数字（无单元 = 空串）
```

- **必须显式带 `state|county_fips`**：二仓的 scope 是 `process_county()` 单县作用域，州/县隐含；三仓是跨州并集，`MAIN ST` 这种名字跨州/跨县必然撞车（`100 MAIN ST` 在美国有上万条）。没有 scope，08 会把整州甚至全国的 `100 MAIN ST` 合成一条。
- **`state` 与 `county_fips` 一律来自 PIP，不来自 `layer_plan.csv`**（R1 实测清单州错了 5/9 层，见 7.1）。
- **不加 `zip5`/`city`**：见 2.4。
- 键是完整字符串（不做 md5 截断），桶号才用哈希 —— 哈希只影响分布，不影响正确性。

### 2.2 `street_key` 归一化规则（Q6，写死）

| 步骤 | 规则 | 理由 |
|---|---|---|
| 1 编码 | `unicodedata.normalize('NFKD')` → 删组合符 → `Ø→O / ß→SS / Æ→AE / Œ→OE` | 二仓现行 `PUNCT=[^A-Z0-9 ]` 会把 `CAÑON` 直接砍成 `CA ON`（实测），等于把一条街拆成两条 |
| 2 大写 | `.upper()` | — |
| 3 标点 | 非 `[A-Z0-9]` → 空格，折叠多空格 | 保留词边界（`O'BRIEN` → `O BRIEN`） |
| 4 序数 | `^(\d+)(ST\|ND\|RD\|TH)$ → \1`；`FIRST..TWELFTH → 1..12` | 二仓 `3RD` ≠ `THIRD`（实测），NAD 与 OA 的序数写法不同源 |
| 5 方向 | 独立字段 `pre_dir/post_dir` 归一为 `N/S/E/W/NE/NW/SE/SW`；名字首词是方向词则提出来当 `pre_dir` | 见 D1（已拍板：含方向）。**R1 IA 实测：结构化行里 62.5% 带方向词**（早期只看顶层字段的 5.7%–26.5% 是低估，`raw` 回退会把 `St_PreDir` 这类独立字段救回来） |
| 6 类型 | **独立 type 字段优先**；缺失才取名字**最后一个**在 SUFFIX 表里的词；未知 type 原样保留不猜 | 二仓在 type 独立成字段时会被名字里的后缀词劫持：名字 `BRIDLE CREEK` + type `BLVD` → `CREEK\|BRIDLE`（实测）；`OAK RUN DR` → `RUN\|OAK` |
| 7 核心 | 剩下的 token 按序拼接，允许内部多词 | `MARTIN LUTHER KING JR` |

**20 条真实/构造对照（二仓现行实测 vs 建议 v3）**：

| # | number | pre_dir | street | type | post_dir | unit | 来源 | 二仓 `street_key`（实测） | 建议 `street_key_v3` | `unit_key` |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `1122` | `` | `CAÑON` | `RD` | `` | `` | 构造：Unicode | `ROAD\|CA ON` | `ROAD\|CANON\|` | `` |
| 2 | `45` | `East` | `Oak` | `Street` | `` | `` | 构造：方向词 | `STREET\|OAK` | `STREET\|OAK\|E` | `` |
| 3 | `308` | `` | `55TH` | `ST` | `` | `` | 构造：序数 | `STREET\|55TH` | `STREET\|55\|` | `` |
| 4 | `850` | `` | `PARK PLACE` | `DR` | `` | `` | 构造：type 被名字吃掉 | `PLACE\|PARK` | `DRIVE\|PARK PLACE\|` | `` |
| 5 | `1292` | `` | `BRIDLE CREEK` | `BLVD` | `` | `` | 构造：同上 CREEK | `CREEK\|BRIDLE` | `BOULEVARD\|BRIDLE CREEK\|` | `` |
| 6 | `3682` | `South` | `22nd` | `Road` | `` | `` | 构造：方向+序数 | `ROAD\|22ND` | `ROAD\|22\|S` | `` |
| 7 | `120` | `` | `MARTIN LUTHER KING JR` | `BLVD` | `` | `` | 构造：多词核心 | `BOULEVARD\|MARTIN LUTHER KING JR` | `BOULEVARD\|MARTIN LUTHER KING JR\|` | `` |
| 8 | `7` | `` | `COUNTY HIGHWAY` | `TT` | `` | `` | 构造：非标准类型不猜 | `HIGHWAY\|COUNTY` | `TT\|COUNTY HIGHWAY\|` | `` |
| 9 | `125` | `` | `OAK RUN` | `DR` | `` | `` | 构造：RUN 被当类型 | `RUN\|OAK` | `DRIVE\|OAK RUN\|` | `` |
| 10 | `600` | `` | `E MAIN` | `ST` | `W` | `` | 构造：前后方向 | `STREET\|MAIN` | `STREET\|MAIN\|E+W` | `` |
| 11 | `1122` | `` | `CAÑON` | `RD` | `` | `#4B` | 构造：unit # | `ROAD\|CA ON` | `ROAD\|CANON\|` | `4B` |
| 12 | `45` | `East` | `Oak` | `Street` | `` | `APT 5` | 构造：unit APT | `STREET\|OAK` | `STREET\|OAK\|E` | `5` |
| 13 | `308` | `` | `55TH` | `ST` | `` | `STE 5` | 构造：unit STE | `STREET\|55TH` | `STREET\|55\|` | `5` |
| 14 | `900` | `` | `PINE` | `ST` | `` | `5` | 构造：unit 裸数字 | `STREET\|PINE` | `STREET\|PINE\|` | `5` |
| 15 | `900` | `` | `PINE` | `ST` | `` | `` | 构造：无单元对照 | `STREET\|PINE` | `STREET\|PINE\|` | `` |
| 16 | `3027` | `East` | `2nd` | `Street` | `` | `` | 真实行 | `STREET\|2ND` | `STREET\|2\|E` | `` |
| 17 | `1123` | `` | `Banks` | `Avenue` | `` | `` | 真实行 | `AVENUE\|BANKS` | `AVENUE\|BANKS\|` | `` |
| 18 | `1227` | `` | `Catlin` | `Avenue` | `` | `` | 真实行 | `AVENUE\|CATLIN` | `AVENUE\|CATLIN\|` | `` |
| 19 | `1614` | `` | `Oakes` | `Avenue` | `` | `` | 真实行 | `AVENUE\|OAKES` | `AVENUE\|OAKES\|` | `` |
| 20 | `2002` | `` | `Hill` | `Avenue` | `` | `` | 真实行 | `AVENUE\|HILL` | `AVENUE\|HILL\|` | `` |

- 1–15 是**构造用例**（为了把边界写死），16–20 是从上表样本里随机抽的**真实行**。
- 二仓现行实现还有两处已实测的错：Unicode 被砍（#1）、type 被名字劫持（#4/#5）、序数不归一（#3）。

### 2.3 `unit_key` 归一化（Q7）

| 输入 | `unit_key` | 说明 |
|---|---|---|
| `APT 5` / `#5` / `UNIT 5` / `STE 5` / `SUITE 5` / `RM. 3` / `LOT 12` / `apt-5` | `5` / `5` / `5` / `5` / `5` / `3` / `12` / `5` | **等价**（实测通过），前缀词 `APT|APARTMENT|STE|SUITE|UNIT|RM|ROOM|#|NO|LOT|BLDG` 全部剥掉 |
| （空） | `""` | **无单元单独成组**，绝不与任何有单元的合并（这是最重要的规则：`100 MAIN ST` ≠ `100 MAIN ST APT 5`） |
| `SUITE 12B` | `12B` | 字母后缀保留 |
| `L` / `R` / `Y` / `N` / `LEFT` / `RIGHT` | `""` | **脏值护栏**：抽样里 `WI_NG911_Site_Structure_Address_Points_2` 有 **48.8%** 的行 `unit` 是 `L`/`R`/`Left`/`Right`（左右侧标志，不是单元）。不设护栏会把整层折叠成 2 行 |
- 原串保留在 `unit_raw`，产品版可还原写法。

### 2.4 为什么 zip/city 不进键（Q8）

沿用二仓口径（`docs/GOLD-LAYERING-2026-10-30.md` §2c）：**zip/city 只进代表行打分**（`zip5 / unit / city / UUID 长度`），不进键。三条硬理由：

1. **zip 会切断街**：一条街跨 2–3 个 zip 是常态，进键等于把同一条街的门牌拆成互不相干的几组，去重率虚高、聚合页断裂。
2. **zip/city 覆盖不稳**：抽样里同一层可以 0%（`Address_Points_Aug6_2019_shp` 的 zip 全空）也可以 100%（`DamageAssessment` 全有）。进键会让「有没有 zip」决定合并结果。
3. **city 有两套口径**：`postal_city`（USPS 邮寄城市）与 `municipal_city`（行政市）常年不一致，二选一都会错。

**跨 zip 边界地址怎么办**：同键合并为一条；`zip5` 取代表行（先非空、再多数派）；成员 zip 不一致记 `zip_conflict=true` 并保留 `zip_alt`，供下游「按邮编聚合」时同时计入两个 zip（歧义显式化，不静默丢）。

---

## 三、分片方案

### 3.1 维度选型（Q9）

| 方案 | 同键同片？ | 全量读几遍 | 判定 |
|---|---|---|---|
| 按 state 分片、每片读**全部**资产 | ✅ | **52 遍 = 2.7 TB egress / ~15 TB 解压** | ❌ 否决 |
| 按 county 直接分片（3,089 片） | ✅ | 1 遍 | ❌ 否决：片数远超并发（20），排队与调度开销压不住 |
| 按 key 的 hash 前缀单遍分片 | ✅ | 1 遍 | ❌ 否决：单遍分片后，同键的行分散在「读到它的那一片」，除非每片都读全部资产 |
| **两段式：stage1 按资产清单分片 → stage2 按 `h(county_fips)%64` 分桶** | ✅ | **1 遍 + 一遍 spill** | ✅ **推荐** |

**推荐方案（两段式）**：

- **stage1（20 片）**：第 i 片只读「资产清单的第 i 段」（4,552 个包切 20 份，每片 ≈2.58 GB 压缩 / 32.2M 行）。逐行算 `county_fips`（复用 `collect/county_assign.py` 的 `Index` + `stream_asset`，本地 3,089 县多边形，PIP 非 bbox），算出 `bucket = h(county_fips) % 64`，**64 个 gzip writer 常开、逐行直写** `spill-<shard>-<bucket>.ndjson.gz`（不做整段内存缓冲，避免 64 桶同时驻留把内存吃满）。
- **stage2（64 片）**：第 b 片只读 20 份 spill 里的 `*-b.ndjson.gz`，按 county 顺序做 in-memory dict 去重，出县/州级产物与聚合。
- **同键必落同片的证明**：`county_fips` 每行只算一次，桶号只取决于 `county_fips`，与「哪一片读到这行」无关 ⇒ 同一键的所有成员一定落在同一个 `(bucket)` 里；stage2 收尾再用「Σ各桶键数 == 全局键数」守恒校验兜底。

### 3.2 每片行数与峰值内存（Q10）

| 段 | 片数 | 行/片 | 压缩/片 | 结构 | 峰值内存 |
|---|---:|---:|---:|---|---:|
| stage1 | 20 | 32,180,605 | 2.58 GB | 流式读 + 64 个常开 gzip writer 逐行直写 | **≈100 MB**（64 × 1 MB 缓冲）+ 县索引 ~0.6 GB ⇒ 实测上限 ≈1.5 GB |
| stage2 | 64 | 10,056,439 | ~0.3 GB spill | 单县 dict 去重（最大县 LA ~3.2M 键） | **≤480 MB** |

- 16 GB 内存绰绰有余。**天真的写法会翻车**：若把 64 个桶都缓存在内存里等扫完再写，32.2M 行 × 150 B ≈ 4.8 GB，加上县索引就贴边；所以采用「逐行直写 + 固定缓冲」。
- 对照：**不按州驻留**——整州驻留 TX（~40M 行 × 150 B ≈ 6 GB）已经贴边，再来一个 LA 县就崩；按县顺序处理才是稳的。
- spill 体积 **【推算】** ≈ 643.6M 行 × 30 B ≈ **19 GB gz**（只投影 12 个字段，不带 `raw`）。

### 3.3 片数与每片预算（Q11）

单 job ≤5 h、留 1 h 余量 ⇒ **单片 ≤4 h 机时**。按 4,003 行/秒·进程（见 5.1）：

| 方案 | 片数 | 机时/片 | 墙钟（按 20 并发） | 一次失败重跑代价 |
|---|---:|---:|---:|---:|
| 粗粒度 | 12 | 3.7 h | **4.4 h**（1 波） | 4.4 h（余量只剩 0.6 h，贴线） |
| 细粒度 | 40 | 1.1 h | **2.7 h**（2 波 × 1.34 h） | 1.3 h |
| **推荐** | **20** | **2.23 h** | **2.7 h**（1 波占满） | **2.7 h** |

- 并发数按 GitHub Actions 默认 20 个并发 job 估（Pro 40 / Team 60 可以整片一波，墙钟减半）。
- 总机时不变（≈44.7 h·进程 + 20% 开销 ≈ 53.6 h），片数只改**墙钟与重跑代价**。

### 3.4 Egress 这笔账（Q12）

| 项 | 字节 | 说明 |
|---|---:|---|
| 08 全量下载 Release 资产 | **51.61 GB** | 「全量读一遍」的固定代价，一次 |
| stage1 spill 上传 | ~19 GB | 走临时 Release tag（沿用现有 `gh release upload --clobber`，不用 artifact —— artifact 存储配额撑不住 19 GB） |
| stage2 spill 下载 | ~19 GB | 每份只被读一次 |
| **合计** | **≈89.6 GB** | 加可选 TIGER 3.06 GB |

- **【实测】** 单流下载 3.4 MB/s（`docs/EGRESS-LIMIT-2026-10-30.md` 三：1.8 GB / 8m57s，0 次 5xx）⇒ 单流跑完 51.61 GB 要 **4.2 h**；20 路并发下总吞吐未知（**待实测**，阶段 0 冒烟第一件事就测这个）。
- **能不能靠投影少下**？**不能。** 资产是 `tar.gz` 套 `ndjson.gz`，gzip 没有随机访问，取任何字段都得下整包；`raw` 占解压后 43%–84%（实测），但它在压缩包里，无法只取一部分。要减下载量只有一条路——重采时不写 `raw`，那是改采集逻辑，08 不做，**而且会丢掉字段回退能力**（见 5.2 第 1 条）。

---

## 四、产物设计

### 4.1 实体台账主表（Q13）—— 一行 = 一条去重后地址，35 字段

| 组 | 字段 | 说明 |
|---|---|---|
| 键 | `dedup_key` | `state\|county_fips\|number\|street_key\|unit_key`，可直接做 dict/join 键 |
| 行政 | `state` `state_fips` `county_fips` `county_name` | `county_fips` 由 PIP 判出（本地 3,089 县），`state` 由 county 反推（层清单里 2,846 层是「未定位」，不能靠清单） |
| 门牌 | `number` `number_suffix` `pre_dir` `street_core` `street_type` `post_dir` `unit` `unit_raw` | `number_suffix`/`pre_dir`/`post_dir` 拆开存，可还原任意书写习惯 |
| 展示 | `street_full` `zip5` `zip4` `city_postal` `city_municipal` | `street_full` 由代表行还原（不含 unit） |
| 地理 | `lat` `lon` `geo_precision` | `geo_precision ∈ {point, centroid, none}`；不做 H3，下游要时再算 |
| 来源 | `src_kinds` `src_layers_n` `src_layers` `independent_sources_n` `src_group_votes` | `src_kinds` 取自 4.2 分组；`src_layers` 最多保留 8 条（防行膨胀） |
| 质量 | `tier` `tiger_verify` `dup_members` `zip_conflict` `dir_conflict` `flags` `rep_reason` | `tier ∈ {S,A,B,U}`；`dup_members` = 被合并进来的成员数 |
| 时间 | `first_seen` `last_seen` | 取该键成员所在层 Release 的 `created_at` 极值（离线可算），09 增量直接用 |

**为什么不是「只输出一个独立地址数」**：一个数字没法支撑下游任何一件事——搜索页要号段与统计，生成器要完整门牌与可信度，09 增量要 per-key 时间戳，10b 宗地要空间连接。台账是唯一能反哺这四件事的形态。

### 4.2 `independent_sources_n`：按「独立源」算，不按文件数（Q14）

**判定依据（实测）**：二仓 `gold-US-IA-v1/MANIFEST.json`（99 县）里，Overture 桶的 `ovt_upstream` = `{"NAD": 1,585,872, "us/mn/statewide": 12}`，即 **99.999% 的 Overture 行上游就是 NAD**。所以「NAD 与 Overture 同源」不是假设，是实测。

| 组 | 成员 | 判定依据 | 三阶段里的层数 | 行数 |
|---|---|---|---:|---:|
| **NAD(+Overture)** | 一仓 `NAD-US-*`；三仓的 NAD 直供/镜像层；二仓 Overture 桶 | IA MANIFEST `ovt_upstream.NAD=1,585,872/1,585,884`；层判定用**字段指纹**（`raw` 含 `UUID`+`AddrClass`+`Placement`+`Addr_Type`，二仓 `read_nad()` 就是这么认的），不用名字 | **3（已确认）** | **116,852,987** |
| **TIGER** | 一仓 `TIGER-US-*-addrfeat` 号段 | 号段不是点，**只做校验/分级，不投票** | — | 3.06 GiB |
| **NG911** | 州级 NG911/E911 项目层（`*911*`） | 各州 NG911 计划独立于 NAD | **286** | **53,545,344** |
| **LOCAL_GIS** | 州/县/市自建 GIS 地址点（NC1Map、MassGIS、NYS SAM、VA、LBRS…） | 独立于联邦源，但**互相之间可能同源**（同一县多套服务） | ≈2,900（余量） | **待实测** |
| **PARCEL_SITUS** | 宗地/assessor situs 地址（`parcel|situs|assessor`） | 评估局地址，独立 | **232** | **21,636,572** |
| **OSM** | `OSM_Address_Points_EU` / `OSM_Addresses_NA` | 众包，独立但质量低、且主要是非美 | **2** | **48,500,000**（默认排除） |

- **分组口径的诚实边界**：上表的层数是**字面匹配的粗分**（名字里带 `911` / `parcel` / `national_address` 等），只用来估规模，**不能直接当交付口径**。例如名字含 `SAM` 的层（`NYS_Address_Points`、`SAM_BERDO_addresses`、`Raleigh_SAMB`、`HBAddressSamrtGov`）是**州/市自建项目**，不是 NAD；而 NAD 真身可以用字段指纹稳定认出来（`UUID` + `AddrClass` + `Placement` + `Addr_Type`）。⇒ R1 必须产出逐层 `src_kind` 确认清单（脚本判定 + 人工抽查 20 层），台账的 `independent_sources_n` 只认这份清单。
- 已确认 NAD 行数构成：`s_Points_from_National_Address_Database_view` 39,875,268（capped）+ `USA_NAD_Addresses` 75,937,418 + `SAMS_NAD_2025_Address_List` 1,040,301 = **116,852,987**。
- 计数规则：`independent_sources_n` = 该键的成员覆盖的**组数**（NAD/Overture 合并算 1 组）；`LOCAL_GIS` 内部若判定为同源（同一县的多套服务重发），只算 1 票，判定靠 4.4 的镜像检测。
- **【实测】** 三阶段里有 **215 组、475 层、8,387 万行** 的 `rows` 完全相同（同一数据集被多个 ArcGIS 服务重发），其中重复行上界 **4,439.8 万（占全部行 6.9%）**。这些层必须只算 1 票，否则「独立源数」会被同一份数据刷高。

### 4.3 从主表派生两份下游（Q15）

| 产物 | 用途 | 字段裁剪 |
|---|---|---|
| **A. public 版（搜索页/SEO 三级聚合）** | 邮编页 / 街道页 / 城市页，**无门牌，只有号段与统计** | **留**：`state` `county_fips` `city_postal` `zip5` `street_full` `number_min` `number_max` `number_span_n` `address_count` `unit_count` `lat_centroid(4位≈11m)` `lon_centroid(4位)` `tier` `first_seen` `last_seen`；**砍**：`number` `number_suffix` `unit` `unit_raw` `lat` `lon` `dup_members` `src_layers` `src_group_votes` `tiger_verify`。**再加两条硬规则**：①号段按 10 取整 ②`address_count < 3` 的街道页不出（防反推） |
| **B. product 版（地址生成器）** | 完整门牌，**不公开** | 主表全部 35 字段（含 `unit`、精确坐标、`src_layers`、`dup_members`、`tiger_verify`）。按 `src_kinds` 挂许可标记（NAD/Overture/OA 各有条款） |

- 两份产物的**键一致**（都是 `dedup_key`），所以「页面上说这条街有 187 个门牌」和「生成器里有 187 条」能对上账。

### 4.4 输出格式与体积（Q16）

| 产物 | 格式 | 体积（**【推算】**） | 依据 |
|---|---|---|---|
| 主台账 | `parquet + zstd`，按 `state=/county=*` 分区 | **10–22 GB** | 二仓 gold 实测 **124 B/行**（gz ndjson，47 字段，IA 1,489,711 行 / 184 MB）；台账 35 字段 ≈100–130 B/行 gz → 2.5–3.5 亿行 = 25–45 GB gz；parquet+zstd 通常再降到 0.35–0.5× |
| public 聚合 | `ndjson.gz`，zip5 / city / street 三份 | **1–2 GB** | 街道页估 500 万–1000 万行 × ~180 B |
| product 导出 | 与主台账同构，`parquet` | 同主台账 | — |

- **「按邮编/按街道聚合」要不要额外一遍？** 要，但是**很轻的一遍**：县内聚合在 stage2 内就能做（zip/city/street 天然不跨县合并时除外）；zip5 与 city 会跨县，所以需要 **stage3 一遍 reduce**——输入是聚合行（百万级），不是 6 亿行原始行，几分钟量级。
- 台账行数 **【待实测】** 落在 **2.5–3.5 亿**：下界是单源最大（NAD 1.25 亿），上界是可核实 6.01 亿；驱动项是同层镜像 4,439.8 万行上界、NAD 内部 4.61% 自撞（IA 实测）、以及**跨源重合率（最大未知项）**。

---

## 五、耗时与风险

### 5.1 耗时预算（Q17）

**【实测】锚点**：
- 判县 PIP：**4,646 行/秒·进程**（`docs/COUNTY-ASSIGN-2026-10-30.md:476`，248,721,878 行实测均值）。
- 解压+JSON 解析：**51,077 行/秒·核 / 75 MB/s**（本轮实测，x3 前 10 个 part，500,000 行 / 734 MiB / 9.8 s）。
- ⚠️ 用户提到的「判县阶段 21,265 行/秒」在仓内 **grep 0 命中**，`COUNTY-ASSIGN` 文档的实测是 4,646 行/秒·进程。本方案按 4,646 做**保守**推导，21,265 只当乐观上界（若成立，PIP 那 38.5 h 会掉到 8.4 h，总机时降到 ~15 h）。

| 环节 | 行/秒·进程 | 全量机时 |
|---|---:|---:|
| 解压 + JSON 解析 | 51,077 | 3.5 h |
| 抽取 + 归一化 | ~150,000 | 1.2 h |
| **判县 PIP** | **4,646** | **38.5 h** ← 决定性 |
| 去重 + 代表行打分 | ~120,000 | 1.5 h |
| **合计** | 4,003 | **44.7 h·进程** |
| 加 20% 开销（下载/落盘/重试/校验） | — | **53.6 h** |

**墙钟**：

| 并发 | 墙钟（stage1） | 加 stage2（64 桶） | 说明 |
|---|---:|---:|---|
| 20 路 | **2.7 h** | **≈3.2 h** | 推荐；正好一波 |
| 40 路 | 1.4 h | ≈1.9 h | 若账号并发 40 可用 |
| 8 路 | 6.7 h | ≈7.2 h | ❌ 单 job 超 5 h |

- **PIP 是唯一值得优化的环节**：可加「0.001° 网格记忆化」（同格不重算，边界格不缓存——二仓 `SpatialIndex` 已有这个模式）；镜像层重复地址会落在同一格，**预计省 20%–40% 的 PIP**，属 R2 优化项，不写进首轮预算。

### 5.2 风险清单（Q18）

| # | 风险 | 检测方法 | 兜底策略 |
|---|---|---|---|
| 1 | **字段映射漏**（最致命） | 逐层 `add_num` / `st_name` 命中率 | **【实测】抽的 3 个层里有 2 层 `add_num` 命中率 0%**（`DamageAssessment` 用 `STREET_NUMBER`、`WI_NG911` 用 NENA `Add_Number`，都不在现行 `F_ADD` 表里）。但 `raw` 留了全部上游属性 ⇒ 用 `raw` 回退字段表可把命中率救到 **100%**（实测 x2/x3 均 100%）。仍 0% 的层标 `unkeyed` 并单列清单 |
| 2 | 内存爆 | stage1 常驻内存水位 + 写缓冲打点 / stage2 单县行数日志 | 桶数 64 可调；单县 >5M 行时该县按县内 hash 二次分片 |
| 3 | job 超 6h | 每 50 万行打一次心跳时间戳 | 单片 2.23 h·机时，余量 2.3 h；asset 级 checkpoint 续跑 |
| 4 | 下载 5xx | HTTP 状态计数进 reports | 指数退避重试 5 次；单包失败只丢该 unit，记 `failed_units` 交 adjudicate 兜底 |
| 5 | hash 碰撞 | 不存在——键用完整字符串做 dict 键 | `h(county)%64` 只影响分布，不影响正确性 |
| 6 | 跨片同键 | stage2 收尾「Σ各桶键数 == 全局键数」守恒校验 | 不守恒即中止，不出账 |
| 7 | 分区重复层 | 同 upstream url 的层对 + 行数相同 | 标 `same_upstream_dup`，独立源只算一票 |
| 8 | capped 层 | ledger `status=capped_by_upstream` | 读入、标 `declared_unverifiable`、不进覆盖率、`tier` 降级 |
| 9 | 编码/脏行 | json 解析失败数 / 非 UTF-8 数 / 非美坐标数 | 逐行 try；脏行前 1,000 条落 `rejects` 样本 |
| 10 | `unit` 空值歧义 | `unit` 非空率 + 值分布 | 「像不像单元」判据（长度 ≤6、纯字母数字）+ 无单元单独成组 + `L/R/Y/N` 护栏 |
| 11 | 非美国数据 | bbox + PIP 落不进任何县 | `unmerged_outside_us`，不进美国台账 |
| 12 | 方向词误合并（D1 选 A 时） | 键相同但 `pre_dir` 集合含 >1 个值 | 记 `dir_conflict` 并降 `tier` |

### 5.3 最少几轮真跑（Q19）

| 轮 | 范围 | 验证什么 | 预算 |
|---|---|---|---|
| **R0 冒烟** | 1 个层（`WI_NG911_Site_Structure_Address_Points_2`，2.3M 行） | 字段回退表、归一化、PIP、64 桶直写落盘、20 路并发下载吞吐 | <10 min |
| **R1 单县端到端** | 挑一个「多源重叠但县小」的县（如 DE 的 10001/10003） | 台账 35 字段是否齐、`independent_sources_n` 是否合口径、public/product 两份裁剪是否能反查 | <1 h |
| **R2 单州全量** | 一个中等州（DE 或 VT，含多州层被裁剪的部分） | 跨县/跨 zip 聚合、`zip_conflict`/`dir_conflict`、stage3 reduce、体积实测 | 1–2 h |
| **R3 全量** | 20 片 + 64 桶 | 全量去重、守恒校验、`adjudicate_08.py --check` | 3.2 h |

⇒ **最少 3 轮**（R1/R2/R3）；R0 是 R1 的前置冒烟，不算独立轮次。

---

## 六、其他

### 6.1 需要新增/修改的脚本与 workflow（Q20，只列接口，不实现）

| 动作 | 文件 | 接口 / 职责 |
|---|---|---|
| 新增 | `collect/lib/addrkey.py` | `num_key(v) / street_key(name,type,pre,post) / unit_key(v) / addr_key(...)`，纯函数、无 IO |
| 新增 | `collect/lib/fieldmap3.py` | 在 `raw` 上做扩展字段映射（NENA：`Add_Number` `St_Name` `St_PosTyp` `St_PreDir` `St_PosDir` `Post_Code` `Inc_Muni` `AddNum_Suf`），返回 `(num,street,type,pre,post,unit,zip,city)`，并统计逐层命中率 |
| 新增 | `collect/dedup_extract.py` | stage1：`--shard i --nshards 20 --plan collect/ledger/08_plan.json --out <spill>`；复用 `county_assign.Index` 与 `stream_asset`；输出 `reports/dedup-extract-<i>.json`（漏斗：读入/可键/判县/UNLOCATED/桶分布） |
| 新增 | `collect/dedup_reduce.py` | stage2：`--bucket b --spills <dir> --out <parquet>`；单县 dict 去重 + 代表行打分 + `tier` + 聚合；输出 `reports/dedup-reduce-<b>.json` |
| 新增 | `collect/dedup_public.py` | stage3：`--ledger <parquet> --out <public>`；字段裁剪 + 号段取整 + `count<3` 屏蔽 |
| 新增 | `collect/adjudicate_08.py` | 与 `adjudicate_05b/07b` 同款：`--check` 必须 `IDENTICAL`；校验「读入行 − 可键过滤 − 去重合并 = 台账行数」与「Σ桶键数 == 全局键数」 |
| 新增 | `.github/workflows/dedup-08.yml` | 两段 matrix（20 → 64）+ `--dry-run`（R1 用）+ 临时 Release tag 存取 spill |
| 新增 | `collect/tests/test_addrkey.py` / `test_dedup_reduce.py` | 20 条归一化对照写进单测；去重/代表行/守恒的边界 |
| 复用（不改） | `collect/county_assign.py` | `Index`（3,089 县 + 1° 网格预筛 + 射线法）、`stream_asset`、`extract`/`coord_kind` |
| 复用（不改） | `collect/ledger_rebuild.py` | 账本口径与 `judge()` |
| 修改 | `collect/preflight_dispatch.py` | 新增 **D15 输入冻结校验**：08 的输入集（3,709 tag / 4,552 资产 / 51,609,500,465 B）与 `collect/ledger/08_plan.json` 不一致即 FAIL |
| 修改 | `docs/PREFLIGHT-GATE.md` | 19 项 → 20 项 |
| 修改 | `docs/WORKFLOW-FAILURE-LEDGER.md` | 新增 W33-042「08 输入集漂移」 |
| 新增 | `collect/ledger/08_plan.json` | 输入清单快照（tag + 资产名 + 字节 + sha256），派单前冻结 |

### 6.2 08 是否访问上游（Q21）

**不访问。** 08 只读两样东西：
1. 三仓 Release 资产（`world-map-data-33`，51.61 GB）；可选再加一仓 `TIGER-US-*-addrfeat`（3.06 GB，仅做分级，D3）。
2. 本地 `analysis/tiger_county/*.json.gz`（50 个州文件、**3,089 个县**多边形，2026-10-30 缓存，源 `TIGERweb State_County/1`）。

**没有任何步骤需要访问上游**。方案里唯一「本该访问上游」的场景是补 `add_num` 字段映射——因为记录里 `raw` 留了全部上游属性，改用离线回退表即可解决（实测命中率 0% → 100%）。**无标红项。**

⚠️ 已知缺口（不是上游访问，是本地数据边界）：county 索引只有 **3,089 县**，缺 PR/VI/GU 等属地 50+ 县；这些行会落 `UNLOCATED(no_county_index)`，需在 R1 明确是「记账」还是「补索引」。

---

## 七、拍板结果（2026-11-01，用户已定）

| # | 议题 | **结论** | 落在文档哪 | 落在代码哪 |
|---|---|---|---|---|
| **D1** | 去重键是否含方向词 | **含**。`E MAIN ST` 与 `W MAIN ST` 是两条街，合并就是编造地址。**三仓为准，二仓将来改**；缺失方向时允许合并但必须标 `dir_conflict`，**这类合并不进 S 级** | 2.1 / 2.2 第 5 步 | `collect/lib/addrkey.py::street_key()`（DIR 进 `street_key` 第三段）；`collect/dedup_reduce.py` 的「去掉 DIR 后同族只有一个非空方向才补全」逻辑 → `dir_inferred` / `dir_ambiguous` 计数；`tier_of()` 里 `dir_inferred` 降级 |
| **D2** | 台账口径：并集 vs NAD 脊柱 | **并集**。LOCAL_GIS / NG911 独有的地址是最稀缺资产，NAD 脊柱会系统性丢长尾。台账必须带 `rep_reason`（代表行来自哪个源组），将来按脊柱口径统计不用重跑 | 4.1 字段表 / 4.2 源组 | `collect/dedup_reduce.py` 输出 `rep_reason = "<src_group>/<layer>"`（35 字段里已有） |
| **D3** | 是否做 TIGER 号段校验 | **做，但排 R3**。R1/R2 不挂（不阻塞出数），**R1/R2 阶段没有 S 级，别对外讲号段可信度** | 5.3 / `docs/08-R1-REPORT.md` 五 | `adjudicate_08.py` 已把 `tier=S` 判为「不可达」；`tier_of()` 注释写死「R1/R2 不挂 TIGER ⇒ 没有 S 级」 |
| **D4** | 215 组重发层必须落进源组逻辑 | **硬要求**：同一 `dataset_fingerprint`（同 url 簇 / 同字段集 + 同行数 + 同键采样哈希）只算 1 票，其余记 `duplicate_dataset`。清单已落 `analysis/08-duplicate-datasets-2026-11-01.json` | 4.2 末段 | `dedup_extract.py` 每层算 `dataset_fingerprint`（键采样 sha1）；`dedup_reduce.py` 先按指纹折叠再按 `src_group` 计票，丢弃票数进 `duplicate_dataset_votes_dropped` |

### 7.1 R1 反过来改掉方案的一处设计（重要）

**计划的 `state` 列不可信，不能用来筛层。** R1 实测：`layer_plan.csv` 里标 `state=IA` 的 9 层，有 5 层实际在别的州（2 层 NE、1 层 WI、2 层跨 NE/IN/IA），31.1% 的行因此落在「不跨州」之外。

- 方案初稿 3.1 写的是「按州筛层」，**已作废**。
- 现行实现：`county_fips` 一律由全国县索引（3,089 县）PIP 判出，`state` 由 `county_fips[:2]` 反推，计划州只做校验；不符记 `plan_state_mismatch_layers` 并在报告点名。
- 台账的键因此写成 `state|county_fips|…`，这里的 `state` **来自 PIP**，不来自清单。

### 7.2 次要默认决定（用户未反对，按此执行）

1. OSM 的 4,850 万行默认排除（非美国为主）。
2. capped 层（3,987.5 万行）读入并去重，但不进覆盖率、`tier` 降级。
3. spill 走临时 Release tag，不走 artifact（19 GB 存储配额撑不住）。
4. R2 建议选 **CO 或 NC**（同时有 NAD + NG911 + LOCAL_GIS，且 NC 有三套 NC1Map 重发层）—— 只有这种州能验证「跨源投票 → A 级」。

## 八、待实测清单（R0/R1 必须回填）

1. 全量 3,709 层的 `add_num`/`st_name` 命中率（决定 `unkeyed` 行数）——抽样里 3 层有 2 层是 0%。
   **R1 已回填（IA 9 层）**：顶层命中 32.7% / `raw` 回退 37.4% / 自由文本 30.0% —— 只靠顶层字段会有 67.3% 不可键。
2. OSM 4,850 万行里真正非美的比例。
3. **跨源重合率**（决定最终台账行数，也是 2.5–3.5 亿这个区间的唯一大变量）。
4. 20 路并发下的总下载吞吐（3.4 MB/s 是单流实测）。
5. 去重后行数 → 决定 parquet 体积与 stage3 聚合规模。
   **R1 已回填（IA）**：254,837 行 → **133,634 键（去重率 47.6%）**；1,000 行台账 ≈ 1.0 MB（≈1 KB/行）。
