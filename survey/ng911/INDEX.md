# INDEX — NG911 / 州级地址数据 普查（2026-10-22）

> 本目录回答一个问题：**「NG911 / 各州 E911 这套地址数据，我们到底能拿到什么？」**
> 只做普查与取证，不做采集。采集流水线在 `../../collect/`。

---

## 1. 一句话结论

全美 51 个州/地区，都能找到含完整地址字段（门牌、街名、单元、城市、州、ZIP、坐标）的地址点图层；
但「覆盖全州、完整到户」**尚未证实**，需按 Census 住房单元数做分母算覆盖率才能下结论。

---

## 2. 文件地图

| 文件 | 作用 | 说明 |
|---|---|---|
| `layers.json` | **采集任务表原料** | 60,694 个图层，每层一条：state / title / url / 服务类型 / 几何 / 要素数 / 覆盖度 / 是否有门牌字段 / 提供方 / 许可 |
| `samples.csv.gz` | **每层字段 + 3 条样本** | 41,662 层取到样本；含完整字段名列表与原始记录前 3 行（未做任何清洗） |
| `清单-精简.md` | 州级概览 | 每州：图层数 / 有样本 / 含门牌样本 / 最大单层要素数 |
| `scripts/harvest.py` | 全国线索收割 | AGOL 全库搜索 + Hub + Socrata 目录，产出 `items.json` |
| `scripts/probe_shard.py` | 分片探针 | 取几何类型 / 要素数 / 字段 / 范围，产出 `shard_*.json` |
| `scripts/portals.py` | 逐州官方门户 | 自动识别 Socrata / CKAN / ArcGIS Hub，抓全部相关数据集 |
| `scripts/reloc.py` | 逐层取样 | 每层拉前 3 行全字段，产出 `samp_*.json` |
| `scripts/merge.py` / `merge2.py` | 合并 | 产出 CSV 与 md 清单 |
| `scripts/make_summary.py` | 精简汇总 | 产出 `清单-精简.md` |
| `ng911_inventory.py` | 公共库 | 所有脚本共用的 HTTP / 探针 / 字段判定函数 |

**全量明细不进 Git**：`清单-全量.md`（63MB）、`清单-全量-含样本.md`（63MB）、全部中间 json，
已打包进 Release 资产 `survey-ng911-2026-10-22`（tag 同名）。

---

## 3. 怎么重跑

```bash
# 第一轮：线索收割 + 分片探针 + 51 州门户（约 20 分钟，63 个 job）
gh workflow run ng911-survey.yml --repo ip9988001/world-map-data-33

# 第二轮：逐层取样（约 15 分钟，20 个分片）
gh workflow run ng911-sample.yml --repo ip9988001/world-map-data-33

# 本地单独跑一个州
python3 portals.py --state VT
```

重跑频率建议：**每季度一次**，用于「数据源漂移监测」——哪个州下架、哪个换 URL、哪个新出全州层。

---

## 4. 口径与已知误差（用之前必读）

1. **州归属是推断的**：按图层几何中心点，或按样本里的「城市, 州 ZIP」模式推断，**不是官方口径**。
   判不出的归「未定位」（33,898 条，其中 18,318 条已有样本）。
2. **要素数含水分**：同一图层常有 view / copy / filtered view 多个入口，count 会重复计。
   全库已探明要素数合计约 46 亿，**不能当成「能拿到的地址总数」**。
3. **`has_point` 会误判**：只要字段名里有 `ADDRESS` 就算命中，parcel、许可、呼叫记录也会被算进去。
4. **存在大量非地址层**：parcel、permit、NFIRS 消防记录、监测点混在同一批结果里。
   按要求**未做筛选**，筛选留给下游加工。
5. **AGOL 搜索上限 10,000 条**：单个查询翻到 10,000 就截断，这就是为什么要拆成 8 个不同查询词。
6. **Socrata / MapServer 拿不到几何范围**：这批只能靠样本内容归州，是「未定位」的主要来源。

---

## 5. 已验证的高价值图层（人工确认过）

| 州 | 图层 | 要素数 |
|---|---|---|
| TX | Address Points | 11,349,117 |
| VA | Virginia Address Points | 3,881,020 |
| AZ | AZ911 AddressPoints | 3,734,802 |
| OK | NG911 Address Points | 1,928,880 |
| KS | Kansas NG911 Address Points | 1,035,861 |
| ME | Addresses | 792,091 |
| ND | NDGISHUB SiteStructure Address Points | 438,139 |
| DE | SUSS Address Points | 184,716 |

样本格式示例（阿拉斯加 `Addresses_Hosted`，原始值）：

```
FULL_ADDRESS   : "26800 Eklutna Village Rd Trlr 26800, Chugiak, AK 99567"
STREET_ADDRESS : "26800 EKLUTNA VILLAGE RD TRLR 26800"
```

---

## 6. 未解决项

- [ ] 覆盖率：每州「最大地址点层要素数 ÷ Census 住房单元数」，得出真实覆盖百分比
- [ ] 逐县覆盖：挑 CA / KS / MT 三个州按县统计，看有多少县为零
- [ ] 未定位 33,898 条继续归位（样本里含城市名或 ZIP 的可继续救）
- [ ] 坐标精度抽样：同一地址在不同层的坐标差多少
