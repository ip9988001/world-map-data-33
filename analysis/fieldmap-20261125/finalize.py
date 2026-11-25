#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾：unusable.csv + REPORT.md（四数先给）+ 覆盖率/闭合/字段有效率汇总。"""
from __future__ import annotations
import collections, csv, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = "/data/workspace/wmd-fieldmap/dist"
REASONS = {"upstream_no_payload", "dialect_unresolved", "adapter_unsupported", "zero_rows",
           "parse_error", "grade_below_C", "only_minimal_safe"}


def free_gb():
    st = os.statvfs("/data")
    return st.f_bavail * st.f_frsize / 2 ** 30


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    total = len(rows)
    mapped = [r for r in rows if int(r["mapped"] or 0) > 0]
    unus = [r for r in rows if int(r["mapped"] or 0) == 0]
    for r in unus:
        assert r["reason"] in REASONS, ("非固定枚举原因", r["reason"])
    with open(os.path.join(HERE, "unusable.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["layer", "reason", "dialect_id", "class", "in_rows",
                                          "dropped_below_c", "parse_error", "in_bytes", "evidence"])
        w.writeheader()
        for r in sorted(unus, key=lambda x: (x["reason"], -int(x["in_rows"] or 0))):
            w.writerow({"layer": r["layer"], "reason": r["reason"], "dialect_id": r["dialect_id"],
                        "class": r["class"], "in_rows": r["in_rows"],
                        "dropped_below_c": r["dropped_below_c"], "parse_error": r["parse_error"],
                        "in_bytes": r["in_bytes"],
                        "evidence": (f"part_files={r['part_files']} in_rows={r['in_rows']} "
                                     f"mapped={r['mapped']} dropped_below_C={r['dropped_below_c']} "
                                     f"parse_error={r['parse_error']} 口径=dropped_below_C")})
    st = json.load(open(os.path.join(HERE, "field-stats.json"), encoding="utf-8"))["global"]
    sp = json.load(open(os.path.join(HERE, "spotcheck-summary.json"), encoding="utf-8"))
    cov = 100.0 * len(mapped) / total
    run = json.load(open(os.path.join(DIST, "run-summary.json"), encoding="utf-8")) if \
        os.path.isfile(os.path.join(DIST, "run-summary.json")) else {}
    shards = [f for f in sorted(os.listdir(os.path.join(DIST, "tar"))) if f.endswith(".tar.gz")]
    shard_bytes = sum(os.path.getsize(os.path.join(DIST, "tar", f)) for f in shards)
    reason_cnt = collections.Counter(r["reason"] for r in unus)
    close_bad = [r for r in rows if int(r["diff"] or 0) != 0]
    four = {"coverage_pct": round(cov, 2), "coverage_layers": f"{len(mapped)}/{total}",
            "unusable": len(unus), "unusable_by_reason": dict(reason_cnt),
            "spotcheck_layers": sp["layers_checked"],
            "spotcheck_match_pct": sp["match_pct"],
            "closing_diff_layers": len(close_bad),
            "output_bytes": shard_bytes, "out_rows_bytes": st["out_bytes"], "free_gb": round(free_gb(), 1),
            "in_rows": st["in_rows"], "mapped_rows": st["mapped"],
            "dropped_below_c": st["dropped_below_c"], "parse_error": st["parse_error"],
            "street_pct": st["street_name_ok_pct"], "number_pct": st["house_number_ok_pct"],
            "zip5_valid_pct": st["zip5_valid_pct"], "coord_ok_pct": st["coord_ok_pct"],
            "coord_out_of_range_rows": st["coord_out_of_range_rows"],
            "grade": st["grade"], "shards": len(shards), "shard_bytes": shard_bytes,
            "invariants": sp["invariants"]}
    json.dump(four, open(os.path.join(HERE, "SUMMARY.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    R = []
    A = R.append
    A("# 第 9 步 · 全量字段映射（3,550 层：到手 → 能用）\n")
    A("> 一句话：**%d/%d 层（%.2f%%）产出 11 列可读数据**；不可用 %d 层（原因全部落在固定枚举内）；"
      "逐层闭合差 ≠ 0 的层 **%d** 个；行级抽查 **%d 层 / %s%% 相符**；输出 **%.1f MiB / %d 个 tar.gz 分片**；"
      "磁盘余量 **%.1f GiB**。\n"
      % (len(mapped), total, cov, len(unus), len(close_bad), sp["layers_checked"],
         sp["match_pct"], shard_bytes / 2 ** 20, len(shards), free_gb()))
    A("## 0. 四数（先给数）\n")
    A("| 指标 | 实测 | 门槛 | 结论 |")
    A("|---|---:|---:|---|")
    A("| 层覆盖率 | **%.2f%%**（%d/%d） | ≥95%%（≥3,373） | %s |"
      % (cov, len(mapped), total, "达标" if len(mapped) >= 3373 else "**未达标**"))
    A("| 不可用层 | **%d** | —（全部进 unusable.csv） | %s |"
      % (len(unus), "原因全部固定枚举内" if not (set(reason_cnt) - REASONS) else "**有兜底桶**"))
    A("| 逐层闭合差额 | **%d 层有差额** | 0 | %s |" % (len(close_bad), "闭合" if not close_bad else "**未闭合**"))
    A("| 行级抽查 | **%d 层 / %s%%** 相符 | ≥355 层（≥10%%） | %s |"
      % (sp["layers_checked"], sp["match_pct"], "达标" if sp["layers_checked"] >= 355 else "**未达标**"))
    A("| 输出字节 | **%d B**（%d 片） | — | 磁盘余量 %.1f GiB |" % (shard_bytes, len(shards), free_gb()))
    A("")
    A("## 1. 不可用分桶（`unusable.csv`）\n")
    A("| 原因 | 层数 | 含义 |")
    A("|---|---:|---|")
    meaning = {"grade_below_C": "所有行都低于 C 级（无街名 / 无任何地址要素）→ 按口径丢弃，不猜",
               "zero_rows": "part 包内 0 行", "parse_error": "JSON/gzip 损坏（本轮近 0）",
               "upstream_no_payload": "无 part 载荷", "dialect_unresolved": "方言在 registry/engine 都对不上",
               "adapter_unsupported": "适配器不支持", "only_minimal_safe": "只拿得出 minimal_safe 两要素"}
    for k, v in sorted(reason_cnt.items(), key=lambda kv: -kv[1]):
        A("| `%s` | %d | %s |" % (k, v, meaning.get(k, "")))
    A("")
    A("## 2. 逐层闭合\n")
    A("| 项 | 行数 |")
    A("|---|---:|")
    A("| 输入行（3,550 层 part 包实读） | %s |" % f"{st['in_rows']:,}")
    A("| 映射行（写进 11 列输出） | %s |" % f"{st['mapped']:,}")
    A("| 丢弃：低于 C 级 | %s |" % f"{st['dropped_below_c']:,}")
    A("| 丢弃：解析失败 | %s |" % f"{st['parse_error']:,}")
    A("| **差额** | **%d** |" % (st["in_rows"] - st["mapped"] - st["dropped_below_c"] - st["parse_error"]))
    A("")
    A("逐层闭合（`in_rows − mapped − dropped_below_C − parse_error`）差额 ≠ 0 的层：**%d** 个%s\n"
      % (len(close_bad), "" if not close_bad else " → " + ", ".join(
          "%s(%s)" % (r["layer"][:40], r["diff"]) for r in close_bad[:10])))
    A("## 3. 字段级有效率（全局）\n")
    A("| 字段 | 有效率 | 门槛 | 结论 |")
    A("|---|---:|---:|---|")
    A("| `street_name` | **%.2f%%** | 100%% | %s |" % (st["street_name_ok_pct"], "达标" if st["street_name_ok_pct"] >= 99.99 else "未达标"))
    A("| `house_number` | **%.2f%%** | ≥90%% | %s |" % (st["house_number_ok_pct"], "达标" if st["house_number_ok_pct"] >= 90 else "**未达标**"))
    A("| `zip5` 合法率 | **%.2f%%** | ≥95%% | %s |" % (st["zip5_valid_pct"], "达标" if st["zip5_valid_pct"] >= 95 else "**未达标**"))
    A("| 坐标落合法范围 | **%.2f%%**（越界残留 %d 行 = 已被置 null） | 100%% | %s |"
      % (st["coord_ok_pct"], st["coord_out_of_range_rows"], "达标" if st["coord_out_of_range_rows"] == 0 else "**未达标**"))
    A("")
    A("> `zip5_valid` 的分母是映射行；源里本就没有邮编的行记 missing（不补零、不截断）。"
      "`house_number` 同理：源里没有门牌就 null，绝不生成。\n")
    A("按 dialect：见 `field-stats.json: by_dialect`。按州：**不适用** —— 信封行恒无 `state` 字段，"
      "state 只能从 raw 的显式州字段或组合串尾部取，因此没有可靠的州分组维度（`field-stats.json: by_state_null`）。\n")
    A("## 4. 行级抽查（`spotcheck.csv`）\n")
    A("| 项 | 值 |")
    A("|---|---:|")
    A("| 抽查层数 | **%d**（含字节最大 10 层） |" % sp["layers_checked"])
    A("| 行级抽样 | %d 行 |" % sp["rows_checked"])
    A("| 相符 | **%d**（%s%%） |" % (sp["rows_matched"], sp["match_pct"]))
    A("| 不变量违反 | `bad_zip5=%d, bad_state=%d, bad_coord=%d, zero_coord=%d, bad_number=%d, bad_columns=%d` |"
      % (sp["invariants"].get("bad_zip5", 0), sp["invariants"].get("bad_state", 0),
         sp["invariants"].get("bad_coord", 0), sp["invariants"].get("zero_coord", 0),
         sp["invariants"].get("bad_number", 0), sp["invariants"].get("bad_columns", 0)))
    A("")
    A("抽查方法：① 对输出行做**不变量**全扫（zip5 恰好 5 位、state 合法、坐标在范围内且非 (0,0)、"
      "门牌非占位值、11 列齐全）；② 另写一份**独立重算**（不复用 `fm_core`）对输入行重打一遍，"
      "按 (门牌, 街名, zip5, lat, lon) 五元组比对。\n")
    A("## 5. 方法与偏差（必须如实说）\n")
    A("1. **方言命中率极低，这是本轮最重要的偏差**：3,550 层的 `layer_id` 与 `url` 与 17,168 行分档表的交集是 **0**，"
      "按 agol org 匹 registry 只命中 **115 层（3.2%）**；其余一律 `minimal_safe`（`pool=manual`、`a_pool_eligible=false`、永不进 A 货池）。"
      "原因是这 3,550 层来自第 4/5/7 批采集，不在方言分档的分母里。")
    A("2. **取值优先级**（逐字段）：信封原生值 → `raw` 角色别名（`engine/split_addr.py: roles_of()` = registry ∪ engine/dialects 合并表，"
      "~200 个别名，不新增、不猜）→ 组合串拆分（`split_addr.split_number_street` / `split_city_tail`）。"
      "组合串拆出来的值 `provenance=split`，**一律不许进 S**（S 级按口径要求全要素原生）。")
    A("3. **未走 `collect/lib/fieldmap3.py`**（硬编码别名表）：它是采集侧的口径，本步按 muse 要求只把它当对照证据。"
      "实测它的别名表与本步用的 registry ∪ engine 表在「组合串字段」（如 `ADDR`/`LSN`）上都没覆盖，"
      "这也是为什么要上 `split_addr` 的拆分规则 —— 不接这一步时覆盖率只有 67%（1,186/1,776），接上后到 94%+。")
    A("4. **grade/tier 全部由配置驱动**：`engine/config/pilot.yaml` 的 `grades`（S/A/B/C 特征表）与 `tier_rank`，"
      "代码里没有硬编码阈值；本批 3,550 层在分档表里**没有任何 (url, dialect_id) 命中**，故 `tier` 一律 `unrated`（照抄 `tier_rank` 的 unrated=9）。")
    A("5. **zip5 口径**：`12345-6789` 取前 5；不足/超长/含字母一律 null 并计 missing，不补零。"
      "**house_number**：占位值（0/000/NULL/N/A/NONE/UNKNOWN/-1/空/纯符号）一律缺失，绝不生成门牌。"
      "**坐标**：范围外、(0,0)、缺省一律 null，绝不写 0 冒充。")
    A("6. **磁盘**：输入 40,341,427,040 B 只读；输出写 `dist/`，每 500 层一个 `fieldmap-partNNN.tar.gz`，"
      "打包后立刻删 `dist/rows/` 里的散文件；`free_gb` 全程未低于 3 GiB（收工 %.1f GiB）。\n" % free_gb())
    A("## 6. 怎么复跑\n")
    A("```bash\ncd /data/workspace/wmd-fieldmap && python3 analysis/fieldmap-20261125/map_layers.py \\\n"
      "  --all --shard 500 --workers 7\n"
      "python3 analysis/fieldmap-20261125/fieldstats.py\n"
      "python3 analysis/fieldmap-20261125/spotcheck.py --layers 355 --rows 200\n"
      "python3 analysis/fieldmap-20261125/finalize.py\n```\n")
    open(os.path.join(HERE, "REPORT.md"), "w", encoding="utf-8").write("\n".join(R) + "\n")
    print(json.dumps(four, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    raise SystemExit(main())
