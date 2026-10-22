# STEP 02 — 试点 8 层（试搬一户）

**目标**：用 8 个柜子把运货链路全部打通，验证「搬得动、运得走、数得清」。

**选样（覆盖三种形态 × 三档规模）**
| 层 | 形态 | 规模 |
|---|---|---|
| Kansas NG911 Address Points | FeatureServer | 104 万 |
| AZ911 AddressPoints | FeatureServer | 374 万 |
| DE SUSS Address Points | FeatureServer | 18 万 |
| ME Addresses | FeatureServer | 79 万 |
| 一个县层（< 5 万） | FeatureServer | 小 |
| 一个 Socrata 层 | Socrata | 中 |
| 一个 CKAN 包 | 文件下载 | 中 |
| 一个 MapServer 层 | MapServer | 小 |

**方法**
- FeatureServer：keyset 游标 `where=OBJECTID>{last} orderBy OBJECTID resultRecordCount={pagesize}`
- 判断有没有下一页看 `exceededTransferLimit`，不靠数到 count
- `f=geojson` 优先；不支持就 esriJSON + `outSR=4326` 自己转
- 每采 20~50 层打一个包传 Release，本机不留盘
- 每行算 `addr_key = hash(add_num|st_name|zip 归一化)`

**产出**：8 层 ndjson.gz + `_manifest.json`（count/实收/耗时/错误）+ Release 资产

**验收判据（机器判）**
- 8 层里至少 7 层产出行数 > 0
- 每层「实收行数 / 声明的 count」误差 < 1%，否则标 `partial`
- `addr_key` 空值率 < 2%
- Release 里能看到资产，且本地无残留文件

**失败怎么办**：某层失败就换该层的抓法重试；仍失败记录下来，用替补层补上，不因为一层卡住整体。

**本步一停必须叫醒我。**

**下一步**：`STEP-03.md`（单州试跑）
