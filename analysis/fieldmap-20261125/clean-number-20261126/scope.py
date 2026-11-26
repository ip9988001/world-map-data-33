#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定范围：把「house_number 命中 ^\\d+\\.0+$」的层做成清单（muse-000275 §1）。

输入：dirty-scan-raw.jsonl（scan_dirty.py 扫 3,413 个已映射层的真实产物）
处理：对每个脏层回放 fm_core 的门牌取值路径，定位是**哪个字段**把 float 带进来的
      （信封 add_num / 强别名 / 弱别名 STR_NUM,CIVIC_NUM / 层级别名 / 组合串拆分）
输出：scope.jsonl（layer / src_field / rows_total / rows_dirty / samples）+ 清单 sha256
只读 dist/intake-full/layers。
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FM = os.path.join(ROOT, "analysis", "fieldmap-20261125")
sys.path.insert(0, FM)
import fm_core as C  # noqa: E402

LAYERS = os.environ.get("INTAKE_LAYERS", "/data/workspace/world-map-data-33/dist/intake-full/layers")
DIRTY_RE = re.compile(r"^\d+\.0+$")
MAX_SCAN = 4000


def first_dirty(lid, url, m):
    """回放门牌路径，返回 (src_field, hv, row_raw, street) 于第一条脏行。"""
    d = os.path.join(LAYERS, lid)
    if not os.path.isdir(d):
        return None
    parts = sorted(f for f in os.listdir(d) if f.startswith("part-u") and f.endswith(".ndjson.gz"))
    m.begin_layer(url, lid)
    seen = 0
    env_dirty = 0
    for fn in parts:
        with gzip.open(os.path.join(d, fn), "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip():
                    continue
                seen += 1
                if seen > MAX_SCAN:
                    return None
                row = json.loads(line)
                raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
                keys = m._keys if m._keys is not None else m._probe_keys(raw)
                hv = None
                src = None
                a = C.clean_number(row.get("add_num"))
                if a:
                    hv, src = a, "add_num(env)"
                if hv is None:
                    for k in keys["number"]:
                        cand = C.clean_number(raw.get(k))
                        if cand:
                            hv, src = cand, k
                            break
                if hv is None:
                    # 组合串拆分（只在本行 street 为空时才走，这里只用于定位）
                    street_env = C.clean_street(row.get("pre_dir"), row.get("st_name"),
                                                row.get("st_suf"), row.get("post_dir"))
                    if not street_env:
                        best = None
                        for k in raw.keys():
                            v = raw.get(k)
                            if not isinstance(v, str) or len(v) < 4 or len(v) > 160:
                                continue
                            r = C.SA.split_number_street(v)
                            if r["reason"] == "ok" and r["street_name"] and r["confidence"] > 0:
                                if best is None or r["confidence"] > best[1]["confidence"]:
                                    best = (k, r)
                        if best:
                            hv, src = C.clean_number(best[1]["house_number"]), "split:" + best[0]
                if hv is None:
                    for k in keys["number_weak"]:
                        cand = C.clean_number(raw.get(k))
                        if cand:
                            hv, src = cand, k
                            break
                if hv is None:
                    for k in keys["number_l"]:
                        cand = C.clean_number(raw.get(k))
                        if cand:
                            hv, src = cand, k
                            break
                if hv and DIRTY_RE.match(hv):
                    rec, _r, _f = m.map_row(row)
                    return (src, hv, row.get("raw") or {}, (rec or {}).get("street_name"))
                if hv and src == "add_num(env)":
                    env_dirty += 1
        if seen >= MAX_SCAN:
            return None
    return None


def main():
    rows = [json.loads(l) for l in open(os.path.join(HERE, "dirty-scan-raw.jsonl"), encoding="utf-8")]
    dirty = [r for r in rows if r["rows_dirty"] > 0]
    dirty.sort(key=lambda r: r["layer"])
    cfg = C.load_pilot_cfg()
    o2d, meta, _fb = C.load_registry_orgs()
    m = C.LayerMapper(cfg, o2d, meta, C.load_tier_map())
    inv = {}
    p = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
    import csv
    for r in csv.DictReader(open(p, encoding="utf-8")):
        inv.setdefault(r["layer"], r.get("url") or "")
    out, nosrc = [], []
    for r in dirty:
        lid = r["layer"]
        got = first_dirty(lid, inv.get(lid, ""), m)
        src = got[0] if got else ""
        if not got:
            nosrc.append(lid)
        out.append({
            "layer": lid,
            "src_field": src,
            "rows_total": r["rows_total"],
            "rows_dirty": r["rows_dirty"],
            "samples": r["samples"],
        })
        print(f"{lid[:56]:56s} {r['rows_dirty']:>9,}/{r['rows_total']:>9,} src={src}", flush=True)
    p = os.path.join(HERE, "scope.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        for o in out:
            fh.write(json.dumps(o, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    tot_dirty = sum(o["rows_dirty"] for o in out)
    tot_rows = sum(o["rows_total"] for o in out)
    meta_out = {"layers": len(out), "rows_dirty": tot_dirty, "rows_total_in_scope": tot_rows,
                "scope_sha256": sha, "scope_sha256_16": sha[:16],
                "layers_scanned": len(rows), "rows_scanned": sum(r["rows_total"] for r in rows),
                "no_src_field": nosrc}
    json.dump(meta_out, open(os.path.join(HERE, "scope-meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(meta_out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
