# STEP 09 — 增量同步

> **判据卡 v2.1（新增环节）**　工头：`collect/supervisors/step_09.py`　工人：`.github/workflows/worker-09.yml`
> 参数唯一来源 `collect/steps.json`；本文件底部机器块是它的镜像，改参数只改 steps.json。

## 目标
验证增量能力：有多少层能按「最后修改时间」只拉变更，而不是每季度全量重采。

## 输入
已采层清单（pilot_report.json）+ 各层服务元数据 `?f=json`

## 产出 / 证据
`collect/reports/DELTA_REPORT.md` + `collect/delta_state.json`

证据清单：`report`、`releases`

## 怎么做
- 逐层探测编辑时间字段（last_edited_date / edit_date / dateupdate / lastupdate …）
- 探到就 `count where <字段> > since`，算窗口内变更行数
- 探不到记 `no_delta_field`：这类层只能全量重采，不硬凑

## 验收判据（机器判；判定权在大脑）
| 指标 | 阈值 |
|---|---|
| `field_rate_min` | ≥ 0.1 |
| `failed_rate_max` | ≤ 0.2 |

## 失败怎么办
单层探测失败只记一笔；字段率低于判据就说明增量不可行，直接停（不铺全量）。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 09
python3 collect/supervisor.py --review pass --note "项目收尾"
python3 collect/supervisor.py --kick 09
```

## 卡死阈值
`stall_min = 180` 分钟：超过只报告，不判死。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "09",
 "kind": "delta",
 "title": "增量同步",
 "select": {
  "source": "collected",
  "batch": 20
 },
 "tag": "collect-delta-{layer}-{date}",
 "evidence": [
  "report",
  "releases"
 ],
 "accept": {
  "field_rate_min": 0.1,
  "failed_rate_max": 0.2
 },
 "since_days": 90
}
```
