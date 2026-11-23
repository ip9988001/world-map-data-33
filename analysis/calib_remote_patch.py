#!/usr/bin/env python3
"""Patch calib-inventory.csv: fill remote counts + qualify probe_err + recover dirty-layer URLs.

Inputs (all read-only evidence):
  /tmp/calib_remote_probe.json   <- analysis/calib_remote_count.py  (count via returnCountOnly, HTTP codes)
  /tmp/calib_remote_fields.json  <- analysis/calib_remote_fields.py (20-sample field usability)
  analysis/calib-inventory-20261123/dirty-layer-urls.json (ledger truncated name -> real url, from survey/ng911)

Only touches `method=remote` rows (15) and `source=NG911(dirty)` rows (15).
No fusion, no grading, no engine change: it rewrites evidence columns of the inventory only.
"""
import csv
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = f"{BASE}/analysis/calib-inventory-20261123/calib-inventory.csv"
PROBE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/calib_remote_probe.json"
FIELDS = sys.argv[2] if len(sys.argv) > 2 else "/tmp/calib_remote_fields.json"
DIRTY = f"{BASE}/analysis/calib-inventory-20261123/dirty-layer-urls.json"

# hand adjudication, one line per layer, derived from the two probe files
# usable: full = number+street+city(+state/zip); partial = address layer but missing a component; no = not an address layer
VERDICT = {
    295: ("no", "non_address_or_mismatch",
          "meta_name=OSM_Amenities_Fire_Stations(不是 NH 地址层，是 OSM POI 导入)；addr_state 20/20='VT'，"
          "addr_housenumber/addr_street/addr_city/addr_postcode 各 1/20；标题 Fire_Stations 与实服务名不符"),
    297: ("full", "", "5 个地址字段均 20/20(ADDRNUM/FULLNAME/MUNICIPALITY/STATE/ZIP_5)"),
    298: ("full", "", "AddressNumber/StreetName/Zipcode 20/20；无 state 字段，城市只有 CADCityCode 三字母代码(Jurisdiction/Community 可补)"),
    299: ("partial", "", "Address_Number 只 2/20、StName 12/20、Municipality 0/20；Full_Address 20/20 但带前导空格且门牌缺失"),
    300: ("full", "", "addr_* 标准 7 字段，5 项 20/20"),
    301: ("full", "title_mismatch", "标题叫 NG911 ESN，实服务名 Address Points(1-1250)；Addr_Num/Addr_St/City/Zipcode 20/20"),
    302: ("partial", "", "ADDRNUM/FULLADDR/MUNICIPALITY 20/20（FULLNAME 空），无 state/zip 字段"),
    303: ("full", "", "addr_* 标准 5 项 20/20"),
    304: ("full", "", "ADDRNUM/FULLNAME/POSTAL_CITY/STATE/ZIPCODE 20/20"),
    305: ("full", "", "HOUSENUMBE/STREETNAME/CITY/STATE/ZIP_CODE 20/20；属性带 parcel/tax 字段(地址视图挂在宗地上)"),
    306: ("full", "title_mismatch", "标题 Address Points and CPNs，实服务名 Address Labels below 4K；5 项 20/20"),
    307: ("partial", "", "ADDRESSNUM/ADDRESSSTR/JURISDICTI 20/20，无 zip/state 字段"),
    308: ("partial", "", "ADDRNUM/FULLNAME/MUNICIPALITY 20/20，无 zip/state 字段"),
    309: ("partial", "", "ADDRNUM/FULLNAME/MUNICIPALITY 20/20，无 zip/state 字段；FULLADDR 里含 city/state/zip 文本"),
    313: ("full", "", "AddrNum/StreetName/ZipCode 20/20(邮编 19/20)，无 city 字段"),
}


def main():
    probe = {r["idx"]: r for r in json.load(open(PROBE))}
    flds = {r["idx"]: r for r in json.load(open(FIELDS))}
    dirty = {d["ledger_layer_truncated"]: d for d in json.load(open(DIRTY))}
    rows = list(csv.DictReader(open(CSV, newline="", encoding="utf-8")))
    cols = list(rows[0].keys())
    changed = {"remote": 0, "dirty": 0}

    for i, r in enumerate(rows):
        if r["method"] == "remote" and i in probe:
            p, f = probe[i], flds.get(i, {})
            usable, flag, why = VERDICT[i]
            r["rows"] = str(p["count"]) if p.get("count") is not None else ""
            r["rows_source"] = "remote_count"
            nn = f.get("nonnull") or {}
            tot = f.get("sampled_n") or 0
            for role, col in (("number", "nonnull_number"), ("street", "nonnull_street"),
                              ("city", "nonnull_city"), ("state", "nonnull_state"), ("zip", "nonnull_zip")):
                v = nn.get(role)
                r[col] = f"{v}/{tot}" if (v is not None and tot) else ""
            if f.get("sampled_n"):
                r["sampled_n"] = str(f["sampled_n"])
            note = [
                f"probe_err_cause=none(不是报错：layer metadata ?f=json 不含 count/featureCount 键，"
                f"旧脚本读不到 declared 就把空值写成 probe_err=；meta_http={p['meta_http']})",
                f"count_via={p['count_method']} count_http={p['count_http']}",
                f"samples={f.get('sampled_n')}/{f.get('sampled_n')} http={f.get('sample_http')} usable={usable}",
            ]
            if flag:
                note.append(flag)
            note.append(why)
            note.append(f"fields_mapped={json.dumps(f.get('field_map'), ensure_ascii=False)}")
            note.append(f"url={p['url']}")
            r["note"] = "; ".join(note)
            changed["remote"] += 1
        elif r["source"] == "NG911(dirty)" and r["layer"] in dirty:
            d = dirty[r["layer"]]
            extra = (f"full_layer_title={d['title']}; survey_count={d['survey_count']}; "
                     f"geom={d['geom']}; nfields={d['nfields']}; url={d['url']}")
            if "url=" not in r["note"]:
                r["note"] = f"{r['note']}; {extra}"
            changed["dirty"] += 1

    with open(CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("patched", changed, "rows:", len(rows))


if __name__ == "__main__":
    main()
