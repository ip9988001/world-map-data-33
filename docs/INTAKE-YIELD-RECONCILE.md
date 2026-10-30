# 全量对账（3 层逐行数）

口径：把每层 payload 全下下来逐行解析，数「总行数」与「门牌号可解析行」，验证 `rows_total == rows_with_number + rows_without_number` 闭合，并对比 INTAKE-YIELD 的抽样外推误差。

| 层 | 门牌字段 | rows_total | with_number | without_number | 闭合 | 抽样估计 | 估计误差 |
|---|---|---|---|---|---|---|---|
| `DQNT3m6mbJlqZ_arcgis_rest_services_Addre` | `Number` | 7,733 | 7,278 | 455 | ✅ | 7,431 | -2.10% |
| `ervices_Addresses_awayfrom3mi_cemeteries` | `ADDR_NUM` | 199 | 196 | 3 | ✅ | 196 | +0.00% |
| `zOpn2_arcgis_rest_services_Streets_Buidl` | `HOUSE_NUMBER` | 65,488 | 65,487 | 1 | ✅ | 65,488 | -0.00% |

**闭合校验：全部通过**（3/3）
