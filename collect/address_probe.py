#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""点类地址层「逐层摸排」：对每个候选层只抽 300 行，算实测有效率并定级。

为什么不能用声明行数：实测过 219 层抽样，avg_eff 只有 7.44%，还有 169 层声明 1.07 亿行
实测 0 行 —— 声明值对本仓筛选毫无预测力。也不能用 bbox 判据（bbox 会把邻县/邻州地址
算进本层，系统性假阳性，见 step04 gap 报告）。所以判据只有一条：**真拉 300 行，看有多少行
能拼出地址**（`lib.schema.normalize` 的 addr_key，或强地址字段里带门牌数字）。

定级（用于批次筛选与 reject 剔除）：
  strong  eff >= 20%                      —— 高产出，优先采
  weak    0 < eff < 20%                   —— 采了有用但性价比低，排在 strong 之后
  reject  eff == 0 / 取不到数据           —— 不采，只记账
另：声明 0 行的层直接记 reject_zero（按全量分母口径「跳过并记账」）。

用法：
  python3 collect/address_probe.py --shard 0 --shards 42 --size 120 \
      --out collect/ledger/addrprobe_00.csv
  python3 collect/address_probe.py --merge            # 合成 collect/address_layers.csv
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lib.fetch import get_json                      # noqa: E402
from lib.schema import normalize                    # noqa: E402

PLAN_F = os.path.join(HERE, "layer_plan.csv")
OUT_CSV = os.path.join(HERE, "address_layers.csv")
CAP = 300
TITLE_RX = re.compile(r"address|addr|situs|911|mailing", re.I)
GEOM_OK = {"point", "multipoint", "socrata"}
STRONG_FIELDS = ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "ADDR",
                 "SITE_ADDRESS", "SITUS_ADDR", "LOCATION", "PREMISE_ADDR", "ADDR_FULL")


def api_of(url: str) -> str:
    u = url.split("?")[0].rstrip("/")
    if not re.search(r"/(FeatureServer|MapServer)(/\d+)?$", u):
        return u
    if not re.search(r"/\d+$", u):
        u += "/0"
    return u


def candidates(dedup: bool = True) -> list[dict]:
    rows = list(csv.DictReader(open(PLAN_F, encoding="utf-8")))
    out, seen = [], set()
    for r in rows:
        if (r.get("geom") or "").lower() not in GEOM_OK:
            continue
        if not TITLE_RX.search(r.get("title") or ""):
            continue
        if not r.get("url"):
            continue
        if dedup:
            k = r["url"]
            if k in seen:
                continue
            seen.add(k)
        out.append(r)
    return out


def probe(r: dict) -> dict:
    lid = r.get("layer_id") or ""
    declared = int(r.get("row_count") or 0)
    st = {"layer_id": lid, "state": r.get("state") or "", "geom": r.get("geom") or "",
          "rows": declared, "grade": "", "eff": 0.0, "fields_hit": "", "url": r.get("url") or "",
          "fetched": 0, "valid": 0, "err": ""}
    if declared == 0:
        st["grade"] = "reject_zero"
        st["err"] = "声明 0 行"
        return st
    try:
        api = api_of(st["url"])
        meta = get_json(api + "?f=json", timeout=25)
        if "__error__" in meta:
            st.update(grade="reject", err="meta:%s" % str(meta["__error__"])[:60])
            return st
        oid = meta.get("objectIdField") or meta.get("objectIdFieldName")
        fns = [f.get("name") for f in (meta.get("fields") or [])]
        if not oid:
            oid = next((k for k in ("OBJECTID", "OBJECTID_1", "FID", "OID") if k in fns), "OBJECTID")
        hit = [f for f in fns if str(f).upper() in STRONG_FIELDS]
        ps = min(int(meta.get("maxRecordCount") or 1000), CAP)
        q = {"where": meta.get("definitionExpression") or "1=1", "outFields": "*",
             "returnGeometry": "false", "f": "json", "resultRecordCount": ps,
             "orderByFields": oid}
        d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=90)
        if "__error__" in d:
            q.pop("orderByFields")
            d = get_json(api + "/query?" + urllib.parse.urlencode(q), timeout=90)
            if "__error__" in d:
                st.update(grade="reject", err="query:%s" % str(d["__error__"])[:60])
                return st
        for ft in (d.get("features") or [])[:CAP]:
            a = ft.get("attributes") or {}
            rec = normalize(a, None, None)
            st["fetched"] += 1
            if rec.get("addr_key"):
                st["valid"] += 1
            else:
                for f in STRONG_FIELDS:
                    v = a.get(f)
                    if v and re.search(r"\d", str(v)):
                        st["valid"] += 1
                        break
        eff = st["valid"] * 100.0 / st["fetched"] if st["fetched"] else 0.0
        st["eff"] = round(eff, 2)
        st["fields_hit"] = ";".join(hit[:6])
        if eff >= 20:
            st["grade"] = "strong"
        elif eff > 0:
            st["grade"] = "weak"
        else:
            st["grade"] = "reject"
            st["err"] = st["err"] or "抽样 %d 行全部拼不出地址" % st["fetched"]
    except Exception as e:  # noqa: BLE001
        st.update(grade="reject", err="%s:%s" % (type(e).__name__, str(e)[:60]))
    return st


