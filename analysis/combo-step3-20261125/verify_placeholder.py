#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳③ 验收 6：addr_key 加「占位缺失值跳过」后，三件事逐条实测。

口径：
  k1 = 基线 registry（PR #54 之前）别名 + 老 addr_key（sandbox 版，不跳占位）
  k2 = 现 registry（27 条别名）  + 老 addr_key          ← 组合拳② 的现状（772 行 questionable 就出在这）
  k3 = 现 registry（27 条别名）  + engine/split_addr.addr_key（**占位跳过**，本轮改动）

产物（analysis/combo-step3-20261125/ 根下）：
  p7-rebuild-after.csv   321 层：k2 / k3 建键层数与行数（验「不许从 83 往下掉」）
  placeholder-fix.csv    772 行 questionable 逐行处置（before → after 标签 + 迁移类型）
  _work/placeholder.json 汇总断言
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import json
import os
import re
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from engine.split_addr import addr_key as addr_key_new, is_placeholder  # noqa: E402
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "step2_verify", os.path.join(ROOT, "analysis", "combo-step2-close-20261125", "verify.py"))
STEP2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(STEP2)          # 只借 addr_key_dbg / label_change / roles_from（判据同源）

STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
REGISTRY = os.path.join(ROOT, "registry", "dialects.v1.yaml")
C2 = os.path.join(ROOT, "analysis", "combo-step2-close-20261125", "old-key-changes.csv")
OLD_MAIN = "a259aa8be40257e43d896e4bac5a6d8308ae87a3"
WORK = os.path.join(HERE, "_work")

SUFFIX = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
          "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "hwy": "highway",
          "pkwy": "parkway", "cir": "circle", "ter": "terrace", "trl": "trail"}
NUM_RE, ZIP_RE = re.compile(r"^\s*(\d+)\s*[A-Za-z]?\s+(.*)$"), re.compile(r"\b(\d{5})\b")
PURE_HN = re.compile(r"^\d{1,6}[A-Za-z]?(-[0-9A-Za-z]{1,4})?$")
norm = lambda f: re.sub(r"[^a-z0-9]", "", (f or "").lower())
FULLISH = re.compile(r"(fulladdr|fulladdress|address1|addressline|streetaddress|siteaddr|prcladdr|"
                     r"propertyaddress|mailaddr|mailadr|ownaddr|combined|^addr$|^address\d*$)")


def street_norm(s):
    w = [SUFFIX.get(x, x) for x in re.findall(r"[a-z0-9]+", (s or "").lower())]
    return "".join(w)


def _unused_addr_key_old(af, ROLES, state):
    """逐字照抄 sandbox/coord_evidence.py:addr_key（不跳占位），并返回贡献列。"""
    n = s = z = ""
    nf = sf = ""
    for k, v in af.items():
        v = str(v).strip() if isinstance(v, (int, float, str)) else ""
        r = ROLES.get(norm(k)) or ()
        if v and "number" in r and not n:
            n, nf = re.sub(r"[^0-9A-Za-z-]", "", v), k
        elif v and "street" in r and not s:
            s, sf = v, k
        elif v and "zip" in r and not z:
            z = (ZIP_RE.search(v) or [None, ""])[1]
    if not (n and s):
        for k, v in af.items():
            v = v if isinstance(v, str) else ""
            m = NUM_RE.match(v.split(",")[0]) if "," in v else None
            if m and ZIP_RE.search(v):
                n, s, z = m.group(1), m.group(2), ZIP_RE.search(v).group(1)
                nf = sf = ""
                break
    return (f"{state}|{n}|{street_norm(s)}|{z}" if (n and s) else ""), nf, sf, s


def key_ok(key):
    p = key.split("|")
    return len(p) == 4 and bool(PURE_HN.match(p[1])) and bool(re.search(r"[a-z]", p[2]))


def roles_from_(text):
    out = collections.defaultdict(set)
    for d in yaml.safe_load(text)["dialects"]:
        t = d.get("template") or {}
        for role, key in (("number", "number_aliases"), ("street", "street_aliases"), ("zip", "zip_aliases")):
            for a in t.get(key) or []:
                out[norm(a)].add(role)
    return out


