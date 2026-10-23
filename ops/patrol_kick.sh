#!/usr/bin/env bash
# 三仓工头兜底闹钟（v2 · 2026-10-24）
#
# v2 铁律：**点火工人只有大脑能下**。本脚本不再看 status=retry 就点火，
# 唯一职责是「保证工头活着」——工头掉了就补一脚，让工头去叫醒大脑。
# 它不看验收、不判死、不 dispatch 任何工人。
#
# 由本机 cron 每 15 分钟跑一次（GitHub schedule 事件不保证送达，双闹钟之一）。
set -u
REPO="ip9988001/world-map-data-33"
STATE=$(gh api "repos/$REPO/contents/collect/state.json" -q '.content' 2>/dev/null | base64 -d 2>/dev/null)
[ -z "$STATE" ] && { echo "$(date -u +%FT%TZ) SKIP 读不到 state.json"; exit 0; }

read -r MODE STATUS AWAIT <<<"$(python3 - <<PY
import json
d=json.loads('''$STATE''')
print(d.get("mode",""), d.get("status",""), d.get("awaiting_brain",False))
PY
)"

case "$MODE" in
  self-drive|self-drive-v2) ;;
  *) echo "$(date -u +%FT%TZ) SKIP 非自研模式($MODE)"; exit 0 ;;
esac
[ "$STATUS" = "paused" ] && { echo "$(date -u +%FT%TZ) SKIP paused（大脑按了暂停）"; exit 0; }
[ "$AWAIT" = "True" ] && echo "$(date -u +%FT%TZ) NOTE 正在等大脑判验收（工头已叫过，不重复叫）"

LAST=$(gh api "repos/$REPO/actions/workflows/collect-supervisor.yml/runs?per_page=1" \
  -q '.workflow_runs[0].created_at // ""' 2>/dev/null)
AGE=$(python3 - "$LAST" <<'PY'
import sys, datetime
try:
    t = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    print(int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() // 60))
except Exception:
    print(9999)
PY
)

if [ "${AGE:-9999}" -lt 20 ]; then
  echo "$(date -u +%FT%TZ) SKIP 工头 ${AGE} 分钟前刚跑过"
  exit 0
fi

ALIVE=$(gh api "repos/$REPO/actions/runs?per_page=20" \
  -q '[.workflow_runs[]|select(.status=="in_progress" or .status=="queued" or .status=="pending")]|length' 2>/dev/null)
if [ "${ALIVE:-0}" -gt 0 ]; then
  echo "$(date -u +%FT%TZ) SKIP 有 $ALIVE 个活着的 run（含工头自己），不重复叫"
  exit 0
fi

echo "$(date -u +%FT%TZ) KICK 工头已 ${AGE} 分钟没跑 → dispatch collect-supervisor"
gh workflow run collect-supervisor.yml --repo "$REPO" 2>&1 | tail -1
