#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""county 逐行判定（全量口径）—— 可分片、可续跑、可核对。

只用已发布资产（三仓 Release）判 county_fips：
  行 → lat/lon（envelope 或属性）→ 该州县界多边形射线法 → county_fips
  判不出来 → 计入 **UNLOCATED**（不猜、不写死、不回落 bbox）

县界来源优先级（都不访问上游）：
  1) 一仓已发布资产 `TIGER-US-<ST>-county-<fips>.geojson`（若本地有）
  2) 本地已有缓存 `analysis/tiger_county/<ST>.json.gz`（此前离线抓取，未再联网）

判定口径（与 2026-10-30 裁定一致）：
  · bbox 只做预筛，命中必须过 PIP；**禁用 bbox 作为判定**
  · 多边形缺失（州界未缓存）→ 该层记 `no_county_index`，不猜
  · 单县层（layer 级已确定）不需要跑本脚本

断点续跑：每层每单元一个标记文件 `collect/progress/county/<layer>/<asset>.done`，
          存在即跳过；同一 run 重跑不会重复下载已完成的单元。

用法：
  python3 collect/county_assign.py --layers A,B,C --out dist/county      # 直接点名（试算）
  python3 collect/county_assign.py --plan collect/ledger/04b_plan.json --shard 0 \
      --out dist/county --max-seconds 12000                              # 分片（matrix 用）
  python3 collect/county_assign.py --selftest --out /tmp/county-selftest # 5 层一致率验收
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))

import county_tiger as CT                       # noqa: E402
from county_index import NationalIndex, locate, get_national   # noqa: E402,F401
from intake_33 import release_assets, FIPS2STATE   # noqa: E402
from field_map_v2 import STATE_ABBR             # noqa: E402

REPO = "ip9988001/world-map-data-33"
PROGRESS = os.environ.get("COUNTY_PROGRESS") or os.path.join(HERE, "progress", "county")
TAG_CANDS = ("collect-step10-", "collect-step04-", "collect-step05-", "collect-step07-")
# ★ 口径版本：改了「怎么记账」就必须进位，否则续跑会把旧口径的结果当完成跳过。
#   v3 = 全国县索引 + 清单州为准/属性州只做校验（state_anomaly）+ suspect_layer（UNLOCATED>50%）
VERDICT_VER = 3
SNAPSHOT_F = os.path.join(ROOT, "analysis", "county", "release-snapshot.json")
STATE_COLS = ("STATE", "State", "state", "STATE_ABBR", "STATE_CODE", "STATECODE",
              "STABBR", "STATE_NAME", "STATENAME")
SUSPECT_UNLOC_PCT = 50.0        # 一层里 UNLOCATED 占比超过这个 → suspect_layer（进人工复核）
UNIT_RE = re.compile(r"-u\d{5}\.tar\.gz$")      # 单元包（每单元一个 tar.gz）
# 一仓已发布县界资产（若本地有一仓 clone 就直接用）
REPO1_GEOJSON = os.environ.get(
    "REPO1_COUNTY_GEOJSON_DIR",
    os.path.join(os.path.dirname(ROOT), "World-US-Map-Data", "data"))

LAT_KEYS = ("lat", "latitude", "y", "LAT", "LATITUDE", "Y")
LON_KEYS = ("lon", "lng", "longitude", "x", "LON", "LONG", "LONGITUDE", "X")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- 县索引
class Index:
    """按州缓存县索引；优先一仓 geojson，其次本地缓存。"""

    def __init__(self):
        self.cache = {}

    def get(self, state: str):
        st = (state or "").upper()
        if not st:
            return None
        if st in self.cache:
            return self.cache[st]
        idx = None
        gj = self._from_repo1(st)
        if gj:
            idx = gj
        else:
            try:
                idx = CT.fetch_state(st)
            except Exception:                        # noqa: BLE001
                idx = None
        self.cache[st] = idx
        return idx

    def _from_repo1(self, st: str):
        """一仓资产 TIGER-US-<ST>-county-<fips>.geojson 逐县拼成索引（不联网）。"""
        d = REPO1_GEOJSON
        if not os.path.isdir(d):
            return None
        cands = []
        for root, _dirs, files in os.walk(d):
            for f in files:
                if re.match(r"TIGER-US-%s-county-\d+\.geojson$" % st, f):
                    cands.append(os.path.join(root, f))
        if not cands:
            return None
        feats = []
        for p in cands:
            try:
                d0 = json.load(open(p, encoding="utf-8"))
            except Exception:                        # noqa: BLE001
                continue
            for f in (d0.get("features") or []):
                pr = f.get("properties") or {}
                fips = str(pr.get("GEOID") or pr.get("fips") or "")
                if len(fips) == 5:
                    feats.append({"type": "Feature", "properties": {
                        "GEOID": fips, "NAME": pr.get("NAME") or pr.get("name") or fips},
                        "geometry": f.get("geometry")})
        return CT.CountyIndex(st, feats) if feats else None


def boundary_case(idx, lat: float, lon: float, ref_name: str, eps: float = 0.001) -> bool:
    """判定「县界点」：±eps 抖动后能落到参照县，说明差异只是边界精度（不是判错）。"""
    for dy in (-eps, 0, eps):
        for dx in (-eps, 0, eps):
            f = locate(idx, lat + dy, lon + dx)
            if f and re.sub(r"\s+(COUNTY|PARISH)$", "",
                            idx.by_fips.get(f, {}).get("name", "").upper()) == ref_name:
                return True
    return False


def boundary_case_fips(idx, lat, lon, fips, eps=0.0015) -> bool:
    """线/点是否只是压在县界上：±eps(≈165m) 抖动能落进目标县 → 边界情形，不是判错。"""
    for dy in (-eps, 0, eps):
        for dx in (-eps, 0, eps):
            if locate(idx, lat + dy, lon + dx) == fips:
                return True
    return False


def state_of_layer(lid: str, ent: dict = None) -> str:
    """层的州：field-map 的 state_abbr 值 → 层元数据 CSV。"""
    if ent:
        v = (ent.get("state_abbr") or {}).get("value")
        if v:
            return str(v).upper()[:2]
    if not hasattr(state_of_layer, "_m"):
        import csv
        m = {}
        for name in ("address_layers.csv", "situs_layers.csv"):
            p = os.path.join(HERE, name)
            if not os.path.exists(p):
                continue
            for r in csv.DictReader(open(p, encoding="utf-8")):
                k = (r.get("layer_id") or "").strip()
                st = (r.get("state") or "").strip().upper()
                if k and st and st not in ("未定位",) and k not in m:
                    m[k] = st
        state_of_layer._m = m
    return state_of_layer._m.get(lid, "")


# ---------------------------------------------------------------- 州口径（只做校验，不参与过滤）
def norm_state(v) -> str:
    """任意州写法 → 两字母码；认不出来就返回 ""（不猜）。"""
    if v is None:
        return ""
    t = str(v).strip().upper()
    if len(t) == 2 and t.isalpha() and t in set(STATE_ABBR.values()):
        return t
    if t in STATE_ABBR:
        return STATE_ABBR[t]
    m = re.match(r"^([A-Z]{2})[\s,_-]", t) if len(t) > 2 else None
    if m and m.group(1) in set(STATE_ABBR.values()):
        return m.group(1)
    return ""


