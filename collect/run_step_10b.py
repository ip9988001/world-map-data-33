#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 10b 专属工人入口 —— 宗地面层 batch2+（batch1 之外的强/弱等级层）。

与 step10 的唯一差异在 steps.json：layer 清单从 batch1.csv 换成 situs_layers.csv，
且 skip_done=true（batch1 已采的 1,261 层自动剔除）。执行机制完全复用 worker_core。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli(step="10b"))
