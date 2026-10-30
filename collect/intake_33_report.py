#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 dist/intake/ledger.json + 各表 ndjson 渲染成 docs/INTAKE-33-2026-10-30.md（离线）。"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dist", "intake")
DST = os.path.join(ROOT, "docs", "INTAKE-33-2026-10-30.md")
TABLES = ("addr", "aux_parcel", "aux_street", "aux_addr_nohouse", "reject")


def ids(path: str, key: str) -> set:
    s = set()
    if not os.path.exists(path):
        return s
    with open(path, encoding="utf-8") as f:
        for ln in f:
            try:
                s.add(json.loads(ln)[key])
            except Exception:      # noqa: BLE001
                continue
    return s


def main() -> int:
    led = json.load(open(os.path.join(OUT, "ledger.json"), encoding="utf-8"))["layers"]
    lines = []
    A = lines.append
    A("# 三仓 intake v1 落地 + 5 层验收（2026-10-30）")
    A("")
    A("契约：二仓 `schema/SCHEMA.json` **v2.0 rev2（LOCKED）** 的 19 个主字段 + 4 个三仓溯源列；"
      "本文件不定义任何新规范字段。")
    A("")
    A("## 一、分流规则（三表 + 拒绝）")
    A("")
    A("| 表 | 收什么 | 主键 |")
    A("|---|---|---|")
    A("| `addr` | 点层且五道门禁全过 | `addr_id` = sha1(state\\|county_fips\\|归一化地址键) |")
    A("| `aux_parcel` | **全部宗地行**（situs） | `aux_key` = `p:` + sha1 |")
    A("| `aux_street` | **全部线层行**（street_line） | `aux_key` = `s:` + sha1 |")
    A("| `aux_addr_nohouse` | 点层里「有街名、无门牌号」 | `aux_key` = `n:` + sha1 |")
    A("| `REJECT` | 门禁不过且无处安放的行 | 带 `reject_reason` |")
    A("")
    A("**宗地绝不出地址行**：`route()` 里 `parcel_situs` 在门禁判定**之前**就返回 `aux_parcel`，"
      "任何宗地行都不可能进 `addr`。依据是实测：55 个宗地层里 12 层 situs 与 mailing 字段并存，"
      "冲突率 100%（`analysis/parcel_conflict.json`），mailing 是业主外地/PO 信箱，当 situs 用会把地址系统性写错。"
      "测试 `collect/tests/test_intake_33.py::test_parcel_never_addr` 锁这条。")
    A("")
    A("五道硬门禁（任一不过 → 不进 `addr`）：`no_house_number` / `no_street_name` / `state_invalid` / "
      "`geo_missing` / `county_unresolved`（县一律射线法多边形判定，**禁用 bbox**）。")
    A("")
    A("## 二、5 层验收（2 点层 + 2 宗地层 + 1 线层，全量读完，非抽样）")
    A("")
    A("| 层 | 类型 | rows_total | with_number | without_number | addr | aux_parcel | aux_street | aux_addr_nohouse | reject | 对账 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    tot = {"rows": 0, "addr": 0, "aux": 0, "reject": 0}
    for l in led:
        t = l["tables"]
        tot["rows"] += l["rows_total"] or 0
        tot["addr"] += t.get("addr", 0)
        tot["aux"] += t.get("aux_parcel", 0) + t.get("aux_street", 0) + t.get("aux_addr_nohouse", 0)
        tot["reject"] += t.get("reject", 0)
        A(f"| `{l['layer'][:52]}` | {l['kind']} | {l['rows_total']:,} | {l['with_number']:,} | "
          f"{l['without_number']:,} | {t.get('addr', 0):,} | {t.get('aux_parcel', 0):,} | "
          f"{t.get('aux_street', 0):,} | {t.get('aux_addr_nohouse', 0):,} | {t.get('reject', 0):,} | "
          f"{'✅' if l.get('reconcile_ok') else '❌'} |")
    A(f"| **合计** | | **{tot['rows']:,}** | | | **{tot['addr']:,}** | | | | **{tot['reject']:,}** | |")
    A("")
    A("对账：每层 `rows_total == with_number + without_number == read`，且 `read == Σ各表`。"
      "线上（`street_line`）本来就是 0 门牌号，所以 `with_number=0 / without_number=rows_total` 是正确结果，不是丢数。")
    A("")
    A("## 三、主键不交集证明")
    A("")
    addr_ids, aux_ids = set(), set()
    for l in led:
        addr_ids |= ids(os.path.join(OUT, "addr.%s.ndjson" % l["layer"]), "addr_id")
        for t in ("aux_parcel", "aux_street", "aux_addr_nohouse"):
            aux_ids |= ids(os.path.join(OUT, "%s.%s.ndjson" % (t, l["layer"])), "aux_key")
    n_addr_rows = sum(l["tables"].get("addr", 0) for l in led)
    A(f"- `addr` 行 {n_addr_rows:,} 条 / 唯一 `addr_id` {len(addr_ids):,} 个 "
      f"（差 {n_addr_rows - len(addr_ids):,} 条是同址重复，留给下一步 coalesce 合并，不在 intake 阶段丢）")
    A(f"- `aux_*` 主键 {len(aux_ids):,} 个；**与 addr 的交集 {len(addr_ids & aux_ids)} 个**")
    A("- 结构上也不可能相交：`addr_id` 是 40 位裸 sha1，`aux_key` 一律带 `p:` / `s:` / `n:` 前缀")
    A("")
    A("## 四、拒绝原因分布（逐条有账，不静默丢）")
    A("")
    A("| 层 | 原因 | 条数 |")
    A("|---|---|---|")
    for l in led:
        for r, n in sorted((l.get("dropped_reason") or {}).items(), key=lambda x: -x[1]):
            A(f"| `{l['layer'][:40]}` | `{r}` | {n:,} |")
    A("")
    A("## 五、复跑")
    A("")
    A("```bash")
    A("python3 collect/county_tiger.py --build TX,WA,GA     # TIGER 县界缓存（只拉一次）")
    A("python3 collect/intake_33.py selftest --out dist/intake")
    A("python3 collect/intake_33.py run --layer <layer_id> --out dist/intake   # 单层")
    A("python3 collect/tests/test_intake_33.py               # 契约测试")
    A("python3 collect/intake_33_report.py                   # 重出本文")
    A("```")
    A("")
    open(DST, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("wrote", DST, os.path.getsize(DST), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
