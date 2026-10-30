#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 02 工人 —— 采集器（试点）

一个图层一个 job，只干活不报警。三种形态三套采法：
  FeatureServer / MapServer → keyset 游标翻页（OID 递增），不支持分页则 OID 区间切片
  Socrata                   → /resource/{id}.csv 分页
产出：
  collect/out/<layer>/part-XXXXX.ndjson.gz
  collect/out/<layer>/_manifest.json   （count / rows / diff / elapsed / err）

用法:
  python3 collect/pilot.py --layer ks911 [--limit 500]   # limit 用于 smoke
  python3 collect/pilot.py --list
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, math, os, random, re, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- v2.1：公共层已抽到 collect/lib/，这里保留同名引用（测试 patch pilot.xxx 仍生效）----
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import units                                      # noqa: E402
from lib.fetch import UA, get_json                      # noqa: E402
from lib.schema import (F_ADD, F_FULL, F_PRE, F_ST, F_SUF, F_POST, F_UNIT,  # noqa: E402
                        F_CITY, F_ZIP, F_ESN, pick, normalize)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, "collect", "pilot_layers.json")
OUTBASE = os.path.join(ROOT, "collect", "out")
CHUNK = 50000          # 每个 part 最多多少行
TARGET_BYTES = 2_000_000




# ---------------- 字段归一化 ----------------
def page_size_for(api):
    """自适应页大小：字段多就少给点，避免响应过大"""
    meta = get_json(api + "?f=json", timeout=25)
    nf = len(meta.get("fields") or [])
    maxrc = int(meta.get("maxRecordCount") or 1000)
    ps = min(maxrc, 2000)
    if nf > 120:
        ps = min(ps, 200)
    elif nf > 60:
        ps = min(ps, 500)
    return ps, maxrc, meta


def collect_arcgis(url, limit=0, log=print):
    global GEOM_TYPE
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", url.rstrip("/"))
    api = url.split("?")[0].rstrip("/")
    if m and not m.group(2):
        api += "/0"
    ps, maxrc, meta = page_size_for(api)
    GEOM_TYPE = str(meta.get("geometryType") or "")      # 老路径同样认面层，不许两套行为
    oid_field = meta.get("objectIdField") or meta.get("objectIdFieldName")
    if not oid_field:
        # ★ 2026-10-23 san_juan：MapServer 的 objectIdField 为 null，实际主键叫 FID。
        #   原来直接兜底 "OBJECTID" → orderByFields=OBJECTID 报 400 → 只拿到第一页 2000 行。
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        oid_field = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID", "OBJECTID_12")
                          if k in fns), "OBJECTID")
    count = int((meta.get("definitionExpression") and 0) or 0)
    cnt = get_json(api + "/query?where=1%3D1&returnCountOnly=true&f=json", timeout=60)
    count = int(cnt.get("count") or 0)
    defexpr = meta.get("definitionExpression") or ""
    where0 = defexpr if defexpr else "1=1"
    log(f"  api={api} count={count} pagesize={ps} defexpr={bool(defexpr)}")

    rows = 0
    last_oid = None
    part_no = 0
    buf = []
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    def flush():
        nonlocal buf, part_no
        if not buf:
            return
        p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for r in buf:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        log(f"  part {part_no}: {len(buf)} rows -> {os.path.basename(p)}")
        part_no += 1
        buf = []

    while True:
        where = where0 if last_oid is None else f"{oid_field}>{last_oid}"
        if defexpr:
            where = f"({defexpr}) AND {where}" if last_oid is not None else defexpr
        q = {"where": where, "outFields": "*", "returnGeometry": "true",
             "outSR": "4326", "f": "json", "resultRecordCount": ps,
             "orderByFields": oid_field}
        if POLY_CENTROID and geom_is_poly():
            q["returnCentroid"] = "true"
        u = api + "/query?" + urllib.parse.urlencode(q)
        d = get_json(u, timeout=180)
        if "__error__" in d:
            return rows, count, "query_fail:" + d["__error__"], part_no
        feats = d.get("features") or []
        if not feats:
            if rows == 0 and not d.get("exceededTransferLimit"):
                # 首查空但 count>0：去掉排序/游标再试一次（有的服务不支持 orderBy）
                q2 = {"where": where0, "outFields": "*", "returnGeometry": "true",
                      "outSR": "4326", "f": "json"}
                d2 = get_json(api + "/query?" + urllib.parse.urlencode(q2), timeout=180)
                feats = (d2.get("features") or []) if "__error__" not in d2 else []
                if not feats:
                    return rows, count, "", part_no
            else:
                break
        for ft in feats:
            a = ft.get("attributes") or {}
            rec = make_rec(ft)
            buf.append(rec)
            rows += 1
            oid = a.get(oid_field)
            if oid is None:
                for k in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                    if k in a:
                        oid = a[k]
                        break
            if oid is not None:
                last_oid = oid
        if len(buf) >= CHUNK:
            flush()
        if limit and rows >= limit:
            break
        if not d.get("exceededTransferLimit") and len(feats) < ps:
            break
        if last_oid is None:      # 没有 OID 字段，退化为 offset 翻页
            break
        time.sleep(0.15)
    flush()
    return rows, count, "", part_no


