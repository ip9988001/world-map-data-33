#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 analysis/out/*.json 的逐层画像聚合成三份交付物（纯离线，不访问任何网络）。

产出：
  docs/VALUE-PROFILE-2026-10-30.md   字段频率 + 门牌号值分布 + 街名/city/zip/latlon + 宗地双套
  schema/field-map-v1.json           逐层 canonical 14 字段映射 + 归一化规则
  docs/INTAKE-YIELD-2026-10-30.md    逐层行数/有门牌号行/丢弃原因 + 行级有效率 + 结论
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")

CANON = ["number", "street", "state", "city", "zip", "unit", "lat", "lon",
         "geom_type", "source_kind", "layer_id", "source_url", "captured_at", "confidence"]

# canonical 字段 → 源字段候选（顺序即优先级，正则不区分大小写）
CAND = {
    "number": [r"^HOUSE_?NUM(BER)?$", r"^HOUSE_?NO$", r"^ADDRESS_?NUM(BER)?$", r"^ADDR_?NUM(BER)?$",
               r"^ADDNUM$", r"^ADDRNUM$", r"^STREET_?NUM(BER)?$", r"^SITUS_?NUM(BER)?$",
               r"^PREMISE_?NUM", r"^NUM(BER)?$", r"^ADDR$", r"^ADDRESS$", r"^FULLADDR$",
               r"^FULL_?ADDR(ESS)?$", r"^SITE_?ADDR", r"^STNUM$", r"^NUMERIC"],
    "street": [r"^STREET_?NAME$", r"^ST_?NAME$", r"^FULL_?STREET", r"^STREET$", r"^ROAD_?NAME$",
               r"^STREETNAME$", r"^FULLNAME$", r"^FULL_?ADDR(ESS)?$", r"^SITE_?ADDR",
               r"^ADDRESS$", r"^ADDR$", r"^ROAD$", r"^THOROUGHFARE", r"^WAY$", r"^STNAME"],
    "state": [r"^STATE$", r"^STATE_?ABBR", r"^STATE_?CODE", r"^ST$", r"^STATECODE", r"^STATE_?NAME$"],
    "city": [r"^CITY$", r"^CITY_?NAME$", r"^MUNICIPALITY$", r"^TOWN$", r"^TOWN_?NAME$",
             r"^PLACE$", r"^POST_?CITY$", r"^MAIL_?CITY$", r"^SITUS_?CITY$", r"^MUNICIPAL"],
    "zip": [r"^ZIP$", r"^ZIP_?CODE$", r"^ZIPCODE$", r"^POSTAL_?CODE$", r"^ZIP5$", r"^ZIP_?5$",
            r"^ZIP_?CD$", r"^POSTCODE$", r"^ZCTA$", r"^SITUS_?ZIP"],
    "unit": [r"^UNIT$", r"^UNIT_?(NUM|NO|ID)$", r"^APT$", r"^APT_?(NUM|NO)?$", r"^SUITE$",
             r"^STE$", r"^UNIT_?DESIGNATOR", r"^BLDG", r"^ROOM$", r"^SPACE$"],
    "lat": [r"^LAT(ITUDE)?$", r"^Y$", r"^Y_?COORD", r"^POINT_?Y$", r"^LAT_?DD$", r"^CENTROID_?Y$"],
    "lon": [r"^(LON|LNG|LONG|LONGITUDE)$", r"^X$", r"^X_?COORD", r"^POINT_?X$", r"^LON_?DD$",
            r"^CENTROID_?X$"],
}

