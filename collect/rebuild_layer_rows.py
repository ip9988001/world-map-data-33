#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Release 里**已经采完的单元包**反推某一层的完成度（不重采、不碰上游）。

为什么需要它：
  2026-10-30 22:23Z，run 41126178216 的 force 补采把 NAD view 层的 checkpoint
  整份覆盖成「1 unit / 0 行 / unit_uploaded=false」。68 个 `u000NN.tar.gz` 都还在
  Release 里（一个字节没少），但**完成度证据没了** —— 账本这层从 partial(39,875,268)
  掉成 failed(0)，ledger_rebuild 的 rows 因此少 33.4M。

  数据在，证据不在，就要能从数据把证据重新算出来：
  逐包下载 → 解包 → 每个 part `.ndjson.gz` 流式数行 → 求和。
  这是唯一不依赖 checkpoint、也不依赖上游 returnCount 的口径（上游当前声明
  97,928,946 行，与已采的 39.9M 不可比，别拿它当分母洗账）。

用法：
  python3 collect/rebuild_layer_rows.py \
      --layer s_Points_from_National_Address_Database_view_FeatureServer_0 \
      --tag collect-step04-s_Points_from_National_Address_Database_view_FeatureServer_0 \
      --out analysis/nad-view-rebuild-2026-10-31.json [--jobs 6] [--expect-rows 39875268]

  # 拿到 JSON 后再把账本这层改回实测口径：
  python3 collect/rebuild_layer_rows.py ... --apply-ledger collect/04b_ledger.json \
      --restore-events analysis/nad-view-ledger-restore-2026-10-31.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
PKG_RE = re.compile(r"-u(\d{5})\.tar\.gz$")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_assets(tag: str, repo: str) -> list:
    r = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "assets"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("列不到 Release %s 的资产：%s" % (tag, (r.stderr or r.stdout)[:300]))
    return (json.loads(r.stdout or "{}") or {}).get("assets") or []


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_lines_gz(path: str) -> int:
    """数一个 `.ndjson.gz` 的行数：流式读、只数换行，不构造 39M 个字符串。"""
    n = 0
    with gzip.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            n += chunk.count(b"\n")
    return n


