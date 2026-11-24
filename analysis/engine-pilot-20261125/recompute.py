#!/usr/bin/env python3
"""复算脚本：只读 graded.ndjson.gz / tiger-streets.csv.gz / stats.json，重算报告里所有数字。

  python3 analysis/engine-pilot-20261125/recompute.py      # 打印 + 写 recompute-stats.json
不依赖引擎、不依赖 sqlite：只用产物文件，保证「报告里每个数字都能从产物复算」。
"""
import collections
import glob
import gzip
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = ("DE", "NH", "IA")
GRADES = ("S", "A", "B", "C")
TIERS = ("tier1", "tier2", "tier3", "unrated")


def main() -> int:
    out = {"states": {}, "totals": collections.Counter()}
    for st in STATES:
        parts = sorted(glob.glob(os.path.join(HERE, st, "graded.part*.ndjson.gz")))
        p = parts[0] if parts else os.path.join(HERE, st, "graded.ndjson.gz")
        if not parts and not os.path.isfile(p):
            out["states"][st] = {"status": "not_run"}
            continue
        n = with_point = multi = interp = conflict = 0
        picks = {}
        grid = collections.defaultdict(lambda: collections.Counter())
        by_family = collections.Counter()
        for line in itertools.chain.from_iterable(gzip.open(x, "rt", encoding="utf-8") for x in (parts or [p])):
            r = json.loads(line)
            n += 1
            grid[r.get("tier") or "unrated"][r.get("grade") or "X"] += 1
            with_point += r.get("lon") is not None
            multi += int(r.get("n_sources") or 1) > 1
            interp += int(r.get("is_interpolated") or 0)
            conflict += int(r.get("coord_conflict") or 0)
            by_family[r.get("source_family") or "?"] += 1
            cell = (r.get("tier") or "unrated", r.get("grade") or "X")
            if picks.setdefault(cell, []) is not None and len(picks[cell]) < 3:
                picks[cell].append({k: r.get(k) for k in ("addrkey", "number", "street", "city", "zip5",
                                                          "state", "lon", "lat", "tier", "grade",
                                                          "n_sources", "precision", "source_family")})
        side = json.load(open(os.path.join(HERE, st, "stats.json"), encoding="utf-8"))
        ts = os.path.join(HERE, st, "tiger-streets.csv.gz")
        tiger_keys = max(0, sum(1 for _ in gzip.open(ts, "rt", encoding="utf-8")) - 1) if os.path.isfile(ts) else 0
        with open(os.path.join(HERE, st, "samples-by-tier-grade.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            import csv as _csv
            w = _csv.DictWriter(fh, fieldnames=["tier", "grade", "addrkey", "number", "street", "city",
                                                "zip5", "state", "lon", "lat", "n_sources",
                                                "precision", "source_family"])
            w.writeheader()
            for (t, g), rs in sorted(picks.items()):
                for r in rs:
                    w.writerow({**{k: r.get(k, "") for k in w.fieldnames}, "tier": t, "grade": g})
        out["states"][st] = {
            "rows_in": side.get("rows_in"), "deduped_rows": n, "dup_rows": side.get("dup_rows"),
            "unkeyed_rows": side.get("unkeyed_rows"), "dropped_low_grade": side.get("dropped_low_grade"),
            "dropped_out_of_state": side.get("dropped_out_of_state"),
            "with_point": with_point, "multi_source": multi, "interpolated": interp,
            "coord_conflict": conflict,
            "by_grade": {g: sum(v[g] for v in grid.values()) for g in GRADES},
            "by_tier": {t: sum(grid[t].values()) for t in TIERS},
            "grid": {t: {g: grid[t][g] for g in GRADES} for t in TIERS},
            "samples_written": sum(len(v) for v in picks.values()),
            "sources": side.get("sources"), "tiger_street_keys": tiger_keys,
            "by_family": dict(by_family),
        }
        out["totals"]["rows_in"] += side.get("rows_in") or 0
        out["totals"]["deduped_rows"] += n
        out["totals"]["dup_rows"] += side.get("dup_rows") or 0
    out["totals"] = dict(out["totals"])
    json.dump(out, open(os.path.join(HERE, "recompute-stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"totals": out["totals"],
                      "per_state": {k: {kk: vv for kk, vv in v.items()
                                        if kk in ("rows_in", "deduped_rows", "by_grade", "by_tier")}
                                    for k, v in out["states"].items()}}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
