# 适配器：地理图层批量采集

- 单元 = 一个图层（layer）
- fetch = ArcGIS/REST 分页拉取 → ndjson.gz → 落约定路径
- verify = manifest 四件套（declared vs actual、差额解释）
- 分片 = 实测速率 × 单 job 时限 × 60%
- 已知坑：端点必须走 /query；ArcGIS JSON 非 GeoJSON（Point=x/y、Polyline=paths、Polygon=rings）；extent 跨州需标 multi-state
