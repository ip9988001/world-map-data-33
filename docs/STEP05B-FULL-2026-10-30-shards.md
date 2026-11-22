# STEP05B 全量补采 · 收官账（2026-11-22）

## 一、总账

- 阶段：`05b` —— 县市碎片 05b（5,000~300,000 行）
- 计划：576 层 / 声明 31,416,597 行 / 192 片（每片 3 层，unit_rows=100000）
- 账本覆盖：**1241 层**（片文件 21 个）
- 逐态：**ok 1119** / capped_by_upstream 0 / empty 18 / partial 75 / failed 29 / skipped_done 0
- 片完成度：应有 **192** 片，有账本 21 片，**未完成 171 片**：片号 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191
- 声明行合计：**66,172,648**；实采行合计：**72,120,512**；差额 -5,947,864（-8.988%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 3 | 3 | 54,648 | 完成 |
| 1 | 200 | 200 | 7,248,389 | 完成 |
| 2 | 179 | 179 | 26,780,253 | 完成 |
| 3 | 50 | 50 | 467,524 | 完成 |
| 4 | 50 | 50 | 544,713 | 完成 |
| 5 | 50 | 50 | 598,520 | 完成 |
| 6 | 50 | 50 | 635,887 | 完成 |
| 7 | 50 | 50 | 766,340 | 完成 |
| 8 | 50 | 50 | 819,589 | 完成 |
| 9 | 50 | 50 | 915,863 | 完成 |
| 10 | 50 | 50 | 980,058 | 完成 |
| 11 | 50 | 50 | 1,057,328 | 完成 |
| 12 | 50 | 50 | 1,128,740 | 完成 |
| 13 | 50 | 50 | 1,196,183 | 完成 |
| 14 | 50 | 50 | 1,570,124 | 完成 |
| 15 | 50 | 50 | 1,748,349 | 完成 |
| 16 | 50 | 50 | 2,081,873 | 完成 |
| 17 | 50 | 50 | 3,338,421 | 完成 |
| 18 | 50 | 50 | 4,562,833 | 完成 |
| 19 | 50 | 50 | 6,807,437 | 完成 |
| 20 | 33 | 33 | 8,819,199 | 完成 |
| 21 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 22 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 23 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 24 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 25 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 26 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 27 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 28 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 29 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 30 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 31 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 32 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 33 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 34 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 35 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 36 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 37 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 38 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 39 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 40 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 41 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 42 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 43 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 44 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 45 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 46 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 47 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 48 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 49 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 50 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 51 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 52 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 53 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 54 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 55 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 56 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 57 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 58 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 59 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 60 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 61 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 62 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 63 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 64 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 65 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 66 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 67 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 68 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 69 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 70 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 71 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 72 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 73 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 74 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 75 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 76 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 77 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 78 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 79 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 80 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 81 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 82 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 83 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 84 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 85 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 86 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 87 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 88 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 89 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 90 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 91 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 92 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 93 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 94 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 95 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 96 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 97 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 98 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 99 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 100 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 101 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 102 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 103 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 104 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 105 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 106 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 107 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 108 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 109 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 110 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 111 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 112 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 113 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 114 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 115 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 116 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 117 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 118 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 119 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 120 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 121 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 122 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 123 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 124 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 125 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 126 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 127 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 128 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 129 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 130 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 131 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 132 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 133 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 134 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 135 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 136 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 137 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 138 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 139 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 140 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 141 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 142 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 143 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 144 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 145 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 146 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 147 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 148 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 149 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 150 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 151 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 152 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 153 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 154 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 155 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 156 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 157 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 158 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 159 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 160 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 161 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 162 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 163 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 164 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 165 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 166 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 167 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 168 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 169 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 170 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 171 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 172 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 173 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 174 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 175 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 176 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 177 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 178 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 179 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 180 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 181 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 182 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 183 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 184 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 185 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 186 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 187 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 188 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 189 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 190 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 191 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |

**未完成片共 171 个，至少 513 层没有任何账本条目**（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。

## 二之二、max_shards 截断：本轮注定没跑的片（W33-036）

> 这不是「没采到」，是 **没派**：`max_shards=1` 把 192 片截成 1 片，573 层连 job 都没起。清单同时写在 plan 的 `shards_dropped[]`，账本 `shards_incomplete` 也会点名。要全跑请 `max_shards=0`。

| 被砍分片 | 层数 | 层 id |
|---|---|---|
| 1 | 3 | `d_Septic_System_Pilot_Project_Addresses_View_FeatureServer_0`, `arcgis_rest_services_Hartford_911_Addresses__FeatureServer_0`, `g5mTyuNWO5xx6_arcgis_rest_services_Addresses_FeatureServer_0` |
| 2 | 3 | `esses_In_Refuse_Recycle_Routes_WFL1_July2019_FeatureServer_0`, `67TISFO3iTjgFX_arcgis_rest_services_address2_FeatureServer_0`, `cgis_rest_services_Administrative_Addressing_FeatureServer_0` |
| 3 | 3 | `bK6DOd0VbR_arcgis_rest_services_SB_Addresses_FeatureServer_0`, `TjgFX_arcgis_rest_services_addresses_120222a_FeatureServer_0`, `unty__GA_Online_911_Addresses_and_Roads_WFL1_FeatureServer_1` |
| 4 | 3 | `e3_arcgis_rest_services_SiteAddresses_public_FeatureServer_0`, `CRVuK_arcgis_rest_services_Map_View_Address_FeatureServer_42`, `HKRPMgv82EjLQ_arcgis_rest_services_Addresses_FeatureServer_0` |
| 5 | 3 | `cgis_rest_services_SiteAddresses_public_2020_FeatureServer_1`, `dlWlBxzX_arcgis_rest_services_Newton_Address_FeatureServer_0`, `Iod9kh71mtnDG_arcgis_rest_services_Addresses_FeatureServer_0` |
| 6 | 3 | `387Pb3S_arcgis_rest_services_LiveAdds_202504_FeatureServer_0`, `st_services_Curb_Transition_Magic_Number2027_FeatureServer_0`, `_in_Incident_Address_and_Type_for_Date_Range_FeatureServer_0` |
| 7 | 3 | `wVADPEG6iD24f_arcgis_rest_services_Addresses_FeatureServer_0`, `ces_Stillwater_County_Addressing_Layers_2026_FeatureServer_0`, `yHixJV_arcgis_rest_services_Master_Addresses_FeatureServer_0` |
| 8 | 3 | `teAddresses_8548b2fdfac0464392b3fd7620a632d7_FeatureServer_0`, `ater_Meter_Replacement_Addresses_Zone_1_view_FeatureServer_1`, `st_services_Lincoln_City_Addresses_View_Only_FeatureServer_0` |
| 9 | 3 | `sdIpPb_arcgis_rest_services_Addresses_Splits_FeatureServer_0`, `SQHJsl5r_arcgis_rest_services_Address_Labels_FeatureServer_0`, `NuFrQ7kB_arcgis_rest_services_Master_Address_FeatureServer_0` |
| 10 | 3 | `7Y8pE5CiojuXeU_arcgis_rest_services_NewSitus_FeatureServer_0`, `M5KB8_arcgis_rest_services_E911_PairwiseClip_FeatureServer_0`, `_rest_services_E911_Houses_Washington_County_FeatureServer_0` |
| 11 | 3 | `kttgSmcq6CPonms_arcgis_rest_services_Address_FeatureServer_0`, `ieS2ld_arcgis_rest_services_Searcy_NG911_gdb_FeatureServer_2`, `_Mountlake_Terrace_Washington_Addresses_view_FeatureServer_0` |
| 12 | 3 | `rest_services_Site_Addresses_06012022_public_FeatureServer_2`, `CY2_arcgis_rest_services_Dispatcher_Map_WFL1_FeatureServer_0`, `rest_services_Pella_Address_Data_Public_View_FeatureServer_2` |
| 13 | 3 | `_ArcGIS_rest_services_AddressesE911Macon2022_FeatureServer_0`, `Z_arcgis_rest_services_CityofDemingAddresses_FeatureServer_0`, `l0FeW1NE_arcgis_rest_services_AddressesWInfo_FeatureServer_0` |
| 14 | 3 | `0hS_arcgis_rest_services_Address_Road_Update_FeatureServer_0`, `Q24dH_arcgis_rest_services_Addresses__Site__FeatureServer_13`, `rest_services_Master_Address_Management_WFL1_FeatureServer_0` |
| 15 | 3 | `ms_arcgis_rest_services_Address_Data_Public_FeatureServer_10`, `cgis_rest_services_Address_Data_Public_view_FeatureServer_10`, `ses_public_3336c922d00a441e8f588e16c3dc2577_FeatureServer_10` |
| 16 | 3 | `gg5s_arcgis_rest_services_Building_Addresses_FeatureServer_0`, `8nlIDAHxNx4_arcgis_rest_services_911_Address_FeatureServer_0`, `is_rest_services_Address_Points_Council_Area_FeatureServer_0` |
| 17 | 3 | `s_rest_services_Richland_County_ND_Addresses_FeatureServer_1`, `HRU_arcgis_rest_services_VFAC_Addresses_WFL1_FeatureServer_0`, `sses_public_e65dd46e9c084cddaedcb94aeea0ed6b_FeatureServer_0` |
| 18 | 3 | `DQNT3m6mbJlqZ_arcgis_rest_services_Addresses_FeatureServer_0`, `_services_Address_and_Street_Annotation_view_FeatureServer_0`, `s_rest_services_City_of_Dinuba_Addresses_gdb_FeatureServer_1` |
| 19 | 3 | `_arcgis_rest_services_Site_Address_Occupants_FeatureServer_0`, `1uhbqnOZPx6qT_arcgis_rest_services_Addresses_FeatureServer_0`, `es_City_Buildings_and_Address_Locations_WFL1_FeatureServer_4` |
| 20 | 3 | `resses___Archuleta_County_201411251147175537_FeatureServer_0`, `Zk1fY2MHCTEXz_arcgis_rest_services_Addresses_FeatureServer_0`, `R_arcgis_rest_services_Tornado_Addresses_NLR_FeatureServer_0` |
| 21 | 3 | `vlQFEpKtV_arcgis_rest_services_DOUGLASCOUNTY_FeatureServer_0`, `wu_arcgis_rest_services_CoStafford_Addresses_FeatureServer_0`, `PSO5BR5eOIggwRH_arcgis_rest_services_Address_FeatureServer_0` |
| 22 | 3 | `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4`, `rcgis_rest_services_OsageCoKS_NG911Addresses_FeatureServer_0`, `Pc_arcgis_rest_services_EL_RENO_911ADDRESSES_FeatureServer_0` |
| 23 | 3 | `gUZUh16VF_arcgis_rest_services_SC_Addressing_FeatureServer_0`, `VF_arcgis_rest_services_SC_Addressing_2025_7_FeatureServer_0`, `sses_public_6332b4b81c614cb4894d5de569a96465_FeatureServer_0` |
| 24 | 3 | `cyjLcCCpGk8Ri_arcgis_rest_services_Addresses_FeatureServer_0`, `BY6OUzMBTZcz_arcgis_rest_services_Addresses_FeatureServer_15`, `Sample_NCTECH_Volusia_Situs_Addresss_VRWorld_FeatureServer_0` |
| 25 | 3 | `hAmRP1z50gTbO_arcgis_rest_services_Addresses_FeatureServer_0`, `oXVtxM_arcgis_rest_services_CountyAddresses_FeatureServer_23`, `_arcgis_rest_services_Address_Pnts_ElSegundo_FeatureServer_2` |
| 26 | 3 | `QpZPT9qY_arcgis_rest_services_TOD_ADDRESS_IN_FeatureServer_0`, `st_services_Winneshiek_County_Address_Points_FeatureServer_1`, `jyn_arcgis_rest_services_Full_Street_Address_FeatureServer_0` |
| 27 | 3 | `s___Pulse_of_OC_Updated_Draft___Site_Address_FeatureServer_0`, `_server_rest_services_Aspen_AspenEditEnabled_FeatureServer_0`, `QSIEviNS_arcgis_rest_services_Addresses_2025_FeatureServer_3` |
| 28 | 3 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0`, `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6`, `p_arcgis_rest_services_Addresses_Public_View_FeatureServer_0` |
| 29 | 3 | `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0`, `tkincounty_com_arcgis_rest_services_Full_Address_MapServer_1`, `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` |
| 30 | 3 | `Qwt3_arcgis_rest_services_Address_Layer_view_FeatureServer_0`, `FjYDrl_arcgis_rest_services_Address_12102021_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address11292023_FeatureServer_0` |
| 31 | 3 | `rWTl_arcgis_rest_services_Harrison_Addresses_FeatureServer_0`, `4soU_arcgis_rest_services_Site_Addresses_gdb_FeatureServer_0`, `t_services_Perry_County_Address_Geocode_v1_1_FeatureServer_0` |
| 32 | 3 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2`, `1mtnDG_arcgis_rest_services_Worth__ADDRESSES_FeatureServer_0`, `t_services_Public_20Notification_20Addresses_FeatureServer_0` |
| 33 | 3 | `lqccxOHLu_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address02202025_FeatureServer_0`, `unty_com_arcgis_rest_services_Hosted_Address_FeatureServer_0` |
| 34 | 3 | `Us_arcgis_rest_services_OC_Site_Address_2023_FeatureServer_0`, `ILCm3hbWNTZLH_arcgis_rest_services_Addresses_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address06192026_FeatureServer_0` |
| 35 | 3 | `Kw_arcgis_rest_services_Situs_Address_Public_FeatureServer_0`, `arcgis_rest_services_BTV_e911_Address_Layers_FeatureServer_0`, `arcgis_rest_services_PAunderservedstructures_FeatureServer_0` |
| 36 | 3 | `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5`, `DdwE7LMrYrEMJ_arcgis_rest_services_Addresses_FeatureServer_1`, `JE9B_arcgis_rest_services_Newberg_Addresses__FeatureServer_0` |
| 37 | 3 | `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0`, `wlO_arcgis_rest_services_Master_Address_List_FeatureServer_0`, `XhtlWzOFCTkO_arcgis_rest_services_AddressPts_FeatureServer_0` |
| 38 | 3 | `services_BRIC_WRC_Situs_Address_LookUp_Table_FeatureServer_0`, `gis_rest_services_Municipal_Address_Points_FeatureServer_214`, `5n_arcgis_rest_services_City_Limit_Addresses_FeatureServer_0` |
| 39 | 3 | `st_services_Arlington_Addresses_current_view_FeatureServer_0`, `drG_arcgis_rest_services_Arlington_Addresses_FeatureServer_0`, `l_Assessor_parcel_Map_June_06_09_2023_WFL1_FeatureServer_219` |
| 40 | 3 | `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_FeatureServer_0`, `aAg05xQLgo7_arcgis_rest_services_SiteAddress_FeatureServer_0`, `dlWlBxzX_arcgis_rest_services_Searcy_Address_FeatureServer_0` |
| 41 | 3 | `teAddresses_176dcf6d135741fcbc3bf17da5aa7aff_FeatureServer_0`, `cgis_rest_services_Site_Addresses_View_Layer_FeatureServer_0`, `teAddresses_1a8d5e9d05674ad599c70df5dfdd4265_FeatureServer_0` |
| 42 | 3 | `m_jOKMO9vKmc98J4JC_arcgis_rest_services_E911_FeatureServer_0`, `BYQ9pcCt_arcgis_rest_services_e911_pt_txdist_FeatureServer_0`, `rcgis_rest_services_VT_Data___E911_Landmarks_FeatureServer_0` |
| 43 | 3 | `dlWlBxzX_arcgis_rest_services_Marion_Address_FeatureServer_1`, `st_services_VacantResidentialProperties_WFL1_FeatureServer_0`, `is_rest_services_Grady_Site_Addresses_Public_FeatureServer_0` |
| 44 | 3 | `MJrpz61FbvL5t_arcgis_rest_services_Addresses_FeatureServer_0`, `gis_rest_services_AddressList_Update20250311_FeatureServer_0`, `us_server_rest_services_NG911_Address_Points_FeatureServer_3` |
| 45 | 3 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3`, `aR3VIVeAhJdr_arcgis_rest_services_AddressBPs_FeatureServer_0`, `kh71mtnDG_arcgis_rest_services_E911addresses_FeatureServer_0` |
| 46 | 3 | `ELbQdlhsJLcCM_arcgis_rest_services_Addresses_FeatureServer_0`, `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0`, `rcgis_rest_services_Johns_Creek_GA_Addresses_FeatureServer_1` |
| 47 | 3 | `Ia_arcgis_rest_services_County_911_Addresses_FeatureServer_0`, `hP2NPfFE_arcgis_rest_services_Site_Addresses_FeatureServer_0`, `m7axC2dD_arcgis_rest_services_WascoAddresses_FeatureServer_5` |
| 48 | 3 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0`, `arcgis_rest_services_Short_Term_Rentals_WFL1_FeatureServer_1`, `8SWPG8KZ6r_arcgis_rest_services_911Addresses_FeatureServer_0` |
| 49 | 3 | `_arcgis_rest_services_911_Addresses_Website2_FeatureServer_0`, `sses_public_35d07adabaff4ddba616f6f365b8954e_FeatureServer_0`, `ervices_Lee_County_E911_Addresses_and_Roads_FeatureServer_20` |
| 50 | 3 | `rcgis_rest_services_Newberg_Addresses_2_view_FeatureServer_0`, `rent_Site_Addresses_and_Entrance_Points_view_FeatureServer_0`, `KPa_arcgis_rest_services_overture_address_sd_FeatureServer_0` |
| 51 | 3 | `C2HwTkBAlth_arcgis_rest_services_Address_gdb_FeatureServer_0`, `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0`, `kTU5o6Z_arcgis_rest_services_Addressing_AGOL_FeatureServer_0` |
| 52 | 3 | `X_arcgis_rest_services_County_P_Address_View_FeatureServer_0`, `jld0x0gpn_arcgis_rest_services_E911Addresses_FeatureServer_0`, `6Z_arcgis_rest_services_N911_Addresses__View_FeatureServer_0` |
| 53 | 3 | `8hGN_arcgis_rest_services_Polk_Addresses_GAC_FeatureServer_0`, `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-1`, `cgis_rest_services_AtascaderoAddresses082025_FeatureServer_0` |
| 54 | 3 | `4OueTcnj_arcgis_rest_services_just_addresses_FeatureServer_0`, `aAg05xQLgo7_arcgis_rest_services_WGS_Address_FeatureServer_0`, `gis_rest_services_GRANT_Address_ClerksOffice_FeatureServer_0` |
| 55 | 3 | `rest_services_Addresses_Clark_County_WI_2019_FeatureServer_0`, `0_arcgis_rest_services_Duncanville_Addresses_FeatureServer_0`, `0_arcgis_rest_services_2022_Sep_01_Addresses_FeatureServer_0` |
| 56 | 3 | `gis_rest_services_SANGIS_AddressAPN_07312024_FeatureServer_0`, `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0`, `So_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 57 | 3 | `ces_911_Address_Street_Review_WFL1_view_only_FeatureServer_0`, `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0`, `ces_Pueblo_County_Addresses_Evacuation_Times_FeatureServer_0` |
| 58 | 3 | `TymXTmwPsPzPHRU_arcgis_rest_services_Address_FeatureServer_0`, `is_rest_services_Master_Address_Database_MAD_FeatureServer_0`, `cjlmqkA8ypi4T_arcgis_rest_services_Addresses_FeatureServer_0` |
| 59 | 3 | `ysZUz_arcgis_rest_services_Carroll_Addresses_FeatureServer_0`, `is_rest_services_Bureau_County_911_Addresses_FeatureServer_0`, `is_rest_services_Cottage_Grove_Address_Point_FeatureServer_0` |
| 60 | 3 | `WuVPEmGK_arcgis_rest_services_Addresses_View_FeatureServer_0`, `1N7Y1EilGjehZ_arcgis_rest_services_ADDRESSES_FeatureServer_0`, `meepNh_arcgis_rest_services_Master_Addresses_FeatureServer_0` |
| 61 | 3 | `pNK5CvU_arcgis_rest_services_HempV_Addresses_FeatureServer_0`, `cgis_rest_services_Skokie_Base_Address_View_FeatureServer_33`, `YdlWlBxzX_arcgis_rest_services_Boone_Address_FeatureServer_0` |
| 62 | 3 | `kIrNAR_arcgis_rest_services_E911_Share_Files_FeatureServer_0`, `wY8_arcgis_rest_services_Address_Ranges_WFL1_FeatureServer_0`, `_rest_services_Oxford_911_Address_View_Layer_FeatureServer_1` |
| 63 | 3 | `m_x7Yxpfpio5GuQWF2_arcgis_rest_services_E911_FeatureServer_0`, `rcgis_rest_services_Mailing_Address_Map_WFL1_FeatureServer_1`, `gis_rest_services_Mailing_Address_Map___WFL1_FeatureServer_1` |
| 64 | 3 | `gis_rest_services_Mailing_Address_Map_2_WFL1_FeatureServer_1`, `_arcgis_rest_services_WyomingCountyAddresses_FeatureServer_0`, `gis_rest_services_Limestone_County_Addresses_FeatureServer_0` |
| 65 | 3 | `xkcSkFAjt_arcgis_rest_services_911_Addresses_FeatureServer_0`, `RnMdg5KWv_arcgis_rest_services_911_Addresses_FeatureServer_0`, `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` |
| 66 | 3 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0`, `is_rest_services_Gloucester_County_Addresses_FeatureServer_0`, `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` |
| 67 | 3 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0`, `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0`, `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` |
| 68 | 3 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0`, `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0`, `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` |
| 69 | 3 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0`, `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0`, `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` |
| 70 | 3 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1`, `cgis_rest_services_AddressesWithElectionData_FeatureServer_0`, `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` |
| 71 | 3 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0`, `arcgis_rest_services_Master_Address_List_New_FeatureServer_0`, `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` |
| 72 | 3 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0`, `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0`, `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` |
| 73 | 3 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0`, `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1`, `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` |
| 74 | 3 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0`, `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0`, `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` |
| 75 | 3 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0`, `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0`, `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` |
| 76 | 3 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0`, `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0`, `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` |
| 77 | 3 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0`, `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0`, `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` |
| 78 | 3 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1`, `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54`, `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` |
| 79 | 3 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0`, `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0`, `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` |
| 80 | 3 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0`, `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0`, `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` |
| 81 | 3 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0`, `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0`, `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` |
| 82 | 3 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0`, `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8`, `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` |
| 83 | 3 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1`, `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20`, `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` |
| 84 | 3 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0`, `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0`, `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` |
| 85 | 3 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76`, `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` |
| 86 | 3 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32`, `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33`, `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` |
| 87 | 3 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0`, `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0`, `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` |
| 88 | 3 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0`, `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0`, `vices_Campbell_County__VA_Broadband_Map_WFL1_FeatureServer_0` |
| 89 | 3 | `ices_City_of_Cuyahoga_Falls_Addressing_WFL1_FeatureServer_11`, `_arcgis_rest_services_TehamaCounty_NG911_gdb_FeatureServer_8`, `rest_services_Hurricane_Ian_Damage_Addresses_FeatureServer_0` |
| 90 | 3 | `est_services_Street_Sweeping_Pilot_Addresses_FeatureServer_0`, `rcgis_rest_services_Bedford_County_Addresses_FeatureServer_0`, `_arcgis_rest_services_Logan_County_Addresses_FeatureServer_0` |
| 91 | 3 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24`, `8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1`, `TOM4lipn_arcgis_rest_services_Addresses_2023_FeatureServer_0` |
| 92 | 3 | `4x6y8cTIstSBE_arcgis_rest_services_Addresses_FeatureServer_0`, `xLBcrikqFM0vkoy_arcgis_rest_services_Address_FeatureServer_0`, `Mk18pL_arcgis_rest_services_Coffee_Addresses_FeatureServer_0` |
| 93 | 3 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1`, `DgvxltnFwP_arcgis_rest_services_NG911_Layers_FeatureServer_1`, `is_rest_services_Lead_Service_Line_Addresses_FeatureServer_0` |
| 94 | 3 | `_arcgis_rest_services_EnerGov_Test_Map1_WFL1_FeatureServer_3`, `s_rest_services_Rural_Addresses__Label_Only__FeatureServer_0`, `rcgis_rest_services_Buildings_and_Addresses_FeatureServer_17` |
| 95 | 3 | `aLg_arcgis_rest_services_Address_Hemet031325_FeatureServer_0`, `ez8fHeIiDRbgb_arcgis_rest_services_Addresses_FeatureServer_0`, `arcgis_rest_services_FranklinCountyAddresses_FeatureServer_0` |
| 96 | 3 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses_FeatureServer_0`, `VDElDOMEad_arcgis_rest_services_WayneAddress_FeatureServer_0`, `rest_services_Cherokee_Address_Analysis_WFL1_FeatureServer_0` |
| 97 | 3 | `BpZX2wFbS_arcgis_rest_services_911addressing_FeatureServer_0`, `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0`, `j7VSF_arcgis_rest_services_TemeculaAddresses_FeatureServer_0` |
| 98 | 3 | `_arcgis_rest_services_zoningAddressingSearch_FeatureServer_0`, `st_services_Vector_Tile_Site_Address_Labels_FeatureServer_57`, `cgis_rest_services_Riley_County_KS_Addresses_FeatureServer_0` |
| 99 | 3 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_FeatureServer_0`, `S1a_arcgis_rest_services_Address_Mailing_Map_FeatureServer_1`, `1_arcgis_rest_services_Longview_TX_Addresses_FeatureServer_0` |
| 100 | 3 | `cgis_rest_services_Franklin_Co_911_Addresses_FeatureServer_0`, `cgis_rest_services_FranklinCoVA_911Addresses_FeatureServer_0`, `WCoI_arcgis_rest_services_20260601_Addresses_FeatureServer_0` |
| 101 | 3 | `rcgis_rest_services_Essex_Address_Pts_9_9_25_FeatureServer_0`, `cgis_rest_services_Sarpy_County_NE_Addresses_FeatureServer_1`, `kOGGtW27pGICf_arcgis_rest_services_Addresses_FeatureServer_0` |
| 102 | 3 | `cgis_rest_services_Master_Addresses_for_Grid_FeatureServer_0`, `pMfHt82xFG_arcgis_rest_services_RouteAddress_FeatureServer_0`, `1p_arcgis_rest_services_ADDRESS_20230403_CoB_FeatureServer_0` |
| 103 | 3 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2`, `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0`, `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` |
| 104 | 3 | `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0`, `arcgis_rest_services_Alexandria_VA_Addresses_FeatureServer_0`, `fMdTkPeHLCobS_arcgis_rest_services_Addresses_FeatureServer_0` |
| 105 | 3 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0`, `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13`, `PlhvQwvs_arcgis_rest_services_E911_Addrs_Pts_FeatureServer_0` |
| 106 | 3 | `rcgis_rest_services_CTSI_AddressChecker_WFL1_FeatureServer_0`, `s_rest_services_CTSI_Address_Check_2023_WFL1_FeatureServer_0`, `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_FeatureServer_0` |
| 107 | 3 | `ofS_arcgis_rest_services_Taos_E911_Addresses_FeatureServer_0`, `gT_arcgis_rest_services_USU_Addressing_view_FeatureServer_26`, `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_FeatureServer_0` |
| 108 | 3 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_FeatureServer_1`, `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0`, `zUpjDtspiBG0j_arcgis_rest_services_E911_Copy_FeatureServer_0` |
| 109 | 3 | `_arcgis_rest_services_Flagstaff_AZ_Addresses_FeatureServer_0`, `QYTTiP6CrfEsw_arcgis_rest_services_Addresses_FeatureServer_0`, `is_rest_services_Madison_County_KY_Addresses_FeatureServer_1` |
| 110 | 3 | `rest_services_CarthageWardsandaddresses_WFL1_FeatureServer_1`, `Ypus4pYH0S_arcgis_rest_services_Site_Address_FeatureServer_4`, `rcgis_rest_services_Daly_City_Addresses_AGOL_FeatureServer_2` |
| 111 | 3 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address_FeatureServer_0`, `d_Waste__Days_of_Service_Per_Address_092424_FeatureServer_52`, `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` |
| 112 | 3 | `rcgis_rest_services_Res_Address_Demographics_FeatureServer_1`, `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54`, `p_arcgis_rest_services_LAFO_ADDRESS_12_17_13_FeatureServer_0` |
| 113 | 3 | `m_nEIrIdcFpdK28ibf_arcgis_rest_services_E911_FeatureServer_1`, `u6oHu4Z_arcgis_rest_services_SITUS_PUB_CBB_2_FeatureServer_0`, `IzAwdHlO_arcgis_rest_services_Address_hosted_FeatureServer_0` |
| 114 | 3 | `1_arcgis_rest_services_Bismarck_ND_Addresses_FeatureServer_0`, `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0`, `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` |
| 115 | 3 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1`, `OU_arcgis_rest_services_Addresses_SIO_Hosted_FeatureServer_0`, `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` |
| 116 | 3 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10`, `s_rest_services_Master_Address_List_Aug_2026_FeatureServer_0`, `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` |
| 117 | 3 | `est_services_NormanResidentialTrashAddresses_FeatureServer_0`, `3kMP_arcgis_rest_services_E911AddressforSOMA_FeatureServer_0`, `s_rest_services_Raleigh_Co_EOC_Address_Sites_FeatureServer_0` |
| 118 | 3 | `s_rest_services_CityAddresses2022bu_CHE_view_FeatureServer_0`, `4Ui_arcgis_rest_services_CityAddresses2022bu_FeatureServer_0`, `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` |
| 119 | 3 | `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0`, `_arcgis_rest_services_Addresses_NOT_ELIGIBLE_FeatureServer_0`, `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` |
| 120 | 3 | `wFbS_arcgis_rest_services_Chemungaddress_pts_FeatureServer_0`, `2kwz79KUqUvxC_arcgis_rest_services_Addresses_FeatureServer_0`, `71LO_arcgis_rest_services_Addresses_CivQuest_FeatureServer_0` |
| 121 | 3 | `qTGWY_arcgis_rest_services_JoCo_Site_Address_FeatureServer_1`, `county_com_arcgis_rest_services_features_Address_MapServer_0`, `gis_rest_services_CountyAddress2023_CHE_View_FeatureServer_7` |
| 122 | 3 | `I64Ui_arcgis_rest_services_CountyAddress2023_FeatureServer_7`, `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0`, `e_Rollout__Days_of_Service_Per_Address__WFL1_FeatureServer_1` |
| 123 | 3 | `_arcgis_rest_services_BG911_Address_20250501_FeatureServer_0`, `Bq9hgug_arcgis_rest_services_BG911_Addresses_FeatureServer_0`, `Ilt_arcgis_rest_services_Clinton_Address_Pts_FeatureServer_0` |
| 124 | 3 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0`, `Geezhu2j_arcgis_rest_services_E911_Addresses_FeatureServer_0`, `KpsCnqD7H_arcgis_rest_services_SiteAddresses_FeatureServer_0` |
| 125 | 3 | `cgis_rest_services_NRSA_Address_Locator_WFL1_FeatureServer_8`, `aNxg1PvwI_arcgis_rest_services_All_Addresses_FeatureServer_0`, `eajjke_arcgis_rest_services_Addresses_Rogers_FeatureServer_0` |
| 126 | 3 | `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0`, `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0`, `sses_public_e7c532395de343e38e58a8463128cfb7_FeatureServer_0` |
| 127 | 3 | `teAddresses_ecd2ff39fbb34f39a2ec415fd784331b_FeatureServer_0`, `teAddresses_b786541565b5475593a786a08ba6b3e2_FeatureServer_0`, `sses_public_a000778ae1664a348de916831f1a0ac0_FeatureServer_0` |
| 128 | 3 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_FeatureServer_0`, `teAddresses_1809c74f027741ce815587367a5cfd68_FeatureServer_0`, `teAddresses_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` |
| 129 | 3 | `teAddresses_25f96256e2164540bc18abbff8a9d5c2_FeatureServer_0`, `sses_public_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0`, `vN_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 130 | 3 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_FeatureServer_0`, `d1DIvN_arcgis_rest_services_SiteAddresses__1_FeatureServer_1`, `sses_public_a2522c3dfde94f6da7500df892abf9aa_FeatureServer_0` |
| 131 | 3 | `sses_public_fa4be22034f14c15a3a589dd7009ca64_FeatureServer_0`, `0JE2L2xUd_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `com_arcgis_rest_services_CommunityAddressing_FeatureServer_0` |
| 132 | 3 | `st_services_A4_Landscape_addressverification_FeatureServer_1`, `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0`, `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` |
| 133 | 3 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1`, `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6`, `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` |
| 134 | 3 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0`, `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11`, `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` |
| 135 | 3 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0`, `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0`, `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` |
| 136 | 3 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0`, `d1_arcgis_rest_services_Visalia_CA_Addresses_FeatureServer_0`, `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` |
| 137 | 3 | `rcgis_rest_services_MC_Address_Pts_PMG_View1_FeatureServer_0`, `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0`, `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` |
| 138 | 3 | `arcgis_rest_services_Tompkins_County_Address_FeatureServer_0`, `vF0A_arcgis_rest_services_AddressSearchLayer_FeatureServer_0`, `AAWNInLrxvF0A_arcgis_rest_services_TCAddress_FeatureServer_0` |
| 139 | 3 | `s_rest_services_Marathon_County_WI_Addresses_FeatureServer_0`, `WNInLrxvF0A_arcgis_rest_services_Address_gdb_FeatureServer_0`, `InLrxvF0A_arcgis_rest_services_AddressR2_gdb_FeatureServer_0` |
| 140 | 3 | `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0`, `dresses_in_City_Limits___ESD9___Web_Map_WFL1_FeatureServer_1`, `5jlmVkpxP_arcgis_rest_services_Online911Data_FeatureServer_0` |
| 141 | 3 | `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0`, `AQdtmx0tv46_arcgis_rest_services_Address_Nye_FeatureServer_6`, `cgis_rest_services_Cedar_Rapids_IA_Addresses_FeatureServer_0` |
| 142 | 3 | `AQncZQEtBv_arcgis_rest_services_Address_Clip_FeatureServer_0`, `Tpwo5_arcgis_rest_services_FullAddress032026_FeatureServer_0`, `_rest_services_Randall_County_Addresses_WFL1_FeatureServer_1` |
| 143 | 3 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0`, `zOpn2_arcgis_rest_services_Streets_Buidlings_FeatureServer_0`, `arverLink_Address_Lookup_20250623_PublicView_FeatureServer_0` |
| 144 | 3 | `0gE_arcgis_rest_services_CenCom_Address_View_FeatureServer_0`, `is_rest_services_Building_Permit_Addresssing_FeatureServer_0`, `f_arcgis_rest_services_Killeen_AddressPoints_FeatureServer_0` |
| 145 | 3 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0`, `t3XQ_arcgis_rest_services_AddressPt_20230629_FeatureServer_0`, `arcgis_rest_services_AddressPt_20240705_WFL1_FeatureServer_0` |
| 146 | 3 | `rcgis_rest_services_AddressPts_20230817_WFL1_FeatureServer_0`, `U5257_arcgis_rest_services_Yonkers_Addresses_FeatureServer_0`, `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` |
| 147 | 3 | `3P_arcgis_rest_services_SiteAddresses_public_FeatureServer_0@TX-2`, `_pa_us_arcgis_rest_services_Hosted_Addresses_FeatureServer_0`, `CXd1_arcgis_rest_services_Fargo_ND_Addresses_FeatureServer_0` |
| 148 | 3 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2`, `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2`, `C0yIuqCBxq_arcgis_rest_services_Address_2024_FeatureServer_0` |
| 149 | 3 | `Cz_arcgis_rest_services_HC_MD_Addresses_10mi_FeatureServer_0`, `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0`, `_arcgis_rest_services_Addresses_USA_combined_FeatureServer_0` |
| 150 | 3 | `arcgis_rest_services_modified_JaCo_addresses_FeatureServer_0`, `wLs3iGyK80EW_arcgis_rest_services_911Address_FeatureServer_0`, `C_arcgis_rest_services_Active_Addresses_2025_FeatureServer_0` |
| 151 | 3 | `jSxUKayj_arcgis_rest_services_911_Addresses_FeatureServer_58`, `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0`, `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_FeatureServer_0` |
| 152 | 3 | `Spu5VOlu_arcgis_rest_services_Site_Addresses_FeatureServer_0`, `I64Ui_arcgis_rest_services_WLAddressAndRoads_FeatureServer_0`, `t_services_Katy_ISD_Harris_County_Addresses_FeatureServer_68` |
| 153 | 3 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1`, `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0`, `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` |
| 154 | 3 | `mxCAS_arcgis_rest_services_ClermontAddresses_FeatureServer_0`, `iJkq4oXsPh_arcgis_rest_services_Addresses_SR_FeatureServer_0`, `is_rest_services_AddressValidationTest2_WFL1_FeatureServer_0` |
| 155 | 3 | `_arcgis_rest_services_BILLING_ACCT_LOCATIONS_FeatureServer_0`, `k6RO1_arcgis_rest_services_HudsonCty_AddrPts_FeatureServer_0`, `arcgis_rest_services_Hudson_County_Addresses_FeatureServer_0` |
| 156 | 3 | `u0_arcgis_rest_services_Address_OfflineCopy_FeatureServer_21`, `ntygov_com_server_rest_services_Addresses_Public_MapServer_0`, `is_rest_services_Forsyth_County_GA_Addresses_FeatureServer_0` |
| 157 | 3 | `is_rest_services_NM911_Address_202301_SC_Web_FeatureServer_0`, `gis_rest_services_Address_For_WebApp_Locator_FeatureServer_0`, `_rest_services_NM911_Address_202401_SC_Web_a_FeatureServer_0` |
| 158 | 3 | `nQPdJ0azuLyn_arcgis_rest_services_AddressPts_FeatureServer_0`, `st_services_Springfield_address_density_WFL1_FeatureServer_2`, `VWAC8iN_arcgis_rest_services_road_centerline_FeatureServer_0` |
| 159 | 3 | `F_arcgis_rest_services_NM911_Address_10_2024_FeatureServer_0`, `F_arcgis_rest_services_NM911_Address_02_2025_FeatureServer_0`, `arcgis_rest_services_NM911_Address_202506_SC_FeatureServer_0` |
| 160 | 3 | `wbCJ2GMP_arcgis_rest_services_E911calls_2020_FeatureServer_0`, `s_rest_services_NM911_Address_01_2026_SC_Web_FeatureServer_0`, `r_arcgis_rest_services_Coryell_address_5Mile_FeatureServer_0` |
| 161 | 3 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0`, `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0`, `tg2A1_arcgis_rest_services_vw_dist_addresses_FeatureServer_0` |
| 162 | 3 | `cgis_rest_services_Delaware_County_E911_Data_FeatureServer_0`, `GEllMqef1LMjj_arcgis_rest_services_Addresses_FeatureServer_0`, `vices_Yuma_911_Data_Roads_and_Addresses_WFL1_FeatureServer_0` |
| 163 | 3 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0`, `V5FXPLX_arcgis_rest_services_Addresses_Units_FeatureServer_0`, `McTk2tV5FXPLX_arcgis_rest_services_Addresses_FeatureServer_0` |
| 164 | 3 | `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0`, `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0`, `GOi6N4Rq5cqFv_arcgis_rest_services_Addresses_FeatureServer_0` |
| 165 | 3 | `rvices_Situs_for_ConsolidatedPrecincts_AGOL_FeatureServer_51`, `4427d57d2827830_rest_services_Base_Addresses_FeatureServer_0`, `CRg_arcgis_rest_services_SBCnty_Address_Grid_FeatureServer_0` |
| 166 | 3 | `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0`, `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0`, `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` |
| 167 | 3 | `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0`, `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0`, `rvices_WCAddresses20251003_gdb_view_Geocivix_FeatureServer_0` |
| 168 | 3 | `is_rest_services_Addresses_2015_Boston_BARI__FeatureServer_0`, `ervices_64a951f0_b017_11e6_b4e3_22000b8406af_FeatureServer_0`, `est_services_Collier_Addresses_Within_3_Mile_FeatureServer_0` |
| 169 | 3 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0`, `8JRPoNeQjgcLi_arcgis_rest_services_Addresses_FeatureServer_0`, `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` |
| 170 | 3 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0`, `_services_Infrastructure_Transportation_Sheriffs_MapServer_0`, `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` |
| 171 | 3 | `_arcgis_rest_services_city_address_march2025_FeatureServer_0`, `_rest_services_HenricoCountyGIS_05082023_gdb_FeatureServer_0`, `cgis_rest_services_Indianapolis_IN_Addresses_FeatureServer_0` |
| 172 | 3 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_FeatureServer_2`, `LmYGD_arcgis_rest_services_DC_Addresses_WFL1_FeatureServer_0`, `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` |
| 173 | 3 | `is_rest_services_Barry_County_E911_Map_WFL1_FeatureServer_29`, `rvices_stratmap19_addresspoints_48027_vector_FeatureServer_0`, `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` |
| 174 | 3 | `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0`, `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0`, `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` |
| 175 | 3 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0`, `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0`, `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` |
| 176 | 3 | `arcgis_rest_services_Addresses_Arcade_Labels_FeatureServer_0`, `QGwSSLC0l_arcgis_rest_services_t07_Addresses_FeatureServer_0`, `j7_arcgis_rest_services_Addresses_GeneralUse_FeatureServer_0` |
| 177 | 3 | `s_rest_services_Solano_County_Addresses_WFL1_FeatureServer_0`, `_rest_services_Site_Addresses_FLOCK_10302024_FeatureServer_0`, `_services_Rutherford_Site_Addresses_11012024_FeatureServer_0` |
| 178 | 3 | `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0`, `rest_services_E911_Addresses_Hamilton_County_FeatureServer_0`, `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` |
| 179 | 3 | `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0`, `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0`, `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` |
| 180 | 3 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2`, `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0`, `ervices_AddressPts_DamageAssessment_REA_VIEW_FeatureServer_0` |
| 181 | 3 | `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0`, `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1`, `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` |
| 182 | 3 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0`, `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0`, `i_arcgis_rest_services_Ada_County_Addresses_FeatureServer_13` |
| 183 | 3 | `services_Zanna_E911_Sites_Within_8min_Buffer_FeatureServer_1`, `services_CountyServices_Municipal_Addressing_FeatureServer_2`, `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` |
| 184 | 3 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0`, `is_rest_services_Chester_County_PA_Addresses_FeatureServer_0`, `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` |
| 185 | 3 | `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0`, `ZHFr6zdgNZuVG0_arcgis_rest_services_Address2_FeatureServer_3`, `arcgis_rest_services_Jeffco_Address_Map_WFL1_FeatureServer_1` |
| 186 | 3 | `MCHD_Environmental_Health_Public_Service_Map_FeatureServer_0`, `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0`, `27_Great_Mississippi_Flood_in_Arkansas_WFL1_FeatureServer_14` |
| 187 | 3 | `_services_Lower_MS_Sediment_Bottleneck_WFL1_FeatureServer_14`, `_Mississippi_Flood_in_Arkansas__Final__WFL1_FeatureServer_14`, `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` |
| 188 | 3 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12`, `xLqeJd2jOX_arcgis_rest_services_VC_Addresses_FeatureServer_0`, `oN_arcgis_rest_services_WASD_Addresses_3_23_FeatureServer_52` |
| 189 | 3 | `0yIuqCBxq_arcgis_rest_services_CNO_Addresses_FeatureServer_0`, `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3`, `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` |
| 190 | 3 | `is_rest_services_Address_1424300337393713068_FeatureServer_0`, `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0`, `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` |
| 191 | 3 | `_rest_services_Arapahoe_County_Addresses_gdb_FeatureServer_0`, `hedVoters_Statewide_withSiteTypeDescription_FeatureServer_32`, `jvohPcWJU5ij6_arcgis_rest_services_Addresses_FeatureServer_0` |

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 209,203 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,277 | 0 | 207,277 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,277 | 0 | 207,277 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 187,871 | 4,000 | 183,871 | failed | rc=1 err=query_fail:http500:
<!DOCTYPE html>
<html>
<head id="Head1">
    <link  |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 125,867 | failed | rc=1 err=? |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 2,000 | 98,314 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Inval |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,362 | 0 | 93,362 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 56,800 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 50,911 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 50,423 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0` | partial | 278192 | 555706 | 缺口 -99.76%（实采 555706 / 声明 278192） |
