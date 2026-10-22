#!/usr/bin/env python3
import csv, json, re, collections
def num(v):
    try: return int(float(v))
    except Exception: return 0
rows = list(csv.DictReader(open("clean.csv")))
REL = re.compile(r"address\s*point|site\s*address|situshub|structure\s*address|e?911.*address|address.*911|addresses|address locations|NG911|AddressPoint|Address_Points", re.I)
JUNK = re.compile(r"permit|business|mining|waterbody|soil|broadband|highway network|postmile|census block|snap|food|health|inlet|shelter|trail|parcel point", re.I)
def good(r):
    t = r["title"] or ""
    return (REL.search(t) and not JUNK.search(t) and r["geom"] == "esriGeometryPoint"
            and r.get("has_point") == "True" and num(r["count"]) > 500
            and r.get("cov") and float(r["cov"]) >= 0.3)
best = {}
for r in rows:
    if not good(r): continue
    st = r["state"]
    if st not in best or num(r["count"]) > num(best[st]["count"]):
        best[st] = r
print("州数有可用全州级点层:", len(best))
tot = 0
for st in sorted(best):
    r = best[st]; c = num(r["count"]); tot += c
    print("%-3s %-11s %-4s %s" % (st, format(c, ","), r["nfields"] + "f", (r["title"] or "")[:52]))
print("合计", format(tot, ","))
missing = [ab for ab in "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split() if ab not in best]
print("缺:", " ".join(missing), len(missing))
json.dump([{"st": k, "count": num(v["count"]), "title": v["title"], "url": v["api_url"],
            "fields": v["nfields"], "license": v["license"], "geom": v["geom"]} for k, v in sorted(best.items())],
          open("state_best.json", "w"), ensure_ascii=False, indent=1)
