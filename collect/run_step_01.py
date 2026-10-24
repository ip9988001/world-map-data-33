#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 01 专属工人入口 —— 预检：给全量图层体检，产出 layer_plan.csv

本文件只声明「这一步的差异」；选层/循环/汇总等机械部分在 worker_core.py。
policy 默认值见 worker_core.DEFAULTS["01"]，C 阶段会迁到 collect/steps.json#$s。

用法:
  python3 collect/run_step_01.py --workers 4 --unit-rows 500000
  python3 collect/run_step_01.py --dry-run --max-layers 5     # 只列选中哪些层
  python3 collect/run_step_01.py --layer <id>                 # 单层直跑（兼容 matrix）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli(step="01"))
