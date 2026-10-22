import csv, json, re
rows = list(csv.DictReader(open("clean.csv")))
out = []
for r in rows:
    u = r.get("api_url") or ""
    if not u: continue
    out.append({"state": r["state"], "title": r["title"], "url": u, "svc": r["service"],
                "geom": r["geom"], "count": r["count"], "cov": r["cov"], "nfields": r["nfields"],
                "has_point": r["has_point"], "provider": r["provider"], "license": r["license"]})
json.dump(out, open("layers.json", "w"), ensure_ascii=False)
print("layers", len(out))
