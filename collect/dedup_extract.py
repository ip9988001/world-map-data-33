#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08 · stage1：把 Release 资产摊平成「按县分桶的 spill」。

做四件事（全离线，只读 Release）：
  1. 逐层下载 `*-uNNNNN.tar.gz`（`gh release download`），流式解 tar → 解内层 `ndjson.gz`；
  2. `fieldmap3` 取地址字段（顶层缺失回落 `raw`）→ `addrkey` 归一化；
  3. 判县：`county_tiger.CountyIndex`（本地缓存多边形，PIP，不用 bbox）；
  4. 按 `bucket = blake2b(county_fips) % N` **逐行直写** `spill-shardXX-bNN.ndjson.gz`。

同键必落同桶：桶号只由 county_fips 决定，与「哪一片读到这行」无关。

用法：
  python3 collect/dedup_extract.py --state IA --out /tmp/08-R1 --buckets 64
  python3 collect/dedup_extract.py --state IA --out /tmp/08-R1 --limit-rows 20000   # 冒烟
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))

from lib import addrkey as AK                     # noqa: E402
from lib.fieldmap3 import extract_addr            # noqa: E402
from county_index import get_national             # noqa: E402

REPO = "ip9988001/world-map-data-33"
STAGE_TAG = {"04b": "collect-step04-", "05b": "collect-step05-", "07b": "collect-step07-"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bucket_of(county_fips: str, n: int) -> int:
    """桶号：只取决于 county_fips ⇒ 同键必落同桶。"""
    h = hashlib.blake2b(str(county_fips).encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") % n


def planned_layers(state: str, plan_path: str) -> list[dict]:
    """该州在三阶段账本里的全部层（不跨州：只取 layer_plan 里 state == 该州的层）。"""
    plan = {}
    with open(plan_path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            plan[r["layer_id"]] = r
    out = []
    for stage, pref in STAGE_TAG.items():
        p = os.path.join(ROOT, "collect", "%s_ledger.json" % stage)
        if not os.path.exists(p):
            continue
        for rec in json.load(open(p, encoding="utf-8"))["records"]:
            lid = rec["layer"]
            ent = plan.get(lid, {})
            if (ent.get("state") or "").upper() != state.upper():
                continue
            ts = (rec.get("last_upload") or rec.get("at") or "").strip()
            out.append({
                "stage": stage,
                "ts": ts,
                "layer": lid,
                "tag": rec.get("tag") or (pref + lid),
                "plan_rows": rec.get("rows") or 0,
                "status": rec.get("status") or "",
                "title": ent.get("title") or "",
                "url": ent.get("url") or "",
            })
    out.sort(key=lambda x: (x["stage"], x["layer"]))
    return out


def download_layer(tag: str, dest: str, retries: int = 5) -> list[str]:
    """把一个 tag 的载荷包下到 dest；返回本地 tar.gz 路径列表。"""
    os.makedirs(dest, exist_ok=True)
    for attempt in range(retries):
        r = subprocess.run(
            ["gh", "release", "download", tag, "-R", REPO, "-p", "*.tar.gz",
             "-D", dest, "--clobber"],
            capture_output=True, text=True)
        if r.returncode == 0:
            break
        if attempt == retries - 1:
            raise RuntimeError("下载失败 %s: %s" % (tag, (r.stderr or "")[-300:]))
        time.sleep(2 ** attempt)
    return sorted(os.path.join(dest, f) for f in os.listdir(dest) if f.endswith(".tar.gz"))


def iter_records(tar_paths: list[str]):
    """流式产出记录：tar.gz → 内层 *.ndjson.gz → 逐行 json。"""
    for tp in tar_paths:
        try:
            with tarfile.open(tp, "r:gz") as tf:
                for m in tf:
                    if not (m.isfile() and m.name.endswith((".ndjson.gz", ".ndjson"))):
                        continue
                    fh = tf.extractfile(m)
                    if fh is None:
                        continue
                    stream = gzip.GzipFile(fileobj=fh) if m.name.endswith(".gz") else fh
                    with stream:
                        for line in stream:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                yield json.loads(line)
                            except Exception:            # noqa: BLE001
                                yield None
        except (tarfile.TarError, OSError, EOFError):
            continue


def nad_like(rec: dict) -> bool:
    """NAD 字段指纹：上游原始属性里有 `UUID` + `AddrClass`/`Addr_Type`（二仓 read_nad 同样判据）。"""
    raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else {}
    up = {str(k).upper() for k in raw}
    return "UUID" in up and ("ADDRCLASS" in up or "ADDR_TYPE" in up or "PLACEMENT" in up)


def classify_group(layer: dict, nad_ratio: float) -> str:
    """源组。先看字段指纹（NAD），再看名字/标题。"""
    if nad_ratio >= 0.5:
        return "NAD"
    blob = (layer["layer"] + " " + (layer.get("title") or "")).lower()
    if "overture" in blob:
        return "OVERTURE"
    if "openstreetmap" in blob or "_osm_" in blob or blob.startswith("osm"):
        return "OSM"
    if "ng911" in blob or "e911" in blob or "_911_" in blob or "911_address" in blob:
        return "NG911"
    if "parcel" in blob or "situs" in blob or "assessor" in blob:
        return "PARCEL_SITUS"
    return "LOCAL_GIS"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--buckets", type=int, default=64)
    ap.add_argument("--plan", default=os.path.join(ROOT, "collect", "layer_plan.csv"))
    ap.add_argument("--layers", default="", help="逗号分隔，只跑这些层（冒烟用）")
    ap.add_argument("--limit-rows", type=int, default=0, help="每层最多读多少行（冒烟用）")
    ap.add_argument("--keep-tars", action="store_true")
    args = ap.parse_args()

    state = args.state.upper()
    spill_dir = os.path.join(args.out, "spill")
    rep_dir = os.path.join(args.out, "reports")
    os.makedirs(spill_dir, exist_ok=True)
    os.makedirs(rep_dir, exist_ok=True)

    layers = planned_layers(state, args.plan)
    if args.layers:
        keep = {x.strip() for x in args.layers.split(",") if x.strip()}
        layers = [x for x in layers if x["layer"] in keep]
    if not layers:
        raise SystemExit("没有该州的层：%s" % state)

    # 全国县索引（3,089 县，1° 网格预筛 + 射线法）。**不限定在计划州**：
    # 计划里的 state 列有错（R1 实测：标 IA 的层里 2 层在 NE、1 层在 WI），
    # 州一律由 PIP 判出的 county_fips 反推，不同就记 plan_state_mismatch。
    ni = get_national()
    print("[extract] %s：%d 层，全国 %d 县 / %d 州" % (state, len(layers), len(ni.by_fips),
                                                   len(ni.states)), flush=True)

    writers = {}
    meta_path = os.path.join(spill_dir, "layers.jsonl")
    meta_fh = open(meta_path, "w", encoding="utf-8")
    layer_idx = {}
    digest_sample = {}

    totals = {"rows": 0, "keyable": 0, "unkeyed": 0, "no_coord": 0, "located": 0,
              "unlocated": 0, "outside_state": 0, "bad_json": 0, "bytes": 0, "assets": 0}
    plan_state_mismatch_layers = []

    def w(bucket: int):
        if bucket not in writers:
            p = os.path.join(spill_dir, "spill-shard00-b%02d.ndjson.gz" % bucket)
            writers[bucket] = gzip.open(p, "wt", encoding="utf-8", compresslevel=6)
        return writers[bucket]

    t0 = time.time()
    tmp_root = tempfile.mkdtemp(prefix="08ext-")
    try:
        for li, layer in enumerate(layers):
            lid, tag = layer["layer"], layer["tag"]
            layer_idx[lid] = li
            ddir = os.path.join(tmp_root, "L%03d" % li)
            tars = download_layer(tag, ddir)
            stats = {"rows": 0, "keyable": 0, "unkeyed": 0, "no_coord": 0, "located": 0,
                     "unlocated": 0, "outside_state": 0, "bad_json": 0, "nad": 0,
                     "top_num": 0, "raw_num": 0, "full_num": 0, "top_street": 0, "raw_street": 0}
            pip_state = {}
            sample = []
            for rec in iter_records(tars):
                if rec is None:
                    stats["bad_json"] += 1
                    continue
                stats["rows"] += 1
                if args.limit_rows and stats["rows"] > args.limit_rows:
                    stats["rows"] -= 1
                    break
                if nad_like(rec):
                    stats["nad"] += 1
                a = extract_addr(rec)
                if a["num_src"] == "top":
                    stats["top_num"] += 1
                elif a["num_src"] == "raw":
                    stats["raw_num"] += 1
                elif a["num_src"] == "full":
                    stats["full_num"] += 1
                if a["street_src"] == "top":
                    stats["top_street"] += 1
                elif a["street_src"] == "raw":
                    stats["raw_street"] += 1

                num = AK.num_key(a["num"])
                skey = AK.street_key(a["street"], a["type"], a["pre"], a["post"])
                ukey = AK.unit_key(a["unit"])
                if not num or not skey.strip("|"):
                    stats["unkeyed"] += 1
                    continue
                if a["lat"] is None or a["lon"] is None:
                    stats["no_coord"] += 1
                    county = ""
                else:
                    county = ni.locate(a["lat"], a["lon"]) or ""
                    if county:
                        stats["located"] += 1
                    else:
                        stats["unlocated"] += 1
                if not county:
                    stats["unkeyed"] += 1
                    continue
                pip_st = ni.fips2state.get(county[:2], "")
                pip_state[pip_st] = pip_state.get(pip_st, 0) + 1
                if pip_st != state:                  # 不跨州：R1 只落本州台账
                    stats["outside_state"] += 1
                    continue
                key = AK.addr_key(pip_st, county, num, skey, ukey)
                row = {
                    "s": pip_st, "c": county, "k": num, "sk": skey, "u": ukey,
                    "ur": AK.unit_raw(a["unit"]),
                    "st": a["street"], "ty": a["type"], "pd": a["pre"], "po": a["post"],
                    "z": a["zip"], "ci": a["city"],
                    "la": round(a["lat"], 7) if a["lat"] is not None else None,
                    "lo": round(a["lon"], 7) if a["lon"] is not None else None,
                    "L": li, "k_": key, "ss": a["street_src"], "t": layer.get("ts") or "",
                }
                w(bucket_of(county, args.buckets)).write(
                    json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                stats["keyable"] += 1
                if len(sample) < 500:
                    sample.append(key)
            for k in ("rows", "keyable", "unkeyed", "no_coord", "located", "unlocated",
                      "outside_state", "bad_json", "top_num", "raw_num", "full_num",
                      "top_street", "raw_street"):
                totals[k] = totals.get(k, 0) + stats[k]

            nbytes = sum(os.path.getsize(t) for t in tars)
            totals["bytes"] += nbytes
            totals["assets"] += len(tars)
            sample.sort()
            fp = hashlib.sha1(("|".join(sample)).encode()).hexdigest()[:16] if sample else ""
            digest_sample[lid] = fp
            nad_ratio = (stats["nad"] / stats["rows"]) if stats["rows"] else 0.0
            if stats["outside_state"] and stats["rows"]:
                ratio = stats["outside_state"] / stats["rows"]
                if ratio >= 0.5:
                    plan_state_mismatch_layers.append({
                        "layer": lid, "plan_state": state, "pip_state": pip_state,
                        "outside_state": stats["outside_state"], "rows": stats["rows"],
                        "ratio": round(ratio, 3)})
            meta = {
                "layer": lid, "tag": tag, "stage": layer["stage"], "status": layer["status"],
                "pip_state": pip_state,
                "plan_rows": layer["plan_rows"], "assets": len(tars), "bytes": nbytes,
                "dataset_fingerprint": fp, "fingerprint_sample": len(sample),
                "nad_ratio": round(nad_ratio, 3), "src_group": classify_group(layer, nad_ratio),
                **stats,
            }
            meta_fh.write(json.dumps(meta, ensure_ascii=False) + "\n")
            meta_fh.flush()
            print("[layer] %-58s rows=%7d keyable=%7d unkeyed=%5d loc=%7d fp=%s %s"
                  % (lid[:58], stats["rows"], stats["keyable"], stats["unkeyed"],
                     stats["located"], fp or "-", meta["src_group"]), flush=True)
            if not args.keep_tars:
                shutil.rmtree(ddir, ignore_errors=True)
    finally:
        for fh in writers.values():
            fh.close()
        meta_fh.close()
        shutil.rmtree(tmp_root, ignore_errors=True)

    json.dump({f: ni.name_of(f) for f in ni.by_fips},
              open(os.path.join(spill_dir, "county_names.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    ver = {
        "schema": "08-extract/v1", "at": now(), "state": state,
        "plan_state_mismatch_layers": plan_state_mismatch_layers,
        "buckets": args.buckets, "layers_n": len(layers),
        "elapsed_s": round(time.time() - t0, 1), "totals": totals,
        "spill_files": sorted(f for f in os.listdir(spill_dir) if f.endswith(".ndjson.gz")),
        "key_by_bucket": {}, "limit_rows": args.limit_rows,
    }
    # 桶内键数（给 stage2 的守恒校验用）
    for f in ver["spill_files"]:
        p = os.path.join(spill_dir, f)
        n = 0
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            for _ in fh:
                n += 1
        ver["key_by_bucket"][f] = n
    json.dump(ver, open(os.path.join(rep_dir, "extract.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[extract] done %.1fs rows=%d keyable=%d spill_rows=%d"
          % (ver["elapsed_s"], totals["rows"], totals["keyable"],
             sum(ver["key_by_bucket"].values())), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
