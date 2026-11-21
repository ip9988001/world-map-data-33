# 05b · C1 真因修复（done 置位门槛 + 旧检查点作废重翻）

- **分支**：`fix/05b-paging-assert-20261121`（从 `origin/main` = `6a6215f` 拉出）
- **commit**：`bc5e0c8`（full `bc5e0c883c6fbf78f1285226dce1e7cb4a6c664a`）
- **diff**：`collect/_recon/20261121/05b-c1.diff`（598 行，8 文件，+367/−45）
- **main**：未动。`git push` 未执行（本次只落分支）。
- **未跑批**：没派 collect / 没重采 / 没碰 07b / 没 cancel 任何东西。

## 一、真因（沿用本轮已定案的日志证据，不重新推断）

```
api=... count=2300 pagesize=2000 workers=4 strategy=keyset
⟲ 续跑：检查点签名 14acda7e100ba989，已完成单元 1/1（2131 行）
done rows=2131 count=2300 diff=0.0735 err=- 3.4s
❌ 数据不齐 rows=2131 count=2300（缺 7.35%）
```

**没有任何「keyset 停在 … → 切 resultOffset」**：本轮续跑直接被检查点的 done 标记跳过，
3.4 秒收工；管线自己算出 7.35% 缺口，但只打一行日志，**没有断言**。

## 二、改了哪几处（文件 + 行号 + 原逻辑 → 新逻辑）

| # | 位置 | 原逻辑 | 新逻辑 |
|---|---|---|---|
| 1 | `collect/pilot.py:923` `resume_todo(units, ck, count, tol, log)` | 只看 `unit_uploaded != false` + `done_units`（跑到末尾即 done） | done 必须**同时**满足：① 产物已上传；② `unit_rows_seen ≥ unit_expect×(1-GAP_TOL)`；③ 老检查点没有 `unit_expect` 时按**层总量**兜底 `Σrows ≥ count×(1-tol)`，`count` 拿不到 = 无法证明 = 重验。不满足 → **从 `ck.done_units` 真删** + 记 `unit_done_voided`（原因）；`redone` 交给调度重翻 |
| 2 | `collect/pilot.py:1028` `_unit_range` 收尾旁 | — | 不变（上一轮 D1 的 `_top_up_offset` 仍在，补翻仍生效） |
| 3 | `collect/pilot.py:1380` `one()` 的 short 分支 | 连续 2 次 short 且行数一致 → `err=""` → 单元算 done → 续跑永久跳过 | `unit_short_ack` 只留证据，**不清 err、不置 done**；日志明说「仍不标 done，续跑会重翻」 |
| 4 | `collect/pilot.py:1385` `one()` 的 done 判定 | `done_ok = (not err) and (ok or not files)` | 加第三道：`rows_ok = limit or not expect or rows ≥ expect×(1-GAP_TOL)`；**上传成功也不放行短单元** |
| 5 | `collect/pilot.py:1370` 记账 | 只写 `unit_rows_seen` | 增写 `unit_expect[i]`（续跑才能逐单元校验；老检查点没有 = 重验） |
| 6 | `collect/pilot.py:40` `GAP_TOL` | `0.005` | **`0.001`**（env `PILOT_GAP_TOL` 覆盖） |
| 7 | `collect/pilot.py:1317` 续跑入口 | `done, redone = resume_todo(units, ck)` | `resume_todo(units, ck, count, log=log)` + 新增一行「done 校验后：真完成 N/M 单元」 |
| 8 | `collect/pilot.py:301` `void_invalidated_ckpt` + `INVALIDATED_CKPT` | 无 | 读 `collect/ledger/ckpt_invalidated.json`，签名命中 → **作废 done_units** 并置 `needs_reverify`（人工标记可执行，不只写在一个 gitignore 的缓存里） |
| 9 | `collect/preflight_dispatch.py:115` `ROWS_GAP_TOL` | `0.005` | `0.001`，注释写清「必须与 pilot.GAP_TOL 同值，否则一处判 done、一处判账本互相打架」 |
| 10 | `collect/ledger/ckpt_invalidated.json`（新增，入库） | 无 | 名单：`14acda7e100ba989` / 138c05 层 / rows 2131 / expect 2300 / gap 7.3478% / action `void_done_units_and_reverify` |
| 11 | `collect/ledger/.ckpt_cache/…138c05…@2026-10-31T08_54_00Z.json`（**gitignore，不在 diff 里**） | `done_units:[0]`, `unit_rows_seen:{0:2131}` | `done_units:[]` + `needs_reverify:true` + 作废原因（行数保留作证据） |

