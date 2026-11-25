"""muse-000250 · 已下载层「只重验不重下」（v2 修正版）：
层目录里的 tar.gz 早按设计删掉了（峰值磁盘只留一层），所以字节必须取 ledger.json 里落盘的 bytes 记录，
不能重扫 tar。校验 ④ 改成单位自适应（bytes 与 kb 取更接近者，都不合 ±20% 只记 anomaly 不判 mismatch）。
只读 dist 数据，唯一写回的是该层 ledger.json 的 status / unit_recheck 注释。
"""
import csv
import json
import os
import time

ROOT = "/data/workspace/wmd-step8-reconcile"
INV = os.path.join(ROOT, "analysis", "full-inventory-20261124", "local-vs-ledger-reconcile.csv")
OUT = os.path.join(ROOT, "analysis", "step8-reconcile-20261125")
DIST = os.environ.get("INTAKE_DIST", "/data/workspace/world-map-data-33/dist/intake-full")
COLS = ["layer", "tag", "assets_n", "payload_n", "dl_bytes", "base", "unit", "bytes_dev",
        "bytes_ok", "was", "now"]


def load_bases():
    d = {}
    for r in csv.DictReader(open(INV, encoding="utf-8")):
        if r["reconcile_class"] == "local_absent_assets_exist_not_downloaded":
            d[r["layer"]] = {"tag": r["tag"], "payload_n": int(r["release_payload_n"] or 0),
                             "bytes_base": int(r["release_bytes_in_dist_snapshot"] or 0)}
    return d


def unit_dev(dl, base):
    if not base:
        return "unavailable", None, None
    cands = {"bytes": base, "kb": base * 1024}
    devs = {u: abs(dl - v) / v for u, v in cands.items()}
    u = min(devs, key=devs.get)
    return u, round(devs[u], 4), devs[u] <= 0.20


def main():
    bases = load_bases()
    rows, changed, restored = [], 0, 0
    for lid, meta in bases.items():
        led_p = os.path.join(DIST, "layers", lid, "ledger.json")
        if not os.path.isfile(led_p):
            continue
        try:
            led = json.load(open(led_p, encoding="utf-8"))
        except Exception as e:                                     # noqa: BLE001
            rows.append({"layer": lid, "now": "ledger_unreadable"})
            continue
        dl = int(led.get("bytes") or 0)
        assets_n = int(led.get("assets_n") or 0)
        base = meta["bytes_base"]
        unit, dev, ok = unit_dev(dl, base)
        now = "ok"
        reason = ""
        if meta["payload_n"] and assets_n and assets_n != meta["payload_n"]:
            now, reason = "mismatch", f"资产数 {assets_n} != CSV {meta['payload_n']}"
        elif ok is False:
            now, reason = "anomaly", f"字节两单位均超 20%（unit={unit} dev={dev} dl={dl} base={base}）"
        was = led.get("status")
        if was != now:
            changed += 1
            if was == "anomaly" and now == "ok":
                restored += 1           # 上一版脚本（误按 tar 存在重扫）留下的错判，回滚
            led["status"] = now
            led["unit_recheck"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "from": was, "to": now,
                                   "bytes_unit": unit, "bytes_dev": dev, "dl_bytes": dl,
                                   "base": base, "note": "muse-000250 单位自适应重验（只重验不重下）"}
            if reason:
                led["reason"] = reason
            elif "reason" in led and not led.get("reason"):
                led.pop("reason", None)
            json.dump(led, open(led_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        rows.append({"layer": lid, "tag": meta["tag"], "assets_n": assets_n,
                     "payload_n": meta["payload_n"], "dl_bytes": dl, "base": base, "unit": unit,
                     "bytes_dev": dev, "bytes_ok": ok, "was": was, "now": now})
    for name, sel in (("re-verify.csv", rows),
                      ("pull-anomaly.csv", [r for r in rows if r.get("now") != "ok"])):
        with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
            w.writeheader()
            [w.writerow(r) for r in sel]
    stat = {"layers_on_disk": len(rows), "status_changed": changed, "restored_from_bad_v1": restored,
            "ok": sum(1 for r in rows if r.get("now") == "ok"),
            "anomaly": sum(1 for r in rows if r.get("now") == "anomaly"),
            "mismatch": sum(1 for r in rows if r.get("now") == "mismatch"),
            "unit_kb_rows": sum(1 for r in rows if r.get("unit") == "kb"),
            "unit_bytes_rows": sum(1 for r in rows if r.get("unit") == "bytes")}
    print(json.dumps(stat, ensure_ascii=False, indent=1))
    for r in [x for x in rows if x.get("now") != "ok"][:10]:
        print("NOTOK", r["layer"][:45], r["now"], r["unit"], r["bytes_dev"], r["dl_bytes"], r["base"])


if __name__ == "__main__":
    main()
