#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-036 回归：`max_shards` 砍片**不许静默**。

三条判据（用户 2026-10-31 明令）：
  ① 不砍（N ≤ MAX）：不打印 warning，`shards_dropped` 为空，片一个不少；
  ② 砍：必须 `::warning::` + 完整列出被砍分片号与其中每一层 id（不许只报数量），
     plan 里留 `shards_dropped[]` / `plan_truncated{}`；
  ③ `max_shards=0`：全起，一个不砍（含 matrix 覆盖全部分片）。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from plan_truncate import truncate_plan, matrix_of   # noqa: E402


def make_plan(n_shards=3, per_shard=2):
    shards = [{"shard": i,
               "layers": ["L%d_%d" % (i, j) for j in range(per_shard)]}
              for i in range(n_shards)]
    return {"schema": "collect-plan/v1", "stage": "04b", "size": per_shard,
            "layers_n": n_shards * per_shard, "shards_n": n_shards, "shards": shards}


class NotTruncated(unittest.TestCase):
    def test_small_plan_is_untouched_and_silent(self):
        plan = make_plan(3)
        warns = []
        out, kept, dropped = truncate_plan(plan, 3, warn=warns.append)
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 3)
        self.assertEqual(out["shards_dropped"], [])
        self.assertIsNone(out["plan_truncated"])
        self.assertEqual(warns, [], "没砍片就不许打 warning（噪声会训练人忽略真 warning）")

    def test_empty_max_shards_is_zero(self):
        plan = make_plan(2)
        out, kept, dropped = truncate_plan(plan, "", warn=lambda m: None)
        self.assertEqual(len(kept), 2)
        self.assertIsNone(out["plan_truncated"])


class TruncationIsLoud(unittest.TestCase):
    def test_warning_lists_every_dropped_shard_and_layer(self):
        plan = make_plan(3, per_shard=2)          # 3 片 / 6 层，砍到 1 片
        warns = []
        out, kept, dropped = truncate_plan(plan, 1, warn=warns.append)
        text = "\n".join(warns)
        # ① 必须带 GitHub annotation 前缀，不然 Actions 里看不出是警告
        self.assertIn("::warning::", text)
        # ② 分片号必须点名
        self.assertEqual([d["shard"] for d in dropped], [1, 2])
        self.assertIn("shard 1", text)
        self.assertIn("shard 2", text)
        # ③ 被砍的每一层 id 都必须出现（不许只报「少了 4 层」）
        for lid in ("L1_0", "L1_1", "L2_0", "L2_1"):
            self.assertIn(lid, text)
        # ④ 账本/收口要读的字段
        self.assertEqual(out["plan_truncated"]["expected_shards"], 3)
        self.assertEqual(out["plan_truncated"]["actual_shards"], 1)
        self.assertEqual(out["plan_truncated"]["dropped_layers"], ["L1_0", "L1_1", "L2_0", "L2_1"])
        self.assertEqual([d["layers"] for d in out["shards_dropped"]],
                         [["L1_0", "L1_1"], ["L2_0", "L2_1"]])
        # ⑤ 计划本身不许被改小（被砍的片在账本里仍要算「该跑没跑」）
        self.assertEqual(out["shards_n"], 3)
        self.assertEqual(len(out["shards"]), 3)
        self.assertEqual(len(kept), 1)


class ZeroMeansAll(unittest.TestCase):
    def test_max_shards_zero_runs_every_shard(self):
        plan = make_plan(14, per_shard=20)
        warns = []
        out, kept, dropped = truncate_plan(plan, 0, warn=warns.append)
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 14)
        self.assertEqual(len(matrix_of(kept)["include"]), 14)
        self.assertEqual([m["shard"] for m in matrix_of(kept)["include"]], list(range(14)))
        self.assertEqual(warns, [])


class CliWritesGithubOutput(unittest.TestCase):
    def test_cli_emits_shards_and_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            plan_p = os.path.join(td, "04b_plan.json")
            out_p = os.path.join(td, "gh_out.txt")
            json.dump(make_plan(3), open(plan_p, "w", encoding="utf-8"))
            r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "plan_truncate.py"),
                                "--plan", plan_p, "--max-shards", "2",
                                "--github-output", out_p],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("::warning::", r.stderr)
            lines = dict(l.split("=", 1) for l in open(out_p, encoding="utf-8").read().splitlines())
            self.assertEqual(lines["shards"], "2")
            self.assertEqual(json.loads(lines["matrix"])["include"], [{"shard": 0}, {"shard": 1}])
            written = json.load(open(plan_p, encoding="utf-8"))
            self.assertEqual(written["plan_truncated"]["actual_shards"], 2)
            self.assertEqual(written["plan_truncated"]["dropped_layers"], ["L2_0", "L2_1"])


if __name__ == "__main__":
    unittest.main()