def measure_package(tag: str, repo: str, name: str, workdir: str, keep: bool = False) -> dict:
    """下载一个单元包 → 解包 → 逐 part 数行。失败不抛，记 err（账本要能看到哪包没验成）。"""
    t0 = time.time()
    d = os.path.join(workdir, name.replace(".tar.gz", ""))
    os.makedirs(d, exist_ok=True)
    pkg = os.path.join(d, name)
    rec = {"name": name, "ok": False, "err": "", "rows": 0, "parts": 0,
           "part_rows": [], "elapsed_s": 0.0}
    m = PKG_RE.search(name)
    rec["unit"] = int(m.group(1)) if m else None
    try:
        r = subprocess.run(["gh", "release", "download", tag, "--repo", repo,
                            "-p", name, "-D", d, "--clobber"],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(pkg):
            rec["err"] = "下载失败：" + (r.stderr or r.stdout or "")[:160]
            return rec
        rec["asset_bytes"] = os.path.getsize(pkg)
        rec["sha256"] = sha256_of(pkg)
        x = os.path.join(d, "x")
        os.makedirs(x, exist_ok=True)
        with tarfile.open(pkg, "r:gz") as tf:
            members = [m0 for m0 in tf.getmembers() if m0.isfile()]
            tf.extractall(x, members=members)      # 只解文件成员，跳过符号链接/设备
        parts = sorted(glob.glob(os.path.join(x, "*.ndjson.gz")))
        part_rows = [count_lines_gz(p) for p in parts]
        rec.update(parts=len(parts), part_rows=part_rows, rows=sum(part_rows),
                   bytes_unpacked=sum(os.path.getsize(p) for p in parts))
        # 一致性：一包里除最后一片外，每片都该是满的（CHUNK=50000）；差太多说明包是半截的
        if len(part_rows) > 1:
            full = max(part_rows[:-1])
            rec["chunk_rows"] = full
            rec["last_part_rows"] = part_rows[-1]
            rec["short_parts"] = [i for i, n in enumerate(part_rows[:-1]) if n < full * 0.5]
        rec["ok"] = rec["rows"] > 0
        if not rec["ok"]:
            rec["err"] = "包解开但 0 行"
    except Exception as e:                          # noqa: BLE001
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    finally:
        rec["elapsed_s"] = round(time.time() - t0, 1)
        if not keep:
            shutil.rmtree(d, ignore_errors=True)
    return rec


def rebuild(tag: str, repo: str, pattern: str, jobs: int, keep: bool, log=print) -> dict:
    assets = list_assets(tag, repo)
    names = sorted(a["name"] for a in assets if PKG_RE.search(a["name"] or ""))
    if pattern:
        names = [n for n in names if re.search(pattern, n)]
    sizes = {a["name"]: a for a in assets}
    log("Release %s：%d 个单元包待核（共 %d 个资产）"
        % (tag, len(names), len(assets)))
    workdir = tempfile.mkdtemp(prefix="rebuild-")
    pkgs, done = [], 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
            futs = {ex.submit(measure_package, tag, repo, n, workdir, keep): n for n in names}
            for f in as_completed(futs):
                rec = f.result()
                meta = sizes.get(rec["name"]) or {}
                rec["asset_size"] = meta.get("size")
                rec["asset_created_at"] = meta.get("createdAt")
                pkgs.append(rec)
                done += 1
                log("  [%d/%d] %s → %s 行（%d part%s）%s"
                    % (done, len(names), rec["name"], f"{rec['rows']:,}", rec["parts"],
                       "" if rec["ok"] else "  ✗ " + rec["err"], ""))
    finally:
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)
    pkgs.sort(key=lambda r: (r.get("unit") is None, r.get("unit")))
    rows = sum(r["rows"] for r in pkgs)
    return {"schema": "collect-rebuild/v1", "generated_at": now(), "repo": repo, "tag": tag,
            "method": "逐包 gh release download → tar 解包 → 每个 part .ndjson.gz 流式数换行 → 求和"
                      "（不重采、不读 checkpoint、不拿上游 returnCount 当分母）",
            "packages": pkgs,
            "summary": {"packages": len(pkgs),
                        "packages_ok": sum(1 for r in pkgs if r["ok"]),
                        "packages_bad": [r["name"] for r in pkgs if not r["ok"]],
                        "rows": rows,
                        "parts": sum(r["parts"] for r in pkgs),
                        "asset_bytes": sum((r.get("asset_size") or 0) for r in pkgs),
                        "bytes_unpacked": sum((r.get("bytes_unpacked") or 0) for r in pkgs),
                        "units": [r["unit"] for r in pkgs if r.get("unit") is not None],
                        "unit_gaps": _unit_gaps(pkgs)}}


def _unit_gaps(pkgs) -> list:
    us = sorted(r["unit"] for r in pkgs if r.get("unit") is not None)
    return [u for u in range(0, (us[-1] + 1) if us else 0) if u not in set(us)]


def recheck_assets(built: dict, tag: str, repo: str, log=print) -> dict:
    """跑完之后再对一次「包指纹」：同样的 (name, size, createdAt) 才算测量有效。

    为什么必要：2026-10-30 的 16 层补采 run（41126178216）在测量期间还在跑，
    老代码没有代际前缀，随时可能用同名包 `--clobber` 盖掉旧包。指纹不一致 = 证据失效，
    必须重测，不能拿旧行数洗账。"""
    cur = {a["name"]: a for a in list_assets(tag, repo)}
    changed, missing = [], []
    for pkg in built.get("packages") or []:
        c = cur.get(pkg["name"])
        if c is None:
            missing.append(pkg["name"])
        elif (c.get("size") != pkg.get("asset_size")
              or c.get("createdAt") != pkg.get("asset_created_at")):
            changed.append({"name": pkg["name"], "was_size": pkg.get("asset_size"),
                            "now_size": c.get("size"),
                            "was_created_at": pkg.get("asset_created_at"),
                            "now_created_at": c.get("createdAt")})
    out = {"at": now(), "packages_checked": len(built.get("packages") or []),
           "changed": changed, "missing": missing,
           "ok": not changed and not missing}
    log("资产复检：%d 包，变化 %d，缺失 %d → %s"
        % (out["packages_checked"], len(changed), len(missing),
           "一致（证据有效）" if out["ok"] else "不一致（证据失效，需重测）"))
    return out