| `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` | partial | 277958 | 555729 | 缺口 -99.93%（实采 555729 / 声明 277958） |
| `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3` | partial | 268407 | 536539 | 缺口 -99.90%（实采 536539 / 声明 268407） |
| `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | partial | 268229 | 536539 | 缺口 -100.03%（实采 536539 / 声明 268229） |
| `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | partial | 227847 | 455698 | 缺口 -100.00%（实采 455698 / 声明 227847） |
| `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | partial | 224311 | 448628 | 缺口 -100.00%（实采 448628 / 声明 224311） |
| `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | partial | 219960 | 439750 | 缺口 -99.92%（实采 439750 / 声明 219960） |
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | failed | 209203 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | failed | 207277 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | failed | 207277 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | partial | 192634 | 385198 | 缺口 -99.96%（实采 385198 / 声明 192634） |
| `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | partial | 190252 | 380483 | 缺口 -99.99%（实采 380483 / 声明 190252） |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | failed | 187871 | 4000 | rc=1 err=query_fail:http500:
<!DOCTYPE html>
<html>
<head id="Head1">
    <link rel="stylesheet" href="/arcgis/css/webad |
| `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | partial | 183836 | 367080 | 缺口 -99.68%（实采 367080 / 声明 183836） |
| `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | partial | 182659 | 365117 | 缺口 -99.89%（实采 365117 / 声明 182659） |
| `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0` | partial | 181440 | 362701 | 缺口 -99.90%（实采 362701 / 声明 181440） |
| `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | partial | 179493 | 358962 | 缺口 -99.99%（实采 358962 / 声明 179493） |
| `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0` | partial | 173381 | 346745 | 缺口 -99.99%（实采 346745 / 声明 173381） |
| `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 158719 | 317114 | 缺口 -99.80%（实采 317114 / 声明 158719） |
| `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | partial | 158408 | 316405 | 缺口 -99.74%（实采 316405 / 声明 158408） |
| `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0` | partial | 156027 | 312042 | 缺口 -99.99%（实采 312042 / 声明 156027） |
| `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | partial | 155653 | 310782 | 缺口 -99.66%（实采 310782 / 声明 155653） |
| `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | partial | 147918 | 295706 | 缺口 -99.91%（实采 295706 / 声明 147918） |
| `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` | partial | 130132 | 260301 | 缺口 -100.03%（实采 260301 / 声明 130132） |
| `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | partial | 130102 | 259861 | 缺口 -99.74%（实采 259861 / 声明 130102） |
| `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | partial | 130102 | 259861 | 缺口 -99.74%（实采 259861 / 声明 130102） |
| `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` | partial | 129693 | 259369 | 缺口 -99.99%（实采 259369 / 声明 129693） |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | failed | 125867 | 0 | rc=1 err=? |
| `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0` | partial | 118128 | 235365 | 缺口 -99.25%（实采 235365 / 声明 118128） |
| `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 114869 | 229458 | 缺口 -99.76%（实采 229458 / 声明 114869） |
| `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0` | partial | 114589 | 229361 | 缺口 -100.16%（实采 229361 / 声明 114589） |
| `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0` | partial | 111350 | 222652 | 缺口 -99.96%（实采 222652 / 声明 111350） |
| `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0` | partial | 110991 | 221935 | 缺口 -99.96%（实采 221935 / 声明 110991） |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | failed | 100314 | 2000 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | failed | 93362 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | partial | 87697 | 174890 | 缺口 -99.43%（实采 174890 / 声明 87697） |
| `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | partial | 84306 | 168433 | 缺口 -99.79%（实采 168433 / 声明 84306） |
| `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 82602 | 165191 | 缺口 -99.98%（实采 165191 / 声明 82602） |
| `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | partial | 72868 | 145729 | 缺口 -99.99%（实采 145729 / 声明 72868） |
| `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | partial | 72868 | 145729 | 缺口 -99.99%（实采 145729 / 声明 72868） |
| `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` | partial | 71260 | 142442 | 缺口 -99.89%（实采 142442 / 声明 71260） |
| `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0` | partial | 64989 | 129960 | 缺口 -99.97%（实采 129960 / 声明 64989） |
| `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0` | partial | 63212 | 126366 | 缺口 -99.91%（实采 126366 / 声明 63212） |
| `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 62581 | 125156 | 缺口 -99.99%（实采 125156 / 声明 62581） |
| `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 59831 | 119500 | 缺口 -99.73%（实采 119500 / 声明 59831） |
| `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0` | partial | 58760 | 117274 | 缺口 -99.58%（实采 117274 / 声明 58760） |
| `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` | partial | 58034 | 116044 | 缺口 -99.96%（实采 116044 / 声明 58034） |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | failed | 56888 | 88 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | partial | 56599 | 113267 | 缺口 -100.12%（实采 113267 / 声明 56599） |
| `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | partial | 54644 | 109268 | 缺口 -99.96%（实采 109268 / 声明 54644） |
| `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | partial | 51423 | 102815 | 缺口 -99.94%（实采 102815 / 声明 51423） |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | failed | 50911 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | failed | 50423 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | failed | 49374 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0` | partial | 49100 | 98176 | 缺口 -99.95%（实采 98176 / 声明 49100） |
| `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` | partial | 43499 | 86993 | 缺口 -99.99%（实采 86993 / 声明 43499） |
| `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0` | partial | 43405 | 86789 | 缺口 -99.95%（实采 86789 / 声明 43405） |
| `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | partial | 43042 | 86008 | 缺口 -99.82%（实采 86008 / 声明 43042） |
| `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | partial | 41018 | 82028 | 缺口 -99.98%（实采 82028 / 声明 41018） |
| `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | failed | 40689 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | partial | 40586 | 81170 | 缺口 -100.00%（实采 81170 / 声明 40586） |
| `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | failed | 39743 | 39503 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` | partial | 38656 | 77304 | 缺口 -99.98%（实采 77304 / 声明 38656） |
| `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 36725 | 73441 | 缺口 -99.98%（实采 73441 / 声明 36725） |
| `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | partial | 35212 | 70424 | 缺口 -100.00%（实采 70424 / 声明 35212） |
| `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` | partial | 34929 | 69851 | 缺口 -99.98%（实采 69851 / 声明 34929） |
| `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0` | partial | 34929 | 69851 | 缺口 -99.98%（实采 69851 / 声明 34929） |
| `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0` | partial | 34840 | 69679 | 缺口 -100.00%（实采 69679 / 声明 34840） |
| `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0` | partial | 32353 | 64689 | 缺口 -99.95%（实采 64689 / 声明 32353） |
| `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | partial | 26320 | 52635 | 缺口 -99.98%（实采 52635 / 声明 26320） |
| `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | failed | 25834 | 51610 | rc=1 err=short:25776/25834 |
| `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | partial | 25817 | 51608 | 缺口 -99.90%（实采 51608 / 声明 25817） |
| `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | partial | 25091 | 50069 | 缺口 -99.55%（实采 50069 / 声明 25091） |
| `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | partial | 23869 | 47732 | 缺口 -99.97%（实采 47732 / 声明 23869） |
| `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | partial | 23819 | 47237 | 缺口 -98.32%（实采 47237 / 声明 23819） |
| `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | partial | 23776 | 47553 | 缺口 -100.00%（实采 47553 / 声明 23776） |
| `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 23338 | 46672 | 缺口 -99.98%（实采 46672 / 声明 23338） |
| `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | failed | 23246 | 20570 | rc=1 err=? |
| `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | failed | 23241 | 20567 | rc=1 err=? |
| `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | partial | 22248 | 44495 | 缺口 -100.00%（实采 44495 / 声明 22248） |
| `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | partial | 21770 | 43524 | 缺口 -99.93%（实采 43524 / 声明 21770） |
| `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | partial | 20040 | 40080 | 缺口 -100.00%（实采 40080 / 声明 20040） |
| `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | partial | 19161 | 38284 | 缺口 -99.80%（实采 38284 / 声明 19161） |
| `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | partial | 18526 | 37031 | 缺口 -99.89%（实采 37031 / 声明 18526） |
| `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | failed | 17295 | 17270 | rc=1 err=short:17270/17295 |
| `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | failed | 16730 | 0 | rc=1 err=batch0:http404: <div style="border: 3px solid #4991C5; font:1.5em; font-family:tahoma,calibri,arial; font-weigh |
| `84Po4FBDs_arcgis_rest_services_Address_Point_FeatureServer_0` | partial | 14616 | 26616 | 缺口 -82.10%（实采 26616 / 声明 14616） |
| `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | failed | 14470 | 6616 | rc=1 err=? |
| `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | failed | 10564 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0` | partial | 5045 | 10085 | 覆盖率 100.00%（实采 10,085 / 声明 5,045）；实采超出声明 5,040 行（99.90%）→ 查重复/双算，不是缺口 |
| `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | failed | None | 0 | rc=3 err=? |
| `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `county_com_arcgis_rest_services_features_Address_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | failed | None | 0 | rc=3 err=? |
| `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |

## 五、逐层台账（按声明行数降序）

| # | 层 | 声明 | 实采 | 差额% | 状态 |
|---|---|---|---|---|---|
| 1 | `g_arcgis_rest_services_DataDownloads_Address_FeatureServer_0` | 299,739 | 299,739 | 0.00% | ok |
| 2 | `x_arcgis_rest_services_Site_Address_Points_b_FeatureServer_3` | 298,012 | 298,012 | 0.00% | ok |
| 3 | `tymd_gov_arcgis_rest_services_Facilities_Address_MapServer_0` | 296,736 | 296,736 | 0.00% | ok |
| 4 | `ountymd_gov_arcgis_rest_services_General_BAR_FeatureServer_0` | 294,680 | 294,680 | 0.00% | ok |
| 5 | `erycountymd_gov_arcgis_rest_services_General_BAR_MapServer_0` | 294,680 | 294,680 | 0.00% | ok |
| 6 | `s_rest_services_SiteAddressPointsPinalCounty_FeatureServer_0` | 292,716 | 292,716 | 0.00% | ok |
| 7 | `OB2_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 291,751 | 291,751 | 0.00% | ok |
| 8 | `cgis_rest_services_Active_Addresses__MAF_NEW_FeatureServer_0` | 291,344 | 291,344 | 0.00% | ok |
| 9 | `hoegov_com_arcgis_rest_services_Address_Verifier_MapServer_0` | 290,831 | 290,831 | 0.00% | ok |
| 10 | `rvices_Assessor_Data_Caddo_Parish_Address_Points_MapServer_0` | 290,095 | 290,095 | 0.00% | ok |
| 11 | `n_arcgis_rest_services_CoGC_Property_Address_FeatureServer_0` | 289,207 | 289,207 | 0.00% | ok |
| 12 | `jvohPcWJU5ij6_arcgis_rest_services_Addresses_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 13 | `IABSMeJD_arcgis_rest_services_address_points_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 14 | `_arcgis_rest_services_Ventura_Address_Points_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 15 | `arcgis_rest_services_VNC_MasterAddressPoints_FeatureServer_0` | 285,257 | 285,257 | 0.00% | ok |
| 16 | `hedVoters_Statewide_withSiteTypeDescription_FeatureServer_32` | 283,974 | 283,974 | 0.00% | ok |
| 17 | `n1c_arcgis_rest_services_Address_Points_2026_FeatureServer_0` | 283,921 | 283,921 | 0.00% | ok |
| 18 | `rcgis_rest_services_Address_Points_SHAPE_UTM_FeatureServer_0` | 282,952 | 282,952 | 0.00% | ok |
| 19 | `t_services_Montgomery_County_Address_Points_FeatureServer_14` | 282,669 | 282,669 | 0.00% | ok |
| 20 | `vices_Planning_COGCC_LC_Oil_Gas_Wells_Published_MapServer_77` | 281,510 | 281,510 | 0.00% | ok |
| 21 | `_rest_services_Arapahoe_County_Addresses_gdb_FeatureServer_0` | 281,486 | 281,486 | 0.00% | ok |
| 22 | `gVyYKfYgW5Nxb1V_arcgis_rest_services_Address_FeatureServer_0` | 281,361 | 281,361 | 0.00% | ok |
| 23 | `Xx_arcgis_rest_services_Address_Point_Native_FeatureServer_0` | 279,406 | 279,406 | 0.00% | ok |
| 24 | `ices_Address_Points_Site_AddressPoints_NG911_FeatureServer_0` | 279,299 | 279,299 | 0.00% | ok |
| 25 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-1` | 279,299 | 279,299 | 0.00% | ok |
| 26 | `tN2gn8MMx1p_arcgis_rest_services_ADDRESS_pts_FeatureServer_0` | 279,000 | 279,000 | 0.00% | ok |
| 27 | `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0` | 278,192 | 555,706 | -99.76% | partial |
| 28 | `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` | 277,958 | 555,729 | -99.93% | partial |
| 29 | `rcgis_rest_services_OpenData_Structure_OpenData_MapServer_12` | 277,815 | 277,815 | 0.00% | ok |
| 30 | `is_rest_services_Waste_Collection_by_Address_FeatureServer_0` | 277,731 | 277,731 | 0.00% | ok |
| 31 | `_gov_dev_rest_services_Planning_AddressPoint_FeatureServer_0` | 276,955 | 276,955 | 0.00% | ok |
| 32 | `XBIeLonX0V_arcgis_rest_services_AddressPoint_FeatureServer_0` | 276,594 | 276,594 | 0.00% | ok |
| 33 | `H5m5JyP_arcgis_rest_services_Address_Points_FeatureServer_21` | 275,376 | 275,376 | 0.00% | ok |
| 34 | `lN_arcgis_rest_services_Ada_County_Addresses_FeatureServer_0` | 275,375 | 275,375 | 0.00% | ok |
| 35 | `782eMbySr2srL_arcgis_rest_services_Addresses_FeatureServer_1` | 274,737 | 274,737 | 0.00% | ok |
| 36 | `is_rest_services_Address_1424300337393713068_FeatureServer_0` | 274,644 | 274,644 | 0.00% | ok |
| 37 | `gd_arcgis_rest_services_NHCRWA_AddressPoints_FeatureServer_0` | 269,633 | 269,633 | 0.00% | ok |
| 38 | `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3` | 268,407 | 536,539 | -99.90% | partial |
| 39 | `or_us_server_rest_services_baselayers_Taxlots_SP_MapServer_1` | 268,271 | 268,271 | 0.00% | ok |
| 40 | `us_server_rest_services_Open_Data_Open_Data_AGOL_MapServer_0` | 268,271 | 268,271 | 0.00% | ok |
| 41 | `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` | 268,229 | 536,539 | -100.03% | partial |
| 42 | `Lhk48K7A_arcgis_rest_services_Address_Labels_FeatureServer_0` | 268,122 | 268,122 | 0.00% | ok |
| 43 | `0yIuqCBxq_arcgis_rest_services_CNO_Addresses_FeatureServer_0` | 267,730 | 267,730 | 0.00% | ok |
| 44 | `vYeDEj7_arcgis_rest_services_zs_sub_poc_bytu_FeatureServer_0` | 267,620 | 267,620 | 0.00% | ok |
| 45 | `cX_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | 264,791 | 264,791 | 0.00% | ok |
| 46 | `oN_arcgis_rest_services_WASD_Addresses_3_23_FeatureServer_52` | 264,398 | 264,398 | 0.00% | ok |
| 47 | `rcgis_rest_services_AddressPoints_20220127v4_FeatureServer_0` | 264,259 | 264,259 | 0.00% | ok |
| 48 | `xLqeJd2jOX_arcgis_rest_services_VC_Addresses_FeatureServer_0` | 263,947 | 263,947 | 0.00% | ok |
| 49 | `st_services_WR_Address_Points_September_2025_FeatureServer_0` | 263,704 | 263,704 | 0.00% | ok |
| 50 | `gis_rest_services_PSAP_Address_Points_Hosted_FeatureServer_0` | 263,523 | 263,523 | 0.00% | ok |
| 51 | `id_arcgis_rest_services_RBI_18_RBI_25_50_250_wms_MapServer_0` | 263,144 | 263,144 | 0.00% | ok |
| 52 | `FVZ_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 260,237 | 260,237 | 0.00% | ok |
| 53 | `vices_LojicSolutions_OpenDataHistoricAddressing_MapServer_22` | 260,087 | 260,087 | 0.00% | ok |
| 54 | `_hosted_rest_services_Address_Address_Points_FeatureServer_0` | 258,903 | 258,903 | 0.00% | ok |
| 55 | `h_net_hosted_rest_services_AddressPoints_DBC_FeatureServer_0` | 258,903 | 258,903 | 0.00% | ok |
| 56 | `27_Great_Mississippi_Flood_in_Arkansas_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 57 | `_services_Lower_MS_Sediment_Bottleneck_WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 58 | `_Mississippi_Flood_in_Arkansas__Final__WFL1_FeatureServer_14` | 230,816 | 230,816 | 0.00% | ok |
| 59 | `_org_ArcGIS_rest_services_APPS_OperationalLayers_MapServer_8` | 230,438 | 230,438 | 0.00% | ok |
| 60 | `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0` | 227,847 | 455,698 | -100.00% | partial |
| 61 | `MCHD_Environmental_Health_Public_Service_Map_FeatureServer_0` | 226,508 | 226,508 | 0.00% | ok |
| 62 | `ZHFr6zdgNZuVG0_arcgis_rest_services_Address2_FeatureServer_3` | 226,170 | 226,170 | 0.00% | ok |
| 63 | `arcgis_rest_services_Jeffco_Address_Map_WFL1_FeatureServer_1` | 226,170 | 226,170 | 0.00% | ok |
| 64 | `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0` | 224,311 | 448,628 | -100.00% | partial |
| 65 | `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` | 221,905 | 221,905 | 0.00% | ok |
| 66 | `is_rest_services_Chester_County_PA_Addresses_FeatureServer_0` | 221,873 | 221,873 | 0.00% | ok |
| 67 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0` | 219,960 | 439,750 | -99.92% | partial |
| 68 | `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,203 | 0 | 100.00% | failed |
| 69 | `services_CountyServices_Municipal_Addressing_FeatureServer_2` | 207,685 | 207,685 | 0.00% | ok |
| 70 | `services_Zanna_E911_Sites_Within_8min_Buffer_FeatureServer_1` | 207,581 | 207,581 | 0.00% | ok |
| 71 | `i_arcgis_rest_services_Ada_County_Addresses_FeatureServer_13` | 207,396 | 207,396 | 0.00% | ok |
| 72 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,277 | 0 | 100.00% | failed |
| 73 | `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,277 | 0 | 100.00% | failed |
| 74 | `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1` | 204,910 | 204,910 | 0.00% | ok |
| 75 | `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` | 204,910 | 204,910 | 0.00% | ok |
| 76 | `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0` | 192,634 | 385,198 | -99.96% | partial |
| 77 | `ervices_AddressPts_DamageAssessment_REA_VIEW_FeatureServer_0` | 190,765 | 190,765 | 0.00% | ok |
| 78 | `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0` | 190,252 | 380,483 | -99.99% | partial |
| 79 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | 187,871 | 4,000 | 97.87% | failed |
| 80 | `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` | 183,836 | 367,080 | -99.68% | partial |
| 81 | `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0` | 182,659 | 365,117 | -99.89% | partial |
| 82 | `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0` | 181,440 | 362,701 | -99.90% | partial |
| 83 | `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` | 179,493 | 358,962 | -99.99% | partial |
| 84 | `rest_services_E911_Addresses_Hamilton_County_FeatureServer_0` | 173,477 | 173,477 | 0.00% | ok |
| 85 | `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0` | 173,381 | 346,745 | -99.99% | partial |
| 86 | `_rest_services_Site_Addresses_FLOCK_10302024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 87 | `_services_Rutherford_Site_Addresses_11012024_FeatureServer_0` | 172,313 | 172,313 | 0.00% | ok |
| 88 | `s_rest_services_Solano_County_Addresses_WFL1_FeatureServer_0` | 171,954 | 171,954 | 0.00% | ok |
| 89 | `j7_arcgis_rest_services_Addresses_GeneralUse_FeatureServer_0` | 169,896 | 169,896 | 0.00% | ok |
| 90 | `QGwSSLC0l_arcgis_rest_services_t07_Addresses_FeatureServer_0` | 168,093 | 168,093 | 0.00% | ok |
| 91 | `ices_Corporate_Address_Gazetteer_Punlic_View_FeatureServer_1` | 166,242 | 166,242 | 0.00% | ok |
| 92 | `arcgis_rest_services_Addresses_Arcade_Labels_FeatureServer_0` | 161,806 | 161,806 | 0.00% | ok |
| 93 | `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` | 158,719 | 317,114 | -99.80% | partial |
| 94 | `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0` | 158,408 | 316,405 | -99.74% | partial |
| 95 | `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 96 | `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 97 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0` | 157,891 | 157,891 | 0.00% | ok |
| 98 | `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0` | 156,027 | 312,042 | -99.99% | partial |
| 99 | `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` | 155,653 | 310,782 | -99.66% | partial |
| 100 | `rvices_stratmap19_addresspoints_48027_vector_FeatureServer_0` | 150,676 | 150,676 | 0.00% | ok |
| 101 | `is_rest_services_Barry_County_E911_Map_WFL1_FeatureServer_29` | 147,967 | 147,967 | 0.00% | ok |
| 102 | `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` | 147,918 | 295,706 | -99.91% | partial |
| 103 | `LmYGD_arcgis_rest_services_DC_Addresses_WFL1_FeatureServer_0` | 144,111 | 144,111 | 0.00% | ok |
| 104 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_FeatureServer_2` | 139,097 | 139,097 | 0.00% | ok |
| 105 | `cgis_rest_services_Indianapolis_IN_Addresses_FeatureServer_0` | 138,941 | 138,941 | 0.00% | ok |
| 106 | `_rest_services_HenricoCountyGIS_05082023_gdb_FeatureServer_0` | 134,041 | 134,041 | 0.00% | ok |
| 107 | `_arcgis_rest_services_city_address_march2025_FeatureServer_0` | 130,386 | 130,386 | 0.00% | ok |
| 108 | `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` | 130,132 | 260,301 | -100.03% | partial |
| 109 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 110 | `_services_Infrastructure_Transportation_Sheriffs_MapServer_0` | 130,102 | 259,861 | -99.74% | partial |
| 111 | `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` | 129,693 | 259,369 | -99.99% | partial |
| 112 | `8JRPoNeQjgcLi_arcgis_rest_services_Addresses_FeatureServer_0` | 128,917 | 128,917 | 0.00% | ok |
| 113 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,867 | 0 | 100.00% | failed |
| 114 | `est_services_Collier_Addresses_Within_3_Mile_FeatureServer_0` | 121,820 | 121,820 | 0.00% | ok |
| 115 | `is_rest_services_Addresses_2015_Boston_BARI__FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 116 | `ervices_64a951f0_b017_11e6_b4e3_22000b8406af_FeatureServer_0` | 118,918 | 118,918 | 0.00% | ok |
| 117 | `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0` | 118,128 | 235,365 | -99.25% | partial |
| 118 | `rvices_WCAddresses20251003_gdb_view_Geocivix_FeatureServer_0` | 118,119 | 118,119 | 0.00% | ok |
| 119 | `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 120 | `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 121 | `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` | 114,869 | 229,458 | -99.76% | partial |
| 122 | `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0` | 114,589 | 229,361 | -100.16% | partial |
| 123 | `CRg_arcgis_rest_services_SBCnty_Address_Grid_FeatureServer_0` | 114,312 | 114,312 | 0.00% | ok |
| 124 | `4427d57d2827830_rest_services_Base_Addresses_FeatureServer_0` | 113,649 | 113,649 | 0.00% | ok |
| 125 | `rvices_Situs_for_ConsolidatedPrecincts_AGOL_FeatureServer_51` | 112,728 | 112,728 | 0.00% | ok |
| 126 | `GOi6N4Rq5cqFv_arcgis_rest_services_Addresses_FeatureServer_0` | 112,607 | 112,607 | 0.00% | ok |
| 127 | `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0` | 111,350 | 222,652 | -99.96% | partial |
| 128 | `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0` | 110,991 | 221,935 | -99.96% | partial |
| 129 | `McTk2tV5FXPLX_arcgis_rest_services_Addresses_FeatureServer_0` | 110,848 | 110,848 | 0.00% | ok |
| 130 | `V5FXPLX_arcgis_rest_services_Addresses_Units_FeatureServer_0` | 110,120 | 110,120 | 0.00% | ok |
| 131 | `_com_gis_rest_services_Public_Site_Addresses_FeatureServer_2` | 109,378 | 109,378 | 0.00% | ok |
| 132 | `unty_us_arcgis_rest_services_maps_Open_Data_FeatureServer_52` | 109,140 | 109,140 | 0.00% | ok |
| 133 | `fy5ay_arcgis_rest_services_propertyaddresses_FeatureServer_0` | 109,006 | 109,006 | 0.00% | ok |
| 134 | `rest_services_WEB_PUBLICATIONS_County_Map_Layers_MapServer_6@未定位-1` | 108,946 | 108,946 | 0.00% | ok |
| 135 | `rest_services_WEB_PUBLICATIONS_County_Map_Layers_MapServer_6@未定位-2` | 108,946 | 108,946 | 0.00% | ok |
| 136 | `rateReferenceLayers_CorporateReferenceLayers_FeatureServer_3` | 108,683 | 108,683 | 0.00% | ok |
| 137 | `vices_Yuma_911_Data_Roads_and_Addresses_WFL1_FeatureServer_0` | 108,514 | 108,514 | 0.00% | ok |
| 138 | `_washco_utah_gov_arcgis_rest_services_Addressing_MapServer_0` | 108,238 | 108,238 | 0.00% | ok |
| 139 | `is_rest_services_Chula_Vista_Address_Points_FeatureServer_13` | 107,770 | 107,770 | 0.00% | ok |
| 140 | `9q8g_arcgis_rest_services_Address_Point_File_FeatureServer_0` | 107,685 | 107,685 | 0.00% | ok |
| 141 | `s_rest_services_Address_Points_by_SWDD_CLASS_FeatureServer_0` | 107,344 | 107,344 | 0.00% | ok |
| 142 | `_gov_server2_rest_services_GeneralUse_Open_Data_MapServer_17` | 107,068 | 107,068 | 0.00% | ok |
| 143 | `xaar_arcgis_rest_services_Site_Address___911_FeatureServer_0` | 106,941 | 106,941 | 0.00% | ok |
| 144 | `4zdJEFmiY_arcgis_rest_services_Address_Point_FeatureServer_0` | 106,694 | 106,694 | 0.00% | ok |
| 145 | `rest_services_Address_Points_St_Louis_County_FeatureServer_0` | 106,680 | 106,680 | 0.00% | ok |
| 146 | `GEllMqef1LMjj_arcgis_rest_services_Addresses_FeatureServer_0` | 106,530 | 106,530 | 0.00% | ok |
| 147 | `gis_rest_services_AddressVerification_Points_FeatureServer_0` | 106,518 | 106,518 | 0.00% | ok |
| 148 | `for_Countywide_FeeParcel_Evaluation_Analysis_FeatureServer_1` | 106,083 | 106,083 | 0.00% | ok |
| 149 | `DyZ77wYt_arcgis_rest_services_Address_Point1_FeatureServer_0` | 105,564 | 105,564 | 0.00% | ok |
| 150 | `is_rest_services_AddressVerification_PROTest_FeatureServer_0` | 105,563 | 105,563 | 0.00% | ok |
| 151 | `ervices_AGO_HarrisonCounty_PhysicalAddresses_FeatureServer_0` | 105,474 | 105,474 | 0.00% | ok |
| 152 | `_data_DATA_LOADER_SiteStructureAddressPoints_FeatureServer_0` | 105,437 | 105,437 | 0.00% | ok |
| 153 | `Z77wYt_arcgis_rest_services_Address_Point_DC_FeatureServer_0` | 105,198 | 105,198 | 0.00% | ok |
| 154 | `es_EnterprisePublishing_WhatcomCo_Administrative_MapServer_4` | 104,607 | 104,607 | 0.00% | ok |
| 155 | `IeLonX0V_arcgis_rest_services_AddressPointCC_FeatureServer_0` | 104,135 | 104,135 | 0.00% | ok |
| 156 | `n9vNc_arcgis_rest_services_RealEstateAddress_FeatureServer_0` | 104,108 | 104,108 | 0.00% | ok |
| 157 | `com_server_rest_services_Site_Address_Points_FeatureServer_0` | 104,075 | 104,075 | 0.00% | ok |
| 158 | `_arcgis_rest_services_LB_Site_Address_Points_FeatureServer_0` | 103,980 | 103,980 | 0.00% | ok |
| 159 | `ervices_E911_Addresses_Active_Address_Points_FeatureServer_0` | 103,938 | 103,938 | 0.00% | ok |
| 160 | `gis_rest_services_Address_Points_Nov_17_2025_FeatureServer_0` | 103,723 | 103,723 | 0.00% | ok |
| 161 | `cgis_rest_services_Delaware_County_E911_Data_FeatureServer_0` | 103,591 | 103,591 | 0.00% | ok |
| 162 | `1yz8_arcgis_rest_services_LocalAddressSearch_FeatureServer_0` | 103,176 | 103,176 | 0.00% | ok |
| 163 | `ounty_gov_ext_rest_services_Public_Addresses_FeatureServer_0` | 103,061 | 103,061 | 0.00% | ok |
| 164 | `t_services_YoloCounty_OpenData_AddressPoints_FeatureServer_3` | 102,821 | 102,821 | 0.00% | ok |
| 165 | `gov_arcgis_rest_services_Open_Data_Addresses_FeatureServer_4` | 101,641 | 101,641 | 0.00% | ok |
| 166 | `Di_arcgis_rest_services_Addresses__Open_Data_FeatureServer_0` | 101,641 | 101,641 | 0.00% | ok |
| 167 | `vices_SAM_Addresses_for_BERDO_2020_Buildings_FeatureServer_0` | 101,615 | 101,615 | 0.00% | ok |
| 168 | `cture_Address_Points_of_Washington_County_PA_FeatureServer_1` | 101,482 | 101,482 | 0.00% | ok |
| 169 | `erver_rest_services_SCData_VotingPrecinctsWebMap_MapServer_2` | 101,043 | 101,043 | 0.00% | ok |
| 170 | `cgis_rest_services_PropertyAndBoundaries_Address_MapServer_0` | 101,036 | 101,036 | 0.00% | ok |
| 171 | `ymNNZ2_arcgis_rest_services_Address_Points_FeatureServer_156` | 100,971 | 100,971 | 0.00% | ok |
| 172 | `tg2A1_arcgis_rest_services_vw_dist_addresses_FeatureServer_0` | 100,714 | 100,714 | 0.00% | ok |
| 173 | `rcgis_rest_services_Address_Point_Extraction_FeatureServer_0` | 100,695 | 100,695 | 0.00% | ok |
| 174 | `jZTGW_arcgis_rest_services_SQL2_Address_view_FeatureServer_0` | 100,695 | 100,695 | 0.00% | ok |
| 175 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 2,000 | 98.01% | failed |
| 176 | `fnAgB_arcgis_rest_services_Weber_address_pts_FeatureServer_0` | 100,184 | 100,184 | 0.00% | ok |
| 177 | `_arcgis_rest_services_AddressPoints_1Spatial_FeatureServer_0` | 99,815 | 99,815 | 0.00% | ok |
| 178 | `gis_rest_services_SiteStructureAddressPoints_FeatureServer_0@未定位-4` | 99,774 | 99,774 | 0.00% | ok |
| 179 | `r_arcgis_rest_services_Coryell_address_5Mile_FeatureServer_0` | 99,593 | 99,593 | 0.00% | ok |
| 180 | `est_services_Orland_Park_Address_Points_2022_FeatureServer_0` | 99,315 | 99,315 | 0.00% | ok |
| 181 | `s_rest_services_NM911_Address_01_2026_SC_Web_FeatureServer_0` | 99,052 | 99,052 | 0.00% | ok |
| 182 | `Ljlp7_arcgis_rest_services_ParcelsAndAddress_FeatureServer_0` | 98,939 | 98,939 | 0.00% | ok |
| 183 | `wbCJ2GMP_arcgis_rest_services_E911calls_2020_FeatureServer_0` | 98,649 | 98,649 | 0.00% | ok |
| 184 | `arcgis_rest_services_NM911_Address_202506_SC_FeatureServer_0` | 98,409 | 98,409 | 0.00% | ok |
| 185 | `_rest_services_CityCounty_addresspoints_view_FeatureServer_0` | 98,399 | 98,399 | 0.00% | ok |
| 186 | `s_rest_services_CityCounty_addresspoint_view_FeatureServer_0` | 98,399 | 98,399 | 0.00% | ok |
| 187 | `F_arcgis_rest_services_NM911_Address_02_2025_FeatureServer_0` | 97,956 | 97,956 | 0.00% | ok |
| 188 | `F_arcgis_rest_services_NM911_Address_10_2024_FeatureServer_0` | 97,603 | 97,603 | 0.00% | ok |
| 189 | `VWAC8iN_arcgis_rest_services_road_centerline_FeatureServer_0` | 97,499 | 97,499 | 0.00% | ok |
| 190 | `st_services_Springfield_address_density_WFL1_FeatureServer_2` | 97,259 | 97,259 | 0.00% | ok |
| 191 | `nQPdJ0azuLyn_arcgis_rest_services_AddressPts_FeatureServer_0` | 97,202 | 97,202 | 0.00% | ok |
| 192 | `rcgis_rest_services_AddressPointsRentalUnits_FeatureServer_0` | 97,090 | 97,090 | 0.00% | ok |
| 193 | `st_services_Auditor_Address_Points_June_2019_FeatureServer_0` | 96,818 | 96,818 | 0.00% | ok |
| 194 | `net_arcgis_rest_services_HubLayers_Addresses_FeatureServer_0` | 96,796 | 96,796 | 0.00% | ok |
| 195 | `is_rest_services_FUSD_AddressPoints_20241007_FeatureServer_0` | 96,737 | 96,737 | 0.00% | ok |
| 196 | `c_com_arcgis_rest_services_Elections_SupDist2021_MapServer_1` | 96,621 | 96,589 | 0.03% | ok |
| 197 | `JbeSi1G6zWeN_arcgis_rest_services_KC_Address_FeatureServer_1` | 96,505 | 96,505 | 0.00% | ok |
| 198 | `NTUHp_arcgis_rest_services_2022AddressPoints_FeatureServer_0` | 96,462 | 96,462 | 0.00% | ok |
| 199 | `_rest_services_NM911_Address_202401_SC_Web_a_FeatureServer_0` | 96,299 | 96,299 | 0.00% | ok |
| 200 | `gis_rest_services_Address_For_WebApp_Locator_FeatureServer_0` | 96,253 | 96,253 | 0.00% | ok |
| 201 | `5OXNGFDn_arcgis_rest_services_Address_Points_FeatureServer_2` | 96,211 | 96,211 | 0.00% | ok |
| 202 | `sPajnMahHp6RYgB_arcgis_rest_services_Base_FS_FeatureServer_0` | 96,204 | 96,204 | 0.00% | ok |
| 203 | `_rest_services_First_Due_Address_Points_WFL1_FeatureServer_0` | 95,990 | 95,990 | 0.00% | ok |
| 204 | `is_rest_services_NM911_Address_202301_SC_Web_FeatureServer_0` | 95,212 | 95,212 | 0.00% | ok |
| 205 | `YRWV44nBqV_arcgis_rest_services_SC_Addresses_FeatureServer_0` | 95,161 | 95,161 | 0.00% | ok |
| 206 | `s_to_All_Bell_County_Voter_Address_Points_v6_FeatureServer_0` | 95,048 | 95,048 | 0.00% | ok |
| 207 | `st_services_VoterRegistrationAddress_Public_FeatureServer_12` | 94,634 | 94,634 | 0.00% | ok |
| 208 | `ty_org_arcgis_rest_services_Hub_PublicSafety_Hub_MapServer_4` | 94,566 | 94,566 | 0.00% | ok |
| 209 | `_services_Ouachita_Parish_911_Address_points_FeatureServer_0` | 94,215 | 94,215 | 0.00% | ok |
| 210 | `037wYhPG904_arcgis_rest_services_address_COV_FeatureServer_0` | 94,002 | 94,002 | 0.00% | ok |
| 211 | `is_rest_services_Forsyth_County_GA_Addresses_FeatureServer_0` | 93,990 | 93,990 | 0.00% | ok |
| 212 | `st_services_SchoolBoundary_addressPnt_Update_FeatureServer_0` | 93,542 | 93,542 | 0.00% | ok |
| 213 | `lueBMxIOHOjKe_arcgis_rest_services_Addresses_FeatureServer_0` | 93,381 | 93,381 | 0.00% | ok |
| 214 | `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,362 | 0 | 100.00% | failed |
| 215 | `u0_arcgis_rest_services_Address_OfflineCopy_FeatureServer_21` | 93,230 | 93,230 | 0.00% | ok |
| 216 | `es_June_2026_Hyland_Hills_Addresses_with_ZIP_FeatureServer_0` | 93,158 | 93,158 | 0.00% | ok |
| 217 | `Ph_arcgis_rest_services_Santa_Rosa_Addresses_FeatureServer_3` | 93,088 | 93,088 | 0.00% | ok |
| 218 | `GqZL7U3_arcgis_rest_services_Primary_Address_FeatureServer_0` | 92,940 | 92,940 | 0.00% | ok |
| 219 | `41_arcgis_rest_services_Riverside_Address_Pt_FeatureServer_0` | 92,927 | 92,927 | 0.00% | ok |
| 220 | `RLGNbA2hh7gE_arcgis_rest_services_EugAddress_FeatureServer_0` | 92,634 | 92,634 | 0.00% | ok |
| 221 | `aNxg1PvwI_arcgis_rest_services_CityAddresses_FeatureServer_0` | 92,587 | 92,587 | 0.00% | ok |
| 222 | `jlqdhhFKP9_arcgis_rest_services_Address_view_FeatureServer_0` | 92,396 | 92,396 | 0.00% | ok |
| 223 | `TCmMFjlqdhhFKP9_arcgis_rest_services_Address_FeatureServer_0` | 92,396 | 92,396 | 0.00% | ok |
| 224 | `s_rest_services_SurpriseAddress_Points052026_FeatureServer_0` | 92,237 | 92,237 | 0.00% | ok |
| 225 | `1SIRs7_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_180` | 92,217 | 92,217 | 0.00% | ok |
| 226 | `s_rest_services_SurpriseAddressPoints_012326_FeatureServer_3` | 91,841 | 91,841 | 0.00% | ok |
| 227 | `ZLFK9_arcgis_rest_services_HB_Address_Point_FeatureServer_25` | 91,787 | 91,787 | 0.00% | ok |
| 228 | `k6RO1_arcgis_rest_services_HudsonCty_AddrPts_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 229 | `arcgis_rest_services_Hudson_County_Addresses_FeatureServer_0` | 91,765 | 91,765 | 0.00% | ok |
| 230 | `s_nnva_gov_gis_rest_services_Operational_Address_MapServer_0` | 91,661 | 91,661 | 0.00% | ok |
| 231 | `Wg1Aw7azh41_arcgis_rest_services_AddressPnts_FeatureServer_0` | 91,597 | 91,597 | 0.00% | ok |
| 232 | `cgis_rest_services_TCECD_Site_Address_Points_FeatureServer_2` | 91,383 | 91,383 | 0.00% | ok |
| 233 | `_arcgis_rest_services_BILLING_ACCT_LOCATIONS_FeatureServer_0` | 91,378 | 91,378 | 0.00% | ok |
| 234 | `erver_rest_services_ReferenceMap_Addresses_R_FeatureServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 235 | `arcserver_rest_services_ReferenceMap_Addresses_R_MapServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 236 | `ervices_ReferenceMap_Aerial_Site_Address_Point_R_MapServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 237 | `is_rest_services_AddressValidationTest2_WFL1_FeatureServer_0` | 91,269 | 91,269 | 0.00% | ok |
| 238 | `RY_arcgis_rest_services_CityAddressPoints_FeatureServer_1521` | 91,215 | 91,215 | 0.00% | ok |
| 239 | `v_arcgis_rest_services_Addresses_Offline2026_FeatureServer_0` | 91,212 | 91,212 | 0.00% | ok |
| 240 | `Np6bMI13R_arcgis_rest_services_AddressPoints_FeatureServer_0` | 91,181 | 91,181 | 0.00% | ok |
| 241 | `h41_arcgis_rest_services_ParcelsAndAddresses_FeatureServer_0` | 91,155 | 91,155 | 0.00% | ok |
| 242 | `41_arcgis_rest_services_ParcelsAndAddresses__FeatureServer_0` | 91,155 | 91,155 | 0.00% | ok |
| 243 | `_rest_services_Greenville__NC_Address_points_FeatureServer_0` | 90,984 | 90,984 | 0.00% | ok |
| 244 | `rcgis_rest_services_City_Address_Points_CAD_FeatureServer_71` | 90,972 | 90,972 | 0.00% | ok |
| 245 | `rest_services_Surprise_Address_Points_092425_FeatureServer_4` | 90,963 | 90,963 | 0.00% | ok |
| 246 | `M5nL34_arcgis_rest_services_GIS_AddressPoint_FeatureServer_0` | 90,879 | 90,879 | 0.00% | ok |
| 247 | `Y_arcgis_rest_services_Address_Points_Static_FeatureServer_0` | 90,874 | 90,874 | 0.00% | ok |
| 248 | `rcgis_rest_services_PropertyViewer_Addresses_FeatureServer_0` | 90,747 | 90,747 | 0.00% | ok |
| 249 | `s_rest_services_City_Address_Points_Dynamic_FeatureServer_30` | 90,706 | 90,706 | 0.00% | ok |
| 250 | `QgoA_arcgis_rest_services_MVWA_AddressPoints_FeatureServer_4` | 90,699 | 90,699 | 0.00% | ok |
| 251 | `rcgis_rest_services_City_Address_Points_RTCC_FeatureServer_0` | 90,687 | 90,687 | 0.00% | ok |
| 252 | `wad_rest_services_PublicSafety_DroneSense_Layers_MapServer_1` | 90,680 | 90,680 | 0.00% | ok |
| 253 | `iJkq4oXsPh_arcgis_rest_services_Addresses_SR_FeatureServer_0` | 88,553 | 88,553 | 0.00% | ok |
| 254 | `mxCAS_arcgis_rest_services_ClermontAddresses_FeatureServer_0` | 88,301 | 88,301 | 0.00% | ok |
| 255 | `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` | 87,697 | 174,890 | -99.43% | partial |
| 256 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1` | 84,306 | 168,433 | -99.79% | partial |
| 257 | `t_services_Katy_ISD_Harris_County_Addresses_FeatureServer_68` | 83,545 | 83,545 | 0.00% | ok |
| 258 | `I64Ui_arcgis_rest_services_WLAddressAndRoads_FeatureServer_0` | 83,223 | 83,223 | 0.00% | ok |
| 259 | `Spu5VOlu_arcgis_rest_services_Site_Addresses_FeatureServer_0` | 83,144 | 83,144 | 0.00% | ok |
| 260 | `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_FeatureServer_0` | 83,101 | 83,101 | 0.00% | ok |
| 261 | `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0` | 82,602 | 165,191 | -99.98% | partial |
| 262 | `jSxUKayj_arcgis_rest_services_911_Addresses_FeatureServer_58` | 81,591 | 81,591 | 0.00% | ok |
| 263 | `C_arcgis_rest_services_Active_Addresses_2025_FeatureServer_0` | 77,324 | 77,324 | 0.00% | ok |
| 264 | `dYPQqS1KF_arcgis_rest_services_AddressPoints_FeatureServer_0` | 76,208 | 76,208 | 0.00% | ok |
| 265 | `23gQB5_arcgis_rest_services_EsiteAddr_Collab_FeatureServer_0` | 76,053 | 76,053 | 0.00% | ok |
| 266 | `ndtexas_gov_arcgis_rest_services_Energov_Energov_MapServer_0` | 76,053 | 76,053 | 0.00% | ok |
| 267 | `wLs3iGyK80EW_arcgis_rest_services_911Address_FeatureServer_0` | 75,909 | 75,909 | 0.00% | ok |
| 268 | `arcgis_rest_services_modified_JaCo_addresses_FeatureServer_0` | 75,681 | 75,681 | 0.00% | ok |
| 269 | `9CkZD_arcgis_rest_services_ChlormaineAddress_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 270 | `srDo0QMPlK9CkZD_arcgis_rest_services_Address_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 271 | `0QMPlK9CkZD_arcgis_rest_services_SiteAddress_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 272 | `arcgis_rest_services_Planning_Address_Points_FeatureServer_1` | 75,416 | 75,416 | 0.00% | ok |
| 273 | `_arcgis_rest_services_Addresses_USA_combined_FeatureServer_0` | 75,340 | 75,340 | 0.00% | ok |
| 274 | `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0` | 75,051 | 75,046 | 0.01% | ok |
| 275 | `Cz_arcgis_rest_services_HC_MD_Addresses_10mi_FeatureServer_0` | 74,273 | 74,273 | 0.00% | ok |
| 276 | `landtx_gov_server1_rest_services_BASEMAP_ADDRESS_MapServer_0` | 74,181 | 74,181 | 0.00% | ok |
| 277 | `C0yIuqCBxq_arcgis_rest_services_Address_2024_FeatureServer_0` | 73,380 | 73,380 | 0.00% | ok |
| 278 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 279 | `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2` | 72,868 | 145,729 | -99.99% | partial |
| 280 | `CXd1_arcgis_rest_services_Fargo_ND_Addresses_FeatureServer_0` | 72,684 | 72,684 | 0.00% | ok |
| 281 | `_pa_us_arcgis_rest_services_Hosted_Addresses_FeatureServer_0` | 72,208 | 72,208 | 0.00% | ok |
| 282 | `3P_arcgis_rest_services_SiteAddresses_public_FeatureServer_0@TX-2` | 71,798 | 71,798 | 0.00% | ok |
| 283 | `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` | 71,260 | 142,442 | -99.89% | partial |
| 284 | `U5257_arcgis_rest_services_Yonkers_Addresses_FeatureServer_0` | 71,097 | 71,097 | 0.00% | ok |
| 285 | `rcgis_rest_services_AddressPts_20230817_WFL1_FeatureServer_0` | 70,830 | 70,830 | 0.00% | ok |
| 286 | `arcgis_rest_services_AddressPt_20240705_WFL1_FeatureServer_0` | 70,586 | 70,586 | 0.00% | ok |
| 287 | `t3XQ_arcgis_rest_services_AddressPt_20230629_FeatureServer_0` | 70,491 | 70,491 | 0.00% | ok |
| 288 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0` | 70,213 | 70,213 | 0.00% | ok |
| 289 | `f_arcgis_rest_services_Killeen_AddressPoints_FeatureServer_0` | 70,199 | 70,199 | 0.00% | ok |
| 290 | `is_rest_services_Building_Permit_Addresssing_FeatureServer_0` | 69,365 | 69,365 | 0.00% | ok |
| 291 | `0gE_arcgis_rest_services_CenCom_Address_View_FeatureServer_0` | 69,075 | 69,075 | 0.00% | ok |
| 292 | `arverLink_Address_Lookup_20250623_PublicView_FeatureServer_0` | 67,699 | 67,699 | 0.00% | ok |
| 293 | `zOpn2_arcgis_rest_services_Streets_Buidlings_FeatureServer_0` | 65,488 | 65,488 | 0.00% | ok |
| 294 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0` | 64,989 | 129,960 | -99.97% | partial |
| 295 | `_rest_services_Randall_County_Addresses_WFL1_FeatureServer_1` | 64,757 | 64,757 | 0.00% | ok |
| 296 | `Tpwo5_arcgis_rest_services_FullAddress032026_FeatureServer_0` | 64,608 | 64,608 | 0.00% | ok |
| 297 | `AQncZQEtBv_arcgis_rest_services_Address_Clip_FeatureServer_0` | 64,333 | 64,333 | 0.00% | ok |
| 298 | `cgis_rest_services_Cedar_Rapids_IA_Addresses_FeatureServer_0` | 63,767 | 63,767 | 0.00% | ok |
| 299 | `AQdtmx0tv46_arcgis_rest_services_Address_Nye_FeatureServer_6` | 63,594 | 63,594 | 0.00% | ok |
| 300 | `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0` | 63,212 | 126,366 | -99.91% | partial |
| 301 | `5jlmVkpxP_arcgis_rest_services_Online911Data_FeatureServer_0` | 63,126 | 63,126 | 0.00% | ok |
| 302 | `dresses_in_City_Limits___ESD9___Web_Map_WFL1_FeatureServer_1` | 62,839 | 62,839 | 0.00% | ok |
| 303 | `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0` | 62,581 | 125,156 | -99.99% | partial |
| 304 | `InLrxvF0A_arcgis_rest_services_AddressR2_gdb_FeatureServer_0` | 60,615 | 60,615 | 0.00% | ok |
| 305 | `WNInLrxvF0A_arcgis_rest_services_Address_gdb_FeatureServer_0` | 60,326 | 60,326 | 0.00% | ok |
| 306 | `s_rest_services_Marathon_County_WI_Addresses_FeatureServer_0` | 59,998 | 59,998 | 0.00% | ok |
| 307 | `vF0A_arcgis_rest_services_AddressSearchLayer_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 308 | `AAWNInLrxvF0A_arcgis_rest_services_TCAddress_FeatureServer_0` | 59,886 | 59,886 | 0.00% | ok |
| 309 | `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` | 59,831 | 119,500 | -99.73% | partial |
| 310 | `arcgis_rest_services_Tompkins_County_Address_FeatureServer_0` | 59,711 | 59,711 | 0.00% | ok |
| 311 | `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0` | 58,760 | 117,274 | -99.58% | partial |
| 312 | `rcgis_rest_services_MC_Address_Pts_PMG_View1_FeatureServer_0` | 58,269 | 58,269 | 0.00% | ok |
| 313 | `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` | 58,034 | 116,044 | -99.96% | partial |
| 314 | `d1_arcgis_rest_services_Visalia_CA_Addresses_FeatureServer_0` | 57,934 | 57,934 | 0.00% | ok |
| 315 | `nica_gov_server_rest_services_Address_Points_FeatureServer_0` | 57,063 | 57,063 | 0.00% | ok |
| 316 | `rcgis_rest_services_Address_Points_Open_Data_FeatureServer_0@VA-2` | 57,046 | 57,046 | 0.00% | ok |
| 317 | `iyW_arcgis_rest_services_BPLU_Address_Points_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 318 | `cgis_rest_services_BPLU_Address_Points_Final_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 319 | `cgis_rest_services_BPLU_Address_Points_Parts_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 320 | `gis_adaptor_rest_services_OpenData_AddressPoints_MapServer_0` | 57,021 | 57,021 | 0.00% | ok |
| 321 | `KtMulHM03_arcgis_rest_services_AddressPoints_FeatureServer_0` | 56,972 | 56,972 | 0.00% | ok |
| 322 | `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 99.85% | failed |
| 323 | `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | 56,599 | 113,267 | -100.12% | partial |
| 324 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0` | 55,639 | 55,639 | 0.00% | ok |
| 325 | `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` | 54,793 | 54,793 | 0.00% | ok |
| 326 | `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | 54,644 | 109,268 | -99.96% | partial |
| 327 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0` | 52,649 | 52,649 | 0.00% | ok |
| 328 | `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` | 52,368 | 52,368 | 0.00% | ok |
| 329 | `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6` | 52,022 | 52,022 | 0.00% | ok |
| 330 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | 51,423 | 102,815 | -99.94% | partial |
| 331 | `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 100.00% | failed |
| 332 | `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 100.00% | failed |
| 333 | `st_services_A4_Landscape_addressverification_FeatureServer_1` | 49,808 | 49,808 | 0.00% | ok |
| 334 | `com_arcgis_rest_services_CommunityAddressing_FeatureServer_0` | 49,804 | 49,804 | 0.00% | ok |
| 335 | `teAddresses_ecd2ff39fbb34f39a2ec415fd784331b_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 336 | `teAddresses_b786541565b5475593a786a08ba6b3e2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 337 | `sses_public_a000778ae1664a348de916831f1a0ac0_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 338 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 339 | `teAddresses_1809c74f027741ce815587367a5cfd68_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 340 | `teAddresses_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 341 | `teAddresses_25f96256e2164540bc18abbff8a9d5c2_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 342 | `sses_public_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 343 | `vN_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 344 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 345 | `d1DIvN_arcgis_rest_services_SiteAddresses__1_FeatureServer_1` | 49,802 | 49,802 | 0.00% | ok |
| 346 | `sses_public_a2522c3dfde94f6da7500df892abf9aa_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 347 | `sses_public_fa4be22034f14c15a3a589dd7009ca64_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 348 | `0JE2L2xUd_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 49,802 | 49,802 | 0.00% | ok |
| 349 | `sses_public_e7c532395de343e38e58a8463128cfb7_FeatureServer_0` | 49,800 | 49,800 | 0.00% | ok |
| 350 | `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 100.00% | failed |
| 351 | `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0` | 49,100 | 98,176 | -99.95% | partial |
| 352 | `eajjke_arcgis_rest_services_Addresses_Rogers_FeatureServer_0` | 48,889 | 48,889 | 0.00% | ok |
| 353 | `aNxg1PvwI_arcgis_rest_services_All_Addresses_FeatureServer_0` | 48,666 | 48,666 | 0.00% | ok |
| 354 | `cgis_rest_services_NRSA_Address_Locator_WFL1_FeatureServer_8` | 48,634 | 48,634 | 0.00% | ok |
| 355 | `KpsCnqD7H_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 48,448 | 48,448 | 0.00% | ok |
| 356 | `Geezhu2j_arcgis_rest_services_E911_Addresses_FeatureServer_0` | 48,443 | 48,443 | 0.00% | ok |
| 357 | `_services_County_Addressing_Application_View_FeatureServer_0` | 47,763 | 47,763 | 0.00% | ok |
| 358 | `rvices_Public_Taxlots_with_SiteAddresses_Service_MapServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 359 | `Taxlots_TRAKiT_with_SiteAddressPoint_Service_FeatureServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 360 | `es_Public_Taxlots_with_SiteAddresses_Service_FeatureServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 361 | `MLI_Taxlots_TRAKiT_with_SiteAddressPoint_Service_MapServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 362 | `ns7W6juha0m_arcgis_rest_services_AddressSite_FeatureServer_0` | 47,592 | 47,592 | 0.00% | ok |
| 363 | `7W6juha0m_arcgis_rest_services_AddressPoints_FeatureServer_0` | 47,577 | 47,577 | 0.00% | ok |
| 364 | `l_gov_arcgis_rest_services_ACGOL_ACGOL_Addresses_MapServer_0` | 47,567 | 47,567 | 0.00% | ok |
| 365 | `G_arcgis_rest_services_Address_Points_Public_FeatureServer_0` | 47,540 | 47,540 | 0.00% | ok |
| 366 | `_rest_services_Worth_Township_Address_Points_FeatureServer_0` | 47,513 | 47,513 | 0.00% | ok |
| 367 | `Ilt_arcgis_rest_services_Clinton_Address_Pts_FeatureServer_0` | 47,510 | 47,510 | 0.00% | ok |
| 368 | `com_arcserver_rest_services_911Addresses_PDS_FeatureServer_0` | 47,416 | 47,416 | 0.00% | ok |
| 369 | `t_services_ReferenceMap_SiteAddressPoint_R_FeatureServer_297` | 47,416 | 47,416 | 0.00% | ok |
| 370 | `_com_arcserver_rest_services_911Addresses_PW_FeatureServer_0` | 47,416 | 47,416 | 0.00% | ok |
| 371 | `ces_City_Share_City_Share_Active911Addresses_FeatureServer_0` | 47,377 | 47,377 | 0.00% | ok |
| 372 | `8SbZx_arcgis_rest_services_Menifee_Addresses_FeatureServer_0` | 47,307 | 47,307 | 0.00% | ok |
| 373 | `gYSxztFGZwla_arcgis_rest_services_AddressPts_FeatureServer_0` | 47,299 | 47,299 | 0.00% | ok |
| 374 | `us_arcgis_ea_rest_services_OpenAccess_CC_Address_MapServer_0` | 47,294 | 47,294 | 0.00% | ok |
| 375 | `_arcgis_rest_services_Parcels_With_Addresses_FeatureServer_0` | 47,286 | 47,286 | 0.00% | ok |
| 376 | `50u6oHu4Z_arcgis_rest_services_FSA_Addresses_FeatureServer_0` | 47,269 | 47,269 | 0.00% | ok |
| 377 | `gis_rest_services_ADDRESS_SITE_POINTS_static_FeatureServer_0` | 47,249 | 47,249 | 0.00% | ok |
| 378 | `rcgis_rest_services_Open_Data_Address_Points_FeatureServer_0@未定位-1` | 47,230 | 47,230 | 0.00% | ok |
| 379 | `_arcgis_rest_services_BG911_Address_20250501_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 380 | `Bq9hgug_arcgis_rest_services_BG911_Addresses_FeatureServer_0` | 47,191 | 47,191 | 0.00% | ok |
| 381 | `rest_services_City_of_Kelowna_Address_Points_FeatureServer_0` | 47,128 | 47,128 | 0.00% | ok |
| 382 | `xPpXv8MHiv19f_arcgis_rest_services_Addresses_FeatureServer_1` | 46,968 | 46,968 | 0.00% | ok |
| 383 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-1` | 46,965 | 46,965 | 0.00% | ok |
| 384 | `0gE_arcgis_rest_services_Address_Points_View_FeatureServer_4` | 46,960 | 46,960 | 0.00% | ok |
| 385 | `e_Rollout__Days_of_Service_Per_Address__WFL1_FeatureServer_1` | 46,949 | 46,949 | 0.00% | ok |
| 386 | `XFjUq7iY_arcgis_rest_services_Address_Points_FeatureServer_0` | 46,934 | 46,934 | 0.00% | ok |
| 387 | `dZFl3Y1kjj_arcgis_rest_services_NC_Addresses_FeatureServer_0` | 46,879 | 46,879 | 0.00% | ok |
| 388 | `arcgis_rest_services_Physical_Addresses_view_FeatureServer_0` | 46,789 | 46,789 | 0.00% | ok |
| 389 | `7ey_arcgis_rest_services_Addresses_Parcel_00_FeatureServer_6` | 46,764 | 46,764 | 0.00% | ok |
| 390 | `9ZWWXL1M_arcgis_rest_services_Address_Points_FeatureServer_0` | 46,759 | 46,759 | 0.00% | ok |
| 391 | `is_rest_services_ParcelsAddressSummaryPoints_FeatureServer_1` | 46,701 | 46,701 | 0.00% | ok |
| 392 | `hhip_arcgis_rest_services_COB_Address_Points_FeatureServer_6` | 46,642 | 46,642 | 0.00% | ok |
| 393 | `eOv_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 46,624 | 46,624 | 0.00% | ok |
| 394 | `gis_rest_services_Public_View_Address_Points_FeatureServer_0` | 46,537 | 46,537 | 0.00% | ok |
| 395 | `ton_ca_arcgis_rest_services_Datasets_Address_Pts_MapServer_0` | 46,446 | 46,446 | 0.00% | ok |
| 396 | `est_services_Datasets_AMANDA_Address_Parcel_Link_MapServer_0` | 46,440 | 46,440 | 0.00% | ok |
| 397 | `2_arcgis_rest_services_BOCA_SITUS_CYCLOMEDIA_FeatureServer_0` | 45,877 | 45,877 | 0.00% | ok |
| 398 | `CjIDJJ2_arcgis_rest_services_BOCA_SITUS_CITY_FeatureServer_0` | 45,877 | 45,877 | 0.00% | ok |
| 399 | `ntyva_gov_arcgis_rest_services_JCC_GIS_Data_FeatureServer_16@未定位-1` | 45,833 | 45,833 | 0.00% | ok |
| 400 | `ntyva_gov_arcgis_rest_services_JCC_GIS_Data_FeatureServer_16@未定位-2` | 45,833 | 45,833 | 0.00% | ok |
| 401 | `gis_rest_services_CountyAddress2023_CHE_View_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 402 | `I64Ui_arcgis_rest_services_CountyAddress2023_FeatureServer_7` | 45,807 | 45,807 | 0.00% | ok |
| 403 | `_rest_services_Site_Structure_Address_Points_FeatureServer_1@AL-1` | 45,765 | 45,765 | 0.00% | ok |
| 404 | `t_services_SiteAddressPoint_ByVotingPrecinct_FeatureServer_9` | 45,699 | 45,699 | 0.00% | ok |
| 405 | `qTGWY_arcgis_rest_services_JoCo_Site_Address_FeatureServer_1` | 45,019 | 45,019 | 0.00% | ok |
| 406 | `71LO_arcgis_rest_services_Addresses_CivQuest_FeatureServer_0` | 45,012 | 45,012 | 0.00% | ok |
| 407 | `2kwz79KUqUvxC_arcgis_rest_services_Addresses_FeatureServer_0` | 44,833 | 44,833 | 0.00% | ok |
| 408 | `wFbS_arcgis_rest_services_Chemungaddress_pts_FeatureServer_0` | 44,642 | 44,642 | 0.00% | ok |
| 409 | `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` | 43,499 | 86,993 | -99.99% | partial |
| 410 | `_arcgis_rest_services_Addresses_NOT_ELIGIBLE_FeatureServer_0` | 43,411 | 43,411 | 0.00% | ok |
| 411 | `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0` | 43,405 | 86,789 | -99.95% | partial |
| 412 | `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` | 43,042 | 86,008 | -99.82% | partial |
| 413 | `s_rest_services_CityAddresses2022bu_CHE_view_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 414 | `4Ui_arcgis_rest_services_CityAddresses2022bu_FeatureServer_0` | 42,337 | 42,337 | 0.00% | ok |
| 415 | `s_rest_services_Raleigh_Co_EOC_Address_Sites_FeatureServer_0` | 42,165 | 42,165 | 0.00% | ok |
| 416 | `3kMP_arcgis_rest_services_E911AddressforSOMA_FeatureServer_0` | 41,887 | 41,887 | 0.00% | ok |
| 417 | `est_services_NormanResidentialTrashAddresses_FeatureServer_0` | 41,811 | 41,811 | 0.00% | ok |
| 418 | `s_rest_services_Master_Address_List_Aug_2026_FeatureServer_0` | 41,460 | 41,460 | 0.00% | ok |
| 419 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10` | 41,175 | 41,175 | 0.00% | ok |
| 420 | `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` | 41,018 | 82,028 | -99.98% | partial |
| 421 | `OU_arcgis_rest_services_Addresses_SIO_Hosted_FeatureServer_0` | 40,752 | 40,752 | 0.00% | ok |
| 422 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | 40,689 | 0 | 100.00% | failed |
| 423 | `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 424 | `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` | 40,586 | 81,170 | -100.00% | partial |
| 425 | `1_arcgis_rest_services_Bismarck_ND_Addresses_FeatureServer_0` | 40,568 | 40,568 | 0.00% | ok |
| 426 | `IzAwdHlO_arcgis_rest_services_Address_hosted_FeatureServer_0` | 40,255 | 40,255 | 0.00% | ok |
| 427 | `u6oHu4Z_arcgis_rest_services_SITUS_PUB_CBB_2_FeatureServer_0` | 39,951 | 39,951 | 0.00% | ok |
| 428 | `m_nEIrIdcFpdK28ibf_arcgis_rest_services_E911_FeatureServer_1` | 39,855 | 39,855 | 0.00% | ok |
| 429 | `p_arcgis_rest_services_LAFO_ADDRESS_12_17_13_FeatureServer_0` | 39,847 | 39,847 | 0.00% | ok |
| 430 | `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | 39,743 | 39,503 | 0.60% | failed |
| 431 | `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54` | 39,239 | 39,239 | 0.00% | ok |
| 432 | `rcgis_rest_services_Res_Address_Demographics_FeatureServer_1` | 39,114 | 39,114 | 0.00% | ok |
| 433 | `_services_Nacogdoches_County_Address_Points_FeatureServer_10` | 38,691 | 38,691 | 0.00% | ok |
| 434 | `om_6443_arcgis_rest_services_Address_Points_2019_MapServer_0` | 38,689 | 38,689 | 0.00% | ok |
| 435 | `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` | 38,656 | 77,304 | -99.98% | partial |
| 436 | `YxoF_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 38,648 | 38,648 | 0.00% | ok |
| 437 | `t0KpGzI_arcgis_rest_services_SiteAddress_pub_FeatureServer_0` | 38,603 | 38,603 | 0.00% | ok |
| 438 | `est_services_OpenData_Address_Points_Updated_FeatureServer_0` | 38,571 | 38,571 | 0.00% | ok |
| 439 | `_services_Streets_and_Address_Points_for_911_FeatureServer_0` | 38,571 | 38,571 | 0.00% | ok |
| 440 | `z971EmeG3_arcgis_rest_services_AddressPoints_FeatureServer_0` | 38,505 | 38,505 | 0.00% | ok |
| 441 | `ca_gisernie_rest_services_Public_Ajax_Open_Data_MapServer_10` | 38,444 | 38,444 | 0.00% | ok |
| 442 | `d_Waste__Days_of_Service_Per_Address_092424_FeatureServer_52` | 38,389 | 38,389 | 0.00% | ok |
| 443 | `n_arcgis_rest_services_Municipal_911_Address_FeatureServer_0` | 38,383 | 38,383 | 0.00% | ok |
| 444 | `Esw_arcgis_rest_services_Ajax_Address_Points_FeatureServer_0` | 38,372 | 38,372 | 0.00% | ok |
| 445 | `8xIvXuYJiVZwF_arcgis_rest_services_Addresses_FeatureServer_0` | 38,356 | 38,356 | 0.00% | ok |
| 446 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address_FeatureServer_0` | 38,345 | 38,345 | 0.00% | ok |
| 447 | `rcgis_rest_services_Daly_City_Addresses_AGOL_FeatureServer_2` | 38,299 | 38,299 | 0.00% | ok |
| 448 | `xmkB3meN_arcgis_rest_services_Address_Points_FeatureServer_0` | 38,281 | 38,281 | 0.00% | ok |
| 449 | `1CITN3V3_arcgis_rest_services_Address_Points_FeatureServer_0` | 38,280 | 38,280 | 0.00% | ok |
| 450 | `temeculaca_gov_arcgis_rest_services_OpenData_FeatureServer_4` | 38,234 | 38,234 | 0.00% | ok |
| 451 | `B5jkAnFA_arcgis_rest_services_Addresses_view_FeatureServer_0` | 38,122 | 38,122 | 0.00% | ok |
| 452 | `P6CrfEsw_arcgis_rest_services_Address_Points_FeatureServer_1` | 38,072 | 38,072 | 0.00% | ok |
| 453 | `DOMEad_arcgis_rest_services_Harrison_Address_FeatureServer_1` | 37,989 | 37,989 | 0.00% | ok |
| 454 | `Ypus4pYH0S_arcgis_rest_services_Site_Address_FeatureServer_4` | 37,961 | 37,961 | 0.00% | ok |
| 455 | `q66_arcgis_rest_services_Erie_Address_Points_FeatureServer_0` | 37,906 | 37,906 | 0.00% | ok |
| 456 | `Kuj4Ua8_arcgis_rest_services_Address_Points_FeatureServer_31` | 37,901 | 37,901 | 0.00% | ok |
| 457 | `s_rest_services_UnionSnyderAddress_01_2026_FeatureServer_188` | 37,850 | 37,850 | 0.00% | ok |
| 458 | `cgis_rest_services_UnionSnyderAddressOct2025_FeatureServer_7` | 37,831 | 37,831 | 0.00% | ok |
| 459 | `blicDataEnterprise_PublicData_Address_Points_FeatureServer_0` | 37,813 | 37,813 | 0.00% | ok |
| 460 | `GIS_rest_services_Streets_and_Address_Points_FeatureServer_0` | 37,812 | 37,812 | 0.00% | ok |
| 461 | `rest_services_CarthageWardsandaddresses_WFL1_FeatureServer_1` | 37,764 | 37,764 | 0.00% | ok |
| 462 | `ElDOMEad_arcgis_rest_services_Marion_Address_FeatureServer_1` | 37,759 | 37,759 | 0.00% | ok |
| 463 | `est_services_Angelina_County_Address_Points_FeatureServer_10` | 37,709 | 37,709 | 0.00% | ok |
| 464 | `rcgis_rest_services_AddressPoints_amandaview_FeatureServer_0` | 37,707 | 37,707 | 0.00% | ok |
| 465 | `cgis_rest_services_AddressPoints_public_view_FeatureServer_0` | 37,707 | 37,707 | 0.00% | ok |
| 466 | `jia0CW_arcgis_rest_services_Address_Points_FeatureServer_340` | 37,635 | 37,635 | 0.00% | ok |
| 467 | `is_rest_services_Address_Points_Merged__view_FeatureServer_6` | 37,487 | 37,487 | 0.00% | ok |
| 468 | `is_rest_services_Madison_County_KY_Addresses_FeatureServer_1` | 37,446 | 37,446 | 0.00% | ok |
| 469 | `arcgis_rest_services_CPC_Address_Points_view_FeatureServer_0` | 37,408 | 37,408 | 0.00% | ok |
| 470 | `QYTTiP6CrfEsw_arcgis_rest_services_Addresses_FeatureServer_0` | 37,276 | 37,276 | 0.00% | ok |
| 471 | `ervices_Parcel_Address_Points_AddressOnly__1_FeatureServer_0` | 37,180 | 37,180 | 0.00% | ok |
| 472 | `_arcgis_rest_services_Flagstaff_AZ_Addresses_FeatureServer_0` | 37,174 | 37,174 | 0.00% | ok |
| 473 | `9J_arcgis_rest_services_AddressesPublic_View_FeatureServer_0` | 37,170 | 37,170 | 0.00% | ok |
| 474 | `TFQ5_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 37,164 | 37,164 | 0.00% | ok |
| 475 | `zUpjDtspiBG0j_arcgis_rest_services_E911_Copy_FeatureServer_0` | 37,066 | 37,066 | 0.00% | ok |
| 476 | `y5MmuVTV_arcgis_rest_services_Address_Points_FeatureServer_0` | 37,010 | 37,010 | 0.00% | ok |
| 477 | `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0` | 36,725 | 73,441 | -99.98% | partial |
| 478 | `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_FeatureServer_0` | 36,292 | 36,292 | 0.00% | ok |
| 479 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_FeatureServer_1` | 36,292 | 36,292 | 0.00% | ok |
| 480 | `gT_arcgis_rest_services_USU_Addressing_view_FeatureServer_26` | 36,150 | 36,150 | 0.00% | ok |
| 481 | `ofS_arcgis_rest_services_Taos_E911_Addresses_FeatureServer_0` | 35,970 | 35,970 | 0.00% | ok |
| 482 | `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,810 | 35,810 | 0.00% | ok |
| 483 | `rcgis_rest_services_CTSI_AddressChecker_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 484 | `s_rest_services_CTSI_Address_Check_2023_WFL1_FeatureServer_0` | 35,710 | 35,710 | 0.00% | ok |
| 485 | `PlhvQwvs_arcgis_rest_services_E911_Addrs_Pts_FeatureServer_0` | 35,637 | 35,637 | 0.00% | ok |
| 486 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0` | 35,212 | 70,424 | -100.00% | partial |
| 487 | `fMdTkPeHLCobS_arcgis_rest_services_Addresses_FeatureServer_0` | 35,199 | 35,199 | 0.00% | ok |
| 488 | `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 489 | `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0` | 34,929 | 69,851 | -99.98% | partial |
| 490 | `arcgis_rest_services_Alexandria_VA_Addresses_FeatureServer_0` | 34,927 | 34,927 | 0.00% | ok |
| 491 | `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0` | 34,840 | 69,679 | -100.00% | partial |
| 492 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2` | 34,683 | 34,683 | 0.00% | ok |
| 493 | `1p_arcgis_rest_services_ADDRESS_20230403_CoB_FeatureServer_0` | 34,536 | 34,536 | 0.00% | ok |
| 494 | `pMfHt82xFG_arcgis_rest_services_RouteAddress_FeatureServer_0` | 34,495 | 34,495 | 0.00% | ok |
| 495 | `cgis_rest_services_Master_Addresses_for_Grid_FeatureServer_0` | 34,386 | 34,386 | 0.00% | ok |
| 496 | `kOGGtW27pGICf_arcgis_rest_services_Addresses_FeatureServer_0` | 34,063 | 34,063 | 0.00% | ok |
| 497 | `cgis_rest_services_Sarpy_County_NE_Addresses_FeatureServer_1` | 33,980 | 33,980 | 0.00% | ok |
| 498 | `rcgis_rest_services_Essex_Address_Pts_9_9_25_FeatureServer_0` | 33,904 | 33,904 | 0.00% | ok |
| 499 | `v_appdata_rest_services_Addressing_MD_Addressing_MapServer_0` | 33,887 | 33,887 | 0.00% | ok |
| 500 | `65ptjBcDZM_arcgis_rest_services_MyMapService_FeatureServer_0` | 33,884 | 33,884 | 0.00% | ok |
| 501 | `WCoI_arcgis_rest_services_20260601_Addresses_FeatureServer_0` | 33,856 | 33,856 | 0.00% | ok |
| 502 | `oqakAkedEx0oU_arcgis_rest_services_Addresses_FeatureServer_0` | 33,791 | 33,791 | 0.00% | ok |
| 503 | `azssuvI82_arcgis_rest_services_AddressPoints_FeatureServer_0` | 33,777 | 33,777 | 0.00% | ok |
| 504 | `cgis_rest_services_Franklin_Co_911_Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 505 | `cgis_rest_services_FranklinCoVA_911Addresses_FeatureServer_0` | 33,769 | 33,769 | 0.00% | ok |
| 506 | `BDvIjv8OhMDVd_arcgis_rest_services_Addresses_FeatureServer_1` | 33,701 | 33,701 | 0.00% | ok |
| 507 | `aPG_arcgis_rest_services_CivicAddress_Public_FeatureServer_0` | 33,669 | 33,669 | 0.00% | ok |
| 508 | `cgis_rest_services_CampbellCountySiteAddress_FeatureServer_1` | 33,655 | 33,655 | 0.00% | ok |
| 509 | `Nwgn5oKx_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_0` | 33,653 | 33,653 | 0.00% | ok |
| 510 | `mpweKJ4f_arcgis_rest_services_Address_Points_FeatureServer_0` | 33,629 | 33,629 | 0.00% | ok |
| 511 | `J4f_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 33,629 | 33,629 | 0.00% | ok |
| 512 | `7_rest_services_Base_Layers_AddressPnt_local_FeatureServer_0` | 33,608 | 33,608 | 0.00% | ok |
| 513 | `1_arcgis_rest_services_Longview_TX_Addresses_FeatureServer_0` | 33,603 | 33,603 | 0.00% | ok |
| 514 | `S1a_arcgis_rest_services_Address_Mailing_Map_FeatureServer_1` | 33,587 | 33,587 | 0.00% | ok |
| 515 | `st_services_sloGISlayers_gisLandManagementWM_FeatureServer_2` | 33,572 | 33,572 | 0.00% | ok |
| 516 | `ev2aNwKyB_arcgis_rest_services_HTE_Addresses_FeatureServer_0` | 33,447 | 33,447 | 0.00% | ok |
| 517 | `wKyB_arcgis_rest_services_HTE_Addresses_view_FeatureServer_0` | 33,447 | 33,447 | 0.00% | ok |
| 518 | `d4ES_arcgis_rest_services_BelcoAddressPoints_FeatureServer_0` | 33,428 | 33,428 | 0.00% | ok |
| 519 | `JHVTrT_arcgis_rest_services_address_vwPublic_FeatureServer_0` | 33,414 | 33,414 | 0.00% | ok |
| 520 | `lYD_arcgis_rest_services_AddressPoints_24_12_FeatureServer_0` | 33,401 | 33,401 | 0.00% | ok |
| 521 | `UHl6XumF_arcgis_rest_services_R_AddressPoint_FeatureServer_0` | 33,337 | 33,337 | 0.00% | ok |
| 522 | `gGO9NJCc_arcgis_rest_services_Address_Points_FeatureServer_0` | 33,334 | 33,334 | 0.00% | ok |
| 523 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_FeatureServer_0` | 33,215 | 33,215 | 0.00% | ok |
| 524 | `cgis_rest_services_Riley_County_KS_Addresses_FeatureServer_0` | 33,193 | 33,193 | 0.00% | ok |
| 525 | `nz_arcgis_rest_services_Property_PropertyandLand_MapServer_0` | 33,167 | 33,167 | 0.00% | ok |
| 526 | `QgATDeUJrt_arcgis_rest_services_Site_Address_FeatureServer_0` | 33,107 | 33,107 | 0.00% | ok |
| 527 | `aCs_arcgis_rest_services_Parcels_and_Address_FeatureServer_0` | 33,041 | 33,041 | 0.00% | ok |
| 528 | `est_services_Pleasanton_Address_Point_Public_FeatureServer_0` | 33,033 | 33,033 | 0.00% | ok |
| 529 | `A3gGO9NJCc_arcgis_rest_services_AddressPoint_FeatureServer_0` | 32,983 | 32,983 | 0.00% | ok |
| 530 | `s_rest_services_Redlands_address_points_view_FeatureServer_0` | 32,926 | 32,926 | 0.00% | ok |
| 531 | `cgis_rest_services_Residential_AddressPoints_FeatureServer_0` | 32,919 | 32,919 | 0.00% | ok |
| 532 | `st_services_Vector_Tile_Site_Address_Labels_FeatureServer_57` | 32,917 | 32,917 | 0.00% | ok |
| 533 | `CFmA_arcgis_rest_services_Address_Points_New_FeatureServer_0` | 32,888 | 32,888 | 0.00% | ok |
| 534 | `ia_wi_us_server_rest_services_Address_points_FeatureServer_0` | 32,879 | 32,879 | 0.00% | ok |
| 535 | `ices_Medina_County_Address_Points_3_21_2023_FeatureServer_98` | 32,846 | 32,846 | 0.00% | ok |
| 536 | `eTUuaT56jB_arcgis_rest_services_RI_E911_Data_FeatureServer_0` | 32,746 | 32,746 | 0.00% | ok |
| 537 | `_arcgis_rest_services_zoningAddressingSearch_FeatureServer_0` | 32,625 | 32,625 | 0.00% | ok |
| 538 | `j7VSF_arcgis_rest_services_TemeculaAddresses_FeatureServer_0` | 32,615 | 32,615 | 0.00% | ok |
| 539 | `s_gscplanning_com_arcgis_rest_services_Addresses_MapServer_0` | 32,599 | 32,599 | 0.00% | ok |
| 540 | `nc_org_jcgis_rest_services_EM_Address_Points_FeatureServer_0` | 32,596 | 32,596 | 0.00% | ok |
| 541 | `s_rest_services_BaseLayer_FlockMap_Addresses_FeatureServer_0` | 32,590 | 32,590 | 0.00% | ok |
| 542 | `t_services_Addresses_with_Services_08_15_25_FeatureServer_14` | 32,559 | 32,559 | 0.00% | ok |
| 543 | `ces_GC_Address_Points_with_Utility_Providers_FeatureServer_0` | 32,534 | 32,534 | 0.00% | ok |
| 544 | `rcgis_rest_services_Pictometry_Layer_Updates_FeatureServer_1` | 32,483 | 32,483 | 0.00% | ok |
| 545 | `vfHOElpgGU_arcgis_rest_services_AddressPoint_FeatureServer_1` | 32,424 | 32,424 | 0.00% | ok |
| 546 | `xQE_arcgis_rest_services_NENA_Address_Points_FeatureServer_7` | 32,381 | 32,381 | 0.00% | ok |
| 547 | `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0` | 32,353 | 64,689 | -99.95% | partial |
| 548 | `_rest_services_ADDRESS_POINTS_CITYVIEW_WGS84_FeatureServer_0` | 32,318 | 32,318 | 0.00% | ok |
| 549 | `services_InteractiveMap_InteractiveMap_Addresses_MapServer_2` | 32,285 | 32,285 | 0.00% | ok |
| 550 | `co_columbia_wi_us_server_rest_services_Open_GIS_MapServer_59` | 32,285 | 32,285 | 0.00% | ok |
| 551 | `_arcgis_rest_services_Site_Address_Points_DL_FeatureServer_0` | 32,261 | 32,261 | 0.00% | ok |
| 552 | `I2T0wc_arcgis_rest_services_Address_Map_WFL1_FeatureServer_0` | 32,260 | 32,260 | 0.00% | ok |
| 553 | `_services_LenoirNC_Parcels_Zoning_Addressing_FeatureServer_0` | 32,218 | 32,218 | 0.00% | ok |
| 554 | `BpZX2wFbS_arcgis_rest_services_911addressing_FeatureServer_0` | 32,197 | 32,197 | 0.00% | ok |
| 555 | `gis_rest_services_BaseFeatures_CityScaleBaseData_MapServer_1` | 32,171 | 32,171 | 0.00% | ok |
| 556 | `rest_services_Cherokee_Address_Analysis_WFL1_FeatureServer_0` | 32,167 | 32,167 | 0.00% | ok |
| 557 | `cgis_rest_services_Addresses_in_service_area_FeatureServer_0` | 32,145 | 32,145 | 0.00% | ok |
| 558 | `l_arcgis_rest_services_Check_Point_Addresses_FeatureServer_0` | 32,097 | 32,097 | 0.00% | ok |
| 559 | `7_arcgis_rest_services_Public_Address_Points_FeatureServer_0` | 31,994 | 31,994 | 0.00% | ok |
| 560 | `VDElDOMEad_arcgis_rest_services_WayneAddress_FeatureServer_0` | 31,980 | 31,980 | 0.00% | ok |
| 561 | `rcgis_rest_services_Public_Addressing_Pro_JG_FeatureServer_0` | 31,966 | 31,966 | 0.00% | ok |
| 562 | `4FfmN3nn5_arcgis_rest_services_AddressPoints_FeatureServer_0` | 31,940 | 31,940 | 0.00% | ok |
| 563 | `SsReIxuA_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,887 | 31,887 | 0.00% | ok |
| 564 | `ss_Points_with_Phase_and_Timeline_View_Layer_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 565 | `est_services_BroadbandPhases_AddressesPoints_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 566 | `vices_Address_Points_with_Phase_and_Timeline_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 567 | `rest_services_AddressPoints_ByBroadbandPhase_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 568 | `Mfde8s_arcgis_rest_services_Site_Addresses_1_FeatureServer_0` | 31,748 | 31,748 | 0.00% | ok |
| 569 | `14j_arcgis_rest_services_Z_GIS_Addresses_SBG_FeatureServer_0` | 31,728 | 31,728 | 0.00% | ok |
| 570 | `qvET_arcgis_rest_services_Address_Points_GSY_FeatureServer_0` | 31,680 | 31,680 | 0.00% | ok |
| 571 | `est_services_InformationTechnology_AddressPoints_MapServer_0` | 31,669 | 31,669 | 0.00% | ok |
| 572 | `services_InformationTechnology_AddressPoints_FeatureServer_0` | 31,669 | 31,669 | 0.00% | ok |
| 573 | `8hXASVYi_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,630 | 31,630 | 0.00% | ok |
| 574 | `RPkF9w28VGX_arcgis_rest_services_Addresses_FeatureServer_359` | 31,624 | 31,624 | 0.00% | ok |
| 575 | `8aWlfDG1Qh_arcgis_rest_services_Address_pnts_FeatureServer_0` | 31,617 | 31,617 | 0.00% | ok |
| 576 | `s_rest_services_MiddlesexCountyAddressPoints_FeatureServer_0` | 31,571 | 31,571 | 0.00% | ok |
| 577 | `is_rest_services_Address_Points_20210707_CoB_FeatureServer_0` | 31,558 | 31,558 | 0.00% | ok |
| 578 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses_FeatureServer_0` | 31,520 | 31,520 | 0.00% | ok |
| 579 | `arcgis_rest_services_FranklinCountyAddresses_FeatureServer_0` | 31,516 | 31,516 | 0.00% | ok |
| 580 | `5GjGWCoI_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,470 | 31,470 | 0.00% | ok |
| 581 | `mib3H_arcgis_rest_services_addresspts_points_FeatureServer_0` | 31,455 | 31,455 | 0.00% | ok |
| 582 | `_rest_services_Address_Points_2019_05_20_CoB_FeatureServer_0` | 31,422 | 31,422 | 0.00% | ok |
| 583 | `k3_arcgis_rest_services_Address_Points_SFRes_FeatureServer_0` | 31,405 | 31,405 | 0.00% | ok |
| 584 | `GexkkJ9w_arcgis_rest_services_CivicAddresses_FeatureServer_0` | 31,363 | 31,363 | 0.00% | ok |
| 585 | `sGtVEXzaX_arcgis_rest_services_NYC_Addresses_FeatureServer_0` | 31,352 | 31,352 | 0.00% | ok |
| 586 | `cgis_rest_services_Address_20Points_20Mark43_FeatureServer_0` | 31,335 | 31,335 | 0.00% | ok |
| 587 | `gov_mapping_rest_services_VIEW_AddressPoints_FeatureServer_0` | 31,263 | 31,263 | 0.00% | ok |
| 588 | `xas_gov_mapping_rest_services_VIEW_AddressPoints_MapServer_0` | 31,263 | 31,263 | 0.00% | ok |
| 589 | `services_franklincountyaddresspoints_10_7_26_FeatureServer_0` | 31,241 | 31,241 | 0.00% | ok |
| 590 | `K9o0xX_arcgis_rest_services_Ztron_View_Layer_FeatureServer_0` | 31,202 | 31,202 | 0.00% | ok |
| 591 | `_arcgis_rest_services_AddressesForFairmont_FeatureServer_115` | 31,175 | 31,175 | 0.00% | ok |
| 592 | `_services_HemetAddressPoints122625_Projected_FeatureServer_0` | 31,162 | 31,162 | 0.00% | ok |
| 593 | `gRR0s_arcgis_rest_services_SiteAddressPoint_FeatureServer_47` | 31,150 | 31,150 | 0.00% | ok |
| 594 | `ct0i_arcgis_rest_services_Whittier_Addresses_FeatureServer_0` | 31,032 | 31,032 | 0.00% | ok |
| 595 | `fc16391ae7_rest_services_AGOPublic_PublicLayers_MapServer_34` | 30,941 | 30,941 | 0.00% | ok |
| 596 | `ez8fHeIiDRbgb_arcgis_rest_services_Addresses_FeatureServer_0` | 30,935 | 30,935 | 0.00% | ok |
| 597 | `aLg_arcgis_rest_services_Address_Hemet031325_FeatureServer_0` | 30,879 | 30,879 | 0.00% | ok |
| 598 | `rcgis_rest_services_Buildings_and_Addresses_FeatureServer_17` | 30,856 | 30,856 | 0.00% | ok |
| 599 | `s_rest_services_Rural_Addresses__Label_Only__FeatureServer_0` | 30,747 | 30,747 | 0.00% | ok |
| 600 | `_arcgis_rest_services_EnerGov_Test_Map1_WFL1_FeatureServer_3` | 30,649 | 30,649 | 0.00% | ok |
| 601 | `is_rest_services_Lead_Service_Line_Addresses_FeatureServer_0` | 30,565 | 30,565 | 0.00% | ok |
| 602 | `DgvxltnFwP_arcgis_rest_services_NG911_Layers_FeatureServer_1` | 30,273 | 30,273 | 0.00% | ok |
| 603 | `Mk18pL_arcgis_rest_services_Coffee_Addresses_FeatureServer_0` | 29,524 | 29,524 | 0.00% | ok |
| 604 | `xLBcrikqFM0vkoy_arcgis_rest_services_Address_FeatureServer_0` | 29,507 | 29,507 | 0.00% | ok |
| 605 | `4x6y8cTIstSBE_arcgis_rest_services_Addresses_FeatureServer_0` | 29,448 | 29,448 | 0.00% | ok |
| 606 | `TOM4lipn_arcgis_rest_services_Addresses_2023_FeatureServer_0` | 29,170 | 29,170 | 0.00% | ok |
| 607 | `8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1` | 28,996 | 28,996 | 0.00% | ok |
| 608 | `_arcgis_rest_services_Logan_County_Addresses_FeatureServer_0` | 28,571 | 28,571 | 0.00% | ok |
| 609 | `rcgis_rest_services_Bedford_County_Addresses_FeatureServer_0` | 28,352 | 28,352 | 0.00% | ok |
| 610 | `est_services_Street_Sweeping_Pilot_Addresses_FeatureServer_0` | 28,338 | 28,338 | 0.00% | ok |
| 611 | `rest_services_Hurricane_Ian_Damage_Addresses_FeatureServer_0` | 27,912 | 27,912 | 0.00% | ok |
| 612 | `_arcgis_rest_services_TehamaCounty_NG911_gdb_FeatureServer_8` | 27,565 | 27,565 | 0.00% | ok |
| 613 | `ices_City_of_Cuyahoga_Falls_Addressing_WFL1_FeatureServer_11` | 27,479 | 27,479 | 0.00% | ok |
| 614 | `vices_Campbell_County__VA_Broadband_Map_WFL1_FeatureServer_0` | 27,456 | 27,456 | 0.00% | ok |
| 615 | `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0` | 27,213 | 27,213 | 0.00% | ok |
| 616 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0` | 27,058 | 27,058 | 0.00% | ok |
| 617 | `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` | 26,965 | 26,965 | 0.00% | ok |
| 618 | `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0` | 26,903 | 26,903 | 0.00% | ok |
| 619 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0` | 26,684 | 26,684 | 0.00% | ok |
| 620 | `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` | 26,510 | 26,510 | 0.00% | ok |
| 621 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | 26,410 | 52,891 | -100.27% | partial |
| 622 | `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | 26,410 | 52,891 | -100.27% | partial |
| 623 | `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | 26,320 | 52,635 | -99.98% | partial |
| 624 | `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 26,021 | 26,021 | 0.00% | ok |
| 625 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | 25,834 | 51,610 | -99.78% | failed |
| 626 | `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | 25,817 | 51,608 | -99.90% | partial |
| 627 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0` | 25,582 | 25,582 | 0.00% | ok |
| 628 | `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` | 25,427 | 25,427 | 0.00% | ok |
| 629 | `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20` | 25,367 | 25,367 | 0.00% | ok |
| 630 | `HiSnaX0z0hS_arcgis_rest_services_E911HeatMap_FeatureServer_0` | 25,193 | 25,193 | 0.00% | ok |
| 631 | `_net_geo_rest_services_Parcels_AddressPoints_FeatureServer_0` | 25,191 | 25,191 | 0.00% | ok |
| 632 | `o_rest_services_Parcels_AddressPoints_Master_FeatureServer_0` | 25,191 | 25,191 | 0.00% | ok |
| 633 | `L0M_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 25,168 | 25,168 | 0.00% | ok |
| 634 | `rest_services_Auburndale_Address_Points_view_FeatureServer_0` | 25,128 | 25,128 | 0.00% | ok |
| 635 | `cgis_rest_services_Auburndale_Address_Points_FeatureServer_0` | 25,128 | 25,128 | 0.00% | ok |
| 636 | `hOza2U_arcgis_rest_services_Civic_Addresses_FeatureServer_16` | 25,111 | 25,111 | 0.00% | ok |
| 637 | `_arcgis_rest_services_Addresses_GeoLoc_Build_FeatureServer_0` | 25,110 | 25,110 | 0.00% | ok |
| 638 | `9Y0AgX_arcgis_rest_services_ToCAddressPoints_FeatureServer_0` | 25,093 | 25,093 | 0.00% | ok |
| 639 | `AgX_arcgis_rest_services_AddressPoints_iWorQ_FeatureServer_0` | 25,093 | 25,093 | 0.00% | ok |
| 640 | `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | 25,091 | 50,069 | -99.55% | partial |
| 641 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1` | 25,081 | 25,081 | 0.00% | ok |
| 642 | `n_Services_Addresses_Subdivisions_Parcels_ArcPro_MapServer_0` | 25,062 | 25,062 | 0.00% | ok |
| 643 | `gis_rest_services_UTILITY_Hydrants_E911_24r1_FeatureServer_0` | 25,052 | 25,052 | 0.00% | ok |
| 644 | `g4_arcgis_rest_services_Addressing_Resources_FeatureServer_3` | 25,027 | 25,027 | 0.00% | ok |
| 645 | `gis_rest_services_Parcel_and_Address_Service_FeatureServer_0` | 25,010 | 25,010 | 0.00% | ok |
| 646 | `gis_rest_services_Parcels_and_Addresses_2025_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 647 | `Oel_arcgis_rest_services_Address_Points_2025_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 648 | `6Oel_arcgis_rest_services_ParcelBaseWAddress_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 649 | `nPbdNoPBNAJ6Oel_arcgis_rest_services_Address_FeatureServer_5` | 25,009 | 25,009 | 0.00% | ok |
| 650 | `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` | 24,987 | 24,987 | 0.00% | ok |
| 651 | `kHkuW_arcgis_rest_services_GC_Address_Points_FeatureServer_8` | 24,978 | 24,978 | 0.00% | ok |
| 652 | `RDcwL2kQ_arcgis_rest_services_City_Addresses_FeatureServer_0` | 24,890 | 24,890 | 0.00% | ok |
| 653 | `gis_rest_services_Parcel_with_addresses_2024_FeatureServer_0` | 24,885 | 24,885 | 0.00% | ok |
| 654 | `_services_BaseMap_Parcels_Addresses_Boundary_FeatureServer_2` | 24,883 | 24,883 | 0.00% | ok |
| 655 | `is_rest_services_AddressesParcelsUtility2024_FeatureServer_2` | 24,883 | 24,883 | 0.00% | ok |
| 656 | `a8HZMsU25Hzzob3_arcgis_rest_services_Address_FeatureServer_0` | 24,882 | 24,882 | 0.00% | ok |
| 657 | `rvices_Address_Points_for_Parks_and_Rec_2026_FeatureServer_0` | 24,878 | 24,878 | 0.00% | ok |
| 658 | `d_arcgis_rest_services_Miller_Address_Points_FeatureServer_0` | 24,846 | 24,846 | 0.00% | ok |
| 659 | `NEViJGK4M_arcgis_rest_services_911_Addresses_FeatureServer_0` | 24,826 | 24,826 | 0.00% | ok |
| 660 | `11SaUIGBo5JYFY_arcgis_rest_services_SRD_Data_FeatureServer_0` | 24,813 | 24,813 | 0.00% | ok |
| 661 | `I39xWsrNH_arcgis_rest_services_Civic_Address_FeatureServer_0` | 24,790 | 24,790 | 0.00% | ok |
| 662 | `cjDyDh65fslIZ_arcgis_rest_services_Addresses_FeatureServer_0` | 24,762 | 24,762 | 0.00% | ok |
| 663 | `services_Tville_Address_Points_UPDATE_Layer_FeatureServer_23` | 24,713 | 24,713 | 0.00% | ok |
| 664 | `s_rest_services_Address_Points_EnerGov_Only_FeatureServer_24` | 24,709 | 24,709 | 0.00% | ok |
| 665 | `arcgis_rest_services_03242025_Address_Points_FeatureServer_0` | 24,675 | 24,675 | 0.00% | ok |
| 666 | `UUihZ0ky_arcgis_rest_services_Address_Points_FeatureServer_1` | 24,669 | 24,669 | 0.00% | ok |
| 667 | `6rq_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 24,652 | 24,652 | 0.00% | ok |
| 668 | `st_services_Barry_County_NG911_Address_Point_FeatureServer_0` | 24,592 | 24,592 | 0.00% | ok |
| 669 | `ces_AddressPoints_Combined_CivicPlus__ROVIEW_FeatureServer_0` | 24,578 | 24,578 | 0.00% | ok |
| 670 | `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` | 24,529 | 24,529 | 0.00% | ok |
| 671 | `G2jt9_arcgis_rest_services_AddressPointsvw1_FeatureServer_10` | 24,520 | 24,520 | 0.00% | ok |
| 672 | `5CWG2jt9_arcgis_rest_services_AddressPoints_FeatureServer_10` | 24,520 | 24,520 | 0.00% | ok |
| 673 | `hwao8WvM_arcgis_rest_services_Address_Points_FeatureServer_0` | 24,483 | 24,483 | 0.00% | ok |
| 674 | `_services_Address_Points_TEST_from_shapefile_FeatureServer_0` | 24,483 | 24,483 | 0.00% | ok |
| 675 | `S9g_arcgis_rest_services_View_Address_Points_FeatureServer_0` | 24,477 | 24,477 | 0.00% | ok |
| 676 | `arcgis_rest_services_Site_Address_Points_WFS_FeatureServer_0` | 24,475 | 24,475 | 0.00% | ok |
| 677 | `rcgis_rest_services_Site_Address_Points_0716_FeatureServer_1` | 24,474 | 24,474 | 0.00% | ok |
| 678 | `a_ca_us_arcgis_rest_services_Basemap_Parcels_AGO_MapServer_0` | 24,468 | 24,468 | 0.00% | ok |
| 679 | `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0` | 24,465 | 24,465 | 0.00% | ok |
| 680 | `es_GeneralPurpose_SiteAddressPoints_JUNE2023_FeatureServer_1` | 24,413 | 24,413 | 0.00% | ok |
| 681 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0` | 24,398 | 24,398 | 0.00% | ok |
| 682 | `lumet_wi_us_server_rest_services_ParcelsService_MapServer_11` | 24,299 | 24,299 | 0.00% | ok |
| 683 | `BtvXuiLQ_arcgis_rest_services_Addresses_view_FeatureServer_2` | 24,235 | 24,235 | 0.00% | ok |
| 684 | `s_InternalANDPublicMaps_Churches_and_Cemeteries_MapServer_10` | 24,210 | 24,210 | 0.00% | ok |
| 685 | `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` | 24,136 | 24,136 | 0.00% | ok |
| 686 | `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0` | 24,123 | 24,123 | 0.00% | ok |
| 687 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0` | 24,109 | 24,109 | 0.00% | ok |
| 688 | `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` | 24,107 | 24,107 | 0.00% | ok |
| 689 | `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0` | 24,045 | 24,045 | 0.00% | ok |
| 690 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0` | 23,950 | 23,950 | 0.00% | ok |
| 691 | `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | 23,869 | 47,732 | -99.97% | partial |
| 692 | `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54` | 23,859 | 23,859 | 0.00% | ok |
| 693 | `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | 23,819 | 47,237 | -98.32% | partial |
| 694 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | 23,776 | 47,553 | -100.00% | partial |
| 695 | `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | 23,338 | 46,672 | -99.98% | partial |
| 696 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | 11.51% | failed |
| 697 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | 11.51% | failed |
| 698 | `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0` | 23,141 | 23,141 | 0.00% | ok |
| 699 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0` | 23,136 | 23,136 | 0.00% | ok |
| 700 | `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` | 23,106 | 23,106 | 0.00% | ok |
| 701 | `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0` | 22,930 | 22,930 | 0.00% | ok |
| 702 | `_services_Civic_Address_Points_5_view_simple_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 703 | `is_rest_services_Civic_Address_Points_View_2_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 704 | `cgis_rest_services_Civic_Address_Points_View_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 705 | `cgis_rest_services_BranchCountyAddressPoints_FeatureServer_0` | 22,344 | 22,344 | 0.00% | ok |
| 706 | `Z_arcgis_rest_services_NG911_SSAP_Web_Viewer_FeatureServer_0` | 22,337 | 22,337 | 0.00% | ok |
| 707 | `arcgis_rest_services_Address_Points_centrvle_FeatureServer_0` | 22,325 | 22,325 | 0.00% | ok |
| 708 | `cdc81CEBk_arcgis_rest_services_AddressPoints_FeatureServer_0` | 22,308 | 22,308 | 0.00% | ok |
| 709 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 710 | `fpWcwy7h_arcgis_rest_services_Address_Points_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 711 | `RaKduZ9Wo_arcgis_rest_services_AddressPoints_FeatureServer_0` | 22,273 | 22,273 | 0.00% | ok |
| 712 | `v_server_rest_services_AGOL_AGOL_INDV_AddrPoints_MapServer_0` | 22,258 | 22,258 | 0.00% | ok |
| 713 | `rcgis_rest_services_Address_Points_Open_Data_FeatureServer_0@未定位-1` | 22,257 | 22,257 | 0.00% | ok |
| 714 | `3u_arcgis_rest_services_Address_NonCollector_FeatureServer_0` | 22,257 | 22,257 | 0.00% | ok |
| 715 | `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 22,248 | 44,495 | -100.00% | partial |
| 716 | `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0` | 22,208 | 22,208 | 0.00% | ok |
| 717 | `is_rest_services_Public_Notification_Address_FeatureServer_0` | 22,188 | 22,188 | 0.00% | ok |
| 718 | `v_arcgis_rest_services_Newnan_Address_Points_FeatureServer_0` | 22,152 | 22,152 | 0.00% | ok |
| 719 | `est_services_Address_Points_Within_Gilleland_FeatureServer_0` | 22,151 | 22,151 | 0.00% | ok |
| 720 | `st_services_Address_Points_Within_Gilleland2_FeatureServer_0` | 22,151 | 22,151 | 0.00% | ok |
| 721 | `QoXoOXkk_arcgis_rest_services_Address_Points_FeatureServer_0` | 22,140 | 22,140 | 0.00% | ok |
| 722 | `msX_arcgis_rest_services_JoplinAddressPoints_FeatureServer_0` | 22,113 | 22,113 | 0.00% | ok |
| 723 | `eUxQY5fQy_arcgis_rest_services_Address_view_FeatureServer_40` | 22,109 | 22,109 | 0.00% | ok |
| 724 | `6ZLWUVjA_arcgis_rest_services_Address_Points_FeatureServer_1` | 22,099 | 22,099 | 0.00% | ok |
| 725 | `JUmf_arcgis_rest_services_NG911AddressPoints_FeatureServer_1` | 22,032 | 22,032 | 0.00% | ok |
| 726 | `vZ_arcgis_rest_services_AddressPoints_081723_FeatureServer_0` | 22,011 | 22,011 | 0.00% | ok |
| 727 | `arcgis_rest_services_tuckeraddresspointLayer_FeatureServer_0` | 21,987 | 21,987 | 0.00% | ok |
| 728 | `EQWYJHMZp_arcgis_rest_services_SITE_ADDRESS_FeatureServer_13` | 21,979 | 21,979 | 0.00% | ok |
| 729 | `NAnn8lip_arcgis_rest_services_Cadastral_PRD_FeatureServer_29` | 21,965 | 21,965 | 0.00% | ok |
| 730 | `p_arcgis_rest_services_Election_Site_Address_FeatureServer_0` | 21,953 | 21,953 | 0.00% | ok |
| 731 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0` | 21,951 | 21,951 | 0.00% | ok |
| 732 | `z0S_arcgis_rest_services_Address_Point_base_FeatureServer_70` | 21,909 | 21,909 | 0.00% | ok |
| 733 | `rcgis_rest_services_Address_Point_base_view_FeatureServer_70` | 21,909 | 21,909 | 0.00% | ok |
| 734 | `Utd_arcgis_rest_services_Civic_Address__od_FeatureServer_152` | 21,900 | 21,900 | 0.00% | ok |
| 735 | `ONZ3C_arcgis_rest_services_Site_Address_View_FeatureServer_0` | 21,898 | 21,898 | 0.00% | ok |
| 736 | `is_rest_services_GIS_AddressPoint_HALVOTEMAP_FeatureServer_0` | 21,837 | 21,837 | 0.00% | ok |
| 737 | `SVDsGFwm_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,813 | 21,813 | 0.00% | ok |
| 738 | `rvices_Siskiyou_County_Public_Address_Points_FeatureServer_0` | 21,794 | 21,794 | 0.00% | ok |
| 739 | `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` | 21,789 | 21,789 | 0.00% | ok |
| 740 | `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | 21,770 | 43,524 | -99.93% | partial |
| 741 | `uxM_arcgis_rest_services_NG911AddressPoints_FeatureServer_13` | 21,764 | 21,764 | 0.00% | ok |
| 742 | `2hyb0Af_arcgis_rest_services_Address_Parcels_FeatureServer_0` | 21,753 | 21,753 | 0.00% | ok |
| 743 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | 21,721 | 21,721 | 0.00% | ok |
| 744 | `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` | 21,706 | 21,706 | 0.00% | ok |
| 745 | `h7e_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 21,694 | 21,694 | 0.00% | ok |
| 746 | `_arcgis_rest_services_SiteAddressPoints_soma_FeatureServer_0` | 21,690 | 21,690 | 0.00% | ok |
| 747 | `VL7iicQLS_arcgis_rest_services_Address_BC911_FeatureServer_0` | 21,676 | 21,676 | 0.00% | ok |
| 748 | `F7Wwkv9D_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,658 | 21,658 | 0.00% | ok |
| 749 | `IQDOsXnGaTxj2_arcgis_rest_services_Addresses_FeatureServer_0` | 21,636 | 21,636 | 0.00% | ok |
| 750 | `z0S_arcgis_rest_services_Address_Point_view_FeatureServer_17` | 21,601 | 21,601 | 0.00% | ok |
| 751 | `4QpdcTJ9_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,597 | 21,597 | 0.00% | ok |
| 752 | `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 753 | `G2Q2tuit_arcgis_rest_services_Addresses_view_FeatureServer_4` | 21,594 | 21,594 | 0.00% | ok |
| 754 | `w5aLHpzj_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 755 | `tb5ipmv9_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,584 | 21,584 | 0.00% | ok |
| 756 | `cTJ9_arcgis_rest_services_street_address_new_FeatureServer_0` | 21,571 | 21,571 | 0.00% | ok |
| 757 | `t_services_HostedService_LakeWorthBeachSitus_FeatureServer_0` | 21,556 | 21,556 | 0.00% | ok |
| 758 | `_rest_services_Greenbrier_Addressing_Service_FeatureServer_0` | 21,547 | 21,547 | 0.00% | ok |
| 759 | `W9v2gSO7_arcgis_rest_services_Address_Points_FeatureServer_4` | 21,490 | 21,490 | 0.00% | ok |
| 760 | `lYKSnzjiOzQig_arcgis_rest_services_Addresses_FeatureServer_1` | 21,419 | 21,419 | 0.00% | ok |
| 761 | `rr0NFJXS_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,415 | 21,415 | 0.00% | ok |
| 762 | `Q1Yngrdc_arcgis_rest_services_Addresses1115_FeatureServer_46` | 21,395 | 21,395 | 0.00% | ok |
| 763 | `yFxn_arcgis_rest_services_AddressPoints5Mile_FeatureServer_0` | 21,385 | 21,385 | 0.00% | ok |
| 764 | `mzqLyRabS_arcgis_rest_services_addresspoints_FeatureServer_0` | 21,385 | 21,385 | 0.00% | ok |
| 765 | `st_services_HostedService_SitusAddressPoints_FeatureServer_0` | 21,361 | 21,361 | 0.00% | ok |
| 766 | `ZLzs7d68_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,318 | 21,318 | 0.00% | ok |
| 767 | `t_services_Yadkin_County_Addresses_Read_Only_FeatureServer_0` | 21,299 | 21,299 | 0.00% | ok |
| 768 | `rest_services_Bettendorf_Address_Points_View_FeatureServer_0` | 21,284 | 21,284 | 0.00% | ok |
| 769 | `_rest_services_Homestead_2023_Address_Points_FeatureServer_0` | 21,275 | 21,275 | 0.00% | ok |
| 770 | `_rest_services_Address_Points_with_Elevation_FeatureServer_0` | 21,218 | 21,218 | 0.00% | ok |
| 771 | `_com_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 21,217 | 21,217 | 0.00% | ok |
| 772 | `Qw11Lg0Zm_arcgis_rest_services_AuroraBasemap_FeatureServer_0` | 21,215 | 21,215 | 0.00% | ok |
| 773 | `arcgis_rest_services_City_of_Hobbs_Addresses_FeatureServer_0` | 21,154 | 21,154 | 0.00% | ok |
| 774 | `729Bn31m_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,153 | 21,153 | 0.00% | ok |
| 775 | `Fvge6E_arcgis_rest_services_Address_Services_FeatureServer_0` | 21,131 | 21,131 | 0.00% | ok |
| 776 | `SYGuYov4_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,117 | 21,117 | 0.00% | ok |
| 777 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0` | 21,108 | 21,108 | 0.00% | ok |
| 778 | `ervices_DeltaCountyAddressPoints2025_Jan2025_FeatureServer_0` | 21,107 | 21,107 | 0.00% | ok |
| 779 | `blkssRx_arcgis_rest_services_Address_Points_FeatureServer_24` | 21,103 | 21,103 | 0.00% | ok |
| 780 | `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` | 21,092 | 21,092 | 0.00% | ok |
| 781 | `t_services_Peachtree_Corners_Address_Points_FeatureServer_14` | 21,065 | 21,065 | 0.00% | ok |
| 782 | `arcgis_rest_services_Master_Address_List_New_FeatureServer_0` | 21,055 | 21,055 | 0.00% | ok |
| 783 | `_rest_services_SiteStructureAddressPoint_utm_FeatureServer_0` | 21,018 | 21,018 | 0.00% | ok |
| 784 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0` | 21,006 | 21,006 | 0.00% | ok |
| 785 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-5` | 20,977 | 20,977 | 0.00% | ok |
| 786 | `P7ekrLYcX5SF2z_arcgis_rest_services_COA_SSAP_FeatureServer_2` | 20,976 | 20,976 | 0.00% | ok |
| 787 | `est_services_City_of_Delaware_Address_Points_FeatureServer_0` | 20,965 | 20,965 | 0.00% | ok |
| 788 | `I7tkz4N_arcgis_rest_services_Address_Point_FeatureServer_105` | 20,937 | 20,937 | 0.00% | ok |
| 789 | `ington_Address_Points_for_Tyler_Technologies_FeatureServer_0` | 20,923 | 20,923 | 0.00% | ok |
| 790 | `za1rSdynU_arcgis_rest_services_AddressPoints_FeatureServer_0` | 20,906 | 20,906 | 0.00% | ok |
| 791 | `wdApEp_arcgis_rest_services_Lander_addresses_FeatureServer_0` | 20,894 | 20,894 | 0.00% | ok |
| 792 | `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` | 20,861 | 20,861 | 0.00% | ok |
| 793 | `Kvz6SRPFWJ_arcgis_rest_services_Address_view_FeatureServer_8` | 20,857 | 20,857 | 0.00% | ok |
| 794 | `kyZtgsuWoNVtB_arcgis_rest_services_Addresses_FeatureServer_0` | 20,813 | 20,813 | 0.00% | ok |
| 795 | `is_rest_services_Redford_Address_Point_Layer_FeatureServer_0` | 20,784 | 20,784 | 0.00% | ok |
| 796 | `rcgis_rest_services_Address_Points_for_Hazus_FeatureServer_0` | 20,775 | 20,775 | 0.00% | ok |
| 797 | `gsuWoNVtB_arcgis_rest_services_Addresses2026_FeatureServer_0` | 20,770 | 20,770 | 0.00% | ok |
| 798 | `_services_AddressPoints_Placentia_July_2026_FeatureServer_16` | 20,737 | 20,737 | 0.00% | ok |
| 799 | `aN8Dr8M_arcgis_rest_services_AddressPoints23_FeatureServer_0` | 20,710 | 20,710 | 0.00% | ok |
| 800 | `s_rest_services_AddressPoints_Placentia_New2_FeatureServer_0` | 20,710 | 20,710 | 0.00% | ok |
| 801 | `rcgis_rest_services_Address_Points_CityView_FeatureServer_34` | 20,709 | 20,709 | 0.00% | ok |
| 802 | `3XOR63A7_arcgis_rest_services_AddressPoints_FeatureServer_34` | 20,709 | 20,709 | 0.00% | ok |
| 803 | `7aN8Dr8M_arcgis_rest_services_Address_Points_FeatureServer_0` | 20,701 | 20,701 | 0.00% | ok |
| 804 | `cgis_rest_services_BeltramiData_BeltramiOpenData_MapServer_0` | 20,671 | 20,671 | 0.00% | ok |
| 805 | `aJipPNFR_arcgis_rest_services_Address_Points_FeatureServer_0` | 20,666 | 20,666 | 0.00% | ok |
| 806 | `VVOdnGdbq_arcgis_rest_services_AddressPoints_FeatureServer_1` | 20,661 | 20,661 | 0.00% | ok |
| 807 | `3lusZ_arcgis_rest_services_CRB_Address_Point_FeatureServer_0` | 20,628 | 20,628 | 0.00% | ok |
| 808 | `V3Stz_arcgis_rest_services_EverettAddressPts_FeatureServer_0` | 20,596 | 20,596 | 0.00% | ok |
| 809 | `lOmSY_arcgis_rest_services_Address_PointsNEW_FeatureServer_0` | 20,587 | 20,587 | 0.00% | ok |
| 810 | `_services_Holyoke_AddressPointsMassGIS_52824_FeatureServer_0` | 20,517 | 20,517 | 0.00% | ok |
| 811 | `s_rest_services_HolyokeAddressPoints_MassGIS_FeatureServer_0` | 20,517 | 20,517 | 0.00% | ok |
| 812 | `Gw9ZnifOd3v8l_arcgis_rest_services_Addresses_FeatureServer_0` | 20,478 | 20,478 | 0.00% | ok |
| 813 | `arcgis_rest_services_AddressPoints_Placentia_FeatureServer_3` | 20,477 | 20,477 | 0.00% | ok |
| 814 | `Txj2_arcgis_rest_services_Driveway_Addresses_FeatureServer_0` | 20,456 | 20,456 | 0.00% | ok |
| 815 | `_arcgis_rest_services_AlexanderAddressPoints_FeatureServer_0` | 20,445 | 20,445 | 0.00% | ok |
| 816 | `ySt_arcgis_rest_services_Addresses_Structure_FeatureServer_2` | 20,437 | 20,437 | 0.00% | ok |
| 817 | `ry3ySt_arcgis_rest_services_Addresses_Road_FeatureServer_156` | 20,437 | 20,437 | 0.00% | ok |
| 818 | `acon_Address_Points_with_Availibility_050223_FeatureServer_0` | 20,437 | 20,437 | 0.00% | ok |
| 819 | `C9UDiTgJU_arcgis_rest_services_Address_Point_FeatureServer_0` | 20,402 | 20,402 | 0.00% | ok |
| 820 | `cgis_rest_services_AddressesWithElectionData_FeatureServer_0` | 20,202 | 20,202 | 0.00% | ok |
| 821 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1` | 20,088 | 20,088 | 0.00% | ok |
| 822 | `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | 20,040 | 40,080 | -100.00% | partial |
| 823 | `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0` | 20,014 | 20,014 | 0.00% | ok |
| 824 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0` | 19,966 | 19,966 | 0.00% | ok |
| 825 | `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` | 19,812 | 19,812 | 0.00% | ok |
| 826 | `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0` | 19,767 | 19,767 | 0.00% | ok |
| 827 | `jqaQHXGlt_arcgis_rest_services_AddressPoints_FeatureServer_0` | 19,634 | 19,634 | 0.00% | ok |
| 828 | `ervices_fulton_911_Online_address_publicview_FeatureServer_0` | 19,633 | 19,633 | 0.00% | ok |
| 829 | `rqC55zVw_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,611 | 19,611 | 0.00% | ok |
| 830 | `IEW_Addresses_NG911_Structure_Current_Active_FeatureServer_2` | 19,605 | 19,605 | 0.00% | ok |
| 831 | `_arcgis_rest_services_BrownE911AddressPoints_FeatureServer_0` | 19,577 | 19,577 | 0.00% | ok |
| 832 | `18b4b78b270efb1_rest_services_Accela_Accela_FeatureServer_79` | 19,544 | 19,544 | 0.00% | ok |
| 833 | `c71b3d4712db5c4e6a2_rest_services_Accela_Accela_MapServer_79` | 19,544 | 19,544 | 0.00% | ok |
| 834 | `rvices_Services_Public_Address_Points_Public_FeatureServer_0` | 19,527 | 19,527 | 0.00% | ok |
| 835 | `JJatlcMHWR_arcgis_rest_services_Address_View_FeatureServer_0` | 19,482 | 19,482 | 0.00% | ok |
| 836 | `gov_arcgis_rest_services_OpenData_Administrative_MapServer_1` | 19,464 | 19,464 | 0.00% | ok |
| 837 | `kj484GNt_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,439 | 19,439 | 0.00% | ok |
| 838 | `ppWGZsn5o_arcgis_rest_services_AddressPoints_FeatureServer_0` | 19,396 | 19,396 | 0.00% | ok |
| 839 | `_rest_services_Hopkins_County_Address_Points_FeatureServer_0` | 19,360 | 19,360 | 0.00% | ok |
| 840 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0` | 19,339 | 19,339 | 0.00% | ok |
| 841 | `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` | 19,308 | 19,308 | 0.00% | ok |
| 842 | `st_services_Parcel_and_Addresses_Layers_WFL1_FeatureServer_3` | 19,248 | 19,248 | 0.00% | ok |
| 843 | `bGN_arcgis_rest_services_AddressPoint_DeSoto_FeatureServer_0` | 19,236 | 19,236 | 0.00% | ok |
| 844 | `rcgis_rest_services_AddressPoint_DeSoto_view_FeatureServer_0` | 19,223 | 19,223 | 0.00% | ok |
| 845 | `8hGa1_arcgis_rest_services_Opelika_Addresses_FeatureServer_0` | 19,209 | 19,209 | 0.00% | ok |
| 846 | `VDElDOMEad_arcgis_rest_services_Ohio_Address_FeatureServer_1` | 19,186 | 19,186 | 0.00% | ok |
| 847 | `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | 19,161 | 38,284 | -99.80% | partial |
| 848 | `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0` | 19,154 | 19,154 | 0.00% | ok |
| 849 | `EGe_arcgis_rest_services_City_Address_Points_FeatureServer_0` | 19,144 | 19,144 | 0.00% | ok |
| 850 | `st_services_Heritage_Register_Address_Points_FeatureServer_0` | 19,132 | 19,132 | 0.00% | ok |
| 851 | `tFEGe_arcgis_rest_services_CityAddressPoints_FeatureServer_0` | 19,130 | 19,130 | 0.00% | ok |
| 852 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0` | 19,123 | 19,123 | 0.00% | ok |
| 853 | `nwcwJe4b_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,101 | 19,101 | 0.00% | ok |
| 854 | `rcgis_rest_services_Homestead_Address_Points_FeatureServer_1` | 19,071 | 19,071 | 0.00% | ok |
| 855 | `is_rest_services_Gloucester_County_Addresses_FeatureServer_0` | 19,037 | 19,037 | 0.00% | ok |
| 856 | `eA2I8MDz_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,023 | 19,023 | 0.00% | ok |
| 857 | `n5o_arcgis_rest_services_AddressPts_3Oct2022_FeatureServer_0` | 19,015 | 19,015 | 0.00% | ok |
| 858 | `iSnaX0z0hS_arcgis_rest_services_MarionMSE911_FeatureServer_0` | 19,007 | 19,007 | 0.00% | ok |
| 859 | `RCn_arcgis_rest_services_brtn_address_points_FeatureServer_0` | 18,998 | 18,998 | 0.00% | ok |
| 860 | `Uw8wmJxSAcUEU_arcgis_rest_services_Addresses_FeatureServer_0` | 18,927 | 18,927 | 0.00% | ok |
| 861 | `_arcgis_rest_services_Hydrants_Address_Flood_FeatureServer_0` | 18,870 | 18,870 | 0.00% | ok |
| 862 | `K_arcgis_rest_services_masteraddresslocator_FeatureServer_21` | 18,858 | 18,858 | 0.00% | ok |
| 863 | `K_arcgis_rest_services_Master_Address_Table_FeatureServer_21` | 18,855 | 18,855 | 0.00% | ok |
| 864 | `BdHIlQ88_arcgis_rest_services_address_points_FeatureServer_0` | 18,850 | 18,850 | 0.00% | ok |
| 865 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0` | 18,822 | 18,822 | 0.00% | ok |
| 866 | `_org_arcgis_rest_services_Property_Addresses_FeatureServer_0` | 18,819 | 18,819 | 0.00% | ok |
| 867 | `_arcgis_rest_services_brtn_address_pointsNEW_FeatureServer_0` | 18,801 | 18,801 | 0.00% | ok |
| 868 | `arcgis_rest_services_City_of_Hutto_Addresses_FeatureServer_5` | 18,798 | 18,798 | 0.00% | ok |
| 869 | `tzEvlHpA_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,771 | 18,771 | 0.00% | ok |
| 870 | `t_services_Addresses_City_of_Laurinburg_view_FeatureServer_0` | 18,770 | 18,770 | 0.00% | ok |
| 871 | `Kfts6TQD_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,754 | 18,754 | 0.00% | ok |
| 872 | `SG_arcgis_rest_services_STJFD_Address_Points_FeatureServer_0` | 18,752 | 18,752 | 0.00% | ok |
| 873 | `s_rest_services_Addresses_BristolTN_SmartGov_FeatureServer_0` | 18,749 | 18,749 | 0.00% | ok |
| 874 | `rvices_NG911_Addresses_and_Roads_Public_View_FeatureServer_0` | 18,717 | 18,717 | 0.00% | ok |
| 875 | `cgis_rest_services_NG911_Addresses_and_Roads_FeatureServer_0` | 18,717 | 18,717 | 0.00% | ok |
| 876 | `arcgis_rest_services_Elm_Ridge_D10_Addresses_FeatureServer_0` | 18,716 | 18,716 | 0.00% | ok |
| 877 | `5SYpBlXQGJEB_arcgis_rest_services_AddressPts_FeatureServer_0` | 18,691 | 18,691 | 0.00% | ok |
| 878 | `arcgis_rest_services_Kennesaw_Address_Points_FeatureServer_0` | 18,686 | 18,686 | 0.00% | ok |
| 879 | `cgis_rest_services_Address_Points_Public_App_FeatureServer_0` | 18,676 | 18,676 | 0.00% | ok |
| 880 | `cOAaTE5R_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,676 | 18,676 | 0.00% | ok |
| 881 | `st_services_Sex_Offender_Ordinance_Addresses_FeatureServer_0` | 18,584 | 18,584 | 0.00% | ok |
| 882 | `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | 18,526 | 37,031 | -99.89% | partial |
| 883 | `i1rmDSHF_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_0` | 18,524 | 18,524 | 0.00% | ok |
| 884 | `y7JDhk1zQOJdo_arcgis_rest_services_Addresses_FeatureServer_0` | 18,517 | 18,517 | 0.00% | ok |
| 885 | `cgis_rest_services_County_AddressPoints_2025_FeatureServer_0` | 18,503 | 18,503 | 0.00% | ok |
| 886 | `rqLn_arcgis_rest_services_Site_Address_Point_FeatureServer_0` | 18,451 | 18,451 | 0.00% | ok |
| 887 | `Ki1rmDSHF_arcgis_rest_services_Address_Label_FeatureServer_0` | 18,451 | 18,451 | 0.00% | ok |
| 888 | `ezuma_co_us_arcgis_rest_services_OpenDataMap_FeatureServer_6` | 18,431 | 18,431 | 0.00% | ok |
| 889 | `gis_rest_services_County_Address_Points_2022_FeatureServer_0` | 18,423 | 18,423 | 0.00% | ok |
| 890 | `TEJ0Ki1rmDSHF_arcgis_rest_services_Addresses_FeatureServer_0` | 18,415 | 18,415 | 0.00% | ok |
| 891 | `i_arcgis_rest_services_Cass_Address_Points_FeatureServer_155` | 18,376 | 18,376 | 0.00% | ok |
| 892 | `gis_rest_services_Stouffville_Address_Points_FeatureServer_0` | 18,375 | 18,375 | 0.00% | ok |
| 893 | `est_services_AddressPointsRevised08292024_FC_FeatureServer_0` | 18,370 | 18,370 | 0.00% | ok |
| 894 | `ACHwgXJb_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,356 | 18,356 | 0.00% | ok |
| 895 | `3M1O_arcgis_rest_services_RSM_Address_Points_FeatureServer_0` | 18,324 | 18,324 | 0.00% | ok |
| 896 | `cgis_rest_services_Address_Number_Annotation_FeatureServer_4` | 18,300 | 18,300 | 0.00% | ok |
| 897 | `fBoQUIwDx_arcgis_rest_services_Address_Point_FeatureServer_4` | 18,292 | 18,292 | 0.00% | ok |
| 898 | `ervices_City_of_Friendswood___Address_Points_FeatureServer_2` | 18,288 | 18,288 | 0.00% | ok |
| 899 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@VA-2` | 18,275 | 18,275 | 0.00% | ok |
| 900 | `e_arcgis_rest_services_County_Address_Points_FeatureServer_0` | 18,257 | 18,257 | 0.00% | ok |
| 901 | `city_ca_arcgis_rest_services_Public_OpenData_FeatureServer_0` | 18,254 | 18,254 | 0.00% | ok |
| 902 | `ty_ca_arcgis_rest_services_Public_AGOLDataLayers_MapServer_1` | 18,252 | 18,252 | 0.00% | ok |
| 903 | `arcgis_rest_services_OpenData_Address_Points_FeatureServer_0` | 18,174 | 18,174 | 0.00% | ok |
| 904 | `rcgis_rest_services_Municipal_Address_Points_FeatureServer_0` | 18,146 | 18,146 | 0.00% | ok |
| 905 | `est_services_Addressing_AddressPoints_Public_FeatureServer_0` | 18,134 | 18,134 | 0.00% | ok |
| 906 | `DjI19VqyUMCS1_arcgis_rest_services_Addresses_FeatureServer_1` | 18,121 | 18,121 | 0.00% | ok |
| 907 | `Gyx40MXP_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,007 | 18,007 | 0.00% | ok |
| 908 | `gis_rest_services_MSWD_Address_Points_Public_FeatureServer_1` | 17,972 | 17,972 | 0.00% | ok |
| 909 | `gis_rest_services_AddressPoints__public_view_FeatureServer_0` | 17,959 | 17,959 | 0.00% | ok |
| 910 | `s_rest_services_Master_Address_Database_view_FeatureServer_0` | 17,922 | 17,922 | 0.00% | ok |
| 911 | `s_rest_services_UA_LBRS_Address_Points_Layer_FeatureServer_0` | 17,914 | 17,914 | 0.00% | ok |
| 912 | `1fngp5cVBlk_arcgis_rest_services_SiteAddress_FeatureServer_0` | 17,914 | 17,914 | 0.00% | ok |
| 913 | `d0ZV_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 17,908 | 17,908 | 0.00% | ok |
| 914 | `r4_arcgis_rest_services_Addresses_30Dec2025_FeatureServer_14` | 17,898 | 17,898 | 0.00% | ok |
| 915 | `eGkGuRiFia_arcgis_rest_services_E911_Address_FeatureServer_1` | 17,871 | 17,871 | 0.00% | ok |
| 916 | `HA6Vis6l_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,859 | 17,859 | 0.00% | ok |
| 917 | `s_PARCEL2016_17_CENTROIDS_FOR_ADDRESS_POINTS_FeatureServer_0` | 17,812 | 17,812 | 0.00% | ok |
| 918 | `ervices_Braintree_Master_Address_Points_View_FeatureServer_0` | 17,794 | 17,794 | 0.00% | ok |
| 919 | `rest_services_Lakewood_Address_Points_032626_FeatureServer_1` | 17,765 | 17,765 | 0.00% | ok |
| 920 | `rvices_Address_Points_Riverton_Non_Sensitive_FeatureServer_0` | 17,761 | 17,761 | 0.00% | ok |
| 921 | `vices_Address_Points_Parcels_Storm_Fee_Areas_FeatureServer_3` | 17,761 | 17,761 | 0.00% | ok |
| 922 | `is_rest_services_Address_Point_and_Parcel_EH_FeatureServer_1` | 17,761 | 17,761 | 0.00% | ok |
| 923 | `a8zFF_arcgis_rest_services_Address_Locations_FeatureServer_0` | 17,753 | 17,753 | 0.00% | ok |
| 924 | `VXXqAFAr_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,752 | 17,752 | 0.00% | ok |
| 925 | `_arcgis_rest_services_Homestead_2024_Address_FeatureServer_0` | 17,744 | 17,744 | 0.00% | ok |
| 926 | `is_rest_services_Douglasville_Address_Points_FeatureServer_0` | 17,724 | 17,724 | 0.00% | ok |
| 927 | `st_services_Elgin_ISD_2025_26_Address_Points_FeatureServer_0` | 17,701 | 17,701 | 0.00% | ok |
| 928 | `vAo6IVI7r_arcgis_rest_services_AddressPoints_FeatureServer_0` | 17,700 | 17,700 | 0.00% | ok |
| 929 | `zX_arcgis_rest_services_Boone_Address_Points_FeatureServer_1` | 17,699 | 17,699 | 0.00% | ok |
| 930 | `YSp_arcgis_rest_services_Address_type_points_FeatureServer_0` | 17,698 | 17,698 | 0.00% | ok |
| 931 | `is_rest_services_ames_basemap_ALL_read_only_V2_MapServer_218` | 17,673 | 17,673 | 0.00% | ok |
| 932 | `OMEad_arcgis_rest_services_AddressRegionV_FZ_FeatureServer_0` | 17,672 | 17,672 | 0.00% | ok |
| 933 | `ervices_Langeberg_Street_Addresses__Public_FeatureServer_139` | 17,609 | 17,609 | 0.00% | ok |
| 934 | `ty_of_Friendswood__Open_Data__Address_Points_FeatureServer_2` | 17,600 | 17,600 | 0.00% | ok |
| 935 | `es_Addresses_Buildings_VacantParcels_Feb2025_FeatureServer_0` | 17,600 | 17,600 | 0.00% | ok |
| 936 | `iiR8VBXvcO_arcgis_rest_services_Site_Address_FeatureServer_0` | 17,568 | 17,568 | 0.00% | ok |
| 937 | `_services_us_mn_co_aitkin_loc_address_points_FeatureServer_0@未定位-1` | 17,533 | 17,533 | 0.00% | ok |
| 938 | `_rest_services_K_WS_Situs_ADD_SDE_2024_05_30_FeatureServer_0` | 17,519 | 17,519 | 0.00% | ok |
| 939 | `is_rest_services_WS_Situs_ADD_SDE_2024_05_30_FeatureServer_0` | 17,519 | 17,519 | 0.00% | ok |
| 940 | `teAddressPoints_OnlyUnionCounty_February2020_FeatureServer_0` | 17,510 | 17,510 | 0.00% | ok |
| 941 | `9s04rg0sr_arcgis_rest_services_AddressPoints_FeatureServer_0` | 17,490 | 17,490 | 0.00% | ok |
| 942 | `rcGIS_rest_services_Site_Address_Points_View_FeatureServer_0` | 17,483 | 17,483 | 0.00% | ok |
| 943 | `arcgis_rest_services_Longview_Address_Update_FeatureServer_0` | 17,479 | 17,479 | 0.00% | ok |
| 944 | `lkwfCfBjSM_arcgis_rest_services_AddressPoint_FeatureServer_0` | 17,462 | 17,462 | 0.00% | ok |
| 945 | `rcgis_rest_services_Address_Points_Only_WFL1_FeatureServer_0` | 17,440 | 17,440 | 0.00% | ok |
| 946 | `2hTY7c_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 17,419 | 17,419 | 0.00% | ok |
| 947 | `ZsZ6el3f_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,397 | 17,397 | 0.00% | ok |
| 948 | `eyGEfuc_arcgis_rest_services_MorganAddresses_FeatureServer_0` | 17,389 | 17,389 | 0.00% | ok |
| 949 | `x_arcgis_rest_services_Anna_Base_Data_Viewer_FeatureServer_3` | 17,383 | 17,383 | 0.00% | ok |
| 950 | `_rest_services_GrotonParcelsAndAddressPoints_FeatureServer_0` | 17,375 | 17,375 | 0.00% | ok |
| 951 | `rest_services_Morgan_Address_Points_Geocoded_FeatureServer_0` | 17,311 | 17,311 | 0.00% | ok |
| 952 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 17,295 | 17,270 | 0.14% | failed |
| 953 | `ces_City_of_Friendswood_Addresses_for_Voting_FeatureServer_2` | 17,294 | 17,294 | 0.00% | ok |
| 954 | `vices_PublicServices_Public_Features_Group_1_FeatureServer_9` | 17,264 | 17,264 | 0.00% | ok |
| 955 | `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | 16,730 | 0 | 100.00% | failed |
| 956 | `st_services_Waste_Pro_Pickup_Days_Addresses_FeatureServer_36` | 16,234 | 16,234 | 0.00% | ok |
| 957 | `CS7Cz_arcgis_rest_services_Edmo911_Addresses_FeatureServer_0` | 15,870 | 15,870 | 0.00% | ok |
| 958 | `t_services_AddressPoints_forSANITARYSEWERAPP_FeatureServer_0` | 15,846 | 15,846 | 0.00% | ok |
| 959 | `7ccd0413_rest_services_Hosted_Address_Points_FeatureServer_0` | 15,838 | 15,838 | 0.00% | ok |
| 960 | `_rest_services_YanceyCountySiteAddressPoints_FeatureServer_0` | 15,772 | 15,772 | 0.00% | ok |
| 961 | `_ca_server_rest_services_OpenData_OpenData_Land_MapServer_10` | 15,764 | 15,764 | 0.00% | ok |
| 962 | `9Lu_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 15,741 | 15,741 | 0.00% | ok |
| 963 | `jTwPS9Lu_arcgis_rest_services_Address_Points_FeatureServer_0` | 15,741 | 15,741 | 0.00% | ok |
| 964 | `ygis_rest_services_Public_PowHUB_Landbase_Layers_MapServer_1` | 15,738 | 15,738 | 0.00% | ok |
| 965 | `whGYUH0pL_arcgis_rest_services_AddressPoints_FeatureServer_0` | 15,736 | 15,736 | 0.00% | ok |
| 966 | `5r1BMKyz_arcgis_rest_services_AddressPoints_FeatureServer_10` | 15,698 | 15,698 | 0.00% | ok |
| 967 | `est_services_Fire_Parcel_Address_Finder_WFL1_FeatureServer_1` | 15,657 | 15,657 | 0.00% | ok |
| 968 | `B5z0_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 15,641 | 15,641 | 0.00% | ok |
| 969 | `_rest_services_EXISTING_ADDRESS_POINTS_view2_FeatureServer_0` | 15,628 | 15,628 | 0.00% | ok |
| 970 | `DlUCS7Cz_arcgis_rest_services_Logan_911_View_FeatureServer_0` | 15,625 | 15,625 | 0.00% | ok |
| 971 | `est_services_Road_Centerlines_by_Maintenance_FeatureServer_2` | 15,579 | 15,579 | 0.00% | ok |
| 972 | `NqLU1DwuT_arcgis_rest_services_AddressPoints_FeatureServer_0` | 15,574 | 15,574 | 0.00% | ok |
| 973 | `gp_ab_ca_arcgis_rest_services_site_addresses_FeatureServer_0` | 15,569 | 15,569 | 0.00% | ok |
| 974 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-3` | 15,545 | 15,545 | 0.00% | ok |
| 975 | `x33spbMD_arcgis_rest_services_Address_Points_FeatureServer_1` | 15,518 | 15,518 | 0.00% | ok |
| 976 | `on_wa_us_server_rest_services_Address_Master_FeatureServer_0` | 15,493 | 15,493 | 0.00% | ok |
| 977 | `cgis_rest_services_LibraryPatrons_AddressPts_FeatureServer_0` | 15,464 | 15,464 | 0.00% | ok |
| 978 | `ry_arcgis_rest_services_AddressEntrancePoint_FeatureServer_0` | 15,446 | 15,446 | 0.00% | ok |
| 979 | `sAU_arcgis_rest_services_COSJ_ADDRESS_POINTS_FeatureServer_0` | 15,428 | 15,428 | 0.00% | ok |
| 980 | `gis_rest_services_SealBeach_Addresses_082025_FeatureServer_0` | 15,410 | 15,410 | 0.00% | ok |
| 981 | `U5_arcgis_rest_services_Civic_Address_Points_FeatureServer_0` | 15,354 | 15,354 | 0.00% | ok |
| 982 | `arcgis_rest_services_GIS_AddressPoint_LKG911_FeatureServer_0` | 15,335 | 15,335 | 0.00% | ok |
| 983 | `yQSD0q_arcgis_rest_services_MASTER_Addresses_FeatureServer_0` | 15,330 | 15,330 | 0.00% | ok |
| 984 | `t_services_Fayette_County_Ohio_GIS_Addresses_FeatureServer_0` | 15,298 | 15,298 | 0.00% | ok |
| 985 | `rest_services_Houston_County_Address_Points_FeatureServer_10` | 15,239 | 15,239 | 0.00% | ok |
| 986 | `lDOMEad_arcgis_rest_services_Hancock_Address_FeatureServer_1` | 15,237 | 15,237 | 0.00% | ok |
| 987 | `arcgis_rest_services_Barnwell_Address_Points_FeatureServer_0` | 15,198 | 15,198 | 0.00% | ok |
| 988 | `s_rest_services_Tyler_County_Address_Points_FeatureServer_10` | 15,194 | 15,194 | 0.00% | ok |
| 989 | `_arcgis_rest_services_AddressBuilidings_View_FeatureServer_5` | 15,141 | 15,141 | 0.00% | ok |
| 990 | `X_arcgis_rest_services_Lafayette_NGAP_0427_FeatureServer_105` | 15,130 | 15,130 | 0.00% | ok |
| 991 | `4d1b0833552_rest_services_Basemaps_Addresses_FeatureServer_0` | 15,107 | 15,107 | 0.00% | ok |
| 992 | `_services_Stark_County_Address_Points_public_FeatureServer_1` | 15,064 | 15,064 | 0.00% | ok |
| 993 | `_services_Stark_County_Address_Points_public_FeatureServer_0` | 15,064 | 15,064 | 0.00% | ok |
| 994 | `PnUOHQnhsl_arcgis_rest_services_Address_view_FeatureServer_0` | 15,024 | 15,024 | 0.00% | ok |
| 995 | `nhsUu_arcgis_rest_services_Canmore_Addresses_FeatureServer_0` | 15,005 | 15,005 | 0.00% | ok |
| 996 | `_rest_services_Address_and_Centerline_Map_V4_FeatureServer_0` | 15,000 | 15,000 | 0.00% | ok |
| 997 | `h71mtnDG_arcgis_rest_services_E911_ADDRESSES_FeatureServer_0` | 14,991 | 14,991 | 0.00% | ok |
| 998 | `9pGRbGVB0nAAA_arcgis_rest_services_Addresses_FeatureServer_0` | 14,968 | 14,968 | 0.00% | ok |
| 999 | `VCGI_OPENDATA_Emergency_HYDRANTS_point_SP_v1_FeatureServer_0` | 14,960 | 14,960 | 0.00% | ok |
| 1000 | `st_services_RDEK_Public_Webmap_20211110_WFL1_FeatureServer_3` | 14,959 | 14,959 | 0.00% | ok |
| 1001 | `GJG22RSY_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,926 | 14,926 | 0.00% | ok |
| 1002 | `rpDGOIDK_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,911 | 14,911 | 0.00% | ok |
| 1003 | `vARAsxza_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,898 | 14,898 | 0.00% | ok |
| 1004 | `rest_services_Address_Points___Edmonson_view_FeatureServer_0` | 14,862 | 14,862 | 0.00% | ok |
| 1005 | `Vod_arcgis_rest_services_ELM_Situs_Addresses_FeatureServer_0` | 14,840 | 14,840 | 0.00% | ok |
| 1006 | `is_rest_services_Emanuel_Address_Points_view_FeatureServer_0` | 14,814 | 14,814 | 0.00% | ok |
| 1007 | `Xz_arcgis_rest_services_Site_Addresses_View_FeatureServer_12` | 14,794 | 14,794 | 0.00% | ok |
| 1008 | `hBWbYdBZ_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,769 | 14,769 | 0.00% | ok |
| 1009 | `ices_County_Point_Address_External_Viewlayer_FeatureServer_0` | 14,758 | 14,758 | 0.00% | ok |
| 1010 | `s_rest_services_VirginiaAddressPoints_Clip_FeatureServer_144` | 14,732 | 14,732 | 0.00% | ok |
| 1011 | `otW_arcgis_rest_services_Kerrville_Addresses_FeatureServer_0` | 14,713 | 14,713 | 0.00% | ok |
| 1012 | `OamkQCWQM5KB8_arcgis_rest_services_E911_Clip_FeatureServer_0` | 14,677 | 14,677 | 0.00% | ok |
| 1013 | `rcgis_rest_services_911_MyPermitsNow_located_FeatureServer_0` | 14,675 | 14,675 | 0.00% | ok |
| 1014 | `cgis_rest_services_Cicero_Parcel_and_Address_FeatureServer_0` | 14,648 | 14,648 | 0.00% | ok |
| 1015 | `XDC07yFxn_arcgis_rest_services_AddressPoints_FeatureServer_0` | 14,622 | 14,622 | 0.00% | ok |
| 1016 | `84Po4FBDs_arcgis_rest_services_Address_Point_FeatureServer_0` | 14,616 | 26,616 | -82.10% | partial |
| 1017 | `poec_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 14,614 | 14,614 | 0.00% | ok |
| 1018 | `HtHcH5kGh_arcgis_rest_services_ADDRESSPOINTS_FeatureServer_0` | 14,594 | 14,594 | 0.00% | ok |
| 1019 | `rcgis_rest_services_EnerGovParcelAddressProd_FeatureServer_1` | 14,566 | 14,566 | 0.00% | ok |
| 1020 | `5kGh_arcgis_rest_services_ClerkAddressPoints_FeatureServer_0` | 14,562 | 14,562 | 0.00% | ok |
| 1021 | `kqyKR88_arcgis_rest_services_Niles_Addresses_FeatureServer_0` | 14,511 | 14,511 | 0.00% | ok |
| 1022 | `gis_rest_services_MSWD_AddressPoints_Active_FeatureServer_62` | 14,499 | 14,499 | 0.00% | ok |
| 1023 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | 54.28% | failed |
| 1024 | `services_Master_Address_File_CWDG_selection_FeatureServer_34` | 14,442 | 14,442 | 0.00% | ok |
| 1025 | `Wt8807Pv_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,435 | 14,435 | 0.00% | ok |
| 1026 | `rcgis_rest_services_FiberServicableAddresses_FeatureServer_0` | 14,421 | 14,421 | 0.00% | ok |
| 1027 | `3LFZv_arcgis_rest_services_Address_Points_CC_FeatureServer_0` | 14,406 | 14,406 | 0.00% | ok |
| 1028 | `qqHxBiQIog_arcgis_rest_services_Addresses4SG_FeatureServer_0` | 14,389 | 14,389 | 0.00% | ok |
| 1029 | `FS_arcgis_rest_services_Civic_Address_Points_FeatureServer_1` | 14,346 | 14,346 | 0.00% | ok |
| 1030 | `est_services_Join_Features_to_Address___View_FeatureServer_0` | 14,319 | 14,319 | 0.00% | ok |
| 1031 | `O_arcgis_rest_services_WY_Teton_Address_view_FeatureServer_0` | 14,301 | 14,301 | 0.00% | ok |
| 1032 | `eLCJ_arcgis_rest_services_PageCoVA_Addresses_FeatureServer_0` | 14,301 | 14,301 | 0.00% | ok |
| 1033 | `l_arcgis_rest_services_ADDRPOINTS_2020_08_03_FeatureServer_0` | 14,288 | 14,288 | 0.00% | ok |
| 1034 | `ibertymo_gov_arcgis_rest_services_Layers_Address_MapServer_0` | 14,286 | 14,286 | 0.00% | ok |
| 1035 | `_rest_services_NewPhiladelphiaGIS_runningMap_FeatureServer_6` | 14,262 | 14,262 | 0.00% | ok |
| 1036 | `t_services_Hosted_OpenGov_Permitting_Service_FeatureServer_0` | 14,261 | 14,261 | 0.00% | ok |
| 1037 | `_arcgis_rest_services_NG911_Core_Data_VIEWER_FeatureServer_0` | 14,257 | 14,257 | 0.00% | ok |
| 1038 | `ountyor_gov_server_rest_services_OpenData_Places_MapServer_0` | 14,256 | 14,256 | 0.00% | ok |
| 1039 | `mJOdyNXk_arcgis_rest_services_Address_points_FeatureServer_4` | 14,221 | 14,221 | 0.00% | ok |
| 1040 | `o_arcgis_rest_services_Tishomingo_addressing_FeatureServer_6` | 14,210 | 14,210 | 0.00% | ok |
| 1041 | `X_arcgis_rest_services_Tishomingo_addressing_FeatureServer_6` | 14,210 | 14,210 | 0.00% | ok |
| 1042 | `v_server_rest_services_GoldenMap_Golden_Misc_FeatureServer_1` | 14,175 | 14,175 | 0.00% | ok |
| 1043 | `DVjy1gZox_arcgis_rest_services_AddressLabels_FeatureServer_0` | 14,161 | 14,161 | 0.00% | ok |
| 1044 | `s_rest_services_Agawam_Address_Points_070826_FeatureServer_0` | 14,124 | 14,124 | 0.00% | ok |
| 1045 | `gis_rest_services_AddressPointsAuth_05292025_FeatureServer_0` | 14,098 | 14,098 | 0.00% | ok |
| 1046 | `5SQm_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 14,086 | 14,086 | 0.00% | ok |
| 1047 | `s_rest_services_Kerrville_Site_Address_Point_FeatureServer_0` | 14,065 | 14,065 | 0.00% | ok |
| 1048 | `wqf_arcgis_rest_services_AddressPointsPublic_FeatureServer_0` | 14,019 | 14,019 | 0.00% | ok |
| 1049 | `ersite_rest_services_Hosted_Address_Points_FeatureServer_137` | 14,017 | 14,017 | 0.00% | ok |
| 1050 | `2ZRTplQC_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,017 | 14,017 | 0.00% | ok |
| 1051 | `rvices_VityOfNewark_SiteAddress_Only_AGOL_FS_FeatureServer_2` | 13,998 | 13,998 | 0.00% | ok |
| 1052 | `5yj_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 13,987 | 13,987 | 0.00% | ok |
| 1053 | `services_EnterpriseGIS_GISDBA_ADDRESS_POINTS_FeatureServer_0` | 13,987 | 13,987 | 0.00% | ok |
| 1054 | `_arcgis_rest_services_Address_Points_Avenity_FeatureServer_0` | 13,981 | 13,981 | 0.00% | ok |
| 1055 | `zUw0cVRX_arcgis_rest_services_Address_Points_FeatureServer_0` | 13,966 | 13,966 | 0.00% | ok |
| 1056 | `H37M_arcgis_rest_services_Address_Points_MWP_FeatureServer_0` | 13,950 | 13,950 | 0.00% | ok |
| 1057 | `arcgis_rest_services_WILDOMAR_ADDRESS_POINTS_FeatureServer_0` | 13,941 | 13,941 | 0.00% | ok |
| 1058 | `rest_services_Trinity_County_Address_Points_FeatureServer_10` | 13,938 | 13,938 | 0.00% | ok |
| 1059 | `nLVk_arcgis_rest_services_AddressPointsDEC25_FeatureServer_0` | 12,518 | 12,518 | 0.00% | ok |
| 1060 | `is_rest_services_Address_Points__City_Limits_FeatureServer_0` | 12,513 | 12,513 | 0.00% | ok |
| 1061 | `rk_County_Address_Points_Clip_AreaOfInterest_FeatureServer_0@ND-1` | 12,510 | 12,510 | 0.00% | ok |
| 1062 | `icQLS_arcgis_rest_services_Address_GSPJ_view_FeatureServer_0` | 12,501 | 12,501 | 0.00% | ok |
| 1063 | `Qeln9HQP_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,495 | 12,495 | 0.00% | ok |
| 1064 | `cgis_rest_services_Address_Points__Open_Data_FeatureServer_0` | 12,475 | 12,475 | 0.00% | ok |
| 1065 | `HpS7dOJQ_arcgis_rest_services_Addresses_View_FeatureServer_0` | 12,472 | 12,472 | 0.00% | ok |
| 1066 | `uYk_arcgis_rest_services_Roads_and_Addresses_FeatureServer_0` | 12,470 | 12,470 | 0.00% | ok |
| 1067 | `cgis_rest_services_Assumption_Address_Points_FeatureServer_0` | 12,470 | 12,470 | 0.00% | ok |
| 1068 | `AOV9p4gC_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,463 | 12,463 | 0.00% | ok |
| 1069 | `IHYICuzkgTNM_arcgis_rest_services_AddressDBS_FeatureServer_0` | 12,458 | 12,458 | 0.00% | ok |
| 1070 | `CAX9v0Owj_arcgis_rest_services_AddressPoints_FeatureServer_0` | 12,432 | 12,432 | 0.00% | ok |
| 1071 | `g1UCmgQ8_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,410 | 12,410 | 0.00% | ok |
| 1072 | `est_services_BaseLayers_Address_Access_Point_FeatureServer_0` | 12,386 | 12,386 | 0.00% | ok |
| 1073 | `ge_arcgis_rest_services_AddressRoadParcelESN_FeatureServer_0` | 12,367 | 12,367 | 0.00% | ok |
| 1074 | `rest_services_2026_WC_Address_Points_service_FeatureServer_0` | 12,351 | 12,351 | 0.00% | ok |
| 1075 | `rest_services_2022_WC_Address_Points_service_FeatureServer_0` | 12,349 | 12,349 | 0.00% | ok |
| 1076 | `rest_services_2023_WC_Address_Points_service_FeatureServer_0` | 12,343 | 12,343 | 0.00% | ok |
| 1077 | `_arcgis_rest_services_Address_Points_Payette_FeatureServer_0` | 12,339 | 12,339 | 0.00% | ok |
| 1078 | `wd7ad0P0_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,337 | 12,337 | 0.00% | ok |
| 1079 | `naX0z0hS_arcgis_rest_services_AddressingData_FeatureServer_0` | 12,331 | 12,331 | 0.00% | ok |
| 1080 | `leycity_ca_server_rest_services_Maps_Open_Data_MapServer_182` | 12,321 | 12,321 | 0.00% | ok |
| 1081 | `X8U_arcgis_rest_services_ParcelAddressPoints_FeatureServer_7` | 12,320 | 12,320 | 0.00% | ok |
| 1082 | `corp_com_arcgis_rest_services_BentonCountyIA_WFS_MapServer_1` | 12,318 | 12,318 | 0.00% | ok |
| 1083 | `s_rest_services_Ashley_County_Address_Points_FeatureServer_0` | 12,315 | 12,315 | 0.00% | ok |
| 1084 | `Qx1O_arcgis_rest_services_AddressInCityLimit_FeatureServer_0` | 12,311 | 12,311 | 0.00% | ok |
| 1085 | `TIvB0lzdRad0i_arcgis_rest_services_Addresses_FeatureServer_0` | 12,308 | 12,308 | 0.00% | ok |
| 1086 | `t_services_us_mn_co_wabasha_loc_addresspoint_FeatureServer_0` | 12,267 | 12,267 | 0.00% | ok |
| 1087 | `is_rest_services_Current_Arlington_Addresses_FeatureServer_0` | 12,267 | 12,267 | 0.00% | ok |
| 1088 | `rxOA_arcgis_rest_services_CivicAddressPoints_FeatureServer_0` | 12,265 | 12,265 | 0.00% | ok |
| 1089 | `DFVQ_arcgis_rest_services_Address_Points_R_A_FeatureServer_0` | 12,250 | 12,250 | 0.00% | ok |
| 1090 | `7KciUs5nOw64q_arcgis_rest_services_Addresses_FeatureServer_0` | 12,240 | 12,240 | 0.00% | ok |
| 1091 | `MSgI0g7r_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,238 | 12,238 | 0.00% | ok |
| 1092 | `4_arcgis_rest_services_GIS_AddressPoint_LUNE_FeatureServer_0` | 12,238 | 12,238 | 0.00% | ok |
| 1093 | `rcgis_rest_services_Address_Pnts_Parcel_2022_FeatureServer_6` | 12,232 | 12,232 | 0.00% | ok |
| 1094 | `2ORwJqb7OUkpO_arcgis_rest_services_addresses_FeatureServer_0` | 12,219 | 12,219 | 0.00% | ok |
| 1095 | `rest_services_AddressPoints_Centerville_view_FeatureServer_0` | 12,206 | 12,206 | 0.00% | ok |
| 1096 | `cgis_rest_services_AddressPoints_Centerville_FeatureServer_0` | 12,206 | 12,206 | 0.00% | ok |
| 1097 | `rvices_Monroe_County_Site_Address_Points_911_FeatureServer_0` | 12,191 | 12,191 | 0.00% | ok |
| 1098 | `0gnCAvCoAhpj_arcgis_rest_services_Addressing_FeatureServer_0` | 12,174 | 12,174 | 0.00% | ok |
| 1099 | `SOeX2vv_arcgis_rest_services_Point_Addresses_FeatureServer_0` | 12,171 | 12,171 | 0.00% | ok |
| 1100 | `cgis_rest_services_IN_Civic_Address_Points_FeatureServer_328` | 12,134 | 12,134 | 0.00% | ok |
| 1101 | `CKvqg56E_arcgis_rest_services_Address_Points_FeatureServer_8` | 12,044 | 12,044 | 0.00% | ok |
| 1102 | `lle_ca_arcgis_rest_services_Location_SiteAddress_MapServer_0` | 12,040 | 12,040 | 0.00% | ok |
| 1103 | `_services_Braidwood_Address_Points_July_2016_FeatureServer_0` | 12,024 | 12,024 | 0.00% | ok |
| 1104 | `_services_DHN_All_Addresses_Aug_4_2023_view_FeatureServer_54` | 11,997 | 11,997 | 0.00% | ok |
| 1105 | `Ad6WMhA7fHTz_arcgis_rest_services_Addressing_FeatureServer_0` | 11,978 | 11,978 | 0.00% | ok |
| 1106 | `int_Address_Unit_Level__Mailing_Address_View_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 1107 | `t_Addresses__Unit_and_Apt_Level_Data_Exports_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 1108 | `_rest_services_E911_Point_Address_Unit_Level_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 1109 | `t_services_AC_CivicAddressPoints_Sept14_2021_FeatureServer_0` | 11,919 | 11,919 | 0.00% | ok |
| 1110 | `est_services_SSLC_Residential_Address_Points_FeatureServer_0` | 11,895 | 11,895 | 0.00% | ok |
| 1111 | `ces_Community_Buildings__Address_Points_View_FeatureServer_0` | 11,875 | 11,875 | 0.00% | ok |
| 1112 | `vices_Guelph_and_Stats_Canada_Addresses_WFL1_FeatureServer_0` | 11,856 | 11,856 | 0.00% | ok |
| 1113 | `VjVOYp6_arcgis_rest_services_Point_Addresses_FeatureServer_0` | 11,855 | 11,855 | 0.00% | ok |
| 1114 | `9JtEo7N6_arcgis_rest_services_Addresses_view_FeatureServer_0` | 11,846 | 11,846 | 0.00% | ok |
| 1115 | `bUyBqyyiCt_arcgis_rest_services_Address_View_FeatureServer_0` | 11,829 | 11,829 | 0.00% | ok |
| 1116 | `ZJTbBa9X_arcgis_rest_services_Address_Points_FeatureServer_0` | 11,816 | 11,816 | 0.00% | ok |
| 1117 | `ed_Address_Points_of_Gilpin_County_Colorado_FeatureServer_10` | 11,813 | 11,813 | 0.00% | ok |
| 1118 | `I6Qk_arcgis_rest_services_Address_Points_NEW_FeatureServer_0` | 11,800 | 11,800 | 0.00% | ok |
| 1119 | `x0tv46_arcgis_rest_services_ClintonAddresses_FeatureServer_0` | 11,779 | 11,779 | 0.00% | ok |
| 1120 | `46_arcgis_rest_services_Lea_County_Addresses_FeatureServer_0` | 11,773 | 11,773 | 0.00% | ok |
| 1121 | `t_services_StructureAddressPoints_publicTest_FeatureServer_1` | 11,771 | 11,771 | 0.00% | ok |
| 1122 | `s_rest_services_E911_SMC_DATA_Address_Points_FeatureServer_0` | 11,758 | 11,758 | 0.00% | ok |
| 1123 | `ning__Industrial__Parcels___Address_Map_WFL1_FeatureServer_0@NE-1` | 11,719 | 11,719 | 0.00% | ok |
| 1124 | `ning__Industrial__Parcels___Address_Map_WFL1_FeatureServer_0@NE-2` | 11,719 | 11,719 | 0.00% | ok |
| 1125 | `es_Address_Points_in_Tsunami_Inundation_Zone_FeatureServer_0` | 11,694 | 11,694 | 0.00% | ok |
| 1126 | `H0fQHR1s_arcgis_rest_services_Address_Points_FeatureServer_2` | 11,635 | 11,635 | 0.00% | ok |
| 1127 | `rcgis_rest_services_Bibb_Address_Points_E911_FeatureServer_0` | 11,633 | 11,633 | 0.00% | ok |
| 1128 | `Zqc8NIv_arcgis_rest_services_Perry_Addresses_FeatureServer_0` | 11,605 | 11,605 | 0.00% | ok |
| 1129 | `_arcgis_rest_services_Address_Points_Public_FeatureServer_37` | 11,589 | 11,589 | 0.00% | ok |
| 1130 | `arcgis_rest_services_Site_Address_Point_view_FeatureServer_0` | 11,529 | 11,529 | 0.00% | ok |
| 1131 | `t_services_Taylor_ISD_2024_25_Address_Points_FeatureServer_0` | 11,508 | 11,508 | 0.00% | ok |
| 1132 | `1Hv4I6Qk_arcgis_rest_services_Address_Points_FeatureServer_4` | 11,466 | 11,466 | 0.00% | ok |
| 1133 | `I6Qk_arcgis_rest_services_Address_Point_Test_FeatureServer_1` | 11,442 | 11,442 | 0.00% | ok |
| 1134 | `BPeNRqI2rE8sfwz_arcgis_rest_services_Address_FeatureServer_0` | 11,430 | 11,430 | 0.00% | ok |
| 1135 | `iKJaT7Upn_arcgis_rest_services_SDEAddressPts_FeatureServer_3` | 11,424 | 11,424 | 0.00% | ok |
| 1136 | `8U_arcgis_rest_services_CC_Parcels_Addresses_FeatureServer_0` | 11,412 | 11,412 | 0.00% | ok |
| 1137 | `gis_rest_services_Address_Points___Open_Data_FeatureServer_1` | 11,401 | 11,401 | 0.00% | ok |
| 1138 | `o_arcgis_rest_services_Willingboro_Addresses_FeatureServer_4` | 11,360 | 11,360 | 0.00% | ok |
| 1139 | `mni5zEMr_arcgis_rest_services_Address_Points_FeatureServer_0` | 11,355 | 11,355 | 0.00% | ok |
| 1140 | `tJVh_arcgis_rest_services_Address_Points_PJ_FeatureServer_14` | 11,319 | 11,319 | 0.00% | ok |
| 1141 | `_services_ROW_Land_Title_Address_Labels_WFL1_FeatureServer_1` | 11,300 | 11,300 | 0.00% | ok |
| 1142 | `cgis_rest_services_Parcels_AddressesforEngov_FeatureServer_0` | 11,298 | 11,298 | 0.00% | ok |
| 1143 | `14smu_arcgis_rest_services_SiteAddressPoints_FeatureServer_0` | 11,288 | 11,288 | 0.00% | ok |
| 1144 | `Mf01B1N0W_arcgis_rest_services_AddressPoints_FeatureServer_0` | 11,286 | 11,286 | 0.00% | ok |
| 1145 | `pa8_arcgis_rest_services_COSB_ADDRESS_POINTS_FeatureServer_0` | 11,245 | 11,245 | 0.00% | ok |
| 1146 | `is_rest_services_Morehead_CityAddress_Points_FeatureServer_0` | 11,217 | 11,217 | 0.00% | ok |
| 1147 | `_rest_services_Site_Structure_Address_Points_FeatureServer_1@TX-2` | 11,210 | 11,210 | 0.00% | ok |
| 1148 | `g57sok_arcgis_rest_services_Address_Points_FeatureServer_108` | 11,202 | 11,202 | 0.00% | ok |
| 1149 | `UH_arcgis_rest_services_France_Address_Pilot_FeatureServer_0` | 11,181 | 11,181 | 0.00% | ok |
| 1150 | `s_rest_services_911_Site_Address_Points_0727_FeatureServer_0` | 11,170 | 11,170 | 0.00% | ok |
| 1151 | `arcgis_rest_services_AddressSearchLayers_MCS_FeatureServer_0` | 11,148 | 11,148 | 0.00% | ok |
| 1152 | `lc2PRESEUr5jw_arcgis_rest_services_Addresses_FeatureServer_7` | 11,130 | 11,130 | 0.00% | ok |
| 1153 | `s_rest_services_Montclair_Twp_Address_Points_FeatureServer_0` | 11,122 | 11,122 | 0.00% | ok |
| 1154 | `gis_rest_services_Parcel_Available_Addresses_FeatureServer_5` | 11,121 | 11,121 | 0.00% | ok |
| 1155 | `s_Building_Footprints_500ft_Buffer_Intersect_FeatureServer_0` | 11,118 | 11,118 | 0.00% | ok |
| 1156 | `uSp_arcgis_rest_services_Address_Leaf_Search_FeatureServer_0` | 11,044 | 11,044 | 0.00% | ok |
| 1157 | `_Schererville_Address_Points_View_Layer_9722_FeatureServer_0` | 11,036 | 11,036 | 0.00% | ok |
| 1158 | `ha_arcgis_rest_services_SiteAddressPoint_APN_FeatureServer_0` | 11,012 | 11,012 | 0.00% | ok |
| 1159 | `NNPvtbwc_arcgis_rest_services_Address_Search_FeatureServer_0` | 10,968 | 10,968 | 0.00% | ok |
| 1160 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | 10,564 | 0 | 100.00% | failed |
| 1161 | `18XGRt6t_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,600 | 9,600 | 0.00% | ok |
| 1162 | `Ce9CL2ex9_arcgis_rest_services_AddressPoint_FeatureServer_67` | 9,592 | 9,592 | 0.00% | ok |
| 1163 | `9CL2ex9_arcgis_rest_services_Address_Points_FeatureServer_10` | 9,590 | 9,590 | 0.00% | ok |
| 1164 | `EK9DB_arcgis_rest_services_HC_Address_Points_FeatureServer_0` | 9,575 | 9,575 | 0.00% | ok |
| 1165 | `xIXpWoaR2sAe_arcgis_rest_services_Addresses_FeatureServer_21` | 9,565 | 9,565 | 0.00% | ok |
| 1166 | `ElDOMEad_arcgis_rest_services_Wetzel_Address_FeatureServer_1` | 9,557 | 9,557 | 0.00% | ok |
| 1167 | `rest_services_public_PublicNotificationQuery_FeatureServer_0` | 9,543 | 9,543 | 0.00% | ok |
| 1168 | `L2ex9_arcgis_rest_services_Address_Point_Int_FeatureServer_3` | 9,541 | 9,541 | 0.00% | ok |
| 1169 | `arcgis_rest_services_Tecumseh_Address_Points_FeatureServer_1` | 9,533 | 9,533 | 0.00% | ok |
| 1170 | `YcNK2j_arcgis_rest_services_2022ADDRESS_view_FeatureServer_0` | 9,530 | 9,530 | 0.00% | ok |
| 1171 | `8MEELvtKj2_arcgis_rest_services_AddressPoint_FeatureServer_0` | 9,517 | 9,517 | 0.00% | ok |
| 1172 | `Ony4j_arcgis_rest_services_NG911_Core_Data_2_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 1173 | `cgis_rest_services_NG911_Final_DashboardView_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 1174 | `rcgis_rest_services_NG911_Core_Data_1_Viewer_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 1175 | `services_Scugog_Addresses_Wards_Intersection_FeatureServer_0` | 9,496 | 9,496 | 0.00% | ok |
| 1176 | `_arcgis_rest_services_Scituate_AddressPoints_FeatureServer_0` | 9,495 | 9,495 | 0.00% | ok |
| 1177 | `ymQJ3T_arcgis_rest_services_Hudson_Addresses_FeatureServer_0` | 9,477 | 9,477 | 0.00% | ok |
| 1178 | `b0ovdJoIQKg_arcgis_rest_services_Base_Layers_FeatureServer_0` | 9,466 | 9,466 | 0.00% | ok |
| 1179 | `k_arcgis_rest_services_Address_Points_Public_FeatureServer_0` | 9,440 | 9,440 | 0.00% | ok |
| 1180 | `ovdJoIQKg_arcgis_rest_services_Situs_clipped_FeatureServer_0` | 9,435 | 9,435 | 0.00% | ok |
| 1181 | `es_Swain_County_Address_Points___Public_View_FeatureServer_0` | 9,428 | 9,428 | 0.00% | ok |
| 1182 | `pids_org_arcgis_rest_services_Public_Basemap_svc_MapServer_8` | 9,404 | 9,404 | 0.00% | ok |
| 1183 | `jgFbdIrkt_arcgis_rest_services_LL_Addressing_FeatureServer_0` | 9,383 | 9,383 | 0.00% | ok |
| 1184 | `OLPdETvKbspkC_arcgis_rest_services_Addresses_FeatureServer_0` | 9,380 | 9,380 | 0.00% | ok |
| 1185 | `fftauX2_arcgis_rest_services_Address_Numbers_FeatureServer_5` | 9,369 | 9,369 | 0.00% | ok |
| 1186 | `B_arcgis_rest_services_E911_Addresses_Binned_FeatureServer_0` | 9,362 | 9,362 | 0.00% | ok |
| 1187 | `uQ_arcgis_rest_services_Master_Address_Table_FeatureServer_1` | 9,352 | 9,352 | 0.00% | ok |
| 1188 | `Hqqcg7Zo8zH_arcgis_rest_services_Address_Pts_FeatureServer_0` | 9,337 | 9,337 | 0.00% | ok |
| 1189 | `rcgis_rest_services_GrantCountyAddressPoints_FeatureServer_1` | 9,307 | 9,307 | 0.00% | ok |
| 1190 | `1tOY_arcgis_rest_services_Address_Points_HMP_FeatureServer_0` | 9,296 | 9,296 | 0.00% | ok |
| 1191 | `OUVqNUhbTXzVc_arcgis_rest_services_Addresses_FeatureServer_0` | 9,295 | 9,295 | 0.00% | ok |
| 1192 | `WLJiNAJwJ_arcgis_rest_services_AddressPoints_FeatureServer_1` | 9,293 | 9,293 | 0.00% | ok |
| 1193 | `arcgis_rest_services_SSSD_Address_and_Parcel_FeatureServer_0` | 9,280 | 9,280 | 0.00% | ok |
| 1194 | `est_services_Address_Points_with_Parcel_Data_FeatureServer_0` | 9,272 | 9,272 | 0.00% | ok |
| 1195 | `est_services_Montville_Address_Points_061826_FeatureServer_0` | 9,271 | 9,271 | 0.00% | ok |
| 1196 | `est_services_Montville_Address_Points_061226_FeatureServer_0` | 9,271 | 9,271 | 0.00% | ok |
| 1197 | `uxxuV9tV_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,268 | 9,268 | 0.00% | ok |
| 1198 | `58_rest_services_Clive_Clive_Land_Record_Service_MapServer_0` | 9,257 | 9,257 | 0.00% | ok |
| 1199 | `Jkj1aWl_arcgis_rest_services_E911_AddressPts_FeatureServer_0` | 9,234 | 9,234 | 0.00% | ok |
| 1200 | `rcgis_rest_services_E911_AddressPts_FirstDue_FeatureServer_0` | 9,234 | 9,234 | 0.00% | ok |
| 1201 | `gis_rest_services_AddressPointsSanDiego_Clip_FeatureServer_0` | 9,212 | 9,212 | 0.00% | ok |
| 1202 | `q0JXOtjNW10pz_arcgis_rest_services_Addresses_FeatureServer_0` | 9,202 | 9,202 | 0.00% | ok |
| 1203 | `ices_OpenDataHub_TOV_AddressPoints_OpenData_FeatureServer_36` | 9,186 | 9,186 | 0.00% | ok |
| 1204 | `cgis_rest_services_SE_Address_Points_8_19_26_FeatureServer_0` | 9,171 | 9,171 | 0.00% | ok |
| 1205 | `q6rKKp0o_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,168 | 9,168 | 0.00% | ok |
| 1206 | `is_rest_services_ADDRESS_POINTS_10152025_shp_FeatureServer_0` | 9,165 | 9,165 | 0.00% | ok |
| 1207 | `services_addresspoints_identifiedServiceArea_FeatureServer_0` | 9,158 | 9,158 | 0.00% | ok |
| 1208 | `ices_CrawfordIL_CityofRobinson_AddressPoints_FeatureServer_0` | 9,154 | 9,154 | 0.00% | ok |
| 1209 | `jCtQj_arcgis_rest_services_AddressPoints2022_FeatureServer_0` | 9,146 | 9,146 | 0.00% | ok |
| 1210 | `z9O_arcgis_rest_services_OpenGovAddress_view_FeatureServer_2` | 9,145 | 9,145 | 0.00% | ok |
| 1211 | `OMEad_arcgis_rest_services_Doddridge_Address_FeatureServer_1` | 9,144 | 9,144 | 0.00% | ok |
| 1212 | `gis_rest_services_911_Address_Points_PC_2024_FeatureServer_0` | 9,129 | 9,129 | 0.00% | ok |
| 1213 | `roY6O3ncx_arcgis_rest_services_MS4_addresses_FeatureServer_0` | 5,060 | 5,060 | 0.00% | ok |
| 1214 | `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0` | 5,045 | 10,085 | -99.90% | partial |
| 1215 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 1216 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | - | 25,659 | 0.00% | empty |
| 1217 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | - | 0 | 0.00% | failed |
| 1218 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | - | 0 | 0.00% | empty |
| 1219 | `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | - | 0 | 0.00% | empty |
| 1220 | `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | - | 0 | 0.00% | failed |
| 1221 | `county_com_arcgis_rest_services_features_Address_MapServer_0` | - | 0 | 0.00% | failed |
| 1222 | `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0` | - | 45,810 | 0.00% | empty |
| 1223 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 1224 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |
| 1225 | `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 1226 | `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | - | 0 | 0.00% | empty |
| 1227 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | - | 0 | 0.00% | failed |
| 1228 | `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` | - | 233,572 | 0.00% | empty |
| 1229 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | - | 0 | 0.00% | empty |
| 1230 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | - | 0 | 0.00% | empty |
| 1231 | `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | - | 0 | 0.00% | empty |
| 1232 | `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | - | 0 | 0.00% | failed |
| 1233 | `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | - | 0 | 0.00% | empty |
| 1234 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | - | 0 | 0.00% | empty |
| 1235 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | - | 0 | 0.00% | failed |
| 1236 | `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | - | 0 | 0.00% | empty |
| 1237 | `_com_geoserver_rest_services_Public_GIS_Data_FeatureServer_0` | - | 0 | 0.00% | empty |
| 1238 | `_org_gisarcweb_rest_services_Base_Base_Addresses_MapServer_0` | - | 0 | 0.00% | empty |
| 1239 | `st_services_Schools_ChathamSchools_AddressPoints_MapServer_0` | - | 0 | 0.00% | empty |
| 1240 | `g_arcgis_rest_services_Open_Data_Open_Data_1_FeatureServer_2` | - | 0 | 0.00% | empty |
| 1241 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | - | 0 | 0.00% | empty |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=05b
python3 collect/full_plan.py --stage 05b --size 3 --out collect/ledger/05b_plan.json
python3 collect/full_shard.py --stage 05b --shard 0 --plan collect/ledger/05b_plan.json
```


