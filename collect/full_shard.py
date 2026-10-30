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
import re
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
# 单层墙钟上限：必须**远小于** job 的 350 分钟，否则一个卡死的上游会把整片带进
# cancelled（2026-10-30 实测 shard 1/3/6 就卡在这里，最后连账本都没写出来）。
LAYER_TIMEOUT_MIN = float(os.environ.get("SHARD_LAYER_TIMEOUT_MIN") or 60)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_layer(step: str, lid: str, workers: int, unit_rows: int, tag_prefix: str = "",
              layer_timeout_min: float = LAYER_TIMEOUT_MIN) -> dict:
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
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=max(60, int(layer_timeout_min * 60)), env=env)
        rc, out, errout = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return {"layer": lid, "status": "failed",
                "reason": "job 内单层超时 %.0f 分钟（--layer-timeout）" % layer_timeout_min,
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


def write_ledger(out, name, stage, shard, shards, plan, unit_rows, forced_here,
                 layers, recs, partial_run):
    """写一片账本。**每跑完一层就写一次**，不是最后写一次。

    ★ 2026-10-30 事故：shard 1/3/6 卡在某个上游（HTTP 挂死不返回），job 被 350 分钟上限
      掐成 cancelled，而账本只在循环结束后写 → 前面已经跑完的层也一起消失，
      整片变成「cancelled，零痕迹」。增量写盘后，哪怕半路被杀，已跑完的层也留得下，
      末尾标 partial_run=true 说明「这片没跑完」。
    """
    cnt = {}
    for r in recs:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    led = {"schema": "collect-ledger/v1", "stage": name, "step": stage, "shard": shard,
           "shards_total": len(shards), "size": plan.get("size"),
           "unit_rows": unit_rows, "at": now(),
           "forced_n": len(forced_here),
           "layers_planned": len(layers), "layers_n": len(recs),
           "partial_run": bool(partial_run),
           "ok": cnt.get("ok", 0), "empty": cnt.get("empty", 0),
           "partial": cnt.get("partial", 0), "failed": cnt.get("failed", 0),
           "skipped_done": cnt.get("skipped_done", 0),
           "rows": sum((r.get("rows") or 0) for r in recs),
           "declared": sum((r.get("declared") or 0) for r in recs),
           "records": recs}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    json.dump(led, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    return led


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--plan", required=True, help="plan job 产出的层清单 JSON")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--unit-rows", type=int, default=0)
    ap.add_argument("--tag-prefix", default="", help="Release tag 前缀，如 collect-step04-")
    ap.add_argument("--layer-timeout", type=float, default=LAYER_TIMEOUT_MIN,
                    help="单层墙钟上限（分钟，默认 60；必须远小于 job 的 350 分钟）")
    ap.add_argument("--force-layers", default="",
                    help="逗号分隔的层 id：即使已判完成也强制重跑（补 cancelled 片的半截层）")
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

    # ★ 强制重跑名单：done_layers 只看 tag+checkpoint，看不见「单元标完成但产物没上传」
    #   和「计划期口径差」。cancelled 片里就有一大批这种半截层 —— 不定点重跑就永久钉死。
    #   同时记下「上轮已有几个单元包」，用于在账本里标「跨轮」（不假装一轮跑完）。
    forced = {x.strip() for x in a.force_layers.split(",") if x.strip()}
    prior = {}
    if forced:
        try:
            from worker_core import release_done      # noqa: E402
            prior = dict(release_done(base))
        except Exception as e:  # noqa: BLE001
            print("⚠️ release_done 取不到（%s），跨轮标注退化为无" % str(e)[:100], flush=True)
    forced_here = [lid for lid in layers if lid in forced]
    if forced_here:
        print("[%s] 本片含 %d 层强制重跑：%s"
              % (name, len(forced_here), ", ".join(forced_here[:3])), flush=True)

    # 账本路径先算好：循环里每跑完一层就落一次盘（被杀也留痕）
    lname = stage if stage.endswith("b") else name
    out = os.path.join(HERE, "ledger", "%s_shard%02d.json" % (lname, a.shard))

    def flush():
        return write_ledger(out, name, stage, a.shard, shards, plan, unit_rows, forced_here,
                            layers, recs, partial_run=True)

    recs = []
    for i, lid in enumerate(layers, 1):
        if lid in done and lid not in forced:
            recs.append({"layer": lid, "status": "skipped_done", "rows": None,
                         "declared": None, "reason": "已采（release tag / 本机 audit 判定完成）",
                         "at": now()})
            print("[%s] (%d/%d) ⏭ %s 已采" % (name, i, len(layers), lid), flush=True)
            flush()
            continue
        print("[%s] (%d/%d) %s" % (name, i, len(layers), lid), flush=True)
        rec = run_layer(base, lid, a.workers, unit_rows, a.tag_prefix, a.layer_timeout)
        if lid in forced:
            pu = sum(1 for n in ((prior.get(lid) or {}).get("assets") or [])
                     if re.search(r"-u\d{5}\.tar\.gz$", n or ""))
            rec.update({"forced": True, "prior_units": pu, "cross_round": bool(pu)})
            if pu:
                note = "跨轮：上轮已有 %d 个单元包，本轮只补缺口" % pu
                rec["reason"] = (rec.get("reason") + "；" + note) if rec.get("reason") else note
        recs.append(rec)
        flush()          # 每层落一次账：被 350 分钟掐掉时，已跑完的层不会跟着蒸发

    # 账本文件名必须用**传入的 stage 前缀**（04b/05b/07b/10b），
    # 因为 workflow 的提交/artifact/汇总三处都按 collect/ledger/${STAGE}_shard*.json 找；
    # 用 name（step04b）会让账本静默落空 —— 2026-10-30 实测 4 片跑完 0 账本就是这个 bug。
    led = write_ledger(out, name, stage, a.shard, shards, plan, unit_rows, forced_here,
                       layers, recs, partial_run=False)
    print("[%s] 片 %d 账本：ok=%d empty=%d partial=%d failed=%d skipped=%d rows=%d"
          % (name, a.shard, led["ok"], led["empty"], led["partial"], led["failed"],
             led["skipped_done"], led["rows"]), flush=True)
    if led["failed"]:
        print("::warning::%s 片 %d 有 %d 层失败：%s"
              % (name, a.shard, led["failed"],
                 ", ".join(r["layer"] for r in recs if r["status"] == "failed")[:200]),
              flush=True)
    return 0            # 片本身不算失败（失败层已在账本里逐条记原因）；merge 会按账本判定


if __name__ == "__main__":
    raise SystemExit(main())