def collect_socrata(url, limit=0, log=print):
    m = re.search(r"https?://([^/]+)/d/([a-z0-9]{4}-[a-z0-9]{4})", url)
    if not m:
        return 0, 0, "bad_socrata_url", 0
    host, did = m.group(1), m.group(2)
    cnt = get_json("https://%s/resource/%s.json?$select=count(1)" % (host, did), timeout=60)
    try:
        count = int(list(cnt[0].values())[0])
    except Exception:
        count = 0
    rows = part_no = 0
    buf = []
    step = 20000
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    off = 0
    while True:
        u = "https://%s/resource/%s.json?$limit=%d&$offset=%d" % (host, did, step, off)
        d = get_json(u, timeout=120)
        if not isinstance(d, list) or not d:
            break
        for a in d:
            rec = normalize(a, a.get("latitude"), a.get("longitude"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": a})
            buf.append(rec)
            rows += 1
        off += len(d)
        if len(buf) >= CHUNK:
            p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
            with gzip.open(p, "wt", encoding="utf-8") as f:
                for r in buf:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            log(f"  part {part_no}: {len(buf)} rows")
            part_no += 1
            buf = []
        if limit and rows >= limit:
            break
        if len(d) < step:
            break
    if buf:
        p = os.path.join(OUTBASE, CUR["id"], "part-%05d.ndjson.gz" % part_no)
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for r in buf:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        part_no += 1
    return rows, count, "", part_no


CUR = {}


# =============== v2：并行采集（按 OID 区间切片） ===============
# 为什么能并行：分页是 OID 键集游标（WHERE oid > last ORDER BY oid），
# 把 oid 的 [min,max] 切成 N 段，各段独立跑同一套循环 → 段间不重叠、不加锁、不丢行。
# 计费：逻辑放在同一个 job 内的线程池，不是 matrix —— Actions 按 job 墙钟计费，
#       8 个 job 各 25 分钟 = 200 分钟；1 个 job 8 线程 25 分钟 = 25 分钟。
PROG_DIR = os.path.join(ROOT, "collect", "progress")
TS = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# ---- 断点续传底座已移到 lib/units.py，这里保留同名薄包装（显式传 outbase/进度目录）----
def _ckpt_path():
    return units.ckpt_path(OUTBASE, CUR["id"])


def _save_ckpt(ck):
    return units.save_ckpt(ck, OUTBASE, CUR["id"])


def _load_ckpt(plan_hash):
    return units.load_ckpt(plan_hash, OUTBASE, CUR["id"], CUR.get("url"), CKPT_VER)


def _write_progress(prog):
    return units.write_progress(prog, OUTBASE, PROG_DIR)


def _purge(files):
    return units.purge(files)


def _record_unit(ck, idx, rows, files):
    out = units.record_unit(ck, idx, rows, files)
    # 真实落盘字节记账（估算可能偏；超 1.5 GB 的单元进明账，不打断采集）
    try:
        b = sum(os.path.getsize(f) for f in files if os.path.exists(f))
        ck.setdefault("unit_bytes", {})[str(idx)] = b
        if b > UNIT_BYTES:
            ck.setdefault("unit_bytes_over", {})[str(idx)] = b
            log("  ⚠ 单元 u%d 落盘 %.2f GB > 1.5 GB 上限（已记账，建议下次按小页重切）"
                % (idx, b / 1e9))
    except Exception:                                  # noqa: BLE001
        pass
    return out


def _q(api, params, timeout=180):
    return get_json(api + "/query?" + urllib.parse.urlencode(params), timeout=timeout)


def _git(args, timeout=90):
    try:
        r = subprocess.run(["git", "-C", ROOT] + args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)[:120]


def _oid_bounds(api, oid_field):
    """取 min/max OID；拿不到就返回 None（调用方退回单线程，绝不猜）"""
    q = {"where": "1=1", "f": "json", "outStatistics": json.dumps([
        {"statisticType": "min", "onStatisticField": oid_field, "outStatisticFieldName": "mn"},
        {"statisticType": "max", "onStatisticField": oid_field, "outStatisticFieldName": "mx"}])}
    d = _q(api, q, timeout=90)
    if "__error__" in d:
        return None, None, d["__error__"]
    try:
        at = (d.get("features") or [{}])[0].get("attributes") or {}
        if at.get("mn") is None or at.get("mx") is None:
            return None, None, "no_min_max"
        return int(at["mn"]), int(at["mx"]), ""
    except Exception as e:
        return None, None, str(e)[:80]




def _push_progress(prog, log):
    """心跳进仓库（只为一个目的：长尾层能被 curl 看到，不用等 job 结束）。
       失败不致命 —— 心跳是辅助证据，不能因为它把数据 job 干掉。"""
    rel = "collect/progress/%s.json" % prog["id"]
    for i in range(3):
        _git(["add", "-f", rel])
        rc, out = _git(["-c", "user.name=collect-bot", "-c", "user.email=bot@users.noreply.github.com",
                        "commit", "-q", "-m", "progress: %s %s/%s" % (prog["id"], prog["rows"], prog["count"])])
        if rc != 0 and "nothing to commit" not in out:
            time.sleep(2)
            continue
        _git(["fetch", "-q", "origin", "main"])
        rc2, _ = _git(["rebase", "-q", "origin/main"])
        if rc2 != 0:
            _git(["rebase", "--abort"])
            time.sleep(2 * (i + 1))
            continue
        rc3, out3 = _git(["push", "-q", "origin", "HEAD:main"])
        if rc3 == 0:
            log("  ♥ progress pushed %s/%s" % (prog["rows"], prog["count"]))
            return True
        time.sleep(2 * (i + 1))
    log("  ♥ progress 推送失败（不影响采集）")
    return False


def _heartbeat(prog, lock, stop, log, interval=20, push_every=None):
    # ★ 2026-10-24：100 个并行 job 每 3 分钟各推一次 main，报告 job 连推 5 次全被拒。
    #   现在默认 6 分钟 + 0~120 秒随机抖动，把推送打散。
    push_every = push_every or int(os.environ.get("PILOT_HEARTBEAT_EVERY", "360"))
    do_push = os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("PILOT_HEARTBEAT_PUSH", "1") != "0"
    last_push = time.time() - random.uniform(0, 120)
    while not stop.is_set():
        try:
            with lock:
                snap = dict(prog)
                _write_progress(snap)
            if do_push and time.time() - last_push >= push_every:
                _push_progress(snap, log)
                last_push = time.time()
        except Exception as e:
            log("  ♥ heartbeat err %s" % str(e)[:80])
        stop.wait(interval)


# 面层（Polygon/Polyline）必须落质心 —— 2026-10-30 结构性回归的修复。
# ★ 事实：`normalize()` 只吃 (attrs, lat, lon)，rings 在采集瞬间就被丢掉；1,038 个宗地层
#   因此「有行无坐标」，下游县判定与坐标补齐全部卡死，只能整层重采（代价 = 全部行）。
# ★ 现在默认开（PILOT_POLY_CENTROID=1）：
#   ① 请求 returnCentroid=true（服务端质心，outSR=4326 = WGS84）
#   ② returnGeometry=true 回来的 rings 在本地算 representative_point（凹多边形/带洞 → 扫描线
#      最宽内区间中点，见 parcel_centroid.representative_point），优先于服务端质心
#   ③ 每行落 `_lat`/`_lon`（与 NAD 口径同名），rings 本身仍不落盘；raw 保留 Shape__Area/Length
#   ④ （2026-10-30 第 ② 档拍定）面层每行**再落一份简化 rings**（`PILOT_POLY_RINGS`）
# 点层不受影响：返回结果没有 rings/centroid，`_lat/_lon` 就是 geometry.y/.x 的同值副本。
POLY_CENTROID = os.environ.get("PILOT_POLY_CENTROID", "1") == "1"
POLY_GEOMS = ("esrigeometrypolygon", "esrigeometrypolyline")
GEOM_TYPE = ""          # collect_arcgis_v2 从图层元数据填，面层判定用

# ---- 面层 rings 落盘（第 ② 档：6 位小数 + RDP 1e-5°）
# 为什么现在才落：之前 rings 在采集瞬间就被丢掉，1,038 个宗地层「有行无坐标」，
# 且**全 1,238 个宗地层都没有边界** —— 跨县宗地只能用质心判县，邻接/边界复算只能重采。
# 为什么只落简化版：20 层上游实测，原始 rings 多出来的是 1e-14° 的投影尾数（+5.2 GB 买亚微米）。
# 口径常量只有一处：`parcel_centroid.SIMP_EPS / SIMP_DECIMALS`（不另写一套）。
POLY_RINGS = os.environ.get("PILOT_POLY_RINGS", "1") == "1"
RING_GEOMS = ("esrigeometrypolygon",)      # 只对面：`rings` 是面的概念，线层的 `paths` 不冒充

# ---- 非宗地面判别（2026-10-30）----
# 20 层实测里混着 5 个「不是宗地」的面：Buildings_2024、Buffer1000、Santee…Buffer、
# sullins_buffer、Offices_of_Physicians（还有 Shoreline/Demographic_Profiles）。
# 它们的几何是缓冲区/楼轮廓、顶点均值远超真宗地，落 rings 纯属烧 0.6 GB。
# 判据（两条同时满足才算）：① 图层名/字段里**没有** parcel|lot|property|tax|situs 语义；
#                        ② 采样顶点均值 > 50 × 真宗地中位（9.75 → 阈值 487.5）。
# 命中 → 本层只落质心，不落 rings，每行记 `rings_skipped="non_parcel"`（明账，不是静默丢）。
NON_PARCEL_TOKENS = ("parcel", "lot", "property", "tax", "situs")
# 层名里的「明显不是宗地」硬负词：缓冲区/楼轮廓/岸线/细分/人口画像/写字楼
# （实测：Buffer1000 顶点只有 124 = 12.7 倍中位，够不上 50 倍，但形状明显不是宗地）
NON_PARCEL_NAME_TOKENS = ("buffer", "building", "footprint", "shoreline", "subdiv",
                          "demographic", "office", "sewer", "basin", "flowline", "road")
PARCEL_VERTEX_MEDIAN = 9.75          # 20 层实测的每宗地顶点中位
NON_PARCEL_VERTEX_RATIO = 50.0       # > 50 倍中位 = 几何形状完全不是宗地
RINGS_SKIP = ""                      # "" 正常；"non_parcel" = 本层只留质心


def is_non_parcel(vertices_mean: float, fields=(), names=()) -> bool:
    """非宗地面判别（纯函数，可单测）。命中 → 该层不落 rings，只落质心。

    两档，任一命中即算（都要先满足「没有 parcel/lot/property/tax/situs 语义」）：
      ① 几何档：顶点均值 > 50 × 真宗地中位（9.75 → 487.5）—— 形状根本不是宗地；
      ② 名称档：层名带 buffer|building|footprint|shoreline|subdiv|demographic|office… ——
         实测这类层（Buffer1000 124 顶点、Santee buffer 218、sullins 128）够不上 50 倍，
         但落 rings 毫无用途。两档都只在「无宗地语义」时才成立，宁可多存不误杀。
    """
    toks = []
    toks.extend(str(x) for x in (names or ()))
    for f in (fields or ()):
        toks.append(str((f or {}).get("name") or ""))
    blob = " ".join(toks).lower()
    if any(t in blob for t in NON_PARCEL_TOKENS):
        return False                 # 有宗地语义 → 哪怕几何也重，按宗地处理
    if float(vertices_mean or 0) > PARCEL_VERTEX_MEDIAN * NON_PARCEL_VERTEX_RATIO:
        return True
    return any(t in blob for t in NON_PARCEL_NAME_TOKENS)


def geom_is_poly():
    """当前图层是不是面/线层（决定要不要 returnCentroid + 本地算质心）。"""
    return str(GEOM_TYPE or "").lower() in POLY_GEOMS


def geom_has_rings():
    """当前图层要不要落 rings（只有面层）。"""
    return POLY_RINGS and str(GEOM_TYPE or "").lower() in RING_GEOMS
STRATEGY = "keyset"
CKPT_VER = 2
UNIT_ROWS = int(os.environ.get("PILOT_UNIT_ROWS", "500000"))   # 一个「单元」的**行数**上限（参考值）
# ★ 2026-10-30 全局修正：GitHub 单资产 2 GB —— 只按行数切会撞线。
#   实测 `Offices_of_Physicians` 32.6 KB/行 × 10 万行 = 3.26 GB（宗地层），点层同理
#   （有些层一行带几十个字段/超长串）。所以切分改成**行数 且 字节**双上限，先到先切：
#   字节 = 估算值（见 `estimate_bytes_per_row`）+ 余量，落盘后再用真实字节记账，超线进明账。
UNIT_BYTES = int(os.environ.get("PILOT_UNIT_BYTES", "1500000000"))   # 1.5e9 B = 1.5 GB
UNIT_BYTES_MARGIN = float(os.environ.get("PILOT_UNIT_BYTES_MARGIN", "1.4"))  # 估算余量
IDS_BATCH = 800                                                # 单次 objectIds 请求最多多少个


# ---------------- 断点续传的底座：单元 / 检查点 / 分批发 ----------------
def _tag():
    """Release tag：由 workflow 传入（collect-<run>-<layer>），本地跑则用 local- 前缀。"""
    return os.environ.get("PILOT_RELEASE_TAG") or ("collect-local-%s" % CUR["id"])








def _pub(cmd, timeout=600):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, ((r.stdout or "") + (r.stderr or ""))[:300]
    except Exception as e:
        return 1, str(e)[:200]


def _upload(files, log, tag=None):
    """把一个单元的 part 打成 tar 传上 Release。成功返回 True；失败只记证据，不抛。"""
    tag = tag or _tag()
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return False
    rep = os.environ.get("GITHUB_REPOSITORY")
    if not rep:
        log("  ↑ 非 CI 环境，跳过上传（%d 个 part）" % len(files))
        return False
    d = os.path.dirname(files[0])
    uid = os.path.basename(files[0]).split("-")[1] if "-" in os.path.basename(files[0]) else "x"
    name = "%s-%s.tar.gz" % (CUR["id"], uid)
    tmp = os.path.join("/tmp", name)
    rc, o = _pub(["tar", "czf", tmp, "-C", d] + [os.path.basename(f) for f in files])
    if rc != 0:
        log("  ✗ 打包失败 %s" % o[:120])
        return False
    rc, o = _pub(["gh", "release", "create", tag, "--repo", rep,
                  "--title", "采集 %s（分批发）" % CUR["id"], "--notes", "unit upload", tmp])
    if rc != 0:
        rc, o = _pub(["gh", "release", "upload", tag, tmp, "--repo", rep, "--clobber"])
    try:
        os.remove(tmp)
    except Exception:
        pass
    if rc != 0:
        log("  ✗ 上传失败 %s" % o[:150])
        return False
    log("  ↑ 已发布 %s（%d 个 part）" % (name, len(files)))
    return True


def _publish_ckpt(ck, log):
    """把检查点本身也传上 Release（同一个 tag，--clobber 覆盖）。
       没有这一步，断点续传只在「同一个 job 内重启」有效；换一次 run 就归零。"""
    rep = os.environ.get("GITHUB_REPOSITORY")
    if not rep:
        return False
    tmp = "/tmp/%s-checkpoint.json" % CUR["id"]
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ck, f, ensure_ascii=False)
    except Exception:
        return False
    rc, o = _pub(["gh", "release", "upload", _tag(), tmp, "--repo", rep, "--clobber"], timeout=180)
    if rc != 0:
        log("  ✗ 检查点上传失败 %s" % o[:120])
    return rc == 0


def _fetch_ckpt_asset(plan_hash, log):
    """本地没有检查点（新 run）→ 从 Release 把上一轮的检查点捞回来。"""
    rep = os.environ.get("GITHUB_REPOSITORY")
    if not rep:
        return None
    name = "%s-checkpoint.json" % CUR["id"]
    rc_v, _ = _pub(["gh", "release", "view", _tag(), "--repo", rep], timeout=60)
    if rc_v != 0:
        return None          # tag 还不存在 = 本层第一次跑，正常，不是错误
    d = "/tmp/ck_%s" % CUR["id"]
    os.makedirs(d, exist_ok=True)
    pth = os.path.join(d, name)
    rc, o = _pub(["gh", "release", "download", _tag(), "-p", name, "-D", d, "--clobber"], timeout=180)
    if rc != 0 or not os.path.exists(pth):
        log("⚠️ 检查点下载失败（tag 存在但取不到）：%s → 本轮从头采" % o[:100])
        return None
    try:
        d2 = json.load(open(pth, encoding="utf-8"))
    except Exception:
        return None
    if d2.get("ver") != CKPT_VER or d2.get("plan_hash") != plan_hash or d2.get("url") != CUR.get("url"):
        log("  ⟲ 上一轮检查点与本次切分不一致 → 忽略")
        return None
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    _save_ckpt(d2)
    log("  ⟲ 已从 Release 恢复检查点：%d 个单元已完成" % len(d2.get("done_units") or []))
    return d2


def _probe_pagination(api, log):
    """探针：有的 MapServer 直接报 `Pagination is not supported.`，
       那种服务只能走 ids 通道（一次拿全量 objectIds，再按批取记录）。"""
    r = _q(api, {"where": "1=1", "resultRecordCount": "1", "f": "json"}, timeout=60)
    e = str(r.get("__error__") or "")
    if "pagination" in e.lower():
        return False, "服务不支持分页(Pagination is not supported)"
    if "__error__" in r:
        return False, e[:100]
    return True, ""






# ---------------- 单元采集 ----------------
def poly_point(geom):
    """面层取一个「落在实心区内」的点 → (lat, lon) 或 None。

    ArcGIS JSON 不是 GeoJSON：面是 `rings`，线是 `paths`。面走 representative_point
    （先面积加权质心，质心落在多边形外/洞里才退回扫描线最宽内区间中点）；线没有面积，
    取最长 path 的中点。纯 stdlib，不依赖 pyproj；几何缺失/退化 → None（调用方退回服务端质心）。
    """
    if not geom:
        return None
    try:
        import parcel_centroid as PC
    except Exception:                                  # noqa: BLE001
        return None
    rings = geom.get("rings")
    if not rings:
        paths = [p for p in (geom.get("paths") or []) if len(p or []) >= 3]
        if not paths:
            return None
        mid = max(paths, key=len)[len(max(paths, key=len)) // 2]
        try:
            return (float(mid[1]), float(mid[0]))
        except Exception:                              # noqa: BLE001
            return None
    try:
        p = PC.representative_point(rings)
    except Exception:                                  # noqa: BLE001
        return None
    if not p:
        return None
    try:
        lon, lat = float(p[0]), float(p[1])
    except Exception:                                  # noqa: BLE001
        return None
    if not (-180.0 <= lon <= -60.0 and 15.0 <= lat <= 72.0):
        return None                                    # outSR 没生效/几何是投影坐标 → 不猜
    return (lat, lon)


def feature_latlon(ft, geom_type=""):
    """一条 feature → (lat, lon, 来源)。来源：rep_point / centroid / geometry。"""
    g = ft.get("geometry") or {}
    want_poly = POLY_CENTROID and str(geom_type or "").lower() in POLY_GEOMS
    if want_poly:
        p = poly_point(g)
        if p:
            return p[0], p[1], "rep_point"
    lat, lon = g.get("y"), g.get("x")
    if lat is None and want_poly:
        cen = ft.get("centroid") or {}
        if cen:
            return cen.get("y"), cen.get("x"), "centroid"
    return lat, lon, "geometry"


def feature_rings(ft, geom_type=""):
    """一条面要素 → 可落盘的简化 rings（列表）或 None。

    退化几何（环 <3 个不同点 / 坐标转不成 float）→ None，**不猜、不补、不拿 bbox 代替**。
    线层不走这里（`rings` 是面的概念；线层保持不落几何）。
    """
    gt = str(geom_type if geom_type is not None else GEOM_TYPE or "").lower()
    if not POLY_RINGS or gt not in RING_GEOMS:
        return None
    try:
        import parcel_centroid as PC
    except Exception:                                  # noqa: BLE001
        return None
    try:
        return PC.simplify_rings((ft.get("geometry") or {}).get("rings"))
    except Exception:                                  # noqa: BLE001
        return None


def make_rec(ft, geom_type=None):
    """一条 feature → 一条落盘记录（三条采集路径共用的唯一入口）。

    契约（单测护着 `test_pilot_centroid_contract.py`）：
      · `_lat`/`_lon` 恒存在（算不出就是 None）—— 面层能不能判县全看这两个键
      · 面层额外落 `rings`（简化版，默认开）：每行必有该**键**；退化/算不出就是 None
      · 点层/线层不带 `rings` 键（不冒充面几何，也不白占字节）
      · `raw` 保留全部属性（Shape__Area/Shape__Length 不丢）
    """
    at = ft.get("attributes") or {}
    gt = geom_type if geom_type is not None else GEOM_TYPE
    lat, lon, _src = feature_latlon(ft, gt)
    rec = normalize(at, lat, lon)
    rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": at,
                "_lat": lat, "_lon": lon})
    if POLY_RINGS and str(gt or "").lower() in RING_GEOMS:
        if RINGS_SKIP:
            rec["rings_skipped"] = RINGS_SKIP         # 例如 "non_parcel"：明账，不是静默丢
        else:
            rec["rings"] = feature_rings(ft, gt)      # 键必在：None = 几何退化，不是没采
    return rec


