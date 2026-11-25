#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② step2：逐层按「行级共同成立」重选门牌列/街名列，给出别名候选 + 值证据。

为什么不直接用 classify() 的 fields[0]/[1]：step1 的判据是按列单独过值形态（sh.num≥0.6 且名字像），
多候选时取字段 schema 顺序第一个 —— 实测会把 TRANUM / EMPNUM / Number_of_Vehicles 当成门牌列。
本脚本改成行级共同成立（同一行里门牌像门牌、街名像街名），并且要求列名语义通过白名单/黑名单。
判据不放松：hn_score/st_score 都要求该列值形态；P7 层清单仍是 step1 的 321 层，一层不增。

产物：_work/p7_pairs.csv（逐层：重选后的门牌列/街名列 + 行级命中率 + 旧选列对比）
      _work/alias_evidence.json（每个候选字段名的值统计 + 归属层）
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
WORK = os.path.join(HERE, "_work")

PURE_HN = re.compile(r"^\d{1,6}[A-Za-z]?(-[0-9A-Za-z]{1,4})?$")
STREETLIKE = re.compile(r"^(?=.*[A-Za-z])[A-Za-z0-9 .,'#/&-]{2,60}$")
ZIPONLY = re.compile(r"^\d{5}(-\d{4})?$")

HN_HINT = re.compile(r"(hous|hse|(^|[^a-z])hn([^a-z]|$)|st_?num|stnum|street_?n|addr.*num|num.*addr|"
                     r"situs.*(num|st)|sit_?num|bldg|bld|blk|beg|start|road.*num|rd.*num|rte.*num|"
                     r"rt_?num|site_?num|loc.*num|prop.*num|nbr|anum|haus|^num$|^numb|numbe$|_num$)", re.I)
HN_REJECT = re.compile(r"(count|total|number_?of|num_?of|score|index|seq|acct|inv|xrf|^map|loop|visit|"
                       r"retail|sna_|esn|nguid|emp|tran|arrest|user|_rev_|rem_|numparts|numgqtrs|"
                       r"^numin|numoccup|numcbldg|numtrks|numb.?vehc|num_?slabs|num_?fruit|"
                       r"numberof|numof|hyd|ldmk|funcnum|muni|cds|subd|srt|stp|overall|_id$|guid)", re.I)
ST_HINT = re.compile(r"(street|st_?name|stnam|str_?name|(^|[^a-z])st([^a-z]|$)|(^|[^a-z])str([^a-z]|$)|"
                     r"road|rd_?name|roadname|address|addr|situs|site|prop|loc_?str|thoroughfare|"
                     r"streetall|fullstreet)", re.I)
ST_REJECT = re.compile(r"(suffix|sufix|^suf|sufi|suff$|prefix|prefx|pre_?dir|post_?dir|dir$|_dir|"
                       r"type$|_type|typ$|_typ|city|guid|_id$|verif|priority|linked|notalready|level|"
                       r"auth|from_|prefix|parcel|mail|owner|date|_dt$)", re.I)
PENDING_RE = re.compile(r"(owner|ownaddr|own_?adr|mail|bill|contact|taxpayer|applicant|deed|ship_?to|"
                        r"pobox|po_?box|legal|mortgage|insur)", re.I)


def norm(f):
    return re.sub(r"[^a-z0-9]", "", (f or "").lower())


