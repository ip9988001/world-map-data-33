# 点类地址层逐层摸排（4,986 层口径，实测抽样）

判据：每层真拉 300 行，按 `lib.schema.normalize` 的 addr_key / 强地址字段含数字判有效。**不用 bbox**（bbox 会把邻州地址算进本层）。

| 指标 | 值 |
|---|---|
| 候选层（geom=Point/Multipoint/Socrata 且标题命中 address\|addr\|situs\|911\|mailing，按 url 去重） | 5064 |
| strong | 2254 层 |
| weak | 22 层 |
| reject | 2514 层 |
| reject_zero | 274 层 |
| 实测 avg_eff | 48.57% |
| 抽样行合计 | 1334144（有效 648036） |

## 定级规则

- strong：eff >= 20%%（优先采）
- weak：0 < eff < 20%%
- reject：抽样 0 有效或取不到数据（不采，只记账）
- reject_zero：上游声明 0 行

逐层明细见 `collect/address_layers.csv`。