def estimate_bytes_per_row(api, where, n=40, log=None):
    """抓一小页真数据，量「一行落盘后多少字节」（含 rings）—— 切分计划要用它。

    只取 n 行（默认 40），不写盘、不影响断点。返回 (bytes_per_row, mean_vertices, n_rows)。
    量的是 `make_rec()` 的序列化长度，不是上游原样 JSON —— 落盘体积才是 GitHub 的约束。
    """
    q = {"where": where, "outFields": "*", "returnGeometry": "true",
         "outSR": "4326", "resultRecordCount": min(200, n), "f": "json"}
    if POLY_CENTROID and geom_is_poly():
        q["returnCentroid"] = "true"        # 采样请求要和正式请求完全同参，否则估小
    try:
        r = _q(api, q, timeout=90)
        feats = (r.get("features") or [])[:n]
    except Exception:                                  # noqa: BLE001
        return 0, 0.0, 0
    if not feats:
        return 0, 0.0, 0
    tot, verts = 0, []
    for ft in feats:
        try:
            rec = make_rec(ft)
            tot += len(json.dumps(rec, ensure_ascii=False).encode())
        except Exception:                              # noqa: BLE001
            continue
        rings = (ft.get("geometry") or {}).get("rings")
        if rings:
            verts.append(sum(len(x) for x in rings))
    bpr = tot / float(len(feats))
    vmean = (sum(verts) / float(len(verts))) if verts else 0.0
    if log and bpr:
        log("  估计：%.0f B/行（含 rings），平均顶点 %.1f" % (bpr, vmean))
    return bpr, vmean, len(feats)


