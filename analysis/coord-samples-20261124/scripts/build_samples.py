#!/usr/bin/env python3
"""把 extract/*.json 落成交付物：samples/<STATE>.csv、layers-status.csv、
unavailable.csv、summary.json。所有数字都从这里的 CSV 复算。

大桶（>SHARD 层，例如 _UNLOCATED 7,802 层）自动切片成 `<BUCKET>-partN.csv`，
避免单文件撞 GitHub 100MB 上限；切片只按层序号切，不丢行、不改口径。

  python3 build_samples.py                    # 全量
  python3 build_samples.py --states DE,NH,IA  # 只出三州
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = os.path.join(ROOT, "layers.json")
EXTRACT = os.environ.get("COORD_EXTRACT", "/data/coord-work-20261124/extract")
S = os.path.join(ROOT, "samples")
SHARD = 1500
COLS = ["layer_url", "layer_id", "state", "provider", "addr_fields_json", "lon", "lat",
        "lon_raw", "lat_raw", "wkid", "geom_type", "row_index", "sample_source"]


def key_of(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def bucket(state):
    s = (state or "").strip()
    if not s:
        return "_UNKNOWN"
    if s in ("未定位", "unknown", "UNKNOWN"):
        return "_UNLOCATED"
    return s


def rec_of(L):
    p = os.path.join(EXTRACT, f"d1_{key_of(L['url'])}.json" if L["universe"] == "d1"
                     else f"d2_{L['layer_id']}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", default="")
    a = ap.parse_args()
    only = {x.strip().upper() for x in a.states.split(",") if x.strip()}
    D = json.load(open(LAYERS))
    groups = defaultdict(list)
    for L in D["layers"]:
        b = bucket(L["state"])
        if only and b not in only:
            continue
        groups[b].append(L)
    os.makedirs(S, exist_ok=True)
    by_state = defaultdict(lambda: {"layers": 0, "ge50": 0, "partial": 0,
                                    "unavailable": 0, "rows": 0, "files": []})
    stat_rows, unavail, tally = [], [], defaultdict(int)
    rows_total = 0
    for b in sorted(groups):
        Ls = sorted(groups[b], key=lambda x: (x["url"] or x["layer_id"]))
        chunks = [Ls[i:i + SHARD] for i in range(0, len(Ls), SHARD)] or [[]]
        for ci, chunk in enumerate(chunks, 1):
            name = f"{b}.csv" if len(chunks) == 1 else f"{b}-part{ci}.csv"
            by_state[b]["files"].append(name)
            with open(os.path.join(S, name), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(COLS)
                for L in chunk:
                    rec = rec_of(L)
                    st = (rec or {}).get("status", "unavailable")
                    rows = (rec or {}).get("rows") or []
                    wkid = (rec or {}).get("wkid")
                    gt = (rec or {}).get("geom_type", "")
                    src = (rec or {}).get("sample_source", "")
                    reason = (rec or {}).get("reason", "") if rec else "not_sampled_yet"
                    tally[st] += 1
                    by_state[b]["layers"] += 1
                    by_state[b]["rows"] += len(rows)
                    rows_total += len(rows)
                    by_state[b]["ge50" if st == "ok" else
                               "partial" if st == "partial" else "unavailable"] += 1
                    for r in rows:
                        w.writerow([L["url"], L["layer_id"], b, L["provider"],
                                    json.dumps(r["addr_fields"], ensure_ascii=False,
                                               separators=(",", ":")),
                                    r["lon"], r["lat"], r["lon_raw"], r["lat_raw"],
                                    wkid if wkid is not None else "", gt, r["row_index"], src])
                    stat_rows.append({"layer_id": L["layer_id"], "layer_url": L["url"],
                                      "state": b, "universe": L["universe"],
                                      "provider": L["provider"], "status": st,
                                      "rows": len(rows), "wkid": wkid or "",
                                      "geom_type": gt, "sample_source": src, "reason": reason})
                    if st == "unavailable":
                        unavail.append({"layer_url": L["url"], "layer_id": L["layer_id"],
                                        "state": b, "universe": L["universe"], "reason": reason,
                                        "http_code": (rec or {}).get("http_code", ""),
                                        "attempts": (rec or {}).get("attempts", 0)})
    with open(os.path.join(ROOT, "layers-status.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(stat_rows[0].keys()) if stat_rows else ["layer_id"])
        w.writeheader()
        w.writerows(stat_rows)
    with open(os.path.join(ROOT, "unavailable.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["layer_url", "layer_id", "state", "universe",
                                          "reason", "http_code", "attempts"])
        w.writeheader()
        w.writerows(unavail)
    order = sorted(stat_rows, key=lambda r: (r["state"], r["layer_url"]))
    with open(os.path.join(ROOT, "layers-status.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(order[0].keys()) if order else ["layer_id"])
        w.writeheader()
        w.writerows(order)
    summary = {"denominator": D["denominator"],
               "layers_total": len(stat_rows),
               "layers_sampled_ge50": tally["ok"],
               "layers_sampled_partial": tally["partial"],
               "layers_unavailable": tally["unavailable"],
               "rows_total": rows_total,
               "by_state": dict(sorted(by_state.items())),
               "target_rows_per_layer": 50,
               "shard_layers_max": SHARD,
               "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if not only:
        with open(os.path.join(ROOT, "summary.json"), "w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
    else:
        summary["scope"] = "3STATES"
        summary["states_in_scope"] = sorted(only)
        del summary["denominator"]
        summary = {"denominator": D["denominator"], **summary}
        with open(os.path.join(ROOT, "summary-3states.json"), "w") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps({"layers_written": len(stat_rows), "rows_total": rows_total,
                      "tally": dict(tally),
                      "closed": sum(tally.values()) == len(stat_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
