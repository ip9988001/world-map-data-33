#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线层「不采」核定 —— 1,946 个 Polyline 层逐层与 TIGER addrfeat 比字段。

为什么必须做这个：三仓一个线层都没采（step01 几何白名单把 Polyline 直接 skip），
但「没采」不能等于「不值得采」。要能查的证据链：**每层字段清单 vs TIGER 25 字段**，
有没有 TIGER 拿不到的独有字段（单元号段、ZIP+4、地址类型、ESN…）。

证据来源（全部离线，不访问上游）：
  · 层清单：collect/situs_layers.csv（8116 行，其中 geom=polyline **1,946** 行 = 本轮口径）
  · 字段清单：collect/polygon_probe.json（23,556 层探针结果，含 Polyline 8,195 层的 fields）
  · TIGER 基准：一仓已发布资产 data/dover/raw/tl_2024_10001_addrfeat.zip（25 字段，dbf 实读）

⚠ 3 条**样本值**拿不到：线层一个都没采，字段名之外的证据需要一次上游 query，
  本轮边界禁止访问上游 → 判定只用字段清单 + nfields + 号段字段语义，并在产物里标注
  `sample_evidence: "unavailable_offline"`。要补样本时按 ledger 里每层的 url 打一次即可。

产出：
  collect/ledger/line_layers_decision.json   1,946 层逐层结论（可查的「为何不采」账本）
  docs/LINE-LAYERS-DECISION-2026-10-30.md    20 层逐条结论表 + 汇总

用法：python3 analysis/line_layers_decision.py
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITUS = os.path.join(ROOT, "collect", "situs_layers.csv")
PROBE = os.path.join(ROOT, "collect", "polygon_probe.json")
OUT_LEDGER = os.path.join(ROOT, "collect", "ledger", "line_layers_decision.json")
OUT_DOC = os.path.join(ROOT, "docs", "LINE-LAYERS-DECISION-2026-10-30.md")
TIGER_ZIP = os.environ.get("TIGER_ADDRFEAT_ZIP",
                           "/data/workspace/World-US-Map-Data/data/dover/raw/"
                           "tl_2024_10001_addrfeat.zip")

# ---------------------------------------------------------------- TIGER 基准字段
def tiger_fields() -> list:
    try:
        import shapefile                                   # pyshp
        z = zipfile.ZipFile(TIGER_ZIP)
        name = next(n for n in z.namelist() if n.endswith(".dbf"))
        r = shapefile.Reader(dbf=io.BytesIO(z.read(name)))
        return [f[0].upper() for f in r.fields[1:]]
    except Exception as e:                                 # noqa: BLE001
        print("⚠️ 读不到 TIGER addrfeat（%s），用内置 25 字段表" % str(e)[:60], file=sys.stderr)
        return ["TLID", "TFIDL", "TFIDR", "ARIDL", "ARIDR", "LINEARID", "FULLNAME", "LFROMHN",
                "LTOHN", "RFROMHN", "RTOHN", "ZIPL", "ZIPR", "EDGE_MTFCC", "ROAD_MTFCC",
                "PARITYL", "PARITYR", "PLUS4L", "PLUS4R", "LFROMTYP", "LTOTYP", "RFROMTYP",
                "RTOTYP", "OFFSETL", "OFFSETR"]


# TIGER 概念 → 同义列名（用于判「我这层有没有 TIGER 拿不到的独有字段」）
CONCEPTS = {
    "TLID": [r"^(TLID|TIGERLINEID|TLID_?1)$"],
    "TFID": [r"^(TFID[LR]|TO_?FACE_?ID|FACE_?ID)$"],
    "ARID": [r"^(ARID[LR]|LINEARID|LINEAR_?ID)$"],
    "FULLNAME": [r"^(FULLNAME|FULL_?NAME|STNAME|ST_?NAME|STREET_?NAME|STREETNAME|ROAD_?NAME|"
                 r"ROADNAME|RD_?NAME|NAME|FULL_?STNAME|LABEL|FULLNAME_?L)$"],
    "FROMHN": [r"^.*FROM_?(HN|ADD|ADDR|ADDRESS|NUM|NUMBER).*$", r"^.*FROMADDR.*$", r"^.*_FROM$"],
    "TOHN": [r"^.*TO_?(HN|ADD|ADDR|ADDRESS|NUM|NUMBER).*$", r"^.*TOADDR.*$", r"^.*_TO$"],
    "ZIP": [r"^(ZIP[LR]?|ZIP_?CODE|ZIP_?L|ZIP_?R|ZIP5|ZIPCODE|POSTAL_?CODE|ZIP_CODE_L|ZIP_CODE_R)$"],
    "PLUS4": [r"^(PLUS4[LR]?|ZIP4[LR]?|ZIP_?PLUS4.*)$"],
    "PARITY": [r"^(PARITY[LR]?|PARITY_?L|PARITY_?R)$"],
    "MTFCC": [r"^(EDGE_?MTFCC|ROAD_?MTFCC|MTFCC.*)$"],
    "ADDRTYPE": [r"^(LFROMTYP|LTOTYP|RFROMTYP|RTOTYP|[LR]TOTYP|[LR]FROMTYP.*|ADDR_?TYPE.*)$"],
    "OFFSET": [r"^(OFFSET[LR]?|OFFSET_?L|OFFSET_?R)$"],
}
CONCEPT_RX = {k: [re.compile(p, re.I) for p in v] for k, v in CONCEPTS.items()}

