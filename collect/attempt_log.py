#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上游尝试账本（attempt log）：把「同一层被反复重试」变成可计数、可刹车的事实。

为什么要有这个模块（2026-10-31 用户立规）：
  证据摆在同一轮 run 上——`41155023558` 的 6 片里 1 片收工、两层全 failed
  （`503 Wait timeout` / `Expecting value: line 1 column 1`）；上一轮三个 missing 层
  **全是单层超时 55 分钟**。这不是采集代码的 bug，是上游服务质量问题：慢、503、
  返回非 JSON。原来的账本只有「这次 failed」一个快照，看不见「同一层已经是第 N 次
  失败、每次失败类型是什么、一共烧了多少分钟」→ 于是同一个层能连续吃掉 3 轮 CI。

本模块只做一件事：**把每次失败尝试逐条记下来**（层 / 时间 / 失败类型 / 耗时 / 当时行数），
并给出每层的连续失败次数与「还有没有进展」。判据是硬的：

  · 失败类型四分类（用户点名要的）：`timeout` / `http_503` / `non_json` / `token`
    ——另外补 `http_4xx`（404/403 那种真·服务没了）、`dns`（解析不到）、`other`。
  · `upstream_unstable` = **可连通、但连续 N 次（默认 3）尝试都超时/503/非 JSON 且没有进展**。
    与 `unverified`（连不上）、`capped`（要 token）区分开：这三种的处置完全不同。
  · **没有进展**才算「重试收益趋零」：尝试记录里的 rows / prior_units 逐次比，只要涨过
    就不算 unstable（半截层还在推进，重试是有收益的）。

数据源（都是仓库里已有的、不经网络）：
  · `collect/ledger/<stage>_run<RUN_ID>.json` —— 每个 run 的阶段快照（status=failed 的逐层记录）
  · `collect/ledger/<stage>_shardNN.json`     —— 片账本（同一 run 的原始记录，与 run 快照重复）
去重靠 `(layer, kind, elapsed_s, rc, prior_units)`：run 快照是片账本的逐字节拷贝，
所以同一次尝试在两边出现时能被合并成一条，不会把「1 次失败」记成「2 次」。

用法：
  # 从既有账本重建尝试日志（只读账本，不联网）
  python3 collect/attempt_log.py --stage 04b --out analysis/04b-attempt-log.json
  # 只判「哪些层已到重试上限」（给 full_plan / preflight 用）
  python3 collect/attempt_log.py --stage 04b --unstable-only
  # 自检：同一输入 → 同一输出
  python3 collect/attempt_log.py --stage 04b --out analysis/04b-attempt-log.json --check
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SCHEMA = "collect-attempt-log/v1"
RETRY_CAP = 3                    # 用户写死：同一层连续 3 次失败 → 改判 upstream_unstable

# 判定顺序有讲究：503 的正文里带 "Wait timeout for the request exceeded"（含 timeout 字样），
# 必须先判 503 再判超时，否则 503 会被误记成超时。
RE_TOKEN = re.compile(r"\b499\b|Token Required|token_required|token required", re.I)
RE_503 = re.compile(r"\b503\b|Wait timeout for the request exceeded|Service (Unavailable|Temporarily)", re.I)
RE_NON_JSON = re.compile(r"Expecting value|JSONDecodeError|非 JSON|not json|non[-_]?json", re.I)
RE_TIMEOUT = re.compile(r"超时|timed out|timeout|TimeoutError|ETIMEDOUT", re.I)
RE_4XX = re.compile(r"\bhttp40[0-9]\b|\b40[34]\b", re.I)
RE_DNS = re.compile(r"name resolution|getaddrinfo|Name or service not known|"
                    r"CERTIFICATE_VERIFY|nodename nor servname", re.I)

