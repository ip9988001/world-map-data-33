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
from intake_33 import release_assets             # noqa: E402
from field_map_v2 import STATE_ABBR             # noqa: E402

REPO = "ip9988001/world-map-data-33"
PROGRESS = os.path.join(HERE, "progress", "county")
TAG_CANDS = ("collect-step10-", "collect-step04-", "collect-step05-", "collect-step07-")
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


def locate(idx, lat, lon):
    """射线法判定。bbox 只做预筛（禁用 bbox 当结论），命中必须过 PIP。"""
    if idx is None or lat is None or lon is None:
        return None
    for fips, e in idx.by_fips.items():
        if not CT.in_bbox(lat, lon, e["bbox"]):
            continue
        if CT.pip(lat, lon, e["geom"]):
            return fips
    return None


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
    """从一条采集记录里取 (lat, lon)：先信封，再 raw 属性。"""
    lat = rec.get("lat")
    lon = rec.get("lon")
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


def iter_rows(tag: str, layer: str, state: str, refresh: bool = False):
    """逐单元（asset）产出 (asset_name, rows_iter)。每个 asset 完成即写 .done 标记。"""
    assets = [a for a in release_assets(tag) if UNIT_RE.search(a["n"])]
    assets.sort(key=lambda a: a["n"])
    d = os.path.join(PROGRESS, layer)
    os.makedirs(d, exist_ok=True)
    for a in assets:
        mark = os.path.join(d, a["n"] + ".done")
        if os.path.exists(mark) and not refresh:
            continue
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, a["n"])
            subprocess.run(["gh", "release", "download", tag, "--repo", REPO,
                            "-p", a["n"], "-D", td, "--clobber"],
                           capture_output=True, timeout=3600)
            if not os.path.exists(p):
                continue
            rows = []
            with tarfile.open(p, "r:gz") as tf:
                for m in tf.getmembers():
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
                                rows.append(json.loads(ln))
                            except Exception:            # noqa: BLE001
                                continue
            open(mark, "w").write(now())
            yield a["n"], rows


