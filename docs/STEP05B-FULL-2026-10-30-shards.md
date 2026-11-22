# STEP05B 全量补采 · 收官账（2026-11-22）

## 一、总账

- 阶段：`05b` —— 县市碎片 05b（5,000~300,000 行）
- 计划：580 层 / 声明 31,967,696 行 / 194 片（每片 3 层，unit_rows=100000）
- 账本覆盖：**962 层**（片文件 21 个）
- 逐态：**ok 897** / capped_by_upstream 0 / empty 16 / partial 21 / failed 28 / skipped_done 0
- 片完成度：应有 **194** 片，有账本 21 片，**未完成 175 片**：片号 1, 2, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193
- 声明行合计：**41,524,278**；实采行合计：**41,109,530**；差额 414,748（0.999%）


> 差额口径：`declared` 是上游 returnCount 的声明值，`rows` 是实采并落 Release 的行数。
> 结论只按账本事实写，不做「大概齐」的模糊表述；每条差额都能落到下面逐层表的具体一层。
> 未完成片里的层**没有账本条目**，既不计入 ok 也不算 failed —— 必须按上面的片号单独补跑。

## 二、片完成度（未完成片显式列出）

| 片 | 计划层 | 已记层 | 实采行 | 状态 |
|---|---|---|---|---|
| 0 | 3 | 3 | 565,724 | 完成 |
| 1 | 200 | 69 | 1,912,004 | 未完成：片内没跑完（partial_run=true） |
| 2 | 180 | 11 | 592,909 | 未完成：片内没跑完（partial_run=true） |
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
| 192 | 3 | 0 | 0 | 未完成：无账本（片被取消/没启动） |
| 193 | 1 | 0 | 0 | 未完成：无账本（片被取消/没启动） |

**未完成片共 175 个，至少 817 层没有任何账本条目**（这些层不是 failed，是「没跑到」，续跑入口：`force_layers` 点名或原地重切）。

## 二之二、max_shards 截断：本轮注定没跑的片（W33-036）

> 这不是「没采到」，是 **没派**：`max_shards=1` 把 194 片截成 1 片，577 层连 job 都没起。清单同时写在 plan 的 `shards_dropped[]`，账本 `shards_incomplete` 也会点名。要全跑请 `max_shards=0`。