def _unused_label_change(k1, k2, sf1, sf2, sv1, sv2):
    """与 analysis/combo-step2-close-20261125/verify.py 完全同一套判据（复算要对得上）。"""
    old_valid, new_valid = key_ok(k1), key_ok(k2)
    old_tok = len(re.findall(r"[A-Za-z]+", sv1 or ""))
    new_tok = len(re.findall(r"[A-Za-z]+", sv2 or ""))
    if not new_valid:
        return "questionable"
    o_n = k1.split("|")[1] if k1 else ""
    n_n = k2.split("|")[1] if k2 else ""
    if not PURE_HN.match(o_n or "-") and PURE_HN.match(n_n):
        return "improved"
    if new_sv_full(k2, sv2):
        return "questionable"
    if not old_valid:
        return "improved"
    if not sf1:
        return "improved" if new_tok >= old_tok else "questionable"
    if FULLISH.search(norm(sf1)) and not FULLISH.search(norm(sf2)):
        return "improved"
    if new_tok < old_tok:
        return "questionable"
    return "improved"


def new_sv_full(k, sv):
    return bool(sv) and (re.match(r"^\s*\d", sv) or ZIP_RE.search(sv) or "," in sv)


def addr_key_new_dbg(af, ROLES, state):
    """engine addr_key 的同判据 dbg 版：返回 (key, 街名列, 街名原值)。"""
    n = s = z = ""
    sf = sv = ""
    for k, v in af.items():
        if is_placeholder(v):
            continue
        v = str(v).strip()
        r = ROLES.get(norm(k)) or ()
        if not n and "number" in r:
            n = re.sub(r"[^0-9A-Za-z-]", "", v)
        elif not s and "street" in r:
            s, sf, sv = v, k, v
        elif not z and "zip" in r:
            m = ZIP_RE.search(v)
            if m:
                z = m.group(1)
    if not (n and s):
        for k, v in af.items():
            if is_placeholder(v) or not isinstance(v, str) or "," not in v:
                continue
            m = NUM_RE.match(v.split(",")[0])
            mz = ZIP_RE.search(v)
            if m and mz:
                return f"{state}|{m.group(1)}|{street_norm(m.group(2))}|{mz.group(1)}", "", m.group(2)
        return "", "", ""
    return f"{state}|{n}|{street_norm(s)}|{z}", sf, sv


