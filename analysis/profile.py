#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""值分布摸底（只读）：流式读 Release 里已采集的层资产，一层一份 JSON，处理完即删。

约束（按本轮任务边界）：
  · 只读 GitHub Release 资产，**不访问上游 ArcGIS/Census**（本文件里没有任何上游 URL 常量）；
  · 一层一个文件，边读边聚合，读完删除；不一次性加载；
  · 输出 analysis/out/<sha1(layer)>.json，可断点续跑（已存在即跳过）。

用法：
  python3 analysis/profile.py points --tags-file /tmp/inv/point_tags.txt --sample 2000
  python3 analysis/profile.py parcels --tar-url-file /tmp/inv/parcel_urls.txt --sample 2000
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
TMP = "/tmp/profile-work"
REPO = "ip9988001/world-map-data-33"
UA = {"User-Agent": "world-map-data-33/readonly-profiler"}

NUM_RX = re.compile(r"(house|housenum|house_num|addrnum|addr_num|situs_?num|street_?num|"
                    r"site_?addr|fulladdr|full_addr|address|addr|num|premise|unit)", re.I)
NULLISH = {"N/A", "NA", "NULL", "NONE", "UNKNOWN", "NOT STATED", "NOTSTATED", "TBD",
           "LOT", "PARCEL", "UNK", "N/A ", "NAN", "-", "--", ""}


def classify(v) -> str:
    """门牌号值的形态分类（这一列的分布是本次摸底的核心）。"""
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        try:
            f = float(v)
        except Exception:  # noqa: BLE001
            return "other"
        if f == 0:
            return "zero"
        return "pure_num" if f == int(f) else "other"
    s = str(v).strip()
    if not s:
        return "empty"
    up = s.upper()
    if up in ("NULL", "NONE"):
        return "null"
    if up in ("N/A", "NA", "NAN"):
        return "na"
    if up in ("UNKNOWN", "UNK", "NOT STATED", "NOTSTATED"):
        return "unknown"
    if up in ("TBD", "LOT", "PARCEL", "LOT-PARCEL", "LOT/PARCEL"):
        return "lot_parcel_tbd"
    if re.fullmatch(r"0+(\.0+)?", s):
        return "zero"
    if re.fullmatch(r"\d+", s):
        return "pure_num"
    if re.fullmatch(r"\d+\s*[-–~]\s*\d+", s):
        return "range"
    if re.fullmatch(r"\d+[A-Za-z]{1,3}", s):
        return "num_suffix"
    if re.fullmatch(r"\d+\s*[A-Za-z]/?\d*", s):
        return "num_suffix"
    if re.fullmatch(r"\d+[\s-]\d+/\d+", s):
        return "range"
    return "other"


def new_field():
    return {"n": 0, "nonempty": 0, "types": {}, "ex": []}


def note(fields: dict, name: str, val):
    f = fields.get(name)
    if f is None:
        f = fields[name] = new_field()
    f["n"] += 1
    if isinstance(val, bool):
        t = "bool"
    elif isinstance(val, (int, float)):
        t = "number"
    elif isinstance(val, (list, dict)):
        t = "json"
    else:
        t = "string"
    f["types"][t] = f["types"].get(t, 0) + 1
    if val is None:
        return
    if isinstance(val, str) and not val.strip():
        return
    if isinstance(val, str) and val.strip().upper() in NULLISH:
        f.setdefault("nullish", 0)
        f["nullish"] += 1
        return
    f["nonempty"] += 1
    if len(f["ex"]) < 3:
        s = str(val)
        if s not in f["ex"]:
            f["ex"].append(s[:60])


