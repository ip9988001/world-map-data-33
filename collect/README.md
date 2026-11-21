# collect/ — 采集流水线（自研模式 v2.1）

**版本：v2.1 · 2026-10-24**　总图与铁律：`ROADMAP.md`　设计由来：`SELF-DRIVE-v2.md`

本目录负责「把普查出来的图层真搬回来」。普查结果在 `../survey/ng911/`。

## 三层结构（改东西先看这张表）

| 层 | 文件 | 职责 | 改它的时机 |
|---|---|---|---|
| 参数 | `steps.json` | **唯一参数源**：7 步的选层/并发/单元/阈值/证据清单/工头配置 | 任何数字要动，都只动这里 |
| 引擎 | `worker_core.py`、`lib/{fetch,schema,units}.py` | 通道、选层、切单元、schema 映射、checkpoint | 采集机制要变 |
| 工人 | `run_step_00..06.py` + `.github/workflows/worker-0X.yml` | 每步一个入口，只声明本步差异 | 某一步的采法要变 |
| 工头 | `supervisor.py` + `supervisors/step_00..06.py` | 巡逻、收证据、叫醒大脑；**不判验收** | 叫醒逻辑要变（单步差异改 `supervisors/step_0X.py`） |
| 文档 | `steps/STEP-0X.md` | 7 份判据卡（目标/输入/产出/判据/失败/命令 + steps.json 镜像块） | 判据说明要变（数字仍以 steps.json 为准） |

坏一处只修那一份：7 个工人、7 个工头各自独立，互不牵连。

## 设计要点

- **采集单元 = 一个图层**，不是州。一个州可能两百个图层，按州做 job 会互相拖死。
- **三条通道**：keyset 游标（首选）→ `resultOffset` 兜底 → `returnIdsOnly` + `objectIds`（服务谎报 200 时救命）。
- **断点续传**：单元约 50 万行，完成即 `gh release upload`；`<layer>-checkpoint.json` 跟同一 tag，
  tag 固定为 `collect-stepNN-<layer>`（不带 run_number，否则换 run 接不上）。
- **单元完成判据**：无错 + 行数差 < 0.1% + 上传成功；同一单元连续两次 short 且行数一致 → 记 ack（上游真缺），不再无限重试。
- **几何白名单** `point / multipoint / socrata / na`；Polygon（1.5 万层）与 Polyline（8 千层）带不进地址字段，直接 skip。
- **产物**：`part-*.ndjson.gz` + `_manifest.json`（count / 实收 / 耗时 / 错误）；本机不留盘（宿主 2GB）。
- **schema**：state / layer_id / src_* / add_num / pre_dir / st_name / st_suf / post_dir / unit / city / zip / lat / lon / esn + **`raw`（原始整条 JSON）**。
- **三道校验**：行数对账（差 >1% 标 `partial`）、空层标 `empty` 不报错、重复层标 `dup_of` 不阻断。

## 账本口径（覆盖率 / hollow）

- **覆盖率一律按「有效覆盖」算** = `有行且非 hollow 的层数 ÷ 计划层数`。
  按 tag 数算的「形式覆盖率」只作参考，**不得用于验收**（tag + Release 齐全但资产为空 = 形式有、实质无）。
- **hollow（空洞层）**：形式存在（tag + Release 都在）、实质为空 —— 资产只有 checkpoint（几百字节）、
  `rows=0`、而 `declared>0`。标 `hollow=true` 并同时保留在缺口清单里，**缺口数字不因标 hollow 而变小**。
  已认定：`rcgis_rest_services_Addressing_Addressing_public_MapServer_0`
  （资产 652B / rows=0 / declared=3,821，第 4 个上游死层；首个为 04b 的 3 层）。

## 跑法

```bash
python3 collect/supervisor.py --entry-check    # 结构自检 25 条
python3 collect/check_docs.py                  # 判据卡一致性
python3 collect/supervisor.py --kick 0X        # 点火某一步
python3 collect/supervisor.py --tick           # 工头巡逻（cron 入口）
```

## 文件地图

```
collect/
├── ROADMAP.md            总图 + 三角色 + 铁律 + 七步表
├── SELF-DRIVE-v2.md      v2 设计由来（含 2026-10-23 事故复盘）
├── steps.json            ★ 唯一参数源
├── supervisor.py         工头机械部分（巡逻/证据/叫醒/自检）
├── check_docs.py         判据卡 ↔ steps.json 一致性校验器
├── supervisors/step_0X.py  7 个单步工头（只报步号，参数读 steps.json）
├── worker_core.py        引擎：选层/单元/通道/对账
├── lib/                  fetch / schema / units 公共层
├── run_step_0X.py        7 个工人入口
├── steps/STEP-0X.md      7 份判据卡
├── state.json            事实账本
├── blocked.json          跳过清单
├── wake/WAKE.json        最近一次叫醒的证据包
├── tests/                26 条单测
└── layer_plan.csv        预检产物（每层该怎么搬）
```
