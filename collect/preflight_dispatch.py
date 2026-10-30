#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""派单前核验（preflight gate）—— 跑之前先把「会不会白跑 / 会不会撞车 / 会不会冲账本」查一遍。

## 为什么要有这个文件

2026-10-30 一天之内返工了五次，每次都有人（我）临场想起来一个点：

  · 派 04b 之前没看同组 pending → 新 dispatch 把旧的 pending 挤掉（同 concurrency group）；
  · 派之前没看那个 run 用的还是旧 YAML（`head_sha` 落后 main）→ 采完又污染一次账本；
  · 派之前没看目标层正在被别的 run 写 → 两层同时写同一层必撞；
  · 派之前没看目标层上游已经 0 行 → 跑两小时白跑；
  · 派之前没钉账本基线 → 跑完「行数变没变小」说不清。

「每次跑之前核验一下」如果只是口号，就一定会漏。所以它必须是一个**机械门禁**：
任一 FAIL → 退出码非 0 → workflow 的 plan job 第一步就红，run 根本进不去 shard。

## 只读承诺

本脚本**不采集、不派发、不改账本、不删资产**：

  · 对上游只发 `returnCountOnly=true` 的计数请求（不取一行数据）；
  · 对 GitHub 只读：`gh run list` / `gh run view` / `gh release view` / `gh api releases`；
  · 对 git 只读：`git show <ref>:<path>`、`git log --grep`；
  · 唯一写盘是自己的产物：`analysis/preflight-<stage>-<ts>.json` 与
    `analysis/rows-baseline-<stage>-<ts>.json`（后者是跑后比对的基线）。

用法：
  python3 collect/preflight_dispatch.py --stage 07b
  python3 collect/preflight_dispatch.py --stage 04b --force-layers a,b --size 20 --max-shards 3
  python3 collect/preflight_dispatch.py --stage 10b              # 预期 FAIL（未授权重阶段）
  python3 collect/preflight_dispatch.py --stage 04b --offline     # 断网/CI 调试：跳过网络项（转 WARN）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ANALYSIS = os.path.join(ROOT, "analysis")
WF = ".github/workflows/collect-full.yml"

STAGES = ("04b", "05b", "07b", "10b")
HEAVY = ("10b",)                       # 必须 --authorize-heavy
MANUAL_ONLY = ("08", "09", "10", "geometry")   # 必须 --authorize-manual
DEFAULT_REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"

# B3：派出的 ref 必须已经带上这些「修好的东西」，否则就是拿旧代码去跑。
#     每项 = (文件, 必须出现的标记, 说明, 对应 PR/来历)
REQUIRED_FIXES = [
    ("collect/chain_policy.py", 'ALLOWED = ("05b", "07b")',
     "接续允许清单只放 05b/07b", "4-7 停车线（已合 main）"),
    ("collect/chain_policy.py", '"07b": "",',
     "07b 的 NEXT 必须为空（断链点）", "4-7 停车线（已合 main）"),
    ("collect/ledger_merge.py", "def write_run_and_stage(",
     "单 run 账本不得覆盖阶段账本", "chore/ledger-merge-fix（PR 待合）"),
    ("collect/step_full_report.py", "from ledger_merge import write_run_and_stage",
     "merge 步骤走 ledger_merge 而不是直接写阶段账本", "chore/ledger-merge-fix（PR 待合）"),
    ("collect/ckpt_guard.py", "def merge_checkpoints(",
     "force 重跑按单元合并检查点（不许整份覆盖）", "fix/force-checkpoint-preserve（PR #12）"),
    ("collect/pilot.py", "_backup_legacy_ckpt",
     "重跑前先备份旧检查点", "fix/force-checkpoint-preserve（PR #12）"),
]
# B3 的另一半：hash 比对用的关键文件（与 main 的 blob sha 对齐）
KEY_FILES = ("collect/chain_policy.py", "collect/pilot.py", "collect/full_shard.py",
             "collect/full_plan.py", "collect/step_full_report.py", "collect/ledger_merge.py",
             "collect/ckpt_guard.py", WF)

PKG_RE = re.compile(r"-u\d{5}\.tar\.gz$")


# ------------------------------------------------------------------ 基础设施
def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd, timeout=120, cwd=ROOT):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except Exception as e:                                     # noqa: BLE001
        return 1, "", "%s: %s" % (type(e).__name__, str(e)[:200])


def gh_json(args, timeout=120):
    """`gh <args> --json ...` → (rc, obj|None)。不做缓存也不写盘。"""
    rc, out, err = _run(["gh"] + list(args), timeout=timeout)
    if rc != 0:
        return rc, None, ((out or "") + (err or ""))[:300]
    try:
        return 0, json.loads(out or "{}"), ""
    except Exception as e:                                     # noqa: BLE001
        return 1, None, "JSON 解析失败：%s" % str(e)[:120]


def git_show(ref: str, path: str):
    """只读取文件内容：`git show <ref>:<path>`；取不到返回 None。"""
    rc, out, _ = _run(["git", "show", "%s:%s" % (ref, path)], timeout=60)
    return out if rc == 0 else None


def git_blob(ref: str, path: str):
    rc, out, _ = _run(["git", "rev-parse", "%s:%s" % (ref, path)], timeout=30)
    return out.strip() if rc == 0 else None


def resolve_ref(ref: str):
    """把 --ref 解析成 sha。

    ★ 顺序是 origin/<ref> **优先**：2026-10-30 实测本仓有个本地 `main` 停在
      `2161d50`（feat/ledger-rebuild 时代），而真正的远端 main 是 `d5b5db2`。
      先读本地 main 会把 preflight 判成「代码版本不对」，等于用假证据挡自己。
    """
    ref = (ref or "").strip()
    if ref.startswith("refs/heads/"):
        ref = ref[len("refs/heads/"):]
    if ref.startswith("origin/"):
        cands = [ref, ref[len("origin/"):]]
    else:
        cands = ["origin/%s" % ref, ref]
    for cand in cands:
        rc, out, _ = _run(["git", "rev-parse", "--verify", "%s^{commit}" % cand], timeout=30)
        if rc == 0:
            return out.strip(), cand
    if os.environ.get("PREFLIGHT_OFFLINE") == "1":
        return None, ""
    rc, out, _ = _run(["gh", "api", "repos/%s/commits/%s" % (DEFAULT_REPO, ref),
                       "--jq", ".sha"], timeout=60)
    if rc == 0 and out.strip():
        return out.strip(), "manual/%s" % ref      # API 给的 sha：只能按 sha 读内容
    return None, ""


