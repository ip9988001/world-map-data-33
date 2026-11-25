# method — tier1 未定位 85 层定州方法（tier1-locate-20261125）

> 本文件写清「怎么取证、阈值多少、参照数据从哪来（含 sha256）、怎么复算」。
> 全部数字都能用本目录脚本 + 原始响应重算；不出现「大致在某州」这类推断。

---

## 1. 输入与口径

| 项 | 值 |
|---|---|
| 输入文件 | `analysis/auto-spatial-relax-20261125/auto-recognized.csv`（只读，未改动） |
| sha256 | `cc60a834625617c1a3a2a4c171217171a95372441561dabb4f4b93d3d4fb812b` |
| 全表行数 | 17,168 |
| tier1 行数 | 176 |
| tier1 且 `state=未定位` | **85**（unique url = 85，url 即主键；`layer_id` 只有 10 个不同值，不能作键） |
| 85 层 `rows_n` 合计 | 20,766,446 |
| 几何类型 | point 62 / polygon 22 / polyline 1 |
| `assign_reason` | template_unresolved 74 / geom_unsupported 8 / share_below_1pct 2 / no_golden_evidence 1 |

原始清单：`tier1-unlocated.csv`（layer_id/url/dialect_id/rows_n/state/assign_reason）。

## 2. 三路证据（各自打分、分列存盘，不合成黑箱分）

### E1 · 服务/条目元数据（最硬的一路）

逐步取：

1. `GET <layer>?f=json` → `name` / `description` / `copyrightText` / `serviceItemId` / `extent`
2. `GET <service 根>?f=json` → `serviceDescription` / `description` / `name`
3. `serviceItemId` → `GET https://www.arcgis.com/sharing/rest/content/items/<id>?f=json` → `title` / `snippet` / `description` / `accessInformation`
4. `item.owner` → `GET https://www.arcgis.com/sharing/rest/community/users/<owner>?f=json` → `fullName` / `description`

从上述文本里抽：

- **显式州名**（50 州 + DC 全称，词边界、忽略大小写）→ 强证据；
- **独立大写两字母州缩写**；其中易与普通词冲突的 17 个（`IN OR ME OK DE HI LA MS AL AR CA CO ID MA MD PA OH MT`）**只认地址形态**（`, XX` 或 `XX 12345`），否则不算；
- `*.xx.us` 域名里的州缩写；
- **县名 / 地名 → 候选州**：按「连续大写词短语」在 `counties-index.json` / `places-index.json` 里查；同一个名字在 **>6 个州**出现的（`Washington`、`Dover`、`Wilkes` 这类）**只记录、不投票**；单字地名同名 >1 州的（`Harper`/`Tyler`/`Falls`）同样丢弃；
- `item.owner` 账号串也进 E1 文本池（`SanClementeGIS` / `MinongGIS` / `ElSegundo` 这类自带地名），驼峰先拆词。

预处理：先剥 HTML 标签与 CSS 片段（AGOL `item.description` 常是整段 HTML 表格，`style=` 里会造出假 `ID`/`IN`），再剥邮箱。

### E2 · 属性样本

1. `GET <layer>/query?where=1=1&outFields=*&resultRecordCount=5&returnGeometry=false&f=json` 取 5 条全字段样本；
2. 从 `fields` 里挑州/县/市/zip 字段做 `returnDistinctValues=true&resultRecordCount=200`；
   `st_name` / `st_num` / `street` 等 NG911 街名字段**明确排除**（名字里带 `st` 但值是街名，会造出假州）；
3. 州字段取值 → 州缩写集合；**该字段 >3 个州 ⇒ 判为多州/邮寄地址口径，不作单州证据**（只记录）；
4. 县/市字段取值走 `counties-index` / `places-index`（全国唯一命中才算）；
5. 样本里地址串命中 `, XX 12345` → 计州；地名形态字段（`city/town/muni/place/communit/hood/village/parish/county/msag/locality`）的值走地名清单（唯一命中才计）；
6. zip 前缀只写进 note，**不进投票**。

### E3 · 几何

1. `GET <layer>/query?where=1=1&returnExtentOnly=true&outSR=4326&f=json` → 图层 bbox（WGS84，服务端重投影，不自算投影）；
2. `GET <layer>/query?where=1=1&outFields=*&resultRecordCount=1000&outSR=4326&returnGeometry=true&f=geojson&geometryPrecision=6` → 最多 1000 条几何；面取 shapely 质心、线取中点、点即点；
3. 点落入哪州用 `shapely.PreparedGeometry.contains`，近岸/边界再放 0.002°（≈200m）容差重判一次；
4. **点落州占比**（`e3_states`，小数=占比）；bbox 与各州求交的**面积占 bbox 比**（`bbox→` 后缀）只作展示与交叉核对——bbox 是矩形，必然外扩到邻州（SC 的 bbox 里有 20% 在 GA），**不能拿来判跨州**；
5. 投票门槛：**采样最高占比 <20% ⇒ 该层几何判为「散列」，不投票**（只记录），避免从 12% 里挑一个州；
6. 对照：同一批点再用仓内 `survey/ng911/us_states.json`（约 1:20m 粗界）跑一遍，纯度差 >5 个百分点写进 note（海岸线外点会被粗界判 OUT，如 Lee County FL 8/27）。

### E4 · 名字兜底（只做 tie-break）

