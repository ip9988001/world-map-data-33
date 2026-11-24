#!/usr/bin/env python3
"""Phase 1①：#9–#15 七个 upstream_unstable 层重探（每层 2 请求，只读）。

输入：analysis/calib-inventory-20261123/dirty-layer-urls.json（000201 还原的唯一 URL）
输出：analysis/full-inventory-20261124/dirty-layer-reprobe.json

每层：
  R1  <url>?f=json                                    meta（nfields/name/geometryType/maxRecordCount）
  R2  <url>/query?where=1=1&outFields=*&resultRecordCount=20&f=json   20 条样值
  （若 R2 报错或 meta 无 count 且需要行数 → 第 3 请求 returnCountOnly，计入 requests_n）
判定：upstream_still_unstable / recovered_with_count / address_fields_absent / empty_result
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "analysis", "full-inventory-20261124", "dirty-layer-reprobe.json")
SRC = os.path.join(REPO, "analysis", "calib-inventory-20261123", "dirty-layer-urls.json")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "pi-inventory/1.0", "Accept": "application/json"}
NUM = ("housenum", "addrnum", "addnum", "number", "num", "houseno", "situs", "bldg",
       "hsn", "stnum", "streetno", "street_no", "_no", "no_", "house")


def http(url, timeout=30):
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout,
                                    context=CTX) as r:
            body = r.read()
            return {"http": r.status, "json": _j(body), "ms": int((time.time() - t0) * 1000), "err": ""}
    except urllib.error.HTTPError as e:
        return {"http": e.code, "json": _j(e.read()[:2000]), "ms": int((time.time() - t0) * 1000),
                "err": f"HTTPError {e.code} {e.reason}"}
    except Exception as e:  # noqa: BLE001
        return {"http": 0, "json": None, "ms": int((time.time() - t0) * 1000),
                "err": f"{type(e).__name__}: {str(e)[:120]}"}


def _j(b):
    try:
        return json.loads(b)
    except Exception:  # noqa: BLE001
        return None


def blanks(v):
    return v in (None, "", " ", "  ") or (isinstance(v, list) and not v)


def num_candidates(attrs):
    """数据驱动找门牌字段：键名像门牌 + 值里真的出现数字。不看字段名凭印象拍。"""
    if not attrs:
        return {}
    keys = list(attrs[0])
    out = {}
    for k in keys:
        kl = k.lower()
        if not any(t in kl for t in NUM):
            continue
        nonblank = [a.get(k) for a in attrs if not blanks(a.get(k))]
        withdigit = [v for v in nonblank if __import__("re").search(r"\d", str(v))]
        out[k] = {"nonblank": len(nonblank), "with_digit": len(withdigit), "n": len(attrs)}
    return out


def main():
    src = json.load(open(SRC, encoding="utf-8"))
    picks = [x for x in src if str(x.get("declared_in_ledger")) in ("None", "", None)] or src[-7:]
    out = []
    for item in picks:
        url = item["url"].rstrip("/")
        rec = {"layer_truncated": item["ledger_layer_truncated"], "state": item["state"],
               "title": item["title"], "url": url,
               "ledger_declared": item.get("declared_in_ledger"),
               "ledger_rows_observed": item.get("rows_observed"),
               "survey_count": item.get("survey_count"), "requests_n": 0}
        m = http(url + "?f=json")
        rec["requests_n"] += 1
        meta = m["json"] or {}
        rec["http_meta"] = m["http"]
        rec["meta_err"] = m["err"]
        rec["meta_name"] = meta.get("name")
        rec["geometryType"] = meta.get("geometryType")
        rec["maxRecordCount"] = meta.get("maxRecordCount")
        fields = [f.get("name") for f in meta.get("fields", [])] if isinstance(meta, dict) else []
        rec["n_fields"] = len(fields)
        rec["fields_named_number_like"] = [f for f in fields if any(t in f.lower() for t in NUM)][:6]

        q = url + "/query?" + urllib.parse.urlencode(
            {"where": "1=1", "outFields": "*", "resultRecordCount": 20, "f": "json"})
        s = http(q)
        rec["requests_n"] += 1
        rec["http_sample"] = s["http"]
        rec["sample_err"] = s["err"]
        feats = (s["json"] or {}).get("features", []) if isinstance(s["json"], dict) else []
        attrs = [f.get("attributes", {}) for f in feats]
        rec["sampled_n"] = len(attrs)
        if attrs:
            keys = list(attrs[0].keys())
            rec["sample_nonnull_keys"] = sum(1 for k in keys if not all(blanks(a.get(k)) for a in attrs))
            rec["sample_keys_n"] = len(keys)
            cand = num_candidates(attrs)
            rec["number_field_candidates"] = list(cand)[:8]
            rec["number_fields"] = cand
            rec["number_nonnull"] = {k: v["with_digit"] for k, v in cand.items()}
            rec["sample1"] = {k: v for k, v in attrs[0].items() if not blanks(v)}

        # count：只在 meta/sample 都活着且拿不到行数时补第 3 个请求
        rec["count"] = None
        if rec["http_sample"] == 200 or (m["http"] == 200 and rec["sampled_n"] >= 0):
            c = http(url + "/query?" + urllib.parse.urlencode(
                {"where": "1=1", "returnCountOnly": "true", "f": "json"}))
            rec["requests_n"] += 1
            rec["http_count"] = c["http"]
            rec["count"] = ((c["json"] or {}).get("count") if isinstance(c["json"], dict) else None)

        # 判定
        if rec["http_meta"] != 200 or rec["http_sample"] != 200 or rec["sampled_n"] == 0:
            rec["verdict"] = "upstream_still_unstable"
            rec["verdict_why"] = (f"meta_http={rec['http_meta']} sample_http={rec['http_sample']} "
                                  f"sampled_n={rec['sampled_n']} err={rec['sample_err'][:80]}")
        elif rec["count"] in (None, 0):
            rec["verdict"] = "empty_result"
            rec["verdict_why"] = f"query 返回 0 行或 count 不可得（count={rec['count']}）"
        elif not any(v.get("with_digit") for v in (rec.get("number_fields") or {}).values()):
            rec["verdict"] = "address_fields_absent"
            rec["verdict_why"] = (f"服务已恢复（count={rec['count']}），但 20 条样值里门牌类字段全空/不存在 → "
                                  "不是地址层，别进地址分母")
        else:
            rec["verdict"] = "recovered_with_count"
            rec["verdict_why"] = (f"服务恢复：count={rec['count']}，"
                                  f"门牌字段非空 {rec['number_nonnull']}")

        out.append(rec)
        print(f"[{item['ledger_layer_truncated'][:34]:34s}] meta={rec['http_meta']} "
              f"sample={rec['http_sample']} n={rec['sampled_n']} count={rec['count']} "
              f"-> {rec['verdict']}", flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n": len(out),
               "requests_total": sum(r["requests_n"] for r in out), "layers": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    sys.exit(main())
