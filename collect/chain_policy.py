#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接续策略（唯一真值）—— 「停在哪」写成代码，不靠人盯。

背景：`collect-full.yml` 的 merge 末尾会自动 `gh workflow run` 下一阶段。原先是
`case "$STAGE" in 04b) NEXT=05b ;; 05b) NEXT=07b ;; 07b) NEXT=10b ;; esac`，
且接续那行**硬编码 `-f chain=1`**。两处叠加的效果：07b 全绿 → 自动派 10b（宗地
8,116 层 / 20~85 GB）→ 10b 绿了还想再往下。而现行口径是「点类 04b→05b→07b 采完就停」，
10b / 08 / 09 / 几何全部等口令。

所以这里把三件事钉死，workflow 只做「读结论 + 执行」：

  ① NEXT        04b→05b→07b，**07b 之后是空**（断链点）
  ② ALLOWED     允许接续进的目标阶段清单，只放 05b / 07b
                 —— 于是即便以后有人手滑把 NEXT 写回 10b，也会被这一步拦下
  ③ CHILD_CHAIN 接续出去的子 run 拿到的 chain 值，默认 **0**（单跳）
                 —— 04b→05b 的子 run 不会自己再往下接 07b，每跳都要人review

用法：
  python3 collect/chain_policy.py --stage 07b                     # 看结论
  python3 collect/chain_policy.py --stage 05b --chain 1 --dry-run  # 打印将 dispatch 的命令
  python3 collect/chain_policy.py --all --dry-run                  # 四阶段全表自证
  python3 collect/chain_policy.py --stage 04b --chain 1 --write-env /tmp/chain.env
"""
from __future__ import annotations

import argparse
import json
import sys

STAGES = ("04b", "05b", "07b", "10b")

# ① 接续表：**唯一真值**。07b 之后空 = 到此为止（08/09/10b/几何一律等口号）
NEXT = {
    "04b": "05b",
    "05b": "07b",
    "07b": "",        # ← 断链点：采完就停，不接 10b
    "10b": "",        # 10b 是终点（且派发前另有 authorize_heavy 闸门）
}

# ② 允许清单：只允许接续进这两个阶段
ALLOWED = ("05b", "07b")

# ③ 接续出去的子 run 的 chain 值（按阶段配置；默认 0 = 单跳，不级联）
CHILD_CHAIN = {
    "04b": "0",
    "05b": "0",
    "07b": "0",
    "10b": "0",
}

# 重阶段：默认关闭，必须显式授权（宗地 8,116 层 / 20~85 GB）
HEAVY = ("10b",)


def decide(stage: str, chain_input: str = "1") -> dict:
    """返回本阶段该不该接续、接到哪、子 run 的 chain 值。"""
    stage = (stage or "").strip()
    nxt = NEXT.get(stage, "")
    child = CHILD_CHAIN.get(stage, "0")
    if stage not in NEXT:
        return {"stage": stage, "next": "", "child_chain": child,
                "decide": "stop", "reason": "unknown_stage"}
    if not nxt:
        return {"stage": stage, "next": "", "child_chain": child,
                "decide": "stop", "reason": "no_next_stage"}
    if nxt not in ALLOWED:
        return {"stage": stage, "next": nxt, "child_chain": child,
                "decide": "stop", "reason": "next_not_in_allowlist"}
    if str(chain_input) != "1":
        return {"stage": stage, "next": nxt, "child_chain": child,
                "decide": "stop", "reason": "chain_off"}
    return {"stage": stage, "next": nxt, "child_chain": child,
            "decide": "dispatch", "reason": "allowed"}


def dispatch_cmd(verdict: dict, repo: str = "$GITHUB_REPOSITORY") -> str:
    return ('gh workflow run collect-full.yml --repo "%s" --ref main '
            '-f stage=%s -f chain=%s -f workers=4'
            % (repo, verdict["next"], verdict["child_chain"]))


def is_heavy_authorized(stage: str, authorize_heavy: str = "0") -> bool:
    """重阶段闸门：10b 只有显式 authorize_heavy=1 才可派。"""
    if stage not in HEAVY:
        return True
    return str(authorize_heavy) == "1"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage")
    ap.add_argument("--chain", default="1", help="本阶段 run 的 chain 输入（默认按 1 预演）")
    ap.add_argument("--all", action="store_true", help="打印四阶段全表")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写 env")
    ap.add_argument("--write-env", default="", help="把结论写成 shell env 文件供 workflow source")
    a = ap.parse_args(argv)

    if a.all:
        for s in STAGES:
            v = decide(s, a.chain)
            print("[chain] stage=%-3s next=%-3s child_chain=%s decide=%-8s reason=%s"
                  % (s, v["next"] or "-", v["child_chain"], v["decide"], v["reason"]))
            if v["decide"] == "dispatch":
                print("        → DRY: " + dispatch_cmd(v, "<repo>"))
        return 0

    if not a.stage:
        print("::error::需要 --stage 或 --all", file=sys.stderr)
        return 2

    v = decide(a.stage, a.chain)
    print("[chain] stage=%-3s next=%-3s child_chain=%s decide=%-8s reason=%s"
          % (v["stage"], v["next"] or "-", v["child_chain"], v["decide"], v["reason"]))
    if v["decide"] == "dispatch":
        print("[chain] DRY 将执行：" + dispatch_cmd(v, "<repo>"))
    else:
        print("[chain] 不接续（%s）—— 到此为止，等口号" % v["reason"])

    if a.write_env:
        with open(a.write_env, "w", encoding="utf-8") as fh:
            fh.write("CHAIN_DECIDE=%s\nCHAIN_NEXT=%s\nCHAIN_CHILD_CHAIN=%s\nCHAIN_REASON=%s\n"
                     % (v["decide"], v["next"], v["child_chain"], v["reason"]))
        print("[chain] 已写 %s" % a.write_env)
    if a.dry_run:
        print("[chain] dry-run：没有派发任何 run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
