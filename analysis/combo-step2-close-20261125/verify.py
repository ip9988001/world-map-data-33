#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② 收尾验收：registry 吃到 27 条别名后的三件事，全本地可复算。

a) P7 的 321 层逐层重跑 addr_key()（ROLES 只从 registry/dialects.v1.yaml 取，证明 E7 真吃到）
b) 非 P7 层：键丢失必须 = 0（范围沿用上一轮：coord-samples 非 P7 695,706 行 + ng911 60,373 层）
c) 旧键被改的层逐层列出改前改后，按 Muse 新口径逐行判 improved / questionable

产物（analysis/combo-step2-close-20261125/ 根下）：
  p7-rebuild.csv        321 层逐层建键结果
  regression-nonP7.csv  非 P7 层逐层改动汇总（harm/loss/gain + 标签）
  old-key-changes.csv   每一处「旧键 → 新键」的行级对照（层 + 旧新键 + 贡献列 + 标签）
  _work/summary.json    汇总断言值
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

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
REGISTRY = os.path.join(ROOT, "registry", "dialects.v1.yaml")
BASELINE = "a259aa8be40257e43d896e4bac5a6d8308ae87a3"
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


def addr_key_dbg(af, ROLES, state):
    """与 sandbox/coord_evidence.py:addr_key 同一判据，额外返回贡献列（审计用）。"""
    n = s = z = ""
    nf = sf = zf = ""
    for k, v in af.items():
        v = str(v).strip() if isinstance(v, (int, float, str)) else ""
        r = ROLES.get(norm(k)) or ()
        if v and "number" in r and not n:
            n, nf = re.sub(r"[^0-9A-Za-z-]", "", v), k
        elif v and "street" in r and not s:
            s, sf = v, k
        elif v and "zip" in r and not z:
            z, zf = (ZIP_RE.search(v) or [None, ""])[1], k
    if not (n and s):
        for k, v in af.items():
            v = v if isinstance(v, str) else ""
            m = NUM_RE.match(v.split(",")[0]) if "," in v else None
            if m and ZIP_RE.search(v):
                n, s, z = m.group(1), m.group(2), ZIP_RE.search(v).group(1)
                nf, sf, zf = "", "", ""
                break
    key = f"{state}|{n}|{street_norm(s)}|{z}" if (n and s) else ""
    return key, nf, sf, s, n


def key_form_ok(key):
    p = key.split("|")
    return len(p) == 4 and bool(PURE_HN.match(p[1])) and bool(re.search(r"[a-z]", p[2]))


def roles_from(yaml_text):
    out = collections.defaultdict(set)
    for d in yaml.safe_load(yaml_text)["dialects"]:
        t = d.get("template") or {}
        for role, key in (("number", "number_aliases"), ("street", "street_aliases"), ("zip", "zip_aliases")):
            for a in t.get(key) or []:
                out[norm(a)].add(role)
    return out


