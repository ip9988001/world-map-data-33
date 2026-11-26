#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""muse-000269 · B 类修复模拟（只读；不改任何既有文件）。

对 195 个未映射层逐层模拟三种可修路径，量化「修了能上多少行」：

  V1 alias  —— 在最小安全安全表（minimal_safe）里补「有辨识度」的地址字段别名
               （street 名/型两族 + number 族），用 map_row 现有拼接逻辑（最多拼 4 个字段）
  V2 split  —— 修 fm_core.map_row 的两个 split 缺陷：(a) 只在首行试一次就永久放弃
               (b) 只试 raw 前 40 个键。这里对**全部**字段逐行试 SA.split_number_street
  V3 loose  —— split 拒收（ambiguous/bad_street/intersection）但「号 + 街名」形态明确时，
               用 SA.split_number_street 的宽松前置正则兜底（本单只做测算，不落实现）

输出：
  fix-simulation.jsonl   每层一行：三种路径的行命中率、修复后 grade 分布、最小复现样例
  stdout                 紧凑表（供人工复核分类）

用法：python3 simulate_fix.py [--rows 150] [--limit N]
口径全部复用 fm_core / split_addr，不另写判定。
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

HERE = os.path.dirname(os.path.abspath(__file__))
FM = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FM))
sys.path.insert(0, FM)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import fm_core as C          # noqa: E402
import split_addr as SA      # noqa: E402

LAYERS = os.environ.get("INTAKE_LAYERS",
                        "/data/workspace/world-map-data-33/dist/intake-full/layers")
UNUSABLE = os.path.join(FM, "unusable-v2.csv")
COVERAGE = os.path.join(FM, "layer-coverage.v2.csv")
OUT = os.path.join(HERE, "fix-simulation.jsonl")

# ---- 候选别名：只收「有辨识度」的（能安全进全局最小安全表的名字）----
STREET_NAME_PAT = ("streetname", "streetnm", "stname", "stnm", "strname", "strnm", "roadname", "roadnm",
                   "thoroughfare", "thorfare", "thorofare", "streetdescription", "fullstnm",
                   "fullstreetname", "feanme", "sfeanme", "situsstreet", "sitestreet", "addressstreet",
                   "addrstreet", "stnamecomplete", "stnmfull", "streetfull", "streetfullname",
                   "msagroute", "civicstreet", "propstreet", "locstnam", "stdstreet", "streettho",
                   "addrsn", "streetnamedesc")
STREET_TYPE_PAT = ("featyp", "sfeatyp", "strtype", "strsuffix", "streettype", "streetsuffix",
                   "roadsuffix", "roadtype", "streetdirsuffix", "strsuf", "propsuffix", "locstsuf",
                   "civictype")
NUMBER_PAT = ("strnum", "streetnum", "streetno", "strno", "houseno", "housenum", "housenumber",
              "addrnum", "addressnum", "civicnum", "civnum", "addnum", "situsnum", "stnum", "hsenum",
              "buildingnum", "bldgnum", "civicnumber", "housebloc", "locstnbr", "number")

RX_LOOSE = re.compile(r"^\s*(\d{1,6}[A-Za-z]?(?:\s?-\s?\d{1,6}[A-Za-z]?)?)\s+(\S.*)$")
STREET_DIGITS = re.compile(r"\d{3,}")


def _norm(s):
    return SA._norm(s)


PERSON_NAME_NORM = {"firstname", "lastname", "firstandlastname", "fullname", "name",
                    "requestorname", "authorname", "creator", "editor"}


def _match(norm, pats):
    # 人名列不是街名列：角色表里 firstname/lastname 被误收为 street 别名（既有缺陷），
    # 这里显式排掉，避免把「Sherie Gibbens」当成街名（muse-000269 发现）。
    if norm in PERSON_NAME_NORM:
        return False
    return any(p in norm for p in pats)


def _nonempty(v):
    if v is None or isinstance(v, bool):
        return False
    sv = str(v).strip()
    return bool(sv) and not SA.is_placeholder(sv)


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


def pick_parts(parts, k=2):
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


