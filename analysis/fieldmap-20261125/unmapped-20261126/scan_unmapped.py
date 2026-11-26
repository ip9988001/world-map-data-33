#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000269 · 195 层未映射逐层取证（只读）。

输入（只读，不写）：
  analysis/fieldmap-20261125/unusable-v2.csv          195 层清单（== layer-coverage.v2.csv 里 mapped==0 的集合）
  analysis/fieldmap-20261125/layer-coverage.v2.csv    in_rows / part_files / out 口径
  analysis/full-inventory-20261124/local-vs-ledger-reconcile.csv   layer → url
  /data/workspace/world-map-data-33/dist/intake-full/layers/<layer>/part-u*.ndjson.gz   原始 envelope 行

输出（本目录）：
  layers-evidence.jsonl    每层一行：字段名集合 + 每字段非空率 + 角色命中/近失 + 组合串命中 + 5 行脱敏样本 + 判据
  scan-summary.json        全量扫描汇总（供 classify_unmapped.py 与报告使用）

复用口径：直接 import fm_core / split_addr（不重写任何判定逻辑），
  - 角色表（148 个归一字段名）走 SA.roles_of
  - 组合串拆分走 SA.split_number_street（与 map_row 同一实现）
  - envelope 直取字段与 map_row 同序：add_num/pre_dir/st_name/st_suf/post_dir/city/state/zip/lat/lon/raw

用法：
  python3 scan_unmapped.py                       # 全量 195 层，每层 300 行样本
  python3 scan_unmapped.py --limit 3 --rows 40   # 冒烟（只写 stdout，不落盘）
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)                                  # analysis/fieldmap-20261125
ROOT = os.path.dirname(os.path.dirname(FM))                 # repo root
sys.path.insert(0, FM)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import fm_core as C          # noqa: E402
import split_addr as SA      # noqa: E402

LAYERS = os.environ.get("INTAKE_LAYERS",
                        "/data/workspace/world-map-data-33/dist/intake-full/layers")
UNUSABLE = os.path.join(FM, "unusable-v2.csv")
COVERAGE = os.path.join(FM, "layer-coverage.v2.csv")
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")

ENV_ADDR_KEYS = ["add_num", "pre_dir", "st_name", "st_suf", "post_dir", "unit", "city", "state", "zip"]

# 地址类候选词（大小写/下划线无关，归一后再匹配）：门牌 / 街名 / 整串 / 场所
NUM_TOKENS = ("housenum", "housenumber", "house", "hsenum", "hsno", "num", "numb", "no", "nbr",
              "number", "strnum", "streetnum", "addrnum", "addnum", "addrno", "bldgnum", "unitnum")
STREET_TOKENS = ("street", "stname", "stree", "road", "rdname", "route", "avenue", "ave", "lane",
                 "drive", "way", "blvd", "highway", "thoroughfare", "streetname")
FULL_TOKENS = ("address", "addr", "location", "situs", "site", "fullname", "fulladdr", "label",
               "displayname", "addy", "mailing", "propertyaddr", "addrfmt")
# 明确不是地址的场所词（仅用于 A 类判据描述，不作硬判定）
NONADDR_TOKENS = ("pool", "hydrant", "station", "school", "park", "trail", "recycle", "dump",
                  "facility", "poi", "business", "parcel", "permit", "plat", "zoning", "owner",
                  "utility", "meter", "manhole", "camera", "signal", "bridge", "culvert")

SAMPLES_PER_LAYER = 5
RX_HAS_LETTER = re.compile(r"[A-Za-z]")
RX_LEAD_DIGIT = re.compile(r"^\s*\d")
LOOSE_SPLIT = re.compile(r"^\s*(\d{1,6}[A-Za-z]?(?:\s?-\s?\d{1,6}[A-Za-z]?)?)\s+(.+)$")


def _norm(s):
    return SA._norm(s)


def _is_empty(v):
    if v is None:
        return True
    if isinstance(v, bool):
        return False
    sv = str(v).strip()
    if not sv:
        return True
    return SA.is_placeholder(sv)


