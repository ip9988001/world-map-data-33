#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宗地层：situs address vs mailing address 两套字段是否共存、冲突率多少。

只读 Release 资产（GitHub），不碰上游。每层取前 N 行（range 抽样，~3MB/层），
逐行比较「房产地址」与「业主/邮寄地址」两套字段，统计：
  · both_layers：该层同时存在 situs 字段与 mailing 字段
  · rows_both：两套都有值的行数
  · rows_conflict：两套都有值且字符串不同（含门牌或街名不同）
  · rows_situs_only / rows_mail_only
输出 analysis/parcel_conflict.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import profile as P                                     # noqa: E402

SITUS_RX = re.compile(r"(situs|site_?addr|prop_?addr|property_?addr|parcel_?addr|phys(ical)?_?addr)", re.I)
MAIL_RX = re.compile(r"(owner|mail|taxpayer|payer|billing|bill_?addr|send_?to)", re.I)


def norm(s: str) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())
    return re.sub(r"\s+", " ", s).strip()


def pick(fields, rx, second_rx=None):
    """在一层里挑出「整条地址」用的一组字段（优先含 addr/full 的组合字段）。"""
    cands = [f for f in fields if rx.search(f)]
    if not cands:
        return []
    def score(f):
        s = 0
        if re.search(r"(full|complete|all|concatenat)", f, re.I):
            s += 3
        if re.search(r"(addr|address)", f, re.I):
            s += 2
        return s
    return sorted(cands, key=score, reverse=True)


def layer_conflict(fields: dict, rows: list[dict]) -> dict:
    sf = pick(fields, SITUS_RX)
    mf = pick(fields, MAIL_RX)
    out = {"situs_fields": sf[:4], "mail_fields": mf[:4],
           "both_layers": bool(sf and mf), "rows": len(rows),
           "rows_both": 0, "rows_conflict": 0, "rows_situs_only": 0, "rows_mail_only": 0}

    def val(rec, names):
        parts = []
        for n in names:
            v = (rec.get("raw") or {}).get(n)
            if v not in (None, "") and str(v).strip().upper() not in ("N/A", "NULL", "NONE"):
                parts.append(str(v))
        return " ".join(parts).strip()

    for rec in rows:
        sv, mv = val(rec, sf), val(rec, mf)
        if sv and mv:
            out["rows_both"] += 1
            if norm(sv) != norm(mv):
                out["rows_conflict"] += 1
        elif sv:
            out["rows_situs_only"] += 1
        elif mv:
            out["rows_mail_only"] += 1
    return out


def grab_rows(url: str, max_rows: int) -> list[dict]:
    rows = []
    for ln in P.partial_targz_rows(url, 4 << 20, max_rows):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags-file", required=True)
    ap.add_argument("--sample", type=int, default=800)
    ap.add_argument("--out", default=os.path.join(HERE, "parcel_conflict.json"))
    a = ap.parse_args()
    tags = [x.strip() for x in open(a.tags_file) if x.strip()]
    res = []
    for i, tag in enumerate(tags, 1):
        try:
            raw = json.loads(subprocess.run(
                ["gh", "release", "view", tag, "--repo", P.REPO, "--json", "assets",
                 "-q", "[.assets[]|select(.name|endswith(\"tar.gz\"))|{n:.name,u:.url}]"],
                capture_output=True, text=True, timeout=300).stdout or "[]")
            if not raw:
                continue
            rows = grab_rows(sorted(raw, key=lambda x: x["n"])[0]["u"], a.sample)
            fields = {}
            for r in rows:
                for k in (r.get("raw") or {}):
                    fields[k] = 1
            d = layer_conflict(fields, rows)
            d.update({"layer_id": re.sub(r"^collect-step\d+-", "", tag), "tag": tag})
            res.append(d)
        except Exception as e:  # noqa: BLE001
            res.append({"layer_id": tag, "err": "%s" % str(e)[:100]})
        if i % 10 == 0:
            print("  %d/%d" % (i, len(tags)), flush=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    both = [r for r in res if r.get("both_layers")]
    rb = sum(r.get("rows_both", 0) for r in both)
    rc = sum(r.get("rows_conflict", 0) for r in both)
    print(json.dumps({"layers": len(res), "both_layers": len(both),
                      "rows_both": rb, "rows_conflict": rc,
                      "conflict_pct": round(rc * 100.0 / max(1, rb), 2)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
