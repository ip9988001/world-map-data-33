#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 02 的工头 —— 试点 8 层

本文件只声明「这一步的差异」（卡死阈值 / 叫醒话术 / 建议命令）；
看活 run、打包证据、开 Issue、暂停闸门这些机械部分全在 ../supervisor.py。

改这一步的行为 → 只改这个文件。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import supervisor as core  # noqa: E402

PROFILE = {
    "step": "02",
    "title": "试点 8 层",
    "stall_min": 150,              # 超过这么久没结束 → 只报告，不判死
    "evidence": ["report","releases","checkpoint","short_units"],
    "wake_reason": "试点 8 层：工人已停手，等大脑判验收",
    "cmds": ['--review pass --next 03', '--kick 02 --layers <缺口层> --workers 4'],
}


def run(dry=False):
    return core.patrol_step(PROFILE, dry=dry)


if __name__ == "__main__":
    raise SystemExit(run("--dry-run" in sys.argv))
