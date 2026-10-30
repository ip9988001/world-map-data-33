#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量补采 · 分片执行器（在 GitHub runner 上跑，一片一个 job）。

为什么要有它：GitHub matrix 硬上限 256 job/run，而 step04 剩 272 层、step05 剩 2,753 层。
所以 matrix 的单元是**片**（shard），一片里顺序跑 N 层（step04: 20 层/片，step05/07/10: 200 层/片）。

铁律：
  · **不许静默丢层**：每层要么 ok / empty / partial / failed，四选一，全部落到账本；
    失败层必须带原因（返回码 / err / 差额），绝不 `|| true` 吞错。
  · **断点续跑**：跑之前先算 done（releases 的 tag + 本机 audit），已完成的层记 skipped_done，
    真重跑也只补缺口（pilot 自己的 checkpoint 在 Release 上）。
  · **一片一账本**：写 collect/ledger/<stage>b_shard<N>.json，多片并发不打架；
    汇总文件 collect/step<stage>b_ledger.json 由 merge job 生成。

用法：
  python3 collect/full_shard.py --stage 04 --shard 3 --plan collect/ledger/step04b_plan.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

STAGE_NAMES = {"04": "step04b", "05": "step05b", "07": "step07b", "10": "step10b",
               "04b": "step04b", "05b": "step05b", "07b": "step07b", "10b": "step10b"}