def sha256_text(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:16]


def rows_of(rec: dict) -> int:
    try:
        return int(rec.get("rows") or 0)
    except (TypeError, ValueError):
        return 0


def verdict_of(items):
    """汇总：任一 FAIL → FAIL；有 WARN → PASS_WITH_WARNINGS；否则 PASS。"""
    st = [i.get("status") for i in items or []]
    if "FAIL" in st:
        return "FAIL"
    if "WARN" in st:
        return "PASS_WITH_WARNINGS"
    return "PASS"


def item(cid, group, title, status, detail, **extra):
    """一条核验结果。status = PASS / WARN / FAIL / INFO。"""
    d = {"id": cid, "group": group, "title": title, "status": status, "detail": detail}
    d.update(extra)
    return d


# ------------------------------------------------------------------ A 队列/并发
ART_RE = re.compile(r"^(?:plan|led)-(0?4b|0?5b|0?7b|10b)(?:-\d+)?$")


def stage_of_run(run_id, plan_commits, artifacts=None) -> str:
    """推断一个 run 属于哪个 stage：先看 plan 提交，其次看 artifact 名（plan-05b / led-05b-7）。"""
    rid = str(run_id)
    for stage, info in (plan_commits or {}).items():
        if rid == str(info.get("run_id")):
            return stage
    for name in artifacts or []:
        m = ART_RE.match(name or "")
        if m:
            return m.group(1)
    return ""


def run_artifacts(run_id, offline=False):
    """该 run 的 artifact 名（只读；老 YAML 没把计划提交到 main 时靠它推断 stage）。"""
    if offline:
        return []
    rc, out, _ = _run(["gh", "api", "repos/%s/actions/runs/%s/artifacts" % (DEFAULT_REPO, run_id),
                       "--jq", ".artifacts[]|.name"], timeout=60)
    return [x.strip() for x in (out or "").splitlines() if x.strip()] if rc == 0 else []


def judge_concurrency(stage, active, run_stage=None, wait_est_min=None, offline=False):
    """A1：同 concurrency group（collect-full-<stage>）已有 in_progress / pending。

    `active` = [{id, status, created_at}]，仅本 stage 的 run。
    """
    out = []
    if offline:
        return [item("A1", "A", "同组占用", "WARN", "offline：拿不到 run 列表，无法判断同组是否排队")]
    same = list(active or [])
    running = [r for r in same if r["status"] == "in_progress"]
    waiting = [r for r in same if r["status"] in ("queued", "pending", "waiting", "requested")]
    if waiting:
        out.append(item("A1", "A", "同组 pending", "FAIL",
                        "同组已有 %d 个排队 run（%s）：新派单会把它挤掉（concurrency 只保留一个 pending）"
                        % (len(waiting), ", ".join(str(r["id"]) for r in waiting[:5])),
                        runs=waiting))
    if running:
        est = wait_est_min if wait_est_min is not None else 180
        out.append(item("A1", "A", "同组 in_progress", "WARN",
                        "同组已有 %d 个在跑（%s），本次会排队，预计等 ≈%d 分钟（按同阶段历史中位时长估）"
                        % (len(running), ", ".join(str(r["id"]) for r in running[:5]), est),
                        runs=running))
    if not out:
        out.append(item("A1", "A", "同组占用", "PASS", "同组空闲（无 in_progress / pending）"))
    return out


PREV = {"05b": "04b", "07b": "05b", "10b": "07b"}


def judge_upstream_stage(stage, active_all, offline=False):
    """A1b：上游阶段正在跑 → 它 merge 全绿后会自动 dispatch 本阶段，手派会撞同组。

    这不是理论风险：2026-10-30 05b 在跑，它的 merge 会 `--workflow run --ref main` 派 07b；
    这时候再手派一个 07b，两个 run 抢同一个 `collect-full-07b` group，先来的 pending 被挤掉。
    """
    if offline:
        return item("A1b", "A", "上游阶段在跑", "WARN", "offline：拿不到 run 列表")
    prev = PREV.get(stage)
    if not prev:
        return item("A1b", "A", "上游阶段在跑", "INFO", "%s 没有上游阶段（链条起点）" % stage)
    live = [r for r in (active_all or []) if r.get("stage") == prev
            and r["status"] in ("in_progress", "queued", "pending", "waiting", "requested")]
    if live:
        return item("A1b", "A", "上游阶段在跑", "WARN",
                    "上游 %s 正在跑（%s）：它全绿后会自动派 %s → 现在手派会撞同一个 concurrency group；"
                    "要么等它派，要么先去把它的接续停掉（chain=0 时不会自动派）"
                    % (prev, ", ".join("#%s" % r["id"] for r in live[:4]), stage), runs=live)
    return item("A1b", "A", "上游阶段在跑", "PASS", "上游 %s 没有在跑（无自动派 %s 的冲突）" % (prev, stage))


def judge_other_stages(stage, active_all, offline=False, limit=2):
    """A2：其他 stage 的在跑 run 数（抢同一批层 / 同一 egress 出口）。"""
    if offline:
        return [item("A2", "A", "跨阶段并发", "WARN", "offline：拿不到 run 列表")]
    others = [r for r in (active_all or []) if r.get("stage") and r["stage"] != stage
              and r["status"] in ("in_progress", "queued", "pending", "waiting", "requested")]
    if len(others) > limit:
        return [item("A2", "A", "跨阶段并发", "WARN",
                     "另有 %d 个其他阶段在跑（%s）：共享 egress 与上游配额，片失败率会升高"
                     % (len(others), ", ".join("%s#%s" % (r["stage"], r["id"]) for r in others[:6])),
                     runs=others)]
    return [item("A2", "A", "跨阶段并发", "PASS",
                 "其他阶段在跑 %d 个（阈值 %d）" % (len(others), limit))]