| 被砍分片 | 层数 | 层 id |
|---|---|---|
| 1 | 3 | `ye4IXyXsdIpPb_arcgis_rest_services_Addresses_FeatureServer_0`, `roY6O3ncx_arcgis_rest_services_MS4_addresses_FeatureServer_0`, `d_Septic_System_Pilot_Project_Addresses_View_FeatureServer_0` |
| 2 | 3 | `arcgis_rest_services_Hartford_911_Addresses__FeatureServer_0`, `g5mTyuNWO5xx6_arcgis_rest_services_Addresses_FeatureServer_0`, `esses_In_Refuse_Recycle_Routes_WFL1_July2019_FeatureServer_0` |
| 3 | 3 | `67TISFO3iTjgFX_arcgis_rest_services_address2_FeatureServer_0`, `cgis_rest_services_Administrative_Addressing_FeatureServer_0`, `bK6DOd0VbR_arcgis_rest_services_SB_Addresses_FeatureServer_0` |
| 4 | 3 | `TjgFX_arcgis_rest_services_addresses_120222a_FeatureServer_0`, `unty__GA_Online_911_Addresses_and_Roads_WFL1_FeatureServer_1`, `e3_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 5 | 3 | `CRVuK_arcgis_rest_services_Map_View_Address_FeatureServer_42`, `HKRPMgv82EjLQ_arcgis_rest_services_Addresses_FeatureServer_0`, `cgis_rest_services_SiteAddresses_public_2020_FeatureServer_1` |
| 6 | 3 | `dlWlBxzX_arcgis_rest_services_Newton_Address_FeatureServer_0`, `Iod9kh71mtnDG_arcgis_rest_services_Addresses_FeatureServer_0`, `387Pb3S_arcgis_rest_services_LiveAdds_202504_FeatureServer_0` |
| 7 | 3 | `st_services_Curb_Transition_Magic_Number2027_FeatureServer_0`, `_in_Incident_Address_and_Type_for_Date_Range_FeatureServer_0`, `wVADPEG6iD24f_arcgis_rest_services_Addresses_FeatureServer_0` |
| 8 | 3 | `ces_Stillwater_County_Addressing_Layers_2026_FeatureServer_0`, `yHixJV_arcgis_rest_services_Master_Addresses_FeatureServer_0`, `teAddresses_8548b2fdfac0464392b3fd7620a632d7_FeatureServer_0` |
| 9 | 3 | `ater_Meter_Replacement_Addresses_Zone_1_view_FeatureServer_1`, `st_services_Lincoln_City_Addresses_View_Only_FeatureServer_0`, `sdIpPb_arcgis_rest_services_Addresses_Splits_FeatureServer_0` |
| 10 | 3 | `SQHJsl5r_arcgis_rest_services_Address_Labels_FeatureServer_0`, `NuFrQ7kB_arcgis_rest_services_Master_Address_FeatureServer_0`, `7Y8pE5CiojuXeU_arcgis_rest_services_NewSitus_FeatureServer_0` |
| 11 | 3 | `M5KB8_arcgis_rest_services_E911_PairwiseClip_FeatureServer_0`, `_rest_services_E911_Houses_Washington_County_FeatureServer_0`, `kttgSmcq6CPonms_arcgis_rest_services_Address_FeatureServer_0` |
| 12 | 3 | `ieS2ld_arcgis_rest_services_Searcy_NG911_gdb_FeatureServer_2`, `_Mountlake_Terrace_Washington_Addresses_view_FeatureServer_0`, `rest_services_Site_Addresses_06012022_public_FeatureServer_2` |
| 13 | 3 | `CY2_arcgis_rest_services_Dispatcher_Map_WFL1_FeatureServer_0`, `rest_services_Pella_Address_Data_Public_View_FeatureServer_2`, `_ArcGIS_rest_services_AddressesE911Macon2022_FeatureServer_0` |
| 14 | 3 | `Z_arcgis_rest_services_CityofDemingAddresses_FeatureServer_0`, `l0FeW1NE_arcgis_rest_services_AddressesWInfo_FeatureServer_0`, `0hS_arcgis_rest_services_Address_Road_Update_FeatureServer_0` |
| 15 | 3 | `Q24dH_arcgis_rest_services_Addresses__Site__FeatureServer_13`, `rest_services_Master_Address_Management_WFL1_FeatureServer_0`, `ms_arcgis_rest_services_Address_Data_Public_FeatureServer_10` |
| 16 | 3 | `cgis_rest_services_Address_Data_Public_view_FeatureServer_10`, `ses_public_3336c922d00a441e8f588e16c3dc2577_FeatureServer_10`, `gg5s_arcgis_rest_services_Building_Addresses_FeatureServer_0` |
| 17 | 3 | `8nlIDAHxNx4_arcgis_rest_services_911_Address_FeatureServer_0`, `is_rest_services_Address_Points_Council_Area_FeatureServer_0`, `s_rest_services_Richland_County_ND_Addresses_FeatureServer_1` |
| 18 | 3 | `HRU_arcgis_rest_services_VFAC_Addresses_WFL1_FeatureServer_0`, `sses_public_e65dd46e9c084cddaedcb94aeea0ed6b_FeatureServer_0`, `DQNT3m6mbJlqZ_arcgis_rest_services_Addresses_FeatureServer_0` |
| 19 | 3 | `_services_Address_and_Street_Annotation_view_FeatureServer_0`, `s_rest_services_City_of_Dinuba_Addresses_gdb_FeatureServer_1`, `_arcgis_rest_services_Site_Address_Occupants_FeatureServer_0` |
| 20 | 3 | `1uhbqnOZPx6qT_arcgis_rest_services_Addresses_FeatureServer_0`, `es_City_Buildings_and_Address_Locations_WFL1_FeatureServer_4`, `resses___Archuleta_County_201411251147175537_FeatureServer_0` |
| 21 | 3 | `Zk1fY2MHCTEXz_arcgis_rest_services_Addresses_FeatureServer_0`, `R_arcgis_rest_services_Tornado_Addresses_NLR_FeatureServer_0`, `vlQFEpKtV_arcgis_rest_services_DOUGLASCOUNTY_FeatureServer_0` |
| 22 | 3 | `wu_arcgis_rest_services_CoStafford_Addresses_FeatureServer_0`, `PSO5BR5eOIggwRH_arcgis_rest_services_Address_FeatureServer_0`, `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-3` |
| 23 | 3 | `mn_gov_arcgis_rest_services_Basemaps_LINKBasemap_MapServer_4`, `rcgis_rest_services_OsageCoKS_NG911Addresses_FeatureServer_0`, `Pc_arcgis_rest_services_EL_RENO_911ADDRESSES_FeatureServer_0` |
| 24 | 3 | `gUZUh16VF_arcgis_rest_services_SC_Addressing_FeatureServer_0`, `VF_arcgis_rest_services_SC_Addressing_2025_7_FeatureServer_0`, `sses_public_6332b4b81c614cb4894d5de569a96465_FeatureServer_0` |
| 25 | 3 | `cyjLcCCpGk8Ri_arcgis_rest_services_Addresses_FeatureServer_0`, `BY6OUzMBTZcz_arcgis_rest_services_Addresses_FeatureServer_15`, `Sample_NCTECH_Volusia_Situs_Addresss_VRWorld_FeatureServer_0` |
| 26 | 3 | `hAmRP1z50gTbO_arcgis_rest_services_Addresses_FeatureServer_0`, `oXVtxM_arcgis_rest_services_CountyAddresses_FeatureServer_23`, `_arcgis_rest_services_Address_Pnts_ElSegundo_FeatureServer_2` |
| 27 | 3 | `QpZPT9qY_arcgis_rest_services_TOD_ADDRESS_IN_FeatureServer_0`, `st_services_Winneshiek_County_Address_Points_FeatureServer_1`, `jyn_arcgis_rest_services_Full_Street_Address_FeatureServer_0` |
| 28 | 3 | `s___Pulse_of_OC_Updated_Draft___Site_Address_FeatureServer_0`, `_server_rest_services_Aspen_AspenEditEnabled_FeatureServer_0`, `QSIEviNS_arcgis_rest_services_Addresses_2025_FeatureServer_3` |
| 29 | 3 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0`, `wi_us_arcgis_rest_services_RichlandCo_GIS_Public_MapServer_6`, `p_arcgis_rest_services_Addresses_Public_View_FeatureServer_0` |
| 30 | 3 | `KcOCt7Lxga2AytI_arcgis_rest_services_Address_FeatureServer_0`, `tkincounty_com_arcgis_rest_services_Full_Address_MapServer_1`, `nDataMaps_OpenDataMAP_InfraZonePropBound_Layers_MapServer_33` |
| 31 | 3 | `Qwt3_arcgis_rest_services_Address_Layer_view_FeatureServer_0`, `FjYDrl_arcgis_rest_services_Address_12102021_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address11292023_FeatureServer_0` |
| 32 | 3 | `rWTl_arcgis_rest_services_Harrison_Addresses_FeatureServer_0`, `4soU_arcgis_rest_services_Site_Addresses_gdb_FeatureServer_0`, `t_services_Perry_County_Address_Geocode_v1_1_FeatureServer_0` |
| 33 | 3 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2`, `1mtnDG_arcgis_rest_services_Worth__ADDRESSES_FeatureServer_0`, `t_services_Public_20Notification_20Addresses_FeatureServer_0` |
| 34 | 3 | `lqccxOHLu_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address02202025_FeatureServer_0`, `unty_com_arcgis_rest_services_Hosted_Address_FeatureServer_0` |
| 35 | 3 | `Us_arcgis_rest_services_OC_Site_Address_2023_FeatureServer_0`, `ILCm3hbWNTZLH_arcgis_rest_services_Addresses_FeatureServer_0`, `kFjYDrl_arcgis_rest_services_Address06192026_FeatureServer_0` |
| 36 | 3 | `Kw_arcgis_rest_services_Situs_Address_Public_FeatureServer_0`, `arcgis_rest_services_BTV_e911_Address_Layers_FeatureServer_0`, `arcgis_rest_services_PAunderservedstructures_FeatureServer_0` |
| 37 | 3 | `ountyny_gov_server_rest_services_EMO_E911_Viewer_MapServer_5`, `DdwE7LMrYrEMJ_arcgis_rest_services_Addresses_FeatureServer_1`, `JE9B_arcgis_rest_services_Newberg_Addresses__FeatureServer_0` |
| 38 | 3 | `ver_rest_services_ParcelViewer_Parcel_Map_Labels_MapServer_0`, `wlO_arcgis_rest_services_Master_Address_List_FeatureServer_0`, `XhtlWzOFCTkO_arcgis_rest_services_AddressPts_FeatureServer_0` |
| 39 | 3 | `services_BRIC_WRC_Situs_Address_LookUp_Table_FeatureServer_0`, `gis_rest_services_Municipal_Address_Points_FeatureServer_214`, `5n_arcgis_rest_services_City_Limit_Addresses_FeatureServer_0` |
| 40 | 3 | `st_services_Arlington_Addresses_current_view_FeatureServer_0`, `drG_arcgis_rest_services_Arlington_Addresses_FeatureServer_0`, `l_Assessor_parcel_Map_June_06_09_2023_WFL1_FeatureServer_219` |
| 41 | 3 | `e8LteOjzU_arcgis_rest_services_MGO_AddressPt_FeatureServer_0`, `aAg05xQLgo7_arcgis_rest_services_SiteAddress_FeatureServer_0`, `dlWlBxzX_arcgis_rest_services_Searcy_Address_FeatureServer_0` |
| 42 | 3 | `teAddresses_176dcf6d135741fcbc3bf17da5aa7aff_FeatureServer_0`, `cgis_rest_services_Site_Addresses_View_Layer_FeatureServer_0`, `teAddresses_1a8d5e9d05674ad599c70df5dfdd4265_FeatureServer_0` |
| 43 | 3 | `m_jOKMO9vKmc98J4JC_arcgis_rest_services_E911_FeatureServer_0`, `BYQ9pcCt_arcgis_rest_services_e911_pt_txdist_FeatureServer_0`, `rcgis_rest_services_VT_Data___E911_Landmarks_FeatureServer_0` |
| 44 | 3 | `dlWlBxzX_arcgis_rest_services_Marion_Address_FeatureServer_1`, `st_services_VacantResidentialProperties_WFL1_FeatureServer_0`, `is_rest_services_Grady_Site_Addresses_Public_FeatureServer_0` |
| 45 | 3 | `MJrpz61FbvL5t_arcgis_rest_services_Addresses_FeatureServer_0`, `gis_rest_services_AddressList_Update20250311_FeatureServer_0`, `us_server_rest_services_NG911_Address_Points_FeatureServer_3` |
| 46 | 3 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3`, `aR3VIVeAhJdr_arcgis_rest_services_AddressBPs_FeatureServer_0`, `kh71mtnDG_arcgis_rest_services_E911addresses_FeatureServer_0` |
| 47 | 3 | `ELbQdlhsJLcCM_arcgis_rest_services_Addresses_FeatureServer_0`, `t_server_rest_services_Public_Roseburg_Addresses_MapServer_0`, `rcgis_rest_services_Johns_Creek_GA_Addresses_FeatureServer_1` |
| 48 | 3 | `Ia_arcgis_rest_services_County_911_Addresses_FeatureServer_0`, `hP2NPfFE_arcgis_rest_services_Site_Addresses_FeatureServer_0`, `m7axC2dD_arcgis_rest_services_WascoAddresses_FeatureServer_5` |
| 49 | 3 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0`, `arcgis_rest_services_Short_Term_Rentals_WFL1_FeatureServer_1`, `8SWPG8KZ6r_arcgis_rest_services_911Addresses_FeatureServer_0` |
| 50 | 3 | `_arcgis_rest_services_911_Addresses_Website2_FeatureServer_0`, `sses_public_35d07adabaff4ddba616f6f365b8954e_FeatureServer_0`, `ervices_Lee_County_E911_Addresses_and_Roads_FeatureServer_20` |
| 51 | 3 | `rcgis_rest_services_Newberg_Addresses_2_view_FeatureServer_0`, `rent_Site_Addresses_and_Entrance_Points_view_FeatureServer_0`, `KPa_arcgis_rest_services_overture_address_sd_FeatureServer_0` |
| 52 | 3 | `C2HwTkBAlth_arcgis_rest_services_Address_gdb_FeatureServer_0`, `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0`, `kTU5o6Z_arcgis_rest_services_Addressing_AGOL_FeatureServer_0` |
| 53 | 3 | `X_arcgis_rest_services_County_P_Address_View_FeatureServer_0`, `jld0x0gpn_arcgis_rest_services_E911Addresses_FeatureServer_0`, `6Z_arcgis_rest_services_N911_Addresses__View_FeatureServer_0` |
| 54 | 3 | `8hGN_arcgis_rest_services_Polk_Addresses_GAC_FeatureServer_0`, `s_rest_services_Addressing_Addressing_public_FeatureServer_0@MN-1`, `cgis_rest_services_AtascaderoAddresses082025_FeatureServer_0` |
| 55 | 3 | `4OueTcnj_arcgis_rest_services_just_addresses_FeatureServer_0`, `aAg05xQLgo7_arcgis_rest_services_WGS_Address_FeatureServer_0`, `gis_rest_services_GRANT_Address_ClerksOffice_FeatureServer_0` |
| 56 | 3 | `rest_services_Addresses_Clark_County_WI_2019_FeatureServer_0`, `0_arcgis_rest_services_Duncanville_Addresses_FeatureServer_0`, `0_arcgis_rest_services_2022_Sep_01_Addresses_FeatureServer_0` |
| 57 | 3 | `gis_rest_services_SANGIS_AddressAPN_07312024_FeatureServer_0`, `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0`, `So_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 58 | 3 | `ces_911_Address_Street_Review_WFL1_view_only_FeatureServer_0`, `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0`, `ces_Pueblo_County_Addresses_Evacuation_Times_FeatureServer_0` |
| 59 | 3 | `TymXTmwPsPzPHRU_arcgis_rest_services_Address_FeatureServer_0`, `is_rest_services_Master_Address_Database_MAD_FeatureServer_0`, `cjlmqkA8ypi4T_arcgis_rest_services_Addresses_FeatureServer_0` |
| 60 | 3 | `ysZUz_arcgis_rest_services_Carroll_Addresses_FeatureServer_0`, `is_rest_services_Bureau_County_911_Addresses_FeatureServer_0`, `is_rest_services_Cottage_Grove_Address_Point_FeatureServer_0` |
| 61 | 3 | `WuVPEmGK_arcgis_rest_services_Addresses_View_FeatureServer_0`, `1N7Y1EilGjehZ_arcgis_rest_services_ADDRESSES_FeatureServer_0`, `meepNh_arcgis_rest_services_Master_Addresses_FeatureServer_0` |
| 62 | 3 | `pNK5CvU_arcgis_rest_services_HempV_Addresses_FeatureServer_0`, `cgis_rest_services_Skokie_Base_Address_View_FeatureServer_33`, `YdlWlBxzX_arcgis_rest_services_Boone_Address_FeatureServer_0` |
| 63 | 3 | `kIrNAR_arcgis_rest_services_E911_Share_Files_FeatureServer_0`, `wY8_arcgis_rest_services_Address_Ranges_WFL1_FeatureServer_0`, `_rest_services_Oxford_911_Address_View_Layer_FeatureServer_1` |
| 64 | 3 | `m_x7Yxpfpio5GuQWF2_arcgis_rest_services_E911_FeatureServer_0`, `rcgis_rest_services_Mailing_Address_Map_WFL1_FeatureServer_1`, `gis_rest_services_Mailing_Address_Map___WFL1_FeatureServer_1` |
| 65 | 3 | `gis_rest_services_Mailing_Address_Map_2_WFL1_FeatureServer_1`, `_arcgis_rest_services_WyomingCountyAddresses_FeatureServer_0`, `gis_rest_services_Limestone_County_Addresses_FeatureServer_0` |
| 66 | 3 | `xkcSkFAjt_arcgis_rest_services_911_Addresses_FeatureServer_0`, `RnMdg5KWv_arcgis_rest_services_911_Addresses_FeatureServer_0`, `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` |
| 67 | 3 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0`, `is_rest_services_Gloucester_County_Addresses_FeatureServer_0`, `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` |
| 68 | 3 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0`, `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0`, `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` |
| 69 | 3 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0`, `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0`, `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` |
| 70 | 3 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0`, `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0`, `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` |
| 71 | 3 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1`, `cgis_rest_services_AddressesWithElectionData_FeatureServer_0`, `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` |
| 72 | 3 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0`, `arcgis_rest_services_Master_Address_List_New_FeatureServer_0`, `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` |
| 73 | 3 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0`, `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0`, `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` |
| 74 | 3 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0`, `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1`, `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` |
| 75 | 3 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0`, `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0`, `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` |
| 76 | 3 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0`, `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0`, `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` |
| 77 | 3 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0`, `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0`, `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` |
| 78 | 3 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0`, `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0`, `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` |
| 79 | 3 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1`, `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54`, `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` |
| 80 | 3 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0`, `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0`, `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` |
| 81 | 3 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0`, `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0`, `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` |
| 82 | 3 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0`, `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0`, `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` |
| 83 | 3 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0`, `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8`, `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` |
| 84 | 3 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1`, `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20`, `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` |
| 85 | 3 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0`, `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0`, `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` |
| 86 | 3 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76`, `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` |
| 87 | 3 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32`, `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33`, `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` |
| 88 | 3 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0`, `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0`, `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` |
| 89 | 3 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0`, `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0`, `vices_Campbell_County__VA_Broadband_Map_WFL1_FeatureServer_0` |
| 90 | 3 | `ices_City_of_Cuyahoga_Falls_Addressing_WFL1_FeatureServer_11`, `_arcgis_rest_services_TehamaCounty_NG911_gdb_FeatureServer_8`, `rest_services_Hurricane_Ian_Damage_Addresses_FeatureServer_0` |
| 91 | 3 | `est_services_Street_Sweeping_Pilot_Addresses_FeatureServer_0`, `rcgis_rest_services_Bedford_County_Addresses_FeatureServer_0`, `_arcgis_rest_services_Logan_County_Addresses_FeatureServer_0` |
| 92 | 3 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24`, `8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1`, `TOM4lipn_arcgis_rest_services_Addresses_2023_FeatureServer_0` |
| 93 | 3 | `4x6y8cTIstSBE_arcgis_rest_services_Addresses_FeatureServer_0`, `xLBcrikqFM0vkoy_arcgis_rest_services_Address_FeatureServer_0`, `Mk18pL_arcgis_rest_services_Coffee_Addresses_FeatureServer_0` |
| 94 | 3 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1`, `DgvxltnFwP_arcgis_rest_services_NG911_Layers_FeatureServer_1`, `is_rest_services_Lead_Service_Line_Addresses_FeatureServer_0` |
| 95 | 3 | `_arcgis_rest_services_EnerGov_Test_Map1_WFL1_FeatureServer_3`, `s_rest_services_Rural_Addresses__Label_Only__FeatureServer_0`, `rcgis_rest_services_Buildings_and_Addresses_FeatureServer_17` |
| 96 | 3 | `aLg_arcgis_rest_services_Address_Hemet031325_FeatureServer_0`, `ez8fHeIiDRbgb_arcgis_rest_services_Addresses_FeatureServer_0`, `arcgis_rest_services_FranklinCountyAddresses_FeatureServer_0` |
| 97 | 3 | `Uiqh7X11gGV2d_arcgis_rest_services_Addresses_FeatureServer_0`, `VDElDOMEad_arcgis_rest_services_WayneAddress_FeatureServer_0`, `rest_services_Cherokee_Address_Analysis_WFL1_FeatureServer_0` |
| 98 | 3 | `BpZX2wFbS_arcgis_rest_services_911addressing_FeatureServer_0`, `JRr_arcgis_rest_services_MAT_NG911_Addresses_FeatureServer_0`, `j7VSF_arcgis_rest_services_TemeculaAddresses_FeatureServer_0` |
| 99 | 3 | `_arcgis_rest_services_zoningAddressingSearch_FeatureServer_0`, `st_services_Vector_Tile_Site_Address_Labels_FeatureServer_57`, `cgis_rest_services_Riley_County_KS_Addresses_FeatureServer_0` |
| 100 | 3 | `yvfv_arcgis_rest_services_Mercer_SiteAddress_FeatureServer_0`, `S1a_arcgis_rest_services_Address_Mailing_Map_FeatureServer_1`, `1_arcgis_rest_services_Longview_TX_Addresses_FeatureServer_0` |
| 101 | 3 | `cgis_rest_services_Franklin_Co_911_Addresses_FeatureServer_0`, `cgis_rest_services_FranklinCoVA_911Addresses_FeatureServer_0`, `WCoI_arcgis_rest_services_20260601_Addresses_FeatureServer_0` |
| 102 | 3 | `rcgis_rest_services_Essex_Address_Pts_9_9_25_FeatureServer_0`, `cgis_rest_services_Sarpy_County_NE_Addresses_FeatureServer_1`, `kOGGtW27pGICf_arcgis_rest_services_Addresses_FeatureServer_0` |
| 103 | 3 | `cgis_rest_services_Master_Addresses_for_Grid_FeatureServer_0`, `pMfHt82xFG_arcgis_rest_services_RouteAddress_FeatureServer_0`, `1p_arcgis_rest_services_ADDRESS_20230403_CoB_FeatureServer_0` |
| 104 | 3 | `maps_rest_services_OPENDATA_RegionalBaseOpenData_MapServer_2`, `_arcgis_rest_services_Civic_Rec_QC_Addresses_FeatureServer_0`, `arcgis_rest_services_OpenNewmarket_Addresses_FeatureServer_0` |
| 105 | 3 | `s_rest_services_OPENNewmarket_Address_3_view_FeatureServer_0`, `arcgis_rest_services_Alexandria_VA_Addresses_FeatureServer_0`, `fMdTkPeHLCobS_arcgis_rest_services_Addresses_FeatureServer_0` |
| 106 | 3 | `_map_claycountymn_gov_arcgis_rest_services_NG911_MapServer_0`, `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13`, `PlhvQwvs_arcgis_rest_services_E911_Addrs_Pts_FeatureServer_0` |
| 107 | 3 | `rcgis_rest_services_CTSI_AddressChecker_WFL1_FeatureServer_0`, `s_rest_services_CTSI_Address_Check_2023_WFL1_FeatureServer_0`, `rOyyLV2jNLiBS_arcgis_rest_services_Addresses_FeatureServer_0` |
| 108 | 3 | `ofS_arcgis_rest_services_Taos_E911_Addresses_FeatureServer_0`, `gT_arcgis_rest_services_USU_Addressing_view_FeatureServer_26`, `s_Meade_Co_KY_Addresses_Roads_Lot_Lines_WFL1_FeatureServer_0` |
| 109 | 3 | `ervices_Meade_Co_KY_Addresses_and_Roads_WFL1_FeatureServer_1`, `CSVXisSNlAAjd_arcgis_rest_services_Addresses_FeatureServer_0`, `zUpjDtspiBG0j_arcgis_rest_services_E911_Copy_FeatureServer_0` |
| 110 | 3 | `_arcgis_rest_services_Flagstaff_AZ_Addresses_FeatureServer_0`, `QYTTiP6CrfEsw_arcgis_rest_services_Addresses_FeatureServer_0`, `is_rest_services_Madison_County_KY_Addresses_FeatureServer_1` |
| 111 | 3 | `rest_services_CarthageWardsandaddresses_WFL1_FeatureServer_1`, `Ypus4pYH0S_arcgis_rest_services_Site_Address_FeatureServer_4`, `rcgis_rest_services_Daly_City_Addresses_AGOL_FeatureServer_2` |
| 112 | 3 | `TiP6CrfEsw_arcgis_rest_services_Ward_Address_FeatureServer_0`, `d_Waste__Days_of_Service_Per_Address_092424_FeatureServer_52`, `arcgis_rest_services_MGO_Master_Address_View_FeatureServer_0` |
| 113 | 3 | `rcgis_rest_services_Res_Address_Demographics_FeatureServer_1`, `y_us_arcgis_rest_services_Addresses_WC_2022_FeatureServer_54`, `p_arcgis_rest_services_LAFO_ADDRESS_12_17_13_FeatureServer_0` |
| 114 | 3 | `m_nEIrIdcFpdK28ibf_arcgis_rest_services_E911_FeatureServer_1`, `u6oHu4Z_arcgis_rest_services_SITUS_PUB_CBB_2_FeatureServer_0`, `IzAwdHlO_arcgis_rest_services_Address_hosted_FeatureServer_0` |
| 115 | 3 | `1_arcgis_rest_services_Bismarck_ND_Addresses_FeatureServer_0`, `q_arcgis_rest_services_Site_Addresses_Public_FeatureServer_0`, `is_rest_services_Public_View_Site_Addresses__FeatureServer_0` |
| 116 | 3 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1`, `OU_arcgis_rest_services_Addresses_SIO_Hosted_FeatureServer_0`, `t_services_SummitCntyCO_Addresses_Pictometry_FeatureServer_0` |
| 117 | 3 | `gis_com_kcsgis_rest_services_Etowah_AL31_VAM_MS_MapServer_10`, `s_rest_services_Master_Address_List_Aug_2026_FeatureServer_0`, `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` |
| 118 | 3 | `est_services_NormanResidentialTrashAddresses_FeatureServer_0`, `3kMP_arcgis_rest_services_E911AddressforSOMA_FeatureServer_0`, `s_rest_services_Raleigh_Co_EOC_Address_Sites_FeatureServer_0` |
| 119 | 3 | `s_rest_services_CityAddresses2022bu_CHE_view_FeatureServer_0`, `4Ui_arcgis_rest_services_CityAddresses2022bu_FeatureServer_0`, `unty_oh_gov_arcgisdev_rest_services_WMAS_Address_MapServer_0` |
| 120 | 3 | `27IJC_arcgis_rest_services_Address_Locations_FeatureServer_0`, `_arcgis_rest_services_Addresses_NOT_ELIGIBLE_FeatureServer_0`, `rcgis_rest_services_Unincorporated_Addresses_FeatureServer_0` |
| 121 | 3 | `wFbS_arcgis_rest_services_Chemungaddress_pts_FeatureServer_0`, `2kwz79KUqUvxC_arcgis_rest_services_Addresses_FeatureServer_0`, `71LO_arcgis_rest_services_Addresses_CivQuest_FeatureServer_0` |
| 122 | 3 | `qTGWY_arcgis_rest_services_JoCo_Site_Address_FeatureServer_1`, `county_com_arcgis_rest_services_features_Address_MapServer_0`, `gis_rest_services_CountyAddress2023_CHE_View_FeatureServer_7` |
| 123 | 3 | `I64Ui_arcgis_rest_services_CountyAddress2023_FeatureServer_7`, `ges_arcgis_rest_services_AddressAndRoads2022_FeatureServer_0`, `e_Rollout__Days_of_Service_Per_Address__WFL1_FeatureServer_1` |
| 124 | 3 | `_arcgis_rest_services_BG911_Address_20250501_FeatureServer_0`, `Bq9hgug_arcgis_rest_services_BG911_Addresses_FeatureServer_0`, `Ilt_arcgis_rest_services_Clinton_Address_Pts_FeatureServer_0` |
| 125 | 3 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0`, `Geezhu2j_arcgis_rest_services_E911_Addresses_FeatureServer_0`, `KpsCnqD7H_arcgis_rest_services_SiteAddresses_FeatureServer_0` |
| 126 | 3 | `cgis_rest_services_NRSA_Address_Locator_WFL1_FeatureServer_8`, `aNxg1PvwI_arcgis_rest_services_All_Addresses_FeatureServer_0`, `eajjke_arcgis_rest_services_Addresses_Rogers_FeatureServer_0` |
| 127 | 3 | `EjnCT_arcgis_rest_services_Leander_Addresses_FeatureServer_0`, `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0`, `sses_public_e7c532395de343e38e58a8463128cfb7_FeatureServer_0` |
| 128 | 3 | `teAddresses_ecd2ff39fbb34f39a2ec415fd784331b_FeatureServer_0`, `teAddresses_b786541565b5475593a786a08ba6b3e2_FeatureServer_0`, `sses_public_a000778ae1664a348de916831f1a0ac0_FeatureServer_0` |
| 129 | 3 | `sses_public_0af1fc8b92f7415dbfdf37c6fa956c77_FeatureServer_0`, `teAddresses_1809c74f027741ce815587367a5cfd68_FeatureServer_0`, `teAddresses_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0` |
| 130 | 3 | `teAddresses_25f96256e2164540bc18abbff8a9d5c2_FeatureServer_0`, `sses_public_33e99042997a472fa1a25a8b6f4465cf_FeatureServer_0`, `vN_arcgis_rest_services_SiteAddresses_public_FeatureServer_0` |
| 131 | 3 | `sses_public_3ac05ddeab6d46389b7b3c0616abc861_FeatureServer_0`, `d1DIvN_arcgis_rest_services_SiteAddresses__1_FeatureServer_1`, `sses_public_a2522c3dfde94f6da7500df892abf9aa_FeatureServer_0` |
| 132 | 3 | `sses_public_fa4be22034f14c15a3a589dd7009ca64_FeatureServer_0`, `0JE2L2xUd_arcgis_rest_services_SiteAddresses_FeatureServer_0`, `com_arcgis_rest_services_CommunityAddressing_FeatureServer_0` |
| 133 | 3 | `st_services_A4_Landscape_addressverification_FeatureServer_1`, `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0`, `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` |
| 134 | 3 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1`, `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6`, `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` |
| 135 | 3 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0`, `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11`, `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` |
| 136 | 3 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0`, `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0`, `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` |
| 137 | 3 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0`, `d1_arcgis_rest_services_Visalia_CA_Addresses_FeatureServer_0`, `1Vphzvgd_arcgis_rest_services_City_Addresses_FeatureServer_0` |
| 138 | 3 | `rcgis_rest_services_MC_Address_Pts_PMG_View1_FeatureServer_0`, `rvices_Deerfield_Case_Addresses_FeatureLayer_FeatureServer_0`, `i4lYRFOsss0F5_arcgis_rest_services_Addresses_FeatureServer_0` |
| 139 | 3 | `arcgis_rest_services_Tompkins_County_Address_FeatureServer_0`, `vF0A_arcgis_rest_services_AddressSearchLayer_FeatureServer_0`, `AAWNInLrxvF0A_arcgis_rest_services_TCAddress_FeatureServer_0` |
| 140 | 3 | `s_rest_services_Marathon_County_WI_Addresses_FeatureServer_0`, `WNInLrxvF0A_arcgis_rest_services_Address_gdb_FeatureServer_0`, `InLrxvF0A_arcgis_rest_services_AddressR2_gdb_FeatureServer_0` |
| 141 | 3 | `C2lEIpJ2TRrs5_arcgis_rest_services_Addresses_FeatureServer_0`, `dresses_in_City_Limits___ESD9___Web_Map_WFL1_FeatureServer_1`, `5jlmVkpxP_arcgis_rest_services_Online911Data_FeatureServer_0` |
| 142 | 3 | `gis_rest_services_Queen_Creek_Addresses__All_FeatureServer_0`, `AQdtmx0tv46_arcgis_rest_services_Address_Nye_FeatureServer_6`, `cgis_rest_services_Cedar_Rapids_IA_Addresses_FeatureServer_0` |
| 143 | 3 | `AQncZQEtBv_arcgis_rest_services_Address_Clip_FeatureServer_0`, `Tpwo5_arcgis_rest_services_FullAddress032026_FeatureServer_0`, `_rest_services_Randall_County_Addresses_WFL1_FeatureServer_1` |
| 144 | 3 | `eDUBgTeCT3_arcgis_rest_services_LC_Addresses_FeatureServer_0`, `zOpn2_arcgis_rest_services_Streets_Buidlings_FeatureServer_0`, `arverLink_Address_Lookup_20250623_PublicView_FeatureServer_0` |
| 145 | 3 | `0gE_arcgis_rest_services_CenCom_Address_View_FeatureServer_0`, `is_rest_services_Building_Permit_Addresssing_FeatureServer_0`, `f_arcgis_rest_services_Killeen_AddressPoints_FeatureServer_0` |
| 146 | 3 | `i_rest_services_Cadastral_Site_Address_Point_FeatureServer_0`, `t3XQ_arcgis_rest_services_AddressPt_20230629_FeatureServer_0`, `arcgis_rest_services_AddressPt_20240705_WFL1_FeatureServer_0` |
| 147 | 3 | `rcgis_rest_services_AddressPts_20230817_WFL1_FeatureServer_0`, `U5257_arcgis_rest_services_Yonkers_Addresses_FeatureServer_0`, `_arcgis_rest_services_CharlesCountyAddresses_FeatureServer_0` |
| 148 | 3 | `3P_arcgis_rest_services_SiteAddresses_public_FeatureServer_0@TX-2`, `_pa_us_arcgis_rest_services_Hosted_Addresses_FeatureServer_0`, `CXd1_arcgis_rest_services_Fargo_ND_Addresses_FeatureServer_0` |
| 149 | 3 | `araca_gov_maps_rest_services_LAYERS_RegionalBase_MapServer_2`, `ntaclaraca_gov_maps_rest_services_LAYERS_BaseMap_MapServer_2`, `C0yIuqCBxq_arcgis_rest_services_Address_2024_FeatureServer_0` |
| 150 | 3 | `Cz_arcgis_rest_services_HC_MD_Addresses_10mi_FeatureServer_0`, `ld_oh_us_arcgis_rest_services_OpenData_Addresses_MapServer_0`, `_arcgis_rest_services_Addresses_USA_combined_FeatureServer_0` |
| 151 | 3 | `arcgis_rest_services_modified_JaCo_addresses_FeatureServer_0`, `wLs3iGyK80EW_arcgis_rest_services_911Address_FeatureServer_0`, `C_arcgis_rest_services_Active_Addresses_2025_FeatureServer_0` |
| 152 | 3 | `jSxUKayj_arcgis_rest_services_911_Addresses_FeatureServer_58`, `5V8PH7DzSE6AU_arcgis_rest_services_Addresses_FeatureServer_0`, `zxvnVEjzQ6xuSXS_arcgis_rest_services_Address_FeatureServer_0` |
| 153 | 3 | `Spu5VOlu_arcgis_rest_services_Site_Addresses_FeatureServer_0`, `I64Ui_arcgis_rest_services_WLAddressAndRoads_FeatureServer_0`, `t_services_Katy_ISD_Harris_County_Addresses_FeatureServer_68` |
| 154 | 3 | `ov_public_rest_services_public_Council_Wards_FeatureServer_1`, `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0`, `_rest_services_EmergencyManagement_Addresses_FeatureServer_0` |
| 155 | 3 | `mxCAS_arcgis_rest_services_ClermontAddresses_FeatureServer_0`, `iJkq4oXsPh_arcgis_rest_services_Addresses_SR_FeatureServer_0`, `is_rest_services_AddressValidationTest2_WFL1_FeatureServer_0` |
| 156 | 3 | `_arcgis_rest_services_BILLING_ACCT_LOCATIONS_FeatureServer_0`, `k6RO1_arcgis_rest_services_HudsonCty_AddrPts_FeatureServer_0`, `arcgis_rest_services_Hudson_County_Addresses_FeatureServer_0` |
| 157 | 3 | `u0_arcgis_rest_services_Address_OfflineCopy_FeatureServer_21`, `ntygov_com_server_rest_services_Addresses_Public_MapServer_0`, `is_rest_services_Forsyth_County_GA_Addresses_FeatureServer_0` |
| 158 | 3 | `is_rest_services_NM911_Address_202301_SC_Web_FeatureServer_0`, `gis_rest_services_Address_For_WebApp_Locator_FeatureServer_0`, `_rest_services_NM911_Address_202401_SC_Web_a_FeatureServer_0` |
| 159 | 3 | `nQPdJ0azuLyn_arcgis_rest_services_AddressPts_FeatureServer_0`, `st_services_Springfield_address_density_WFL1_FeatureServer_2`, `VWAC8iN_arcgis_rest_services_road_centerline_FeatureServer_0` |
| 160 | 3 | `F_arcgis_rest_services_NM911_Address_10_2024_FeatureServer_0`, `F_arcgis_rest_services_NM911_Address_02_2025_FeatureServer_0`, `arcgis_rest_services_NM911_Address_202506_SC_FeatureServer_0` |
| 161 | 3 | `wbCJ2GMP_arcgis_rest_services_E911calls_2020_FeatureServer_0`, `s_rest_services_NM911_Address_01_2026_SC_Web_FeatureServer_0`, `r_arcgis_rest_services_Coryell_address_5Mile_FeatureServer_0` |
| 162 | 3 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0`, `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0`, `tg2A1_arcgis_rest_services_vw_dist_addresses_FeatureServer_0` |
| 163 | 3 | `cgis_rest_services_Delaware_County_E911_Data_FeatureServer_0`, `GEllMqef1LMjj_arcgis_rest_services_Addresses_FeatureServer_0`, `vices_Yuma_911_Data_Roads_and_Addresses_WFL1_FeatureServer_0` |
| 164 | 3 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0`, `V5FXPLX_arcgis_rest_services_Addresses_Units_FeatureServer_0`, `McTk2tV5FXPLX_arcgis_rest_services_Addresses_FeatureServer_0` |
| 165 | 3 | `s_rest_services_ElectionsPollingPlaceAddress_FeatureServer_0`, `LmXo7Hn9vNc_arcgis_rest_services_E911Address_FeatureServer_0`, `GOi6N4Rq5cqFv_arcgis_rest_services_Addresses_FeatureServer_0` |
| 166 | 3 | `rvices_Situs_for_ConsolidatedPrecincts_AGOL_FeatureServer_51`, `4427d57d2827830_rest_services_Base_Addresses_FeatureServer_0`, `CRg_arcgis_rest_services_SBCnty_Address_Grid_FeatureServer_0` |
| 167 | 3 | `aVKdPC5e_arcgis_rest_services_Address_Public_FeatureServer_0`, `is_rest_services_Addresses_CitizenServe_View_FeatureServer_0`, `tUCmxaVKdPC5e_arcgis_rest_services_Addresses_FeatureServer_0` |
| 168 | 3 | `JdBHI0_arcgis_rest_services_Addresses_SC_USE_FeatureServer_0`, `t_services_NG911_Map__Lake_County__Ohio_WFL1_FeatureServer_0`, `rvices_WCAddresses20251003_gdb_view_Geocivix_FeatureServer_0` |
| 169 | 3 | `is_rest_services_Addresses_2015_Boston_BARI__FeatureServer_0`, `ervices_64a951f0_b017_11e6_b4e3_22000b8406af_FeatureServer_0`, `est_services_Collier_Addresses_Within_3_Mile_FeatureServer_0` |
| 170 | 3 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0`, `8JRPoNeQjgcLi_arcgis_rest_services_Addresses_FeatureServer_0`, `wbHlfF_arcgis_rest_services_Addresses_Hosted_FeatureServer_0` |
| 171 | 3 | `cgis_rest_services_Infrastructure_Transportation_MapServer_0`, `_services_Infrastructure_Transportation_Sheriffs_MapServer_0`, `ABcyiF_arcgis_rest_services_Address_pt_views_FeatureServer_0` |
| 172 | 3 | `_arcgis_rest_services_city_address_march2025_FeatureServer_0`, `_rest_services_HenricoCountyGIS_05082023_gdb_FeatureServer_0`, `cgis_rest_services_Indianapolis_IN_Addresses_FeatureServer_0` |
| 173 | 3 | `ervices_Zanna_E911_Sites_Outside_8min_Buffer_FeatureServer_2`, `LmYGD_arcgis_rest_services_DC_Addresses_WFL1_FeatureServer_0`, `rcgis_rest_services_HostedServices_Addresses_FeatureServer_0` |
| 174 | 3 | `is_rest_services_Barry_County_E911_Map_WFL1_FeatureServer_29`, `rvices_stratmap19_addresspoints_48027_vector_FeatureServer_0`, `rvices_MapServices_TLC_OverlayAddressSearch_D_WM_MapServer_0` |
| 175 | 3 | `C7QlRK1kZ_arcgis_rest_services_EAS_Addresses_FeatureServer_0`, `countyfl_gov_accelasupp_rest_services_AccelaXAPO_MapServer_0`, `leoncountyfl_gov_accela_rest_services_AccelaXAPO_MapServer_0` |
| 176 | 3 | `ountyfl_gov_accela_rest_services_AccelaXAPO_Test_MapServer_0`, `st_services_Vector_COT_UtilityERM_Addresses_D_WM_MapServer_0`, `LxyiJoNiVHKwq_arcgis_rest_services_Addresses_FeatureServer_0` |
| 177 | 3 | `arcgis_rest_services_Addresses_Arcade_Labels_FeatureServer_0`, `QGwSSLC0l_arcgis_rest_services_t07_Addresses_FeatureServer_0`, `j7_arcgis_rest_services_Addresses_GeneralUse_FeatureServer_0` |
| 178 | 3 | `s_rest_services_Solano_County_Addresses_WFL1_FeatureServer_0`, `_rest_services_Site_Addresses_FLOCK_10302024_FeatureServer_0`, `_services_Rutherford_Site_Addresses_11012024_FeatureServer_0` |
| 179 | 3 | `gis_rest_services_NENA_Addresses_WGS_Service_FeatureServer_0`, `rest_services_E911_Addresses_Hamilton_County_FeatureServer_0`, `rcgis_rest_services_Addressing_RoadsAndAddresses_MapServer_0` |
| 180 | 3 | `W83eUIFui_arcgis_rest_services_Address_Sites_FeatureServer_0`, `couver_us_arcgis_rest_services_common_BasemapPUB_MapServer_0`, `cGIS_rest_services_Baldwin911Addresses__view_FeatureServer_2` |
| 181 | 3 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2`, `SE6sXfoLq_arcgis_rest_services_Address_ProdA_FeatureServer_0`, `ervices_AddressPts_DamageAssessment_REA_VIEW_FeatureServer_0` |
| 182 | 3 | `_rest_services_Address__GCS_WGS_1984__Public_FeatureServer_0`, `vices_BaseLayers_BaseLayers_for_BackdropPurposes_MapServer_1`, `rvices_BaseLayers_Addresses_for_BackdropPurposes_MapServer_0` |
| 183 | 3 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0`, `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0`, `i_arcgis_rest_services_Ada_County_Addresses_FeatureServer_13` |
| 184 | 3 | `services_Zanna_E911_Sites_Within_8min_Buffer_FeatureServer_1`, `services_CountyServices_Municipal_Addressing_FeatureServer_2`, `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` |
| 185 | 3 | `M5ymMLbxIyWTjn2_arcgis_rest_services_Address_FeatureServer_0`, `is_rest_services_Chester_County_PA_Addresses_FeatureServer_0`, `rcgis_rest_services_Address_Pts_Living_Units_FeatureServer_0` |
| 186 | 3 | `_Zs2aNLFN00jrS4gG_arcgis_rest_services_data2_FeatureServer_0`, `ZHFr6zdgNZuVG0_arcgis_rest_services_Address2_FeatureServer_3`, `arcgis_rest_services_Jeffco_Address_Map_WFL1_FeatureServer_1` |
| 187 | 3 | `MCHD_Environmental_Health_Public_Service_Map_FeatureServer_0`, `_arcgis_rest_services_AMI_Deployment_Address_FeatureServer_0`, `27_Great_Mississippi_Flood_in_Arkansas_WFL1_FeatureServer_14` |
| 188 | 3 | `_services_Lower_MS_Sediment_Bottleneck_WFL1_FeatureServer_14`, `_Mississippi_Flood_in_Arkansas__Final__WFL1_FeatureServer_14`, `_rest_services_Atlanta_Streets_and_Addresses_FeatureServer_0` |
| 189 | 3 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12`, `xLqeJd2jOX_arcgis_rest_services_VC_Addresses_FeatureServer_0`, `oN_arcgis_rest_services_WASD_Addresses_3_23_FeatureServer_52` |
| 190 | 3 | `0yIuqCBxq_arcgis_rest_services_CNO_Addresses_FeatureServer_0`, `arcgis_rest_services_Nightly_OpenData_Update_FeatureServer_3`, `server_rest_services_Intermap_Situs_address_WMAS_MapServer_0` |
| 191 | 3 | `is_rest_services_Address_1424300337393713068_FeatureServer_0`, `rcgis_rest_services_Richfield_Comm_Addresses_FeatureServer_0`, `w_arcgis_rest_services_Addresses_not_in_Town_FeatureServer_5` |
| 192 | 3 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2`, `_rest_services_Arapahoe_County_Addresses_gdb_FeatureServer_0`, `hedVoters_Statewide_withSiteTypeDescription_FeatureServer_32` |
| 193 | 1 | `jvohPcWJU5ij6_arcgis_rest_services_Addresses_FeatureServer_0` |

