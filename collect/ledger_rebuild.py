#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账本重建 · 以 **Release 资产为唯一真值**，重建逐层账本 + 收官文档。

为什么要它：04b 的 shard 0/3/5/6 跑完 1~2 小时、conclusion=success，但 main 上
一个账本都没有（账本文件名与 workflow 查找路径不一致，已由 98bd461 修好）。
已经在跑的那批 run 用的是它们自己 checkout 的 SHA，修丁补不回来 —— 所以事后的
账只能从**资产**反推，而不是从「谁记得跑过什么」推。

真值口径（三层，逐层交叉，任一不符即 failed，绝不猜）：
  1. Release tag `collect-step<NN>-<layer>` 存在 → 有产物
  2. tag 下资产：`<layer>-checkpoint.json` + 每个已完成单元一个 `<layer>-uNNNNN.tar.gz`
  3. checkpoint 内部：`unit_rows`(计划行) / `unit_rows_seen`(实采行) /
     `unit_uploaded`(是否上传) / `done_units`(完成单元) / `unit_errors`(未消解错误)

  declared = 计划期上游 returnCount（layer_plan.csv，按 worker_core 同一套唯一化规则取）
  实采     = Σ checkpoint.unit_rows_seen（老 checkpoint 无此字段时退回 Σ unit_rows 并标注）

判据：
  · `declared - 实采` > 1% → partial，必须单列并写原因
  · checkpoint 与资产 parts 对不上（缺资产 / 多资产 / 单元未传 / 有未消解错误 /
    done_units 不齐 / tag 不符）→ **failed，不猜**
  · declared==0 且无资产 → empty（上游空层，不是失败）

幂等：输出内容只由 GitHub 现状决定（时间戳取「最新资产上传时间」，不取 now()），
      同一状态下重复跑字节一致；`--check` 只比对不写盘，差异时退出码 1。
      单元 checkpoint 按 `tag@created_at` 内容寻址缓存，重跑不重复下载。

用法：
  python3 collect/ledger_rebuild.py --stage 04b \
      --plan collect/ledger/04b_plan.json \
      --out collect/ledger/step04b_rebuilt.json
  python3 collect/ledger_rebuild.py --stage 04b --check     # 只验证幂等
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# 阶段 → Release tag 前缀 / 文档标题（与 collect/steps.json 的 tag 字段一致）
STAGE_TAG = {"04b": ("collect-step04-", "STEP04", "全州放量（row_count>300,000 全量补采）"),
             "05b": ("collect-step05-", "STEP05", "县市碎片（5,000~300,000 行）全量补采"),
             "07b": ("collect-step07-", "STEP07", "碎片补齐（1~4,999 行）全量补采"),
             "10b": ("collect-step10-", "STEP10", "宗地面层 batch2+（strong/weak 有效层）")}
GAP_TOL = 0.01          # 用户口径：declared - 实采 超过 1% 必须单列
UNIT_RE = re.compile(r"-u(\d{5})\.tar\.gz$")


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gh(args: list, binary=False, timeout=180):
    cmd = ["gh"] + args
    r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("gh %s 失败：%s" % (" ".join(args), (r.stderr or b"").decode("utf-8", "replace")[:300]))
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def repo_default() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"


# ---------------------------------------------------------------- declared 侧

def declared_index() -> dict:
    """layer_id → 计划期声明行数。

    必须复用 worker_core 的同一套规则：layer_id 撞车的行会被加 `@<state>-<n>` 后缀，
    自己再写一份就会把 11 个 `@STATE-n` 层算成 0（差额 3,153,051 行，实测踩过）。
    """
    from worker_core import _rows_from_csv, _norm_plan_row       # noqa: E402
    return {r["id"]: r["expect"] for r in (_norm_plan_row(x) for x in _rows_from_csv())
            if r["id"]}


