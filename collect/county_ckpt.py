#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单县断点续跑 checkpoint（W2-018 / muse-000146 Phase 1a 第 4 片 · 第 11 项）。

目标：**单县失败/中断后只重跑该县，不整州重来。**

现状（本模块落地前的粒度，实测自仓内代码）：
  · 采集 `collect/pilot.py`：**单元级**（`_checkpoint.json` 的 `plan_hash + done_units`）
  · 判县 `collect/county_assign.py`：**层 × 资产级**（`collect/progress/county/<layer>/<asset>.done`）
  · 分片 `collect/full_shard.py`：**层级**（`skipped_done` 只看 release tag + checkpoint）
  · 单县 `run_intake_pipeline.py`：**阶段级**（`stage1-county.done` …）
  → 全链路**没有县粒度**。所以一个县坏掉（几何缺失 / 行级异常 / 上游该县 0 行）时，
    最小重跑单位是「整个层×资产」甚至「整片」。

当前重跑代价（实测 `collect/ledger/county_plan.json`）：
  858 层 / 1.34 亿行 / 22 片 → **每层均值 156,620 行**，最重的层上百万行。
  即：一个县坏掉，今天要连带重跑那 15.7 万行（以及该层的下载 + 判县 + 落盘），
  而不是只跑坏掉的那个县（一个县通常几百~几万行）。
  这就是 W2-018 要的差距。

本模块给的就是这个缺失的粒度：
  每县一条 checkpoint 记录
    {county_fips, state, status, started_at, finished_at, rows, source, attempt, fail_reason}
  落在**既有账本目录** `collect/ledger/`，命名沿用既有风格：`county_ckpt_<ST>.json`
  （与 `county_plan.json` / `county_shard<NN>.json` 同级同风格，不自造新目录）。

县内对象级续跑（muse-000146 第 11 项后补，本模块 v2 追加）：
  县是**最小调度单位**，但一个县也可能几十万行、上游翻页中途被打断。所以记录里再追加四个字段：
    last_objectid     已落盘到的最后一个上游对象 id（续跑从它之后接着拉，不从 0 重来）
    raw_fetched       本县已落盘行数
    declared_upstream 上游声明的本县行数
    sha256            本县已落盘分片（.part）的 sha256，用于续写前校验「接的是自己那份」
    updated_at        每次写盘刷成 UTC（上面 doc 级的同名头字段是整州时间戳）
  分片文件路径：`collect/ledger/county_part_<ST>/<fips>.part`（
  `part_path()`），县完成后自动删掉；断点县留着续写。
  口径：**raw_fetched == declared_upstream 才算该县完成**（与上面的 `rows >= expect_rows` 一致，
  前者是后者的具名版本）；已完成的县不会因为文件存在而重抓——跳过逻辑仍在 `pending_counties()`。

三条边界（违反即视为数据污染）：
  1. **同一州同一轮口径内才生效**：checkpoint 文件头带 `fingerprint` = 源文件指纹
     （几何缓存 / 计划 / 上游资产清单的 path+size+mtime_ns）。指纹不符 → `status` 全部作废、
     整个州重跑，**不许拿旧 checkpoint 冒充新数据**。
  2. **失败必须留痕**：`status=failed` + `fail_reason`，绝不是 done；续跑会重试该县。
  3. **`done` 只在行数对账后置位**：调用方给 `rows`，与 `expect_rows`（可空）比对，
     不达标记 `failed`（理由 `rows_mismatch`），不许静默当完成 —— 同 pilot.py W33-043 教训。

用法（两个定向入口）：
  python3 collect/county_ckpt.py --state NH --list                     # 看哪些县 done/failed/pending
  python3 collect/county_ckpt.py --state NH --counties 33011,33013     # **只跑**这两县（其余跳过）
  python3 collect/county_ckpt.py --state NH --force-counties 33011     # 强制重跑这两县（忽略 done）
  python3 collect/county_ckpt.py --state NH --reset                    # 整州作废
  python3 collect/county_ckpt.py --selftest                            # 自测（3 县中断场景 + 指纹失效）

作为库用（`run_counties` 是唯一调度入口）：
  from county_ckpt import run_counties, source_fingerprint
  run_counties("NH", counties, work=lambda fips: {...}, ledger_dir="collect/ledger",
               counties=["33011"], force=["33013"], fingerprint=source_fingerprint([...]))
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_LEDGER = os.path.join(ROOT, "collect", "ledger")