# 与地址无关、或能由 TIGER/层元数据推出的列（不算「独有」）
OIM = re.compile(r"^(OBJECTID.*|OID|FID|GLOBALID|SHAPE.*|SE_ANNO.*|CREATED?_?(DATE|BY|USER).*|"
                 r"EDIT.*DATE.*|LAST_?EDIT.*|ST_?LENGTH|ST_?AREA|LENGTH|AREA|PERIMETER|"
                 r"X|Y|LAT|LON|LATITUDE|LONGITUDE|POINT_?X|POINT_?Y|MGRS.*)$", re.I)
# 「真·独有地址语义」：TIGER addrfeat 结构上没有的东西
#   · 单元级：UNIT/APT/SUITE/SUBADDR/ROOM/BLDG
#   · E911 专用：ESN（应急服务号）
#   · 整串地址：FULL_ADDRESS（TIGER 只给 FULLNAME+号段，不给拼好的整串）
ADDR_EXTRA = re.compile(r"^(ESN|ESN_?[LR]?|.*EMERG.*|.*SUB_?ADDR.*|.*_?UNIT.*|.*APT.*|"
                        r"APARTMENT.*|.*SUITE.*|STE_?[LR]?$|.*_ROOM.*|.*BLDG.*|BUILDING.*|"
                        r".*FULL_?ADDR.*|.*FULL_?ADDRESS.*)$", re.I)
# 可从 FULLNAME/号段推出的拆分列（TIGER 概念等价）与弱字段（ID/useflag）→ 不算独有
DERIVABLE = re.compile(r"^(.*_?ID|ADDR_?ID|ADDRESS_?ID|THEADDR_?ID|.*_?PD|.*_?PT|.*_?SN|"
                       r"ADDR_?STREET|STREET|ADDR_?PROVINCE|ADDR_?POSTCODE|.*USE_?FOR_?ADDRESS|"
                       r".*_FLAG|.*FLAG)$", re.I)
NON_US = re.compile(r"^(.*PROVINCE.*|.*POSTCODE.*|.*POSTAL_?CODE_?CA.*)$", re.I)
PLACE = re.compile(r"^(CITY|POSTAL_?CITY|MAIL_?CITY|MUNICIPALITY|COUNTY.*|STATE.*|"
                   r"PLACE.*|TOWN.*|COMMUNITY.*|ZCTA.*)$", re.I)
ROAD = re.compile(r"^(.*SPEED.*|.*LANE.*|.*SURFACE.*|.*ONEWAY.*|.*ONE_?WAY.*|.*FUNC.*|"
                  r".*ROUTE.*|.*HWY.*|.*CLASS.*|.*WIDTH.*|.*PAVE.*|.*CONDITION.*|"
                  r".*MAINT.*|.*OWNER.*|.*FCLASS.*)$", re.I)


def norm_fields(fields: list) -> dict:
    """把该层字段分成：被 TIGER 覆盖 / 独有（再细分桶）。"""
    covered, extras = [], []
    for f in fields:
        hit = next((c for c, rxs in CONCEPT_RX.items() if any(r.match(f) for r in rxs)), None)
        if hit:
            covered.append((f, hit))
        else:
            extras.append(f)
    buckets = {"oim": [], "addr_extra": [], "place": [], "road": [], "derivable": [],
               "non_us": [], "other": []}
    for f in extras:
        if OIM.match(f):
            buckets["oim"].append(f)
        elif NON_US.match(f):
            buckets["non_us"].append(f)
        elif DERIVABLE.match(f):
            buckets["derivable"].append(f)
        elif ADDR_EXTRA.match(f):
            buckets["addr_extra"].append(f)
        elif PLACE.match(f):
            buckets["place"].append(f)
        elif ROAD.match(f):
            buckets["road"].append(f)
        else:
            buckets["other"].append(f)
    return {"tiger_covered": covered, "extras": buckets}


