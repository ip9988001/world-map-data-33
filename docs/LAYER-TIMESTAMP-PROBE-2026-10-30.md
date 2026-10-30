# STEP 09 前置：时间戳字段探测（只读元数据）

> 目的：回答「增量同步（09）到底能做多大一片」。**只读**：逐层 `GET <layer_url>?f=json`，
> 未发起任何 `/query` 数据请求、未下载任何 Release 资产本体。

## 一、范围与方法

- 已采层全集：扫全部 Releases（2,425 个 release / 25 页）→ `collect-step03|04|05|07|10-<layer>` 带 `-checkpoint.json` 的层，去重 **2327 层**（step04 308 / step05 1,468 / step07 436 / step03 111 / step10 53）
- 本次探测 **2327 层**（2026-10-30T22:18:16Z UTC），12 并发、单请求 10 s 上限
- 脚本：`analysis/scan_collected.py`（扫已采层）+ `analysis/layer_timestamp_probe.py`（逐层探元数据）

## 二、结论（一句话）

**928/2327 层（39.9%）可做增量**（有日期型编辑时间字段且服务支持高级查询）；**1127 层（48.4%）没有任何时间字段** → 只能全量重采；另有 117 层元数据拉不到（403/超时/服务下线），需单独重探。

## 三、六桶（逐层判定）

| 判定 | 层数 | 含义 |
|---|---|---|
| `incremental` | 928 | 有 **日期型** 编辑字段（`esriFieldTypeDate` 等）+ `supportsAdvancedQueries=true`，可直接 `where <field> > since` |
| `edit_field_no_date` | 104 | 有 `last_edited_user`/`lasteditor` 这类**字符串**字段 → 只能看人，不能按时间过滤 |
| `create_only` | 51 | 只有创建时间（无编辑时间）→ 只能做「新增」，改过的行抓不到 |
| `no_time_field` | 1127 | 元数据里完全没有时间字段 → 只能全量重采 |
| `no_meta` | 117 | 元数据请求失败（403 / 超时 / 服务下线），不是「没有字段」 |

按阶段拆（`incremental / no_time_field / no_meta`）：

| 步骤 | incremental | edit_no_date | create_only | no_time_field | no_meta |
|---|---|---|---|---|---|
| step 03 | 26 | 0 | 2 | 81 | 2 |
| step 04 | 116 | 7 | 16 | 134 | 32 |
| step 05 | 614 | 70 | 23 | 645 | 78 |
| step 07 | 160 | 24 | 10 | 230 | 4 |
| step 10 | 12 | 3 | 0 | 37 | 1 |

## 四、字段长什么样（决定 09 的 where 子句要用哪个名字）

日期型编辑字段 Top：`last_edited_date`(265)、`dateupdate`(237)、`editdate`(148)、`lastupdate`(137)、`edit_date`(51)、`updatedate`(35)、`updated`(22)、`l_update`(16)、`last_edite`(12)、`dateupdated`(12)

类型分布：esriFieldTypeDate 1083、esriFieldTypeDateOnly 4、esriFieldTypeTimestampOffset 1

## 五、09 的落地建议（等口号再动）

1. **只对 928 层 incremental 跑增量**，逐层生成 `where <该层真实字段名> > '<since>'`，产物一律打 `collect-delta-<layer>-<date>`，绝不覆盖全量 tag。
2. `no_time_field` 的 1127 层 + `create_only` 的 51 层 = **只能全量重采**，成本按全量估，不要混进增量的乐观数字里。
3. `no_meta` 的 117 层先单独重探一轮再定性（今天有 403/超时，不代表永久不可达）。
4. 探测结果按层落档（`analysis/layer-timestamp-probe-*.json` 的 `layers[]` 里有 `edit_fields[] / date_edit_fields[] / supports_advanced / service_last_edit`），09 直接读这份 JSON，不要重新探。

## 六、顺带做的重叠对账（防重复采）

07b 待采 **667 层**（`skip_done` 只认 `collect-step07-*`，所以专门查了一遍 04b/05b 有没有已顺手采掉）：

| 组 | 层数 |
|---|---|
| 07b_candidates_pending | 667 |
| 07b_done_step07 | 436 |
| already_done_step03 | 111 |
| already_done_step04 | 308 |
| already_done_step05 | 1468 |
| collected_layers_total | 2327 |

**重叠 0 层 → `no_double_collect`**：07b 的 667 层里没有任何一层已被 step03/04/05 采过；04b(272)/05b(2,770)/07b(667) 三份计划的层集合两两**交集为 0**（row 区间本来就不重叠：04b >300k、05b 5k~300k、07b 1~4,999）。

复现：

```bash
python3 analysis/scan_collected.py
python3 analysis/layer_timestamp_probe.py --timeout 10 --workers 16
python3 collect/full_plan.py --stage 07b --size 120 --out /tmp/07b_plan.json
python3 analysis/overlap_07b_vs_done.py
```
