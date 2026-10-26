#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【已退役 · 禁止生产使用】本机应急批处理器（2026-10-26 宗地批1 用）。

★ 为什么退役：三仓的正牌第 10 环是 collect/run_step_10.py → worker_core.py → pilot.py，
  pilot.py 已具备分 part / keyset 分页 / _checkpoint 断点 / Release 上传 / 报告全套能力。
  本文件是绕过 pilot 的平行实现，且带本机硬编码（哨兵 send_once.mjs、ops/parcel_progress.json），
  在 runner 上跑不起来，在本机跑就违反「采集/批量生产铁律」第 1 条。
  保留只为留档：批1 当时的行为与参数可回溯。任何新作业一律走 workflow。
"""
from __future__ import annotations
import csv, gzip, json, os, re, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.fetch import get_json
from lib.schema import normalize

HERE = os.path.dirname(os.path.abspath(__file__))
OUTBASE = os.path.join(HERE, "parcel_out")
PROG = os.path.join(os.path.dirname(HERE), "ops", "parcel_progress.json")
SEND = "/root/pi-work/sentinel-bot/send_once.mjs"
PUSH_EVERY = 600
CHUNK = 50000
os.makedirs(OUTBASE, exist_ok=True)

_lock = {}

def log(*a):
    print(*a, flush=True)


def push(msg):
    try:
        subprocess.Popen(["node", SEND, msg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def api_of(url):
    u = url.split("?")[0].rstrip("/")
    if not re.search(r"/(FeatureServer|MapServer)(/\d+)?$", u):
        return u
    if not re.search(r"/\d+$", u):
        u += "/0"
    return u


def run_layer(r):
    lid = r["layer"]
    st = {"layer": lid, "state": r["state"], "declared": int(r["declared"]),
          "fetched": 0, "valid": 0, "parts": 0, "err": ""}
    try:
        api = api_of(r["url"])
        meta = get_json(api + "?f=json", timeout=25)
        if "__error__" in meta:
            st["err"] = "meta"; return st
        oid = meta.get("objectIdField") or meta.get("objectIdFieldName")
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        if not oid:
            oid = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID", "OBJECTID_12") if k in fns), "OBJECTID")
        maxrc = int(meta.get("maxRecordCount") or 1000)
        ps = min(maxrc, 2000)
        if len(fns) > 120: ps = min(ps, 200)
        elif len(fns) > 60: ps = min(ps, 500)
        where = meta.get("definitionExpression") or "1=1"
        d = os.path.join(OUTBASE, re.sub(r"[^A-Za-z0-9_.-]", "_", lid)[:90])
        os.makedirs(d, exist_ok=True)
        buf, part, last = [], 0, None

        def flush():
            nonlocal buf, part
            if not buf: return
            p = os.path.join(d, "part-%05d.ndjson.gz" % part)
            with gzip.open(p, "wt", encoding="utf-8") as f:
                for rec in buf:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            buf = []; part += 1; st["parts"] = part

        while True:
            w = where if last is None else ("(%s) AND %s>%s" % (where, oid, last) if where != "1=1" else "%s>%s" % (oid, last))
            q = {"where": w, "outFields": "*", "returnGeometry": "true", "outSR": 4326,
                 "f": "json", "resultRecordCount": ps, "orderByFields": oid}
            d2 = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=180)
            if "__error__" in d2:
                if st["fetched"] == 0:
                    q.pop("orderByFields"); q["where"] = where
                    d2 = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=180)
                    if "__error__" in d2:
                        st["err"] = "query"; return st
                    st["err"] = "no_keyset"
                else:
                    st["err"] = "mid"; break
            feats = d2.get("features") or []
            if not feats: break
            for ft in feats:
                a = ft.get("attributes") or {}
                g = ft.get("geometry") or {}
                rec = normalize(a, g.get("y"), g.get("x"))
                rec.update({"src_layer": lid, "src_state": r["state"], "raw": a})
                if rec.get("addr_key"):
                    st["valid"] += 1
                else:
                    for f in ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION"):
                        v = a.get(f)
                        if v and re.search(r"\d", str(v)):
                            st["valid"] += 1; break
                buf.append(rec); st["fetched"] += 1
                oidv = a.get(oid)
                if oidv is None:
                    for kk in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                        if kk in a: oidv = a[kk]; break
                if oidv is not None: last = oidv
            if len(buf) >= CHUNK: flush()
            if not d2.get("exceededTransferLimit") and len(feats) < ps: break
            if last is None: break
            time.sleep(0.1)
        flush()
        return st
    except Exception as e:
        st["err"] = type(e).__name__
        return st


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "batch1.csv"), encoding="utf-8")))
    allmeta = {r["layer_id"]: r for r in csv.DictReader(open(os.path.join(HERE, "situs_layers.csv"), encoding="utf-8"))}
    for r in rows:
        r["url"] = allmeta.get(r["layer"], {}).get("url", "")
    rows = [r for r in rows if r["url"]]
    # 续跑：已有 part 文件的层直接跳过（避免暂停/恢复后重复采）
    def _san(l): return re.sub(r"[^A-Za-z0-9_.-]", "_", l)[:90]
    before = len(rows)
    rows = [r for r in rows if not os.path.exists(os.path.join(OUTBASE, _san(r["layer"]), "part-00000.ndjson.gz"))]
    log("[批1] 续跑：跳过已完成 %d 层，本轮 %d 层" % (before - len(rows), len(rows)))
    total_decl = sum(int(r["declared"]) for r in rows)
    t0 = time.time()
    last_push = t0
    done = {"layers": 0, "fetched": 0, "valid": 0, "err": 0}
    log("[批1] %d 层 / 声明 %s 行" % (len(rows), format(total_decl, ",")))
    push("▶️ 宗地扩采 批1 开跑\n%d 层 / 声明 %s 行\n按有效率≥50%%筛出，全量采" % (len(rows), format(total_decl, ',')))
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(run_layer, r): r for r in rows}
        for f in as_completed(futs):
            st = f.result()
            done["layers"] += 1
            done["fetched"] += st["fetched"]
            done["valid"] += st["valid"]
            if st["err"]: done["err"] += 1
            pr = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  "done_layers": done["layers"], "total_layers": len(rows),
                  "fetched": done["fetched"], "valid": done["valid"], "err": done["err"],
                  "total_declared": total_decl,
                  "pct": round(done["fetched"] * 100.0 / max(1, total_decl), 2),
                  "elapsed_min": round((time.time() - t0) / 60, 1)}
            json.dump(pr, open(PROG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            now = time.time()
            if now - last_push >= PUSH_EVERY:
                last_push = now
                eta = (time.time() - t0) / max(1e-9, done["fetched"]) * max(1, total_decl - done["fetched"]) / 60
                push("⏳ 宗地扩采 批1 进度\n层 %d/%d · 行 %s/%s（%.1f%%）\n有效 %s · 失败 %d\n已跑 %.0f 分 · 预计剩余 %.0f 分" % (
                    done["layers"], len(rows), format(done["fetched"], ','), format(total_decl, ','),
                    pr["pct"], format(done["valid"], ','), done["err"], pr["elapsed_min"], eta))
    el = round((time.time() - t0) / 60, 1)
    push("✅ 宗地扩采 批1 完成\n层 %d/%d · 实采 %s 行\n有效地址 %s 条（%.1f%%）\n失败 %d 层 · 用时 %.0f 分" % (
        done["layers"], len(rows), format(done["fetched"], ','), format(done["valid"], ','),
        done["valid"] * 100.0 / max(1, done["fetched"]), done["err"], el))
    json.dump({"done": done, "elapsed_min": el, "total_declared": total_decl},
              open(os.path.join(HERE, "batch1_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(json.dumps(done, ensure_ascii=False))


if __name__ == "__main__":
    main()
