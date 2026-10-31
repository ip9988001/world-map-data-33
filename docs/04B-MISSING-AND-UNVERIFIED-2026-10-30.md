# 04b · `missing 7` 与 `unverified 6` 的取证（2026-10-30）

> 原则：`missing` 必须是「上游有 N 行 / 本层 0 行」的**证据链**，`unverified` 必须是
> **跨时段重复观测**（一次超时只能算噪声）。两者都不许互相顶替，更不许归到 `empty`。

## 一、`missing 7` —— 上游活着，本层 0 行（= 真缺口，必须重采）

证据文件：`analysis/04b-missing-evidence-2026-10-30.json`
方法：`GET <layer_url>/query?where=1=1&returnCountOnly=true&f=json`（只读上游，不采数据）

| 层 | 上游 returnCount（实测） | 账本 declared | 账本 rows | Release 单元包 | 原片结局 |
|---|---|---|---|---|---|
| `cgis_rest_services_SAM_Address_Points_Symbolized_MapServer_0` | 6,585,376 | 6,585,376 | 0 | 0 | 片 7 / failure |
| `s_ny_gov_arcgis_rest_services_SAM_Address_Points_MapServer_0` | 6,585,376 | 6,585,376 | 0 | 0 | 片 9 / cancelled |
| `_secure_rest_services_AddressNC_NC1Map_Addresses_MapServer_0@未定位-1` | 6,297,169 | 6,297,169 | 0 | 0 | 片 2 / cancelled |
| `vices_AGOL_AddressPts_for_NG911AddressFinder_FeatureServer_0` | 3,618,012 | 3,618,012 | 0 | 0 | 片 1 / cancelled |
| `ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1` | 2,220,021 | 2,220,021 | 0 | 0 | 片 1 / cancelled |
| `_rgv911_org_server_rest_services_Public_Map_MIL1_MapServer_1` | 303,175 | 303,175 | 0 | 0 | 片 10 / cancelled |
| `_rgv911_org_server_rest_services_RGV911_OPS_MIL1_MapServer_0` | 303,175 | 303,175 | 0 | 0 | 片 2 / cancelled |
| **合计** | **25,912,304** | **25,912,304** | **0** | **0** | — |

三点结论：

1. **上游全活**，且返回行数与 `layer_plan.csv` 的声明值**逐层完全相等**（7/7 相等，无一例外）
   ⇒ 这 25,912,304 行不是「上游没数据」，是**我们一行都没采到**。
2. **Release 上零资产**（`parts_assets=0`，取证时刻的快照），所以不是「采了没上传」，是**当时压根没采**：
   6 层挂在 `cancelled` 片（另 1 层在 failure 片），与「片被掐成 cancelled → 整片零痕迹」的历史事故同源。
3. **它们已在跑**：定向 run `41121952357`（feat/gold-intake，20:17 起，未取消）的 plan 是 3 片 × 6 层，
   正好覆盖这 7 层 + 6 层 unverified + `FLEXMOBILE`。跑完按 `ledger_rebuild --check` 复验。

## 二、`unverified 6` —— 3 轮跨时段重测（当前已完成 2 轮）

证据文件：`analysis/unverified-04b-2026-10-30.json`（脚本 `collect/retest_unverified.py --append`，
**间隔 < 30 分钟会被脚本自己拒绝追加**，所以「三次同秒」这种假重测不可能发生）

| 轮次 | 时间（UTC） | 距上轮 |
|---|---|---|
| 轮 1 | 2026-10-30T20:57:34Z | — |
| 轮 2 | 2026-10-30T21:29:08Z | 31.6 分钟 |
| 轮 3 | 2026-10-30T22:00:13Z | 31.1 分钟 |

