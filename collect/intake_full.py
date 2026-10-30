#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量 intake（一次盘点）—— 2,364 层 → 四表 + 逐层账 → 三张实体台账 → 基线/页面草案

边界（2026-10-30）：
  · 只读三仓已发布资产；不访问上游；不占 GitHub runner（本机跑）
  · 逐层流式：一个单元包读完就丢（tempfile 自删），不落中间大文件
  · **不静默丢行**：每层 rows_total/read/各表/reject/unlocated 全部落账，并对账

三个阶段：
  tables   逐层跑（可并发、可续跑）→ dist/intake-full/layers/<layer>/<table>.<layer>.ndjson.gz + ledger.json
  build    把 addr / aux_addr_nohouse 灌进 SQLite → entity_street / entity_zip / entity_city
  pages    指标 + 分档 + pages.csv 草案（前 10 万行进仓库，全量留本机）

用法：
  python3 collect/intake_full.py tables --concurrency 6
  python3 collect/intake_full.py tables --layers 5 --limit 2000     # 灰度
  python3 collect/intake_full.py build
  python3 collect/intake_full.py pages
  python3 collect/intake_full.py all --concurrency 6
"""
from __future__ import annotations

import argparse
import csv
import glob
import gzip
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))

import intake_33 as I33                          # noqa: E402
import field_map_v2 as FMV2                      # noqa: E402

FMAP_F = os.path.join(ROOT, "schema", "field-map-v2.json")
PLAN_F = os.path.join(HERE, "layer_plan.csv")
OUT_DEFAULT = os.path.join(ROOT, "dist", "intake-full")
TABLES = ("addr", "aux_parcel", "aux_street", "aux_addr_nohouse", "reject")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def up(v) -> str:
    return re.sub(r"\s+", " ", str(v)).strip().upper()


_FMAP = None


def fmap() -> dict:
    global _FMAP
    if _FMAP is None:
        with open(FMAP_F, encoding="utf-8") as f:
            _FMAP = json.load(f)
    return _FMAP


SNAPSHOT_F = ""


class Snapshot:
    """一次性 release 快照：tag → 资产名列表。

    为什么不在每层里 `gh release view`：全量 2,364 层 × 最多 5 个 tag 候选 = 上万次 API，
    必然撞 5,000 次/小时的配额（撞了以后 gh 返回空，看起来像「这层没资产」，会静默少采）。
    快照一次几十页，落盘复用，缺 tag 的层直接判 no_assets，不猜、不误伤。
    """

    def __init__(self, path: str, refresh: bool = False):
        self.path = path
        self.map = {}
        self.tags = set()
        if os.path.exists(path) and not refresh:
            try:
                d = json.load(open(path, encoding="utf-8"))
                self.map = d.get("map") or {}
                self.at = d.get("at")
            except Exception:                        # noqa: BLE001
                self.map = {}
        self.at = getattr(self, "at", None)
        if not self.map:
            self.fetch()

    def fetch(self) -> None:
        import subprocess
        repo = I33.REPO
        self.map = {}
        for page in range(1, 101):
            r = subprocess.run(["gh", "api", "repos/%s/releases?per_page=100&page=%d" % (repo, page)],
                               capture_output=True, text=True)
            try:
                batch = json.loads(r.stdout or "[]")
            except Exception:                        # noqa: BLE001
                batch = []
            if not batch:
                break
            for rel in batch:
                tag = rel.get("tag_name")
                if tag:
                    self.map[tag] = [{"n": a.get("name"), "u": a.get("url"),
                                      "b": a.get("browser_download_url"),
                                      "s": a.get("size")}
                                     for a in (rel.get("assets") or [])]
            if len(batch) < 100:
                break
        self.at = now()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"at": self.at, "map": self.map}, f, ensure_ascii=False)
        print("release 快照：%d 个 tag" % len(self.map), flush=True)

    def tag_of(self, lid: str) -> tuple:
        """按 TAG_CANDS 顺序找 tag → (tag, 资产字典列表[{n,u,s}])；找不到返回 (None, [])。"""
        for cand in ("collect-step10-", "collect-step04-", "collect-step05-", "collect-step07-",
                     "collect-step03-"):
            t = cand + lid
            if t in self.map:
                return t, self.map[t]
        return None, []


_SNAP = None


def snapshot() -> Snapshot:
    global _SNAP
    if _SNAP is None:
        _SNAP = Snapshot(SNAPSHOT_F or os.path.join(OUT_DEFAULT, "release-index.json"))
    return _SNAP


def declared_map() -> dict:
    """计划期声明行数（layer_plan.csv 的 row_count）—— 不花 API、不下载 checkpoint。"""
    m = {}
    if os.path.exists(PLAN_F):
        for r in csv.DictReader(open(PLAN_F, encoding="utf-8")):
            lid = (r.get("layer_id") or "").strip()
            if lid:
                try:
                    m[lid] = int(float(r.get("row_count") or 0))
                except Exception:                    # noqa: BLE001
                    m[lid] = None
    return m


# ---------------------------------------------------------------- 台账聚合用的辅助键
def street_norm_key(row: dict) -> str:
    """街道归一化键：**复用 field-map 的同一套归一化**（后缀/方向全称化已由 norm_street 做完），
    这里只做「拼成完整街道名 + 大写 + 压空格」，不许另写一套口径。"""
    parts = [row.get("street_pre_dir"), row.get("street_name"),
             row.get("street_post_type"), row.get("street_post_dir")]
    return up(" ".join(str(p) for p in parts if p))


def house_num_int(v):
    if v is None:
        return None
    m = re.match(r"\s*(\d+)", str(v))
    return int(m.group(1)) if m else None


def extra_keys(row: dict) -> dict:
    return {"_street_norm": street_norm_key(row),
            "_house_num": house_num_int(row.get("house_number")),
            "_src": source_bucket(row.get("src_kind"), row.get("src_layer_url") or "")}


def source_bucket(kind: str, url: str) -> str:
    """来源桶：NAD / NG911 / OA / PARCEL / AGOL（只用于 sources[] 展示，不改任何判据）。"""
    u = (url or "").lower()
    if kind == "parcel_situs":
        return "PARCEL"
    if "ng911" in u or "911" in u:
        return "NG911"
    if "national_address_database" in u or "_nad" in u or "nad_" in u:
        return "NAD"
    if "openaddress" in u or "oa_" in u:
        return "OA"
    return "AGOL"


# ---------------------------------------------------------------- 阶段一：逐层
def process_layer(job) -> dict:
    lid, outdir, limit = job
    ldir = os.path.join(outdir, "layers", lid)
    os.makedirs(ldir, exist_ok=True)
    ledf = os.path.join(ldir, "ledger.json")
    if os.path.exists(ledf) and not limit:
        try:
            old = json.load(open(ledf, encoding="utf-8"))
            if old.get("status") == "ok":
                return old
        except Exception:                            # noqa: BLE001
            pass
    t0 = time.time()
    fm = fmap()
    dec = declared_map().get(lid)
    tag, names = snapshot().tag_of(lid)
    if not tag:
        led = {"layer": lid, "status": "no_assets", "err": "release 快照里没有该层",
               "rows_total": dec, "read": 0, "unlocated": 0,
               "tables": {k: 0 for k in TABLES}, "dropped_reason": {}, "geo_missing": 0,
               "with_number": 0, "without_number": 0, "declared_hint": dec,
               "elapsed_s": 0.0, "at": now()}
        with open(ledf, "w", encoding="utf-8") as f:
            json.dump(led, f, ensure_ascii=False, indent=1)
        return led
    try:
        led = I33.run_layer(lid, fm, ldir, limit=limit, compress=True,
                            declared_hint=dec, extra_keys=extra_keys,
                            tag_hint=tag, assets_hint=names, write_reject=False)
        led["status"] = "ok"
    except SystemExit as e:                          # 找不到 Release = 本层还没采
        led = {"layer": lid, "status": "no_assets", "err": str(e)[:160], "rows_total": dec,
               "read": 0, "unlocated": 0, "tables": {k: 0 for k in TABLES},
               "dropped_reason": {}, "geo_missing": 0, "with_number": 0,
               "without_number": 0, "declared_hint": dec}
    except Exception as e:                           # noqa: BLE001
        led = {"layer": lid, "status": "failed", "err": "%s: %s" % (type(e).__name__, str(e)[:160]),
               "rows_total": dec, "read": 0, "unlocated": 0,
               "tables": {k: 0 for k in TABLES}, "dropped_reason": {}, "geo_missing": 0,
               "with_number": 0, "without_number": 0, "declared_hint": dec}
    led["elapsed_s"] = round(time.time() - t0, 2)
    led["at"] = now()
    with open(ledf, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    return led


def stage_tables(outdir: str, layers: list[str], concurrency: int, limit: int) -> dict:
    jobs = [(lid, outdir, limit) for lid in layers]
    out, t0 = [], time.time()
    if concurrency <= 1:
        for i, j in enumerate(jobs, 1):
            led = process_layer(j)
            out.append(led)
            _log(i, len(jobs), led)
    else:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=concurrency) as ex:
            futs = {ex.submit(process_layer, j): j[0] for j in jobs}
            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    led = fut.result()
                except Exception as e:               # noqa: BLE001
                    led = {"layer": futs[fut], "status": "failed", "err": str(e)[:160],
                           "tables": {k: 0 for k in TABLES}, "rows_total": None, "read": 0,
                           "unlocated": 0, "dropped_reason": {}, "geo_missing": 0,
                           "with_number": 0, "without_number": 0}
                out.append(led)
                _log(i, len(jobs), led)
    wall = round(time.time() - t0, 1)
    agg = summarise(out)
    agg.update({"wall_s": wall, "concurrency": concurrency, "at": now(),
                "rows_per_s": round(agg["read"] / max(1e-9, wall), 1),
                "peak_rss_mb": _peak_rss_mb()})
    _dump(os.path.join(outdir, "intake-progress.json"), agg)
    print(json.dumps({k: agg[k] for k in ("layers_n", "rows_total", "read", "tables",
                                          "wall_s", "rows_per_s")}, ensure_ascii=False))
    return agg


def _log(i: int, n: int, led: dict) -> None:
    t = led.get("tables") or {}
    print("[%d/%d] %-46s %-10s read=%-9d addr=%-8d parcel=%-8d nohouse=%-7d rej=%-6d %s"
          % (i, n, str(led.get("layer"))[:46], led.get("status"), led.get("read") or 0,
             t.get("addr") or 0, t.get("aux_parcel") or 0, t.get("aux_addr_nohouse") or 0,
             t.get("reject") or 0, led.get("err") or ""), flush=True)


def summarise(leds: list[dict]) -> dict:
    tbl = {k: 0 for k in TABLES}
    st = {}
    for l in leds:
        st[l.get("status")] = st.get(l.get("status"), 0) + 1
        for k in TABLES:
            tbl[k] += ((l.get("tables") or {}).get(k) or 0)
    read = sum(l.get("read") or 0 for l in leds)
    rt = sum(l.get("rows_total") or 0 for l in leds)
    # ★ 对账必须**逐层**闭合，不能只看全局合计：某层漏 1 行、另一层多 1 行，
    #   合计照样「闭合」—— 那就是静默丢行。所以逐层算，并把不闭合的层点名列出来。
    unreconciled = []
    for l in leds:
        if l.get("status") != "ok":
            continue
        if (l.get("read") or 0) != sum((l.get("tables") or {}).get(k, 0) for k in TABLES):
            unreconciled.append(l.get("layer"))
    short = [l.get("layer") for l in leds
             if l.get("rows_total") is not None and (l.get("read") or 0) != l.get("rows_total")
             and l.get("status") == "ok"]
    return {"layers_n": len(leds), "layers_by_status": st, "rows_total": rt, "read": read,
            "tables": tbl, "unlocated": sum(l.get("unlocated") or 0 for l in leds),
            "geo_missing": sum(l.get("geo_missing") or 0 for l in leds),
            "with_number": sum(l.get("with_number") or 0 for l in leds),
            "without_number": sum(l.get("without_number") or 0 for l in leds),
            "reconcile_ok": not unreconciled and tbl["addr"] + tbl["aux_parcel"] +
                            tbl["aux_street"] + tbl["aux_addr_nohouse"] + tbl["reject"] == read,
            "layers_unreconciled": unreconciled,
            "layers_read_ne_declared": len(short),
            "read_equals_declared": read == rt}


def _peak_rss_mb() -> float:
    """本进程（含子进程 wait 未计入）峰值 RSS，给「能否再跑一遍增量」做依据。"""
    try:
        import resource
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        c = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        return round(max(r, c) / 1024.0, 1)          # KB → MB
    except Exception:                                # noqa: BLE001
        return 0.0


def _dump(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 阶段二：台账
SCHEMA = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
PRAGMA temp_store = FILE;
PRAGMA cache_size = -1000000;

CREATE TABLE addr (
  addr_id TEXT, state TEXT, zip5 TEXT, street_norm TEXT, house_num INTEGER,
  street_name TEXT, postal_city TEXT, municipal_city TEXT, county_fips TEXT,
  lat REAL, lon REAL, src TEXT, layer TEXT, addr_type TEXT, has_unit INTEGER);
CREATE TABLE nohouse (
  state TEXT, zip5 TEXT, street_norm TEXT, street_name TEXT, postal_city TEXT,
  municipal_city TEXT, county_fips TEXT, lat REAL, lon REAL, src TEXT, layer TEXT);
"""


