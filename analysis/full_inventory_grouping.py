#!/usr/bin/env python3
"""Phase 1②：用 URL 唯一键重算 20 层校准集分组 → grouping-v2.json（原 grouping.json 不动）。

复算口径（两套都给，不挑一个凑数）：
  · group_first_sample  = rules.layer_profile()[group]（首条样值的组；000201 回执用的口径）
  · group_majority_vote = rules.group_layers()[groups]（全样多数票；F2 修复后 grouping.json 的口径）
class 一律 = rules.layer_profile()[class_mode]（样值众数）。

输入为仓内已冻结的 survey 样值缓存（survey/ng911/samples.csv.gz），**零网络**。
"""
from __future__ import annotations

import collections
import csv
import gzip
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "analysis", "full-inventory-20261124")
CAL = os.path.join(REPO, "analysis", "calib-inventory-20261123")
sys.path.insert(0, os.path.join(REPO, "sandbox"))
import rules  # noqa: E402


def load_survey():
    d = {}
    with gzip.open(os.path.join(REPO, "survey", "ng911", "samples.csv.gz"), "rt",
                   encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                d[r["url"].rstrip("/")] = json.loads(r["samples"])
            except Exception:  # noqa: BLE001
                pass
    return d


def load_rules_at(rev: str):
    """取历史版本的 sandbox/rules.py（用于复现 pre-F1 口径），不落仓库、不覆盖现文件。"""
    src = subprocess.check_output(["git", "-C", REPO, "show", f"{rev}:sandbox/rules.py"])
    fd, path = tempfile.mkstemp(suffix="_rules.py")
    os.write(fd, src)
    os.close(fd)
    spec = importlib.util.spec_from_file_location("rules_at_" + rev, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ng = json.load(open(os.path.join(CAL, "inventory-ng911.json"), encoding="utf-8"))
    survey = load_survey()
    recs, meta = {}, {}
    for r in ng:
        m = re.search(r"url=(\S+)$", r.get("note") or "")
        url = m.group(1).rstrip("/") if m else None
        if not url:
            continue
        smp = survey.get(url) or []
        if not smp:
            continue
        recs[url] = smp
        meta[url] = {"layer": r["layer"], "state": r["state"], "rows": r.get("rows"),
                     "n_fields": r.get("n_fields"), "method": r.get("method"),
                     "sampled_n": len(smp)}

    g_major = rules.group_layers(recs)
    maj = {u: k for k, v in g_major["groups"].items() for u in v}
    per, cls = {}, collections.Counter()
    first_counts = collections.Counter()
    for url, smp in recs.items():
        prof = rules.layer_profile(meta[url]["layer"], smp)
        votes = collections.Counter(rules.field_group(x) for x in smp)
        cls[prof["class_mode"]] += 1
        first_counts[prof["group"]] += 1
        per[url] = {**meta[url], "class": prof["class_mode"], "class_counts": prof["class_counts"],
                    "group_first_sample": prof["group"], "group_majority_vote": maj[url],
                    "vote_counts": dict(votes)}

    # ---- pre-F1 复现（b0a9587 = F1/F2 修复前）----
    old = load_rules_at("b0a9587")
    og = old.group_layers(recs)
    omn = {u: k for k, v in og["groups"].items() for u in v}
    ocls = collections.Counter()
    ofirst = collections.Counter()
    oper = {}
    for url, smp in recs.items():
        prof = old.layer_profile(meta[url]["layer"], smp)
        ocls[prof["class_mode"]] += 1
        ofirst[prof["group"]] += 1
        oper[url] = {"class": prof["class_mode"], "group_first_sample": prof["group"],
                     "group_majority_vote": omn[url]}
    moved = [{"url": u, "before_first_sample": oper[u]["group_first_sample"],
              "after_first_sample": per[u]["group_first_sample"],
              "before_class": oper[u]["class"], "after_class": per[u]["class"],
              "layer": per[u]["layer"], "state": per[u]["state"]}
             for u in per if (oper[u]["class"], oper[u]["group_first_sample"]) !=
             (per[u]["class"], per[u]["group_first_sample"])]

    out = {
        "schema": "grouping-v2/2026-11-24",
        "key": "url",
        "source": "analysis/calib-inventory-20261123/inventory-ng911.json + survey/ng911/samples.csv.gz",
        "denom": len(recs),
        "class_counts": dict(sorted(cls.items())),
        "group_counts_first_sample": dict(sorted(first_counts.items())),
        "group_counts_majority_vote": dict(sorted(g_major["counts"].items())),
        "groups_majority_vote": g_major["groups"],
        "pre_f1_reproduction": {
            "rules_rev": "b0a9587",
            "denom": len(recs),
            "class_counts": dict(sorted(ocls.items())),
            "group_counts_first_sample": dict(sorted(ofirst.items())),
            "group_counts_majority_vote": dict(sorted(og["counts"].items())),
            "layers_moved_by_f1": moved,
        },
        "reproduce_target_000205": {
            "denom": 20, "class_counts": {"A": 9, "B": 3, "C": 7, "S": 1},
            "group_counts": {"full_address": 1, "no_zip": 5, "no_city": 6,
                             "road_only": 4, "empty_shell": 4},
            "which_rule": "group_first_sample（rules.layer_profile().group，首条样值）",
        },
        "layers": per,
    }
    os.makedirs(OUTDIR, exist_ok=True)
    json.dump(out, open(os.path.join(OUTDIR, "grouping-v2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("denom", out["denom"])
    print("class_counts", out["class_counts"])
    print("group_counts_first_sample", out["group_counts_first_sample"])
    print("group_counts_majority_vote", out["group_counts_majority_vote"])
    tgt = out["reproduce_target_000205"]
    pre = out["pre_f1_reproduction"]
    print("pre-F1（b0a9587 规则 + 首样口径）:", pre["class_counts"], pre["group_counts_first_sample"])
    print("复现 muse 给的基线（应指向 pre-F1）:",
          pre["class_counts"] == tgt["class_counts"],
          pre["group_counts_first_sample"] == tgt["group_counts"])
    print("F1 移动的层:", [(m["state"], m["layer"][:28], m["before_class"] + "/" + m["before_first_sample"],
                        "->", m["after_class"] + "/" + m["after_first_sample"]) for m in pre["layers_moved_by_f1"]])
    diff = [(u, per[u]["group_first_sample"], per[u]["group_majority_vote"])
            for u in per if per[u]["group_first_sample"] != per[u]["group_majority_vote"]]
    print("两套口径不一致的层:", [(d[0][-60:], d[1], d[2]) for d in diff])


if __name__ == "__main__":
    sys.exit(main())
