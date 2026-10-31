# WORKFLOW 故障清单 · 世界地图三仓（world-map-data-33）

> 立规：2026-10-31。用户原话：**每个仓建一份 workflow 故障清单，写之前必查、跑后必补。**
> 本文是该仓 workflow 的**唯一故障台账**（唯一真值）。别处写的「踩坑记录」一律以本文为准并回链到编号。
>
> **本表条目以代码 / 文档可复核证据为准，记忆与传闻不入表。**（证据路径见 §3；复核不了的一律标「待复核」或搬进附录 A）
>
> 三条铁律：
> 1. **写之前必查**：派单前先查本文 + 本次涉及的类别，派单里写 `故障清单已查：<编号列表 | 无>`，没有这行视为无效派单。
>    机械门禁：`collect/preflight_dispatch.py` 的 **F16** 读本文 → 输出 `ledger_hits[]`
    （2026-10-31 改版：**复发 ≥2 且未规避 → FAIL**；**复发 ≥2 且已规避 → WARN**（打印修复 sha + 验证方式）；
    未规避且复发 = 1 → WARN；台账缺失 / 表解析失败 → FAIL。`--ledger-waive 编号=理由` 显式豁免，**空理由拒绝执行**）。
> 2. **跑后必补**：新踩的坑**当天**补进本文（含错误原文关键行、证据路径、修法、验证方式、关联提交），**不许事后凭记忆补**。
> 3. **补完提交**：commit message 写 `ledger: +N <类别>`（例如 `ledger: +2 账本与口径`）。
>
> 类别固定 10 个：`并发队列` `artifact与下载` `git提交` `账本与口径` `checkpoint与断点` `切分与体积` `采集器逻辑` `上游不可达` `缓存与签名` `测试与CI`。

## 0. 本仓 workflow 骨架速查（写之前先看这一段）

- **采集唯一入口 `collect-full.yml`**：`workflow_dispatch`，输入 `stage(04b/05b/07b/10b)` `size` `workers` `unit_rows` `max_shards` `chain` `authorize_heavy` `force_layers` `layer_timeout` `rebuild_ledger` `plan_run_id`；并发组 **`collect-full-<stage>`**（`cancel-in-progress: false` → 同组只留 1 个 pending）；`plan` job 第一步就是 preflight 门禁；分片 job 上限 350 分钟、`max-parallel: 8`。
- **产物落点**：`collect/ledger/<stage>_plan.json`（计划）、`collect/ledger/<stage>_shardNN.json`（每片账本，每层增量写）、`collect/ledger/<stage>_run<RUN_ID>.json`（单 run）、`collect/<stage>_ledger.json`（阶段账本，只做按层合并）、`collect/ledger/step04b_rebuilt.json`（资产真值快照）、`docs/STEP0N-FULL-*-shards.md`（分片口径收官文档）、`docs/STEP04-ADJUDICATED-*.md`（判定修正层）。artifact `plan-<stage>` / `led-<stage>-<n>` / `final-<stage>` **只兜底，主路径走 git 提交**。
- **数据真值在 Release**：tag `collect-step0N-<layer>` 下 `<layer>-checkpoint.json` + `<layer>-uNNNNN.tar.gz`；账本口径一律「资产反推」优先。
- **自检 `ci-smoke.yml`**：push 到 `collect/**` `scripts/**` 触发，五道闸（`compileall` / `supervisor.py --entry-check` 25 条 / `check_docs.py` / `unittest discover` / 选层干跑）。
- **专项入口**（人工 dispatch）：`collect-oid-range.yml`（定向区间 `--oid-range lo:hi`）、`county-fill.yml`、`geo-fill.yml`、`ng911-*.yml`、`collect-supervisor.yml`、`worker-00..10.yml`、`address-probe.yml`。

## 1. 台账

