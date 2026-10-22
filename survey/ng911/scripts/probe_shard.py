#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 items.json 分片探针，输出 shard_<i>.json"""
import argparse, json, os, re
from concurrent.futures import ThreadPoolExecutor
from ng911_inventory import probe_layer, probe_socrata, ABBR, GEO

HERE = os.path.dirname(os.path.abspath(__file__))

def bbox_of_state(ab):
    for f in GEO["features"]:
        if ABBR.get(f["properties"]["name"]) == ab:
            xs, ys = [], []
            def walk(c):
                if isinstance(c[0], (int, float)): xs.append(c[0]); ys.append(c[1])
                else:
                    for i in c: walk(i)
            walk(f["geometry"]["coordinates"])
            return [min(xs), min(ys), max(xs), max(ys)]
    return None

STATES = [(ab, bbox_of_state(ab)) for ab in sorted(set(ABBR.values()))]

def locate(bb):
    """bbox 中心点落在哪个州（粗略矩形判定）"""
    if not bb: return None
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    for ab, sb in STATES:
        if sb and sb[0] <= cx <= sb[2] and sb[1] <= cy <= sb[3]:
            return ab
    return None

def one(r):
    u = str(r.get("url") or "")
    if not u: return dict(r, ok=False, err="no url")
    try:
        p = probe_socrata(u) if (r["ch"] == "socrata" or re.search(r"/d/[a-z0-9]{4}-", u)) else probe_layer(u)
    except Exception as e:
        p = {"ok": False, "err": str(e)[:100]}
    out = dict(r)
    out.update({k: v for k, v in p.items() if k != "bbox"})
    bb = p.get("bbox") or r.get("bbox")
    out["bbox"] = bb
    out["state"] = locate(bb)
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, required=True)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()
    items = json.load(open(os.path.join(HERE, "items.json")))
    part = [x for i, x in enumerate(items) if i % a.n == a.shard]
    print("shard %d/%d items=%d" % (a.shard, a.n, len(part)), flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(one, part))
    json.dump(rows, open(os.path.join(HERE, "shard_%d.json" % a.shard), "w"), ensure_ascii=False)
    print("ok=%d" % sum(1 for r in rows if r.get("ok")), flush=True)