def main():
    os.makedirs(WORK, exist_ok=True)
    old_yaml = subprocess.run(["git", "show", f"{OLD_MAIN}:registry/dialects.v1.yaml"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout
    R1 = STEP2.roles_from(old_yaml)
    R2 = STEP2.roles_from(open(REGISTRY, encoding="utf-8").read())

    p7 = {r["url"]: r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"}

    # 逐行计算 k1/k2/k3
    p7stat = collections.defaultdict(lambda: [0, 0, 0])          # url → [rows, k2_keys, k3_keys]
    nonp7 = {"loss": 0, "harm": 0, "gain": 0}
    # loss 拆两类：k1 本身形态合法（真丢键，必须 0）/ k1 是占位值拼出来的垃圾键（本轮有意剔除）
    harm_rows = []                                                # 非 P7 的 harm 行（用于复算 772）
    for f in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            u = r.get("layer_url") or ""
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                af = {}
            if not af:
                continue
            st = r.get("state") or ""
            k1, nf1, sf1, sv1, nv1 = STEP2.addr_key_dbg(af, R1, st)
            k2, nf2, sf2, sv2, nv2 = STEP2.addr_key_dbg(af, R2, st)
            k3, sf3, sv3 = addr_key_new_dbg(af, R2, st)
            if u in p7:
                e = p7stat[u]
                e[0] += 1
                e[1] += 1 if k2 else 0
                e[2] += 1 if k3 else 0
            else:
                if k1 and not k3:
                    if STEP2.key_form_ok(k1) and not (is_placeholder(nv1) or is_placeholder(sv1)):
                        nonp7["loss"] += 1
                    else:
                        nonp7["loss_placeholder_only"] = nonp7.get("loss_placeholder_only", 0) + 1
                elif k1 and k2 and k1 != k2:
                    nonp7["harm"] += 1
                    harm_rows.append({"url": u, "layer_id": r.get("layer_id") or "", "state": st,
                                      "k1": k1, "k2": k2, "k3": k3,
                                      "sf1": sf1, "sf2": sf2, "sf3": sf3,
                                      "sv1": (sv1 or "")[:60], "sv2": (sv2 or "")[:60],
                                      "sv3": (sv3 or "")[:60], "nv1": nv1, "nv2": nv2,
                                      "k1_valid": STEP2.key_form_ok(k1)})
                elif not k1 and k3:
                    nonp7["gain"] += 1

    # P7 321 层（k2 = 组合拳② 现状 83 层；k3 = 本轮）
    out = []
    for u, m in p7.items():
        rows_n, k2n, k3n = p7stat.get(u, [0, 0, 0])
        out.append({"layer_id": m["layer_id"], "url": u, "state": m["state"], "rows_n": m["rows_n"],
                    "sample_rows": rows_n, "built_before_c3_rows": k2n, "built_after_c3_rows": k3n,
                    "built_before": "yes" if k2n else "no", "built_after": "yes" if k3n else "no"})
    with open(os.path.join(HERE, "p7-rebuild-after.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    # 772 行 questionable 逐行处置（先复算，再用 k3 复判）
    committed = list(csv.DictReader(open(C2, encoding="utf-8")))
    q_committed = [c for c in committed if c["label"] == "questionable"]
    recon = [h for h in harm_rows
             if STEP2.label_change(h["k1"], h["k2"], h["sf1"], h["sf2"], h["sv1"], h["sv2"])[0] == "questionable"]
    fix = []
    trans = collections.Counter()
    for h in recon:
        before = "questionable"
        after = STEP2.label_change(h["k1"], h["k3"], h["sf1"], h["sf3"], h["sv1"], h["sv3"])[0] \
            if h["k3"] else "worse"
        if not h["k3"]:
            t = "worse(key_lost)"
        elif after == "questionable":
            t = "still_questionable"
        else:
            t = "improved" if h["k3"] != h["k2"] else "unchanged_label_improved"
        trans[t] += 1
        fix.append({"layer_id": h["layer_id"], "url": h["url"], "state": h["state"],
                    "key_before_c3": h["k2"], "key_after_c3": h["k3"],
                    "baseline_key": h["k1"], "label_before": before, "label_after": after,
                    "transition": t})
    with open(os.path.join(HERE, "placeholder-fix.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fix[0]) if fix else
                           ["layer_id", "url", "state", "key_before_c3", "key_after_c3", "baseline_key",
                            "label_before", "label_after", "transition"])
        w.writeheader()
        w.writerows(fix)

    summary = {
        "p7_layers": len(out),
        "p7_built_before_c3": sum(1 for r in out if r["built_before"] == "yes"),
        "p7_built_after_c3": sum(1 for r in out if r["built_after"] == "yes"),
        "p7_key_rows_before_c3": sum(r["built_before_c3_rows"] for r in out),
        "p7_key_rows_after_c3": sum(r["built_after_c3_rows"] for r in out),
        "non_p7_loss": nonp7["loss"],
        "non_p7_loss_valid_key": nonp7["loss"],
        "non_p7_loss_placeholder_key": nonp7.get("loss_placeholder_only", 0), "non_p7_harm": nonp7["harm"], "non_p7_gain": nonp7["gain"],
        "questionable_committed_rows": len(q_committed),
        "questionable_recomputed_rows": len(recon),
        "recompute_matches_committed": len(recon) == len(q_committed),
        "old_label_breakdown": dict(collections.Counter(
            STEP2.label_change(h["k1"], h["k2"], h["sf1"], h["sf2"], h["sv1"], h["sv2"])[0]
            for h in harm_rows)),
        "transitions": dict(trans),
        "assert_p7_not_dropped": sum(1 for r in out if r["built_after"] == "yes") >= 83,
        "assert_loss_zero": nonp7["loss"] == 0,
    }
    json.dump(summary, open(os.path.join(WORK, "placeholder.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