# ------------------------------------------------------------------ B 代码版本
def judge_code_gate(ref, main_ref="main", show=git_show, blob=git_blob):
    """B3：--ref 的关键文件 hash 是否等于 main，且已带上「修好的东西」。

    返回 (items, diffs)。diffs = [{file, ref_blob, main_blob}]
    """
    out = []
    diffs, missing = [], []
    for f in KEY_FILES:
        a, b = blob(ref, f), blob(main_ref, f)
        if a != b:
            diffs.append({"file": f, "ref_blob": a, "main_blob": b})
    for f, marker, desc, origin in REQUIRED_FIXES:
        text = show(ref, f)
        if text is None:
            missing.append({"file": f, "why": "文件不存在于该 ref", "need": desc, "from": origin})
        elif marker not in text:
            missing.append({"file": f, "why": "缺少标记 %r" % marker, "need": desc, "from": origin})
    if missing:
        out.append(item("B3", "B", "代码版本（修复已生效）", "FAIL",
                        "该 ref 缺少 %d 项已批准的修复：%s"
                        % (len(missing),
                           "; ".join("%s→%s" % (m["file"], m["need"]) for m in missing[:4])),
                        missing=missing))
    if diffs:
        out.append(item("B3", "B", "代码版本（与 main 一致）", "FAIL" if not missing else "WARN",
                        "该 ref 有 %d 个关键文件与 main 不同：%s"
                        % (len(diffs), ", ".join(d["file"] for d in diffs[:6])),
                        diffs=diffs))
    if not missing and not diffs:
        out.append(item("B3", "B", "代码版本", "PASS", "关键文件与 main 逐一对齐，且 6 项已批准修复齐全"))
    return out, diffs


def judge_chain(stage, chain_out, chain_rc=0):
    """B4：接续策略 dry-run 结论是否与「停车线」一致。

    期望：04b/05b → next ∈ {05b,07b} 且 child_chain=0；07b/10b → next 为空且 decide=stop。
    """
    if chain_rc != 0:
        return item("B4", "B", "接续策略 dry-run", "FAIL",
                    "chain_policy --dry-run 跑不起来（rc=%s）：%s" % (chain_rc, (chain_out or "")[:200]))
    m_next = re.search(r"next=(\S*)", chain_out or "")
    m_dec = re.search(r"decide=(\S+)", chain_out or "")
    m_cc = re.search(r"child_chain=(\S+)", chain_out or "")
    nxt = (m_next.group(1) if m_next else "?").strip()
    dec = (m_dec.group(1) if m_dec else "?").strip()
    cc = (m_cc.group(1) if m_cc else "").strip()
    if stage in ("04b", "05b"):
        if nxt in ("05b", "07b") and cc == "0":
            return item("B4", "B", "接续策略 dry-run", "PASS",
                        "%s → next=%s（在允许清单内），child_chain=%s（单跳）" % (stage, nxt, cc),
                        next=nxt, child_chain=cc)
        return item("B4", "B", "接续策略 dry-run", "FAIL",
                    "%s 的 next=%s / child_chain=%s 不在允许清单（只许 05b/07b 且单跳）"
                    % (stage, nxt, cc), next=nxt, child_chain=cc)
    # 07b / 10b 必须 stop
    if nxt in ("", "-") and dec == "stop":
        return item("B4", "B", "接续策略 dry-run", "PASS",
                    "%s → next=空 / decide=stop（停车线正确，不会自动接下一阶段）" % stage,
                    next=nxt)
    return item("B4", "B", "接续策略 dry-run", "FAIL",
                "%s 竟然还会接续（next=%s / decide=%s）：停车线破了，先修 chain_policy.py"
                % (stage, nxt, dec), next=nxt)


def judge_authorization(stage, authorize_heavy=False, authorize_manual=(), offline=False):
    """B5：禁止清单 —— 10b 要 authorize_heavy=1；08/09/10/几何要显式口号。"""
    if stage not in STAGES:
        if stage in MANUAL_ONLY:
            if stage in (authorize_manual or ()):
                return item("B5", "B", "阶段授权", "WARN",
                            "%s 已显式授权，但它不在 collect-full 的四个阶段内（要另写流程）" % stage)
            return item("B5", "B", "阶段授权", "FAIL",
                        "%s 属「等口号」范围（08 去重 / 09 增量 / 10 宗地 / 几何），未授权不得派单" % stage)
        return item("B5", "B", "阶段授权", "FAIL",
                    "未知 stage %r（允许：%s）" % (stage, " / ".join(STAGES)))
    if stage in HEAVY and not authorize_heavy:
        return item("B5", "B", "阶段授权", "FAIL",
                    "%s 是重阶段（宗地 8,116 层 / 20~85 GB），必须显式 authorize_heavy=1 才可派" % stage)
    if stage in HEAVY:
        return item("B5", "B", "阶段授权", "WARN",
                    "%s 已显式授权（authorize_heavy=1）—— 这是重阶段，跑之前再确认一次磁盘/时长预算" % stage)
    return item("B5", "B", "阶段授权", "PASS", "%s 在四阶段常规范围，无需额外授权" % stage)


# ------------------------------------------------------------------ C 账本基线
LEDGER_ALIASES = {"04b": ("04b", "step04b"), "05b": ("05b", "step05b"),
                  "07b": ("07b", "step07b"), "10b": ("10b", "step10b")}


def _find(paths):
    if isinstance(paths, str):
        paths = [paths]
    for p in paths:
        hit = sorted(glob.glob(p))
        if hit:
            return hit[-1]
    return ""


def summarize_ledger(path, scope=""):
    """把任意账本读成计数摘要（不猜、不改）。"""
    if not path or not os.path.exists(path):
        return {"path": path or "", "exists": False}
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:                                     # noqa: BLE001
        return {"path": path, "exists": True, "error": str(e)[:120]}
    recs = d.get("records") or d.get("layers") or []
    cnt = {}
    for r in recs:
        cnt[str(r.get("status") or "?")] = cnt.get(str(r.get("status") or "?"), 0) + 1
    return {"path": os.path.relpath(os.path.abspath(path), ROOT), "exists": True,
            "scope": d.get("scope") or scope, "layers_n": d.get("layers_n") or len(recs),
            "rows": d.get("rows") if d.get("rows") is not None else sum(rows_of(r) for r in recs),
            "declared": d.get("declared"),
            "ok": d.get("ok", cnt.get("ok", 0)), "partial": d.get("partial", cnt.get("partial", 0)),
            "missing": d.get("missing", cnt.get("missing", 0)),
            "unverified": d.get("unverified", cnt.get("unverified", 0)),
            "empty": d.get("empty", cnt.get("empty", 0)),
            "failed": d.get("failed", cnt.get("failed", 0)),
            "complete": d.get("complete"), "at": d.get("at"),
            "run_id": d.get("run_id"), "revisions": len(d.get("revisions") or [])}


