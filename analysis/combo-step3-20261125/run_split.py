#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合拳③：P1 切分 / P3 城市黏尾 / P8 区间 / P10 交叉核 的逐层实测（全本地，不联网）。

数据可得性（本单第一步就要说清）：这批层在本地 dist 快照基本是空表，本轮只用两路真实值——
  · analysis/coord-samples-20261124/samples/*.csv（管线当时抽的坐标样本，含 addr_fields_json 真实值）
  · survey/ng911/samples.csv.gz（每层 3 条原始记录，兜底）
所以所有行级数字都是「采样实测」，**不是 rows_n 全量**。覆盖率逐层落 p1-coverage.csv。

产物（analysis/combo-step3-20261125/ 根下）：
  p1-split-perlayer.csv  431 层逐层：实测行/成功/失败/成功率/主因
  p1-failures.csv        P1 行级失败清单（url/layer_id/field/原始值/reason）
  p1-coverage.csv        覆盖率：可及行数 vs rows_n + 层级（全量/采样/零样本）
  p3-citytail.csv        53 层逐层：可切/不可切行数、置信度分布、失败样例
  p8-layers.csv          22 层区间列清单（给 p8-decision.md 用）
  p10-crosscheck.csv     字段数少的 P10 层 vs inventory-remote-uncollected.csv 的 n_fields
  _work/summary.json     汇总断言值
"""
from __future__ import annotations

import collections
import csv
import glob
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from engine.split_addr import split_city_tail, split_number_street  # noqa: E402

PATTERNS = os.path.join(ROOT, "analysis", "combo-step1-20261125", "patterns.csv")
SAMPLES = os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
NG911 = os.path.join(ROOT, "survey", "ng911", "samples.csv.gz")
REMOTE = os.path.join(ROOT, "analysis", "full-inventory-20261124", "inventory-remote-uncollected.csv")
WORK = os.path.join(HERE, "_work")


def load_patterns():
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(PATTERNS, encoding="utf-8")):
        by[r["pattern_id"]].append(r)
    return by


def load_rows(urls):
    """只取目标层的真实样本行：url → [addr_fields_json dict, ...]"""
    rows = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            u = r.get("layer_url") or ""
            if u not in urls:
                continue
            try:
                af = json.loads(r.get("addr_fields_json") or "{}")
            except Exception:
                continue
            af = {k: sv for k, sv in ((k, str(v).strip()) for k, v in af.items())
                  if sv and sv.lower() not in ("null", "none")}
            if af:
                rows[u].append(af)
    # 兜底：没有坐标样本行的层，用 ng911 的 3 条原始记录
    need = {u for u in urls if not rows.get(u)}
    if need:
        with gzip.open(NG911, "rt", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                u = r.get("url") or ""
                if u not in need:
                    continue
                try:
                    smp = json.loads(r.get("samples") or "[]")[:3]
                except Exception:
                    smp = []
                for s in smp:
                    af = {k: str(v).strip() for k, v in (s or {}).items() if v not in (None, "", "null")}
                    if af:
                        rows[u].append(af)
    return rows


def pick_field(layer, rows):
    """该层的「组合串」字段：优先 patterns.csv 里点名的字段，其次按值命中率挑。"""
    cand = [f.strip() for f in (layer.get("fields") or "").split("|") if f.strip()]
    present = collections.Counter()
    for r in rows:
        for k in r:
            present[k] += 1
    for f in cand:
        if present.get(f):
            return f, "patterns.csv"
    best = None
    for k, n in present.most_common():
        hit = sum(1 for r in rows if r.get(k) and split_number_street(r[k])["reason"] in ("ok", "ambiguous"))
        if hit / max(1, n) >= 0.3:
            best = k
            break
    return (best or (cand[0] if cand else "")), ("值命中率" if best else "缺失")


def main():
    os.makedirs(WORK, exist_ok=True)
    by = load_patterns()
    p1, p3, p8, p10 = by["P1"], by["P3"], by["P8"], by["P10"]
    urls = {r["url"] for r in p1 + p3 + p8 + p10}
    rows = load_rows(urls)

    # ---------------- P1 ----------------
    per, fails, cov = [], [], []
    for r in p1:
        u = r["url"]
        rr = rows.get(u) or []
        field, src = pick_field(r, rr)
        ok = fail = 0
        reasons = collections.Counter()
        for af in rr:
            v = af.get(field)
            if v is None:                     # 该行没有这一列
                reasons["field_absent"] += 1
                fail += 1
                continue
            res = split_number_street(v)
            if res["reason"] == "ok":
                ok += 1
            else:
                fail += 1
                reasons[res["reason"]] += 1
                fails.append({"layer_id": r["layer_id"], "url": u, "field": field,
                              "raw_value": v[:120], "reason": res["reason"]})
        n = len(rr)
        present = sum(1 for af in rr if af.get(field) is not None)
        per.append({"layer_id": r["layer_id"], "url": u, "state": r["state"], "field": field,
                    "field_source": src, "rows_n": r["rows_n"], "sample_rows": n,
                    "field_present_rows": present, "split_ok": ok, "split_fail": fail,
                    "success_rate": round(ok / present, 4) if present else 0.0,
                    "evaluable": "yes" if present else "no(该列不在样本行里)",
                    "top_reason": reasons.most_common(1)[0][0] if reasons else ""})
        rows_n = int(r["rows_n"])
        cov.append({"layer_id": r["layer_id"], "url": u, "rows_n": rows_n, "available_rows": n,
                    "coverage_pct": round(100.0 * n / rows_n, 4) if rows_n else 0.0,
                    "kind": ("零样本" if n == 0 else ("全量" if n >= rows_n else "采样")),
                    "value_source": "coord-samples" if n else "ng911-3rows/无"})

    def dump(name, data):
        with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(data[0]), extrasaction="ignore")
            w.writeheader()
            w.writerows(data)

    dump("p1-split-perlayer.csv", per)
    dump("p1-failures.csv", fails)
    dump("p1-coverage.csv", cov)

    # ---------------- P3 ----------------
    p3out = []
    for r in p3:
        u = r["url"]
        rr = rows.get(u) or []
        field, src = pick_field(r, rr)
        ok = fail = 0
        reasons, confs, samples = collections.Counter(), collections.Counter(), []
        for af in rr:
            v = af.get(field)
            if v is None:
                reasons["field_absent"] += 1
                fail += 1
                continue
            res = split_city_tail(v)
            if res["reason"] == "ok":
                ok += 1
                confs[str(res["confidence"])] += 1
                if len(samples) < 2:
                    samples.append(f"{v[:70]} → {res['house_number']}|{res['street_name']}|{res['city']}|{res['state']}|{res['zip']}")
            else:
                fail += 1
                reasons[res["reason"]] += 1
        n = len(rr)
        p3out.append({"layer_id": r["layer_id"], "url": u, "state": r["state"], "field": field,
                      "rows_n": r["rows_n"], "sample_rows": n, "split_ok": ok, "split_fail": fail,
                      "success_rate": round(ok / n, 4) if n else 0.0,
                      "conf_0.9": confs.get("0.9", 0), "conf_0.6": confs.get("0.6", 0),
                      "top_reason": reasons.most_common(1)[0][0] if reasons else "",
                      "samples": " ; ".join(samples)})
    dump("p3-citytail.csv", p3out)

    # ---------------- P8 ----------------
    p8out = []
    for r in p8:
        u = r["url"]
        rr = rows.get(u) or []
        p8out.append({"layer_id": r["layer_id"], "url": u, "state": r["state"],
                      "fields": r["fields"], "rows_n": r["rows_n"], "sample_rows": len(rr),
                      "example_values": (r["example_values"] or "")[:200]})
    dump("p8-layers.csv", p8out)

    # ---------------- P10 字段数少的层 ----------------
    remote = {r["url"].rstrip("/"): r for r in csv.DictReader(open(REMOTE, encoding="utf-8"))}
    p10out = []
    for r in p10:
        nf = int(r["n_fields"] or 0)
        if nf > 3:
            continue
        rm = remote.get(r["url"].rstrip("/")) or {}
        rr = rows.get(r["url"]) or []
        vals = [v for af in rr for v in af.values() if v]
        p10out.append({"layer_id": r["layer_id"], "url": r["url"],
                       "n_fields_patterns": nf, "fields_patterns": r["fields"],
                       "n_fields_remote": rm.get("n_fields", ""), "remote_http_meta": rm.get("http_meta", ""),
                       "remote_sampled_n": rm.get("sampled_n", ""), "remote_addr_core_hit": rm.get("addr_core_hit", ""),
                       "remote_usable": rm.get("usable", ""), "sample_rows": len(rr),
                       "nonempty_values": len(vals),
                       "verdict": ("采集漏字段：远端 ?f=json 报 n_fields=%s，patterns 只看到 %s 个"
                                   % (rm.get("n_fields", "?"), nf)) if str(rm.get("n_fields", "")) not in ("", str(nf))
                                  else "字段数一致 → 数据本身没有地址列（应排除）"})
    dump("p10-crosscheck.csv", p10out)

    # ---------------- 汇总 ----------------
    evalable = [x for x in per if x["evaluable"] == "yes"]
    lvl_ok = sum(1 for x in evalable if x["success_rate"] >= 0.95)
    tot_ok = sum(x["split_ok"] for x in evalable)
    tot_rows = sum(x["field_present_rows"] for x in evalable)
    lvl_p3 = sum(1 for x in p3out if x["sample_rows"] and x["success_rate"] >= 0.95)
    tot_p3_ok = sum(x["split_ok"] for x in p3out)
    tot_p3_rows = sum(x["sample_rows"] for x in p3out)
    summary = {
        "p1": {"layers": len(per), "layers_evaluable": len(evalable),
               "layers_field_not_in_samples": len(per) - len(evalable),
               "layers_success_ge95": lvl_ok,
               "evaluated_rows": tot_rows, "split_ok_rows": tot_ok,
               "row_success_rate": round(tot_ok / tot_rows, 4) if tot_rows else 0.0,
               "rows_n_total": sum(int(x["rows_n"]) for x in per),
               "coverage_pct_of_rows_n": round(100.0 * tot_rows / sum(int(x["rows_n"]) for x in per), 4),
               "failure_buckets": dict(collections.Counter(f["reason"] for f in fails).most_common())},
        "p3": {"layers": len(p3out), "layers_success_ge95": lvl_p3,
               "sample_rows": tot_p3_rows, "split_ok_rows": tot_p3_ok,
               "row_success_rate": round(tot_p3_ok / tot_p3_rows, 4) if tot_p3_rows else 0.0,
               "rows_n_total": sum(int(x["rows_n"]) for x in p3out)},
        "p8": {"layers": len(p8out), "rows_n": sum(int(x["rows_n"]) for x in p8out)},
        "p10_lowfield_layers": len(p10out),
        "p10_verdicts": dict(collections.Counter(x["verdict"][:12] for x in p10out)),
    }
    json.dump(summary, open(os.path.join(WORK, "summary.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
