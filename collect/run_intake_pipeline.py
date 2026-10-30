#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全流程编排（后台、串行、每一阶段断点可续）—— 判县 → 全量 intake → 实体台账 → 基线文档

五段，严格串行，任何一段跑完就落标记文件；重跑同一命令 = 从下一个未完成段开始。

  ① 等判县跑完        county_assign.py（不抢 CPU，只轮询；完了再做一次补跑 + --summary --doc）
  ② 全量 intake 逐层   intake_full.py tables（每层 ledger.json status=ok 即跳过，天然断点可续）
  ③ 三张实体台账       intake_full.py build（addr/nohouse → SQLite 重建，主键去重 + 并集 + sources[]）
  ④ 基线文档 + 页面    intake_full.py pages --doc docs/ENTITY-BASELINE-2026-10-30.md（pages.csv 前 10 万行）
  ⑤ 收尾              写 intake-pipeline.finished（时间 + 关键计数）

边界：
  · 不访问上游（release 快照读本机 dist/intake-full/release-index.json；缺了才由 intake_full 自己拉）
  · 不改三仓 main，不 push（数据提交另行人工决定）
  · 台账口径不变：主键去重 + 并集 + sources[]，**不按源累加**

启动（必须脱离会话，别在前台等）：
  setsid nohup python3 collect/run_intake_pipeline.py >> /data/logs/intake-pipeline.log 2>&1 < /dev/null &
查看进度：
  cat /data/workspace/wmd33/current-stage ; ls /data/workspace/wmd33
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = "/data/workspace/wmd33"                    # 标记文件目录（用户指定路径所在）
LOG = "/data/logs/intake-pipeline.log"

sys.path.insert(0, HERE)
import county_assign as CA                          # noqa: E402  （复用 is_done / safe_name，不另抄口径）

PLAN_COUNTY = os.path.join(HERE, "ledger", "county_plan_all.json")
DOC_COUNTY = os.path.join(ROOT, "docs", "COUNTY-ASSIGN-2026-10-30.md")
DOC_ENTITY = os.path.join(ROOT, "docs", "ENTITY-BASELINE-2026-10-30.md")
INTAKE_OUT = os.path.join(ROOT, "dist", "intake-full")
INTAKE_PY = os.path.join(HERE, "intake_full.py")

# 五个标记文件（按序落；存在即该段已完成）
M = {
    1: os.path.join(STATE, "stage1-county.done"),
    2: os.path.join(STATE, "stage2-intake-tables.done"),
    3: os.path.join(STATE, "stage3-entity-build.done"),
    4: os.path.join(STATE, "stage4-doc-pages.done"),
    5: os.path.join(STATE, "intake-pipeline.finished"),
}
STAGE_FILE = os.path.join(STATE, "current-stage")

POLL = 60                     # 轮询间隔（秒）
MAX_COUNTY_PASSES = 3         # 判县补跑上限（partial/no_assets 层补跑几次就不再纠缠）
MAX_INTAKE_PASSES = 2         # intake 重跑上限（第一次跑 + 一次补 failed）
FROZEN_RESUME = True          # 卡在 SIGSTOP 的 intake 进程先 SIGCONT 续跑，而不是杀掉重来


# ---------------------------------------------------------------- 基础设施
def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print("[%s] %s" % (now(), msg), flush=True)


def run(cmd: list[str], check: bool = True) -> int:
    """同步跑子进程，输出直接进本进程 stdout（= 编排日志）。"""
    log("RUN %s" % " ".join(cmd))
    t0 = time.time()
    rc = subprocess.call(cmd, cwd=ROOT)
    log("EXIT %d (%.0fs) %s" % (rc, time.time() - t0, " ".join(cmd[:4])))
    if check and rc != 0:
        raise SystemExit("子进程失败 rc=%d：%s" % (rc, " ".join(cmd)))
    return rc


def pgrep(pattern: str) -> list[int]:
    """按命令行子串找进程（不含自己）。"""
    me = {os.getpid(), os.getppid()}
    try:
        out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout
    except FileNotFoundError:                        # 没有 pgrep 就退化成 ps
        out = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True).stdout
        return [int(l.split()[0]) for l in out.splitlines()
                if pattern in l and int(l.split()[0]) not in me]
    pids = []
    for line in out.split():
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid not in me:
            pids.append(pid)
    return pids


