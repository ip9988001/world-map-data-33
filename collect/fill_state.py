#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 补州归属：对 state=未定位 的层做文本判定（州全名 / 唯一两字母州码 token）。"""
from __future__ import annotations
import csv, json, os, re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CSVF = os.path.join(HERE, "situs_layers.csv")

FULL = {"alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
 "colorado":"CO","connecticut":"CT","delaware":"DE","florida":"FL","georgia":"GA",
 "hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA","kansas":"KS",
 "kentucky":"KY","louisiana":"LA","maine":"ME","maryland":"MD","massachusetts":"MA",
 "michigan":"MI","minnesota":"MN","mississippi":"MS","missouri":"MO","montana":"MT",
 "nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ","new mexico":"NM",
 "new york":"NY","north carolina":"NC","north dakota":"ND","ohio":"OH","oklahoma":"OK",
 "oregon":"OR","pennsylvania":"PA","rhode island":"RI","south carolina":"SC",
 "south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT",
 "virginia":"VA","washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY",
 "district of columbia":"DC","puerto rico":"PR"}
ABBR = set(FULL.values())


def guess(layer: str, url: str):
    hay = (layer + " " + url).lower()
    # 1. 州全名（最可靠）
    for full, ab in FULL.items():
        if full in hay:
            return ab, "full_name"
    # 2. 两字母州码 token（原始大小写，必须全大写且独立）
    for src, tag in ((layer, "name_abbr"), (url, "url_abbr")):
        toks = re.split(r"[^A-Za-z]+", src)
        two = [t for t in toks if len(t) == 2 and t.isupper() and t in ABBR]
        if not two:
            continue
        c = Counter(two)
        if len(c) == 1:
            ab = two[0]
            return ab, tag + ("_x%d" % c[ab] if c[ab] > 1 else "")
        # 多个州码：取唯一最多的；并列则放弃
        mc = c.most_common()
        if mc[0][1] > mc[1][1]:
            return mc[0][0], tag + "_max"
    return "", "none"


def main():
    rows = list(csv.DictReader(open(CSVF, encoding="utf-8")))
    stat, rows_by = Counter(), Counter()
    fixed = 0
    for r in rows:
        r["state_src"] = "probe"
        if r["state"] != "未定位":
            continue
        ab, src = guess(r["layer_id"], r.get("url", ""))
        r["state_src"] = src
        if ab:
            r["state"] = ab
            fixed += 1
            stat[src] += 1
            rows_by[ab] += int(r["rows"])
        else:
            stat["none"] += 1
    fn = ["layer_id","state","state_src","geom","rows","grade","reason","nfields","fields_hit","url"]
    with open(CSVF, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); w.writerows(rows)
    unk_rows = sum(int(r["rows"]) for r in rows if r["state"] == "未定位" and r["grade"] in ("strong","weak"))
    out = {"fixed_layers": fixed, "src": dict(stat),
           "still_unknown_layers": sum(1 for r in rows if r["state"]=="未定位"),
           "still_unknown_rows_strong_weak": unk_rows,
           "strong_by_state_top": Counter(),
           }
    st = Counter()
    for r in rows:
        if r["grade"] == "strong" and r["state"] != "未定位":
            st[r["state"]] += int(r["rows"])
    out["states_strong"] = len(st)
    out["strong_rows_known"] = sum(st.values())
    out["top"] = st.most_common(8)
    json.dump(out, open(os.path.join(HERE,"fill_state.json"),"w",encoding="utf-8"),
              ensure_ascii=False, indent=1, default=dict)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=dict))
    open("/tmp/s2.txt","w",encoding="utf-8").write(
"\n".join([
"✅ 10-P 自研 S2/7 · 补州归属完成",
"",
"未定位 4,583 层 → 补上 %d 层（%.0f%%）" % (fixed, fixed*100.0/4583),
"· 州全名命中 %d 层" % stat["full_name"],
"· 州码 token 命中 %d 层" % (stat["name_abbr"]+stat["url_abbr"]),
"· 仍无法判定 %d 层" % stat["none"],
"",
"strong 层现在覆盖 %d 州 / %s 亿行可采" % (len(st), round(sum(st.values())/1e8,2)),
"仍挂未定位的 strong+weak 行数：%s" % format(unk_rows, ","),
"",
"做法：州全名优先，其次独立大写两字母州码；纯文本判不出的留给 S5 读属性 STATE 字段。",
"",
"下一步 S3：可采清单定稿（按州对齐你已有的 47 州）"]))

if __name__ == "__main__":
    main()
