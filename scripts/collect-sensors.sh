#!/usr/bin/env bash
# System Sensor Layer — 采集运行事实数据
# 原则: append only, 时间戳, 不修改历史, 不影响主流程
# 周期: 每小时 (与 LCO 同步)
set -euo pipefail

BASE="$HOME/.openclaw/workspace/memory/data/system"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── 1. 系统健康 ──
LOAD=$(cat /proc/loadavg | awk '{printf "%.2f %.2f %.2f", $1, $2, $3}')
MEM=$(free -m | awk 'NR==2 {print $3}')
DISK=$(df / | awk 'NR==2 {printf "%s %s", $5, $3/1024/1024}')
DISK_PCT=$(echo "$DISK" | cut -d' ' -f1)
DISK_GB=$(echo "$DISK" | awk '{printf "%.1f", $2}')
CPU_IDLE=$(top -bn1 2>/dev/null | awk '/Cpu/ {print $8}' | cut -d',' -f1 || echo "?")
CPU_USED=$(awk "BEGIN {printf \"%.0f\", 100 - ${CPU_IDLE:-0}}")

echo "{\"ts\":\"$TS\",\"metric\":\"system_health\",\"cpu_pct\":$CPU_USED,\"mem_mb\":$MEM,\"disk_pct\":\"$DISK_PCT\",\"disk_gb\":$DISK_GB,\"load\":\"$LOAD\"}" >> "$BASE/system-health.jsonl"

# ── 2. 服务状态 ──
# openclaw is user service, ollama is system service
STATUS_GW=$(systemctl --user is-active openclaw-gateway 2>/dev/null || echo "unknown")
RESTART_GW=$(systemctl --user show openclaw-gateway -p NRestarts --value 2>/dev/null || echo "0")
STATUS_OL=$(systemctl is-active ollama 2>/dev/null || echo "unknown")
RESTART_OL=$(systemctl show ollama -p NRestarts --value 2>/dev/null || echo "0")
echo "{\"ts\":\"$TS\",\"metric\":\"service_state\",\"service\":\"openclaw-gateway\",\"status\":\"$STATUS_GW\",\"restarts\":$RESTART_GW}" >> "$BASE/service-state.jsonl"
echo "{\"ts\":\"$TS\",\"metric\":\"service_state\",\"service\":\"ollama\",\"status\":\"$STATUS_OL\",\"restarts\":$RESTART_OL}" >> "$BASE/service-state.jsonl"

# ── 3. 记忆系统快照 ──
WS="$HOME/.openclaw/workspace"
MEM_FILES=$(find "$WS/memory" -name "*.md" 2>/dev/null | wc -l)
MEM_SIZE=$(du -sb "$WS/memory" 2>/dev/null | awk '{print $1}' || echo 0)
MEM_SIZE_KB=$(( MEM_SIZE / 1024 ))
MEM_KB_TOTAL=0
if [ -f "$WS/MEMORY.md" ]; then
  MEM_KB=$(wc -c < "$WS/MEMORY.md" 2>/dev/null || echo 0)
  MEM_KB_TOTAL=$(( MEM_KB / 1024 ))
fi
# Track oldest/newest daily files to detect accumulation
NEWEST_DAYS="-"
OLDEST_DAYS="-"
if [ -d "$WS/memory" ]; then
  DAILY_FILES=$(find "$WS/memory" -name "????-??-??*.md" 2>/dev/null)
  if [ -n "$DAILY_FILES" ]; then
    NEWEST_DAYS=$(echo "$DAILY_FILES" | sort | tail -1 | xargs basename 2>/dev/null | cut -d'.' -f1)
    OLDEST_DAYS=$(echo "$DAILY_FILES" | sort | head -1 | xargs basename 2>/dev/null | cut -d'.' -f1)
  fi
fi
echo "{\"ts\":\"$TS\",\"metric\":\"memory_snapshot\",\"mem_file_count\":$MEM_FILES,\"mem_dir_kb\":$MEM_SIZE_KB,\"mem_md_kb\":$MEM_KB_TOTAL,\"oldest_day\":\"$OLDEST_DAYS\",\"newest_day\":\"$NEWEST_DAYS\"}" >> "$BASE/memory-snapshot.jsonl"
