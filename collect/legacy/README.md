# 历史文件（不再作为判断依据）

- `geo_state-2026-10-25.json` —— 旧版州定位账（todo 4359 / still_unknown 656）。
  口径与现行的 `layer_plan_clean.csv` 不同（它只覆盖 parcel 子集），
  2026-10-28 核查时确认无任何脚本消费它，故移出主目录，避免被误读成"当前未定位数"。
  当前真实未定位数看 `collect/plan_clean_report.json`（由 stat_plan.py 生成）。