def plan_units(count, mn, mx, bytes_per_row=0, unit_rows=None, unit_bytes=None,
               margin=None, kind="range"):
    """切分计划：**行数上限 且 字节上限**，先到先切。返回 (units, rows_cap)。

    为什么单单行数不够：GitHub 单个 Release 资产上限 2 GB，某些层一行就 30 KB，
    10 万行 = 3.26 GB（实测 `Offices_of_Physicians`）→ 必须同时按字节收。
    估算不确定（行大小有长尾），所以给 `margin` 余量；落盘后再用真实字节记账。
    """
    unit_rows = UNIT_ROWS if unit_rows is None else unit_rows
    unit_bytes = UNIT_BYTES if unit_bytes is None else unit_bytes
    margin = UNIT_BYTES_MARGIN if margin is None else margin
    cap = int(unit_rows)
    if bytes_per_row and bytes_per_row > 0:
        by_bytes = int(unit_bytes / (float(bytes_per_row) * float(margin)))
        cap = max(1, min(cap, by_bytes))
    if kind == "range":
        n_units = max(1, int(math.ceil((count or 0) / float(cap)))) if count else 1
        span = max(1, int(math.ceil(((mx or 0) - (mn or 0) + 1) / float(n_units))))
        units, a0 = [], mn
        while a0 is not None and mx is not None and a0 <= mx:
            units.append((a0, min(a0 + span - 1, mx)))
            a0 += span
        return (units or [(None, None)]), cap
    return None, cap


