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
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", url.rstrip("/"))
    api = url.split("?")[0].rstrip("/")
    if m and not m.group(2):
        api += "/0"
    ps, maxrc, meta = page_size_for(api)
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
            g = (ft.get("geometry") or {})
            rec = normalize(a, g.get("y"), g.get("x"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": a})
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
    return units.record_unit(ck, idx, rows, files)


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


STRATEGY = "keyset"
CKPT_VER = 2
UNIT_ROWS = int(os.environ.get("PILOT_UNIT_ROWS", "500000"))   # 一个「单元」目标行数
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
            g = ft.get("geometry") or {}
            rec = normalize(at, g.get("y"), g.get("x"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": at})
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
        r = _q(api, q)
        if "__error__" in r:
            errs.append("batch%d:%s" % (bi, str(r["__error__"])[:120]))
            continue
        recs = []
        for ft in (r.get("features") or []):
            at = ft.get("attributes") or {}
            g = ft.get("geometry") or {}
            rec = normalize(at, g.get("y"), g.get("x"))
            rec.update({"src_layer": CUR["id"], "src_title": CUR["title"], "raw": at})
            recs.append(rec)
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
    global STRATEGY, UNIT_ROWS
    m = re.search(r"/(FeatureServer|MapServer)(/\d+)?$", url.rstrip("/"))
    api = url.split("?")[0].rstrip("/")
    if m and not m.group(2):
        api += "/0"
    ps, maxrc, meta = page_size_for(api)
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
        bl, cur = [], []
        for i in range(0, len(ids), IDS_BATCH):
            cur.append((i // IDS_BATCH, ids[i:i + IDS_BATCH]))
            if len(cur) * IDS_BATCH >= UNIT_ROWS:
                bl.append(cur)
                cur = []
        if cur:
            bl.append(cur)
        units = bl
        plan = {"kind": "ids", "n_ids": len(ids), "batch": IDS_BATCH,
                "units": [[b[0] for b in u] for u in units]}
    else:
        mn, mx, e = _oid_bounds(api, oid_field) if workers > 1 or count > UNIT_ROWS else (None, None, "small")
        if mn is not None and mx is not None and mx > mn:
            n_units = max(1, int(math.ceil(count / float(UNIT_ROWS)))) if count else 1
            span = max(1, int(math.ceil((mx - mn + 1) / float(n_units))))
            a0 = mn
            while a0 <= mx:
                units.append((a0, min(a0 + span - 1, mx)))
                a0 += span
            plan = {"kind": "range", "units": units}
        else:
            units = [(None, None)]
            plan = {"kind": "single", "units": [[None, None]]}

    if limit:
        # --limit 是试采用：只跑一个单元、单线程、忽略既有检查点，免得 5 个单元各采 limit 行
        units, workers, fresh = units[:1], 1, True
    plan_hash = hashlib.sha1(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:16]
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
