# REPORT — 1,340 层「构不出门牌+街名键」的组合串写法摸底

> 只调查，不改任何代码。本轮回答一个问题：**这 1,340 层的地址字段到底长什么样，下一步是加别名表还是写切分算法。**

---

## 0. 一句话结论

1,340 层里 **321 层（24.0%）只要往 registry 别名表加字段名就能出键**，**597 层（44.6%）必须写切分/拼列算法**，**422 层（31.5%）根本不是地址数据（排除即可）**；最大单一写法是「门牌+街名拼一格」（431 层 / 2,864 万行，占 32.2%）。

---

## 1. 采样口径自证（全部本地产物，未抓网）

| 项 | 值 |
|---|---|
| 目标集合 | 「E7 构不出门牌+街名键」= `n_addr_rows = 0` 的 1,340 层 |
| 复算脚本 | `combo_list.py`（照抄 `sandbox/coord_evidence.py:addr_key()` 的建键逻辑 + `sandbox/tier_relax.py` 的归因过滤，原文件零改动） |
| 复算结果 | **1,340**（`_work/recount.json: matches_1340 = true`） |
| 复算分解 | 假设池 1,831（E3=na/clear ∧ E7=unknown ∧ 其余 E 全 clear/na）− 491 = 1,340；其中 491 = 已进 Tier1 的 10 层 + n_cmp<3 的 481 层（`summary.json: attribution.blocked` 逐桶对齐） |
| 层清单 | `_work/target_layers.csv`（1,340 行，含 url / layer_id / rows_n / state / sample_rows） |
| 输入 1 | `analysis/auto-spatial-relax-20261125/auto-recognized.csv` sha256 `cc60a834625617c1…`（20.5 MB，17,168 行） |
| 输入 2 | `registry/dialects.v1.yaml` sha256 `bc7bd3bc68f52d01…`（只读，未改） |
| 输入 3（字段名+3 条原始记录） | `survey/ng911/samples.csv.gz` sha256 `5b5f0ef33b49dcbe…`（28.1 MB，60,697 层）——覆盖 **1,340/1,340** |
| 输入 4（真实值） | `analysis/coord-samples-20261124/samples/*.csv`（59 个文件，738,174 行）→ 本批命中 **61,918 行 / 1,340 层**，平均 46 行/层 |
| 本地 ndjson 快照 | 对这批层基本是空表（`ledger.json` 里 `tables.addr = 0`，行都进了 `reject` 且 reject 未落盘），**因此无法从 `dist/intake-full/layers/` 取到原始行**；改用上面两个采样源，未联网补抓 |
| 采样量 | 每层：完整字段名列表 + 3 条原始记录（ng911）+ 该层地址类字段的全部去重值（≤40 个/字段，管线当时的坐标样本） |

**判据只用「字段名 + 真实样例值形态」，不猜、不补**：每个字段先按值形态打成 number / street / city / state / zip / combo / fulladdr / range / idlike 之一，再按列的组合方式定模式。

---

## 2. 模式汇总表（层数之和 = 1,340，代码里有断言）

| pid | 模式 | 层数 | 占比 | rows_n 合计 | 可解析性 | 下一步修法 |
|---|---|---|---|---|---|---|
| P1 | 门牌+街名拼一格 | 431 | 32.16% | 28,644,662 | 可直接切出 | 切分算法 |
| P7 | 门牌+街名两列分列、字段名不在 registry 别名表 | 321 | 23.96% | 5,520,975 | 可直接切出 | 别名表 |
| P10 | 无任何可识别地址字段（非地址图层 / 字段少或样例全空） | 224 | 16.72% | 4,223,214 | 不可切 | 排除 |
| P5 | 多字段分列且街名本身要 2+ 列拼（pre-dir/type/suffix 分列），字段名不在别名表 | 101 | 7.54% | 1,418,701 | 可直接切出 | 别名表+拼列 |
| P6 | 结构 ID / 地块 ID / 分区号冒充地址（根本不是地址） | 90 | 6.72% | 702,896 | 不可切 | 排除 |
| P9 | 只有街名（或街名+城市分列），全层无门牌列 | 66 | 4.93% | 767,980 | 不可切 | 排除 |
| P3 | 门牌+街名+城市/州/邮编全拼一格（无显式分隔符） | 53 | 3.96% | 2,238,360 | 需猜或NLP | 切分算法 |
| P8 | 路段门牌区间（from/to addr + 街名，中心线层） | 22 | 1.64% | 184,987 | 需猜或NLP | 排除/专用逻辑 |
| P12 | 打码/占位门牌或路口名（3XX E 12TH ST、A ST / B AVE） | 11 | 0.82% | 887,307 | 不可切 | 排除 |
| P11 | PO BOX / POST OFFICE BOX（邮政信箱，非街道地址） | 9 | 0.67% | 82,887 | 不可切 | 排除 |
| P4 | 全地址单串（带逗号/竖线等分隔符） | 8 | 0.6% | 35,822 | 可直接切出 | 切分算法 |
| P13 | 业主名/联系人 + 完整地址混在一格（mailing label） | 4 | 0.3% | 19,783 | 需猜或NLP | 切分算法 |
| — | **合计** | **1340** | 100% | **44,727,574** | 可直接切出 861 / 需猜 79 / 不可切 400 | — |

