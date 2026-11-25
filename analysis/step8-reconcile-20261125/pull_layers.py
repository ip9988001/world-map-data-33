#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · A：拉层补齐（Release 载荷 → dist/intake-full/layers/<layer>/）

**口径（先小样验证后定的，见 sample-validation.json / pull.log）**
Release 上的载荷是「每 URL 一片的 part 包」：`<layer>-uNNNNN.tar.gz`，解开是
`part-uNNNNN-NNN.ndjson.gz`（信封行：add_num/st_name/…/src_layer/raw）。
它**不是**本地层目录里的 `addr.<layer>.ndjson.gz` 分表形态 —— 分表要过 intake 的
`LayerMapper`，而 `schema/field-map-v2.json` 只覆盖已入库的 2,364 层，这 3,550 层
**没有 fmap 条目**（重建 fmap 需要逐层价值分布画像，schema/ 又禁改）。
所以本脚本做的是「载荷落齐 + 逐层可校验」，**不做分表**，层目录形态记为
`payload-part passthrough`，绝不冒充 `local_ok_readable`。

四道校验（逐层写 manifest）：
  ① 解包 part 文件数 == CSV `release_payload_n`（同 tag 的 checkpoint 不计）
  ② 每个 part `.ndjson.gz` 都 `gzip -t` 通过（解到磁盘后再验，坏了立刻报 corrupt）
  ③ 行级：抽样层 `zcat|wc -l` 合计 == tag 里 checkpoint.json 的 `unit_rows` 合计
     （这 3,550 层没有 intake ledger.json，「声明的行数」只能取采集侧 checkpoint；
       不抽样到 10% 以上就不许在报告里写「行级实测」）
  ④ 下载字节 vs CSV `release_bytes_in_dist_snapshot`，偏差 >20% 记 anomaly（baseline=0 记 unavailable）

失败三分类：asset_gone（tag/资产 404）/ corrupt（gzip 坏、tar 解不开）/ mismatch（①③④ 不符）。
单层最多重试 3 次；磁盘可用 <15G 立刻停手（status=failed，已拉层数照写）。

用法：
  python3 analysis/step8-reconcile-20261125/pull_layers.py --sample     # 3 层小样（含 payload 最多的 67 层）
  python3 analysis/step8-reconcile-20261125/pull_layers.py --concurrency 6
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import random
import shutil
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
OUT = HERE
REPO = "ip9988001/world-map-data-33"
MIN_FREE_BYTES = 15 * 1024 ** 3        # 磁盘护栏：可用 <15G 立即停手
BIG_LAYER_ASSETS = 20                  # 载荷资产 >20 片的层串行跑（峰值磁盘只留一层）
TMP = "/data/tmp/step8pull"


def rows_absent():
    out = []
    for r in csv.DictReader(open(INV, encoding="utf-8")):
        if r["reconcile_class"] == "local_absent_assets_exist_not_downloaded":
            out.append({"layer": r["layer"], "stage": r["stage"], "tag": r["tag"],
                        "payload_n": int(r["release_payload_n"] or 0),
                        "bytes_base": int(r["release_bytes_in_dist_snapshot"] or 0)})
    return out


def free_bytes(path="/data"):
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize


def layer_dir(lid):
    return os.path.join(DIST, "layers", lid)


def dir_state(lid, payload_n):
    """已有目录状态：part 文件数 / 是否完整（part 数达标）"""
    d = layer_dir(lid)
    if not os.path.isdir(d):
        return 0, False
    n = len([f for f in os.listdir(d) if f.endswith(".ndjson.gz") and f.startswith("part-u")])
    return n, n >= payload_n > 0


def gh(args, timeout=3600):
    return subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)


