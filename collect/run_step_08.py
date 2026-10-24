#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 08 专属工人入口 —— 去重与真实地址数

本文件只声明「这一步的身份」；选层/循环/汇总全在 worker_core.py，参数在 steps.json。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worker_core import cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(cli(step="08"))