# 差额容忍：实采/声明 差 > 0.2% 记 partial（不是失败，但要在文档里解释）
DIFF_TOL = 0.002


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_layer(step: str, lid: str, workers: int, unit_rows: int, tag_prefix: str = "") -> dict:
    """跑一层，返回账本记录（四态之一 + 原因）。"""
    t0 = time.time()
    cmd = [sys.executable, os.path.join(HERE, "run_step_%s.py" % step),
           "--layer", lid, "--workers", str(workers), "--unit-rows", str(unit_rows)]
    print("▶ %s" % " ".join(cmd), flush=True)
    env = dict(os.environ)
    if tag_prefix:
        # pilot 按这个环境变量决定单元发到哪个 tag —— 必须显式给，
        # 否则全量补采会把数据塞进 tag 名为空/默认的 Release，续跑也就对不上了。
        env["PILOT_RELEASE_TAG"] = tag_prefix + lid
        env["PILOT_HEARTBEAT_PUSH"] = "1"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3 * 3600, env=env)
        rc, out, errout = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return {"layer": lid, "status": "failed", "reason": "job 内单层超时 3h",
                "rc": -1, "elapsed_s": round(time.time() - t0, 1)}
    tail = (out or "")[-1500:] + ("\n--stderr--\n" + errout[-800:] if errout else "")
    print(tail, flush=True)                      # 日志留痕，不吞
    rep = os.path.join(HERE, "reports", lid + ".json")
    rec = {"layer": lid, "rc": rc, "elapsed_s": round(time.time() - t0, 1), "at": now()}
    man = {}
    if os.path.exists(rep):
        try:
            man = json.load(open(rep, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            rec.update(status="failed", reason="报告 JSON 读不动：%s" % str(e)[:80])
            return rec
    declared = man.get("count")
    rows = man.get("rows") or 0
    err = man.get("err") or ""
    diff = man.get("diff")
    rec.update({"declared": declared, "rows": rows, "err": err, "diff": diff,
                "parts": man.get("parts"), "svc": man.get("svc")})
    if rc != 0 or err:
        rec.update(status="failed", reason="rc=%s err=%s" % (rc, err or "?"))
    elif declared == 0:
        rec.update(status="empty", reason="上游声明 0 行，按空层记账")
    elif rows == 0:
        rec.update(status="failed", reason="声明 %s 行但实采 0 行" % declared)
    elif declared and (diff is None or diff > DIFF_TOL):
        rec.update(status="partial",
                   reason="缺口 %.2f%%（实采 %s / 声明 %s）"
                          % (100.0 * (declared - rows) / max(declared, 1), rows, declared))
    else:
        rec.update(status="ok", reason="")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--plan", required=True, help="plan job 产出的层清单 JSON")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--unit-rows", type=int, default=0)
    ap.add_argument("--tag-prefix", default="", help="Release tag 前缀，如 collect-step04-")
    a = ap.parse_args()
    stage = a.stage
    name = STAGE_NAMES.get(stage)
    if not name:
        raise SystemExit("未知 stage %r（只允许 %s）" % (stage, "/".join(STAGE_NAMES)))

    plan = json.load(open(a.plan, encoding="utf-8"))
    shards = plan.get("shards") or []
    if a.shard >= len(shards):
        raise SystemExit("shard %d 越界（plan 只有 %d 片）" % (a.shard, len(shards)))
    layers = shards[a.shard].get("layers") or []
    base = str(plan.get("done_from") or stage)
    unit_rows = a.unit_rows or int(plan.get("unit_rows") or 1000000)
    print("[%s] 片 %d/%d：%d 层，unit_rows=%d"
          % (name, a.shard + 1, len(shards), len(layers), unit_rows), flush=True)

    # 断点续跑：已完成的层直接记 skipped_done（不重采）
    from worker_core import done_layers          # noqa: E402
    try:
        done = set(done_layers(base))
    except Exception as e:  # noqa: BLE001
        done = set()
        print("⚠️ done_layers 取不到（%s），本片不做 skipped_done 判定" % str(e)[:100], flush=True)

    recs = []
    for i, lid in enumerate(layers, 1):
        if lid in done:
            recs.append({"layer": lid, "status": "skipped_done", "rows": None,
                         "declared": None, "reason": "已采（release tag / 本机 audit 判定完成）",
                         "at": now()})
            print("[%s] (%d/%d) ⏭ %s 已采" % (name, i, len(layers), lid), flush=True)
            continue
        print("[%s] (%d/%d) %s" % (name, i, len(layers), lid), flush=True)
        recs.append(run_layer(base, lid, a.workers, unit_rows, a.tag_prefix))

    ok = [r for r in recs if r["status"] == "ok"]
    empty = [r for r in recs if r["status"] == "empty"]
    part = [r for r in recs if r["status"] == "partial"]
    fail = [r for r in recs if r["status"] == "failed"]
    skip = [r for r in recs if r["status"] == "skipped_done"]
    led = {"schema": "collect-ledger/v1", "stage": name, "step": stage, "shard": a.shard,
           "shards_total": len(shards), "size": plan.get("size"),
           "unit_rows": unit_rows, "at": now(),
           "layers_n": len(recs), "ok": len(ok), "empty": len(empty),
           "partial": len(part), "failed": len(fail), "skipped_done": len(skip),
           "rows": sum((r.get("rows") or 0) for r in recs),
           "declared": sum((r.get("declared") or 0) for r in recs),
           "records": recs}
    # 账本文件名必须用**传入的 stage 前缀**（04b/05b/07b/10b），
    # 因为 workflow 的提交/artifact/汇总三处都按 collect/ledger/${STAGE}_shard*.json 找；
    # 用 name（step04b）会让账本静默落空 —— 2026-10-30 实测 4 片跑完 0 账本就是这个 bug。
    lname = stage if stage.endswith("b") else name
    out = os.path.join(HERE, "ledger", "%s_shard%02d.json" % (lname, a.shard))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(led, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[%s] 片 %d 账本：ok=%d empty=%d partial=%d failed=%d skipped=%d rows=%d"
          % (name, a.shard, len(ok), len(empty), len(part), len(fail), len(skip), led["rows"]),
          flush=True)
    if fail:
        print("::warning::%s 片 %d 有 %d 层失败：%s"
              % (name, a.shard, len(fail), ", ".join(r["layer"] for r in fail[:5])), flush=True)
    return 0            # 片本身不算失败（失败层已在账本里逐条记原因）；merge 会按账本判定


if __name__ == "__main__":
    raise SystemExit(main())
