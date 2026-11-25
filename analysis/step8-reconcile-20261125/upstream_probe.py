#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 8 步 · B：54 层「上游无资产」逐层原因表 + C：3 层「账本 ok 却本地零资产」。

只读：`analysis/full-inventory-20261124/local-vs-ledger-reconcile.csv`（账本冻结口径）
     + 每层 URL 只探一次（`?f=json` 与 `returnCountOnly=true`），不下载、不落数据、不改账本。

结论分类（四选一，判定顺序写死）：
  upstream_empty     上游层还在、count=0（或 features=[] 且 count=0）→ 整层本来就空
  upstream_offline   连接失败 / 5xx / 403 / "Invalid URL" / 层不存在（?f=json 报 error）→ 上游现在不可达
  id_drifted         URL 的 layer id 段与当前服务层号不符，或服务指向了另一个数据集（?f=json 的 name 与账本 title 明显不符）
  ledger_overclaimed 上游 count 或 ?f=json 正常但账本 declared 明显大于实测（账本虚记）

用法：python3 analysis/step8-reconcile-20261125/upstream_probe.py
"""
from __future__ import annotations

import csv
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
OUT = HERE
UA = {"User-Agent": "wmd33-step8-reconcile/1.0"}
TIMEOUT = 25


def get(url):
    """返回 (http_code, body_text_or_empty, err_text)。只探一次，绝不重试到死循环。"""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(2_000_000).decode("utf-8", "replace")
            return r.status, body, ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read(4000).decode("utf-8", "replace")
        except Exception:                                        # noqa: BLE001
            body = ""
        return e.code, body, f"HTTPError {e.code}"
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
        return 0, "", f"{type(e).__name__}: {str(e)[:160]}"


def probe(url):
    """一次 ?f=json + 一次 returnCountOnly。返回实测 dict。"""
    u = (url or "").strip().rstrip("/")
    if not u.startswith("http"):
        return {"http_meta": None, "meta_err": "CSV 里该层 url 为空（未定位层无 URL）", "layer_name": "",
                "geom": "", "http_count": None, "count": None, "count_err": ""}
    res = {"http_meta": None, "meta_err": "", "layer_name": "", "geom": "",
           "http_count": None, "count": None, "count_err": ""}
    code, body, err = get(u + "?f=json")
    res["http_meta"], res["meta_err"] = code, err
    if body:
        try:
            doc = json.loads(body)
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            if "error" in doc:
                res["meta_err"] = (res["meta_err"] + " | " if res["meta_err"] else "") + \
                    "esri_error: " + json.dumps(doc.get("error"), ensure_ascii=False)[:200]
            res["layer_name"] = str(doc.get("name") or "")[:120]
            res["geom"] = str(doc.get("geometryType") or "")[:40]
    if code == 200 and not res["meta_err"]:
        code2, body2, err2 = get(u + "/query?where=1%3D1&returnCountOnly=true&f=json")
        res["http_count"], res["count_err"] = code2, err2
        if body2:
            try:
                doc = json.loads(body2)
                if "count" in doc:
                    res["count"] = int(doc["count"])
                elif "error" in doc:
                    res["count_err"] = "esri_error: " + json.dumps(doc["error"], ensure_ascii=False)[:200]
            except ValueError:
                res["count_err"] = "bad_json"
    return res


def classify(row, p):
    dec = row["ledger_declared"] or ""
    try:
        dec_n = int(float(dec)) if dec.strip() not in ("", "None") else None
    except ValueError:
        dec_n = None
    if p["http_meta"] == 200 and p["count"] == 0:
        return "upstream_empty", "上游层可达、returnCountOnly=0 → 整层本来就空"
    if p["http_meta"] == 200 and p["count"] and dec_n and p["count"] != dec_n:
        # 上游有数、账本也有数的差额：判虚记 vs 上游变化，用 5% 容差
        if dec_n > p["count"] * 1.05:
            return "ledger_overclaimed", f"上游 count={p['count']} 明显小于账本 declared={dec_n} → 账本虚记"
        return "id_drifted", f"上游 count={p['count']} 与账本 declared={dec_n} 不符（差<5% 或反向）→ 同一层两次快照不一致"
    if p["http_meta"] == 200 and p["count"] is not None:
        return "ledger_overclaimed", f"上游 count={p['count']} 正常但账本 declared={dec_n} 与本地 0 资产不符"
    if p["http_meta"] and p["http_meta"] != 200:
        return "upstream_offline", f"上游返回 HTTP {p['http_meta']}（{p['meta_err'][:80]}）"
    if p["meta_err"]:
        return "upstream_offline", f"上游不可达：{p['meta_err'][:100]}"
    return "upstream_offline", "探针未取得可用响应（无 count、无 ?f=json 内容）"


SUGGEST = {
    "upstream_empty": "不补采：上游整层为空，补采也只能拿到 0 行；从可采清单标注 empty_shell，下一轮复核是否复播",
    "upstream_offline": "不补采：抓取失败（站点/网关/权限），保留在待重试清单；先解网关与 DNS，不要重复派单",
    "id_drifted": "待复核：同一 URL 的层号/服务内容与采集期不一致，重新取 ?f=json 定位新层号后单独补采",
    "ledger_overclaimed": "待复核账本：上游可采但账本声明的行数取不到，按上游实测重写 declared 前先人工确认",
}


def main():
    rows = [r for r in csv.DictReader(open(INV, encoding="utf-8"))
            if r["reconcile_class"] == "local_absent_upstream_no_assets"]
    out, t0 = [], time.time()
    for i, r in enumerate(rows, 1):
        p = probe(r["url"])
        cls, why = classify(r, p)
        out.append({
            "layer": r["layer"], "stage": r["stage"],
            "ledger_declared": r["ledger_declared"], "ledger_rows": r["ledger_rows"],
            "ledger_status": r["status"], "url": r["url"],
            "upstream_http_meta": p["http_meta"], "upstream_http_count": p["http_count"],
            "upstream_count": "" if p["count"] is None else p["count"],
            "upstream_layer_name": p["layer_name"], "upstream_geom": p["geom"],
            "upstream_err_raw": (p["meta_err"] or p["count_err"])[:220],
            "conclusion": cls, "conclusion_reason": why, "suggestion": SUGGEST[cls]})
        print(f"[{i}/{len(rows)}] {r['layer'][:48]:48s} http={p['http_meta']} count={p['count']} -> {cls}",
              flush=True)
    with open(os.path.join(OUT, "upstream-no-assets.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)

    # —— C：账本 ok 却本地零资产（本表 54 层的子集；另把 3,550 里的同名条件也扫一遍）——
    all_rows = list(csv.DictReader(open(INV, encoding="utf-8")))
    # 「账本 ok 却本地零资产」：status=ok + 本地 0 字节 + **Release 也没有载荷**（payload_n=0）。
    # 不加最后一条会把 3,550 层（有载荷、只是没下）全扫进来 —— 那是 A 的事，不是这一类。
    zero = [r for r in all_rows
            if (r["status"] or "").strip().lower() == "ok"
            and (r["ledger_declared"] or "").strip() not in ("", "None", "0")
            and int(r["local_bytes"] or 0) == 0
            and int(r["release_payload_n"] or 0) == 0]
    cls_of = {r["layer"]: r["reconcile_class"] for r in all_rows}
    conc = {r["layer"]: r["conclusion"] for r in out}
    with open(os.path.join(OUT, "zero-asset-3.csv"), "w", newline="", encoding="utf-8") as fh:
        cols = ["layer", "stage", "ledger_declared", "ledger_rows", "ledger_status", "local_bytes",
                "reconcile_class_v1", "in_3550", "in_54", "upstream_conclusion", "note"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in zero:
            in54 = r["reconcile_class"] == "local_absent_upstream_no_assets"
            w.writerow({"layer": r["layer"], "stage": r["stage"], "ledger_declared": r["ledger_declared"],
                        "ledger_rows": r["ledger_rows"], "ledger_status": r["status"],
                        "local_bytes": r["local_bytes"], "reconcile_class_v1": r["reconcile_class"],
                        "in_3550": r["reconcile_class"] == "local_absent_assets_exist_not_downloaded",
                        "in_54": in54, "upstream_conclusion": conc.get(r["layer"], ""),
                        "note": ("账本 ok 与上游无资产冲突：属 54 层（并入 B 原因表）" if in54
                                 else "属 3,550 类（A 拉起后自然归零）")})
    print(json.dumps({"probed": len(out), "buckets": {k: sum(1 for x in out if x["conclusion"] == k)
                                                      for k in SUGGEST},
                      "zero_asset_ok_layers": [z["layer"] for z in zero],
                      "zero_asset_all_in_54": all(z["reconcile_class"] == "local_absent_upstream_no_assets"
                                                  for z in zero),
                      "secs": round(time.time() - t0, 1)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
