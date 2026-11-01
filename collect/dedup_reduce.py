#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""08 · stage2：spill → 实体台账（一行 = 一条去重后地址）+ 三级聚合。

三件硬规则（R1 落地，全量沿用）：
  1. **同键必合并**：键 = `state|county_fips|number|street_key|unit_key`，同一键的成员只出一行。
  2. **重发层只算 1 票**：同一 `dataset_fingerprint` 的层（同一数据集被多个服务重发）
     在 `independent_sources_n` 里只算 1 次，其余记 `duplicate_dataset`。
  3. **方向词缺失可合并但必须标记**：键里带 DIR，所以 `E MAIN` 与 `W MAIN` 天然分开；
     只有当某个「去掉 DIR 后相同」的族里**只有一个**非空方向时，才把空方向的行并进那个方向，
     并记 `dir_inferred`（这类不进 A 级）。

用法：
  python3 collect/dedup_reduce.py --spill /tmp/08-R1/spill --out /tmp/08-R1
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

TIER_ORDER = {"S": 0, "A": 1, "B": 2, "U": 3}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_layers(spill_dir: str) -> list[dict]:
    out = []
    p = os.path.join(spill_dir, "layers.jsonl")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def expand(row: dict, layers: list[dict]) -> dict:
    """spill 压缩键 → 可读字段（省字节用短键，reduce 里展开）。"""
    L = layers[row["L"]] if 0 <= row["L"] < len(layers) else {}
    return {
        "street_src": row.get("ss") or "", "ts": row.get("t") or "",
        "s": row["s"], "c": row["c"], "k": row["k"], "sk": row["sk"], "u": row["u"],
        "unit_raw": row.get("ur") or "",
        "street": row.get("st") or "", "type": row.get("ty") or "",
        "pre": row.get("pd") or "", "post": row.get("po") or "",
        "zip": row.get("z") or "", "city": row.get("ci") or "",
        "lat": row.get("la"), "lon": row.get("lo"),
        "layer": L.get("layer", "?"), "group": L.get("src_group", "LOCAL_GIS"),
        "fp": L.get("dataset_fingerprint", ""), "status": L.get("status", ""),
        "title": L.get("title", ""),
    }


def split_key(key: str) -> tuple:
    """`state|county|num|TYPE|CORE|DIR|unit` → 7 段（street_key 自带两个 `|`，不能拍平数）。"""
    parts = key.split("|")
    while len(parts) < 7:
        parts.append("")
    return parts[0], parts[1], parts[2], "%s|%s|%s" % (parts[3], parts[4], parts[5]), parts[6]


def nodir_key(key: str) -> str:
    """去掉 street_key 末段的 DIR（用于「缺方向时能否安全补全」的判定）。"""
    st, co, num, skey, ukey = split_key(key)
    bits = skey.split("|")
    if len(bits) == 3:
        bits[2] = ""
    return "%s|%s|%s|%s|%s" % (st, co, num, "|".join(bits), ukey)


def rep_score(m: dict) -> tuple:
    """代表行打分：坐标 > 邮编 > 城市 > 结构化来源（非自由文本）。"""
    return (
        1 if (m["lat"] is not None and m["lon"] is not None) else 0,
        1 if m["zip"] else 0,
        1 if m["city"] else 0,
        1 if m["type"] else 0,
        0 if m["status"] != "ok" else 1,
    )


