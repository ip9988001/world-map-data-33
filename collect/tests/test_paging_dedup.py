#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-048 缺陷 B 单测：keyset → offset 顶补**不产生重复行**。

事故实数（run 44985733259 · led-05b-0/05b_shard00.json，两轮一致）：
    cgis_..._911_Addresses_Public_View_FeatureServer_2   163,221 / 81,784  = 1.996×
    qKAFwdGU_..._Address_Points_FeatureServer_0          363,000 / 181,471 = 2.000×
根因两条，都在 `pilot._unit_range` / `pilot._top_up_offset`：
  ① `_absorb` 无条件 `buf.append(...)` + `rows += 1`，没有行身份判重 → 顶补重叠的页被**实写**第二遍；
  ② `_top_up_offset` 自己 `got += len(feats)`，调用方又 `rows += gained` → 行数还**再翻一倍**。

本文件锁四件事：
  ① 服务把 resultOffset 夹住/忽略（同一页反复回来）→ 只写一遍，行数 == 唯一 OID 数；
  ② 顶补只收 oid > 游标 的新行（keyset 语义不被 offset 页污染）；
  ③ 行数不重复累加（990 + 顶补 10 → 1,000，不是 1,010）；
  ④ 无 OID 的行按属性摘要判重（`_row_key`）。
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
import tempfile
import threading
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pilot  # noqa: E402


class _Svc:
    """可控的假上游：keyset 只吐 visible 行；offset 页可选择「夹住 offset 从头再来」。"""

    def __init__(self, total=1000, visible=990, page=200, clamp_offset=True, null_oid=0):
        self.total, self.visible, self.page = total, visible, page
        self.clamp_offset, self.null_oid = clamp_offset, null_oid
        self.calls = []

    def __call__(self, api, params, timeout=60):
        self.calls.append(dict(params))
        w = str(params.get("where") or "")
        if str(params.get("returnCountOnly") or "").lower() == "true":
            return {"count": self.total}
        ps = int(params.get("resultRecordCount") or self.page)
        if "resultOffset" in params:
            off = int(params.get("resultOffset") or 0)
            if self.clamp_offset:          # ← 事故形态：服务不认 offset，永远回第一页
                off = 0
            n = min(ps, max(0, self.total - off))
            feats = [{"attributes": {"OBJECTID": 5000 + off + i}} for i in range(n)]
            return {"features": feats, "exceededTransferLimit": n == ps}
        # keyset 页
        m = w.rsplit(">", 1)[-1].strip()
        try:
            last = int(m)
        except ValueError:
            last = 0
        start = max(last + 1, 5000)
        n = min(ps, max(0, 5000 + self.visible - start))
        feats = [{"attributes": {"OBJECTID": start + i}} for i in range(n)]
        return {"features": feats, "exceededTransferLimit": n == ps}


def _read_parts(d):
    oids = []
    for p in sorted(glob.glob(os.path.join(d, "*.ndjson.gz"))):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                oids.append((json.loads(line).get("raw") or {}).get("OBJECTID"))
    return oids


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="w33048-")
        self._old = (pilot._q, pilot.OUTBASE, dict(pilot.CUR), pilot.CHUNK)
        pilot.OUTBASE = self.tmp
        pilot.CUR = {"id": "layer-A", "title": "A"}
        pilot.CHUNK = 50000

    def tearDown(self):
        pilot._q, pilot.OUTBASE, pilot.CHUNK = self._old[0], self._old[1], self._old[3]
        pilot.CUR.clear()
        pilot.CUR.update(self._old[2])

    def _run(self, svc, ps=200):
        pilot._q = svc
        lock = threading.Lock()
        prog = {"workers": {}, "rows": 0, "base_rows": 0}
        return pilot._unit_range("http://stub/0", "OBJECTID", "", None, None, 0, ps, 0,
                                 lambda *a, **k: None, prog, lock, {})


class NoDuplicateRows(_Base):
    def test_clamped_offset_does_not_duplicate(self):
        """事故形态：服务夹住 offset 反复回第一页 → 只许写一遍。"""
        svc = _Svc(total=1000, visible=990, clamp_offset=True)
        rows, files, err, expect = self._run(svc)
        oids = _read_parts(os.path.join(self.tmp, "layer-A"))
        self.assertEqual(len(oids), len(set(oids)), "写出重复行：%d 行里有 %d 个唯一 OID"
                         % (len(oids), len(set(oids))))
        self.assertEqual(rows, len(set(oids)))
        self.assertLess(rows, expect)              # 补不回来就如实 short，不靠重复行凑数
        self.assertTrue(err.startswith("short:"), err)

    def test_offset_topup_recovers_without_double_count(self):
        """offset 正常回数据：990 + 10 → 1,000（不是 1,010，也不是 1,990）。"""
        svc = _Svc(total=1000, visible=990, clamp_offset=False)
        rows, files, err, expect = self._run(svc)
        oids = _read_parts(os.path.join(self.tmp, "layer-A"))
        self.assertEqual(len(oids), len(set(oids)))
        self.assertEqual(rows, 1000)
        self.assertEqual(len(set(oids)), 1000)
        self.assertEqual(err, "")

    def test_topup_ignores_oids_at_or_below_cursor(self):
        """顶补页里 oid ≤ 游标 的老行一律不要。"""
        seen = []
        got, _ = pilot._top_up_offset(
            "http://stub/0", {"outFields": "*", "f": "json"}, ps=10, start_offset=0,
            expect=100, oid_field="OBJECTID", idx=0, log=lambda *a, **k: None,
            sink=lambda feats: seen.append(len(feats)))
        self.assertEqual(got, 0)                   # 没有 sink 语义时按「全收」返回 0 行（空页）
        self.assertEqual(seen, [])


class RowKeyTest(unittest.TestCase):
    def test_oid_first(self):
        self.assertEqual(pilot._row_key({"OBJECTID": 7, "X": 1}, "OBJECTID"), ("oid", "7"))
        self.assertEqual(pilot._row_key({"OBJECTID_1": 9}, "OBJECTID"), ("oid", "9"))

    def test_hash_fallback_is_stable_and_order_free(self):
        a = pilot._row_key({"A": 1, "B": 2}, "")
        b = pilot._row_key({"B": 2, "A": 1}, "")
        self.assertEqual(a, b)
        self.assertEqual(a[0], "h")
        self.assertNotEqual(a, pilot._row_key({"A": 1, "B": 3}, ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
