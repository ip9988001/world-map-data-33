#!/usr/bin/env python3
"""NG911 remote layers: pull 20 samples and measure address-field usability.

The field->role map below is hand-curated from each layer's real `fields` list
(dumped by calib_remote_count.py); no guessing is done at runtime — every name in
the map must exist in the layer metadata or the layer is reported as a map error.

One request per layer (resultRecordCount=20), read-only.
Writes /tmp/calib_remote_fields.json
"""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

PROBE = json.load(open("/tmp/calib_remote_probe.json"))
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

MAP = {
    295: dict(number="addr_housenumber", street="addr_street", city="addr_city", state="addr_state", zip="addr_postcode"),
    297: dict(number="ADDRNUM", street="FULLNAME", city="MUNICIPALITY", state="STATE", zip="ZIP_5"),
    298: dict(number="AddressNumber", street="StreetName", city="CADCityCode", state=None, zip="Zipcode"),
    299: dict(number="Address_Number", street="StName", city="Municipality", state=None, zip="ZIP"),
    300: dict(number="addr_housenumber", street="addr_street", city="addr_city", state="addr_state", zip="addr_postcode"),
    301: dict(number="Addr_Num", street="Addr_St", city="City", state=None, zip="Zipcode"),
    302: dict(number="ADDRNUM", street="FULLNAME", city="MUNICIPALITY", state=None, zip=None),
    303: dict(number="addr_housenumber", street="addr_street", city="addr_city", state="addr_state", zip="addr_postcode"),
    304: dict(number="ADDRNUM", street="FULLNAME", city="POSTAL_CITY", state="STATE", zip="ZIPCODE"),
    305: dict(number="HOUSENUMBE", street="STREETNAME", city="CITY", state="STATE", zip="ZIP_CODE"),
    306: dict(number="ADDR_NUMBER", street="STREET_NAME", city="POSTAL_CITY", state="STATE", zip="ZIP"),
    307: dict(number="ADDRESSNUM", street="ADDRESSSTR", city="JURISDICTI", state=None, zip=None),
    308: dict(number="ADDRNUM", street="FULLNAME", city="MUNICIPALITY", state=None, zip=None),
    309: dict(number="ADDRNUM", street="FULLNAME", city="MUNICIPALITY", state=None, zip=None),
    313: dict(number="AddrNum", street="StreetName", city=None, state=None, zip="ZipCode"),
}
# what the row was labelled as (state the 000199 pick claimed), for mismatch detection
DECLARED_STATE = {r["idx"]: r["state"] for r in PROBE}


def q(url, timeout=120):
    u = url + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "outFields": "*", "resultRecordCount": 20, "f": "json"})
    req = urllib.request.Request(u, headers={"User-Agent": "pi-calib/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read()), r.status, ""
    except urllib.error.HTTPError as e:
        return None, e.code, f"HTTPError {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, 0, f"{type(e).__name__}: {str(e)[:120]}"


def rate(v):
    return v not in (None, "", " ", "  ")


out = []
for rec in PROBE:
    idx, url = rec["idx"], rec["url"]
    m = MAP[idx]
    fields = rec["fields"]
    bad = [k for k, v in m.items() if v and v not in fields]
    d, http, err = q(url)
    feats = (d or {}).get("features", []) if isinstance(d, dict) else []
    attrs = [f.get("attributes", {}) for f in feats]
    n = len(attrs)
    stats = {}
    for role, fname in m.items():
        stats[role] = (sum(1 for a in attrs if rate(a.get(fname))) if fname and n else None)
    state_vals = sorted({str(a.get(m["state"])) for a in attrs if m["state"] and rate(a.get(m["state"]))}) if m["state"] and n else []
    # does the sample look like the state we filed it under?
    geo_hint = {k: v for k, v in (attrs[0].items() if attrs else []) if k.lower() in
                ("state", "st", "addr_state", "addresscou", "addr_statecode") and rate(v)}
    row = {"idx": idx, "state_declared": DECLARED_STATE[idx], "count": rec["count"], "url": url,
           "meta_name": rec["name"], "title": rec["layer"], "n_fields": rec["n_fields"],
           "sample_http": http, "sample_err": err, "sampled_n": n,
           "field_map": m, "map_missing_fields": bad, "nonnull": stats,
           "state_field_values": state_vals[:6], "state_field_distinct": len(state_vals),
           "sample1": {k: v for k, v in (attrs[0].items() if attrs else []) if rate(v)}}
    out.append(row)
    print(f"[{idx}] {DECLARED_STATE[idx]:2s} n={n} http={http} miss={bad} "
          f"nn={ {k: (None if v is None else f'{v}/{n}') for k, v in stats.items()} }", flush=True)

json.dump(out, open("/tmp/calib_remote_fields.json", "w"), ensure_ascii=False, indent=1)
print("wrote /tmp/calib_remote_fields.json", len(out))
