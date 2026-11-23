"""Calibration sandbox: stateless address-layer rules (S/A/B/C + field-signature groups).

Discipline (hard):
  * pure functions, no persistence, no DB, no network
  * never imports any production collection/fusion/refinement module
  * ~200 lines, hard cap 300
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import zipfile

# ---------------------------------------------------------------- field aliases
ALIASES = {
    "number": ["number", "house_number", "housenum", "add_number", "addrnum", "address_number",
               "addnum", "house_no", "hno", "num", "building"],
    "street": ["street", "street_name", "st_name", "stnam_full", "fullname", "road", "streetaddress",
               "street_address", "addr_street", "road_name", "streetname"],
    "city": ["city", "postal_city", "town", "municipality", "place", "city_name", "post_office"],
    "state": ["state", "st", "state_abbr", "state_code", "province"],
    "zip": ["zip", "postcode", "zipcode", "zip_code", "postal_code", "zipl", "zipr", "zipplus4"],
    "county": ["county", "county_name", "countyid", "county_fips", "countyname", "parish"],
    "lon": ["lon", "longitude", "x", "xcoord", "long"],
    "lat": ["lat", "latitude", "y", "ycoord"],
}

SUFFIX = {"ST": "STREET", "RD": "ROAD", "LN": "LANE", "DR": "DRIVE", "AVE": "AVENUE",
          "BLVD": "BOULEVARD", "CT": "COURT", "PL": "PLACE", "TER": "TERRACE", "TRL": "TRAIL",
          "HWY": "HIGHWAY", "RT": "ROUTE", "RTE": "ROUTE", "CIR": "CIRCLE", "PKWY": "PARKWAY",
          "N": "NORTH", "S": "SOUTH", "E": "EAST", "W": "WEST"}

GROUPS = ("full_address", "no_zip", "no_city", "no_number", "road_only", "empty_shell")


def _norm_key(k: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or v == [] or v == {}


def canonical(rec: dict) -> dict:
    """Map an arbitrary record onto the canonical 8-field address shape.

    Pure: returns a new dict, never mutates the input.
    """
    by_norm = {_norm_key(k): v for k, v in rec.items()}
    out = {}
    for canon, names in ALIASES.items():
        val = None
        for n in names:
            nk = _norm_key(n)
            if nk in by_norm and not _blank(by_norm[nk]):
                val = by_norm[nk]
                break
        out[canon] = val
    return out


def norm_street(value) -> str:
    s = re.sub(r"[^A-Z0-9 ]+", " ", str(value or "").upper())
    return " ".join(SUFFIX.get(t, t) for t in s.split())


def street_key(rec: dict) -> str:
    c = canonical(rec) if rec else {}
    return norm_street(c.get("street"))


def has_number(rec: dict) -> bool:
    c = canonical(rec)
    if _blank(c["number"]):
        return False
    return bool(re.search(r"\d", str(c["number"])))


def classify(rec: dict) -> str:
    """S/A/B/C rule (pure).

    S = number + street + city + state + zip + coordinates
    A = number + street, but missing zip and/or city
    B = street only when number is present?  -> B = missing number AND zip
    C = street/road only (no number, no zip and no city/state completeness)
    """
    c = canonical(rec)
    num = has_number(rec)
    street = bool(c["street"])
    city = bool(c["city"])
    state = bool(c["state"])
    zp = bool(c["zip"])
    geo = c["lon"] is not None and c["lat"] is not None
    if num and street and city and state and zp and geo:
        return "S"
    if num and street:
        return "A"
    if street and not num:
        return "B" if (city or zp or state) else "C"
    return "C"


def field_group(rec: dict) -> str:
    """Field-signature family used by the grouping algorithm."""
    c = canonical(rec)
    num, street = has_number(rec), bool(c["street"])
    city, state, zp = bool(c["city"]), bool(c["state"]), bool(c["zip"])
    geo = c["lon"] is not None and c["lat"] is not None
    if not street and not num:
        return "empty_shell"
    if not num:
        return "road_only"
    if num and street and city and state and zp and geo:
        return "full_address"
    if not zp:
        return "no_zip"
    if not city:
        return "no_city"
    if not num:
        return "no_number"
    return "no_city"


def nonnull_rate(records, field: str, denom: int | None = None) -> dict:
    """Explicit-denominator non-null rate. denom defaults to len(records) but is never inferred silently."""
    recs = list(records)
    d = len(recs) if denom is None else int(denom)
    if d <= 0:
        return {"field": field, "nonnull": 0, "denom": 0, "rate": 0.0}
    n = sum(1 for r in recs if not _blank(canonical(r).get(field, r.get(field))))
    return {"field": field, "nonnull": n, "denom": d, "rate": round(n / d, 4)}


def group_layers(layer_records: dict) -> dict:
    """{layer: [records]} -> {group: [layers]} plus counts."""
    out = {g: [] for g in GROUPS}
    for layer, recs in layer_records.items():
        votes = {}
        for r in recs:
            g = field_group(r)
            votes[g] = votes.get(g, 0) + 1
        out[max(votes, key=votes.get) if votes else "empty_shell"].append(layer)
    return {"groups": out, "counts": {g: len(v) for g, v in out.items()}}


def layer_profile(name: str, records, declared_rows=None, geometry=None) -> dict:
    recs = list(records)
    n = len(recs)
    cls = {}
    for r in recs:
        k = classify(r)
        cls[k] = cls.get(k, 0) + 1
    return {
        "layer": name,
        "declared_rows": declared_rows,
        "sampled_n": n,
        "geometry": geometry,
        "class_mode": max(cls, key=cls.get) if cls else "C",
        "class_counts": cls,
        "group": field_group(recs[0]) if recs else "empty_shell",
        "nonnull": {f: nonnull_rate(recs, f, n)["rate"] for f in ALIASES},
        "fields_left": sorted({k for r in recs for k in r})[:40],
    }


# ------------------------------------------------------------------ readers
def read_ndjson_gz(path: str, limit: int = 200) -> list:
    out = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(out) >= limit:
                break
            try:
                d = json.loads(line)
            except Exception:
                continue
            out.append(d.get("properties") if isinstance(d.get("properties"), dict) else d)
    return out


def read_csv_zip(path: str, limit: int = 200) -> list:
    with zipfile.ZipFile(path) as z:
        name = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
        if not name:
            return []
        with z.open(name) as fh:
            rd = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"))
            out = []
            for row in rd:
                if len(out) >= limit:
                    break
                out.append(dict(row))
            return out


def read_remote_json(payload: dict) -> list:
    feats = payload.get("features") or []
    return [f.get("attributes", f) for f in feats]
