#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""断点续跑实证（可复跑，隔离目录，不污染全量跑的 .done / rows-*.json）。

做法：
  1. 从计划里挑 6 个中等大小的层（同一条命令跑到第 2 个层附近强制 kill -9）
  2. 记录这时的「已完成层数 / 行数 / 每个 rows-*.json 的 mtime」
  3. 用**完全相同的命令**重启：必须打印「跳过已完成 N 层」，只跑剩下的
  4. 断言：① 跳过数与已完成数一致 ② 行数相加 == 6 层的真实总行数 ③ 已完成层文件没被重写

用法：python3 collect/tests/resume_proof.py
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
ROOT = os.path.dirname(COLLECT)
OUT = "/tmp/ct-resume-out"
PROG = "/tmp/ct-resume-prog"
LOG = "/tmp/ct-resume-run.log"
PLAN = os.path.join(COLLECT, "ledger", "county_plan_all.json")


def cmd(layers, extra=()):
    return ([sys.executable, os.path.join(COLLECT, "county_assign.py"),
             "--layers", ",".join(layers), "--out", OUT, "--concurrency", "2"] + list(extra))


def env():
    e = dict(os.environ)
    e["COUNTY_PROGRESS"] = PROG
    return e


def pick(n=6):
    plan = json.load(open(PLAN, encoding="utf-8"))
    rows = {}
    for f in os.listdir(os.path.join(ROOT, "analysis", "tiger_county")):
        if f.startswith("rows-") and f.endswith(".json"):
            try:
                d = json.load(open(os.path.join(ROOT, "analysis", "tiger_county", f)))
                rows[d["layer"]] = d.get("rows") or 0
            except Exception:                        # noqa: BLE001
                pass
    cand = sorted(((r, k) for k, r in rows.items() if 40000 <= r <= 250000))
    return [k for _, k in cand[:n]]


def stats():
    ok = {}
    for f in os.listdir(OUT) if os.path.isdir(OUT) else []:
        if f.startswith("rows-") and f.endswith(".json"):
            p = os.path.join(OUT, f)
            try:
                d = json.load(open(p, encoding="utf-8"))
            except Exception:                        # noqa: BLE001
                continue
            ok[d["layer"]] = {"rows": d.get("rows") or 0, "mtime": os.path.getmtime(p)}
    return ok


def main() -> int:
    layers = pick()
    if len(layers) < 4:
        print("❌ 挑不到足够的层，先跑一部分判县再来")
        return 1
    shutil.rmtree(OUT, ignore_errors=True)
    shutil.rmtree(PROG, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)

    print("样本 %d 层：%s" % (len(layers), layers))
    # ---- 第一段：跑到第 2 个层完成左右，kill -9（模拟被超时杀掉）
    p = subprocess.Popen(cmd(layers), env=env(), stdout=open(LOG, "w"), stderr=subprocess.STDOUT,
                         start_new_session=True)
    deadline = time.time() + 90
    killed_after = None
    while time.time() < deadline:
        time.sleep(1)
        if len(stats()) >= 2:
            time.sleep(1)
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)     # 杀整个进程组，模拟 OOM/超时
            killed_after = round(time.time() - (deadline - 90), 1)
            break
    p.wait()
    before = stats()
    rows_before = sum(v["rows"] for v in before.values())
    print("kill -9 于 %.1fs：已完成 %d 层 / %d 行" % (killed_after or -1, len(before), rows_before))

    # ---- 第二段：同一条命令重启，必须跳过已完成的
    t0 = time.time()
    r = subprocess.run(cmd(layers), env=env(), capture_output=True, text=True)
    log2 = r.stdout + r.stderr
    after = stats()
    rows_after = sum(v["rows"] for v in after.values())

    skipped = None
    for line in log2.splitlines():
        if "待跑" in line and "跳过已完成" in line:
            skipped = int(line.split("跳过已完成")[1].split("层")[0].strip())
            break
    rewritten = [k for k in before if k in after and abs(after[k]["mtime"] - before[k]["mtime"]) > 1e-6]
    total_rows = sum(json.load(open(os.path.join(ROOT, "analysis", "tiger_county",
                                                "rows-%s.json" % k), encoding="utf-8")).get("rows") or 0
                     for k in layers)

    rec = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "what": "断点续跑实测：%d 层小样，跑到中途 kill -9，重启同一条命令" % len(layers),
        "sample_layers": layers,
        "killed_after_s": killed_after,
        "layers_before": len(before), "rows_before": rows_before,
        "skipped_on_restart": skipped,
        "layers_after": len(after), "rows_after": rows_after,
        # write_doc 直接读这两个键（老字段名，保持兼容）
        "skipped": skipped, "todo": len(layers) - (skipped or 0),
        "rows_total_expected": total_rows,
        "files_rewritten": rewritten,
        "restart_wall_s": round(time.time() - t0, 1),
        "verdict": ("重启后跳过已完成 %s 层（= kill 前的 %d 层），只跑剩余 %d 层；"
                    "行数相加 %d == 6 层真实总行数 %d；已完成层 rows-*.json 重写数 %d"
                    % (skipped, len(before), len(layers) - (skipped or 0),
                       rows_after, total_rows, len(rewritten))),
        "progress_dir": PROG + "（隔离目录，避免污染全量跑）",
        "log": LOG,
    }
    out = os.path.join(ROOT, "analysis", "county", "resume-test.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(rec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: rec[k] for k in ("killed_after_s", "layers_before", "rows_before",
                                          "skipped_on_restart", "layers_after", "rows_after",
                                          "rows_total_expected", "files_rewritten")},
                     ensure_ascii=False, indent=1))
    print("→", out)
    ok = (skipped == len(before) and rows_after == total_rows and len(after) == len(layers)
          and not rewritten)
    print("✅ 断点续跑成立" if ok else "❌ 断点续跑不成立")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
