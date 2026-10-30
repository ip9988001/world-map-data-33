#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04b 判定修正 · 上游实测取证（只读上游，不采数据）。

为什么需要它：账本里 18 层 failed 里混着两种完全不同的情况 ——
  ①上游确实 0 行 / 服务已下线（不该算「采集失败」，要归 empty）
  ②确实跑了一半（应归 partial 并进定向重采队列）
判据不能靠猜，所以对每层直接问上游 `returnCountOnly`，把 HTTP 状态码 +
原始响应逐层落盘，作为状态改判的唯一证据。

用法：
  python3 collect/verify_04b_upstream.py --out analysis/04b-upstream-evidence-2026-10-30.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REBUILT = os.path.join(HERE, "ledger", "step04b_rebuilt.json")
PLAN_CSV = os.path.join(HERE, "layer_plan_clean.csv")
UA = {"User-Agent": "collect-audit/1.0 (+world-map-data-33)"}


def layer_urls():
    """layer_id / base_id → url（layer_plan_clean.csv）。"""
    idx = {}
    with open(PLAN_CSV, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            lid = r.get("layer_id") or ""
            if lid and r.get("url"):
                idx[lid] = r["url"]
    return idx


def ask(url, timeout=25, tries=2):
    """问上游「这一层有多少行」。返回 dict(status_code, count, raw, err)。"""
    q = url.rstrip("/") + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    last = {"url": q, "http": None, "count": None, "raw": "", "err": ""}
    for i in range(tries):
        try:
            req = urllib.request.Request(q, headers=UA)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                body = resp.read(4000).decode("utf-8", "replace")
                last.update(http=resp.status, raw=body[:400], err="")
                try:
                    j = json.loads(body)
                    if isinstance(j, dict) and "count" in j:
                        last["count"] = int(j["count"])
                    elif isinstance(j, dict) and j.get("error"):
                        last["err"] = "esri_error: %s" % str(j["error"])[:160]
                except Exception:
                    last["err"] = "非 JSON 响应"
                return last
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(400).decode("utf-8", "replace")
            except Exception:
                pass
            last.update(http=e.code, raw=body[:400], err="HTTP %d" % e.code)
            if e.code in (404, 410, 403, 401):
                return last
        except Exception as e:  # noqa: BLE001
            last.update(http=None, err="%s: %s" % (type(e).__name__, str(e)[:120]))
        time.sleep(1.5 * (i + 1))
    return last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rb = json.load(open(REBUILT, encoding="utf-8"))
    urls = layer_urls()

    # 需要取证的层：failed（0 行 / 半截）+ partial（声明值口径差）
    targets = [r for r in rb["records"] if r["status"] in ("failed", "partial")]
    out = {"schema": "04b-upstream-evidence/v1", "stage": "04b",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "method": "GET <layer_url>/query?where=1=1&returnCountOnly=true&f=json（每层最多 2 次）",
           "layers": []}
    for r in targets:
        lid = r["layer"]
        url = urls.get(lid) or urls.get(lid.split("@")[0]) or ""
        rec = {"layer": lid, "ledger_status": r["status"],
               "ledger_declared": r.get("declared"), "ledger_rows": r.get("rows"),
               "layer_url": url}
        if not url:
            rec.update(probe={"err": "layer_plan_clean.csv 里查不到 url", "count": None, "http": None})
        else:
            rec["probe"] = ask(url)
        p = rec["probe"]
        cnt, http = p.get("count"), p.get("http")
        if cnt == 0:
            rec["verdict"] = "upstream_no_data"          # 上游明确 0 行
        elif cnt is not None:
            rec["verdict"] = "upstream_alive"            # 上游活着，能给出当前 returnCount
        elif http in (404, 410):
            rec["verdict"] = "upstream_gone_404"         # 服务/层已下线
        else:
            rec["verdict"] = "upstream_unreachable"      # 连不上/超时/5xx
        out["layers"].append(rec)
        print("%-14s %-8s %s" % (rec["verdict"], p.get("count"), lid[:66]))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(x["verdict"] for x in out["layers"]))
    print("写入", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