def tier_of(groups: set, dir_inferred: bool, rep_street_src: str, status: str) -> str:
    """R1/R2 不挂 TIGER ⇒ **没有 S 级**（S 需要 TIGER 号段命中 + 第二源投票）。

    判级只看**代表行**的来源质量：成员里有个把自由文本行，不该把整条地址降级；
    但方向是推断补出来的（`dir_inferred`）一律降级 —— 那条街可能真的分 E/W 两条。
    """
    if status in ("upstream_unstable", "unverified") or rep_street_src == "full":
        return "U"
    if len(groups) >= 2 and not dir_inferred:
        return "A"
    return "B"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spill", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int, default=1000)
    args = ap.parse_args()

    layers = load_layers(args.spill)
    names = {}
    np_ = os.path.join(args.spill, "county_names.json")
    if os.path.exists(np_):
        names = json.load(open(np_, encoding="utf-8"))
    files = sorted(f for f in os.listdir(args.spill) if f.endswith(".ndjson.gz"))
    if not files:
        raise SystemExit("spill 为空：%s" % args.spill)

    # ---- 读 spill：按 (state, county) 分组（R1 规模可全量驻留；全量按桶顺序流式处理）
    by_county = collections.defaultdict(lambda: collections.defaultdict(list))
    rows_in = 0
    for f in files:
        with gzip.open(os.path.join(args.spill, f), "rt", encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                rows_in += 1
                by_county[(row["s"], row["c"])][row["k_"]].append(row)

    ledger_dir = os.path.join(args.out, "ledger")
    os.makedirs(ledger_dir, exist_ok=True)
    agg_dir = os.path.join(args.out, "agg")
    os.makedirs(agg_dir, exist_ok=True)

    ledger_rows = 0
    dup_total = 0
    dir_inferred_n = 0
    dir_ambiguous_n = 0
    tier_count = collections.Counter()
    group_vote = collections.Counter()
    fp_dup_votes = 0
    sample_out = []
    street_agg = collections.defaultdict(lambda: {"n": 0, "lo": None, "hi": None, "units": 0})
    zip_agg = collections.defaultdict(lambda: {"n": 0, "streets": set()})
    city_agg = collections.defaultdict(lambda: {"n": 0, "streets": set()})
    county_rep = names

    for (state, county), keys in sorted(by_county.items()):
        # ---- 方向词补全：只在「去掉 DIR 后同族」里只有一个非空方向时才合并
        fam = collections.defaultdict(set)
        for k in keys:
            st, co, num, skey, ukey = split_key(k)
            fam[nodir_key(k)].add(skey.split("|")[2] if skey.count("|") == 2 else "")
        merge_into = {}
        merged_from = collections.defaultdict(list)
        for k in keys:
            famkey = nodir_key(k)
            dirs = {d for d in fam[famkey] if d}
            if len(dirs) == 1:
                only = next(iter(dirs))
                cur = split_key(k)[3].split("|")[2] if split_key(k)[3].count("|") == 2 else ""
                if cur != only:
                    st, co, num, skey, ukey = split_key(k)
                    bits = skey.split("|")
                    bits[2] = only
                    tgt = "%s|%s|%s|%s|%s" % (st, co, num, "|".join(bits), ukey)
                    merge_into[k] = tgt
                    merged_from[tgt].append(k)
            elif len(dirs) > 1:
                cur = split_key(k)[3].split("|")[2] if split_key(k)[3].count("|") == 2 else ""
                if not cur:
                    dir_ambiguous_n += 1

        merged = collections.defaultdict(list)
        for k, ms in keys.items():
            merged[merge_into.get(k, k)].extend(ms)
            if k in merge_into:
                dir_inferred_n += 1

        out_rows = []
        for key, members in merged.items():
            ms = [expand(m, layers) for m in members]
            ms.sort(key=rep_score, reverse=True)
            rep = ms[0]
            # 独立源：先按 dataset_fingerprint 折叠重发层，再按 src_group 计票
            seen_fp = set()
            groups = set()
            votes = collections.Counter()
            fp_dup = 0
            for m in ms:
                fp = m["fp"] or ("L:" + m["layer"])
                if fp in seen_fp:                 # 重发层：不计票，只记重复
                    fp_dup += 1
                    continue
                seen_fp.add(fp)
                groups.add(m["group"])
                votes[m["group"]] += 1
            fp_dup_votes += fp_dup
            flags = set()
            if any(m["street_src"] == "full" for m in ms):
                flags.add("mixed_street_source" if rep["street_src"] != "full"
                          else "street_from_fulltext")
            src_layers = sorted({m["layer"] for m in ms})
            dir_inf = key in merged_from
            if dir_inf:
                flags.add("dir_inferred")
            if len({m["pre"] for m in ms if m["pre"]}) > 1:
                flags.add("dir_conflict")
            zips = {m["zip"] for m in ms if m["zip"]}
            if len(zips) > 1:
                flags.add("zip_conflict")
            if len({m["city"] for m in ms if m["city"]}) > 1:
                flags.add("city_conflict")
            st, co, num, skey, ukey = split_key(key)
            bits = skey.split("|")
            t = tier_of(groups, dir_inf, rep["street_src"], rep["status"])
            tier_count[t] += 1
            for g in groups:
                group_vote[g] += 1
            row = {
                "dedup_key": key,
                "state": st, "state_fips": co[:2], "county_fips": co,
                "county_name": county_rep.get(co, ""),
                "number": num, "number_suffix": "",
                "pre_dir": bits[2].split("+")[0] if bits[2] else "",
                "street_core": bits[1], "street_type": bits[0],
                "post_dir": bits[2].split("+")[1] if "+" in bits[2] else "",
                "unit": ukey, "unit_raw": rep["unit_raw"],
                "street_full": " ".join(x for x in (bits[2].split("+")[0] if bits[2] else "",
                                                   bits[1], bits[0]) if x),
                "zip5": rep["zip"], "zip4": "",
                "city_postal": rep["city"], "city_municipal": "",
                "lat": rep["lat"], "lon": rep["lon"],
                "geo_precision": "point" if rep["lat"] is not None else "none",
                "src_kinds": sorted(groups), "src_layers_n": len(src_layers),
                "src_layers": src_layers[:8],
                "independent_sources_n": len(groups),
                "src_group_votes": dict(votes),
                "tier": t, "tiger_verify": None,
                "dup_members": len(ms) - 1,
                "zip_conflict": "zip_conflict" in flags,
                "dir_conflict": "dir_conflict" in flags or "dir_inferred" in flags,
                "first_seen": min([m["ts"] for m in ms if m["ts"]] or [""]),
                "last_seen": max([m["ts"] for m in ms if m["ts"]] or [""]),
                "flags": sorted(flags), "rep_reason": "%s/%s" % (rep["group"], rep["layer"][:40]),
            }
            out_rows.append(row)
            ledger_rows += 1
            dup_total += row["dup_members"]
            if len(sample_out) < args.sample:
                sample_out.append(row)
            # 聚合（县内）
            sk = "%s|%s|%s" % (bits[0], bits[1], bits[2])
            sa = street_agg[(st, co, rep["city"], sk)]
            sa["n"] += 1
            nv = int(num) if num.isdigit() else None
            if nv is not None:
                sa["lo"] = nv if sa["lo"] is None else min(sa["lo"], nv)
                sa["hi"] = nv if sa["hi"] is None else max(sa["hi"], nv)
            if ukey:
                sa["units"] += 1
            za = zip_agg[(st, rep["zip"])]
            za["n"] += 1
            za["streets"].add(sk)
            ca = city_agg[(st, rep["city"].upper())]
            ca["n"] += 1
            ca["streets"].add(sk)

        p = os.path.join(ledger_dir, "state=%s" % state)
        os.makedirs(p, exist_ok=True)
        with gzip.open(os.path.join(p, "county=%s.ndjson.gz" % county), "wt",
                       encoding="utf-8") as fh:
            for r in out_rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ---- 跨县聚合（stage3 的等价物；R1 在内存里做）
    def write_agg(name, rows):
        with gzip.open(os.path.join(agg_dir, name), "wt", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    street_rows = []
    for (st, co, city, sk), v in street_agg.items():
        street_rows.append({"state": st, "county_fips": co, "city": city, "street_key": sk,
                            "address_count": v["n"], "unit_count": v["units"],
                            "number_min": v["lo"], "number_max": v["hi"]})
    zip_rows = [{"state": k[0], "zip5": k[1], "address_count": v["n"],
                 "street_count": len(v["streets"])} for k, v in zip_agg.items()]
    city_rows = [{"state": k[0], "city": k[1], "address_count": v["n"],
                  "street_count": len(v["streets"])} for k, v in city_agg.items()]
    write_agg("streets.ndjson.gz", street_rows)
    write_agg("zips.ndjson.gz", zip_rows)
    write_agg("cities.ndjson.gz", city_rows)

    rep = {
        "schema": "08-reduce/v1", "at": now(),
        "rows_in": rows_in, "keys_out": ledger_rows,
        "dup_members_total": dup_total,
        "conservation": {"rows_in == keys_out + dup_members": rows_in == ledger_rows + dup_total},
        "dir_inferred_keys": dir_inferred_n, "dir_ambiguous_keys": dir_ambiguous_n,
        "duplicate_dataset_votes_dropped": fp_dup_votes,
        "tier": dict(tier_count), "src_group_votes": dict(group_vote),
        "aggregates": {"streets": len(street_rows), "zips": len(zip_rows),
                       "cities": len(city_rows)},
        "counties": len(by_county),
    }
    json.dump(rep, open(os.path.join(args.out, "reports", "reduce.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "sample.ndjson"), "w", encoding="utf-8") as fh:
        for r in sample_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("[reduce] rows_in=%d keys_out=%d dup=%d 守恒=%s tiers=%s"
          % (rows_in, ledger_rows, dup_total,
             rep["conservation"]["rows_in == keys_out + dup_members"], dict(tier_count)),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
