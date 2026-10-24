#!/usr/bin/env bash
# 三仓改造进度看门狗 —— 独立于 AI 会话，专治「卡死了没人知道」
# 由本机 cron 每 10 分钟跑一次；只在异常态推送，正常态不打扰。
set -u
P=/root/pi-work/world-map-data-33/ops/progress.json
SEND=/root/pi-work/sentinel-bot/send_once.mjs
ST=/root/pi-work/world-map-data-33/ops/.beacon_state
NODE=$(command -v node || echo /usr/bin/node)
[ -f "$P" ] || exit 0
read -r STATUS SUB STEP TS ETA <<<"$(python3 - <<PY
import json
d=json.load(open("$P"))
print(d.get("status",""), d.get("sub",""), d.get("step",""), d.get("ts",""), d.get("eta_left_min",""))
PY
)"
AGE=$(python3 - "$TS" <<'PY'
import sys, datetime
try:
    t = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    print(int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60))
except Exception:
    print(9999)
PY
)
LAST=$(cat "$ST" 2>/dev/null || echo "")
KEY="$STATUS|$SUB|$AGE"
case "$STATUS" in
  working)
    if [ "$AGE" -ge 25 ] && [ "${LAST%%|*}" != "warned:$SUB" ]; then
      printf '⚠️ 三仓改造疑似卡死\n\n最后完成：%s / %s\n已静默：%s 分钟\n本大步原本还剩：%s 分钟\n\n→ 需要你看一眼（或回一句「继续」我接着来）' \
        "$STEP" "$SUB" "$AGE" "$ETA" | "$NODE" "$SEND" --stdin
      echo "warned:$SUB" > "$ST"
    fi ;;
  failed)
    if [ "$LAST" != "failed:$SUB" ]; then
      printf '❌ 三仓改造报错停下\n\n停在：%s / %s\n已静默：%s 分钟\n→ 详情在 ops/progress.json' "$STEP" "$SUB" "$AGE" | "$NODE" "$SEND" --stdin
      echo "failed:$SUB" > "$ST"
    fi ;;
  awaiting_confirm)
    if [ "$AGE" -ge 60 ] && [ "$LAST" != "await:$SUB" ]; then
      printf '⏳ 三仓改造在等你确认\n\n已完成：%s 大步（停在 %s，%s 分钟前）\n→ 回一句「继续」我就往下走' "$STEP" "$SUB" "$AGE" | "$NODE" "$SEND" --stdin
      echo "await:$SUB" > "$ST"
    fi ;;
esac
