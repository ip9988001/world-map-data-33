#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 04b 的工头 —— 全量补采变体（与基础步共用执行引擎，差异只在 steps.json 的 select）

本文件只剩一个身份：步号。
卡死阈值 / 叫醒话术 / 建议命令 / 要收哪些证据 / 判据卡 —— 全部从
collect/steps.json 的 supervise 块读。改参数请改那一处，不要改这里。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import supervisor as core  # noqa: E402

PROFILE = core.profile_of("04b")


def run(dry=False):
    return core.patrol_step(PROFILE, dry=dry)


if __name__ == "__main__":
    raise SystemExit(run("--dry-run" in sys.argv))
