#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付前校验：覆盖表里标了 out_file 的层，必须能在 dist/tar/*.tar.gz 里找到同名成员（一个不能少）。"""
from __future__ import annotations
import csv, os, sys, tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
TARS = "/data/workspace/wmd-fieldmap/dist/tar"


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "layer-coverage.csv"), encoding="utf-8")))
    want = {r["layer"] + ".ndjson.gz" for r in rows if r.get("out_file")}
    have = set()
    for f in sorted(os.listdir(TARS)):
        if f.endswith(".tar.gz"):
            with tarfile.open(os.path.join(TARS, f)) as tf:
                for m in tf:
                    have.add(m.name)
    missing = want - have
    print(f"layers_with_output={len(want)} members_in_tars={len(have)} missing={len(missing)}")
    if missing:
        print("MISSING:", sorted(missing)[:10])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
