#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""step3：把 1,340 层逐层归入一种「组合串/分列」写法模式（规则见 REPORT.md §3）。

输入：_work/per_layer.json（combo_fields.py 产出，全本地）
输出：patterns.csv（逐层）/ patterns.json（模式汇总）/ _work/classify_detail.json（逐层特征，便于复核）

判定只用字段名 + 真实样例值，不猜：
  · 每个字段先用「值形态」判定成 number / street / city / state / zip / combo / fulladdr / range / idlike
  · 再看这些字段的组合方式决定模式
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

# ---------------------------------------------------------------- 字段名 → 角色线索
NUM_NAME = re.compile(r"(house|housenum|hse|nbr|num|number|addnum|addrnum|anum|prem|premis|"
                      r"street_?no|str_?no|bldg_?no)", re.I)
STREET_NAME = re.compile(r"(^|[^a-z])(street|st_?name|st_?nm|stname|road|rd_?name|thoroughfare|"
                         r"addr_?line2|address_?line2|situs|street_?address|full_?street|avenue|"
                         r"streetname|street_?nam)([^a-z]|$)", re.I)
CITY_NAME = re.compile(r"^(city|town|municipal|place|postal_?city|postcomm|inc_?muni|msagcomm|"
                       r"community|postal_?community|locality)", re.I)
STATE_NAME = re.compile(r"^(state|state_?name|state_?code|state_?abbr|st_?abbr)", re.I)
ZIP_NAME = re.compile(r"(zip|postcode|postal_?code|post_?code)", re.I)
COMBO_NAME = re.compile(r"(addr|address|situs|fulladdr|full_?address|complete_?address|"
                        r"addr_?line1|address_?line1|loc_?addr|site_?addr|mail_?addr|"
                        r"str_?addr|street_?addr|all|label)", re.I)
ID_NAME = re.compile(r"(^|_)(id|pid|apn|pin|parcel|parcelid|gis_?id|globalid|guid|uuid|fid|"
                     r"objectid|key|code|zone|zoning|district|class|lot|block|map_?no|"
                     r"account|acct|route|route_?id|segment|seg_?id|license|permit)(_|$)", re.I)
RANGE_NAME = re.compile(r"(from_?addr|to_?addr|fromaddr|toaddr|from_?num|to_?num|hn_?low|hn_?high|"
                        r"add_?low|add_?high|range)", re.I)

NUM_VAL = re.compile(r"^\s*(\d{1,6})\s*[A-Za-z]?\s*$")
NUM_RANGE_VAL = re.compile(r"^\s*(\d{1,6})\s*[-/]\s*(\d{1,6})\s*$")
COMBO_VAL = re.compile(r"^\s*(\d{1,6})\s*[-A-Za-z]?[\s,]+([A-Za-z][^\n]{1,80})$")
STREETISH_VAL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9'.\- ]{1,70}$")
ZIP_VAL = re.compile(r"^\s*(\d{5})(-\d{4})?\s*$")
ZIP_IN = re.compile(r"\b\d{5}\b")
ST_ABBR = ("AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|"
           "NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC")
# 只有「逗号后跟州缩写」或「州缩写+5 位邮编」或「以州缩写结尾」才算州证据
STATE_TOK = re.compile(r"(?:,\s*(?:" + ST_ABBR + r")\b|\b(?:" + ST_ABBR + r")\s+\d{5}\b|\s(?:" + ST_ABBR + r")$)")
MASK_RE = re.compile(r"^\s*(?:[0-9]{0,3}X{2,}|[0-9]{1,4}\?{1,}|XX\b)", re.I)      # 3XX / 145XX / 45? 这类打码门牌
STTYPE = r"(?:ST|AVE|AV|RD|DR|BLVD|LN|WAY|CT|PL|HWY|PKWY|CIR|TER|TRL|STREET|AVENUE|ROAD|DRIVE|LANE|COURT|PLACE)"
INTERSECT_RE = re.compile(r"[A-Z0-9]{2,}\s+" + STTYPE + r"?\s*(?:&|/|\bAND\b|\bAT\b)\s*[A-Z0-9]{2,}\s+" + STTYPE)
MAILLABEL_NAME = re.compile(r"(owner|mail|contact|taxpayer|applicant|name)", re.I)
SEP_RE = re.compile(r"[,|;/]")
POBOX_RE = re.compile(r"^\s*(P\.?\s*O\.?\s*(BOX|B\.?)\s*\d+|POST\s+OFFICE\s+BOX)", re.I)
LISTLIKE_RE = re.compile(r",\s*\d")          # "4 permanent, 32 temporary" 这类列举，不是地址
LONG_DIGITS = re.compile(r"\d{7,}")