def proc_state(pid: int) -> str:
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().split(")")[-1].split()[0]
    except Exception:                               # noqa: BLE001
        return "?"


def marker_says(stage: int) -> bool:
    return os.path.exists(M[stage])


def mark(stage: int, payload: dict) -> None:
    os.makedirs(STATE, exist_ok=True)
    rec = {"stage": stage, "at": now(), "pid": os.getpid(), "log": LOG}
    rec.update(payload or {})
    tmp = M[stage] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.replace(tmp, M[stage])                       # 原子落盘：半截标记 = 没完成
    log("标记 → %s" % M[stage])
    for k, v in (payload or {}).items():
        log("    %s = %s" % (k, v))


def set_stage(text: str) -> None:
    os.makedirs(STATE, exist_ok=True)
    with open(STAGE_FILE, "w", encoding="utf-8") as f:
        f.write("%s\t%s\n" % (now(), text))
    log("阶段 → %s" % text)


# ---------------------------------------------------------------- ① 等判县
def county_plan_layers() -> list[str]:
    with open(PLAN_COUNTY, encoding="utf-8") as f:
        plan = json.load(f)
    return [lid for s in (plan.get("shards") or []) for lid in (s.get("layers") or [])]


def county_remaining() -> tuple[int, int]:
    """(未完成层数, 已完成层数) —— 口径复用 county_assign.is_done，不另抄。"""
    out = os.path.join(ROOT, "analysis", "tiger_county")
    todo = ok = 0
    for lid in county_plan_layers():
        p = os.path.join(out, "rows-%s.json" % CA.safe_name(lid))
        if os.path.exists(p):
            try:
                rec = json.load(open(p, encoding="utf-8"))
            except Exception:                        # noqa: BLE001
                rec = {}
            if CA.is_done(rec):
                ok += 1
                continue
        todo += 1
    return todo, ok


def county_summary() -> dict:
    """写 analysis/county-assign-summary.json + docs/COUNTY-ASSIGN-*.md（幂等，纯本机）。"""
    rc = run([sys.executable, os.path.join(HERE, "county_assign.py"), "--summary",
              "--plan", PLAN_COUNTY, "--out", os.path.join(ROOT, "analysis", "tiger_county"),
              "--doc", DOC_COUNTY], check=False)
    p = os.path.join(ROOT, "analysis", "county-assign-summary.json")
    if rc != 0 or not os.path.exists(p):
        log("⚠️ 判县汇总没出来（rc=%d），不阻塞后续段" % rc)
        return {"summary_ok": False}
    s = json.load(open(p, encoding="utf-8"))
    return {"summary_ok": True, "layers": s.get("layers_total"),
            "rows": s.get("rows"), "located": s.get("located"),
            "unlocated_pct": s.get("unlocated_pct")}


def stage1_county() -> dict:
    set_stage("① 等判县跑完（county_assign 仍在跑就只轮询，不抢 CPU）")
    passes, t0 = 0, time.time()
    while True:
        pids = pgrep("county_assign.py")
        if pids:
            todo, ok = county_remaining()
            log("判县仍在跑：pid=%s，进度 %d 完成 / %d 待跑，已等 %.0f 分钟" %
                (",".join(map(str, pids[:3])), ok, todo, (time.time() - t0) / 60))
            time.sleep(POLL)
            continue
        todo, ok = county_remaining()
        if todo and passes < MAX_COUNTY_PASSES:
            passes += 1
            log("判县进程已退出，但还有 %d 层未完成 → 第 %d 次补跑（断点续跑，已完成的会跳过）"
                % (todo, passes))
            run([sys.executable, os.path.join(HERE, "county_assign.py"), "--plan", PLAN_COUNTY,
                 "--concurrency", "8", "--out", os.path.join(ROOT, "analysis", "tiger_county")],
                check=False)
            continue
        break
    todo, ok = county_remaining()
    log("判县收尾：完成 %d 层，剩 %d 层（补跑 %d 次）" % (ok, todo, passes))
    extra = county_summary()
    return {"county_layers_done": ok, "county_layers_todo": todo,
            "county_passes": passes, "waited_min": round((time.time() - t0) / 60, 1), **extra}


# ---------------------------------------------------------------- ② 全量 intake
def _cmdline(pid: int) -> str:
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            return f.read().replace(b"\0", b" ").decode("utf-8", "replace")
    except Exception:                                # noqa: BLE001
        return ""