## 附录：口径备注（2026-11-22 复核 · 只解释数字，不改数字）

> 本节由 `docs/STEP05B-FULL-2026-10-30-shards.notes.md` 随文生成时自动追加（`step_full_report.py`
> 会在正文之后拼接同名 `.notes.md`），所以 CI 重跑 merge 不会把这段解释冲掉。

### A. 本文件修订前的数字是「merge 作用域」污染出来的，已作废

旧版本头部写「计划：577 层」，同一段又写「账本覆盖：1426 层（片文件 21 个）」
「声明行合计 68,180,805；实采行合计 75,100,286」—— 这两个数**不是本轮采的**：

- `step_full_report.py` 原先无条件 `glob ledger/05b_shard*.json`，把同目录里属于**更早轮次**的
  shard03..shard20 十八个片文件一起并进了 merge；
- 05b 本轮 plan 只有 **3 片 / 577 层**（`collect/ledger/05b_plan.json`：`shards_n=3`、`layers_n=577`），
  目录里却躺着 21 片 → 1426 − 577 = **849 层是别轮次的**；
- 修法（W33-058）：merge 作用域 = 本轮 plan 的片号集合，片号 ∉ plan 一律不读，并逐个打印；
  run 账本 `collect/ledger/05b_run<RUN_ID>.json` 新增 `read_shards` / `ignored_shard_files` 留痕。

