#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【7】only_layers / 独占白名单收敛成单一来源（muse-000146 第 7 项）。

现场先说清：**全仓检索该入口名 = 0 命中**（这个名字在本仓从来没存在过；字面 token 只出现在本文件里，
所以这一项不是「删掉第二处」，而是「把『不许有第二处』做成会红的断言」——
以免以后有人顺手在 workflow 里加个 `only_layers`、或在脚本里再开一条放行入口。

四条断言：
  ① 全仓（除 .git）`only_layers` 命中 = 0；同类的 `allow_layers` / `layer_allowlist` 也 = 0
  ② collect-full.yml 的 inputs 里，名字带 layer 的**只有一个**：force_layers
  ③ full_plan.py 只有一面 --force-layers 旗子，且唯一合并点 = resolve_allowlist()
  ④ 运行时：resolve_allowlist 不接受额外放行参数（谁也扩不出第二条入口）
"""
from __future__ import annotations

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
ROOT = os.path.dirname(COLLECT)
sys.path.insert(0, COLLECT)

import full_plan as FP                                     # noqa: E402

FORBIDDEN = ("only_layers", "allow_layers", "layer_allowlist", "LAYERS_ONLY")
CODE_EXT = (".py", ".yml", ".yaml", ".sh", ".json", ".md")


def _walk_sources():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in filenames:
            if fn.endswith(CODE_EXT):
                yield os.path.join(dirpath, fn)


class TestNoSecondAllowlistEntry(unittest.TestCase):
    def test_no_forbidden_flag_anywhere(self):
        hits = []
        for path in _walk_sources():
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for word in FORBIDDEN:
                if word in text:
                    # 本测试文件自身会提到这些词，跳过自己
                    if os.path.abspath(path) == os.path.abspath(__file__):
                        continue
                    hits.append("%s: %s" % (os.path.relpath(path, ROOT), word))
        self.assertEqual(hits, [], "出现第二处层白名单入口：%s" % hits)

    def test_workflow_has_single_layer_input(self):
        wf = os.path.join(ROOT, ".github", "workflows", "collect-full.yml")
        text = open(wf, encoding="utf-8").read()
        block = text.split("on:", 1)[1].split("\npermissions:", 1)[0]
        names = re.findall(r"^\s{6}([a-zA-Z0-9_]+):", block, re.M)
        # 只看「能塞层 id 的输入」：名字以 layers 结尾（layer_timeout 是墙钟，不是白名单）
        layer_inputs = [n for n in names if n.lower().endswith("layers")]
        self.assertEqual(layer_inputs, ["force_layers"],
                         "workflow 里出现了第二个放行层的入口：%s" % layer_inputs)

    def test_full_plan_single_flag_and_single_merge_point(self):
        src = open(os.path.join(COLLECT, "full_plan.py"), encoding="utf-8").read()
        self.assertEqual(src.count('add_argument("--force-layers"'), 1)
        self.assertEqual(src.count("def resolve_allowlist("), 1)
        self.assertEqual(src.count("= resolve_allowlist(a."), 1,
                         "resolve_allowlist 必须是唯一的合并点（定义 1 + 调用 1）")
        self.assertIn("唯一来源", src)
        self.assertIn('LAYERS_ALLOWLIST_SOURCE = "force_layers"', src)

    def test_runtime_rejects_extra_channel(self):
        allow = FP.resolve_allowlist("a,b", "c")
        self.assertEqual(allow["source"], "force_layers")
        self.assertEqual(allow["forced"], ["a", "b"])
        self.assertEqual(allow["forced_unstable"], ["c"])
        with self.assertRaises(TypeError):
            FP.resolve_allowlist("a", "", only_layers="x")     # 第二条入口扩不出来


if __name__ == "__main__":
    unittest.main()