`layer.name` + url 路径命中州名/州缩写/县市名，**单独一路，不计入「≥2 路一致」**，只在前三路并列时用来挑一个。

## 3. 定州规则（写死在 `assign.py`，与派单原文一致）

1. 投票只算 E1 / E2 / E3；E4 只做 tie-break。
2. `state_final` = 三路里出现次数最多、且出现在 **≥2 路**的州：2 路一致 `high`，3 路一致 `very_high`；只有 1 路有线索 `medium`。
3. 三路互相冲突且无多数 → `unresolved` / `conflict`，候选全列。
4. 完全无线索 → `unresolved` / `none`。
5. 跨州层 → `state_final` 写占比最大州，另列 `states_covered`，`multi_state=true`。
6. 输出列固定 18 列（见 `tier1-unlocated-states.csv` 表头）。

实现里对第 5 条的**口径收紧并写明**：`multi_state=true` 判据 = 采样点落州占比（不是 bbox，理由见 E3-4）中出现 **≥2 个州各 ≥20%**，或最高占比 <50% 且 ≥3 个州各 ≥5%。派单原文「任一州 E3 覆盖 ≥20%」若按 bbox 执行，会让每一个全州层都被判跨州（矩形外扩），故以点占比为准并在报告里逐层披露 bbox 外扩情况。

## 4. 参照数据（全部落 `ref/`，含 sha256）

| 文件 | 用途 | 来源 | sha256 |
|---|---|---|---|
| `tigerweb-states.geojson.gz` | **主用**州界（51 个：50 州 + DC） | TIGERweb `State_County/MapServer/0`，`outSR=4326&maxAllowableOffset=0.002`（≈200m 简化） | `e28e9f8af7a88b7152ab1015ec541e62dcfe94f87ccf761924f66d2a57315b89` |
| `counties-index.json` | 县名 → 州（1,834 个名字 / 50 个州文件） | 仓内 `analysis/tiger_county/*.json.gz`（TIGERweb `State_County/1` 派生） | `e4ac0ffc3a0f893a984ac650af7d8e2e91b04938561f5d118b1b071acbb048ed` |
| `places-index.json` | 地名 → 州（20,711 个名字 / 32,642 行） | TIGERweb `Places_CouSub_ConCity_SubMCD/4`（Incorporated Places）+ `/5`（CDP） | `575717a96d9c663119ab03590ea71240fbb8eb74f7a544107e5af14a8daccb8c` |
| 对照：仓内 `survey/ng911/us_states.json` | 粗界交叉核对（不复制进本目录） | 仓内既有资产 | `6f23ed91fce2c25d57c01d83225342ba40258e9571c486c3999bd827c80d193b` |
| `geom1000.tar.gz` | 85 层采样几何原始响应（80MB → 8.2MB） | 本目录 `locate.py e3` 抓取 | `a7105279da05ac0c2e2b5f22a55a24ce0683c39c8c24bec06839146119ea9bab` |
| `agol/*.json` | 每层 layer/service/item/user 元数据 + extent4326 + distinct 原始响应 | 同上 | 逐文件见 `git ls-tree` |

Census 官方 `www2.census.gov` 在本机出口返回 **403**（Cloudflare 拦截页），故州界/地名改用同源的 TIGERweb REST 服务；`ref/refs.meta.json` 记了完整请求 URL。

## 5. 复算命令

```bash
cd analysis/tier1-locate-20261125
python3 locate.py e1        # 85 层元数据（网络，约 2 min；结果落 ref/agol/）
python3 locate.py e2        # 属性样本 + distinct（约 2 min）
python3 locate.py e3        # bbox4326 + 1000 行采样几何（约 6 min）
python3 refs.py             # 州界 / 县名 / 地名参照（约 3 min）
python3 assign.py           # 三路 → 定州，写 tier1-unlocated-states.csv
python3 dist.py             # 写 state-distribution.json
```

- `assign.py` 会按需解压 `ref/geom1000.tar.gz`（`ensure_geom()`），不需要重新抓几何。
- 人工复核意见在 `overrides.json`（8 层，逐条给了理由与证据），`assign.py` 会把它并进 `note`，**不会改证据列**。
- `_work/` 是可重建中间件（已 gitignore）。

## 6. 已知误差与边界

1. **E1/E2 都依赖字符串与清单匹配，是启发式**：同名小地名（`Harper`、`Tyler`、`Central Square`）、命名沿用（`NC Parcel Data` 实际是 Burlington VT 的层）都会误命中。因此 E1/E2 单独一路只给 `medium`，并在 `note` 里原样留下命中片段供复核；8 层因此做了人工复核（见 `overrides.json`）。
2. **州界简化 200m**：边界附近的点可能判给邻州；全州层的纯度不受影响（实测 1000 点纯度 100% 的有 62 层）。
3. **采样 1000 条不是全量**：`e3_states` 是占比，不是精确覆盖率；`rows_n` 与采样量在 `tier1-unlocated.csv` / `tier1-unlocated-states.csv` 里都能对。
4. **OUT 点**：`_OUT` 占比写进 note = 点落在 50 州 + DC 之外（州界外/水域/几何为空/全国性调研点）。最高 OUT 是 `service_76dad3d0…`（60%，全国性调研层）。
5. **本轮不写回任何分档数据**：`auto-recognized.csv` 只读，state 列未改；建议归属待后续全量重认统一落库。