def _iter_gz_rows(path: str):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                yield json.loads(ln)


def stage_build(outdir: str, dbpath: str, limit_layers: int = 0) -> dict:
    if os.path.exists(dbpath):
        os.unlink(dbpath)
    con = sqlite3.connect(dbpath)
    con.executescript(SCHEMA)
    dirs = sorted(glob.glob(os.path.join(outdir, "layers", "*")))
    if limit_layers:
        dirs = dirs[:limit_layers]
    t0 = time.time()
    n_addr = n_no = 0
    for d in dirs:
        lid = os.path.basename(d)
        a = glob.glob(os.path.join(d, "addr.*.ndjson.gz"))
        if a:
            batch = []
            for r in _iter_gz_rows(a[0]):
                batch.append((r.get("addr_id"), r.get("state_abbr"), r.get("zip5"),
                              r.get("_street_norm"), r.get("_house_num"), r.get("street_name"),
                              r.get("postal_city"), r.get("municipal_city"), r.get("county_fips"),
                              r.get("latitude"), r.get("longitude"), r.get("_src"), lid,
                              r.get("addr_type"), 1 if r.get("unit") else 0))
                if len(batch) >= 20000:
                    con.executemany("INSERT INTO addr VALUES (%s)" % ",".join("?" * 15), batch)
                    n_addr += len(batch)
                    batch = []
            if batch:
                con.executemany("INSERT INTO addr VALUES (%s)" % ",".join("?" * 15), batch)
                n_addr += len(batch)
                batch = []
        h = glob.glob(os.path.join(d, "aux_addr_nohouse.*.ndjson.gz"))
        if h:
            batch = []
            for r in _iter_gz_rows(h[0]):
                batch.append((r.get("state_abbr"), r.get("zip5"), r.get("_street_norm"),
                              r.get("street_name"), r.get("postal_city"),
                              r.get("municipal_city"), r.get("county_fips"), r.get("latitude"),
                              r.get("longitude"), r.get("_src"), lid))
                if len(batch) >= 20000:
                    con.executemany("INSERT INTO nohouse VALUES (%s)" % ",".join("?" * 11), batch)
                    n_no += len(batch)
                    batch = []
            if batch:
                con.executemany("INSERT INTO nohouse VALUES (%s)" % ",".join("?" * 11), batch)
                n_no += len(batch)
        con.commit()
    load_s = round(time.time() - t0, 1)
    print("装入 addr=%d nohouse=%d 用时 %.0fs" % (n_addr, n_no, load_s), flush=True)

    t1 = time.time()
    # ---- entity_street：主键 (state, zip5, street_norm)
    con.executescript("""
    DROP TABLE IF EXISTS entity_street;
    CREATE TABLE entity_street AS
    SELECT a.state AS state_abbr, a.zip5, a.street_norm,
           MIN(a.street_name) AS street_name_display,
           MIN(a.house_num)  AS house_min,
           MAX(a.house_num)  AS house_max,
           COUNT(*)          AS n_addr,
           COUNT(DISTINCT a.postal_city) AS n_cities,
           AVG(a.lat) AS lat_avg, AVG(a.lon) AS lon_avg,
           GROUP_CONCAT(DISTINCT a.src)   AS sources,
           GROUP_CONCAT(DISTINCT a.layer) AS layer_ids
    FROM addr a
    WHERE a.street_norm IS NOT NULL AND a.street_norm <> ''
    GROUP BY a.state, a.zip5, a.street_norm;
    """)
    print("entity_street 建好 %.0fs" % (time.time() - t1), flush=True)

    # ---- 坐标中位（分两次窗口取真正的中位，不猜、不拿平均当中位）
    # 地理键只用 (state, street_norm)：带 zip 会让「没 zip 的行」拿不到坐标中位，
    # 实测 60 层样本里 zip 缺失占 25%，那样 streets 的 geo 非空率会被 zip 缺失拖死。
    t2 = time.time()
    for col in ("lat", "lon"):
        con.executescript("""
        DROP TABLE IF EXISTS med_%(c)s;
        CREATE TABLE med_%(c)s AS
        SELECT state, street_norm, AVG(v) AS %(c)s_med FROM (
          SELECT state, street_norm, %(c)s AS v,
                 ROW_NUMBER() OVER (PARTITION BY state, street_norm ORDER BY %(c)s) rn,
                 COUNT(*)     OVER (PARTITION BY state, street_norm) c
          FROM addr WHERE %(c)s IS NOT NULL AND street_norm <> '')
        WHERE rn IN ((c + 1) / 2, (c + 2) / 2)
        GROUP BY 1, 2;
        CREATE INDEX ix_med_%(c)s ON med_%(c)s(state, street_norm);
        """ % {"c": col})
        print("  %s 中位 %.0fs" % (col, time.time() - t2), flush=True)
        t2 = time.time()
    con.executescript("""
    ALTER TABLE entity_street ADD COLUMN lat_med REAL;
    ALTER TABLE entity_street ADD COLUMN lon_med REAL;
    UPDATE entity_street SET
      lat_med = (SELECT lat_med FROM med_lat m WHERE m.state=state_abbr AND m.street_norm=street_norm),
      lon_med = (SELECT lon_med FROM med_lon m WHERE m.state=state_abbr AND m.street_norm=street_norm);
    """)

    # ---- entity_zip：主键 zip5
    con.executescript("""
    DROP TABLE IF EXISTS zip_city;
    CREATE TABLE zip_city AS
    SELECT zip5, postal_city, COUNT(*) c FROM addr
    WHERE zip5 <> '' AND postal_city IS NOT NULL GROUP BY 1, 2;
    DROP TABLE IF EXISTS zip_county;
    CREATE TABLE zip_county AS
    SELECT zip5, county_fips, COUNT(*) c FROM addr
    WHERE zip5 <> '' AND county_fips IS NOT NULL GROUP BY 1, 2;
    DROP TABLE IF EXISTS entity_zip;
    CREATE TABLE entity_zip AS
    SELECT z.zip5,
      (SELECT postal_city FROM zip_city y WHERE y.zip5=z.zip5 ORDER BY y.c DESC LIMIT 1) AS postal_city,
      (SELECT county_fips FROM zip_county y WHERE y.zip5=z.zip5 ORDER BY y.c DESC LIMIT 1) AS county_fips,
      (SELECT GROUP_CONCAT(county_fips) FROM zip_county y WHERE y.zip5=z.zip5) AS county_fips_all,
      COUNT(DISTINCT z.street_norm) AS n_streets,
      COUNT(*) AS n_addr
    FROM addr z WHERE z.zip5 <> '' AND z.zip5 IS NOT NULL GROUP BY z.zip5;
    """)
    print("entity_zip 建好 %.0fs" % (time.time() - t1), flush=True)

    # ---- entity_city：主键 (state, city_slug)
    con.executescript("""
    DROP TABLE IF EXISTS entity_city;
    CREATE TABLE entity_city AS
    SELECT state, city_slug, MIN(postal_city) AS city_display,
           GROUP_CONCAT(DISTINCT zip5) AS zip_list,
           COUNT(DISTINCT street_norm) AS n_streets, COUNT(*) AS n_addr
    FROM (SELECT state, LOWER(REPLACE(postal_city, ' ', '-')) AS city_slug, postal_city, zip5,
                 street_norm
          FROM addr WHERE postal_city IS NOT NULL AND postal_city <> '' AND street_norm <> '')
    GROUP BY state, city_slug;
    """)
    build_s = round(time.time() - t1, 1)
    stats = {t: con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
             for t in ("addr", "nohouse", "entity_street", "entity_zip", "entity_city")}
    con.commit()
    con.close()
    res = {"at": now(), "db": dbpath, "db_mb": round(os.path.getsize(dbpath) / 1e6, 1),
           "loaded": {"addr": n_addr, "nohouse": n_no}, "load_s": load_s,
           "aggregate_s": build_s, "counts": stats}
    print(json.dumps(res, ensure_ascii=False))
    return res