（`P2 街名+城市拼一格` 实测 **0 层**：这批里没有「街名+城市挤在同一格但缺门牌」的层，同样的数据都落在 P9 或 P3。）

---

## 3. 分流依据（组合拳下一步靠这节分配资源）

| 分流 | 层数 | 占比 | rows_n | 对应模式 |
|---|---|---|---|---|
| **只加 registry 别名表即可** | **321** | 23.96% | 5,520,975 | P7（门牌列/街名列各一列，名字不在表里） |
| **必须靠切分（或拼列）算法** | **597** | 44.55% | 32,357,328 | P1、P3、P4、P5、P13 |
| **根本不是地址 / 无法构成键** | **422** | 31.49% | 6,849,271 | P6、P8、P9、P10、P11、P12 |

读法：
- **别名表是便宜且确定的一手**：321 层、552 万行，只要把各层真实字段名（`ADDRESSNUM`、`HOUSENO`、`SITUS_NU`、`PROP_ST_NO`、`ADDR_NBR`…）补成 number/street 别名，`addr_key` 立刻能出键，**不需要动算法**。
- **切分算法是主力活**：597 层、3,234 万行。其中 P1（431 层 / 2,864 万行）只要「首个空格切门牌」的确定性规则就能覆盖；P3（53 层）要处理「城市+州+邮编黏在尾部」；P5（101 层）要按 pre-dir/type/suffix 拼列。
- **排除是正当结论**：422 层里 224 层压根没有地址字段（只有 OBJECTID/ROUTEID 这类），90 层字段名像地址但值是 ID，66 层只有街名没门牌，11 层是打码门牌/路口名，9 层是 PO BOX，22 层是中心线门牌区间。这些层**不管怎么改别名表/切分算法都不会出键**，应当从「E7 可验」分母里剔掉，别再拿它们算缺口。

---

## 4. 逐模式证据（层名 + 原始字段值原文）

### P1 门牌+街名拼一格 — 431 层 / 28,644,662 行 / 可直接切出
规则：存在字段，其 ≥60% 样例值匹配 `^\s*(\d{1,6})[-A-Za-z]?[\s,]+([A-Za-z].{1,80})$`，且值里没有州/邮编/分隔符。
  - `FeatureServer/2`（Commissioner District And Neighborho）rows_n=24,955 fields=`FULLADDR`
    values: ["5391 N Federal Hwy", "2080 NE 54 St", "2064 NE 54 St"]
  - `FeatureServer/0`（Aggregation_of_incidents_to_Join_Use）rows_n=224 fields=`GC_Address`
    values: ["2800 E michigan Street", "3737 N Meridian Street", "902 N Bosart Avenue"]
  - `FeatureServer/0`（DCR Recreation Courts）rows_n=110 fields=`Address`
    values: ["Education st", "Dilboy field", "682 Willard st"]
> 另有 40 余层是「混合形态」（30%~70% 带门牌，其余只有街名，如 `STREET` = `257 Country Club Rd` / `Highway 75`），这些层切分后能出一部分键，缺号行仍会落空，已在 `patterns.csv` 的 `example_values` 里标 `mixed`。