## 三、差额最大的 10 层

| 层 | 声明 | 实采 | 差额 | 状态 | 原因 |
|---|---|---|---|---|---|
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,057 | 0 | 209,057 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,155 | 0 | 207,155 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,155 | 0 | 207,155 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,648 | 0 | 125,648 | failed | rc=1 err=? |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,600 | 98,714 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Inval |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,291 | 0 | 93,291 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 56,800 | failed | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 50,911 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 50,423 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |
| `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 49,374 | failed | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input pa |

## 四、残缺层清单（failed / partial，逐条原因）

| 层 | 状态 | 声明 | 实采 | 原因 |
|---|---|---|---|---|
| `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | failed | 209057 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | failed | 207155 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | failed | 207155 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` | partial | 181471 | 363000 | 缺口 -100.03%（实采 363000 / 声明 181471）；跨轮：上轮已有 4 个单元包，本轮只补缺口 |
| `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | failed | 125648 | 0 | rc=1 err=? |
| `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | failed | 100314 | 1600 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Cannot perform query. Invalid query parameters.", "details": ["Unab |
| `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | failed | 93291 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` | partial | 81784 | 163221 | 缺口 -99.58%（实采 163221 / 声明 81784）；跨轮：上轮已有 2 个单元包，本轮只补缺口 |
| `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | failed | 56888 | 88 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | partial | 56599 | 113267 | 缺口 -100.12%（实采 113267 / 声明 56599） |
| `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | partial | 54644 | 109268 | 缺口 -99.96%（实采 109268 / 声明 54644） |
| `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | partial | 51423 | 102815 | 缺口 -99.94%（实采 102815 / 声明 51423） |
| `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | failed | 50911 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | failed | 50423 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | failed | 49374 | 0 | rc=1 err=query_fail:svcerr:{"code": 400, "message": "Invalid or missing input parameters.", "details": []} |
| `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | failed | 40675 | 0 | rc=1 err=batch0:http404:<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1 |
| `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | failed | 39743 | 39503 | rc=1 err=?；跨轮：上轮已有 1 个单元包，本轮只补缺口 |
| `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | partial | 26410 | 52891 | 缺口 -100.27%（实采 52891 / 声明 26410） |
| `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | partial | 26320 | 52635 | 缺口 -99.98%（实采 52635 / 声明 26320） |
| `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | partial | 25834 | 51668 | 缺口 -100.00%（实采 51668 / 声明 25834） |
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
| `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `county_com_arcgis_rest_services_features_Address_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |
| `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | failed | None | None | job 内单层超时 60 分钟（--layer-timeout） |

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
| 12 | `IABSMeJD_arcgis_rest_services_address_points_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 13 | `_arcgis_rest_services_Ventura_Address_Points_FeatureServer_0` | 285,259 | 285,259 | 0.00% | ok |
| 14 | `arcgis_rest_services_VNC_MasterAddressPoints_FeatureServer_0` | 285,257 | 285,257 | 0.00% | ok |
| 15 | `n1c_arcgis_rest_services_Address_Points_2026_FeatureServer_0` | 283,921 | 283,921 | 0.00% | ok |
| 16 | `rcgis_rest_services_Address_Points_SHAPE_UTM_FeatureServer_0` | 282,952 | 282,952 | 0.00% | ok |
| 17 | `t_services_Montgomery_County_Address_Points_FeatureServer_14` | 282,669 | 282,669 | 0.00% | ok |
| 18 | `vices_Planning_COGCC_LC_Oil_Gas_Wells_Published_MapServer_77` | 281,510 | 281,510 | 0.00% | ok |
| 19 | `gVyYKfYgW5Nxb1V_arcgis_rest_services_Address_FeatureServer_0` | 281,361 | 281,361 | 0.00% | ok |
| 20 | `Xx_arcgis_rest_services_Address_Point_Native_FeatureServer_0` | 279,406 | 279,406 | 0.00% | ok |
| 21 | `ices_Address_Points_Site_AddressPoints_NG911_FeatureServer_0` | 279,299 | 279,299 | 0.00% | ok |
| 22 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-1` | 279,299 | 279,299 | 0.00% | ok |
| 23 | `tN2gn8MMx1p_arcgis_rest_services_ADDRESS_pts_FeatureServer_0` | 279,000 | 279,000 | 0.00% | ok |
| 24 | `rcgis_rest_services_OpenData_Structure_OpenData_MapServer_12` | 277,815 | 277,815 | 0.00% | ok |
| 25 | `is_rest_services_Waste_Collection_by_Address_FeatureServer_0` | 277,731 | 277,731 | 0.00% | ok |
| 26 | `_gov_dev_rest_services_Planning_AddressPoint_FeatureServer_0` | 276,955 | 276,955 | 0.00% | ok |
| 27 | `XBIeLonX0V_arcgis_rest_services_AddressPoint_FeatureServer_0` | 276,594 | 276,594 | 0.00% | ok |
| 28 | `H5m5JyP_arcgis_rest_services_Address_Points_FeatureServer_21` | 275,376 | 275,376 | 0.00% | ok |
| 29 | `lN_arcgis_rest_services_Ada_County_Addresses_FeatureServer_0` | 275,375 | 275,375 | 0.00% | ok |
| 30 | `782eMbySr2srL_arcgis_rest_services_Addresses_FeatureServer_1` | 274,737 | 274,737 | 0.00% | ok |
| 31 | `gd_arcgis_rest_services_NHCRWA_AddressPoints_FeatureServer_0` | 269,633 | 269,633 | 0.00% | ok |
| 32 | `or_us_server_rest_services_baselayers_Taxlots_SP_MapServer_1` | 268,271 | 268,271 | 0.00% | ok |
| 33 | `us_server_rest_services_Open_Data_Open_Data_AGOL_MapServer_0` | 268,271 | 268,271 | 0.00% | ok |
| 34 | `Lhk48K7A_arcgis_rest_services_Address_Labels_FeatureServer_0` | 268,122 | 268,122 | 0.00% | ok |
| 35 | `vYeDEj7_arcgis_rest_services_zs_sub_poc_bytu_FeatureServer_0` | 267,620 | 267,620 | 0.00% | ok |
| 36 | `cX_arcgis_rest_services_NG911_Address_Points_FeatureServer_0` | 264,791 | 264,791 | 0.00% | ok |
| 37 | `rcgis_rest_services_AddressPoints_20220127v4_FeatureServer_0` | 264,259 | 264,259 | 0.00% | ok |
| 38 | `st_services_WR_Address_Points_September_2025_FeatureServer_0` | 263,704 | 263,704 | 0.00% | ok |
| 39 | `gis_rest_services_PSAP_Address_Points_Hosted_FeatureServer_0` | 263,523 | 263,523 | 0.00% | ok |
| 40 | `id_arcgis_rest_services_RBI_18_RBI_25_50_250_wms_MapServer_0` | 263,144 | 263,144 | 0.00% | ok |
| 41 | `FVZ_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 260,237 | 260,237 | 0.00% | ok |
| 42 | `vices_LojicSolutions_OpenDataHistoricAddressing_MapServer_22` | 260,087 | 260,087 | 0.00% | ok |
| 43 | `_hosted_rest_services_Address_Address_Points_FeatureServer_0` | 258,903 | 258,903 | 0.00% | ok |
| 44 | `h_net_hosted_rest_services_AddressPoints_DBC_FeatureServer_0` | 258,903 | 258,903 | 0.00% | ok |
| 45 | `_org_ArcGIS_rest_services_APPS_OperationalLayers_MapServer_8` | 230,438 | 230,438 | 0.00% | ok |
| 46 | `vt_nz_arcgis_rest_services_CorporateData_Address_MapServer_0` | 209,057 | 0 | 100.00% | failed |
| 47 | `v_gis_rest_services_Map_Reference_Street_Address_MapServer_0` | 207,155 | 0 | 100.00% | failed |
| 48 | `ov_gis_rest_services_Map_Reference_Address_Label_MapServer_0` | 207,155 | 0 | 100.00% | failed |
| 49 | `qKAFwdGU_arcgis_rest_services_Address_Points_FeatureServer_0` | 181,471 | 363,000 | -100.03% | partial |
| 50 | `ices_Corporate_Address_Gazetteer_Punlic_View_FeatureServer_1` | 166,242 | 166,242 | 0.00% | ok |
| 51 | `nc_gov_server_rest_services_CityWorks_Basemap_CW_MapServer_0` | 125,648 | 0 | 100.00% | failed |
| 52 | `_com_gis_rest_services_Public_Site_Addresses_FeatureServer_2` | 109,378 | 109,378 | 0.00% | ok |
| 53 | `unty_us_arcgis_rest_services_maps_Open_Data_FeatureServer_52` | 109,140 | 109,140 | 0.00% | ok |
| 54 | `fy5ay_arcgis_rest_services_propertyaddresses_FeatureServer_0` | 109,006 | 109,006 | 0.00% | ok |
| 55 | `rest_services_WEB_PUBLICATIONS_County_Map_Layers_MapServer_6@未定位-1` | 108,946 | 108,946 | 0.00% | ok |
| 56 | `rest_services_WEB_PUBLICATIONS_County_Map_Layers_MapServer_6@未定位-2` | 108,946 | 108,946 | 0.00% | ok |
| 57 | `rateReferenceLayers_CorporateReferenceLayers_FeatureServer_3` | 108,683 | 108,683 | 0.00% | ok |
| 58 | `_washco_utah_gov_arcgis_rest_services_Addressing_MapServer_0` | 108,238 | 108,238 | 0.00% | ok |
| 59 | `is_rest_services_Chula_Vista_Address_Points_FeatureServer_13` | 107,770 | 107,770 | 0.00% | ok |
| 60 | `9q8g_arcgis_rest_services_Address_Point_File_FeatureServer_0` | 107,685 | 107,685 | 0.00% | ok |
| 61 | `s_rest_services_Address_Points_by_SWDD_CLASS_FeatureServer_0` | 107,344 | 107,344 | 0.00% | ok |
| 62 | `_gov_server2_rest_services_GeneralUse_Open_Data_MapServer_17` | 107,068 | 107,068 | 0.00% | ok |
| 63 | `xaar_arcgis_rest_services_Site_Address___911_FeatureServer_0` | 106,941 | 106,941 | 0.00% | ok |
| 64 | `4zdJEFmiY_arcgis_rest_services_Address_Point_FeatureServer_0` | 106,694 | 106,694 | 0.00% | ok |
| 65 | `rest_services_Address_Points_St_Louis_County_FeatureServer_0` | 106,680 | 106,680 | 0.00% | ok |
| 66 | `gis_rest_services_AddressVerification_Points_FeatureServer_0` | 106,518 | 106,518 | 0.00% | ok |
| 67 | `for_Countywide_FeeParcel_Evaluation_Analysis_FeatureServer_1` | 106,083 | 106,083 | 0.00% | ok |
| 68 | `DyZ77wYt_arcgis_rest_services_Address_Point1_FeatureServer_0` | 105,564 | 105,564 | 0.00% | ok |
| 69 | `is_rest_services_AddressVerification_PROTest_FeatureServer_0` | 105,563 | 105,563 | 0.00% | ok |
| 70 | `ervices_AGO_HarrisonCounty_PhysicalAddresses_FeatureServer_0` | 105,474 | 105,474 | 0.00% | ok |
| 71 | `_data_DATA_LOADER_SiteStructureAddressPoints_FeatureServer_0` | 105,437 | 105,437 | 0.00% | ok |
| 72 | `Z77wYt_arcgis_rest_services_Address_Point_DC_FeatureServer_0` | 105,198 | 105,198 | 0.00% | ok |
| 73 | `es_EnterprisePublishing_WhatcomCo_Administrative_MapServer_4` | 104,607 | 104,607 | 0.00% | ok |
| 74 | `IeLonX0V_arcgis_rest_services_AddressPointCC_FeatureServer_0` | 104,135 | 104,135 | 0.00% | ok |
| 75 | `n9vNc_arcgis_rest_services_RealEstateAddress_FeatureServer_0` | 104,108 | 104,108 | 0.00% | ok |
| 76 | `com_server_rest_services_Site_Address_Points_FeatureServer_0` | 104,075 | 104,075 | 0.00% | ok |
| 77 | `_arcgis_rest_services_LB_Site_Address_Points_FeatureServer_0` | 103,980 | 103,980 | 0.00% | ok |
| 78 | `ervices_E911_Addresses_Active_Address_Points_FeatureServer_0` | 103,938 | 103,938 | 0.00% | ok |
| 79 | `gis_rest_services_Address_Points_Nov_17_2025_FeatureServer_0` | 103,723 | 103,723 | 0.00% | ok |
| 80 | `1yz8_arcgis_rest_services_LocalAddressSearch_FeatureServer_0` | 103,176 | 103,176 | 0.00% | ok |
| 81 | `ounty_gov_ext_rest_services_Public_Addresses_FeatureServer_0` | 103,061 | 103,061 | 0.00% | ok |
| 82 | `t_services_YoloCounty_OpenData_AddressPoints_FeatureServer_3` | 102,821 | 102,821 | 0.00% | ok |
| 83 | `gov_arcgis_rest_services_Open_Data_Addresses_FeatureServer_4` | 101,641 | 101,641 | 0.00% | ok |
| 84 | `Di_arcgis_rest_services_Addresses__Open_Data_FeatureServer_0` | 101,641 | 101,641 | 0.00% | ok |
| 85 | `vices_SAM_Addresses_for_BERDO_2020_Buildings_FeatureServer_0` | 101,615 | 101,615 | 0.00% | ok |
| 86 | `cture_Address_Points_of_Washington_County_PA_FeatureServer_1` | 101,482 | 101,482 | 0.00% | ok |
| 87 | `erver_rest_services_SCData_VotingPrecinctsWebMap_MapServer_2` | 101,043 | 101,043 | 0.00% | ok |
| 88 | `cgis_rest_services_PropertyAndBoundaries_Address_MapServer_0` | 101,036 | 101,036 | 0.00% | ok |
| 89 | `ymNNZ2_arcgis_rest_services_Address_Points_FeatureServer_156` | 100,971 | 100,971 | 0.00% | ok |
| 90 | `rcgis_rest_services_Address_Point_Extraction_FeatureServer_0` | 100,695 | 100,695 | 0.00% | ok |
| 91 | `jZTGW_arcgis_rest_services_SQL2_Address_view_FeatureServer_0` | 100,695 | 100,695 | 0.00% | ok |
| 92 | `vices_Join_Features_to_Address_Points_2_view_FeatureServer_0` | 100,314 | 1,600 | 98.41% | failed |
| 93 | `fnAgB_arcgis_rest_services_Weber_address_pts_FeatureServer_0` | 100,184 | 100,184 | 0.00% | ok |
| 94 | `_arcgis_rest_services_AddressPoints_1Spatial_FeatureServer_0` | 99,815 | 99,815 | 0.00% | ok |
| 95 | `gis_rest_services_SiteStructureAddressPoints_FeatureServer_0@未定位-4` | 99,774 | 99,774 | 0.00% | ok |
| 96 | `est_services_Orland_Park_Address_Points_2022_FeatureServer_0` | 99,315 | 99,315 | 0.00% | ok |
| 97 | `Ljlp7_arcgis_rest_services_ParcelsAndAddress_FeatureServer_0` | 98,939 | 98,939 | 0.00% | ok |
| 98 | `_rest_services_CityCounty_addresspoints_view_FeatureServer_0` | 98,399 | 98,399 | 0.00% | ok |
| 99 | `s_rest_services_CityCounty_addresspoint_view_FeatureServer_0` | 98,399 | 98,399 | 0.00% | ok |
| 100 | `rcgis_rest_services_AddressPointsRentalUnits_FeatureServer_0` | 97,090 | 97,090 | 0.00% | ok |
| 101 | `st_services_Auditor_Address_Points_June_2019_FeatureServer_0` | 96,818 | 96,818 | 0.00% | ok |
| 102 | `net_arcgis_rest_services_HubLayers_Addresses_FeatureServer_0` | 96,796 | 96,796 | 0.00% | ok |
| 103 | `is_rest_services_FUSD_AddressPoints_20241007_FeatureServer_0` | 96,737 | 96,737 | 0.00% | ok |
| 104 | `c_com_arcgis_rest_services_Elections_SupDist2021_MapServer_1` | 96,621 | 96,589 | 0.03% | ok |
| 105 | `JbeSi1G6zWeN_arcgis_rest_services_KC_Address_FeatureServer_1` | 96,505 | 96,505 | 0.00% | ok |
| 106 | `NTUHp_arcgis_rest_services_2022AddressPoints_FeatureServer_0` | 96,462 | 96,462 | 0.00% | ok |
| 107 | `5OXNGFDn_arcgis_rest_services_Address_Points_FeatureServer_2` | 96,211 | 96,211 | 0.00% | ok |
| 108 | `sPajnMahHp6RYgB_arcgis_rest_services_Base_FS_FeatureServer_0` | 96,204 | 96,204 | 0.00% | ok |
| 109 | `_rest_services_First_Due_Address_Points_WFL1_FeatureServer_0` | 95,990 | 95,990 | 0.00% | ok |
| 110 | `YRWV44nBqV_arcgis_rest_services_SC_Addresses_FeatureServer_0` | 95,161 | 95,161 | 0.00% | ok |
| 111 | `s_to_All_Bell_County_Voter_Address_Points_v6_FeatureServer_0` | 95,048 | 95,048 | 0.00% | ok |
| 112 | `st_services_VoterRegistrationAddress_Public_FeatureServer_12` | 94,634 | 94,634 | 0.00% | ok |
| 113 | `ty_org_arcgis_rest_services_Hub_PublicSafety_Hub_MapServer_4` | 94,566 | 94,566 | 0.00% | ok |
| 114 | `_services_Ouachita_Parish_911_Address_points_FeatureServer_0` | 94,215 | 94,215 | 0.00% | ok |
| 115 | `037wYhPG904_arcgis_rest_services_address_COV_FeatureServer_0` | 94,002 | 94,002 | 0.00% | ok |
| 116 | `st_services_SchoolBoundary_addressPnt_Update_FeatureServer_0` | 93,542 | 93,542 | 0.00% | ok |
| 117 | `lueBMxIOHOjKe_arcgis_rest_services_Addresses_FeatureServer_0` | 93,381 | 93,381 | 0.00% | ok |
| 118 | `ntygov_com_server_rest_services_Addresses_Public_MapServer_0` | 93,291 | 0 | 100.00% | failed |
| 119 | `es_June_2026_Hyland_Hills_Addresses_with_ZIP_FeatureServer_0` | 93,158 | 93,158 | 0.00% | ok |
| 120 | `Ph_arcgis_rest_services_Santa_Rosa_Addresses_FeatureServer_3` | 93,088 | 93,088 | 0.00% | ok |
| 121 | `GqZL7U3_arcgis_rest_services_Primary_Address_FeatureServer_0` | 92,940 | 92,940 | 0.00% | ok |
| 122 | `41_arcgis_rest_services_Riverside_Address_Pt_FeatureServer_0` | 92,927 | 92,927 | 0.00% | ok |
| 123 | `RLGNbA2hh7gE_arcgis_rest_services_EugAddress_FeatureServer_0` | 92,634 | 92,634 | 0.00% | ok |
| 124 | `aNxg1PvwI_arcgis_rest_services_CityAddresses_FeatureServer_0` | 92,587 | 92,587 | 0.00% | ok |
| 125 | `jlqdhhFKP9_arcgis_rest_services_Address_view_FeatureServer_0` | 92,396 | 92,396 | 0.00% | ok |
| 126 | `TCmMFjlqdhhFKP9_arcgis_rest_services_Address_FeatureServer_0` | 92,396 | 92,396 | 0.00% | ok |
| 127 | `s_rest_services_SurpriseAddress_Points052026_FeatureServer_0` | 92,237 | 92,237 | 0.00% | ok |
| 128 | `1SIRs7_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_180` | 92,217 | 92,217 | 0.00% | ok |
| 129 | `s_rest_services_SurpriseAddressPoints_012326_FeatureServer_3` | 91,841 | 91,841 | 0.00% | ok |
| 130 | `ZLFK9_arcgis_rest_services_HB_Address_Point_FeatureServer_25` | 91,787 | 91,787 | 0.00% | ok |
| 131 | `s_nnva_gov_gis_rest_services_Operational_Address_MapServer_0` | 91,661 | 91,661 | 0.00% | ok |
| 132 | `Wg1Aw7azh41_arcgis_rest_services_AddressPnts_FeatureServer_0` | 91,597 | 91,597 | 0.00% | ok |
| 133 | `cgis_rest_services_TCECD_Site_Address_Points_FeatureServer_2` | 91,383 | 91,383 | 0.00% | ok |
| 134 | `erver_rest_services_ReferenceMap_Addresses_R_FeatureServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 135 | `arcserver_rest_services_ReferenceMap_Addresses_R_MapServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 136 | `ervices_ReferenceMap_Aerial_Site_Address_Point_R_MapServer_0` | 91,327 | 91,327 | 0.00% | ok |
| 137 | `RY_arcgis_rest_services_CityAddressPoints_FeatureServer_1521` | 91,215 | 91,215 | 0.00% | ok |
| 138 | `v_arcgis_rest_services_Addresses_Offline2026_FeatureServer_0` | 91,212 | 91,212 | 0.00% | ok |
| 139 | `Np6bMI13R_arcgis_rest_services_AddressPoints_FeatureServer_0` | 91,181 | 91,181 | 0.00% | ok |
| 140 | `h41_arcgis_rest_services_ParcelsAndAddresses_FeatureServer_0` | 91,155 | 91,155 | 0.00% | ok |
| 141 | `41_arcgis_rest_services_ParcelsAndAddresses__FeatureServer_0` | 91,155 | 91,155 | 0.00% | ok |
| 142 | `_rest_services_Greenville__NC_Address_points_FeatureServer_0` | 90,984 | 90,984 | 0.00% | ok |
| 143 | `rcgis_rest_services_City_Address_Points_CAD_FeatureServer_71` | 90,972 | 90,972 | 0.00% | ok |
| 144 | `rest_services_Surprise_Address_Points_092425_FeatureServer_4` | 90,963 | 90,963 | 0.00% | ok |
| 145 | `M5nL34_arcgis_rest_services_GIS_AddressPoint_FeatureServer_0` | 90,879 | 90,879 | 0.00% | ok |
| 146 | `Y_arcgis_rest_services_Address_Points_Static_FeatureServer_0` | 90,874 | 90,874 | 0.00% | ok |
| 147 | `rcgis_rest_services_PropertyViewer_Addresses_FeatureServer_0` | 90,747 | 90,747 | 0.00% | ok |
| 148 | `s_rest_services_City_Address_Points_Dynamic_FeatureServer_30` | 90,706 | 90,706 | 0.00% | ok |
| 149 | `QgoA_arcgis_rest_services_MVWA_AddressPoints_FeatureServer_4` | 90,699 | 90,699 | 0.00% | ok |
| 150 | `rcgis_rest_services_City_Address_Points_RTCC_FeatureServer_0` | 90,687 | 90,687 | 0.00% | ok |
| 151 | `wad_rest_services_PublicSafety_DroneSense_Layers_MapServer_1` | 90,680 | 90,680 | 0.00% | ok |
| 152 | `cgis_rest_services_911_Addresses_Public_View_FeatureServer_2` | 81,784 | 163,221 | -99.58% | partial |
| 153 | `dYPQqS1KF_arcgis_rest_services_AddressPoints_FeatureServer_0` | 76,208 | 76,208 | 0.00% | ok |
| 154 | `23gQB5_arcgis_rest_services_EsiteAddr_Collab_FeatureServer_0` | 76,053 | 76,053 | 0.00% | ok |
| 155 | `ndtexas_gov_arcgis_rest_services_Energov_Energov_MapServer_0` | 76,053 | 76,053 | 0.00% | ok |
| 156 | `9CkZD_arcgis_rest_services_ChlormaineAddress_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 157 | `srDo0QMPlK9CkZD_arcgis_rest_services_Address_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 158 | `0QMPlK9CkZD_arcgis_rest_services_SiteAddress_FeatureServer_0` | 75,526 | 75,526 | 0.00% | ok |
| 159 | `arcgis_rest_services_Planning_Address_Points_FeatureServer_1` | 75,416 | 75,416 | 0.00% | ok |
| 160 | `landtx_gov_server1_rest_services_BASEMAP_ADDRESS_MapServer_0` | 74,181 | 74,181 | 0.00% | ok |
| 161 | `nica_gov_server_rest_services_Address_Points_FeatureServer_0` | 57,063 | 57,063 | 0.00% | ok |
| 162 | `rcgis_rest_services_Address_Points_Open_Data_FeatureServer_0@VA-2` | 57,046 | 57,046 | 0.00% | ok |
| 163 | `iyW_arcgis_rest_services_BPLU_Address_Points_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 164 | `cgis_rest_services_BPLU_Address_Points_Final_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 165 | `cgis_rest_services_BPLU_Address_Points_Parts_FeatureServer_0` | 57,040 | 57,040 | 0.00% | ok |
| 166 | `gis_adaptor_rest_services_OpenData_AddressPoints_MapServer_0` | 57,021 | 57,021 | 0.00% | ok |
| 167 | `KtMulHM03_arcgis_rest_services_AddressPoints_FeatureServer_0` | 56,972 | 56,972 | 0.00% | ok |
| 168 | `_ca_arcgis_adaptor_rest_services_LCGIS_VertiGIS_MapServer_25` | 56,888 | 88 | 99.85% | failed |
| 169 | `rXp_arcgis_rest_services_LPG_Address_Records_FeatureServer_0` | 56,599 | 113,267 | -100.12% | partial |
| 170 | `_cfmdyB05xBau1dNQ_arcgis_rest_services_Situs_FeatureServer_0` | 55,639 | 55,639 | 0.00% | ok |
| 171 | `rcgis_rest_services_Deerfield_Case_Addresses_FeatureServer_0` | 54,793 | 54,793 | 0.00% | ok |
| 172 | `eeeoWYqSyV5I_arcgis_rest_services_E911_gdb__FeatureServer_11` | 54,644 | 109,268 | -99.96% | partial |
| 173 | `_qnjIrwR8z5Izc0ij_arcgis_rest_services_ng911_FeatureServer_0` | 52,649 | 52,649 | 0.00% | ok |
| 174 | `est_services_AddressPtsAndUnitNumbersWebsite_FeatureServer_0` | 52,368 | 52,368 | 0.00% | ok |
| 175 | `exxB_arcgis_rest_services_911_Address_Labels_FeatureServer_6` | 52,022 | 52,022 | 0.00% | ok |
| 176 | `BvD2F_arcgis_rest_services_COG_StreetAddress_FeatureServer_1` | 51,423 | 102,815 | -99.94% | partial |
| 177 | `gis_net_arcgis_rest_services_BASE_Address_Points_MapServer_0` | 50,911 | 0 | 100.00% | failed |
| 178 | `om_arcgis_rest_services_Cadastral_Address_Points_MapServer_0` | 50,423 | 0 | 100.00% | failed |
| 179 | `_gov_uk_arcweb_rest_services_Addresses_Addresses_MapServer_0` | 49,374 | 0 | 100.00% | failed |
| 180 | `_services_County_Addressing_Application_View_FeatureServer_0` | 47,763 | 47,763 | 0.00% | ok |
| 181 | `rvices_Public_Taxlots_with_SiteAddresses_Service_MapServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 182 | `Taxlots_TRAKiT_with_SiteAddressPoint_Service_FeatureServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 183 | `es_Public_Taxlots_with_SiteAddresses_Service_FeatureServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 184 | `MLI_Taxlots_TRAKiT_with_SiteAddressPoint_Service_MapServer_0` | 47,625 | 47,625 | 0.00% | ok |
| 185 | `ns7W6juha0m_arcgis_rest_services_AddressSite_FeatureServer_0` | 47,592 | 47,592 | 0.00% | ok |
| 186 | `7W6juha0m_arcgis_rest_services_AddressPoints_FeatureServer_0` | 47,577 | 47,577 | 0.00% | ok |
| 187 | `l_gov_arcgis_rest_services_ACGOL_ACGOL_Addresses_MapServer_0` | 47,567 | 47,567 | 0.00% | ok |
| 188 | `G_arcgis_rest_services_Address_Points_Public_FeatureServer_0` | 47,540 | 47,540 | 0.00% | ok |
| 189 | `_rest_services_Worth_Township_Address_Points_FeatureServer_0` | 47,513 | 47,513 | 0.00% | ok |
| 190 | `com_arcserver_rest_services_911Addresses_PDS_FeatureServer_0` | 47,416 | 47,416 | 0.00% | ok |
| 191 | `t_services_ReferenceMap_SiteAddressPoint_R_FeatureServer_297` | 47,416 | 47,416 | 0.00% | ok |
| 192 | `_com_arcserver_rest_services_911Addresses_PW_FeatureServer_0` | 47,416 | 47,416 | 0.00% | ok |
| 193 | `ces_City_Share_City_Share_Active911Addresses_FeatureServer_0` | 47,377 | 47,377 | 0.00% | ok |
| 194 | `8SbZx_arcgis_rest_services_Menifee_Addresses_FeatureServer_0` | 47,307 | 47,307 | 0.00% | ok |
| 195 | `gYSxztFGZwla_arcgis_rest_services_AddressPts_FeatureServer_0` | 47,299 | 47,299 | 0.00% | ok |
| 196 | `us_arcgis_ea_rest_services_OpenAccess_CC_Address_MapServer_0` | 47,294 | 47,294 | 0.00% | ok |
| 197 | `_arcgis_rest_services_Parcels_With_Addresses_FeatureServer_0` | 47,286 | 47,286 | 0.00% | ok |
| 198 | `50u6oHu4Z_arcgis_rest_services_FSA_Addresses_FeatureServer_0` | 47,269 | 47,269 | 0.00% | ok |
| 199 | `gis_rest_services_ADDRESS_SITE_POINTS_static_FeatureServer_0` | 47,249 | 47,249 | 0.00% | ok |
| 200 | `rcgis_rest_services_Open_Data_Address_Points_FeatureServer_0@未定位-1` | 47,230 | 47,230 | 0.00% | ok |
| 201 | `rest_services_City_of_Kelowna_Address_Points_FeatureServer_0` | 47,128 | 47,128 | 0.00% | ok |
| 202 | `xPpXv8MHiv19f_arcgis_rest_services_Addresses_FeatureServer_1` | 46,968 | 46,968 | 0.00% | ok |
| 203 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-1` | 46,965 | 46,965 | 0.00% | ok |
| 204 | `0gE_arcgis_rest_services_Address_Points_View_FeatureServer_4` | 46,960 | 46,960 | 0.00% | ok |
| 205 | `XFjUq7iY_arcgis_rest_services_Address_Points_FeatureServer_0` | 46,934 | 46,934 | 0.00% | ok |
| 206 | `dZFl3Y1kjj_arcgis_rest_services_NC_Addresses_FeatureServer_0` | 46,879 | 46,879 | 0.00% | ok |
| 207 | `arcgis_rest_services_Physical_Addresses_view_FeatureServer_0` | 46,789 | 46,789 | 0.00% | ok |
| 208 | `7ey_arcgis_rest_services_Addresses_Parcel_00_FeatureServer_6` | 46,764 | 46,764 | 0.00% | ok |
| 209 | `9ZWWXL1M_arcgis_rest_services_Address_Points_FeatureServer_0` | 46,759 | 46,759 | 0.00% | ok |
| 210 | `is_rest_services_ParcelsAddressSummaryPoints_FeatureServer_1` | 46,701 | 46,701 | 0.00% | ok |
| 211 | `hhip_arcgis_rest_services_COB_Address_Points_FeatureServer_6` | 46,642 | 46,642 | 0.00% | ok |
| 212 | `eOv_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 46,624 | 46,624 | 0.00% | ok |
| 213 | `gis_rest_services_Public_View_Address_Points_FeatureServer_0` | 46,537 | 46,537 | 0.00% | ok |
| 214 | `ton_ca_arcgis_rest_services_Datasets_Address_Pts_MapServer_0` | 46,446 | 46,446 | 0.00% | ok |
| 215 | `est_services_Datasets_AMANDA_Address_Parcel_Link_MapServer_0` | 46,440 | 46,440 | 0.00% | ok |
| 216 | `2_arcgis_rest_services_BOCA_SITUS_CYCLOMEDIA_FeatureServer_0` | 45,877 | 45,877 | 0.00% | ok |
| 217 | `CjIDJJ2_arcgis_rest_services_BOCA_SITUS_CITY_FeatureServer_0` | 45,877 | 45,877 | 0.00% | ok |
| 218 | `ntyva_gov_arcgis_rest_services_JCC_GIS_Data_FeatureServer_16@未定位-1` | 45,833 | 45,833 | 0.00% | ok |
| 219 | `ntyva_gov_arcgis_rest_services_JCC_GIS_Data_FeatureServer_16@未定位-2` | 45,833 | 45,833 | 0.00% | ok |
| 220 | `_rest_services_Site_Structure_Address_Points_FeatureServer_1@AL-1` | 45,765 | 45,765 | 0.00% | ok |
| 221 | `t_services_SiteAddressPoint_ByVotingPrecinct_FeatureServer_9` | 45,699 | 45,699 | 0.00% | ok |
| 222 | `_gov_arcgis_rest_services_Land_Records_Open_Data_MapServer_1` | 40,675 | 0 | 100.00% | failed |
| 223 | `arcgis_rest_services_LAWRENCEGIS_NG911Addressing_MapServer_0` | 39,743 | 39,503 | 0.60% | failed |
| 224 | `_services_Nacogdoches_County_Address_Points_FeatureServer_10` | 38,691 | 38,691 | 0.00% | ok |
| 225 | `om_6443_arcgis_rest_services_Address_Points_2019_MapServer_0` | 38,689 | 38,689 | 0.00% | ok |
| 226 | `YxoF_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 38,648 | 38,648 | 0.00% | ok |
| 227 | `t0KpGzI_arcgis_rest_services_SiteAddress_pub_FeatureServer_0` | 38,603 | 38,603 | 0.00% | ok |
| 228 | `est_services_OpenData_Address_Points_Updated_FeatureServer_0` | 38,571 | 38,571 | 0.00% | ok |
| 229 | `_services_Streets_and_Address_Points_for_911_FeatureServer_0` | 38,571 | 38,571 | 0.00% | ok |
| 230 | `z971EmeG3_arcgis_rest_services_AddressPoints_FeatureServer_0` | 38,505 | 38,505 | 0.00% | ok |
| 231 | `ca_gisernie_rest_services_Public_Ajax_Open_Data_MapServer_10` | 38,444 | 38,444 | 0.00% | ok |
| 232 | `n_arcgis_rest_services_Municipal_911_Address_FeatureServer_0` | 38,383 | 38,383 | 0.00% | ok |
| 233 | `Esw_arcgis_rest_services_Ajax_Address_Points_FeatureServer_0` | 38,372 | 38,372 | 0.00% | ok |
| 234 | `8xIvXuYJiVZwF_arcgis_rest_services_Addresses_FeatureServer_0` | 38,356 | 38,356 | 0.00% | ok |
| 235 | `xmkB3meN_arcgis_rest_services_Address_Points_FeatureServer_0` | 38,281 | 38,281 | 0.00% | ok |
| 236 | `1CITN3V3_arcgis_rest_services_Address_Points_FeatureServer_0` | 38,280 | 38,280 | 0.00% | ok |
| 237 | `temeculaca_gov_arcgis_rest_services_OpenData_FeatureServer_4` | 38,234 | 38,234 | 0.00% | ok |
| 238 | `B5jkAnFA_arcgis_rest_services_Addresses_view_FeatureServer_0` | 38,122 | 38,122 | 0.00% | ok |
| 239 | `P6CrfEsw_arcgis_rest_services_Address_Points_FeatureServer_1` | 38,072 | 38,072 | 0.00% | ok |
| 240 | `DOMEad_arcgis_rest_services_Harrison_Address_FeatureServer_1` | 37,989 | 37,989 | 0.00% | ok |
| 241 | `q66_arcgis_rest_services_Erie_Address_Points_FeatureServer_0` | 37,906 | 37,906 | 0.00% | ok |
| 242 | `Kuj4Ua8_arcgis_rest_services_Address_Points_FeatureServer_31` | 37,901 | 37,901 | 0.00% | ok |
| 243 | `s_rest_services_UnionSnyderAddress_01_2026_FeatureServer_188` | 37,850 | 37,850 | 0.00% | ok |
| 244 | `cgis_rest_services_UnionSnyderAddressOct2025_FeatureServer_7` | 37,831 | 37,831 | 0.00% | ok |
| 245 | `blicDataEnterprise_PublicData_Address_Points_FeatureServer_0` | 37,813 | 37,813 | 0.00% | ok |
| 246 | `GIS_rest_services_Streets_and_Address_Points_FeatureServer_0` | 37,812 | 37,812 | 0.00% | ok |
| 247 | `ElDOMEad_arcgis_rest_services_Marion_Address_FeatureServer_1` | 37,759 | 37,759 | 0.00% | ok |
| 248 | `est_services_Angelina_County_Address_Points_FeatureServer_10` | 37,709 | 37,709 | 0.00% | ok |
| 249 | `rcgis_rest_services_AddressPoints_amandaview_FeatureServer_0` | 37,707 | 37,707 | 0.00% | ok |
| 250 | `cgis_rest_services_AddressPoints_public_view_FeatureServer_0` | 37,707 | 37,707 | 0.00% | ok |
| 251 | `jia0CW_arcgis_rest_services_Address_Points_FeatureServer_340` | 37,635 | 37,635 | 0.00% | ok |
| 252 | `is_rest_services_Address_Points_Merged__view_FeatureServer_6` | 37,487 | 37,487 | 0.00% | ok |
| 253 | `arcgis_rest_services_CPC_Address_Points_view_FeatureServer_0` | 37,408 | 37,408 | 0.00% | ok |
| 254 | `ervices_Parcel_Address_Points_AddressOnly__1_FeatureServer_0` | 37,180 | 37,180 | 0.00% | ok |
| 255 | `9J_arcgis_rest_services_AddressesPublic_View_FeatureServer_0` | 37,170 | 37,170 | 0.00% | ok |
| 256 | `TFQ5_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 37,164 | 37,164 | 0.00% | ok |
| 257 | `y5MmuVTV_arcgis_rest_services_Address_Points_FeatureServer_0` | 37,010 | 37,010 | 0.00% | ok |
| 258 | `v_appdata_rest_services_Addressing_MD_Addressing_MapServer_0` | 33,887 | 33,887 | 0.00% | ok |
| 259 | `65ptjBcDZM_arcgis_rest_services_MyMapService_FeatureServer_0` | 33,884 | 33,884 | 0.00% | ok |
| 260 | `oqakAkedEx0oU_arcgis_rest_services_Addresses_FeatureServer_0` | 33,791 | 33,791 | 0.00% | ok |
| 261 | `azssuvI82_arcgis_rest_services_AddressPoints_FeatureServer_0` | 33,777 | 33,777 | 0.00% | ok |
| 262 | `BDvIjv8OhMDVd_arcgis_rest_services_Addresses_FeatureServer_1` | 33,701 | 33,701 | 0.00% | ok |
| 263 | `aPG_arcgis_rest_services_CivicAddress_Public_FeatureServer_0` | 33,669 | 33,669 | 0.00% | ok |
| 264 | `cgis_rest_services_CampbellCountySiteAddress_FeatureServer_1` | 33,655 | 33,655 | 0.00% | ok |
| 265 | `Nwgn5oKx_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_0` | 33,653 | 33,653 | 0.00% | ok |
| 266 | `mpweKJ4f_arcgis_rest_services_Address_Points_FeatureServer_0` | 33,629 | 33,629 | 0.00% | ok |
| 267 | `J4f_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 33,629 | 33,629 | 0.00% | ok |
| 268 | `7_rest_services_Base_Layers_AddressPnt_local_FeatureServer_0` | 33,608 | 33,608 | 0.00% | ok |
| 269 | `st_services_sloGISlayers_gisLandManagementWM_FeatureServer_2` | 33,572 | 33,572 | 0.00% | ok |
| 270 | `ev2aNwKyB_arcgis_rest_services_HTE_Addresses_FeatureServer_0` | 33,447 | 33,447 | 0.00% | ok |
| 271 | `wKyB_arcgis_rest_services_HTE_Addresses_view_FeatureServer_0` | 33,447 | 33,447 | 0.00% | ok |
| 272 | `d4ES_arcgis_rest_services_BelcoAddressPoints_FeatureServer_0` | 33,428 | 33,428 | 0.00% | ok |
| 273 | `JHVTrT_arcgis_rest_services_address_vwPublic_FeatureServer_0` | 33,414 | 33,414 | 0.00% | ok |
| 274 | `lYD_arcgis_rest_services_AddressPoints_24_12_FeatureServer_0` | 33,401 | 33,401 | 0.00% | ok |
| 275 | `UHl6XumF_arcgis_rest_services_R_AddressPoint_FeatureServer_0` | 33,337 | 33,337 | 0.00% | ok |
| 276 | `gGO9NJCc_arcgis_rest_services_Address_Points_FeatureServer_0` | 33,334 | 33,334 | 0.00% | ok |
| 277 | `nz_arcgis_rest_services_Property_PropertyandLand_MapServer_0` | 33,167 | 33,167 | 0.00% | ok |
| 278 | `QgATDeUJrt_arcgis_rest_services_Site_Address_FeatureServer_0` | 33,107 | 33,107 | 0.00% | ok |
| 279 | `aCs_arcgis_rest_services_Parcels_and_Address_FeatureServer_0` | 33,041 | 33,041 | 0.00% | ok |
| 280 | `est_services_Pleasanton_Address_Point_Public_FeatureServer_0` | 33,033 | 33,033 | 0.00% | ok |
| 281 | `A3gGO9NJCc_arcgis_rest_services_AddressPoint_FeatureServer_0` | 32,983 | 32,983 | 0.00% | ok |
| 282 | `s_rest_services_Redlands_address_points_view_FeatureServer_0` | 32,926 | 32,926 | 0.00% | ok |
| 283 | `cgis_rest_services_Residential_AddressPoints_FeatureServer_0` | 32,919 | 32,919 | 0.00% | ok |
| 284 | `CFmA_arcgis_rest_services_Address_Points_New_FeatureServer_0` | 32,888 | 32,888 | 0.00% | ok |
| 285 | `ia_wi_us_server_rest_services_Address_points_FeatureServer_0` | 32,879 | 32,879 | 0.00% | ok |
| 286 | `ices_Medina_County_Address_Points_3_21_2023_FeatureServer_98` | 32,846 | 32,846 | 0.00% | ok |
| 287 | `eTUuaT56jB_arcgis_rest_services_RI_E911_Data_FeatureServer_0` | 32,746 | 32,746 | 0.00% | ok |
| 288 | `s_gscplanning_com_arcgis_rest_services_Addresses_MapServer_0` | 32,599 | 32,599 | 0.00% | ok |
| 289 | `nc_org_jcgis_rest_services_EM_Address_Points_FeatureServer_0` | 32,596 | 32,596 | 0.00% | ok |
| 290 | `s_rest_services_BaseLayer_FlockMap_Addresses_FeatureServer_0` | 32,590 | 32,590 | 0.00% | ok |
| 291 | `t_services_Addresses_with_Services_08_15_25_FeatureServer_14` | 32,559 | 32,559 | 0.00% | ok |
| 292 | `ces_GC_Address_Points_with_Utility_Providers_FeatureServer_0` | 32,534 | 32,534 | 0.00% | ok |
| 293 | `rcgis_rest_services_Pictometry_Layer_Updates_FeatureServer_1` | 32,483 | 32,483 | 0.00% | ok |
| 294 | `vfHOElpgGU_arcgis_rest_services_AddressPoint_FeatureServer_1` | 32,424 | 32,424 | 0.00% | ok |
| 295 | `xQE_arcgis_rest_services_NENA_Address_Points_FeatureServer_7` | 32,381 | 32,381 | 0.00% | ok |
| 296 | `_rest_services_ADDRESS_POINTS_CITYVIEW_WGS84_FeatureServer_0` | 32,318 | 32,318 | 0.00% | ok |
| 297 | `services_InteractiveMap_InteractiveMap_Addresses_MapServer_2` | 32,285 | 32,285 | 0.00% | ok |
| 298 | `co_columbia_wi_us_server_rest_services_Open_GIS_MapServer_59` | 32,285 | 32,285 | 0.00% | ok |
| 299 | `_arcgis_rest_services_Site_Address_Points_DL_FeatureServer_0` | 32,261 | 32,261 | 0.00% | ok |
| 300 | `I2T0wc_arcgis_rest_services_Address_Map_WFL1_FeatureServer_0` | 32,260 | 32,260 | 0.00% | ok |
| 301 | `_services_LenoirNC_Parcels_Zoning_Addressing_FeatureServer_0` | 32,218 | 32,218 | 0.00% | ok |
| 302 | `gis_rest_services_BaseFeatures_CityScaleBaseData_MapServer_1` | 32,171 | 32,171 | 0.00% | ok |
| 303 | `cgis_rest_services_Addresses_in_service_area_FeatureServer_0` | 32,145 | 32,145 | 0.00% | ok |
| 304 | `l_arcgis_rest_services_Check_Point_Addresses_FeatureServer_0` | 32,097 | 32,097 | 0.00% | ok |
| 305 | `7_arcgis_rest_services_Public_Address_Points_FeatureServer_0` | 31,994 | 31,994 | 0.00% | ok |
| 306 | `rcgis_rest_services_Public_Addressing_Pro_JG_FeatureServer_0` | 31,966 | 31,966 | 0.00% | ok |
| 307 | `4FfmN3nn5_arcgis_rest_services_AddressPoints_FeatureServer_0` | 31,940 | 31,940 | 0.00% | ok |
| 308 | `SsReIxuA_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,887 | 31,887 | 0.00% | ok |
| 309 | `ss_Points_with_Phase_and_Timeline_View_Layer_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 310 | `est_services_BroadbandPhases_AddressesPoints_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 311 | `vices_Address_Points_with_Phase_and_Timeline_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 312 | `rest_services_AddressPoints_ByBroadbandPhase_FeatureServer_0` | 31,842 | 31,842 | 0.00% | ok |
| 313 | `Mfde8s_arcgis_rest_services_Site_Addresses_1_FeatureServer_0` | 31,748 | 31,748 | 0.00% | ok |
| 314 | `14j_arcgis_rest_services_Z_GIS_Addresses_SBG_FeatureServer_0` | 31,728 | 31,728 | 0.00% | ok |
| 315 | `qvET_arcgis_rest_services_Address_Points_GSY_FeatureServer_0` | 31,680 | 31,680 | 0.00% | ok |
| 316 | `est_services_InformationTechnology_AddressPoints_MapServer_0` | 31,669 | 31,669 | 0.00% | ok |
| 317 | `services_InformationTechnology_AddressPoints_FeatureServer_0` | 31,669 | 31,669 | 0.00% | ok |
| 318 | `8hXASVYi_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,630 | 31,630 | 0.00% | ok |
| 319 | `RPkF9w28VGX_arcgis_rest_services_Addresses_FeatureServer_359` | 31,624 | 31,624 | 0.00% | ok |
| 320 | `8aWlfDG1Qh_arcgis_rest_services_Address_pnts_FeatureServer_0` | 31,617 | 31,617 | 0.00% | ok |
| 321 | `s_rest_services_MiddlesexCountyAddressPoints_FeatureServer_0` | 31,571 | 31,571 | 0.00% | ok |
| 322 | `is_rest_services_Address_Points_20210707_CoB_FeatureServer_0` | 31,558 | 31,558 | 0.00% | ok |
| 323 | `5GjGWCoI_arcgis_rest_services_Address_Points_FeatureServer_0` | 31,470 | 31,470 | 0.00% | ok |
| 324 | `mib3H_arcgis_rest_services_addresspts_points_FeatureServer_0` | 31,455 | 31,455 | 0.00% | ok |
| 325 | `_rest_services_Address_Points_2019_05_20_CoB_FeatureServer_0` | 31,422 | 31,422 | 0.00% | ok |
| 326 | `k3_arcgis_rest_services_Address_Points_SFRes_FeatureServer_0` | 31,405 | 31,405 | 0.00% | ok |
| 327 | `GexkkJ9w_arcgis_rest_services_CivicAddresses_FeatureServer_0` | 31,363 | 31,363 | 0.00% | ok |
| 328 | `sGtVEXzaX_arcgis_rest_services_NYC_Addresses_FeatureServer_0` | 31,352 | 31,352 | 0.00% | ok |
| 329 | `cgis_rest_services_Address_20Points_20Mark43_FeatureServer_0` | 31,335 | 31,335 | 0.00% | ok |
| 330 | `gov_mapping_rest_services_VIEW_AddressPoints_FeatureServer_0` | 31,263 | 31,263 | 0.00% | ok |
| 331 | `xas_gov_mapping_rest_services_VIEW_AddressPoints_MapServer_0` | 31,263 | 31,263 | 0.00% | ok |
| 332 | `services_franklincountyaddresspoints_10_7_26_FeatureServer_0` | 31,241 | 31,241 | 0.00% | ok |
| 333 | `K9o0xX_arcgis_rest_services_Ztron_View_Layer_FeatureServer_0` | 31,202 | 31,202 | 0.00% | ok |
| 334 | `_arcgis_rest_services_AddressesForFairmont_FeatureServer_115` | 31,175 | 31,175 | 0.00% | ok |
| 335 | `_services_HemetAddressPoints122625_Projected_FeatureServer_0` | 31,162 | 31,162 | 0.00% | ok |
| 336 | `gRR0s_arcgis_rest_services_SiteAddressPoint_FeatureServer_47` | 31,150 | 31,150 | 0.00% | ok |
| 337 | `ct0i_arcgis_rest_services_Whittier_Addresses_FeatureServer_0` | 31,032 | 31,032 | 0.00% | ok |
| 338 | `fc16391ae7_rest_services_AGOPublic_PublicLayers_MapServer_34` | 30,941 | 30,941 | 0.00% | ok |
| 339 | `arcgis_rest_services_Wellington_FL_Addresses_FeatureServer_0` | 27,213 | 27,213 | 0.00% | ok |
| 340 | `j_arcgis_rest_services_BARRON_ADDRESSES_2025_FeatureServer_0` | 27,058 | 27,058 | 0.00% | ok |
| 341 | `arcgis_rest_services_Hinesville_GA_Addresses_FeatureServer_0` | 26,965 | 26,965 | 0.00% | ok |
| 342 | `_services_Lincoln_LUCA_Addresses_Counts_WFL1_FeatureServer_0` | 26,903 | 26,903 | 0.00% | ok |
| 343 | `es_Service_Location_Moving_ToCURB_ASof712025_FeatureServer_0` | 26,684 | 26,684 | 0.00% | ok |
| 344 | `OLvsmwpY1RmFG_arcgis_rest_services_Addresses_FeatureServer_0` | 26,510 | 26,510 | 0.00% | ok |
| 345 | `_rest_services_NM_911_Addresses_Large_Scale_FeatureServer_32` | 26,410 | 52,891 | -100.27% | partial |
| 346 | `_rest_services_NM_911_Addresses_Small_Scale_FeatureServer_33` | 26,410 | 52,891 | -100.27% | partial |
| 347 | `iGx_arcgis_rest_services_Addresses_Only_view_FeatureServer_0` | 26,320 | 52,635 | -99.98% | partial |
| 348 | `J9QAHCiGx_arcgis_rest_services_SiteAddresses_FeatureServer_0` | 26,021 | 26,021 | 0.00% | ok |
| 349 | `ttesville_org_cvgisweb_rest_services_OpenData_1_MapServer_76` | 25,834 | 51,668 | -100.00% | partial |
| 350 | `WQTB2G8AH9RQYE_arcgis_rest_services_address_FeatureServer_16` | 25,817 | 51,608 | -99.90% | partial |
| 351 | `st_services_City_of_Pittsburg_Address_Public_FeatureServer_0` | 25,582 | 25,582 | 0.00% | ok |
| 352 | `_arcgis_rest_services_Shawano_Addresses_2026_FeatureServer_0` | 25,427 | 25,427 | 0.00% | ok |
| 353 | `l_org_arcgis_rest_services_Weston_Basemap_cache_MapServer_20` | 25,367 | 25,367 | 0.00% | ok |
| 354 | `HiSnaX0z0hS_arcgis_rest_services_E911HeatMap_FeatureServer_0` | 25,193 | 25,193 | 0.00% | ok |
| 355 | `_net_geo_rest_services_Parcels_AddressPoints_FeatureServer_0` | 25,191 | 25,191 | 0.00% | ok |
| 356 | `o_rest_services_Parcels_AddressPoints_Master_FeatureServer_0` | 25,191 | 25,191 | 0.00% | ok |
| 357 | `L0M_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 25,168 | 25,168 | 0.00% | ok |
| 358 | `rest_services_Auburndale_Address_Points_view_FeatureServer_0` | 25,128 | 25,128 | 0.00% | ok |
| 359 | `cgis_rest_services_Auburndale_Address_Points_FeatureServer_0` | 25,128 | 25,128 | 0.00% | ok |
| 360 | `hOza2U_arcgis_rest_services_Civic_Addresses_FeatureServer_16` | 25,111 | 25,111 | 0.00% | ok |
| 361 | `_arcgis_rest_services_Addresses_GeoLoc_Build_FeatureServer_0` | 25,110 | 25,110 | 0.00% | ok |
| 362 | `9Y0AgX_arcgis_rest_services_ToCAddressPoints_FeatureServer_0` | 25,093 | 25,093 | 0.00% | ok |
| 363 | `AgX_arcgis_rest_services_AddressPoints_iWorQ_FeatureServer_0` | 25,093 | 25,093 | 0.00% | ok |
| 364 | `rcgis_rest_services_GC_Address_Points_Public_FeatureServer_8` | 25,091 | 50,069 | -99.55% | partial |
| 365 | `Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1` | 25,081 | 25,081 | 0.00% | ok |
| 366 | `n_Services_Addresses_Subdivisions_Parcels_ArcPro_MapServer_0` | 25,062 | 25,062 | 0.00% | ok |
| 367 | `gis_rest_services_UTILITY_Hydrants_E911_24r1_FeatureServer_0` | 25,052 | 25,052 | 0.00% | ok |
| 368 | `g4_arcgis_rest_services_Addressing_Resources_FeatureServer_3` | 25,027 | 25,027 | 0.00% | ok |
| 369 | `gis_rest_services_Parcel_and_Address_Service_FeatureServer_0` | 25,010 | 25,010 | 0.00% | ok |
| 370 | `gis_rest_services_Parcels_and_Addresses_2025_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 371 | `Oel_arcgis_rest_services_Address_Points_2025_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 372 | `6Oel_arcgis_rest_services_ParcelBaseWAddress_FeatureServer_0` | 25,009 | 25,009 | 0.00% | ok |
| 373 | `nPbdNoPBNAJ6Oel_arcgis_rest_services_Address_FeatureServer_5` | 25,009 | 25,009 | 0.00% | ok |
| 374 | `sKPeG_arcgis_rest_services_Address_ViewLayer_FeatureServer_0` | 24,987 | 24,987 | 0.00% | ok |
| 375 | `kHkuW_arcgis_rest_services_GC_Address_Points_FeatureServer_8` | 24,978 | 24,978 | 0.00% | ok |
| 376 | `RDcwL2kQ_arcgis_rest_services_City_Addresses_FeatureServer_0` | 24,890 | 24,890 | 0.00% | ok |
| 377 | `gis_rest_services_Parcel_with_addresses_2024_FeatureServer_0` | 24,885 | 24,885 | 0.00% | ok |
| 378 | `_services_BaseMap_Parcels_Addresses_Boundary_FeatureServer_2` | 24,883 | 24,883 | 0.00% | ok |
| 379 | `is_rest_services_AddressesParcelsUtility2024_FeatureServer_2` | 24,883 | 24,883 | 0.00% | ok |
| 380 | `a8HZMsU25Hzzob3_arcgis_rest_services_Address_FeatureServer_0` | 24,882 | 24,882 | 0.00% | ok |
| 381 | `rvices_Address_Points_for_Parks_and_Rec_2026_FeatureServer_0` | 24,878 | 24,878 | 0.00% | ok |
| 382 | `d_arcgis_rest_services_Miller_Address_Points_FeatureServer_0` | 24,846 | 24,846 | 0.00% | ok |
| 383 | `NEViJGK4M_arcgis_rest_services_911_Addresses_FeatureServer_0` | 24,826 | 24,826 | 0.00% | ok |
| 384 | `11SaUIGBo5JYFY_arcgis_rest_services_SRD_Data_FeatureServer_0` | 24,813 | 24,813 | 0.00% | ok |
| 385 | `I39xWsrNH_arcgis_rest_services_Civic_Address_FeatureServer_0` | 24,790 | 24,790 | 0.00% | ok |
| 386 | `cjDyDh65fslIZ_arcgis_rest_services_Addresses_FeatureServer_0` | 24,762 | 24,762 | 0.00% | ok |
| 387 | `services_Tville_Address_Points_UPDATE_Layer_FeatureServer_23` | 24,713 | 24,713 | 0.00% | ok |
| 388 | `s_rest_services_Address_Points_EnerGov_Only_FeatureServer_24` | 24,709 | 24,709 | 0.00% | ok |
| 389 | `arcgis_rest_services_03242025_Address_Points_FeatureServer_0` | 24,675 | 24,675 | 0.00% | ok |
| 390 | `UUihZ0ky_arcgis_rest_services_Address_Points_FeatureServer_1` | 24,669 | 24,669 | 0.00% | ok |
| 391 | `6rq_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 24,652 | 24,652 | 0.00% | ok |
| 392 | `st_services_Barry_County_NG911_Address_Point_FeatureServer_0` | 24,592 | 24,592 | 0.00% | ok |
| 393 | `ces_AddressPoints_Combined_CivicPlus__ROVIEW_FeatureServer_0` | 24,578 | 24,578 | 0.00% | ok |
| 394 | `s_rest_services_Fayette_County_911_Addresses_FeatureServer_1` | 24,529 | 24,529 | 0.00% | ok |
| 395 | `G2jt9_arcgis_rest_services_AddressPointsvw1_FeatureServer_10` | 24,520 | 24,520 | 0.00% | ok |
| 396 | `5CWG2jt9_arcgis_rest_services_AddressPoints_FeatureServer_10` | 24,520 | 24,520 | 0.00% | ok |
| 397 | `hwao8WvM_arcgis_rest_services_Address_Points_FeatureServer_0` | 24,483 | 24,483 | 0.00% | ok |
| 398 | `_services_Address_Points_TEST_from_shapefile_FeatureServer_0` | 24,483 | 24,483 | 0.00% | ok |
| 399 | `S9g_arcgis_rest_services_View_Address_Points_FeatureServer_0` | 24,477 | 24,477 | 0.00% | ok |
| 400 | `arcgis_rest_services_Site_Address_Points_WFS_FeatureServer_0` | 24,475 | 24,475 | 0.00% | ok |
| 401 | `rcgis_rest_services_Site_Address_Points_0716_FeatureServer_1` | 24,474 | 24,474 | 0.00% | ok |
| 402 | `a_ca_us_arcgis_rest_services_Basemap_Parcels_AGO_MapServer_0` | 24,468 | 24,468 | 0.00% | ok |
| 403 | `m_Iwwqwcdc5CWG2jt9_arcgis_rest_services_ADDR_FeatureServer_0` | 24,465 | 24,465 | 0.00% | ok |
| 404 | `es_GeneralPurpose_SiteAddressPoints_JUNE2023_FeatureServer_1` | 24,413 | 24,413 | 0.00% | ok |
| 405 | `rest_services_Addresses_With_Voting_Precinct_FeatureServer_0` | 24,398 | 24,398 | 0.00% | ok |
| 406 | `lumet_wi_us_server_rest_services_ParcelsService_MapServer_11` | 24,299 | 24,299 | 0.00% | ok |
| 407 | `BtvXuiLQ_arcgis_rest_services_Addresses_view_FeatureServer_2` | 24,235 | 24,235 | 0.00% | ok |
| 408 | `s_InternalANDPublicMaps_Churches_and_Cemeteries_MapServer_10` | 24,210 | 24,210 | 0.00% | ok |
| 409 | `TlITuys_arcgis_rest_services_WyboSiteAddress_FeatureServer_0` | 24,136 | 24,136 | 0.00% | ok |
| 410 | `arcgis_rest_services_BarryCountyMO_Addresses_FeatureServer_0` | 24,123 | 24,123 | 0.00% | ok |
| 411 | `Yd7fCfTTiVp8_arcgis_rest_services_Addresses2_FeatureServer_0` | 24,109 | 24,109 | 0.00% | ok |
| 412 | `yYd7fCfTTiVp8_arcgis_rest_services_Addresses_FeatureServer_0` | 24,107 | 24,107 | 0.00% | ok |
| 413 | `RmLNAomixG_arcgis_rest_services_RP_Addr_2022_FeatureServer_0` | 24,045 | 24,045 | 0.00% | ok |
| 414 | `7IM34hqT9y9ew_arcgis_rest_services_Addresses_FeatureServer_0` | 23,950 | 23,950 | 0.00% | ok |
| 415 | `0ipEAOFhn_arcgis_rest_services_Address_Tiles_FeatureServer_0` | 23,869 | 47,732 | -99.97% | partial |
| 416 | `gis_rest_services_BransonAddressSearch_WFL1_FeatureServer_54` | 23,859 | 23,859 | 0.00% | ok |
| 417 | `h_arcgis_rest_services_Addresses_for_Clariti_FeatureServer_0` | 23,819 | 47,237 | -98.32% | partial |
| 418 | `isapp_dunwoodyga_gov_arcgis_rest_services_Parcel_MapServer_1` | 23,776 | 47,553 | -100.00% | partial |
| 419 | `DL6ILvlkPNTg8_arcgis_rest_services_Addresses_FeatureServer_0` | 23,338 | 46,672 | -99.98% | partial |
| 420 | `ices_GeorginaMap_W84_SiteAddressPoint_Labels_W84_MapServer_0` | 23,246 | 20,570 | 11.51% | failed |
| 421 | `st_services_GeorginaMap_W84_SiteAddressPoint_W84_MapServer_0` | 23,241 | 20,567 | 11.51% | failed |
| 422 | `g_arcgis_rest_services_BarryCounty_Addresses_FeatureServer_0` | 23,141 | 23,141 | 0.00% | ok |
| 423 | `KckAl7VOw_arcgis_rest_services_Address_Lists_FeatureServer_0` | 23,136 | 23,136 | 0.00% | ok |
| 424 | `field_College_Block_Lot_and_Address_Map_WFL1_FeatureServer_0` | 23,106 | 23,106 | 0.00% | ok |
| 425 | `ycSVzMEzm7ey_arcgis_rest_services_Addressing_FeatureServer_0` | 22,930 | 22,930 | 0.00% | ok |
| 426 | `_services_Civic_Address_Points_5_view_simple_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 427 | `is_rest_services_Civic_Address_Points_View_2_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 428 | `cgis_rest_services_Civic_Address_Points_View_FeatureServer_0` | 22,412 | 22,412 | 0.00% | ok |
| 429 | `cgis_rest_services_BranchCountyAddressPoints_FeatureServer_0` | 22,344 | 22,344 | 0.00% | ok |
| 430 | `Z_arcgis_rest_services_NG911_SSAP_Web_Viewer_FeatureServer_0` | 22,337 | 22,337 | 0.00% | ok |
| 431 | `arcgis_rest_services_Address_Points_centrvle_FeatureServer_0` | 22,325 | 22,325 | 0.00% | ok |
| 432 | `cdc81CEBk_arcgis_rest_services_AddressPoints_FeatureServer_0` | 22,308 | 22,308 | 0.00% | ok |
| 433 | `yjVw1fpWcwy7h_arcgis_rest_services_ADDRESSES_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 434 | `fpWcwy7h_arcgis_rest_services_Address_Points_FeatureServer_0` | 22,283 | 22,283 | 0.00% | ok |
| 435 | `RaKduZ9Wo_arcgis_rest_services_AddressPoints_FeatureServer_0` | 22,273 | 22,273 | 0.00% | ok |
| 436 | `v_server_rest_services_AGOL_AGOL_INDV_AddrPoints_MapServer_0` | 22,258 | 22,258 | 0.00% | ok |
| 437 | `rcgis_rest_services_Address_Points_Open_Data_FeatureServer_0@未定位-1` | 22,257 | 22,257 | 0.00% | ok |
| 438 | `3u_arcgis_rest_services_Address_NonCollector_FeatureServer_0` | 22,257 | 22,257 | 0.00% | ok |
| 439 | `eSvF_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 22,248 | 44,495 | -100.00% | partial |
| 440 | `ow3ofS_arcgis_rest_services_NM_911_Addresses_FeatureServer_0` | 22,208 | 22,208 | 0.00% | ok |
| 441 | `is_rest_services_Public_Notification_Address_FeatureServer_0` | 22,188 | 22,188 | 0.00% | ok |
| 442 | `v_arcgis_rest_services_Newnan_Address_Points_FeatureServer_0` | 22,152 | 22,152 | 0.00% | ok |
| 443 | `est_services_Address_Points_Within_Gilleland_FeatureServer_0` | 22,151 | 22,151 | 0.00% | ok |
| 444 | `st_services_Address_Points_Within_Gilleland2_FeatureServer_0` | 22,151 | 22,151 | 0.00% | ok |
| 445 | `QoXoOXkk_arcgis_rest_services_Address_Points_FeatureServer_0` | 22,140 | 22,140 | 0.00% | ok |
| 446 | `msX_arcgis_rest_services_JoplinAddressPoints_FeatureServer_0` | 22,113 | 22,113 | 0.00% | ok |
| 447 | `eUxQY5fQy_arcgis_rest_services_Address_view_FeatureServer_40` | 22,109 | 22,109 | 0.00% | ok |
| 448 | `6ZLWUVjA_arcgis_rest_services_Address_Points_FeatureServer_1` | 22,099 | 22,099 | 0.00% | ok |
| 449 | `JUmf_arcgis_rest_services_NG911AddressPoints_FeatureServer_1` | 22,032 | 22,032 | 0.00% | ok |
| 450 | `vZ_arcgis_rest_services_AddressPoints_081723_FeatureServer_0` | 22,011 | 22,011 | 0.00% | ok |
| 451 | `arcgis_rest_services_tuckeraddresspointLayer_FeatureServer_0` | 21,987 | 21,987 | 0.00% | ok |
| 452 | `EQWYJHMZp_arcgis_rest_services_SITE_ADDRESS_FeatureServer_13` | 21,979 | 21,979 | 0.00% | ok |
| 453 | `NAnn8lip_arcgis_rest_services_Cadastral_PRD_FeatureServer_29` | 21,965 | 21,965 | 0.00% | ok |
| 454 | `p_arcgis_rest_services_Election_Site_Address_FeatureServer_0` | 21,953 | 21,953 | 0.00% | ok |
| 455 | `arcgis_rest_services_AddressQC_fieldmap_WFL1_FeatureServer_0` | 21,951 | 21,951 | 0.00% | ok |
| 456 | `z0S_arcgis_rest_services_Address_Point_base_FeatureServer_70` | 21,909 | 21,909 | 0.00% | ok |
| 457 | `rcgis_rest_services_Address_Point_base_view_FeatureServer_70` | 21,909 | 21,909 | 0.00% | ok |
| 458 | `Utd_arcgis_rest_services_Civic_Address__od_FeatureServer_152` | 21,900 | 21,900 | 0.00% | ok |
| 459 | `ONZ3C_arcgis_rest_services_Site_Address_View_FeatureServer_0` | 21,898 | 21,898 | 0.00% | ok |
| 460 | `is_rest_services_GIS_AddressPoint_HALVOTEMAP_FeatureServer_0` | 21,837 | 21,837 | 0.00% | ok |
| 461 | `SVDsGFwm_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,813 | 21,813 | 0.00% | ok |
| 462 | `rvices_Siskiyou_County_Public_Address_Points_FeatureServer_0` | 21,794 | 21,794 | 0.00% | ok |
| 463 | `h_arcgis_rest_services_AddressesJuly26B_WFL1_FeatureServer_2` | 21,789 | 21,789 | 0.00% | ok |
| 464 | `c_gov_arcgis_rest_services_Addresses_E911Address_MapServer_1` | 21,770 | 43,524 | -99.93% | partial |
| 465 | `uxM_arcgis_rest_services_NG911AddressPoints_FeatureServer_13` | 21,764 | 21,764 | 0.00% | ok |
| 466 | `2hyb0Af_arcgis_rest_services_Address_Parcels_FeatureServer_0` | 21,753 | 21,753 | 0.00% | ok |
| 467 | `_rest_services_GIS_ENV_GIS_Work_Background_Layer_MapServer_0` | 21,721 | 21,721 | 0.00% | ok |
| 468 | `WTywHfayX67L_arcgis_rest_services_NG911_Data_FeatureServer_0` | 21,706 | 21,706 | 0.00% | ok |
| 469 | `h7e_arcgis_rest_services_Site_Address_Points_FeatureServer_0` | 21,694 | 21,694 | 0.00% | ok |
| 470 | `_arcgis_rest_services_SiteAddressPoints_soma_FeatureServer_0` | 21,690 | 21,690 | 0.00% | ok |
| 471 | `VL7iicQLS_arcgis_rest_services_Address_BC911_FeatureServer_0` | 21,676 | 21,676 | 0.00% | ok |
| 472 | `F7Wwkv9D_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,658 | 21,658 | 0.00% | ok |
| 473 | `IQDOsXnGaTxj2_arcgis_rest_services_Addresses_FeatureServer_0` | 21,636 | 21,636 | 0.00% | ok |
| 474 | `z0S_arcgis_rest_services_Address_Point_view_FeatureServer_17` | 21,601 | 21,601 | 0.00% | ok |
| 475 | `4QpdcTJ9_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,597 | 21,597 | 0.00% | ok |
| 476 | `arcgis_rest_services_Jasper_County_Addresses_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 477 | `G2Q2tuit_arcgis_rest_services_Addresses_view_FeatureServer_4` | 21,594 | 21,594 | 0.00% | ok |
| 478 | `w5aLHpzj_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,594 | 21,594 | 0.00% | ok |
| 479 | `tb5ipmv9_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,584 | 21,584 | 0.00% | ok |
| 480 | `cTJ9_arcgis_rest_services_street_address_new_FeatureServer_0` | 21,571 | 21,571 | 0.00% | ok |
| 481 | `t_services_HostedService_LakeWorthBeachSitus_FeatureServer_0` | 21,556 | 21,556 | 0.00% | ok |
| 482 | `_rest_services_Greenbrier_Addressing_Service_FeatureServer_0` | 21,547 | 21,547 | 0.00% | ok |
| 483 | `W9v2gSO7_arcgis_rest_services_Address_Points_FeatureServer_4` | 21,490 | 21,490 | 0.00% | ok |
| 484 | `lYKSnzjiOzQig_arcgis_rest_services_Addresses_FeatureServer_1` | 21,419 | 21,419 | 0.00% | ok |
| 485 | `rr0NFJXS_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,415 | 21,415 | 0.00% | ok |
| 486 | `Q1Yngrdc_arcgis_rest_services_Addresses1115_FeatureServer_46` | 21,395 | 21,395 | 0.00% | ok |
| 487 | `yFxn_arcgis_rest_services_AddressPoints5Mile_FeatureServer_0` | 21,385 | 21,385 | 0.00% | ok |
| 488 | `mzqLyRabS_arcgis_rest_services_addresspoints_FeatureServer_0` | 21,385 | 21,385 | 0.00% | ok |
| 489 | `st_services_HostedService_SitusAddressPoints_FeatureServer_0` | 21,361 | 21,361 | 0.00% | ok |
| 490 | `ZLzs7d68_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,318 | 21,318 | 0.00% | ok |
| 491 | `t_services_Yadkin_County_Addresses_Read_Only_FeatureServer_0` | 21,299 | 21,299 | 0.00% | ok |
| 492 | `rest_services_Bettendorf_Address_Points_View_FeatureServer_0` | 21,284 | 21,284 | 0.00% | ok |
| 493 | `_rest_services_Homestead_2023_Address_Points_FeatureServer_0` | 21,275 | 21,275 | 0.00% | ok |
| 494 | `_rest_services_Address_Points_with_Elevation_FeatureServer_0` | 21,218 | 21,218 | 0.00% | ok |
| 495 | `_com_arcgis_rest_services_OpenData_Addresses_FeatureServer_0` | 21,217 | 21,217 | 0.00% | ok |
| 496 | `Qw11Lg0Zm_arcgis_rest_services_AuroraBasemap_FeatureServer_0` | 21,215 | 21,215 | 0.00% | ok |
| 497 | `arcgis_rest_services_City_of_Hobbs_Addresses_FeatureServer_0` | 21,154 | 21,154 | 0.00% | ok |
| 498 | `729Bn31m_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,153 | 21,153 | 0.00% | ok |
| 499 | `Fvge6E_arcgis_rest_services_Address_Services_FeatureServer_0` | 21,131 | 21,131 | 0.00% | ok |
| 500 | `SYGuYov4_arcgis_rest_services_Address_Points_FeatureServer_0` | 21,117 | 21,117 | 0.00% | ok |
| 501 | `_rest_services_Delta_County_Address_01232025_FeatureServer_0` | 21,108 | 21,108 | 0.00% | ok |
| 502 | `ervices_DeltaCountyAddressPoints2025_Jan2025_FeatureServer_0` | 21,107 | 21,107 | 0.00% | ok |
| 503 | `blkssRx_arcgis_rest_services_Address_Points_FeatureServer_24` | 21,103 | 21,103 | 0.00% | ok |
| 504 | `j53q3aOgCSYTp_arcgis_rest_services_Addresses_FeatureServer_0` | 21,092 | 21,092 | 0.00% | ok |
| 505 | `t_services_Peachtree_Corners_Address_Points_FeatureServer_14` | 21,065 | 21,065 | 0.00% | ok |
| 506 | `arcgis_rest_services_Master_Address_List_New_FeatureServer_0` | 21,055 | 21,055 | 0.00% | ok |
| 507 | `_rest_services_SiteStructureAddressPoint_utm_FeatureServer_0` | 21,018 | 21,018 | 0.00% | ok |
| 508 | `rcgis_rest_services_TLWaddressInternetAccess_FeatureServer_0` | 21,006 | 21,006 | 0.00% | ok |
| 509 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-5` | 20,977 | 20,977 | 0.00% | ok |
| 510 | `P7ekrLYcX5SF2z_arcgis_rest_services_COA_SSAP_FeatureServer_2` | 20,976 | 20,976 | 0.00% | ok |
| 511 | `est_services_City_of_Delaware_Address_Points_FeatureServer_0` | 20,965 | 20,965 | 0.00% | ok |
| 512 | `I7tkz4N_arcgis_rest_services_Address_Point_FeatureServer_105` | 20,937 | 20,937 | 0.00% | ok |
| 513 | `ington_Address_Points_for_Tyler_Technologies_FeatureServer_0` | 20,923 | 20,923 | 0.00% | ok |
| 514 | `za1rSdynU_arcgis_rest_services_AddressPoints_FeatureServer_0` | 20,906 | 20,906 | 0.00% | ok |
| 515 | `wdApEp_arcgis_rest_services_Lander_addresses_FeatureServer_0` | 20,894 | 20,894 | 0.00% | ok |
| 516 | `Zm_arcgis_rest_services_Aurora_Address_view_FeatureServer_15` | 20,861 | 20,861 | 0.00% | ok |
| 517 | `Kvz6SRPFWJ_arcgis_rest_services_Address_view_FeatureServer_8` | 20,857 | 20,857 | 0.00% | ok |
| 518 | `kyZtgsuWoNVtB_arcgis_rest_services_Addresses_FeatureServer_0` | 20,813 | 20,813 | 0.00% | ok |
| 519 | `is_rest_services_Redford_Address_Point_Layer_FeatureServer_0` | 20,784 | 20,784 | 0.00% | ok |
| 520 | `rcgis_rest_services_Address_Points_for_Hazus_FeatureServer_0` | 20,775 | 20,775 | 0.00% | ok |
| 521 | `gsuWoNVtB_arcgis_rest_services_Addresses2026_FeatureServer_0` | 20,770 | 20,770 | 0.00% | ok |
| 522 | `_services_AddressPoints_Placentia_July_2026_FeatureServer_16` | 20,737 | 20,737 | 0.00% | ok |
| 523 | `aN8Dr8M_arcgis_rest_services_AddressPoints23_FeatureServer_0` | 20,710 | 20,710 | 0.00% | ok |
| 524 | `s_rest_services_AddressPoints_Placentia_New2_FeatureServer_0` | 20,710 | 20,710 | 0.00% | ok |
| 525 | `rcgis_rest_services_Address_Points_CityView_FeatureServer_34` | 20,709 | 20,709 | 0.00% | ok |
| 526 | `3XOR63A7_arcgis_rest_services_AddressPoints_FeatureServer_34` | 20,709 | 20,709 | 0.00% | ok |
| 527 | `7aN8Dr8M_arcgis_rest_services_Address_Points_FeatureServer_0` | 20,701 | 20,701 | 0.00% | ok |
| 528 | `cgis_rest_services_BeltramiData_BeltramiOpenData_MapServer_0` | 20,671 | 20,671 | 0.00% | ok |
| 529 | `aJipPNFR_arcgis_rest_services_Address_Points_FeatureServer_0` | 20,666 | 20,666 | 0.00% | ok |
| 530 | `VVOdnGdbq_arcgis_rest_services_AddressPoints_FeatureServer_1` | 20,661 | 20,661 | 0.00% | ok |
| 531 | `3lusZ_arcgis_rest_services_CRB_Address_Point_FeatureServer_0` | 20,628 | 20,628 | 0.00% | ok |
| 532 | `V3Stz_arcgis_rest_services_EverettAddressPts_FeatureServer_0` | 20,596 | 20,596 | 0.00% | ok |
| 533 | `lOmSY_arcgis_rest_services_Address_PointsNEW_FeatureServer_0` | 20,587 | 20,587 | 0.00% | ok |
| 534 | `_services_Holyoke_AddressPointsMassGIS_52824_FeatureServer_0` | 20,517 | 20,517 | 0.00% | ok |
| 535 | `s_rest_services_HolyokeAddressPoints_MassGIS_FeatureServer_0` | 20,517 | 20,517 | 0.00% | ok |
| 536 | `Gw9ZnifOd3v8l_arcgis_rest_services_Addresses_FeatureServer_0` | 20,478 | 20,478 | 0.00% | ok |
| 537 | `arcgis_rest_services_AddressPoints_Placentia_FeatureServer_3` | 20,477 | 20,477 | 0.00% | ok |
| 538 | `Txj2_arcgis_rest_services_Driveway_Addresses_FeatureServer_0` | 20,456 | 20,456 | 0.00% | ok |
| 539 | `_arcgis_rest_services_AlexanderAddressPoints_FeatureServer_0` | 20,445 | 20,445 | 0.00% | ok |
| 540 | `ySt_arcgis_rest_services_Addresses_Structure_FeatureServer_2` | 20,437 | 20,437 | 0.00% | ok |
| 541 | `ry3ySt_arcgis_rest_services_Addresses_Road_FeatureServer_156` | 20,437 | 20,437 | 0.00% | ok |
| 542 | `acon_Address_Points_with_Availibility_050223_FeatureServer_0` | 20,437 | 20,437 | 0.00% | ok |
| 543 | `C9UDiTgJU_arcgis_rest_services_Address_Point_FeatureServer_0` | 20,402 | 20,402 | 0.00% | ok |
| 544 | `cgis_rest_services_AddressesWithElectionData_FeatureServer_0` | 20,202 | 20,202 | 0.00% | ok |
| 545 | `l9_arcgis_rest_services_svcBndryAddress_view_FeatureServer_1` | 20,088 | 20,088 | 0.00% | ok |
| 546 | `ZPiRSTUFu_arcgis_rest_services_Situs_Address_FeatureServer_0` | 20,040 | 40,080 | -100.00% | partial |
| 547 | `arcgis_rest_services_Winona_County_Addresses_FeatureServer_0` | 20,014 | 20,014 | 0.00% | ok |
| 548 | `st_services_WinonaCounty_DBO_CountyAddresses_FeatureServer_0` | 19,966 | 19,966 | 0.00% | ok |
| 549 | `rcgis_rest_services_Sioux_Falls_SD_Addresses_FeatureServer_1` | 19,812 | 19,812 | 0.00% | ok |
| 550 | `_arcgis_rest_services_Wyoming_SAMB_Addresses_FeatureServer_0` | 19,767 | 19,767 | 0.00% | ok |
| 551 | `jqaQHXGlt_arcgis_rest_services_AddressPoints_FeatureServer_0` | 19,634 | 19,634 | 0.00% | ok |
| 552 | `ervices_fulton_911_Online_address_publicview_FeatureServer_0` | 19,633 | 19,633 | 0.00% | ok |
| 553 | `rqC55zVw_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,611 | 19,611 | 0.00% | ok |
| 554 | `IEW_Addresses_NG911_Structure_Current_Active_FeatureServer_2` | 19,605 | 19,605 | 0.00% | ok |
| 555 | `_arcgis_rest_services_BrownE911AddressPoints_FeatureServer_0` | 19,577 | 19,577 | 0.00% | ok |
| 556 | `18b4b78b270efb1_rest_services_Accela_Accela_FeatureServer_79` | 19,544 | 19,544 | 0.00% | ok |
| 557 | `c71b3d4712db5c4e6a2_rest_services_Accela_Accela_MapServer_79` | 19,544 | 19,544 | 0.00% | ok |
| 558 | `rvices_Services_Public_Address_Points_Public_FeatureServer_0` | 19,527 | 19,527 | 0.00% | ok |
| 559 | `JJatlcMHWR_arcgis_rest_services_Address_View_FeatureServer_0` | 19,482 | 19,482 | 0.00% | ok |
| 560 | `gov_arcgis_rest_services_OpenData_Administrative_MapServer_1` | 19,464 | 19,464 | 0.00% | ok |
| 561 | `kj484GNt_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,439 | 19,439 | 0.00% | ok |
| 562 | `ppWGZsn5o_arcgis_rest_services_AddressPoints_FeatureServer_0` | 19,396 | 19,396 | 0.00% | ok |
| 563 | `_rest_services_Hopkins_County_Address_Points_FeatureServer_0` | 19,360 | 19,360 | 0.00% | ok |
| 564 | `uTYf_arcgis_rest_services_Bell_AddressPoints_FeatureServer_0` | 19,339 | 19,339 | 0.00% | ok |
| 565 | `sez_arcgis_rest_services_Tyler_Property_Data_FeatureServer_1` | 19,308 | 19,308 | 0.00% | ok |
| 566 | `st_services_Parcel_and_Addresses_Layers_WFL1_FeatureServer_3` | 19,248 | 19,248 | 0.00% | ok |
| 567 | `bGN_arcgis_rest_services_AddressPoint_DeSoto_FeatureServer_0` | 19,236 | 19,236 | 0.00% | ok |
| 568 | `rcgis_rest_services_AddressPoint_DeSoto_view_FeatureServer_0` | 19,223 | 19,223 | 0.00% | ok |
| 569 | `8hGa1_arcgis_rest_services_Opelika_Addresses_FeatureServer_0` | 19,209 | 19,209 | 0.00% | ok |
| 570 | `VDElDOMEad_arcgis_rest_services_Ohio_Address_FeatureServer_1` | 19,186 | 19,186 | 0.00% | ok |
| 571 | `dHIlQ88_arcgis_rest_services_LCaddresspts_GW_FeatureServer_0` | 19,161 | 38,284 | -99.80% | partial |
| 572 | `rcgis_rest_services_Facility_Sites_E911_Clip_FeatureServer_0` | 19,154 | 19,154 | 0.00% | ok |
| 573 | `EGe_arcgis_rest_services_City_Address_Points_FeatureServer_0` | 19,144 | 19,144 | 0.00% | ok |
| 574 | `st_services_Heritage_Register_Address_Points_FeatureServer_0` | 19,132 | 19,132 | 0.00% | ok |
| 575 | `tFEGe_arcgis_rest_services_CityAddressPoints_FeatureServer_0` | 19,130 | 19,130 | 0.00% | ok |
| 576 | `dHIlQ88_arcgis_rest_services_LCaddresspts_SB_FeatureServer_0` | 19,123 | 19,123 | 0.00% | ok |
| 577 | `nwcwJe4b_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,101 | 19,101 | 0.00% | ok |
| 578 | `rcgis_rest_services_Homestead_Address_Points_FeatureServer_1` | 19,071 | 19,071 | 0.00% | ok |
| 579 | `is_rest_services_Gloucester_County_Addresses_FeatureServer_0` | 19,037 | 19,037 | 0.00% | ok |
| 580 | `eA2I8MDz_arcgis_rest_services_Address_Points_FeatureServer_0` | 19,023 | 19,023 | 0.00% | ok |
| 581 | `n5o_arcgis_rest_services_AddressPts_3Oct2022_FeatureServer_0` | 19,015 | 19,015 | 0.00% | ok |
| 582 | `iSnaX0z0hS_arcgis_rest_services_MarionMSE911_FeatureServer_0` | 19,007 | 19,007 | 0.00% | ok |
| 583 | `RCn_arcgis_rest_services_brtn_address_points_FeatureServer_0` | 18,998 | 18,998 | 0.00% | ok |
| 584 | `Uw8wmJxSAcUEU_arcgis_rest_services_Addresses_FeatureServer_0` | 18,927 | 18,927 | 0.00% | ok |
| 585 | `_arcgis_rest_services_Hydrants_Address_Flood_FeatureServer_0` | 18,870 | 18,870 | 0.00% | ok |
| 586 | `K_arcgis_rest_services_masteraddresslocator_FeatureServer_21` | 18,858 | 18,858 | 0.00% | ok |
| 587 | `K_arcgis_rest_services_Master_Address_Table_FeatureServer_21` | 18,855 | 18,855 | 0.00% | ok |
| 588 | `BdHIlQ88_arcgis_rest_services_address_points_FeatureServer_0` | 18,850 | 18,850 | 0.00% | ok |
| 589 | `X4bb8_arcgis_rest_services_Fulton_NG911_WFL1_FeatureServer_0` | 18,822 | 18,822 | 0.00% | ok |
| 590 | `_org_arcgis_rest_services_Property_Addresses_FeatureServer_0` | 18,819 | 18,819 | 0.00% | ok |
| 591 | `_arcgis_rest_services_brtn_address_pointsNEW_FeatureServer_0` | 18,801 | 18,801 | 0.00% | ok |
| 592 | `arcgis_rest_services_City_of_Hutto_Addresses_FeatureServer_5` | 18,798 | 18,798 | 0.00% | ok |
| 593 | `tzEvlHpA_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,771 | 18,771 | 0.00% | ok |
| 594 | `t_services_Addresses_City_of_Laurinburg_view_FeatureServer_0` | 18,770 | 18,770 | 0.00% | ok |
| 595 | `Kfts6TQD_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,754 | 18,754 | 0.00% | ok |
| 596 | `SG_arcgis_rest_services_STJFD_Address_Points_FeatureServer_0` | 18,752 | 18,752 | 0.00% | ok |
| 597 | `s_rest_services_Addresses_BristolTN_SmartGov_FeatureServer_0` | 18,749 | 18,749 | 0.00% | ok |
| 598 | `rvices_NG911_Addresses_and_Roads_Public_View_FeatureServer_0` | 18,717 | 18,717 | 0.00% | ok |
| 599 | `cgis_rest_services_NG911_Addresses_and_Roads_FeatureServer_0` | 18,717 | 18,717 | 0.00% | ok |
| 600 | `arcgis_rest_services_Elm_Ridge_D10_Addresses_FeatureServer_0` | 18,716 | 18,716 | 0.00% | ok |
| 601 | `5SYpBlXQGJEB_arcgis_rest_services_AddressPts_FeatureServer_0` | 18,691 | 18,691 | 0.00% | ok |
| 602 | `arcgis_rest_services_Kennesaw_Address_Points_FeatureServer_0` | 18,686 | 18,686 | 0.00% | ok |
| 603 | `cgis_rest_services_Address_Points_Public_App_FeatureServer_0` | 18,676 | 18,676 | 0.00% | ok |
| 604 | `cOAaTE5R_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,676 | 18,676 | 0.00% | ok |
| 605 | `st_services_Sex_Offender_Ordinance_Addresses_FeatureServer_0` | 18,584 | 18,584 | 0.00% | ok |
| 606 | `tBHQoYlrmJI_arcgis_rest_services_address_pts_FeatureServer_1` | 18,526 | 37,031 | -99.89% | partial |
| 607 | `i1rmDSHF_arcgis_rest_services_ADDRESS_POINTS_FeatureServer_0` | 18,524 | 18,524 | 0.00% | ok |
| 608 | `y7JDhk1zQOJdo_arcgis_rest_services_Addresses_FeatureServer_0` | 18,517 | 18,517 | 0.00% | ok |
| 609 | `cgis_rest_services_County_AddressPoints_2025_FeatureServer_0` | 18,503 | 18,503 | 0.00% | ok |
| 610 | `rqLn_arcgis_rest_services_Site_Address_Point_FeatureServer_0` | 18,451 | 18,451 | 0.00% | ok |
| 611 | `Ki1rmDSHF_arcgis_rest_services_Address_Label_FeatureServer_0` | 18,451 | 18,451 | 0.00% | ok |
| 612 | `ezuma_co_us_arcgis_rest_services_OpenDataMap_FeatureServer_6` | 18,431 | 18,431 | 0.00% | ok |
| 613 | `gis_rest_services_County_Address_Points_2022_FeatureServer_0` | 18,423 | 18,423 | 0.00% | ok |
| 614 | `TEJ0Ki1rmDSHF_arcgis_rest_services_Addresses_FeatureServer_0` | 18,415 | 18,415 | 0.00% | ok |
| 615 | `i_arcgis_rest_services_Cass_Address_Points_FeatureServer_155` | 18,376 | 18,376 | 0.00% | ok |
| 616 | `gis_rest_services_Stouffville_Address_Points_FeatureServer_0` | 18,375 | 18,375 | 0.00% | ok |
| 617 | `est_services_AddressPointsRevised08292024_FC_FeatureServer_0` | 18,370 | 18,370 | 0.00% | ok |
| 618 | `ACHwgXJb_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,356 | 18,356 | 0.00% | ok |
| 619 | `3M1O_arcgis_rest_services_RSM_Address_Points_FeatureServer_0` | 18,324 | 18,324 | 0.00% | ok |
| 620 | `cgis_rest_services_Address_Number_Annotation_FeatureServer_4` | 18,300 | 18,300 | 0.00% | ok |
| 621 | `fBoQUIwDx_arcgis_rest_services_Address_Point_FeatureServer_4` | 18,292 | 18,292 | 0.00% | ok |
| 622 | `ervices_City_of_Friendswood___Address_Points_FeatureServer_2` | 18,288 | 18,288 | 0.00% | ok |
| 623 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@VA-2` | 18,275 | 18,275 | 0.00% | ok |
| 624 | `e_arcgis_rest_services_County_Address_Points_FeatureServer_0` | 18,257 | 18,257 | 0.00% | ok |
| 625 | `city_ca_arcgis_rest_services_Public_OpenData_FeatureServer_0` | 18,254 | 18,254 | 0.00% | ok |
| 626 | `ty_ca_arcgis_rest_services_Public_AGOLDataLayers_MapServer_1` | 18,252 | 18,252 | 0.00% | ok |
| 627 | `arcgis_rest_services_OpenData_Address_Points_FeatureServer_0` | 18,174 | 18,174 | 0.00% | ok |
| 628 | `rcgis_rest_services_Municipal_Address_Points_FeatureServer_0` | 18,146 | 18,146 | 0.00% | ok |
| 629 | `est_services_Addressing_AddressPoints_Public_FeatureServer_0` | 18,134 | 18,134 | 0.00% | ok |
| 630 | `DjI19VqyUMCS1_arcgis_rest_services_Addresses_FeatureServer_1` | 18,121 | 18,121 | 0.00% | ok |
| 631 | `Gyx40MXP_arcgis_rest_services_Address_Points_FeatureServer_0` | 18,007 | 18,007 | 0.00% | ok |
| 632 | `gis_rest_services_MSWD_Address_Points_Public_FeatureServer_1` | 17,972 | 17,972 | 0.00% | ok |
| 633 | `gis_rest_services_AddressPoints__public_view_FeatureServer_0` | 17,959 | 17,959 | 0.00% | ok |
| 634 | `s_rest_services_Master_Address_Database_view_FeatureServer_0` | 17,922 | 17,922 | 0.00% | ok |
| 635 | `s_rest_services_UA_LBRS_Address_Points_Layer_FeatureServer_0` | 17,914 | 17,914 | 0.00% | ok |
| 636 | `1fngp5cVBlk_arcgis_rest_services_SiteAddress_FeatureServer_0` | 17,914 | 17,914 | 0.00% | ok |
| 637 | `d0ZV_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 17,908 | 17,908 | 0.00% | ok |
| 638 | `r4_arcgis_rest_services_Addresses_30Dec2025_FeatureServer_14` | 17,898 | 17,898 | 0.00% | ok |
| 639 | `eGkGuRiFia_arcgis_rest_services_E911_Address_FeatureServer_1` | 17,871 | 17,871 | 0.00% | ok |
| 640 | `HA6Vis6l_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,859 | 17,859 | 0.00% | ok |
| 641 | `s_PARCEL2016_17_CENTROIDS_FOR_ADDRESS_POINTS_FeatureServer_0` | 17,812 | 17,812 | 0.00% | ok |
| 642 | `ervices_Braintree_Master_Address_Points_View_FeatureServer_0` | 17,794 | 17,794 | 0.00% | ok |
| 643 | `rest_services_Lakewood_Address_Points_032626_FeatureServer_1` | 17,765 | 17,765 | 0.00% | ok |
| 644 | `rvices_Address_Points_Riverton_Non_Sensitive_FeatureServer_0` | 17,761 | 17,761 | 0.00% | ok |
| 645 | `vices_Address_Points_Parcels_Storm_Fee_Areas_FeatureServer_3` | 17,761 | 17,761 | 0.00% | ok |
| 646 | `is_rest_services_Address_Point_and_Parcel_EH_FeatureServer_1` | 17,761 | 17,761 | 0.00% | ok |
| 647 | `a8zFF_arcgis_rest_services_Address_Locations_FeatureServer_0` | 17,753 | 17,753 | 0.00% | ok |
| 648 | `VXXqAFAr_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,752 | 17,752 | 0.00% | ok |
| 649 | `_arcgis_rest_services_Homestead_2024_Address_FeatureServer_0` | 17,744 | 17,744 | 0.00% | ok |
| 650 | `is_rest_services_Douglasville_Address_Points_FeatureServer_0` | 17,724 | 17,724 | 0.00% | ok |
| 651 | `st_services_Elgin_ISD_2025_26_Address_Points_FeatureServer_0` | 17,701 | 17,701 | 0.00% | ok |
| 652 | `vAo6IVI7r_arcgis_rest_services_AddressPoints_FeatureServer_0` | 17,700 | 17,700 | 0.00% | ok |
| 653 | `zX_arcgis_rest_services_Boone_Address_Points_FeatureServer_1` | 17,699 | 17,699 | 0.00% | ok |
| 654 | `YSp_arcgis_rest_services_Address_type_points_FeatureServer_0` | 17,698 | 17,698 | 0.00% | ok |
| 655 | `is_rest_services_ames_basemap_ALL_read_only_V2_MapServer_218` | 17,673 | 17,673 | 0.00% | ok |
| 656 | `OMEad_arcgis_rest_services_AddressRegionV_FZ_FeatureServer_0` | 17,672 | 17,672 | 0.00% | ok |
| 657 | `ervices_Langeberg_Street_Addresses__Public_FeatureServer_139` | 17,609 | 17,609 | 0.00% | ok |
| 658 | `ty_of_Friendswood__Open_Data__Address_Points_FeatureServer_2` | 17,600 | 17,600 | 0.00% | ok |
| 659 | `es_Addresses_Buildings_VacantParcels_Feb2025_FeatureServer_0` | 17,600 | 17,600 | 0.00% | ok |
| 660 | `iiR8VBXvcO_arcgis_rest_services_Site_Address_FeatureServer_0` | 17,568 | 17,568 | 0.00% | ok |
| 661 | `_services_us_mn_co_aitkin_loc_address_points_FeatureServer_0@未定位-1` | 17,533 | 17,533 | 0.00% | ok |
| 662 | `_rest_services_K_WS_Situs_ADD_SDE_2024_05_30_FeatureServer_0` | 17,519 | 17,519 | 0.00% | ok |
| 663 | `is_rest_services_WS_Situs_ADD_SDE_2024_05_30_FeatureServer_0` | 17,519 | 17,519 | 0.00% | ok |
| 664 | `teAddressPoints_OnlyUnionCounty_February2020_FeatureServer_0` | 17,510 | 17,510 | 0.00% | ok |
| 665 | `9s04rg0sr_arcgis_rest_services_AddressPoints_FeatureServer_0` | 17,490 | 17,490 | 0.00% | ok |
| 666 | `rcGIS_rest_services_Site_Address_Points_View_FeatureServer_0` | 17,483 | 17,483 | 0.00% | ok |
| 667 | `arcgis_rest_services_Longview_Address_Update_FeatureServer_0` | 17,479 | 17,479 | 0.00% | ok |
| 668 | `lkwfCfBjSM_arcgis_rest_services_AddressPoint_FeatureServer_0` | 17,462 | 17,462 | 0.00% | ok |
| 669 | `rcgis_rest_services_Address_Points_Only_WFL1_FeatureServer_0` | 17,440 | 17,440 | 0.00% | ok |
| 670 | `2hTY7c_arcgis_rest_services_Master_Addresses_FeatureServer_0` | 17,419 | 17,419 | 0.00% | ok |
| 671 | `ZsZ6el3f_arcgis_rest_services_Address_Points_FeatureServer_0` | 17,397 | 17,397 | 0.00% | ok |
| 672 | `eyGEfuc_arcgis_rest_services_MorganAddresses_FeatureServer_0` | 17,389 | 17,389 | 0.00% | ok |
| 673 | `x_arcgis_rest_services_Anna_Base_Data_Viewer_FeatureServer_3` | 17,383 | 17,383 | 0.00% | ok |
| 674 | `_rest_services_GrotonParcelsAndAddressPoints_FeatureServer_0` | 17,375 | 17,375 | 0.00% | ok |
| 675 | `rest_services_Morgan_Address_Points_Geocoded_FeatureServer_0` | 17,311 | 17,311 | 0.00% | ok |
| 676 | `ellington_ca_server_rest_services_Parcels_Public_MapServer_1` | 17,295 | 17,270 | 0.14% | failed |
| 677 | `ces_City_of_Friendswood_Addresses_for_Voting_FeatureServer_2` | 17,294 | 17,294 | 0.00% | ok |
| 678 | `vices_PublicServices_Public_Features_Group_1_FeatureServer_9` | 17,264 | 17,264 | 0.00% | ok |
| 679 | `erva_gov_arcgis_rest_services_Winchester_Address_MapServer_0` | 16,730 | 0 | 100.00% | failed |
| 680 | `st_services_Waste_Pro_Pickup_Days_Addresses_FeatureServer_36` | 16,234 | 16,234 | 0.00% | ok |
| 681 | `CS7Cz_arcgis_rest_services_Edmo911_Addresses_FeatureServer_0` | 15,870 | 15,870 | 0.00% | ok |
| 682 | `t_services_AddressPoints_forSANITARYSEWERAPP_FeatureServer_0` | 15,846 | 15,846 | 0.00% | ok |
| 683 | `7ccd0413_rest_services_Hosted_Address_Points_FeatureServer_0` | 15,838 | 15,838 | 0.00% | ok |
| 684 | `_rest_services_YanceyCountySiteAddressPoints_FeatureServer_0` | 15,772 | 15,772 | 0.00% | ok |
| 685 | `_ca_server_rest_services_OpenData_OpenData_Land_MapServer_10` | 15,764 | 15,764 | 0.00% | ok |
| 686 | `9Lu_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 15,741 | 15,741 | 0.00% | ok |
| 687 | `jTwPS9Lu_arcgis_rest_services_Address_Points_FeatureServer_0` | 15,741 | 15,741 | 0.00% | ok |
| 688 | `ygis_rest_services_Public_PowHUB_Landbase_Layers_MapServer_1` | 15,738 | 15,738 | 0.00% | ok |
| 689 | `whGYUH0pL_arcgis_rest_services_AddressPoints_FeatureServer_0` | 15,736 | 15,736 | 0.00% | ok |
| 690 | `5r1BMKyz_arcgis_rest_services_AddressPoints_FeatureServer_10` | 15,698 | 15,698 | 0.00% | ok |
| 691 | `est_services_Fire_Parcel_Address_Finder_WFL1_FeatureServer_1` | 15,657 | 15,657 | 0.00% | ok |
| 692 | `B5z0_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 15,641 | 15,641 | 0.00% | ok |
| 693 | `_rest_services_EXISTING_ADDRESS_POINTS_view2_FeatureServer_0` | 15,628 | 15,628 | 0.00% | ok |
| 694 | `DlUCS7Cz_arcgis_rest_services_Logan_911_View_FeatureServer_0` | 15,625 | 15,625 | 0.00% | ok |
| 695 | `est_services_Road_Centerlines_by_Maintenance_FeatureServer_2` | 15,579 | 15,579 | 0.00% | ok |
| 696 | `NqLU1DwuT_arcgis_rest_services_AddressPoints_FeatureServer_0` | 15,574 | 15,574 | 0.00% | ok |
| 697 | `gp_ab_ca_arcgis_rest_services_site_addresses_FeatureServer_0` | 15,569 | 15,569 | 0.00% | ok |
| 698 | `cgis_rest_services_SiteStructureAddressPoint_FeatureServer_0@未定位-3` | 15,545 | 15,545 | 0.00% | ok |
| 699 | `x33spbMD_arcgis_rest_services_Address_Points_FeatureServer_1` | 15,518 | 15,518 | 0.00% | ok |
| 700 | `on_wa_us_server_rest_services_Address_Master_FeatureServer_0` | 15,493 | 15,493 | 0.00% | ok |
| 701 | `cgis_rest_services_LibraryPatrons_AddressPts_FeatureServer_0` | 15,464 | 15,464 | 0.00% | ok |
| 702 | `ry_arcgis_rest_services_AddressEntrancePoint_FeatureServer_0` | 15,446 | 15,446 | 0.00% | ok |
| 703 | `sAU_arcgis_rest_services_COSJ_ADDRESS_POINTS_FeatureServer_0` | 15,428 | 15,428 | 0.00% | ok |
| 704 | `gis_rest_services_SealBeach_Addresses_082025_FeatureServer_0` | 15,410 | 15,410 | 0.00% | ok |
| 705 | `U5_arcgis_rest_services_Civic_Address_Points_FeatureServer_0` | 15,354 | 15,354 | 0.00% | ok |
| 706 | `arcgis_rest_services_GIS_AddressPoint_LKG911_FeatureServer_0` | 15,335 | 15,335 | 0.00% | ok |
| 707 | `yQSD0q_arcgis_rest_services_MASTER_Addresses_FeatureServer_0` | 15,330 | 15,330 | 0.00% | ok |
| 708 | `t_services_Fayette_County_Ohio_GIS_Addresses_FeatureServer_0` | 15,298 | 15,298 | 0.00% | ok |
| 709 | `rest_services_Houston_County_Address_Points_FeatureServer_10` | 15,239 | 15,239 | 0.00% | ok |
| 710 | `lDOMEad_arcgis_rest_services_Hancock_Address_FeatureServer_1` | 15,237 | 15,237 | 0.00% | ok |
| 711 | `arcgis_rest_services_Barnwell_Address_Points_FeatureServer_0` | 15,198 | 15,198 | 0.00% | ok |
| 712 | `s_rest_services_Tyler_County_Address_Points_FeatureServer_10` | 15,194 | 15,194 | 0.00% | ok |
| 713 | `_arcgis_rest_services_AddressBuilidings_View_FeatureServer_5` | 15,141 | 15,141 | 0.00% | ok |
| 714 | `X_arcgis_rest_services_Lafayette_NGAP_0427_FeatureServer_105` | 15,130 | 15,130 | 0.00% | ok |
| 715 | `4d1b0833552_rest_services_Basemaps_Addresses_FeatureServer_0` | 15,107 | 15,107 | 0.00% | ok |
| 716 | `_services_Stark_County_Address_Points_public_FeatureServer_1` | 15,064 | 15,064 | 0.00% | ok |
| 717 | `_services_Stark_County_Address_Points_public_FeatureServer_0` | 15,064 | 15,064 | 0.00% | ok |
| 718 | `PnUOHQnhsl_arcgis_rest_services_Address_view_FeatureServer_0` | 15,024 | 15,024 | 0.00% | ok |
| 719 | `nhsUu_arcgis_rest_services_Canmore_Addresses_FeatureServer_0` | 15,005 | 15,005 | 0.00% | ok |
| 720 | `_rest_services_Address_and_Centerline_Map_V4_FeatureServer_0` | 15,000 | 15,000 | 0.00% | ok |
| 721 | `h71mtnDG_arcgis_rest_services_E911_ADDRESSES_FeatureServer_0` | 14,991 | 14,991 | 0.00% | ok |
| 722 | `9pGRbGVB0nAAA_arcgis_rest_services_Addresses_FeatureServer_0` | 14,968 | 14,968 | 0.00% | ok |
| 723 | `VCGI_OPENDATA_Emergency_HYDRANTS_point_SP_v1_FeatureServer_0` | 14,960 | 14,960 | 0.00% | ok |
| 724 | `st_services_RDEK_Public_Webmap_20211110_WFL1_FeatureServer_3` | 14,959 | 14,959 | 0.00% | ok |
| 725 | `GJG22RSY_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,926 | 14,926 | 0.00% | ok |
| 726 | `rpDGOIDK_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,911 | 14,911 | 0.00% | ok |
| 727 | `vARAsxza_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,898 | 14,898 | 0.00% | ok |
| 728 | `rest_services_Address_Points___Edmonson_view_FeatureServer_0` | 14,862 | 14,862 | 0.00% | ok |
| 729 | `Vod_arcgis_rest_services_ELM_Situs_Addresses_FeatureServer_0` | 14,840 | 14,840 | 0.00% | ok |
| 730 | `is_rest_services_Emanuel_Address_Points_view_FeatureServer_0` | 14,814 | 14,814 | 0.00% | ok |
| 731 | `Xz_arcgis_rest_services_Site_Addresses_View_FeatureServer_12` | 14,794 | 14,794 | 0.00% | ok |
| 732 | `hBWbYdBZ_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,769 | 14,769 | 0.00% | ok |
| 733 | `ices_County_Point_Address_External_Viewlayer_FeatureServer_0` | 14,758 | 14,758 | 0.00% | ok |
| 734 | `s_rest_services_VirginiaAddressPoints_Clip_FeatureServer_144` | 14,732 | 14,732 | 0.00% | ok |
| 735 | `otW_arcgis_rest_services_Kerrville_Addresses_FeatureServer_0` | 14,713 | 14,713 | 0.00% | ok |
| 736 | `OamkQCWQM5KB8_arcgis_rest_services_E911_Clip_FeatureServer_0` | 14,677 | 14,677 | 0.00% | ok |
| 737 | `rcgis_rest_services_911_MyPermitsNow_located_FeatureServer_0` | 14,675 | 14,675 | 0.00% | ok |
| 738 | `cgis_rest_services_Cicero_Parcel_and_Address_FeatureServer_0` | 14,648 | 14,648 | 0.00% | ok |
| 739 | `XDC07yFxn_arcgis_rest_services_AddressPoints_FeatureServer_0` | 14,622 | 14,622 | 0.00% | ok |
| 740 | `84Po4FBDs_arcgis_rest_services_Address_Point_FeatureServer_0` | 14,616 | 26,616 | -82.10% | partial |
| 741 | `poec_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 14,614 | 14,614 | 0.00% | ok |
| 742 | `HtHcH5kGh_arcgis_rest_services_ADDRESSPOINTS_FeatureServer_0` | 14,594 | 14,594 | 0.00% | ok |
| 743 | `rcgis_rest_services_EnerGovParcelAddressProd_FeatureServer_1` | 14,566 | 14,566 | 0.00% | ok |
| 744 | `5kGh_arcgis_rest_services_ClerkAddressPoints_FeatureServer_0` | 14,562 | 14,562 | 0.00% | ok |
| 745 | `kqyKR88_arcgis_rest_services_Niles_Addresses_FeatureServer_0` | 14,511 | 14,511 | 0.00% | ok |
| 746 | `gis_rest_services_MSWD_AddressPoints_Active_FeatureServer_62` | 14,499 | 14,499 | 0.00% | ok |
| 747 | `us_arcgis_rest_services_Addressing_AddressPoints_MapServer_0` | 14,470 | 6,616 | 54.28% | failed |
| 748 | `services_Master_Address_File_CWDG_selection_FeatureServer_34` | 14,442 | 14,442 | 0.00% | ok |
| 749 | `Wt8807Pv_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,435 | 14,435 | 0.00% | ok |
| 750 | `rcgis_rest_services_FiberServicableAddresses_FeatureServer_0` | 14,421 | 14,421 | 0.00% | ok |
| 751 | `3LFZv_arcgis_rest_services_Address_Points_CC_FeatureServer_0` | 14,406 | 14,406 | 0.00% | ok |
| 752 | `qqHxBiQIog_arcgis_rest_services_Addresses4SG_FeatureServer_0` | 14,389 | 14,389 | 0.00% | ok |
| 753 | `FS_arcgis_rest_services_Civic_Address_Points_FeatureServer_1` | 14,346 | 14,346 | 0.00% | ok |
| 754 | `est_services_Join_Features_to_Address___View_FeatureServer_0` | 14,319 | 14,319 | 0.00% | ok |
| 755 | `O_arcgis_rest_services_WY_Teton_Address_view_FeatureServer_0` | 14,301 | 14,301 | 0.00% | ok |
| 756 | `eLCJ_arcgis_rest_services_PageCoVA_Addresses_FeatureServer_0` | 14,301 | 14,301 | 0.00% | ok |
| 757 | `l_arcgis_rest_services_ADDRPOINTS_2020_08_03_FeatureServer_0` | 14,288 | 14,288 | 0.00% | ok |
| 758 | `ibertymo_gov_arcgis_rest_services_Layers_Address_MapServer_0` | 14,286 | 14,286 | 0.00% | ok |
| 759 | `_rest_services_NewPhiladelphiaGIS_runningMap_FeatureServer_6` | 14,262 | 14,262 | 0.00% | ok |
| 760 | `t_services_Hosted_OpenGov_Permitting_Service_FeatureServer_0` | 14,261 | 14,261 | 0.00% | ok |
| 761 | `_arcgis_rest_services_NG911_Core_Data_VIEWER_FeatureServer_0` | 14,257 | 14,257 | 0.00% | ok |
| 762 | `ountyor_gov_server_rest_services_OpenData_Places_MapServer_0` | 14,256 | 14,256 | 0.00% | ok |
| 763 | `mJOdyNXk_arcgis_rest_services_Address_points_FeatureServer_4` | 14,221 | 14,221 | 0.00% | ok |
| 764 | `o_arcgis_rest_services_Tishomingo_addressing_FeatureServer_6` | 14,210 | 14,210 | 0.00% | ok |
| 765 | `X_arcgis_rest_services_Tishomingo_addressing_FeatureServer_6` | 14,210 | 14,210 | 0.00% | ok |
| 766 | `v_server_rest_services_GoldenMap_Golden_Misc_FeatureServer_1` | 14,175 | 14,175 | 0.00% | ok |
| 767 | `DVjy1gZox_arcgis_rest_services_AddressLabels_FeatureServer_0` | 14,161 | 14,161 | 0.00% | ok |
| 768 | `s_rest_services_Agawam_Address_Points_070826_FeatureServer_0` | 14,124 | 14,124 | 0.00% | ok |
| 769 | `gis_rest_services_AddressPointsAuth_05292025_FeatureServer_0` | 14,098 | 14,098 | 0.00% | ok |
| 770 | `5SQm_arcgis_rest_services_AddressPoints_view_FeatureServer_0` | 14,086 | 14,086 | 0.00% | ok |
| 771 | `s_rest_services_Kerrville_Site_Address_Point_FeatureServer_0` | 14,065 | 14,065 | 0.00% | ok |
| 772 | `wqf_arcgis_rest_services_AddressPointsPublic_FeatureServer_0` | 14,019 | 14,019 | 0.00% | ok |
| 773 | `ersite_rest_services_Hosted_Address_Points_FeatureServer_137` | 14,017 | 14,017 | 0.00% | ok |
| 774 | `2ZRTplQC_arcgis_rest_services_Address_Points_FeatureServer_0` | 14,017 | 14,017 | 0.00% | ok |
| 775 | `rvices_VityOfNewark_SiteAddress_Only_AGOL_FS_FeatureServer_2` | 13,998 | 13,998 | 0.00% | ok |
| 776 | `5yj_arcgis_rest_services_Address_Points_view_FeatureServer_0` | 13,987 | 13,987 | 0.00% | ok |
| 777 | `services_EnterpriseGIS_GISDBA_ADDRESS_POINTS_FeatureServer_0` | 13,987 | 13,987 | 0.00% | ok |
| 778 | `_arcgis_rest_services_Address_Points_Avenity_FeatureServer_0` | 13,981 | 13,981 | 0.00% | ok |
| 779 | `zUw0cVRX_arcgis_rest_services_Address_Points_FeatureServer_0` | 13,966 | 13,966 | 0.00% | ok |
| 780 | `H37M_arcgis_rest_services_Address_Points_MWP_FeatureServer_0` | 13,950 | 13,950 | 0.00% | ok |
| 781 | `arcgis_rest_services_WILDOMAR_ADDRESS_POINTS_FeatureServer_0` | 13,941 | 13,941 | 0.00% | ok |
| 782 | `rest_services_Trinity_County_Address_Points_FeatureServer_10` | 13,938 | 13,938 | 0.00% | ok |
| 783 | `nLVk_arcgis_rest_services_AddressPointsDEC25_FeatureServer_0` | 12,518 | 12,518 | 0.00% | ok |
| 784 | `is_rest_services_Address_Points__City_Limits_FeatureServer_0` | 12,513 | 12,513 | 0.00% | ok |
| 785 | `rk_County_Address_Points_Clip_AreaOfInterest_FeatureServer_0@ND-1` | 12,510 | 12,510 | 0.00% | ok |
| 786 | `icQLS_arcgis_rest_services_Address_GSPJ_view_FeatureServer_0` | 12,501 | 12,501 | 0.00% | ok |
| 787 | `Qeln9HQP_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,495 | 12,495 | 0.00% | ok |
| 788 | `cgis_rest_services_Address_Points__Open_Data_FeatureServer_0` | 12,475 | 12,475 | 0.00% | ok |
| 789 | `HpS7dOJQ_arcgis_rest_services_Addresses_View_FeatureServer_0` | 12,472 | 12,472 | 0.00% | ok |
| 790 | `uYk_arcgis_rest_services_Roads_and_Addresses_FeatureServer_0` | 12,470 | 12,470 | 0.00% | ok |
| 791 | `cgis_rest_services_Assumption_Address_Points_FeatureServer_0` | 12,470 | 12,470 | 0.00% | ok |
| 792 | `AOV9p4gC_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,463 | 12,463 | 0.00% | ok |
| 793 | `IHYICuzkgTNM_arcgis_rest_services_AddressDBS_FeatureServer_0` | 12,458 | 12,458 | 0.00% | ok |
| 794 | `CAX9v0Owj_arcgis_rest_services_AddressPoints_FeatureServer_0` | 12,432 | 12,432 | 0.00% | ok |
| 795 | `g1UCmgQ8_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,410 | 12,410 | 0.00% | ok |
| 796 | `est_services_BaseLayers_Address_Access_Point_FeatureServer_0` | 12,386 | 12,386 | 0.00% | ok |
| 797 | `ge_arcgis_rest_services_AddressRoadParcelESN_FeatureServer_0` | 12,367 | 12,367 | 0.00% | ok |
| 798 | `rest_services_2026_WC_Address_Points_service_FeatureServer_0` | 12,351 | 12,351 | 0.00% | ok |
| 799 | `rest_services_2022_WC_Address_Points_service_FeatureServer_0` | 12,349 | 12,349 | 0.00% | ok |
| 800 | `rest_services_2023_WC_Address_Points_service_FeatureServer_0` | 12,343 | 12,343 | 0.00% | ok |
| 801 | `_arcgis_rest_services_Address_Points_Payette_FeatureServer_0` | 12,339 | 12,339 | 0.00% | ok |
| 802 | `wd7ad0P0_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,337 | 12,337 | 0.00% | ok |
| 803 | `naX0z0hS_arcgis_rest_services_AddressingData_FeatureServer_0` | 12,331 | 12,331 | 0.00% | ok |
| 804 | `leycity_ca_server_rest_services_Maps_Open_Data_MapServer_182` | 12,321 | 12,321 | 0.00% | ok |
| 805 | `X8U_arcgis_rest_services_ParcelAddressPoints_FeatureServer_7` | 12,320 | 12,320 | 0.00% | ok |
| 806 | `corp_com_arcgis_rest_services_BentonCountyIA_WFS_MapServer_1` | 12,318 | 12,318 | 0.00% | ok |
| 807 | `s_rest_services_Ashley_County_Address_Points_FeatureServer_0` | 12,315 | 12,315 | 0.00% | ok |
| 808 | `Qx1O_arcgis_rest_services_AddressInCityLimit_FeatureServer_0` | 12,311 | 12,311 | 0.00% | ok |
| 809 | `TIvB0lzdRad0i_arcgis_rest_services_Addresses_FeatureServer_0` | 12,308 | 12,308 | 0.00% | ok |
| 810 | `t_services_us_mn_co_wabasha_loc_addresspoint_FeatureServer_0` | 12,267 | 12,267 | 0.00% | ok |
| 811 | `is_rest_services_Current_Arlington_Addresses_FeatureServer_0` | 12,267 | 12,267 | 0.00% | ok |
| 812 | `rxOA_arcgis_rest_services_CivicAddressPoints_FeatureServer_0` | 12,265 | 12,265 | 0.00% | ok |
| 813 | `DFVQ_arcgis_rest_services_Address_Points_R_A_FeatureServer_0` | 12,250 | 12,250 | 0.00% | ok |
| 814 | `7KciUs5nOw64q_arcgis_rest_services_Addresses_FeatureServer_0` | 12,240 | 12,240 | 0.00% | ok |
| 815 | `MSgI0g7r_arcgis_rest_services_Address_Points_FeatureServer_0` | 12,238 | 12,238 | 0.00% | ok |
| 816 | `4_arcgis_rest_services_GIS_AddressPoint_LUNE_FeatureServer_0` | 12,238 | 12,238 | 0.00% | ok |
| 817 | `rcgis_rest_services_Address_Pnts_Parcel_2022_FeatureServer_6` | 12,232 | 12,232 | 0.00% | ok |
| 818 | `2ORwJqb7OUkpO_arcgis_rest_services_addresses_FeatureServer_0` | 12,219 | 12,219 | 0.00% | ok |
| 819 | `rest_services_AddressPoints_Centerville_view_FeatureServer_0` | 12,206 | 12,206 | 0.00% | ok |
| 820 | `cgis_rest_services_AddressPoints_Centerville_FeatureServer_0` | 12,206 | 12,206 | 0.00% | ok |
| 821 | `rvices_Monroe_County_Site_Address_Points_911_FeatureServer_0` | 12,191 | 12,191 | 0.00% | ok |
| 822 | `0gnCAvCoAhpj_arcgis_rest_services_Addressing_FeatureServer_0` | 12,174 | 12,174 | 0.00% | ok |
| 823 | `SOeX2vv_arcgis_rest_services_Point_Addresses_FeatureServer_0` | 12,171 | 12,171 | 0.00% | ok |
| 824 | `cgis_rest_services_IN_Civic_Address_Points_FeatureServer_328` | 12,134 | 12,134 | 0.00% | ok |
| 825 | `CKvqg56E_arcgis_rest_services_Address_Points_FeatureServer_8` | 12,044 | 12,044 | 0.00% | ok |
| 826 | `lle_ca_arcgis_rest_services_Location_SiteAddress_MapServer_0` | 12,040 | 12,040 | 0.00% | ok |
| 827 | `_services_Braidwood_Address_Points_July_2016_FeatureServer_0` | 12,024 | 12,024 | 0.00% | ok |
| 828 | `_services_DHN_All_Addresses_Aug_4_2023_view_FeatureServer_54` | 11,997 | 11,997 | 0.00% | ok |
| 829 | `Ad6WMhA7fHTz_arcgis_rest_services_Addressing_FeatureServer_0` | 11,978 | 11,978 | 0.00% | ok |
| 830 | `int_Address_Unit_Level__Mailing_Address_View_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 831 | `t_Addresses__Unit_and_Apt_Level_Data_Exports_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 832 | `_rest_services_E911_Point_Address_Unit_Level_FeatureServer_0` | 11,956 | 11,956 | 0.00% | ok |
| 833 | `t_services_AC_CivicAddressPoints_Sept14_2021_FeatureServer_0` | 11,919 | 11,919 | 0.00% | ok |
| 834 | `est_services_SSLC_Residential_Address_Points_FeatureServer_0` | 11,895 | 11,895 | 0.00% | ok |
| 835 | `ces_Community_Buildings__Address_Points_View_FeatureServer_0` | 11,875 | 11,875 | 0.00% | ok |
| 836 | `vices_Guelph_and_Stats_Canada_Addresses_WFL1_FeatureServer_0` | 11,856 | 11,856 | 0.00% | ok |
| 837 | `VjVOYp6_arcgis_rest_services_Point_Addresses_FeatureServer_0` | 11,855 | 11,855 | 0.00% | ok |
| 838 | `9JtEo7N6_arcgis_rest_services_Addresses_view_FeatureServer_0` | 11,846 | 11,846 | 0.00% | ok |
| 839 | `bUyBqyyiCt_arcgis_rest_services_Address_View_FeatureServer_0` | 11,829 | 11,829 | 0.00% | ok |
| 840 | `ZJTbBa9X_arcgis_rest_services_Address_Points_FeatureServer_0` | 11,816 | 11,816 | 0.00% | ok |
| 841 | `ed_Address_Points_of_Gilpin_County_Colorado_FeatureServer_10` | 11,813 | 11,813 | 0.00% | ok |
| 842 | `I6Qk_arcgis_rest_services_Address_Points_NEW_FeatureServer_0` | 11,800 | 11,800 | 0.00% | ok |
| 843 | `x0tv46_arcgis_rest_services_ClintonAddresses_FeatureServer_0` | 11,779 | 11,779 | 0.00% | ok |
| 844 | `46_arcgis_rest_services_Lea_County_Addresses_FeatureServer_0` | 11,773 | 11,773 | 0.00% | ok |
| 845 | `t_services_StructureAddressPoints_publicTest_FeatureServer_1` | 11,771 | 11,771 | 0.00% | ok |
| 846 | `s_rest_services_E911_SMC_DATA_Address_Points_FeatureServer_0` | 11,758 | 11,758 | 0.00% | ok |
| 847 | `ning__Industrial__Parcels___Address_Map_WFL1_FeatureServer_0@NE-1` | 11,719 | 11,719 | 0.00% | ok |
| 848 | `ning__Industrial__Parcels___Address_Map_WFL1_FeatureServer_0@NE-2` | 11,719 | 11,719 | 0.00% | ok |
| 849 | `es_Address_Points_in_Tsunami_Inundation_Zone_FeatureServer_0` | 11,694 | 11,694 | 0.00% | ok |
| 850 | `H0fQHR1s_arcgis_rest_services_Address_Points_FeatureServer_2` | 11,635 | 11,635 | 0.00% | ok |
| 851 | `rcgis_rest_services_Bibb_Address_Points_E911_FeatureServer_0` | 11,633 | 11,633 | 0.00% | ok |
| 852 | `Zqc8NIv_arcgis_rest_services_Perry_Addresses_FeatureServer_0` | 11,605 | 11,605 | 0.00% | ok |
| 853 | `_arcgis_rest_services_Address_Points_Public_FeatureServer_37` | 11,589 | 11,589 | 0.00% | ok |
| 854 | `arcgis_rest_services_Site_Address_Point_view_FeatureServer_0` | 11,529 | 11,529 | 0.00% | ok |
| 855 | `t_services_Taylor_ISD_2024_25_Address_Points_FeatureServer_0` | 11,508 | 11,508 | 0.00% | ok |
| 856 | `1Hv4I6Qk_arcgis_rest_services_Address_Points_FeatureServer_4` | 11,466 | 11,466 | 0.00% | ok |
| 857 | `I6Qk_arcgis_rest_services_Address_Point_Test_FeatureServer_1` | 11,442 | 11,442 | 0.00% | ok |
| 858 | `BPeNRqI2rE8sfwz_arcgis_rest_services_Address_FeatureServer_0` | 11,430 | 11,430 | 0.00% | ok |
| 859 | `iKJaT7Upn_arcgis_rest_services_SDEAddressPts_FeatureServer_3` | 11,424 | 11,424 | 0.00% | ok |
| 860 | `8U_arcgis_rest_services_CC_Parcels_Addresses_FeatureServer_0` | 11,412 | 11,412 | 0.00% | ok |
| 861 | `gis_rest_services_Address_Points___Open_Data_FeatureServer_1` | 11,401 | 11,401 | 0.00% | ok |
| 862 | `o_arcgis_rest_services_Willingboro_Addresses_FeatureServer_4` | 11,360 | 11,360 | 0.00% | ok |
| 863 | `mni5zEMr_arcgis_rest_services_Address_Points_FeatureServer_0` | 11,355 | 11,355 | 0.00% | ok |
| 864 | `tJVh_arcgis_rest_services_Address_Points_PJ_FeatureServer_14` | 11,319 | 11,319 | 0.00% | ok |
| 865 | `_services_ROW_Land_Title_Address_Labels_WFL1_FeatureServer_1` | 11,300 | 11,300 | 0.00% | ok |
| 866 | `cgis_rest_services_Parcels_AddressesforEngov_FeatureServer_0` | 11,298 | 11,298 | 0.00% | ok |
| 867 | `14smu_arcgis_rest_services_SiteAddressPoints_FeatureServer_0` | 11,288 | 11,288 | 0.00% | ok |
| 868 | `Mf01B1N0W_arcgis_rest_services_AddressPoints_FeatureServer_0` | 11,286 | 11,286 | 0.00% | ok |
| 869 | `pa8_arcgis_rest_services_COSB_ADDRESS_POINTS_FeatureServer_0` | 11,245 | 11,245 | 0.00% | ok |
| 870 | `is_rest_services_Morehead_CityAddress_Points_FeatureServer_0` | 11,217 | 11,217 | 0.00% | ok |
| 871 | `_rest_services_Site_Structure_Address_Points_FeatureServer_1@TX-2` | 11,210 | 11,210 | 0.00% | ok |
| 872 | `g57sok_arcgis_rest_services_Address_Points_FeatureServer_108` | 11,202 | 11,202 | 0.00% | ok |
| 873 | `UH_arcgis_rest_services_France_Address_Pilot_FeatureServer_0` | 11,181 | 11,181 | 0.00% | ok |
| 874 | `s_rest_services_911_Site_Address_Points_0727_FeatureServer_0` | 11,170 | 11,170 | 0.00% | ok |
| 875 | `arcgis_rest_services_AddressSearchLayers_MCS_FeatureServer_0` | 11,148 | 11,148 | 0.00% | ok |
| 876 | `lc2PRESEUr5jw_arcgis_rest_services_Addresses_FeatureServer_7` | 11,130 | 11,130 | 0.00% | ok |
| 877 | `s_rest_services_Montclair_Twp_Address_Points_FeatureServer_0` | 11,122 | 11,122 | 0.00% | ok |
| 878 | `gis_rest_services_Parcel_Available_Addresses_FeatureServer_5` | 11,121 | 11,121 | 0.00% | ok |
| 879 | `s_Building_Footprints_500ft_Buffer_Intersect_FeatureServer_0` | 11,118 | 11,118 | 0.00% | ok |
| 880 | `uSp_arcgis_rest_services_Address_Leaf_Search_FeatureServer_0` | 11,044 | 11,044 | 0.00% | ok |
| 881 | `_Schererville_Address_Points_View_Layer_9722_FeatureServer_0` | 11,036 | 11,036 | 0.00% | ok |
| 882 | `ha_arcgis_rest_services_SiteAddressPoint_APN_FeatureServer_0` | 11,012 | 11,012 | 0.00% | ok |
| 883 | `NNPvtbwc_arcgis_rest_services_Address_Search_FeatureServer_0` | 10,968 | 10,968 | 0.00% | ok |
| 884 | `Pvc_arcgis_rest_services_Address_Points_View_FeatureServer_2` | 10,564 | 0 | 100.00% | failed |
| 885 | `18XGRt6t_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,600 | 9,600 | 0.00% | ok |
| 886 | `Ce9CL2ex9_arcgis_rest_services_AddressPoint_FeatureServer_67` | 9,592 | 9,592 | 0.00% | ok |
| 887 | `9CL2ex9_arcgis_rest_services_Address_Points_FeatureServer_10` | 9,590 | 9,590 | 0.00% | ok |
| 888 | `EK9DB_arcgis_rest_services_HC_Address_Points_FeatureServer_0` | 9,575 | 9,575 | 0.00% | ok |
| 889 | `xIXpWoaR2sAe_arcgis_rest_services_Addresses_FeatureServer_21` | 9,565 | 9,565 | 0.00% | ok |
| 890 | `ElDOMEad_arcgis_rest_services_Wetzel_Address_FeatureServer_1` | 9,557 | 9,557 | 0.00% | ok |
| 891 | `rest_services_public_PublicNotificationQuery_FeatureServer_0` | 9,543 | 9,543 | 0.00% | ok |
| 892 | `L2ex9_arcgis_rest_services_Address_Point_Int_FeatureServer_3` | 9,541 | 9,541 | 0.00% | ok |
| 893 | `arcgis_rest_services_Tecumseh_Address_Points_FeatureServer_1` | 9,533 | 9,533 | 0.00% | ok |
| 894 | `YcNK2j_arcgis_rest_services_2022ADDRESS_view_FeatureServer_0` | 9,530 | 9,530 | 0.00% | ok |
| 895 | `8MEELvtKj2_arcgis_rest_services_AddressPoint_FeatureServer_0` | 9,517 | 9,517 | 0.00% | ok |
| 896 | `Ony4j_arcgis_rest_services_NG911_Core_Data_2_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 897 | `cgis_rest_services_NG911_Final_DashboardView_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 898 | `rcgis_rest_services_NG911_Core_Data_1_Viewer_FeatureServer_0` | 9,497 | 9,497 | 0.00% | ok |
| 899 | `services_Scugog_Addresses_Wards_Intersection_FeatureServer_0` | 9,496 | 9,496 | 0.00% | ok |
| 900 | `_arcgis_rest_services_Scituate_AddressPoints_FeatureServer_0` | 9,495 | 9,495 | 0.00% | ok |
| 901 | `ymQJ3T_arcgis_rest_services_Hudson_Addresses_FeatureServer_0` | 9,477 | 9,477 | 0.00% | ok |
| 902 | `b0ovdJoIQKg_arcgis_rest_services_Base_Layers_FeatureServer_0` | 9,466 | 9,466 | 0.00% | ok |
| 903 | `k_arcgis_rest_services_Address_Points_Public_FeatureServer_0` | 9,440 | 9,440 | 0.00% | ok |
| 904 | `ovdJoIQKg_arcgis_rest_services_Situs_clipped_FeatureServer_0` | 9,435 | 9,435 | 0.00% | ok |
| 905 | `es_Swain_County_Address_Points___Public_View_FeatureServer_0` | 9,428 | 9,428 | 0.00% | ok |
| 906 | `pids_org_arcgis_rest_services_Public_Basemap_svc_MapServer_8` | 9,404 | 9,404 | 0.00% | ok |
| 907 | `jgFbdIrkt_arcgis_rest_services_LL_Addressing_FeatureServer_0` | 9,383 | 9,383 | 0.00% | ok |
| 908 | `OLPdETvKbspkC_arcgis_rest_services_Addresses_FeatureServer_0` | 9,380 | 9,380 | 0.00% | ok |
| 909 | `fftauX2_arcgis_rest_services_Address_Numbers_FeatureServer_5` | 9,369 | 9,369 | 0.00% | ok |
| 910 | `B_arcgis_rest_services_E911_Addresses_Binned_FeatureServer_0` | 9,362 | 9,362 | 0.00% | ok |
| 911 | `uQ_arcgis_rest_services_Master_Address_Table_FeatureServer_1` | 9,352 | 9,352 | 0.00% | ok |
| 912 | `Hqqcg7Zo8zH_arcgis_rest_services_Address_Pts_FeatureServer_0` | 9,337 | 9,337 | 0.00% | ok |
| 913 | `rcgis_rest_services_GrantCountyAddressPoints_FeatureServer_1` | 9,307 | 9,307 | 0.00% | ok |
| 914 | `1tOY_arcgis_rest_services_Address_Points_HMP_FeatureServer_0` | 9,296 | 9,296 | 0.00% | ok |
| 915 | `OUVqNUhbTXzVc_arcgis_rest_services_Addresses_FeatureServer_0` | 9,295 | 9,295 | 0.00% | ok |
| 916 | `WLJiNAJwJ_arcgis_rest_services_AddressPoints_FeatureServer_1` | 9,293 | 9,293 | 0.00% | ok |
| 917 | `arcgis_rest_services_SSSD_Address_and_Parcel_FeatureServer_0` | 9,280 | 9,280 | 0.00% | ok |
| 918 | `est_services_Address_Points_with_Parcel_Data_FeatureServer_0` | 9,272 | 9,272 | 0.00% | ok |
| 919 | `est_services_Montville_Address_Points_061826_FeatureServer_0` | 9,271 | 9,271 | 0.00% | ok |
| 920 | `est_services_Montville_Address_Points_061226_FeatureServer_0` | 9,271 | 9,271 | 0.00% | ok |
| 921 | `uxxuV9tV_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,268 | 9,268 | 0.00% | ok |
| 922 | `58_rest_services_Clive_Clive_Land_Record_Service_MapServer_0` | 9,257 | 9,257 | 0.00% | ok |
| 923 | `Jkj1aWl_arcgis_rest_services_E911_AddressPts_FeatureServer_0` | 9,234 | 9,234 | 0.00% | ok |
| 924 | `rcgis_rest_services_E911_AddressPts_FirstDue_FeatureServer_0` | 9,234 | 9,234 | 0.00% | ok |
| 925 | `gis_rest_services_AddressPointsSanDiego_Clip_FeatureServer_0` | 9,212 | 9,212 | 0.00% | ok |
| 926 | `q0JXOtjNW10pz_arcgis_rest_services_Addresses_FeatureServer_0` | 9,202 | 9,202 | 0.00% | ok |
| 927 | `ices_OpenDataHub_TOV_AddressPoints_OpenData_FeatureServer_36` | 9,186 | 9,186 | 0.00% | ok |
| 928 | `cgis_rest_services_SE_Address_Points_8_19_26_FeatureServer_0` | 9,171 | 9,171 | 0.00% | ok |
| 929 | `q6rKKp0o_arcgis_rest_services_Address_Points_FeatureServer_0` | 9,168 | 9,168 | 0.00% | ok |
| 930 | `is_rest_services_ADDRESS_POINTS_10152025_shp_FeatureServer_0` | 9,165 | 9,165 | 0.00% | ok |
| 931 | `services_addresspoints_identifiedServiceArea_FeatureServer_0` | 9,158 | 9,158 | 0.00% | ok |
| 932 | `ices_CrawfordIL_CityofRobinson_AddressPoints_FeatureServer_0` | 9,154 | 9,154 | 0.00% | ok |
| 933 | `jCtQj_arcgis_rest_services_AddressPoints2022_FeatureServer_0` | 9,146 | 9,146 | 0.00% | ok |
| 934 | `z9O_arcgis_rest_services_OpenGovAddress_view_FeatureServer_2` | 9,145 | 9,145 | 0.00% | ok |
| 935 | `OMEad_arcgis_rest_services_Doddridge_Address_FeatureServer_1` | 9,144 | 9,144 | 0.00% | ok |
| 936 | `gis_rest_services_911_Address_Points_PC_2024_FeatureServer_0` | 9,129 | 9,129 | 0.00% | ok |
| 937 | `ices_Assessor_Data_Webster_Parish_Address_Points_MapServer_0` | - | 0 | 0.00% | empty |
| 938 | `DDRnnsbCKWWP_arcgis_rest_services_Addresses2_FeatureServer_0` | - | 25,659 | 0.00% | empty |
| 939 | `_rest_services_NG24DataModelUpdate_WFL1_view_FeatureServer_0` | - | 0 | 0.00% | empty |
| 940 | `gis_rest_services_Municipal_Address_Points_FeatureServer_214` | - | 0 | 0.00% | empty |
| 941 | `almbeach_com_arcgis_rest_services_BaseData_Situs_MapServer_0` | - | 0 | 0.00% | failed |
| 942 | `us_server_rest_services_NG911_Address_Points_FeatureServer_3` | - | 0 | 0.00% | empty |
| 943 | `_mn_us_server_rest_services_NG911_Address_Points_MapServer_3` | - | 0 | 0.00% | empty |
| 944 | `ca_gov_server_rest_services_Address_Range_Labels_MapServer_0` | - | 0 | 0.00% | failed |
| 945 | `gis_rest_services_Hosted_Master_Address_File_FeatureServer_0` | - | 0 | 0.00% | empty |
| 946 | `_com_geoserver_rest_services_Public_GIS_Data_FeatureServer_0` | - | 0 | 0.00% | empty |
| 947 | `paca_wi_us_arcgis_rest_services_Public_OpenData_MapServer_24` | - | 0 | 0.00% | failed |
| 948 | `s_rest_services_DynamicMaps_Address_Explorer_Map_MapServer_1` | - | 0 | 0.00% | empty |
| 949 | `_org_gisarcweb_rest_services_Base_Base_Addresses_MapServer_0` | - | 0 | 0.00% | empty |
| 950 | `fpl_arcgis_rest_services_ArcGISHub_OpenData_FeatureServer_13` | - | 0 | 0.00% | empty |
| 951 | `ervices_DataPortal_DataPortal_BuildingsAddresses_MapServer_0` | - | 0 | 0.00% | failed |
| 952 | `county_com_arcgis_rest_services_features_Address_MapServer_0` | - | 0 | 0.00% | failed |
| 953 | `st_services_Schools_ChathamSchools_AddressPoints_MapServer_0` | - | 0 | 0.00% | empty |
| 954 | `untywi_gov_vilasgis_rest_services_V4_SiteAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 955 | `tamonica_gov_server_rest_services_Address_Points_MapServer_0` | - | 0 | 0.00% | failed |
| 956 | `g_arcgis_rest_services_Search_SMSA_ParcelAddress_MapServer_0` | - | 0 | 0.00% | failed |
| 957 | `rb80Pvlu_arcgis_rest_services_Address_Points_FeatureServer_0` | - | 0 | 0.00% | empty |
| 958 | `_services_NG911_ReadOnly_NG911_Addressing_Layers_MapServer_0` | - | 0 | 0.00% | failed |
| 959 | `buncombecounty_org_arcgis_rest_services_opendata_MapServer_2` | - | 0 | 0.00% | failed |
| 960 | `unty_org_arcgis_rest_services_OpenData_Property_MapServer_12` | - | 0 | 0.00% | empty |
| 961 | `g_arcgis_rest_services_Open_Data_Open_Data_1_FeatureServer_2` | - | 0 | 0.00% | empty |
| 962 | `_services_Address_Points_AddressPoint_Native_FeatureServer_0@未定位-2` | - | 0 | 0.00% | empty |

## 六、复现

```bash
gh workflow run collect-full.yml -f stage=05b
python3 collect/full_plan.py --stage 05b --size 3 --out collect/ledger/05b_plan.json
python3 collect/full_shard.py --stage 05b --shard 0 --plan collect/ledger/05b_plan.json
```
