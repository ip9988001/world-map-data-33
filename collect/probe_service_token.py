#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判定一层是不是「服务级 token」—— 连续两轮探三个端点，全 499 才算。

为什么需要单独一支脚本：
  2026-10-30 的 NAD view 层，上游悄悄改成要 token 之后，`query` 与 `?f=json` 一起返回
  `{"error":{"code":499,"message":"Token Required"}}`，**HTTP 状态码却是 200**。
  任何只看状态码的检查都会说「服务正常」，于是这层永远被记成「我们没采」，
  每一轮都派单重采一遍，永远采 0 行。preflight 的 E14 能看出「声明不可复核」，
  但要把它落成账本状态 `capped_by_upstream`，必须先有**可复核的探测证据**。

判据（写死，不给参数）：
  · 三个端点：`<api>?f=json`（服务元数据）、`returnCountOnly`、`returnIdsOnly`；
  · 任一端点能读到 `count`（或元数据正常返回 name/geometryType）→ **不是**服务级 token；
  · 三段全是 499 `Token Required`，且**连续两轮**（间隔 ≥ `--gap` 秒）都如此 → `service_level_token`；
  · 只有一轮、或两轮结论不一致 → `inconclusive`，**不得据此改账本**。

产出（`--out`，`--append` 可把多层合进一个文件）：
  {schema, stage, generated_at, method, layers: [{layer, layer_url, verdict, all_rounds_token,
    rounds_n, conclusion, impact, rounds: [{round, at, probes{...}}]}]}

用法：
  python3 collect/probe_service_token.py \
      --target 's_Points_from_..._FeatureServer_0=https://services.arcgis.com/.../FeatureServer/0' \
      --stage 04b --out analysis/04b-token-499-evidence-2026-10-31.json --append
  # 拿到 evidence 之后**由人**决定是否改口径（本脚本绝不自动改账本）：
  python3 collect/adjudicate_04b.py --capped <layer> --capped-evidence <上面那份 JSON>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOKEN_CODE = 499


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def endpoints(api: str) -> dict:
    api = api.rstrip("/")
    return {
        "service_metadata": api + "?f=json",
        "returnCountOnly": api + "/query?where=1%3D1&returnCountOnly=true&f=json",
        "returnIdsOnly": api + "/query?where=1%3D1&returnIdsOnly=true&f=json",
    }


def probe(url: str, timeout: int = 30) -> dict:
    """一次探测。判据只看**响应体**：HTTP 200 + body 里的 499 才是服务级 token。"""
    tmp = "/tmp/probe_service_token.json"
    r = subprocess.run(["curl", "-s", "-m", str(timeout), "-o", tmp, "-w", "%{http_code}", url],
                       capture_output=True, text=True)
    try:
        body = open(tmp, encoding="utf-8", errors="replace").read()
    except OSError:
        body = ""
    try:
        d = json.loads(body)
    except Exception:                                         # noqa: BLE001
        d = {}
    err = d.get("error") or {}
    code = err.get("code")
    has_count = isinstance(d.get("count"), int)
    # 元数据端点正常时没有 error，且带 name/geometryType
    meta_ok = bool(d) and not err and ("name" in d or "geometryType" in d)
    return {"url": url, "http": r.stdout.strip(), "raw": body[:400],
            "error_code": code, "error_message": err.get("message"),
            "message_code": err.get("messageCode"), "count": d.get("count"),
            "service_level_token": (str(code) == str(TOKEN_CODE)
                                    or "Token Required" in body) and not has_count,
            "endpoint_ok": has_count or meta_ok}


def probe_layer(layer: str, api: str, rounds: int, gap: int) -> dict:
    eps = endpoints(api)
    rec = {"layer": layer, "layer_url": api.rstrip("/"), "rounds": []}
    for i in range(1, max(1, rounds) + 1):
        if i > 1:
            time.sleep(max(0, gap))
        rec["rounds"].append({"round": i, "at": now(),
                              "probes": {k: probe(u) for k, u in eps.items()}})
    all_tok = all(p["service_level_token"] for x in rec["rounds"] for p in x["probes"].values())
    any_ok = any(p["endpoint_ok"] for x in rec["rounds"] for p in x["probes"].values())
    rec["rounds_n"] = len(rec["rounds"])
    if all_tok and not any_ok:
        rec["verdict"], rec["all_rounds_token"] = "service_level_token", True
        rec["conclusion"] = ("服务级 token：连 `?f=json` 都 499，returnCountOnly / returnIdsOnly 同样 499，"
                             "连续两轮一致 → 本层已无法再采一个字节，也无法复核 declared。")
    elif any_ok:
        rec["verdict"], rec["all_rounds_token"] = "reachable", False
        rec["conclusion"] = "至少一个端点能读到数据 → 不是服务级 token（单次 query 被拦另说）"
    else:
        rec["verdict"], rec["all_rounds_token"] = "inconclusive", False
        rec["conclusion"] = "两轮结论不一致或都不是 499 Token Required → 不得据此改账本"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", action="append", required=True, metavar="LAYER=API_URL")
    ap.add_argument("--stage", default="04b")
    ap.add_argument("--out", required=True)
    ap.add_argument("--rounds", type=int, default=2, help="必须 ≥2 才算数（默认 2）")
    ap.add_argument("--gap", type=int, default=60, help="两轮之间的间隔秒数（默认 60）")
    ap.add_argument("--append", action="store_true", help="把结果并进已有 --out 文件（按 layer 去重）")
    a = ap.parse_args()

    targets = []
    for spec in a.target:
        layer, _, url = spec.partition("=")
        if not url:
            raise SystemExit("--target 要写成 LAYER=API_URL：%r" % spec)
        targets.append((layer.strip(), url.strip()))

    doc = {"schema": "upstream-token-evidence/v1", "stage": a.stage, "generated_at": now(),
           "method": ("每轮探 3 个端点（`?f=json` / returnCountOnly / returnIdsOnly），"
                      "间隔 ≥%d 秒连探 %d 轮。判据只看响应体：HTTP 200 + body 里 code=499 "
                      "`Token Required` 才算服务级 token —— 只看状态码会误判成「服务正常」。"
                      % (a.gap, a.rounds)),
           "layers": []}
    if a.append and os.path.exists(a.out):
        try:
            old = json.load(open(a.out, encoding="utf-8"))
            doc["layers"] = [x for x in (old.get("layers") or [])
                             if x.get("layer") not in {l for l, _ in targets}]
        except Exception:                                     # noqa: BLE001
            doc["layers"] = []

    for layer, url in targets:
        rec = probe_layer(layer, url, a.rounds, a.gap)
        doc["layers"].append(rec)
        print(json.dumps({"layer": layer, "verdict": rec["verdict"],
                          "rounds_n": rec["rounds_n"],
                          "all_rounds_token": rec["all_rounds_token"]}, ensure_ascii=False))

    tok = [x["layer"] for x in doc["layers"] if x["verdict"] == "service_level_token"]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(doc, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("写入 %s（服务级 token：%s）" % (a.out, ", ".join(tok) or "无"))
    if tok:
        print("下一步（**改账本要人点头**，本脚本不自动改）：")
        for L in tok:
            print("  python3 collect/adjudicate_04b.py --capped %s --capped-evidence %s" % (L, a.out))
    return 0 if not [x for x in doc["layers"] if x["verdict"] == "inconclusive"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