| 层 | 轮次 | 可达次数 | HTTP / 错误 | 终判 |
|---|---|---|---|---|
| `tyil_gov_traditional_rest_services_cookVwrDynmc_MapServer_63` | 3 | 0 | 超时 ×3 | unreachable_all_rounds |
| `yil_gov_traditional_rest_services_addressZipCode_MapServer_0` | 3 | 0 | 超时 ×3 | unreachable_all_rounds |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | 3 | 0 | 超时 ×3 | **见下：CI 侧可达（已采成）** |
| `is4_ocfl_net_arcgis_rest_services_AGOL_Open_Data_MapServer_0` | 3 | 0 | 超时 ×3 | unreachable_all_rounds |
| `g_rest_services_Basemap_Address_Points_EagleView_MapServer_0` | 3 | 0 | **403 ×3** | unreachable_all_rounds（服务活着、不给读） |
| `rest_services_Countywide_Layers_Cagis_Map_Labels_MapServer_5` | 3 | 0 | 超时 ×3 | unreachable_all_rounds |

### ⚠️ 重要限定：这里是「从本机不可达」，不等于「从 CI 不可达」

反例已出现：`rvices_location_Address_Points_Modifications_FeatureServer_0` 本机 3 轮全超时，
但定向 run `41121952357` 在 GitHub runner 上把同一层采到 **1,369,487 行 / 2 个单元包**
（`ledger_rebuild` 里已转 `ok`）。所以：

- 本文的 `unreachable_all_rounds` 只能当**本机观测**结论；
- 去留判据要加一条：**若该层在任一采集轮里出现了单元包/行数，就不再是 `unverified`**，按实测行数重判；
- 这也是「不许拿不可达当 `empty`」的正面证据：说「不可达」的层，换个出口就能采到。


判据（写死在脚本里）：

- 3 轮全不可达 → 账本**保持 `unverified`**，文档写「上游不可达，未验证，非空层」；
- 任一轮可达 → 变 `alive`，按上游行数重判（有数但本层 0 行 ⇒ `missing`，必须重采）；
- 这 6 层**不进缺口分母**，单列「不确定行数区间」：`low = 0`，`high = 5,605,041`
  （声明值之和，来自 `layer_plan.csv`，未经上游确认，只能当上界）。
  ⇒ 84.51% 这类比例既不被它们稀释、也不被它们抬高。
- 另注意 `EagleView` 是**连上但被拒（403）**，与「超时」不是一回事：它说明**服务活着、只是不给我们读**，
  更要留在 `unverified` 而不是 `empty`。

## 三、顺带查出的一处「声明值本身不可验证」

`partial` 里最大的那层 `s_Points_from_National_Address_Database_view_FeatureServer_0`
（账本：declared 97,928,946 / rows 39,875,268 / 缺口 58,053,678）本轮重探上游返回：

```
HTTP 200  {"error":{"code":499,"message":"Token Required","messageCode":"GWM_0003"}}
```

即**该服务现在要 token 才给读**（已不是公开可查层）。这意味着：

- 它的 `declared`（9792.9 万）**无法再复核**，不能继续拿它当「我们欠 58M 行」的证据；
- 也不该因此把它改判 `empty` 或 `ok`（那是拿口径凑数）；
- ~~正确去向是 `unverified`~~ **【2026-10-31 改判】**：更进一步，这层已是**服务级 token**
  （`/0?f=json` 也 499，连续两轮一致）→ 状态改为 **`capped_by_upstream`**：
  已采 39,875,268 行照旧计入 `rows`，97,928,946 移出分母记 `declared_unverifiable`。
  依据 `analysis/04b-token-499-evidence-2026-10-31.json`，落点 `collect/04b_ledger.json`，
  来龙去脉见 `docs/STEP04-ADJUDICATED-2026-10-30.md` §3.0 与故障清单 `W33-033`。

其余 `partial` 4 层里，两层的声明值已被上游确认（`LBRSforLocator` 5,573,001 = 声明；
`COTGEO` 525,381 = 声明 ⇒ 缺口 2,799,879 / 46,381 是真缺口，且两层都在定向 run 的 plan 里）；
另两层的上游本轮超时（`Ky_911_Site_Structure`、`PlatTracker`），需并入 `unverified` 重测队列。

