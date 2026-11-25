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

输出：`dist/rows/<layer>.ndjson.gz`（打包后即删）→ `dist/tar/fieldmap-part%03d.tar.gz`（每 500 层一片）。
`dist/intake-full` 一个字节都不动；`free_gb < 3` 会立即停手。

## 关键口径（细节见 REPORT.md §5）

- 取值优先级：**信封原生值** → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects，约 200 个别名）→ **组合串拆分**（`split_number_street` / `split_city_tail`）。
- 组合串拆出来的值 `provenance=split`，**一律不许进 S**。
- `zip5` 恰好 5 位才算有效（`12345-6789` 取前 5）；`house_number` 占位值一律缺失、**绝不生成门牌**；坐标越界/(0,0)/缺省一律 null。
- `grade` / `tier` 完全由 `engine/config/pilot.yaml` 的 `grades` / `tier_rank` 驱动，代码里没有硬编码阈值。
- 方言：registry 按 agol org 命中 115 层，其余 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`）。