def label_change(old_key, new_key, old_sf, new_sf, old_sval, new_sval):
    """Muse 新口径：同语义更完整列名替换 = improved；否则 questionable（不许放宽）。

    判据只用键本身 + 贡献列 + 街名原值，不看「层是不是 P7」：
      1) 新键形态不合法 → questionable
      2) 新街名原值以数字开头 / 含 5 位邮编 / 含逗号 → 那是整串地址列，不是街名列 → questionable
      3) 旧键来自「整串地址兜底解析」（old_sf 为空）且新街名词数更少 → questionable（缺 type 后缀，要拼列才等价）
      4) 旧街名取自整串/组合列（FULLISH）而新取自专用街名列 → improved
      5) 新街名词数 >= 旧 → 同语义（更完整或等价）→ improved
    """
    old_valid, new_valid = key_form_ok(old_key), key_form_ok(new_key)
    old_tok = len(re.findall(r"[A-Za-z]+", old_sval or ""))
    new_tok = len(re.findall(r"[A-Za-z]+", new_sval or ""))
    if not new_valid:
        return "questionable", f"新键形态不合法（门牌/街名不是干净地址）：{new_key}"
    old_n = old_key.split("|")[1] if old_key else ""
    new_n = new_key.split("|")[1] if new_key else ""
    if not PURE_HN.match(old_n or "-") and PURE_HN.match(new_n):   # 旧键门牌本身是整串垃圾 → 必然改善
        return "improved", f"旧键门牌段不是纯门牌（{old_n[:30]}），新键为纯门牌（{new_n}）"
    if new_sval and (re.match(r"^\s*\d", new_sval) or ZIP_RE.search(new_sval) or "," in new_sval):
        return "questionable", f"新街名列 {new_sf} 的值是整串地址（{new_sval[:40]}），不是纯街名"
    if not old_valid:
        return "improved", "旧键形态不合法（门牌/街名含垃圾），新键合法"
    if not old_sf:                                    # 旧键来自「首段门牌 + 含 zip」兜底解析
        if new_tok < old_tok:
            return "questionable", (f"旧键由整串地址兜底解析得到（含 type），新键只取街名列 {new_sf}"
                                    f"（{old_tok}→{new_tok} 词），要拼 type 后缀才等价")
        return "improved", f"旧键由整串地址兜底解析，新键改用专用街名列 {new_sf}"
    if FULLISH.search(norm(old_sf)) and not FULLISH.search(norm(new_sf)):
        return "improved", f"旧街名取自整串地址列 {old_sf}，新取专用街名列 {new_sf}"
    if new_tok < old_tok:
        return "questionable", (f"新街名更短（{old_tok}→{new_tok} 词）：{old_sf}={old_sval} → "
                                f"{new_sf}={new_sval}")
    if new_tok > old_tok:
        return "improved", f"新街名更完整（{old_tok}→{new_tok} 词）：{old_sf} → {new_sf}"
    return "improved", f"同词数、同为干净地址列：{old_sf} → {new_sf}（同语义替换）"


