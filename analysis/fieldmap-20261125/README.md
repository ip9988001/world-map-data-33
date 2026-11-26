# 第 9 步 · 全量字段映射（`analysis/fieldmap-20261125/`）

把 3,550 层「Release 载荷已到手」的 part 包（`/data/workspace/world-map-data-33/dist/intake-full/layers/`，只读）
映射成 **11 列** 可读数据：`house_number / street_name / city / state / zip5 / lat / lon / source_layer / tier / grade / addrkey`。

## 复跑

```bash
cd /data/workspace/wmd-fieldmap
python3 analysis/fieldmap-20261125/map_layers.py --all --shard 500 --workers 7   # 主跑（可 --resume 续跑）
python3 analysis/fieldmap-20261125/fieldstats.py                                  # 字段有效率
python3 analysis/fieldmap-20261125/spotcheck.py --layers 355 --rows 200            # 行级抽查
python3 analysis/fieldmap-20261125/health_probe.py 10                              # HEALTH.md
python3 analysis/fieldmap-20261125/finalize.py                                     # unusable.csv + REPORT.md + SUMMARY.json
```

### 只改口径、不重扫 40 G 输入的增量重写（muse-000258）

```bash
python3 analysis/fieldmap-20261125/amend_rewrite.py --workers 7   # dist/tar → dist/tar2
mv dist/tar2/* dist/tar/ && rmdir dist/tar2
python3 analysis/fieldmap-20261125/amend_apply_stats.py          # 回填 layer-coverage.csv（v1 → layer-coverage.v1.csv）
python3 analysis/fieldmap-20261125/fieldstats.py
python3 analysis/fieldmap-20261125/amend_verify.py --layers 355   # anchor-check.json/.csv
python3 analysis/fieldmap-20261125/finalize.py
```

## 口径权威源

**`w2-fieldmap-plan-20261125.md`**（muse-000258 全文，原样落盘）= 分级/字段/验收的唯一口径。

输出：`dist/rows/<layer>.ndjson.gz`（打包后即删）→ `dist/tar/fieldmap-part%03d.tar.gz`（每 500 层一片）。
`dist/intake-full` 一个字节都不动；`free_gb < 3` 会立即停手。

## 关键口径（细节见 REPORT.md §5）

- 取值优先级：**信封原生值** → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects，约 200 个别名）→ **组合串拆分**（`split_number_street` / `split_city_tail`）。
- 组合串拆出来的值 `provenance=split`，**一律不许进 S**。
- `zip5` 恰好 5 位才算有效（`12345-6789` 取前 5）；`house_number` 占位值（`-1/0/-9/NULL/NA`…）一律缺失、**绝不生成门牌**；坐标越界/(0,0)/缺省一律 null。
- `source_layer` = **url**（无 url 的 71 层 `@未定位` 退回 layer_id）。
- `addrkey` = **engine 档 v3**：`engine/outlet_clean.addrkey_v3`（parts = state2 / zip5 / num_key / street_key / unit_key；`include_unit` 读 `pilot.yaml`；num 或 street 缺 → null）。
- `tier` 取 `analysis/grading-rerun-20261125/auto-recognized.csv`（**Tier1 = 410 那版**）按 url 匹配，未命中 = `unrated`。
- `grade` / `tier` 完全由 `engine/config/pilot.yaml` 的 `grades` / `tier_rank` 驱动，代码里没有硬编码阈值。
- 方言：registry 按 agol org 命中 115 层，其余 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`）。
