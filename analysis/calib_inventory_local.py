#!/usr/bin/env python3
"""Calibration inventory: local (already-collected) layers -> CSV records.

Sources scanned offline (zero network):
  DE  : raw-US-DE-v1  NAD / OA / TIGER-addrfeat / OVERTURE
  IA  : raw-US-IA-v1  NAD / OA / TIGER-addrfeat / OVERTURE
  NH  : raw-US-NH-granit-v1 (GRANIT parcel points) + raw-US-NH-v1 (TIGER addrfeat)
Sample: first 200 records per layer. Non-null rate denominator is explicit.
"""
import csv, glob, gzip, io, json, os, sys, zipfile, collections

SCRATCH = "/data/scratch/calib-20261123"
NHB = "/data/workspace/nh-collect-both"
NSAMP = 200
OUT = "/data/workspace/world-map-data-33/analysis/calib-inventory-20261123"
os.makedirs(OUT, exist_ok=True)

KEYNUM = ["number", "NUMBER", "Add_Number", "HOUSE_NUMBER", "LFROMHN", "address"]
KEYSTREET = ["street", "STREET", "St_Name", "FULLNAME", "streetaddress", "STREET_NAME"]
KEYCITY = ["postal_city", "CITY", "city", "town"]
KEYSTATE = ["state", "STATE", "State"]
KEYZIP = ["postcode", "ZIPCODE", "ZIPL", "zip"]
KEYCOUNTY = ["county", "County", "COUNTY", "county_fips", "county_name"]


def typ(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int,)):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, (list, dict)):
        return "json"
    return "str"


def summarize(records, extra_fields=None):
    """records: list[dict]. returns fields, sample non-null rate, 3 samples."""
    fields = collections.OrderedDict()
    n = len(records)
    for r in records:
        for k, v in r.items():
            if k not in fields:
                fields[k] = {"types": set(), "nonnull": 0}
            t = typ(v)
            fields[k]["types"].add(t)
            if v not in (None, "", [], {}):
                fields[k]["nonnull"] += 1
    out = []
    for k, meta in fields.items():
        out.append({"name": k, "types": "/".join(sorted(meta["types"])),
                    "nonnull": meta["nonnull"], "denom": n})
    return out, out


def pick(fields, candidates):
    names = [f["name"] for f in fields]
    for c in candidates:
        if c in names:
            return c
    low = {n.lower(): n for n in names}
    for c in candidates:
        if c.lower() in low:
            return low[c.lower()]
    return None


def rec_row(layer, state, source, method, geom, rows, rows_src, fields, samples, note=""):
    def rate(fn):
        n = pick(fields, fn)
        if not n:
            return ""
        f = next(x for x in fields if x["name"] == n)
        return f"{f['nonnull']}/{f['denom']}"
    return {
        "layer": layer, "state": state, "source": source, "method": method, "geom": geom,
        "rows": rows, "rows_source": rows_src,
        "n_fields": len(fields),
        "fields": ";".join(f"{f['name']}:{f['types']}" for f in fields),
        "sampled_n": fields[0]["denom"] if fields else 0,
        "nonnull_number": rate(KEYNUM), "nonnull_street": rate(KEYSTREET),
        "nonnull_city": rate(KEYCITY), "nonnull_state": rate(KEYSTATE),
        "nonnull_zip": rate(KEYZIP), "nonnull_county": rate(KEYCOUNTY),
        "samples": json.dumps(samples, ensure_ascii=False, default=str)[:600], "note": note,
    }


def scan_ndjson_gz(path):
    rows = 0
    recs = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            rows += 1
            if len(recs) < NSAMP:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                props = d.get("properties") if isinstance(d.get("properties"), dict) else d
                recs.append(props)
    return rows, recs


def scan_csv_zip(path):
    rows = 0
    recs = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            return 0, []
        with z.open(names[0]) as fh:
            rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
            for d in rd:
                rows += 1
                if len(recs) < NSAMP:
                    recs.append(dict(d))
    return rows, recs


def scan_tiger_zip(path):
    import shapefile
    rows = 0; recs = []
    with zipfile.ZipFile(path) as z:
        shp = [n for n in z.namelist() if n.endswith(".shp")][0]
        dbf = shp[:-4] + ".dbf"
        tmp = f"/tmp/_inv_{os.getpid()}"
        os.makedirs(tmp, exist_ok=True)
        base = os.path.join(tmp, "x")
        z.extract(shp, tmp); z.extract(dbf, tmp)
        r = shapefile.Reader(os.path.join(tmp, shp))
        rows = len(r)
        names = [f[0] for f in r.fields[1:]]
        for i, rec in enumerate(r.iterRecords()):
            if i >= NSAMP:
                break
            recs.append({n: rec[j] for j, n in enumerate(names)})
        r.close()
    return rows, recs


def scan_parquet(path):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    tbl = pf.read_row_group(0).slice(0, NSAMP)
    return pf.metadata.num_rows, tbl.to_pylist()