def ledger_paths(stage):
    names = LEDGER_ALIASES.get(stage, (stage,))
    stage_ledger = _find([os.path.join(ROOT, "collect", "%s_ledger.json" % n) for n in names])
    rebuilt = _find([os.path.join(ROOT, "collect", "ledger", "%s_rebuilt.json" % n) for n in names])
    runs = sorted(glob.glob(os.path.join(ROOT, "collect", "ledger", "%s_run*.json" % names[0])))
    return stage_ledger, rebuilt, (runs[-1] if runs else "")


def judge_baseline(stage, paths=None):
    """C6：三份账本现值（阶段级 / rebuilt / 最近一次 run）。"""
    stage_path, rebuilt_path, run_path = paths or ledger_paths(stage)
    got = {"stage_ledger": summarize_ledger(stage_path, "stage"),
           "rebuilt": summarize_ledger(rebuilt_path, "rebuilt_from_assets"),
           "last_run": summarize_ledger(run_path, "single_run")}
    missing = [k for k, v in got.items() if not v.get("exists")]
    detail = "阶段账本 %s 层/%s 行；rebuilt %s 层/%s 行；最近 run %s 层/%s 行" % (
        got["stage_ledger"].get("layers_n", "-"), got["stage_ledger"].get("rows", "-"),
        got["rebuilt"].get("layers_n", "-"), got["rebuilt"].get("rows", "-"),
        got["last_run"].get("layers_n", "-"), got["last_run"].get("rows", "-"))
    return item("C6", "C", "账本现值", "WARN" if missing else "PASS",
                detail + ("（缺：%s）" % ",".join(missing) if missing else ""),
                ledgers=got)


def judge_merge_guard(ref, show=git_show):
    """C8：merge 写入逻辑是否已带「单 run 不得覆盖阶段账本」保护。"""
    ledger_merge = show(ref, "collect/ledger_merge.py") or ""
    sfr = show(ref, "collect/step_full_report.py") or ""
    ckpt = show(ref, "collect/ckpt_guard.py") or ""
    pilot = show(ref, "collect/pilot.py") or ""
    checks = {
        "ledger_merge.write_run_and_stage": "def write_run_and_stage(" in ledger_merge,
        "ledger_merge.stage_overwrite_allowed": "def stage_overwrite_allowed(" in ledger_merge,
        "step_full_report 走 ledger_merge": "from ledger_merge import write_run_and_stage" in sfr,
        "step_full_report 带行数闸门": "row-shrink-evidence" in sfr or "allow_shrink" in sfr,
        "ckpt_guard.merge_checkpoints": "def merge_checkpoints(" in ckpt,
        "pilot 收尾合并检查点": "_merge_legacy_ckpt" in pilot,
    }
    bad = [k for k, v in checks.items() if not v]
    if bad:
        return item("C8", "C", "账本写入保护", "FAIL",
                    "该 ref 的 merge/采集写入还没带保护：%s —— 跑完账本必被冲（缺列见 evidence）"
                    % ", ".join(bad[:3]), checks=checks)
    return item("C8", "C", "账本写入保护", "PASS",
                "单 run 不覆盖阶段账本 + 逐层 rows 不减 + 检查点按单元合并，三项齐全",
                checks=checks)


# ------------------------------------------------------------------ D 数据重叠
def layers_of_plan(plan):
    out = []
    for s in plan.get("shards") or []:
        if isinstance(s, dict):
            out += [x if isinstance(x, str) else (x or {}).get("layer") for x in (s.get("layers") or [])]
        else:
            out += [x if isinstance(x, str) else (x or {}).get("layer") for x in (s or [])]
    return [x for x in out if x]


def judge_overlap(force_layers, inflight_targets, offline=False):
    """D9：本次 force 的目标层 vs 在跑 run 的目标层 —— 交集必须为空。"""
    if offline:
        return item("D9", "D", "目标层撞车", "WARN", "offline：拿不到在跑 run 的计划，无法判交集")
    force = [x for x in (force_layers or []) if x]
    if not force:
        return item("D9", "D", "目标层撞车", "INFO", "本次没有 --force-layers，无「点名层撞车」风险（按计划切片仍可能重叠，见 D10）")
    hits = []
    for lid in force:
        for run_id, tgt in (inflight_targets or {}).items():
            if lid in (tgt.get("layers") or []):
                hits.append({"layer": lid, "run_id": run_id, "stage": tgt.get("stage")})
    if hits:
        return item("D9", "D", "目标层撞车", "FAIL",
                    "%d 个 force 层正在被在跑 run 写：%s"
                    % (len(hits), "; ".join("%s ← #%s(%s)" % (h["layer"][:40], h["run_id"], h["stage"])
                                            for h in hits[:4])), hits=hits)
    unknown = [rid for rid, tgt in (inflight_targets or {}).items()
               if not tgt.get("layers")]
    tail = ("；但 %d 个在跑 run 的目标层取不到（%s）→ 交集无法证明"
            % (len(unknown), ",".join("#%s" % u for u in unknown[:3]))) if unknown else ""
    return item("D9", "D", "目标层撞车", "WARN" if unknown else "PASS",
                "%d 个 force 层与在跑 run 的目标层无交集%s" % (len(force), tail))


def judge_done_overlap(stage, planned_layers, done_layers, offline=False, sample=5,
                       estimated=False, force_layers=()):
    """D10：本次计划层 vs Release 已采层集合（重叠>0 必须说清是「补采」而不是「重复采」）。"""
    if offline:
        return item("D10", "D", "已采重叠", "WARN", "offline：拿不到 Release 已采集合")
    if planned_layers is None:
        return item("D10", "D", "已采重叠", "WARN",
                    "拿不到本次计划（没有 %s_plan.json，且该阶段不在 layer_plan.csv 的分档范围内"
                    "（10b 是宗地层））：先跑一次 full_plan 再核 —— 现在无法比对已采集合" % stage)
    done = set(done_layers or ())
    planned = list(planned_layers)
    overlap = sorted(set(planned) & done)
    force_done = sorted(set(force_layers or ()) & done)
    tail = "（口径：%s）" % ("全档估算，非 full_plan 精确计划" if estimated else "现有 --plan 文件")
    if overlap:
        return item("D10", "D", "已采重叠", "WARN",
                    "计划 %d 层里有 %d 层已在 Release（交集>0）：这些会记 skipped_done，白占片位；"
                    "若确有缺口需补采请用 --force-layers 点名。样例：%s%s"
                    % (len(planned), len(overlap), ", ".join(overlap[:sample]), tail),
                    overlap_n=len(overlap), overlap_sample=overlap[:20])
    extra = ""
    if force_done:
        extra = "；另：%d 个 force 层已在 Release（本次属**补采**，不是重复采）" % len(force_done)
    return item("D10", "D", "已采重叠", "PASS",
                "计划 %d 层 vs 已采 %d 层，交集 0 —— 全是新层%s%s"
                % (len(planned), len(done), extra, tail),
                overlap_n=0)