STATUS = ("pending", "running", "done", "failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ckpt_path(state: str, ledger_dir: str | None = None) -> str:
    """账本目录里的单州 checkpoint 文件名（沿用既有 ledger 命名风格）。"""
    return os.path.join(ledger_dir or DEFAULT_LEDGER, "county_ckpt_%s.json" % (state or "").upper())


def part_path(state: str, fips: str, ledger_dir: str | None = None) -> str:
    """单县分片文件路径：`<ledger>/county_part_<ST>/<fips>.part`。

    县内中断时这份文件里是已落盘的部分行，续跑从 `last_objectid` 之后接着 append；
    县完成后由 `run_counties_take_done()` 删掉（不留半成品混淆下游）。
    """
    return os.path.join(ledger_dir or DEFAULT_LEDGER,
                        "county_part_%s" % (state or "").upper(), "%s.part" % fips)


def source_fingerprint(paths) -> str:
    """源文件指纹：path + size + mtime_ns 的 sha1。

    任何源文件被重生成/替换 → 指纹变 → 旧 checkpoint 自动失效（边界 1）。
    `paths` 可以是 str 列表或 Path 列表；不存在的文件记 "missing"（本身也算指纹的一部分，
    这样「文件消失」同样会让旧 checkpoint 失效）。
    """
    h = hashlib.sha1()
    for p in sorted(str(x) for x in paths):
        try:
            st = os.stat(p)
            h.update(("%s|%d|%d\n" % (p, st.st_size, st.st_mtime_ns)).encode("utf-8"))
        except OSError:
            h.update(("%s|missing\n" % p).encode("utf-8"))
    return h.hexdigest()


def load(state: str, ledger_dir: str | None = None) -> dict:
    p = ckpt_path(state, ledger_dir)
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        doc = {}
    doc.setdefault("state", (state or "").upper())
    doc.setdefault("fingerprint", "")
    doc.setdefault("updated_at", "")
    doc.setdefault("counties", {})
    return doc


def save(doc: dict, ledger_dir: str | None = None) -> str:
    p = ckpt_path(doc.get("state") or "", ledger_dir)
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    doc["updated_at"] = now_iso()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)                      # 原子写：中断也不会留半截 JSON
    return p


def invalidate_if_stale(doc: dict, fingerprint: str) -> tuple[dict, str]:
    """指纹不符 → 把已有记录整体作废（保留在 `invalidated` 里供对账）。返回 (doc, reason)。"""
    if not fingerprint:
        return doc, ""
    if not doc.get("counties"):
        doc["fingerprint"] = fingerprint
        return doc, ""
    if doc.get("fingerprint") == fingerprint:
        return doc, ""
    old = doc.get("counties") or {}
    doc["invalidated"] = {"at": now_iso(), "old_fingerprint": doc.get("fingerprint") or "",
                          "counties": old}
    doc["counties"] = {}
    doc["fingerprint"] = fingerprint
    return doc, "source_fingerprint_changed(%s→%s)" % ((doc["invalidated"]["old_fingerprint"] or "?")[:8],
                                                      fingerprint[:8])


def begin(doc: dict, fips: str, state: str, source: str = "") -> dict:
    e = (doc.setdefault("counties", {})).setdefault(fips, {})
    e.update({"county_fips": fips, "state": (state or "").upper(), "status": "running",
              "started_at": now_iso(), "finished_at": "", "source": source or e.get("source") or "",
              "attempt": int(e.get("attempt") or 0) + 1, "fail_reason": ""})
    return e


