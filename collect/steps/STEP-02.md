# STEP 02 — 试点 8 层

> **判据卡 v2.1**　工头：`collect/supervisors/step_02.py`　工人：`.github/workflows/worker-02.yml`
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**——
> 改参数只改 steps.json，然后跑 `python3 collect/check_docs.py` 校验一致。

## 目标
8 个典型层各采一遍，验证三条通道（keyset / resultOffset 兜底 / ids）与断点续传在真实数据上成立。

## 输入
`collect/pilot_layers.json`（8 层：三种形态 × 三档规模）

## 产出 / 证据（工头只递这些事实）
每层 `part-*.ndjson.gz` + `<layer>-checkpoint.json`，全部落 Release `collect-step02-<layer>`；`collect/pilot_report.json`

证据清单：`report`、`releases`、`checkpoint`、`short_units`

## 怎么做
- 单元粒度 `unit_rows`，单元完成即 `gh release upload`（本机不留盘）
- 检查点随 tag 固定（不带 run_number），换 run 也能接上
- `returnIdsOnly` + `objectIds` 兜底：服务用 HTTP 200 包 `{"error":...}` 时必须识别，不许静默退化成 2000 行

## 验收判据（机器判；**判定权在大脑，工头只递事实不判**）
| 指标 | 阈值 | 说明 |
|---|---|---|
| `with_rows_min` | ≥ 8 | 产出行数 > 0 的层数下限 |
| `diff_max` | ≤ 0.01 | 「实收 / 声明 count」误差上限 |

## 失败怎么办
某层换抓法重试；同一单元连续两次 short 且行数一致 → 记 ack（上游真缺）不再无限重试；仍失败记 `blocked.json`，用替补层补位。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 02 --workers 4
python3 collect/supervisor.py --review pass --next 03 --note "..."
python3 collect/supervisor.py --review pass --next 03
```

## 卡死阈值
`stall_min = 240` 分钟：超过只报告（写进叫醒简报），**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "02",
 "kind": "collect",
 "title": "试点 8 层",
 "select": {
  "source": "pilot_layers"
 },
 "workers": 4,
 "unit_rows": 500000,
 "tag": "collect-step02-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "short_units"
 ],
 "accept": {
  "with_rows_min": 8,
  "diff_max": 0.01
 }
}
```
