#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05b plan probe 重探（方案 a）：只用 full_plan 既有探针，不新写探针逻辑，只读。

verdict 三分类（写死，不许改口径）：
  alive        —— returnCountOnly 拿到 count（写进 expect_live，不许用 0 填）
  unverified   —— 服务已死：404 / 400 / 500 / 502 / 503 / no Query / not supported / TLS 失败 / token required
  pending      —— 暂时性：超时 / 限流(429) / 连接重置 —— 不代表死，也不代表活

参数（用户 2026-11-21 口径）：timeout 60s、重试 3 次、指数退避 2s/4s/8s、并发 ≤4。

层→URL：plan probe 文件里没有 url 字段（0 层自带），统一走 plan 阶段同一套映射函数
worker_core._rows_from_csv + _norm_plan_row + _url_index —— 不手写 API 模板、不猜路径。

用法：python3 collect/plan_probe_reprobe.py [--workers 4] [--timeout 60] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from full_plan import _count_one            # noqa: E402  ★ 既有探针，不新写
import worker_core as W                     # noqa: E402  ★ plan 阶段同一套层→URL 映射

PLAN_F = os.path.join(ROOT, "collect", "ledger", "05b_plan_probe.json")
OUT_F = os.path.join(ROOT, "collect", "ledger", "05b_plan_probe_reprobe.json")
BACKOFF = (2, 4, 8)

_orig_urlopen = urllib.request.urlopen


class _Slots(__import__("threading").local):   # 每线程独立槽位：http_code / err / body
    http = None
    err = ""
    body = ""


_T = _Slots()


def _traced(*a, **kw):
    try:
        r = _orig_urlopen(*a, **kw)
        _T.http = getattr(r, "status", None) or 200
        _T.err = ""
        _orig_read, _buf = r.read, []

        def _read(*ra, **rkw):               # 200 回错误体时能看见原因
            b = _orig_read(*ra, **rkw)
            if sum(len(x) for x in _buf) < 300:
                _buf.append(b)
            _T.body = b"".join(_buf)[:300].decode("utf-8", "replace").replace("\n", " ")
            return b

        r.read = _read
        return r
    except Exception as e:  # noqa: BLE001
        _T.http = getattr(e, "code", None)
        body = ""
        try:
            body = (e.read() or b"")[:200].decode("utf-8", "replace").replace("\n", " ")
        except Exception:  # noqa: BLE001
            pass
        _T.err = "%s: %s" % (type(e).__name__, str(e)[:160]) + (" | " + body[:120] if body else "")
        raise


urllib.request.urlopen = _traced

DEAD_SIGNS = ("no query", "not supported", "token required", "invalid url", "unsupported",
              "certificate", "ssl", "tls")


def verdict(http, live, err):
    if live is not None:
        return "alive"
    e = (err or "").lower()
    if http and int(http) >= 400 and int(http) != 429:
        if any(k in e for k in DEAD_SIGNS):
            return "unverified"
        return "unverified"
    if "without count" in e:
        return "unverified"                      # 200 但响应无 count：服务端不认 returnCountOnly / no Query
    if any(k in e for k in DEAD_SIGNS):
        return "unverified"                      # TLS/证书/不支持 —— 服务端侧死
    return "pending"                             # 超时 / 429 / 连接重置


def probe(lid, url, timeout, retries):
    rec = {"layer": lid, "url": url, "http_code": None, "err": "", "tries": 0,
           "elapsed_ms": None, "expect_live": None, "verdict": None}
    t0 = time.time()
    for i in range(retries + 1):
        _T.http, _T.err, _T.body = None, "", ""
        rec["tries"] = i + 1
        c = _count_one(url, tries=1, timeout=timeout)
        rec["http_code"] = _T.http
        rec["err"] = _T.err or ""
        if not rec["err"] and c is None and _T.body:
            rec["err"] = "http%s without count | %s" % (rec["http_code"], _T.body[:160])
        if c is not None:
            rec["expect_live"] = c               # 只写真值，不用 0 填
            rec["err"] = ""
            break
        if i < retries:
            time.sleep(BACKOFF[min(i, len(BACKOFF) - 1)])
    rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    rec["verdict"] = verdict(rec["http_code"], rec["expect_live"], rec["err"])
    return rec


def dump(path, doc):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4, help="并发上限（口径 ≤4）")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    assert a.workers <= 4, "并发上限 4"

    plan = json.load(open(PLAN_F, encoding="utf-8"))
    order = []
    for s in plan.get("shards") or []:
        order += list(s.get("layers") or [])
    order += [i for i in plan.get("expect_by_layer") or {} if i not in set(order)]
    live = set(plan.get("expect_live") or {})
    targets = [i for i in order if i not in live]
    if a.limit:
        targets = targets[:a.limit]

    rows = [W._norm_plan_row(r) for r in W._rows_from_csv(os.path.join(HERE, "layer_plan.csv"))]
    idx = {r["id"]: r["url"] for r in rows if r.get("url")}
    uidx = W._url_index()

    def resolve(lid):
        for k, src in ((lid, "layer_plan.csv"), (lid.split("@")[0], "layer_plan.csv(base_id_strip)"),
                       (lid, "situs_layers.csv"), (lid.split("@")[0], "situs_layers.csv(base_id_strip)")):
            u = (idx if src.startswith("layer_plan") else uidx).get(k)
            if u:
                return u, src
        return "", ""

    doc = {"schema": "collect-plan-probe-reprobe/v1", "stage": "05b",
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "source_plan": os.path.relpath(PLAN_F, ROOT),
           "probe_fn": "collect/full_plan.py:_count_one (unchanged)",
           "url_source": "worker_core._rows_from_csv+_norm_plan_row(layer_plan.csv) / _url_index()",
           "timeout_s": a.timeout, "retries": a.retries, "backoff_s": list(BACKOFF),
           "workers": a.workers, "read_only": True, "targets_n": len(targets),
           "verdict_defs": {"alive": "returnCountOnly 拿到 count",
                            "unverified": "服务已死：404/400/500/502/503/no Query/not supported/TLS/token required",
                            "pending": "暂时性：超时/429/连接重置"},
           "records": []}
    dump(OUT_F, doc)
    print("★ 目标 %d 层，workers=%d timeout=%ds retries=%d backoff=%s"
          % (len(targets), a.workers, a.timeout, a.retries, list(BACKOFF)), flush=True)

    done, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {}
        for lid in targets:
            u, src = resolve(lid)
            if not u:
                done.append({"layer": lid, "url": "", "url_source": "none", "http_code": None,
                             "err": "no url in registry", "tries": 0, "elapsed_ms": 0,
                             "expect_live": None, "verdict": "unverified"})
                continue
            futs[ex.submit(probe, lid, u, a.timeout, a.retries)] = (lid, src)
        for fu in as_completed(futs):
            r = fu.result()
            r["url_source"] = futs[fu][1]
            done.append(r)
            doc["records"] = done
            dump(OUT_F, doc)                     # 逐层落盘
            print("  [%2d/%2d] %-10s %-56s http=%s %dms"
                  % (len(done), len(targets), r["verdict"], r["layer"][:56],
                     r["http_code"], r["elapsed_ms"] or 0), flush=True)

    doc["records"] = done
    cnt = {}
    for r in done:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    doc["verdict_counts"] = cnt
    doc["elapsed_s"] = round(time.time() - t0, 1)
    dump(OUT_F, doc)
    print("★ 完成 %d 层，%.1fs，%s" % (len(done), doc["elapsed_s"], cnt), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
