#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归：片被 cancel / 缺片时，step_full_report 必须照出部分账本，不许整体失败。

事故背景（2026-10-30，run 41019004076）：14 片里 4 片被 350 分钟上限掐成 cancelled，
merge 拿不到那 4 片的账本 → step_full_report 直接 SystemExit → merge job failure →
整轮一行账都没有。立规：缺片只能被记成「未完成片」，不能变成「没有账」。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "collect", "step_full_report.py")


def shard_ledger(stage, shard, shards_total, recs, partial=False, planned=None):
    return {"schema": "collect-ledger/v1", "stage": stage, "step": stage.split("step")[-1],
            "shard": shard, "shards_total": shards_total, "size": 2, "unit_rows": 1000,
            "at": "2026-10-30T00:00:00Z", "forced_n": 0,
            "layers_planned": planned if planned is not None else len(recs),
            "layers_n": len(recs), "partial_run": partial,
            "ok": sum(1 for r in recs if r["status"] == "ok"),
            "failed": sum(1 for r in recs if r["status"] == "failed"),
            "partial": sum(1 for r in recs if r["status"] == "partial"),
            "empty": 0, "skipped_done": 0,
            "rows": sum((r.get("rows") or 0) for r in recs),
            "declared": sum((r.get("declared") or 0) for r in recs),
            "records": recs}


class TestFullReportTolerance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "collect", "ledger"))
        os.makedirs(os.path.join(self.tmp, "docs"))
        shutil.copy(SCRIPT, os.path.join(self.tmp, "collect", "step_full_report.py"))
        self.plan = os.path.join(self.tmp, "collect", "ledger", "step04b_plan.json")
        json.dump({"schema": "plan/v1", "stage": "step04b", "size": 2, "layers_n": 8,
                   "shards_n": 4, "declared_rows": 400, "unit_rows": 1000, "tag": "collect-step04-{layer}",
                   "shards": [[{"layer": "a"}, {"layer": "b"}],
                              [{"layer": "c"}, {"layer": "d"}],
                              [{"layer": "e"}, {"layer": "f"}],
                              [{"layer": "g"}, {"layer": "h"}]]},
                  open(self.plan, "w", encoding="utf-8"), ensure_ascii=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _led(self, shard, recs, partial=False, planned=None, stage="step04b"):
        p = os.path.join(self.tmp, "collect", "ledger", "%s_shard%02d.json" % (stage, shard))
        json.dump(shard_ledger(stage, shard, 4, recs, partial, planned),
                  open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def _run(self):
        r = subprocess.run([sys.executable, os.path.join(self.tmp, "collect", "step_full_report.py"),
                            "--stage", "step04b", "--plan", self.plan],
                           capture_output=True, text=True, cwd=self.tmp)
        return r

    def test_missing_shards_do_not_crash(self):
        """4 片里 2 片被 cancel（无账本）→ 仍出账，未完成片 = [2,3]。"""
        ok = [{"layer": "a", "status": "ok", "rows": 50, "declared": 50},
              {"layer": "b", "status": "ok", "rows": 50, "declared": 50}]
        self._led(0, ok)
        self._led(1, [{"layer": "c", "status": "ok", "rows": 50, "declared": 50},
                      {"layer": "d", "status": "failed", "rows": 0, "declared": 50,
                       "reason": "上游 0 数据"}])
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        led = json.load(open(os.path.join(self.tmp, "collect", "step04b_ledger.json"), encoding="utf-8"))
        self.assertEqual(led["shards_expected"], 4)
        self.assertEqual(led["shards_reported"], 2)
        self.assertEqual(led["shards_incomplete"], [2, 3])
        self.assertEqual(led["layers_n"], 4)          # 缺片层不凭空造记录
        self.assertEqual(led["failed"], 1)
        self.assertFalse(led["complete"])
        doc = open(os.path.join(self.tmp, "docs", "STEP04-FULL-2026-10-30-shards.md"), encoding="utf-8").read()
        self.assertIn("未完成片显式列出", doc)
        self.assertIn("没有账本", doc)

    def test_partial_run_shard_flagged(self):
        """片内跑一半（partial_run=true）→ 记为未完成片，已跑层照常进账。"""
        self._led(0, [{"layer": "a", "status": "ok", "rows": 10, "declared": 10}],
                  partial=True, planned=2)
        self._led(1, [{"layer": "c", "status": "ok", "rows": 10, "declared": 10},
                      {"layer": "d", "status": "ok", "rows": 10, "declared": 10}])
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        led = json.load(open(os.path.join(self.tmp, "collect", "step04b_ledger.json"), encoding="utf-8"))
        self.assertEqual(led["shards_incomplete"], [0, 2, 3])
        detail = {d["shard"]: d["cause"] for d in led["shards_incomplete_detail"]}
        self.assertEqual(detail[0], "partial_run")
        self.assertEqual(detail[2], "no_ledger")
        self.assertEqual(led["ok"], 3)

    def test_all_green_marks_complete(self):
        for s in range(4):
            self._led(s, [{"layer": "l%d" % s, "status": "ok", "rows": 5, "declared": 5}])
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        led = json.load(open(os.path.join(self.tmp, "collect", "step04b_ledger.json"), encoding="utf-8"))
        self.assertEqual(led["shards_incomplete"], [])
        self.assertTrue(led["complete"])

    def test_no_shard_but_plan_still_reports(self):
        """一片账本都没有（全被 cancel）→ 仍写真值：全片未完成，退出码 0。"""
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        led = json.load(open(os.path.join(self.tmp, "collect", "step04b_ledger.json"), encoding="utf-8"))
        self.assertEqual(led["shards_incomplete"], [0, 1, 2, 3])
        self.assertEqual(led["layers_n"], 0)
        self.assertFalse(led["complete"])


if __name__ == "__main__":
    unittest.main()