NORM_RULES = {
    "street_suffix": {"STREET": "ST", "STR": "ST", "ST": "ST", "AVENUE": "AVE", "AV": "AVE",
                      "AVE": "AVE", "ROAD": "RD", "RD": "RD", "DRIVE": "DR", "DR": "DR",
                      "LANE": "LN", "LN": "LN", "BOULEVARD": "BLVD", "BLVD": "BLVD",
                      "COURT": "CT", "CT": "CT", "CIRCLE": "CIR", "CIR": "CIR",
                      "PLACE": "PL", "PL": "PL", "TERRACE": "TER", "TER": "TER",
                      "PARKWAY": "PKWY", "PKWY": "PKWY", "HIGHWAY": "HWY", "HWY": "HWY",
                      "TRAIL": "TRL", "TRL": "TRL", "SQUARE": "SQ", "SQ": "SQ"},
    "direction_prefix": {"NORTH": "N", "N": "N", "SOUTH": "S", "S": "S", "EAST": "E", "E": "E",
                         "WEST": "W", "W": "W", "NORTHEAST": "NE", "NE": "NE",
                         "NORTHWEST": "NW", "NW": "NW", "SOUTHEAST": "SE", "SE": "SE",
                         "SOUTHWEST": "SW", "SW": "SW"},
    "case": "全部转大写后去多余空格（UPPER + collapse spaces）",
    "zip": "去非数字字符后左补零到 5 位；9 位保留前 5 位（ZIP+4 的 +4 丢到 unit 之外不保留）",
    "number": "去空白；A-Z 后缀保留（12A）；号段 100-102 保留原样，标 range=true",
    "city_alias": {"SAINT LOUIS": "ST LOUIS", "SAINT PAUL": "ST PAUL", "FORT WORTH": "FT WORTH",
                   "MOUNT VERNON": "MT VERNON", "MOUNDS VIEW": "MOUNDS VIEW"},
    "confidence": "number+street+state 全有 = 0.9；缺 unit/zip 各 -0.05；来自 parcel_situs = -0.1",
}


def load():
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        d["_file"] = os.path.basename(f)
        rows.append(d)
    return rows