KINDS = ("token", "http_503", "non_json", "timeout", "http_4xx", "dns", "other")
KIND_ZH = {"token": "token(499)", "http_503": "503", "non_json": "非 JSON",
           "timeout": "超时", "http_4xx": "4xx", "dns": "DNS/TLS", "other": "其它"}


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def classify_failure(err="", reason="", rc=None, elapsed_s=None) -> str:
    """一次失败尝试归到哪一类。**只按证据文本判，不猜。**

    `rc=-1` + 3300s 这种「job 内单层超时」在 reason 里有 `单层超时`，归 timeout；
    503 的正文 `code: 503 ... Wait timeout for the request exceeded` 归 http_503（先判）；
    `Expecting value: line 1 column 1` 是上游返回了 HTML/空体 → non_json（入口被反爬/网关吞了）。
    """
    text = ("%s %s" % (err or "", reason or "")).strip()
    if RE_TOKEN.search(text):
        return "token"
    if RE_503.search(text):
        return "http_503"
    if RE_NON_JSON.search(text):
        return "non_json"
    if RE_TIMEOUT.search(text):
        return "timeout"
    if RE_4XX.search(text):
        return "http_4xx"
    if RE_DNS.search(text):
        return "dns"
    if rc is not None and int(rc) == -1:
        # rc=-1 是「被墙钟掐掉」的约定值（full_shard.py），即使 reason 没写清也算超时
        return "timeout"
    return "other"


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def attempt_of(rec, at="", run="", shard=None, source="") -> dict:
    """账本里的一条 failed 记录 → 一条尝试记录（字段顺序固定，便于 --check 字节比对）。"""
    err = str(rec.get("err") or "")
    reason = str(rec.get("reason") or "")
    rc = rec.get("rc")
    elapsed = rec.get("elapsed_s")
    return {
        "layer": str(rec.get("layer") or ""),
        "at": str(rec.get("at") or at or ""),
        "at_src": "record" if rec.get("at") else ("ledger" if at else "none"),
        "kind": classify_failure(err, reason, rc, elapsed),
        "rc": rc,
        "elapsed_s": (round(float(elapsed), 1) if isinstance(elapsed, (int, float)) else None),
        "rows": _int(rec.get("rows")),
        "prior_units": _int(rec.get("prior_units")),
        "run": str(run or ""),
        "shard": shard,
        "source": str(source or ""),
        "err": err[:160],
    }


def _stage_ok(found, stage) -> bool:
    """片账本写的 stage 是 `step04b`，run 快照写 `04b` —— 两种都认，别把自家账本滤掉。"""
    found = str(found or "")
    if not found:
        return True
    aliases = {stage, "step" + stage, stage.replace("step", "")}
    if stage in ("04b", "05b", "07b", "10b"):
        aliases.add("step" + stage[:2] + stage[2:])
    return found in aliases


def attempts_from_ledger(path, stage="04b") -> list:
    """从一个账本文件里抽出 attempts（只认 status=failed 的记录）。"""
    d = jload(path)
    if not _stage_ok(d.get("stage"), stage):
        return []
    run = str(d.get("run_id") or "")
    top_at = str(d.get("at") or "")
    shard = d.get("shard")
    shard = shard if isinstance(shard, int) else 0
    out = []
    for r in d.get("records") or []:
        if str(r.get("status") or "") != "failed":
            continue
        s = r.get("shard")
        out.append(attempt_of(r, at=top_at, run=run,
                              shard=s if isinstance(s, int) else shard,
                              source=os.path.basename(path)))
    return out


def ledger_files(base_dir, stage="04b") -> list:
    """尝试日志的输入账本清单（run 快照 + 片账本），顺序固定。"""
    base = base_dir or os.path.join(ROOT, "collect", "ledger")
    files = sorted(glob.glob(os.path.join(base, "%s_run*.json" % stage)))
    files += sorted(glob.glob(os.path.join(base, "%s_shard*.json" % stage)))
    return [f for f in files if os.path.exists(f)]