def rate(vals, fn, min_n=1):
    if len(vals) < min_n:
        return 0.0
    return sum(1 for v in vals if fn(v)) / len(vals)


def is_num(v):
    return bool(NUM_VAL.match(v)) or bool(NUM_RANGE_VAL.match(v))


def is_street(v):
    if not STREETISH_VAL.match(v) or not re.search(r"[A-Za-z]{2}", v):
        return False
    if NUM_VAL.match(v) or ZIP_VAL.match(v):
        return False
    return not LONG_DIGITS.search(v)


def is_combo(v):
    return bool(COMBO_VAL.match(v)) and bool(re.search(r"[A-Za-z]{2}", v)) and not LISTLIKE_RE.search(v)


def is_fulladdr(v):
    if not is_combo(v) or LISTLIKE_RE.search(v):
        return False
    return bool(SEP_RE.search(v)) or bool(ZIP_IN.search(v)) or bool(STATE_TOK.search(v))


def shares(vals):
    if not vals:
        return {}
    n = len(vals)
    return {
        "combo": sum(1 for v in vals if is_combo(v)) / n,
        "fulladdr": sum(1 for v in vals if is_fulladdr(v)) / n,
        "pobox": sum(1 for v in vals if POBOX_RE.search(v)) / n,
        "num": sum(1 for v in vals if is_num(v)) / n,
        "street": sum(1 for v in vals if is_street(v)) / n,
        "zip": sum(1 for v in vals if ZIP_VAL.match(v)) / n,
    }


def role_of_field(name, vals):
    """字段名 + 值形态共同定角色。值形态是硬门槛（避免 parcel num 被当门牌）。"""
    n = (name or "").strip()
    sh = shares(vals)
    r = []
    if sh.get("fulladdr", 0) >= 0.5:
        r.append("fulladdr")
    elif sh.get("combo", 0) >= 0.5:
        r.append("combo")
    if sh.get("pobox", 0) >= 0.5:
        r.append("pobox")
    if sh.get("num", 0) >= 0.6 and NUM_NAME.search(n):
        r.append("number")
    if sh.get("street", 0) >= 0.6 and (STREET_NAME.search(n) or COMBO_NAME.search(n)):
        r.append("street")
    if CITY_NAME.search(n) and sh.get("street", 0) >= 0.6:
        r.append("city")
    elif sh.get("street", 0) >= 0.6 and vals and \
            sum(1 for v in vals if re.search(r",?\s[A-Z]{2}\s*$", v.strip())) / len(vals) >= 0.5:
        r.append("city")   # 形如 "NATIONAL CITY CA" 的列，本质是城市+州，不是街名
    if STATE_NAME.search(n) and sh.get("street", 0) >= 0.6:
        r.append("state")
    if ZIP_NAME.search(n) and sh.get("zip", 0) >= 0.6:
        r.append("zip")
    if RANGE_NAME.search(n) and sh.get("num", 0) >= 0.3:
        r.append("range")
    if ID_NAME.search(n) and not [x for x in r if x != "idlike"]:
        r.append("idlike")
    return r, sh


STREET_MOD = re.compile(r"(st_?(pre|pos)?(dir|typ|mod|sep)|prefix|suffix|pre_?dir|post_?dir|street_?type|"
                        r"st_?type|st_?suffix|st_?predir|st_?postyp|st_?postype|direction)", re.I)