def plan_sig(plan):
    """检查点签名：**只认决定切分的字段**（kind + units [+ ids 的批参数]）。

    ★ 2026-10-30 踩过：把整个 plan 字典丟进 sha1，只要多加一个纯展示字段
      （bytes_per_row_est / unit_bytes_cap / rings_skipped …）签名就全变 →
      已有 checkpoint 全部认不得 → 续跑静默变成「从头重采」，97.9M 行的 NAD 层
      要重拉一遍。切分只由 kind+units 决定，签名就只该看这两个。
      旧 format（plan 里只有 kind+units）算出来的 sha1 与新规则完全一致，
      所以这个函数对历史 checkpoint 是向后兼容的。
    """
    core = {"kind": plan.get("kind"), "units": plan.get("units")}
    if plan.get("kind") == "ids":
        core["n_ids"] = plan.get("n_ids")
        core["batch"] = plan.get("batch")
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:16]


def resume_todo(units, ck):
    """续跑该跑哪些单元：返回 (已真完成, 必须重采)。

    ★ done_units 只代表「这单元跑到了末尾」，**不代表产物进了 Release**。
      2026-10-30 实测：NAD 全国层 64 单元全标完成，6 个 -uNNNNN.tar.gz 根本没上传
      （unit_uploaded=false）。新 runner 上本地文件已不在，补传不可能成功 ——
      若继续按 done_units 跳过，这 6 个单元的行就永久缺口（账本还会显示 ok？不，
      账本从资产反推会显示 failed，但永远补不上）。所以：产物没上传的单元一律重采。
    """
    done = {int(x) for x in (ck.get("done_units") or [])}
    up = {}
    for k, v in (ck.get("unit_uploaded") or {}).items():
        try:
            up[int(k)] = bool(v)
        except (TypeError, ValueError):
            continue
    n_units = len(units or [])
    # 重切片后 plan 变短 → 旧 done_units 里越界的下标一律丢掉，别让它们混进计数
    done = {i for i in done if 0 <= i < n_units}
    # 老 checkpoint 可能整段没有 unit_uploaded 字段：**不据此判定「没传」**
    # （否则一次续跑会把几十个已完成单元全部重采）；真缺产物的由账本按资产反查抓到，
    # 再用 full_shard --force-layers 定点重跑 —— 两条路各管一段，不互相假装。
    redone = {i for i in done if up.get(i) is False}
    return sorted(done - redone), sorted(redone)