def judge_ckpt_backup(tag_prefix, force_layers, release_assets=None, offline=False):
    """D11：目标层已有检查点 / 单元包 → 跑前必须先备份（给出备份命令）。"""
    if offline:
        return item("D11", "D", "检查点备份", "WARN", "offline：查不到 Release 资产")
    force = [x for x in (force_layers or []) if x]
    if not force:
        return item("D11", "D", "检查点备份", "INFO", "本次无 --force-layers，跳过逐层检查点核查")
    no_bak, has_bak, missing = [], [], []
    for lid in force:
        tag = (tag_prefix or "collect-step04-") + lid
        names = (release_assets or {}).get(lid)
        if names is None:
            missing.append(lid)
            continue
        if any(n.endswith("-checkpoint.json") for n in names):
            if any("-checkpoint.bak-" in n for n in names):
                has_bak.append(lid)
            else:
                no_bak.append((lid, tag))
    if no_bak:
        cmds = ["gh release upload %s <path>/%s-checkpoint.bak-<RUN_ID>.json --clobber"
                % (t, lid) for lid, t in no_bak[:3]]
        return item("D11", "D", "检查点备份", "WARN",
                    "%d 个目标层已有检查点但没有 .bak 备份：pilot 会自动备份（保留 3 代），"
                    "手工补也要先备份，否则覆盖后证据不可恢复。命令样例：%s" % (len(no_bak), cmds[0]),
                    layers=[l for l, _ in no_bak], commands=cmds)
    if missing:
        return item("D11", "D", "检查点备份", "WARN",
                    "%d 个目标层的资产清单取不到（%s）：无法确认是否已有检查点"
                    % (len(missing), ", ".join(missing[:3])))
    return item("D11", "D", "检查点备份", "PASS",
                "%d 个目标层：%d 个已备份 / 其余无检查点（首次采）" % (len(force), len(has_bak)))


