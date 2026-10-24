# world-map-data-33 — 三仓采集项目

**版本：v2.1（自研模式）· 2026-10-24**

把 NG911 地址普查里所有对我们有用的地址点，完整、可对账地搬回 GitHub Releases。
公开仓库，2026-10-22 创建；数据源普查在 `survey/`，采集流水线在 `collect/`。

---

## 两个目录

- `survey/` —— **普查**：数据源里有什么、能不能拿。见 `survey/ng911/INDEX.md`
- `collect/` —— **采集流水线**：怎么搬回来、每一步怎么验收。见 `collect/ROADMAP.md`

普查会反复重跑（季度漂移监测）；采集一次跑完产出数据。两者分开放，避免互相污染。

---

## 怎么跑（v2.1）

```bash
python3 collect/supervisor.py --entry-check          # 25 条结构红线自检
python3 collect/check_docs.py                        # steps.json ↔ 7 份判据卡比对
python3 -m pytest collect/tests -q                   # 26 条单测

python3 collect/supervisor.py --kick 03 --workers 4  # 大脑点火（唯一放量入口）
python3 collect/supervisor.py --tick                 # 工头巡逻（cron 每小时，7 步共用一个）
python3 collect/supervisor.py --review pass --next 04 --note "验收理由"
python3 collect/supervisor.py --review fail --note "为什么不行"   # 停住并关单
```

分工：**工人**只采、**工头**只叫醒、**大脑**只判。判定权不在脚本里。

---

## 约定

- 本仓库由 pi 维护，改动走 commit
- 所有参数只有一个来源：`collect/steps.json`
- 每一大步完成、每一步判完，都推一条企微简报（`【三仓项目】` 前缀）
