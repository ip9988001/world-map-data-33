#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 04b 专属工人入口 —— 全量补采（与 step04 共用引擎，差异只在 steps.json 的 select）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli(step="04b"))