# ---------------------------------------------------------------- 阶段三：指标 + 页面
def stage_pages(outdir: str, dbpath: str, repo_dir: str) -> dict:
    con = sqlite3.connect(dbpath)
    con.row_factory = sqlite3.Row
    q = lambda s: [dict(r) for r in con.execute(s)]      # noqa: E731

    street = q("""SELECT state_abbr, zip5, street_norm, street_name_display, house_min, house_max,
                         n_addr, lat_med, lon_med, lat_avg, lon_avg, sources, layer_ids,
                         (lat_med IS NOT NULL) AS has_geo,
                         (zip5 IS NOT NULL AND zip5 <> '') AS has_zip,
                         n_cities
                  FROM entity_street""")
    zips = q("""SELECT zip5, postal_city, county_fips, county_fips_all, n_streets, n_addr,
                       (postal_city IS NOT NULL) AS has_city,
                       (county_fips IS NOT NULL) AS has_county FROM entity_zip""")
    cities = q("""SELECT state, city_slug, city_display, zip_list, n_streets, n_addr
                  FROM entity_city""")
    con.close()

    # ---- 非空率（决定页面质量）
    def rate(rows, key):
        return round(100.0 * sum(1 for r in rows if r.get(key)) / max(1, len(rows)), 2)
    zip_county = {z["zip5"]: z["county_fips"] for z in zips if z.get("county_fips")}
    for r in street:
        r["has_county"] = bool(zip_county.get(r["zip5"] or ""))
    rates = {
        "street": {"n": len(street), "street_name": rate(street, "street_name_display"),
                   "zip5": rate(street, "has_zip"), "geo": rate(street, "has_geo"),
                   "county(由 zip 带出)": rate(street, "has_county"), "house_range": rate(
                       [r for r in street if r["house_min"] is not None], "house_min")},
        "zip": {"n": len(zips), "postal_city": rate(zips, "has_city"),
                "county_fips": rate(zips, "has_county"), "streets": 100.0},
        "city": {"n": len(cities), "zip_list": rate(cities, "zip_list"),
                 "streets": 100.0},
    }

    # ---- quality_score（0~100，公式写进文档，不搞黑箱）
    import math
    for r in street:
        s = 0.0
        s += 30 if r["has_geo"] else 0
        s += 20 if r["has_zip"] else 0
        s += 15 if (r["n_cities"] or 0) >= 1 else 0
        s += min(35.0, 35.0 * math.log10(max(1, r["n_addr"])) / 2.0)     # 100 条 → 满分
        r["quality_score"] = round(s, 1)
    for r in zips:
        s = 0.0
        s += 40 if r["has_city"] else 0
        s += 20 if r["has_county"] else 0
        s += min(40.0, 40.0 * math.log10(max(1, r["n_streets"])) / 2.0)  # 100 条街 → 满分
        r["quality_score"] = round(s, 1)
    for r in cities:
        s = 0.0
        s += 40 if r["zip_list"] else 0
        s += min(30.0, 30.0 * math.log10(max(1, r["n_streets"])) / 2.0)
        s += min(30.0, 30.0 * math.log10(max(1, r["n_addr"])) / 3.0)
        r["quality_score"] = round(s, 1)

    def band(x):
        return "live" if x >= 80 else ("fill" if x >= 50 else "no_page")

    rows = []
    for r in zips:
        r["level"], r["sitemap_batch"] = "L3", 1
        slug_city = (r["postal_city"] or "").lower().replace(" ", "-")
        r["slug"] = "%s/%s" % ("zip", r["zip5"]) if not slug_city else "zip/%s-%s" % (r["zip5"], slug_city)
        r["entity_key"] = r["zip5"]
        rows.append(r)
    for r in street:
        r["level"], r["sitemap_batch"] = "L4", 2
        r["slug"] = "%s/%s/%s" % ((r["state_abbr"] or "xx").lower(), r["zip5"] or "nozip",
                                  re.sub(r"[^a-z0-9]+", "-", (r["street_norm"] or "").lower()).strip("-"))
        r["entity_key"] = "%s|%s|%s" % (r["state_abbr"], r["zip5"], r["street_norm"])
        rows.append(r)
    for r in cities:
        r["level"], r["sitemap_batch"] = "L2", 3
        r["slug"] = "%s/%s" % ((r["state"] or "xx").lower(), r["city_slug"])
        r["entity_key"] = "%s|%s" % (r["state"], r["city_slug"])
        rows.append(r)

    bands = {}
    for r in rows:
        b = (r["level"], band(r["quality_score"]))
        bands[b] = bands.get(b, 0) + 1
    live = [r for r in rows if band(r["quality_score"]) == "live"]
    live.sort(key=lambda r: (r["sitemap_batch"], -r["quality_score"]))
    full = os.path.join(outdir, "pages-full.csv")
    os.makedirs(outdir, exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "slug", "entity_key", "quality_score", "sitemap_batch"])
        for r in live:
            w.writerow([r["level"], r["slug"], r["entity_key"], r["quality_score"], r["sitemap_batch"]])
    repo_pages = os.path.join(ROOT, "pages.csv")
    with open(repo_pages, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["level", "slug", "entity_key", "quality_score", "sitemap_batch"])
        for r in live[:100000]:
            w.writerow([r["level"], r["slug"], r["entity_key"], r["quality_score"], r["sitemap_batch"]])

    res = {"at": now(), "counts": {"street": len(street), "zip": len(zips), "city": len(cities)},
           "rates": rates,
           "bands": {"%s/%s" % k: v for k, v in sorted(bands.items())},
           "pages_total": len(live), "pages_in_repo": min(100000, len(live)),
           "pages_by_level": {lv: sum(1 for r in live if r["level"] == lv) for lv in ("L2", "L3", "L4")},
           "quality_thresholds": {"live": 80, "fill": 50},
           "pages_full": full, "pages_repo": repo_pages}
    _dump(os.path.join(outdir, "entity-baseline.json"), res)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return res