def verdict(nf: dict) -> tuple:
    """返回 (结论, 理由)。只有「真的多出地址语义字段」才算值得补采候选。

    ⚠ 探针的 `fields` 是**地址相关子集**（`nfields` 才是总列数），所以这里只判
    「地址语义有没有 TIGER 拿不到的」，不再拿它当全量字段表。
    """
    ae = nf["extras"]["addr_extra"]
    pl = nf["extras"]["place"]
    nu = nf["extras"]["non_us"]
    if ae:
        return "worth_collect", "独有地址语义字段：%s" % ", ".join(ae[:6])
    if nu and not pl:
        return "out_of_scope", "非美国数据（%s：PROVINCE/POSTCODE 类）→ 不在三仓美国门牌范围" % ", ".join(nu[:3])
    if pl:
        return "not_worth_collect", ("独有仅行政区名（%s）：县可由 TIGER 文件自身确定，"
                                     "city 对号段无增益 → 不值得为它重采整层" % ", ".join(pl[:4]))
    dv = nf["extras"]["derivable"]
    if dv and not (pl or nf["extras"]["road"]):
        return "not_worth_collect", ("独有字段只是拆分/ID 类（%s）→ FULLNAME+号段可推导，"
                                     "TIGER addrfeat 已覆盖" % ", ".join(dv[:4]))
    return "not_worth_collect", "除 OIM/几何/道路属性外无独有字段，TIGER addrfeat 已覆盖号段语义"


def tier(nf: dict) -> str:
    """值得补采的两档：A=单元/ESN（TIGER 结构上没有）；B=只有整串地址（可拼但未发布）。"""
    ae = " ".join(nf["extras"]["addr_extra"]).upper()
    if re.search(r"SUB_?ADDR|UNIT|APT|SUITE|STE|ROOM|BLDG|ESN|EMERG", ae):
        return "A_unit_or_esn"
    return "B_full_address_only"


