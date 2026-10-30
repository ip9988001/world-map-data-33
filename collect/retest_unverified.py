#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04b · `unverified` 层的跨时段重测（只读上游，不采数据）。

为什么单独一个脚本：`unverified` 是「上游不可达/403」的唯一合法去向 ——
既不许当 `empty`（那等于宣称「上游没数据」），也不许进 `failed`（那等于宣称「我们采挂了」）。
判据必须是**跨时段重复观测**，一次超时只能算一次噪声：

  · 每轮对每层打一次 `returnCountOnly`，记 HTTP 码 + 原始响应体 + 错误类型；
  · 轮次间隔 >= 30 分钟（脚本自己拦：间隔不够就拒绝追加，避免「三次同秒」假装重测）；
  · 3 轮全不可达 → 账本保持 `unverified`，文档写「上游不可达，未验证，非空层」；
  · 任一轮可达 → 变 `alive`，按上游行数重判（有数但本层 0 行 = missing，必须重采）。

这 6 层的声明值**不进分母**（分母只算能验证的层），但单列「不确定行数区间」：
  low  = 0
  high = 声明值之和（声明值本身来自 layer_plan.csv，未经上游确认，只能当上界）

用法（每次只追加一轮，天然满足「间隔 >= 30 分钟」）：
  python3 collect/retest_unverified.py --append            # 追加第 N 轮
  python3 collect/retest_unverified.py --status            # 只看现状
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(HERE, "04b_ledger.json")
PLAN_CSV = os.path.join(HERE, "layer_plan_clean.csv")
OUT_DIR = os.path.join(ROOT, "analysis")
GAP_MIN = 30
UA = {"User-Agent": "collect-audit/1.0 (+world-map-data-33)"}


def out_path(date=None):
    date = date or time.strftime("%Y-%m-%d", time.gmtime())
    return os.path.join(OUT_DIR, "unverified-04b-%s.json" % date)


def layer_urls():
    idx = {}
    with open(PLAN_CSV, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            lid = r.get("layer_id") or ""
            if lid and r.get("url"):
                idx[lid] = r["url"]
    return idx


def targets():
    led = json.load(open(LEDGER, encoding="utf-8"))
    recs = led.get("records") or led.get("layers") or []
    return [r for r in recs if r.get("status") == "unverified"]


def probe(url, timeout=25):
    """一次只读探测。返回 dict(http, count, raw, err, elapsed_ms)。"""
    q = url.rstrip("/") + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    t0 = time.time()
    rec = {"url": q, "http": None, "count": None, "raw": "", "err": ""}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(q, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read(4000).decode("utf-8", "replace")
            rec.update(http=resp.status, raw=body[:400])
            try:
                j = json.loads(body)
                if isinstance(j, dict) and "count" in j:
                    rec["count"] = int(j["count"])
                elif isinstance(j, dict) and j.get("error"):
                    rec["err"] = "esri_error: %s" % str(j["error"])[:200]
            except Exception:                          # noqa: BLE001
                rec["err"] = "非 JSON 响应"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read(400).decode("utf-8", "replace")
        except Exception:                              # noqa: BLE001
            pass
        rec.update(http=e.code, raw=body[:400], err="HTTP %d" % e.code)
    except Exception as e:                             # noqa: BLE001
        rec["err"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    rec["elapsed_ms"] = int((time.time() - t0) * 1000)
    return rec


def load(path):
    if not os.path.exists(path):
        return {"schema": "unverified-retest/v1", "stage": "04b", "gap_min": GAP_MIN,
                "rule": "3 轮全不可达 → 保持 unverified（非空层）；任一轮可达 → 按上游行数重判；"
                        "声明值不计入分母，单列不确定区间 [0, 声明值之和]",
                "rounds": []}
    return json.load(open(path, encoding="utf-8"))


def summarize(doc):
    """按层汇总：几轮不可达 / 是否出现可达。"""
    per = {}
    for rd in doc["rounds"]:
        for l in rd["layers"]:
            d = per.setdefault(l["layer"], {"rounds": 0, "unreachable": 0, "alive": 0,
                                            "counts": [], "http": [], "errs": []})
            d["rounds"] += 1
            d["http"].append(l["probe"].get("http"))
            if l["probe"].get("count") is not None:
                d["alive"] += 1
                d["counts"].append(l["probe"]["count"])
            else:
                d["unreachable"] += 1
                d["errs"].append((l["probe"].get("err") or "")[:60])
    for lid, d in per.items():
        d["verdict"] = ("upstream_alive_after_retest" if d["alive"]
                        else ("unreachable_all_rounds" if d["rounds"] >= 3 else "pending_rounds"))
    return per


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--append", action="store_true", help="追加一轮重测")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--force", action="store_true", help="无视 30 分钟间隔（仅调试；不留作证据）")
    ap.add_argument("--timeout", type=int, default=25)
    a = ap.parse_args()
    path = out_path()
    doc = load(path)

    if a.status or not a.append:
        per = summarize(doc)
        print("轮次：%d（%s）" % (len(doc["rounds"]),
                               ", ".join(r["at"] for r in doc["rounds"]) or "-"))
        for lid, d in sorted(per.items()):
            print("%-14s rounds=%d alive=%d counts=%s http=%s"
                  % (d["verdict"], d["rounds"], d["alive"], d["counts"][:3], d["http"][:3]))
        if not per:
            print("（还没有轮次）")
        return 0

    now = time.time()
    if doc["rounds"] and not a.force:
        last = doc["rounds"][-1].get("at_epoch") or 0
        gap = (now - last) / 60.0
        if gap < GAP_MIN:
            print("拒绝追加：距上一轮只有 %.1f 分钟（要求 >= %d 分钟）" % (gap, GAP_MIN))
            return 3

    urls = layer_urls()
    tg = targets()
    if not tg:
        print("账本里没有 unverified 层（可能已重判），无事可做")
        return 0
    rd = {"round": len(doc["rounds"]) + 1,
          "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "at_epoch": int(now),
          "layers": []}
    for r in tg:
        lid = r["layer"]
        url = urls.get(lid) or urls.get(lid.split("@")[0]) or ""
        rec = {"layer": lid, "ledger_declared": r.get("declared"), "layer_url": url}
        rec["probe"] = probe(url, a.timeout) if url else \
            {"err": "layer_plan_clean.csv 里查不到 url", "http": None, "count": None}
        rec["state"] = ("alive" if rec["probe"].get("count") is not None else "unreachable")
        rd["layers"].append(rec)
        p = rec["probe"]
        print("轮%d %-12s http=%-4s count=%-10s %s"
              % (rd["round"], rec["state"], p.get("http"), p.get("count"), lid[:52]))
    doc["rounds"].append(rd)
    doc["summary"] = summarize(doc)
    doc["uncertain_rows"] = {
        "low": 0,
        # 声明值取自 layer_plan.csv（未经上游确认），只当上界；不能当已采行数用
        "high": sum(int(x.get("declared") or 0) for x in tg),
        "note": "声明值未经上游确认，只当上界；这几层不计入缺口分母",
    }
    doc["updated_at"] = rd["at"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("追加轮 %d → %s" % (rd["round"], path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
