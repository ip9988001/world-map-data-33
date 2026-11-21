#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「collect-full 在跑就不许合」合并门禁判定（muse-000146 Phase 1a 第 3 片 · 第 8 项）。

三处口径（二号 2026-11-22 仲裁定稿，改口径必须重新批示，不许在本文件里擅自放宽）：

(a) 查哪条 run
    只查**三仓** ip9988001/world-map-data-33 的 `collect-full.yml`：
      GET /repos/{owner}/{repo}/actions/workflows/collect-full.yml/runs?per_page=100
    未完成集合 = {in_progress, queued, waiting, requested, pending}，任一命中 → 判「在跑」。
    不查一仓/二仓（它们没有 collect-full，查了只会产生假阻塞）。
    查询原样输出（run id + status + head_sha + createdAt）**必须**写进 check 摘要，留痕
    防「我以为没在跑」。

(b) 判定窗口
    只判**查询瞬间的快照**，不设「最近 N 分钟有过 run」这类历史窗口（历史窗口会永久阻塞）。
    触发点 = PR 的 opened / synchronize / reopened 三个事件，取**最近一次**结果为准。
    结果时效 30 分钟：超过即 stale → 按「未通过」处理（fail-closed，无 docs 例外）。
      · 事件触发时刚查过，天然新鲜；
      · 复用旧快照（--snapshot-in）或人工复核超过 30 分钟 → stale → 红，重跑即可。
    重跑：`gh workflow run merge-gate-collect-running.yml -f pr=<N> --repo <repo>`