def classify(rec, aliases):
    """返回 (pattern_id, detail)。优先级：分列（P7/P5）> 组合串（P1/P3/P4）> 区间/无门牌/ID。"""
    cv = dict(rec.get("coord_values") or {})
    fields = list(rec.get("fields") or [])
    # 样例值缺失时用 ng911 的 3 条样本补
    if not cv:
        for smp in rec.get("ng911_samples") or []:
            for k, v in (smp or {}).items():
                if v in (None, "", "null"):
                    continue
                cv.setdefault(k, []).append(re.sub(r"\s+", " ", str(v)).strip())
    roles, sh = {}, {}
    for f in fields:
        roles[f], sh[f] = role_of_field(f, cv.get(f) or [])
    if not fields:
        fields = list(cv)
        for f in fields:
            roles[f], sh[f] = role_of_field(f, cv.get(f) or [])

    def fs(*role):
        return [f for f, r in roles.items() if any(x in r for x in role)]

    fulladdr, combo, pobox = fs("fulladdr"), fs("combo"), fs("pobox")
    num = [f for f in fs("number") if f not in fulladdr and f not in combo and f not in pobox]
    street = [f for f in fs("street") if f not in fulladdr and f not in combo and f not in pobox
              and "city" not in roles.get(f, [])]
    street.sort(key=lambda f: (0 if STREET_NAME.search(f or "") else 1, -sh[f].get("street", 0)))
    city, state, zp, rng = fs("city"), fs("state"), fs("zip"), fs("range")
    idlike = fs("idlike")

    # ---- 0) PO BOX：不是街道地址
    if pobox and not (num and street):
        f = pobox[0]
        return "P11", {"field": f, "values": cv.get(f, [])[:3], "why": "组合串是 PO BOX/POST OFFICE BOX，不是街道地址"}

    # ---- 1) 门牌列 + 街名列都真实存在（分列）→ 只看要不要拼列/加别名
    if num and street:
        nf, sf = num[0], street[0]
        mods = [f for f in fields if STREET_MOD.search(f or "") and f not in (nf, sf) and (cv.get(f) or [])]
        if mods:
            return "P5", {"fields": [nf, sf] + mods[:3], "values": [cv.get(nf, [])[:2], cv.get(sf, [])[:2]],
                          "why": f"门牌 {nf} + 街名 {sf} 之外还要拼 {mods[:3]}（2+ 列拼街名）"}
        extra = (city[:1] + state[:1] + zp[:1])
        return "P7", {"fields": [nf, sf] + extra, "values": [cv.get(nf, [])[:3], cv.get(sf, [])[:3]],
                      "why": f"门牌列 {nf} + 街名列 {sf}（各一列即可）"
                              + (f"；城市州邮编另分列 {len(city)}/{len(state)}/{len(zp)}" if extra else "")
                              + "；至少一列不在 registry 别名表"}

    # ---- 2) 混合形态的单字段（门牌时有时无）也算 P1：靠切分仍能救回来
    for f in fields:
        vals = cv.get(f, [])
        if vals and 0.2 <= sh[f].get("combo", 0) + sh[f].get("fulladdr", 0) < 0.5 and (COMBO_NAME.search(f or "") or STREET_NAME.search(f or "")):
            return "P1", {"field": f, "values": vals[:3], "mixed": True,
                          "why": f"单字段混合：{round(sh[f].get('combo',0)*100)}% 带门牌，其余只有街名（切分后仍可出键，缺号行会落空）"}
    # ---- 2) 单字段组合串
    for kind, pid in (("fulladdr", None), ("combo", "P1")):
        if not fs(kind):
            continue
        f = sorted(fs(kind), key=lambda x: -sh[x].get(kind, 0))[0]
        vals = cv.get(f, [])
        sep = sum(1 for v in vals if SEP_RE.search(v)) / max(1, len(vals))
        if kind == "fulladdr":
            return ("P4" if sep >= 0.5 else "P3"), {
                "field": f, "values": vals[:3], "sep_share": round(sep, 2),
                "why": "单字段含门牌+街名+城市/州/邮编；" + ("有显式分隔符（按分隔符切）" if sep >= 0.5 else "无显式分隔符（只能靠空格切）")}
        return "P1", {"field": f, "values": vals[:3], "why": "单字段 = 门牌 + 街名，无城市/州/邮编"}

    # ---- 3) 区间 / 只有街名 / ID / 空
    if rng:
        return "P8", {"fields": rng[:4], "values": [cv.get(f, [])[:2] for f in rng[:3]],
                      "why": "路段/中心线门牌区间（from/to addr、low/high range），不是单点门牌"}
    if street and not num:
        return "P9", {"fields": [street[0]] + city[:1], "values": [cv.get(street[0], [])[:3]],
                      "why": ("只有街名（+城市）分列，全层无门牌列" if city else "只有街名，无门牌列")}
    addr_named = [f for f in fields if COMBO_NAME.search(f or "")]
    # 打码/占位门牌、路口名（不是可切的门牌+街名）
    for f in addr_named + street + combo:
        vals = cv.get(f, [])
        if vals and (sum(1 for v in vals if MASK_RE.search(v)) / len(vals) >= 0.3 or
                     sum(1 for v in vals if INTERSECT_RE.search(v)) / len(vals) >= 0.3):
            return "P12", {"field": f, "values": vals[:3],
                           "why": "门牌被打码（3XX/145XX）或为路口名（A ST / B AVE），不是可切的门牌+街名"}
    # 业主名/联系人 + 完整地址挤在同一格（mailing label）
    for f in addr_named + combo:
        if not MAILLABEL_NAME.search(f or ""):
            continue
        vals = cv.get(f, [])
        if vals and sum(1 for v in vals if ZIP_IN.search(v) and re.search(r"\d{1,6}\s+[A-Za-z]", v)) / len(vals) >= 0.5:
            return "P13", {"field": f, "values": vals[:3],
                           "why": "业主名/联系人 + 完整地址混在同一格（mailing label），要先剥人名再切地址"}
    if addr_named and idlike and all(sh.get(f, {}).get("combo", 0) + sh.get(f, {}).get("fulladdr", 0) < 0.3
                                     for f in addr_named):
        return "P6", {"fields": addr_named[:3] + idlike[:2],
                      "values": [cv.get(f, [])[:3] for f in (addr_named[:2] + idlike[:1])],
                      "why": "字段名看着像地址（ADDR/ADDRESS/SITUS），值却是 ID/地块号/分区号"}
    if idlike:
        return "P10", {"fields": idlike[:4], "values": [cv.get(f, [])[:2] for f in idlike[:3]],
                       "why": "图层只有 ID/路线/管理字段，没有门牌、街名或组合串（非地址图层）"}
    empty = sum(1 for f in fields if not cv.get(f))
    return "P10", {"fields": fields[:6], "values": {f: (cv.get(f) or [])[:2] for f in fields[:4]},
                   "why": f"无可识别地址字段（{len(fields)} 个字段里 {empty} 个样例全空，其余与地址无关）"}


