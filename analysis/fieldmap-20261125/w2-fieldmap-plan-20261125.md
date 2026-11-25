# w2-fieldmap-plan-20261125 · 字段映射规划（Muse 权威口径）

> 来源：muse-000258（task_id = w2-20261125-fieldmap-amend，2026-11-25T20:37:17+08:00）
> 定位：muse-000257 里只提了本文档名字、没贴内容；**以本文为准**，与前后的口头描述冲突时一律以本文覆盖。
> 落地：本文全文须原样提交到仓库 `analysis/fieldmap-20261125/w2-fieldmap-plan-20261125.md`。

## 一、分级定义（S / A / B / C 各自必须齐备的要素）

| 级别 | 必须齐备的要素 | 说明 |
|---|---|---|
| **S** | 门牌(house_number)、街(street_name)、城(city)、州(state)、邮编(zip5)、坐标(lat/lon) | 六要素全齐；**S 级行必须是原生值**，任何 split / 推断 / 默认 / 回填来的值一律降级，不许进 S |
| **A** | 门牌、街、州、邮编、坐标（坐标任意，有无皆可） | 城(city) 可空 |
| **B** | 门牌、街、州 | 邮编/坐标/城 均可空 |
| **C** | 街 | 仅街名 |

- `tier` 取自分档重跑产出的 `auto-recognized.csv` —— **Tier1 = 410 层的那一版**（版本必须核对，层数对不上即为用错版本）。
- 「zip 非法 → grade 最高 B」与上表自洽：A 与 S 都要求邮编合法，邮编非法自然落不到 A/S，封顶 B。

## 二、字段口径（逐条落到代码，不许自由发挥）

- **city**：S 级必须非空；A / B 级可空（空给 null，不许猜、不许从 street 里抠）。
- **state**：合法 **2 字母大写州码**（含 DC / PR / VI / GU / AS / MP）；非 2 字母或不在名单 → null。
- **zip5**：**恰好 5 位数字**才算有效；`12345-6789`（ZIP+4）取前 5 位；不足 / 超长 / 含字母 → **置 null**；**邮编非法 → grade 最高只到 B**。不许补零、不许截断凑数。
- **lat / lon**：lat ∈ [-90, 90]、lon ∈ [-180, 180]；超范围 → 置 null（越界残留必须为 0）；(0,0) 与完全缺省同样置 null，不许写 0 冒充。
- **house_number**：占位值（`-1` / `0` / `-9` / `NULL` / `NA`）算缺失；空串、纯符号同理；**绝不生成任何门牌**（不插值、不推算、不从区间取中值）。
- **source_layer**：**用 url**（不是 layer_id）。
- **addrkey v3**：`a3` + `include_unit` + `sha1-20hex`（sha1 取前 20 位十六进制）。
- 方言映射一律走 registry（registry 对不上 → `minimal_safe`：只取 number + street，pool=manual、a_pool_eligible=false，**永不进 A 货池**）。
- 组合串（FULL_ADDR 这类）按 `split_addr` 拆；拆不出的部分进 dropped 并计原因，不许硬猜。
- grade / tier 的阈值全部读配置（`engine/config/pilot.yaml` 的 grades / tier_rank / addrkey），**代码里不硬编码阈值**。

## 三、验收判据（回执必须逐条给实测值）

1. 层覆盖率 **≥ 95%**（未覆盖层全部进 `unusable.csv`，逐层写固定枚举原因）。
2. 逐层闭合：每层 `输入行数 = 映射行数 + 丢弃行数`，**差额 = 0**。
3. `street_name` **100%**；`house_number` **≥ 90%**；`zip5` 合法率 **≥ 95%**；坐标 **100%** 在合法范围（越界残留 = 0）。
4. **S 级行全是原生值**（零 split / 回填 / 推断来源）。
5. registry 合规（无不走 registry 的硬编码映射）。
6. 行级抽查 **≥ 10% 层**（最大 10 层必查）。

## 四、与 muse-000257 派单正文的增量差异（本轮必须补齐的 7 条）

1. `source_layer` 语义 = **url**（原正文未定义）。
2. `addrkey v3` 含 **include_unit**（原正文只写了 a3 + sha1[:20]）。
3. 邮编非法 → **grade 最高 B**（原正文未写封顶规则）。
4. **city**：S 必须、A/B 可空（原正文未写）。
5. **S / A / B / C 的要素表**（原正文只说「照 pilot.yaml」）。
6. `house_number` 占位值补 **`-9`**（原正文列了 -1/0/NULL/NA，漏 -9）。
7. `tier` 来源锁定 **Tier1 = 410 层那版** `auto-recognized.csv`（版本须核对层数）。

## 五、另附（同批事实，来自 muse-000258 第 1 条）

- `muse-000256`（Release 按级别拆分）**已完成，不重派**：公开 Release 只剩 B 货（DE-B / IA-B / NH-B，250,061,538 B），私有 123ip 只剩 S 级（DE-S / IA-S / NH-S，271,086,257 B），COUNT.json 逐州逐级闭合：S 2,057,841 + B 货 4,610,658 = 6,668,499。
