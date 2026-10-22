#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob, json, os, csv, gzip, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, "samp_*.json"))):
    rows += json.load(open(f))
def num(v):
    try: return int(float(v))
    except Exception: return 0
ok = [r for r in rows if r.get("samples")]
print("records", len(rows), "with samples", len(ok))
cols = ["state","title","provider","svc","geom","count","cov","nfields","url","fields","samples"]
with gzip.open(os.path.join(HERE, "samples.csv.gz"), "wt", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({"state": r.get("state"), "title": r.get("title"), "provider": r.get("provider"),
                    "svc": r.get("svc"), "geom": r.get("geom"), "count": r.get("count"),
                    "cov": r.get("cov"), "nfields": r.get("nfields"), "url": r.get("url"),
                    "fields": ";".join([str(x) for x in (r.get("fields") or [])]),
                    "samples": json.dumps(r.get("samples") or [], ensure_ascii=False)[:3000]})
by = collections.defaultdict(list)
for r in rows: by[r.get("state") or "未定位"].append(r)
L = ["# NG911 全量清单（含逐层样本地址）", "",
     "记录 %d 条，取到样本 %d 条。样本为每层前 3 行的原始字段值，未做任何筛选。" % (len(rows), len(ok)), ""]
L += ["| 州 | 记录 | 有样本 | 最大层要素数 |", "|---|---|---|---|"]
for st in sorted(by):
    rs = by[st]
    L.append("| %s | %d | %d | %s |" % (st, len(rs), sum(1 for x in rs if x.get("samples")),
             format(max((num(x.get("count")) for x in rs), default=0), ",")))
for st in sorted(by):
    L += ["", "## %s (%d 条)" % (st, len(by[st])), ""]
    for r in sorted(by[st], key=lambda r: -num(r.get("count"))):
        L.append("### %s | %s | %s 条 | %s" % (r.get("title"), r.get("provider"),
                 format(num(r.get("count")), ","), r.get("url")))
        L.append("字段: %s" % ", ".join([str(x) for x in (r.get("fields") or [])][:40]))
        for s in (r.get("samples") or [])[:3]:
            L.append("- `%s`" % json.dumps(s, ensure_ascii=False)[:400])
        L.append("")
open(os.path.join(HERE, "清单-全量-含样本.md"), "w").write("\n".join(L))
print("md lines", len(L))
