# STEP 10b — 宗地地址扩采（batch2+）

> **判据卡 v2.1（补采变体）**　工头：`collect/supervisors/step_10b.py`　工人：`.github/workflows/collect-full.yml`（stage=10b）
> 参数唯一来源是 `collect/steps.json`。**本文件底部的机器块是它的镜像，不许手改数字**。

## 目标
10 的 batch1 只采了 `batch1.csv` 里的 1,261 层（强/弱等级中各挑最赚的）。
10b 把 batch1 之外**全部 strong/weak 有效层**采掉（`situs_layers.csv` 全集，8,117 层分级），
reject 档**只记账不采** —— 宗地面层是采集面最大的缺口，但绝不全采。

| 差异点 | 10 | 10b |
|---|---|---|
| 层清单 | `batch1.csv`（批1，1,261 层） | `situs_layers.csv`（全集分级，weak/strong 全采） |
| 已采层 | `skip_done=true` | 同（batch1 已采层自动剔除，不重采） |
| 执行方式 | 一层一个 matrix job | 分片：**一片一个 job，片内顺序跑 200 层** |

## 输入
`collect/situs_layers.csv`（全集 8,117 层分级：`layer/state/grade/declared/eff`），取 `grade ∈ {strong, weak}`，
减去 `done_from = 10` 判为已完成的层（即 batch1 已采的 1,261 层）。

## 产出 / 证据
`collect/ledger/10b_plan.json` → `collect/ledger/step10b_shard<N>.json` → `collect/step10b_ledger.json`
→ `collect-step10b-<layer>` Release 资产（面层用 `returnCentroid=true` 拿质心当坐标）

证据清单：`report`、`releases`、`checkpoint`、`layer_plan.csv`、`state`

## 怎么做
- 切 200 层/片；片数上限 250
- 按 `rows_desc`：宗地层产出/分钟最高，先吃大的
- **面层必须落简化 rings（硬判据，`steps.json#steps.10b.poly_rings=true`）**：
  `PILOT_POLY_RINGS` 默认已开。面层每行额外落 `rings`（6 位小数 + RDP 1e-5°，第 ② 档），
  退化几何 → `rings=null`；点层/线层不带该键。**只落简化版，不落原始 rings**（实测：原始多付 5.2 GB 买亚微米噪声）。
  已有 part 资产不动，存量层补几何走 `--geom-backfill`（见几何方案文档第五节）
- **非宗地面只落质心**（`rings_skipped="non_parcel"`）+ **unit 按行数且字节（1.5 GB）双上限先到先切**：
  两条都是硬判据（`steps.json#steps.10b.unit_bytes`），`--entry-check` 第 30/31 条守着
- **面层必须带质心（硬判据，`steps.json#steps.10b.poly_centroid=true`）**：
  `PILOT_POLY_CENTROID` 默认已开。面层每行落 `_lat`/`_lon`（= rings 本地算的
  `representative_point`，算不出来才退回 `returnCentroid=true` 的服务端质心，`outSR=4326` 即 WGS84）。
  几何仍缺的层记 `geom_missing` 计数，**不猜坐标**
- **2026-10-30 踩过的坑（防回归）**：老实现只读 `geometry.y/.x`，Polygon 的 `rings` 在采集瞬间
  就被丢掉、`normalize()` 签名里也没有落坐标的位置 —— 结果 1,038 个宗地层「有行、有 Shape__Area、
  无坐标」，下游县判定与坐标补齐全部卡死，只能整层重采（代价 = 全部行数）。
  所以现在：**面层缺 `_lat`/`_lon` 键 = 采集失败**，不允许「先采属性、以后再补几何」。
  回归保护：`collect/tests/test_pilot_centroid_contract.py`（11 条，含「面层每行必有 _lat/_lon」）
- 每层四态落账；实采与声明差 > 0.2% 记 `partial`（宗地层声明数是服务端估算，差额常见）

## 验收判据（机器判；**判定权在大脑**）
| 指标 | 阈值 |
|---|---|
| `eff_min` | ≥ 0.2（单层有效率门槛） |
| `pick_layers_min` | ≥ 1000 层 |
| `budget_min_max` | ≤ 900 job-分钟 |

## 失败怎么办
有效率低于门槛就丢层，不硬采；预算撞上限就停并在简报写明，不自动接续。
面层 4xx（查询超时 / 超出 maxRecordCount）记 `unit_errors` 并降 `unit_rows` 重试，不整层判死。

## 命令（照抄）
```bash
python3 collect/full_plan.py --stage 10b --size 200 --out collect/ledger/10b_plan.json
python3 collect/full_shard.py --stage 10b --shard 0 --plan collect/ledger/10b_plan.json --workers 4
python3 collect/step_full_report.py --stage step10b
```

## 卡死阈值
`stall_min = 180` 分钟：超过只报告，**不判死、不重跑**。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "10b",
 "kind": "parcel_situs",
 "poly_centroid": true,
 "poly_rings": true,
 "title": "宗地地址扩采 batch2+",
 "select": {
  "source": "layer_plan",
  "file": "collect/situs_layers.csv",
  "grade": [
   "strong",
   "weak"
  ],
  "mode": "bulk",
  "order": "rows_desc",
  "offset": 0,
  "batch": 4000,
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 100000,
 "unit_bytes": 1500000000,
 "tag": "collect-step10b-{layer}",
 "evidence": [
  "report",
  "releases",
  "checkpoint",
  "layer_plan.csv",
  "state"
 ],
 "accept": {
  "eff_min": 0.2,
  "pick_layers_min": 1000,
  "budget_min_max": 900
 }
}
```