| 口径 | 层数 | 声明行 | 实采行 |
|---|---|---|---|
| 旧（污染，glob 全量读 21 片） | 1,426 | 68,180,805 | 75,100,286 |
| 新（plan 作用域，只读 3 片） | **577** | **30,398,942** | **37,069,680** |

差额来源一句话：旧账本比新账本多算的声明 37,781,863 行 / 实采 38,030,606 行，全部来自
shard03..shard20（849 层净增 + 34 层重层层的取值差异），它们不在本轮 plan 里。
片账本 `shard0/1/2` 的实采行 2,458,675 + 7,276,367 + 27,334,638 = **37,069,680**，
与正文总账一位不差。

### B. 遗留片文件：18 个 / 883 条层记录 / 净增 849 层

shard03..shard20 共 18 个文件，是更早的 **21 片轮次**（`shards_total=21`、`size=50`）的产物，
片账本里合计 **883 条层记录**（17 片 × 50 层 + 1 片 × 33 层）。
其中 **34 层**与本轮 3 片里的层同名（按层合并会去重），所以旧账本的净增正好是 883 − 34 = **849 层**。
这些层不属本轮，要采必须单独派单（`force_layers`），不能靠 merge 混进来。

### C. 声明行两个数为何差 1,265,481（plan 31,664,423 vs 片账本 30,398,942）