def _argv0(pid: int) -> str:
    try:
        with open("/proc/%d/cmdline" % pid, "rb") as f:
            return f.read().split(b"\0")[0].decode("utf-8", "replace")
    except Exception:                                # noqa: BLE001
        return ""


def intake_py_pids() -> list[int]:
    """真正在写 dist/intake-full 的 python 进程。

    **必须按 argv[0] 判断**：历史上同一个会话留下过几层 bash 包装进程（命令行里也含
    `intake_full.py tables`，其中一个是 `rm -rf dist/intake-full/layers` + 重启），
    它们卡在 T 状态永远不退出 —— 按子串匹配会：① 编排永远等不到头；② SIGCONT 时
    把 `rm -rf` 那条唤醒，直接抹掉已经跑完的层。
    """
    out = []
    for pid in pgrep("intake_full.py"):
        a0 = os.path.basename(_argv0(pid))
        if not a0.startswith("python"):
            continue
        if "rm -rf" in _cmdline(pid):
            continue
        out.append(pid)
    return out


def resume_frozen_tables() -> int:
    """被打 SIGSTOP 的 intake 进程先 SIGCONT：续跑比杀掉重来省几十分钟。

    只碰 **python 解释器本体**（见 intake_py_pids 里的解释）。
    """
    if not FROZEN_RESUME:
        return 0
    n = 0
    for pid in intake_py_pids():
        if proc_state(pid) in ("T", "t"):
            try:
                os.kill(pid, signal.SIGCONT)
                n += 1
            except Exception:                        # noqa: BLE001
                pass
    if n:
        log("SIGCONT 恢复了 %d 个被暂停的 intake 进程" % n)
    return n


