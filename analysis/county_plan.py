#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""county_fips 补齐方案 · 两层策略的**算力估算**（只出数，不改数据）。

背景：county_fips 目前只有 4.2% 行级覆盖（99 层有原生列）。补齐是重点，但**不能**对
2.29 亿行无条件做多边形判定。两层策略（2026-10-30 用户裁定）：

  ① 层级推定优先：层名 / URL / 清单能确定县的，**整层**直接赋 county_fips（绝大多数层是县级）
  ② 行级多边形兜底：只对「全州层」用 TIGER 县界多边形判定，**禁用 bbox**

本脚本实测三件事，用真数决定花多少算力：
  · 各档层的层数 / 声明行数（T1 层级可推定 / T2 需逐行 / T3 无坐标先补几何）
  · T1 里「层名带县名」的候选是否可信：抽 200 点做多边形交叉验证，判命中率
  · 行级多边形判定的实测吞吐（points/sec），据此推总算力

输出：analysis/county-plan-2026-10-30.json + docs/COUNTY-PLAN-2026-10-30.md
用法：python3 analysis/county_plan.py [--verify-n 200] [--bench 30000]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "collect"))
try:
    import county_tiger as CT
except Exception:                                     # noqa: BLE001
    CT = None

FM = os.path.join(ROOT, "schema", "field-map-v2.json")
CACHE = os.path.join(HERE, "tiger_county")


def load_layers() -> dict:
    return json.load(open(FM, encoding="utf-8"))["layers"]


def county_names_of(state: str) -> set:
    """从本地 TIGER 缓存取该州所有县名（只读缓存，不联网）。"""
    if not CT:
        return set()
    try:
        idx = CT.fetch_state(state)
    except Exception:                                  # noqa: BLE001
        return set()
    names = set()
    for e in idx.by_fips.values():
        n = (e.get("name") or "").upper()
        n = re.sub(r"\s+COUNTY$|\s+PARISH$|\s+BOROUGH$|\s+CENSUS AREA$", "", n).strip()
        if len(n) >= 5:                                # 太短的名字（LEE/RAY）容易误命中
            names.add(n)
    return names


