#!/usr/bin/env python3
"""把 8 个层的 _manifest.json 汇总成 pilot_report.json（工头据此判验收）"""
import glob, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ms = []
seen = set()
for f in sorted(glob.glob(os.path.join(ROOT, "collect", "reports", "*.json")) +
                glob.glob(os.path.join(ROOT, "collect", "out", "*", "_manifest.json"))):
    try:
        m = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if m.get("id") in seen:
        continue
    seen.add(m.get("id"))
    ms.append(m)
ok = [m for m in ms if (m.get("rows") or 0) > 0 and not m.get("err")]
worst = max([(m.get("diff") or 0) for m in ok], default=0)
rep = {"layers": len(ms), "with_rows": len(ok),
       "worst_diff": round(worst, 4),
       "total_rows": sum((m.get("rows") or 0) for m in ms),
       "failed": [m["id"] for m in ms if m.get("err") or not (m.get("rows") or 0)],
       "detail": ms}
json.dump(rep, open(os.path.join(ROOT, "collect", "pilot_report.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "detail"}, ensure_ascii=False))