def dedupe(attempts) -> list:
    """同一次尝试在 run 快照与片账本里各出现一次 → 合并成一条。

    去重键不含时间戳：片账本的 failed 记录常常没有 `at`，回退成「账本生成时间」，
    两次读同一份记录会得到不同 at；但 elapsed_s / rc / prior_units 是同一次尝试的指纹。
    反例要照顾：同一层在不同时间用同样耗时失败（33.4s 的两轮）是**两次**尝试，不是一次 ——
    所以只要记录自带 `at`，就把它算进键里。
    """
    seen, out = set(), []
    for a in sorted(attempts, key=lambda x: (x["layer"], x["at"], x["kind"],
                                             -1 if x["elapsed_s"] is None else x["elapsed_s"])):
        key = (a["layer"], a["kind"], a["elapsed_s"], a["rc"], a["prior_units"],
               a["at"] if a.get("at_src") == "record" else "")
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def collect_attempts(base_dir=None, stage="04b") -> tuple:
    """返回 (attempts, sources)。sources 是这次读了哪些账本（写进产物，便于复核）。"""
    files = ledger_files(base_dir, stage)
    attempts = []
    for f in files:
        try:
            attempts += attempts_from_ledger(f, stage=stage)
        except Exception:                                  # noqa: BLE001
            continue
    return dedupe(attempts), [os.path.relpath(f, ROOT) for f in files]


def _progress(a) -> tuple:
    """进展指纹：先看行数，再看已有单元包数（跨轮续跑时行数常为 0）。"""
    return (a["rows"], a["prior_units"])


def summarize(attempts, cap=RETRY_CAP) -> dict:
    """逐层汇总：尝试次数 / 每次失败类型 / 累计耗时 / 有没有进展 / 是否已到重试上限。"""
    by = {}
    for a in attempts:
        by.setdefault(a["layer"], []).append(a)
    out = {}
    for layer, items in by.items():
        items = sorted(items, key=lambda x: (x["at"], x["kind"], x["elapsed_s"] or 0))
        keys = [_progress(a) for a in items]
        # 「有没有进展」：所有尝试的进展指纹都一样 → 一行没多、一个单元包也没多
        no_progress = len(set(keys)) <= 1
        elapsed = sum((a["elapsed_s"] or 0) for a in items)
        kinds = [a["kind"] for a in items]
        out[layer] = {
            "layer": layer,
            "attempts_n": len(items),
            "kinds": kinds,
            "kinds_n": {k: kinds.count(k) for k in KINDS if k in kinds},
            "first_at": items[0]["at"],
            "last_at": items[-1]["at"],
            "last_kind": kinds[-1],
            "rows_at_last": items[-1]["rows"],
            "prior_units_at_last": items[-1]["prior_units"],
            "no_progress": no_progress,
            "elapsed_s": round(elapsed, 1),
            "elapsed_min": round(elapsed / 60.0, 1),
            "unstable": bool(len(items) >= cap and no_progress),
            "runs": sorted({x["run"] for x in items if x["run"]}),
            "shards": sorted({x["shard"] for x in items if isinstance(x["shard"], int)}),
        }
    return out


def unstable_layers(summary, cap=RETRY_CAP) -> list:
    """到了重试上限的层（按尝试次数、累计耗时降序：先照最贵的看）。"""
    rows = [v for v in (summary or {}).values() if v.get("attempts_n", 0) >= cap and v.get("unstable")]
    rows.sort(key=lambda x: (-x["attempts_n"], -x["elapsed_s"], x["layer"]))
    return rows


def partition_queue(layer_ids, summary, force=(), cap=RETRY_CAP) -> tuple:
    """待采队列：默认**剔除**已到上限的 upstream_unstable 层。

    `force`（`--force-unstable-layer L`）是唯一显式例外：用户点名「仍要试」才放回去。
    返回 (keep, excluded, forced_back)。
    """
    force = tuple(force or ())
    keep, excluded, forced_back = [], [], []
    for lid in layer_ids:
        info = (summary or {}).get(lid) or {}
        if info.get("unstable"):
            if lid in force:
                keep.append(lid)
                forced_back.append(lid)
                continue
            excluded.append({"layer": lid, "attempts_n": info.get("attempts_n"),
                             "kinds": info.get("kinds"), "elapsed_min": info.get("elapsed_min")})
            continue
        keep.append(lid)
    return keep, excluded, forced_back