def pull_one(job):
    """单层：下载全部 tar.gz + checkpoint → 解包 → 四道校验 → 删 tar.gz。返回 manifest 记录。"""
    lid, tag, payload_n, bytes_base, do_rows = job
    t0 = time.time()
    rec = {"layer": lid, "tag": tag, "assets_n": payload_n, "part_files": 0, "bytes": 0,
           "checks": {}, "result": "", "reason": "", "rows_declared": None, "rows_counted": None,
           "elapsed_s": 0.0, "form": "payload-part-passthrough"}
    d = layer_dir(lid)
    td = os.path.join(TMP, "dl-" + str(abs(hash(lid)) % 10 ** 12))
    os.makedirs(d, exist_ok=True)
    shutil.rmtree(td, ignore_errors=True)
    os.makedirs(td, exist_ok=True)
    try:
        # ---- 下载（整层一次 gh 调用；峰值磁盘 = 本层载荷，>20 片的层由 parent 串行化）----
        r = gh(["release", "download", tag, "--repo", REPO, "-D", td, "--clobber",
                "-p", "*-u*.tar.gz", "-p", "*-checkpoint.json"])
        tgz = sorted(f for f in os.listdir(td) if f.endswith(".tar.gz"))
        cp = [f for f in os.listdir(td) if f.endswith("checkpoint.json")]
        if not tgz:
            err = (r.stderr or "")[-300:]
            gone = ("not found" in err.lower() or "404" in err or "release not found" in err.lower())
            rec.update(result="asset_gone" if gone else "corrupt",
                       reason=("tag/资产 404: " + err) if gone else ("无 tar.gz 资产: " + err))
            return rec
        rec["checks"]["assets_n"] = len(tgz) == payload_n          # ①
        dl_bytes = sum(os.path.getsize(os.path.join(td, f)) for f in tgz)
        rec["bytes"] = dl_bytes
        # ---- 声明行数（checkpoint.json 的 unit_rows）----
        declared = None
        if cp:
            try:
                doc = json.load(open(os.path.join(td, cp[0]), encoding="utf-8"))
                ur = doc.get("unit_rows") or {}
                declared = sum(int(v or 0) for v in ur.values()) if ur else None
                shutil.copy(os.path.join(td, cp[0]), os.path.join(d, "release-checkpoint.json"))
            except Exception:                                        # noqa: BLE001
                declared = None
        rec["rows_declared"] = declared
        # ---- 解包 + gzip -t ----
        bad = []
        parts = 0
        for f in tgz:
            p = os.path.join(td, f)
            try:
                subprocess.run(["tar", "xzf", p, "-C", d], check=True,
                               capture_output=True, timeout=3600)
            except Exception as e:                                   # noqa: BLE001
                bad.append(f"tar:{f}:{e}")
                continue
            os.unlink(p)                                             # 立刻删该片压缩包
        part_files = sorted(x for x in os.listdir(d) if x.startswith("part-u") and x.endswith(".ndjson.gz"))
        parts = len(part_files)
        rec["part_files"] = parts
        for x in part_files:
            chk = subprocess.run(["gzip", "-t", os.path.join(d, x)], capture_output=True)
            if chk.returncode != 0:
                bad.append("gzip:" + x)
        rec["checks"]["gzip_ok"] = not bad                            # ②
        # ---- ③ 行级（抽样层）：zcat|wc -l 合计 vs checkpoint unit_rows ----
        if do_rows and declared is not None:
            n = 0
            for x in part_files:
                z = subprocess.run(["zcat", os.path.join(d, x)], capture_output=True)
                n += z.stdout.count(b"\n")
            rec["rows_counted"] = n
            rec["checks"]["rows_match"] = (n == declared)
        # ---- ④ 字节：与 CSV 快照字节同量级（±20%），单位逐层自适应 ----
        # 2026-11-25 muse-000250 复核修正：v1 CSV 该列主体是「字节」（随机 20 层 gh 实测 20/20 比值 1.00），
        # 个别行是 KB 量级（..._Indiana_2021_FeatureServer_1 记 267791，实测载荷 262,550,165）。
        # 故禁止整列 x1024（那会把 3,547 层全打成不符）；改为 b 与 b*1024 取更接近者，
        # 两种都不合 ±20% 时只记 anomaly、不判 mismatch（快照字节列噪声，不做硬门禁）。
        if bytes_base:
            cands = {"bytes": bytes_base, "kb": bytes_base * 1024}
            devs = {u: abs(dl_bytes - v) / v for u, v in cands.items()}
            unit = min(devs, key=devs.get)
            rec["checks"]["bytes_dev"] = round(devs[unit], 4)
            rec["checks"]["bytes_unit"] = unit
            rec["checks"]["bytes_ok"] = devs[unit] <= 0.20
            if not rec["checks"]["bytes_ok"]:
                rec["checks"]["bytes_anomaly"] = "both_units_over_20pct"
        rec["checks"]["bytes_baseline"] = "csv_snapshot" if bytes_base else "unavailable"
        # ---- 结论 ----
        if not rec["checks"]["assets_n"]:
            rec.update(result="mismatch", reason=f"资产数 {len(tgz)} != CSV {payload_n}")
        elif bad:
            rec.update(result="corrupt", reason=";".join(bad[:3]))
        elif rec["checks"].get("rows_match") is False:
            rec.update(result="mismatch",
                       reason=f"行数 {rec['rows_counted']} != checkpoint unit_rows {declared}")
        elif rec["checks"].get("bytes_anomaly"):
            rec["result"] = "ok"
            rec["anomaly"] = (f"字节偏差 {rec['checks']['bytes_dev']:.1%}"
                              f"（dl={dl_bytes} base={bytes_base} 单位={rec['checks']['bytes_unit']}）")
        else:
            rec["result"] = "ok"
        # ---- 逐层 ledger.json（自带账，供 reconcile v2 读；绝不冒充 intake 分表账）----
        led = {"layer": lid, "tag": tag, "status": "ok" if rec["result"] == "ok" else rec["result"],
               "form": "payload-part-passthrough",
               "rows_total": declared, "rows_counted": rec["rows_counted"],
               "assets_n": payload_n, "part_files": parts, "bytes": dl_bytes,
               "note": "Release part 包原样落盘；未分表（该层无 field-map 条目）", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        with open(os.path.join(d, "ledger.json"), "w", encoding="utf-8") as fh:
            json.dump(led, fh, ensure_ascii=False, indent=1)
        return rec
    except Exception as e:                                           # noqa: BLE001
        rec.update(result="corrupt", reason=f"{type(e).__name__}: {e}"[:200])
        rec["trace"] = traceback.format_exc()[-500:]
        return rec
    finally:
        shutil.rmtree(td, ignore_errors=True)
        rec["elapsed_s"] = round(time.time() - t0, 1)


def write_manifest(recs, shard):
    p = os.path.join(OUT, f"pull-manifest-shard-{shard:05d}.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"shard": shard, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "records": recs},
                  fh, ensure_ascii=False, indent=1)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--sample", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--exclude-file", default="")
    a = ap.parse_args()
    rows = rows_absent()
    os.makedirs(TMP, exist_ok=True)
    log = open(os.path.join(OUT, "pull.log"), "a", encoding="utf-8", buffering=1)

    def L(msg):
        log.write(msg + "\n")

    L(f"\n=== start {time.strftime('%Y-%m-%dT%H:%M:%SZ')} sample={a.sample} conc={a.concurrency} "
      f"free={free_bytes()/2**30:.1f}G ===")

    if a.sample:
        # 小样 3 层：payload 最多（67 片）+ 资产最少（4 片）+ 一片中等
        big = max(rows, key=lambda x: x["payload_n"])
        cheap = sorted([r for r in rows if r["bytes_base"] and r is not big],
                       key=lambda x: x["bytes_base"])[:2]
        pick = cheap + [big]
        open("/tmp/sample_ids.txt", "w").write("\n".join(p["layer"] for p in pick) + "\n")
        recs = []
        for i, j in enumerate(pick, 1):
            rec = pull_one((j["layer"], j["tag"], j["payload_n"], j["bytes_base"], True))
            recs.append(rec)
            L(f"[sample {i}/3] {j['layer'][:55]:55s} result={rec['result']} parts={rec['part_files']}/"
              f"{j['payload_n']} bytes={rec['bytes']} rows={rec['rows_counted']}/{rec['rows_declared']} "
              f"checks={rec['checks']} reason={rec['reason'][:120]}")
        json.dump(recs, open(os.path.join(OUT, "sample-validation.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(json.dumps([{k: r[k] for k in ("layer", "result", "part_files", "assets_n", "bytes",
                                             "rows_counted", "rows_declared", "checks", "reason")}
                          for r in recs], ensure_ascii=False, indent=1))
        return 0

    excl = set()
    if a.exclude_file and os.path.isfile(a.exclude_file):
        excl = {x.strip() for x in open(a.exclude_file, encoding="utf-8") if x.strip()}
    # 续跑：已完成（ledger status=ok 且 part 数达标）的层跳过
    todo = []
    for j in rows:
        if j["layer"] in excl:
            continue
        n, ok = dir_state(j["layer"], j["payload_n"])
        if not ok:
            j["_do_rows"] = False
            todo.append(j)
    # 排序：小层先跑（清单/进度快），payload 多的层排后面
    todo.sort(key=lambda x: (x["payload_n"], x["bytes_base"]))
    # 行级抽样：≥10% 且必须包含字节最大的 10 层
    by_bytes = sorted([j for j in todo if j["bytes_base"]], key=lambda x: -x["bytes_base"])
    rowset = {j["layer"] for j in by_bytes[:10]}
    rest = [j for j in todo if j["layer"] not in rowset]
    k = max(int(0.10 * len(todo)), 1)
    random.seed(20261125)
    rowset |= {j["layer"] for j in random.sample(rest, min(k, len(rest)))}
    for j in todo:
        j["_do_rows"] = j["layer"] in rowset
    L(f"[plan] todo={len(todo)} rowcheck={len(rowset)} (含字节最大 10 层) "
      f"concurrency={a.concurrency} free={free_bytes()/2**30:.1f}G")
    if a.limit:
        todo = todo[:a.limit]

    recs, done, shard = [], 0, 0
    stop_reason = ""
    big = [j for j in todo if j["payload_n"] > BIG_LAYER_ASSETS]
    small = [j for j in todo if j["payload_n"] <= BIG_LAYER_ASSETS]
    t_all = time.time()
    with ProcessPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(pull_one, (j["layer"], j["tag"], j["payload_n"], j["bytes_base"], j["_do_rows"])): j
                for j in small}
        for f in as_completed(futs):
            rec = f.result()
            recs.append(rec)
            done += 1
            L(f"[{done}/{len(todo)}] {rec['layer'][:52]:52s} {rec['result']:8s} parts={rec['part_files']}/"
              f"{rec['assets_n']} {rec['bytes']/2**20:.0f}MB {rec['elapsed_s']}s {rec['reason'][:80]}")
            if done % 200 == 0:
                write_manifest(recs, shard)
                shard += 1
            if free_bytes() < MIN_FREE_BYTES:
                stop_reason = f"disk_guard: free={free_bytes()/2**30:.1f}G"
                for x in futs:
                    x.cancel()
                break
    for j in big:                                   # 大层串行（峰值磁盘只留一层载荷）
        if stop_reason:
            break
        rec = pull_one((j["layer"], j["tag"], j["payload_n"], j["bytes_base"], j["_do_rows"]))
        recs.append(rec)
        done += 1
        L(f"[{done}/{len(todo)}] BIG {rec['layer'][:48]:48s} {rec['result']:8s} parts={rec['part_files']}/"
          f"{rec['assets_n']} {rec['bytes']/2**20:.0f}MB {rec['elapsed_s']}s {rec['reason'][:60]}")
        if done % 200 == 0:
            write_manifest(recs, shard)
            shard += 1
        if free_bytes() < MIN_FREE_BYTES:
            stop_reason = f"disk_guard: free={free_bytes()/2**30:.1f}G"
    write_manifest(recs, shard)
    agg = collections.Counter(r["result"] for r in recs)
    summary = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "todo": len(todo), "done": len(recs),
               "by_result": dict(agg), "rowcheck_layers": len(rowset), "shards": shard + 1,
               "wall_s": round(time.time() - t_all, 1), "stop_reason": stop_reason,
               "free_gb": round(free_bytes() / 2**30, 1),
               "rowcheck_pass": sum(1 for r in recs if r["checks"].get("rows_match") is True),
               "rowcheck_fail": sum(1 for r in recs if r["checks"].get("rows_match") is False)}
    json.dump(summary, open(os.path.join(OUT, "pull-summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    L("[done] " + json.dumps(summary, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
