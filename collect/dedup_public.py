#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08 · stage3：台账 → 两份下游产物（public 版无门牌 / product 版完整）+ 泄漏扫描。

public 版（可公开，喂搜索页/SEO 三级聚合）：
  · 只出 州 / 市 / 邮编 / 街道页，字段是**号段 + 统计**，没有任何单条门牌
  · 号段按 10 取整；`address_count < 3` 的街道页不出（防反推）
product 版（不公开，喂地址生成器）：主台账全部字段

泄漏扫描（硬门禁）：public 版任何一行都不许出现
  ① 非整十的门牌号 ② `APT/STE/#/UNIT` 这类单元串 ③ `\d+ 街名 类型` 形态的完整地址

用法：
  python3 collect/dedup_public.py --out /tmp/08-R1
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

BAD_UNIT = re.compile(r"(?i)\b(APT|APARTMENT|STE|SUITE|UNIT|FL|FLOOR|BLDG|ROOM|#)\b")
# 门牌号形态：**只当前导整数不属于街名本体时才算泄漏**（`5 AVENUE COURT` 是「第五大道」，不是门牌 5）
LEAD_NUM = re.compile(r"^\s*(\d{1,6})\b")
FORBIDDEN_FIELDS = ("number", "number_suffix", "unit", "unit_raw", "lat", "lon",
                    "dup_members", "src_layers", "src_group_votes", "tiger_verify")
PUBLIC_FIELDS = ("state", "county_fips", "city_postal", "zip5", "street_full", "street_core",
                 "number_min", "number_max", "number_span_n", "address_count", "unit_count",
                 "lat_centroid", "lon_centroid", "tier", "first_seen", "last_seen")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def round10(n):
    return None if n is None else int(n) // 10 * 10


def street_full_of(street_key: str) -> str:
    bits = (street_key or "").split("|")
    while len(bits) < 3:
        bits.append("")
    typ, core, d = bits[0], bits[1], bits[2]
    pre = d.split("+")[0] if d else ""
    return " ".join(x for x in (pre, core, typ) if x)


def iter_ledger(ledger_dir: str):
    for root, _dirs, files in os.walk(ledger_dir):
        for f in sorted(files):
            if not f.endswith(".ndjson.gz"):
                continue
            with gzip.open(os.path.join(root, f), "rt", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        yield json.loads(line)


def write_gz(path: str, rows) -> int:
    n = 0
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def scan_public(rows: list[dict]) -> dict:
    """泄漏扫描：只在 public 行上跑。五类命中任一 > 0 即 FAIL。"""
    hits = {"forbidden_field": [], "non_decade_number": [], "unit_token": [],
            "leading_door_number": [], "small_sample": []}
    for r in rows:
        for f in FORBIDDEN_FIELDS:
            if f in r:
                hits["forbidden_field"].append({"field": f})
        for k in ("number_min", "number_max"):
            v = r.get(k)
            if isinstance(v, int) and v % 10 != 0:
                hits["non_decade_number"].append({k: v, "street": r.get("street_full")})
        core_first = (r.get("street_core") or "").split(" ")[0]
        for k, v in r.items():
            if not isinstance(v, str):
                continue
            if BAD_UNIT.search(v):
                hits["unit_token"].append({k: v[:60]})
            if k not in ("street_full", "city_postal"):
                continue
            m = LEAD_NUM.match(v)
            if m and m.group(1) != core_first:      # 前导整数不是街名本体 → 当门牌号
                hits["leading_door_number"].append({k: v[:60]})
        if (r.get("address_count") or 0) < 3:
            hits["small_sample"].append({"street": r.get("street_full"),
                                         "n": r.get("address_count")})
    return {k: {"n": len(v), "sample": v[:3]} for k, v in hits.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-count", type=int, default=3)
    args = ap.parse_args()

    ledger_dir = os.path.join(args.out, "ledger")
    agg_dir = os.path.join(args.out, "agg")
    pub_dir = os.path.join(args.out, "public")
    prod_dir = os.path.join(args.out, "product")
    rep_dir = os.path.join(args.out, "reports")
    for d in (pub_dir, prod_dir, rep_dir):
        os.makedirs(d, exist_ok=True)

    # ---- product：完整台账（直接搬运，字段不动）
    prod_n = 0
    with gzip.open(os.path.join(prod_dir, "ledger-full.ndjson.gz"), "wt",
                   encoding="utf-8") as fh:
        for r in iter_ledger(ledger_dir):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            prod_n += 1

    # ---- public：从聚合行派生，号段取整 + 小样本屏蔽
    street_rows = []
    with gzip.open(os.path.join(agg_dir, "streets.ndjson.gz"), "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["address_count"] < args.min_count:
                continue
            lo, hi = round10(r.get("number_min")), round10(r.get("number_max"))
            street_rows.append({
                "state": r["state"], "county_fips": r["county_fips"],
                "city_postal": r.get("city") or "", "zip5": "",
                "street_full": street_full_of(r["street_key"]),
                "street_core": (r["street_key"].split("|") + ["", "", ""])[1],
                "number_min": lo, "number_max": hi,
                "number_span_n": (None if (lo is None or hi is None) else max(0, (hi - lo) // 10 + 1)),
                "address_count": r["address_count"], "unit_count": r["unit_count"],
                "lat_centroid": None, "lon_centroid": None,
                "tier": None, "first_seen": "", "last_seen": "",
            })
    pub_streets = write_gz(os.path.join(pub_dir, "streets.ndjson.gz"), street_rows)

    zip_rows = []
    with gzip.open(os.path.join(agg_dir, "zips.ndjson.gz"), "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["address_count"] < args.min_count:
                continue
            zip_rows.append({"state": r["state"], "zip5": r["zip5"],
                             "address_count": r["address_count"],
                             "street_count": r["street_count"]})
    pub_zips = write_gz(os.path.join(pub_dir, "zips.ndjson.gz"), zip_rows)

    city_rows = []
    with gzip.open(os.path.join(agg_dir, "cities.ndjson.gz"), "rt", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["address_count"] < args.min_count:
                continue
            city_rows.append({"state": r["state"], "city": r["city"],
                              "address_count": r["address_count"],
                              "street_count": r["street_count"]})
    pub_cities = write_gz(os.path.join(pub_dir, "cities.ndjson.gz"), city_rows)

    scan = scan_public(street_rows + zip_rows + city_rows)
    leaks = sum(v["n"] for v in scan.values())
    rep = {
        "schema": "08-public/v1", "at": now(),
        "product_rows": prod_n,
        "public_rows": {"streets": pub_streets, "zips": pub_zips, "cities": pub_cities},
        "min_count": args.min_count,
        "leak_scan": scan, "leak_total": leaks,
        "schema_has_no_door_field": not any(f in PUBLIC_FIELDS for f in FORBIDDEN_FIELDS),
    }
    json.dump(rep, open(os.path.join(rep_dir, "public.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[public] product=%d public=%s 泄漏=%d" % (prod_n, rep["public_rows"], leaks), flush=True)
    return 0 if leaks == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