| 编号 | 发现日期 | 类别 | 症状（错误原文关键行） | 根因 | 影响（数据/账本/时间/假红） | 修法 | 验证方式 | 关联提交 | 复发次数 |
|---|---|---|---|---|---|---|---|---|---|
| W33-001 | 2026-10-30 | 并发队列 | run `41126178216` 派出后，先前排队的 `41124980564` 直接 `conclusion=cancelled` 且 **0 个 job 执行** | GitHub 同 concurrency group 只保留**一个** pending，新派单会静默把旧 pending 变 cancelled | 时间：白排一整轮；数据：无（没跑）；**极易误判成「被上游取消」** | 同组一次只排一条；派单前必须查 `pending`（preflight A1）；要排队就等它变 in_progress 再派 | `gh run list --workflow collect-full.yml --json status,concurrency,createdAt` 同组只剩 1 条非 completed | 无（行为由 GitHub 决定，靠流程规避） | 1 |
| W33-002 | 2026-10-31 | 并发队列 | 手派 07b 时上游 05b 正在跑 → 05b 全绿会自动 dispatch 07b，两条撞同一组 | 接续逻辑（chain）与人工派单共用同一个 concurrency group | 时间：撞组后手派那条可能被挤掉；数据：无 | 派 07b 前查上游 run：上游会自己派就等它派；要手派就确认上游 `chain=0`（preflight A1b 已 WARN） | `collect/chain_policy.py --stage 05b --dry-run` 与在跑 run 的 `chain` 输入 | d685af8 | 0 |
| W33-003 | 2026-10-24 | 并发队列 | 100 并行 job 抢 main：`failed to push some refs ... ! [rejected] main -> main (fetch first)`，重试 10 次仍被拒 | 分片/报告 job 各自 push，无串行化也无硬对齐 | 时间：报告连续被拒；账本：报告 commit 丢 | 报告 job 改硬对齐 `origin/main` 只提交自己的文件；心跳加抖动 | 100 并行下报告 job 一次过（`run-watch` 无 push 冲突） | c78cd0e；c3530c1 | 0 |
| W33-004 | 2026-10-30 | artifact与下载 | `Unable to download artifact(s): ... failed after 5 retries` → run `41120626718` **9 片假红**、后续一轮 **14 片全红** | 8~14 个分片**同时** `gh run download`/`download-artifact` 同一个 artifact，撞账号 egress 配额 | 假红：整轮看着全红，数据其实没问题；时间：每片 5 次重试 | 计划/片账本**走 git 提交**（本来就有），artifact 只当兜底；取 artifact 也改 `gh run download` + 重试 | 一轮全量跑下来无 `failed after 5 retries`；片账本能从 git 读到 | a348351；cf8ab47；7ed74c8；e6d602a | 2 |
| W33-005 | 2026-10-30 | artifact与下载 | 取计划 artifact 重试 5 次全报 `error downloading plan-05b: error extracting zip archive: error extracting "05b_plan.json": openat 05b_plan.json: file exists` → 整片红（**原文已钉**：run `41122821137`，job `shard (6)`，step「取计划 artifact（带重试，避开下载限流）」，2026-10-30T20:24:34Z 起连续 5 条同错） | `gh run download` 解压**不覆盖**同名文件：第 1 次成功后 zip 里已有 `05b_plan.json`，重试再解压撞 `file exists`；重试循环没有先清目标目录。注意原文里**没有** `FileExistsError` 字样（那是转述） | 假红：数据/计划已在包内，纯重试逻辑自杀 | 重试前先 `rm -rf` 目标目录（或 `gh run download` 到临时目录再搬）；脚本里不许把「解压已存在」当失败 | 对同一 artifact 连下载 2 次不再报 `file exists`；`rg 'file exists'` 在 shard 日志里 0 命中 | cf8ab47；e6d602a（计划/片账本改走 git） | 0 |
| W33-006 | 2026-10-30 | artifact与下载 | 收官文档写成 `docs/04B-FULL-2026-10-30.md`，但提交步与上传步都在找 `DOC=$(ls docs/STEP0*-FULL-*.md …)`（取不到就空）与 `path: docs/STEP0*-FULL-*.md` → **连 artifact 都没留**（**原文已钉**：run `41092912755`，job `merge`，step「提交（账本 + 文档）」，2026-10-30T19:17:13Z；该 run 的 `final-04b` artifact 实际内容只有 `collect/`，无 `docs/`） | 文档名把 stage 写成 `04B`，glob 只认 `STEP0N` | 账本：文档丢（账本 JSON 在）；时间：事后重跑一次 | 命名统一（`STEP04B-FULL-*`）+ glob 放宽成 `docs/*FULL-*.md` 双 pattern | `ls docs/*FULL-*.md` 与 workflow `path:` 的 glob 匹配；`gh run download <run> -n final-<stage>` 里能下到文档 | 7ed74c8（glob 放宽）；cf8ab47 | 0 |
| W33-007 | 2026-10-30 | git提交 | 采后提交步 `git checkout -q -B main origin/main` → `error: Your local changes to the following files would be overwritten by checkout` → **shard 4/5/7/8 整片假红** | 采集产物没清干净，裸 `checkout` 被未提交文件拒；`-q` 把错误压得更难看见 | 假红：4 片全红；账本：这 4 片的账没提交 | `checkout -q**f**` + 硬复位保险（`git reset --hard origin/main` 后再搬产物） | 分片跑完产物目录脏时，提交步 rc=0 且 `git log` 有该片账本 | 74af38f；9300f91；037e984；cb86f42 | 3 |
| W33-008 | 2026-10-30 | git提交 | merge 提交步 `git rebase` 卡在 `cannot rebase: You have unstaged changes`，且该行 `2>/dev/null` **把错误吞了** | rebase 要求工作区干净；错误被重定向丢弃 → 脚本以为成功 | 账本：**merge 说成功但账本没落地**（最危险的一类） | 产物先搬到 `/tmp` → `checkout -qf` 硬对齐 → 搬回 → 只 `git add` 自己的文件；**不许 `2>/dev/null` 吞错误** | `git log origin/main -- collect/<stage>_ledger.json` 有本轮提交；脚本失败时 rc≠0 且日志有原文 | e758d26；0c62357；c3530c1 | 1 |
| W33-009 | 2026-10-30 | git提交 | merge 闸门 `KeyError: 'STAGE'` → merge job 判红 | 闸门脚本用 `os.environ["STAGE"]`，workflow 没注入 | 假红：账本其实已生成 | 显式注入 `env: STAGE: ${{ inputs.stage }}`；脚本侧改 `os.environ.get` 并给默认报错信息 | 手动 `STAGE=04b python3 <gate>` 与 job 内一致；job 不再 KeyError | 0c62357 | 0 |
| W33-010 | 2026-10-30 | 账本与口径 | 分片账本写成 `collect/ledger/step04b_shardNN.json`，汇总脚本 glob 找 `collect/ledger/04b_shard*.json` → **账本静默落空**（merge 报 0 层） | 命名两套：`step04b` 与 `04b` | 账本：整轮 merge 空账；排查 2 小时 | 统一 `<stage>_shardNN.json`，汇总脚本双 pattern 兜底（`<stage>` 与 `step<stage>` 都认） | merge 后 `collect/ledger/<stage>_run<id>.json` 的 `layers_n` 与计划片层数一致 | ab56323；7ed74c8 | 0 |
| W33-011 | 2026-10-30 | 账本与口径 | merge 把「本次 run 的片汇总」直接写成阶段账本：run `41092912755` 把 **272 层冲成 20 层**、run `41121952357` 冲成 **31 层**（`layers_n 272→31`、`shards_expected=3`） | 单 run 结果与阶段账本共用同一个文件，写入逻辑没有按层合并 | 账本：阶段口径被冲掉（层/行数结论全错），**发生过 2 次** | 单 run → `collect/ledger/<stage>_run<RUN_ID>.json`；阶段账本只做按层合并（状态优先 + 同状态取大）+ 小 run（<1/2）不碰阶段文件（`--allow-stage-overwrite` 才覆盖） | `test_ledger_merge.py` 全绿；跑完看 `collect/<stage>_ledger.json` 的 `layers_n` 未变小 + `revisions[]` 有本轮 | 35904fb；a478570（f68c002 合入） | 2 |
| W33-012 | 2026-10-30 | 账本与口径 | 单 run 的 plan 覆盖阶段 plan：`collect/ledger/04b_plan.json` 从 **272 层 / 14 片** 变成 **22 层 / 3 片** | run 的 plan 提交直接写同一个文件，没区分「round plan」与「阶段 plan」 | 账本：之后所有以 plan 为分母的统计（缺口/片数）全错 | 复原阶段 plan；run 自己的 plan 走 artifact `plan-<stage>` + run 级账本记录，不覆盖阶段 plan | `jq .layers_n collect/ledger/04b_plan.json` = 272；`shards_n` = 14 | 35904fb | 1 |
| W33-013 | 2026-10-30 | 账本与口径 | shard 1/3/6 卡上游被 350 分钟掐成 `cancelled` → **前面跑完的层也一起消失**，整片「零痕迹」 | 账本只在循环结束后写一次 | 账本：已采层的账全丢（数据在 Release，账上没有） | 每层增量落盘（`partial_run=true`）+ 账本显式记 `shards_expected/reported/incomplete/incomplete_detail` | 人为 kill 分片后账本仍有已跑完的层；merge 的 `shards_incomplete` 非空 | f3fdc02；ab56323；f46589a | 0 |
| W33-014 | 2026-10-30 | 账本与口径 | `full_shard.py`：`if rc != 0 or err: rec.update(status="failed", ...)` → 任何非 0 退出码都判 failed 并计入阶段 failed | 只区分「0 / 非 0」，没有「上游未就绪/参数错」这类可跳过语义 | 假红：本可以跳过重试的层被记成 failed，阶段永远不收敛 | 约定退出码：`2 = 上游未就绪（可跳过）` → 记 `unverified` + warning，不判 failed；`pilot.py` 目前把 2 用于 `unknown layer`/参数错，改前必须先统一语义 | 构造 rc=2 的层，跑完账本该层 `unverified` 且 `failed` 不变 | 未修（pilot.py 的 2 目前是参数错，改语义属采集口径变更，需单独审批） | 0 |
| W33-015 | 2026-10-31 | 账本与口径 | 合并「状态取优者 + 同状态取大者」把真退化永久掩盖：`partial 39,875,268 → ok 5,000,000` 合并后账本 rows 真变小，但**没有任何一处留痕** | 只在内存里比一次就丢，没落账 | 账本：真丢数据查不出来（只能看到总数莫名变小） | 合并前逐层比 rows，变小写 `regressions[]`（层/旧/新/差额/原因/证据）+ `rows_regressions` 计数；人读摘要单列一节；**不拦截**但必须点名（证据：`row_shrink_evidence{layer:path}`） | `test_ledger_merge.py::RowsRegressionNotSilent` 9 条；收官文档有「七、rows 回退」节 | fb85504（3f3c9b9 合入）；f55f6a5 | 0 |
| W33-016 | 2026-10-30 | 账本与口径 | 汇总脚本只认「片 = list」，`full_plan.py` 写的是 `{"shard":0,"layers":[...]}` → 片号对不上、未完成片漏报 | 计划结构改过（list → dict）但消费方没跟 | 账本：缺片不被发现（看着 100% 完成） | 两种结构都认（`expected_of()`），片号优先取字段再回退文件名 | 计划为 dict 结构时 merge 的 `shards_expected` = 计划片数 | ab56323 | 0 |
| W33-017 | 2026-10-30 | 账本与口径 | 全国 NAD 汇总层与各县层重复：`声明 3,197 万 / 实际 7,594 万`（+44,109,677 行全来自 8 层） | 计划期 `row_count` 估算，大层普遍低估；同一批地址在汇总层与县层各出现一次 | 账本：以声明为分母会低估缺口，按实际读入才准；数据：必须靠 3 元组去重 | 统计一律以**实际读入**为准；去重键 `number` + `street_key` + `unit_key` 3 元组，不靠「声明不重复」 | 重算 `gap_pct` 用实际读入；去重后行数守恒 | 见 `docs/COUNTY-ASSIGN-2026-10-30.md` | 0 |
| W33-018 | 2026-10-30 | checkpoint与断点 | `--force-layers` 重跑把 NAD-view 检查点覆盖成 `1 unit / 0 行 / unit_uploaded=false / done_units=[0]`（441 B），而 Release 上 68 个 `u00000..u00067.tar.gz`（4.60 GB）一个没少 | 重跑按新切分整份写 checkpoint，不认旧单元包；`--force` 路径没备份 | 账本：`partial(39,875,268) → failed(0)`，`ledger_rebuild` rows 少 33.4M；**数据没丢但完成度证据被抹** | force 前备份（本地+Release 各留 3 代）+ 按**旧单元包名**逐项合并（旧包仍在 Release 且 `size>0` → 保留行数 + `unit_uploaded=true` + `legacy_split=true`）；切分不兼容时单元包加代际前缀 `r<planhash8>-` | `test_ckpt_guard.py` 18 条；`analysis/nad-view-rebuild-2026-10-31.json` 68 包/816 part/39,875,268 行、`--expect-rows` delta 0 | 2d6c2af（PR #12） | 0 |
| W33-019 | 2026-10-30 | checkpoint与断点 | 无计划文件的兜底路径把 **tag 当 layer id** → `238 层真资产被误标 empty` | 兜底分支没做 tag → layer 映射 | 账本：238 层被判「上游无数据」，白采风险极大 | tag → layer 显式解析（`collect-step0N-<layer>` 去前缀），解析不出就 `unverified` 不许 `empty` | `ledger_rebuild` 对无 plan 的 tag：`empty` 层数 0 或全部有理由 | 1d4c117 | 1 |
| W33-020 | 2026-10-31 | checkpoint与断点 | 本机 `main` 停在 `2161d50`、远端 `main` 是 `d5b5db2` → 门禁把「代码版本不一致」判成假 FAIL | 任何「与 main 比对」的逻辑读本地 `main` 而不是 `origin/main` | 假红：明明已合入却被判缺修复 | 一律 `origin/<ref>` 优先（`resolve_ref` 先试 `origin/`），本地 `main` 只作兜底 | `preflight 04b --ref main` 的 `ref_sha` == `origin/main`；B3 不再报缺修复 | 8724a98（preflight） | 1 |
| W33-021 | 2026-10-30 | 切分与体积 | 按行数切单元必撞 2GB 上限（某层 **32.6 KB/行**，50 万行就 16 GB） | 只按 `unit_rows` 切，不看字节 | 数据：单元上传失败/整层红；时间：重切重跑 | `unit_rows` + `unit_bytes=1.5 GB` 双上限**先到先切**（`PILOT_UNIT_BYTES`），单元字节写进 checkpoint `unit_bytes` | 大单元层跑完 `unit_bytes` 全部 < 1.5e9；上传成功率 100% | 566b20b | 0 |
| W33-022 | 2026-10-30 | 切分与体积 | `returnIdsOnly` 返回的 `objectIds` 被截断（超过上限只给一部分）却照单全采 → **安静少采 80%** | 没识别「截断」信号，也没退回 keyset 分页 | 数据：少采且账本看着 ok（最坑的一种） | 截断即退回 keyset 分页（`where` 范围切分），并把策略写进报告 `funnel` | 对照 `returnCountOnly` 与实采行数：差距 < 1% | e2068b3 | 0 |
| W33-023 | 2026-10-30 | 采集器逻辑 | 单层无墙钟上限 → 某层吃满 **350 分钟**把 job 掐死，整片 cancelled | 只在 job 级设 timeout | 时间：整片白跑；账本：零痕迹（见 W33-013） | 单层 60 分钟上限（`--layer-timeout`，workflow 输入 `layer_timeout`）+ 每层增量落盘 + 超时记 `failed(reason=job 内单层超时)` | 挂死层在 60 分钟被切并继续下一层；账本有该层 `failed` 原因 | f46589a；404fa50 | 0 |
| W33-024 | 2026-10-30 | 采集器逻辑 | 07b 跑完**自动接宗地 10b**（20~85 GB），派单里硬编码 `-f chain=1` | 接续表写在 workflow 的 shell `case` 里，允许清单不存在 | 数据：误采重阶段烧配额；时间：数小时 | 接续策略进 `collect/chain_policy.py`（唯一真值 + 单测）：`04b→05b→07b`、**07b 的 NEXT 为空**、允许清单只放 05b/07b、子 run 一律 `chain=0`（单跳不级联）+ 10b 必须 `authorize_heavy=1` | `chain_policy.py --all --dry-run`；`test_chain_policy.py` 全绿；07b 收尾日志 `decide=stop` | d685af8 | 0 |
| W33-025 | 2026-10-30 | 采集器逻辑 | 按属性州过滤判县：肯塔基层被标成 `IN` → 旧实现把 **490 万行整层假判成 UNLOCATED** | 用「层属性里的州」当判县依据，而数据横跨州界 | 数据：整层被误判丢弃（490 万行）；账本：unlocated 数虚高 | 全国县索引 + 用清单州做命名/统计，判县只看坐标落在哪个多边形；属性州只用来记 `anomaly`，不参与过滤 | 重算该层 `unlocated` 占比下降且行数守恒；`docs/COUNTY-ASSIGN` 复现 | 09d8472 | 0 |
| W33-026 | 2026-10-30 | 采集器逻辑 | `collect-oid-range.yml` 的 `layer_timeout` 那行少个空格 → YAML 把整行当标量 → `422` 且 `workflow_dispatch` 入口直接消失 | YAML 键值少空格 | 时间：派单 422，排查一圈 | 加空格；改 workflow 后必须 `yaml.safe_load` 自检 | `python3 -c "import yaml;yaml.safe_load(open('.github/workflows/x.yml'))"`；`gh workflow view` 有 dispatch | 5591172 | 0 |
| W33-027 | 2026-10-30 | 上游不可达 | 本机 3 轮超时判「上游无数据」，而 CI 同一层采到 **137 万行** | 把「本机不可达」当「上游 0 行」 | 账本：真数据被标 `empty`（白采风险） | 不可达只标 `unverified`，不许 `empty`；`empty` 必须有 `returnCountOnly=0` 或 esri 404；本机 ≠ CI 写进判据 | 重测 3 轮（间隔 31.6/31.1 分钟）后 `unverified` 层的判定有证据 | 7c7a242；be11ebd；86adc5c | 1 |
| W33-028 | 2026-10-31 | 上游不可达 | NAD-view 层 `/0?f=json`、`returnCountOnly`、`returnIdsOnly` **全部 499 `Token Required`** → 该层已无法再采 | 上游把该服务切成**服务级 token**（连元数据都要 token，且 tier 不足） | 数据：该层永久停采（39,875,268 行是现有上限）；账本：见 W33-033（改判 `capped_by_upstream`，不再挂 unverified） | 该层标 `capped_by_upstream`：已采 39,875,268 行计 `rows`，declared 移出分母记 `declared_unverifiable`；除非拿到 token，否则不再派 | 三个端点复测仍 499 即确认；preflight E13/E14 报「服务级 token」 | 证据见 `analysis/`（2026-10-31 探测） | 0 |
| W33-029 | 2026-10-31 | 缓存与签名 | `ledger_rebuild` 早先按 tag 名缓存 checkpoint → Release 重发同名文件后**静默复用旧内容** | 缓存键只有文件名 | 账本：用旧检查点算出「完成度」，与资产不符 | 内容寻址缓存 `tag@created_at`（Release 重发 → `created_at` 变 → 自然失效），无需 `--refresh` | 重发 checkpoint 后重跑 `ledger_rebuild`，行数跟着变（不再用旧缓存） | 见 `collect/ledger_rebuild.py` 头注释 | 0 |
| W33-030 | 2026-10-30 | 测试与CI | 单测把 `step_full_report.py`/`ledger_merge.py` **复制到临时目录**运行，新增依赖没一起 copy → `ModuleNotFoundError` 假红 | 测试用「复制脚本」而不是「按模块导入」 | 假红：CI 红但代码没问题（也掩盖真错） | 复制清单随依赖更新（`ckpt_guard.py`/`ledger_merge.py` 都要 copy）；新增模块时同 PR 改测试 | `test_full_report_tolerance` 与全量 unittest 本地全绿且 CI 绿 | 见 `test_full_report_tolerance.py` | 1 |
| W33-031 | 2026-10-24 | 测试与CI | `python3 -m py_compile scripts/*.py` 在目录为空时 glob 不展开 → `No such file or directory`，**CI 连续 4 次假红** | shell glob 空展开把字面量当路径 | 假红：4 次 | 改 `compileall.compile_dir()`，目录不存在/为空就跳过并报明确信息 | CI 在空目录分支上不再假红 | ci-smoke.yml 内注释（2026-10-24 事故） | 0 |
| W33-032 | 2026-10-30 | 采集器逻辑 | 2,327 个已采层里 **1,127 层（48.4%）没有时间字段** → 「增量同步」对它们无效 | 源数据没有 `last_edited_date` 之类字段 | 对外承诺风险：不能承诺「全量可增量」 | 逐层记能力（`LAYER-TIMESTAMP-PROBE`），只有 928 层可增量；对外按层说清 | 重跑探测脚本，分层能力表与账本一致 | 3141bab | 0 |
| W33-033 | 2026-10-31 | 上游不可达 | 上游把服务切成**服务级 token** 后，整层永久不可采，而账本里它会**伪装成「0 行 / 我们没采」**：三端点全返回 **HTTP 200** + `{"error":{"code":499,"message":"Token Required","messageCode":"GWM_0003"}}` | 只看 HTTP 状态码 → 200 当「服务正常」；账本把「采不到」记成 `missing`/`partial`，等于把上游变更算成我们的欠账 | 账本：97,928,946 行虚假缺口稀释分母（gap% 14.2735% → 5.1331%）；时间：每轮派单都重采一遍、永远 0 行 | ①新状态 `capped_by_upstream`：已采行数照旧计 `rows`，`declared` 移出分母记 `declared_unverifiable`；②判据=**连续两轮** 3 端点全 499（`collect/probe_service_token.py`）；③preflight **E14** 两轮确认后只**建议**改判并打印命令，**不自动改账本** | `adjudicate_04b.py --capped --capped-evidence …` 重放 `--check` = `IDENTICAL`；账本 `capped_by_upstream=1`、`capped_layers[]` 带证据路径；单测 `test_adjudicate_04b`/`test_probe_service_token`/`test_preflight_dispatch` | 见 `docs/STEP04-ADJUDICATED-2026-10-30.md` §3.0；证据 `analysis/04b-token-499-evidence-2026-10-31.json` | 1 |
| W33-034 | 2026-10-31 | 账本与口径 | 声明值为过期快照：**80 层实采 > 声明、超采合计 3,547,920 行**（rebuilt 口径 81 层 / 3,547,930；全账 `gap` 24,751,959）→ 覆盖率算不准，且「按声明分母 / 按可核实分母」两个百分比**不可相减**，解释负担全压在读报表的人身上 | 声明值来自 `layer_plan.csv` 的计划期快照；上游缩水/删数据/改口径后没人刷新，分母永久用旧值 | 账本：覆盖率系统性偏高或偏低（看哪边变化大）；对外数字没有共同口径，每次都要口头补解释 | 分母定期用上游 `returnCount` 刷新（只对 ok/missing/partial 且可达的层），刷新记录进账本 `declared_refreshed_at` + `revisions[kind=declared_refreshed]`；**对外一律报两个数**（`按声明分母` / `按可核实分母`，剔除 capped + 已刷新），禁只报一个 | `python3 collect/adjudicate_04b.py --refresh-declared` 出「旧声明/新声明/实采/关系」差异表（只读）；采纳后账本出现 `declared_refreshed_at` 与 `revisions[kind=declared_refreshed]`；`--apply-declared-refresh` 缺口号则拒绝写盘 | 见 `docs/STEP04-ADJUDICATED-2026-10-30.md` §3.0.1（机制已落；首轮刷新待 04b 收口后执行） | 0 |
| W33-035 | 2026-10-31 | 账本与口径 | 同一上游层被拆成 `@<州>-1/-2` 两个分区时，**两个分区都写了全量 declared** → 分母重复计一次，制造整层假缺口。实例：`_secure_…_NC1Map_Addresses_MapServer_0@未定位-1` declared 6,297,169 / 0 行（missing），而 `@未定位-2` 实采 6,648,000 行 ≥ 全量 6,297,169（上游 `returnCount` 实测同值）→ 该 6,297,169 是**假缺口** | 分区声明没有按上游计数拆分：同一 base 层的每个分区都继承了整层 declared。对照反例：`Maricopa@AZ-1/-2`（2,139,288+2,078,539）、`Hennepin@MN-1/-2`（481,609+480,300）都拆开了 → 说明是逐层数据问题，不是普遍机制 | 账本：missing 6 层里 1 层是假缺口（6,297,169 行 ≈ 总声明的 1.3%），gap 24,751,959 虚高；capped 判定若按分区做会重复报 | 分区层的 declared 必须按上游计数拆（或按已采行数守恒校验：Σ分区 rows 与 Σ分区 declared 同量级）；同一 base 层已有某分区实采 ≥ 全量时，其余分区 declared 置 null 并注明「重复声明」 | `Σ分区 declared` 与 base 层 `returnCount` 相差 <1%；本次实例 12,594,338 vs 6,297,169（**2 倍**）即应报警 | 未修（需人工点头把 `@未定位-1` 的 declared 移出分母；证据：`gh api releases/tags/…@未定位-2` 4 包 + `returnCount=6,297,169`） | 0 |