def _unit_range(api, oid_field, defexpr, lo, hi, idx, ps, limit, log, prog, lock, ck):
    """一个 OID 区间单元。返回 (rows, files, err)。"""
    conds = []
    if defexpr:
        conds.append("(%s)" % defexpr)
    if lo is not None:
        conds.append("%s>=%s" % (oid_field, lo))
    if hi is not None:
        conds.append("%s<=%s" % (oid_field, hi))
    w0 = " AND ".join(conds) or "1=1"
    c = _q(api, {"where": w0, "returnCountOnly": "true", "f": "json"}, timeout=90)
    try:
        expect = int(c.get("count") or 0)
    except Exception:
        expect = 0
    base = {"where": w0, "outFields": "*", "returnGeometry": "true", "outSR": "4326", "f": "json"}
    if POLY_CENTROID and geom_is_poly():
        base["returnCentroid"] = "true"          # 服务端质心 = 本地算不出来时的兜底
    d = os.path.join(OUTBASE, CUR["id"])
    os.makedirs(d, exist_ok=True)
    if expect == 0:
        return 0, [], "", 0
    if limit:                       # 试采：把页大小压到 limit，别一次拉回 2000 行
        ps = max(1, min(ps, limit))
    rows = part_no = 0
    buf, last, off, mode = [], None, 0, "keyset"
    files = []

    def flush():
        nonlocal buf, part_no
        if not buf:
            return
        p = os.path.join(d, "part-u%05d-%03d.ndjson.gz" % (idx, part_no))
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for r in buf:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        files.append(p)
        part_no += 1
        buf = []

    while True:
        if mode == "keyset":
            w = w0 if last is None else "%s AND %s>%s" % (w0, oid_field, last)
            q = dict(base, where=w, resultRecordCount=ps, orderByFields=oid_field)
        else:
            q = dict(base, resultOffset=off, resultRecordCount=ps, orderByFields=oid_field)
        r = _q(api, q)
        if "__error__" in r:
            flush()
            return rows, files, "query_fail:" + str(r["__error__"])[:160], expect
        feats = r.get("features") or []
        if not feats:
            if rows == 0 and last is None and mode == "keyset":
                q2 = {k: v for k, v in q.items() if k != "orderByFields"}
                r = _q(api, q2)
                feats = r.get("features") or []
            if not feats:
                # keyset 翻不动（服务端把「主键>n」当空条件）但 count 没拿够 → 换 resultOffset 续翻
                if mode == "keyset" and rows > 0 and rows < expect:
                    mode, off = "offset", rows
                    log("  u%d keyset 停在 %d/%d → 切 resultOffset" % (idx, rows, expect))
                    continue
                break
        for ft in feats:
            at = ft.get("attributes") or {}
            rec = make_rec(ft)
            buf.append(rec)
            rows += 1
            oid = at.get(oid_field)
            if oid is None:
                for k in ("OBJECTID", "OBJECTID_1", "FID", "OID"):
                    if k in at:
                        oid = at[k]
                        break
            if oid is not None:
                last = oid
        if len(buf) >= CHUNK:
            flush()
        with lock:
            prog["workers"][str(idx)] = rows
            prog["rows"] = prog.get("base_rows", 0) + sum(prog["workers"].values())
        if limit and rows >= limit:
            break
        if mode == "offset":
            off += len(feats)
        if not r.get("exceededTransferLimit") and len(feats) < ps:
            break
        time.sleep(0.1)
    flush()
    return rows, files, "", expect


def _unit_ids(api, batches, idx, log, prog, lock, limit=0):
    """一个 ids 单元（若干 objectIds 批，顺序取）。返回 (rows, files, err)。"""
    d = os.path.join(OUTBASE, CUR["id"])
    os.makedirs(d, exist_ok=True)
    rows, files, errs = 0, [], []
    for bi, batch in batches:
        q = {"objectIds": ",".join(str(x) for x in batch), "outFields": "*",
             "returnGeometry": "true", "outSR": "4326", "f": "json"}
        if POLY_CENTROID and geom_is_poly():
            q["returnCentroid"] = "true"
        r = _q(api, q)
        if "__error__" in r:
            errs.append("batch%d:%s" % (bi, str(r["__error__"])[:120]))
            continue
        recs = []
        for ft in (r.get("features") or []):
            recs.append(make_rec(ft))
        if limit and rows + len(recs) > limit:      # --limit 试采：多出来的直接裁掉
            recs = recs[:max(0, limit - rows)]
        if not recs:
            continue
        p = os.path.join(d, "part-u%05d-b%05d.ndjson.gz" % (idx, bi))
        with gzip.open(p, "wt", encoding="utf-8") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        files.append(p)
        rows += len(recs)
        with lock:
            prog["workers"][str(idx)] = rows
            prog["rows"] = prog.get("base_rows", 0) + sum(prog["workers"].values())
        if limit and rows >= limit:
            break
    expect = sum(len(b[1]) for b in batches)
    if limit:
        expect = min(expect, limit)
    return rows, files, (";".join(errs) if errs else ""), expect


