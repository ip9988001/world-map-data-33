#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 清洗分级：把 10-P 探测出的 8,116 个 situs 层分成 strong / weak / reject。

不碰 steps.json（编外自研期）。产物：collect/situs_layers.csv
"""
from __future__ import annotations
import csv, json, os, re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "situs_layers.csv")

# 名称/字段里出现即判为「路网·非宗地」噪声
NOISE = ("centerline", "centreline", "_road", "road_", "roads", "roadway", "highway",
         "psap", "contact", "call_handle", "callhandling", "call_handling",
         "boundary", "boundaries", "intersection", "easement", "culvert", "stream",
         "river", "waterline", "water_line", "sewer", "pipeline", "transit",
         "bus_route", "busroute", "rail", "taxiway", "runway", "trail", "sidewalk",
         "milepost", "mile_marker", "milemarker", "pavement", "flood", "census",
         "tract", "block_group", "voting", "precinct", "school", "hospital",
         "fire_station", "hydrant", "sign", "signal", "pole", "street_light",
         "bridge", "bikeway", "greenway", "monument", "control_point")

# 强字段：明确是「房产/宗地地址」
STRONG = ("situs_addr", "situsaddress", "situs_add", "situsaddr", "situsaddress",
          "site_addr", "siteaddress", "site_address", "siteadd",
          "prop_addr", "propaddr", "property_addr", "propertyaddress", "property_address",
          "parcel_addr", "parceladdress", "parcel_address", "parc_addr", "parcaddr",
          "phys_addr", "physaddr", "physical_addr", "physical_address", "physaddress",
          "full_addr", "fulladdr", "full_address", "fulladdress",
          "loc_addr", "locaddress", "loc_address",
          "primary_addr", "primaryaddress", "building_addr", "bldg_addr",
          "struct_addr", "structaddr", "structure_addr", "house_addr", "house_num",
          "housenum", "street_address", "streetaddress", "street_add")

# 泛字段：可能是地址，也可能不是 → weak
WEAK = ("address", "addr", "location")

# owner / 邮寄 类词：命中即不算 situs
OWNER = ("owner", "mail", "taxpayer", "payee", "own_", "ownaddr", "po_box", "pobox")

RANGE_RE = re.compile(r"^(from|to)[_\-]?(addr|address)", re.I)


def grade_it(layer, geom, fields, rows):
    """返回 (grade, reason, hit)"""
    if rows <= 0:
        return "reject", "空层", []
    low = [str(f).lower() for f in fields]
    name = layer.lower()

    # 1. 线要素：不可能承载门牌点
    if geom == "Polyline":
        return "reject", "线要素(Polyline)", []

    # 2. 层名撞噪声词
    for w in NOISE:
        if w in name:
            return "reject", "层名噪声:" + w, []

    # 3. 字段撞噪声词
    for f in low:
        for w in NOISE:
            if w in f:
                return "reject", "字段噪声:" + w, [f]

    # 4. 只有 from/to 门牌区间，没有单点地址字段
    if low and all(RANGE_RE.match(f) for f in low):
        return "reject", "仅门牌区间(from/to)", low[:4]

    # 5. 强字段（先剔 owner/mail）
    strong_hit = []
    for f in low:
        if any(o in f for o in OWNER):
            continue
        if any(s in f for s in STRONG):
            strong_hit.append(f)
    if strong_hit:
        # 强字段里如果混着 from/to，说明是区间 → 降 weak
        if all(RANGE_RE.match(f) for f in strong_hit):
            return "weak", "强字段但为区间", strong_hit[:4]
        return "strong", "强字段", strong_hit[:6]

    # 6. 泛字段
    weak_hit = []
    for f in low:
        if any(o in f for o in OWNER):
            continue
        if any(s in f for s in WEAK):
            weak_hit.append(f)
    if weak_hit:
        # 只剩 mile/mill/oper + location 这种运营位置
        if all(any(p in f for p in ("mile", "mill", "oper", "ms")) for f in weak_hit):
            return "reject", "运营里程位置", weak_hit[:4]
        return "weak", "泛字段", weak_hit[:6]

    return "reject", "无地址字段", []


def main():
    probe = json.load(open(os.path.join(HERE, "polygon_probe.json"), encoding="utf-8"))
    plan = {}
    with open(os.path.join(HERE, "layer_plan.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            plan.setdefault(r["layer_id"], r)

    out, stat = [], Counter()
    by_state_s, by_state_w = defaultdict(int), defaultdict(int)
    rows_s = rows_w = 0
    for x in probe["detail"]:
        if x["verdict"] != "situs":
            continue
        g, reason, hit = grade_it(x["layer"], x["geom"], x["fields"], x["rows"])
        stat[g + "|" + reason] += 1
        st = x["state"] or "未定位"
        if g == "strong":
            rows_s += x["rows"]; by_state_s[st] += x["rows"]
        elif g == "weak":
            rows_w += x["rows"]; by_state_w[st] += x["rows"]
        out.append({"layer_id": x["layer"], "state": x["state"] or "", "geom": x["geom"],
                    "rows": x["rows"], "grade": g, "reason": reason,
                    "nfields": x["nfields"], "fields_hit": ",".join(hit),
                    "url": plan.get(x["layer"], {}).get("url", "")})

    out.sort(key=lambda r: (r["grade"] != "strong", r["grade"] != "weak", -r["rows"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["layer_id", "state", "geom", "rows", "grade",
                                          "reason", "nfields", "fields_hit", "url"])
        w.writeheader(); w.writerows(out)

    g = Counter(r["grade"] for r in out)
    print(json.dumps({"total_situs": len(out), "strong": g["strong"], "weak": g["weak"],
                      "reject": g["reject"], "rows_strong": rows_s, "rows_weak": rows_w,
                      "rows_reject": probe["situs_rows"] - rows_s - rows_w,
                      "states_strong": len([k for k in by_state_s if k != "未定位"]),
                      "top_reject": stat.most_common(8)}, ensure_ascii=False, indent=1))
    json.dump({"strong": g["strong"], "weak": g["weak"], "reject": g["reject"],
               "rows_strong": rows_s, "rows_weak": rows_w,
               "by_state_strong": dict(by_state_s), "by_state_weak": dict(by_state_w),
               "reasons": dict(stat)}, open(os.path.join(HERE, "gate_situs.json"), "w",
                                            encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
