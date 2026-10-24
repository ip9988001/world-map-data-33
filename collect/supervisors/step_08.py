#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 08 的工头 —— 去重与真实地址数

本文件只剩一个身份：步号。参数/证据/话术全部从 collect/steps.json 读。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import supervisor as core  # noqa: E402

PROFILE = core.profile_of("08")


def run(dry=False):
    return core.patrol_step(PROFILE, dry=dry)


if __name__ == "__main__":
    raise SystemExit(run("--dry-run" in sys.argv))
