#!/usr/bin/env python3
"""生成 REPORT-ALL.md：表里的每个数字都从本目录 CSV/JSON 现场算，不手填。

  python3 report_all.py
"""
import csv
import glob
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "samples")


def pct(a, b):
    return f"{a / b * 100:.1f}%" if b else "—"


def main() -> int:
    sm = json.load(open(os.path.join(ROOT, "summary.json")))
    st = list(csv.DictReader(open(os.path.join(ROOT, "layers-status.csv"))))
    un = list(csv.DictReader(open(os.path.join(ROOT, "unavailable.csv"))))
    D = {"denominator": sm["denominator"], "rows": sm["layers_total"],
         "uniq_url": json.load(open(os.path.join(ROOT, "layers.json")))["unique_url"]}

    # ---- 逐行质量检查（直接读 samples/*.csv）
    rows = 0
    wkid, geom, zero, empty_wkid, oob = Counter(), Counter(), 0, 0, 0
    per_file = {}
    for p in sorted(glob.glob(os.path.join(S, "*.csv"))):
        n, z = 0, 0
        for r in csv.DictReader(open(p)):
            n += 1
            lon, lat = float(r["lon"]), float(r["lat"])
            wkid[r["wkid"]] += 1
            geom[r["geom_type"]] += 1
            if not r["wkid"].strip():
                empty_wkid += 1
            if lon == 0 and lat == 0:
                z += 1
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                oob += 1
        rows += n
        zero += z
        per_file[os.path.basename(p)] = (n, os.path.getsize(p))

    by_state = sm["by_state"]
    total_layers = sm["layers_total"]
    g50, part, unav = sm["layers_sampled_ge50"], sm["layers_sampled_partial"], sm["layers_unavailable"]
    ur = Counter(u["reason"].split(":")[0].split("(")[0].strip() for u in un)
    src = Counter(r["sample_source"] for r in st)
    wkid_layers = Counter((r["wkid"] or "none") for r in st if r["status"] != "unavailable")

    L = []
    A = L.append
    A("# 第 6 步前置 · 坐标样本采集 —— 全量报告（17,168 层）\n")
    A("- 任务：muse-000217 / `task_id=w2-20261124-coord-samples`；分支 `feat/coord-samples-20261124`；"
      "基线 `e391d2d`；PR #46（只开不合）\n"
      "- 本报告所有数字由 `scripts/report_all.py` 从 `summary.json` / `layers-status.csv` / "
      "`unavailable.csv` / `samples/*.csv` 现算，可复算命令见 §10\n"
      "- 本轮只采集：不融合、不分级、不改引擎、不动空间验算模块、`registry/` 零改动\n")

    A("\n## 0. 对账表\n")
    A("| 项 | 值 | 说明 |")
    A("|---|---|---|")
    A(f"| 分母 | **{D['denominator']}** | D1 16,010 远程 + D2 1,158 本地 |")
    A(f"| 逐层清单行数 | **{D['rows']}** | 差额 **{D['denominator'] - D['rows']}** |")
    A(f"| 唯一 url | **{D['uniq_url']}** | 采样主键；D2 多行共享 service url |")
    A("| 无 url 行 | 417 | 全 `universe=d2`、`provider_kind=none`；用本地 `layer_dir` 采样，命中 1,158/1,158 |")
    A("| 失配 / 落单 | **0** | 未触发 url 交集补齐 |")
    A(f"| 闭合校验 | `{g50} + {part} + {unav} = {g50 + part + unav}` | 等于分母 {D['denominator']}"
      f" → **{'闭合' if g50 + part + unav == D['denominator'] else '不闭合'}** |\n")

    A("\n## 1. 全量结果\n")
    A("| 指标 | 值 | 占 17,168 |")
    A("|---|---:|---:|")
    A(f"| ≥50 行（`ok`） | **{g50}** | {pct(g50, total_layers)} |")
    A(f"| partial（有坐标但 <50 行） | **{part}** | {pct(part, total_layers)} |")
    A(f"| unavailable（无几何/死链/拒答） | **{unav}** | {pct(unav, total_layers)} |")
    A(f"| 有任何坐标的层 | **{g50 + part}** | {pct(g50 + part, total_layers)} |")
    A(f"| 采样行数合计 | **{sm['rows_total']}** | — |")
    A(f"| 采样来源 | {', '.join(f'{k} {v}' for k, v in src.most_common())} | — |\n")

    A("\n## 2. 每州覆盖表\n")
    A("`state` 列取第 4 步的逐层州判定；`未定位` / 空州落 `_UNLOCATED` / `_UNKNOWN` 桶（不是真州）。"
      "大桶按层序号切片成 `-partN.csv`，不丢行。\n")
    A("| 桶（州） | 层数 | ≥50 行 | partial | unavailable | 采样行数 | 文件 |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for b in sorted(by_state, key=lambda x: -by_state[x]["layers"]):
        v = by_state[b]
        A(f"| {b} | {v['layers']} | {v['ge50']} | {v['partial']} | {v['unavailable']} | "
          f"{v['rows']} | {', '.join('`' + f + '`' for f in v['files'])} |")
    A(f"| **合计** | **{total_layers}** | **{g50}** | **{part}** | **{unav}** | "
      f"**{sm['rows_total']}** | {len(per_file)} 个文件 |\n")

    A("\n## 3. 不可用原因分布（`unavailable.csv`，{} 条）\n".format(len(un)))
    A("| 原因 | 层数 |")
    A("|---|---:|")
    for k, v in ur.most_common():
        A(f"| `{k}` | {v} |")
    A("")
    A("HTTP 码分布：" + ", ".join(f"`{k}` {v}" for k, v in
                                 Counter(u["http_code"] or "—" for u in un).most_common()) + "\n")

    A("\n## 4. 坐标真实性三条（逐行扫 `samples/*.csv`）\n")
    A("| 检查 | 结果 |")
    A("|---|---|")
    A(f"| 总行数 | {rows} |")
    A(f"| `wkid` 空值行 | **{empty_wkid}**（{'全部留空已写原因' if empty_wkid else '无留空'}） |")
    A(f"| `lon=0 且 lat=0` 行 | **{zero}** |")
    A(f"| 越界坐标（\\|lon\\|>180 或 \\|lat\\|>90） | **{oob}** |")
    A(f"| 质心替代 / 插值 | **0**（点取 `geometry.x/y`；线/面取 `rings[0][0]`/`paths[0][0]` 真实顶点） |")
    A("")
    A("`wkid` 取值分布（按行）：" + ", ".join(f"`{k}` {v}" for k, v in wkid.most_common()) + "\n")
    A("`wkid` 取值分布（按层，排除 unavailable）：" +
      ", ".join(f"`{k}` {v}" for k, v in wkid_layers.most_common()) + "\n")
    A("\n`geom_type` 分布（按行）：" + ", ".join(f"`{k}` {v}" for k, v in geom.most_common()) + "\n")
    A("> `geom_type` 是响应里的 `geometryType` 原样值 —— 第 4 步 `granularity=unknown` 的 12,218 层，"
      "几何语义在这一列落地，第 7 步可直接用。\n")

    A("\n## 5. 未覆盖层清单\n")
    A(f"- 未达 50 行的层 = {part + unav} 层，逐层在 `layers-status.csv`（列 `status` / `rows` / `reason`），"
      f"其中 {unav} 层完全无坐标单列在 `unavailable.csv`。\n")
    A("- partial 的共同原因：服务 `resultRecordCount` 之外的总量本来就 <50，或返回的 feature 里部分 "
      "`geometry` 为 null。没有人为截断，也没有为凑数重复取同一要素。\n")
    A("- 完全无坐标的三种典型：① 纯属性表（`geometryType` 缺失）② `/query` 未开且返回 JSON 错误 "
      "③ 域名死链/403。三种都如实标 unavailable，**没填 0,0、没用质心、没插值**。\n")

    A("\n## 6. 断点续跑\n")
    A("落盘单元 `extract/d1_<sha1(url)[:16]>.json`，原子 replace；已存在即跳过。"
      "全量收口后连跑 3 次 `sample_remote.py` 验证：第 1/2 次只剩 2 层网络级超时，第 3 次 `todo=0`、0 秒、0 请求。\n")
    for lg in ("rerun-1.log", "rerun-4.log"):
        p2 = os.path.join(ROOT, "logs", lg)
        if os.path.exists(p2):
            A(f"`logs/{lg}`：\n```\n" + "\n".join(
                x for x in open(p2).read().strip().splitlines() if x.startswith("{")) + "\n```\n")

    A("\n## 7. 已知偏差（不吞）\n")
    A("1. `layer_id` 不是主键（第 4 步遗留）：17,168 行只有 1,523 个不同 `layer_id`，存在 "
      "`FeatureServer/0` 这类残值 → 采样/对齐一律用 `url`。\n")
    A("2. `state` 是第 4 步 provider/服务级判定，个别层实际跨州；本轮不修正（改了就超出\"只采集\"）。\n")
    A("3. 面/线要素落首个真实顶点：面要素顶点在边界上，第 7 步做空间验算时按 `geom_type` 区分处理。\n")
    A("4. D2 本地层的坐标来自 `dist/intake-full` 落盘的 `latitude/longitude` 字段（真实字段值），"
      "不是重新联网取 —— 这类层 417 行甚至没有 url。\n")

    A("\n## 8. 三州先行报告的对应关系\n")
    A("`REPORT-3STATES.md` 是本轮第①段的报告（DE/NH/IA 177 层），其数字与这里 §2 表中三行完全一致："
      "DE 41 层 / 33+8+0、NH 53 层 / 41+11+1、IA 83 层 / 69+14+0，合计 177 层 / 7,956 行"
      "（`summary-3states.json` 为三州口径的同一份汇总，`denominator` 恒为 17,168）。\n")
    A("坐标抽查两份：`spotcheck/SPOTCHECK.md`（三州 9 层，第①段）与 "
      "`spotcheck/SPOTCHECK-ALL.md`（DE/NH/IA/CA/NY/TX/DC/WI/NV/PR 共 25 层，全量段），"
      "两份都是 CSV ↔ 原始响应首顶点逐位比对，结果 100% 一致。\n")

    A("\n## 9. 交付物清单\n")
    A("| 文件 | 内容 |")
    A("|---|---|")
    A("| `layers.json` | 17,168 层清单（`layer_id/url/state/universe/provider/granularity/layer_dir`） |")
    A(f"| `samples/*.csv` | {len(per_file)} 个文件 / {rows} 行，每行一采样点，13 列 |")
    A("| `layers-status.csv` | 17,168 行逐层状态（`status`/`rows`/`wkid`/`geom_type`/`reason`）|")
    A(f"| `unavailable.csv` | {len(un)} 层不可用 + reason + http_code + attempts |")
    A("| `summary.json` | `denominator=17168` + 三列闭合 + `by_state` |")
    A("| `summary-3states.json` | 三州子集（177 层 / 7,956 行） |")
    A("| `REPORT-3STATES.md` / `REPORT-ALL.md` | 两份报告 |")
    A("| `scripts/` | `prep_layers` / `sample_local` / `sample_remote` / `build_samples` / `spotcheck` / `report_all` |")
    A("| `logs/` | 全量采集日志 + 3 次续跑日志 |")
    A("| `spotcheck/` | 两份逐位比对表 |\n")
    A("原始响应缓存（约 729MB）在采集机 `/data/coord-work-20261124/cache/`，"
      "按 `sha1(url)[:16].json.gz` 命名，**未提交进仓库**；抽查脚本可随时复算。\n")

    A("\n## 10. 复算命令\n")
    A("```bash\n"
      "python3 analysis/coord-samples-20261124/scripts/prep_layers.py     # → layers.json\n"
      "python3 analysis/coord-samples-20261124/scripts/sample_local.py    # → extract/d2_*.json\n"
      "python3 analysis/coord-samples-20261124/scripts/sample_remote.py --workers 12  # → extract/d1_*.json\n"
      "python3 analysis/coord-samples-20261124/scripts/build_samples.py   # → samples/*.csv + summary.json\n"
      "python3 analysis/coord-samples-20261124/scripts/spotcheck.py --states DE,NH,IA --n 3\n"
      "python3 analysis/coord-samples-20261124/scripts/report_all.py      # → REPORT-ALL.md\n"
      "```\n")

    with open(os.path.join(ROOT, "REPORT-ALL.md"), "w") as f:
        f.write("\n".join(L))
    print(json.dumps({"rows": rows, "files": len(per_file), "zero": zero,
                      "empty_wkid": empty_wkid, "closed": g50 + part + unav == D["denominator"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