DOC_TPL = """# 实体台账 + 页面基线（一次盘点 · {date}）

> 数据来源：三仓已发布 Release 资产（只读），逐层流式处理，**不落中间大文件**。
> 口径全部来自 `collect/intake_full.py` 的实现；本文数字由 `--doc` 从
> `dist/intake-full/entity-baseline.json` 直接渲染，**不许手抄**。

## 一、四表与对账

| 项 | 行数 |
|---|---|
| 层数 | {layers_n}（{status_line}） |
| 读入行数 | {read} |
| `addr`（点层过五道门禁） | {addr} |
| `aux_parcel`（宗地层，**绝不进 addr**） | {aux_parcel} |
| `aux_street`（线层；本轮线层核定不采 → 0） | {aux_street} |
| `aux_addr_nohouse`（有点无门牌） | {aux_nohouse} |
| `reject`（四表都放不下） | {reject} |
| 对账 `read = Σ四表 + reject` | {reconcile} |

硬约束（测试卡死，不是靠跑完再查）：
`addr` 行零缺 `house_number`/`street_name`；`addr_id` 是裸 40 位 sha1、
`aux_key` 一律带 `p:`/`s:`/`n:` 前缀 → **两表主键结构上不可能相交**。

## 二、三张实体台账（主键去重，不按源重复累加）

| 台账 | 实体数 | 主键 |
|---|---|---|
| `entity_street` | {street_n} | `(state_abbr, zip5, street_norm)` |
| `entity_zip` | {zip_n} | `zip5` |
| `entity_city` | {city_n} | `(state_abbr, city_slug)` |

`street_norm` 归一化**复用 field-map 同一套**（后缀/方向全称化 + 大写 + 压空格），
没有第二套口径。

### 字段非空率（决定页面能写到什么程度）

| 层级 | 字段 | 非空率 |
|---|---|---|
{rate_table}

## 三、页面草案（`pages.csv`）

质量分公式（写死，不搞黑箱）：
- street：`geo 30 + zip5 20 + city 15 + min(35, 35·log10(n_addr)/2)`
- zip：`postal_city 40 + county_fips 20 + min(40, 40·log10(n_streets)/2)`
- city：`zip_list 40 + min(30, 30·log10(n_streets)/2) + min(30, 30·log10(n_addr)/3)`

分档：`live ≥ 80`（可立刻上线）/ `fill 50~80`（需补数据）/ `no_page < 50`（**不建页**）。

| 层级 × 档 | 实体数 |
|---|---|
{band_table}

入库 `pages.csv`：**{pages_in_repo} 行**（前 10 万，够验证）；本机全量 {pages_total} 行。
sitemap 批次按质量降序：L3(zip) → L4(street) → L2(city)。

## 四、耗时与资源（评估能否再跑增量）

| 项 | 值 |
|---|---|
| 逐层处理耗时 | {wall_s}s（{concurrency} 并发） |
| 吞吐 | {rows_per_s} 行/秒 |
| 峰值内存 | {peak_rss_mb} MB |
| 装载 + 聚合（SQLite） | {load_s}s + {aggregate_s}s |
| 增量可行性 | 逐层台账 `status=ok` 即跳过 → 再跑一遍只补新增/失败层 |
"""


