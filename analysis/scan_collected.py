#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫一遍 Releases，把「已采层」按步骤归集（一次扫完，避免每步各扫 25 页）。

产出 /tmp/collected.json：
  {"by_step": {"04": {layer: {assets, has_ckpt}}, ...},
   "layer_step": {layer: "04"},   # 同一层被多步采过时取最早的步
   "counts": {...}}

只读 GitHub Releases 元数据，不下载任何资产本体。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

REPO = "ip9988001/world-map-data-33"
OUT = "/tmp/collected.json"


def gh(url):
    r = subprocess.run(["gh", "api", url], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:300])
    return json.loads(r.stdout)


def main():
    by_step = {}
    page = 1
    pages = 0
    while page <= 60:
        batch = gh("repos/%s/releases?per_page=100&page=%d" % (REPO, page))
        pages += 1
        if not batch:
            break
        for rel in batch:
            tag = rel.get("tag_name") or ""
            m = re.match(r"^collect-step(0[0-9]|1[0-9])-(.+?)(-r\d+)?$", tag)
            if not m:
                continue
            step, lid = m.group(1), m.group(2)
            alist = rel.get("assets") or []
            assets = [a.get("name") or "" for a in alist]
            nbytes = sum(int(a.get("size") or 0) for a in alist)
            rec = by_step.setdefault(step, {}).setdefault(
                lid, {"tag": tag, "assets_n": 0, "has_ckpt": False,
                      "parts_n": 0, "bytes": 0})
            rec["assets_n"] = max(rec["assets_n"], len(assets))
            if any(a.endswith("-checkpoint.json") for a in assets):
                rec["has_ckpt"] = True
            rec["parts_n"] = max(rec["parts_n"], sum(1 for a in assets if a.endswith(".tar.gz")))
            rec["bytes"] = max(rec["bytes"], nbytes)
        if len(batch) < 100:
            break
        page += 1

    layer_step = {}
    for step in sorted(by_step):
        for lid, rec in by_step[step].items():
            if not rec["has_ckpt"]:
                continue
            layer_step.setdefault(lid, step)

    counts = {s: {"layers": len(v), "with_ckpt": sum(1 for r in v.values() if r["has_ckpt"])}
              for s, v in by_step.items()}
    data = {"repo": REPO, "pages": pages, "by_step": by_step,
            "layer_step": layer_step, "counts": counts,
            "collected_layers": len(layer_step)}
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"pages": pages, "counts": counts, "collected_layers": len(layer_step)},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
