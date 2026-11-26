#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000264 A1：确定性选样（≤20 层、300k–2M 行），落 sample-layers.csv。

先说两条**不可达**的选样要求（本批数据本身不满足，不是脚本没写）：
  · tier1/tier2/tier3 各 ≥3 层：`grading-rerun-20261125/auto-recognized.csv`（Tier1=410 版）与本批 3,100 个已映射层
    的 **layer_id 交集 0、非空 url 交集 0（归一化 scheme/trailing-slash 后仍是 0）** → 全部 `unrated`。
  · 方言 ≥4 种：`registry/dialects.v1.yaml` 只有 4 个 dialect / 34 个 org，本批 url 的 agol org 抽取结果是
    `''` 3,059 层 + `'rest'` 41 层 → **registry 命中 0 层**，全部 `minimal_safe`。
  → 因此改用**可观测且与本 bug 相关**的维度选样：state 有效率两端、信封原生度、fallback(无 url)、
    字段来源混合度、体量梯度；并把「不可达」写进 CSV 的 reason 列。

用法：python3 sample_select.py [--n 16] [--seed 264] [--max-rows 2000000]
"""
from __future__ import annotations

import argparse, collections, csv, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import fm_core as C  # noqa: E402

COV = os.path.join(HERE, "layer-coverage.csv")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
OUT = os.path.join(HERE, "sample-layers.csv")


def norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    return u.rstrip("/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=16)
    ap.add_argument("--seed", type=int, default=264)
    ap.add_argument("--max-rows", type=int, default=2000000)
    a = ap.parse_args()
    random.seed(a.seed)
    cov = [r for r in csv.DictReader(open(COV, encoding="utf-8")) if int(r["mapped"] or 0) > 0]
    inv = {}
    for r in csv.DictReader(open(INV, encoding="utf-8")):
        inv.setdefault(r["layer"], r)
    tiers = C.load_tier_map()                      # url → tier（Tier1=410 那版）
    tiers_norm = {norm_url(k): v for k, v in tiers.items()}
    org2dial, meta, fb = C.load_registry_orgs()

    def row(r):
        url = (inv.get(r["layer"]) or {}).get("url") or ""
        m = int(r["mapped"])
        org = C.agol_org(url)
        dial = (org2dial.get(org) or ["minimal_safe"])[0] if org in org2dial else "minimal_safe"
        tier = tiers.get(url) or tiers_norm.get(norm_url(url)) or "unrated"
        return {
            "layer_id": r["layer"], "url": url, "tier": tier, "dialect": dial,
            "source_layer_kind": r.get("source_layer_kind") or ("url" if url else "layer_id_fallback"),
            "rows": m, "state_rate_main": round(100.0 * int(r["state_ok"] or 0) / m, 2),
            "number_rate_main": round(100.0 * int(r["number_ok"] or 0) / m, 2),
            "city_rate_main": round(100.0 * int(r["city_ok"] or 0) / m, 2),
            "zip5_rate_main": round(100.0 * int(r["zip5_ok"] or 0) / m, 2),
            "class": r["class"],
        }

    pool = [row(r) for r in cov]
    picked, used, reasons = [], set(), {}

    def take(cand, why, cap=400000):
        for c in cand:
            if c["layer_id"] in used or c["rows"] > cap:
                continue
            picked.append(c)
            used.add(c["layer_id"])
            reasons[c["layer_id"]] = why
            return True
        return False

    def by_size(rs, lo=2000, hi=400000):
        return sorted(rs, key=lambda x: x["rows"])

    # 1) fallback（无 url，@未定位）≥2
    fb_rows = [x for x in pool if x["source_layer_kind"] == "layer_id_fallback"]
    take(sorted(fb_rows, key=lambda x: -x["rows"])[:5], "无url(fallback) 最大可用")
    take(sorted(fb_rows, key=lambda x: x["rows"])[:5], "无url(fallback) 最小可用")
    # 2) state 有效率最高 ≥1（挑中等体量、避免超大层）
    cand = [x for x in pool if 20000 <= x["rows"] <= 400000]
    take(sorted(cand, key=lambda x: -x["state_rate_main"])[:1], "state有效率最高")
    take(sorted(cand, key=lambda x: (-x["state_rate_main"], x["rows"]))[1:2], "state有效率次高")
    # 3) state 有效率最低 ≥1
    take(sorted(cand, key=lambda x: (x["state_rate_main"], -x["rows"]))[:1], "state有效率最低(0)")
    take(sorted(cand, key=lambda x: (x["state_rate_main"], -x["rows"]))[1:2], "state有效率次低")
    # 4) 信封原生对照：四项字段全 100%
    native = [x for x in cand if x["number_rate_main"] >= 99.9 and x["city_rate_main"] >= 99.9
              and x["zip5_rate_main"] >= 99.9]
    take(native[:1], "信封原生对照(门牌/城/邮编全100%)")
    take(native[1:2], "信封原生对照2")
    # 5) 全靠 raw 别名/拆串补：zip5=0 且 city=0、门牌>0（信封锁没有的字段）
    rawsplit = [x for x in cand if x["zip5_rate_main"] == 0 and x["city_rate_main"] == 0
                and x["number_rate_main"] > 50]
    take(rawsplit[:1], "raw别名/拆串依赖(zip城全0、门牌>50%)")
    take(rawsplit[1:2], "raw别名/拆串依赖2")
    # 6) 门牌>0 但 street 之外都空（只有门牌+街，靠 raw）
    onlynum = [x for x in cand if x["number_rate_main"] > 90 and x["zip5_rate_main"] == 0]
    take(onlynum[:1], "门牌高/邮编0（raw 单一来源）")
    # 7) 体量梯度：大/中/小各一
    big = sorted([x for x in pool if x["rows"] <= 400000], key=lambda x: -x["rows"])
    take(big[:1], "体量梯度-大(≤400k)")
    mid = [x for x in pool if 40000 <= x["rows"] <= 80000]
    take(random.sample(mid, len(mid))[:1], "体量梯度-中(40k-80k)")
    small = [x for x in pool if 2000 <= x["rows"] <= 6000]
    take(random.sample(small, len(small))[:1], "体量梯度-小(2k-6k)")
    # 8) 杂项补到目标层数
    rest = [x for x in cand if x["layer_id"] not in used]
    while len(picked) < a.n and rest:
        c = random.choice(rest)
        rest = [x for x in rest if x["layer_id"] != c["layer_id"]]
        take([c], "随机补足")

    # 控制总行数 ≤ max_rows（超了就从最大的开始剔）
    while sum(p["rows"] for p in picked) > a.max_rows and picked:
        biggest = max(picked, key=lambda x: x["rows"])
        picked.remove(biggest)
        used.discard(biggest["layer_id"])
        reasons[biggest["layer_id"]] = "剔除(总行数超上限)"
    for p in picked:
        p["reason"] = reasons.get(p["layer_id"], "")
    cols = ["layer_id", "url", "tier", "dialect", "source_layer_kind", "rows", "state_rate_main",
            "number_rate_main", "city_rate_main", "zip5_rate_main", "class", "reason"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for p in picked:
            w.writerow({k: p[k] for k in cols})
    tot = sum(p["rows"] for p in picked)
    print(json.dumps({"layers": len(picked), "rows": tot,
                      "tier": dict(collections.Counter(p["tier"] for p in picked)),
                      "dialect": dict(collections.Counter(p["dialect"] for p in picked)),
                      "fallback": sum(1 for p in picked if p["source_layer_kind"] == "layer_id_fallback"),
                      "state_min_max": [min(p["state_rate_main"] for p in picked),
                                        max(p["state_rate_main"] for p in picked)]},
                     ensure_ascii=False))
    for p in picked:
        print(f"{p['rows']:8d} state{p['state_rate_main']:6.2f}% num{p['number_rate_main']:6.2f}% "
              f"zip{p['zip5_rate_main']:6.2f}% {p['source_layer_kind'][:9]:9s} {p['reason'][:28]:28s} {p['layer_id'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
