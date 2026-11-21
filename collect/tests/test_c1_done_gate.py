#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1-b stub：复刻 138c05 的检查点状态（签名 14acda7e100ba989，2131/2300 却被标 done）

要证明的是**「旧的 done 标记被推翻并重翻」**，不是「断言会打印」：

  ① `resume_todo` 直接判：done=[0] + unit_rows={0:2131} + 无 unit_expect + count=2300
     → keep=[] / redone=[0]（作废）；
  ② 端到端 `collect_arcgis_v2` 带着这份旧检查点续跑：
     - 日志出现「作废 … done 标记」「本轮重翻」（签名在 ckpt_invalidated.json 名单里 → 名单先挡，
       名单没覆盖的由 resume_todo 行数判据兜）；
     - 真的重翻了（服务端收到 query，不是 3.4 秒跳过）；
     - rows 补到 2300（≥ expect×(1-GAP_TOL)），done 重新置位并写入 unit_expect；
  ③ 补不回来的形态（上游只给 2131 行）：err = `short:2131/2300`，**done 仍为空**（→ partial/failed）。

零网络：patch `pilot.get_json`（底层请求）、`pilot._load_ckpt`（给旧检查点）、`pilot._upload`。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import pilot  # noqa: E402

# 138c05 的真实检查点签名（collect/ledger/.ckpt_cache/collect-step07-138c05_...@2026-10-31T08_54_00Z.json）
CKPT_SIG_138C05 = "14acda7e100ba989"
COUNT_138C05 = 2300          # 上游实时 count
ROWS_STALE = 2131            # 旧检查点里被标 done 的行数


class Svc:
    """最小 ArcGIS stub：支持 count / returnIds / keyset(FID) / resultOffset / objectIds。

    cap=None  → 全量可翻（2300 行都能拿到）
    cap=2131  → 上游只给 2131 行（模拟「补翻也补不回来」）
    """

    def __init__(self, n=COUNT_138C05, cap=None, page=2000):
        self.n, self.cap, self.page = n, cap, page
        self.queries = 0

    def rows_visible(self):
        return self.n if self.cap is None else min(self.n, self.cap)

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries += 1
        vis = self.rows_visible()
        if q.get("outStatistics"):
            return {"features": [{"attributes": {"mn": 1, "mx": vis}}]}
        if q.get("returnCountOnly") == "true":
            return {"count": self.n}
        if q.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": "FID", "objectIds": list(range(1, vis + 1))}
        if "objectIds" in q:
            ids = [int(x) for x in q["objectIds"].split(",") if x]
            return {"features": [{"attributes": {"FID": i}} for i in ids]}
        if "resultRecordCount" not in q and "where" not in q:
            return {"fields": [{"name": "FID"}], "maxRecordCount": self.page,
                    "objectIdField": "FID", "definitionExpression": None}
        ps = int(q.get("resultRecordCount") or self.page)
        lo, hi, after = 1, vis, None
        import re
        w = q.get("where", "1=1")
        m = re.search(r"FID>=(\d+)", w)
        if m:
            lo = int(m.group(1))
        m = re.search(r"FID<=(\d+)", w)
        if m:
            hi = min(int(m.group(1)), vis)
        m = re.search(r"FID>(?!=)(\d+)", w)
        if m:
            after = int(m.group(1))
        if "resultOffset" in q:
            start = lo + int(q["resultOffset"])
        else:
            start = max(lo, after + 1) if after is not None else lo
        end = min(hi, start + ps - 1)
        if start > hi:
            return {"features": [], "exceededTransferLimit": False}
        return {"features": [{"attributes": {"FID": i}} for i in range(start, end + 1)],
                "exceededTransferLimit": end < hi}


def legacy_ckpt():
    """复刻 14acda7e100ba989 的状态：单元 1/1 标 done，实际只有 2,131 / 2,300 行。"""
    return {"ver": pilot.CKPT_VER,
            "url": "http://stub.local/FeatureServer/0",
            "plan_hash": CKPT_SIG_138C05,
            "unit_rows": {"0": ROWS_STALE},
            "unit_rows_seen": {"0": ROWS_STALE},
            "unit_files": {}, "unit_package": {},
            "unit_uploaded": {"0": True},          # 产物上传过 → 旧逻辑「产物在 = 完成」
            "done_units": [0],
            "tag": "collect-step07-138c05"}


class DoneGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="c1stub-")
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload,
                      pilot._load_ckpt, pilot._save_ckpt, pilot._publish_ckpt,
                      pilot.UNIT_ROWS, pilot.PROG_DIR, pilot.STRATEGY)
        pilot.OUTBASE = self.tmp
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.UNIT_ROWS = 5000                  # 2,300 行 → 单单元（对齐 138c05 的 1/1）
        pilot.CUR.update({"id": "c138", "title": "c138",
                          "url": "http://stub.local/FeatureServer/0", "svc": "FeatureServer"})
        self.saved = {}
        self.logs = []
        pilot._upload = lambda files, log=None, tag=None: True
        pilot._publish_ckpt = lambda snap, log=None: None
        pilot._save_ckpt = lambda ck: self.saved.update({"ck": json.loads(json.dumps(ck))})
        pilot._load_ckpt = lambda plan_hash: legacy_ckpt()

    def tearDown(self):
        (pilot.OUTBASE, cur, gj, up, lc, sc, pc, pilot.UNIT_ROWS,
         pilot.PROG_DIR, pilot.STRATEGY) = self._orig
        pilot.get_json, pilot._upload = gj, up
        pilot._load_ckpt, pilot._save_ckpt, pilot._publish_ckpt = lc, sc, pc
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_resume_todo_voids_stale_done(self):
        """① 纯判定层：done 被作废，返回的 redone 含该单元"""
        keep, redone = pilot.resume_todo([(None, None)], legacy_ckpt(), COUNT_138C05,
                                        log=self.logs.append)
        self.assertEqual(keep, [])
        self.assertEqual(redone, [0])
        self.assertTrue(any("作废 done 标记 u0" in m for m in self.logs), self.logs)
        print("STUB| " + [m for m in self.logs if "作废 done 标记 u0" in m][0])

    def test_end_to_end_refetch_reaches_expect(self):
        """② 端到端：作废 → 真重翻 → rows 补到 2,300，done 重新置位"""
        svc = Svc()
        pilot.get_json = svc
        rows, count, err, parts = pilot.collect_arcgis_v2(
            pilot.CUR["url"], 0, self.logs.append, 1, False)
        self.assertEqual(count, COUNT_138C05)
        self.assertEqual(rows, COUNT_138C05)                  # ★ 补到 expect 以上
        self.assertEqual(err, "")
        self.assertGreater(svc.queries, 1)                    # ★ 真重翻了，不是跳过
        # 作废走两条路：签名在「需重验」名单（14acda7e100ba989 就在名单里）→ 先被名单挡掉；
        # 名单没覆盖时由 resume_todo 的行数判据兜住（test ① 单独证明）。
        self.assertTrue(any(("在「需重验」名单" in m) or ("作废 done 标记 u0" in m) for m in self.logs),
                        self.logs)
        self.assertTrue(any("本轮重翻" in m or "重翻" in m for m in self.logs), self.logs)
        ck = self.saved.get("ck") or {}
        self.assertEqual(ck.get("done_units"), [0])           # ★ 采齐后才重新置位
        self.assertEqual(str((ck.get("unit_expect") or {}).get("0")), str(COUNT_138C05))
        self.assertEqual(str((ck.get("unit_rows_seen") or {}).get("0")), str(COUNT_138C05))
        for m in self.logs:
            if "作废" in m or "重翻" in m or m.startswith("done rows="):
                print("STUB| " + m)

    def test_end_to_end_unfixable_stays_partial(self):
        """③ 补不回来：上游只给 2,131 → err=short，done 仍为空（→ partial/failed）"""
        svc = Svc(cap=ROWS_STALE)
        pilot.get_json = svc
        rows, count, err, _ = pilot.collect_arcgis_v2(
            pilot.CUR["url"], 0, self.logs.append, 1, False)
        self.assertEqual(rows, ROWS_STALE)
        self.assertTrue(err.startswith("short:%d/%d" % (ROWS_STALE, COUNT_138C05)), err)
        ck = self.saved.get("ck") or {}
        self.assertNotIn(0, ck.get("done_units") or [])        # ★ 不标 done
        self.assertIn("0", ck.get("unit_errors") or {})
        print("STUB| err=%s done_units=%s" % (err, ck.get("done_units")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