def main():
    out = []
    # ---------- DE / IA ----------
    for st, d in (("DE", f"{SCRATCH}/de"), ("IA", f"{SCRATCH}/ia")):
        status = json.load(open(f"{SCRATCH}/{st.lower()}/STATUS.json"))
        srows = {k: v.get("rows") for k, v in status.get("assets", {}).items()}
        for p in sorted(glob.glob(f"{d}/NAD-US-{st}-*.ndjson.gz")):
            try:
                rows, recs = scan_ndjson_gz(p)
            except Exception as e:
                out.append(dict(layer=os.path.basename(p), state=st, source="NAD", method="local",
                                geom="point", rows="", rows_source="read_error", n_fields=0, fields="",
                                sampled_n=0, nonnull_number="", nonnull_street="", nonnull_city="",
                                nonnull_state="", nonnull_zip="", nonnull_county="", samples="",
                                note=f"read_error={str(e)[:80]}")); continue
            fields, _ = summarize(recs)
            out.append(rec_row(os.path.basename(p), st, "NAD", "local", "point", rows, "file_read",
                               fields, recs[:3],
                               note=f"STATUS rows={srows.get(os.path.basename(p))}"))
        for p in sorted(glob.glob(f"{d}/OA-US-{st}-*.zip")):
            try:
                rows, recs = scan_csv_zip(p)
            except Exception as e:
                out.append(dict(layer=os.path.basename(p), state=st, source="OA", method="local",
                                geom="point", rows="", rows_source="read_error", n_fields=0, fields="",
                                sampled_n=0, nonnull_number="", nonnull_street="", nonnull_city="",
                                nonnull_state="", nonnull_zip="", nonnull_county="", samples="",
                                note=f"read_error={str(e)[:80]}")); continue
            fields, _ = summarize(recs)
            out.append(rec_row(os.path.basename(p), st, "OA", "local", "point", rows, "file_read",
                               fields, recs[:3]))
        for p in sorted(glob.glob(f"{d}/TIGER-US-{st}-*-addrfeat.zip")):
            try:
                rows, recs = scan_tiger_zip(p)
            except Exception as e:
                out.append(dict(layer=os.path.basename(p), state=st, source="TIGER", method="local",
                                geom="line", rows="", rows_source="read_error", n_fields=0, fields="",
                                sampled_n=0, nonnull_number="", nonnull_street="", nonnull_city="",
                                nonnull_state="", nonnull_zip="", nonnull_county="", samples="",
                                note=f"read_error={str(e)[:80]}")); continue
            fields, _ = summarize(recs)
            out.append(rec_row(os.path.basename(p), st, "TIGER", "local", "line", rows, "file_read",
                               fields, recs[:3]))
        for p in sorted(glob.glob(f"{d}/OVERTURE-US-{st}.parquet")):
            try:
                rows, recs = scan_parquet(p)
            except Exception as e:
                out.append(dict(layer=os.path.basename(p), state=st, source="OVERTURE", method="local",
                                geom="point", rows="", rows_source="read_error", n_fields=0, fields="",
                                sampled_n=0, nonnull_number="", nonnull_street="", nonnull_city="",
                                nonnull_state="", nonnull_zip="", nonnull_county="", samples="",
                                note=f"read_error={str(e)[:80]}")); continue
            fields, _ = summarize(recs)
            out.append(rec_row(os.path.basename(p), st, "OVERTURE", "local", "point", rows, "file_read",
                               fields, recs[:3]))
    # ---------- NH spine ----------
    for p in sorted(glob.glob(f"{NHB}/GRANIT-US-NH-*-parcel-points.ndjson.gz")) + [f"{NHB}/GRANIT-US-NH-parcel-points.ndjson.gz"]:
        rows, recs = scan_ndjson_gz(p)
        fields, _ = summarize(recs)
        out.append(rec_row(os.path.basename(p), "NH", "GRANIT", "local", "point", rows, "file_read",
                           fields, recs[:3], note="spine=parcel_centroid"))
    tg = sorted(glob.glob(f"{NHB}/tiger/TIGER-US-NH-addrfeat-interpolated-33*.ndjson.gz")) + [f"{NHB}/TIGER-US-NH-addrfeat-interpolated.ndjson.gz"]
    for p in tg:
        rows, recs = scan_ndjson_gz(p)
        fields, _ = summarize(recs)
        out.append(rec_row(os.path.basename(p), "NH", "TIGER-addrfeat", "local", "line", rows, "file_read",
                           fields, recs[:3], note="spine=interpolated"))
    # ---------- NH reference (non-spine) ----------
    for p in sorted(glob.glob(f"{SCRATCH}/nh/NAD-US-NH-*.ndjson.gz")):
        rows, recs = scan_ndjson_gz(p)
        fields, _ = summarize(recs)
        out.append(rec_row(os.path.basename(p), "NH", "NAD", "local", "point", rows, "file_read",
                           fields, recs[:3], note="non-spine (reference only)"))
    with open(f"{OUT}/inventory-local.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print("rows:", len(out), "->", f"{OUT}/inventory-local.csv")


if __name__ == "__main__":
    main()
