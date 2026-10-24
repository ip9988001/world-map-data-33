#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 05 的工头 —— 县市碎片

本文件只声明「这一步的差异」（卡死阈值 / 叫醒话术 / 建议命令）；
看活 run、打包证据、开 Issue、暂停闸门这些机械部分全在 ../supervisor.py。

改这一步的行为 → 只改这个文件。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import supervisor as core  # noqa: E402

PROFILE = {
    "step": "05",
    "title": "县市碎片",
    "stall_min": 300,              # 超过这么久没结束 → 只报告，不判死
    "evidence": ["recent_runs","releases","checkpoint"],
    "wake_reason": "县市碎片：工人已停手，等大脑判验收",
    "cmds": ['--review pass --next 06', '--kick 05 --offset <N> --size 40'],
}


def run(dry=False):
    return core.patrol_step(PROFILE, dry=dry)


if __name__ == "__main__":
    raise SystemExit(run("--dry-run" in sys.argv))
