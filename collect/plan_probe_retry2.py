#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05b retry2：42 个 pending 用长超时补探（60s×3、并发 4、分两批 21+21、单批墙钟上限）。

口径（用户 2026-11-21 立规，不许改）：
  alive      = returnCountOnly 拿到 count（回填 expect_live）
  unverified = 服务已死：404/500/no Query/not supported/TLS 失败/token required（含其他 4xx，429 除外）
  pending    = 暂时性：超时/429/连接重置/撞墙钟

探针仍走 collect/full_plan.py:_count_one（2026-11-22 起内部改为 probe_layer：复探 + 失败分类 + 解析固化；返回语义不变 = int|None）。URL 直接取 retry1 记录里的 url 字段（既有注册表来的，不重拼）。
每批跑完立刻落盘（覆盖写入 05b_plan_probe_retry.json 的 retry2 段）；撞墙钟的层标 pending 并 note「撞墙钟」。
挂死线程是 daemon，落盘后 os._exit 直接退出 —— 不留 ThreadPoolExecutor.__exit__ 等挂起任务的坑。

用法：python3 collect/plan_probe_retry2.py --batch 1 --cap 720
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from full_plan import _count_one            # noqa: E402  ★ 既有探针，不新写

RETRY_F = os.path.join(ROOT, "collect", "ledger", "05b_plan_probe_retry.json")
BACKOFF = (2, 4, 8)
_T = threading.local()
_orig = urllib.request.urlopen
DEAD_SIGNS = ("no query", "not supported", "token required", "invalid url", "unsupported",
              "certificate", "ssl", "tls")


def _traced(*a, **kw):
    try:
        r = _orig(*a, **kw)
        _T.http = getattr(r, "status", None) or 200
        _T.err, _T.body = "", ""
        oread, buf = r.read, []

        def _read(*ra, **rkw):
            b = oread(*ra, **rkw)
            if sum(len(x) for x in buf) < 300:
                buf.append(b)
            _T.body = b"".join(buf)[:300].decode("utf-8", "replace").replace("\n", " ")
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
        _T.err = "%s: %s" % (type(e).__name__, str(e)[:160])
        _T.body = body
        raise


urllib.request.urlopen = _traced


def verdict(http, live, err):
    if live is not None:
        return "alive"
    e = (err or "").lower()
    if "without count" in e:
        return "unverified"
    if http and int(http) >= 400 and int(http) != 429:
        return "unverified"
    if any(k in e for k in DEAD_SIGNS):
        return "unverified"
    return "pending"


def probe(rec, timeout, tries, deadline):
    out = {"layer": rec["layer"], "url": rec.get("url") or "", "src": "retry2",
           "http_code": None, "err": "", "tries": 0, "elapsed_ms": None,
           "expect_live": None, "verdict": None, "note": ""}
    t0 = time.time()
    for i in range(tries):
        if time.time() > deadline:
            out["note"] = "撞墙钟（本批 cap 到点，未完成第 %d 次尝试）" % (i + 1)
            break
        _T.http, _T.err, _T.body = None, "", ""
        out["tries"] = i + 1
        c = _count_one(out["url"], tries=1, timeout=timeout)
        out["http_code"] = _T.http
        out["err"] = _T.err or ""
        if c is not None:
            out["expect_live"] = c
            out["err"] = ""
            break
        if not out["err"]:
            out["err"] = "no count | http=%s | %s" % (_T.http, (_T.body or "")[:140])
        if i < tries - 1:
            time.sleep(BACKOFF[min(i, len(BACKOFF) - 1)])
    out["elapsed_ms"] = int((time.time() - t0) * 1000)
    out["verdict"] = verdict(out["http_code"], out["expect_live"], out["err"])
    if out["note"]:
        out["verdict"] = "pending" if out["verdict"] != "alive" else out["verdict"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, required=True)
    ap.add_argument("--size", type=int, default=21)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cap", type=int, default=720, help="单批墙钟上限（秒）")
    a = ap.parse_args()
    assert a.workers <= 4

    doc = json.load(open(RETRY_F, encoding="utf-8"))
    pend = [x for x in doc["records"] if x.get("verdict") == "pending"]
    lo = (a.batch - 1) * a.size
    todo = pend[lo:lo + a.size]
    if not todo:
        print("本批无待探层"); return 0

    out = {"batch": a.batch, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "params": {"timeout_s": a.timeout, "tries": a.tries, "backoff_s": list(BACKOFF),
                      "workers": a.workers, "cap_s": a.cap},
           "layers_n": len(todo), "records": []}
    deadline = time.time() + a.cap
    lock = threading.Lock()
    got = {}

    def run(rec):
        r = probe(rec, a.timeout, a.tries, deadline)
        with lock:
            got[rec["layer"]] = r
            out["records"] = list(got.values())
            dump()

    def dump():
        tmp = RETRY_F + ".tmp"
        d2 = dict(doc)
        cur = dict(out)
        cur["records"] = [got[k] for k in sorted(got)]
        prev = (doc.get("retry2") or {})
        batches = dict(prev.get("batches") or {})
        batches[str(a.batch)] = cur
        merged = {k: v for k, v in (prev.get("records") or {}) .items()} if isinstance(prev.get("records"), dict) else {}
        d2["retry2"] = {"batches": batches}
        d2["retry2"]["records"] = cur["records"]
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(d2, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, RETRY_F)

    ths = []
    for rec in todo:
        while len([t for t in ths if t.is_alive()]) >= a.workers:
            time.sleep(0.5)
        t = threading.Thread(target=run, args=(rec,), daemon=True)
        t.start()
        ths.append(t)
    while any(t.is_alive() for t in ths) and time.time() < deadline:
        time.sleep(1)
    time.sleep(0.2)
    # 撞墙钟未启动/未完成的层补 pending
    for rec in todo:
        if rec["layer"] not in got:
            got[rec["layer"]] = {"layer": rec["layer"], "url": rec.get("url") or "", "src": "retry2",
                                 "http_code": None, "err": "", "tries": 0, "elapsed_ms": None,
                                 "expect_live": None, "verdict": "pending",
                                 "note": "撞墙钟（本批 cap 到点，未开跑）"}
    cur = dict(out); cur["records"] = [got[k] for k in sorted(got)]
    prev = doc.get("retry2") or {}
    batches = dict(prev.get("batches") or {})
    batches[str(a.batch)] = cur
    doc["retry2"] = {"batches": batches}
    allr = []
    for b in sorted(batches, key=lambda x: int(x)):
        allr += batches[b]["records"]
    doc["retry2"]["records"] = allr
    with open(RETRY_F, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    cnt = {}
    for r in cur["records"]:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1
    print("batch#%d 完成 %d 层 %s" % (a.batch, len(cur["records"]), cnt), flush=True)
    sys.stdout.flush()
    os._exit(0)          # 不等挂起 daemon 线程


if __name__ == "__main__":
    main()