def plan_ids(plan_path: str) -> list:
    if not plan_path or not os.path.exists(plan_path):
        return []
    d = json.load(open(plan_path, encoding="utf-8"))
    out = []
    for s in d.get("shards") or []:
        out += list(s.get("layers") or [])
    return out


# ---------------------------------------------------------------- release 侧

def list_releases(repo: str, prefix: str, max_pages: int = 60) -> dict:
    """一次翻页拿全 releases（含 assets 元数据，不下载）。返回 tag → 记录。"""
    tags = {}
    page = 1
    while page <= max_pages:
        raw = gh(["api", "repos/%s/releases?per_page=100&page=%d" % (repo, page)])
        batch = json.loads(raw)
        if not batch:
            break
        for r in batch:
            t = r.get("tag_name") or ""
            if not t.startswith(prefix):
                continue
            tags[t] = {"tag": t, "created_at": r.get("created_at"),
                       "assets": [{"id": a["id"], "name": a["name"], "size": a["size"],
                                   "created_at": a.get("created_at")}
                                  for a in (r.get("assets") or [])]}
        page += 1
    return tags


def fetch_checkpoint(repo: str, tag: str, asset: dict, cache: str, refresh: bool) -> dict:
    """按 `tag@created_at` 内容寻址缓存下载 checkpoint（资产每次发布都会覆盖同名文件）。

    ★ 资产 id 会随 checkpoint 重发而失效（实测跑批中撞到 404 Not Found）：
      下载失败时重新拉一次 tag 元数据拿新 id 再试，绝不静默当「没有 checkpoint」。
    """
    last = None
    for _ in range(3):
        key = re.sub(r"[^A-Za-z0-9._@-]", "_",
                     "%s@%s" % (tag, asset.get("created_at") or asset["id"]))
        path = os.path.join(cache, key + ".json")
        if not refresh and os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))
        try:
            data = gh(["api", "repos/%s/releases/assets/%d" % (repo, asset["id"]),
                       "-H", "Accept: application/octet-stream"], binary=True)
        except Exception as e:                                          # noqa: BLE001
            last = e
            rel = json.loads(gh(["api", "repos/%s/releases/tags/%s" % (repo, tag)]))
            asset = next((x for x in (rel.get("assets") or [])
                          if x["name"].endswith("-checkpoint.json")), None)
            if asset is None:
                raise
            continue
        os.makedirs(cache, exist_ok=True)
        tmp = path + ".tmp"
        open(tmp, "wb").write(data)
        os.replace(tmp, path)
        return json.load(open(path, encoding="utf-8"))
    raise last or RuntimeError("checkpoint 下载失败")


# ---------------------------------------------------------------- 逐层判定