## 四、04b 是否 `complete` 的判词

**不成立。**

缺口 `89,314,341` 行可拆成四块，缺什么就一目了然：

| 块 | 行数 | 现状 | 补齐条件 |
|---|---|---|---|
| `missing 7` | 25,912,304 | 上游全活、本层 0 行（证据齐全） | 定向 run `41121952357` 跑完并落账 |
| `partial` 可验证缺口 | 2,846,260（LBRS 2,799,879 + COTGEO 46,381） | 上游确认有数、本层短采 | 同上（两层都在定向 run 的 plan 里） |
| `partial` 声明不可验证 | 58,053,678（NAD view 层） | 上游 499 Token Required | 拿到 token 重验声明；否则改判 `unverified`、移出分母 |
| `unverified 6` | 声明 5,605,041（**不计入分母**） | 2/3 轮不可达 | 第 3 轮 + 判定 |
| `empty 1` | 367,002 | 上游 0 行 / 服务 404 | 无需补（口径正确） |

⇒ **complete 成立需要三件事同时到位**：
① 定向 run `41121952357` 跑完且这 9 层（7 missing + 2 partial）全部 `ok` 或给出上游确证的短采理由；
② NAD view 层拿到 token 复核声明值（或按 `unverified` 移出分母并写进文档）；
③ 6 层 `unverified` 走完 3 轮重测并给出终判。

## 五、现状更新（21:45 → 22:05 UTC 快照）—— 上面是「刚取证时」的状态，这里是「正在被填」的状态

⚠️ 先纠正我自己的一个误读：**不能拿 `gh release list` 的 `created_at` 判断有没有在采** ——
往**已存在**的 tag 继续传资产不会改这个时间。要看「有没有在采」，唯一可信的是
`ledger_rebuild` 里的 `parts_assets`（资产数）。按资产数看，定向 run 一直在干活：

| 层 | 取证时 | 21:45 现状 | 说明 |
|---|---|---|---|
| `UyC7jAmu_…_LBRSforLocator_FeatureServer_0` | failed / 2,773,122 行 / 3 包 | **ok / 5,573,001 行 / 7 包** | = 上游 count，缺口补齐 |
| `fD_…_COTGEO_ADDRESS_POINT_FeatureServer_0` | partial / 479,000 / 1 包 | **ok / 525,381 / 1 包** | = 上游 count |
| `ces_Ky_911_Site_Structure_…_MapServer_0` | failed / 2,416,763 / 3 包 | **ok / 2,489,597 / 4 包** | 已补齐 |
| `rvices_location_Address_Points_Modifications_FeatureServer_0` | unverified（403）/ 0 包 | **ok / 1,369,487 / 2 包** | 那层 403 是可采的 |
| `t01_…_PlatTracker_PT365_PLAT_MAPPING_MapServer_5` | partial / 310,418 | partial / 310,520 | 仍差 4,524 |
| `_secure_…_NC1Map_Addresses_MapServer_0@未定位-1` | missing / 0 行 / 0 包 | **6,648,000 行 / 4 包（进行中）** | 已在采，未收官 |

口径变化（`ledger_rebuild` raw 口径；两次快照都不含任何 run-id 误输入）：

```
          rows             gap           gap_pct        ok/partial/failed
21:45  495,110,230      85,696,256       14.7547       254 / 3 / 15
22:05  497,330,251      83,476,235       14.3725       255 / 3 / 14     ← 定向 run 仍在跑，数字还会动
```

已转 `ok` 的层（含 `missing` 转正）：
`ervices_us_mn_state_mngeo_loc_addresses_open_FeatureServer_0@未定位-1`
**2,220,021 行 = 上游 count**（原来 0 行 0 包）；`_services_AGOL_AddressPts_for_NG911AddressFinder_MapServer_0`
3,618,012 行（= 声明）；`_secure_…_NC1Map_Addresses@未定位-1` 已有 6,648,000 行 / 4 包（未收官）。