def done(doc: dict, fips: str, rows: int, expect_rows: int | None = None,
         *, raw_fetched: int | None = None, declared_upstream: int | None = None,
         sha256: str = "", last_objectid=None) -> dict:
    """置 done（行数对账不过 → failed，边界 3）。

    `raw_fetched` / `declared_upstream` 是本县对象级续跑口径的具名别名：
      raw_fetched == declared_upstream 才算完成；缺一就记 failed(incomplete_upstream)。
    两者都没给时退回旧口径（rows vs expect_rows），向后兼容。
    """
    e = doc.setdefault("counties", {}).setdefault(fips, {})
    got = int(raw_fetched if raw_fetched is not None else (rows or 0))
    want = declared_upstream if declared_upstream is not None else expect_rows
    e.update({"raw_fetched": got, "declared_upstream": (None if want is None else int(want)),
              "sha256": str(sha256 or e.get("sha256") or ""),
              "updated_at": now_iso()})
    if last_objectid is not None:
        e["last_objectid"] = last_objectid
    if want is not None and got < int(want):
        return fail(doc, fips, "rows_mismatch: %d < %d" % (got, int(want)), rows=got)
    e.update({"status": "done", "rows": got, "finished_at": now_iso(), "fail_reason": ""})
    return e


def progress(doc: dict, fips: str, *, last_objectid=None, raw_fetched: int | None = None,
             declared_upstream: int | None = None, sha256: str = "", source: str = "") -> dict:
    """县内对象级断点：只改记录，不落盘（调用方自己 save）。

    典型用法（上游翻页循环里）：
        county_ckpt.progress(doc, fips, last_objectid=oid, raw_fetched=n,
                             declared_upstream=declared, sha256=part_sha256(part_path(...)))
        county_ckpt.save(doc, ledger_dir)          # 每 N 页落一次盘
    续跑时用 `resume_point(doc, fips)["last_objectid"] + 1` 作为起点。
    """
    e = doc.setdefault("counties", {}).setdefault(fips, {})
    e.setdefault("county_fips", fips)
    if e.get("status") != "done":
        e["status"] = "running"
    if last_objectid is not None:
        e["last_objectid"] = last_objectid
    if raw_fetched is not None:
        e["raw_fetched"] = int(raw_fetched)
    if declared_upstream is not None:
        e["declared_upstream"] = int(declared_upstream)
    if sha256:
        e["sha256"] = str(sha256)
    if source:
        e["source"] = str(source)
    e["updated_at"] = now_iso()
    return e


def resume_point(doc: dict, fips: str) -> dict:
    """取该县的续跑点（无记录 → 全空/0 起点）。

    返回 {fips, status, last_objectid, raw_fetched, declared_upstream, sha256, updated_at}。
    调用方拿 `last_objectid` 作上游游标起点、拿 `sha256` 校验 `.part` 是否还是自己那份。
    """
    e = (doc.get("counties") or {}).get(fips) or {}
    return {"fips": fips,
            "status": e.get("status") or "pending",
            "last_objectid": e.get("last_objectid"),
            "raw_fetched": int(e.get("raw_fetched") or e.get("rows") or 0),
            "declared_upstream": e.get("declared_upstream"),
            "sha256": e.get("sha256") or "",
            "updated_at": e.get("updated_at") or ""}


def resume_of(state: str, fips: str, ledger_dir: str | None = None) -> dict:
    """从磁盘读该州 checkpoint 再取续跑点（供 work 函数在无 doc 引用时用）。"""
    return resume_point(load(state, ledger_dir), fips)


def part_sha256(path: str) -> str:
    """分片文件的 sha256（不存在 → 空串）。"""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def drop_part(state: str, fips: str, ledger_dir: str | None = None) -> bool:
    """县完成后删掉分片（不存在 → False）。"""
    p = part_path(state, fips, ledger_dir)
    try:
        os.remove(p)
        return True
    except OSError:
        return False


def fail(doc: dict, fips: str, reason: str, rows: int | None = None) -> dict:
    """置 failed：**必须**留 fail_reason（边界 2），绝不静默当 done。"""
    e = doc.setdefault("counties", {}).setdefault(fips, {})
    e.update({"status": "failed", "finished_at": now_iso(),
              "fail_reason": str(reason or "unknown")[:300]})
    if rows is not None:
        e["rows"] = int(rows)
    return e


def pending_counties(doc: dict, counties: list[str], *, counties_only: list[str] | None = None,
                     force: list[str] | None = None) -> list[str]:
    """算出本轮该跑的县清单。

    · `counties_only`（`--counties`）：**定向点名** —— 只跑这些县（其余一律不动），
      且名单内一律重跑（不看 done）：「点名即重跑」，否则这个入口对已完成县毫无用处
    · `force`（`--force-counties`）：同上语义的显式写法（可与 `--counties` 并用，取并集）
    · 默认（两个都不给）：`status == done` 的跳过；其余（pending/running/failed/无记录）都跑
    """
    pool = [c for c in (counties or []) if not counties_only or c in set(counties_only)]
    forced = set(force or []) | (set(counties_only) if counties_only else set())
    recs = doc.get("counties") or {}
    out = []
    for c in pool:
        if c in forced:
            out.append(c)
            continue
        if (recs.get(c) or {}).get("status") == "done":
            continue                                   # ★ 默认跳过已完成县
        out.append(c)
    return out


