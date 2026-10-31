# 派单模板（照抄，缺行 = 无效派单）

> 立规：2026-10-31。背景：2026-10-30 一天内 04b/05b 因「派单前没核验」返工五次。
> 本模板是**派单的最小必备内容**；少一行就算无效派单，对方可以直接退回。

```markdown
【派单】<stage> · <一句话目标>

## 0. 强制项（缺一行 = 本派单作废）
- 故障清单已查：<W33-011,W33-013 | 无>
- preflight：verdict=<PASS|PASS_WITH_WARNINGS>  FAIL=<n>  WARN=<n>（贴结论行 + 每条 WARN 的处置）
- ledger_hits：<编号列表 | 无>（F16 输出；有 WARN 必须逐条写规避动作）

## 1. 派什么
- 入口：<collect-full.yml / collect-oid-range.yml / county-fill.yml / ...>
- 目标分支（ref）：<分支名，不是 main —— main 只接 merge>
- 参数：stage=<...> size=<...> workers=<...> unit_rows=<...> layer_timeout=<...>
        max_shards=<...> chain=<0|1> authorize_heavy=<0|1>
        目标层（如定向补采）：<layer_id,...>

## 2. 跑前基线（跑后才好对比）
- 阶段账本：`collect/<stage>_ledger.json` → layers_n=<n> rows=<n> ok/partial/missing/unverified/empty/failed=<...>
- 资产真值：`collect/ledger/step0Nb_rebuilt.json` → layers_n=<n> rows=<n>
- 逐层 rows 基线：`analysis/rows-baseline-<stage>-<ts>.json`（preflight 产出）
- 目标层现有 checkpoint / 单元包：<tag, 单元数, 是否需要备份>

## 3. 撞车检查
- 同组 pending：<无 | run id>（有 pending = 先等，别硬派）
- 在跑 run 的目标层 × 本次目标层：交集=<0 层 | 层列表>（必须为空）
- 上游阶段会自己派吗：<不会（chain=0） | 会 → 这次手派会撞组，改等它>

## 4. 判成功（跑完看什么，不看日志感觉）
- `failed == 0`
- `shards_expected == shards_reported`、`shards_incomplete == []`
- 阶段账本 `layers_n` 未变小、`regressions[]` 无新增（或每条都有 `row_shrink_evidence`）
- 定向层：`rows` ≥ 基线 且 `ledger_rebuild --check` 的差异能逐层解释

## 5. 禁止
- 碰在跑的 run（不许 cancel/重派同组）
- 改采集口径（除非本派单就是改口径，且单列一节说明）
- 事后补台账（新坑必须当天补，commit message 写 `ledger: +N <类别>`）
```

## 用法要点

1. **第 0 节是硬门禁**：`故障清单已查` 与 `ledger_hits` 都来自 `docs/WORKFLOW-FAILURE-LEDGER.md` + `collect/preflight_dispatch.py`（F16）；
   没有这两行，派单视为无效——不是「建议」。
2. **第 2 节必须数字**，不许「大概」「应该还是 272 层」。基线不钉死，跑完就说不清行数变没变小。
3. **第 3 节必须机械核对**（`gh run list` + 目标层取交集），不许「应该不会撞」。
4. **第 4 节是判成功的唯一标准**，贴账本字段与文档节号，不贴「看起来没问题」。
5. 派单回执里附：`run id`、`verdict`、`FAIL/WARN` 明细、落库的 commit sha。