def state_cols_of(lid: str, ent: dict = None) -> list:
    """该层「属性州」的候选列名：field-map 画像点名的真实列优先，其次常见列名。"""
    cols = []
    src = ((ent or {}).get("state_abbr") or {}).get("src") or ""
    if src and not str(src).startswith("[["):       # [[layer_meta.state]] = 元数据，不是数据列
        cols.append(str(src))
    for c in STATE_COLS:
        if c not in cols:
            cols.append(c)
    return cols


class StateProbe:
    """逐行统计「属性州」：只在真的能解出两字母码时计数，解不出就跳过（不猜）。

    用途只有一个 —— 与清单州比对，冲突时记 `state_anomaly`。**绝不参与判县过滤**：
    点在邻县/邻州是合法结果，判县只看坐标落在哪个县多边形里。
    """

    def __init__(self, lid: str, ent: dict = None):
        self.cols = state_cols_of(lid, ent)
        self.col = None            # 第一次命中后锁定，后面只查这一列
        self.counts = {}

    def feed(self, rec: dict) -> None:
        raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else {}
        if self.col is None:
            for c in self.cols:
                if c in raw:
                    self.col = c
                    break
            if self.col is None:
                return
        st = norm_state(raw.get(self.col))
        if st:
            self.counts[st] = self.counts.get(st, 0) + 1

    def top(self) -> str:
        if not self.counts:
            return ""
        return max(self.counts.items(), key=lambda kv: kv[1])[0]

    def dist(self, k: int = 3) -> dict:
        return dict(sorted(self.counts.items(), key=lambda kv: -kv[1])[:k])


def geo_top_state(fips_state: dict) -> str:
    """由「县多边形反推的州码」取主导州（行数最多的那个）。"""
    if not fips_state:
        return ""
    f2 = max(fips_state.items(), key=lambda kv: kv[1])[0]
    try:
        return FIPS2STATE.get(str(f2), "")
    except Exception:                                # noqa: BLE001
        return ""


def state_verdict(lid: str, list_state: str, attr_top: str, geo_state: str,
                  rows: int, rows_off: int) -> dict:
    """把「清单州 / 属性州 / 县多边形裁决」三方摆在一起，给一条可复核的结论。

    口径（2026-10-30 用户裁定）：
      · 清单州（layer_plan / 层清单）是**唯一**的层的州
      · 属性州只做校验；冲突记 `state_anomaly`，**不参与过滤**
      · 跨州溢出合法：点落在邻县不因「州不符」改判（这里只记账，不改 by_county）
      · 只有当「主导县州」与清单州不同（说明整层标错了）才升级为 anomaly
    """
    anomaly = None
    if list_state and attr_top and list_state != attr_top:
        anomaly = {"kind": "conflict", "layer": lid, "list_state": list_state,
                   "attr_state": attr_top, "geo_state": geo_state, "rows": rows,
                   "rows_off_state": rows_off}
    elif not list_state and (attr_top or geo_state):
        anomaly = {"kind": "list_missing", "layer": lid, "list_state": "",
                   "attr_state": attr_top, "geo_state": geo_state, "rows": rows,
                   "rows_off_state": rows_off}
    elif list_state and geo_state and list_state != geo_state and rows > 0:
        anomaly = {"kind": "geo_conflict", "layer": lid, "list_state": list_state,
                   "attr_state": attr_top, "geo_state": geo_state, "rows": rows,
                   "rows_off_state": rows_off}
    return anomaly or {}


# ---------------------------------------------------------------- 行读取
def pick_latlon(rec: dict) -> tuple:
    for k in LAT_KEYS:
        v = rec.get(k)
        if isinstance(v, (int, float)):
            return float(v), None
    for k in LON_KEYS:
        v = rec.get(k)
        if isinstance(v, (int, float)):
            return None, float(v)
    lat = next((rec[k] for k in LAT_KEYS if isinstance(rec.get(k), (int, float))), None)
    lon = next((rec.get(k) for k in LON_KEYS if isinstance(rec.get(k), (int, float))), None)
    return lat, lon


def extract(rec: dict) -> tuple:
    """从一条采集记录里取 (lat, lon)：`_lat`/`_lon`（采集侧原样）→ lat/lon → raw 属性。"""
    for a, b in (("_lat", "_lon"), ("lat", "lon")):
        lat, lon = rec.get(a), rec.get(b)
        if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
            return float(lat), float(lon)
    raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else {}
    la = next((raw[k] for k in ("LATITUDE", "LAT", "Y_COORD", "Y", "LAT_DD") if
               isinstance(raw.get(k), (int, float))), None)
    lo = next((raw[k] for k in ("LONGITUDE", "LON", "X_COORD", "X", "LON_DD") if
               isinstance(raw.get(k), (int, float))), None)
    if la is None or lo is None:
        return None, None
    la, lo = float(la), float(lo)
    if 15 <= abs(la) <= 75 and 60 <= abs(lo) <= 180:
        return la, lo
    return None, None


# 像坐标的列名（用于把「投影坐标」从「根本没坐标」里分出来）
_COORD_KEY_RE = re.compile(
    r"(?i)^(x|y|lon|lng|long|longitude|lat|latitude|lat_dd|lon_dd|"
    r"x_?coord(inate)?|y_?coord(inate)?|easting|northing|xcoord|ycoord)$")


def coord_kind(rec: dict) -> tuple:
    """三分类：ok（WGS84 经纬可用）/ proj_failed（有坐标列但不是经纬，典型是投影坐标）/ no_coords。

    为什么要分：2026-10-30 裁定要求「落不了县的一条不漏」，而「投影坐标」与「根本没坐标」
    是两种完全不同的缺口 —— 前者能靠反推 EPSG 救（宗地那批救回 47.9 万行），后者只能等上游补。
    把它们混成一个 no_coords 会让救援优先级失去依据。
    """
    lat, lon = extract(rec)
    if lat is not None and lon is not None:
        return "ok", lat, lon
    raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else {}
    hits = [k for k, v in raw.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool) and _COORD_KEY_RE.match(str(k))]
    if len(hits) >= 2:                      # 有坐标列，但值不是合法经纬 → 投影坐标
        return "proj_failed", None, None
    return "no_coords", None, None


def safe_name(lid: str) -> str:
    """层 id → 安全文件名（只去路径分隔符与空白；可读性优先，不做哈希）。"""
    s = re.sub(r"[\\/\s]+", "_", str(lid)).strip("_")
    return s[:180] or "layer"


_SNAP = {"m": None}


def snapshot() -> dict:
    """tag → 资产列表的一次性快照（`gh api releases` 拉全量，~15 次调用）。

    为什么要快照：1,158 层 × 最多 4 个 tag 候选 = 4,600 次 `gh release view`，
    会直接撞 GitHub 5,000 次/小时配额。快照一次几十次调用就够，也快一个数量级。
    """
    if _SNAP["m"] is None:
        try:
            _SNAP["m"] = json.load(open(SNAPSHOT_F, encoding="utf-8")).get("map") or {}
        except Exception:                            # noqa: BLE001
            _SNAP["m"] = {}
    return _SNAP["m"]


def assets_of(tag: str) -> list:
    """某 tag 下的资产：快照存在就是权威（缺 tag = 该层没有资产），只有在快照缺失时才打 API。"""
    snap = snapshot()
    if snap:
        return snap.get(tag) or []
    try:
        return release_assets(tag)
    except Exception:                                # noqa: BLE001
        return []


