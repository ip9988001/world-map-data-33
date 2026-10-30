# 定向区间补采（`--oid-range`）· 灰度第一区间对账（2026-10-30）

> 对象：NAD 全国层
> `UCXd1_arcgis_rest_services_USA_NAD_Addresses_FeatureServer_0`
> 区间：`[1, 999177]`（= 旧单元 `u00000` 的实测 OID 全域，1:1 可比）
> 产物：旧 `collect-step04-<layer>`（76 单元）vs 新 `collect-step04-<layer>-r2`（本次 1 单元）

## 一、做了什么（只加参数，没动口径）

| 改动 | 内容 |
|---|---|
| `pilot.py` | 新增 `--oid-range LO:HI`：**只换切分域的上下界**，`keyset` / `ids` / `plan_units` 一行未动 |
| 分母 | 区间运行时把「上游行数」换成**该区间内**的 `returnCountOnly`（否则 100 万行会被拿去和 7593 万行比，必然判 short） |
| tag | `OID_RANGE` 非空时 `_tag()` 追加 `-r2`（幂等），**绝不与旧单元抢同一个 Release** —— 抢了就 `--clobber` 覆盖，覆盖了就没有比对基准、也谈不上回滚 |
| 账本 | **不写**：灰度 workflow 不碰 `collect/ledger/*`、不提交任何文件，产物只进 `<tag>-r2` |
| 单测 | `collect/tests/test_oid_range.py` 8 条：r2 后缀幂等 / 区间拼接无缝无洞 / 分母口径 |

覆盖可证：上游 `outStatistics` min/max 实测 **OBJECTID ∈ [1, 75,937,418]**，且 `count = 75,937,418 = max`
（OID 连续无洞）；旧 76 单元 = `ceil(75,937,418/1,000,000) = 76` 段 × 每段 `ceil(75,937,418/76) = 999,177`
个 OID ⇒ `[1,999177]` 正是第 1 段。灰度区间落在旧单元内，行数可 1:1 对账。

## 二、执行记录

| 项 | 值 |
|---|---|
| workflow | `collect-oid-range.yml`（独立并发组，不排队挡在跑的阶段后面） |
| run | **41130212146**（成功；前两次 41127719288 / 41129462009 是上传链路故障，见第四节） |
| 区间上游 count | 999,177 |
| 实采 | **999,177**（`diff=0.0`，`pilot_rc=0`），耗时 395 s |
| 产物 | `…-r2` tag 下 `u00000.tar.gz` 30,211,879 B + checkpoint 1,006 B |

## 三、对账结果（`collect/compare_oid_range.py`）

```
old_rows = 999,177      new_rows = 999,177      upstream_count_in_range = 999,177
only_old = 0            only_new = 0            ← OID 集合零差（既不漏采也不重采）
抽样 1,000 行逐字段比：26 个字段，24 个 1000/1000 全等
```

| 字段 | 一致 / 1000 | 说明 |
|---|---|---|
| `raw.OBJECTID` `raw.addr_*` `raw.source` `raw.building` | 1000 | 上游原始属性逐字节相同 |
| `add_num` `pre_dir` `st_name` `st_suf` `post_dir` `unit` `city` `zip` `esn` `addr_key` | 1000 | 归一化字段全等 |
| `lat` `lon` | 1000 | 坐标值全等 |
| `src_layer` `src_title` | 1000 | 全等 |
| **`_lat` / `_lon`** | **0 / 1000** | **旧产物没有这两个键；新产物按契约给出（值与 `lat`/`lon` 相同）** |

`verdict = rows_identical_fields_differ`（脚本按严格口径判的）。

### 差异到底是不是「数据不一致」——不是，是「旧产物缺契约字段」

- 抽 7 个旧单元（u00000/1/2/3/10/11/12）× 每单元 4,000 行：`_lat` 非空 = **0**。
  即 **旧 NAD 全层 76 个单元都没有 `_lat`/`_lon` 键**（08:22 采集时 pilot 还没这条契约）。
- 新产物 `_lat/_lon` = 该行几何坐标，且与归一化 `lat/lon` **逐行相等**。
- 所以关系是「新 ⊃ 旧」：行数、OID 集合、其余 24 个字段**零差**；新产物多两个契约键。

## 四、灰度期间踩到的真问题（已修，不是数据问题）

| run | 现象 | 根因 | 处置 |
|---|---|---|---|
| 41127719288 | `rows=999177` 全对，但 `✗ 上传失败 release not found` | `gh release create` 失败的真实原因被 upload 的报错盖掉（`_upload` 只打最后一条错误） | `_upload` 把 create / upload 错误分开记 |
| 41129462009 | 自检 `create_rc=1`：`error checking for existing release: HTTP 403` | GITHUB_TOKEN 对该次调用 403（14 个 shard 同时在打 Releases API，判为瞬时/次级限流；同一分钟内 05b 的 `gh release create` 是成功的） | 自检步骤原样打 `gh auth status` + create/upload 输出；`fetch-depth: 0`；产物兜底 artifact |
| **41130212146** | `create_rc=0` / `upload_rc=0` / `assets=2` | 403 不可复现 ⇒ 瞬时 | 已确认上传链路正常 |

## 五、闸门判定（按你定的硬边界）

- 行数：**999,177 / 999,177 / 上游 999,177** —— 三段对齐。
- 字段：**24/26 字段 100% 一致**，第 25、26 个字段（`_lat/_lon`）是**旧产物缺失、新产物补齐**。
- 因此严格口径下 `verdict ≠ identical`。按你的规矩「不一致就回滚」的字面含义，
  **本区间不算通过，不自动铺满全层**（4~8 区间轮转**未启动**）。

要放量需要你一句话，两条路二选一：

1. **认「新 ⊃ 旧」为通过**：`_lat/_lon` 是契约补齐（值 = 现有 `lat/lon`），不改变任何既有字段的语义 →
   按 4~8 区间轮转跑满全层，旧 76 单元保留不动（r2 全部落在 `<tag>-r2`，随时可弃）。
2. **认「必须逐字节相同」为通过**：那 r2 就得抹掉 `_lat/_lon`，与契约
   （`test_pilot_centroid_contract`：`_lat/_lon` 恒存在）冲突 → 不建议，且需要先改契约。

## 六、附带发现（重要，影响 04b 是否 complete）

旧 NAD 76 单元**行数齐全但缺 `_lat/_lon`**。凡下游按 `_lat/_lon` 判县/落点的环节，对 NAD 这 7593 万行
等于没有几何坐标（虽然 `lat/lon` 有值）。这不是本次改动的锅，是 08:22 那轮采集的产物早于契约。
要不要补，取决于下游是否只读 `_lat/_lon` —— 这一点需另行确认，本文不代为决定。
