#!/usr/bin/env python3
"""把 recompute-stats.json 渲染成 REPORT.md 的数据段（避免手抄数字出错）。

  python3 analysis/engine-pilot-20261125/render_report.py
只读 recompute-stats.json / summary.json，不改任何数据。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = ("tier1", "tier2", "tier3", "unrated")
GRADES = ("S", "A", "B", "C")


def main() -> int:
    rs = json.load(open(os.path.join(HERE, "recompute-stats.json"), encoding="utf-8"))
    sm = json.load(open(os.path.join(HERE, "summary.json"), encoding="utf-8"))
    L = []
    A = L.append
    A("# 三州试点 · 分级结果（数据段自动生成）\n")
    A(f"- 生成时间：{sm.get('generated_utc')}　配置：`{sm.get('config')}`")
    A(f"- addrkey：`{sm['addrkey']['version']}` 前缀 `{sm['addrkey']['prefix']}:`，"
      f"include_unit={sm['addrkey']['include_unit']}，hash={sm['addrkey']['hash']}")
    A(f"- 方言：registry {len(sm['dialects']['registry'])} 支 + engine 扩展 {len(sm['dialects']['engine'])} 支；"
      f"unsupported = **{sm['unsupported']}** 条\n")

    A("## 1. 去重前后（每州）\n")
    A("| 州 | 输入行数 | 去重后行数 | 合并掉（dup） | 多源同址 | unkeyed | 低于 min_grade 丢弃 | 跨州丢弃 | 有坐标 |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for st, v in rs["states"].items():
        if v.get("status") == "not_run":
            A(f"| {st} | — | — | — | — | — | — | — | — |")
            continue
        A(f"| {st} | {v['rows_in']:,} | {v['deduped_rows']:,} | {v['dup_rows']:,} | {v['multi_source']:,} | "
          f"{v['unkeyed_rows']:,} | {v['dropped_low_grade']:,} | {v.get('dropped_out_of_state', 0):,} | "
          f"{v['with_point']:,} |")
    t = rs["totals"]
    A(f"| **合计** | **{t.get('rows_in', 0):,}** | **{t.get('deduped_rows', 0):,}** | **{t.get('dup_rows', 0):,}** | "
      f"— | — | — | — | — |\n")

    A("## 2. 分级分布 S/A/B/C（每州）\n")
    A("| 州 | S | A | B | C | 合计 |")
    A("|---|---:|---:|---:|---:|---:|")
    for st, v in rs["states"].items():
        if v.get("status") == "not_run":
            continue
        g = v["by_grade"]
        A(f"| {st} | {g['S']:,} | {g['A']:,} | {g['B']:,} | {g['C']:,} | {sum(g.values()):,} |")
    A("")

    A("## 3. 分档 × 完整度（每州网格）\n")
    for st, v in rs["states"].items():
        if v.get("status") == "not_run":
            continue
        A(f"### {st}\n")
        A("| Tier | S | A | B | C | 小计 |")
        A("|---|---:|---:|---:|---:|---:|")
        for ti in TIERS:
            g = v["grid"][ti]
            A(f"| {ti} | {g['S']:,} | {g['A']:,} | {g['B']:,} | {g['C']:,} | {sum(g.values()):,} |")
        A("")

    A("## 4. 每州输入源明细\n")
    for st, v in rs["states"].items():
        if v.get("status") == "not_run" or not v.get("sources"):
            continue
        A(f"### {st}\n")
        A("| 源 | 方言 | 适配器 | 文件数 | 输入行数 | 耗时(s) | 说明 |")
        A("|---|---|---|---:|---:|---:|---|")
        for s in v["sources"]:
            A(f"| `{s['id']}` | `{s['dialect']}` | `{s['adapter']}` | {s['files']} | {s['rows_in']:,} | "
              f"{s['secs']} | {'街段区间（不出点）' if s.get('range_only') else '地址行'} |")
        extra = []
        if v.get("tiger_street_keys"):
            extra.append(f"TIGER 确认街名键 {v['tiger_street_keys']:,}")
        if v.get("interpolated"):
            extra.append(f"插值点行 {v['interpolated']:,}")
        if v.get("coord_conflict"):
            extra.append(f"同址坐标冲突行 {v['coord_conflict']:,}")
        A("\n" + ("；".join(extra) + "\n" if extra else ""))

    A("## 5. 复算方式\n")
    A("```bash\npython3 analysis/engine-pilot-20261125/recompute.py    # 只读产物重算 → recompute-stats.json\n"
      "python3 analysis/engine-pilot-20261125/render_report.py   # 由 recompute-stats.json 渲染本文件\n```\n")
    open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))
    print("wrote REPORT.md", len(L), "lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