def judge(layer: str, declared, rel, ck, ck_err: str) -> dict:
    """一层一条记录。四态：ok / empty / partial / failed。"""
    rec = {"layer": layer, "tag": None, "declared": declared, "declared_src": "layer_plan.csv",
           "rows": None, "rows_src": None, "parts_assets": 0, "parts_ckpt": None,
           "bytes": 0, "units": None, "units_done": None, "first_upload": None,
           "last_upload": None, "problems": [], "warn": [], "status": "failed", "reason": ""}
    if rel is None:
        if not declared:                       # 计划期就 0 行：上游空层，不算失败
            rec.update(status="empty", reason="上游声明 0 行，无资产（空层）")
        else:
            rec.update(reason="无 Release 资产（tag 不存在）—— 该层从未跑成，不猜行数")
        return rec

    rec["tag"] = rel["tag"]
    assets = rel.get("assets") or []
    ups = [a["created_at"] for a in assets if a.get("created_at")]
    rec["bytes"] = sum(a["size"] or 0 for a in assets)
    rec["first_upload"] = min(ups) if ups else None
    rec["last_upload"] = max(ups) if ups else None
    unit_assets = {}
    for a in assets:
        m = UNIT_RE.search(a["name"])
        if m:
            unit_assets[int(m.group(1))] = a
    rec["parts_assets"] = len(unit_assets)

    ck_asset = next((a for a in assets if a["name"].endswith("-checkpoint.json")), None)
    if ck_asset is None:
        rec.update(reason="有资产无 checkpoint（%d 个 unit 包但无检查点）→ 完成度不可证"
                          % len(unit_assets))
        return rec
    if ck is None:
        rec.update(reason="checkpoint 拉取/解析失败：%s" % (ck_err or "未知"))
        return rec

    if (ck.get("tag") or "") != rel["tag"]:
        rec["problems"].append("checkpoint.tag=%r 与 Release tag 不符" % ck.get("tag"))

    ur = {int(k): int(v or 0) for k, v in (ck.get("unit_rows") or {}).items()}
    seen = ck.get("unit_rows_seen")
    seen = {int(k): int(v or 0) for k, v in seen.items()} if isinstance(seen, dict) else None
    files = {int(k): len(v or []) for k, v in (ck.get("unit_files") or {}).items()}
    up = {int(k): bool(v) for k, v in (ck.get("unit_uploaded") or {}).items()}
    done = {int(x) for x in (ck.get("done_units") or [])}
    errs = {int(k): v for k, v in (ck.get("unit_errors") or {}).items()}
    ack = {int(k) for k in (ck.get("unit_short_ack") or {})}

    rec["units"] = len(ur)
    rec["units_done"] = len(done)
    rec["parts_ckpt"] = sum(files.values()) or None
    if seen is not None:
        rec["rows"], rec["rows_src"] = sum(seen.values()), "unit_rows_seen"
    else:
        rec["rows"], rec["rows_src"] = sum(ur.values()), "unit_rows"
        rec["warn"].append("老 checkpoint 无 unit_rows_seen，行数退回计划值（可能高估）")

    if not ur:
        rec["problems"].append("checkpoint.unit_rows 为空")
    for i, n in sorted(ur.items()):
        if i not in done:
            rec["problems"].append("unit %d 不在 done_units" % i)
        if not up.get(i):
            rec["problems"].append("unit %d 未上传（unit_uploaded=false）" % i)
        if i not in unit_assets:
            rec["problems"].append("unit %d 标记完成但 Release 无 -u%05d.tar.gz" % (i, i))
    for i in sorted(unit_assets):
        if i not in ur:
            rec["problems"].append("Release 有 -u%05d.tar.gz 但 checkpoint 无该单元" % i)
    for i, e in sorted(errs.items()):
        rec["problems"].append("unit %d 残留错误：%s" % (i, str(e)[:80]))
    for i in sorted(ack):
        n = seen.get(i) if seen else None
        rec["warn"].append("unit %d 上游短供已确认（ack rows=%s）" % (i, n))

    # 声明值 vs checkpoint 计划值（两者同源但可能因上游更新而不同，>1% 才提示）
    ck_plan = sum(ur.values())
    if declared and abs(ck_plan - declared) > GAP_TOL * declared:
        rec["warn"].append("checkpoint 计划行 %s 与清单声明 %s 差 %.2f%%"
                           % (f"{ck_plan:,}", f"{declared:,}",
                              100.0 * (ck_plan - declared) / declared))
    # 资产字节为 0 说明空包（历史上出现过 13 个 0 MB 资产）
    if assets and rec["bytes"] == 0:
        rec["problems"].append("资产总字节为 0（空包）")

    if not declared:                            # 清单没声明但真有资产
        if rec["rows"]:
            rec.update(status="ok", reason="清单声明 0 行但实采 %s 行（按实采记账）" % f"{rec['rows']:,}")
        else:
            rec.update(status="empty", reason="清单声明 0 行、实采 0 行")
        if rec["problems"]:
            rec.update(status="failed", reason="；".join(rec["problems"])[:300])
        return rec

    if rec["problems"]:
        rec.update(reason="；".join(rec["problems"])[:300])
        return rec
    if rec["rows"] == 0:
        rec.update(reason="声明 %s 行但实采 0 行" % f"{declared:,}")
        return rec

    gap = declared - rec["rows"]
    rec["gap"] = gap
    rec["gap_pct"] = round(100.0 * gap / declared, 4)
    if gap > GAP_TOL * declared:
        # 区分两种缺口：① 本层自己的单元没跑完（rows < 本层计划）
        #               ② 本层计划行本身就小于清单声明（口径差/上游增长，要按新 returnCount 重采）
        if ck_plan and rec["rows"] >= ck_plan * 0.999:
            rec.update(status="partial",
                       reason=("实采已等于本层 checkpoint 计划行 %s，但清单声明 %s："
                               "计划期口径差 %.2f%%，需按上游当前 returnCount 重采")
                              % (f"{ck_plan:,}", f"{declared:,}", rec["gap_pct"]))
        else:
            rec.update(status="partial",
                       reason="缺口 %.2f%%（实采 %s / 声明 %s，缺 %s 行）"
                              % (rec["gap_pct"], f"{rec['rows']:,}", f"{declared:,}", f"{gap:,}"))
    else:
        rec.update(status="ok", reason="")
    return rec


