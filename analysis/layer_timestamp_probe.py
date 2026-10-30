#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 09 前置 —— 时间戳字段探测（只读元数据，不采数据、不下载资产本体）。

问三个问题：
  1. 已采的两千多层的元数据里，有没有「编辑/更新时间」字段？
  2. 字段名、类型（Date / DateOnly / DateTime / string）是什么，能不能参与 where 过滤？
  3. 有多少层根本无时间字段（只能全量重采）？

做法：逐层 GET `<layer_url>?f=json`（ArcGIS 元数据，几 KB），解析 fields + editingInfo
+ supportsAdvancedQueries。不做任何 /query 数据请求。

输入：/tmp/collected.json（analysis/scan_collected.py 产出：已采层 → 步骤）
输出：analysis/layer-timestamp-probe-<date>.json

用法：
  python3 analysis/layer_timestamp_probe.py                 # 全量
  python3 analysis/layer_timestamp_probe.py --limit 50      # 灰度
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_F = os.path.join(ROOT, "collect", "layer_plan.csv")
ADDR_F = os.path.join(ROOT, "collect", "address_layers.csv")
COLLECTED_F = "/tmp/collected.json"
UA = "world-map-data-33/1.0 (+collect; metadata probe)"

DATE_TYPES = {"esriFieldTypeDate", "esriFieldTypeDateOnly", "esriFieldTypeTimestampOffset",
              "date", "datetime", "timestamp", "calendar_date", "text date-time"}
# 明确是「编辑 / 更新」语义的字段名（不猜）
EDIT_RE = re.compile(r"(last[_ ]?edit|edit[_ ]?date|editdate|^edited|dateupdate|last[_ ]?update|"
                     r"update[_ ]?date|updated|modified|modify[_ ]?date|last_?modified|"
                     r"l_update|lastupdate|update_dt|upd_date)", re.I)
CREATE_RE = re.compile(r"(created?[_ ]?date|creation[_ ]?date|create[_ ]?dt|^created$|"
                       r"date[_ ]?created|insert[_ ]?date|load[_ ]?date|data[_ ]?date)", re.I)


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def url_map():
    out = {}
    for f in (PLAN_F, ADDR_F):
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                lid = (row.get("layer_id") or "").strip()
                u = (row.get("url") or "").strip()
                if lid and u and lid not in out:
                    out[lid] = u
    return out


def classify(field):
    name = str(field.get("name") or "")
    typ = str(field.get("type") or "")
    is_date = typ.lower() in DATE_TYPES or "date" in typ.lower() or "time" in typ.lower()
    kind = None
    if EDIT_RE.search(name):
        kind = "edit"
    elif CREATE_RE.search(name):
        kind = "create"
    return {"name": name, "type": typ, "is_date": is_date, "kind": kind,
            "nullable": field.get("nullable"), "editable": field.get("editable")}


def probe(lid, step, url, timeout=25):
    base = {"layer": lid, "step": step, "url": url}
    if not url:
        return dict(base, ok=False, err="no_url", verdict="no_meta")
    u = url.rstrip("/")
    if u.endswith("/query"):
        u = u[: -len("/query")]
    try:
        d = get(u + "?f=json", timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return dict(base, ok=False, err=str(e)[:110], verdict="no_meta")
    if not isinstance(d, dict):
        return dict(base, ok=False, err="bad_response", verdict="no_meta")
    if d.get("error"):
        return dict(base, ok=False, err=str(d["error"])[:110], verdict="no_meta")
    fields = [classify(f) for f in (d.get("fields") or [])]
    edit = [f for f in fields if f["kind"] == "edit"]
    create = [f for f in fields if f["kind"] == "create"]
    adv = d.get("supportsAdvancedQueries")
    edit_info = d.get("editingInfo") or {}
    # 可增量 = 有**日期型**编辑时间字段（字符串字段 lasteditor 之类不算，不能做 where 时间过滤）
    # 且服务未明确不支持高级查询（supportsAdvancedQueries=False 时 where 过滤会失效）
    date_edit = [f for f in edit if f["is_date"]]
    incr = bool(date_edit) and (adv is not False)
    verdict = ("incremental" if incr else
               "edit_field_no_date" if edit else
               "create_only" if create else
               "no_time_field")
    return dict(base, ok=True, verdict=verdict, geom=str(d.get("geometryType") or ""),
                oid=str(d.get("objectIdField") or ""),
                supports_advanced=adv,
                service_last_edit=edit_info.get("lastEditDate"),
                n_fields=len(fields),
                edit_fields=edit, create_fields=create,
                date_edit_fields=[f["name"] for f in date_edit],
                date_fields=[f["name"] for f in fields if f["is_date"]][:8])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 0
    timeout = int(argv[argv.index("--timeout") + 1]) if "--timeout" in argv else 12
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 12
    date = time.strftime("%Y-%m-%d", time.gmtime())
    out_f = os.path.join(ROOT, "analysis", "layer-timestamp-probe-%s.json" % date)

    coll = json.load(open(COLLECTED_F, encoding="utf-8"))
    layer_step = coll["layer_step"]
    urls = url_map()
    items = sorted(layer_step.items())
    if limit:
        items = items[:limit]
    print("[probe] 已采层 %d，本次探 %d 层" % (len(layer_step), len(items)), flush=True)

    out = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(probe, lid, step, urls.get(lid) or urls.get(lid.split("@")[0]) or "",
                          timeout)
                for lid, step in items]
        for i, f in enumerate(futs, 1):
            out.append(f.result())
            if i % 200 == 0:
                print("  %d/%d  %.0fs" % (i, len(items), time.time() - t0), flush=True)

    ver = Counter(r["verdict"] for r in out)
    fnames = Counter(f["name"].lower() for r in out for f in (r.get("edit_fields") or []))
    ftypes = Counter(f["type"] for r in out for f in (r.get("edit_fields") or []))
    data = {
        "schema": "layer-timestamp-probe/v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "method": "逐层 GET <layer_url>?f=json，只读元数据；未发起任何 /query 数据请求，未下载资产",
        "scope": {"collected_layers": len(layer_step), "probed": len(items),
                  "steps": coll.get("counts")},
        "summary": {
            "verdict": dict(ver),
            "with_edit_field": sum(1 for r in out if (r.get("edit_fields") or [])),
            "with_date_edit_field": sum(1 for r in out if (r.get("date_edit_fields") or [])),
            "incremental_capable": ver["incremental"],
            "create_field_only": ver["create_only"],
            "no_time_field": ver["no_time_field"],
            "no_meta": ver["no_meta"],
            "field_name_top": fnames.most_common(20),
            "field_type_top": ftypes.most_common(10),
            "with_service_last_edit": sum(1 for r in out if r.get("service_last_edit")),
        },
        "layers": out,
    }
    json.dump(data, open(out_f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(data["summary"], ensure_ascii=False, indent=1)[:1800])
    print("→", out_f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
