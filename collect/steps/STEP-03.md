# STEP 03 — 单州试跑（KS 全州）

**目标**：一个州的所有层跑一遍，验证批量、并发、打包、上传在真实规模下不崩。

**方法**
- 取 `layer_plan.csv` 里 state=KS 的全部层（非 skip）
- 按 host 限速：同一域名最多 2 并发；arcgis.com 放宽到 8
- 每层独立状态：done / empty / partial / failed
- 每 20~50 层打一个 tar.gz 上传 Release `collect-ks`，传完删本地

**产出**：KS 全部层的数据 + `ks_report.json`

**验收判据（机器判）**
- KS 的层状态无 `pending`
- `failed` 占比 < 15%
- 打包上传成功，Release 里资产数与预期批次一致
- 本地磁盘无残留（`df` 前后差 < 1GB）

**失败怎么办**：429 就降并发；空间不够就先传后删；某层反复失败标 failed 跳过。

**本步一停必须叫醒我。**

**下一步**：`STEP-04.md`（全州级放量）
