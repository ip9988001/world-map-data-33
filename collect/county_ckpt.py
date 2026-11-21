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


def done(doc: dict, fips: str, rows: int, expect_rows: int | None = None) -> dict:
    """置 done（行数对账不过 → failed，边界 3）。"""
    e = doc.setdefault("counties", {}).setdefault(fips, {})
    rows = int(rows or 0)
    if expect_rows is not None and rows < int(expect_rows):
        return fail(doc, fips, "rows_mismatch: %d < %d" % (rows, int(expect_rows)), rows=rows)
    e.update({"status": "done", "rows": rows, "finished_at": now_iso(), "fail_reason": ""})
    return e


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


def run_counties(state: str, counties: list[str], work, *, ledger_dir: str | None = None,
                 counties_only: list[str] | None = None, force: list[str] | None = None,
                 fingerprint: str = "", source: str = "", expect_rows: dict | None = None,
                 log=None) -> dict:
    """**唯一调度入口**：按 checkpoint 决定跑哪些县，逐县调用 `work(fips)`。

    `work(fips) -> dict|int|None`：
      · dict：可含 `rows` / `source` / `expect_rows` / `error`
      · int ：视为 rows
      · None：视为 rows=0
      抛异常 → 该县记 failed（fail_reason=异常摘要），**不影响其他县**，异常不外抛
        （单县失败正是本模块要接住的东西；要整轮失败请调用方自己看 summary()["failed"]）。

    返回 summary(doc, counties) + `ran`（本轮实际跑了的县）+ `skipped`（按 checkpoint 跳过的县）。
    """
    say = log or (lambda m: None)
    doc = load(state, ledger_dir)
    doc, why = invalidate_if_stale(doc, fingerprint)
    if why:
        say("⚠ checkpoint 失效（%s）→ 整州重跑" % why)
    todo = pending_counties(doc, counties, counties_only=counties_only, force=force)
    skipped = [c for c in (counties or []) if c not in set(todo)]
    say("checkpoint: 待跑 %d 县 / 跳过 %d 县（state=%s）"
        % (len(todo), len(skipped), (state or "").upper()))
    for fips in todo:
        begin(doc, fips, state, source=source)
        save(doc, ledger_dir)                      # 先落 running：进程被杀也留痕
        try:
            res = work(fips)
        except Exception as e:                     # noqa: BLE001
            fail(doc, fips, "%s: %s" % (type(e).__name__, str(e)[:200]))
            save(doc, ledger_dir)
            say("  ❌ %s 失败：%s" % (fips, (doc["counties"][fips] or {}).get("fail_reason")))
            continue
        if isinstance(res, dict):
            rows = res.get("rows")
            if res.get("error"):
                fail(doc, fips, res["error"], rows=rows)
                continue_done = False
            else:
                exp = res.get("expect_rows")
                if exp is None and expect_rows:
                    exp = expect_rows.get(fips)
                done(doc, fips, int(rows or 0), exp)
                continue_done = True
            if not continue_done:
                save(doc, ledger_dir)
                say("  ❌ %s 失败：%s" % (fips, doc["counties"][fips].get("fail_reason")))
                continue
            if res.get("source"):
                doc["counties"][fips]["source"] = res["source"]
        else:
            done(doc, fips, int(res or 0), (expect_rows or {}).get(fips))
        save(doc, ledger_dir)
    s = summary(doc, counties)
    s["ran"], s["skipped"] = todo, skipped
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