def _clip(v, n=60):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def pick_part_files(parts, k=2):
    """从 part 列表里挑 k 个（首 + 中），保证样本不只看开头。"""
    if not parts:
        return []
    if len(parts) == 1:
        return parts[:1]
    idxs = [0, len(parts) // 2, len(parts) - 1][:k]
    out = []
    for i in idxs:
        if parts[i] not in out:
            out.append(parts[i])
    return out


def read_rows(path, n):
    rows = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
            if len(rows) >= n:
                break
    return rows


def scan_layer(lid, rows_per_file):
    d = os.path.join(LAYERS, lid)
    parts = sorted(f for f in os.listdir(d)
                   if f.startswith("part-u") and f.endswith(".ndjson.gz")) if os.path.isdir(d) else []
    ev = {"layer_id": lid, "part_files": len(parts), "sample_rows": 0,
          "sample_files": [], "env_key_stats": {}, "raw_key_stats": {},
          "n_raw_keys": 0, "role_hits": {"number": [], "street": [], "zip": []},
          "near_miss": [], "state_key_hits": [], "title": "",
          "split_hits": {}, "split_reject": {}, "loose_split_rows": 0,
          "rows_num_ok": 0, "rows_street_ok": 0, "rows_num_street_ok": 0,
          "rows_env_addr": 0, "rows_any_addrish_value": 0,
          "geo_median": None, "geo_us_frac": None, "samples": [],
          "envelope_nonempty": {}, "errors": []}
    if not parts:
        ev["errors"].append("no_part_u_files")
        return ev

    files = pick_part_files(parts)
    env_cnt = collections.Counter()
    raw_cnt = collections.Counter()
    raw_nonempty = collections.Counter()
    fstats = {}
    fvals = collections.defaultdict(list)
    split_fields = collections.Counter()
    split_reject = collections.Counter()
    env_nonempty = collections.Counter()
    latl = []
    lonl = []
    titles = collections.Counter()
    us_hits = 0

    for fp in files:
        try:
            rows = read_rows(os.path.join(d, fp), rows_per_file)
        except OSError as e:
            ev["errors"].append(f"read {fp}: {e}")
            continue
        ev["sample_files"].append(fp)
        for row in rows:
            if not isinstance(row, dict):
                continue
            ev["sample_rows"] += 1
            for k, v in row.items():
                env_cnt[k] += 1
                if not isinstance(v, dict) and not _is_empty(v):
                    env_nonempty[k] += 1
            raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
            for k, v in raw.items():
                raw_cnt[k] += 1
                if not _is_empty(v):
                    raw_nonempty[k] += 1
            t = row.get("src_title")
            if t:
                titles[str(t)] += 1
            for k in ENV_ADDR_KEYS:
                if not _is_empty(row.get(k)):
                    env_nonempty[k] += 1
            try:
                la, lo = float(row.get("lat")), float(row.get("lon"))
                if la and lo and -90 <= la <= 90 and -180 <= lo <= 180:
                    latl.append(la)
                    lonl.append(lo)
                    if 17.0 <= la <= 72.0 and -180.0 <= lo <= -64.0:
                        us_hits += 1
            except (TypeError, ValueError):
                pass

            # --- 行级：门牌 / 街名（与 map_row 同序，但不写任何东西）---
            num = C.clean_number(row.get("add_num"))
            street = C.clean_street(row.get("pre_dir"), row.get("st_name"),
                                    row.get("st_suf"), row.get("post_dir"))
            env_addr = bool(num or street)
            if env_addr:
                ev["rows_env_addr"] += 1

            any_addrish = False
            row_loose = False
            row_split_street = False
            # 组合串：对所有字符串字段试 split（与 map_row 同实现），并单独试宽松正则
            for k, v in raw.items():
                if not isinstance(v, str) or not v:
                    continue
                sv = v.strip()
                if len(sv) < 4 or len(sv) > 160:
                    continue
                fst = fstats.setdefault(k, collections.Counter())
                fst["seen"] += 1
                toks = [t for t in SA._tokens(sv)]
                if any(t.upper().strip(".") in SA.STREET_TYPES for t in toks):
                    fst["street_type_token"] += 1
                if RX_HAS_LETTER.search(sv) and not RX_LEAD_DIGIT.match(sv):
                    fst["alpha_no_lead_digit"] += 1
                r = SA.split_number_street(sv)
                if r["reason"] == "ok" and r["street_name"]:
                    split_fields[k] += 1
                    fst["split_ok"] += 1
                    row_split_street = True
                    if r["house_number"] and not num:
                        num = C.clean_number(r["house_number"])
                    if not street:
                        street = r["street_name"]
                elif r["reason"] not in ("empty", "placeholder", "no_street", "no_house_number",
                                         "po_box", "rural_route", "masked_number"):
                    split_reject[f"{k}:{r['reason']}"] += 1
                    fst["split_" + r["reason"]] += 1
                    if r["reason"] in ("ambiguous", "bad_street", "intersection") \
                            and LOOSE_SPLIT.match(sv):
                        fst["loose_ok"] += 1
                        row_loose = True
                if len([t for t in toks if len(re.sub(r"[^A-Za-z]", "", t)) >= 3]) >= 2:
                    fst["multitoken_text"] += 1
            if row_loose:
                ev["loose_split_rows"] += 1
            if row_split_street:
                ev["rows_split_street"] = ev.get("rows_split_street", 0) + 1
            # 非 envelope 字段里有没有「像地址串/街名」的值：含空格的多词文本 或 带街道类型词
            if not street:
                for k, v in raw.items():
                    if isinstance(v, str) and len(v.strip()) >= 5 and RX_HAS_LETTER.search(v):
                        sv = v.strip()
                        tk = [t for t in SA._tokens(sv)]
                        if (" " in sv and not re.fullmatch(r"[\w\-]+_[\w\-]+", sv)) or \
                                any(t.upper().strip(".") in SA.STREET_TYPES for t in tk):
                            any_addrish = True
                            break
            if any_addrish:
                ev["rows_any_addrish_value"] += 1
            if num:
                ev["rows_num_ok"] += 1
            if street:
                ev["rows_street_ok"] += 1
            if num and street:
                ev["rows_num_street_ok"] += 1
            for k, v in raw.items():
                if isinstance(v, str) and v.strip() and len(fvals[k]) < 3:
                    fvals[k].append(_clip(v))
            if len(ev["samples"]) < SAMPLES_PER_LAYER:
                ev["samples"].append({
                    "env": {k: _clip(row.get(k)) for k in ENV_ADDR_KEYS if not _is_empty(row.get(k))},
                    "raw": {k: _clip(v) for k, v in list(raw.items())[:25]},
                    "raw_key_count": len(raw),
                })

    n = ev["sample_rows"] or 1
    ev["env_key_stats"] = {k: {"present": c, "nonempty": env_nonempty.get(k, 0)}
                           for k, c in env_cnt.items()}
    ev["raw_key_stats"] = {k: {"present": c, "nonempty": raw_nonempty.get(k, 0)}
                           for k, c in sorted(raw_cnt.items())}
    ev["n_raw_keys"] = len(raw_cnt)
    ev["title"] = titles.most_common(1)[0][0] if titles else ""

    # --- 字段名级别：角色命中 / 近失 / 州码字段 ---
    roles = SA.roles_of(os.path.join(ROOT, "registry", "dialects.v1.yaml"),
                        os.path.join(ROOT, "engine", "dialects"))
    role_hits = {"number": [], "street": [], "zip": []}
    near_miss = []
    state_hits = []
    for k in raw_cnt:
        nk = _norm(k)
        rs = roles.get(nk) or set()
        for role in ("number", "street", "zip"):
            if role in rs:
                role_hits[role].append(k)
        if nk in C.STATE_KEYS:
            state_hits.append(k)
        if not rs:
            toks = nk
            if any(t in toks for t in NUM_TOKENS + STREET_TOKENS + FULL_TOKENS):
                near_miss.append(k)
    ev["role_hits"] = role_hits
    ev["near_miss"] = near_miss
    ev["state_key_hits"] = state_hits

    field_stats = []
    for k, c in sorted(fstats.items(), key=lambda x: -x[1]["seen"]):
        field_stats.append({
            "field": k, "norm": _norm(k),
            "role": sorted(roles.get(_norm(k)) or []),
            "seen": c["seen"], "nonempty": raw_nonempty.get(k, 0),
            "split_ok": c["split_ok"], "street_type_token": c["street_type_token"],
            "alpha_no_lead_digit": c["alpha_no_lead_digit"], "multitoken_text": c["multitoken_text"],
            "loose_ok": c["loose_ok"],
            "split_reject": {kk[6:]: vv for kk, vv in c.items() if kk.startswith("split_") and kk != "split_ok"},
            "values": fvals.get(k, []),
        })
    ev["field_stats"] = field_stats
    ev["split_hits"] = {k: {"rows": c, "nonempty": raw_nonempty.get(k, 0)} for k, c in split_fields.items()}
    ev["split_reject"] = dict(split_reject.most_common(10))
    ev["envelope_nonempty"] = {k: {"rows": c, "rate": round(c / n, 4)} for k, c in env_nonempty.items()}

    if latl:
        latl.sort()
        lonl.sort()
        ev["geo_median"] = [round(latl[len(latl) // 2], 4), round(lonl[len(lonl) // 2], 4)]
        ev["geo_us_frac"] = round(us_hits / len(latl), 4)

    ev.setdefault("rows_split_street", 0)
    for key in ("rows_num_ok", "rows_street_ok", "rows_num_street_ok", "rows_env_addr",
                "rows_any_addrish_value", "loose_split_rows", "rows_split_street"):
        ev[key + "_rate"] = round(ev[key] / n, 4)
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150, help="每个被抽 part 文件读多少行（默认 150 × 2 文件）")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 层（冒烟用，不落盘）")
    ap.add_argument("--out", default=os.path.join(HERE, "layers-evidence.jsonl"))
    ap.add_argument("--summary", default=os.path.join(HERE, "scan-summary.json"))
    args = ap.parse_args()

    cov = {r["layer"]: r for r in csv.DictReader(open(COVERAGE, encoding="utf-8"))}
    un = [r["layer"] for r in csv.DictReader(open(UNUSABLE, encoding="utf-8"))]
    url = {}
    if os.path.isfile(INV):
        for r in csv.DictReader(open(INV, encoding="utf-8")):
            if r.get("url"):
                url[r["layer"]] = r["url"]
    zero = {l for l, r in cov.items() if int(r["mapped"]) == 0}

    t0 = time.time()
    outs = []
    for i, lid in enumerate(un, 1):
        ev = scan_layer(lid, args.rows)
        c = cov.get(lid, {})
        ev["in_rows"] = int(c.get("in_rows") or 0)
        ev["coverage_class"] = c.get("class")
        ev["url"] = url.get(lid, "")
        ev["in_unusable"] = lid in zero
        outs.append(ev)
        if i % 10 == 0 or args.limit or i == len(un):
            print(f"[{i}/{len(un)}] {int(time.time()-t0)}s  {lid[:60]}  rows={ev['sample_rows']} "
                  f"rawkeys={ev['n_raw_keys']} hit={ev.get('rows_num_street_ok_rate')}", flush=True)
        if args.limit and i >= args.limit:
            break

    if args.limit:
        print(json.dumps(outs[:args.limit], ensure_ascii=False)[:4000])
        return

    with open(args.out, "w", encoding="utf-8") as fh:
        for ev in outs:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    summary = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "layers": len(outs),
        "total_in_rows": sum(ev["in_rows"] for ev in outs),
        "unusable_match_coverage_mapped0": sum(1 for ev in outs if ev["in_unusable"]),
        "coverage_mapped0_not_in_unusable": sorted(zero - set(un))[:20],
        "unusable_not_mapped0": sorted(set(un) - zero)[:20],
        "sample_rows_total": sum(ev["sample_rows"] for ev in outs),
        "rows_per_file": args.rows,
        "wall_s": round(time.time() - t0, 1),
    }
    with open(args.summary, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