def load_rows():
    """逐层保留真实坐标样本行（addr_fields_json），数量与 step1 同源。"""
    p7 = [r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"]
    assert len(p7) == 321, len(p7)
    meta = {r["url"]: r for r in p7}
    rows = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r.get("layer_url") or ""
            if u not in meta:
                continue
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                continue
            af = {k: re.sub(r"\s+", " ", str(v)).strip() for k, v in af.items()
                  if v not in (None, "", "null", "None")}
            if af:
                rows[u].append(af)
    # ng911 兜底：没有坐标样本行的层用 3 条原始记录
    need = {u for u in meta if not rows.get(u)}
    if need:
        with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                u = r.get("url") or ""
                if u not in need:
                    continue
                try:
                    smp = json.loads(r.get("samples") or "[]")[:3]
                except Exception:
                    smp = []
                for s in smp:
                    af = {k: re.sub(r"\s+", " ", str(v)).strip() for k, v in (s or {}).items()
                          if v not in (None, "", "null", "None")}
                    if af:
                        rows[u].append(af)
    return meta, rows


def is_street_val(v):
    """街道名的值形态：有字母、不像门牌、不像邮编、不含邮编/州缩写（含＝全地址，不是街名列）。"""
    if not v or PURE_HN.match(v) or ZIPONLY.match(v) or re.search(r"\d{5}", v):
        return False
    if not re.search(r"[A-Za-z]{2,}", v):
        return False
    return not (v.count(",") and re.search(r"\b[A-Z]{2}\b", v.upper()))


def score(rows, f, test):
    vals = [r[f] for r in rows if r.get(f)]
    if not vals:
        return 0.0, 0
    return sum(1 for v in vals if test(v)) / len(vals), len(vals)


def main():
    os.makedirs(WORK, exist_ok=True)
    meta, rows = load_rows()
    # step1 的选列（用于对比，不改判据）
    import importlib.util
    spec = importlib.util.spec_from_file_location("s1", os.path.join(STEP1, "combo_classify.py"))
    s1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(s1)

    old = {}
    for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8")):
        if r["pattern_id"] != "P7":
            continue
        old[r["url"]] = r["fields"].split("|")

    out, ev = [], collections.defaultdict(lambda: {"as_hn": [], "as_st": [], "vals": []})
    for u, m in meta.items():
        rr = rows.get(u) or []
        fields = []
        for r in rr:
            for k in r:
                if k not in fields:
                    fields.append(k)
        hn, st = [], []
        for f in fields:
            hs, n1 = score(rr, f, lambda v: bool(PURE_HN.match(v)))
            ss, n2 = score(rr, f, is_street_val)
            if n1 >= 1:
                ev[f]["vals"].extend([r[f] for r in rr if r.get(f)][:3])
            if hs >= 0.6 and HN_HINT.search(f) and not HN_REJECT.search(f):
                hn.append((hs, f))
            if ss >= 0.6 and ST_HINT.search(f) and not ST_REJECT.search(f):
                st.append((ss, f))
        best, bp = None, 0.0
        for hs, nf in sorted(hn, reverse=True):
            for ss, sf in sorted(st, reverse=True):
                if nf == sf:
                    continue
                ok = sum(1 for r in rr if PURE_HN.match(r.get(nf, "")) and is_street_val(r.get(sf, "")))
                p = ok / max(1, len(rr))
                if p > bp:
                    best, bp = (nf, sf), p
        rec = {"url": u, "layer_id": m["layer_id"], "state": m["state"], "rows_n": m["rows_n"],
               "coord_rows": len(rr), "old_fields": "|".join(old.get(u) or []),
               "number_field": best[0] if best else "", "street_field": best[1] if best else "",
               "pair_share": round(bp, 3), "hn_candidates": "|".join(f for _, f in sorted(hn, reverse=True)),
               "st_candidates": "|".join(f for _, f in sorted(st, reverse=True))}
        out.append(rec)
        if best and bp >= 0.5:
            ev[best[0]]["as_hn"].append(u)
            ev[best[1]]["as_st"].append(u)

    with open(os.path.join(WORK, "p7_pairs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    # 全量字段证据（供 alias_select.py 用严格规则定别名）
    full = {}
    for u, m in meta.items():
        rr = rows.get(u) or []
        flds = []
        for r in rr:
            for k in r:
                if k not in flds:
                    flds.append(k)
        for f in flds:
            hs, n1 = score(rr, f, lambda v: bool(PURE_HN.match(v)))
            ss, n2 = score(rr, f, is_street_val)
            full.setdefault(f, {"hn_share": 0.0, "st_share": 0.0, "vals": [], "layers": [], "n": 0})
            e = full[f]
            e["n"] += n1
            e["hn_share"] = max(e["hn_share"], round(hs, 3))
            e["st_share"] = max(e["st_share"], round(ss, 3))
            for v in [r[f] for r in rr if r.get(f)][:2]:
                if v not in e["vals"]:
                    e["vals"].append(v)
            if u not in e["layers"]:
                e["layers"].append(u)
    json.dump({"fields": full, "verified_pairs": [
        {k: r[k] for k in ("url", "number_field", "street_field", "pair_share")}
        for r in out if r["pair_share"] >= 0.5]},
        open(os.path.join(WORK, "alias_evidence.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"p7_layers": len(out),
                      "layers_with_verified_pair": sum(1 for r in out if r["pair_share"] >= 0.5),
                      "fields_with_evidence": len(full)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