def pick_field(fields: dict, cands: list[str], min_rate: float = 0.02):
    """在层内按优先级挑源字段；要求该字段在样本里非空率 >= min_rate（避免全空字段被选中）。"""
    names = list(fields)
    for rx in cands:
        r = re.compile(rx, re.I)
        hit = [n for n in names if r.match(n)]
        hit.sort(key=lambda n: -fields[n].get("nonempty", 0))
        for n in hit:
            f = fields[n]
            rate = f.get("nonempty", 0) / max(1, f.get("n", 1))
            if rate >= min_rate:
                return n, rate
        if hit:
            return hit[0], fields[hit[0]].get("nonempty", 0) / max(1, fields[hit[0]].get("n", 1))
    return None, 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conflict", default=os.path.join(HERE, "parcel_conflict.json"))
    a = ap.parse_args()
    layers = load()
    if not layers:
        raise SystemExit("analysis/out 是空的，先跑 profile.py")

    pts = [d for d in layers if d.get("kind") == "address_point"]
    par = [d for d in layers if d.get("kind") == "parcel_situs"]

    # ---------- 字段频率 ----------
    fl = Counter()
    finfo = {}
    for d in layers:
        for name, f in (d.get("fields") or {}).items():
            fl[name] += 1
            e = finfo.setdefault(name, {"n": 0, "nonempty": 0, "types": Counter(), "ex": []})
            e["n"] += f.get("n", 0)
            e["nonempty"] += f.get("nonempty", 0)
            e["types"].update(f.get("types") or {})
            for x in f.get("ex") or []:
                if len(e["ex"]) < 3 and x not in e["ex"]:
                    e["ex"].append(x)

    # ---------- 门牌号字段值分布 ----------
    num_agg = {}
    for d in layers:
        for name, b in (d.get("num_fields") or {}).items():
            e = num_agg.setdefault(name, Counter())
            e.update(b)
    num_layers = Counter()
    for d in layers:
        for name in (d.get("num_fields") or {}):
            num_layers[name] += 1

    # ---------- canonical 映射 ----------
    fmap = {"schema": "field-map/v1", "generated_at": "2026-10-30",
            "canonical_fields": CANON,
            "source_kind_allowed": ["address_point", "parcel_situs", "street_line"],
            "normalization": NORM_RULES,
            "layers": {}}
    usable_n = 0
    for d in layers:
        lid = d["layer_id"]
        fields = d.get("fields") or {}
        m = {}
        for c in ("number", "street", "state", "city", "zip", "unit", "lat", "lon"):
            fname, rate = pick_field(fields, CAND[c])
            m[c] = fname
            m[c + "_nonempty_rate"] = round(rate, 3) if fname else None
        # 归一化后的 lat/lon 来自采集器的 geometry（norm.lat/lon），优先用它
        nl = (d.get("norm") or {})
        if (nl.get("lat") or {}).get("nonempty"):
            m["lat"], m["lat_norm_field"] = "[[geometry.y]]", True
        if (nl.get("lon") or {}).get("nonempty"):
            m["lon"], m["lon_norm_field"] = "[[geometry.x]]", True
        missing = [c for c in ("number", "street", "state") if not m.get(c)]
        ent = {
            "number": m["number"], "street": m["street"], "state": m["state"],
            "city": m["city"], "zip": m["zip"], "unit": m["unit"],
            "lat": m["lat"], "lon": m["lon"],
            "geom_type": {"address_point": "Point", "parcel_situs": "Polygon"}.get(d.get("kind"), None),
            "source_kind": d.get("kind"),
            "layer_id": lid,
            "source_url": None,           # 上游 URL 不在本轮读取范围（禁访上游），见 layer 元数据
            "captured_at": None,
            "confidence": None,
            "usable": not missing,
            "number_nonempty_rate": m["number_nonempty_rate"],
            "street_nonempty_rate": m["street_nonempty_rate"],
            "state_nonempty_rate": m["state_nonempty_rate"],
        }
        if missing:
            ent["reason"] = "缺 canonical 必需字段：%s" % ", ".join(missing)
        else:
            usable_n += 1
            ent["confidence"] = round(max(0.3, 0.9 - (0.0 if m["zip"] else 0.05)
                                          - (0.0 if m["unit"] else 0.05)
                                          - (0.1 if d.get("kind") == "parcel_situs" else 0.0)), 2)
        fmap["layers"][lid] = ent
    # 次级口径：state 常来自层元数据（源层没有 state 列），按「number+street 可得」再算一次
    ns_ok = sum(1 for e in fmap["layers"].values() if e.get("number") and e.get("street"))
    fmap["coverage"] = {"layers_profiled": len(layers), "address_point": len(pts),
                        "usable_by_number_street": ns_ok,
                        "usable_by_number_street_pct": round(ns_ok * 100.0 / max(1, len(layers)), 2),
                        "parcel_situs": len(par),
                        "usable": usable_n, "usable_pct": round(usable_n * 100.0 / max(1, len(layers)), 2)}

    # ---------- 产出 1：VALUE-PROFILE ----------
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    V = ["# 值分布摸底（2026-10-30）", "",
         "数据范围：**已发布 Release 资产**（`collect-step04/05/07` 点层 + `collect-step10` 宗地层），"
         "全程只读 GitHub，**未访问任何上游 ArcGIS/Census 接口**。", "",
         f"- 已画像层数：**{len(layers)}**（点层 {len(pts)} / 宗地层 {len(par)}）",
         f"- 抽样方式：payload ≤30MB 的层全量流式扫（每单元前 2,000 行入样），大层用 HTTP Range 取前 3MB "
         f"部分解压取 2,000 行；宗地大包（`parcel1-raw-*.tar`）流式扫、每层取前 2,000 行",
         "", "## 一、字段频率（出现层数 Top 60）", "",
         "| 字段名 | 出现层数 | 主类型 | 非空率 | 示例值 |", "|---|---|---|---|---|"]
    for name, n in fl.most_common(60):
        e = finfo[name]
        rate = 100.0 * e["nonempty"] / max(1, e["n"])
        t = e["types"].most_common(1)[0][0] if e["types"] else "-"
        ex = " / ".join(str(x)[:28] for x in e["ex"][:3])
        V.append("| `%s` | %d | %s | %.1f%% | %s |" % (name, n, t, rate, ex))
    V += ["", f"字段名去重共 **{len(fl)}** 个；上表按「出现层数」降序取前 60，"
              f"完整清单见 `analysis/out/*.json`（逐层原始统计，可复核）。", "",
          "## 二、门牌号字段的值分布（核心）", "",
          "分类口径：`pure_num`=纯数字 / `num_suffix`=数字+字母(12A) / `range`=号段(100-102) / "
          "`zero`=`0` / `empty`=空串 / `null`=null·NULL·NONE / `na`=N/A·NA / `unknown`=UNKNOWN·UNKNOWN·NOT STATED / "
          "`lot_parcel_tbd`=Lot·Parcel·TBD / `other`=其它", "",
          "| 字段 | 层数 | 样本值数 | pure_num | num_suffix | range | zero | empty | null | na | unknown | lot_parcel_tbd | other |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    cls = ["pure_num", "num_suffix", "range", "zero", "empty", "null", "na", "unknown",
           "lot_parcel_tbd", "other"]
    tot = Counter()
    for name, c in sorted(num_agg.items(), key=lambda x: -sum(x[1].values()))[:25]:
        n = sum(c.values())
        tot.update(c)
        V.append("| `%s` | %d | %s | %s |" % (
            name, num_layers[name], f"{n:,}",
            " | ".join(f"{c.get(k, 0):,} ({100.0 * c.get(k, 0) / max(1, n):.1f}%)" for k in cls)))
    N = sum(tot.values())
    V += ["", "**全体门牌字段合计**（%s 个样本值）：" % f"{N:,}", "",
          "| 类 | 行数 | 占比 |", "|---|---|---|"]
    for k in cls:
        V.append("| %s | %s | %.2f%% |" % (k, f"{tot.get(k, 0):,}", 100.0 * tot.get(k, 0) / max(1, N)))
    V += ["", "解读：`pure_num + num_suffix` 才是可直接进 gold 的门牌号；`zero/empty/null/na/unknown/"
              "lot_parcel_tbd` 全部视为「无门牌号」。", ""]

    # 街名 / city / zip / latlon 非空率
    V += ["## 三、街名 / city / zip / lat / lon 的非空率（按层平均）", "",
          "| 字段 | 覆盖层数 | 非空率中位数 | 非空率均值 |", "|---|---|---|---|"]
    import statistics
    for k in ("st_name", "city", "zip", "lat", "lon", "unit", "add_num"):
        rates = []
        for d in layers:
            b = (d.get("norm") or {}).get(k)
            if b and b.get("n"):
                rates.append(100.0 * b["nonempty"] / b["n"])
        if rates:
            V.append("| %s | %d / %d | %.1f%% | %.1f%% |"
                     % (k, len(rates), len(layers), statistics.median(rates),
                        sum(rates) / len(rates)))
    V += [""]

    # 宗地双套
    cf = []
    if os.path.exists(a.conflict):
        cf = json.load(open(a.conflict, encoding="utf-8"))
    both = [x for x in cf if x.get("both_layers")]
    rb = sum(x.get("rows_both", 0) for x in both)
    rc = sum(x.get("rows_conflict", 0) for x in both)
    V += ["## 四、宗地层：situs address vs mailing address", ""]
    if cf:
        V += [f"- 检查层数：**{len(cf)}**（`collect-step10` 宗地层，每层前 800 行）",
              f"- 两套字段**同时存在**的层：**{len(both)}** / {len(cf)}"
              f"（{100.0 * len(both) / max(1, len(cf)):.1f}%）",
              f"- 两套都有值的行：**{rb:,}**；其中字符串不一致（冲突）：**{rc:,}**"
              f" → **冲突率 {100.0 * rc / max(1, rb):.2f}%**",
              "", "| 层 | situs 字段 | mailing 字段 | 两套都有 | 冲突 | 冲突率 |",
              "|---|---|---|---|---|---|"]
        for x in both[:25]:
            V.append("| `%s` | %s | %s | %s | %s | %.1f%% |"
                     % (str(x.get("layer_id"))[:44], ",".join(x.get("situs_fields") or [])[:40],
                        ",".join(x.get("mail_fields") or [])[:40], f"{x.get('rows_both', 0):,}",
                        f"{x.get('rows_conflict', 0):,}",
                        100.0 * x.get("rows_conflict", 0) / max(1, x.get("rows_both", 1))))
        V += ["", "> 冲突率的含义：同一行里房产地址与业主/邮寄地址文本不一致。"
                  "冲突不代表谁对，但说明**不能把 mailing 当 situs 用**（会把出租房的业主外地地址算成本地门牌）。"]
    else:
        V += ["（未跑 `analysis/parcel_conflict.py`）"]
    V += [""]
    open(os.path.join(ROOT, "docs", "VALUE-PROFILE-2026-10-30.md"), "w",
         encoding="utf-8").write("\n".join(V))

    # ---------- 产出 2 ----------
    os.makedirs(os.path.join(ROOT, "schema"), exist_ok=True)
    json.dump(fmap, open(os.path.join(ROOT, "schema", "field-map-v1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ---------- 产出 3：INTAKE-YIELD ----------
    Y = ["# 入仓产出率（intake yield）2026-10-30", "",
         "口径：`rows_with_number` = `rows_total × 门牌字段非空率`（非空率来自本轮抽样），"
         "`rows_without_number` = 差额；丢弃原因按门牌字段值分布分类归因。", "",
         "| 层 | 类型 | rows_total | 门牌字段 | 非空率 | rows_with_number | rows_without_number | 主因 |",
         "|---|---|---|---|---|---|---|---|"]
    sum_tot = sum_wn = 0
    top_drop = Counter()
    per_layer = {}
    for d in sorted(layers, key=lambda x: -(x.get("rows_total") or 0)):
        lid = d["layer_id"]
        ent = fmap["layers"].get(lid) or {}
        numf = ent.get("number")
        rate = (ent.get("number_nonempty_rate") or 0.0)
        rt = d.get("rows_total") or 0
        wn = int(round(rt * rate))
        nb = (d.get("num_fields") or {}).get(numf) or {}
        n = sum(nb.values()) or 1
        main = max(nb.items(), key=lambda kv: kv[1])[0] if nb else "no_number_field"
        top_drop[main] += rt - wn
        sum_tot += rt
        sum_wn += wn
        per_layer[lid] = {"rows_total": rt, "rows_with_number": wn,
                          "rows_without_number": rt - wn, "number_field": numf,
                          "nonempty_rate": round(rate, 4),
                          "dropped_reason": {k: round(v * 100.0 / n, 2) for k, v in
                                             sorted(nb.items(), key=lambda kv: -kv[1])}}
        if len(Y) < 200:
            Y.append("| `%s` | %s | %s | `%s` | %.1f%% | %s | %s | %s |"
                     % (lid[:52], d.get("kind"), f"{rt:,}", numf or "-", rate * 100,
                        f"{wn:,}", f"{rt - wn:,}", main))
    Y += ["", "## 汇总", "",
          f"- 层数：**{len(layers)}**（点层 {len(pts)} / 宗地层 {len(par)}）",
          f"- 总行数：**{sum_tot:,}**",
          f"- 有门牌号行：**{sum_wn:,}**",
          f"- **行级有效率：{100.0 * sum_wn / max(1, sum_tot):.2f}%**", "",
          "## 丢弃原因分布 Top10（按行数）", "", "| 原因（门牌字段抽样里的主类） | 影响行数 |", "|---|---|"]
    for k, v in top_drop.most_common(10):
        Y.append("| %s | %s |" % (k, f"{v:,}"))
    Y += ["", "## 结论：按现有数据能出多少真实地址行", "",
          f"以本轮画像为准，把点层 + 宗地层按上述映射转 gold，"
          f"**可产出约 {sum_wn // 10000} 万条（{sum_wn:,}）带门牌号的行**；"
          f"另有 {sum_tot - sum_wn:,} 行缺门牌号，只能进 silver/留档，不能算地址。",
          "", "注意两点：",
          "1. `rows_with_number` 是抽样比例外推（每层 2,000 行样本），不是逐行全扫；"
          "3 个层的全量核对结果见 `docs/INTAKE-YIELD-RECONCILE.md`。",
          "2. 宗地层的 `number` 多半来自 situs 字段，confidence 已在 field-map 里自动降 0.1。", ""]
    open(os.path.join(ROOT, "docs", "INTAKE-YIELD-2026-10-30.md"), "w",
         encoding="utf-8").write("\n".join(Y))
    json.dump(per_layer, open(os.path.join(HERE, "yield_per_layer.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(json.dumps({"layers": len(layers), "fields": len(fl),
                      "usable": usable_n, "usable_pct": fmap["coverage"]["usable_pct"],
                      "rows_total": sum_tot, "rows_with_number": sum_wn,
                      "row_yield_pct": round(100.0 * sum_wn / max(1, sum_tot), 2),
                      "conflict_pct": round(100.0 * rc / max(1, rb), 2) if cf else None},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