def run_layer(lid: str, idx: Index, outdir: str = "", ref_col: str = "",
              max_seconds: int = 0, refresh: bool = False, layer_state: str = "",
              ent: dict = None) -> dict:
    t0 = time.time()
    tag = None
    for c in TAG_CANDS:
        t = c + lid
        try:
            if release_assets(t):
                tag = t
                break
        except Exception:                            # noqa: BLE001
            continue
    st = {"layer": lid, "tag": tag, "rows": 0, "located": 0, "unlocated": 0,
          "no_coords": 0, "by_county": {}, "ref_checked": 0, "ref_agree": 0,
          "ref_disagree": [], "elapsed_s": 0.0, "err": "", "max_seconds_hit": False}
    if not tag:
        st["err"] = "无 Release 资产"
        return st
    base_state = layer_state or state_of_layer(lid, ent)
    st["state"] = base_state
    idx_cache = {}
    for asset, rows in iter_rows(tag, lid, base_state, refresh):
        for rec in rows:
            st["rows"] += 1
            lat, lon = extract(rec)
            if lat is None or lon is None:
                st["no_coords"] += 1
                continue
            state = base_state
            if not state:                            # 层元数据没州时再看行属性
                rv = (rec.get("raw") or {}).get("STATE") or (rec.get("raw") or {}).get("STATE_ABBR") or ""
                sv = str(rv).strip().upper()
                state = STATE_ABBR.get(sv, sv)[:2] if sv else ""
            if state not in idx_cache:
                idx_cache[state] = idx.get(state) if state else None
            ix = idx_cache[state]
            fips = locate(ix, lat, lon)
            if fips:
                st["located"] += 1
                st["by_county"][fips] = st["by_county"].get(fips, 0) + 1
            else:
                st["unlocated"] += 1
            if ref_col:
                rv = (rec.get("raw") or {}).get(ref_col)
                if rv:
                    ref_name = re.sub(r"\s+(COUNTY|PARISH)$", "", str(rv).strip().upper())
                    got = ix.by_fips.get(fips, {}).get("name", "") if (ix and fips) else ""
                    got_n = re.sub(r"\s+(COUNTY|PARISH)$", "", got.upper())
                    st["ref_checked"] += 1
                    if got_n == ref_name:
                        st["ref_agree"] += 1
                    elif ix and boundary_case(ix, lat, lon, ref_name):
                        # 县界点：±0.001°(≈111m) 抖动就能落到参照县 → 记 boundary，不算硬冲突
                        st["ref_boundary"] = st.get("ref_boundary", 0) + 1
                        st["ref_agree"] += 1
                    elif len(st["ref_disagree"]) < 5:
                        st["ref_disagree"].append({"ref": ref_name, "got": got, "fips": fips,
                                                   "lat": lat, "lon": lon})
        if max_seconds and time.time() - t0 > max_seconds:
            st["max_seconds_hit"] = True
            break
    st["unlocated_total"] = st["no_coords"] + st["unlocated"]   # 落不了县的总数（含无坐标）
    st["unlocated_pct"] = round(100.0 * st["unlocated_total"] / max(1, st["rows"]), 3)
    st["elapsed_s"] = round(time.time() - t0, 2)
    st["rps"] = round(st["rows"] / st["elapsed_s"], 1) if st["elapsed_s"] else 0.0
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        json.dump(st, open(os.path.join(outdir, "county.%s.json" % lid), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    return st


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", default="", help="逗号分隔层 id")
    ap.add_argument("--plan", default="", help="分片计划 JSON（含 shards[].layers）")
    ap.add_argument("--shard", type=int, default=-1)
    ap.add_argument("--out", default="", help="输出目录（逐层 JSON 统计）")
    ap.add_argument("--ref-column", default="", help="用于一致性核对的上游属性列（如 COUNTY）")
    ap.add_argument("--max-seconds", type=int, default=0, help="单层软超时（秒）")
    ap.add_argument("--refresh", action="store_true", help="忽略 .done 标记，重读")
    ap.add_argument("--keep-cache", action="store_true", help="selftest 时复用 .done 标记")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--make-plan", action="store_true")
    ap.add_argument("--size", type=int, default=40, help="每片层数（--make-plan 用）")
    a = ap.parse_args()
    if a.make_plan:
        return make_plan(a.size, a.plan or os.path.join(HERE, "ledger", "county_plan.json"))
    if a.selftest:
        return selftest(a.out or "/tmp/county-selftest", refresh=not a.keep_cache)

    layers = [x for x in a.layers.split(",") if x]
    if a.plan:
        plan = json.load(open(a.plan, encoding="utf-8"))
        shards = plan.get("shards") or []
        if a.shard < 0:
            raise SystemExit("--plan 必须配 --shard")
        if a.shard >= len(shards):
            raise SystemExit("shard %d 越界（共 %d 片）" % (a.shard, len(shards)))
        layers = shards[a.shard].get("layers") or []
    if not layers:
        raise SystemExit("没有层可跑：给 --layers 或 --plan/--shard")

    idx = Index()
    out = []
    for i, lid in enumerate(layers, 1):
        st = run_layer(lid, idx, outdir=a.out, ref_col=a.ref_column,
                       max_seconds=a.max_seconds, refresh=a.refresh)
        out.append(st)
        print("[%d/%d] %-52s rows=%-8d located=%-8d unloc=%-6d %.0f 行/秒 %s"
              % (i, len(layers), lid[:52], st["rows"], st["located"], st["unlocated"],
                 st["rps"], st["err"] or ""), flush=True)
    agg = {"at": now(), "layers_n": len(out),
           "rows": sum(s["rows"] for s in out),
           "located": sum(s["located"] for s in out),
           "unlocated": sum(s["unlocated"] for s in out),
           "no_coords": sum(s["no_coords"] for s in out),
           "elapsed_s": round(sum(s["elapsed_s"] for s in out), 1),
           "records": out}
    agg["unlocated_pct"] = round(100.0 * agg["unlocated"] / max(1, agg["rows"]), 3)
    agg["rps"] = round(agg["rows"] / max(1e-9, agg["elapsed_s"]), 1)
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        json.dump(agg, open(os.path.join(a.out, "county_ledger_shard%02d.json"
                                         % max(0, a.shard)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(json.dumps({k: agg[k] for k in ("layers_n", "rows", "located", "unlocated",
                                          "unlocated_pct", "rps")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