测试（`collect/tests/`）：

| 文件 | 变化 |
|---|---|
| `test_c1_done_gate.py`（新增） | 3 条 stub，复刻 14acda 状态 |
| `test_pilot_baseline.py` | `test_short_ack_after_two_runs` 改为「ack 仍记、done 不置位、unit_errors 保留 short」 |
| `test_pilot_unit_bytes.py` | `resume_todo` 4 条按新口径更新；**新增** `test_rows_short_of_expect_voids_done`、`test_old_ckpt_without_rows_is_reverified` |
| `test_paging_assert.py` | GAP_TOL 断言 0.005 → 0.001，边界用例重算 |
| `test_preflight_rows_gate.py` | live 分母用例按 0.1% 重算（2299 过 / 2296 挂） |

## 三、单测

```
python3 -m unittest discover -s collect/tests -q
Ran 454 tests in 20.996s
OK
```

（上一轮 449 → 本轮 454：+3 C1 stub，+2 resume_todo 口径用例。）

## 四、stub 实跑输出（原样，`python3 -m unittest collect.tests.test_c1_done_gate -v`）

```
STUB|   ⚠ 作废 done 标记 u0：老检查点无 unit_expect，单元合计 2,131 < count 2,300×(1-0.1%) → 本轮重翻
STUB|   ⚠ 检查点签名 14acda7e100ba989 在「需重验」名单（ckpt_invalidated.json）→ 作废 1 个 done 标记，本轮重翻
STUB| err=short:2131/2300 done_units=[]
```

三条分别证明：

1. **纯判定层**（`resume_todo` 直接调用）：`keep=[]`、`redone=[0]`，日志点名「作废 done 标记 u0」；
2. **端到端重翻**：带 `done_units:[0] / unit_rows_seen:{0:2131} / unit_uploaded:{0:true} / 无 unit_expect` 的旧检查点续跑 →
   服务端 query 次数 > 1（不是 3.4s 跳过）、`rows == 2300`、`err == ""`、`unit_expect[0]=2300`、
   **`done_units == [0]` 是采齐之后重新置位的**；
3. **补不回来**（上游只给 2,131）：`err = short:2131/2300`、`done_units == []`、`unit_errors["0"]` 挂着 → 落 partial/failed。

## 五、风险点

1. **旧检查点会不会被误作废导致重采量暴增？**
   - 逐单元有 `unit_expect` 的 → 精确判，不会误伤；
   - 老检查点（没有 `unit_expect`）→ 用**层总量** `Σdone_rows ≥ count×(1-tol)` 兜底：只要这一层历史上真采齐了，就不会被作废；
   - 真正会被作废的是「层总量也不够」的，**那就是本来就该重采的**（例如 138c05）。
   - 唯一的放大场景：`count` 取不到（上游 count 接口挂了）。此时按「无法证明 = 重验」处理，最坏情况是把这一层所有单元重翻一遍。这里选了「宁可重采，不许假装完成」，与用户口径一致；若担心代价，可 `PILOT_GAP_TOL` 放宽，但不能关掉重验。
2. **`unit_short_ack` 不再终结重试**：上游真短（例如服务确实只有 2,131 行，而 count 报 2,300）的层会**每次 run 都重翻一次**。代价是重复下载，但产出会一直标 partial，不会假装完成。若某层长期如此，应走 `attempt_log` 的重试上限 / `unavailable` 定案，而不是把它标 done。
3. **GAP_TOL 从 0.5% 收紧到 0.1%**：上游日常漂移（±0.x%）可能把个别层打成 short。冒烟 05b 账本时已看到 `LAWRENCEGIS −0.62%` 会被判 partial（真缺口，符合预期）；若后续证明 0.1% 过敏，只调 env，不动代码。
4. **`ckpt_invalidated.json` 是人工名单**：只影响签名命中的检查点（当前仅 138c05），不会扩大影响面；文件缺失/损坏时函数返回空集，行为退回自动判据。

## 六、待办（不在本轮）

- C4（主键非空率探测）上一轮已落但按用户口径**降为可选**，本轮未动；
- C3/C5 上一轮已完成（preflight D15 双分母 + `05b-done-layers.md`/JSON），本轮只同步了容差 0.001。