def scope_layers(ids: list, releases: dict, prefix: str) -> list:
    """本次账本该算哪些层。

    计划里有就用计划；**没有计划时只能拿 Release 里真实存在的 tag 反推层 id，
    并且必须去掉 tag 前缀** —— 2026-10-30 实测踩过：直接 sorted(releases) 拿到的是
    `collect-step04-<layer>`，再去 releases.get(prefix + layer) 就永远 None，
    238 个真资产的层被整片标成 empty（empty 会掩盖 failed，是最坏的一种静默）。
    """
    if ids:
        return list(ids)
    return [t[len(prefix):] for t in sorted(releases) if t.startswith(prefix)]


def extras_not_in_plan(ids: list, releases: dict, prefix: str) -> list:
    """前缀下真实存在、但不在本次计划里的 tag（往轮 pilot / 其他阶段的产物）。"""
    if not ids:
        return []
    idset = set(ids)
    return [t for t in sorted(releases) if t[len(prefix):] not in idset]


def rebuild(stage: str, plan_path: str, cache: str, repo: str, refresh: bool,
            jobs: int, max_pages: int, generated_at: str = "") -> dict:
    prefix, tag, title = STAGE_TAG[stage]
    ids = plan_ids(plan_path)
    dec = declared_index()
    print("[rebuild] %s：计划 %d 层，声明合计 %s 行"
          % (stage, len(ids), f"{sum(dec.get(i) or 0 for i in ids):,}"), flush=True)

    releases = list_releases(repo, prefix, max_pages=max_pages)
    print("[rebuild] Release 扫描：前缀 %s 命中 %d 个 tag" % (prefix, len(releases)), flush=True)

    scope = scope_layers(ids, releases, prefix)

    def work(layer: str) -> dict:
        rel = releases.get(prefix + layer)
        declared = dec.get(layer)          # 清单声明与「有没有计划文件」无关
        ck, err = None, ""
        if rel:
            a = next((x for x in rel["assets"] if x["name"].endswith("-checkpoint.json")), None)
            if a is not None:
                try:
                    ck = fetch_checkpoint(repo, rel["tag"], a, cache, refresh)
                except Exception as e:                       # noqa: BLE001
                    err = str(e)[:200]
        return judge(layer, declared, rel, ck, err)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        recs = list(ex.map(work, scope))
    recs.sort(key=lambda r: (-(r.get("declared") or 0), r["layer"]))

    cnt = {}
    for r in recs:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    declared = sum((r.get("declared") or 0) for r in recs)
    rows = sum((r.get("rows") or 0) for r in recs)
    if not generated_at:
        stamps = [r["last_upload"] for r in recs if r.get("last_upload")]
        generated_at = max(stamps) if stamps else "unknown"

    extras = extras_not_in_plan(ids, releases, prefix)
    agg = {
        "schema": "collect-ledger-rebuild/v1",
        "stage": stage,
        "source_of_truth": "github release assets（checkpoint + unit 包），非 workflow 账本",
        "tag_prefix": prefix,
        "generated_at": generated_at,
        "generated_note": "generated_at = 最新资产上传时间（不取 now()），保证同状态重跑字节一致",
        "tolerance": {"gap_partial": GAP_TOL},
        "plan": {"file": os.path.relpath(plan_path, ROOT) if plan_path and os.path.exists(plan_path) else None,
                 "layers_n": len(ids), "declared_rows": declared},
        "scan_meta": {"tags_under_prefix": len(releases),
                      "note": "采集进行中会持续增长，与账本事实无关；--check 已忽略本字段"},
        "layers_n": len(recs),
        "ok": cnt.get("ok", 0), "empty": cnt.get("empty", 0),
        "partial": cnt.get("partial", 0), "failed": cnt.get("failed", 0),
        "declared": declared, "rows": rows, "gap": declared - rows,
        "gap_pct": round(100.0 * (declared - rows) / declared, 4) if declared else 0.0,
        "assets_total": sum(r["parts_assets"] for r in recs),
        "bytes_total": sum(r["bytes"] for r in recs),
        "gap_gt_tol": [{"layer": r["layer"], "declared": r.get("declared"), "rows": r.get("rows"),
                        "gap": r.get("gap"), "gap_pct": r.get("gap_pct"),
                        "reason": r.get("reason")}
                       for r in recs if r["status"] == "partial"],
        "failed_layers": [{"layer": r["layer"], "reason": r.get("reason"),
                           "problems": r.get("problems")} for r in recs if r["status"] == "failed"],
        "empty_layers": [r["layer"] for r in recs if r["status"] == "empty"],
        "extras_not_in_plan": {"n": len(extras), "tags": extras},
        "records": recs,
    }
    return agg


