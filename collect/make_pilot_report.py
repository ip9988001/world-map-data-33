#!/usr/bin/env python3
"""把 8 个层的 _manifest.json 汇总成 pilot_report.json（工头据此判验收）"""
import glob, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ROOT, "collect", "pilot_report.json")
# ★ 2026-10-23：改成增量合并。只补跑某一层时（-f layers=xxx），报告不能退化成 1 层，
#   否则工头/核验会把「只跑了 1 层」误读成「整个试点退步了」。
base = {}
if os.path.exists(REP):
    try:
        for m in (json.load(open(REP, encoding="utf-8")).get("detail") or []):
            if m.get("id"):
                base[m["id"]] = m
    except Exception:
        base = {}
for f in sorted(glob.glob(os.path.join(ROOT, "collect", "reports", "*.json")) +
                glob.glob(os.path.join(ROOT, "collect", "out", "*", "_manifest.json"))):
    try:
        m = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if not m.get("id"):
        continue
    prev = base.get(m["id"]) or {}
    # 本次结果比上次更差（0 行 / 有 err）时不要覆盖已有好数据
    if (prev.get("rows") or 0) > 0 and (m.get("err") or not (m.get("rows") or 0)):
        continue
    base[m["id"]] = m
ms = list(base.values())
ok = [m for m in ms if (m.get("rows") or 0) > 0 and not m.get("err")]
worst = max([(m.get("diff") or 0) for m in ok], default=0)
rep = {"layers": len(ms), "with_rows": len(ok),
       "worst_diff": round(worst, 4),
       "total_rows": sum((m.get("rows") or 0) for m in ms),
       "failed": [m["id"] for m in ms if m.get("err") or not (m.get("rows") or 0)],
       "detail": ms}
json.dump(rep, open(REP, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "detail"}, ensure_ascii=False))