def summary(doc: dict, counties: list[str]) -> dict:
    recs = doc.get("counties") or {}
    agg = {"total": len(counties or []), "done": 0, "failed": 0, "running": 0, "pending": 0}
    for c in counties or []:
        st = (recs.get(c) or {}).get("status") or "pending"
        agg[st if st in agg else "pending"] += 1
    agg["fail_reasons"] = {c: (recs.get(c) or {}).get("fail_reason")
                           for c in counties or [] if (recs.get(c) or {}).get("status") == "failed"}
    return agg


def _absorb_progress(doc: dict, state: str, ledger_dir: str | None = None) -> dict:
    """把 work 自己写进盘里的县内进度吸进内存 doc，防止被本轮覆盖掉。

    为什么必须有这一步：`work` 里常见的写法是自己 `load/progress/save` 三件套刷断点
    （子进程更只能走盘）。`run_counties` 手里的 doc 是进 county 之前读的旧快照，
    直接 `fail()`/`done()` 再 save 就会把 work 刚写的 `last_objectid` 抹掉 ——
    于是中断一次之后断点全丢，下次还是从头拉。这里只认「盘上更新」的进度字段，
    状态机仍由 run_counties 决定。
    """
    disk = load(state, ledger_dir)
    for fips, rec in (disk.get("counties") or {}).items():
        if not isinstance(rec, dict):
            continue
        cur = doc.setdefault("counties", {}).setdefault(fips, {})
        if (rec.get("updated_at") or "") < (cur.get("updated_at") or ""):
            continue                      # 盘上更旧：不用它覆盖
        for k in ("last_objectid", "raw_fetched", "declared_upstream", "sha256",
                  "updated_at", "rows", "fail_reason"):
            if k in rec and rec[k] not in (None, ""):
                cur[k] = rec[k]
    return doc


