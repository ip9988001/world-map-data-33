# REPORT — tier1 未定位 85 层定州（tier1-locate-20261125）

**一句话**：85 层「`state=未定位`」已逐层取证定州，**83 层定出唯一州、2 层判 unresolved**；三州试点里 **DE 0 层 / NH 2 层 / IA 0 层**，其余 83 层分布在 NC 14、PA 13、WI 11、SC 9、CA 7 等 19 个州——**本批未定位层与 DE/IA 两个试点州无关**。

- 输入：`analysis/auto-spatial-relax-20261125/auto-recognized.csv`（sha256 `cc60a834…fb812b`，17,168 行，tier1 176 行，未定位 85 行，rows_n 合计 20,766,446），**未改动**
- 产物：`tier1-unlocated.csv`（原始清单 85 行）、`tier1-unlocated-states.csv`（定州结果 85 行 × 18 列）、`state-distribution.json`、`method.md`、`ref/`
- 规则：E1/E2/E3 三路投票（E4 只 tie-break），阈值与规则原文见 `method.md` §3

---

## 1. 三州答案（本活最关心的数）

| 州 | 层数 | 是哪几层 |
|---|---|---|
| **DE** | **0** | 无 |
| **NH** | **2** | `VW_Base_Map_(View)/FeatureServer/0`、`pbBaseMap_View/FeatureServer/0` |
| **IA** | **0** | 无 |

NH 这 2 层证据：`distinct state = NH`（地址点层）+ 1000/1000 采样点落 NH（bbox 89.7% NH、10.4% MA 属矩形外扩）+ 样本 municipality `Pelham`（NH）。

> DE 与 IA 各 0 层，意思是这 85 层里**没有任何一层落在 DE 或 IA**——三州试点若不动 registry 别名表，靠这批「未定位」层补不出 DE/IA 的 tier1。

## 2. state_final 完整计数（85 层）

| 州 | 层数 | 州 | 层数 |
|---|---|---|---|
| NC | 14 | NH | 2 |
| PA | 13 | VT | 2 |
| WI | 11 | WA | 2 |
| SC | 9 | FL | 1 |
| CA | 7 | GA | 1 |
| MN | 4 | MA | 1 |
| VA | 4 | ME | 1 |
| CO | 3 | ND | 1 |
| TN | 3 | WV | 1 |
| TX | 3 | **unresolved** | **2** |

按 rows_n 排序（层多不代表行多）：NC 19,212,042 行（含 AddressNC 单层 6,297,169 ×3 入口）> CA 532,832 > GA 481,847 > TX 148,889 > PA 106,869 > ME 55,592 > WI 43,891 > MN 42,238 > VA 37,765 > NH 30,014 > SC 24,324 > ND 19,640 > VT 13,009 > WV 12,717 > CO 3,076 > TN 837 > MA 659 > WA 128 > unresolved 50 > FL 27。

## 3. confidence 分布与三路覆盖率

| confidence | 层数 | 含义 |
|---|---|---|
| very_high | 33 | 三路一致 |
| high | 33 | 两路一致 |
| medium | 17 | 只有一路有线索 |
| conflict | 2 | 无多数/散列 |
| none | 0 | — |

三路覆盖：**E1 命中 52 层 / E2 命中 55 层 / E3 有几何 85 层（1000 行采样）+ 85 层都有 bbox4326**；E3 实际进入投票 83 层（2 层几何散列 <20% 不投票）。

## 4. 跨州层（multi_state=true，2 层）

- `Generic_Photos_and_Captions_Survey_VIEW_LAYER/FeatureServer/0` — WA/medium（rows_n=64）
- `service_48189ad1d7074d58856d07727687d617/FeatureServer/0` — WA/medium（rows_n=64）

两层是同一份数据的 view/original（`Generic_Photos_and_Captions_Survey`），采样 64 点：WA 67.2% / OR 26.6% / AZ 3.1% / OUT 3.1%。无 E1/E2 线索，按规则 5 取占比最大州 WA，`confidence=medium`，`states_covered=OR/WA`。

另有 8 层 SC 系的 bbox 覆盖到 GA 20~23%、3 层覆盖到邻州 10~20%，那是**矩形外扩**，点落州仍是 SC 100%，已在 note 里逐层写明、不计 cross-state。

## 5. unresolved / conflict（2 层）

- `service_76dad3d0ee7846aeb514cb27afb72727/FeatureServer/1` — unresolved/conflict（rows_n=25）
- `survey123_7d6d08601847441f966e7f0a679f6bf7_stakeholder/FeatureServer/2` — unresolved/conflict（rows_n=25）

