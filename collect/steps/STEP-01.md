# STEP 01 — 预检（探路队）

**目标**：给 6 万个图层做一次体检，把「空壳子」和「假门」挑出来，同时量出每个层该怎么搬。

**方法**
1. 读 `survey/ng911/layers.json` + `clean.csv.gz`
2. 每层发一次 `returnCountOnly` 拿真实行数
3. 每层读元数据抓四个关键参数：
   - `supportsPagination`（能不能翻页，不能就得换招）
   - `definitionExpression`（有没有自带过滤条件，有就必须原样带上）
   - `maxRecordCount`（一次最多给多少行）
   - 字段数（字段太多要减小页大小）
4. 按行数分档算页大小：目标每次响应 ≤ 2MB
5. 产出 `collect/layer_plan.csv`

**产出**：`layer_plan.csv`，每行一个层：`layer_id,state,url,row_count,pagination,defexpr,pagesize,plan(keyset/offset/package/skip),svc`

**验收判据（机器判）**
- `layer_plan.csv` 行数 ≥ 50,000
- `plan` 列无空值
- `skip`（空层）比例有记录
- 至少 95% 的层拿到了真实 `row_count`

**失败怎么办**：403 就换 UA/加 referer；超时就重试 3 次退避；仍失败标 `unknown` 继续跑，不卡住。

**本步一停必须叫醒我。**

**下一步**：`STEP-02.md`（试点 8 层）