def run_counties(state: str, counties: list[str], work=None, *, ledger_dir: str | None = None,
                 counties_only: list[str] | None = None, force: list[str] | None = None,
                 fingerprint: str = "", source: str = "", expect_rows: dict | None = None,
                 work_with_resume=None, drop_part_on_done: bool = True,
                 log=None) -> dict:
    """**唯一调度入口**：按 checkpoint 决定跑哪些县，逐县调用 `work(fips)`。

    `work(fips) -> dict|int|None`：
      · dict：可含 `rows` / `raw_fetched` / `declared_upstream` / `sha256` /
              `last_objectid` / `source` / `expect_rows` / `error`
      · int ：视为 rows
      · None：视为 rows=0
      抛异常 → 该县记 failed（fail_reason=异常摘要），**不影响其他县**，异常不外抛
        （单县失败正是本模块要接住的东西；要整轮失败请调用方自己看 summary()["failed"]）。

    `work_with_resume(fips, resume) -> 同上`（可选，县内对象级续跑专用）：
      `resume` = `resume_point(doc, fips)`，含 `last_objectid` / `raw_fetched` /
      `declared_upstream` / `sha256`。给了它就不用 `work`。**两者都不给→ ValueError**。

    `drop_part_on_done=True`：该县跑成 done 后删掉 `county_part_<ST>/<fips>.part`。

    返回 summary(doc, counties) + `ran`（本轮实际跑的县）+ `skipped`（按 checkpoint 跳过的县）
      + `resumed`（其中带着非空 last_objectid 续跑的县）。
    """
    say = log or (lambda m: None)
    if work is None and work_with_resume is None:
        raise ValueError("run_counties 需要 work 或 work_with_resume 其中一个")
    doc = load(state, ledger_dir)
    doc, why = invalidate_if_stale(doc, fingerprint)
    if why:
        say("⚠ checkpoint 失效（%s）→ 整州重跑" % why)
    todo = pending_counties(doc, counties, counties_only=counties_only, force=force)
    skipped = [c for c in (counties or []) if c not in set(todo)]
    say("checkpoint: 待跑 %d 县 / 跳过 %d 县（state=%s）"
        % (len(todo), len(skipped), (state or "").upper()))
    resumed: list[str] = []
    for fips in todo:
        begin(doc, fips, state, source=source)
        save(doc, ledger_dir)                      # 先落 running：进程被杀也留痕
        rp = resume_point(doc, fips)
        if rp.get("last_objectid") is not None:
            resumed.append(fips)
            say("  ↺ %s 续跑：last_objectid=%r raw_fetched=%s%s"
                % (fips, rp["last_objectid"], rp["raw_fetched"],
                   "" if rp.get("declared_upstream") is None
                   else " declared_upstream=%s" % rp["declared_upstream"]))
        try:
            res = work_with_resume(fips, rp) if work_with_resume is not None else work(fips)
        except Exception as e:                     # noqa: BLE001
            _absorb_progress(doc, state, ledger_dir)   # work 可能已刷过断点，别覆盖
            fail(doc, fips, "%s: %s" % (type(e).__name__, str(e)[:200]))
            save(doc, ledger_dir)
            say("  ❌ %s 失败：%s" % (fips, (doc["counties"][fips] or {}).get("fail_reason")))
            continue
        if isinstance(res, dict):
            rows = res.get("rows", res.get("raw_fetched"))
            if res.get("error"):
                fail(doc, fips, res["error"], rows=rows)
                continue_done = False
            else:
                _absorb_progress(doc, state, ledger_dir)
                exp = res.get("expect_rows")
                if exp is None and expect_rows:
                    exp = expect_rows.get(fips)
                done(doc, fips, int(rows or 0), exp,
                     raw_fetched=res.get("raw_fetched"),
                     declared_upstream=res.get("declared_upstream"),
                     sha256=res.get("sha256") or "",
                     last_objectid=res.get("last_objectid"))
                continue_done = True
            if not continue_done:
                save(doc, ledger_dir)
                say("  ❌ %s 失败：%s" % (fips, doc["counties"][fips].get("fail_reason")))
                continue
            if res.get("source"):
                doc["counties"][fips]["source"] = res["source"]
        else:
            done(doc, fips, int(res or 0), (expect_rows or {}).get(fips))
        if drop_part_on_done and (doc["counties"][fips] or {}).get("status") == "done":
            drop_part(state, fips, ledger_dir)
        save(doc, ledger_dir)
    s = summary(doc, counties)
    s["ran"], s["skipped"], s["resumed"] = todo, skipped, resumed
    return s