class LayerProfile:
    def __init__(self, layer_id: str, kind: str, tag: str):
        self.d = {"layer_id": layer_id, "kind": kind, "tag": tag,
                  "rows_total": None, "sampled": 0, "fields": {},
                  "num_fields": {}, "norm": {}, "err": ""}

    def feed_raw(self, raw: dict):
        for k, v in raw.items():
            note(self.d["fields"], str(k), v)
            if NUM_RX.search(str(k)) and not isinstance(v, (dict, list)):
                b = self.d["num_fields"].setdefault(str(k), {})
                c = classify(v)
                b[c] = b.get(c, 0) + 1

    def feed_norm(self, rec: dict):
        for k in ("add_num", "st_name", "st_suf", "pre_dir", "city", "zip", "unit"):
            v = rec.get(k)
            b = self.d["norm"].setdefault(k, {"n": 0, "nonempty": 0})
            b["n"] += 1
            if v not in (None, "") and not (isinstance(v, str) and not v.strip()):
                b["nonempty"] += 1
        for k in ("lat", "lon"):
            v = rec.get(k)
            b = self.d["norm"].setdefault(k, {"n": 0, "nonempty": 0})
            b["n"] += 1
            if isinstance(v, (int, float)) and v == v:
                b["nonempty"] += 1

    def feed_line(self, line: bytes):
        line = line.strip()
        if not line:
            return
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            return
        self.d["sampled"] += 1
        raw = rec.get("raw")
        if isinstance(raw, dict):
            self.feed_raw(raw)
        self.feed_norm(rec)


def gh_dl(tag: str, pattern: str, dest: str) -> str:
    r = subprocess.run(["gh", "release", "download", tag, "--repo", REPO, "-p", pattern,
                        "-D", dest, "--clobber"], capture_output=True, text=True, timeout=1200)
    for f in sorted(os.listdir(dest)):
        if re.search(pattern.replace("*", ".*"), f):
            return os.path.join(dest, f)
    return ""


