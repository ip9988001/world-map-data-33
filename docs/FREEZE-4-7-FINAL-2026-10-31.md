# 4-7 全线冻结（FINAL）· 2026-10-31

> **一句话状态：04b / 05b / 07b 采集与收口全部完成（`failed=0`），4-7 到此为止；三仓不再派任何 run，二仓保持停摆，一仓封印不动。**

## 一、冻结时的事实

| 项 | 状态 |
|---|---|
| 04b | 272 层 / ok 257 / failed 0 / rows 500,948,263（可核实 458,452,144）/ gap 17,457,629（3.6683%） |
| 05b | 2,770 层（含 cancel 片补账 445 层）/ ok 2,722 / failed 0 / rows 141,664,792 / gap 1,403,617（0.9811%） |
| 07b | 667 层 / ok 661 / failed 0 / rows 1,050,601 / gap 3,988（0.3782%） |
| 三阶段合计 | 3,709 层 / 可核实实采 601,167,537 / 声明 620,032,771 / 缺口 18,865,234（3.0426%） |
| 正在跑的 collect run | **无**（07b `41184978867` 已完成；同组无 pending） |

> 总账逐项与可加性证明见 `docs/4-7-TOTAL-2026-10-31.md` 与 `analysis/4-7-total-2026-10-31.json`。
> 三层级 exact 层 id 交集 = 0，上游 url 交集 = 0；rows 可直接相加。

## 二、三仓：不再派任何 run

**从本文件落 main 起，`world-map-data-33` 不派任何 `collect-*` / `county-*` / `geo-*` / `ng911-*` workflow。**
下列四项是**硬禁止**，不是「默认不跑」：

| # | 禁止项 | 为什么禁止 | 放开条件（缺一不可） |
|---|---|---|---|
| 1 | **08 去重** | 会全量读 30+ GB 原始资产，必须独占窗口；与任何采集/几何 run 并行都会打爆 egress 与磁盘 | ①用户显式口号；②独占窗口（确认无 in_progress 的 collect / 08 / 几何 run）；③`--authorize-manual 08`（preflight B5 硬闸门）；④先出 08 的输入清单与耗时预算，经人确认 |
| 2 | **09 增量拉取** | 只有 928 / 2,327 层（39.9%）有时间字段可增量，1,127 层（48.4%）无时间字段只能全量重采；盲目跑会变成第二轮全量 | ①用户显式口号；②先决定「可增量 928 层」与「只能全量 1,127 层」分别怎么处理；③`--authorize-manual 09` |
| 3 | **10b 宗地** | 8,116 层 / 20~85 GB，重阶段 | ①用户显式口号；②`authorize_heavy=1`（workflow 硬闸门 + preflight B5）；③先出分片预算与 egress 评估 |
| 4 | **几何边车（1,238 层）** | 几何/边车是 4-7 之外的独立阶段，未获授权 | ①用户显式口号；②`--authorize-manual geometry`；③先确认 08 去重口径（几何依赖去重后的键） |

- 04b / 05b / 07b 本身也**不再补跑**：缺口已按证据挂账（`partial` 13 层 / `unstable` 24 层 / `unverified` 8 层 / `missing` 2 层 / `capped` 1 层），要动必须用户点名 `--force-layers`，并重新过 preflight。
- `chain_policy.py` 的停车线不变：`04b→05b→07b→空`，`10b→空`，子 run 一律 `chain=0`。

## 三、二仓：保持停摆（等第五源形状确定）

- 仓库：`ip9988001/world-map-data-test`；状态：**停摆，不跑任何 run**。
- 重启前提：第五源形状确定；重启 checklist 第 1 项 = **接 F16 故障清单门禁**，见
  `world-map-data-test/docs/RESTART-CHECKLIST-2026-10-31.md` 与 `docs/WORKFLOW-FAILURE-LEDGER.md` 顶部 TODO。
- 在 F16 接上之前，二仓任何 run 都视为无效派单。

## 四、一仓：封印不动

- 仓库：`ip9988001/World-US-Map-Data`；状态：**封印**。不再补抓、不再改 MANIFEST、不再动 Release。
- 封印依据：`docs/TIGER-BACKFILL-2026-10-30.md`（52 个州 tag 前后快照，仅 AK/GA/ID 三州按判据重封，其余 52 个 tag 零变化）。
- 只读引用可以；任何写入（包括「顺手补一个州」）都必须先解封并拿到用户口号。

## 五、当前 main sha 与备份 tag

| 仓库 | 当前 main | 备份 tag → 指向 |
|---|---|---|
| `ip9988001/world-map-data-33`（三仓） | **`c373cf4`**（4-7 收口提交；本文件是随后的 docs-only 提交，main 会再 +1） | `backup/pre-freeze-20261031` → `5115f34`（事后冻结点）<br>`backup/pre-freeze-20261031-early` → `f405331`（改动前）<br>`backup/pre-freeze-20261031-stated` → `f405331`<br>`backup/pre-freeze-20261031-v1` → `3141bab`（旧值，仅追溯）<br>`backup/feat-gold-intake-20261031` → `7cb1c98` |
| `ip9988001/world-map-data-test`（二仓） | **`7b9c641`** | `backup/pre-freeze-20261031` → `c03c79a`（事后）<br>`backup/pre-freeze-20261031-early` → `514f12f`（rev3 前）<br>`backup/pre-freeze-20261031-stated` → `514f12f`<br>`backup/rev3-20261031` → `5841aef` |
| `ip9988001/World-US-Map-Data`（一仓） | **`dafef5e`** | **无 `backup/*` tag**；封印点 = main `dafef5e`。数据 tag 为 `raw-US-*-v1`（52 个州/分区）+ `v0-pipeline`（只读，不许移动） |

> 本地整仓快照（三仓/二仓）：`/data/backup/snap-20261031/*.tar.gz` + `SHA-清单.txt`。
> **任何情况下不许 `git push --delete` / `git tag -f` 动备份 tag**（最后一道回退点）。

## 六、冻结期间允许的提交（三仓）

只允许两类：

1. **文档 / 账本 / 分析产物**：`docs/**`、`collect/ledger/**`、`collect/<NN>b_ledger.json`、`analysis/**`；
2. 已批准的 **docs-only merge**。

**不允许**改 `collect/*.py`、`.github/workflows/**`、`collect/steps/**`、测试或任何采集逻辑。确需改代码 → 新开分支，不许直推 main；派单目标写分支名，不写 main。

## 七、自证（只读，不派 run）

```bash
# 1) 停车线：07b/10b 必须 stop，04b/05b 只接一跳且 child_chain=0
python3 collect/chain_policy.py --all --dry-run

# 2) 没有在跑的 collect run（输出应为空或只有 completed）
gh run list --workflow collect-full.yml --limit 10 --json databaseId,status,conclusion

# 3) 三阶段账本与总账口径
python3 collect/adjudicate_05b.py --check     # 必须 IDENTICAL
python3 collect/adjudicate_07b.py --check     # 必须 IDENTICAL
python3 - <<'PY'
import json
for st in ("04b","05b","07b"):
    d=json.load(open("collect/%s_ledger.json"%st))
    print(st, d["layers_n"], d["failed"], d["gap"], d["gap_pct"])
PY

# 4) 门禁：账本 vs 计划层数（D14）
python3 collect/preflight_dispatch.py --stage 07b --offline --no-write
```