def render_doc(res: dict, progress: dict, path: str) -> str:
    rates, bands = res["rates"], res["bands"]

    def line(level, key, label=""):
        v = rates.get(level, {}).get(key)
        return "| %s | `%s`%s | %s |" % (level, key, label,
                                         "-" if v is None else "%.2f%%" % v)

    rate_table = "\n".join([
        line("street", "street_name"), line("street", "zip5"), line("street", "geo"),
        line("street", "county(由 zip 带出)"), line("street", "house_range"),
        line("zip", "postal_city"), line("zip", "county_fips"),
        line("city", "zip_list")])
    band_table = "\n".join("| %s | %d |" % (k, v) for k, v in sorted(bands.items()))
    st = progress.get("layers_by_status") or {}
    body = DOC_TPL.format(
        date=now()[:10],
        layers_n=progress.get("layers_n", 0),
        status_line="、".join("%s %d" % (k, v) for k, v in sorted(st.items())) or "-",
        read=f"{progress.get('read', 0):,}",
        addr=f"{(progress.get('tables') or {}).get('addr', 0):,}",
        aux_parcel=f"{(progress.get('tables') or {}).get('aux_parcel', 0):,}",
        aux_street=f"{(progress.get('tables') or {}).get('aux_street', 0):,}",
        aux_nohouse=f"{(progress.get('tables') or {}).get('aux_addr_nohouse', 0):,}",
        reject=f"{(progress.get('tables') or {}).get('reject', 0):,}",
        reconcile="✅ 闭合" if progress.get("reconcile_ok") else "❌ 有层不闭合（见 progress.json）",
        street_n=f"{res['counts']['street']:,}",
        zip_n=f"{res['counts']['zip']:,}",
        city_n=f"{res['counts']['city']:,}",
        rate_table=rate_table, band_table=band_table,
        pages_in_repo=f"{res['pages_in_repo']:,}", pages_total=f"{res['pages_total']:,}",
        wall_s=progress.get("wall_s", "-"), concurrency=progress.get("concurrency", "-"),
        rows_per_s=progress.get("rows_per_s", "-"),
        peak_rss_mb=progress.get("peak_rss_mb", "-"),
        load_s=res.get("load_s", "-"), aggregate_s=res.get("aggregate_s", "-"))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(body)
    return body