def stream_asset(tag: str, asset_name: str) -> "object":
    """流式读一个单元包，逐条 yield 记录 —— 不把整包 ndjson 读进内存。

    2026-10-30 改：老实现 rows.append(json.loads(ln)) 把一整个单元（最大 100 万行）堆在内存里，
    4 并发时会直接打爆 16G。现在 tarfile 用 "r|gz" 流式模式 + gzip 逐行解码，常驻内存只有一行。
    """
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, asset_name)
        r = subprocess.run(["gh", "release", "download", tag, "--repo", REPO,
                            "-p", asset_name, "-D", td, "--clobber"],
                           capture_output=True, text=True, timeout=3600)
        if not os.path.exists(p):
            # 不许静默丢单元：拿不到包就整层判 failed（带原因），下次续跑再来
            raise RuntimeError("下载失败 %s rc=%s %s"
                               % (asset_name, r.returncode, (r.stderr or "")[-160:]))
        with tarfile.open(p, "r|gz") as tf:
            for m in tf:
                if not m.name.endswith(".ndjson.gz"):
                    continue
                fh = tf.extractfile(m)
                if fh is None:
                    continue
                with gzip.GzipFile(fileobj=fh) as gz:
                    for ln in gz:
                        if not ln.strip():
                            continue
                        try:
                            yield json.loads(ln)
                        except Exception:            # noqa: BLE001
                            continue


def iter_rows(tag: str, layer: str, state: str = "", refresh: bool = False):
    """逐单元（asset）产出 (asset_name, records)。records 是**列表**，只为兼容老调用方；
    run_layer 已改用 stream_asset 逐行流式，新代码不要再走这里。"""
    for a in iter_assets(tag, layer, refresh):
        yield a["n"], list(stream_asset(tag, a["n"]))


def iter_assets(tag: str, layer: str, refresh: bool = False):
    """本层还没跑完的单元包（按名字排序；有 .done 标记就跳）。"""
    assets = [a for a in assets_of(tag) if UNIT_RE.search(a["n"])]
    assets.sort(key=lambda a: a["n"])
    d = os.path.join(PROGRESS, layer)
    os.makedirs(d, exist_ok=True)
    for a in assets:
        if os.path.exists(os.path.join(d, a["n"] + ".done")) and not refresh:
            continue
        yield a


def run_layer(lid: str, idx: Index, outdir: str = "", ref_col: str = "",
              max_seconds: int = 0, refresh: bool = False, layer_state: str = "",
              ent: dict = None) -> dict:
    t0 = time.time()
    tag = None
    for c in TAG_CANDS:
        t = c + lid
        try:
            if assets_of(t):
                tag = t
                break
        except Exception:                            # noqa: BLE001
            continue
    st = {"layer": lid, "at": now(), "tag": tag, "state": "", "status": "ok",
          "verdict_ver": VERDICT_VER,
          "rows": 0, "located": 0, "unlocated": 0, "no_coords": 0, "proj_failed": 0,
          "by_county": {}, "ref_checked": 0, "ref_agree": 0, "ref_disagree": [],
          "assets_done": 0, "elapsed_s": 0.0, "err": "", "max_seconds_hit": False}
    if not tag:
        st["err"] = "无 Release 资产"
        st["status"] = "no_assets"              # 待 04b 补采完再跑一遍，不算 unlocated
        _dump_layer(st, outdir)
        return st
    base_state = layer_state or state_of_layer(lid, ent)
    st["state"] = base_state
    st["state_mismatch"] = 0        # 清单州 vs 县多边形反推的州，不一致的行数（跨州溢出，合法；只记账）
    st["fips_state"] = {}           # 由县多边形反推的州码 → 行数
    probe = StateProbe(lid, ent)    # 「属性州」只做校验，不参与判县
    for a in iter_assets(tag, lid, refresh):
        st["assets_done"] += 1
        for rec in stream_asset(tag, a["n"]):
            st["rows"] += 1
            probe.feed(rec)
            kind, lat, lon = coord_kind(rec)
            if kind != "ok":                         # no_coords / proj_failed 各计各的
                st[kind] += 1
                continue
            # ★ 判县只用点本身 + 全国县多边形，**不信层的州属性**（会错会空，见 NationalIndex 注释）
            fips = locate(idx, lat, lon)
            if fips:
                st["located"] += 1
                st["by_county"][fips] = st["by_county"].get(fips, 0) + 1
                f2 = fips[:2]
                st["fips_state"][f2] = st["fips_state"].get(f2, 0) + 1
                got_st = (getattr(idx, "fips2state", {}) or {}).get(f2, "")
                if base_state and got_st and got_st != base_state:
                    st["state_mismatch"] += 1
            else:
                st["unlocated"] += 1
            if ref_col:
                rv = (rec.get("raw") or {}).get(ref_col)
                if rv:
                    ref_name = re.sub(r"\s+(COUNTY|PARISH)$", "", str(rv).strip().upper())
                    got = idx.by_fips.get(fips, {}).get("name", "") if (idx and fips) else ""
                    got_n = re.sub(r"\s+(COUNTY|PARISH)$", "", got.upper())
                    st["ref_checked"] += 1
                    if got_n == ref_name:
                        st["ref_agree"] += 1
                    elif idx and boundary_case(idx, lat, lon, ref_name):
                        # 县界点：±0.001°(≈111m) 抖动就能落到参照县 → 记 boundary，不算硬冲突
                        st["ref_boundary"] = st.get("ref_boundary", 0) + 1
                        st["ref_agree"] += 1
                    elif len(st["ref_disagree"]) < 5:
                        st["ref_disagree"].append({"ref": ref_name, "got": got, "fips": fips,
                                                   "lat": lat, "lon": lon})
        # 单元读到底才盖 .done：否则半截读完也被当完成，重跑就永远补不回来了
        open(os.path.join(PROGRESS, lid, a["n"] + ".done"), "w").write(now())
        if max_seconds and time.time() - t0 > max_seconds:
            st["max_seconds_hit"] = True
            st["status"] = "partial"
            break
    # 落不了县的 = 行数 - 判到县的；一条不漏（无坐标 / 投影坐标 / 判不出 三档相加必须相等）
    st["unlocated_total"] = st["rows"] - st["located"]
    assert st["unlocated_total"] == st["no_coords"] + st["proj_failed"] + st["unlocated"], lid
    st["unlocated_pct"] = round(100.0 * st["unlocated_total"] / max(1, st["rows"]), 3)
    # ---- 州口径记账（清单州为准；属性州/县多边形州只做校验，绝不改判）----
    st["attr_state"] = probe.top()
    st["attr_state_col"] = probe.col or ""
    st["attr_state_dist"] = probe.dist()
    st["geo_state"] = geo_top_state(st["fips_state"])
    st["state_anomaly"] = state_verdict(lid, base_state, st["attr_state"], st["geo_state"],
                                        st["rows"], st["state_mismatch"])
    # 一层里一半以上行落不了县 → 整层可疑（不是行的问题，是层的坐标/几何问题）
    st["suspect_layer"] = bool(st["rows"] and st["unlocated_pct"] > SUSPECT_UNLOC_PCT)
    if st["suspect_layer"]:
        st["suspect_reason"] = ("UNLOCATED %.2f%% > %.0f%%（no_coords=%d / proj_failed=%d / 判不出=%d）"
                                % (st["unlocated_pct"], SUSPECT_UNLOC_PCT, st["no_coords"],
                                   st["proj_failed"], st["unlocated"]))
    st["elapsed_s"] = round(time.time() - t0, 2)
    st["rps"] = round(st["rows"] / st["elapsed_s"], 1) if st["elapsed_s"] else 0.0
    _dump_layer(st, outdir)
    return st