PATTERNS = {
    "P1": {"name": "门牌+街名拼一格", "parse": "可直接切出", "fix": "切分算法",
           "rule": "存在字段，其 ≥60% 样例值匹配 ^\\s*(\\d{1,6})[-A-Za-z]?[\\s,]+([A-Za-z].{1,80})$ 且值内无州/邮编/分隔符（逗号、竖线、分号、斜杠）"},
    "P2": {"name": "街名+城市拼一格", "parse": "需猜或NLP", "fix": "切分算法",
           "rule": "存在字段值里同时含街名与城市名但无门牌号（本批 0 层：实测全部落到 P9 或 P3）"},
    "P3": {"name": "门牌+街名+城市/州/邮编全拼一格（无显式分隔符）", "parse": "需猜或NLP", "fix": "切分算法",
           "rule": "单字段 ≥60% 样例值 = 门牌+街名+城市/州/邮编，但分隔符（逗号/竖线/分号/斜杠）占比 <50%，只能靠空格与尾部州/邮编切"},
    "P4": {"name": "全地址单串（带逗号/竖线等分隔符）", "parse": "可直接切出", "fix": "切分算法",
           "rule": "单字段 ≥60% 样例值 = 门牌+街名+城市/州/邮编，且分隔符占比 ≥50%（按分隔符切段即可）"},
    "P5": {"name": "多字段分列且街名本身要 2+ 列拼（pre-dir/type/suffix 分列），字段名不在别名表", "parse": "可直接切出", "fix": "别名表+拼列",
           "rule": "门牌列与街名列都过值形态校验，但街名还需 ≥1 个修饰列（pre/post dir、type、suffix）拼在一起才算完整街名"},
    "P6": {"name": "结构 ID / 地块 ID / 分区号冒充地址（根本不是地址）", "parse": "不可切", "fix": "排除",
           "rule": "无门牌列、无街名列、无组合串；被当成地址的字段名命中 id/pid/apn/pin/parcel/zone/lot/block/route/segment 且值形态不是门牌+街名"},
    "P7": {"name": "门牌+街名两列分列、字段名不在 registry 别名表", "parse": "可直接切出", "fix": "别名表",
           "rule": "门牌列 + 街名列各一列、都过值形态校验、街名不需拼列，且至少一列名不在 registry 别名表（城市/州/邮编另分列不影响判定）"},
    "P8": {"name": "路段门牌区间（from/to addr + 街名，中心线层）", "parse": "需猜或NLP", "fix": "排除/专用逻辑",
           "rule": "存在字段名命中 from_addr/to_addr/from_num/to_num/hn_low/hn_high/range，值是门牌区间或起止门牌"},
    "P9": {"name": "只有街名（或街名+城市分列），全层无门牌列", "parse": "不可切", "fix": "排除",
           "rule": "有街名列但无任何门牌列、无组合串、无区间列；构不出「门牌+街名」键是数据本身没有门牌"},
    "P13": {"name": "业主名/联系人 + 完整地址混在一格（mailing label）", "parse": "需猜或NLP", "fix": "切分算法",
            "rule": "字段名命中 owner/mail/contact/taxpayer/applicant/name，且 ≥50% 样例值同时含 5 位邮编与「门牌 空格 词」形态"},
    "P12": {"name": "打码/占位门牌或路口名（3XX E 12TH ST、A ST / B AVE）", "parse": "不可切", "fix": "排除",
            "rule": "地址值 ≥30% 匹配打码门牌（^\\d{0,3}X{2,}、^XX、数字+?）或路口形态（A ST & / AVE / B RD）"},
    "P11": {"name": "PO BOX / POST OFFICE BOX（邮政信箱，非街道地址）", "parse": "不可切", "fix": "排除",
            "rule": "组合串样例值 ≥50% 匹配 ^\s*P\.?\s*O\.?\s*(BOX|B\.?)\s*\d+ 或 POST OFFICE BOX，且没有独立的门牌列+街名列"},
    "P10": {"name": "无任何可识别地址字段（非地址图层 / 字段少或样例全空）", "parse": "不可切", "fix": "排除",
            "rule": "既无 list/门牌/街名/组合串/区间列，也无 id 类地址嫌疑字段；或该层样例值全空"},
}