def partial_targz_rows(url: str, cap_bytes: int, max_rows: int):
    """只下 cap_bytes 字节，从 tar.gz 里抠出第一个 .ndjson.gz 成员并**部分解压**取前若干行。
    这样一层大层只要 ~3MB 就能拿到样本，不必下 178MB。"""
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes=0-{cap_bytes}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        blob = r.read()
    d = zlib.decompressobj(31)
    tar_bytes = d.decompress(blob, 64 << 20)
    off, n = 0, 0
    while off + 512 <= len(tar_bytes) and n < 10:
        hdr = tar_bytes[off:off + 512]
        if hdr[:1] == b"\0":
            break
        name = hdr[:100].rstrip(b"\0").decode("utf-8", "replace")
        try:
            size = int(hdr[124:136].rstrip(b"\0 ") or b"0", 8)
        except ValueError:
            break
        data = tar_bytes[off + 512: off + 512 + size]
        off += 512 + ((size + 511) // 512) * 512
        n += 1
        if not name.endswith(".ndjson.gz"):
            continue
        if len(data) < size:                     # 数据被截断 → 部分解压即可
            gz = zlib.decompressobj(31)
            try:
                text = gz.decompress(data, 64 << 20)
            except Exception:  # noqa: BLE001
                text = b""
        else:
            text = gzip.decompress(data)
        lines = text.split(b"\n")
        for ln in lines[:max_rows]:
            yield ln
        return


def profile_point(tag: str, mode: str, cap_bytes: int, max_rows: int) -> dict:
    layer = re.sub(r"^collect-step\d+-", "", tag)
    kind = "parcel_situs" if "-step10-" in tag else "address_point"
    lp = LayerProfile(layer, kind, tag)
    d = os.path.join(TMP, hashlib.sha1(tag.encode()).hexdigest()[:10])
    os.makedirs(d, exist_ok=True)
    try:
        cp = gh_dl(tag, "*-checkpoint.json", d)
        rows_total = None
        if cp:
            try:
                j = json.load(open(cp, encoding="utf-8"))
                ur = j.get("unit_rows") or {}
                if ur:
                    rows_total = sum(int(v) for v in ur.values())
            except Exception:  # noqa: BLE001
                pass
        lp.d["rows_total"] = rows_total
        raw = json.loads(subprocess.run(
            ["gh", "release", "view", tag, "--repo", REPO, "--json", "assets",
             "-q", "[.assets[]|select(.name|endswith(\"tar.gz\"))|{n:.name,u:.url,s:.size}]"],
            capture_output=True, text=True, timeout=300).stdout or "[]")
        assets = sorted(raw, key=lambda a: a["n"])
        if not assets:
            lp.d["err"] = "no_payload"
            return lp.d
        if mode == "sample":
            for ln in partial_targz_rows(assets[0]["u"], cap_bytes, max_rows):
                lp.feed_line(ln)
        else:
            for a in assets:
                p = gh_dl(tag, a["n"], d)
                if not p:
                    continue
                with tarfile.open(p, "r:gz") as tf:
                    for m in tf.getmembers():
                        if not m.name.endswith(".ndjson.gz"):
                            continue
                        fh = tf.extractfile(m)
                        if fh is None:
                            continue
                        with gzip.GzipFile(fileobj=fh) as gz:
                            for i, ln in enumerate(gz):
                                if i < max_rows:
                                    lp.feed_line(ln)
                os.unlink(p)
    except Exception as e:  # noqa: BLE001
        lp.d["err"] = "%s:%s" % (type(e).__name__, str(e)[:120])
    finally:
        for f in os.listdir(d):
            try:
                os.unlink(os.path.join(d, f))
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass
    return lp.d


def profile_parcels_tar(url: str, max_rows: int) -> list[dict]:
    """流式扫 parcel1-raw-N.tar：每层（目录）取前 max_rows 行做画像，同时数总行数。"""
    import subprocess as sp
    dest = os.path.join(TMP, "parcel-" + hashlib.sha1(url.encode()).hexdigest()[:8] + ".tar")
    os.makedirs(TMP, exist_ok=True)
    if not os.path.exists(dest):
        r = sp.run(["curl", "-sSL", "-o", dest, url], capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            return [{"err": "download_failed", "url": url}]
    profs: dict[str, LayerProfile] = {}
    with tarfile.open(dest, "r:") as tf:
        for m in tf:
            if not m.name.endswith(".ndjson.gz"):
                continue
            layer = m.name.split("/")[0]
            lp = profs.get(layer)
            if lp is None:
                lp = profs[layer] = LayerProfile(layer, "parcel_situs", "parcel1-raw")
                lp.d["rows_total"] = 0
            fh = tf.extractfile(m)
            if fh is None:
                continue
            try:
                with gzip.GzipFile(fileobj=fh) as gz:
                    for ln in gz:
                        lp.d["rows_total"] = (lp.d["rows_total"] or 0) + 1
                        if lp.d["sampled"] < max_rows:
                            lp.feed_line(ln)
            except Exception as e:  # noqa: BLE001
                lp.d["err"] = (lp.d["err"] or "") + "|%s" % type(e).__name__
    os.unlink(dest)
    return [p.d for p in profs.values()]


def save(d: dict) -> None:
    os.makedirs(OUT, exist_ok=True)
    key = hashlib.sha1((d.get("tag", "") + "|" + d.get("layer_id", "")).encode()).hexdigest()[:16]
    json.dump(d, open(os.path.join(OUT, key + ".json"), "w", encoding="utf-8"), ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["points", "parcels"])
    ap.add_argument("--tags-file", default="")
    ap.add_argument("--tar-url-file", default="")
    ap.add_argument("--sample", type=int, default=2000)
    ap.add_argument("--cap-bytes", type=int, default=3 << 20)
    ap.add_argument("--full-under", type=int, default=30 << 20,
                    help="payload 小于该字节数则全量扫，否则只取 range 样本")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    if a.mode == "parcels":
        urls = [x.strip() for x in open(a.tar_url_file) if x.strip()]
        for u in urls:
            t0 = time.time()
            for d in profile_parcels_tar(u, a.sample):
                save(d)
            print("[parcels] %s 完成 %.0fs" % (os.path.basename(u), time.time() - t0), flush=True)
        return 0

    tags = [x.strip() for x in open(a.tags_file) if x.strip()]
    if a.limit:
        tags = tags[:a.limit]
    for i, tag in enumerate(tags, 1):
        key = hashlib.sha1((tag + "|" + re.sub(r"^collect-step\d+-", "", tag)).encode()).hexdigest()[:16]
        if os.path.exists(os.path.join(OUT, key + ".json")):
            continue
        t0 = time.time()
        sz = json.loads(subprocess.run(
            ["gh", "release", "view", tag, "--repo", REPO, "--json", "assets",
             "-q", "[.assets[]|select(.name|endswith(\"tar.gz\"))|.size]|add // 0"],
            capture_output=True, text=True, timeout=300).stdout or "0")
        mode = "full" if sz <= a.full_under else "sample"
        d = profile_point(tag, mode, a.cap_bytes, a.sample)
        d["payload_bytes"] = sz
        d["mode"] = mode
        save(d)
        print("[%d/%d] %s %s rows=%s sampled=%d %.1fs"
              % (i, len(tags), tag[-48:], mode, d.get("rows_total"), d.get("sampled"),
                 time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
