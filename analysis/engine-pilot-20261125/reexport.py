#!/usr/bin/env python3
"""从 _work/<STATE>.sqlite 重新导出分片 + 统计（不重跑 ingest）。

  python3 analysis/engine-pilot-20261125/reexport.py
用于「只改导出格式」的场景（本轮：单文件 232MB 撞 GitHub 100MB 上限 → 改 40MB 分片）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import yaml  # noqa: E402
from engine.fusion import Fusion  # noqa: E402

cfg = yaml.safe_load(open(os.path.join(ROOT, "engine", "config", "pilot.yaml"), encoding="utf-8"))
cfg["addrkey"] = cfg["addrkey"]
shard = cfg.get("export_shard_mb", 40)
for st in cfg["states"]:
    db = os.path.join(HERE, "_work", f"{st}.sqlite")
    if not os.path.isfile(db):
        print(f"{st}: skip (no sqlite)")
        continue
    f = Fusion(db, cfg, fresh=False)
    for old in __import__("glob").glob(os.path.join(HERE, st, "graded*.ndjson.gz")):
        os.remove(old)
    n = f.export(os.path.join(HERE, st, "graded"), state=st, shard_mb=shard)
    sums = f.summaries(state=st)
    stj = os.path.join(HERE, st, "stats.json")
    stats = json.load(open(stj, encoding="utf-8")) if os.path.isfile(stj) else {"state": st}
    tiered = dict(f.db.execute("SELECT tier, COUNT(*) FROM fused WHERE state=? GROUP BY tier", (st,)).fetchall())
    stats.update({"deduped_rows": n, **sums, "by_tier": tiered})
    json.dump(stats, open(stj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(st, "re-exported", n, "rows, shard_mb", shard, flush=True)
    f.db.close()
