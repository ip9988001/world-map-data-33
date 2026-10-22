# collect/ — 采集流水线（待建）

本目录负责「**把普查出来的图层真搬回来**」。普查结果在 `../survey/ng911/`。

## 设计要点（定稿前不要改）

- **采集单元 = 一个图层**，不是州。一个州可能两百个图层，按州做 job 会互相拖死。
- **三种形态三种采法**
  - ArcGIS FeatureServer：`query?where=1=1&outFields=*&resultOffset=N&resultRecordCount=2000&f=geojson`
    （>200 万行走 OID 切片，不要深翻 offset）
  - Socrata：`/resource/{id}.csv?$limit=50000&$offset=N`
  - CKAN / 文件包：直下 zip / shp / gdb，落地转换
- **产物**：`{STATE}/{layer_id}/part-*.ndjson.gz` + `_manifest.json`（count / 实收行数 / 耗时 / 错误）
- **即传即删**：边采边传 Release 资产，本机不留盘（宿主内存 2GB）。
- **统一 schema**：state / layer_id / src_* / add_num / pre_dir / st_name / st_suf / post_dir / unit /
  city / zip / lat / lon / esn + **`raw`（原始整条 JSON 保留）**。
  字段命名各县不同，靠通用映射会丢信息，`raw` 是事后重算的唯一保险。
- **三道校验**：行数对账（差 >1% 标 `partial`）、空层标 `empty` 不报错、重复层标 `dup_of` 不阻断。

## 分阶段

| 阶段 | 范围 | 目的 |
|---|---|---|
| 0 | 8 个层（三种形态 + 大中小三档） | 打通链路、验证 schema |
| 1 | 全州级单层（约 20~40 个） | 拿到大部分人口 |
| 2 | 县市碎片（约两万层） | 全自动铺量，不人工盯 |
| 3 | 增量 | 按 `lastEditedDate` 只拉变更 |

预期失败率 5~10%（403 / 超时 / 需 token），必须重试 + 标记，不允许静默丢。