两层是同一份数据的两个入口（NG State Hosted Training Locations 及其 survey123 stakeholder 副本），25 个点位散列在 NM 3 / MD 2 / CO 1 / PA 1（60% 落在 50 州 + DC 之外），样本 5 条只有 2 条地址在 NM。**几何散列 + E1 误命中 + 无多数 ⇒ 不定州**（人工复核已确认，见 `overrides.json`）。这类全国性调研点层本来就没有单州归属，硬塞一个州是造假。

## 6. 逐层归属表（85 行，E1/E2/E3 分列）

| # | state_final | conf | layer（服务名/层号） | E1 | E2 | E3（点落州占比） | rows_n |
|---|---|---|---|---|---|---|---|
| 1 | **CA** | very_high | `City_Owned_Parcels_(View)/FS/0` | CA | CA | CA:100.0%; bbox→CA:100.0% | 26,007 |
| 2 | **MA** | high | `All_TH_Lots/FS/0` | GA / IN / KY / MA / PA / VA | — | MA:100.0%; bbox→MA:100.0% | 659 |
| 3 | **CA** | high | `GeoType_SAR/FS/0` | CA / CO / NY | — | CA:100.0%; bbox→CA:100.0% | 9,043 |
| 4 | **CA** | very_high | `Public_Parcels/FS/0` | CA | CA | CA:100.0%; bbox→CA:100.0% | 205,346 |
| 5 | **CA** | very_high | `County_Parcels_-_Public_View/FS/0` | CA | CA | CA:100.0%; bbox→CA:100.0% | 199,341 |
| 6 | **FL** | very_high | `Air_Transportation_Locations/FS/0` | FL | FL | FL:100.0%; bbox→FL:100.0% | 27 |
| 7 | **GA** | high | `LSLI/FS/1` | — | GA | GA:100.0%; bbox→GA:100.0% | 481,847 |
| 8 | **SC** | medium | `EnerGov/FS/0` | TX | — | SC:100.0%; bbox→SC:100.0% | 4,627 |
| 9 | **ME** | very_high | `Androscoggin_County_District_Notes/FS/3` | ME | ME | ME:100.0%; bbox→ME:100.0% | 55,592 |
| 10 | **CA** | very_high | `AddPts_020724/FS/0` | CA | CA | CA:100.0%; bbox→CA:100.0% | 60,659 |
| 11 | **NC** | high | `AddPoints_102325_/FS/0` | — | NC / VA | NC:100.0%; bbox→NC:94.1% / SC:5.9% | 107,060 |
| 12 | **MN** | very_high | `us_mn_state_mde/struc_school_program_locs/FS/0` | MN | MI / MN | MN:100.0%; bbox→MN:59.5% / WI:19.9% | 5,904 |
| 13 | **WI** | medium | `Pierce_Data_Other/MS/4` | — | — | WI:100.0%; bbox→WI:80.4% / MN:19.6% | 20,829 |
| 14 | **NC** | very_high | `GIS/Collector_Base_Layers_GIS_STAGE/FS/0` | NC | NC | NC:100.0%; bbox→NC:98.7% | 37,938 |
| 15 | **TN** | high | `HomelessCount_2fff2b74033e443c93e5a56b17904e02/FS/0` | NC / TN | — | TN:100.0%; bbox→TN:100.0% | 279 |
| 16 | **TN** | high | `Homeless_Count_dashboard2/FS/0` | NC / TN | — | TN:100.0%; bbox→TN:100.0% | 279 |
| 17 | **TN** | high | `Homeless_Count_public2/FS/0` | NC / TN | — | TN:100.0%; bbox→TN:100.0% | 279 |
| 18 | **VA** | high | `VPRA_Roles_and_Responsibilities_/FS/1` | VA | — | VA:94.9% / DC:5.1%; bbox→VA:85.9% / MD:8.7% / WV:5.1 | 39 |
| 19 | **VA** | high | `Virginia_Passenger_Rail_Authority_Roles_and_Responsibilities/FS/1` | VA | — | VA:94.9% / DC:5.1%; bbox→VA:85.9% / MD:8.7% / WV:5.1 | 40 |
| 20 | **MN** | very_high | `Minnesota_School_Program_Locations_2026/FS/0` | MN | MI / MN | MN:100.0%; bbox→MN:58.4% / WI:20.2% | 5,904 |
| 21 | **NC** | very_high | `AddressNC/NC1Map_Addresses/MS/0` | NC | NC | NC:100.0% | 6,297,169 |
| 22 | **NC** | very_high | `AddressNC/NC1Map_Addresses/FS/0` | NC | NC | NC:100.0% | 6,297,169 |
| 23 | **NC** | very_high | `AddressNC/NC1Map_Addresses/MS/0` | NC | NC | NC:100.0% | 6,297,169 |
| 24 | **VT** | medium | `Neighborhood_Code_Parcel_Data_Updated/FS/0` | NC | — | VT:100.0%; bbox→VT:100.0% | 7,565 |
| 25 | **VT** | medium | `RL_Parcels_NC_WebMap/FS/0` | NC | — | VT:100.0%; bbox→VT:100.0% | 5,444 |
| 26 | **WV** | high | `AwareMap/FS/3` | — | WV | WV:88.3% / MD:11.7%; bbox→WV:79.2% / MD:17.4% | 12,717 |
| 27 | **NC** | high | `Fire_Districts_Relation/FS/0` | — | NC | NC:100.0%; bbox→NC:97.8% | 30,946 |
| 28 | **NC** | high | `Operational_Layers/FS/34` | — | NC | NC:100.0%; bbox→NC:97.8% | 32,602 |
| 29 | **CA** | high | `Centerlines/FS/1` | CA | — | CA:100.0%; bbox→CA:100.0% | 14,014 |
| 30 | **WI** | very_high | `JEFCO_Parcels_Master_V2_FLU/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 340 |
| 31 | **WI** | very_high | `JEFCO_Parcels_Master_V2_ReadOnly/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 340 |
| 32 | **WI** | very_high | `WALCO_Parcels_Master_V2_FLU/FS/5` | WI | WI | WI:100.0%; bbox→WI:100.0% | 3,164 |
| 33 | **WI** | very_high | `WALCO_Parcels_Master_V2_ReadOnly/FS/5` | WI | WI | WI:100.0%; bbox→WI:100.0% | 3,164 |
| 34 | **PA** | high | `service_d9d3509c05444e8b88165b3a82a01953/FS/0` | — | NC / PA / VA | PA:32.1% | 757 |
| 35 | **PA** | high | `survey123_7ef8a22afe724ad596c5b8efb7aca1e0_stakeholder/FS/0` | SC | NC / PA / VA | PA:32.1% | 757 |
| 36 | **CO** | very_high | `Denver_SNAP_LILA/FS/0` | CO | CO | CO:100.0%; bbox→CO:100.0% | 399 |
| 37 | **MN** | very_high | `TaxParcelsGAC/FS/0` | MN | MN | MN:100.0%; bbox→MN:99.7% | 15,215 |
| 38 | **MN** | very_high | `Tax_Parcels_(Public)/FS/0` | MN | MN | MN:100.0%; bbox→MN:99.7% | 15,215 |
| 39 | **unresolved** | conflict | `service_76dad3d0ee7846aeb514cb27afb72727/FS/1` | — | NM | NM:12.0% / MD:8.0% | 25 |
| 40 | **unresolved** | conflict | `survey123_7d6d08601847441f966e7f0a679f6bf7_stakeholder/FS/2` | SC | NM | NM:12.0% / MD:8.0% | 25 |
| 41 | **CA** | very_high | `Fire_All_Eaton/FS/0` | CA | CA | CA:100.0%; bbox→CA:100.0% | 18,422 |
| 42 | **NC** | very_high | `NorthWilkesboro_TownWebMap/FS/0` | GA / IL / NC / SC | GA / NC | NC:100.0%; bbox→NC:100.0% | 20,246 |
| 43 | **PA** | medium | `Existing_Land_Use_Dover_Borough/FS/3` | — | — | PA:100.0%; bbox→PA:100.0% | 9,234 |
| 44 | **PA** | medium | `Parcels/FS/2` | — | — | PA:100.0%; bbox→PA:100.0% | 9,234 |
| 45 | **PA** | medium | `Parcels_050621/FS/0` | — | — | PA:100.0%; bbox→PA:100.0% | 4,481 |
| 46 | **PA** | medium | `Parcels_21119/FS/0` | — | — | PA:100.0%; bbox→PA:100.0% | 4,242 |
| 47 | **WI** | very_high | `Platteville_Future_Land_Use_2026/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 3,434 |
| 48 | **WI** | very_high | `Zoning_2026/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 3,434 |
| 49 | **NC** | very_high | `Wilkesboro_PublicTownWebMap/FS/0` | GA / NC | GA / NC | NC:100.0%; bbox→NC:100.0% | 20,245 |
| 50 | **SC** | very_high | `Phase_1_Assessment_Brownfields/FS/0` | SC | SC | SC:100.0%; bbox→SC:59.6% / GA:20.7% / NC:9.4% | 1,150 |
| 51 | **SC** | high | `Phase_1_Assessment_Superfund_Site_Assessment_View/FS/0` | — | SC | SC:99.9%; bbox→SC:60.5% / GA:20.1% / NC:9.7% | 1,023 |
| 52 | **SC** | high | `Phase_1_Assessment_Superfund_State_Remediation_View/FS/0` | — | SC | SC:100.0%; bbox→SC:63.1% / GA:19.6% / NC:8.8% | 353 |
| 53 | **SC** | high | `Phase_1_Assessment_Superfund_State_Voluntary_Cleanup_View/FS/0` | — | SC | SC:100.0%; bbox→SC:65.4% / GA:21.6% / NC:7.1% | 271 |
| 54 | **SC** | high | `UST_Phase1_Releases_(Active_View)/FS/0` | — | SC | SC:100.0%; bbox→SC:58.2% / GA:20.5% / NC:10.0% | 1,954 |
| 55 | **SC** | high | `UST_Phase1_Releases_(CNFA_View)/FS/0` | — | SC | SC:99.9%; bbox→SC:57.5% / GA:20.9% / NC:10.5% | 2,544 |
| 56 | **SC** | high | `UST_Phase1_Releases_(NFA_View)/FS/0` | — | SC | SC:100.0%; bbox→SC:56.1% / GA:22.8% / NC:10.2% | 6,768 |
| 57 | **SC** | high | `UST_Phase1_Releases_(Regulatory_View)/FS/0` | — | SC | SC:100.0%; bbox→SC:56.1% / GA:22.5% / NC:10.5% | 5,634 |
| 58 | **NC** | high | `HomelessCount_dashboard_16d1edf69b554f7a904d9142e67eaa2d/FS/0` | NC | — | NC:63.9% | 584 |
| 59 | **NC** | high | `Homeless_Count_join_16d1edf69b554f7a904d9142e67eaa2d/FS/0` | NC | — | NC:64.6% | 724 |
| 60 | **TX** | very_high | `FireBoundaries/FS/0` | TX | OK / TX | TX:100.0%; bbox→TX:100.0% | 116,193 |
| 61 | **VA** | high | `Add_point/FS/0` | — | VA | VA:100.0%; bbox→VA:100.0% | 18,844 |
| 62 | **VA** | high | `Add_point_0524/FS/0` | — | VA | VA:100.0%; bbox→VA:100.0% | 18,842 |
| 63 | **ND** | very_high | `OpenDataHubLayers/FS/0` | ND | ND | ND:100.0%; bbox→ND:79.3% / MN:20.7% | 19,640 |
| 64 | **WI** | very_high | `ParcelsV10/FS/1` | WI | WI | WI:100.0%; bbox→WI:100.0% | 535 |
| 65 | **WI** | very_high | `ParcelsV10_view/FS/1` | WI | WI | WI:100.0%; bbox→WI:100.0% | 535 |
| 66 | **WA** | medium | `Generic_Photos_and_Captions_Survey_VIEW_LAYER/FS/0` | — | — | WA:67.2% / OR:26.6% | 64 |
| 67 | **WA** | medium | `service_48189ad1d7074d58856d07727687d617/FS/0` | — | — | WA:67.2% / OR:26.6% | 64 |
| 68 | **NH** | high | `VW_Base_Map_(View)/FS/0` | — | NH | NH:100.0%; bbox→NH:89.7% / MA:10.4% | 15,007 |
| 69 | **NH** | high | `pbBaseMap_View/FS/0` | — | NH | NH:100.0%; bbox→NH:89.7% / MA:10.4% | 15,007 |
| 70 | **NC** | high | `ADP_CTR/FS/0` | NC | — | NC:100.0%; bbox→NC:99.1% | 23,938 |
| 71 | **NC** | high | `Envirolink/FS/0` | NC | — | NC:100.0%; bbox→NC:99.2% | 23,126 |
| 72 | **NC** | medium | `Web_Map_Service/FS/4` | — | — | NC:100.0%; bbox→NC:99.2% | 23,126 |
| 73 | **TX** | very_high | `JimWellsCADAdditionalData/FS/3` | TX | TX | TX:100.0%; bbox→TX:100.0% | 16,300 |
| 74 | **TX** | very_high | `JimWellsCADWebService/FS/6` | TX | TX | TX:100.0%; bbox→TX:100.0% | 16,396 |
| 75 | **PA** | medium | `CivicRec/FS/0` | — | — | PA:100.0%; bbox→PA:100.0% | 8,364 |
| 76 | **PA** | medium | `CivicRec_view/FS/0` | — | — | PA:100.0%; bbox→PA:100.0% | 8,364 |
| 77 | **PA** | high | `MoonTwpPoliceEmergencyManagementMapping/FS/3` | — | PA | PA:100.0%; bbox→PA:100.0% | 13,440 |
| 78 | **PA** | high | `zMoonTownshipOverallBaseMapping/FS/1` | — | PA | PA:100.0%; bbox→PA:100.0% | 13,382 |
| 79 | **CO** | medium | `FAR2025_Basemap/FS/0` | — | — | CO:100.0%; bbox→CO:100.0% | 1,344 |
| 80 | **CO** | high | `Zoning/FS/0` | CO | — | CO:100.0%; bbox→CO:100.0% | 1,333 |
| 81 | **PA** | medium | `Base_Layers_View/FS/5` | TX | — | PA:100.0%; bbox→PA:86.2% / NJ:13.8% | 11,538 |
| 82 | **PA** | medium | `HistoricLocations/FS/3` | — | — | PA:100.0%; bbox→PA:86.2% / NJ:13.8% | 11,538 |
| 83 | **PA** | medium | `HistoricLocations_view/FS/3` | — | — | PA:100.0%; bbox→PA:86.2% / NJ:13.8% | 11,538 |
| 84 | **WI** | very_high | `City_Parcels_Public_View_Layer/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 4,058 |
| 85 | **WI** | very_high | `City_of_Shawano_Parcels_2019/FS/0` | WI | WI | WI:100.0%; bbox→WI:100.0% | 4,058 |

## 7. 人工复核的 8 层（`overrides.json`，逐条留证据）

| 层 | 机器结果 | 复核后 | 理由（节选） |
|---|---|---|---|
| `service_76dad3d0…/FS/1`、`survey123_7d6d0860…/FS/2` | NM/medium（E2 单路） | **unresolved/conflict** | 几何散列 NM 12%/MD 8%/OUT 60%，样本仅 2/5 在 NM |
| `Neighborhood_Code_Parcel_Data_Updated`、`RL_Parcels_NC_WebMap` | VT/medium（E1 说 NC） | VT/medium（保留） | E1 的 NC 来自描述里 "NC Parcel Data" 字样；几何 1000/1000 点在 Burlington VT（44.446446,-73.216376，`378 QUEEN CITY PARK RD`） |
| `EnerGov` | SC/medium | SC/medium（保留） | E1 的 TX 来自描述 "Tyler Parcel" 误命中；样本为 Kiawah Island SC 物业（PID/GPIN），几何 SC 100% |
| `GeoType_SAR` | CA/high | CA/high（保留） | E1 的 NY 来自 "Central Square"（同名 14 州）、CO 来自 owner 串误切；owner 域名 `ElSegundo.org`，几何 CA 100% |
| `CivicRec`/`CivicRec_view` | PA/medium | 保留 | E1 KS/OK 来自 owner `HarperB@3Phillies` 里的 Harper（已降级），几何 PA 100% |
| `Base_Layers_View` | PA/medium | 保留 | E1 的 TX 来自 `Falls Twp`（同名多州），几何 PA 100% |

## 8. 对三州试点的影响（一句话）

这 85 层里没有 DE、没有 IA，NH 只有 2 层（30,014 行，全是通用地址点 view）——**本批定州结果不足以改变第 7 步三州试点的任何数字**；Tier1 的瓶颈仍在 E7 地址键构不出来与 OA 空州行，不在「未定位层的州归属」。

## 9. 未跑项 / 拿不到的数

| 项 | 状态 | 原因 |
|---|---|---|
| Census 官方 `cb_2024_us_state_500k` / Gazetteer | unavailable | `www2.census.gov` 对本机出口返回 403（Cloudflare 拦截页），改用同源 TIGERweb REST |
| 全量要素的精确覆盖占比 | 未做 | 本轮按派单只采 1000 行/层；精确覆盖率需要逐层全量拉几何（85 层合计 20.7M 行），代价与产出不成比例 |
| 60% OUT 层的海外点归属 | 未做 | 不做海外/属地拆分，仅标注 OUT 占比 |
| 分档数据写回 | **不做** | 派单硬边界：本轮只出「层级建议归属」，写回由后续全量重认统一做 |
