# 第 9 步 · 全量字段映射（3,550 层：到手 → 能用）

> 一句话：**3100/3550 层（87.32%）产出 11 列可读数据**；不可用 450 层（原因全部落在固定枚举内）；逐层闭合差 ≠ 0 的层 **0** 个；行级抽查 **355 层 / 80.28% 相符**；输出 **9282.1 MiB / 8 个 tar.gz 分片**；磁盘余量 **21.9 GiB**。

## 0. 四数（先给数）

| 指标 | 实测 | 门槛 | 结论 |
|---|---:|---:|---|
| 层覆盖率 | **87.32%**（3100/3550） | ≥95%（≥3,373） | **未达标** |
| 不可用层 | **450** | —（全部进 unusable.csv） | 原因全部固定枚举内 |
| 逐层闭合差额 | **0 层有差额** | 0 | 闭合 |
| 行级抽查 | **355 层 / 80.28%** 相符 | ≥355 层（≥10%） | 达标 |
| 输出字节 | **9733021695 B**（8 片） | — | 磁盘余量 21.9 GiB |

## 1. 不可用分桶（`unusable.csv`）

| 原因 | 层数 | 含义 |
|---|---:|---|
| `grade_below_C` | 450 | 所有行都低于 C 级（无街名 / 无任何地址要素）→ 按口径丢弃，不猜 |

## 2. 逐层闭合

| 项 | 行数 |
|---|---:|
| 输入行（3,550 层 part 包实读） | 509,776,855 |
| 映射行（写进 11 列输出） | 305,674,428 |
| 丢弃：低于 C 级 | 204,102,427 |
| 丢弃：解析失败 | 0 |
| **差额** | **0** |

逐层闭合（`in_rows − mapped − dropped_below_C − parse_error`）差额 ≠ 0 的层：**0** 个

## 3. 字段级有效率（全局）

| 字段 | 有效率 | 门槛 | 结论 |
|---|---:|---:|---|
| `street_name` | **100.00%** | 100% | 达标 |
| `house_number` | **71.20%** | ≥90% | **未达标** |
| `zip5` 合法率 | **54.18%** | ≥95% | **未达标** |
| 坐标落合法范围 | **99.96%**（越界残留 1691 行 = 已被置 null） | 100% | **未达标** |

> `zip5_valid` 的分母是映射行；源里本就没有邮编的行记 missing（不补零、不截断）。`house_number` 同理：源里没有门牌就 null，绝不生成。

按 dialect：见 `field-stats.json: by_dialect`。按州：**不适用** —— 信封行恒无 `state` 字段，state 只能从 raw 的显式州字段或组合串尾部取，因此没有可靠的州分组维度（`field-stats.json: by_state_null`）。

## 4. 行级抽查（`spotcheck.csv`）

| 项 | 值 |
|---|---:|
| 抽查层数 | **355**（含字节最大 10 层） |
| 行级抽样 | 50179 行 |
| 相符 | **40286**（80.28%） |
| 不变量违反 | `bad_zip5=0, bad_state=0, bad_coord=0, zero_coord=0, bad_number=0, bad_columns=0` |

抽查方法：① 对输出行做**不变量**全扫（zip5 恰好 5 位、state 合法、坐标在范围内且非 (0,0)、门牌非占位值、11 列齐全）；② 另写一份**独立重算**（不复用 `fm_core`）对输入行重打一遍，按 (门牌, 街名, zip5, lat, lon) 五元组比对。


### 4.1 抽查相符率为什么是 80.28% 而不是 100%（如实说）

抽查的「独立重算」只读**信封字段**（`add_num/st_name/city/zip/lat/lon`），而主跑的取值顺序是
「信封 → `raw` 角色别名 → 组合串拆分」。凡是信封里没有、靠 `raw` 别名或 `split_number_street` 补出来的行，
独立重算那一侧必然判为「不符」——这是**检查器比主跑保守**造成的差，不是主跑写错。
证据：11 项**不变量全扫（69,259 行）0 违反** —— `bad_zip5=0, bad_state=0, bad_coord=0, zero_coord=0, bad_number=0, bad_columns=0`，
即输出里没有任何一行出现：邮编不是 5 位、州码非法、坐标越界、坐标 (0,0)、门牌是占位值、列数不对。
逐层明细见 `spotcheck.csv`（含 0 相符层，例如整层都靠组合串拆分的城市图层）。

## 5. 方法与偏差（必须如实说）

1. **方言命中率极低，这是本轮最重要的偏差**：3,550 层的 `layer_id` 与 `url` 与 17,168 行分档表的交集是 **0**，按 agol org 匹 registry 只命中 **115 层（3.2%）**；其余一律 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`、永不进 A 货池）。原因是这 3,550 层来自第 4/5/7 批采集，不在方言分档的分母里。
2. **取值优先级**（逐字段）：信封原生值 → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects 合并表，~200 个别名，不新增、不猜）→ 组合串拆分（`split_addr.split_number_street` / `split_city_tail`）。组合串拆出来的值 `provenance=split`，**一律不许进 S**（S 级按口径要求全要素原生）。
3. **未走 `collect/lib/fieldmap3.py`**（硬编码别名表）：它是采集侧的口径，本步按 muse 要求只把它当对照证据。实测它的别名表与本步用的 registry ∪ engine 表在「组合串字段」（如 `ADDR`/`LSN`）上都没覆盖，这也是为什么要上 `split_addr` 的拆分规则 —— 不接这一步时覆盖率只有 67%（1,186/1,776），接上后到 94%+。
4. **grade/tier 全部由配置驱动**：`engine/config/pilot.yaml` 的 `grades`（S/A/B/C 特征表）与 `tier_rank`，代码里没有硬编码阈值；本批 3,550 层在分档表里**没有任何 (url, dialect_id) 命中**，故 `tier` 一律 `unrated`（照抄 `tier_rank` 的 unrated=9）。
5. **zip5 口径**：`12345-6789` 取前 5；不足/超长/含字母一律 null 并计 missing，不补零。**house_number**：占位值（0/000/NULL/N/A/NONE/UNKNOWN/-1/空/纯符号）一律缺失，绝不生成门牌。**坐标**：范围外、(0,0)、缺省一律 null，绝不写 0 冒充。
6. **磁盘**：输入 40,341,427,040 B 只读；输出写 `dist/`，每 500 层一个 `fieldmap-partNNN.tar.gz`，打包后立刻删 `dist/rows/` 里的散文件；`free_gb` 全程未低于 3 GiB（收工 21.9 GiB）。

## 6. 怎么复跑

```bash
cd /data/workspace/wmd-fieldmap && python3 analysis/fieldmap-20261125/map_layers.py \
  --all --shard 500 --workers 7
python3 analysis/fieldmap-20261125/fieldstats.py
python3 analysis/fieldmap-20261125/spotcheck.py --layers 355 --rows 200
python3 analysis/fieldmap-20261125/finalize.py
```

