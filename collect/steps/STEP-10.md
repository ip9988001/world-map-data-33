# STEP 10 — 宗地地址扩采

> **判据卡 v2.1（新增环节）**　工头：`collect/supervisors/step_10.py`　工人：`.github/workflows/worker-10.yml`
> 参数唯一来源 `collect/steps.json`；本文件底部机器块是它的镜像，改参数只改 steps.json。

## 目标
01 预检按几何白名单把 Polygon/Polyline 全 skip 了（23,556 层 / 声明 11.8 亿行）。
但很多州的地址只存在于宗地属性里（situs address），这是采集面最大的缺口。
本环节负责：把这批层里**真的有房产地址**的挑出来，并按实测有效率只采高产出层。

## 输入
`collect/layer_plan.csv`（全量层计划）→ 探测得到 `collect/polygon_probe.json`

## 产出 / 证据
`collect/reports/PARCEL_DECISION.md`（决策报告）+ `collect/situs_layers.csv`（全集 8117 层分级 + url 字典）、`collect/batch1.csv`（批1 选层清单：layer/state/grade/declared/eff）
`collect/parcel_yield.json`（实测漏斗）+ `collect/s6c_merge.json`（全库合并）

证据清单：`report`、`releases`、`checkpoint`、`layer_plan.csv`、`state`

## 怎么做
1. **探测**：只调 `?f=json` 读字段名，不取数据；分 situs / owner / none 三档
2. **清洗**：剔 Polyline 线要素、路网/PSAP/联系人等层名噪声、仅 from/to 门牌区间的层
3. **补州**：州全名 → 独立州码 token → 取 1 条要素 `f=geojson&outSR=4326` 用州界多边形反查
4. **抽样实测**：分层抽 200 层真下载，量 声明→实采→有效地址→去重净新增 四层漏斗
5. **全库快测**：剩余层各取 300 行测有效率，按 `eff_min` 筛层
6. **决策**：只采达标层，按产出/分钟排序，绝不按声明行数全采
7. **面层带质心（硬判据，`steps.json#steps.10.poly_centroid=true`）**：`PILOT_POLY_CENTROID` 默认已开，
   面层每行落 `_lat`/`_lon`（rings 本地算 `representative_point`，算不出才退回 `returnCentroid=true` 的服务端质心，`outSR=4326`）。
   **2026-10-30 踩过的坑（防回归）**：老实现只读 `geometry.y/.x`，`rings` 在采集瞬间就被丢掉 ——
   1,038 个宗地层「有行、有 Shape__Area、无坐标」，县判定与坐标补齐全部卡死，只能整层重采。
   现在：面层缺 `_lat`/`_lon` 键 = 采集失败；回归保护在 `collect/tests/test_pilot_centroid_contract.py`。

## 验收判据（机器判；判定权在大脑）
| 指标 | 阈值 |
|---|---|
| `eff_min` | ≥ 0.2（单层有效率门槛） |
| `pick_layers_min` | ≥ 1000 层 |
| `budget_min_max` | ≤ 900 job-分钟 |

## 失败怎么办
有效率低于门槛就丢层，不硬采；全库达标层不足 1000 层说明这条路不成立，直接停，不铺全量。

## 命令（照抄）
```bash
python3 collect/supervisor.py --kick 10
python3 collect/supervisor.py --review pass --note "宗地扩采收尾"
```

## 卡死阈值
`stall_min = 180` 分钟：超过只报告，不判死。

<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->
```json
{
 "step": "10",
 "kind": "parcel_situs",
 "poly_centroid": true,
 "title": "宗地地址扩采",
 "select": {
  "source": "layer_plan",
  "file": "collect/batch1.csv",
  "grade": [
   "strong",
   "weak"
  ],
  "eff_min": 0.2,
  "mode": "bulk",
  "order": "rows_desc",
  "offset": 0,
  "batch": 200,
  "skip_done": true
 },
 "workers": 4,
 "unit_rows": 100000,
 "tag": "collect-step10-{layer}",
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