def grade_from(num, street, city, state, zip5, has_point, has_point_any):
    rec = {"house_number": num or None, "street_name": street or None, "city": city or None,
           "state": state or None, "zip5": zip5 or None,
           "lat": 1.0 if has_point_any else None, "lon": 1.0 if has_point_any else None,
           "_interp": not has_point}
    g = C.grade_of(rec, GRADES)
    if g in ZIP_GRADES and not rec["zip5"]:
        g = C.grade_of(rec, {k: v for k, v in GRADES.items() if k not in ZIP_GRADES})
    return g


def simulate(lid, rows, roles):
    parts_dir = os.path.join(LAYERS, lid)
    ev = {"layer_id": lid, "rows": 0, "v1_alias": 0, "v2_split_all": 0, "v1_first40": 0,
          "v3_loose": 0, "any": 0, "grades_after_fix": collections.Counter(),
          "alias_fields": collections.Counter(), "split_fields": collections.Counter(),
          "repro": {}}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ev["rows"] += 1
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        # 原生值（与 map_row 同序）
        num = C.clean_number(row.get("add_num"))
        street = C.clean_street(row.get("pre_dir"), row.get("st_name"),
                                row.get("st_suf"), row.get("post_dir"))
        city = C.clean_city(row.get("city"))
        state = C.clean_state(row.get("state") or row.get("st"))
        zip5, _ = C.clean_zip5(row.get("zip"))
        la, lo, _ = C.clean_coord(row.get("lat"), row.get("lon"))
        has_point_any = la is not None and lo is not None
        has_point = has_point_any and not row.get("pos_estimated")

        # raw 角色别名（现状逻辑：roles 表）
        if not num:
            for k in raw:
                if _nonempty(raw.get(k)) and "number" in (roles.get(_norm(k)) or ()):
                    cand = C.clean_number(raw.get(k))
                    if cand:
                        num = cand
                        break
        if not street:
            got = []
            for k in raw:
                if _nonempty(raw.get(k)) and "street" in (roles.get(_norm(k)) or ()):
                    got.append(str(raw.get(k)).strip())
            if got:
                got.sort(key=lambda x: -len(x))
                street = " ".join(got[:4])

        # ---- V1：补有辨识度的别名（street 名 + 型，number）----
        v1_street, v1_num, v1_hit = street, num, False
        if not street:
            names = [(k, str(v).strip()) for k, v in raw.items()
                     if _nonempty(v) and _match(_norm(k), STREET_NAME_PAT)]
            types = [(k, str(v).strip()) for k, v in raw.items()
                     if _nonempty(v) and _match(_norm(k), STREET_TYPE_PAT) and
                     not any(k == a for a, _ in names)]
            if names:
                names.sort(key=lambda x: -len(x[1]))
                sv = " ".join([v for _, v in names[:1]] + [v for _, v in types[:1]])
                nk = _norm(names[0][0])
                if not STREET_DIGITS.search(names[0][1]):
                    v1_street, v1_hit = sv, True
                    ev["alias_fields"][f"{nk}+{_norm(types[0][0]) if types else ''}"] += 1
                    ev["repro"].setdefault("v1", {"field": names[0][0], "value": names[0][1][:60]})
        if not v1_num:
            for k, v in raw.items():
                if _nonempty(v) and _match(_norm(k), NUMBER_PAT):
                    cand = C.clean_number(v)
                    if cand:
                        v1_num = cand
                        break
        if v1_hit:
            ev["v1_alias"] += 1

        # ---- V2：split 全字段（不受 40 键限制、每行都试）----
        v2_street, v2_num, v2_hit = street, num, False
        if not street:
            for k, v in raw.items():
                if not isinstance(v, str) or not (4 <= len(v.strip()) <= 160):
                    continue
                r = SA.split_number_street(v)
                if r["reason"] == "ok" and r["street_name"] and r["confidence"] > 0:
                    v2_street = r["street_name"]
                    if not v2_num and r["house_number"]:
                        v2_num = C.clean_number(r["house_number"])
                    v2_hit = True
                    if v2_num:
                        v2_num_street = True
                    ev["split_fields"][_norm(k)] += 1
                    ev["repro"].setdefault("v2", {"field": k, "value": v.strip()[:60],
                                                  "num": r["house_number"], "street": r["street_name"]})
                    break
        # 首 40 键版本（衡量 (b) 40 键上限的影响）
        if not street:
            for k in list(raw.keys())[:40]:
                v = raw.get(k)
                if not isinstance(v, str) or not (4 <= len(v.strip()) <= 160):
                    continue
                r = SA.split_number_street(v)
                if r["reason"] == "ok" and r["street_name"] and r["confidence"] > 0:
                    ev["v1_first40"] += 1
                    break
        if v2_hit:
            ev["v2_split_all"] += 1

        # ---- V3：split 拒收但形态明确（宽松兜底）----
        v3_hit = False
        if not street and not v2_hit:
            for k, v in raw.items():
                if not isinstance(v, str) or not (4 <= len(v.strip()) <= 160):
                    continue
                r = SA.split_number_street(v)
                if r["reason"] in ("ambiguous", "bad_street") and RX_LOOSE.match(v.strip()):
                    ev["v3_loose"] += 1
                    ev["repro"].setdefault("v3", {"field": k, "value": v.strip()[:60],
                                                  "reason": r["reason"]})
                    v3_hit = True
                    break
        if v1_hit or v2_hit or v3_hit:
            ev["any"] += 1

        # 修复后 grade（取 v1/v2 里更"原生"的 street；split 出来的只能 ≤ A）
        if v1_hit:
            g = grade_from(v1_num, v1_street, city, state, zip5, has_point, has_point_any)
            if g:
                ev["grades_after_fix"][g] += 1
        elif v2_hit:
            g = grade_from(v2_num, v2_street, city, state, zip5, has_point, has_point_any)
            if g == "S":
                g = "A"
            if g:
                ev["grades_after_fix"][g] += 1
        elif street:
            g = grade_from(num, street, city, state, zip5, has_point, has_point_any)
            if g:
                ev["grades_after_fix"][g] += 1
    n = ev["rows"] or 1
    for k in ("v1_alias", "v2_split_all", "v1_first40", "v3_loose", "any"):
        ev[k + "_rate"] = round(ev[k] / n, 4)
    ev["grades_after_fix"] = dict(ev["grades_after_fix"])
    ev["alias_fields"] = dict(ev["alias_fields"].most_common(5))
    ev["split_fields"] = dict(ev["split_fields"].most_common(5))
    return ev


