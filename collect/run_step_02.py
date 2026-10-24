#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 02 专属工人入口 —— 试点 8 层

本文件只声明「这一步的差异」；机械部分在 worker_core.py。
带 --layer 时直接进 pilot.main()，现有 matrix workflow 零改动。

用法:
  python3 collect/run_step_02.py --layer nysam --workers 8   # matrix 模式（每层一个 job）
  python3 collect/run_step_02.py --dry-run                    # 列出 8 层
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import run  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run("02"))
