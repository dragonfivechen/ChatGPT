#!/usr/bin/env bash
# Daily System Status Report — collect facts, generate markdown report
# Output: memory/data/system/daily-report/YYYY-MM-DD.md + latest.md
# Type: oneshot, systemd timer @ 08:00 daily
set -euo pipefail

BASE="$HOME/.openclaw/workspace"
DATA_DIR="$BASE/memory/data/system/daily-report"
TEMPLATE="$DATA_DIR/daily-status-template.md"
TS=$(TZ='Asia/Shanghai' date +"%Y-%m-%d")
TS_DISPLAY=$(TZ='Asia/Shanghai' date +"%Y-%m-%d %H:%M")
ARCHIVE_DIR="$DATA_DIR/archive"
mkdir -p "$ARCHIVE_DIR"

REPORT="$ARCHIVE_DIR/${TS}.md"
LATEST="$DATA_DIR/latest.md"

echo "[daily-status] generating report for ${TS}"

# ── 1. System Status ──
GATEWAY_ACTIVE=$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || echo "unknown")
GATEWAY_PID=$(systemctl --user show openclaw-gateway.service -p MainPID --value 2>/dev/null || echo "")
OLLAMA_ACTIVE=$(systemctl is-active ollama.service 2>/dev/null || echo "unknown")
GW_UPTIME=$(systemctl --user show openclaw-gateway.service -p ActiveEnterTimestamp --value 2>/dev/null | cut -d' ' -f2-3 || echo "")
OC_VERSION=$(/usr/lib/node_modules/openclaw/dist/index.js --version 2>/dev/null | head -1 || echo "v2026.5.20")

# ── 2. Metrics: CPU / MEM / DISK ──
read -r CPU_IDLE <<< "$(top -bn1 2>/dev/null | awk '/Cpu/ {print $8}' | cut -d',' -f1 || echo "?")"
CPU_USED=$(awk "BEGIN {printf \"%.0f\", 100 - ${CPU_IDLE:-0}}" 2>/dev/null || echo "?")
MEM_TOTAL=$(free -m 2>/dev/null | awk 'NR==2 {print $2}') || echo "?"
MEM_USED=$(free -m 2>/dev/null | awk 'NR==2 {print $3}') || echo "?"
DISK_PCT=$(df / 2>/dev/null | awk 'NR==2 {print $5}') || echo "?"
LOAD=$(cat /proc/loadavg 2>/dev/null | awk '{print $1,$2,$3}') || echo "?"

# ── 3. Token Observe (past 24h) ──
TOKEN_FILE="$HOME/.openclaw/token_observe.jsonl"
TOKEN_EVENTS=0
TOKEN_TOTAL=0
if [ -f "$TOKEN_FILE" ]; then
  TOKEN_STATS=$(python3 -c "
import json
from datetime import datetime
now=$(date +%s)
cnt=0
total=0
with open('$TOKEN_FILE') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        d=json.loads(line)
        ts=d.get('timestamp','')
        try:
            ts_u=datetime.fromisoformat(ts.replace('Z','+00:00')).timestamp()
        except:
            continue
        if now - ts_u < 86400:
            cnt+=1
            total+=d.get('total_tokens_k',0)
print(f'{cnt} {total}')
" 2>/dev/null || echo "0 0")
  TOKEN_EVENTS=$(echo "$TOKEN_STATS" | awk '{print $1}')
  TOKEN_TOTAL=$(echo "$TOKEN_STATS" | awk '{print $2}')
fi

# ── 4. Events (past 24h from events/huo) ──
HUO_DIR="$BASE/memory/events/huo"
EVENT_FILES=$(find "$HUO_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
EVENT_TODAY=$(grep -c "${TS}" "$HUO_DIR/${TS}.md" 2>/dev/null || echo "0")
EVENT_EXCEPTIONS=$(grep -ci "error\|fail\|violation\|abort" "$HUO_DIR/${TS}.md" 2>/dev/null || echo "0")

# ── 5. Ollama Eval status ──
EVAL_FILE="$BASE/memory/events/huo/ollama-eval.jsonl"
EVAL_COUNT=0
EVAL_SUCCESS=0
EVAL_LATENCY=0
if [ -f "$EVAL_FILE" ]; then
  EVAL_STATS=$(python3 -c "
import json
now='$TS'
entries=[]
with open('$EVAL_FILE') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        d=json.loads(line)
        ts=d.get('timestamp','')
        if ts[:10]==now:
            entries.append(d)
total=len(entries)
succ=sum(1 for e in entries if e.get('success'))
lat=[e['latency_ms'] for e in entries if 'latency_ms' in e]
avg_lat=sum(lat)/len(lat)/1000 if lat else 0
print(f'{total} {succ} {avg_lat:.1f}')
" 2>/dev/null || echo "0 0 0")
  EVAL_COUNT=$(echo "$EVAL_STATS" | awk '{print $1}')
  EVAL_SUCCESS=$(echo "$EVAL_STATS" | awk '{print $2}')
  EVAL_LATENCY=$(echo "$EVAL_STATS" | awk '{print $3}')
fi

# ── Write Report ──
cat > "$REPORT" << EOF
# System Daily Status Report

Date: ${TS}

## 1. System Status

Version: ${OC_VERSION}
Runtime: Gateway=${GATEWAY_ACTIVE} (pid=${GATEWAY_PID}) | Ollama=${OLLAMA_ACTIVE}
Uptime: ${GW_UPTIME}
Health: CPU=${CPU_USED}% | MEM=${MEM_USED}/${MEM_TOTAL}MB | DISK=${DISK_PCT} | LOAD=${LOAD}

## 2. Completed Changes

- (auto-collected from events)

## 3. Current Observations

Running experiments:
- Local Model Eval (ollama-eval): ${EVAL_COUNT} samples today, ${EVAL_SUCCESS} success, avg ${EVAL_LATENCY}s

Monitoring items:
- Token Observe: ${TOKEN_EVENTS} data points
- Billing: oek-billing-snapshot (5min) / oek-billing-push (1h)

## 4. Metrics

CPU: ${CPU_USED}%
Memory: ${MEM_USED}MB / ${MEM_TOTAL}MB
Disk: ${DISK_PCT}
Token (24h): ${TOKEN_TOTAL}K across ${TOKEN_EVENTS} observations
Events (huo today): ${EVENT_FILES} files, ${EVENT_EXCEPTIONS} flagged entries

## 5. Exceptions

Errors:
Warnings:
Unresolved:

## 6. Architecture State

Frozen decisions:
Pending review:

## 7. Long-term Memory Candidate

Potential durable changes:
None / Details:
EOF

# Update latest.md symlink/copy
cp "$REPORT" "$LATEST"

echo "[daily-status] wrote ${TS}.md ($(wc -c < "$REPORT") bytes)"
echo "[daily-status] done"
