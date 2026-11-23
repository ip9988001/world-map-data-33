#!/usr/bin/env python3
"""NG911 remote layers: fill real counts (returnCountOnly) + qualify the probe_err.

For each remote layer URL:
  1. GET  <url>?f=json                       -> metadata (HTTP code, advertised keys)
  2. GET  <url>/query?where=1=1&returnCountOnly=true&f=json
  3. GET  <url>/query?where=1=1&returnIdsOnly=true&f=json   (fallback: len(objectIds))
  4. GET  <url>/query?where=1=1&outFields=*&resultRecordCount=20&f=json  (sample usability)

Writes /tmp/calib_remote_probe.json (raw evidence) and prints one line per layer.
Read-only: no writes outside /tmp, no service mutation, 2-4 requests per layer.
"""
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URLS = json.load(open("/tmp/calib_remote_urls.json"))
OUT = "/tmp/calib_remote_probe.json"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

NUM_KEYS = ("number", "num", "housenum", "housenumber", "addrnum", "addnum", "situsnum", "streetnum")
STREET_KEYS = ("street", "stname", "st_name", "road", "thoroughfare", "addstreet", "fulladdr", "address")
CITY_KEYS = ("city", "municipality", "muni", "postcity", "comm")
STATE_KEYS = ("state", "st", "statecode")
ZIP_KEYS = ("zip", "postcode", "postal")


def http(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "pi-calib/1.0", "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            body = r.read()
            return {"http": r.status, "body": body, "ms": int((time.time() - t0) * 1000), "err": ""}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read()[:4000], "ms": int((time.time() - t0) * 1000), "err": f"HTTPError {e.code} {e.reason}"}
    except Exception as e:  # noqa: BLE001
        return {"http": 0, "body": b"", "ms": int((time.time() - t0) * 1000), "err": f"{type(e).__name__}: {str(e)[:160]}"}


def as_json(res):
    try:
        return json.loads(res["body"])
    except Exception:  # noqa: BLE001
        return None


def pick(attrs, keys):
    for k in attrs:
        kl = k.lower()
        if any(t in kl for t in keys):
            return k
    return None


def main():
    out = []
    for item in URLS:
        url = item["url"].rstrip("/")
        rec = {"idx": item["idx"], "state": item["state"], "layer": item["layer"], "url": url}

        meta_r = http(url + "?f=json")
        meta = as_json(meta_r)
        rec["meta_http"] = meta_r["http"]
        rec["meta_err"] = meta_r["err"]
        rec["meta_ms"] = meta_r["ms"]
        rec["meta_keys"] = sorted(meta.keys()) if isinstance(meta, dict) else []
        rec["has_count_key"] = bool(isinstance(meta, dict) and "count" in meta)
        rec["has_featureCount_key"] = bool(isinstance(meta, dict) and "featureCount" in meta)
        rec["service_error"] = (meta or {}).get("error") if isinstance(meta, dict) else None
        rec["geometryType"] = (meta or {}).get("geometryType", "")
        rec["name"] = (meta or {}).get("name", "")
        rec["type"] = (meta or {}).get("type", "")
        rec["maxRecordCount"] = (meta or {}).get("maxRecordCount")
        fields = [f.get("name") for f in (meta or {}).get("fields", [])] if isinstance(meta, dict) else []
        rec["fields"] = fields
        rec["n_fields"] = len(fields)

        # count
        c_url = url + "/query?" + urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
        c_r = http(c_url)
        c = as_json(c_r)
        rec["count_http"] = c_r["http"]
        rec["count_err"] = c_r["err"]
        rec["count"] = None
        rec["count_method"] = ""
        if isinstance(c, dict) and c.get("count") is not None:
            rec["count"] = c["count"]
            rec["count_method"] = "returnCountOnly"
        else:
            rec["count_error_body"] = (c or c_r["body"][:300] if not isinstance(c, dict) else c)
            # fallback: ids
            i_url = url + "/query?" + urllib.parse.urlencode({"where": "1=1", "returnIdsOnly": "true", "f": "json"})
            i_r = http(i_url)
            i = as_json(i_r)
            rec["ids_http"] = i_r["http"]
            rec["ids_err"] = i_r["err"]
            if isinstance(i, dict) and isinstance(i.get("objectIds"), list):
                rec["count"] = len(i["objectIds"])
                rec["count_method"] = "returnIdsOnly(possibly truncated at maxRecordCount)"
            elif isinstance(i, dict) and i.get("error"):
                rec["ids_error_body"] = i["error"]

        # samples
        s_url = url + "/query?" + urllib.parse.urlencode(
            {"where": "1=1", "outFields": "*", "resultRecordCount": 20, "f": "json"})
        s_r = http(s_url)
        s = as_json(s_r)
        rec["sample_http"] = s_r["http"]
        rec["sample_err"] = s_r["err"]
        feats = (s or {}).get("features", []) if isinstance(s, dict) else []
        rec["sampled_n"] = len(feats)
        rec["sample_error_body"] = (s or {}).get("error") if isinstance(s, dict) else None
        attrs = [f.get("attributes", {}) for f in feats]
        rec["samples"] = attrs[:3]
        if attrs:
            keys = list(attrs[0].keys())
            kn, ks, kc, kst, kz = (pick(keys, NUM_KEYS), pick(keys, STREET_KEYS), pick(keys, CITY_KEYS),
                                   pick(keys, STATE_KEYS), pick(keys, ZIP_KEYS))
            rec["map_fields"] = {"number": kn, "street": ks, "city": kc, "state": kst, "zip": kz}
            rec["nonnull"] = {
                "number": sum(1 for a in attrs if kn and a.get(kn) not in (None, "")),
                "street": sum(1 for a in attrs if ks and a.get(ks) not in (None, "")),
                "city": sum(1 for a in attrs if kc and a.get(kc) not in (None, "")),
                "state": sum(1 for a in attrs if kst and a.get(kst) not in (None, "")),
                "zip": sum(1 for a in attrs if kz and a.get(kz) not in (None, "")),
            }
            rec["n_key"] = len(keys)
            rec["state_values"] = sorted({str(a.get(kst)) for a in attrs if kst and a.get(kst)}) if kst else []
        out.append(rec)
        print(f"[{item['idx']}] {item['state']:2s} {item['layer'][:38]:38s} meta={rec['meta_http']} "
              f"count={rec['count']} via={rec['count_method']} samples={rec['sampled_n']} "
              f"err={rec['meta_err'][:50]}", flush=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    sys.exit(main())
