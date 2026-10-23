#!/usr/bin/env bash
# 三仓工头兜底点火器 —— 治「GitHub schedule 丢事件导致自研链路静默停摆」
#
# 背景（2026-10-23）：collect-supervisor 配 cron */10，但从 10:25 之后 3.5 小时一次没跑，
# STEP02 停在 retry 没人递活。GitHub 的 schedule 事件本身不保证送达。
# 本脚本由本机 cron 每 15 分钟跑一次：发现「该动没动」就直接 dispatch 工头。
#
# 判据（全部满足才点火）：
#   1. mode = self-drive
#   2. collapsed != true（三振收摊了就别再叫）
#   3. 当前步 status in (running, started, retry)
#   4. 近 40 分钟内没有任何 in_progress / queued 的 run（工人和工头都没在动）
set -u
REPO="ip9988001/world-map-data-33"
STATE=$(gh api "repos/$REPO/contents/collect/state.json" -q '.content' 2>/dev/null | base64 -d 2>/dev/null)
[ -z "$STATE" ] && { echo "$(date -u +%FT%TZ) SKIP 读不到 state.json"; exit 0; }

read -r MODE COLLAPSED STEP STATUS <<<"$(python3 - <<PY
import json
d=json.loads('''$STATE''')
print(d.get("mode",""), d.get("collapsed",False), d.get("current_step",""), d.get("steps",{}).get(d.get("current_step",""),{}).get("status",""))
PY
)"

[ "$MODE" != "self-drive" ] && { echo "$(date -u +%FT%TZ) SKIP 非自研模式($MODE)"; exit 0; }
[ "$COLLAPSED" = "True" ] && { echo "$(date -u +%FT%TZ) SKIP 已收摊(collapsed)"; exit 0; }
case "$STATUS" in
  running|started|retry) ;;
  *) echo "$(date -u +%FT%TZ) SKIP STEP$STEP 状态=$STATUS 不需要点火"; exit 0 ;;
esac

ALIVE=$(gh api "repos/$REPO/actions/runs?per_page=20" \
  -q '[.workflow_runs[]|select(.status=="in_progress" or .status=="queued" or .status=="pending")]|length' 2>/dev/null)
ALIVE=${ALIVE:-99}
if [ "$ALIVE" -gt 0 ]; then
  echo "$(date -u +%FT%TZ) SKIP STEP$STEP 有 $ALIVE 个活着的 run，不重复点火"
  exit 0
fi

echo "$(date -u +%FT%TZ) KICK STEP$STEP status=$STATUS 无活 run → dispatch collect-supervisor"
gh workflow run collect-supervisor.yml --repo "$REPO" 2>&1 | tail -1
