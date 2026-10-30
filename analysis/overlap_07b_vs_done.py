#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""07b 待采层 与 已采层（step03/04/05/07 的 tag）的重叠对账 —— 防重复采。

为什么查这个：07b 的 skip_done 只认 `collect-step07-*` 这一套 tag（steps.json done_from="07"）。
如果某层其实已经被 04b/05b 采过（tag 落在 step04/step05 命名空间），07b 会把它当「没采过」
再采一遍 —— 白烧几小时带宽，并让 08 的去重多一份重复来源。

输入：/tmp/07b_plan.json（full_plan.py --stage 07b 产出，skip_done 后）、/tmp/collected.json
输出：analysis/07b-overlap-<date>.json + 一行结论
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    date = time.strftime("%Y-%m-%d", time.gmtime())
    plan = json.load(open("/tmp/07b_plan.json", encoding="utf-8"))
    coll = json.load(open("/tmp/collected.json", encoding="utf-8"))
    by_step = coll["by_step"]

    pending = []
    for sh in plan.get("shards") or []:
        for r in sh.get("layers") or []:
            pending.append(r if isinstance(r, str) else (r.get("id") or r.get("layer")))
    if not pending:  # 兼容不带 shards 的扁平格式
        pending = plan.get("layers") or []

    def done_set(step):
        return {lid for lid, rec in (by_step.get(step) or {}).items() if rec.get("has_ckpt")}

    d03, d04, d05, d07 = done_set("03"), done_set("04"), done_set("05"), done_set("07")
    hits = {"03": [], "04": [], "05": [], "07": []}
    for r in pending:
        lid = r if isinstance(r, str) else (r.get("id") or r.get("layer"))
        for k, s in (("03", d03), ("04", d04), ("05", d05), ("07", d07)):
            if lid in s:
                hits[k].append(lid)

    overlap_any = sorted({x for v in hits.values() for x in v})
    out = {
        "schema": "07b-overlap/v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"plan": "collect/full_plan.py --stage 07b --size 670（skip_done 后）",
                   "collected_scan": "analysis/scan_collected.py（Releases tag + checkpoint）"},
        "groups": {
            "07b_candidates_pending": len(pending),
            "07b_done_step07": len(d07),
            "already_done_step03": len(d03),
            "already_done_step04": len(d04),
            "already_done_step05": len(d05),
            "collected_layers_total": coll["collected_layers"],
        },
        "overlap": {k: {"n": len(v), "layers": v[:80]} for k, v in hits.items()},
        "overlap_any_n": len(overlap_any),
        "overlap_any": overlap_any[:200],
        "verdict": ("no_double_collect" if not overlap_any else "would_recollect"),
    }
    f = os.path.join(ROOT, "analysis", "07b-overlap-%s.json" % date)
    json.dump(out, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out["groups"][k] for k in out["groups"]}, ensure_ascii=False, indent=1))
    print("重叠层数：%d  verdict=%s" % (len(overlap_any), out["verdict"]))
    for k, v in hits.items():
        if v:
            print("  step%s 重叠 %d 层：%s" % (k, len(v), ", ".join(v[:10])))
    print("→", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
