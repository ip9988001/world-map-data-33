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
| CA | https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHboundary/Congressional_Districts/FeatureServer/0 | `8a524a00c784a7a5.json.gz` | -118.272360000, 35.104428000 (rings) | -118.272360000, 35.104428000 | ✅ 一致 |
| CA | https://gis.cccounty.us/arcgis/rest/services/CCMAP/Assessment_Parcels_ArcPro/MapServer/0 | `a09bcc66cdf1952e.json.gz` | -122.364441831, 37.900657731 (rings) | -122.364441831, 37.900657731 | ✅ 一致 |
| CA | https://gis01.city.sanjacintoca.gov/server/rest/services/Bikeways/FeatureServer/13 | `03b7a532a76b2331.json.gz` | -116.951063765, 33.780294767 (paths) | -116.951063765, 33.780294767 | ✅ 一致 |
| NY | https://anrmaps.vermont.gov/arcgis/rest/services/map_services/MAP_ANR_ANRATLASRIVERSPROGRAM_WM_NOCACHE/MapServer/30 | `ece217b102e00425.json.gz` | -72.427626274, 44.128622521 (point) | -72.427626274, 44.128622521 | ✅ 一致 |
| NY | https://arcgisweb.welland.ca/serverprodpub/rest/services/OpenData/OPENDATA_Active_Schools_Points/MapServer/0 | `3a68fe6258c95d45.json.gz` | -79.223499157, 42.988909115 (point) | -79.223499157, 42.988909115 | ✅ 一致 |
| NY | https://arcgisweb.welland.ca/serverprodpub/rest/services/OpenData/OPENDATA_Community_Services/MapServer/0 | `1fe1c5e3ef937f1e.json.gz` | -79.256779215, 42.982532920 (point) | -79.256779215, 42.982532920 | ✅ 一致 |
| TX | https://gis.rgv911.org/server/rest/services/RGV911_Web_Apps_MIL1/MapServer/1 | `f9af93bbc363f1af.json.gz` | -98.061236378, 26.177941004 (paths) | -98.061236378, 26.177941004 | ✅ 一致 |
| TX | https://gis.wilco.org/ags/rest/services/rb/rb_wilcoroads/MapServer/0 | `b26afc482d9a138a.json.gz` | -97.921517234, 30.692873726 (paths) | -97.921517234, 30.692873726 | ✅ 一致 |
| TX | https://services.arcgis.com/0H6bQdxd9223gQB5/arcgis/rest/services/DowntownMap_WFL1/FeatureServer/2 | `d74c27d479bffadf.json.gz` | -102.079587504, 32.003162057 (rings) | -102.079587504, 32.003162057 | ✅ 一致 |
| DC | https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Cultural_and_Society_WebMercator/MapServer/0 | `b3e0f66e027167dc.json.gz` | -77.049223266, 38.903127178 (point) | -77.049223266, 38.903127178 | ✅ 一致 |
| DC | https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Health_WebMercator/MapServer/0 | `214c07d45f1dac0b.json.gz` | -77.031093093, 38.970276949 (point) | -77.031093093, 38.970276949 | ✅ 一致 |
| DC | https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Historic_WebMercator/MapServer/1 | `20ef49d9ed448377.json.gz` | -77.027038472, 38.920770859 (paths) | -77.027038472, 38.920770859 | ✅ 一致 |
| NV | https://services3.arcgis.com/6qQvkMi8WzsDQFHC/arcgis/rest/services/BestVeganBakeries/FeatureServer/0 | `2a93c9039dd7c10c.json.gz` | -86.794285265, 33.393475178 (point) | -86.794285265, 33.393475178 | ✅ 一致 |
| PR | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/PODs_PR_2025/FeatureServer/208 | `2d347cee3f4e2044.json.gz` | -66.292866000, 18.452239000 (point) | -66.292866000, 18.452239000 | ✅ 一致 |
| PR | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/PREMB_Zone_EOCs/FeatureServer/0 | `fdbbda1a59552363.json.gz` | -67.134659039, 18.455501002 (point) | -67.134659039, 18.455501002 | ✅ 一致 |
| PR | https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/PREMB_Zone_EOCs_2022/FeatureServer/108 | `26df8fdd0f800d79.json.gz` | -67.134659039, 18.455501002 (point) | -67.134659039, 18.455501002 | ✅ 一致 |
