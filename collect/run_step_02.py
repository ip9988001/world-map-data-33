#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 02 专属工人 —— 8 层试点采集入口

自研模式 v2 §8：**每步一个脚本**，不让一个脚本扛所有步。
本文件只管「STEP 02 该干什么」，采集引擎仍在 pilot.py；
哪天 STEP 03 要完全不同的逻辑，直接新建 run_step_03.py，改它不会碰到这里。

用法:
  python3 collect/run_step_02.py --layer nysam --workers 8
  python3 collect/run_step_02.py --list
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pilot  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(pilot.main())