FIELDS = ["layer_id", "state", "geom", "rows", "grade", "eff", "fields_hit", "url",
          "fetched", "valid", "err"]


def merge() -> int:
    rows = []
    for f in sorted(glob.glob(os.path.join(HERE, "ledger", "addrprobe_*.csv"))):
        with open(f, encoding="utf-8") as fh:
            rows += list(csv.DictReader(fh))
    by = {r["layer_id"]: r for r in rows}
    out = sorted(by.values(), key=lambda r: -int(r.get("rows") or 0))
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    cnt = {}
    for r in out:
        cnt[r["grade"]] = cnt.get(r["grade"], 0) + 1
    ok = [r for r in out if int(r.get("fetched") or 0) > 0]
    fet = sum(int(r["fetched"]) for r in ok)
    val = sum(int(r["valid"]) for r in ok)
    # 收官文档（摸排结论，供批次筛选用）
    ok2 = [r for r in out if int(r.get("fetched") or 0) > 0]
    doc = os.path.join(ROOT, "docs", "ADDRESS-LAYERS-PROBE-2026-10-30.md")
    os.makedirs(os.path.dirname(doc), exist_ok=True)
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write("# 点类地址层逐层摸排（4,986 层口径，实测抽样）\n\n")
        fh.write("判据：每层真拉 300 行，按 `lib.schema.normalize` 的 addr_key / 强地址字段含数字判有效。"
                 "**不用 bbox**（bbox 会把邻州地址算进本层）。\n\n")
        fh.write("| 指标 | 值 |\n|---|---|\n")
        fh.write("| 候选层（geom=Point/Multipoint/Socrata 且标题命中 address\\|addr\\|situs\\|911\\|mailing，按 url 去重） | %d |\n" % len(out))
        for k in ("strong", "weak", "reject", "reject_zero"):
            fh.write("| %s | %d 层 |\n" % (k, cnt.get(k, 0)))
        fh.write("| 实测 avg_eff | %.2f%% |\n" % (val * 100.0 / max(1, fet)))
        fh.write("| 抽样行合计 | %d（有效 %d） |\n" % (fet, val))
        fh.write("\n## 定级规则\n\n- strong：eff >= 20%%（优先采）\n- weak：0 < eff < 20%%\n"
                 "- reject：抽样 0 有效或取不到数据（不采，只记账）\n- reject_zero：上游声明 0 行\n\n")
        fh.write("逐层明细见 `collect/address_layers.csv`。\n")
    print("写入 %s" % doc)
    print(json.dumps({"layers": len(out), "grades": cnt,
                      "avg_eff_pct": round(val * 100.0 / max(1, fet), 2),
                      "fetched": fet, "valid": val,
                      "declared_of_strong": sum(int(r["rows"]) for r in out
                                                if r["grade"] == "strong")},
                     ensure_ascii=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--size", type=int, default=120)
    ap.add_argument("--threads", type=int, default=10)
    ap.add_argument("--out", default="")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        return merge()
    cand = candidates()
    lo = a.shard * a.size
    hi = min(len(cand), lo + a.size) if a.shards > 1 else len(cand)
    mine = cand[lo:hi]
    print("[probe] 候选 %d 层，本片 %d 层（%d..%d）" % (len(cand), len(mine), lo, hi), flush=True)
    out = a.out or os.path.join(HERE, "ledger", "addrprobe_%02d.csv" % a.shard)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    res = []
    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        for i, st in enumerate(ex.map(probe, mine), 1):
            res.append(st)
            if i % 25 == 0:
                print("  %d/%d" % (i, len(mine)), flush=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(res)
    cnt = {}
    for r in res:
        cnt[r["grade"]] = cnt.get(r["grade"], 0) + 1
    print("[probe] 片 %d 完成：%s → %s" % (a.shard, cnt, out), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