### P7 门牌+街名两列分列、字段名不在别名表 — 321 层 / 5,520,975 行 / 可直接切出
规则：门牌列 + 街名列各一列、都过值形态校验、街名不需要拼列，且至少一列名不在 registry 别名表。
  - `FeatureServer/0`（FPA_parcels_area）rows_n=991 fields=`TRANUM|SITUS_SUFF|OWN_ADDR2|OWN_ZIP`
    values: [["81004", "89000", "81066"], ["ST", "RD", "VW"]]
  - `FeatureServer/0`（Study_Area_Parcels）rows_n=119,693 fields=`TRANUM|SITUS_SUFF|OWN_ADDR1|OWN_ZIP`
    values: [["08244", "08001"], ["ST"]]
  - `FeatureServer/0`（Division Map 2022）rows_n=35,280 fields=`TRANUM|SITUS_SUFF|OWN_ADDR1|OWN_ZIP`
    values: [["74120", "13115", "04230"], ["CT", "BLVD", "AVE"]]

### P10 无任何可识别地址字段（非地址图层 / 字段少或样例全空）— 224 层 / 4,223,214 行 / 不可切
  - `FeatureServer/0`（Accessory Dwelling Units (ADUs)）rows_n=7,987 fields=`OBJECTID|LOT_SIZE|C_DISTRICT|MAF_ID`
    values: [[], [], []]
  - `FeatureServer/0`（BaltimoreCenterlinesSHA）rows_n=11,765 fields=`OBJECTID|ID_PREFIX_NAME|ID_PREFIX|ID_RTE_NO`
    values: [[], [], []]
  - `FeatureServer/0`（BSD_ParcelsAug23_Public）rows_n=9,937 fields=`OBJECTID|REM_GIS_ID|LND_USE_CODE|LND_ZONE`
    values: [[], [], []]

### P5 多字段分列且街名要 2+ 列拼 — 101 层 / 1,418,701 行 / 可直接切出（别名+拼列）
  - `FeatureServer/3`（911_Data_Layers）rows_n=232,673 fields=`Addr_Num|Addr_St|St_Suffix`
    values: [["421", "506"], ["FRANCIS", "FERN"]]
  - `FeatureServer/0`（Slidell Permitting Web Map_WFL1）rows_n=13,075 fields=`ADDRES_NUM|Street1|POST_DIR`
    values: [["118", "116"], ["Port", "Chamale"]]
  - `FeatureServer/0`（Black Businesses Matter Map_WFL1）rows_n=215 fields=`A_NUM|St_Name|St_Postype`
    values: [["238", "256"], ["TARBORO", "ATLANTIC"]]

