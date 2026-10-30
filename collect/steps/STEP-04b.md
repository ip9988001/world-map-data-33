# STEP 04b — 全州放量（全量补采）

> **判据卡 v2.1（补采变体）**　工头：`collect/supervisors/step_04b.py`　工人：`.github/workflows/collect-full.yml`（stage=04b）
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
04 是「一次拿大部分人口」的通用放量，历史上有 272 层因 matrix 上限 / 单元没跑完而留在 pending。
04b 只做一件事：**把 `row_count > 300000` 的层补完，一层不留**。
它与 04 的全部差异：

| 差异点 | 04 | 04b |
|---|---|---|
| 已采层 | 重采（幂等覆盖） | `skip_done=true` 直接剔除，只补缺口 |
| 执行方式 | 一层一个 matrix job | 分片：**一片一个 job，片内顺序跑 20 层** |
| Release tag | `collect-step04-<layer>` | 同上（**共用命名空间**，续跑判定才对得上） |

## 输入
`layer_plan.csv` 里 `row_count > 300000` 的层，减去 `done_from = 04` 判为已完成的层
（判定 = Release tag 命中 + 本机 audit；两处都不认，宁可重跑也不漏层）。

## 产出 / 证据
`collect/ledger/04b_plan.json`（分片计划）→ `collect/ledger/step04b_shard<N>.json`（逐片逐层账本）
→ `collect/step04b_ledger.json`（合并）→ `collect-step04-<layer>` Release 资产（part + checkpoint）

证据清单：`report`、`releases`、`checkpoint`、`unit_errors`

## 怎么做
- `collect/full_plan.py` 先切片（默认 20 层/片），片数上限 250（GitHub matrix 硬顶 256，留余量）
- 每片一个 job 调 `collect/full_shard.py`；片内逐层跑 `collect/run_step_04b.py`
- 每层四态之一：`ok` / `empty` / `partial` / `failed`（外加 `skipped_done`），**全部落账**
- 单层 3h 硬超时；失败层必须带原因（rc / err / 差额），**不吞错、不 `|| true`**
- 实采与声明差 > 0.2% 记 `partial`：不是失败，但收官文档必须写清是「单元没跑完」还是「计划期口径差」
- 每单元完成即传即删；checkpoint 在 Release 上，重跑只补缺口

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `total_rows_min` | ≥ 30000000 | 累计实收行数下限 |
| `layers_min` | ≥ 40 | 覆盖层数下限 |
| `layers_max` | ≤ 60 | 覆盖层数上限（超了说明选层口径跑偏） |
| `per_layer_rows_max` | ≤ 5000000 | 单层实收上限（超了说明口径不对） |

## 失败怎么办
单层失败只影响该层（`fail-fast: false`），记 failed 继续；本阶段 failed ≠ 0 就**不自动接续**下一阶段，
停在原地等人看账本。同一 host 反复 5xx 降到 1 并发；额度接近上限时主动停并在简报写明。

## 命令（照抄）
```bash
python3 collect/full_plan.py --stage 04b --size 20 --out collect/ledger/04b_plan.json
python3 collect/full_shard.py --stage 04b --shard 0 --plan collect/ledger/04b_plan.json --workers 4
python3 collect/step_full_report.py --stage step04b
```

## 卡死阈值
`stall_min = 300` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "04b",
 "kind": "collect",
 "title": "全州放量（全量补采）",
 "select": {
  "where": "row_count>300000",
  "title_include": "address|addr\\b|situs|e-?911|ng911|mailing|delivery point|location point",
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 1000000,
 "unit_bytes": 1500000000,
 "tag": "collect-step04-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "unit_errors"
 ],
 "accept": {
  "total_rows_min": 30000000,
  "layers_min": 40,
  "layers_max": 60,
  "per_layer_rows_max": 5000000
 }
}
```
