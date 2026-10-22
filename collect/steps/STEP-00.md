# STEP 00 — 地基

**目标**：把「图纸 + 账本 + 报工员 + 兜底看守」四件东西立起来，保证后面每一步都有人叫醒执行者。

**方法**
1. `ROADMAP.md` 定总图与验收判据
2. `state.json` 建账本
3. `scripts/herald.py` 造报工员（读账本 → 判验收 → 开 Issue，自带地图）
4. `.github/workflows/herald-watchdog.yml` 造兜底看守（每 30 分钟查：有没有 workflow 卡死 / 账本和现实对不上）

**产出**：4 个文件 + 1 个 workflow

**验收判据（机器判）**
- `state.json` 能被 herald 读出 step 00 且状态可写
- herald 自检模式（`--selftest`）能成功创建一个 Issue 并读到它
- watchdog 在 Actions 上跑一次 exit 0

**失败怎么办**：token 权限不够就改 `permissions:`；Issue 建不出来就换 `gh api` 直连；都没有就写文件到仓库代替 Issue。

**本步一停必须叫醒我。**

**下一步**：`STEP-01.md`（预检）
