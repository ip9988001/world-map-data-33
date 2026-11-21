# 05b reprobe 终态与 gap list 的账目对平（2026-11-21）

来源：`collect/ledger/05b_plan_probe_reprobe.json`（60 目标，07:46:52Z 起跑，elapsed 1295.2s，resume enabled、复用前次 2 层、新探 58）+ `collect/ledger/05b_plan_probe_retry.json`（retry1/retry2）+ `collect/ledger/05b_gap_list.json`（583 层快照）。

## 一句话结论

- **reprobe pending 37 = gap list pending 35（一层未动）+ 2 层由 retry1-alive 掉成 pending**。差额 +2 的来源就是这 2 层，不是「7 层 retry1-alive 全部掉进 pending」。
- **7 层 retry1-alive 并非都在 pending 37 里**：2 层 → pending、3 层 → unverified（403 `error code: 1010`）、2 层 → alive（Georgina ×2）。
- gap list 的 pending 35 层在 reprobe 中**零变化**；「3 转 unverified、2 转 alive」这 5 层不是从 35 里出去的，而是上面 7 层 retry1-alive 组里的 5 层。

## 交叉表（60 目标 = retry1 11 unverified + 42 pending + 7 alive）

| retry1 口径 | reprobe pending | reprobe unverified | reprobe alive | 合计 |
|---|---|---|---|---|
| retry1 pending 42 | 35 | 7（retry2 已判 unverified） | 0 | 42 |
| retry1 unverified 11 | 0 | 11 | 0 | 11 |
| retry1 alive 7 | **2** | **3** | **2** | 7 |
| 合计 | **37** | **21** | **2** | 60 |

与 gap list 的快照对照：pending 35（全部仍 pending）+ 2 = 37；unverified 18（全部仍 unverified）+ 3 = 21；alive 2 = 0 + 2。

## 明细：7 层 retry1-alive 的终态

| 层 | retry1 | reprobe | 证据 | gap class |
|---|---|---|---|---|
| `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | alive（http200 无 count） | pending | 4 tries / 258,540ms / `urlopen error timed out` | missing（expect 279,299） |
| `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` | alive（http200 无 count） | pending | 4 tries / 258,780ms / `urlopen error timed out` | missing（expect 15,033） |
| `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | alive | unverified | 4 tries / 18,503ms / HTTP 403 `error code: 1010` | missing |
| `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | alive | unverified | 4 tries / 18,468ms / HTTP 403 `error code: 1010` | missing |
| `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | alive | unverified | 4 tries / 18,503ms / HTTP 403 `error code: 1010` | missing |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | alive | alive | http 200 / 1 try / 1,108ms | partial（rows 20,570 / expect 23,246） |
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | alive | alive | http 200 / 1 try / 1,074ms | partial（rows 20,567 / expect 23,241） |

## 若把 reprobe 终态并入 583 快照

| 口径 | ok | partial | missing | unverified | pending | 合计 |
|---|---|---|---|---|---|---|
| 现行快照（retry2） | 1 | 6 | 523 | 18 | 35 | 583 |
| 并入 reprobe 终态 | 1 | 6 | **518** | **21** | **37** | 583 |

变化只有三格：missing −5（3 转 unverified、2 转 pending），unverified +3，pending +2。ok / partial 不动。

## 两条判读备注

1. **403 `error code: 1010` 是 Cloudflare 的 UA/浏览器签名拦截，不代表层已死。** 这三层按 `unverified` 记是对的（我们被挡，不是它没了），但不宜当死层永久放弃；要收复得改探针出口或 UA/Referer，属后续单独立项。
2. **alive ≠ 补齐。** Georgina 两层只有 http 200（count 未取到），rows 仍比 expect 少约 11.5%，继续按 `partial` 记，不许借 alive 转绿。