def build(base_dir=None, stage="04b", cap=RETRY_CAP, prev_attempts=None) -> dict:
    attempts, sources = collect_attempts(base_dir, stage)
    # ★ 追加而不是重建（2026-10-31）：片账本每轮被新 run 覆盖，历史尝试会跟着消失 ——
    #   如果每次都「从现存账本重建」，连续失败次数永远涨不到 3，重试上限就是纸面的。
    #   所以：旧日志里的尝试一律保留，新读到的只是并进来（靠指纹去重，不会重复计数）。
    merged = dedupe(list(prev_attempts or []) + attempts)
    summary = summarize(merged, cap)
    unst = unstable_layers(summary, cap)
    return {
        "schema": SCHEMA,
        "stage": stage,
        "cap": cap,
        "at": max([a["at"] for a in merged] or [""]),
        "sources": sources,
        "append": True,
        "kept_from_prev_n": len(merged) - len(attempts),
        "attempts_n": len(merged),
        "layers_n": len(summary),
        "unstable_n": len(unst),
        "kind_rule": ("失败类型先判 token(499) → 503 → 非 JSON → 超时 → 4xx → DNS/TLS → other；"
                      "503 的正文里带 «Wait timeout…»，所以必须排在「超时」之前，否则会被误记成超时。"),
        "cap_rule": ("同一层连续 %d 次尝试失败且**没有进展**（每次尝试的 rows/prior_units 全一样）"
                     "→ 判 upstream_unstable：默认从待采队列剔除，只有 "
                     "`--force-unstable-layer <层>` 能放回去" % cap),
        "unstable": unst,
        "attempts": merged,
        "layers": summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="04b")
    ap.add_argument("--base-dir", default="", help="账本目录（默认 collect/ledger）")
    ap.add_argument("--out", default=os.path.join(ROOT, "analysis", "04b-attempt-log.json"))
    ap.add_argument("--cap", type=int, default=RETRY_CAP, help="连续失败上限（默认 3）")
    ap.add_argument("--check", action="store_true", help="只比对 --out，不一致退 1")
    ap.add_argument("--rebuild", action="store_true",
                    help="丢掉旧日志、只从现存账本重建（默认追加：历史尝试不因片账本被覆盖而消失）")
    ap.add_argument("--unstable-only", action="store_true", help="只打印到上限的层（给脚本用）")
    ap.add_argument("--json", action="store_true", help="打印完整 JSON")
    a = ap.parse_args()

    prev = []
    if not a.rebuild and os.path.exists(a.out):
        try:
            prev = jload(a.out).get("attempts") or []
        except Exception:                                  # noqa: BLE001
            prev = []
    log = build(a.base_dir or None, a.stage, a.cap, prev_attempts=prev)
    if a.unstable_only:
        print(json.dumps({"cap": log["cap"], "unstable_n": log["unstable_n"],
                          "unstable": log["unstable"]}, ensure_ascii=False, indent=1))
        return 0
    payload = json.dumps(log, ensure_ascii=False, indent=1)
    if a.check:
        cur = open(a.out, encoding="utf-8").read() if os.path.exists(a.out) else ""
        if cur != payload:
            print("DIFFERS: %s" % a.out)
            return 1
        print("IDENTICAL")
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(payload)
    if a.json:
        print(payload)
    else:
        print(json.dumps({"out": os.path.relpath(a.out, ROOT), "attempts_n": log["attempts_n"],
                          "layers_n": log["layers_n"], "unstable_n": log["unstable_n"],
                          "cap": log["cap"],
                          "sources_n": len(log["sources"])}, ensure_ascii=False))
        for u in log["unstable"]:
            print("  ⛔ %s — %d 次（%s），累计 %.1f 分钟"
                  % (u["layer"], u["attempts_n"],
                     "/".join(KIND_ZH.get(k, k) for k in u["kinds"]), u["elapsed_min"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