### P6 结构 ID/地块 ID/分区号冒充地址 — 90 层 / 702,896 行 / 不可切
  - `FeatureServer/0`（Enterprise GIS Form Responses）rows_n=155 fields=`email_addr|OBJECTID|GlobalID`
    values: [["peter.strand@co.eau-claire.wi.us", "geraldk@jeffersoncountywi.gov", "baker.megan@rigov.org"], []]
  - `FeatureServer/0`（Dam NID）rows_n=124 fields=`Url_Address|Record_ID|State_or_Federal_Agency_ID`
    values: [["https://dams.hawaii.gov/DamInformation.aspx?id=818982DE-5FDA-4442-89F2-0D7E3EA2E1F4", "https://dams.hawaii.gov/DamInformation.aspx?id=C14EB5EC-E1CB-4304-B013-7AE2B1ED7167", "https://dams.hawaii.gov
  - `FeatureServer/0`（Ludlow Zoning Map DRAFT 2026_WFL1）rows_n=78,638 fields=`SymbolLabel|OBJECTID|GlobalID`
    values: [[], []]

### P9 只有街名（或街名+城市分列），全层无门牌列 — 66 层 / 767,980 行 / 不可切
  - `FeatureServer/0`（Centerlines）rows_n=35,740 fields=`FULL_STREET_NAME`
    values: [["PLATHE ROAD", "LITTLE ROAD", "ALTERNATE HWY 19"]]
  - `FeatureServer/0`（Active Streets (CNNs, from DataSF, p）rows_n=16,378 fields=`street_gc|streetname`
    values: [["CROWN", "SAINT GERMAIN", "WASHINGTON"]]
  - `FeatureServer/0`（AddressRange）rows_n=2,317 fields=`StreetName`
    values: [["LACONNER WHITNEY", "MARCHS POINT", "TEXAS"]]

### P3 门牌+街名+城市/州/邮编全拼一格（无显式分隔符）— 53 层 / 2,238,360 行 / 需猜或NLP
  - `FeatureServer/0`（Erase_Parcels_20191028_with_Interior）rows_n=2,037 fields=`address_2`
    values: ["19561 MECHANICSVILLE RD", "18833 RUNIONS CREEK RD", "17042 LITTLE DRY RIVER RD"]
  - `FeatureServer/0`（Parcels35）rows_n=111,036 fields=`Address1`
    values: ["3900 COMMONWEALTH BLVD", "21208 NW 238TH AVE", "25508 OLD BELLAMY RD"]
  - `FeatureServer/0`（AGOL_Service_LUZoning）rows_n=76,085 fields=`MailingAddress`
    values: ["1201 NEW HOPE CHURCH RD Chapel Hill NC 27516", "5401 SPRING HOUSE LANE CHAPEL HILL NC 27516", "1000 WOODLOT RIDGE RD CHAPEL HILL NC 27516"]

### P8 路段门牌区间（中心线层）— 22 层 / 184,987 行 / 需猜或NLP（建议排除）
  - `FeatureServer/0`（Caltrans Freeway Centerline）rows_n=792 fields=`fromaddr_l|toaddr_l|fromaddr_r|toaddr_r`
    values: [["0", "4901"], ["0", "5049"], ["0"]]
  - `FeatureServer/0`（Centerlines）rows_n=5,359 fields=`V_TOADDR`
    values: [["370", "318"]]
  - `MapServer/6`（Roads - Hawaii County）rows_n=13,821 fields=`toaddr`
    values: [["2318", "550580"]]

### P12 打码/占位门牌或路口名 — 11 层 / 887,307 行 / 不可切
  - `FeatureServer/0`（2013 Ottawa County Sheriff Incident ）rows_n=78,299 fields=`IncidentAddress`
    values: ["1xx BALDWIN ST", "122xx FILLMORE ST", "5xx BUTTERNUT DR"]
  - `FeatureServer/0`（2014 Ottawa County Sheriff Incident ）rows_n=80,487 fields=`IncidentAddress`
    values: ["6xx BUTTERNUT DR", "94xx 72ND AVE", "RILEY ST & WEST SHORE DR"]
  - `FeatureServer/0`（2015 Ottawa County Sheriff Incident ）rows_n=83,256 fields=`IncidentAddress`
    values: ["N STATE ST & W OAK AVE", "42ND AVE & LUCE ST", "x E 48TH ST"]

### P11 PO BOX / POST OFFICE BOX — 9 层 / 82,887 行 / 不可切
  - `FeatureServer/0`（2025 Zoning Code）rows_n=43,995 fields=`MailADDRESS1`
    values: ["PO BOX 20000", "PO BOX 1747", "1800 MARQUESS"]
  - `FeatureServer/6`（UCRC - Pilot Project Application Loc）rows_n=6 fields=`Primary_Contact_Address`
    values: ["PO Box 779 Price, UT 84501", "PO 357 Cleveland, UT 84518"]
  - `FeatureServer/0`（Tax Parcel Public）rows_n=32,240 fields=`Mailing_Address`
    values: ["PO BOX 87", "1630 E 2450 S UNIT 203", "PO BOX 114"]

### P4 全地址单串（带逗号/竖线分隔符）— 8 层 / 35,822 行 / 可直接切出
  - `FeatureServer/0`（CFN_1）rows_n=29 fields=`Address`
    values: ["603 Cedar Point Rd, Cedar Point", "1006 Cedar Point Rd, Cedar Point", "195 Guthrie Farm Rd, Bogue/ Newport"]
  - `FeatureServer/0`（CFN_2）rows_n=36 fields=`Address`
    values: ["603 Cedar Point Rd, Cedar Point", "1006 Cedar Point Rd, Cedar Point", "195 Guthrie Farm Rd, Bogue/ Newport"]
  - `FeatureServer/0`（San Juan Bautista Historical Resourc）rows_n=333 fields=`FullAddress`
    values: ["1131 Salinas Grade Road, San Juan Bautista, CA", "651-1 Salinas Road, San Juan Bautista, CA", "115 Fifth Street, San Juan Bautista, CA"]

### P13 业主名/联系人 + 完整地址混在一格 — 4 层 / 19,783 行 / 需猜或NLP
  - `FeatureServer/1`（MLG_Client_Parcels）rows_n=14,692 fields=`ownerAddress`
    values: ["TERRELL, J CRAIG & MARGO P 26035 GRAND PINES RD MAGNOLIA, TX 77355-2085 USA", "JANECEK, RAYMOND 23919 SANDERS CEMETERY RD MAGNOLIA, TX 77354 USA", "HOOPER, RONNIE & BARBARA 20319 SANDERS RD MAGNOLIA
  - `FeatureServer/0`（175637_ComEd_IL_Greenleaf_Parcels）rows_n=987 fields=`Own1_FullMailingAddress`
    values: ["{\"mailadd\":\"1 E BELVIDERE RD\",\"mail_city\":\"GRAYSLAKE\",\"mail_state2\":\"IL\",\"mail_zip\":\"60030\"}", "{\"mailadd\":\"12 S CENTER ST\",\"mail_city\":\"BENSENVILLE\",\"mail_state2\":\"IL\",\
  - `FeatureServer/0`（4217_IECA_TX_IECADemo_Parcel_View）rows_n=351 fields=`Own1_FullMailingAddress`
    values: ["{\"mailadd\":\"180 HERBER\",\"mail_city\":\"NEW BRAUNFELS\",\"mail_state2\":\"TX\",\"mail_zip\":\"78130\"}", "{\"mailadd\":\"3614 TWIN DISH WAY\",\"mail_city\":\"NEW BRAUNFELS\",\"mail_state2\":\"TX

---

## 5. 未决项（下一步开工前要拍板）

1. **别名的边界**：P7 里有批层（如 `ADDRESSNUM`+`STREET`+`ZIP`、`TRANUM`+`OWN_ADDR2`+`OWN_ZIP`）字段名介于「门牌列」和「邮件地址列」之间，加别名会不会把「业主邮寄地址」也当成地点地址，需要定规则（建议：别名只加在 `addr`/`situs`/`site`/`prop` 这类「地点」语义前缀上，`own_`/`mail_`/`bill_` 前缀排除）。
2. **P1 的切分失败率没测**：`257 Country Club Rd` 这类规则切分没问题，但 `P O BOX 2431`、`RR 2 BOX 45`、`12 1/2 N Main`、`100 Bypass 35` 这类需要后缀/分数规则；本轮只按形态统计，没有逐层算「切出来后能过地址字典的比例」——建议下一步在 20~30 层上做白盒抽样定规则再全量跑。
3. **P3 的「城市+州+邮编黏尾」判定没有真值**：`1846 TOWER Chaves County NM 88201` 里 `Chaves County` 是县名不是城市，靠空格切只能靠「尾部 ZIP5 + 州缩写」锚定；对 `848 W COLONIAL CIR DAYTONA BEACH FL 32117` 可行，对没有 ZIP 的行不可行，需要分层统计（本轮未做）。
4. **P10 里 224 层是「字段少」还是「字段抓漏」没区分**：其中 7 层字段数 ≤3（如只有 `OBJECTID`/`FID`），可能是采集侧没取到字段，不一定是数据没地址——建议下一步拿 `inventory-remote-uncollected.csv` 的 `n_fields` 交叉核一遍再决定是否排除。
5. **P8（22 层中心线区间）** 是否要单独建模（`from/to` 转区间匹配）不在本轮范围；若不做，应从 E7 可验分母里剔除。

---

## 6. 产物与复算

```
analysis/combo-step1-20261125/
├── REPORT.md            本文件
├── patterns.csv         1,340 行逐层清单（layer_id/url/rows_n/pattern_id/pattern/fields/example_values/parseability/fix_path/title/state/n_fields/coord_rows）
├── patterns.json        模式汇总（pattern_id/名称/规则/层数/行数/可解析性/修法/例子 + triage + 断言）
├── combo_list.py        ① 复算 1,340 层清单（照抄 addr_key 逻辑，只读）
├── combo_fields.py      ② 装配字段名 + 样例值（全本地）
├── combo_classify.py    ③ 分类 + 断言（各模式层数之和 == 总层数、分流三桶之和 == 总层数）
└── _work/               中间件（已 gitignore）：target_layers.csv / per_layer.json / classify_detail.json / recount.json
```

复算（约 4 分钟，无网络）：

```bash
cd analysis/combo-step1-20261125
python3 combo_list.py       # → _work/target_layers.csv + _work/recount.json（断言 matches_1340=true）
python3 combo_fields.py     # → _work/per_layer.json
python3 combo_classify.py   # → patterns.csv + patterns.json（两条断言）
```

## 7. 边界自证

- 只新增 `analysis/combo-step1-20261125/`；`engine/ registry/ collect/ schema/ sandbox/` **零改动**（`git diff --name-only origin/main...HEAD` 可验）
- 未改 registry、未重跑分档、未起 Actions、未动账本/Release/网站
- `sandbox/coord_evidence.py` 的 `addr_key()` 是**照抄**到本目录脚本里用，原文件一个字节没动
