#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 10 专属工人入口 —— 宗地地址扩采

本文件只声明「这一步的身份」；选层/循环/分片/Release 上传全在 worker_core.py + pilot.py，
参数在 steps.json。选层清单不是 layer_plan.csv（Polygon 层在 STEP-01 就被几何白名单 skip 了），
由 steps.json#steps.10.select.file 指向 collect/batch1.csv，url 从 situs_layers.csv 补。

用法（与其它步完全一致）:
  python3 collect/run_step_10.py --validate
  python3 collect/run_step_10.py --list-matrix --offset 0 --size 40
  python3 collect/run_step_10.py --layer <id>              # matrix 单层直跑
  python3 collect/run_step_10.py --offset 0 --size 40      # 本机小批调试（≤5 层）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli(step="10"))