def main():
    os.makedirs(WORK, exist_ok=True)
    old_yaml = subprocess.run(["git", "show", f"{BASELINE}:registry/dialects.v1.yaml"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout
    R_OLD = roles_from(old_yaml)
    R_NEW = roles_from(open(REGISTRY, encoding="utf-8").read())

    p7 = {r["url"]: r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"}
    assert len(p7) == 321
    pairs = {}
    pp = os.path.join(ROOT, "analysis", "combo-step2-20261125", "_work", "p7_pairs.csv")
    if os.path.exists(pp):
        pairs = {r["url"]: r for r in csv.DictReader(open(pp, encoding="utf-8"))}

    p7rows = collections.defaultdict(list)
    non_p7 = []
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
            k1, nf1, sf1, sv1, nv1 = addr_key_dbg(af, R_OLD, st)
            k2, nf2, sf2, sv2, nv2 = addr_key_dbg(af, R_NEW, st)
            if u in p7:
                p7rows[u].append((k1, k2))
            else:
                non_p7.append((u, r.get("layer_id") or "", st, k1, k2, nf1, nf2, sf1, sf2, sv1, sv2))

    # ---- a) P7 321 层 ----
    out_a, ok = [], 0
    for u, m in p7.items():
        rr = p7rows.get(u) or []
        n1 = sum(1 for k1, _ in rr if k1)
        n2 = sum(1 for _, k2 in rr if k2)
        v2 = sum(1 for _, k2 in rr if key_form_ok(k2))
        rec = {"layer_id": m["layer_id"], "url": u, "state": m["state"], "rows_n": m["rows_n"],
               "sample_rows": len(rr), "old_key_rows": n1, "new_key_rows": n2, "new_valid_key_rows": v2,
               "number_field": (pairs.get(u) or {}).get("number_field", ""),
               "street_field": (pairs.get(u) or {}).get("street_field", ""),
               "built": "yes" if n2 else "no", "reason": ""}
        if not n2:
            rec["reason"] = ("无样本行" if not rr else
                             "该层门牌/街名列不在 27 条别名（整串地址列或语义不明，需切分/待定）")
        else:
            ok += 1
        out_a.append(rec)

    # ---- b/c) 非 P7 回归 ----
    agg = collections.defaultdict(lambda: {"layer_id": "", "state": "", "rows": 0, "harm": 0, "loss": 0,
                                           "gain": 0, "gain_ok": 0, "changes": []})
    changes = []
    for u, lid, st, k1, k2, nf1, nf2, sf1, sf2, sv1, sv2 in non_p7:
        a = agg[u]
        a["layer_id"], a["state"], a["rows"] = lid, st, a["rows"] + 1
        if k1 and k2 and k1 != k2:
            a["harm"] += 1
            lab, why = label_change(k1, k2, sf1, sf2, sv1, sv2)
            a["changes"].append(lab)
            changes.append({"layer_id": lid, "url": u, "state": st, "change_type": "harm",
                            "old_key": k1, "new_key": k2,
                            "old_number_field": nf1, "new_number_field": nf2,
                            "old_street_field": sf1, "new_street_field": sf2,
                            "old_street_value": (sv1 or "")[:60], "new_street_value": (sv2 or "")[:60],
                            "label": lab, "reason": why})
        elif k1 and not k2:
            a["loss"] += 1
            changes.append({"layer_id": lid, "url": u, "state": st, "change_type": "loss",
                            "old_key": k1, "new_key": "", "old_number_field": nf1, "new_number_field": nf2,
                            "old_street_field": sf1, "new_street_field": sf2,
                            "old_street_value": (sv1 or "")[:60], "new_street_value": "",
                            "label": "loss", "reason": "键丢失（越界红线）"})
        elif not k1 and k2:
            a["gain"] += 1
            a["gain_ok"] += 1 if key_form_ok(k2) else 0

    rows_b = []
    for u, a in agg.items():
        lab = ("no_change" if not (a["harm"] or a["loss"] or a["gain"]) else
               ("loss" if a["loss"] else
                ("questionable" if "questionable" in a["changes"] else
                 ("improved" if a["harm"] else "gain_only"))))
        rows_b.append({"layer_id": a["layer_id"], "url": u, "state": a["state"], "sample_rows": a["rows"],
                       "harm_rows": a["harm"], "loss_rows": a["loss"], "gain_rows": a["gain"],
                       "gain_form_valid": a["gain_ok"], "label": lab})

    # ---- ng911 全量层（只看丢失）----
    ng_layers = ng_recs = ng_loss = ng_harm = ng_gain = 0
    with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            u = r.get("url") or ""
            if u in p7:
                continue
            ng_layers += 1
            try:
                smp = json.loads(r.get("samples") or "[]")[:3]
            except Exception:
                smp = []
            for s in smp:
                af = {k: v for k, v in (s or {}).items() if v not in (None, "", "null")}
                if not af:
                    continue
                ng_recs += 1
                k1 = addr_key_dbg(af, R_OLD, "")[0]
                k2 = addr_key_dbg(af, R_NEW, "")[0]
                if k1 and not k2:
                    ng_loss += 1
                elif k1 and k2 and k1 != k2:
                    ng_harm += 1
                elif not k1 and k2:
                    ng_gain += 1

    def dump(name, rows, fields=None):
        fields = fields or list(rows[0])
        with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    dump("p7-rebuild.csv", out_a)
    dump("regression-nonP7.csv", rows_b)
    dump("old-key-changes.csv", changes)

    summary = {
        "baseline_sha": BASELINE,
        "registry_dialects": len(yaml.safe_load(open(REGISTRY, encoding="utf-8"))["dialects"]),
        "p7_layers": len(p7), "p7_built": ok, "p7_built_pct": round(ok / len(p7), 4),
        "p7_sample_rows": sum(r["sample_rows"] for r in out_a),
        "p7_key_rows": sum(r["new_key_rows"] for r in out_a),
        "p7_valid_key_rows": sum(r["new_valid_key_rows"] for r in out_a),
        "non_p7_rows": len(non_p7),
        "non_p7_layers": len(agg),
        "non_p7_loss_rows": sum(a["loss"] for a in agg.values()),
        "non_p7_harm_rows": sum(a["harm"] for a in agg.values()),
        "non_p7_gain_rows": sum(a["gain"] for a in agg.values()),
        "harm_layers": sum(1 for a in agg.values() if a["harm"]),
        "harm_layers_improved": sum(1 for r in rows_b if r["label"] == "improved"),
        "harm_layers_questionable": sum(1 for r in rows_b if r["label"] == "questionable"),
        "changes_improved": sum(1 for c in changes if c["label"] == "improved"),
        "changes_questionable": sum(1 for c in changes if c["label"] == "questionable"),
        "changes_loss": sum(1 for c in changes if c["label"] == "loss"),
        "ng911_layers": ng_layers, "ng911_records": ng_recs,
        "ng911_loss": ng_loss, "ng911_harm": ng_harm, "ng911_gain": ng_gain,
        "assert_p7_83": ok == 83,
        "assert_loss_zero": sum(a["loss"] for a in agg.values()) == 0 and ng_loss == 0,
    }
    json.dump(summary, open(os.path.join(WORK, "summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