两边都是逐层 `returnCount` 之和，差在**快照时间不同**（plan 在 2026-11-21 生成，片账本在采集时又探了一次），
可逐层对齐（577 层两边层集合完全一致，plan 侧逐层值 = `collect/ledger/05b_plan_probe.json`
的 `expect_by_layer`，求和正好 31,664,423）：

| 分类 | 层数 | plan 侧声明 | 片账本声明 | 差（plan − 账本） |
|---|---|---|---|---|
| empty（采集时上游声明 0 行） | 14 | 847,823 | 0 | **+847,823** |
| failed | 28 | 2,151,134 | 1,724,064 | **+427,070** |
| └ 其中 collect 时探针失败、`declared=null` | 8 | 428,427 | 0（不可复核，不入分母） | +428,427 |
| ok | 434 | 21,305,889 | 21,306,590 | −701 |
| partial | 101 | 7,359,577 | 7,368,288 | −8,711 |
| **合计** | **577** | **31,664,423** | **30,398,942** | **+1,265,481** |

即：**847,823（14 层采集时变空）+ 427,070（28 层失败，其中 8 层连声明都探不到）− 9,412（ok/partial 层
采集时 returnCount 已上浮）= 1,265,481**。这不是记账错误，也不是覆盖率缩水，是 plan 快照与采集快照的差。

