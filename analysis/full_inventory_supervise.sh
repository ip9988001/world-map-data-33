#!/usr/bin/env bash
# Phase 3 看门狗（只用 analysis/full-inventory-* 产物；不改采集语义）
#   每 60s 检查一次：
#     1) 探测进程不存在            → append 日志 + 重新拉起（续跑靠 shards，不重采）
#     2) 进程在但 progress.json 心跳 >10min 未更新 → 判卡死，kill + 重新拉起
#     3) phase3_live.done >= total → 计划跑完，退出
#   最多重启 24 次；每次重启留痕到 supervisor.log
set -u
REPO=/data/workspace/wmd-inv24
D=$REPO/analysis/full-inventory-20261124
LOG=$D/inventory-remote-uncollected.run.log
SL=$D/inventory-remote-uncollected.supervisor.log
PAT='^python3 -u analysis/full_inventory_remote\.py'
STALL=600
MAX=24
restarts=0
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) supervisor start pid=$$ pattern=$PAT stall=${STALL}s max_restarts=$MAX" >>"$SL"

prog() {
  python3 - "$REPO/progress.json" <<'PY' 2>/dev/null
import json, sys, time
try:
    d = (json.load(open(sys.argv[1], encoding="utf-8")).get("phase3_live") or {})
except Exception:
    d = {}
ts = d.get("updated_at") or ""
age = -1
try:
    age = int(time.time() - time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone)
except Exception:
    pass
print(int(d.get("done", 0)), int(d.get("total", 0)), age)
PY
}

while :; do
  sleep 60
  alive=0
  if pgrep -f "$PAT" >/dev/null; then alive=1; fi
  read -r done total age <<<"$(prog)"
  done=${done:-0}; total=${total:-0}; age=${age:--1}

  if [ "$total" -gt 0 ] && [ "$done" -ge "$total" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) plan complete done=$done total=$total -> supervisor exit" >>"$SL"
    break
  fi

  reason=""
  if [ "$alive" = 0 ]; then
    reason="dead"
  elif [ "$age" -gt "$STALL" ]; then
    reason="stalled(heartbeat_age=${age}s)"
    pkill -f "$PAT" && echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) killed stalled pid(s)" >>"$SL"
    sleep 5
  fi
  [ -z "$reason" ] && continue

  restarts=$((restarts + 1))
  if [ "$restarts" -gt "$MAX" ]; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) give up: $restarts > $MAX restarts" >>"$SL"
    break
  fi
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) restart #$restarts reason=$reason done=$done/$total" >>"$SL"
  echo "=== supervisor restart #$restarts $(date -u +%Y-%m-%dT%H:%M:%SZ) reason=$reason ===" >>"$LOG"
  cd "$REPO" && setsid --fork nohup python3 -u analysis/full_inventory_remote.py \
      --concurrency 8 >>"$LOG" 2>&1 </dev/null
  sleep 20
done