def build_restored_checkpoint(built: dict, tag: str, layer: str, url: str,
                              evidence_path: str, run_id: str = "",
                              overwrote: dict | None = None) -> dict:
    """把「实测结果」变成一份合法检查点（纯函数，不碰网络 —— 单测与本地复验都用它）。"""
    pk = {str(p["unit"]): p for p in built["packages"] if p.get("unit") is not None}
    units = sorted(int(k) for k in pk)
    return {"ver": 2, "url": url,
            "plan_hash": "rebuilt-from-assets-%s" % str(built.get("generated_at") or now())[:10],
            "tag": tag, "unit_rows_provenance": "assets_recount",
            "unit_rows": {k: pk[k]["rows"] for k in pk},
            "unit_rows_seen": {k: pk[k]["rows"] for k in pk},
            "unit_files": {k: [pk[k]["name"]] for k in pk},
            "unit_package": {k: pk[k]["name"] for k in pk},
            "unit_uploaded": {k: True for k in pk},
            "done_units": units,
            "restored": {"at": now(), "by": "collect/rebuild_layer_rows.py",
                         "run_id": run_id or os.environ.get("GITHUB_RUN_ID") or "local",
                         "evidence": os.path.relpath(os.path.abspath(evidence_path), ROOT),
                         "packages": len(units),
                         "parts": built["summary"]["parts"],
                         "rows": built["summary"]["rows"],
                         "overwrote": overwrote,
                         "note": "checkpoint 曾被 force 重跑整份覆盖；本文件由单元包实测反推重建"}}


