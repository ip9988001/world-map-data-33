#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② step1：从 P7 的 321 层抽「门牌列名 / 街名列名」，去重 + 边界过滤 → 别名候选 / 待定表。

输入（全本地，不抓网，只用已提交文件）：
  analysis/combo-step1-20261125/patterns.csv            —— P7 层清单（321 层）
  analysis/combo-step1-20261125/combo_classify.py       —— 复用同一份 role_of_field()/classify()（判据不许改）
  survey/ng911/samples.csv.gz                           —— 完整字段名 + 3 条原始记录
  analysis/coord-samples-20261124/samples/*.csv         —— 真实地址值（addr_fields_json）

产物：
  _work/p7_fields.csv        逐层：门牌列 / 街名列 / 其余分列
  _work/alias_candidates.json 去重后的别名候选 + 冲突 + 待定
  （CSV 产物由 verify_keys.py 落 analysis/combo-step2-20261125/ 根下）
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import importlib.util
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
REGISTRY = os.path.join(ROOT, "registry", "dialects.v1.yaml")
WORK = os.path.join(HERE, "_work")
MAXVAL = 40

# 「像邮寄/业主地址」→ 不进别名表（派单第 3 条边界）
PENDING_RE = re.compile(r"(owner|ownaddr|own_?adr|mail|bill|contact|taxpayer|applicant|"
                        r"deed|ship_?to|pobox|po_?box|legal|mortgage|insur)", re.I)
# 结构 ID：不是地址列
IDLIKE_RE = re.compile(r"^(objectid|fid|globalid|seqnum|seq_num|oid|shape|st_area|st_length)", re.I)


def load_step1_module():
    p = os.path.join(STEP1, "combo_classify.py")
    spec = importlib.util.spec_from_file_location("combo_classify_step1", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def norm(f):
    return re.sub(r"[^a-z0-9]", "", (f or "").lower())


def registry_aliases():
    import yaml
    out = collections.defaultdict(set)
    for d in yaml.safe_load(open(REGISTRY, encoding="utf-8"))["dialects"]:
        for role in ("number", "street", "zip", "unit", "city", "state"):
            key = {"city": "place"}.get(role, role)
            for a in (d.get("template") or {}).get(key + "_aliases") or []:
                out[norm(a)].add(role)
    return out


def main():
    os.makedirs(WORK, exist_ok=True)
    p7 = [r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"]
    assert len(p7) == 321, f"P7 层数 {len(p7)} != 321"
    tgt = {r["url"]: r for r in p7}

    # 1) ng911：字段清单 + 3 条记录
    per = {u: {"url": u, "fields": [], "ng911_samples": [], "coord_values": collections.defaultdict(list),
               "coord_rows": 0} for u in tgt}
    with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            u = r.get("url") or ""
            rec = per.get(u)
            if not rec:
                continue
            rec["fields"] = [f.strip() for f in (r.get("fields") or "").split(";") if f.strip()]
            try:
                rec["ng911_samples"] = json.loads(r.get("samples") or "[]")[:3]
            except Exception:
                rec["ng911_samples"] = []

    # 2) coord samples：真实值
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            rec = per.get(r.get("layer_url") or "")
            if not rec:
                continue
            rec["coord_rows"] += 1
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                continue
            for k, v in af.items():
                v = v if isinstance(v, str) else str(v)
                v = re.sub(r"\s+", " ", v).strip()
                if not v or v.lower() in ("null", "none"):
                    continue
                vals = rec["coord_values"][k]
                if v not in vals and len(vals) < MAXVAL:
                    vals.append(v)
                if k not in rec["fields"]:
                    rec["fields"].append(k)

    cc = load_step1_module()
    reg = registry_aliases()

    rows, cand = [], collections.defaultdict(lambda: {"number": 0, "street": 0, "layers": [], "states": set()})
    conflicts, not_p7 = [], []
    for u, meta in tgt.items():
        rec = {"fields": per[u]["fields"],
               "coord_values": dict(per[u]["coord_values"]),
               "ng911_samples": per[u]["ng911_samples"]}
        pid, det = cc.classify(rec, None)
        if pid != "P7":                      # 复算不得与 step1 判据出现分歧
            not_p7.append((u, pid))
            continue
        nf, sf = det["fields"][0], det["fields"][1]
        extra = det["fields"][2:]
        rows.append({"url": u, "layer_id": meta["layer_id"], "state": meta["state"], "rows_n": meta["rows_n"],
                     "number_field": nf, "street_field": sf, "extra_fields": "|".join(extra),
                     "coord_rows": per[u]["coord_rows"]})
        for role, f in (("number", nf), ("street", sf)):
            c = cand[norm(f)]
            c[role] += 1
            c["layers"].append(u)
            c["states"].add(meta["state"])
            c.setdefault("spellings", collections.Counter())[f] += 1

    with open(os.path.join(WORK, "p7_fields.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    applied, pending = [], []
    for n, c in sorted(cand.items()):
        spelling = c["spellings"].most_common(1)[0][0]
        rec = {"alias": spelling, "norm": n, "as_number": c["number"], "as_street": c["street"],
               "layers": len(set(c["layers"])), "states": sorted(c["states"])}
        if c["number"] and c["street"]:
            pending.append(dict(rec, reason="同名在不同层分任门牌列与街名列（冲突）"))
        elif IDLIKE_RE.search(spelling or ""):
            pending.append(dict(rec, reason="结构 ID / 序号列（不是地址）"))
        elif PENDING_RE.search(spelling or ""):
            pending.append(dict(rec, reason="像业主/邮寄/联系地址，是否地点地址未定（派单边界）"))
        elif n in reg and {"number" if c["number"] else "street"} <= reg[n]:
            rec["reason"] = "registry 已有（无需新增）"
            applied.append(rec)
        else:
            applied.append(rec)

    json.dump({"p7_layers": len(rows), "not_p7_after_recount": not_p7,
               "applied": applied, "pending": pending},
              open(os.path.join(WORK, "alias_candidates.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"p7_rows": len(rows), "recount_mismatch": len(not_p7),
                      "candidate_names": len(cand),
                      "new_number_aliases": sum(1 for a in applied if a.get("as_number")),
                      "new_street_aliases": sum(1 for a in applied if a.get("as_street")),
                      "already_in_registry": sum(1 for a in applied if a.get("reason")),
                      "pending": len(pending)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