### D. rows 37,069,680 > declared 30,398,942（+6,670,738）：**已知分页去重缺陷，不是超额完成**

分解（逐层核对，可复算）：

| 分类 | 层数 | 声明 | 实采 | 差 |
|---|---|---|---|---|
| partial | 101 | 7,368,288 | 14,728,222 | **+7,359,934** |
| empty（declared=0） | 3 | 0 | 305,041 | +305,041 |
| failed | 28 | 1,724,064 | 729,815 | −994,249 |
| ok | 434 | 21,306,590 | 21,306,602 | +12 |
| **合计** | **577** | **30,398,942** | **37,069,680** | **+6,670,738** |

- 主体是 **101 个 partial 层，实采/声明比 1.983 ~ 2.003（中位 2.000）**——正是顶补环节分页重复
  （同一批行被连采两遍）造成的，已定位为采集侧缺陷，另一个 PR（`fix/w33-048-variant-merge-and-paging-dedup`）
  在修「按行身份去重」。**修好之前，实采行一律按「含重复行」看待，不得对外声称超额完成。**
- 3 个 empty 层 `declared=0` 但实采 305,041 行（25,659 + 45,810 + 233,572），
  是「声明 0 时上游仍吐行」的账本口径问题，同样等着重采后收敛。
- 28 个 failed 层少采 994,249 行，按口径如实记 failed，不放宽容差。