⇒ 所以「complete 不成立」是**当下判词**，不是终局：缺口正在被定向 run 填。
等 `41121952357` 跑完（job 上限 20:17 + 350 min）再按 ① 复验一次 `ledger_rebuild --check`，
IDENTICAL 才叫「账本对资产说真话」。

## 六、两份重建文件的分工（2026-10-31 定，别再用混）

`collect/ledger/` 下现在有**两份**看起来同源的重建产物，职责完全不同：

| 文件 | 角色 | 会不会变 | 用途 |
|---|---|---|---|
| `step04b_rebuilt_20261030-committed.json` | **审结快照**（`frozen_at` / `frozen_sha` / `frozen_from_commit` 写在文件头） | **永久不动**，任何重算都不许改它 | 历史对账的参照：2026-10-30T20:18:28Z（`3223b4e`）那一刻的审结版本 = 272 层 / 490,821,547 行 / ok250·partial4·failed18 |
| `step04b_rebuilt.json` | **活态重建**（`ledger_rebuild` 从 Release 资产算出来的当前真值） | **会变**，资产变了它就变 | 回答「现在资产到底有多少行」；workflow/复核都用这一份 |

为什么分成两份：活态文件如果被当成「历史真值」冻住，后面每一层新进展都进不了账（账本会永远停在
490.8M，正是 2026-10-30 那次的形态）；反过来，如果活态文件被当成对账基准，那「重算」就等于
「改历史」，两次事故的对账就再也做不成了。**审结对账看快照，现场判断看活态。**

### `--check` 的语义已改（2026-10-31 用户定）

旧语义：重算后**跟历史文件比字节**（`IDENTICAL` 才叫对）。这会逼人把活态文件冻死 —— 资产一有进展就
永远 `DIFFERS`，只能靠「别重算」来维持绿色，等于把「账本在说真话」换成「账本没动」。

新语义：**同一输入 → 同一输出**。产物里带 `input_fingerprint`（`collect-ledger-input-fingerprint/v1`）：

- 逐层取**资产名 + 字节**（Release 侧）、**checkpoint 内容摘要**（`ckpt_sha256`）、**声明行数**；
- **不含** asset id / 上传时间 / `now()` / `scan_meta` —— 重传同内容会换 id，那是「资产重发」，不是输入变了；
- `--check` 重算指纹并与产物里的指纹比对：一致 → `IDENTICAL（输入指纹一致 digest=…）`，不一致 → `DIFFERS`
  并**点名变了几层、哪几层**；
- 所以「账本对资产说真话」的判据变成：**指纹一致的 `IDENTICAL`**，而不是字节没变。

```
python3 collect/ledger_rebuild.py --stage 04b --check     # 只比输入指纹，不写盘
```

### checkpoint 证据被覆盖时：`--asset-evidence`

checkpoint 被 force 重跑整份覆盖（2026-10-30 22:23Z 的 NAD view 事故）后，`judge()` 只能判
`failed(0)` —— 数据在、证据没了。这时 `--asset-evidence analysis/nad-view-rebuild-2026-10-31.json`
（`collect/rebuild_layer_rows.py` 的逐包数行产物）会把 rows 补回来，条件是**指纹对得上**：
证据里每个包的 `name + asset_bytes` 与当前 Release 逐个相等、`packages_bad` 为空、`recheck.ok=true`。
任一条不满足就**不采用**（宁可 failed，也不拿旧实测洗账）。采用后该层：

- `rows_src = rebuild_from_assets`
- `evidence = {rebuild: <证据 JSON 路径>, kind: release_assets_recount, packages, parts, generated_at}`
- 声明值仍拿不到（上游 499 Token Required）⇒ 状态是 `partial`，缺口照旧单列，**不因补回 39.8M 就变 ok**。
