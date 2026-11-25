#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""step1：复算「构不出门牌+街名键」的层集合（= 派单说的 1,340 层），并落 patterns 输入的层清单。

复算口径完全照搬 sandbox/coord_evidence.py 的 addr_key()（registry 别名 + 「首段门牌 + 含 zip」兜底），
再加 sandbox/tier_relax.py 的归因过滤条件。只读，不改任何代码。

用法：python3 combo_list.py
产物：_work/target_layers.csv（url / layer_id / rows_n / state / sample_rows / n_addr_rows）
      _work/recount.json（复算口径 + 数字自证）
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import os
import re
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RELAX = os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125")
SAMPLES = os.environ.get("COORD_SAMPLES") or os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")

NUM_RE = re.compile(r"^\s*(\d+)\s*[A-Za-z]?\s+(.*)$")
ZIP_RE = re.compile(r"\b(\d{5})\b")
SUFFIX = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
          "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "hwy": "highway",
          "pkwy": "parkway", "cir": "circle", "ter": "terrace", "trl": "trail"}


def norm(f):
    return re.sub(r"[^a-z0-9]", "", (f or "").lower())


def street_norm(s):
    return "".join(SUFFIX.get(x, x) for x in re.findall(r"[a-z0-9]+", (s or "").lower()))


def roles_of():
    out = collections.defaultdict(set)
    doc = yaml.safe_load(open(os.path.join(ROOT, "registry", "dialects.v1.yaml"), encoding="utf-8"))
    for d in doc["dialects"]:
        for role in ("number", "street", "zip"):
            for a in (d.get("template") or {}).get(role + "_aliases") or []:
                out[norm(a)].add(role)
    return out


def addr_key(af, ROLES, state):
    """与 sandbox/coord_evidence.py:addr_key 逐字一致（照抄，未修改原文件）。"""
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


def main():
    ROLES = roles_of()
    n_rows = collections.Counter()      # url -> 有键行数（= coord_evidence 的 n_addr_rows）
    s_rows = collections.Counter()      # url -> 样本行数
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r["layer_url"] or f"local:{r['layer_id']}"
            s_rows[u] += 1
            af = json.loads(r["addr_fields_json"] or "{}")
            if addr_key(af, ROLES, r["state"]):
                n_rows[u] += 1

    # ---- tier_relax 的归因过滤：rest 全 clear/na 且 E3 na/clear 且 E7 unknown 且未进 tier1
    recs = list(csv.DictReader(open(os.path.join(RELAX, "auto-recognized.csv"), encoding="utf-8")))
    EKEYS = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"]
    hyp = []
    for r in recs:
        st = {k: r[f"{k}_state"] for k in EKEYS}
        rest = {k: v for k, v in st.items() if k not in ("E3", "E7")}
        if any(v not in ("clear", "na") for v in rest.values()):
            continue
        if r["e3_relax_state"] in ("na", "clear") and st["E7"] == "unknown":
            hyp.append(r)
    no_sample = zero_key = 0
    target = []
    for r in hyp:
        u = r["url"]
        if u not in s_rows:                      # 无坐标样本
            no_sample += 1
            continue
        if r["tier"] == "tier1":
            continue
        if n_rows[u] == 0:
            zero_key += 1
            target.append({
                "url": u, "layer_id": r["layer_id"], "rows_n": r["rows_n"], "state": r["state"],
                "sample_rows": s_rows[u], "n_addr_rows": n_rows[u],
                "dialect_id": r["dialect_id"], "provider": r["provider"],
                "granularity": r["granularity"], "geom_type": r["geom_type"],
                "assign_reason": r["assign_reason"],
            })
    os.makedirs(os.path.join(HERE, "_work"), exist_ok=True)
    with open(os.path.join(HERE, "_work", "target_layers.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(target[0]))
        w.writeheader()
        w.writerows(target)
    meta = {
        "recount": {
            "hypothetical_pool(E3 na/clear + E7 unknown + rest clear/na)": len(hyp),
            "minus_no_coord_sample": no_sample,
            "minus_already_tier1": len(hyp) - no_sample - zero_key,
            "target_zero_key_layers": zero_key,
        },
        "matches_1340": zero_key == 1340,
        "rows_n_sum": sum(int(t["rows_n"]) for t in target),
        "sample_rows_sum": sum(t["sample_rows"] for t in target),
        "inputs": {
            "coord_samples": SAMPLES,
            "n_sample_csv": len(glob.glob(os.path.join(SAMPLES, "*.csv"))),
            "registry": os.path.join(ROOT, "registry", "dialects.v1.yaml"),
            "relax_auto_recognized": os.path.join(RELAX, "auto-recognized.csv"),
        },
    }
    json.dump(meta, open(os.path.join(HERE, "_work", "recount.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