## 2. 用法（照抄即可）

```bash
# ① 派单前：查清单 + 本次涉及的类别（preflight F16 会自动读本文并输出 ledger_hits[]）
python3 collect/preflight_dispatch.py --stage 04b --ledger-category 账本与口径,并发队列
#   复发 ≥2 且**未规避** → FAIL；复发 ≥2 且**已修** → WARN（只提醒「确认未重新引入」+ 打印验证方式）
#   真已规避还要豁免时：理由必填（空理由 / ok / 无 → rc=2 拒绝执行）
python3 collect/preflight_dispatch.py --stage 04b \
    --ledger-waive 'W33-011=a478570 已按层合并且 test_ledger_merge 全绿，本单只动 preflight'
#   豁免与理由写进 analysis/preflight-*.json 的 evidence.ledger.waivers[]

# ② 派单里必须写这一行（没有 = 无效派单）
#    故障清单已查：W33-011,W33-013（或「无」）

# ③ 新坑当天补：加一行 + 证据路径 + 修法 + 验证方式，然后
git commit -m "ledger: +1 账本与口径   # 例：W33-034 ..."
```

## 3. 证据路径索引（本文引用到的仓内文件）

- `docs/PREFLIGHT-GATE.md`（派单门禁 16 项 / FAIL 处置表 / 已批准版本白名单）
- `docs/COUNTY-ASSIGN-2026-10-30.md`（判县 / 汇总层重复 / 490 万行假 UNLOCATED / 3,197 万 vs 7,594 万）
- `docs/LAYER-TIMESTAMP-PROBE-2026-10-30.md`（2,327 层 / 928 可增量 / 1,127 无时间字段）
- `docs/LEDGER-MERGE-GUARD-2026-10-31.md`（rows 回退 `regressions[]` 护栏）
- `docs/CHECKPOINT-GUARD-2026-10-31.md`（force 重跑 checkpoint 合并/备份）
- `docs/ROLLBACK-20261031.md` / `docs/FREEZE-4-7-20261031.md`（回退与冻结口径）
- `analysis/nad-view-rebuild-2026-10-31.json`（68 包 / 816 part / 39,875,268 行）
- `analysis/04b-ledger-restore-events.json`（阶段账本复原事件，只追加）
- `analysis/04b-upstream-evidence-2026-10-30.json`（上游 returnCount 取证）
- `analysis/04b-token-499-evidence-2026-10-31.json`（服务级 token：2 轮 × 3 端点全 499，含 499 原文）
- `collect/tests/test_ledger_merge.py` / `test_ckpt_guard.py` / `test_chain_policy.py`（对应修法的回归）