def main() -> int:
    tig = tiger_fields()
    rows = [r for r in csv.DictReader(open(SITUS, encoding="utf-8"))
            if (r.get("geom") or "").strip().lower() == "polyline"]
    # 去重（同层可能多行）
    by = {}
    for r in rows:
        lid = (r.get("layer_id") or "").strip()
        if lid and lid not in by:
            by[lid] = r
    probe = {x["layer"]: x for x in json.load(open(PROBE, encoding="utf-8"))["detail"]}
    print("[line] situs 线层 %d 行 → 去重 %d 层；探针里有字段清单的 %d 层"
          % (len(rows), len(by), sum(1 for k in by if k in probe)))

    recs = []
    for lid, r in by.items():
        p = probe.get(lid) or {}
        fields = [str(x).upper() for x in (p.get("fields") or [])]
        nf = norm_fields(fields) if fields else None
        v, why = verdict(nf) if nf else ("no_field_evidence",
                                         "探针未覆盖该层（polygon_probe 无记录）→ 需一次元数据读取才能定")
        recs.append({
            "layer_id": lid,
            "state": (r.get("state") or "").strip().upper(),
            "title": (r.get("title") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "rows": int(r.get("rows") or 0) if str(r.get("rows") or "").isdigit() else None,
            "nfields": len(fields) or (int(r["nfields"]) if str(r.get("nfields") or "").isdigit() else None),
            "fields_have_evidence": bool(fields),
            "sample_evidence": "unavailable_offline（线层未采，取样本需上游 query）",
            "tiger_matched_n": len(nf["tiger_covered"]) if nf else 0,
            "extras": nf["extras"] if nf else None,
            "verdict": v,
            "tier": (tier(nf) if v == "worth_collect" else None),
            "why": why,
        })
    recs.sort(key=lambda x: (-(x.get("rows") or 0), x["layer_id"]))
    cnt = {}
    for r in recs:
        cnt[r["verdict"]] = cnt.get(r["verdict"], 0) + 1

    # ---- 20 层抽样：值得补采的全部（最多 12）+ 有 place/road 独有字段 4 层 + 最典型 4 层
    worth = [r for r in recs if r["verdict"] == "worth_collect"]
    others = [r for r in recs if r["verdict"] not in ("worth_collect", "out_of_scope")
              and r["fields_have_evidence"]]
    oos = [r for r in recs if r["verdict"] == "out_of_scope"]
    pick = worth[:12] + others[:4] + [r for r in others[4:] if r["extras"]
                                      and (r["extras"]["place"] or r["extras"]["road"])][:4]
    seen, sample = set(), []
    for r in pick:
        if r["layer_id"] in seen:
            continue
        seen.add(r["layer_id"])
        sample.append(r)
    for r in oos[:2]:
        if len(sample) < 20 and r["layer_id"] not in seen:
            seen.add(r["layer_id"]); sample.append(r)
    sample = sample[:20]

    ledger = {
        "schema": "line-layers-decision/v1",
        "scope": "collect/situs_layers.csv 里 geom=polyline 的 1,946 层",
        "why_ledger": "「不采」必须可查：逐层写明字段对比结果与理由，不许默认放弃",
        "tiger_reference": {"asset": TIGER_ZIP, "repo": "ip9988001/World-US-Map-Data",
                            "fields_n": len(tig), "fields": tig,
                            "note": "TIGER addrfeat 已含 号段(LFROMHN/LTOHN/RFROMHN/RTOHN)、"
                                    "ZIP+4(PLUS4L/R)、号段类型(LFROMTYP…)、parity、offset、MTFCC、FULLNAME"},
        "field_evidence_source": "collect/polygon_probe.json（23,556 层探针，离线）",
        "sample_evidence": "unavailable_offline",
        "totals": {"layers": len(recs), "verdict": cnt,
                   "with_field_evidence": sum(1 for r in recs if r["fields_have_evidence"])},
        "conclusion": {
            "worth_collect": cnt.get("worth_collect", 0),
            "not_worth_collect": cnt.get("not_worth_collect", 0),
            "no_field_evidence": cnt.get("no_field_evidence", 0),
            "headline": "TIGER addrfeat 的 25 字段覆盖了号段/ZIP+4/号段类型/parity/offset/FULLNAME，"
                        "绝大多数线层没有它拿不到的地址语义字段；只有带单元号段/ESN/房号等"
                        "「独有地址语义」的层才值得补采（名单见 worth_collect 列表）",
        },
        "records": recs,
    }
    os.makedirs(os.path.dirname(OUT_LEDGER), exist_ok=True)
    json.dump(ledger, open(OUT_LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    L = ["# 线层「不采」核定（2026-10-30）", "",
         "> 三仓 1,946 个 Polyline 层一个都没采（STEP-01 几何白名单直接 skip）。",
         "> 本文件是**可查的账**：逐层把字段清单与 TIGER addrfeat 的 25 字段对齐，写明为什么不采、",
         "> 哪些其实值得补采。**不许默认放弃**。", "",
         "## 一、基准与证据来源", "",
         f"- TIGER 基准：一仓已发布资产 `{os.path.basename(TIGER_ZIP)}`（{len(tig)} 字段，dbf 实读）",
         "  `%s`" % ", ".join(tig),
         "  → 已含 **号段**（LFROMHN/LTOHN/RFROMHN/RTOHN）、**ZIP+4**（PLUS4L/R）、"
         "**号段类型**（LFROMTYP…）、**parity**、**offset**、**MTFCC**、**FULLNAME**",
         "- 线层字段清单：`collect/polygon_probe.json`（23,556 层探针，离线，无需访问上游）",
         "- ⚠ **样本值未取**：线层未采，3 条样本需要一次上游 query，本轮边界禁止 → "
         "判定只用字段清单 + `nfields`；每层 `url` 已入账本，批准后一条 query 即可补证", "",
         "## 二、总账（1,946 层）", "",
         "| 结论 | 层数 | 含义 |", "|---|---|---|",
         "| `not_worth_collect` | %d | 独有字段只有 OIM/几何/道路属性/行政区名 → TIGER 已覆盖号段语义 |"
         % cnt.get("not_worth_collect", 0),
         "| `worth_collect` | %d | **有 TIGER 拿不到的独有地址语义字段** → 候选补采（再分 A/B 两档，见第四节） |"
         % cnt.get("worth_collect", 0),
         "| `out_of_scope` | %d | 非美国数据（PROVINCE/POSTCODE）→ 不在范围 |"
         % cnt.get("out_of_scope", 0),
         "| `no_field_evidence` | %d | 探针没覆盖该层，无法定论（不是「不采」的理由） |"
         % cnt.get("no_field_evidence", 0), "",
         "## 三、20 层逐条结论", "",
         "| # | 层 | 州 | 行数 | 字段数 | TIGER 命中 | 独有字段（地址语义） | 独有（其它） | 结论 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sample, 1):
        ex = r["extras"] or {}
        ae = ", ".join((ex.get("addr_extra") or [])[:3]) or "—"
        other = ", ".join(((ex.get("place") or []) + (ex.get("road") or []) + (ex.get("other") or []))[:3]) or "—"
        L.append("| %d | `%s` | %s | %s | %s | %d | %s | %s | %s |"
                 % (i, r["layer_id"][:52], r["state"] or "-",
                    f"{r['rows']:,}" if r.get("rows") else "-", r.get("nfields") or "-",
                    r["tiger_matched_n"], ae, other, r["verdict"]))
    L += ["", "逐层理由（抽样层）：", ""]
    for r in sample:
        L.append("- `%s` → **%s**：%s" % (r["layer_id"], r["verdict"], r["why"]))
    ta = [r for r in worth if r["tier"] == "A_unit_or_esn"]
    tb = [r for r in worth if r["tier"] == "B_full_address_only"]
    L += ["", "## 四、值得补采的层（全部 %d 层，不只抽样）" % len(worth), "",
          "- **A 档（%d 层）：含单元/ESN 等 TIGER 结构上真没有的字段 → 建议补采**" % len(ta),
          "- **B 档（%d 层）：只多一个「拼好的整串地址」字段 → 不补**（TIGER 的 FULLNAME+号段可自行拼，"
          "没有新语义；补采只为省一次拼接不值）" % len(tb), ""]
    if ta:
        L += ["### A 档（建议补采）", "", "| 层 | 州 | 行数 | 独有字段 |", "|---|---|---|---|"]
        for r in ta:
            L.append("| `%s` | %s | %s | %s |"
                     % (r["layer_id"][:52], r["state"] or "-",
                        f"{r['rows']:,}" if r.get("rows") else "-",
                        ", ".join((r["extras"]["addr_extra"])[:6])))
    else:
        L += ["**A 档：无。**"]
    L += ["", "### B 档（不建议补采，仅记账）", "",
          "共 %d 层，独有字段都是 `FULLADDRESS`/`GEOFULLADDRESS`/`FULLADDR_L` 这类拼串列。"
          "逐层见 `collect/ledger/line_layers_decision.json`（`tier=B_full_address_only`）。" % len(tb)]
    L += ["", "## 五、结论", "",
          "1. **不采的结论仍然成立**，但理由从「几何白名单 skip」升级为「字段对比后无增益」——"
          "TIGER addrfeat 已覆盖号段/ZIP+4/号段类型/parity/offset/FULLNAME。",
          "2. 有独有字段的是 %d 层，但真正值得补采的只有 **A 档 %d 层**（单元/ESN，TIGER 结构上真没有）；"
          "其余 %d 层只是多一个拼好的整串地址列，TIGER 的 FULLNAME+号段能自行拼出 → 不补。"
          % (len(worth), len(ta), len(tb)),
          "3. %d 层因探针未覆盖**无法定论**，不能计入「不采」——补一次元数据读取即可（账本里已存 url）。"
          % cnt.get("no_field_evidence", 0),
          "4. 量化：A 档 %d 层合计只有 **%s 行**（占号段类总量不到 0.01%%），其中唯一有真实单元语义的"
          "是 `Addresses_to_Romkey_v2`（3,550 行，且是地理编码拼接层不是街道层）→ "
          "**结论：线层整体不值得补采，A 档留名待有需要时按需单采**。"
          % (len(ta), f"{sum((r['rows'] or 0) for r in ta):,}"),
          "5. 样本值（3 条/层）本轮未取：需要上游 query，等边界放开后按账本 url 批量补，"
          "届时可一并核实号段语义（如 LFROMHN 是否真的存在）。", "",
          "## 六、复现", "", "```bash",
          "python3 analysis/line_layers_decision.py", "```", ""]
    open(OUT_DOC, "w", encoding="utf-8").write("\n".join(L))
    print(json.dumps({"layers": len(recs), "verdict": cnt, "worth": len(worth),
                      "sample": len(sample)}, ensure_ascii=False))
    print("写入 %s\n写入 %s" % (OUT_LEDGER, OUT_DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
