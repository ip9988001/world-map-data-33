#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""10-P 探测：Polygon/Polyline 层里到底有多少带「真地址」字段

背景：01 预检时按几何白名单把 Polygon/Polyline 全 skip 了（23,556 层 / 声明 11.8 亿行）。
      但很多州的地址只存在于宗地属性里（situs address），这是目前最大的缺口。

做法：只调 `?f=json` 读字段名（不取数据），判定分三档：
  situs  —— 有房产地址字段（SITUS_ADDR / PROP_ADDR / FULLADDR / ADDRESS…）→ 值得采
  owner  —— 只有业主通讯地址（OWNER_ADDR / MAIL_ADDR…）→ 采了是垃圾
  none   —— 没有任何地址字段

输出：
  collect/reports/POLYGON_PROBE.md
  collect/polygon_probe.json

用法：
  python3 collect/probe_polygon.py                 # 全量 2.3 万层
  python3 collect/probe_polygon.py --limit 500     # 抽样
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLAN_F = os.path.join(HERE, "layer_plan.csv")
OUT_MD = os.path.join(HERE, "reports", "POLYGON_PROBE.md")
OUT_JSON = os.path.join(HERE, "polygon_probe.json")
UA = "world-map-data-33/1.0 (+probe)"

# 房产地址（要）
SITUS = ("situs", "situsaddr", "situs_addr", "situsaddress", "prop_addr", "propaddr",
         "property_address", "propertyaddress", "parcel_addr", "parceladdress",
         "site_addr", "siteaddress", "fulladdr", "full_addr", "fulladdress",
         "address", "addr", "location", "loc_addr", "paddr", "physaddr", "physical_address")
# 业主/邮寄地址（不要）
OWNER = ("owner_addr", "owneraddr", "owner_address", "owneraddress", "mail_addr", "mailaddr",
         "mailing_address", "mailingaddress", "owner_mail", "taxpayer_addr", "taxpayeraddress",
         "own_addr", "owner", "mailing", "payee")


def get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def classify(fields):
    low = [str(f).lower() for f in fields]
    situs = [f for f in low if any(k in f for k in SITUS)]
    owner = [f for f in low if any(k in f for k in OWNER)]
    # situs 命中里排除只匹配到 owner 的（例如 owner_addr 同时含 addr）
    situs_only = [f for f in situs if not any(k in f for k in OWNER)]
    if situs_only:
        return "situs", situs_only[:6]
    if owner:
        return "owner", owner[:6]
    return "none", []


def one(row):
    url = (row.get("url") or "").rstrip("/")
    base = {"layer": row["layer_id"], "state": row.get("state") or "", "geom": row.get("geom") or "",
            "rows": int(row["row_count"]) if (row.get("row_count") or "").isdigit() else 0}
    if not url:
        return dict(base, verdict="no_url", fields=[])
    try:
        d = get(url + "?f=json")
    except Exception as e:
        return dict(base, verdict="error", fields=[], err=str(e)[:60])
    if not isinstance(d, dict) or "fields" not in d:
        return dict(base, verdict="error", fields=[], err="no_fields")
    names = [f.get("name") for f in (d.get("fields") or []) if f.get("name")]
    verdict, hit = classify(names)
    return dict(base, verdict=verdict, fields=hit, nfields=len(names))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0
    rows = []
    with open(PLAN_F, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("geom") or "") in ("Polygon", "Polyline") and r.get("url"):
                rows.append(r)
    seen, uniq = set(), []
    for r in rows:
        if r["url"] in seen:
            continue
        seen.add(r["url"]); uniq.append(r)
    if limit:
        uniq = uniq[:limit]
    print("[probe] 待探 %d 层（去重后）" % len(uniq), flush=True)

    out = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=16) as ex:
        for i, r in enumerate(ex.map(one, uniq), 1):
            out.append(r)
            if i % 500 == 0:
                print("  %d/%d  %.0fs" % (i, len(uniq), time.time() - t0), flush=True)

    from collections import Counter
    v = Counter(x["verdict"] for x in out)
    situs_rows = sum(x["rows"] for x in out if x["verdict"] == "situs")
    situs_by_state = Counter()
    for x in out:
        if x["verdict"] == "situs":
            situs_by_state[x["state"] or "未定位"] += x["rows"]

    lines = ["# Polygon 宗地探测报告（10-P）", "",
             "- 探测层数：**%d**" % len(out),
             "- `situs`（有房产地址字段，值得采）：**%d 层 / 声明 %s 行**" % (v["situs"], format(situs_rows, ",")),
             "- `owner`（只有业主通讯地址，采了是垃圾）：%d 层" % v["owner"],
             "- `none`（无地址字段）：%d 层" % v["none"],
             "- 访问异常：%d 层" % (v["error"] + v["no_url"]),
             "", "## 有房产地址的层，按州分布（行数）", "",
             "| 州 | 声明行数 |", "|---|---|"]
    for st, n in situs_by_state.most_common(30):
        lines.append("| %s | %s |" % (st, format(n, ",")))
    lines += ["", "## 字段命中样例（前 20 层）", ""]
    for x in [y for y in out if y["verdict"] == "situs"][:20]:
        lines.append("- `%s`（%s，%s 行）字段：`%s`" % (x["layer"][:52], x["state"], format(x["rows"], ","),
                                                "`, `".join(x["fields"][:4])))
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"probed": len(out), "verdicts": dict(v), "situs_rows": situs_rows,
               "situs_by_state": dict(situs_by_state), "detail": out},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"probed": len(out), "situs": v["situs"], "owner": v["owner"],
                      "none": v["none"], "situs_rows": situs_rows}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