> 结论：row 侧数字要去重 PR 合入、重采之后才可信；本文件只保证「读哪几片、算哪些层」这一层是对的。


## 七、rows 回退（本次合并检测到，未静默取大）

检测到 **2** 层 rows 回退（其中 2 层没有证据路径）。

处置分布（只有 `took_run_record_status_better` 是真的把阶段账本 rows 改小了；另两类是合并挡住了降级、账本 rows 没变，但本轮确实少采了）：`kept_stage_record_status_better` 2 层

| 层 | 旧 rows | 新 rows | 差额 | 状态 旧→新 | 合并处置 | 原因 | 证据 |
|---|---|---|---|---|---|---|---|
| `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | 39,504 | 39,503 | -1 | ok→failed | kept_stage_record_status_better | 状态变差且行数变少（合并保留了旧记录） | **缺** |
| `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | 51,668 | 51,610 | -58 | partial→failed | kept_stage_record_status_better | 状态变差且行数变少（合并保留了旧记录） | **缺** |

> 处置：回退不拦截（保进展靠取优者），但**必须点名**。能证明是「口径变了/上游真删了」的，把证据路径写进 run 账本的 `row_shrink_evidence: {<layer>: <path>}`（或逐层 `regression_reason`）；无证据的回退一律当事故追。累计视图看 `collect/05b_ledger.json` 的 `regressions[]`。