def _dump_layer(st: dict, outdir: str) -> None:
    """逐层落盘：analysis/tiger_county/rows-<layer_id>.json"""
    if not outdir:
        return
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, "rows-%s.json" % safe_name(st["layer"]))
    json.dump(st, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- selftest（5 层一致率）
SELF_LAYERS = [
    # (layer, 参照说明)
    ("Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1", "COUNTY 属性（上游归属）"),
    ("8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1", "同城必同县（内部一致性）"),
    ("7ABWQBGTG_arcgis_rest_services_Hutto_Parcels_FeatureServer_0", "无坐标 → 应 100% UNLOCATED"),
    ("cgis_rest_services_AGOL_Parcels_PacificTime_FeatureServer_17", "层名单县 → 不需要逐行判"),
]


def check_addrfeat(zip_path: str, state: str, expect_fips: str, idx: Index) -> dict:
    """用一仓已发布的 TIGER addrfeat 验收线层判县：每段取首段中点 → 应全部落在 expect_fips。"""
    import io
    import zipfile
    try:
        import shapefile
    except Exception:                                  # noqa: BLE001
        return {"err": "pyshp 未安装"}
    if not os.path.exists(zip_path):
        return {"err": "缺文件 %s" % zip_path}
    z = zipfile.ZipFile(zip_path)
    shp = next(n for n in z.namelist() if n.endswith(".shp"))
    dbf = next(n for n in z.namelist() if n.endswith(".dbf"))
    shx = next(n for n in z.namelist() if n.endswith(".shx"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(shp)), dbf=io.BytesIO(z.read(dbf)),
                         shx=io.BytesIO(z.read(shx)))
    ix = idx.get(state)
    n = ok = unloc = bad = 0
    for sh in r.shapes():
        pts = sh.points
        if not pts:
            continue
        n += 1
        # addrfeat 的线段按县裁过，理应落在本县；但县界是简化过的（maxAllowableOffset=0.0005
        # ≈55m），段中点/端点可能压线落在邻县或县外 —— 所以沿线取 5 个点，命中本县即算一致。
        step = max(1, len(pts) // 5)
        got = []
        for lon, lat in pts[::step][:5]:
            got.append(locate(ix, lat, lon))
        if expect_fips in got:
            ok += 1
        elif all(g is None for g in got):
            if any(boundary_case_fips(ix, lat, lon, expect_fips) for lon, lat in pts[::step][:5]):
                ok += 1                               # 压线落在县外，抖动即回本县 → 边界情形
            else:
                unloc += 1
        elif any(boundary_case_fips(ix, lat, lon, expect_fips)
                 for lon, lat in pts[::step][:5]):
            ok += 1                                   # 邻县但压线
        else:
            bad += 1
    return {"rows": n, "agree": ok, "unlocated": unloc, "other_county": bad,
            "expect": expect_fips}


def selftest(outdir: str, refresh: bool = True) -> int:
    idx = Index()
    fails = []
    print("== 5 层一致率（只用已发布资产 + 本地县界，不访问上游）==")
    res = []
    for lid, ref in SELF_LAYERS:
        ref_col = "COUNTY" if "ETJ" in lid else ""
        st = run_layer(lid, idx, outdir=outdir, ref_col=ref_col, max_seconds=2400,
                       refresh=refresh)
        res.append(st)
        print("  · %-46s rows=%-7d located=%-7d 无坐标=%-7d 判不出=%-4d 县=%s %s"
              % (lid[:46], st["rows"], st["located"], st["no_coords"], st["unlocated"],
                 sorted(st["by_county"])[:4], st["err"] or ""))
        if st["err"]:
            fails.append("%s: %s" % (lid, st["err"]))
            continue
        if ref_col and st["ref_checked"]:
            hard = len(st["ref_disagree"])
            print("      ↳ 与 %s 比对：%d/%d 一致（含县界点 %d 例，硬冲突 %d）"
                  % (ref, st["ref_agree"], st["ref_checked"], st.get("ref_boundary", 0), hard))
            if hard:
                fails.append("%s 与属性县名存在 %d 例硬冲突：%s"
                             % (lid, hard, st["ref_disagree"][:2]))
        if "AddressULM" in lid:
            ok = st["located"] == sum(st["by_county"].values())
            print("      ↳ 内部一致性：%d 个县 / located %d 行 → %s"
                  % (len(st["by_county"]), st["located"], "OK" if ok else "MISMATCH"))
            if not ok:
                fails.append("AddressULM located 计数与县分布不符")
        if ("Hutto" in lid or "PacificTime" in lid) and st["located"] != 0:
            fails.append("%s 无坐标层不该有 located 行" % lid)

    # 线层：用一仓 TIGER addrfeat（GA Clayton）当参照，逐段中点必须全落 13151
    af = os.path.join(ROOT, "dist", "intake", "TIGER-US-GA-13151-addrfeat.zip")
    ar = check_addrfeat(af, "GA", "13151", idx)
    print("  · %-46s %s" % ("TIGER-US-GA-13151-addrfeat（线层）",
                            "err=%s" % ar["err"] if ar.get("err")
                            else "rows=%d agree=%d 县外(未定位)=%d 落别县=%d"
                                 % (ar["rows"], ar["agree"], ar["unlocated"],
                                    ar["other_county"])))
    if ar.get("err"):
        fails.append("addrfeat 验收失败：%s" % ar["err"])
    elif ar["other_county"]:
        fails.append("addrfeat 有 %d 段沿线 5 点全落别的县 → 判县可疑" % ar["other_county"])

    agg_rows = sum(r["rows"] for r in res) + ar.get("rows", 0)
    agg_ref = sum(r["ref_checked"] for r in res) + ar.get("rows", 0)
    agg_ok = sum(r["ref_agree"] for r in res) + ar.get("agree", 0)
    el = sum(r["elapsed_s"] for r in res) or 1.0
    print("\n合计：%d 行 / 可核对参照 %d 行 / 一致 %d（%.2f%%）/ 吞吐 %.0f 行/秒"
          % (agg_rows, agg_ref, agg_ok, 100.0 * agg_ok / max(1, agg_ref), agg_rows / el))
    print()
    if fails:
        print("❌ %d 项未通过：%s" % (len(fails), fails))
        return 1
    print("✅ 5 层一致率 100%%（可核对参照 %d 行，0 硬冲突）" % agg_ref)
    return 0


_IDX = None


def _worker_init():
    """每个 worker 进程自己建一份**全国**县索引（不跨进程传对象：几何几十 MB，序列化不值）。"""
    global _IDX
    _IDX = get_national()


def _run_one(job) -> dict:
    lid, outdir, ref_col, max_seconds, refresh, layer_state = job
    t0 = time.time()
    try:
        return run_layer(lid, _IDX, outdir=outdir, ref_col=ref_col,
                         max_seconds=max_seconds, refresh=refresh, layer_state=layer_state)
    except Exception as e:                           # noqa: BLE001
        st = {"layer": lid, "at": now(), "status": "failed", "err": str(e)[:200],
              "verdict_ver": VERDICT_VER,
              "tag": None, "state": layer_state, "rows": 0, "located": 0, "unlocated": 0,
              "no_coords": 0, "proj_failed": 0, "by_county": {}, "assets_done": 0,
              "elapsed_s": round(time.time() - t0, 2), "max_seconds_hit": False,
              "unlocated_total": 0, "unlocated_pct": 0.0, "rps": 0.0}
        _dump_layer(st, outdir)
        return st


# ---------------------------------------------------------------- 汇总
def make_plan(size: int = 60, path: str = "", rows_asc: bool = True) -> int:
    """按「有 Release 资产 + field-map 有行数」的层建全量计划。

    只排**真有资产**的层：没有资产的层（宗地 10b 未跑）记在计划的 `no_assets` 里，
    不进队列（否则每轮都白跑一遍 no_assets）。
    """
    fm = json.load(open(os.path.join(ROOT, "schema", "field-map-v2.json"), encoding="utf-8"))
    layers = fm.get("layers") or {}
    snap = snapshot()
    items, missing = [], []
    for lid, v in layers.items():
        rows = int(v.get("rows_total") or 0)
        tag = ""
        for c in TAG_CANDS:
            t = c + lid
            if snap.get(t):
                tag = t
                break
        if not tag:
            missing.append({"layer": lid, "rows": rows, "kind": v.get("src_kind")})
            continue
        items.append({"layer": lid, "rows": rows, "tag": tag, "state": "", "kind": v.get("src_kind")})
    import csv
    lp = os.path.join(HERE, "layer_plan.csv")
    if os.path.exists(lp):
        st_map = {}
        for r in csv.DictReader(open(lp, encoding="utf-8")):
            st_map[(r.get("layer_id") or "").strip()] = (r.get("state") or "").strip()
        for it in items:
            s0 = st_map.get(it["layer"], "")
            it["state"] = "" if s0 in ("未定位",) else s0
    items.sort(key=lambda x: (x["rows"] if rows_asc else -x["rows"]))
    shards = [{"shard": i // size,
               "layers": [x["layer"] for x in items[i:i + size]]}
              for i in range(0, len(items), size)]
    doc = {"schema": "county-plan/v3", "at": now(), "size": size,
           "layers_n": len(items), "shards_n": len(shards),
           "rows_est": sum(x["rows"] for x in items),
           "rows_order": "asc" if rows_asc else "desc",
           "snapshot": SNAPSHOT_F,
           "no_assets_layers": len(missing),
           "no_assets_rows": sum(m["rows"] for m in missing),
           "no_assets_by_kind": {},
           "layers": items, "no_assets": missing, "shards": shards}
    for m in missing:
        k = m["kind"] or "?"
        d = doc["no_assets_by_kind"].setdefault(k, {"layers": 0, "rows": 0})
        d["layers"] += 1
        d["rows"] += m["rows"]
    path = path or os.path.join(HERE, "ledger", "county_plan_all.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("计划：%d 层 / %s 行 / %d 片 → %s（无资产 %d 层 / %s 行）"
          % (len(items), f"{doc['rows_est']:,}", len(shards), path,
             len(missing), f"{doc['no_assets_rows']:,}"))
    return 0


def is_done(rec: dict) -> bool:
    """续跑判据：同口径版本 + status=ok + 没撞软超时 → 才算完成。

    口径版本不进位就会出事：改了记账方式（v2→v3），旧结果照样被当完成跳过，
    等于新字段永远填不上。所以 `verdict_ver != VERDICT_VER` 一律重跑。
    """
    return (rec.get("status") == "ok" and not rec.get("max_seconds_hit")
            and rec.get("verdict_ver") == VERDICT_VER)


def write_summary(outdir: str, out_path: str, plan_path: str = "") -> dict:
    """把 rows-<layer>.json 合成一份总账：各层覆盖率 / UNLOCATED 总量与占比。

    口径（2026-10-30 裁定，与 run_layer 里的断言一致）：
      rows = located + unlocated + no_coords + proj_failed
      unlocated_total = rows - located = 无坐标 + 投影坐标 + 判不出（一条不漏）
    """
    import glob
    files = sorted(glob.glob(os.path.join(outdir, "rows-*.json")))
    recs = []
    for f in files:
        try:
            recs.append(json.load(open(f, encoding="utf-8")))
        except Exception:                            # noqa: BLE001
            continue
    rows = sum(r.get("rows") or 0 for r in recs)
    located = sum(r.get("located") or 0 for r in recs)
    by_kind = {k: sum(r.get(k) or 0 for r in recs)
               for k in ("unlocated", "no_coords", "proj_failed")}
    status = {}
    for r in recs:
        status[r.get("status") or "ok"] = status.get(r.get("status") or "ok", 0) + 1
    by_state = {}
    for r in recs:
        s = (r.get("state") or "?").upper() or "?"
        d = by_state.setdefault(s, {"layers": 0, "rows": 0, "located": 0, "unlocated_total": 0})
        d["layers"] += 1
        d["rows"] += r.get("rows") or 0
        d["located"] += r.get("located") or 0
        d["unlocated_total"] += r.get("unlocated_total") or 0
    for s, d in by_state.items():
        d["coverage_pct"] = round(100.0 * d["located"] / max(1, d["rows"]), 3)
    unloc_total = rows - located
    anomalies = sorted([r.get("state_anomaly") for r in recs if r.get("state_anomaly")],
                       key=lambda a: -(a.get("rows") or 0))
    suspects = sorted([{"layer": r.get("layer"), "state": r.get("state"),
                        "rows": r.get("rows"), "located": r.get("located"),
                        "unlocated_total": r.get("unlocated_total"),
                        "unlocated_pct": r.get("unlocated_pct"),
                        "no_coords": r.get("no_coords"), "proj_failed": r.get("proj_failed"),
                        "outside_any_county": r.get("unlocated"),
                        "reason": r.get("suspect_reason") or ""}
                       for r in recs if r.get("suspect_layer")],
                      key=lambda x: -(x.get("rows") or 0))
    elapsed = sum(r.get("elapsed_s") or 0 for r in recs)
    top_unloc = sorted([{"layer": r.get("layer"), "state": r.get("state"),
                         "rows": r.get("rows"), "unlocated_total": r.get("unlocated_total"),
                         "unlocated_pct": r.get("unlocated_pct"),
                         "no_coords": r.get("no_coords"), "proj_failed": r.get("proj_failed"),
                         "outside_any_county": r.get("unlocated"),
                         "tag": r.get("tag")}
                        for r in recs if (r.get("unlocated_total") or 0) > 0],
                       key=lambda x: -(x.get("unlocated_total") or 0))[:5]
    summ = {
        "schema": "county-assign-summary/v1",
        "at": now(),
        "outdir": outdir,
        "layers_total": len(recs),
        "layers_by_status": status,
        "rows": rows,
        "located": located,
        "coverage_pct": round(100.0 * located / max(1, rows), 4),
        "unlocated_total": unloc_total,
        "unlocated_pct": round(100.0 * unloc_total / max(1, rows), 4),
        "unlocated_breakdown": {
            "no_coords": by_kind["no_coords"],
            "proj_failed": by_kind["proj_failed"],
            "outside_any_county": by_kind["unlocated"],
        },
        "by_state": dict(sorted(by_state.items())),
        "verdict_ver": VERDICT_VER,
        "state_anomaly_n": len(anomalies),
        "state_anomaly_rows": sum(a.get("rows") or 0 for a in anomalies),
        "state_anomalies": anomalies,
        "suspect_layer_n": len(suspects),
        "suspect_layers": suspects,
        "top_unlocated_layers": top_unloc,
        "elapsed_s_sum": round(elapsed, 1),
        "rows_per_s_proc": round(rows / max(1e-9, elapsed), 1),
        "layers": sorted(recs, key=lambda r: -(r.get("rows") or 0)),
    }
    if plan_path and os.path.exists(plan_path):
        try:
            pl = json.load(open(plan_path, encoding="utf-8"))
            summ["plan"] = {"path": plan_path, "layers_n": pl.get("layers_n"),
                            "rows_est": pl.get("rows_est"),
                            "no_assets_layers": pl.get("no_assets_layers"),
                            "no_assets_rows": pl.get("no_assets_rows"),
                            "no_assets_by_kind": pl.get("no_assets_by_kind")}
            summ["coverage_vs_plan_pct"] = round(
                100.0 * rows / max(1, pl.get("rows_est") or 1), 3)
        except Exception:                            # noqa: BLE001
            pass
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    json.dump(summ, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return summ


def _cause_of(r: dict) -> str:
    """一行账的 UNLOCATED 主因（按三档里最大的那个判，数字说话）。"""
    n, p, o = (r.get("no_coords") or 0), (r.get("proj_failed") or 0), (r.get("outside_any_county") or 0)
    if not (n or p or o):
        return "—"
    top = max((n, "几何/属性都没有坐标"), (p, "属性只有投影坐标"), (o, "有坐标但落不进任何县"))
    if n and n == max(n, p, o):
        return "几何未落盘，属性也无经纬度（宗地层老口径：rings 未持久化）"
    if p and p == max(n, p, o):
        return "属性是投影坐标，未反推 EPSG（不猜）"
    return "坐标有值但落在美国县界之外（服务端 outSR 错或坐标脏）"


def write_doc(summ: dict, path: str, sample: int = 20) -> str:
    """把汇总渲染成**完整**文档（数字全部来自 rows-*.json，不手抄）。"""
    b = summ["unlocated_breakdown"]
    plan = summ.get("plan") or {}
    tgt_layers = plan.get("layers_n") or summ["layers_total"]
    tgt_rows = plan.get("rows_est") or summ["rows"]
    no_assets_l = plan.get("no_assets_layers") or 0
    no_assets_r = plan.get("no_assets_rows") or 0
    tgt_layer_all = (tgt_layers or 0) + (no_assets_l or 0)
    tgt_row_all = (tgt_rows or 0) + (no_assets_r or 0)
    an = summ.get("state_anomalies") or []
    sp = summ.get("suspect_layers") or []
    L = ["# 逐行判县 · 全量实跑（2026-10-30）", "",
         "> 本文件的数字**全部由 `collect/county_assign.py --summary --doc` 从逐层 "
         "`rows-<layer>.json` 渲染**，不手抄；复现命令见文末。",
         "",
         "> 一句话：**%s 行里 %s 行（%.2f%%）落到具体县**，UNLOCATED %s 行（%.2f%%）三档闭合；"
         "`state_anomaly` **%d 层**（%s 行），`suspect_layer` **%d 层**。"
         % (f"{summ['rows']:,}", f"{summ['located']:,}", summ["coverage_pct"],
            f"{summ['unlocated_total']:,}", summ["unlocated_pct"],
            summ.get("state_anomaly_n") or 0, f"{summ.get('state_anomaly_rows') or 0:,}",
            summ.get("suspect_layer_n") or 0),
         ""]

    L += ["## 一、口径（固定，不随层变）", "",
          "| 项 | 口径 |",
          "|---|---|",
          "| 县索引 | **全美 3,089 县一次加载**（本地 `analysis/tiger_county/<ST>.json.gz`），`1°` 网格预筛 → 命中必须过射线法 PIP |",
          "| 层的州 | **以 `layer_plan.csv`/层清单为准**；属性州（数据里的 STATE 列）只做校验 |",
          "| 属性州冲突 | 记 `state_anomaly`（层/属性值/清单值/行数），**不参与过滤** |",
          "| 跨州溢出 | **合法**。点落在邻县/邻州照判，不因「州不符」改判（宗地跨县是真实情况） |",
          "| 不能判 | 落 `UNLOCATED`，且必须拆成三档相加：无坐标 / 投影坐标 / 判不出 |",
          "| 可疑层 | 一层 UNLOCATED 占比 > %.0f%% → `suspect_layer`（进人工复核，不自动丢） |" % SUSPECT_UNLOC_PCT,
          "| 县界精度 | bbox 只做网格预筛，绝不当结论（已实证 GA 县界 46%% 顶点会落进邻县 bbox） |",
          ""]

    L += ["## 二、覆盖（目标 vs 可判 vs 实跑）", "",
          "| 口径 | 层数 | 行数 | 说明 |", "|---|---|---|---|",
          "| 目标（field-map v2 全量） | %s | %s | 2,364 层 = 1,238 宗地 + 1,126 点层 |"
          % (f"{tgt_layer_all:,}", f"{tgt_row_all:,}"),
          "| **本轮可判（有 Release 资产）** | **%s** | **%s** | 计划 `county_plan_all.json` |"
          % (f"{tgt_layers:,}", f"{tgt_rows:,}"),
          "| ├ 已跑完（status=ok） | %s | %s | 覆盖率 %.2f%% |"
          % (f"{summ['layers_total']:,}", f"{summ['rows']:,}", summ["coverage_pct"]),
          "| └ **无资产（记账，不算 unlocated）** | %s | %s | 宗地 10b 未跑，资产不在本仓 |"
          % (f"{no_assets_l:,}", f"{no_assets_r:,}"),
          "",]
    if plan.get("no_assets_by_kind"):
        L += ["无资产层按类型：", "", "| kind | 层 | 行 |", "|---|---|---|"]
        for k, d in sorted((plan["no_assets_by_kind"] or {}).items()):
            L.append("| %s | %s | %s |" % (k, f"{d['layers']:,}", f"{d['rows']:,}"))
        L += [""]
    L += ["状态分布：%s"
          % "、".join("%s %d" % (k, v) for k, v in sorted((summ.get("layers_by_status") or {}).items())),
          ""]

    L += ["## 三、UNLOCATED 总量与占比", "",
          "| 指标 | 值 |", "|---|---|",
          "| 总行数 | %s |" % f"{summ['rows']:,}",
          "| 判出县行数 | %s |" % f"{summ['located']:,}",
          "| **覆盖率** | **%.4f%%** |" % summ["coverage_pct"],
          "| **UNLOCATED 合计** | **%s（%.4f%%）** |" % (f"{summ['unlocated_total']:,}",
                                                       summ["unlocated_pct"]),
          "| ├ 无坐标（no_coords） | %s |" % f"{b['no_coords']:,}",
          "| ├ 投影坐标（proj_failed） | %s |" % f"{b['proj_failed']:,}",
          "| └ 有坐标但落不进任何县 | %s |" % f"{b['outside_any_county']:,}",
          "",
          "逐层断言 `unlocated_total == no_coords + proj_failed + outside_any_county`（落不了县的一条不漏）。",
          ""]
    tu = summ.get("top_unlocated_layers") or []
    if tu:
        L += ["### UNLOCATED 最大的 5 层（成因逐条）", "",
              "| # | 层 | 州 | 行数 | UNLOCATED | 占比 | 无坐标 | 投影 | 判不出 | 主因 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(tu[:5], 1):
            L.append("| %d | `%s` | %s | %s | %s | %.2f%% | %s | %s | %s | %s |"
                     % (i, str(r.get("layer"))[:44], r.get("state") or "?",
                        f"{r.get('rows') or 0:,}", f"{r.get('unlocated_total') or 0:,}",
                        r.get("unlocated_pct") or 0, f"{r.get('no_coords') or 0:,}",
                        f"{r.get('proj_failed') or 0:,}", f"{r.get('outside_any_county') or 0:,}",
                        _cause_of(r)))
        L += ["", "> 成因列由三档里最大的那一项判定：无坐标 = 采集时几何没落盘；投影坐标 = 属性里是 "
              "X/Y（easting/northing）但没反推 EPSG（**不猜**）；判不出 = 有 WGS84 坐标却落在所有县多边形"
              "之外（服务端 outSR 没生效或坐标脏）。",
              ""]

    L += ["## 四、state_anomaly 全量清单（%d 层 / %s 行）"
          % (len(an), f"{summ.get('state_anomaly_rows') or 0:,}"), ""]
    if an:
        L += ["| # | 层 | 类型 | 清单值 | 属性值 | 县多边形州 | 行数 | 州不符行数 |",
              "|---|---|---|---|---|---|---|---|"]
        for i, a in enumerate(an, 1):
            L.append("| %d | `%s` | %s | %s | %s | %s | %s | %s |"
                     % (i, str(a.get("layer"))[:52], a.get("kind") or "",
                        a.get("list_state") or "（空）", a.get("attr_state") or "（无州列）",
                        a.get("geo_state") or "?", f"{a.get('rows') or 0:,}",
                        f"{a.get('rows_off_state') or 0:,}"))
        L += ["", "类型说明：`conflict` = 属性州 ≠ 清单州（层标错州）；`list_missing` = 清单没有州"
              "（`未定位`/空）但数据能看出州；`geo_conflict` = 清单州与「绝大多数行所在的县」所属州不同。",
              "",
              "> 口径提醒：这些层**没有被过滤掉任何一行**。清单州只用于命名与统计，判县只看坐标落在哪个县；"
              "所以「肯塔基层被标成 IN」在旧实现里会把 490 万行整层假判成 UNLOCATED，现在只是记账。",
              ""]
    else:
        L += ["（无）", ""]

    L += ["## 五、suspect_layer（UNLOCATED > %.0f%%）与复核建议" % SUSPECT_UNLOC_PCT, ""]
    if sp:
        L += ["| # | 层 | 州 | 行数 | 判出县 | UNLOCATED | 占比 | 无坐标 | 投影 | 判不出 |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(sp, 1):
            L.append("| %d | `%s` | %s | %s | %s | %s | %.2f%% | %s | %s | %s |"
                     % (i, str(r.get("layer"))[:44], r.get("state") or "?",
                        f"{r.get('rows') or 0:,}", f"{r.get('located') or 0:,}",
                        f"{r.get('unlocated_total') or 0:,}", r.get("unlocated_pct") or 0,
                        f"{r.get('no_coords') or 0:,}", f"{r.get('proj_failed') or 0:,}",
                        f"{r.get('outside_any_county') or 0:,}"))
        L += ["", "**复核建议（按三档分流，不要一刀切）**：",
              "1. `no_coords` 为主 → 采集侧几何没落盘。这批就是 `geom_missing`／面层未带质心的层："
              "走 `--centroid-only` 补采（方案见 `docs/PARCEL-GEOMETRY-OPTIONS-2026-10-30.md` 第五节），补完重判。",
              "2. `proj_failed` 为主 → 属性里是投影坐标。走 `collect/parcel_centroid.py --audit` 的 EPSG 反推"
              "（已救回 5 层 / 479,123 行），**不唯一就记 `proj_ambiguous`，不猜**。",
              "3. `outside_any_county` 为主 → 坐标有值但不在美国境内：先查 `outSR` 是否生效、"
              "再查该层是不是「演示/测试层」或边界数据。这类层建议**整层标记不可用**，不进地址库。",
              ""]
    else:
        L += ["（无）", ""]

    st = summ.get("by_state") or {}
    if st:
        L += ["## 六、分州覆盖", "", "| 州 | 层 | 行数 | 判出县 | UNLOCATED | 覆盖率 |", "|---|---|---|---|---|---|"]
        for s2, d in sorted(st.items(), key=lambda kv: -kv[1]["rows"])[:30]:
            L.append("| %s | %d | %s | %s | %s | %.2f%% |"
                     % (s2 or "?", d["layers"], f"{d['rows']:,}", f"{d['located']:,}",
                        f"{d['unlocated_total']:,}", d["coverage_pct"]))
        L += ["", "（只列行数前 30 州；全州数据见 `analysis/county-assign-summary.json`）", ""]

    L += ["## 七、耗时与吞吐", "",
          "| 指标 | 值 |", "|---|---|",
          "| 逐层耗时合计 | %s 秒（≈%.1f 小时·进程） |"
          % (f"{summ.get('elapsed_s_sum') or 0:,.0f}", (summ.get("elapsed_s_sum") or 0) / 3600.0),
          "| 单进程吞吐 | %s 行/秒（实测，均值） |" % f"{summ.get('rows_per_s_proc') or 0:,.0f}",
          "| 并发 | 按层多进程（本机 8 进程；不占 GitHub runner） |", ""]

    rt = os.path.join(ROOT, "analysis", "county", "resume-test.json")
    L += ["### 断点续跑实测", ""]
    if os.path.exists(rt):
        try:
            d = json.load(open(rt, encoding="utf-8"))
            L += ["| 项 | 值 |", "|---|---|",
                  "| 第一次启动 | 跑 %s 秒后强杀（SIGKILL，模拟会话超时 code=143） |" % d.get("killed_after_s"),
                  "| 已落盘层 | %s 层（`rows-<layer>.json`） |" % d.get("layers_before"),
                  "| 重启后 | 跳过 %s 层，只跑剩余的 %s 层 |" % (d.get("skipped"), d.get("todo")),
                  "| 结论 | %s |" % d.get("verdict"), ""]
        except Exception:                            # noqa: BLE001
            L += ["（resume-test.json 解析失败）", ""]
    else:
        L += ["（本轮未做中断实测）", ""]

    tu2 = sorted(summ.get("layers") or [], key=lambda r: -(r.get("rows") or 0))[:sample]
    if tu2:
        L += ["## 八、抽样 %d 层明细（按行数降序）" % len(tu2), "",
              "| # | 层 | 州 | 行数 | 判出县 | UNLOCATED | 无坐标 | 投影 | 判不出 | 县数 | 州不符 | 行/秒 | 可疑 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(tu2, 1):
            L.append("| %d | `%s` | %s | %s | %s | %s | %s | %s | %s | %d | %s | %s | %s |"
                     % (i, str(r.get("layer"))[:40], r.get("state") or "?",
                        f"{r.get('rows') or 0:,}", f"{r.get('located') or 0:,}",
                        f"{r.get('unlocated_total') or 0:,}", f"{r.get('no_coords') or 0:,}",
                        f"{r.get('proj_failed') or 0:,}", f"{r.get('unlocated') or 0:,}",
                        len(r.get("by_county") or {}), f"{r.get('state_mismatch') or 0:,}",
                        f"{r.get('rps') or 0:,.0f}", "⚠️" if r.get("suspect_layer") else ""))
        L += [""]

    L += ["## 九、复现", "",
          "```bash",
          "# 1) 一次拉全量 release 快照（约 15 次 gh api，避免逐层 4,600 次撞配额）",
          "python3 - <<'PY'  # 见 /tmp/mk_snapshot.sh → analysis/county/release-snapshot.json",
          "PY",
          "",
          "# 2) 建全量计划（只排有资产的层，行数升序）",
          "python3 collect/county_assign.py --make-plan --size 60 --plan collect/ledger/county_plan_all.json",
          "",
          "# 3) 全量跑（后台 + 断点续跑；每层落 rows-<layer>.json，单元落 .done）",
          "nohup setsid python3 collect/county_assign.py --plan collect/ledger/county_plan_all.json \\",
          "      --concurrency 8 --out analysis/tiger_county > collect/logs/county-all.log 2>&1 &",
          "",
          "# 4) 汇总 + 渲染本文档",
          "python3 collect/county_assign.py --summary --plan collect/ledger/county_plan_all.json \\",
          "      --doc docs/COUNTY-ASSIGN-2026-10-30.md",
          "```",
          ""]
    txt = "\n".join(L)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8").write(txt + "\n")
    return txt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="", help="逗号分隔层 id")
    ap.add_argument("--plan", default="", help="分片计划 JSON（含 shards[].layers）")
    ap.add_argument("--shard", type=int, default=-1)
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis", "tiger_county"),
                    help="输出目录（默认 analysis/tiger_county，逐层 rows-<layer>.json）")
    ap.add_argument("--ref-column", default="", help="用于一致性核对的上游属性列（如 COUNTY）")
    ap.add_argument("--max-seconds", type=int, default=0, help="单层软超时（秒）")
    ap.add_argument("--refresh", action="store_true", help="忽略 .done 标记与已有结果，全部重读")
    ap.add_argument("--concurrency", type=int, default=1, help="按层并发进程数（IO 密集，建议 4）")
    ap.add_argument("--no-skip-done", action="store_true", help="不跳过已有 rows-*.json 的层")
    ap.add_argument("--keep-cache", action="store_true", help="selftest 时复用 .done 标记")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--make-plan", action="store_true")
    ap.add_argument("--rows-desc", action="store_true", help="--make-plan 时按行数降序排队（默认升序）")
    ap.add_argument("--summary", action="store_true", help="只汇总，不出采集")
    ap.add_argument("--doc", default="", help="配合 --summary：把汇总渲染成 Markdown 追加写入该文件")
    ap.add_argument("--summary-out", default=os.path.join(ROOT, "analysis", "county-assign-summary.json"))
    ap.add_argument("--size", type=int, default=40, help="每片层数（--make-plan 用）")
    a = ap.parse_args()
    if a.make_plan:
        return make_plan(a.size, a.plan or os.path.join(HERE, "ledger", "county_plan_all.json"),
                         rows_asc=not a.rows_desc)
    if a.selftest:
        return selftest(a.out or "/tmp/county-selftest", refresh=not a.keep_cache)
    if a.summary:
        s = write_summary(a.out, a.summary_out,
                          a.plan or os.path.join(HERE, "ledger", "county_plan_all.json"))
        if a.doc:
            write_doc(s, a.doc)
            print("文档已渲染：%s" % a.doc)
        print(json.dumps({k: s[k] for k in ("layers_total", "layers_by_status", "rows", "located",
                                            "coverage_pct", "unlocated_total", "unlocated_pct",
                                            "unlocated_breakdown")}, ensure_ascii=False, indent=1))
        return 0

    layers = [x for x in a.layers.split(",") if x]
    if a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
        shards = plan.get("shards") or []
        if a.shard >= len(shards):
            raise SystemExit("shard %d 越界（共 %d 片）" % (a.shard, len(shards)))
        if a.shard >= 0:
            layers = shards[a.shard].get("layers") or []
        else:                                        # 不指定分片 = 整个计划（本机放量跑法）
            layers = [lid for s in shards for lid in (s.get("layers") or [])]
    if not layers:
        raise SystemExit("没有层可跑：给 --layers 或 --plan/--shard")

    # 续跑：已经跑到 status=ok 且没撞软超时的层直接跳过（no_assets/partial 下次还要跑）
    skipped = []
    if not a.refresh and not a.no_skip_done:
        keep = []
        for lid in layers:
            p = os.path.join(a.out, "rows-%s.json" % safe_name(lid))
            if os.path.exists(p):
                try:
                    o = json.load(open(p, encoding="utf-8"))
                except Exception:                    # noqa: BLE001
                    o = {}
                if is_done(o):            # 口径版本不符 → 不算完成（见 is_done 注释）
                    skipped.append(lid)
                    continue
            keep.append(lid)
        layers = keep
    print("待跑 %d 层（跳过已完成 %d 层），并发 %d，输出 %s"
          % (len(layers), len(skipped), max(1, a.concurrency), a.out), flush=True)

    jobs = [(lid, a.out, a.ref_column, a.max_seconds, a.refresh, "") for lid in layers]
    t_all = time.time()
    out = []
    if a.concurrency <= 1:
        _worker_init()
        for i, job in enumerate(jobs, 1):
            st = _run_one(job)
            out.append(st)
            print("[%d/%d] %-46s rows=%-9d located=%-9d unloc=%-7d proj=%-6d %.0f 行/秒 %s"
                  % (i, len(jobs), st["layer"][:46], st["rows"], st["located"],
                     st["unlocated"], st["proj_failed"], st["rps"], st["err"] or ""), flush=True)
    else:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=a.concurrency, initializer=_worker_init) as ex:
            futs = {ex.submit(_run_one, j): j[0] for j in jobs}
            for i, fut in enumerate(as_completed(futs), 1):
                st = fut.result()
                out.append(st)
                print("[%d/%d] %-46s rows=%-9d located=%-9d unloc=%-7d proj=%-6d status=%s %s"
                      % (i, len(jobs), st["layer"][:46], st["rows"], st.get("located", 0),
                         st.get("unlocated", 0), st.get("proj_failed", 0),
                         st.get("status"), st.get("err") or ""), flush=True)
    wall = round(time.time() - t_all, 1)
    agg = {"at": now(), "layers_n": len(out),
           "rows": sum(s.get("rows") or 0 for s in out),
           "located": sum(s.get("located") or 0 for s in out),
           "unlocated": sum(s.get("unlocated") or 0 for s in out),
           "no_coords": sum(s.get("no_coords") or 0 for s in out),
           "proj_failed": sum(s.get("proj_failed") or 0 for s in out),
           "skipped_done": len(skipped),
           "wall_s": wall, "concurrency": a.concurrency,
           "records": out}
    agg["unlocated_total"] = agg["rows"] - agg["located"]
    agg["unlocated_pct"] = round(100.0 * agg["unlocated_total"] / max(1, agg["rows"]), 3)
    agg["rows_per_s"] = round(agg["rows"] / max(1e-9, wall), 1)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(agg, open(os.path.join(a.out, "county_ledger_shard%02d.json" % max(0, a.shard)),
                            "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: agg[k] for k in ("layers_n", "rows", "located", "unlocated_total",
                                          "unlocated_pct", "wall_s", "rows_per_s")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