# ---------------------------------------------------------------- 入口
def all_layers() -> list[str]:
    return list(fmap()["layers"].keys())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["tables", "build", "pages", "all"])
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--db", default="")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--layers", type=int, default=0, help="只跑前 N 层（灰度用）")
    ap.add_argument("--limit", type=int, default=0, help="每层只读前 N 行（灰度用）")
    ap.add_argument("--refresh-index", action="store_true", help="重建 release 快照")
    ap.add_argument("--doc", default=os.path.join(ROOT, "docs", "ENTITY-BASELINE-2026-10-30.md"))
    a = ap.parse_args()
    global SNAPSHOT_F
    SNAPSHOT_F = os.path.join(a.out, "release-index.json")
    if a.stage in ("tables", "all"):
        snapshot()
    db = a.db or os.path.join(a.out, "index.sqlite")
    layers = all_layers()
    if a.layers:
        layers = layers[:a.layers]
    if a.stage in ("tables", "all"):
        stage_tables(a.out, layers, a.concurrency, a.limit)
    if a.stage in ("build", "all"):
        stage_build(a.out, db, limit_layers=a.layers)
    if a.stage in ("pages", "all"):
        res = stage_pages(a.out, db, ROOT)
        prog = {}
        pf = os.path.join(a.out, "intake-progress.json")
        if os.path.exists(pf):
            prog = json.load(open(pf, encoding="utf-8"))
        if a.doc and prog:
            render_doc(res, prog, a.doc)
            print("文档已渲染：%s" % a.doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