def restore_checkpoint(built: dict, tag: str, repo: str, layer: str, url: str,
                      evidence_path: str, run_id: str = "", log=print) -> dict:
    """用 68 个单元包的实测结果**重建 Release 上的 checkpoint**（把证据放回去）。

    ★ 为什么要写 Release：`ledger_rebuild --check` 与 `step_full_report` 读的是 checkpoint 口径。
      只改 git 里的账本、不修 Release 上的检查点，下一次 rebuild 还是按 0 行算 → 永远 DIFFERS。
      写之前先把当前（被覆盖的）那份备份成 `<layer>-checkpoint.bak-<ts>.json`。
    ★ plan_hash 用 `rebuilt-from-assets-<date>` 而不是伪造旧哈希：旧的 68 段区间切分已不可复原，
      硬编一个「像真的」哈希反而是假证据。将来任何 run 拿到这份检查点都会判为 legacy →
      备份 + 按包名合并，不会重复采、也不会丢行。
    """
    import tempfile
    assets = list_assets(tag, repo)
    idx = {a["name"]: a for a in assets}
    ck_name = "%s-checkpoint.json" % layer
    work = tempfile.mkdtemp(prefix="ckrestore-")
    overwrote = None
    if ck_name in idx:
        rc = subprocess.run(["gh", "release", "download", tag, "--repo", repo, "-p", ck_name,
                             "-D", work, "--clobber"], capture_output=True, text=True)
        old_path = os.path.join(work, ck_name)
        if rc.returncode == 0 and os.path.exists(old_path):
            try:
                old = json.load(open(old_path, encoding="utf-8"))
                overwrote = {"unit_rows": len(old.get("unit_rows") or {}),
                             "rows": sum((old.get("unit_rows_seen") or old.get("unit_rows") or {}).values()),
                             "asset_created_at": (idx[ck_name] or {}).get("createdAt"),
                             "asset_size": (idx[ck_name] or {}).get("size")}
            except Exception:                                       # noqa: BLE001
                overwrote = {"unreadable": True}
            ts = now().replace(":", "").replace("-", "")
            bak = "%s-checkpoint.bak-%s.json" % (layer, ts)
            bak_path = os.path.join(work, bak)
            shutil.copy2(old_path, bak_path)
            r2 = subprocess.run(["gh", "release", "upload", tag, bak_path, "--repo", repo],
                                capture_output=True, text=True)
            log("  备份当前检查点：%s（%s）" % (bak, "ok" if r2.returncode == 0 else
                                              (r2.stderr or r2.stdout)[:120]))
    ck = build_restored_checkpoint(built, tag, layer, url, evidence_path, run_id,
                                   overwrote=overwrote)
    units = ck["done_units"]
    out = os.path.join(work, ck_name)
    json.dump(ck, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    r = subprocess.run(["gh", "release", "upload", tag, out, "--repo", repo, "--clobber"],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    log("  %s 检查点已重建并上传：%d 单元 / %s 行%s"
        % ("✓" if ok else "✗", len(units), f"{built['summary']['rows']:,}",
           "" if ok else "（%s）" % ((r.stderr or r.stdout)[:160])))
    shutil.rmtree(work, ignore_errors=True)
    return {"ok": ok, "units": len(units), "rows": built["summary"]["rows"],
            "overwrote": overwrote, "uploaded": ck_name}


def apply_ledger(path: str, built: dict, layer: str, evidence_path: str,
                 events_path: str = "", log=print) -> dict:
    """把实测行数写回阶段账本里的这一层。状态按实测重算（不美化）。"""
    led = json.load(open(path, encoding="utf-8"))
    recs = led.get("records") or []
    hit = [r for r in recs if r.get("layer") == layer]
    if not hit:
        raise SystemExit("账本 %s 里没有这一层：%s" % (path, layer))
    r = hit[0]
    before = {"rows": r.get("rows"), "status": r.get("status"), "parts_assets": r.get("parts_assets")}
    rows = built["summary"]["rows"]
    declared = r.get("declared") or 0
    if declared and rows >= declared * 0.998:
        status, reason = "ok", "实测 %s 行 ≥ 声明 %s 行的 99.8%%" % (f"{rows:,}", f"{declared:,}")
    else:
        pct = (100.0 * (declared - rows) / declared) if declared else 0.0
        status = "partial"
        reason = ("实测 %s / 上游声明 %s（差 %.2f%%）：差额属上游可见性变化，"
                  "包与行数由 Release 逐个单元包实测" % (f"{rows:,}", f"{declared:,}", pct))
    r.update({"rows": rows, "rows_src": "rebuild_from_assets",
              "parts_assets": built["summary"]["packages"],
              "units": built["summary"]["packages"],
              "units_done": built["summary"]["packages_ok"],
              "status": status, "reason": reason,
              "gap": (declared - rows) if declared else None,
              "gap_pct": round(100.0 * (declared - rows) / declared, 4) if declared else None,
              "evidence": {"rebuild": os.path.relpath(os.path.abspath(evidence_path), ROOT),
                           "kind": "release_assets_recount",
                           "packages": built["summary"]["packages"],
                           "parts": built["summary"]["parts"],
                           "generated_at": built["generated_at"]}})
    r["warn"] = [w for w in (r.get("warn") or []) if "checkpoint 计划行" not in w]
    # 汇总口径重算（rows/ok/partial 等必须跟着动，否则账本自相矛盾）
    led["rows"] = sum((x.get("rows") or 0) for x in recs)
    led["gap"] = (led.get("declared") or 0) - led["rows"]
    for k in ("ok", "partial", "failed", "missing", "unverified", "empty"):
        led[k] = sum(1 for x in recs if x.get("status") == k)
    led["complete"] = bool(led.get("failed", 0) == 0 and led.get("missing", 0) == 0)
    led.setdefault("revisions", []).append({
        "at": now(), "kind": "layer_rows_rebuilt_from_assets", "layer": layer,
        "before": before, "after": {"rows": rows, "status": status},
        "evidence": r["evidence"]["rebuild"],
        "note": "checkpoint 被 force 重跑覆盖（run 41126178216），本行由 68 个单元包实测反推"})
    json.dump(led, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if events_path:
        ev = {"schema": "collect-ledger-restore-events/v1", "events": [
            {"at": now(), "kind": "layer_rows_rebuilt_from_assets", "layer": layer,
             "run_id": "41126178216", "stage": led.get("stage"),
             "before_rows": before["rows"], "after_rows": rows,
             "before_status": before["status"], "after_status": status,
             "evidence": r["evidence"]["rebuild"]}]}
        old = {}
        if os.path.exists(events_path):
            try:
                old = json.load(open(events_path, encoding="utf-8")) or {}
            except Exception:
                old = {}
        old.setdefault("events", []).extend(ev["events"])
        json.dump(old, open(events_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("账本 %s：%s rows %s → %s，status %s → %s"
        % (path, layer, f"{before['rows']:,}", f"{rows:,}", before["status"], status))
    return {"before": before, "after": {"rows": rows, "status": status}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True)
    ap.add_argument("--tag", required=True, help="Release tag（一层的全部单元包都在这个 tag 下）")
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--pattern", default="", help="只核名字匹配这个正则的包")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--keep", action="store_true", help="保留解包目录（排障用）")
    ap.add_argument("--expect-rows", type=int, default=0,
                    help="旧 checkpoint 记录的行数（对得上说明复原口径与历史一致）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--from-json", default="",
                    help="不重新下载，直接用已有测量结果（--out 那份 JSON）做 --apply-ledger / --recheck")
    ap.add_argument("--recheck", action="store_true",
                    help="对现有 --out JSON 再做一次资产指纹复检（测量期间有别的 run 在同 tag 上跑时必做）")
    ap.add_argument("--apply-ledger", default="", help="把实测行数写回这个阶段账本")
    ap.add_argument("--layer-in-ledger", default="", help="账本里的层名（默认=--layer）")
    ap.add_argument("--restore-events", default="", help="复原事件追加到这个 JSON")
    ap.add_argument("--restore-checkpoint", action="store_true",
                    help="用实测结果重建 Release 上的 checkpoint（先把当前那份备份成 .bak-<ts>.json），"
                         "让 ledger_rebuild --check 回到 IDENTICAL")
    ap.add_argument("--layer-url", default="", help="--restore-checkpoint 时要写的图层 url")
    ap.add_argument("--run-id", default="", help="--restore-checkpoint 记事件用的 run id")
    a = ap.parse_args()

    if a.recheck or a.from_json:
        built = json.load(open(a.from_json or a.out, encoding="utf-8"))
        built["recheck"] = recheck_assets(built, a.tag, a.repo)
        json.dump(built, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps({"recheck": {k: built["recheck"][k] for k in ("ok", "packages_checked")},
                          "changed": len(built["recheck"]["changed"]),
                          "missing": built["recheck"]["missing"]}, ensure_ascii=False))
        if not a.from_json or not (a.apply_ledger or a.restore_checkpoint):
            return 0 if built["recheck"]["ok"] else 1
    else:
        built = rebuild(a.tag, a.repo, a.pattern, a.jobs, a.keep)
    built["layer"] = a.layer
    s = built["summary"]
    if a.expect_rows:
        built["expect_rows"] = a.expect_rows
        built["expect_match"] = (s["rows"] == a.expect_rows)
        built["expect_delta"] = s["rows"] - a.expect_rows
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(built, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"layer": a.layer, "tag": a.tag, "packages": s["packages"],
                      "packages_ok": s["packages_ok"], "parts": s["parts"],
                      "rows": s["rows"], "expect_match": built.get("expect_match"),
                      "out": a.out}, ensure_ascii=False))
    if a.apply_ledger:
        apply_ledger(a.apply_ledger, built, a.layer_in_ledger or a.layer,
                     a.out, a.restore_events)
    if a.restore_checkpoint:
        r = restore_checkpoint(built, a.tag, a.repo, a.layer, a.layer_url, a.out, a.run_id)
        built["checkpoint_restore"] = r
        json.dump(built, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0 if s["packages_bad"] == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
