#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 09 —— 增量同步（试点版：探测 + 变更量统计，暂不落地数据）

为什么先不落地：抽样 20 个层，只有 3 个有编辑时间字段（15%），字段名还各不相同
（edit_date / dateupdate / editdate）。机制没验证之前不写数据，先把「有多少层能做增量、
各自有多少变更」算清楚 —— 这本身就是决策依据。

流程：
  1. 从 pilot_report.json 拿已采层清单
  2. 逐层请求 `<layer_url>?f=json`，看 fields 里有没有编辑时间字段
  3. 有 → `count where <字段> > '<since>'`，得到变更行数
  4. 无 → 记 no_delta_field（这类层只能全量重采）

输出：
  collect/reports/DELTA_REPORT.md
  collect/delta_state.json

用法：
  python3 collect/delta.py                 # 默认 batch（steps.json 09.select.batch）
  python3 collect/delta.py --limit 20      # 只探 20 层
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT_F = os.path.join(HERE, "pilot_report.json")
PLAN_F = os.path.join(HERE, "layer_plan.csv")
STEPS_F = os.path.join(HERE, "steps.json")
OUT_MD = os.path.join(HERE, "reports", "DELTA_REPORT.md")
OUT_JSON = os.path.join(HERE, "delta_state.json")
UA = "world-map-data-33/1.0 (+collect)"

# 各家的编辑时间字段名（不猜，只认这些）
EDIT_FIELDS = ["last_edited_date", "last_edit_date", "edit_date", "editdate",
               "dateupdate", "lastupdate", "last_update", "last_edited", "updated", "modified"]


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def plan_map():
    out = {}
    if os.path.exists(PLAN_F):
        import csv
        for row in csv.DictReader(open(PLAN_F, encoding="utf-8")):
            out[row["layer_id"]] = row
    return out


def probe(url, plan):
    """返回 (字段名 or None, 错误)。"""
    try:
        d = get(url.rstrip("/") + "?f=json")
    except Exception as e:
        return None, str(e)[:80]
    if not isinstance(d, dict):
        return None, "bad_response"
    names = [str(f.get("name") or "").lower() for f in (d.get("fields") or [])]
    for want in EDIT_FIELDS:
        if want in names:
            return want, ""
    for n in names:                        # 兜底：含 edit/update 也算候选
        if "edit" in n or "update" in n:
            return n, ""
    return None, ""


def count_where(url, field, since):
    q = urllib.parse.urlencode({"where": "%s > '%s'" % (field, since),
                                "returnCountOnly": "true", "f": "json"})
    try:
        d = get(url.rstrip("/") + "/query?" + q)
        return int(d.get("count") or 0), ""
    except Exception as e:
        return 0, str(e)[:80]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cfg = (json.load(open(STEPS_F, encoding="utf-8")).get("steps") or {}).get("09") or {}
    batch = int(cfg.get("select", {}).get("batch") or 20)
    since_days = int(cfg.get("since_days") or 90)
    if "--limit" in argv:
        batch = int(argv[argv.index("--limit") + 1])
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - since_days * 86400))

    rep = json.load(open(REPORT_F, encoding="utf-8")) if os.path.exists(REPORT_F) else {}
    done = [m.get("id") for m in (rep.get("detail") or []) if m.get("id")]
    plan = plan_map()
    picked = done[:batch]
    print("[delta] 已采 %d 层，本批探 %d 层，since=%s（%d 天）" % (len(done), len(picked), since, since_days))

    def one(lid):
        row = plan.get(lid) or plan.get(lid.split("@")[0]) or {}
        url = row.get("url") or ""
        if not url:
            return {"id": lid, "field": None, "err": "no_url"}
        field, err = probe(url, plan)
        if not field:
            return {"id": lid, "field": None, "err": err or "no_delta_field"}
        n, cerr = count_where(url, field, since)
        return {"id": lid, "field": field, "changed": None if cerr else n, "err": cerr}

    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(one, picked):
            out.append(r)

    with_field = [r for r in out if r.get("field")]
    changed = sum(r.get("changed") or 0 for r in with_field)
    lines = ["# 三仓采集 · 增量能力探测报告（STEP 09 试点）", "",
             "- 探测层数：**%d**" % len(out),
             "- 有编辑时间字段：**%d** 层（%.0f%%）" % (len(with_field), 100 * len(with_field) / max(len(out), 1)),
             "- since：`%s`（%d 天窗口）" % (since, since_days),
             "- 窗口内变更行数合计：%s" % format(changed, ","),
             "", "## 能增量的层", "", "| 层 | 时间字段 | 变更行数 |", "|---|---|---|"]
    for r in with_field[:50]:
        lines.append("| `%s` | `%s` | %s |" % (r["id"][:52], r["field"], format(r.get("changed") or 0, ",")))
    lines += ["", "## 不能增量的层（只能全量重采）", ""]
    nof = [r for r in out if not r.get("field")]
    lines += ["- `%s` — %s" % (r["id"][:52], r.get("err")) for r in nof[:30]] or ["- 无"]
    lines += ["", "## 下一步", "",
              "- 这些层验证成立后，再改 pilot 支持 `--since`（真正的增量落地）",
              "- 增量产物一律打 `collect-delta-<层>-<日期>`，绝不覆盖全量 tag"]

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"since": since, "probed": len(out), "with_field": len(with_field),
               "changed_rows": changed, "detail": out},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"probed": len(out), "with_field": len(with_field),
                      "field_rate": round(len(with_field) / max(len(out), 1), 3),
                      "changed_rows": changed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
