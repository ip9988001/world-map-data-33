#!/usr/bin/env python3
"""§五 可选补充探针（有界）：只对「已探通 + 有同源本地可读层」的代表层发 1 次 `?f=json`。

为什么需要：
  `inventory-local-fields.csv` 的字段名是 **stage-08 规范化后的 canonical 字段**（31 个，
  housenumber/streetname/postalcity/...），**不携带上游命名信息**；远程 CSV 只留了
  `fields_number_like`（门牌候选别名），没有街名/城市/邮编别名。因此「上游字段命名模板」只能靠
  `?f=json` 拿一次完整字段表。

纪律：
  · 每层最多 **1 个请求**（只 meta，不取样值、不下载资产）；总数硬上限 **1000**（--max-requests）
  · 8s 超时，失败不重试（死站不重复等）
  · 并发 8；结果逐层 append 到 checkpoint ndjson，重跑自动跳过已探层
  · 选择策略：provider 级去重（每个 provider 只探 1 个代表层），只探「D1 层 ∧ provider 有本地可读层」
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INV = os.path.join(REPO, "analysis", "full-inventory-20261124")
OUT = os.path.join(REPO, "analysis", "dialect-20261124")
CKPT = os.path.join(OUT, "probe-fields.ndjson")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "pi-dialect-probe/1.0", "Accept": "application/json"}


def prov_key(url):
    """provider 身份（与 build_dialects.py 保持同一实现）。"""
    m = re.match(r"https?://services\d*\.arcgis\.com/([^/]+)", url)
    if m:
        return f"agol:{m.group(1)}"
    m = re.match(r"https?://([^/]+)/arcgis/rest", url)
    if m:
        return f"host:{m.group(1).lower()}"
    m = re.match(r"https?://([^/]+)", url)
    if m:
        return f"dom:{m.group(1).lower()}"
    return "none"


def probe_one(url):
    rec = {"url": url, "requests_n": 0, "http": 0}
    try:
        with urllib.request.urlopen(urllib.request.Request(url.rstrip("/") + "?f=json",
                                                           headers=UA), timeout=8, context=CTX) as r:
            rec["requests_n"] += 1
            rec["http"] = r.status
            meta = json.loads(r.read())
    except urllib.error.HTTPError as e:
        rec["requests_n"] += 1
        rec["http"] = e.code
        rec["note"] = f"HTTPError {e.code}"
        return rec
    except Exception as e:  # noqa: BLE001
        rec["requests_n"] += 1
        rec["note"] = f"{type(e).__name__}: {str(e)[:90]}"
        return rec
    if not isinstance(meta, dict):
        rec["note"] = "non_json"
        return rec
    rec["fields"] = [f.get("name") for f in (meta.get("fields") or []) if f.get("name")]
    rec["geometryType"] = (meta.get("geometryType") or "").replace("esriGeometry", "")
    sr = meta.get("spatialReference") or {}
    rec["sr"] = {k: sr.get(k) for k in ("wkid", "latestWkid", "wkt") if sr.get(k) is not None}
    rec["name"] = meta.get("name")
    rec["maxRecordCount"] = meta.get("maxRecordCount")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-requests", type=int, default=1000)
    ap.add_argument("--mode", choices=("local-overlap", "highcov"), default="local-overlap",
                    help="local-overlap=有同源本地层的 provider（保证能出 golden case）；"
                         "highcov=按 D1 行数从大到小补探未探 provider（只提升模板可判率）")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    rem = list(csv.DictReader(open(os.path.join(INV, "inventory-remote-uncollected.csv"), encoding="utf-8")))
    D1 = [x for x in rem if x["usable"] in ("full_address", "no_zip", "no_city", "road_only")]
    loc = [x for x in csv.DictReader(open(os.path.join(INV, "inventory-local-all.csv"), encoding="utf-8"))
           if x.get("readable") == "1" and x["url"].strip()]
    local_prov = {prov_key(x["url"]) for x in loc}

    # provider 级去重：每个 provider 只挑 1 个代表层（优先 http 200 且样值多、count 大的）
    cand = collections.defaultdict(list)
    for x in D1:
        p = prov_key(x["url"])
        if a.mode == "local-overlap" and p not in local_prov:
            continue
        cand[p].append(x)
    targets, per_prov = [], {}
    for p, lst in cand.items():
        lst.sort(key=lambda x: (x["http_sample"] == "200", x["http_meta"] == "200",
                                int(x["sampled_n"] or 0)), reverse=True)
        targets.append(lst[0])
        per_prov[p] = len(lst)
    # 排序：信息增益最大者先探
    if a.mode == "highcov":
        rowsum = collections.defaultdict(int)
        for x in D1:
            try:
                rowsum[prov_key(x["url"])] += int(x["count"] or 0)
            except ValueError:
                pass
        targets.sort(key=lambda x: rowsum[prov_key(x["url"])], reverse=True)
    else:
        targets.sort(key=lambda x: per_prov[prov_key(x["url"])], reverse=True)
    targets = targets[: a.max_requests]

    done = set()
    if os.path.exists(CKPT):
        for line in open(CKPT, encoding="utf-8"):
            try:
                done.add(json.loads(line)["url"])
            except Exception:  # noqa: BLE001
                pass
    done_prov = set()
    if os.path.exists(CKPT):
        for line in open(CKPT, encoding="utf-8"):
            try:
                done_prov.add(json.loads(line)["provider"])
            except Exception:  # noqa: BLE001
                pass
    todo = [x for x in targets if x["url"] not in done and prov_key(x["url"]) not in done_prov]
    budget = max(0, a.max_requests - len(done_prov))
    todo = todo[:budget]
    print(f"providers_with_local={len(cand)} targets={len(targets)} already={len(done)} todo={len(todo)}",
          flush=True)

    t0 = time.time()
    n = 0
    with open(CKPT, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(probe_one, x["url"]): x for x in todo}
        for fut in as_completed(futs):
            r = fut.result()
            r["provider"] = prov_key(futs[fut]["url"])
            r["state"] = futs[fut].get("state", "")
            r["title"] = futs[fut].get("title", "")
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
            if n % 50 == 0:
                fh.flush()
                os.fsync(fh.fileno())
                el = time.time() - t0
                print(f"  {n}/{len(todo)} {el:.0f}s -> {n/max(el,1e-9):.2f} layer/s", flush=True)
    print(json.dumps({"probed": n, "requests_n": n, "wall_s": round(time.time() - t0, 1),
                      "checkpoint": CKPT}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
