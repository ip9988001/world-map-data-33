#!/usr/bin/env python3
"""D1（远程 16,010 层）坐标采样：ArcGIS REST /query 直取几何，断点续跑。

- 每层一条 query：where=1=1&outFields=*&returnGeometry=true&outSR=4326
  &resultRecordCount=50&f=json
- 断点续跑：extract/d1_<sha1>.json 已存在即跳过，第二遍请求数 = 0。
- 死链/无几何/403/404：单层最多 3 次（退避 2s/5s/10s），标 unavailable，不死磕。
- 坐标只取响应里的几何；非 4326 才做换算（3857 族反算，公式写进 REPORT），
  换算不了的 wkid 一律 unavailable，不填 0,0、不用质心、不插值。
用法：
  python3 sample_remote.py [--workers 12] [--states DE,NH,IA] [--limit N]
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import threading
import time
from collections import defaultdict
from urllib.parse import urlsplit

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = os.path.join(ROOT, "layers.json")
EXTRACT = os.environ.get("COORD_EXTRACT", "/data/coord-work-20261124/extract")
CACHE = os.environ.get("COORD_CACHE", "/data/coord-work-20261124/cache")
LOG = os.environ.get("COORD_LOG", "/data/coord-work-20261124/fetch.log")
TARGET = 50
TIMEOUT = (8, 25)
BACKOFF = (2, 5, 10)
MERK = {"wkid": 3857, "factors": 20037508.342789244}

_tls = threading.local()
_host_sem = defaultdict(lambda: threading.Semaphore(4))
_lock = threading.Lock()
_log_lock = threading.Lock()


def sess():
    if not getattr(_tls, "s", None):
        s = requests.Session()
        s.headers["User-Agent"] = "wmd-coord-samples/1.0 (research; contact ip9988001)"
        _tls.s = s
    return _tls.s


def log(msg):
    with _log_lock:
        with open(LOG, "a") as f:
            f.write(msg + "\n")


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def query_url(url):
    u = url.rstrip("/")
    if u.endswith("/query"):
        return u + "?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326" \
                   "&resultRecordCount=50&f=json"
    return u + "/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326" \
               "&resultRecordCount=50&f=json"


def merc_to_wgs(x, y):
    lon = x / MERK["factors"] * 180.0
    lat = y / MERK["factors"] * 180.0
    lat = 180.0 / 3.141592653589793 * (2 * __import__("math").atan(
        __import__("math").exp(lat * 3.141592653589793 / 180.0)) - 3.141592653589793 / 2)
    return lon, lat


def vert(g, gt):
    """从一个 feature 的 geometry 取一个真实顶点（不做质心）。"""
    if not isinstance(g, dict):
        return None
    for k in ("y", "Y"):
        if k in g and g.get("x") is not None and g.get("y") is not None:
            return float(g["x"]), float(g["y"])
    for k in ("rings", "paths"):
        a = g.get(k)
        if a:
            p = a[0][0] if isinstance(a[0][0], (list, tuple)) else a[0]
            if len(p) >= 2:
                return float(p[0]), float(p[1])
    for k in ("points", "curvePaths"):
        a = g.get(k)
        if a:
            p = a[0]
            p = p[0] if isinstance(p[0], (list, tuple)) else p
            if len(p) >= 2:
                return float(p[0]), float(p[1])
    return None


def probe(L):
    url = L["url"]
    if not url:
        return {"status": "unavailable", "reason": "empty_url", "attempts": 0,
                "http_code": None, "rows": []}
    host = urlsplit(url).netloc
    out = {"layer_id": L["layer_id"], "url": url, "state": L["state"], "universe": "d1",
           "provider": L["provider"], "sample_source": "arcgis_query", "rows": [],
           "http_code": None, "attempts": 0}
    last = ""
    with _host_sem[host]:
        for i, wait in enumerate((0,) + BACKOFF):
            if wait:
                time.sleep(wait)
            out["attempts"] = i + 1
            try:
                r = sess().get(query_url(url), timeout=TIMEOUT)
            except Exception as e:
                last = f"{type(e).__name__}: {str(e)[:120]}"
                log(f"{key_of(url)}\tattempt{i+1}\texc\t{last}\t{url}")
                continue
            out["http_code"] = r.status_code
            if r.status_code in (403, 404, 410):
                out.update(status="unavailable", reason=f"http_{r.status_code}")
                log(f"{key_of(url)}\tattempt{i+1}\thttp{r.status_code}\t{url}")
                return out
            if r.status_code != 200:
                last = f"http_{r.status_code}"
                log(f"{key_of(url)}\tattempt{i+1}\thttp{r.status_code}\t{url}")
                continue
            try:
                j = r.json()
            except Exception:
                last = "non_json_response"
                log(f"{key_of(url)}\tattempt{i+1}\tnon_json\t{r.text[:80]}")
                continue
            if isinstance(j, dict) and j.get("error"):
                err = j["error"]
                code = err.get("code") if isinstance(err, dict) else None
                msg = (err.get("message") if isinstance(err, dict) else str(err))[:120]
                out.update(status="unavailable", reason=f"rest_error_{code}: {msg}")
                log(f"{key_of(url)}\tattempt{i+1}\tresterr{code}\t{msg}\t{url}")
                return out
            with gzip.open(os.path.join(CACHE, key_of(url) + ".json.gz"), "wt") as f:
                f.write(json.dumps(j, ensure_ascii=False))
            return parse(j, out)
    out.update(status="unavailable", reason=f"exhausted: {last}")
    return out


def parse(j, out):
    feats = j.get("features") or []
    sr = j.get("spatialReference") or {}
    wkid = sr.get("latestWkid") or sr.get("wkid")
    gt = j.get("geometryType") or ""
    out["wkid"] = wkid
    out["geom_type"] = gt
    out["exceeded"] = j.get("exceededTransferLimit")
    fields = [f.get("name") for f in (j.get("fields") or []) if isinstance(f, dict)]
    addr_like = {f for f in fields if re.search(
        r"addr|house|street|st_?name|num|suf|zip|post|city|muni|place", f or "", re.I)}
    for idx, ft in enumerate(feats[:TARGET]):
        g = (ft or {}).get("geometry") or {}
        xy = vert(g, gt)
        if not xy:
            continue
        x, y = xy
        lon_raw, lat_raw = x, y
        if wkid in (4326, 4269, None) and -180 <= x <= 180 and -90 <= y <= 90:
            lon, lat = x, y
            if wkid is None:
                out.setdefault("wkid_note", "no_spatial_reference_in_response; values are degree-range")
        elif wkid in (3857, 102100, 102113, 900913):
            lon, lat = merc_to_wgs(x, y)
            out["converted"] = "3857->4326 inverse mercator"
        elif wkid in (4326, 4269):
            lon, lat = x, y
        else:
            out.update(status="unavailable", reason=f"wkid_unconvertible:{wkid}",
                       http_code=out.get("http_code"))
            out["rows"] = []
            return out
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lon == 0 and lat == 0):
            continue
        at = (ft or {}).get("attributes") or {}
        addr = {k: v for k, v in at.items() if k in addr_like and v not in (None, "")}
        out["rows"].append({"addr_fields": addr, "lon": lon, "lat": lat,
                            "lon_raw": lon_raw, "lat_raw": lat_raw,
                            "geom_type": gt, "row_index": len(out["rows"])})
        if len(out["rows"]) >= TARGET:
            break
    if len(out["rows"]) >= TARGET:
        out["status"] = "ok"
    elif out["rows"]:
        out["status"] = "partial"
        out["reason"] = f"features_with_geometry={len(out['rows'])}<{TARGET}" \
                        f" (features_returned={len(feats)}, exceededTransferLimit={out['exceeded']})"
    else:
        out.update(status="unavailable",
                   reason=f"no_geometry_in_response (features={len(feats)}, geometryType={gt or 'none'})")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--states", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(EXTRACT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    layers = [l for l in json.load(open(LAYERS))["layers"] if l["universe"] == "d1"]
    if a.states:
        keep = {s.strip().upper() for s in a.states.split(",") if s.strip()}
        layers = [l for l in layers if (l["state"] or "").upper() in keep]
    todo = []
    for L in layers:
        p = os.path.join(EXTRACT, f"d1_{key_of(L['url'])}.json")
        if not os.path.exists(p):
            todo.append(L)
    if a.limit:
        todo = todo[:a.limit]
    print(json.dumps({"d1_layers": len(layers), "todo": len(todo),
                      "skipped_cached": len(layers) - len(todo)}), flush=True)
    t0 = time.time()
    done = [0]
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def work(L):
        p = os.path.join(EXTRACT, f"d1_{key_of(L['url'])}.json")
        try:
            rec = probe(L)
        except Exception as e:
            rec = {"layer_id": L["layer_id"], "url": L["url"], "state": L["state"],
                   "universe": "d1", "provider": L["provider"], "rows": [],
                   "status": "unavailable", "reason": f"worker_exc: {type(e).__name__}: {e}",
                   "http_code": None, "attempts": 0}
        if rec.get("status") == "unavailable" and rec.get("reason", "").startswith("exhausted"):
            return L["url"], rec   # 不落盘的临时失败，下一轮还能重试
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, p)
        return L["url"], rec

    tally = defaultdict(int)
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(work, L) for L in todo]
        for fu in as_completed(futs):
            try:
                u, rec = fu.result()
            except Exception:
                tally["worker_error"] += 1
                continue
            tally[rec.get("status", "?")] += 1
            done[0] += 1
            if done[0] % 200 == 0:
                el = time.time() - t0
                print(json.dumps({"done": done[0], "of": len(todo), "tally": dict(tally),
                                  "elapsed_s": round(el), "rate_per_min": round(done[0] / el * 60)}),
                      flush=True)
    print(json.dumps({"finished": done[0], "tally": dict(tally),
                      "elapsed_s": round(time.time() - t0)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
