#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 可采清单定稿 + S4 抽样设计（分层抽 200 层 + unknown 组 20 层）。"""
from __future__ import annotations
import csv, json, os, random
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "situs_layers.csv"), encoding="utf-8")))
for r in rows:
    r["rows"] = int(r["rows"])

# ---------- S3：按州聚合 ----------
agg = defaultdict(lambda: {"strong_layers": 0, "strong_rows": 0, "weak_layers": 0, "weak_rows": 0})
for r in rows:
    if r["state"] == "未定位":
        continue
    a = agg[r["state"]]
    if r["grade"] == "strong":
        a["strong_layers"] += 1; a["strong_rows"] += r["rows"]
    elif r["grade"] == "weak":
        a["weak_layers"] += 1; a["weak_rows"] += r["rows"]

plan = sorted(agg.items(), key=lambda kv: -kv[1]["strong_rows"])
with open(os.path.join(HERE, "situs_plan.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["state", "strong_layers", "strong_rows", "weak_layers", "weak_rows"])
    for st, a in plan:
        w.writerow([st, a["strong_layers"], a["strong_rows"], a["weak_layers"], a["weak_rows"]])

ts = sum(a["strong_rows"] for _, a in plan)
tl = sum(a["strong_layers"] for _, a in plan)
tw_rows = sum(a["weak_rows"] for _, a in plan)
s3 = {"states": len(plan), "strong_layers": tl, "strong_rows": ts,
      "weak_rows": tw_rows, "top5": [(k, v["strong_rows"]) for k, v in plan[:5]],
      "median_state_rows": sorted(a["strong_rows"] for _, a in plan)[len(plan)//2]}
json.dump(s3, open(os.path.join(HERE, "situs_plan.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---------- S4：分层抽样 ----------
BUCKETS = [(1, 1_000), (1_000, 50_000), (50_000, 500_000), (500_000, 10**12)]
def bucket_of(n):
    for i, (lo, hi) in enumerate(BUCKETS):
        if lo <= n < hi: return i
    return 3

pool = [r for r in rows if r["grade"] in ("strong", "weak") and r["state"] != "未定位"]
by_b = defaultdict(list)
for r in pool:
    by_b[bucket_of(r["rows"])].append(r)

random.seed(33)
N = 200
weights = {0: 0.10, 1: 0.25, 2: 0.35, 3: 0.30}
sample = []
for b, w in weights.items():
    lst = by_b[b]
    k = min(len(lst), max(3, int(N * w)))
    sample += random.sample(lst, k)
# 补足到 200
rest = [r for r in pool if r not in sample]
random.shuffle(rest)
sample += rest[:max(0, N - len(sample))]

# unknown 组：单独 20 层
unk = [r for r in rows if r["state"] == "未定位" and r["grade"] in ("strong", "weak")]
random.shuffle(unk)
unk_s = unk[:20]
for r in unk_s:
    r["_grp"] = "unknown"
for r in sample:
    r["_grp"] = "B%d" % bucket_of(r["rows"])

with open(os.path.join(HERE, "sample200.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["grp", "layer_id", "state", "grade", "rows", "url"])
    for r in sample + unk_s:
        w.writerow([r["_grp"], r["layer_id"], r["state"], r["grade"], r["rows"], r["url"]])

cov = sum(r["rows"] for r in sample)
cov_all = sum(r["rows"] for r in pool)
s4 = {"sample_layers": len(sample), "unknown_layers": len(unk_s),
      "buckets": {b: len(by_b[b]) for b in by_b},
      "sample_by_bucket": dict(Counter(r["_grp"] for r in sample)),
      "sample_rows": cov, "pool_rows": cov_all, "cover_pct": round(cov * 100.0 / cov_all, 1),
      "unknown_pool_layers": len(unk), "unknown_pool_rows": sum(r["rows"] for r in unk)}
json.dump(s4, open(os.path.join(HERE, "sample200.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(json.dumps({"S3": s3, "S4": s4}, ensure_ascii=False, indent=1))

open("/tmp/s3.txt", "w", encoding="utf-8").write("\n".join([
    "✅ 10-P 自研 S3/7 · 可采清单定稿",
    "",
    "strong 层 %d 层 / %s 行，覆盖 %d 个州" % (tl, format(ts, ','), len(plan)),
    "weak 层另 %s 行（待实测再定）" % format(tw_rows, ','),
    "",
    "Top5: " + " / ".join("%s %s万" % (k, round(v/1e4)) for k, v in s3["top5"]),
    "中位数州 %s 万行" % round(s3["median_state_rows"]/1e4),
    "",
    "产出：collect/situs_plan.csv（按州聚合）",
    "下一步 S4：分层抽 200 层 ∪ 未定州 20 层"]))
open("/tmp/s4.txt", "w", encoding="utf-8").write("\n".join([
    "✅ 10-P 自研 S4/7 · 抽样设计完成",
    "",
    "池子 %d 层 / %s 行" % (len(pool), format(cov_all, ',')),
    "按声明行数分 4 桶：" + "  ".join(
        "%s:%d层" % (["<1千","1千~5万","5万~50万",">50万"][b], len(by_b[b])) for b in sorted(by_b)),
    "",
    "抽 200 层 / %s 行，覆盖池子 %.1f%%" % (format(cov, ','), cov*100.0/cov_all),
    "另单抽未定州 20 层（该组共 %d 层 / %s 行）" % (len(unk), format(s4["unknown_pool_rows"], ',')),
    "",
    "口径：单层采样上限 30 万行（keyset 前 30 万），超限层按比例外推",
    "产出：collect/sample200.csv",
    "下一步 S5：实测漏斗（需新写抽样下载脚本）"]))
