#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳② step3：从字段证据里定「明确是门牌列 / 街名列」的别名，其余进待定表。

严格白名单（名字必须直说自己是门牌号或街道名，值形态还必须过）：
  number：hous / hse / 独立 hn / addr+num 组合 / situs+num / street(no|number)
  street：名字里带 street 或 st_name/stname 语义，且不是 type/suffix/prefix/direction/全地址/城市/人名
值形态门槛（与 step1 同源，不放松）：number ≥60% 样本值形如 1~6 位数字（可带 A 或 -1）+ 该层有共同成立的街名列；
                               street ≥60% 样本值有字母、不是纯门牌、不含 5 位邮编/州缩写。
其余全部进 pending（带原因），一条都不塞进别名表。

产物：_work/alias_final.json（applied / pending / 逐别名归属层）
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")

HN_ALLOW = re.compile(r"(hous|hse|addr(ess)?_?(num|no|nbr)|addr.*nbr|num.*addr|sit(us)?_?(num|no)|"
                      r"st(num|reet)?_?no|street_?number|(^|[^a-z])hn([^a-z]|$)|anum)", re.I)
HN_DENY = re.compile(r"(count|total|number_?of|num_?of|household|population|person|injr|fatal|crash|ksi|"
                     r"score|index|seq|acct|inv|xrf|^map|loop|visit|retail|sna_|esn|nguid|emp|tran|arrest|"
                     r"user|_rev_|rem_|numparts|numgqtrs|^numin|numoccup|numcbldg|numtrks|numb.?vehc|"
                     r"num_?slabs|num_?fruit|numberof|numof|hyd|ldmk|funcnum|muni|cds|subd|srt|stp|overall|"
                     r"apt|apartment|unit|suite|ste_|_id$|guid|class|section|sect|year|yr_|effective)", re.I)
ST_ALLOW = re.compile(r"(street|st_?name|stnam)", re.I)
ST_DENY = re.compile(r"(suf|sufix|prefix|prefx|pre_?dir|post_?dir|_?dir(_|$)|type|typ|_city|city_|city$|"
                     r"guid|_id$|verif|priority|linked|notalready|level|auth|from_|to_|location|attention|"
                     r"combined|full_?addr|^address|address_?\d|street_?address|parcel|prcl|mail|own|"
                     r"last_?name|lst_?name|first_?name|statute|_sou$|_own$|sweeping|operation)", re.I)
# 人工复核后剔除（理由写在 pending 原因里）：值形态过了但名字/语义不可靠
MANUAL_DENY = {"V_StName": "样本值是人名（Michael/Ashton），不是街名", "Street_Nam": "样本值 98% 是纯数字，实为门牌或错列",
               "STREET_NAM": "有层样本值纯数字，语义混杂（同族 STREET_NAME 已在别名表）",
               "ADDRNUMTT": "后缀 TT 含义不明（total?），不敢认定门牌"}
RANGE_RE = re.compile(r"(_r(_to)?$|_r_|from_|_from|_to$|start|beg|low|high|_hi)", re.I)
PENDING_RE = re.compile(r"(owner|ownaddr|own_?adr|mail|bill|contact|taxpayer|applicant|deed|ship_?to|"
                        r"pobox|po_?box|legal|mortgage|insur)", re.I)


def main():
    ev = json.load(open(os.path.join(WORK, "alias_evidence.json")))
    fields, pairs = ev["fields"], ev["verified_pairs"]
    verified_hn = {p["number_field"] for p in pairs}
    verified_st = {p["street_field"] for p in pairs}

    applied, pending = [], []
    for f, e in sorted(fields.items()):
        hn_ok = f in verified_hn and e["hn_share"] >= 0.6
        st_ok = f in verified_st and e["st_share"] >= 0.6
        if not (hn_ok or st_ok):
            continue
        role = "number" if hn_ok and not st_ok else ("street" if st_ok and not hn_ok else "conflict")
        rec = {"alias": f, "role": role, "hn_share": e["hn_share"], "st_share": e["st_share"],
               "layers": len(e["layers"]), "sample_values": e["vals"][:3]}
        if role == "conflict":
            pending.append(dict(rec, reason="同名字段在不同层分任门牌列/街名列（语义冲突）"))
            continue
        if f in MANUAL_DENY:
            pending.append(dict(rec, reason=MANUAL_DENY[f]))
            continue
        if RANGE_RE.search(f):
            pending.append(dict(rec, reason="门牌区间/起止列（P8 型，单点地址不适用）"))
            continue
        if PENDING_RE.search(f):
            pending.append(dict(rec, reason="像业主/邮寄/联系地址，是否地点地址未定（派单边界）"))
            continue
        if role == "number" and HN_ALLOW.search(f) and not HN_DENY.search(f):
            applied.append(rec)
        elif role == "street" and ST_ALLOW.search(f) and not ST_DENY.search(f):
            applied.append(rec)
        else:
            pending.append(dict(rec, reason="值形态像" + ("门牌" if role == "number" else "街名")
                                     + "，但列名语义不明确（未过白名单）"))

    num = [a for a in applied if a["role"] == "number"]
    st = [a for a in applied if a["role"] == "street"]
    json.dump({"applied": applied, "pending": pending,
               "n_number": len(num), "n_street": len(st),
               "layers_covered": sorted({p["url"] for p in pairs
                                         if p["number_field"] in {a["alias"] for a in num}
                                         and p["street_field"] in {a["alias"] for a in st}})},
              open(os.path.join(WORK, "alias_final.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"number_aliases": len(num), "street_aliases": len(st),
                      "applied_total": len(applied), "pending": len(pending),
                      "p7_layers_covered_by_applied": len({p["url"] for p in pairs
                                                           if p["number_field"] in {a["alias"] for a in num}
                                                           and p["street_field"] in {a["alias"] for a in st}})},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