def collect_arcgis_v2(url, limit=0, log=print, workers=1, fresh=False):
    global STRATEGY, UNIT_ROWS, GEOM_TYPE, RINGS_SKIP
    RINGS_SKIP = ""
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", url.rstrip("/"))
    api = url.split("?")[0].rstrip("/")
    if m and not m.group(2):
        api += "/0"
    ps, maxrc, meta = page_size_for(api)
    GEOM_TYPE = str(meta.get("geometryType") or "")
    if POLY_CENTROID and geom_is_poly():
        log("  面层（%s）→ 质心开：rings 就地算 representative_point，落 _lat/_lon" % GEOM_TYPE)
    oid_field = meta.get("objectIdField") or meta.get("objectIdFieldName")
    if not oid_field:
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        oid_field = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID", "OBJECTID_12")
                          if k in fns), "OBJECTID")
    defexpr = meta.get("definitionExpression") or ""
    w_all = "(%s)" % defexpr if defexpr else "1=1"
    cnt = get_json(api + "/query?where=1%3D1&returnCountOnly=true&f=json", timeout=60)
    count = int(cnt.get("count") or 0)

    ok_page, why = _probe_pagination(api, log)
    STRATEGY = "keyset" if ok_page else "ids"
    log("  api=%s count=%d pagesize=%d workers=%d strategy=%s%s"
        % (api, count, ps, workers, STRATEGY, "" if ok_page else "（%s）" % why))

    # ---- 切分方案（决定断点能不能续：切分必须确定） ----
    ids, units, plan = None, [], {}
    if STRATEGY == "ids":
        r_ids = _q(api, {"where": w_all, "returnIdsOnly": "true", "f": "json"}, timeout=180)
        ids = r_ids.get("objectIds") or []
        if not ids:
            log("  returnIdsOnly 失败（%s）→ 退回 keyset" % str(r_ids.get("__error__"))[:80])
            STRATEGY = "keyset"
    if STRATEGY == "ids":
        bpr_ids, _vm, _n = estimate_bytes_per_row(api, w_all, log=log)
        _u, cap_ids = plan_units(len(ids), 0, 0, bytes_per_row=bpr_ids, kind="ids")
        bl, cur = [], []
        for i in range(0, len(ids), IDS_BATCH):
            cur.append((i // IDS_BATCH, ids[i:i + IDS_BATCH]))
            if len(cur) * IDS_BATCH >= cap_ids:
                bl.append(cur)
                cur = []
        if cur:
            bl.append(cur)
        units = bl
        plan = {"kind": "ids", "n_ids": len(ids), "batch": IDS_BATCH,
                "units": [[b[0] for b in u] for u in units],
                "bytes_per_row_est": round(bpr_ids, 1), "unit_bytes_cap": UNIT_BYTES,
                "unit_rows_cap": cap_ids}
    else:
        mn, mx, e = _oid_bounds(api, oid_field) if workers > 1 or count > UNIT_ROWS else (None, None, "small")
        if mn is not None and mx is not None and mx > mn:
            bpr, vmean, _n = estimate_bytes_per_row(api, w_all, log=log)
            units, cap = plan_units(count, mn, mx, bytes_per_row=bpr, kind="range")
            if cap < UNIT_ROWS:
                log("  ⚠ 按字节切：行数上限 %d → %d（估 %.0f B/行 × 余量 %.1f，1.5 GB/单元）"
                    % (UNIT_ROWS, cap, bpr, UNIT_BYTES_MARGIN))
            if POLY_RINGS and geom_is_poly():
                skip = "non_parcel" if is_non_parcel(
                    vmean, fields=meta.get("fields") or (),
                    names=(CUR.get("id"), CUR.get("title"))) else ""
                globals()["RINGS_SKIP"] = skip
                if skip:
                    log("  ⏭ 判为非宗地面（顶点均值 %.0f > %.0f 且层名/字段无 parcel 语义）"
                        "→ 只落质心，不落 rings" % (vmean, PARCEL_VERTEX_MEDIAN * NON_PARCEL_VERTEX_RATIO))
            plan = {"kind": "range", "units": units, "bytes_per_row_est": round(bpr, 1),
                    "unit_bytes_cap": UNIT_BYTES, "unit_rows_cap": cap,
                    "vertices_mean_est": round(vmean, 1),
                    "rings_skipped": RINGS_SKIP or None}
        else:
            units = [(None, None)]
            plan = {"kind": "single", "units": [[None, None]], "unit_bytes_cap": UNIT_BYTES,
                    "unit_rows_cap": UNIT_ROWS}

    if limit:
        # --limit 是试采用：只跑一个单元、单线程、忽略既有检查点，免得 5 个单元各采 limit 行
        units, workers, fresh = units[:1], 1, True
    plan_hash = plan_sig(plan)
    ck = None if fresh else _load_ckpt(plan_hash)
    if ck is None and not fresh:
        ck = _fetch_ckpt_asset(plan_hash, log)
    done = set()
    if ck:
        done = set(ck.get("done_units") or [])
        log("  ⟲ 续跑：检查点签名 %s，已完成单元 %d/%d（%s 行）"
            % (plan_hash, len(done), len(units), sum((ck.get("unit_rows") or {}).values())))
        # 已完成但没传上去的，先补传（本地文件还在的话）
        for k, fs in (ck.get("unit_files") or {}).items():
            if int(k) in done and ck.get("unit_uploaded", {}).get(str(k)) is False:
                paths = [os.path.join(OUTBASE, CUR["id"], f) for f in fs]
                if all(os.path.exists(p) for p in paths) and _upload(paths, log):
                    ck.setdefault("unit_uploaded", {})[str(k)] = True
                    _purge(paths)
                    _save_ckpt(ck)
        # 补传不成的（新 runner 上文件本来就不在）→ 重采，不拿 done_units 当挡箭牌
        done, redone = resume_todo(units, ck)
        if redone:
            log("  ⚠ 检查点里 %d 个单元标了完成但产物没上传，本轮重采：%s"
                % (len(redone), ",".join(str(i) for i in redone[:8])))
    else:
        ck = {"ver": CKPT_VER, "url": CUR.get("url"), "plan_hash": plan_hash,
              "unit_rows": {}, "unit_files": {}, "unit_uploaded": {},
              "done_units": [], "tag": _tag()}
    ck.setdefault("unit_uploaded", {})
    ck.setdefault("unit_rows", {})
    ck.setdefault("unit_files", {})

    base_rows = sum((ck.get("unit_rows_seen") or ck.get("unit_rows") or {}).values())
    prog = {"id": CUR["id"], "ts": TS(), "api": api, "count": count,
            "base_rows": base_rows, "rows": base_rows,
            "parts": sum(len(v) for v in ck["unit_files"].values()), "workers": {},
            "strategy": STRATEGY, "units": len(units), "done_units": len(done),
            "unit_rows_target": UNIT_ROWS, "done": False}
    lock = threading.Lock()
    up_lock = threading.Lock()
    stop = threading.Event()
    _set_prog(prog)
    hb = threading.Thread(target=_heartbeat, args=(prog, lock, stop, log), daemon=True)
    hb.start()
    rows_new, errs = 0, []
    todo = [(i, u) for i, u in enumerate(units) if i not in done]

    def one(i, u):
        if STRATEGY == "ids":
            rows, files, err, expect = _unit_ids(api, u, i, log, prog, lock, limit)
        else:
            lo, hi = u
            rows, files, err, expect = _unit_range(api, oid_field, defexpr, lo, hi, i, ps,
                                                   limit, log, prog, lock, ck)
        # ① 无错 ② 行数对得上（--limit 试采不判）③ 上传成功 —— 三条同时成立才算完成
        if not err and not limit and expect > 0 and rows < expect * 0.999:
            err = "short:%d/%d" % (rows, expect)
        ok = False
        if files:                      # 数据先落地：哪怕这个单元还不算完成，拿到的行也是真的
            with up_lock:
                ok = _upload(files, log)
        snap = None
        with lock:
            ck.setdefault("unit_uploaded", {})[str(i)] = bool(ok)
            ck.setdefault("unit_rows_seen", {})[str(i)] = rows   # 采到的行如实记账（不管是否算完成）
            if err.startswith("short:"):
                # 上游真实缺失：同一单元连续两次 short 且行数一致 → 认可，不再无限重试
                st = ck.setdefault("unit_short_tries", {}).setdefault(str(i), {"n": 0, "rows": -1})
                if st["rows"] == rows:
                    st["n"] += 1
                else:
                    st["rows"], st["n"] = rows, 1
                if st["n"] >= 2:
                    ck.setdefault("unit_short_ack", {})[str(i)] = rows
                    err = ""
            done_ok = (not err) and (ok or not files)
            if done_ok:
                _record_unit(ck, i, rows, files)
                ck.setdefault("unit_errors", {}).pop(str(i), None)
            else:
                ck.setdefault("unit_errors", {})[str(i)] = (err or "upload_failed")[:200]
            _save_ckpt(ck)
            snap = json.loads(json.dumps(ck))
            if done_ok:
                _purge(files)
        if done_ok:
            _publish_ckpt(snap, log)   # 锁外：上传检查点不再阻塞采集线程
        return rows, (err or "")

    try:
        if len(todo) == 1 or workers <= 1:
            for i, u in todo:
                r_, e_ = one(i, u)
                rows_new += r_
                if e_:
                    errs.append(e_)
        else:
            with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
                futs = [ex.submit(one, i, u) for i, u in todo]
                for f in as_completed(futs):
                    r_, e_ = f.result()
                    rows_new += r_
                    if e_:
                        errs.append(e_)
    finally:
        with lock:
            rows_total = sum((ck.get("unit_rows_seen") or ck.get("unit_rows") or {}).values())
            prog["rows"] = rows_total
            prog["done"] = True
            prog["done_units"] = len(ck.get("done_units") or [])
            _write_progress(prog)
            _save_ckpt(ck)
        stop.set()
    parts = sum(len(v) for v in (ck.get("unit_files") or {}).values())
    resumed = len(done)
    if resumed and not errs:
        log("  ⟲ 本次续跑：跳过 %d 个已完成单元，新采 %d 行" % (resumed, rows_new))
    return sum((ck.get("unit_rows_seen") or ck.get("unit_rows") or {}).values()), count, \
        (";".join(errs) if errs else ""), parts


def verdict(rows, count, err, limit=0):
    """工人退出码判据（可单测）。

    「采到 99% 但没报错」以前会返回 0 = 绿灯，正是 de_suss 空包能混过去的原因。
    现在：行数不齐也判失败，阈值用绝对+相对双阈值（至少容 1 行，避免小层误杀）。
    --limit 试采不判（否则 smoke 必红）。
    """
    if count == 0 and not err:
        return 0, ""
    short = (not limit) and count > 0 and rows < count - max(1, count // 1000)
    if err or rows <= 0 or short:
        return 1, ("short:%d/%d" % (rows, count)) if short else ""
    return 0, ""


# ---------------- 无进展看门狗 ----------------
# 2026-10-24 事故：STEP-04 有一层（MapServer + keyset）跑了 91 分钟、一个单元都没上传，
# 只能人工 cancel。并行度一高这种空转最贵，所以让工人自己判死自己。
STALL_MIN = int(os.environ.get("PILOT_STALL_MIN", "12"))
_PROG = {"p": None}
_WD = {"at": time.time()}


def _set_prog(prog):
    _PROG["p"] = prog
    _WD["at"] = time.time()


def _watchdog(log, stall_min=None):
    stall = (stall_min or STALL_MIN) * 60
    last = None
    while True:
        time.sleep(30)
        p = _PROG.get("p")
        if not p:
            continue
        sig = (p.get("parts"), p.get("rows"), p.get("done"))
        if sig != last:
            last = sig
            _WD["at"] = time.time()
        elif time.time() - _WD["at"] > stall:
            log("❌ 无进展 %d 分钟（parts=%s rows=%s，共 %s 单元）→ 主动退出，记为 no_progress"
                % (stall // 60, p.get("parts"), p.get("rows"), p.get("units")))
            sys.stdout.flush()
            os._exit(3)


def _start_watchdog(log):
    th = threading.Thread(target=_watchdog, args=(log,), daemon=True)
    th.start()
    return th


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=int(os.environ.get("PILOT_WORKERS", "1")))
    ap.add_argument("--unit-rows", type=int, default=int(os.environ.get("PILOT_UNIT_ROWS", "500000")))
    ap.add_argument("--fresh", action="store_true", help="忽略检查点，从头重采")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--cfg", help="图层配置文件（默认 collect/pilot_layers.json）")
    a = ap.parse_args()
    cfg = json.load(open(a.cfg or CFG, encoding="utf-8"))
    if a.list:
        for x in cfg:
            print("%-10s %-10s %10s  %s" % (x["id"], x["svc"], x.get("expect"), x["title"][:50]))
        return 0
    L = [x for x in cfg if x["id"] == a.layer]
    if not L:
        print("unknown layer"); return 2
    global UNIT_ROWS
    UNIT_ROWS = a.unit_rows
    CUR.update(L[0])
    os.makedirs(os.path.join(OUTBASE, CUR["id"]), exist_ok=True)
    t0 = time.time()
    log = lambda m: print("[%s] %s" % (CUR["id"], m), flush=True)
    log("start %s" % CUR["url"][:90])
    _start_watchdog(log)
    if CUR["svc"] in ("FeatureServer", "MapServer"):
        rows, count, err, parts = collect_arcgis_v2(CUR["url"], a.limit, log, a.workers, a.fresh)
    elif CUR["svc"] == "Socrata":
        rows, count, err, parts = collect_socrata(CUR["url"], a.limit, log)
    else:
        rows, count, err, parts = 0, 0, "unsupported_svc", 0
    elapsed = round(time.time() - t0, 1)
    diff = round(abs(rows - count) / count, 4) if count else None
    man = {"id": CUR["id"], "title": CUR["title"], "url": CUR["url"], "svc": CUR["svc"],
           "count": count, "rows": rows, "parts": parts, "diff": diff,
           "elapsed_s": elapsed, "err": err, "limit": a.limit, "strategy": STRATEGY,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(os.path.join(OUTBASE, CUR["id"], "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(ROOT, "collect", "reports"), exist_ok=True)
    with open(os.path.join(ROOT, "collect", "reports", CUR["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    log("done rows=%d count=%d diff=%s err=%s %.1fs" % (rows, count, diff, err or "-", elapsed))
    if count == 0 and not err:
        log("empty layer（count=0），按空层处理，不算失败")
        return 0
    code, short = verdict(rows, count, err, a.limit)
    if short:
        log("❌ 数据不齐 rows=%d count=%d（缺 %.2f%%）" % (rows, count, 100.0 * (count - rows) / max(count, 1)))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
