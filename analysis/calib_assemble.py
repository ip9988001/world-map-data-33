#!/usr/bin/env python3
"""Assemble calibration inventory: local + NG911(20) + dirty(15) -> csv + md + grouping."""
import csv, json, os, sys, collections

sys.path.insert(0, "/data/workspace/world-map-data-33/sandbox")
import rules

BASE = "/data/workspace/world-map-data-33"
OUT = f"{BASE}/analysis/calib-inventory-20261123"
WMD = "/data/workspace/wmd-merge"

def load_dirty():
    gap = json.load(open(f"{WMD}/analysis/05b-gap-classification-2026-10-31.json"))
    rows = []
    for l in gap["layers"]:
        rows.append({"layer": l["layer"], "evidence": "analysis/05b-gap-classification-2026-10-31.json",
                     "type": {"partial": "partial", "unverified": "404_upstream_dead",
                              "upstream_unstable": "upstream_unstable", "missing": "missing"}[l["class"]],
                     "rows": l.get("rows"), "declared": l.get("declared")})
    # duplicates (2x) — from d15 ack / attempt logs where present
    for fn, tag in (("analysis/05b-attempt-log.json", "05b"), ("analysis/07b-attempt-log.json", "07b")):
        p = f"{WMD}/{fn}"
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        beats = d.get("layers") or d.get("records") or d.get("attempts") or []
        if isinstance(beats, dict):
            beats = list(beats.values())
        for b in beats:
            if not isinstance(b, dict):
                continue
            name = b.get("layer") or b.get("name")
            kinds = json.dumps(b.get("failure_kinds") or b.get("err") or "", ensure_ascii=False)
            if not name:
                continue
            if "dup" in kinds.lower() or (b.get("rows") and b.get("declared") and b["rows"] > b["declared"] * 1.5):
                rows.append({"layer": name, "evidence": fn, "type": "duplicate_2x",
                             "rows": b.get("rows"), "declared": b.get("declared")})
    seen, out = set(), []
    for r in rows:
        if r["layer"] in seen:
            continue
        seen.add(r["layer"]); out.append(r)
    return out[:15]

def main():
    loc = list(csv.DictReader(open(f"{OUT}/inventory-local.csv")))
    ng = json.load(open(f"{OUT}/inventory-ng911.json"))
    dirty = load_dirty()

    records = []
    for r in loc:
        records.append({**r, "evidence": "release asset (see rows_source)"})
    for r in ng:
        if r.get("rows") is True:
            r["rows"] = None
        records.append({**r, "evidence": "survey/ng911 + 2-request probe"})
    for r in dirty:
        records.append({"layer": r["layer"], "state": "", "source": "NG911(dirty)", "method": "ledger",
                        "geom": "", "rows": r.get("rows"), "rows_source": r["evidence"],
                        "n_fields": "", "fields": "", "sampled_n": 0, "nonnull_number": "",
                        "nonnull_street": "", "nonnull_city": "", "nonnull_state": "", "nonnull_zip": "",
                        "nonnull_county": "", "samples": "", "note": f"type={r['type']} declared={r.get('declared')}",
                        "evidence": r["evidence"]})

    cols = ["layer", "state", "source", "method", "geom", "rows", "rows_source", "n_fields", "fields",
            "sampled_n", "nonnull_number", "nonnull_street", "nonnull_city", "nonnull_state",
            "nonnull_zip", "nonnull_county", "samples", "note"]
    with open(f"{OUT}/calib-inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(records)

    # grouping: pull the full sample rows from the survey csv (url keyed)
    import gzip, re
    survey = {}
    with gzip.open(f"{BASE}/survey/ng911/samples.csv.gz", "rt", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            try:
                survey[r["url"].rstrip("/")] = json.loads(r["samples"])
            except Exception:
                pass
    layer_recs = {}
    for r in ng:
        m = re.search(r"url=(\S+)$", r.get("note") or "")
        url = m.group(1).rstrip("/") if m else None
        smp = survey.get(url) or []
        if smp:
            layer_recs[r["layer"]] = smp
    g = rules.group_layers(layer_recs)
    cls = collections.Counter()
    for layer, recs in layer_recs.items():
        p = rules.layer_profile(layer, recs)
        cls[p["class_mode"]] += 1
        g["groups"][p["group"]].append(layer) if layer not in g["groups"][p["group"]] else None
    json.dump({"group_counts": {k: len(v) for k, v in g["groups"].items()},
               "groups": g["groups"], "class_counts": dict(cls)},
              open(f"{OUT}/grouping.json", "w"), ensure_ascii=False, indent=1)

    per = collections.Counter((r["state"], r["source"]) for r in records)
    md = [f"# 校准集逐层盘点（{len(records)} 条）\n",
          "| 州 | 源 | 层数 |", "|---|---|---|"]
    for (st, src), n in sorted(per.items()):
        md.append(f"| {st or '—'} | {src} | {n} |")
    md += ["", f"合计 **{len(records)}** 条（local {sum(1 for r in records if r['method']=='local')} / "
               f"remote {sum(1 for r in records if r['method']=='remote')} / ledger {sum(1 for r in records if r['method']=='ledger')}）", "",
           "## 分组输出（NG911 20 层）", "", "| 组 | 层数 |", "|---|---|"]
    for k, v in g["groups"].items():
        md.append(f"| {k} | {len(v)} |")
    md += ["", "## 分层输出（S/A/B/C）", "", "| 级别 | 层数 |", "|---|---|"]
    for k, v in sorted(cls.items()):
        md.append(f"| {k} | {v} |")
    open(f"{OUT}/calib-inventory.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("records", len(records), "groups", {k: len(v) for k, v in g["groups"].items()}, "classes", dict(cls))

if __name__ == "__main__":
    main()
