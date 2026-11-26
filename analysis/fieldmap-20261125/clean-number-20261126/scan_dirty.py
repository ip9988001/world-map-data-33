#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫「house_number 写成 x.0」的脏行（muse-000275 定范围用）。

扫描对象（都是**已落盘的真实映射产物**，不是猜测）：
  1) `dist-v2/tar/fieldmap-part*.tar.gz` —— PR #58 合并后的 3,355 层产物（tar 内成员是 ndjson.gz）
  2) `/data/scratch/fix58-20261126/rows/*.ndjson.gz` —— fix58 那 58 层的新产物
两层合计 = 现在的 3,413 个已映射层。

判定：行内 `"house_number":"<num>"` 且 num 匹配 `^\\d+\\.0+$`。用字节正则扫，不逐行 json.loads
（只有命中行才解析，取样本）。

输出：每层一行 jsonl
  {layer, rows_total, rows_dirty, samples:[{house_number, street_name, lat, lon}], street_dirty}
  street_dirty = 同一行 street_name 非空且 house_number 为脏（用于后面「只改格式不改身份」抽查底稿）
只读；不写任何映射产物。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import re
import sys
import tarfile

DIRTY = re.compile(rb'"house_number":"(\d+)\.0+"')
HN_STREET = re.compile(rb'"house_number":"([^"]*)","street_name":("([^"]*)"|null)')
SAMPLE_MAX = 5


def scan_stream(fh, layer, st):
    n = 0
    dirty = 0
    for line in fh:
        n += 1
        if b'.0"' not in line or b'"house_number":"' not in line:
            continue
        m = DIRTY.search(line)
        if not m:
            continue
        dirty += 1
        if len(st["samples"]) < SAMPLE_MAX:
            rec = json.loads(line)
            st["samples"].append({"house_number": rec.get("house_number"),
                                  "street_name": rec.get("street_name"),
                                  "lat": rec.get("lat"), "lon": rec.get("lon"),
                                  "grade": rec.get("grade")})
    st["layer"] = layer
    st["rows_total"] = n
    st["rows_dirty"] = dirty
    return st


def scan_ndjson_gz(path, layer):
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        st = {"layer": layer, "rows_total": 0, "rows_dirty": 0, "samples": [], "src": path}
        # 逐行读到 bytes 更稳：用二进制再解一次
    st = {"layer": layer, "rows_total": 0, "rows_dirty": 0, "samples": [], "src": path}
    with gzip.open(path, "rb") as fh:
        return scan_stream(fh, layer, st)


def scan_tar(path):
    out = []
    with tarfile.open(path, "r|gz") as tf:
        for m in tf:
            if not m.isfile() or not m.name.endswith(".ndjson.gz"):
                continue
            layer = os.path.basename(m.name)[:-len(".ndjson.gz")]
            st = {"layer": layer, "rows_total": 0, "rows_dirty": 0, "samples": [],
                  "src": os.path.basename(path)}
            fobj = tf.extractfile(m)
            if fobj is None:
                continue
            with gzip.GzipFile(fileobj=fobj) as gz:
                scan_stream(gz, layer, st)
            out.append(st)
    return out


def work(job):
    kind, path = job
    if kind == "tar":
        return scan_tar(path)
    return [scan_ndjson_gz(path, os.path.basename(path)[:-len(".ndjson.gz")])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tars", default="/data/workspace/wmd-fieldmap/dist-v2/tar/fieldmap-part*.tar.gz")
    ap.add_argument("--rows-dir", default="/data/scratch/fix58-20261126/rows")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=7)
    a = ap.parse_args()
    jobs = [("tar", p) for p in sorted(glob.glob(a.tars))]
    jobs += [("gz", p) for p in sorted(glob.glob(os.path.join(a.rows_dir, "*.ndjson.gz")))]
    import multiprocessing as mp
    with open(a.out, "w", encoding="utf-8") as fh, mp.Pool(a.workers) as pool:
        done = 0
        for res in pool.imap_unordered(work, jobs, chunksize=1):
            for st in res:
                fh.write(json.dumps(st, ensure_ascii=False) + "\n")
            done += 1
            fh.flush()
            tag = res[0]["layer"] if res else "?"
            print(f"[{done}/{len(jobs)}] {tag[:44]:44s} layers_in_unit={len(res)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
