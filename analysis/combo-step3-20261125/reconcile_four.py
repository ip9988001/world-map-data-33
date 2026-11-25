#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四数对账（Muse 点名）：1,268 / 1,066 / 982 / +1,784 各自的口径与实算。

全部用 PR #53 的**代码即产物**复算，不估、不猜：
  · 1,268 = 组合拳②「严格口径（19 条别名）下，非 P7 coord 行的纯增益行数」（旧键空 → 新键非空）
  · 1,066 = 同口径下 P7 321 层「出键行数」合计（样本行 15,293 行里的 1,066）
  ·   982 = 同口径下 P7 321 层「键形合法行数」合计
  · +1,784 = PR #53 的 git 增行数（git diff --numstat 汇总）

复现材料：registry@a2e3c88（PR #52 merge，组合拳② 的基线）+ engine/dialects/sources.v1.yaml@ebe6a14（19 条别名）。
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
STEP1 = os.path.join(ROOT, "analysis", "combo-step1-20261125")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
WORK = os.path.join(HERE, "_work")

BASE2 = "a2e3c887294008b7227fb14bb7b5d0e32bc86a83"   # PR #52 merge（组合拳② 基线）
HEAD2 = "ebe6a14322a739a977418c443ff9b76f37335916"   # PR #53 head

SUFFIX = {"st": "street", "ave": "avenue", "av": "avenue", "rd": "road", "blvd": "boulevard",
          "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "hwy": "highway",
          "pkwy": "parkway", "cir": "circle", "ter": "terrace", "trl": "trail"}
NUM_RE, ZIP_RE = re.compile(r"^\s*(\d+)\s*[A-Za-z]?\s+(.*)$"), re.compile(r"\b(\d{5})\b")
PURE_HN = re.compile(r"^\d{1,6}[A-Za-z]?(-[0-9A-Za-z]{1,4})?$")
norm = lambda f: re.sub(r"[^a-z0-9]", "", (f or "").lower())


def street_norm(s):
    w = [SUFFIX.get(x, x) for x in re.findall(r"[a-z0-9]+", (s or "").lower())]
    return "".join(w)


def addr_key(af, ROLES, state):
    """逐字照抄 PR #53 用的 sandbox/coord_evidence.py:addr_key（判据不许变）。"""
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


def key_ok(key):
    p = key.split("|")
    return len(p) == 4 and bool(PURE_HN.match(p[1])) and bool(re.search(r"[a-z]", p[2]))


def roles_from(text):
    out = collections.defaultdict(set)
    for d in yaml.safe_load(text)["dialects"]:
        t = d.get("template") or {}
        for role, key in (("number", "number_aliases"), ("street", "street_aliases"), ("zip", "zip_aliases")):
            for a in t.get(key) or []:
                out[norm(a)].add(role)
    return out


def git_show(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT,
                          capture_output=True, text=True, check=True).stdout


def main():
    os.makedirs(WORK, exist_ok=True)
    R_OLD = roles_from(git_show(BASE2, "registry/dialects.v1.yaml"))
    engine_doc = yaml.safe_load(git_show(HEAD2, "engine/dialects/sources.v1.yaml"))
    ext = [d for d in engine_doc["dialects"] if d.get("id") == "p7-alias-ext-v1"][0]
    R_NEW = collections.defaultdict(set)
    for k, v in R_OLD.items():
        R_NEW[k] |= v
    for a in ext["fields"]["number"]:
        R_NEW[norm(a)].add("number")
    for a in ext["fields"]["street"]:
        R_NEW[norm(a)].add("street")

    p7 = {r["url"]: r for r in csv.DictReader(open(os.path.join(STEP1, "patterns.csv"), encoding="utf-8"))
          if r["pattern_id"] == "P7"}

    gain_rows = 0
    p7rows = collections.defaultdict(list)
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
            k1, k2 = addr_key(af, R_OLD, st), addr_key(af, R_NEW, st)
            if u in p7:
                p7rows[u].append((k1, k2))
            elif not k1 and k2:
                gain_rows += 1
    # ng911 兜底（P7 里没有 coord 行的层；上一轮同口径也这么做）
    need = {u for u in p7 if not p7rows.get(u)}
    if need:
        with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                u = r.get("url") or ""
                if u not in need:
                    continue
                for s in (json.loads(r.get("samples") or "[]")[:3]):
                    af = {k: v for k, v in (s or {}).items() if v not in (None, "", "null")}
                    if af:
                        p7rows[u].append((addr_key(af, R_OLD, ""), addr_key(af, R_NEW, "")))

    key_rows = sum(1 for u in p7 for _, k2 in p7rows.get(u, []) if k2)
    valid_rows = sum(1 for u in p7 for _, k2 in p7rows.get(u, []) if key_ok(k2))
    built = sum(1 for u in p7 if any(k2 for _, k2 in p7rows.get(u, [])))
    sample_rows = sum(len(p7rows.get(u, [])) for u in p7)

    numstat = subprocess.run(["git", "diff", "--numstat", BASE2, HEAD2, "--"],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
    adds = dels = 0
    for line in numstat.strip().splitlines():
        a, d, _ = line.split("\t", 2)
        adds += int(a) if a.isdigit() else 0
        dels += int(d) if d.isdigit() else 0

    out = {
        "1268_gain_rows_non_p7": gain_rows,
        "1066_p7_key_rows": key_rows,
        "982_p7_valid_key_rows": valid_rows,
        "1784_pr53_added_lines": adds,
        "pr53_deleted_lines": dels,
        "p7_sample_rows": sample_rows,
        "p7_layers_with_key": built,
        "recorded": {"gain_1268": 1268, "key_rows_1066": 1066, "valid_982": 982, "added_1784": 1784},
        "match": {"1268": gain_rows == 1268, "1066": key_rows == 1066,
                  "982": valid_rows == 982, "1784": adds == 1784},
    }
    json.dump(out, open(os.path.join(WORK, "four_numbers.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
