#!/usr/bin/env python3
"""D2（本地 1,158 层）坐标采样：只读 intake-full 落盘的 ndjson.gz，不联网、不猜。

每层取 addr 表前 50 行「同时有 latitude/longitude」的记录；addr 无坐标时退到
aux_addr_nohouse（日志里记 fallback）。坐标是响应里原样的 latitude/longitude，
不做质心、不插值。
"""
import gzip
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS = os.path.join(ROOT, "layers.json")
EXTRACT = os.environ.get("COORD_EXTRACT", "/data/coord-work-20261124/extract")
TARGET = 50
ADDR_KEYS = ("house_number", "house_number_suffix", "street_pre_dir", "street_name",
             "street_post_type", "street_post_dir", "street_full", "unit", "postal_city",
             "municipal_city", "county_name", "county_fips", "state_abbr", "zip5")


def rows_of(layer_dir, table):
    fs = glob.glob(os.path.join(layer_dir, f"{table}.*.ndjson.gz"))
    if not fs:
        return
    with gzip.open(fs[0], "rt") as f:
        for line in f:
            try:
                yield json.loads(line)
            except Exception:
                continue


def main() -> int:
    os.makedirs(EXTRACT, exist_ok=True)
    layers = [l for l in json.load(open(LAYERS))["layers"] if l["universe"] == "d2"]
    stat = {"ok": 0, "partial": 0, "unavailable": 0, "skipped": 0}
    for L in layers:
        key = L["layer_id"]
        path = os.path.join(EXTRACT, f"d2_{key}.json")
        if os.path.exists(path):
            stat["skipped"] += 1
            continue
        d = L.get("layer_dir")
        rec = {"layer_id": L["layer_id"], "url": L["url"], "state": L["state"],
               "universe": "d2", "provider": L["provider"], "sample_source": "local_ndjson",
               "http_code": None, "attempts": 0, "wkid": "4326(local field lat/lon)",
               "geom_type": "point(lat/lon fields)", "exceeded": None, "rows": []}
        tables = []
        for table in ("addr", "aux_addr_nohouse", "aux_street", "aux_parcel"):
            for d0 in rows_of(d, table) if d else []:
                la, lo = d0.get("latitude"), d0.get("longitude")
                try:
                    la, lo = float(la), float(lo)
                except (TypeError, ValueError):
                    continue
                if not (-90 <= la <= 90 and -180 <= lo <= 180) or (la == 0 and lo == 0):
                    continue
                addr = {k: d0[k] for k in ADDR_KEYS if d0.get(k) not in (None, "")}
                rec["rows"].append({"addr_fields": addr, "lon": lo, "lat": la,
                                    "lon_raw": lo, "lat_raw": la,
                                    "geom_type": "point(lat/lon fields)",
                                    "row_index": len(rec["rows"]), "table": table})
                if len(rec["rows"]) >= TARGET:
                    break
            if rec["rows"]:
                tables.append(table)
                if len(rec["rows"]) >= TARGET:
                    break
        rec["tables"] = tables
        if len(rec["rows"]) >= TARGET:
            rec["status"], stat["ok"] = "ok", stat["ok"] + 1
        elif rec["rows"]:
            rec["status"], stat["partial"] = "partial", stat["partial"] + 1
            rec["reason"] = f"local_rows_with_coords={len(rec['rows'])}<{TARGET}"
        else:
            rec["status"], stat["unavailable"] = "unavailable", stat["unavailable"] + 1
            rec["reason"] = "no_coords_in_local_tables"
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, path)
    print(json.dumps({"d2_layers": len(layers), **stat}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
