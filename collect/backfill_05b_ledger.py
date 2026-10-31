#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05b 阶段账本补账：把「数据在 Release、账本没行」的层按 **资产证据** 补回来。

事故形状（W33-013 的尾巴，2026-10-31 用户拍板必须补）：
  run `41123309047` 的 shard 3/8/11/13 被 350 分钟 cap 掐成 `cancelled`，片账本随
  job 一起消失；但那 4 片里**跑完的 445 层** checkpoint 完整、Release 资产齐全，
  `done_layers('05')` 判完成 445/445。结果阶段账本 `layers_n=2325`，而阶段计划是
  **2770** —— 数据全在，账本说没有，覆盖率被系统性低估 19.3%。

口径（与 `ledger_rebuild.py` 的 05b 判定完全一致，不另写一套）：
  · declared：`layer_plan.csv` 经 `worker_core._rows_from_csv/_norm_plan_row` 唯一化后的
    `expect`（与采集器同源，避免 `@STATE-n` 层被算成 0）；
  · rows：checkpoint 的 `unit_rows_seen`（老 checkpoint 无此字段才退回 `unit_rows`）；
  · status：复用 `ledger_rebuild.judge()` —— ok / empty / partial / failed；
  · **只补可证的**：`judge()` 判 `failed`（缺资产 / 单元未传 / 残留错误 / tag 不符）
    的层**不写账**，进 `skipped[]` 并写明原因；绝不猜行数。

逐层落账字段（用户 2026-10-31 指定）：
  `backfilled_from: "release_assets"`、`reason: "ledger_row_lost_on_cancel"`，
  另附 `units_done` / `packages`（unit 包名清单）/ `evidence`（Release tag、checkpoint
  资产名与 sha256、unit 包名与字节、上传时间）。

幂等：`--check` 重算后与账本 + 证据文件逐字节比对，必须 `IDENTICAL`。
时间戳取「445 层里最晚的资产上传时间」，不取 `now()`，所以同一输入 → 同一输出。

用法：
  python3 collect/backfill_05b_ledger.py --plan <2770 层阶段计划> \
      --evidence analysis/05b-backfill-2026-10-31.json
  python3 collect/backfill_05b_ledger.py --plan <...> --check
  python3 collect/backfill_05b_ledger.py --plan <...> --dry-run   # 只打印将补哪些层
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ledger_rebuild as lr                                     # noqa: E402
from ledger_merge import recount                                # noqa: E402
from worker_core import _rows_from_csv, _norm_plan_row          # noqa: E402

SCHEMA = "collect-stage-ledger-backfill/v1"
STAGE = "05b"
PREFIX = "collect-step05-"
LOST_RUN = "41123309047"
LOST_SHARDS = [3, 8, 11, 13]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jload(path):
    return json.load(open(path, encoding="utf-8"))


def canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1)


def plan_layers(plan_path: str) -> list:
    d = jload(plan_path)
    out = []
    for s in d.get("shards") or []:
        out += list(s.get("layers") or [])
    return out


def plan_row_index() -> dict:
    """layer_id → 计划行（declared 与 svc 同源；唯一化规则与采集器一致）。"""
    idx = {}
    for raw in _rows_from_csv():
        r = _norm_plan_row(raw)
        lid = r.get("id")
        if lid:
            idx[lid] = r
    return idx