GRADES = C.load_pilot_cfg()["grades"]
ZIP_GRADES = {k for k, v in GRADES.items() if "zip5" in v}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=150)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    cov = {r["layer"]: r for r in csv.DictReader(open(COVERAGE, encoding="utf-8"))}
    un = [r["layer"] for r in csv.DictReader(open(UNUSABLE, encoding="utf-8"))]
    roles = SA.roles_of(os.path.join(ROOT, "registry", "dialects.v1.yaml"),
                        os.path.join(ROOT, "engine", "dialects"))
    outs = []
    for i, lid in enumerate(un, 1):
        d = os.path.join(LAYERS, lid)
        parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".gz")) \
            if os.path.isdir(d) else []
        rows = []
        for fp in pick_parts(parts):
            rows.extend(read_rows(os.path.join(d, fp), args.rows))
        ev = simulate(lid, rows, roles)
        ev["in_rows"] = int(cov[lid]["in_rows"])
        outs.append(ev)
        if i % 20 == 0 or args.limit or i == len(un):
            print(f"[{i}/{len(un)}] {lid[:56]} v1={ev['v1_alias_rate']} v2={ev['v2_split_all_rate']} "
                  f"v3={ev['v3_loose_rate']} any={ev['any_rate']}", flush=True)
        if args.limit and i >= args.limit:
            break
    if args.limit:
        return
    with open(OUT, "w", encoding="utf-8") as fh:
        for ev in outs:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
    tot = sum(e["any"] for e in outs)
    print(f"\nlayers={len(outs)} fixed_layers(any>0)={sum(1 for e in outs if e['any']>0)} "
          f"rows_recoverable_sample={tot}")


if __name__ == "__main__":
    main()