def intake_progress() -> dict:
    p = os.path.join(INTAKE_OUT, "intake-progress.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:                               # noqa: BLE001
        return {}


def stage2_intake() -> dict:
    set_stage("② 全量 intake 逐层（tables，逐层 ledger 断点续跑）")
    resume_frozen_tables()
    # 有别的 intake 在跑就等它（同一份输出目录不许两个进程写）
    while True:
        pids = intake_py_pids()
        if not pids:
            break
        resume_frozen_tables()
        log("已有 intake python 进程在跑（pid=%s），等它退出" % ",".join(map(str, pids[:3])))
        time.sleep(POLL)
    for i in range(1, MAX_INTAKE_PASSES + 1):
        run([sys.executable, INTAKE_PY, "tables", "--concurrency", "6"], check=(i == 1))
        agg = intake_progress()
        st = agg.get("layers_by_status") or {}
        failed = st.get("failed", 0)
        log("intake 第 %d 遍：layers=%s，状态=%s，read=%s" %
            (i, agg.get("layers_n"), json.dumps(st, ensure_ascii=False), agg.get("read")))
        if not failed:
            break
        log("还有 %d 层 failed → 再跑一遍（status=ok 的层会跳过）" % failed)
    agg = intake_progress()
    if not agg:
        raise SystemExit("intake-progress.json 不存在，tables 阶段没跑起来")
    layered = len(os.listdir(os.path.join(INTAKE_OUT, "layers"))) \
        if os.path.isdir(os.path.join(INTAKE_OUT, "layers")) else 0
    return {"intake_layers": agg.get("layers_n"), "intake_layer_dirs": layered,
            "intake_status": agg.get("layers_by_status"), "rows_total": agg.get("rows_total"),
            "read": agg.get("read"), "tables": agg.get("tables"),
            "rows_per_s": agg.get("rows_per_s"), "reconcile_ok": agg.get("reconcile_ok")}


# ---------------------------------------------------------------- ③ 实体台账
def stage3_entities() -> dict:
    set_stage("③ 聚合三张实体台账（entity_street / entity_zip / entity_city）")
    run([sys.executable, INTAKE_PY, "build"], check=True)
    db = os.path.join(INTAKE_OUT, "index.sqlite")
    out = {"db": db, "db_mb": round(os.path.getsize(db) / 1e6, 1) if os.path.exists(db) else None}
    try:
        import sqlite3
        con = sqlite3.connect(db)
        for t in ("addr", "aux_addr_nohouse", "entity_street", "entity_zip", "entity_city"):
            try:
                out[t] = con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
            except Exception:                        # noqa: BLE001
                out[t] = None
        # 口径自检：主键唯一（去重生效）+ sources 是并集而不是重复行
        try:
            dup = con.execute("""SELECT COUNT(*) FROM (SELECT state_abbr, zip5, street_norm
                                 FROM entity_street GROUP BY 1,2,3 HAVING COUNT(*)>1)""").fetchone()[0]
            out["entity_street_dup_keys"] = dup
        except Exception:                            # noqa: BLE001
            pass
        con.close()
    except Exception as e:                           # noqa: BLE001
        log("⚠️ 台账计数读不出来：%s" % e)
    return out


# ---------------------------------------------------------------- ④ 文档 + pages.csv
def stage4_doc_pages() -> dict:
    set_stage("④ 生成 ENTITY-BASELINE 文档 + pages.csv（前 10 万行）")
    run([sys.executable, INTAKE_PY, "pages", "--doc", DOC_ENTITY], check=True)
    pages = os.path.join(ROOT, "pages.csv")
    n = 0
    if os.path.exists(pages):
        with open(pages, encoding="utf-8") as f:
            n = max(0, sum(1 for _ in f) - 1)         # 去掉表头
    out = {"doc": DOC_ENTITY, "doc_exists": os.path.exists(DOC_ENTITY),
           "pages_csv": pages, "pages_rows": n}
    if not out["doc_exists"]:
        raise SystemExit("文档没生成：%s" % DOC_ENTITY)
    return out


# ---------------------------------------------------------------- ⑤ 收尾
def stage5_finish() -> dict:
    set_stage("⑤ 收尾")
    summ = {}
    p = os.path.join(STATE, "stage1-county.done")
    if os.path.exists(p):
        summ["county"] = {k: v for k, v in json.load(open(p, encoding="utf-8")).items()
                          if k in ("county_layers_done", "rows", "located", "unlocated_pct")}
    for st in (2, 3, 4):
        p = M[st]
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            summ["stage%d" % st] = {k: v for k, v in d.items()
                                    if k not in ("at", "pid", "log", "stage")}
    body = ["# intake pipeline finished", "at: %s" % now(), "state_dir: %s" % STATE, ""]
    for k, v in summ.items():
        body.append("%s: %s" % (k, json.dumps(v, ensure_ascii=False)))
    return {"summary": summ, "body": "\n".join(body)}


def main() -> int:
    os.makedirs(STATE, exist_ok=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    # 单实例锁：同一个 pipeline 不许起两份
    lock = os.path.join(STATE, "pipeline.lock")
    if os.path.exists(lock):
        try:
            old = int(open(lock).read().strip() or 0)
        except Exception:                            # noqa: BLE001
            old = 0
        if old and old != os.getpid() and proc_state(old) != "?":
            log("已有 pipeline 在跑（pid=%d），退出" % old)
            return 0
    open(lock, "w").write(str(os.getpid()))

    log("=" * 70)
    log("pipeline 启动 pid=%d root=%s state=%s" % (os.getpid(), ROOT, STATE))
    try:
        if marker_says(1):
            log("① 已完成（%s），跳过" % M[1])
        else:
            mark(1, stage1_county())
        if marker_says(2):
            log("② 已完成（%s），跳过" % M[2])
        else:
            mark(2, stage2_intake())
        if marker_says(3):
            log("③ 已完成（%s），跳过" % M[3])
        else:
            mark(3, stage3_entities())
        if marker_says(4):
            log("④ 已完成（%s），跳过" % M[4])
        else:
            mark(4, stage4_doc_pages())
        fin = stage5_finish()
        os.makedirs(STATE, exist_ok=True)
        open(os.path.join(STATE, "intake-pipeline.finished"), "w", encoding="utf-8").write(fin["body"])
        mark(5, fin["summary"])
        log("全部完成 → %s" % M[5])
        return 0
    except SystemExit as e:
        log("❌ 中止：%s（已完成段的标记保留，修好后重跑同一命令即可续跑）" % e)
        return 2
    except Exception as e:                           # noqa: BLE001
        import traceback
        traceback.print_exc()
        log("❌ 异常：%s: %s" % (type(e).__name__, e))
        return 3
    finally:
        try:
            if open(lock).read().strip() == str(os.getpid()):
                os.remove(lock)
        except Exception:                            # noqa: BLE001
            pass


if __name__ == "__main__":
    sys.exit(main())