# ------------------------------------------------------------------ 自测
def selftest() -> int:
    import tempfile
    ok = 0
    bad = 0

    def check(name, cond, extra=""):
        nonlocal ok, bad
        if cond:
            ok += 1
            print("  ✅ %s %s" % (name, extra))
        else:
            bad += 1
            print("  ❌ %s %s" % (name, extra))

    counties = ["33001", "33003", "33005"]
    tmp = tempfile.mkdtemp(prefix="ckpt-")
    src = os.path.join(tmp, "geom.json.gz")
    open(src, "wb").write(b"v1")
    fp1 = source_fingerprint([src])
    calls = []

    print("===== T1 3 县，第 2 县中断 =====")

    def work(fips):
        calls.append(fips)
        if fips == "33003":
            raise RuntimeError("杀进程/上游超时（模拟中断）")
        return {"rows": 100}

    s1 = run_counties("NH", counties, work, ledger_dir=tmp, fingerprint=fp1)
    check("第一次跑了 3 县", calls == ["33001", "33003", "33005"], str(calls))
    check("done=2 / failed=1", s1["done"] == 2 and s1["failed"] == 1,
          "done=%d failed=%d" % (s1["done"], s1["failed"]))
    check("失败县留了 fail_reason", bool(s1["fail_reasons"].get("33003")), str(s1["fail_reasons"])[:80])

    calls.clear()

    def work2(fips):
        calls.append(fips)
        return {"rows": 100}

    s2 = run_counties("NH", counties, work2, ledger_dir=tmp, fingerprint=fp1)
    check("第二次只跑第 2 县", calls == ["33003"], str(calls))
    check("另两县 0 次调用", "33001" not in calls and "33005" not in calls, str(calls))
    check("第二次后全 done", s2["done"] == 3 and s2["failed"] == 0,
          "done=%d failed=%d" % (s2["done"], s2["failed"]))
    check("跳过 2 县", sorted(s2["skipped"]) == ["33001", "33005"], str(s2["skipped"]))

    print("\n===== T2 源指纹变化 → checkpoint 失效全跑 =====")
    calls.clear()
    open(src, "wb").write(b"v2-upstream-republished")     # 源被重生成
    fp2 = source_fingerprint([src])
    check("指纹确实变了", fp1 != fp2, "%s → %s" % (fp1[:8], fp2[:8]))

    def work3(fips):
        calls.append(fips)
        return {"rows": 100}

    s3 = run_counties("NH", counties, work3, ledger_dir=tmp, fingerprint=fp2)
    check("指纹变化 → 3 县全跑", sorted(calls) == sorted(counties), str(calls))
    check("旧记录被作废", "invalidated" in load("NH", tmp), "")
    check("全 done 重新计", s3["done"] == 3, "done=%d" % s3["done"])

    print("\n===== T3 --counties 白名单 / --force-counties 强制 =====")
    calls.clear()
    run_counties("NH", counties, lambda f: calls.append(f) or {"rows": 1},
                 ledger_dir=tmp, fingerprint=fp2, counties_only=["33005"])
    check("--counties 只跑白名单（且不看 done）", calls == ["33005"], str(calls))

    calls.clear()
    run_counties("NH", counties, lambda f: calls.append(f) or {"rows": 1},
                 ledger_dir=tmp, fingerprint=fp2, force=["33001"])
    check("--force-counties 强制重跑", calls == ["33001"], str(calls))

    print("\n===== T4 行数对账不过 → failed（不许静默 done）=====")
    calls.clear()
    run_counties("NH", ["33007"], lambda f: {"rows": 3, "expect_rows": 10},
                 ledger_dir=tmp, fingerprint=fp2)
    d = load("NH", tmp)
    check("rows 不足记 failed", d["counties"]["33007"]["status"] == "failed",
          str(d["counties"]["33007"])[:100])
    check("fail_reason 是 rows_mismatch", "rows_mismatch" in (d["counties"]["33007"]["fail_reason"] or ""), "")

    print("\n总判定：%s（%d 通过 / %d 失败）"
          % ("✅ 全部通过" if not bad else "❌ 有失败", ok, bad))
    return 0 if not bad else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="", help="州缩写（如 NH）")
    ap.add_argument("--counties", default="", help="白名单：只跑这些县（逗号分隔）")
    ap.add_argument("--force-counties", default="", help="强制重跑这些县（忽略 done）")
    ap.add_argument("--ledger-dir", default="", help="账本目录（默认 collect/ledger）")
    ap.add_argument("--list", action="store_true", help="打印每县状态")
    ap.add_argument("--reset", action="store_true", help="作废整州 checkpoint")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    st = (a.state or "").upper()
    if not st:
        ap.error("--state 必填（或 --selftest）")
    doc = load(st, a.ledger_dir or None)
    if a.reset:
        doc["invalidated"] = {"at": now_iso(), "old_fingerprint": doc.get("fingerprint") or "",
                              "counties": doc.get("counties") or {}}
        doc["counties"] = {}
        p = save(doc, a.ledger_dir or None)
        print("已作废整州 checkpoint：%s" % p)
        return 0
    if a.list:
        print("== county_ckpt_%s.json（fingerprint=%s）==" % (st, (doc.get("fingerprint") or "?")[:12]))
        for fips, e in sorted((doc.get("counties") or {}).items()):
            print("  %s  %-8s attempt=%s rows=%s %s"
                  % (fips, e.get("status"), e.get("attempt"), e.get("rows"),
                     e.get("fail_reason") or ""))
        if not doc.get("counties"):
            print("  （空）")
        return 0
    only = [x.strip() for x in a.counties.split(",") if x.strip()]
    force = [x.strip() for x in a.force_counties.split(",") if x.strip()]
    print("state=%s counties=%s force=%s → 该跑的县：%s"
          % (st, only or "（全部）", force or "（无）",
             pending_counties(doc, sorted(doc.get("counties") or {}), counties_only=only or None,
                              force=force)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