# ------------------------------------------------------------------ E 上游可用性
def probe_count(url, timeout=15):
    """只发 returnCountOnly 的计数请求（不取一行数据）。"""
    api = (url or "").split("?")[0].rstrip("/")
    if re.search(r"/(FeatureServer|MapServer)$", api):
        api += "/0"
    q = urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    req = urllib.request.Request(api + "/query?" + q,
                                 headers={"User-Agent": "preflight/1.0 (+read-only count)"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(4000).decode("utf-8", "replace")
            code = r.status
    except urllib.error.HTTPError as e:
        body = (e.read(600) or b"").decode("utf-8", "replace")
        return {"http": e.code, "err": "HTTP %s" % e.code, "body": body[:300],
                "count": None, "elapsed_s": round(time.time() - t0, 1)}
    except Exception as e:                                     # noqa: BLE001
        return {"http": 0, "err": "%s: %s" % (type(e).__name__, str(e)[:120]),
                "count": None, "elapsed_s": round(time.time() - t0, 1)}
    try:
        d = json.loads(body)
    except Exception:                                          # noqa: BLE001
        d = {}
    return {"http": code, "count": d.get("count"), "err": d.get("error") or "",
            "body": body[:300], "elapsed_s": round(time.time() - t0, 1)}


def probe_meta(url, timeout=15):
    """只看服务元数据（`<api>?f=json`）：判断是不是**服务级**要 token。

    服务级 token（连 /0?f=json 都 499）与「单次 query 被拦」不是一回事：
    前者 CI 也采不到（要么配 token，要么从计划里剔除），后者可能只是查询形态/参数问题。
    """
    api = (url or "").split("?")[0].rstrip("/")
    try:
        with urllib.request.urlopen(urllib.request.Request(api + "?f=json",
                                                          headers={"User-Agent": "preflight/1.0"}),
                                    timeout=timeout) as r:
            body = r.read(2000).decode("utf-8", "replace")
            code = r.status
    except urllib.error.HTTPError as e:
        return {"http": e.code, "token": False, "body": (e.read(300) or b"").decode("utf-8", "replace")}
    except Exception as e:                                     # noqa: BLE001
        return {"http": 0, "token": False, "err": str(e)[:120]}
    return {"http": code, "token": "Token Required" in body, "body": body[:200]}


def classify_probe(res):
    """把一次 count 探测归类：ok / empty / token / forbidden / timeout / error / unverifiable。"""
    if res.get("count") is not None:
        return "empty" if int(res.get("count") or 0) == 0 else "ok"
    err = str(res.get("err") or "").lower()
    body = str(res.get("body") or "").lower()
    if res.get("meta_token"):
        return "service_token"
    if "token required" in err or "token required" in body or "token" in body and res.get("http") in (401, 403):
        return "token"
    if res.get("http") == 403:
        return "forbidden"
    if res.get("http") == 0 and ("timeout" in err or "timed out" in err):
        return "timeout"
    if res.get("http") == 0:
        return "error"
    return "unverifiable"


def judge_upstream(samples, results=None, offline=False, min_samples=5):
    """E12/E13/E14：抽样计数 → 0 行层 / 403 超时层 / 声明不可复核层。"""
    items = []
    if offline:
        return [item("E12", "E", "上游抽样", "WARN", "offline：跳过上游计数探测"),
                item("E13", "E", "上游 403/超时", "WARN", "offline：跳过"),
                item("E14", "E", "声明可复核率", "WARN", "offline：跳过")]
    n = len(samples or [])
    if n < min_samples:
        items.append(item("E12", "E", "上游抽样", "WARN",
                          "可抽样层只有 %d 个（< %d 层）：样本不足，只能说明局部情况" % (n, min_samples)))
    res = results or {}
    classes = {k: classify_probe(v) for k, v in res.items()}
    empty = [k for k, c in classes.items() if c == "empty"]
    bad = [(k, v) for k, v in res.items() if classes[k] in ("forbidden", "timeout", "error")]
    unver = [k for k, c in classes.items() if c in ("token", "service_token", "unverifiable")]
    service_token = [k for k, c in classes.items() if c == "service_token"]
    ok = [k for k, c in classes.items() if c == "ok"]
    if empty:
        items.append(item("E12", "E", "上游 0 行层", "WARN",
                          "%d 层上游 returnCount=0（跑了也白跑，建议从计划里剔掉）：%s"
                          % (len(empty), ", ".join(empty[:5])), layers=empty))
    else:
        items.append(item("E12", "E", "上游 0 行层", "PASS",
                          "抽样 %d 层，无 0 行层（%d 层有行）" % (len(res), len(ok))))
    if bad:
        items.append(item("E13", "E", "上游 403/超时", "WARN",
                          "%d 层本机取不到（%s）：**不判死**（本机 ≠ CI，egress/区域不同），"
                          "仅记录证据" % (len(bad), "; ".join("%s=%s" % (k[:32], classes[k])
                                                              for k, _ in bad[:4])),
                          layers=[{"layer": k, "class": classes[k], "probe": v} for k, v in bad]))
    else:
        items.append(item("E13", "E", "上游 403/超时", "PASS", "%d 层抽样无 403/超时" % len(res)))
    if unver:
        extra = ""
        if service_token:
            extra = ("；其中 %d 层是**服务级** token（连 `?f=json` 都 499）→ CI 也采不到，"
                     "要么配 token，要么从计划里剔掉" % len(service_token))
        items.append(item("E14", "E", "声明可复核率", "WARN",
                          "%d 层声明不可复核（Token Required / 非 JSON 响应），标记 declared_unverifiable，"
                          "不计入分母：%s%s" % (len(unver), ", ".join(unver[:4]), extra),
                          layers=unver, service_token=service_token))
    else:
        items.append(item("E14", "E", "声明可复核率", "PASS",
                          "%d 层声明都可复核（用于跑后差额分母）" % len(res)))
    return items


# ------------------------------------------------------------------ 采集：把数据找齐
def plan_commits(ref="main", limit=40):
    """从 main 的提交信息里找「collect: <stage> 计划（run <id>）」→ 在跑 run 的目标层。

    这是仓库既有机制（plan job 把计划提交到 main），所以不依赖 artifact 下载（egress 限流）。
    """
    rc, out, _ = _run(["git", "log", ref, "-n", str(limit), "--format=%H%x09%s"], timeout=60)
    found = {}
    if rc != 0:
        return found
    for line in out.splitlines():
        sha, _, subj = line.partition("\t")
        m = re.match(r"collect: (\S+) 计划（run (\d+)）", subj)
        if not m:
            continue
        stage, rid = m.group(1), m.group(2)
        raw = git_show(sha, "collect/ledger/%s_plan.json" % stage)
        layers = []
        if raw:
            try:
                layers = layers_of_plan(json.loads(raw))
            except Exception:                                  # noqa: BLE001
                layers = []
        found[stage] = {"run_id": rid, "commit": sha[:9], "layers": layers}
    return found


def active_runs(offline=False):
    """在跑 + 排队的 collect-full run（含 status/时间），失败返回 (None, err)。"""
    if offline:
        return None, "offline"
    rc, d, err = gh_json(["run", "list", "--repo", DEFAULT_REPO, "--workflow", "collect-full.yml",
                          "--limit", "40", "--json",
                          "databaseId,status,conclusion,createdAt,updatedAt,headSha,headBranch"],
                         timeout=90)
    if rc != 0 or d is None:
        return None, err
    return d, ""


def release_done_set(stage, offline=False):
    """Release 已采层集合（tag 形如 collect-step04-<layer> 且有 checkpoint）。只读 API。"""
    if offline:
        return None, "offline"
    base = {"04b": "04", "05b": "05", "07b": "07", "10b": "10"}.get(stage, stage.rstrip("b"))
    prefix = "collect-step%s-" % base
    done, page = set(), 1
    while page <= 40:
        rc, batch, err = gh_json(["api", "repos/%s/releases?per_page=100&page=%d"
                                  % (DEFAULT_REPO, page)], timeout=90)
        if rc != 0 or batch is None:
            return (done or None), err
        if not batch:
            break
        for r in batch:
            tag = r.get("tag_name") or ""
            if not tag.startswith(prefix):
                continue
            names = [a.get("name") for a in (r.get("assets") or [])]
            if any((x or "").endswith("-checkpoint.json") for x in names):
                done.add(tag[len(prefix):])
        if len(batch) < 100:
            break
        page += 1
    return done, ""


def release_assets_for(layer, tag_prefix, offline=False):
    if offline:
        return None
    tag = (tag_prefix or "") + layer
    rc, d, _ = gh_json(["release", "view", tag, "--repo", DEFAULT_REPO, "--json", "assets"],
                       timeout=60)
    if rc != 0 or d is None:
        return None
    return [a.get("name") for a in (d.get("assets") or [])]


_LAYER_INDEX = {}


def layer_index():
    """`collect/layer_plan.csv`（60,695 层：id / url / row_count / state）→ dict。只读本地文件。"""
    global _LAYER_INDEX
    if _LAYER_INDEX:
        return _LAYER_INDEX
    import csv
    p = os.path.join(ROOT, "collect", "layer_plan.csv")
    out = {}
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                lid = (r.get("layer_id") or "").strip()
                if not lid:
                    continue
                try:
                    rc = int(float(r.get("row_count") or 0))
                except (TypeError, ValueError):
                    rc = 0
                out[lid] = {"url": (r.get("url") or "").strip(), "row_count": rc,
                            "state": r.get("state") or "", "svc": r.get("svc") or ""}
    _LAYER_INDEX = out
    return out


# 各阶段的行数分档（与 collect/steps.json / full_plan 的选层口径一致）
BANDS = {"04b": (300000, None), "05b": (5000, 300000), "07b": (1, 4999), "10b": (None, None)}


def band_layers(stage, done=None):
    """按行数分档取该阶段的候选层（不含已采）。10b 是宗地面层，不在这份点类清单里。"""
    lo, hi = BANDS.get(stage, (None, None))
    if lo is None:
        return []
    idx = layer_index()
    done = set(done or ())
    out = []
    for lid, v in idx.items():
        n = v["row_count"]
        if n < lo or (hi is not None and n > hi):
            continue
        if lid in done:
            continue
        out.append(lid)
    out.sort(key=lambda x: idx[x]["row_count"])
    return out


def layer_urls(layers):
    """层 id → url（优先 layer_plan.csv，其次 pilot_layers.json）。"""
    idx = layer_index()
    extra = {}
    p = os.path.join(ROOT, "collect", "pilot_layers.json")
    if os.path.exists(p):
        try:
            for x in json.load(open(p, encoding="utf-8")):
                if x.get("id"):
                    extra[x["id"]] = x.get("url") or ""
        except Exception:                                      # noqa: BLE001
            pass
    out = {}
    for lid in layers or []:
        u = (idx.get(lid) or {}).get("url") or extra.get(lid) or ""
        if u:
            out[lid] = u
    return out


def stage_plan_file(stage):
    names = LEDGER_ALIASES.get(stage, (stage,))
    for n in names:
        p = os.path.join(ROOT, "collect", "ledger", "%s_plan.json" % n)
        if os.path.exists(p):
            return p
    return ""


def tag_prefix_of(stage):
    return {"04b": "collect-step04-", "05b": "collect-step05-",
            "07b": "collect-step07-", "10b": "collect-step10-"}.get(stage, "collect-step04-")


# ------------------------------------------------------------------ 主流程
def build_report(args) -> dict:
    offline = bool(args.offline) or os.environ.get("PREFLIGHT_OFFLINE") == "1"
    stage = args.stage
    ref = args.ref
    force = [x.strip() for x in (args.force_layers or "").split(",") if x.strip()]
    tag_prefix = tag_prefix_of(stage)
    items = []
    evidence = {}

    # ---- 运行时数据（一次取齐，失败不致命） ----
    runs, runs_err = active_runs(offline)
    pcommits = plan_commits("origin/main") if git_blob("origin/main", WF) else plan_commits("main")
    stage_runs, all_runs = [], []
    if runs:
        for r in runs:
            st = stage_of_run(r.get("databaseId"), pcommits)
            if not st and r.get("status") in ("in_progress", "queued", "pending", "waiting", "requested"):
                st = stage_of_run(r.get("databaseId"), pcommits,
                                  run_artifacts(r.get("databaseId"), offline=offline))
            rec = {"id": r.get("databaseId"), "status": r.get("status"), "stage": st,
                   "created_at": r.get("createdAt"), "head_sha": (r.get("headSha") or "")[:9],
                   "dur_min": _dur_min(r.get("createdAt"), r.get("updatedAt"))}
            all_runs.append(rec)
            if st == stage:
                stage_runs.append(rec)
    wait_est = estimate_wait(stage_runs, runs, stage)
    evidence["active_runs"] = all_runs
    evidence["runs_err"] = runs_err
    evidence["plan_commits"] = {k: {"run_id": v["run_id"], "commit": v["commit"],
                                    "layers_n": len(v["layers"])} for k, v in pcommits.items()}

    # ---- A 队列/并发 ----
    items += judge_concurrency(stage, stage_runs, wait_est_min=wait_est, offline=offline or not runs)
    items.append(judge_upstream_stage(stage, all_runs, offline=offline or not runs))
    items += judge_other_stages(stage, all_runs, offline=offline or not runs)

    # ---- B 代码版本 ----
    ref_sha, ref_name = resolve_ref(ref)
    ref_for_git = ref_name or ref
    main_sha, main_name = resolve_ref("main")
    main_for_git = main_name or "main"
    if not ref_sha:
        items.append(item("B3", "B", "代码版本", "FAIL", "解析不到 --ref %r 的 sha（连 origin/%s 都没有）"
                          % (ref, ref)))
    else:
        citems, diffs = judge_code_gate(ref_for_git, main_for_git)
        items += citems
    evidence["ref"] = {"ref": ref, "sha": ref_sha, "main_sha": main_sha}
    chain_rc, chain_out, chain_err = _run(
        [sys.executable, os.path.join(HERE, "chain_policy.py"), "--stage", stage, "--dry-run"],
        timeout=60)
    items.append(judge_chain(stage, chain_out + chain_err, chain_rc))
    items.append(judge_authorization(stage, args.authorize_heavy,
                                     tuple(x for x in (args.authorize_manual or "").split(",") if x),
                                     offline=offline))
    evidence["chain_dry_run"] = (chain_out or chain_err or "").strip()

    # ---- C 账本基线 ----
    paths = ledger_paths(stage)
    bitem = judge_baseline(stage, paths)
    items.append(bitem)
    evidence["stage_ledger_path"] = (bitem.get("ledgers") or {}).get("stage_ledger", {}).get("path", "")
    items.append(judge_merge_guard(ref_for_git))
    baseline = {}
    if paths[0] and os.path.exists(paths[0]):
        try:
            d = json.load(open(paths[0], encoding="utf-8"))
            baseline = {str(r.get("layer")): {"rows": rows_of(r), "status": r.get("status")}
                        for r in (d.get("records") or [])}
        except Exception:                                      # noqa: BLE001
            baseline = {}
    evidence["rows_baseline_layers"] = len(baseline)

    # ---- D 数据重叠 ----
    inflight_targets = {}
    for st, info in pcommits.items():
        live = [r for r in (all_runs or []) if str(r["id"]) == str(info["run_id"])
                and r["status"] in ("in_progress", "queued", "pending", "waiting", "requested")]
        if live:
            inflight_targets[info["run_id"]] = {"stage": st, "layers": info["layers"]}
    items.append(judge_overlap(force, inflight_targets, offline=offline or not all_runs))
    evidence["inflight_targets"] = {k: {"stage": v["stage"], "layers_n": len(v["layers"])}
                                    for k, v in inflight_targets.items()}
    planned = None
    pf = stage_plan_file(stage)
    if pf:
        try:
            planned = layers_of_plan(json.load(open(pf, encoding="utf-8")))
        except Exception:                                      # noqa: BLE001
            planned = None
    done, done_err = release_done_set(stage, offline=offline)
    estimated = planned is None
    if planned is None and done is not None:
        est = band_layers(stage, done)              # 分档估算（明确标注，不当精确计划用）
        planned = est if est else None              # 10b（宗地层）不在 layer_plan.csv 里，估不出就明说
    items.append(judge_done_overlap(stage, planned, done,
                                    offline=offline or done is None,
                                    estimated=estimated, force_layers=force))
    evidence["planned"] = {"layers_n": None if planned is None else len(planned),
                           "source": "estimate(band)" if estimated else "plan_file",
                           "done_layers_n": None if done is None else len(done)}
    if force:
        assets = {lid: release_assets_for(lid, tag_prefix, offline=offline) for lid in force[:10]}
        items.append(judge_ckpt_backup(tag_prefix, force[:10], assets, offline=offline))
    else:
        items.append(judge_ckpt_backup(tag_prefix, [], None, offline=False))

    # ---- E 上游可用性 ----
    # 抽样口径：force 层优先（本次真要跑的），再按分档均匀抽样（避免全挤在最小/最大层）
    pool = list(force)
    rest = [x for x in (planned or []) if x not in set(pool)]
    if rest:
        step = max(1, len(rest) // 6)
        pool += rest[::step][:max(0, 8 - len(pool))]
    urls = layer_urls(pool)
    samples = list(urls)
    results = {}
    if samples and not offline:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(probe_count, urls[s]): s for s in samples}
            for f in futs:
                try:
                    results[futs[f]] = f.result()
                except Exception as e:                         # noqa: BLE001
                    results[futs[f]] = {"http": 0, "err": str(e)[:120], "count": None}
        # 被判「token」的，再探一次服务元数据：区分「服务级要 token」与「单次查询被拦」
        tok = [k for k, v in results.items() if classify_probe(v) in ("token", "unverifiable")]
        for k in tok:
            results[k]["meta_token"] = bool(probe_meta(urls[k]).get("token"))
    if not samples and not offline:
        items += [item("E12", "E", "上游抽样", "WARN",
                       "没有可抽样层（--force-layers 为空且清单里没有分档候选）：上游可用性未核"),
                  item("E13", "E", "上游 403/超时", "WARN", "未抽样"),
                  item("E14", "E", "声明可复核率", "WARN", "未抽样，declared_unverifiable 未标注")]
    else:
        items += judge_upstream(samples, results, offline=offline or not samples)
    evidence["upstream_probe"] = {k: {kk: v.get(kk) for kk in ("http", "count", "err", "elapsed_s",
                                                               "meta_token")}
                                  for k, v in results.items()}

    fails = [i for i in items if i["status"] == "FAIL"]
    warns = [i for i in items if i["status"] == "WARN"]
    verdict = verdict_of(items)
    return {"schema": "preflight/v1", "at": now(), "stage": stage, "ref": ref,
            "ref_sha": ref_sha, "main_sha": main_sha, "repo": DEFAULT_REPO,
            "inputs": {"stage": stage, "force_layers": force, "size": args.size,
                       "max_shards": args.max_shards, "ref": ref,
                       "authorize_heavy": bool(args.authorize_heavy)},
            "verdict": verdict, "fail_n": len(fails), "warn_n": len(warns),
            "checks": items, "rows_baseline": baseline, "evidence": evidence,
            "checks_total": len(items)}


def _dur_min(created, updated):
    try:
        a = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
        b = datetime.strptime(updated, "%Y-%m-%dT%H:%M:%SZ")
        return int((b - a).total_seconds() / 60)
    except Exception:                                          # noqa: BLE001
        return None


def estimate_wait(stage_runs, all_runs, stage):
    """粗估等待分钟：同阶段历史中位总时长 − 已经在跑的时间。"""
    durs = []
    for r in all_runs or []:
        if r.get("status") != "in_progress":
            continue
    # 历史时长：用已完成 run 的 createdAt → updatedAt（不查每 run 详情，够用）
    hist = []
    for r in all_runs or []:
        if r.get("status") == "completed" and r.get("dur_min"):
            hist.append(r["dur_min"])
    hist.sort()
    med = hist[len(hist) // 2] if hist else 180
    running = [r for r in (stage_runs or []) if r["status"] == "in_progress"]
    if not running:
        return 0
    el = 0
    for r in running:
        t0 = r.get("created_at")
        if t0:
            try:
                el = max(el, int((datetime.now(timezone.utc)
                                  - datetime.strptime(t0, "%Y-%m-%dT%H:%M:%SZ")).total_seconds() / 60))
            except Exception:                                  # noqa: BLE001
                pass
    return max(0, int(med - el))


def human_summary(rep: dict) -> str:
    lines = ["=" * 78,
             "preflight  %s   ref=%s(%s)   →  %s   (FAIL %d / WARN %d，共 %d 项)"
             % (rep["stage"], rep["ref"], (rep.get("ref_sha") or "?")[:9],
                rep["verdict"], rep["fail_n"], rep["warn_n"], rep["checks_total"]),
             "=" * 78]
    mark = {"PASS": "✅", "WARN": "⚠️ ", "FAIL": "❌", "INFO": "ℹ️ "}
    for i in rep["checks"]:
        lines.append("%s %-4s %-24s %s" % (mark.get(i["status"], "?"), i["id"],
                                           i["title"][:24], i["detail"][:150]))
    lines.append("-" * 78)
    if rep["fail_n"]:
        lines.append("❌ 门禁未通过：修完上面标 ❌ 的项再派单（处置见 docs/PREFLIGHT-GATE.md）")
    else:
        lines.append("✅ 门禁通过：可以派单（WARN 项要写在派单回执里）")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, help="04b / 05b / 07b / 10b")
    ap.add_argument("--force-layers", default="")
    ap.add_argument("--size", default="0")
    ap.add_argument("--max-shards", default="0")
    ap.add_argument("--ref", default="main", help="要派的 ref（默认 main）：其代码就是将要跑的代码")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--authorize-heavy", action="store_true", help="10b 重阶段授权（= workflow 的 authorize_heavy=1）")
    ap.add_argument("--authorize-manual", default="", help="08/09/10/几何：显式口号（逗号分隔）")
    ap.add_argument("--offline", action="store_true", help="跳过网络项（转 WARN）；单测/断网排障用")
    ap.add_argument("--json-out", default="", help="默认 analysis/preflight-<stage>-<ts>.json")
    ap.add_argument("--baseline-out", default="", help="默认 analysis/rows-baseline-<stage>-<ts>.json")
    ap.add_argument("--no-write", action="store_true", help="不写 analysis 产物（只打印）")
    a = ap.parse_args()
    if a.offline:
        os.environ["PREFLIGHT_OFFLINE"] = "1"
    globals()["DEFAULT_REPO"] = a.repo

    rep = build_report(a)
    print(human_summary(rep))
    ts = rep["at"].replace(":", "").replace("-", "")
    if not a.no_write:
        os.makedirs(ANALYSIS, exist_ok=True)
        jp = a.json_out or os.path.join(ANALYSIS, "preflight-%s-%s.json" % (a.stage, ts))
        json.dump(rep, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        bp = a.baseline_out or os.path.join(ANALYSIS, "rows-baseline-%s-%s.json" % (a.stage, ts))
        json.dump({"schema": "rows-baseline/v1", "at": rep["at"], "stage": a.stage,
                   "source": rep["evidence"].get("stage_ledger_path", ""),
                   "layers": rep["rows_baseline"]}, open(bp, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("\n产物：%s\n       %s" % (os.path.relpath(jp, ROOT), os.path.relpath(bp, ROOT)))
    return 1 if rep["fail_n"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
