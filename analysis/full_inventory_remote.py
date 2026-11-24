#!/usr/bin/env python3
"""Phase 3：远程未采层 2 请求极速盘点（可续跑）。

每层：
  R1  <url>?f=json                                     meta（name/geometryType/nfields/maxRecordCount）
  R2  <url>/query?where=1=1&outFields=*&resultRecordCount=20&f=json   20 条样值
  R3  仅当 R1/R2 都没给出要素数时：query?returnCountOnly=true（第 3 请求，计入 requests_n）

纪律：
  · 并发 ≤ 8；单层超时 30s；429/503/5xx 退避重试 2 次（1s、3s）
  · 单层失败不中断整轮；每 200 层写 checkpoint（progress.json）+ 分片 ndjson
  · 可续跑：启动时读已有分片，跳过已完成 url
  · 零写入上游、零下载资产（只要 metadata + 20 条样值）

用法：
  python3 analysis/full_inventory_remote.py --concurrency 8 [--limit N] [--minutes M]
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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "analysis", "full-inventory-20261124")
SHARDS = os.path.join(OUTDIR, "inventory-remote-uncollected.shards")
PROGRESS = os.path.join(REPO, "progress.json")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "pi-inventory/1.0", "Accept": "application/json"}
NUM = ("housenum", "addrnum", "addnum", "number", "num", "houseno", "situs", "bldg", "hsn",
       "stnum", "streetno", "street_no", "_no", "house")
COLS = ["url", "state", "title", "svc", "geom", "n_fields", "maxRecordCount", "count",
        "count_source", "sampled_n", "fields_number_like", "number_nonnull",
        "addr_core_hit", "usable", "requests_n", "http_meta", "http_sample", "probe_note"]
_lock = threading.RLock()
# 实时状态（供 30s 心跳写 progress.json；不改动采集语义）
STATE = {"done": 0, "done0": 0, "total": 0, "last_url": "", "pid": 0,
         "ok": 0, "fail": 0, "unreachable": 0, "t0": 0.0}
_stop = threading.Event()


def utcnow(offset_s=0.0):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + offset_s))


def write_progress():
    """原子写 progress.json：新增顶层 phase3_live（done/total/pct/last_url/pid/
    updated_at/eta_utc），同时刷新既有 phase3 块，不删除任何既有键。"""
    with _lock:
        st = dict(STATE)
        try:
            prog = (json.load(open(PROGRESS, encoding="utf-8"))
                    if os.path.exists(PROGRESS) else {})
            if not isinstance(prog, dict):
                prog = {}
        except Exception:  # noqa: BLE001
            prog = {}
        el = max(1e-9, time.time() - st["t0"]) if st["t0"] else 0.0
        rate = (st["done"] - st["done0"]) / el if el else 0.0
        remain = max(0, st["total"] - st["done"])
        live = {"done": st["done"], "total": st["total"],
                "pct": round(100.0 * st["done"] / st["total"], 2) if st["total"] else 0.0,
                "last_url": st["last_url"], "pid": st["pid"],
                "updated_at": utcnow(),
                "eta_utc": utcnow(remain / rate) if rate > 0 else "",
                "ok": st["ok"], "fail": st["fail"],
                "rate_layers_per_s": round(rate, 3), "elapsed_s": round(el, 1)}
        prog = {"phase3_live": live, **{k: v for k, v in prog.items() if k != "phase3_live"}}
        p3 = prog.get("phase3")
        if not isinstance(p3, dict):
            p3 = prog["phase3"] = {}
        p3.update({"at": live["updated_at"], "planned": st["total"], "done": st["done"],
                   "ok": st["ok"], "fail": st["fail"], "unreachable": st["unreachable"],
                   "elapsed_s": live["elapsed_s"],
                   "rate_layers_per_s": live["rate_layers_per_s"]})
        tmp = PROGRESS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(prog, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, PROGRESS)


def _heartbeat(interval=30):
    while not _stop.wait(interval):
        try:
            write_progress()
        except Exception as e:  # noqa: BLE001
            print(f"progress_err {type(e).__name__}: {e}", flush=True)


def _j(b):
    try:
        return json.loads(b)
    except Exception:  # noqa: BLE001
        return None


def http(url, timeout=15, retries=1):
    last = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout,
                                        context=CTX) as r:
                return r.status, _j(r.read()), ""
        except urllib.error.HTTPError as e:
            last = f"HTTP{e.code}"
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1 + 2 * attempt)
                continue
            return e.code, _j(e.read()[:1500]), f"HTTPError {e.code} {e.reason}"
        except Exception as e:  # noqa: BLE001
            # 超时/断连不重试（死站会白等 3 倍时间），只有 429/5xx 才退避重试
            return 0, None, f"{type(e).__name__}: {str(e)[:90]}"
    return 0, None, last


def blanks(v):
    return v in (None, "", " ") or (isinstance(v, (list, dict)) and not v)


def num_fields(attrs):
    if not attrs:
        return {}, {}
    out, keys = {}, list(attrs[0])
    for k in keys:
        kl = k.lower()
        if not any(t in kl for t in NUM):
            continue
        nb = [a.get(k) for a in attrs if not blanks(a.get(k))]
        wd = [v for v in nb if re.search(r"\d", str(v))]
        out[k] = {"nonblank": len(nb), "with_digit": len(wd), "n": len(attrs)}
    return out, keys


def probe(layer):
    url = layer["url"].rstrip("/")
    rec = {"url": url, "state": layer.get("state", ""), "title": layer.get("title", ""),
           "svc": layer.get("svc", ""), "requests_n": 0}
    st, meta, err = http(url + "?f=json", timeout=8)
    rec["requests_n"] += 1
    rec["http_meta"], rec["probe_note"] = st, err
    meta = meta if isinstance(meta, dict) else {}
    rec["geom"] = (meta.get("geometryType") or layer.get("geom") or "").replace("esriGeometry", "")
    rec["maxRecordCount"] = meta.get("maxRecordCount")
    fields = [f.get("name") for f in meta.get("fields", [])] if meta else []
    rec["n_fields"] = len(fields) or layer.get("nfields") or ""
    rec["count"] = meta.get("count") if meta.get("count") is not None else None
    rec["count_source"] = "meta" if rec["count"] is not None else ""

    if st != 200:
        # meta 就拿不到 → 不再发第二个请求（死站白等 20s），单层成本从 28s 降到 8s
        rec["http_sample"] = 0
        rec["probe_note"] = (err or f"http_meta={st}") + "; sample:skipped_meta_failed"
        rec["sampled_n"], rec["fields_number_like"], rec["number_nonnull"] = 0, "", "{}"
        rec["addr_core_hit"], rec["usable"] = "", "unreachable"
        return rec
    q = url + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "outFields": "*", "resultRecordCount": 20, "f": "json"})
    st2, smp, err2 = http(q, timeout=15)
    rec["requests_n"] += 1
    rec["http_sample"] = st2
    if err2:
        rec["probe_note"] = (rec["probe_note"] + "; " if rec["probe_note"] else "") + "sample:" + err2
    feats = (smp or {}).get("features", []) if isinstance(smp, dict) else []
    attrs = [f.get("attributes", {}) for f in feats]
    rec["sampled_n"] = len(attrs)
    nf, _ = num_fields(attrs)
    rec["fields_number_like"] = ",".join(list(nf)[:6])
    rec["number_nonnull"] = json.dumps({k: v["with_digit"] for k, v in nf.items()},
                                       ensure_ascii=False)[:200]
    if rec["count"] is None and st2 == 200:
        st3, cnt, err3 = http(url + "/query?" + urllib.parse.urlencode(
            {"where": "1=1", "returnCountOnly": "true", "f": "json"}), timeout=15, retries=0)
        rec["requests_n"] += 1
        if isinstance(cnt, dict) and cnt.get("count") is not None:
            rec["count"] = cnt["count"]
            rec["count_source"] = "returnCountOnly"

    # addr_core_hit：门牌 / 街名 / 城市 / 州 / 邮编 是否在样值里过半非空
    if attrs:
        keys = list(attrs[0])
        def frac(pred):
            return sum(1 for a in attrs if any(pred(k) and not blanks(a.get(k)) for k in keys)) / len(attrs)
        num_hit = any(v["with_digit"] >= max(1, len(attrs) // 2) for v in nf.values())
        street = frac(lambda k: any(t in k.lower() for t in ("street", "st_name", "stname", "road", "addr"))
                      and not any(t in k.lower() for t in NUM))
        city = frac(lambda k: any(t in k.lower() for t in ("city", "municipality", "town", "place")))
        state = frac(lambda k: k.lower() in ("state", "st", "state_abbr", "addr_state", "statecode"))
        zp = frac(lambda k: any(t in k.lower() for t in ("zip", "postcode", "postal")))
        rec["addr_core_hit"] = "".join("1" if x else "0" for x in (num_hit, street, city, state, zp))
        rec["usable"] = ("full_address" if all([num_hit, street, city, state, zp])
                         else "no_zip" if (num_hit and street and not zp)
                         else "no_city" if (num_hit and street and not city)
                         else "road_only" if (street and not num_hit)
                         else "empty_shell")
    else:
        rec["addr_core_hit"], rec["usable"] = "", "empty_shell"
    if rec["http_meta"] != 200 and rec["http_sample"] != 200:
        rec["usable"] = "unreachable"
    return rec


def load_done():
    done = set()
    if os.path.isdir(SHARDS):
        for fn in os.listdir(SHARDS):
            if not fn.endswith(".ndjson"):
                continue
            with open(os.path.join(SHARDS, fn), encoding="utf-8") as f:
                for line in f:
                    try:
                        done.add(json.loads(line)["url"])
                    except Exception:  # noqa: BLE001
                        pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--minutes", type=int, default=0, help="跑满 N 分钟就收尾（0=不限）")
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()
    os.makedirs(SHARDS, exist_ok=True)

    sets = json.load(open(os.path.join(a.outdir, "_url_sets.json"), encoding="utf-8"))
    survey = json.load(open(os.path.join(REPO, "survey", "ng911", "layers.json"), encoding="utf-8"))
    by_url = {}
    for x in survey:
        by_url.setdefault(x["url"].rstrip("/"), x)
    todo = [by_url[u] for u in sets["survey_urls"] if u not in set(sets["collected_urls"])]
    done = load_done()
    todo = [x for x in todo if x["url"].rstrip("/") not in done]
    if a.limit:
        todo = todo[:a.limit]
    print(f"todo={len(todo)} already_done={len(done)} concurrency={a.concurrency}", flush=True)

    t0 = time.time()
    try:
        _prev = json.load(open(PROGRESS, encoding="utf-8")).get("phase3", {}) or {}
    except Exception:  # noqa: BLE001
        _prev = {}
    base = {k: int(_prev.get(k) or 0) for k in ("ok", "fail", "unreachable")}
    STATE.update({"done": len(done), "done0": len(done), "total": len(todo) + len(done),
                  "last_url": "", "pid": os.getpid(), "t0": t0,
                  "ok": base["ok"], "fail": base["fail"], "unreachable": base["unreachable"]})
    threading.Thread(target=_heartbeat, kwargs={"interval": 30}, daemon=True).start()
    write_progress()
    existing = [int(f[6:11]) for f in os.listdir(SHARDS) if f.startswith("shard-") and f.endswith(".ndjson")]
    shard_no, buf, n_ok, n_fail = (max(existing) + 1 if existing else 0), [], 0, 0
    stats = collections.Counter()
    csv_f = os.path.join(a.outdir, "inventory-remote-uncollected.csv")
    new_file = not os.path.exists(csv_f)

    def flush_csv(rows, first=False):
        with open(csv_f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            if first:
                w.writeheader()
            w.writerows(rows)

    def flush_shard(force=False):
        nonlocal shard_no, buf
        if not buf or (not force and len(buf) < 200):
            return
        p = os.path.join(SHARDS, f"shard-{shard_no:05d}.ndjson")
        with open(p, "w", encoding="utf-8") as fh:
            for r in buf:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        flush_csv(buf, first=new_file if shard_no == 0 else False)
        shard_no += 1
        buf = []
        write_progress()

    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(probe, x): x for x in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                r = fut.result()
            except Exception as e:  # noqa: BLE001
                r = {"url": futs[fut]["url"], "probe_note": f"worker_err:{type(e).__name__}",
                     "requests_n": 0, "usable": "worker_error"}
            if r.get("usable") == "unreachable":
                stats["fail"] += 1
            elif r.get("http_meta") == 200 or r.get("http_sample") == 200:
                stats["ok"] += 1
            else:
                stats["fail"] += 1
            stats[r.get("usable") or "?"] += 1
            with _lock:
                buf.append(r)
                n_ok, n_fail = stats["ok"], stats["fail"]
                STATE["last_url"] = r.get("url", "")
                STATE.update({"done": len(done) + n_ok + n_fail,
                              "ok": base["ok"] + stats["ok"],
                              "fail": base["fail"] + stats["fail"],
                              "unreachable": base["unreachable"] + stats["unreachable"]})
                flush_shard()
            if i % 500 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(todo)} ok={stats['ok']} fail={stats['fail']} "
                      f"{el:.0f}s -> {i/el:.2f} layer/s", flush=True)
            if a.minutes and (time.time() - t0) > a.minutes * 60:
                print("  TIME BUDGET reached", flush=True)
                break
    flush_shard(force=True)
    _stop.set()
    write_progress()
    print(json.dumps({"probed": n_ok + n_fail, "ok": stats["ok"], "fail": stats["fail"],
                      "unreachable": stats["unreachable"],
                      "usable": {k: v for k, v in stats.items()
                                 if k in ("full_address", "no_zip", "no_city", "road_only",
                                          "empty_shell", "unreachable")},
                      "wall_s": round(time.time() - t0, 1)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