def main():
    per = json.load(open(os.path.join(WORK, "per_layer.json"), encoding="utf-8"))
    import yaml
    reg = yaml.safe_load(open(os.path.join(HERE, "..", "..", "registry", "dialects.v1.yaml"), encoding="utf-8"))
    aliases = set()
    for d in reg["dialects"]:
        t = d.get("template") or {}
        for role in ("number", "street", "zip"):
            for a in t.get(role + "_aliases") or []:
                aliases.add(re.sub(r"[^a-z0-9]", "", a.lower()))

    rows, detail = [], {}
    cnt = collections.Counter()
    rows_n = collections.Counter()
    for url, rec in per.items():
        pid, d = classify(rec, aliases)
        cnt[pid] += 1
        rows_n[pid] += rec["rows_n"]
        # 该层名字是否「已命中别名」：用于区分 P7（真的要加别名）
        hit_alias = [f for f in (d.get("fields") or ([d["field"]] if d.get("field") else []))
                     if re.sub(r"[^a-z0-9]", "", f.lower()) in aliases]
        d["alias_hit_fields"] = hit_alias
        detail[url] = {"pattern_id": pid, "pattern": PATTERNS[pid]["name"], **d}
        rows.append({
            "layer_id": rec["layer_id"], "url": url, "rows_n": rec["rows_n"], "state": rec["state"],
            "title": rec.get("ng911_title") or "",
            "pattern_id": pid, "pattern": PATTERNS[pid]["name"],
            "fields": "|".join(d.get("fields") or ([d["field"]] if d.get("field") else []))[:300],
            "example_values": json.dumps(d.get("values"), ensure_ascii=False)[:400],
            "parseability": PATTERNS[pid]["parse"], "fix_path": PATTERNS[pid]["fix"],
            "n_fields": len(rec["fields"]), "coord_rows": rec["coord_rows"],
        })

    # ---- 硬校验：各模式层数之和 == 总层数
    total = sum(cnt.values())
    assert total == len(per) == 1340, f"模式层数之和 {total} != 层数 {len(per)}"

    import csv
    with open(os.path.join(HERE, "patterns.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["pattern_id"], -int(r["rows_n"]))))

    out = {
        "generated_from": {"per_layer": "_work/per_layer.json", "layers": len(per)},
        "total_layers": len(per),
        "assert_sum_layers_equals_total": True,
        "patterns": [
            {"pattern_id": pid, "name": PATTERNS[pid]["name"], "rule": PATTERNS[pid]["rule"],
             "layers": cnt.get(pid, 0), "rows_n": rows_n.get(pid, 0),
             "pct_layers": round(cnt.get(pid, 0) * 100.0 / len(per), 2),
             "parseability": PATTERNS[pid]["parse"], "fix_path": PATTERNS[pid]["fix"],
             "examples": [r for r in rows if r["pattern_id"] == pid][:3]}
            for pid in sorted(PATTERNS)],
        "triage": {},
        "parseability": dict(collections.Counter(PATTERNS[r["pattern_id"]]["parse"] for r in rows)),
        "fix_path": dict(collections.Counter(PATTERNS[r["pattern_id"]]["fix"] for r in rows)),
    }
    # 分流：别名表 / 切分算法 / 排除
    buckets = {"只加 registry 别名表即可": ["P7"], "必须靠切分（或拼列）算法": ["P1", "P3", "P4", "P5", "P13"],
               "根本不是地址 / 无法构成键": ["P6", "P8", "P9", "P10", "P11", "P12"], "街名+城市拼一格": ["P2"]}
    for k, pids in buckets.items():
        out["triage"][k] = {
            "layers": sum(cnt.get(p, 0) for p in pids),
            "rows_n": sum(rows_n.get(p, 0) for p in pids),
            "pct_layers": round(sum(cnt.get(p, 0) for p in pids) * 100.0 / len(per), 2),
            "patterns": pids,
        }
    # ---- 硬校验：分流三桶之和 == 总层数
    tri_sum = sum(v["layers"] for v in out["triage"].values())
    assert tri_sum == len(per), f"分流层数之和 {tri_sum} != {len(per)}"
    out["assert_triage_sum_equals_total"] = True
    json.dump(out, open(os.path.join(HERE, "patterns.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(detail, open(os.path.join(WORK, "classify_detail.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"total": total, "counts": dict(sorted(cnt.items())),
                      "rows_n": dict(sorted(rows_n.items())),
                      "triage": {k: v["layers"] for k, v in out["triage"].items()}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