# ---------------------------------------------------------------- 文档

def render_doc(agg: dict) -> str:
    stage = agg["stage"]
    _, tag, title = STAGE_TAG[stage]
    recs = agg["records"]
    gaps = sorted([r for r in recs if (r.get("gap") or 0) > 0],
                  key=lambda r: (r.get("gap") or 0), reverse=True)
    big = [r for r in recs if r["status"] == "partial"]
    bad = [r for r in recs if r["status"] == "failed"]
    empty = [r for r in recs if r["status"] == "empty"]
    day = (agg["generated_at"] or "")[:10]

    L = ["# %s 全量补采 · 账本重建（%s）" % (tag, day), "",
         "> 本文件**不由 workflow 账本生成**：04b 前几片跑完时账本因文件名不匹配而静默落空"
         "（已由 `98bd461` 修好），已跑完的部分只能从 **Release 资产**反推。",
         "> 真值链：`Release tag` → `checkpoint.json`（unit_rows / unit_rows_seen / "
         "unit_uploaded / done_units / unit_errors）→ `-uNNNNN.tar.gz` 实际存在。"
         "任一环对不上即判 failed，不估算、不补齐。", "",
         "## 一、总账", "",
         "- 阶段：`%s` —— %s" % (stage, title),
         "- 计划：%s 层 / 声明 %s 行（`%s`）"
         % (agg["plan"]["layers_n"] or "?", f"{agg['plan']['declared_rows']:,}", agg["plan"]["file"]),
         "- Release 资产覆盖：**%d / %d 层**（计划内命中 tag）"
         % (sum(1 for r in recs if r.get("tag")), agg["layers_n"]),
         "- 逐态：**ok %d** / empty %d / partial %d / failed %d"
         % (agg["ok"], agg["empty"], agg["partial"], agg["failed"]),
         "- 声明行合计 **%s** / 实采行合计 **%s** / 差额 **%s**（%.3f%%）"
         % (f"{agg['declared']:,}", f"{agg['rows']:,}", f"{agg['gap']:,}", agg["gap_pct"]),
         "- 资产：%s 个单元包 / %s 字节（%.2f GB）"
         % (f"{agg['assets_total']:,}", f"{agg['bytes_total']:,}",
            agg["bytes_total"] / 1e9),
         "- 生成时间（最新资产上传时间）：`%s`" % agg["generated_at"], "",
         "> 实采口径 = `Σ checkpoint.unit_rows_seen`（真采到的行）。"
         "老 checkpoint 缺该字段时退回 `Σ unit_rows`（计划值）并在逐层表标注 `unit_rows`。", ""]

    L += ["## 二、差额 > 1%% 的层（必须逐条说明）", ""]
    if big:
        L += ["| # | 层 | 声明 | 实采 | 缺 | 缺口% | 原因 |", "|---|---|---|---|---|---|---|"]
        for i, r in enumerate(big, 1):
            L.append("| %d | `%s` | %s | %s | %s | %.2f%% | %s |"
                     % (i, r["layer"], f"{r.get('declared') or 0:,}", f"{r.get('rows') or 0:,}",
                        f"{r.get('gap') or 0:,}", r.get("gap_pct") or 0,
                        (r.get("reason") or "")[:100]))
        L += ["", "**为什么会有缺口（按原因归类）**："]
        kinds = {}
        for r in big:
            k = ("上游短供（checkpoint 有 unit_short_ack）" if any("短供" in w for w in r["warn"])
                 else "其他 / 待查" if not r["warn"] else "见备注")
            kinds.setdefault(k, []).append(r["layer"])
        for k, v in kinds.items():
            L.append("- %s：%d 层" % (k, len(v)))
    else:
        L.append("**无。** 所有层实采与声明差额 ≤ 1%。")
    L += [""]

    L += ["## 三、差额绝对值最大的 10 层", ""]
    if gaps:
        L += ["| 层 | 声明 | 实采 | 差额 | 缺口% | 状态 |", "|---|---|---|---|---|---|"]
        for r in gaps[:10]:
            L.append("| `%s` | %s | %s | %s | %.2f%% | %s |"
                     % (r["layer"], f"{r.get('declared') or 0:,}", f"{r.get('rows') or 0:,}",
                        f"{r.get('gap') or 0:,}", r.get("gap_pct") or 0, r["status"]))
    else:
        L.append("**零差额。**")
    L += [""]

    L += ["## 四、failed（%d 层，逐条原因）" % len(bad), ""]
    if bad:
        L += ["| 层 | checkpoint | 资产单元包 | done/units | 原因 |", "|---|---|---|---|---|"]
        for r in bad:
            L.append("| `%s` | %s | %s | %s/%s | %s |"
                     % (r["layer"], "有" if r.get("tag") else "无 tag",
                        r.get("parts_assets"), r.get("units_done") or "-", r.get("units") or "-",
                        (r.get("reason") or "")[:140]))
    else:
        L.append("**无。**")
    L += [""]

    L += ["## 五、empty（%d 层）" % len(empty), ""]
    L += (["| 层 | 声明 | 原因 |", "|---|---|---|"]
          + ["| `%s` | %s | %s |" % (r["layer"], r.get("declared"), (r.get("reason") or "")[:80])
             for r in empty]) if empty else ["**无。**"]
    L += [""]

    if agg["extras_not_in_plan"]["n"]:
        L += ["## 六、不在本次计划内的 step04 Release（%d 个，供交叉核对）"
              % agg["extras_not_in_plan"]["n"], "",
              "这些 tag 是往轮 pilot / 其他阶段的产物，不在 04b 计划清单里，未计入总账：", ""]
        L += ["- `%s`" % t for t in agg["extras_not_in_plan"]["tags"][:30]]
        if agg["extras_not_in_plan"]["n"] > 30:
            L += ["- …（另有 %d 个，见 JSON `extras_not_in_plan.tags`）"
                  % (agg["extras_not_in_plan"]["n"] - 30)]
        L += [""]

    L += ["## 七、逐层台账（%d 层，按声明行数降序）" % len(recs), "",
          "| # | 层 | 声明 | 实采 | 缺口% | 单元(done/all) | 包 | 字节 | 上传(最后) | 状态 | 行数源 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(recs, 1):
        L.append("| %d | `%s` | %s | %s | %.2f%% | %s/%s | %s | %s | %s | %s | %s |"
                 % (i, r["layer"],
                    f"{r['declared']:,}" if r.get("declared") else "-",
                    f"{r['rows']:,}" if r.get("rows") is not None else "-",
                    r.get("gap_pct") or 0.0,
                    r.get("units_done") or "-", r.get("units") or "-",
                    r.get("parts_assets"),
                    f"{r['bytes']:,}" if r.get("bytes") else "-",
                    (r.get("last_upload") or "-")[:16], r["status"], r.get("rows_src") or "-"))
    L += ["", "## 八、复现（幂等）", "", "```bash",
          "# 拉 04b 计划（若本地没有）：gh run download <run-id> -n plan-04b -D collect/ledger",
          "python3 collect/ledger_rebuild.py --stage %s \\" % stage,
          "    --plan collect/ledger/%s_plan.json \\" % stage,
          "    --out collect/ledger/step%sb_rebuilt.json" % stage[:2],
          "python3 collect/ledger_rebuild.py --stage %s --check   # 同状态应输出 IDENTICAL"
          % stage, "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="04b", choices=sorted(STAGE_TAG))
    ap.add_argument("--plan", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--doc", default="")
    ap.add_argument("--cache", default=os.path.join(HERE, "ledger", ".ckpt_cache"))
    ap.add_argument("--repo", default="")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--max-pages", type=int, default=60)
    ap.add_argument("--refresh", action="store_true", help="忽略 checkpoint 缓存，全部重下")
    ap.add_argument("--generated-at", default="", help="覆盖 generated_at（默认取最新资产时间）")
    ap.add_argument("--check", action="store_true", help="只比对现有输出是否一致，不写盘")
    a = ap.parse_args()

    stage = a.stage
    plan = a.plan or os.path.join(HERE, "ledger", "%s_plan.json" % stage)
    out = a.out or os.path.join(HERE, "ledger", "step%sb_rebuilt.json" % stage[:2])
    agg = rebuild(stage, plan, a.cache, a.repo or repo_default(), a.refresh,
                  a.jobs, a.max_pages, a.generated_at)
    doc = a.doc or os.path.join(ROOT, "docs", "%s-FULL-%s.md"
                                % (STAGE_TAG[stage][1], (agg["generated_at"] or utcnow())[:10]))
    body = json.dumps(agg, ensure_ascii=False, indent=1, sort_keys=False)
    md = render_doc(agg)

    if a.check:
        def norm(txt: str) -> str:
            d = json.loads(txt)
            d.pop("scan_meta", None)          # 采集进行中会变，与账本事实无关
            return json.dumps(d, ensure_ascii=False, sort_keys=True)
        same = (os.path.exists(out) and norm(open(out, encoding="utf-8").read()) == norm(body)
                and os.path.exists(doc) and open(doc, encoding="utf-8").read() == md)
        print("IDENTICAL" if same else "DIFFERS（%s / %s）" % (out, doc))
        return 0 if same else 1

    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(body)
    os.makedirs(os.path.dirname(doc), exist_ok=True)
    open(doc, "w", encoding="utf-8").write(md)
    print(json.dumps({k: agg[k] for k in ("stage", "layers_n", "ok", "empty", "partial",
                                          "failed", "declared", "rows", "gap", "gap_pct")},
                     ensure_ascii=False))
    print("写入 %s\n写入 %s" % (out, doc))
    return 0 if agg["failed"] == 0 else 0     # failed 由文档/账本呈现，脚本本身不报错


if __name__ == "__main__":
    raise SystemExit(main())
