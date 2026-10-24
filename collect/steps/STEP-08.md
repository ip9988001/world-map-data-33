# STEP 08 — 去重与真实地址数

> **判据卡 v2.1（新增环节）**　工头：`collect/supervisors/step_08.py`　工人：`.github/workflows/worker-08.yml`
> 参数唯一来源 `collect/steps.json`；本文件底部机器块是它的镜像，改参数只改 steps.json。

## 目标
回答「8,360 万行里独立地址到底多少」—— 只读自家 Release，不动任何数据。

## 输入
Release 里各步的 `*.tar.gz`（tag 前缀见 steps.json 08.tag_prefixes）

## 产出 / 证据
`collect/reports/DEDUP_REPORT.md` + `collect/dedup_status.json`

证据清单：`FINAL_REPORT.md`

## 怎么做
- 逐层下载 part 包 → 解压 → 流式解析每行 `addr_key`（采集时已写，md5 前 16 位）
- 按州精确去重：州内一个集合，处理完就丢，内存峰值只跟最大州有关
- 输出层内合计 / 州内独立 / 重复率 / 真实覆盖率（÷ Census 住房单元）

## 验收判据（机器判；判定权在大脑）
| 指标 | 阈值 |
|---|---|
| `states_min` | ≥ 40 |
| `unique_rows_min` | ≥ 30000000 |
| `dup_rate_max` | ≤ 0.9 |

## 失败怎么办
解包失败或资产缺失只跳过该层并记录，不中断整表；某州数据缺失在该州行标 0 并在报告注明。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 08
python3 collect/supervisor.py --review pass --next 07
python3 collect/supervisor.py --kick 08
```

## 卡死阈值
`stall_min = 120` 分钟：超过只报告，不判死。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "08",
 "kind": "analyze",
 "title": "去重与真实地址数",
 "evidence": [
  "FINAL_REPORT.md"
 ],
 "accept": {
  "states_min": 40,
  "unique_rows_min": 30000000,
  "dup_rate_max": 0.9
 }
}
```
