#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归：merge 作用域必须等于「本轮 plan 的片号集合」，不许把遗留片文件吃进账本。

事故背景（W33-058）：`step_full_report.py` 原先无条件
`glob(ledger/<stage>_shard*.json)`，把历次轮次留在同目录的片文件一起并进 merge。
05b 实测：plan 只有 3 片 / 577 层，目录里躺着 21 片 → 账本被冲成 1426 层、
实采行 37,069,680 被冲成 75,100,286（虚高一倍），收官文档自相矛盾。

立规：
1. 片号 ∉ plan 的片号集合 → 不读，且必须打印「忽略遗留片文件 N 个：<清单>」；
2. run 账本留痕 `read_shards` / `ignored_shard_files` / `shard_scope`，谁都能复核这轮读了哪几片；
3. 找不到 plan → 退回旧行为（全量读），但必须 ::warning:: 喊出来；
4. 判不出片号的文件不静默丢（保留 + warning）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(ROOT, "collect", "step_full_report.py")
STAGE = "05b"
RUN_ID = "scopetest"


def shard_ledger(stage, shard, shards_total, recs, partial=False, planned=None):
    return {"schema": "collect-ledger/v1", "stage": stage, "shard": shard,
            "shards_total": shards_total, "size": len(recs), "unit_rows": 1000,
            "at": "2026-11-22T00:00:00Z", "forced_n": 0,
            "layers_planned": planned if planned is not None else len(recs),
            "layers_n": len(recs), "partial_run": partial,
            "declared": sum((r.get("declared") or 0) for r in recs),
            "rows": sum((r.get("rows") or 0) for r in recs),
            "records": recs}


def r(layer, declared, rows, status="ok"):
    return {"layer": layer, "status": status, "declared": declared, "rows": rows}


class TestMergePlanScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ledger = os.path.join(self.tmp, "collect", "ledger")
        os.makedirs(self.ledger)
        os.makedirs(os.path.join(self.tmp, "docs"))
        for name in ("step_full_report.py", "ledger_merge.py", "ckpt_guard.py"):
            shutil.copy(os.path.join(ROOT, "collect", name),
                        os.path.join(self.tmp, "collect", name))
        # 本轮 plan：3 片（片号 0/1/2）
        self.plan = os.path.join(self.ledger, STAGE + "_plan.json")
        json.dump({"schema": "collect-plan/v1", "stage": STAGE, "size": 3, "layers_n": 3,
                   "shards_n": 3, "declared_rows": 600, "unit_rows": 1000,
                   "shards": [{"shard": 0, "layers": ["a"]},
                              {"shard": 1, "layers": ["b"]},
                              {"shard": 2, "layers": ["c"]}]},
                  open(self.plan, "w", encoding="utf-8"), ensure_ascii=False)
        # 本轮 3 片
        self._write_shard(0, [r("a", 100, 100)])
        self._write_shard(1, [r("b", 200, 200)])
        self._write_shard(2, [r("c", 300, 299, "partial")])
        # 遗留片：来自更早轮次（片号 7 / 9），层数各不同
        self._write_shard(7, [r("old7_%d" % i, 10, 10) for i in range(5)], total=21)
        self._write_shard(9, [r("old9_%d" % i, 10, 10) for i in range(4)], total=21)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---------- helpers ----------
    def _write_shard(self, shard, recs, total=3, partial=False, name=None):
        p = os.path.join(self.ledger, name or ("%s_shard%02d.json" % (STAGE, shard)))
        json.dump(shard_ledger(STAGE, shard, total, recs, partial),
                  open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return p

    def _run(self, plan=True, extra=()):
        cmd = [sys.executable, os.path.join(self.tmp, "collect", "step_full_report.py"),
               "--stage", STAGE, "--run-id", RUN_ID]
        if plan:
            cmd += ["--plan", self.plan]
        cmd += list(extra)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.tmp)

    def _run_ledger(self):
        return json.load(open(os.path.join(self.ledger, "%s_run%s.json" % (STAGE, RUN_ID)),
                              encoding="utf-8"))

    def _doc(self):
        return open(os.path.join(self.tmp, "docs", "STEP05B-FULL-2026-10-30-shards.md"),
                    encoding="utf-8").read()

    # ---------- 用例 ----------
    def test_only_plan_shards_are_merged(self):
        """3 片 plan + 遗留 shard07/shard09 → 只算 3 片，层数/行数按 3 片，ignored 名单正确。"""
        res = self._run(extra=["--audit-ignored"])
        self.assertEqual(res.returncode, 0, res.stderr)
        led = self._run_ledger()
        self.assertEqual(led["layers_n"], 3)
        self.assertEqual(led["declared"], 600)
        self.assertEqual(led["rows"], 599)
        self.assertEqual(led["read_shards"], [0, 1, 2])
        self.assertEqual(led["ignored_shard_files"],
                         ["05b_shard07.json", "05b_shard09.json"])
        self.assertEqual(led["shard_scope"], "plan")
        self.assertEqual(led["shards_reported"], 3)
        self.assertEqual(led["shards_incomplete"], [])
        self.assertEqual(led["ok"], 2)          # a / b
        self.assertEqual(led["partial"], 1)      # c

    def test_ignored_files_are_printed_not_silent(self):
        """被排除的遗留片必须点名打印，且文档里单独成节（含 --audit-ignored 的层数）。"""
        res = self._run(extra=["--audit-ignored"])
        self.assertIn("忽略遗留片文件 2 个", res.stdout)
        self.assertIn("05b_shard07.json", res.stdout)
        self.assertIn("05b_shard09.json", res.stdout)
        doc = self._doc()
        self.assertIn("## 二之三、遗留片文件（不计入本轮）", doc)
        self.assertIn("遗留片合计 2 个文件 / 9 层记录", doc)
        # 遗留层绝不能出现在逐层台账里
        self.assertNotIn("old7_0", doc)
        self.assertNotIn("old9_0", doc)
        # 片完成度表只有 0/1/2 三行
        rows = re.findall(r"^\| (\d+) \| \d+ \| \d+ \|", doc, re.M)
        self.assertEqual(rows, ["0", "1", "2"])

    def test_no_plan_falls_back_to_dir_all_with_warning(self):
        """找不到 plan → 退回旧行为（全量读），但必须 ::warning:: 喊出来。"""
        os.remove(self.plan)
        res = self._run(plan=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("::warning::", res.stdout)
        self.assertIn("无 plan", res.stdout)
        self.assertIn("可能吃到遗留片", res.stdout)
        led = self._run_ledger()
        self.assertEqual(led["shard_scope"], "dir-all")
        self.assertEqual(led["layers_n"], 5 + 4 + 3)      # 全量读：旧行为
        self.assertEqual(led["read_shards"], [0, 1, 2, 7, 9])
        self.assertEqual(led["ignored_shard_files"], [])

    def test_missing_shard_still_reported_incomplete(self):
        """作用域收窄不能把「本轮某片没跑」藏起来：缺片仍要记未完成片。"""
        os.remove(os.path.join(self.ledger, "%s_shard02.json" % STAGE))
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stderr)
        led = self._run_ledger()
        self.assertEqual(led["layers_n"], 2)
        self.assertEqual(led["read_shards"], [0, 1])
        self.assertEqual(led["shards_incomplete"], [2])
        self.assertFalse(led["complete"])

    def test_unparsable_shard_name_is_kept_with_warning(self):
        """判不出片号的文件不静默丢：保留读取 + warning。"""
        self._write_shard(None, [r("weird", 7, 7)], total=None,
                          name="%s_shard_bogus.json" % STAGE)
        res = self._run()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("判不出片号", res.stdout)
        led = self._run_ledger()
        self.assertEqual(led["layers_n"], 4)               # 3 片 + 判不出片号那 1 层
        self.assertIn("weird", [rec["layer"] for rec in led["records"]])
        self.assertEqual(led["unparsable_shard_files"], ["05b_shard_bogus.json"])


if __name__ == "__main__":
    unittest.main()
