# 05b plan-probe 重探（方案 a）— 只读，未采集/未上传

- 脚本 `collect/plan_probe_reprobe.py`，探针 = `collect/full_plan.py:_count_one`（**未改**），产物 `collect/ledger/05b_plan_probe_reprobe.json`
- 口径：timeout 60s / 重试 3 / 退避 [2, 4, 8] / 并发 4；不重派 05b、不写采集账本、不发 Release
- verdict：**alive** = 拿到 count；**unverified** = 服务已死（404/400/500/502/503/no Query/not supported/TLS/token required/200 但无 count）；**pending** = 暂时性（超时/429/连接重置）
- 层→URL：plan probe 文件**无 url 字段**，全部走 plan 阶段同函数 `worker_core._rows_from_csv`+`_norm_plan_row`（`layer_plan.csv`），无手写模板
- 状态：**进行中 2/60**（4 并发 + 60s×4 次尝试，挂死端点每层最多 254s，全程需 ~1h）

当前计数：{'unverified': 2}

| # | 层名 | verdict | 依据（http / tries / err） | 耗时ms |
|---|---|---|---|---|
| 1 | `is_rest_services_Address_Points_Council_Area_FeatureServer_0` | unverified | http=200 / tries=4 / http200 without count / {"error":{"code":400,"message":"Invalid URL","details":[ | 15330 |
| 2 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | unverified | http=200 / tries=4 / http200 without count / {"error":{"code":499,"message":"Token Required","message | 15550 |

（未完成 58 层仍在跑；跑完后本表自动补全，计数以 JSON 的 `verdict_counts` 为准）
