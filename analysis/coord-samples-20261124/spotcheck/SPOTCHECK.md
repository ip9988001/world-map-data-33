# 坐标真实性抽查（CSV ↔ 原始响应）

原始响应缓存在采集机 `/data/coord-work-20261124/cache/<sha1(url)[:16]>.json.gz`，未提交进仓库（体积原因）；校验方式：`scripts/spotcheck.py --states DE,NH,IA --n 3`。

| 州 | layer_url | 原始响应 | 响应首个几何顶点 | CSV lon_raw/lat_raw | 结论 |
|---|---|---|---|---|---|
| DE | https://enterprise.firstmap.delaware.gov/arcgis/rest/services/Society/DE_Art_Inventory/FeatureServer/0 | `c13dc491ebf06fc5.json.gz` | -75.753983960, 39.664201750 (point) | -75.753983960, 39.664201750 | ✅ 一致 |
| DE | https://gis.kentcountyde.gov/server/rest/services/Transportation/Roads/FeatureServer/0 | `c84097785618d92d.json.gz` | -75.537883571, 39.293604455 (paths) | -75.537883571, 39.293604455 | ✅ 一致 |
| DE | https://services.arcgis.com/DCPX1PuggGH4Tici/arcgis/rest/services/Cooling_Services_2026_Flyer_GIS_Table/FeatureServer/0 | `780c8c0145c6f3db.json.gz` | -75.556917000, 39.744198000 (point) | -75.556917000, 39.744198000 | ✅ 一致 |
| NH | https://anrmaps.vermont.gov/arcgis/rest/services/map_services/MAP_ANR_ANRATLASBASEMAPLITE_WM_NOCACHE/MapServer/4 | `04de31bdbcbcf59d.json.gz` | -72.330636983, 43.635150390 (point) | -72.330636983, 43.635150390 | ✅ 一致 |
| NH | https://services.arcgis.com/2gdL2gxYNFY2TOUb/arcgis/rest/services/Winery_Location_Table/FeatureServer/0 | `d822df8d49bfbcc1.json.gz` | -71.419027677, 43.390403918 (point) | -71.419027677, 43.390403918 | ✅ 一致 |
| NH | https://services.arcgis.com/pwNwIGBE7M7VOXjQ/arcgis/rest/services/MilesPondParcels_Data_Collection/FeatureServer/0 | `94ee8b180be73aa9.json.gz` | -71.805217055, 44.444952997 (rings) | -71.805217055, 44.444952997 | ✅ 一致 |
| IA | https://services.arcgis.com/4Y5FNypV9g2Wgf92/arcgis/rest/services/Larimer_SNAP_Households_and_Food_Banks_WFL1/FeatureServer/0 | `608ea45185cf50ff.json.gz` | -83.094769700, 41.256779300 (point) | -83.094769700, 41.256779300 | ✅ 一致 |
| IA | https://services.arcgis.com/4YineAQdtmx0tv46/arcgis/rest/services/Railroad_Centerline_MitchellIA/FeatureServer/0 | `313dc46954b6bf48.json.gz` | -92.957597659, 43.487239699 (paths) | -92.957597659, 43.487239699 | ✅ 一致 |
| IA | https://services.arcgis.com/8lRhdTsQyJpO52F1/arcgis/rest/services/Traffic_Data_view/FeatureServer/8 | `c72b66ff543ff336.json.gz` | -96.128582091, 42.022317656 (paths) | -96.128582091, 42.022317656 | ✅ 一致 |