def checkpoint_sha(ck: dict) -> str:
    return hashlib.sha256(json.dumps(ck, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def judge_backfill(layer: str, declared, rel: dict, ck: dict) -> dict:
    """`ledger_rebuild.judge()` 的 05b 补账口径 —— 只补一个零行单元的边界。

    judge() 把「unit 1 未上传 / 无 -u00001.tar.gz」一律记 failed。实测
    `UojyNPhsWOk1W_..._FeatureServer_1`：unit 1 计划 0 行、实采 0 行、无 part 文件，
    `unit_uploaded=false` 是**正常**的（没有东西可传），而另外两个单元把 250,208 行
    全部传完。若照 judge 判 failed，这一层会永远补不回账 —— 所以只在「出问题的
    单元全部是零行单元」时豁免，其余问题一条不放。
    """
    j = lr.judge(layer, declared, rel, ck, "")
    if j["status"] != "failed":
        return j
    ur = {int(k): int(v or 0) for k, v in (ck.get("unit_rows") or {}).items()}
    seen = {int(k): int(v or 0) for k, v in (ck.get("unit_rows_seen") or {}).items()}         if isinstance(ck.get("unit_rows_seen"), dict) else {}
    files = {int(k): len(v or []) for k, v in (ck.get("unit_files") or {}).items()}
    up = {int(k): bool(v) for k, v in (ck.get("unit_uploaded") or {}).items()}
    zero = {i for i in ur if ur[i] == 0 and seen.get(i, 0) == 0
            and not files.get(i) and not up.get(i)}
    if not zero:
        return j
    remains = []
    for p in j.get("problems") or []:
        m = re.match(r"unit (\d+) ", p)
        if m and int(m.group(1)) in zero:
            continue
        remains.append(p)
    if remains:
        return j
    j["status"] = "ok"
    j["reason"] = ("零行单元 %s 无包可传（unit_rows=unit_rows_seen=0），"
                   "其余单元全部上传完毕" % ",".join(str(i) for i in sorted(zero)))
    j.setdefault("warn", []).append("零行单元 %s 豁免「未上传」判据（没有数据可传）"
                                    % ",".join(str(i) for i in sorted(zero)))
    return j


def build_record(layer: str, declared, svc: str, rel: dict, ck: dict) -> dict:
    """把 judge() 的结论落成阶段账本行（字段与 shard 账本保持兼容）。"""
    j = judge_backfill(layer, declared, rel, ck)
    if j["status"] == "failed":
        return {"layer": layer, "judge": j}

    unit_names = sorted(a["name"] for a in (rel.get("assets") or [])
                        if lr.UNIT_RE.search(a["name"]))
    ck_asset = next((a for a in (rel.get("assets") or [])
                     if a["name"].endswith("-checkpoint.json")), None)
    gap = int(declared or 0) - int(j["rows"] or 0)
    rec = {
        "layer": layer,
        "rc": 0 if j["status"] in ("ok", "empty") else 1,
        "elapsed_s": None,
        "at": j.get("last_upload"),
        "declared": declared,
        "rows": j.get("rows"),
        "err": "",
        "diff": round(abs(gap) / declared, 4) if declared else 0.0,
        "parts": j.get("units_done"),
        "svc": svc,
        "status": j["status"],
        # 用户指定的固定语义：这一行是「cancel 时丢的账」，不是重采结果
        "reason": "ledger_row_lost_on_cancel",
        "judge_reason": j.get("reason") or "",
        "backfilled_from": "release_assets",
        "backfilled_at": None,          # 由调用方统一填「最晚上传时间」
        "units": j.get("units"),
        "units_done": j.get("units_done"),
        "packages": unit_names,
        "packages_n": len(unit_names),
        "evidence": {
            "release_tag": rel["tag"],
            "release_created_at": rel.get("created_at"),
            "checkpoint_asset": (ck_asset or {}).get("name"),
            "checkpoint_bytes": (ck_asset or {}).get("size"),
            "checkpoint_sha256": checkpoint_sha(ck),
            "unit_assets": unit_names,
            "unit_assets_n": len(unit_names),
            "assets_bytes": j.get("bytes"),
            "first_upload": j.get("first_upload"),
            "last_upload": j.get("last_upload"),
            "plan_hash": ck.get("plan_hash"),
            "url": ck.get("url"),
        },
    }
    return {"layer": layer, "judge": j, "record": rec}


def fetch_all(missing: list, repo: str, workers: int = 6) -> tuple[dict, dict, list]:
    releases = lr.list_releases(repo, PREFIX, max_pages=80)
    cache = os.path.join(HERE, "ledger", ".ckpt_cache")
    rows_idx = plan_row_index()

    def one(layer):
        rel = releases.get(PREFIX + layer)
        if rel is None:
            return {"layer": layer, "error": "no_release_asset"}
        ck_asset = next((a for a in (rel.get("assets") or [])
                         if a["name"].endswith("-checkpoint.json")), None)
        if ck_asset is None:
            return {"layer": layer, "error": "no_checkpoint_asset"}
        try:
            ck = lr.fetch_checkpoint(repo, rel["tag"], ck_asset, cache, False)
        except Exception as e:                                   # noqa: BLE001
            return {"layer": layer, "error": "checkpoint_fetch_failed: %s" % str(e)[:160]}
        p = rows_idx.get(layer) or {}
        return build_record(layer, p.get("expect"), p.get("svc") or "FeatureServer", rel, ck)

    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, missing):
            out.append(r)
    out.sort(key=lambda x: x["layer"])
    return releases, {r["layer"]: r for r in out}, out


def summarize(records: list) -> dict:
    cnt = recount(records)
    return {k: cnt[k] for k in ("layers_n", "declared", "rows", "gap", "gap_pct",
                                "ok", "empty", "partial", "failed", "upstream_unstable",
                                "missing", "unverified", "capped_by_upstream")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=STAGE)
    ap.add_argument("--ledger", default=os.path.join(ROOT, "collect", "05b_ledger.json"))
    ap.add_argument("--plan", required=True, help="阶段计划（2770 层）")
    ap.add_argument("--evidence", default=os.path.join(
        ROOT, "analysis", "05b-backfill-2026-10-31.json"))
    ap.add_argument("--repo", default=lr.repo_default())
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="重算并与账本/证据比对（同输入必须 IDENTICAL）")
    a = ap.parse_args()
    if a.stage != STAGE:
        raise SystemExit("::error::本脚本只处理 05b（阶段账本口径已按 05b 固定）")

    led = jload(a.ledger)
    ids = plan_layers(a.plan)
    have = {str(r.get("layer")) for r in (led.get("records") or [])}
    missing = [x for x in ids if x not in have]
    # --check 时账本已经补过了（missing=[]），要拿证据文件里的层清单重算一遍，
    # 不能因为「不缺层」就直接退 0 —— 那样 --check 永远绿，等于没检。
    check_layers = []
    if a.check and os.path.exists(a.evidence):
        check_layers = [x["layer"] for x in (jload(a.evidence).get("layers") or [])]
    candidates = missing or (check_layers if a.check else [])
    if not candidates:
        print("✅ 账本已覆盖计划全部 %d 层，无需补账" % len(ids))
        return 0

    releases, got, results = fetch_all(candidates, a.repo, a.workers)
    ok = [r for r in results if r.get("record")]
    skipped = [r for r in results if not r.get("record")]
    stamped = max((r["record"]["evidence"]["last_upload"] or "" for r in ok), default="")
    at = stamped or utcnow()
    for r in ok:
        r["record"]["backfilled_at"] = at

    new_recs = [r["record"] for r in ok]
    before = summarize(led.get("records") or [])
    merged_map = {str(r.get("layer")): r for r in (led.get("records") or [])}
    for r in new_recs:
        merged_map[str(r.get("layer"))] = r
    merged = sorted(merged_map.values(), key=lambda r: str(r.get("layer")))
    cnt = recount(merged)
    after = summarize(merged)

    buckets = {k: cnt[k] for k in ("ok", "capped_by_upstream", "partial", "upstream_unstable",
                                   "missing", "unverified", "empty", "failed")}
    bad = [r for r in merged
           if str(r.get("status") or "").lower() not in ("ok", "empty", "skipped_done")]
    complete = bool(merged) and not bad and cnt["failed"] == 0

    # 四类归因只在原 31 层上，不因为补账而改类目；对账差额单独给数
    cls_of = {r["layer"]: {"class": r["gap_class"]} for r in merged if r.get("gap_class")}
    gap_by_class = {}
    if cls_of:
        import adjudicate_05b as adj
        gap_by_class = adj.gap_by_class(merged, cls_of)
    class_sum = sum(v["gap"] for v in gap_by_class.values())
    over = sum(max(0, int(r.get("rows") or 0) - int(r.get("declared") or 0)) for r in merged)
    delta = max(0, cnt["gap"]) - class_sum

    evidence = {
        "schema": SCHEMA,
        "stage": STAGE,
        "at": at,
        "generated_by": "backfill_05b_ledger.py",
        "reason": "ledger_row_lost_on_cancel",
        "backfilled_from": "release_assets",
        "source": {
            "repo": a.repo,
            "release_prefix": PREFIX,
            "plan": os.path.relpath(a.plan, ROOT),
            "plan_layers_n": len(ids),
            "ledger": os.path.relpath(a.ledger, ROOT),
            "lost_run_id": LOST_RUN,
            "lost_shards": LOST_SHARDS,
        },
        "summary": {
            "candidates_n": len(candidates),
            "backfilled_n": len(ok),
            "skipped_n": len(skipped),
            "by_status": {s: sum(1 for r in ok if r["record"]["status"] == s)
                          for s in ("ok", "empty", "partial", "failed")},
            "declared": sum(int(r["record"].get("declared") or 0) for r in ok),
            "rows": sum(int(r["record"].get("rows") or 0) for r in ok),
            "gap": sum(max(0, int(r["record"].get("declared") or 0)
                           - int(r["record"].get("rows") or 0)) for r in ok),
            "layers_n_before": before["layers_n"],
            "layers_n_after": after["layers_n"],
            "before": before,
            "after": after,
            "gap_by_class_sum": class_sum,
            "over_collected_rows": over,
            "gap_by_class_delta": delta,
        },
        "layers": [{
            "layer": r["record"]["layer"], "status": r["record"]["status"],
            "declared": r["record"]["declared"], "rows": r["record"]["rows"],
            "units_done": r["record"]["units_done"], "packages": r["record"]["packages"],
            "evidence": r["record"]["evidence"],
        } for r in ok],
        "skipped": skipped,
    }

    new_led = dict(led)
    new_led.update({
        "schema": led.get("schema") or "collect-ledger-agg/v1",
        "stage": STAGE,
        "at": at,
        "scope": "stage",
        "layers_n": cnt["layers_n"],
        "declared": cnt["declared"],
        "rows": cnt["rows"],
        "gap": cnt["gap"],
        "gap_pct": cnt["gap_pct"],
        "records": merged,
        "complete": complete,
        "buckets": buckets,
        "gap_by_class": gap_by_class or led.get("gap_by_class"),
    })
    for k, v in buckets.items():
        new_led[k] = v
    revs = list(led.get("revisions") or [])
    revs = [r for r in revs if r.get("kind") != "stage_ledger_backfilled"]
    revs.append({
        "kind": "stage_ledger_backfilled",
        "at": at,
        "layers": len(ok),
        "skipped": len(skipped),
        "source": "release_assets",
        "reason": "ledger_row_lost_on_cancel",
        "lost_run_id": LOST_RUN,
        "lost_shards": LOST_SHARDS,
        "evidence": os.path.relpath(a.evidence, ROOT),
        "layers_n_before": before["layers_n"],
        "layers_n_after": after["layers_n"],
        "note": ("cancel 片账本随 job 丢失（W33-013 尾巴）：按 Release checkpoint 逐层"
                 "补回，状态与行数用 ledger_rebuild.judge 的同一套判据"),
    })
    new_led["revisions"] = revs

    if a.dry_run:
        print(json.dumps({"missing_n": len(missing), "backfill_n": len(ok),
                          "skipped": skipped, "before": before, "after": after,
                          "revisions": revs[-1]},
                         ensure_ascii=False, indent=1))
        return 0

    if a.check:
        # --check 只比「补账」这一层语义：逐层 backfill 字段 + 证据文件，不比后续
        # adjudicate 追加的 gap_class/status_before_*，也不比由全账重算的 gap_by_class
        # （那些会随正常收口变化，混进来就会把 check 做成假红）。
        cur_ev = jload(a.evidence) if os.path.exists(a.evidence) else None
        if cur_ev is None:
            print("::error::DIFFERS：证据文件不存在（%s）" % a.evidence, file=sys.stderr)
            return 1
        bads = []
        by_layer = {str(r.get("layer")): r for r in (led.get("records") or [])}
        recomputed = {r["layer"]: r["record"] for r in ok if r.get("record")}
        fields = ("status", "declared", "rows", "units_done", "packages", "evidence")
        for x in cur_ev.get("layers") or []:
            lid = x.get("layer")
            rec = by_layer.get(lid)
            rr = recomputed.get(lid)
            if rec is None:
                bads.append("%s 不在账本里" % lid)
                continue
            if rr is None:
                bads.append("%s 重算不出证据（Release 变了？）" % lid)
            for k in fields:
                if (rec.get(k) if k != "evidence" else rec.get("evidence")) != x.get(k):
                    bads.append("%s 的 %s 与证据不符" % (lid, k))
                if rr is not None and (rr.get(k) if k != "evidence" else rr.get("evidence")) != x.get(k):
                    bads.append("%s 的 %s 与重算不符" % (lid, k))
            if rec.get("backfilled_from") != "release_assets":
                bads.append("%s 缺 backfilled_from" % lid)
            if rec.get("reason") != "ledger_row_lost_on_cancel":
                bads.append("%s 的 reason 不是 ledger_row_lost_on_cancel" % lid)
        if int(led.get("layers_n") or 0) != len(ids):
            bads.append("账本 layers_n=%s 与计划 %d 层不符" % (led.get("layers_n"), len(ids)))
        if len(cur_ev.get("layers") or []) != int((cur_ev.get("summary") or {}).get("backfilled_n") or -1):
            bads.append("证据文件 layers 数与 summary.backfilled_n 不符")
        if bads:
            print("::error::DIFFERS（%d 处）：%s" % (len(bads), "；".join(bads[:6])), file=sys.stderr)
            return 1
        print("IDENTICAL：账本 %d 层 / 计划 %d 层；补账 %d 层（逐层 rows/units/packages/evidence）"
              " 与证据文件和 Release 重算一致"
              % (led.get("layers_n"), len(ids), len(cur_ev.get("layers") or [])))
        return 0

    os.makedirs(os.path.dirname(a.evidence) or ".", exist_ok=True)
    json.dump(evidence, open(a.evidence, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(new_led, open(a.ledger, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({
        "candidates_n": len(candidates), "backfilled_n": len(ok), "skipped_n": len(skipped),
        "by_status": evidence["summary"]["by_status"],
        "layers_n": cnt["layers_n"], "declared": cnt["declared"], "rows": cnt["rows"],
        "gap": cnt["gap"], "gap_pct": cnt["gap_pct"],
        "buckets": buckets, "complete": complete,
        "gap_by_class_delta": delta,
    }, ensure_ascii=False, indent=1))
    print("✅ 写盘：%s / %s" % (os.path.relpath(a.ledger, ROOT),
                                os.path.relpath(a.evidence, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
