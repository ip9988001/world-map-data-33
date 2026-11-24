#!/usr/bin/env python3
"""NG911 20 layers: 2-request probe (remote) or offline survey sample (local)."""
import csv, gzip, json, re, time, urllib.parse, urllib.request, os

REPO = "/data/workspace/world-map-data-33"
OUT = f"{REPO}/analysis/calib-inventory-20261123"
os.makedirs(OUT, exist_ok=True)
PICKS = json.load(open("/tmp/ng911_20.json"))["picked"]

def http(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "pi-calib/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def probe(url):
    rec = {"geo": "", "declared": None, "fields": [], "samples": [], "err": ""}
    try:
        meta = http(url + "?f=json")
        rec["geo"] = meta.get("geometryType", "")
        rec["declared"] = meta.get("count") or meta.get("featureCount")
        rec["fields"] = [(f.get("name"), f.get("type")) for f in meta.get("fields", [])]
        q = url + "/query?" + urllib.parse.urlencode({
            "where": "1=1", "outFields": "*", "resultRecordCount": 20, "f": "json"})
        d = http(q)
        feats = d.get("features", [])
        rec["samples"] = [f.get("attributes", {}) for f in feats]
        if rec["declared"] is None:
            rec["declared"] = None  # count not advertised by this service
    except Exception as e:
        rec["err"] = str(e)[:200]
    return rec

def main():
    rows = []
    for p in PICKS:
        url = p["url"].rstrip("/")
        if p["collected"]:
            samples = json.loads(p["samples"]) if p["samples"] else []
            fields = [tuple(x.split(":", 1)) if ":" in x else (x, "") for x in (p["fields"] or "").split(";") if x]
            rows.append({"layer": p["title"], "state": p["state"], "source": "NG911",
                         "method": "local", "geom": "esriGeometryPoint", "rows": p["count"],
                         "rows_source": "survey_samples_csv", "n_fields": len(fields),
                         "fields": ";".join(f"{a}:{b}" for a, b in fields),
                         "sampled_n": len(samples), "nonnull_number": "", "nonnull_street": "",
                         "nonnull_city": "", "nonnull_state": "", "nonnull_zip": "", "nonnull_county": "",
                         "samples": json.dumps(samples[:3], ensure_ascii=False)[:600],
                         "note": f"ledger={p['collected']['stage']} status={p['collected']['status']} url={url}"})
        else:
            pr = probe(url)
            rows.append({"layer": p["title"], "state": p["state"], "source": "NG911",
                         "method": "remote", "geom": pr["geo"].replace("esriGeometry", ""), "rows": pr["declared"],
                         "rows_source": "remote_count", "n_fields": len(pr["fields"]),
                         "fields": ";".join(f"{a}:{b}" for a, b in pr["fields"]),
                         "sampled_n": len(pr["samples"]), "nonnull_number": "", "nonnull_street": "",
                         "nonnull_city": "", "nonnull_state": "", "nonnull_zip": "", "nonnull_county": "",
                         "samples": json.dumps(pr["samples"][:3], ensure_ascii=False)[:600],
                         "note": f"probe_err={pr['err']} url={url}"})
            print(f"{p['state']} {p['title'][:40]:40s} geo={pr['geo']} n={pr['declared']} err={pr['err'][:60]}", flush=True)
    json.dump(rows, open(f"{OUT}/inventory-ng911.json", "w"), ensure_ascii=False, indent=1)
    print("wrote", len(rows))

if __name__ == "__main__":
    main()
