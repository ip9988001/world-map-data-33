#!/usr/bin/env python3
"""Rebuild the 20 NG911 calibration layers (picked.txt missing) + resolve collected status."""
import csv, gzip, json, re, collections, os

REPO = "/data/workspace/world-map-data-33"
NUMRE = re.compile(r'(HOUSE_?NUM|ADDR(ESS)?_?NUM|^NUMBER$|^ADDRNUM$|^NUM$)', re.I)
STRRE = re.compile(r'(STREET|ROAD|FULL_?ADDR|ADDRESS)', re.I)

STATES = {
 "Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO",
 "Connecticut":"CT","Delaware":"DE","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID",
 "Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA",
 "Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS",
 "Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ",
 "New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK",
 "Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD",
 "Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA",
 "West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}

def load_candidates():
    out = []
    with gzip.open(f"{REPO}/survey/ng911/samples.csv.gz", "rt", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if r.get("geom") != "esriGeometryPoint": continue
            fs = [x for x in (r["fields"] or "").split(";") if x]
            if not fs or not r.get("samples") or r["samples"] in ("[]", ""): continue
            if not any(NUMRE.search(x) for x in fs): continue
            if not any(STRRE.search(x) for x in fs): continue
            try: c = int(r["count"] or 0)
            except Exception: c = 0
            if c <= 0: continue
            blob = (r["title"] + " " + r["url"]).lower()
            if r["state"] not in STATES.values(): continue
            if re.search(r"(drive time|soil|network asset|parcel|boundar|traffic|elevation|hydro|wetland|"
                         r"school|transit|snow|emergency service zone|zip code tabulation|broadband|fire station|"
                         r"building info|temporary|water|sewer|police|hospital|park)", blob): continue
            if re.search(r"(united states|europe|openstreetmap|usa_)", blob): continue
            svc = r["url"].rstrip("/").split("/")[-3] if r["url"].count("/") >= 3 else ""
            strict = bool(re.search(r"(?i)(addr|e911|911|situs|site)", svc + " " + r["title"]))
            try:
                smp = json.loads(r["samples"])
            except Exception:
                continue
            if not smp: continue
            okv = False
            for rec in smp[:3]:
                vals = list(rec.values())
                has_num = any(isinstance(v, (int, float)) and v > 0 for v in vals)
                has_str = any(isinstance(v, str) and len(v.strip()) >= 5 and re.search(r"[A-Za-z]{3}", v) for v in vals)
                if has_num and has_str: okv = True; break
            if not okv: continue
            foreign = [ab for name, ab in STATES.items()
                       if ab not in (r["state"], "US") and re.search(r"\b" + name.lower().replace(" ", r"[_ ]") + r"\b", blob)]
            nm = STATES and [n for n, ab in STATES.items() if ab == r["state"]][0]
            aff = 1 if (nm.lower() in blob or re.search(r"\b" + r["state"].lower() + r"\b", blob)) else 0
            out.append({"state": r["state"], "title": r["title"].strip(), "url": r["url"], "count": c, "affinity": aff, "strict": strict,
                        "cov": float(r["cov"] or 0), "provider": r["provider"], "fields": r["fields"],
                        "samples": r["samples"], "svc": r["svc"], "foreign": foreign})
    return out

def main():
    cands = load_candidates()
    clean = [c for c in cands if not c["foreign"]]
    relaxed_by = collections.defaultdict(list)
    for c in clean: relaxed_by[c["state"]].append(c)
    strict_by = collections.defaultdict(list)
    for c in clean:
        if c.get("strict"): strict_by[c["state"]].append(c)
    best = {st: max(v, key=lambda c: (c["count"], c["cov"])) for st, v in strict_by.items()}
    for st in ("DE", "NH", "IA"):
        pool = [c for c in relaxed_by.get(st, []) if re.search(r"(?i)address", c["title"])] or relaxed_by.get(st, [])
        if st not in best and pool:
            best[st] = max(pool, key=lambda c: (c["count"], c["cov"]))
    ranked = sorted(best.values(), key=lambda c: -c["count"])
    must = [best[s] for s in ("DE", "NH", "IA") if s in best]
    picks = list(must)
    for c in ranked:
        if len(picks) >= 20: break
        if c in picks: continue
        picks.append(c)
    # url -> layer_id from plan csv
    key = {}
    with open(f"{REPO}/collect/layer_plan_clean.csv", newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f):
            key[row["url"].rstrip("/")] = row["layer_id"]
    led = {}
    for fn in ("collect/05b_ledger.json", "collect/07b_ledger.json"):
        d = json.load(open(f"/data/workspace/wmd-merge/{fn}"))
        for rec in d["records"]:
            led.setdefault(rec["layer"], {"stage": d["stage"], "status": rec.get("status"),
                                          "rows": rec.get("rows"), "declared": rec.get("declared")})
    out = []
    for c in picks:
        lid = key.get(c["url"].rstrip("/"))
        coll = led.get(lid) if lid else None
        out.append({**c, "layer_id": lid, "collected": coll,
                    "method": "local" if coll else "remote"})
    json.dump({"rule": "geom=esriGeometryPoint ∧ fields 含 number∧street ∧ samples 非空 ∧ count>0 ∧ "
                       "title/url 不含他州州名；每州取 count 最大（并列取 cov 大）；DE/NH/IA 必含 + 其余按 count 取前 17",
               "candidates_total": len(cands), "candidates_after_guard": len(clean),
               "states_with_candidate": len(strict_by), "picked_n": len(out), "picked": out},
              open("/tmp/ng911_20.json", "w"), ensure_ascii=False, indent=1)
    for c in out:
        print(f"{c['state']} {c['count']:>9} {c['title'][:38]:38s} {'LOCAL' if c['collected'] else 'remote'} {c['url'][:70]}")

if __name__ == "__main__":
    main()