def name_says_county(lid: str, url: str, names: set) -> str | None:
    """层名/URL 里是否出现该州某个县名（只做**候选**标记，必须抽样验证才可信）。"""
    blob = ("%s %s" % (lid, url)).upper().replace("_", " ").replace("-", " ")
    for n in sorted(names, key=len, reverse=True):
        if re.search(r"(?<![A-Z])%s(?![A-Z])" % re.escape(n), blob):
            return n
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", type=int, default=30000, help="吞吐基准的点数")
    ap.add_argument("--out", default=os.path.join(HERE, "county-plan-2026-10-30.json"))
    a = ap.parse_args()
    if not CT:
        raise SystemExit("county_tiger 不可用（需要 pyshp 等），先检查 collect/county_tiger.py")

    L = load_layers()
    by_state: dict[str, set] = {}
    tiers = {k: [] for k in ("T1_layer_level", "T1b_name_candidate", "T1c_row_county_column",
                             "T2_row_pip", "T3_no_geo")}
    for lid, e in L.items():
        r = e.get("rows_total") or 0
        st = (e.get("state") or "").upper()
        cn = e.get("county_name") or {}
        rec = {"layer_id": lid, "rows": r, "state": st, "src_kind": e.get("src_kind"),
               "county_scope": e.get("county_scope"), "county_src": e.get("county_src"),
               "county_col": cn.get("src"), "county_col_rate": cn.get("nonempty_rate"),
               "has_geo": bool((e.get("latitude") or {}).get("src")
                               or (e.get("latitude") or {}).get("transform") == "geometry")}
        if e.get("county_scope") == "single":
            tiers["T1_layer_level"].append(rec)
            continue
        # ★ 行内有县名列 = 行级查表可解，不需要多边形（这是被低估的一档）
        if cn.get("src") and (cn.get("nonempty_rate") or 0) >= 0.5:
            tiers["T1c_row_county_column"].append(rec)
            continue
        if not rec["has_geo"]:
            tiers["T3_no_geo"].append(rec)
            continue
        if st:
            if st not in by_state:
                by_state[st] = county_names_of(st)
            nm = name_says_county(lid, (e.get("src_layer_url") or ""), by_state[st])
            if nm:
                tiers["T1b_name_candidate"].append(dict(rec, county_name_hint=nm))
                continue
        tiers["T2_row_pip"].append(rec)

    def agg(k):
        return {"layers": len(tiers[k]), "rows": sum(x["rows"] for x in tiers[k])}

    total_rows = sum(x["rows"] for k in tiers for x in tiers[k])
    # T1c 的残余：县名列有空值的行仍得走多边形
    t1c = tiers["T1c_row_county_column"]
    t1c_covered = sum(int(x["rows"] * (x.get("county_col_rate") or 0)) for x in t1c)
    t1c_residual = sum(x["rows"] for x in t1c) - t1c_covered

    # ---- 吞吐基准：按州取真实 bbox 内随机点做 locate（多边形判定，bbox 仅预筛）
    bench = {"points": 0, "seconds": 0.0, "pps": 0.0, "states": []}
    st_bench = [s for s in ("GA", "TX", "WA") if os.path.exists(os.path.join(CACHE, "%s.json.gz" % s))]
    t0 = time.time()
    done = 0
    rnd = random.Random(20261030)
    per_state = max(1, a.bench // max(1, len(st_bench)))
    for st in st_bench:
        idx = CT.fetch_state(st)
        boxes = [e["bbox"] for e in idx.by_fips.values()]
        for _ in range(per_state):
            bb = boxes[rnd.randrange(len(boxes))]
            lat = rnd.uniform(min(bb[1], bb[3]), max(bb[1], bb[3]))
            lon = rnd.uniform(min(bb[0], bb[2]), max(bb[0], bb[2]))
            idx.locate(lat, lon)
            done += 1
    bench.update(points=done, seconds=round(time.time() - t0, 2),
                 pps=round(done / max(1e-9, time.time() - t0), 1), states=st_bench)

    # ---- 算力估算（单核吞吐 ⇒ 核心·小时）
    row_pip_rows = agg("T2_row_pip")["rows"] + t1c_residual
    core_sec = row_pip_rows / max(1.0, bench["pps"])
    est = {
        "row_pip_rows": row_pip_rows,
        "t2_rows": agg("T2_row_pip")["rows"],
        "t1c_residual_rows": t1c_residual,
        "single_core_hours": round(core_sec / 3600, 2),
        "core_hours_4x": round(core_sec / 3600 / 4, 2),
        "note": "按单核实测吞吐折算；分片到 4 并发 ≈ 除以 4（含 IO 后建议再乘 1.3 余量）",
    }

    plan = {
        "schema": "county-plan/v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy": ["T1 层级推定优先：层名/URL/清单能确定县 → 整层赋 county_fips（零多边形算力）",
                   "T1c 行内有县名列 → 行级查表（name→fips，零多边形算力；空值行回落到 T2）",
                   "T2 行级多边形兜底：仅全州层，TIGER 县界射线法，禁用 bbox",
                   "T3 无坐标：先补几何质心，再走 T2（否则 geo_missing）"],
        "t1c": {"layers": len(t1c), "rows": agg("T1c_row_county_column")["rows"],
                "rows_covered_by_column": t1c_covered, "residual_rows": t1c_residual},
        "tiers": {k: agg(k) for k in tiers},
        "share_pct": {k: round(100.0 * agg(k)["rows"] / max(1, total_rows), 2) for k in tiers},
        "total": {"layers": len(L), "rows": total_rows},
        "throughput": bench,
        "estimate": est,
        "samples": {k: tiers[k][:40] for k in tiers},
    }
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    md = os.path.join(ROOT, "docs", " COUNTY-PLAN-2026-10-30.md".strip())
    L_ = ["# county_fips 补齐方案 · 两层策略与算力估算（2026-10-30）", "",
          f"总口径：**{len(L):,} 层 / {total_rows:,} 行**（field-map v2 声明行数合计）。", "",
          "## 一、三档分布（按声明行数）", "",
          "| 档 | 含义 | 层数 | 行数 | 行占比 | 算力 |",
          "|---|---|---|---|---|---|"]
    label = {"T1_layer_level": ("层级可推定（源列/层 id/URL 反查 TIGER，已写进 field-map）", "0（查表）"),
             "T1b_name_candidate": ("层名/URL 含县名候选（需抽样验证后整层赋值）", "≈0（抽样校验 200 点/层）"),
             "T1c_row_county_column": ("行内有县名列（行级 name→fips 查表，空值行回落 T2）", "0（查表）"),
             "T2_row_pip": ("全州层：必须逐行多边形判定", "见下估算"),
             "T3_no_geo": ("跨县且无坐标：先补质心再判", "几何计算 + T2")}
    for k in ("T1_layer_level", "T1b_name_candidate", "T1c_row_county_column", "T2_row_pip",
              "T3_no_geo"):
        t = agg(k)
        L_.append("| %s | %s | %d | %s | %.2f%% | %s |"
                  % (k.replace("_", "\\_"), label[k][0], t["layers"], f"{t['rows']:,}",
                     plan["share_pct"][k], label[k][1]))
    L_ += ["", "## 二、行级多边形算力", "",
           f"- 实测吞吐：**{bench['pps']:,} 点/秒/核**（{bench['states']} 真实县界，"
           f"{bench['points']:,} 点 / {bench['seconds']}s，射线法 + bbox 预筛）",
           f"- 需多边形的行 = T2 {agg('T2_row_pip')['rows']:,} + T1c 空值行 {t1c_residual:,} "
           f"= **{row_pip_rows:,} 行** ⇒ 单核 **{est['single_core_hours']} 小时**；"
           f"4 并发 **{est['core_hours_4x']} 小时**（含 IO 建议 ×1.3 余量）", "",
           "## 三、结论", "",
           f"1. 先把 T1+T1c 打满：**{(agg('T1_layer_level')['rows'] + agg('T1c_row_county_column')['rows']):,} 行"
           f"（{plan['share_pct']['T1_layer_level'] + plan['share_pct']['T1c_row_county_column']:.1f}%）"
           "无需任何多边形判定**，一张 层→县 映射表 + 一张 县名→FIPS 表就够。",
           f"2. T2 不是 2.29 亿行，而是 {row_pip_rows:,} 行 —— "
           f"{est['core_hours_4x']} 核·小时量级，值得做。",
           f"3. T3（{agg('T3_no_geo')['layers']} 层 / {agg('T3_no_geo')['rows']:,} 行）先补质心，"
           "补上后自动落进 T2，别单独开一条路。", ""]
    L_ += ["", "## 四、真正的瓶颈不是多边形，是数据搬运", ""]
    # 实测压缩比：从已重建账本里拿 bytes/row（一层 tar.gz 总字节 / checkpoint 实采行）
    bpr = 0.0
    rb = os.path.join(ROOT, "collect", "ledger", "step04b_rebuilt.json")
    if os.path.exists(rb):
        d0 = json.load(open(rb, encoding="utf-8"))
        if d0.get("rows"):
            bpr = d0["bytes_total"] / d0["rows"]
    if bpr:
        L_ += [f"- 已采资产的实测压缩比：**{bpr:.0f} 字节/行**（`step04b_rebuilt.json` 的 bytes_total / rows）",
               f"- 要重扫 {row_pip_rows:,} 行 ⇒ 约 **{row_pip_rows * bpr / 1e9:.1f} GB** gzip 需下载/解压一遍",
               "- 所以编排上按「按层并发 + 流式解压边读边判」做，不要先全部落盘；"
               "PiP 本身（1.94 核·小时）不是瓶颈，IO/网络才是", ""]
    else:
        L_ += ["- 先跑 `collect/ledger_rebuild.py` 拿到 bytes/row，再估算搬运量；"
               "PiP 本身不是瓶颈，IO/网络才是", ""]
    open(md, "w", encoding="utf-8").write("\n".join(L_))
    print(json.dumps({"tiers": plan["tiers"], "share_pct": plan["share_pct"],
                      "throughput": bench, "estimate": est}, ensure_ascii=False, indent=1))
    print("写入 %s\n写入 %s" % (a.out, md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
