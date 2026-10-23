#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DS 余额守护：低于 ¥5 连续推 3 次企微提醒充值。

为什么放本机 cron：pi 用的是这个 key，余额耗尽 = 我直接失能，
           必须有**不依赖我**的东西盯着，光靠我自己查是悖论。

规则
  balance < 5.0  → 每轮最多推 1 次，累计推 3 次后静默
  balance >= 5.0 → 计数清零（下次再低会重新推 3 次）
状态：ops/.ds_balance_state.json
用法：python3 ops/ds_balance.py [--dry] [--simulate 3.5]
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, urllib.request
from datetime import datetime

ENVF = "/root/.pi/secrets/mapdata-xiaoxin.env"
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, ".ds_balance_state.json")
SEND = "/root/pi-work/sentinel-bot/send_once.mjs"
THRESHOLD = 5.0
MAX_PUSH = 3


def load_key():
    key = os.environ.get("LLM_API_KEY", "")
    if key:
        return key
    if os.path.exists(ENVF):
        for line in open(ENVF, encoding="utf-8"):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("LLM_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def fetch(key):
    req = urllib.request.Request("https://api.deepseek.com/user/balance",
                                 headers={"Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.loads(r.read().decode())
    b = (d.get("balance_infos") or [{}])[0]
    return {"available": d.get("is_available"),
            "total": float(b.get("total_balance") or 0),
            "granted": float(b.get("granted_balance") or 0),
            "topped": float(b.get("topped_up_balance") or 0)}


def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"pushed": 0, "last_check": None, "last_balance": None}


def save_state(s):
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def push(body, dry=False):
    if dry:
        print("[dry] 本该推送：\n" + body)
        return True
    p = subprocess.run(["node", SEND, body], capture_output=True, text=True, timeout=90)
    ok = p.returncode == 0 and "已推送" in (p.stdout or "")
    print(("[推送成功] " if ok else "[推送失败] ") + (p.stdout or p.stderr or "")[-160:])
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--simulate", type=float, help="用假余额测试")
    a = ap.parse_args()

    st = load_state()
    if a.simulate is not None:
        info = {"available": True, "total": a.simulate, "granted": 0.0, "topped": a.simulate}
        key = "simulated"
    else:
        key = load_key()
        if not key:
            print("❌ 找不到 LLM_API_KEY，无法查余额")
            return 2
        try:
            info = fetch(key)
        except Exception as e:
            print("❌ 查询失败:", e)
            return 2

    st["last_check"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    st["last_balance"] = info["total"]

    if info["total"] >= THRESHOLD:
        if st.get("pushed"):
            print("✅ 余额已恢复 ≥%.0f，告警计数清零" % THRESHOLD)
        st["pushed"] = 0
        save_state(st)
        print("✅ DS 余额 ¥%.2f（赠送 %.2f / 充值 %.2f）≥ %.0f，无需提醒"
              % (info["total"], info["granted"], info["topped"], THRESHOLD))
        return 0

    n = st.get("pushed", 0)
    if n >= MAX_PUSH:
        save_state(st)
        print("🔇 余额 ¥%.2f 仍低于 %.0f，但已推满 %d 次，静默（充值后自动复位）"
              % (info["total"], THRESHOLD, MAX_PUSH))
        return 0

    n += 1
    body = (
        "【余额告警】DS 账户余额不足，第 %d/3 次提醒\n\n"
        "■ 当前余额：¥%.2f（赠送 ¥%.2f · 充值 ¥%.2f）\n"
        "■ 阈值：¥%.0f —— 低于此线我会直接失能，所有自研模式的活都会停\n"
        "■ 时间：%s\n\n"
        "■ 请去 https://platform.deepseek.com/top_up 充值。\n"
        "■ 充完这个提醒会自动停；没充我会再推，最多推 3 次就不再打扰。"
        % (n, info["total"], info["granted"], info["topped"], THRESHOLD,
           datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    )
    if push(body, a.dry):
        st["pushed"] = n
    save_state(st)
    print("⚠️ 余额 ¥%.2f < %.0f，已推 %d/%d 次" % (info["total"], THRESHOLD, st["pushed"], MAX_PUSH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
