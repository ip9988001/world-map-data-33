#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② step4：验收三件事，全部可复算。

1) P7 的 321 层建键：addr_key() 逐字照抄 sandbox/coord_evidence.py（不改判据），
   ROLES 两份：old = registry/dialects.v1.yaml 别名；new = old + 本轮 engine 别名表。
   成功 = 该层真实坐标样本行里至少 1 行能出「门牌+街名」键；另报「键形合法」行占比。
2) 回归 A：coord-samples 全量行（13,532 层 / 738,174 行）old vs new 建键结果逐行对照，
   非 P7 层差异必须为 0（P7 层的变化是本轮目的，单列）。
3) 回归 B：survey/ng911 全量层（60,697 层 × 3 条原始记录）old vs new 对照，差异必须为 0。

产物（写在 analysis/combo-step2-20261125/ 根下）：
  p7-alias-applied.csv   逐层：新旧建键行数、选列、别名是否命中
  failed-layers.csv      建键失败的层 + 原因
  pending-uncertain.csv  待定别名表
  _work/recount.json     汇总数字（断言用）
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import json
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
REGISTRY = os.path.join(ROOT, "registry", "dialects.v1.yaml")
ENGINE_YAML = os.path.join(ROOT, "engine", "dialects", "sources.v1.yaml")
WORK = os.path.join(HERE, "_work")

# ---- 以下 4 个函数逐字照抄 sandbox/coord_evidence.py（判据不许改）----
SUFFIX = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
          "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "hwy": "highway",
          "pkwy": "parkway", "cir": "circle", "ter": "terrace", "trl": "trail"}
NUM_RE, ZIP_RE = re.compile(r"^\s*(\d+)\s*[A-Za-z]?\s+(.*)$"), re.compile(r"\b(\d{5})\b")
norm = lambda f: re.sub(r"[^a-z0-9]", "", (f or "").lower())


def street_norm(s):
    w = [SUFFIX.get(x, x) for x in re.findall(r"[a-z0-9]+", (s or "").lower())]
    return "".join(w)


def addr_key(af, ROLES, state):
    n = s = z = ""
    for k, v in af.items():
        v = str(v).strip() if isinstance(v, (int, float, str)) else ""
        r = ROLES.get(norm(k)) or ()
        if v and "number" in r and not n:
            n = re.sub(r"[^0-9A-Za-z-]", "", v)
        elif v and "street" in r and not s:
            s = v
        elif v and "zip" in r and not z:
            z = (ZIP_RE.search(v) or [None, ""])[1]
    if not (n and s):
        for v in af.values():
            v = v if isinstance(v, str) else ""
            m = NUM_RE.match(v.split(",")[0]) if "," in v else None
            if m and ZIP_RE.search(v):
                n, s, z = m.group(1), m.group(2), ZIP_RE.search(v).group(1)
                break
    return f"{state}|{n}|{street_norm(s)}|{z}" if (n and s) else ""


PURE_HN = re.compile(r"^\d{1,6}[A-Za-z]?(-[0-9A-Za-z]{1,4})?$")


def key_ok(key):
    """键形合法：门牌段是纯门牌，街名段有字母。"""
    if not key:
        return False
    parts = key.split("|")
    if len(parts) != 4:
        return False
    return bool(PURE_HN.match(parts[1])) and bool(re.search(r"[a-z]", parts[2]))


def roles_old():
    out = collections.defaultdict(set)
    for d in yaml.safe_load(open(REGISTRY, encoding="utf-8"))["dialects"]:
        for role in ("number", "street", "zip"):
            for a in (d.get("template") or {}).get(role + "_aliases") or []:
                out[norm(a)].add(role)
    return out


def roles_new(extra):
    out = collections.defaultdict(set)
    for k, v in roles_old().items():
        out[k] |= v
    for a in extra["number"]:
        out[norm(a)].add("number")
    for a in extra["street"]:
        out[norm(a)].add("street")
    return out


def engine_alias_section(profile=None):
    """从 engine/dialects/sources.v1.yaml 读本轮新增的别名条目（单一来源，不重复维护）。"""
    if os.environ.get("ALIAS_PROFILE") == "all":       # 对照口径：把被剔除的 8 个也算进来
        rows = list(csv.DictReader(open(os.path.join(WORK, "alias_screen.csv"), encoding="utf-8")))
        return {"number": [r["alias"] for r in rows if r["role"] == "number"],
                "street": [r["alias"] for r in rows if r["role"] == "street"]}
    doc = yaml.safe_load(open(ENGINE_YAML, encoding="utf-8"))
    for d in doc.get("dialects") or []:
        if d.get("id") == "p7-alias-ext-v1":
            f = d.get("fields") or {}
            return {"number": list(f.get("number") or []), "street": list(f.get("street") or [])}
    raise SystemExit("engine/dialects/sources.v1.yaml 里没有 p7-alias-ext-v1")