(c) 失败是否阻塞 docs 类合并（按 PR 实际 diff 路径分流，不认标题/描述）
    命中 collect/** · .github/workflows/** · schema/** · scripts/** · config/** 任一 → **阻塞**。
    **仅** docs/** · *.md · *.txt → **不阻塞**（结论 success，但摘要仍写「查到 N 条在跑 run，仅
    docs 变更故不阻塞」+ run id）。
    既不在阻塞前缀、又不属 docs-only 的路径（如 analysis/、survey/、根目录杂项）→ **按阻塞处理**
    （fail-closed；muse 原文只给了这两个白/黑名单，中间地带不许自行放行）。

(d) API 异常（非 200 / 超时 / 限流）→ **fail-closed 阻塞**；唯一例外是 docs-only PR 仍放行，
    但摘要必须写明「API 失败，未验证采集态」。

判定只看上面四条，没有任何别的放行条件。合并权不在这里（本脚本只产出 check 结论）。

用法：
  python3 collect/check_collect_running.py --changed-files /tmp/changed
  python3 collect/check_collect_running.py --changed-files /tmp/changed \
          --snapshot-in /tmp/snap.json --max-age-min 30
  python3 collect/check_collect_running.py --changed-files - --changed-from-event   # CI 用

退出码：0 = 通过（可合）；1 = 未通过（阻塞 / stale / API 失败）；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_REPO = "ip9988001/world-map-data-33"
WORKFLOW = "collect-full.yml"
UNFINISHED = ("in_progress", "queued", "waiting", "requested", "pending")

# (c) 阻塞前缀：命中任一即阻塞
BLOCKING_PREFIXES = ("collect/", ".github/workflows/", "schema/", "scripts/", "config/")
# (c) docs-only 放行：全部文件都命中才算 docs-only
DOCS_PREFIXES = ("docs/",)
DOCS_SUFFIXES = (".md", ".txt")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def classify_paths(files: list[str]) -> dict:
    files = [f.strip() for f in files if f.strip()]
    blocking_hits = sorted({p for f in files for p in BLOCKING_PREFIXES if f.startswith(p)})
    docs_only = bool(files) and all(
        f.startswith(DOCS_PREFIXES) or f.endswith(DOCS_SUFFIXES) for f in files)
    return {"files": files, "blocking_hits": blocking_hits,
            "docs_only": docs_only, "empty": not files}


def query_runs(repo: str, token: str | None, per_page: int = 100, timeout: int = 20) -> tuple[dict, str | None]:
    """返回 ({runs, incomplete, total_count}, error)。error 非空 = API 异常（走 (d)）。"""
    url = ("https://api.github.com/repos/%s/actions/workflows/%s/runs?per_page=%d"
           % (repo, WORKFLOW, per_page))
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pi-merge-gate-collect-running",
        **( {"Authorization": "Bearer " + token} if token else {} ),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            doc = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {}, "HTTP %s %s" % (e.code, e.reason)
    except Exception as e:                              # 超时 / DNS / 限流都算 (d)
        return {}, "%s: %s" % (type(e).__name__, str(e)[:120])
    runs = doc.get("workflow_runs") or []
    slim = [{"id": r.get("id"), "status": r.get("status"), "conclusion": r.get("conclusion"),
             "head_sha": (r.get("head_sha") or "")[:12], "created_at": r.get("created_at"),
             "event": r.get("event"), "html_url": r.get("html_url")} for r in runs]
    incomplete = [r for r in slim if r["status"] in UNFINISHED]
    return {"runs": slim, "incomplete": incomplete,
            "total_count": doc.get("total_count", len(slim))}, None


def render(query: dict, changed: dict, verdict: dict, *, queried_at: str,
           source: str, api_error: str | None, age_min: float | None) -> str:
    L: list[str] = []
    L.append("## 合并门禁 · collect-full 在跑就不许合")
    L.append("")
    L.append("- 仓库 / workflow：`%s` · `%s`（只查这一条，口径 (a)）" % (verdict["repo"], WORKFLOW))
    L.append("- 快照时刻（UTC）：`%s`（来源：%s；时效 %s）"
             % (queried_at, source, "stale ❌" if verdict["stale"] else
                ("%.1f 分钟 ✅" % age_min if age_min is not None else "本次实时 ✅")))
    L.append("- PR 改动：%d 个文件 → %s"
             % (len(changed["files"]),
                ("仅 docs / *.md / *.txt（不阻塞，口径 (c)）" if changed["docs_only"]
                 else "命中阻塞前缀 %s（口径 (c)）" % changed["blocking_hits"] if changed["blocking_hits"]
                 else "既非 docs-only 也非白名单 → 按阻塞处理（fail-closed，口径 (c)）")))
    L.append("")
    if api_error:
        L.append("- ⚠️ API 失败：`%s` → 未验证采集态（口径 (d)）" % api_error)
    else:
        L.append("- 查询到 %d 条 collect-full run（per_page=100 全量快照），未完成 %d 条："
                 % (query.get("total_count", 0), len(query.get("incomplete") or [])))
        L.append("")
        L.append("```")
        L.append("run_id          status        head_sha      created_at")
        for r in query.get("runs") or []:
            flag = "  ← 在跑" if r["status"] in UNFINISHED else ""
            L.append("%-15s %-13s %-13s %s%s" % (r["id"], r["status"], r["head_sha"], r["created_at"], flag))
        L.append("```")
    L.append("")
    L.append("**判定：%s**" % verdict["headline"])
    L.append("")
    L.append("> 口径：查哪条 run = 只查三仓 collect-full.yml；判定窗口 = 查询瞬间快照、时效 30 分钟、"
             "stale 即未通过；docs-only（仅 docs/**、*.md、*.txt）不阻塞，其余 fail-closed。")
    return "\n".join(L)


def decide(changed: dict, query: dict, api_error: str | None, *, stale: bool) -> dict:
    incomplete = query.get("incomplete") or []
    n = len(incomplete)
    ids = ", ".join(str(r["id"]) for r in incomplete) or "无"
    if stale:
        return {"pass": False, "stale": True,
                "headline": "❌ 未通过 — 快照 stale（超过时效窗口），按未通过处理（口径 (b)，无 docs 例外）",
                "note": ""}
    if api_error:
        if changed["docs_only"]:
            return {"pass": True, "stale": False,
                    "headline": "✅ 通过 — API 失败，未验证采集态；但本 PR 仅 docs 变更，不阻塞（口径 (d)）",
                    "note": "api_error_docs_only"}
        return {"pass": False, "stale": False,
                "headline": "❌ 未通过 — API 失败（%s），fail-closed 阻塞（口径 (d)）" % api_error,
                "note": ""}
    if n:
        if changed["docs_only"]:
            return {"pass": True, "stale": False,
                    "headline": ("✅ 通过 — 查询到 %d 条在跑 run（%s），但本 PR 仅 docs 变更，不阻塞（口径 (c)）"
                                 % (n, ids)),
                    "note": "running_docs_only"}
        return {"pass": False, "stale": False,
                "headline": "❌ 未通过 — collect-full 有 %d 条在跑 run（%s），等它结束再合（口径 (a)/(c)）"
                            % (n, ids),
                "note": ""}
    return {"pass": True, "stale": False,
            "headline": "✅ 通过 — 快照内 collect-full 无在跑 run", "note": ""}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--changed-files", required=True, help="改动文件名清单文件，一行一个；`-` = stdin")
    ap.add_argument("--snapshot-out", default="")
    ap.add_argument("--snapshot-in", default="", help="复用旧快照（会做 30 分钟时效校验）")
    ap.add_argument("--max-age-min", type=float, default=30.0)
    ap.add_argument("--now", default="", help="覆盖当前时间（自测用，ISO8601）")
    ap.add_argument("--summary-out", default="", help="把摘要另存一份（默认也写 $GITHUB_STEP_SUMMARY）")
    a = ap.parse_args(argv)

    raw = sys.stdin.read() if a.changed_files == "-" else open(a.changed_files, encoding="utf-8").read()
    changed = classify_paths(raw.splitlines())

    now = parse_ts(a.now) if a.now else utc_now()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    api_error = None
    source = "本次实时查询"
    if a.snapshot_in:
        source = "复用快照 %s" % a.snapshot_in
        try:
            snap = json.loads(open(a.snapshot_in, encoding="utf-8").read())
            query = {"runs": snap.get("runs") or [], "incomplete": snap.get("incomplete") or [],
                     "total_count": snap.get("total_count", len(snap.get("runs") or []))}
            queried_at_dt = parse_ts(snap.get("queried_at"))
            api_error = snap.get("api_error")
        except Exception as e:
            query = {"runs": [], "incomplete": [], "total_count": 0}
            queried_at_dt = None
            api_error = "快照读取失败：%s" % str(e)[:100]
    else:
        query, api_error = query_runs(a.repo, token)
        queried_at_dt = now

    age_min = None
    stale = False
    if queried_at_dt is not None:
        age_min = (now - queried_at_dt).total_seconds() / 60.0
        stale = age_min > a.max_age_min
    else:
        stale = True                                        # 快照没时间戳也算 stale（fail-closed）

    queried_at = (queried_at_dt or now).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdict = decide(changed, query, api_error, stale=stale)
    verdict["repo"] = a.repo

    text = render(query, changed, verdict, queried_at=queried_at, source=source,
                  api_error=api_error, age_min=age_min)
    print(text)
    print("\nRESULT=%s" % ("PASS" if verdict["pass"] else "FAIL"))

    if a.snapshot_out:
        with open(a.snapshot_out, "w", encoding="utf-8") as fh:
            json.dump({"repo": a.repo, "workflow": WORKFLOW, "queried_at": queried_at,
                       "api_error": api_error, "total_count": query.get("total_count", 0),
                       "incomplete": query.get("incomplete") or [], "runs": query.get("runs") or []},
                      fh, ensure_ascii=False, indent=1)
    for path in [a.summary_out] if a.summary_out else []:
        open(path, "w", encoding="utf-8").write(text + "\n")
    gs = os.environ.get("GITHUB_STEP_SUMMARY")
    if gs and not a.summary_out:
        with open(gs, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
