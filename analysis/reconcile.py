#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量对账：挑 3 个层，把 payload 全下下来逐行数，验证
  ① 层内行数 == rows_with_number + rows_without_number（账本必须闭合）
  ② 抽样外推（INTAKE-YIELD 用的比例）与全量真值的偏差有多大
只读 GitHub Release，不访问上游。输出 docs/INTAKE-YIELD-RECONCILE.md。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import profile as P                                    # noqa: E402


def full_scan(tag: str, number_field: str | None) -> dict:
    assets = json.loads(subprocess.run(
        ["gh", "release", "view", tag, "--repo", P.REPO, "--json", "assets",
         "-q", "[.assets[]|select(.name|endswith(\"tar.gz\"))|{n:.name,u:.url}]"],
        capture_output=True, text=True, timeout=300).stdout or "[]")
    d = "/tmp/reconcile-" + re.sub(r"[^A-Za-z0-9]", "", tag)[-12:]
    os.makedirs(d, exist_ok=True)
    tot = wn = 0
    fields_seen = {}
    for a in sorted(assets, key=lambda x: x["n"]):
        p = P.gh_dl(tag, a["n"], d)
        if not p:
            continue
        with tarfile.open(p, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.name.endswith(".ndjson.gz"):
                    continue
                fh = tf.extractfile(m)
                with gzip.GzipFile(fileobj=fh) as gz:
                    for ln in gz:
                        ln = ln.strip()
                        if not ln:
                            continue
                        tot += 1
                        if not number_field:
                            continue
                        try:
                            rec = json.loads(ln)
                        except Exception:  # noqa: BLE001
                            continue
                        raw = rec.get("raw") or {}
                        for k in raw:
                            fields_seen[k] = 1
                        v = raw.get(number_field)
                        if v is None and rec.get("add_num"):
                            v = rec.get("add_num")
                        if v not in (None, "") and P.classify(v) in ("pure_num", "num_suffix"):
                            wn += 1
        os.unlink(p)
    for f in os.listdir(d):
        os.unlink(os.path.join(d, f))
    os.rmdir(d)
    return {"rows_total": tot, "rows_with_number": wn, "rows_without_number": tot - wn,
            "number_field": number_field}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", default="", help="逗号分隔的 tag，留空=自动挑 3 个（小/中/大）")
    a = ap.parse_args()
    fmap = json.load(open(os.path.join(ROOT, "schema", "field-map-v1.json"), encoding="utf-8"))
    yld = json.load(open(os.path.join(HERE, "yield_per_layer.json"), encoding="utf-8"))
    prof = {}
    for f in os.listdir(os.path.join(HERE, "out")):
        d = json.load(open(os.path.join(HERE, "out", f), encoding="utf-8"))
        prof[d["layer_id"]] = d

    if a.pick:
        tags = [x.strip() for x in a.pick.split(",") if x.strip()]
    else:
        # 小 / 中 / 大 各一个（都是 step 前缀可反查的层）
        cand = sorted(((yld.get(l) or {}).get("rows_total") or 0, l) for l in yld)
        cand = [c for c in cand if c[0] > 0]
        tags = []
        for idx in (len(cand) // 10, len(cand) // 2, len(cand) - 3):
            if 0 <= idx < len(cand):
                lid = cand[idx][1]
                tags.append(prof.get(lid, {}).get("tag") or lid)

    rows = []
    for tag in tags:
        lid = re.sub(r"^collect-step\d+-", "", tag)
        nf = (fmap["layers"].get(lid) or {}).get("number")
        r = full_scan(tag, nf)
        r["tag"] = tag
        r["layer_id"] = lid
        est = (yld.get(lid) or {})
        r["estimated_with_number"] = est.get("rows_with_number")
        r["estimate_err_pct"] = (round(100.0 * (r["rows_with_number"] - (est.get("rows_with_number") or 0))
                                       / max(1, r["rows_with_number"]), 2)
                                 if est else None)
        r["closed"] = (r["rows_total"] == r["rows_with_number"] + r["rows_without_number"])
        rows.append(r)
        print(json.dumps(r, ensure_ascii=False), flush=True)

    L = ["# 全量对账（3 层逐行数）", "",
         "口径：把每层 payload 全下下来逐行解析，数「总行数」与「门牌号可解析行」，"
         "验证 `rows_total == rows_with_number + rows_without_number` 闭合，并对比 INTAKE-YIELD 的抽样外推误差。", "",
         "| 层 | 门牌字段 | rows_total | with_number | without_number | 闭合 | 抽样估计 | 估计误差 |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| `%s` | `%s` | %s | %s | %s | %s | %s | %s |"
                 % (r["layer_id"][:40], r.get("number_field"), f"{r['rows_total']:,}",
                    f"{r['rows_with_number']:,}", f"{r['rows_without_number']:,}",
                    "✅" if r["closed"] else "❌",
                    f"{r['estimated_with_number']:,}" if r.get("estimated_with_number") is not None else "-",
                    ("%+.2f%%" % r["estimate_err_pct"]) if r.get("estimate_err_pct") is not None else "-"))
    ok = all(r["closed"] for r in rows)
    L += ["", f"**闭合校验：{'全部通过' if ok else '有不闭合项'}**（{sum(1 for r in rows if r['closed'])}/{len(rows)}）", ""]
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    open(os.path.join(ROOT, "docs", "INTAKE-YIELD-RECONCILE.md"), "w", encoding="utf-8").write("\n".join(L))
    print("closed_all=%s" % ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