def main():
    os.makedirs(WORK, exist_ok=True)
    final = json.load(open(os.path.join(WORK, "alias_final.json")))
    extra = engine_alias_section()
    R_OLD, R_NEW = roles_old(), roles_new(extra)

    p7 = {r["url"]: r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"}
    assert len(p7) == 321
    pairs = {r["url"]: r for r in csv.DictReader(open(os.path.join(WORK, "p7_pairs.csv"), encoding="utf-8"))}

    # ---------- 1) P7 321 层建键 ----------
    decomp = {"harm": 0, "loss": 0, "gain": 0, "gain_ok": 0}
    rows_by = collections.defaultdict(list)
    diff_rows = 0
    diff_layers_non_p7 = set()
    all_layers = 0
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r.get("layer_url") or ""
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                af = {}
            if not af:
                continue
            st = r.get("state") or ""
            k1, k2 = addr_key(af, R_OLD, st), addr_key(af, R_NEW, st)
            all_layers += 0
            if u in p7:
                rows_by[u].append((k1, k2))
            elif k1 != k2:
                diff_rows += 1
                diff_layers_non_p7.add(u)
                if k1 and k2:
                    decomp["harm"] += 1
                elif k1 and not k2:
                    decomp["loss"] += 1
                else:
                    decomp["gain"] += 1
                    decomp["gain_ok"] += 1 if key_ok(k2) else 0
    # ng911 兜底给没有坐标样本行的 P7 层
    need = {u for u in p7 if not rows_by.get(u)}
    ng_layer_rows = 0
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
                    af = {k: v for k, v in (s or {}).items() if v not in (None, "", "null")}
                    if af:
                        rows_by[u].append((addr_key(af, R_OLD, ""), addr_key(af, R_NEW, "")))
                        ng_layer_rows += 1

    applied = []
    failed = []
    ok_layers = 0
    for u, m in p7.items():
        rr = rows_by.get(u) or []
        n1 = sum(1 for k1, _ in rr if k1)
        n2 = sum(1 for _, k2 in rr if k2)
        ok2 = sum(1 for _, k2 in rr if key_ok(k2))
        pr = pairs.get(u) or {}
        rec = {"layer_id": m["layer_id"], "url": u, "state": m["state"], "rows_n": m["rows_n"],
               "sample_rows": len(rr), "old_key_rows": n1, "new_key_rows": n2, "new_valid_key_rows": ok2,
               "old_key_share": round(n1 / len(rr), 3) if rr else 0,
               "new_key_share": round(n2 / len(rr), 3) if rr else 0,
               "number_field": pr.get("number_field", ""), "street_field": pr.get("street_field", ""),
               "pair_share": pr.get("pair_share", ""),
               "number_alias_hit": norm(pr.get("number_field", "")) in R_NEW and "number" in R_NEW[norm(pr.get("number_field", ""))],
               "street_alias_hit": norm(pr.get("street_field", "")) in R_NEW and "street" in R_NEW[norm(pr.get("street_field", ""))]}
        applied.append(rec)
        if n2 > 0:
            ok_layers += 1
        else:
            if not rr:
                why = "无坐标样本行且 ng911 无原始记录"
            elif not pr.get("number_field"):
                why = "该层找不出「门牌列+街名列」组合（列名语义不过白名单或值形态不成立）"
            elif not rec["number_alias_hit"] and not rec["street_alias_hit"]:
                why = "选出的门牌/街名列均不在别名表（进了待定表）"
            elif not rec["number_alias_hit"]:
                why = f"门牌列 {pr['number_field']} 不在别名表（待定/语义不明）"
            elif not rec["street_alias_hit"]:
                why = f"街名列 {pr['street_field']} 不在别名表（多为整串地址列，需切分而非别名）"
            else:
                why = "列在别名表但样例行里该列值为空"
            failed.append(dict(rec, reason=why))

    # ---------- 2) 回归 B：ng911 全量层 ----------
    ng_diff_layers, ng_layers, ng_recs = 0, 0, 0
    ng_decomp = {"harm": 0, "loss": 0, "gain": 0}
    with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            u = r.get("url") or ""
            if u in p7:
                continue
            try:
                smp = json.loads(r.get("samples") or "[]")[:3]
            except Exception:
                smp = []
            ng_layers += 1
            hit = False
            for s in smp:
                af = {k: v for k, v in (s or {}).items() if v not in (None, "", "null")}
                if not af:
                    continue
                ng_recs += 1
                k1, k2 = addr_key(af, R_OLD, ""), addr_key(af, R_NEW, "")
                if k1 != k2:
                    hit = True
                    ng_decomp["harm" if (k1 and k2) else ("loss" if k1 else "gain")] += 1
            if hit:
                ng_diff_layers += 1

    with open(os.path.join(HERE, "p7-alias-applied.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(applied[0]))
        w.writeheader()
        w.writerows(applied)
    with open(os.path.join(HERE, "failed-layers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(failed[0]))
        w.writeheader()
        w.writerows(failed)
    with open(os.path.join(HERE, "pending-uncertain.csv"), "w", newline="", encoding="utf-8") as fh:
        if final["pending"]:
            w = csv.DictWriter(fh, fieldnames=list(final["pending"][0]))
            w.writeheader()
            w.writerows(final["pending"])

    out = {"p7_layers": len(p7), "p7_key_ok_layers": ok_layers,
           "p7_key_valid_layers": sum(1 for r in applied if r["new_valid_key_rows"] > 0),
           "p7_failed_layers": len(failed),
           "p7_ng911_fallback_rows": ng_layer_rows,
           "regression_coord_rows_diff_non_p7": diff_rows,
           "regression_coord_layers_diff_non_p7": len(diff_layers_non_p7),
           "regression_coord_diff_layer_sample": sorted(diff_layers_non_p7)[:5],
           "regression_ng911_layers": ng_layers, "regression_ng911_records": ng_recs,
           "regression_ng911_diff_layers": ng_diff_layers,
           "alias_number": len(extra["number"]), "alias_street": len(extra["street"]),
           "regression_decomp_non_p7": decomp,
           "regression_ng911_decomp": ng_decomp,
           "alias_profile": os.environ.get("ALIAS_PROFILE") or "shipped",
           "assert_zero_regression": diff_rows == 0 and ng_diff_layers == 0,
           "assert_no_key_overwrite": decomp["harm"] == 0 and decomp["loss"] == 0 and ng_decomp["harm"] == 0 and ng_decomp["loss"] == 0}
    json.dump(out, open(os.path.join(WORK, "recount.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
