#!/usr/bin/env python3
"""构建第 6 步逐层清单 layers.json（分母必须闭合 17,168）。

来源（只读）：
  analysis/dialect-20261124/dialect-assignment.csv  ← 第 4 步逐层分配表（17,168 行）
  analysis/full-inventory-20261124/inventory-local-all.csv ← 本地层目录（layer_dir）
不修改任何输入，只在 analysis/coord-samples-20261124/ 写 layers.json。
"""
import csv, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.abspath(os.path.join(ROOT, "../.."))
ASSIGN = os.path.join(REPO, "analysis/dialect-20261124/dialect-assignment.csv")
LOCAL = os.path.join(REPO, "analysis/full-inventory-20261124/inventory-local-all.csv")
OUT = os.path.join(ROOT, "layers.json")
LAYER_ROOT = "/data/workspace/world-map-data-33/dist/intake-full/layers"


def main() -> int:
    dirs = {os.path.basename(p.rstrip("/")): p.rstrip("/")
            for p in glob.glob(os.path.join(LAYER_ROOT, "*")) if os.path.isdir(p)}
    alias = {}
    for name, p in dirs.items():
        if "_" in name:
            alias.setdefault(name.split("_", 1)[1], p)

    out, seen = [], set()
    with open(ASSIGN, newline="") as f:
        for r in csv.DictReader(f):
            lid, url = r["layer_id"], r["url"]
            rec = {
                "layer_id": lid,
                "url": url,
                "universe": r["universe"],
                "state": r["state"],
                "provider": r["provider_id"],
                "provider_kind": r["provider_kind"],
                "granularity": r["granularity"],
                "dialect_id": r["dialect_id"],
                "status": r["status"],
            }
            if r["universe"] == "d2":
                rec["layer_dir"] = dirs.get(lid) or alias.get(lid)
            out.append(rec)
            seen.add(url)

    with open(OUT, "w") as f:
        json.dump({"layers": out,
                   "denominator": len(out),
                   "unique_url": len(seen),
                   "generated_from": [os.path.relpath(ASSIGN, REPO),
                                      os.path.relpath(LOCAL, REPO)]}, f)
    print(json.dumps({"layers": len(out), "unique_url": len(seen),
                      "d1": sum(1 for x in out if x["universe"] == "d1"),
                      "d2": sum(1 for x in out if x["universe"] == "d2"),
                      "d2_missing_dir": sum(1 for x in out if x["universe"] == "d2" and not x.get("layer_dir")),
                      "out": OUT}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