## 附录 A：被推翻的传闻（2026-10-31 首次实战）

> 本节记「曾经当事实流传、复核后被推翻」的说法。**保留原文 + 推翻依据**，防止它们换个说法再回来。
> 用户 2026-10-31 原话：这五条「全部按你的证据改，我这边不再坚持」——清单的第一次实战价值就是**把人的错也筛出来**。

| # | 传闻（原说法） | 复核结果 | 推翻依据（可复核） |
|---|---|---|---|
| A1 | 一仓「TIGER 补抓 GA 有 46.2% 顶点落进邻县 bbox」 | **无出处，不作数** | 一仓 `grep -r '46.2'` 零命中；已用可核数字替换（`docs/NAD-COVERAGE-2026-10-28.md`：Clayton bbox 235 / 多边形 0；`docs/NAD-COVERAGE-FULL-2026-10-30.md`：`bbox_false_positive_n: 32`） |
| A2 | 「Kentucky 层属性州标成 IN → 490 万行假 UNLOCATED」是**一仓**的坑 | **属三仓**（已记 `W33-025`） | 一仓 `grep -rn UNLOCATED` 0 命中；实现与证据都在三仓：`collect/county_assign.py`、`docs/COUNTY-ASSIGN-2026-10-30.md:334` |
| A3 | 「NAD 汇总层与县层重复（声明 3,197 万 / 实际 7,594 万）」是**一仓**的账本坑 | **属三仓**（已记 `W33-017`） | 同上：`docs/COUNTY-ASSIGN-2026-10-30.md:36`（三仓 `collect/` 侧统计口径），一仓无对应实现 |
| A4 | 二仓「G3 缺 addrfeat 不拒跑 / G9 无离线自测 / G11 `oa_rows` 恒 None」按**现状缺陷**记 | **均已修**，只能按历史记（`W2-009`/`W2-011` 等已标「已修」） | 二仓 `scripts/gold_preflight.py:139-141`（G3 只 WARN）、`tests/test_gold_offline.py` 存在（G9）、`scripts/gold_coalesce.py:1016-1017`（G11 已回填 `oa_rows`） |
| A5 | 二仓「Overture 缓存键只有文件名，多包互相覆盖」 | **更严重**：不是「按包名拼目录」，而是**固定单目录** `cache_dir/overture/`（`W2-013`） | `scripts/gold_coalesce.py:476-490`；三个缓存（OA 包名目录 / Overture 固定目录 / Actions `gold-cache-<ST>-v1`）**全都没有 size/hash/mtime** |

| A6 | 「反向溢出 43,423,188 行（81 层实采超声明）」是我自己在 2026-10-30 报告里给的数 | **不可复现，已改** | 按账本逐层重算：超采 **80 层 / 合计 3,547,920 行**；rebuilt 口径 81 层 / 3,547,930。差 40 倍——那个数当时是把「欠采合计 + 全账 gap」串了口径。**结论不受影响**（声明确实会过期），但对外只许引可复现的数：`gap` 24,751,959 / 超采 3,547,920 |
另注（**2026-10-31 已钉死，不再是待复核**）：`W33-005` 与 `W33-006` 的原始日志已用 `gh run view <run> --log \| grep` 捞到并写回行内（run id / job / step / 时间戳 / 原文），证据不落仓（日志太大），复核命令写在该行「验证方式」列。
