#!/usr/bin/env bash
# Token Metrics Collector v1.1 — 每小时采集 Token 状态
# Output: memory/data/system/token-metrics.jsonl (append-only)
# 不修改运行状态，只记录观测数据
set -euo pipefail

BASE="$HOME/.openclaw/workspace"
OUTFILE="$BASE/memory/data/system/token-metrics.jsonl"
TS=$(TZ='Asia/Shanghai' date +"%Y-%m-%dT%H:%M:%S%z")

mkdir -p "$(dirname "$OUTFILE")"

STATUS=$(openclaw status --json 2>/dev/null || echo "")
if [ -z "$STATUS" ]; then
  echo "{\"ts\":\"$TS\",\"error\":\"status_unavailable\"}" >> "$OUTFILE"
  exit 0
fi

python3 -c "
import sys, json

try:
    root = json.loads(sys.stdin.read())
except:
    print(json.dumps({'ts':'$TS','error':'parse_failed'}))
    sys.exit(0)

sessions = root.get('sessions', {})
if isinstance(sessions, dict):
    recent = sessions.get('recent', [])
elif isinstance(sessions, list):
    recent = sessions
else:
    recent = []

total = len(recent)
sum_input = sum_output = sum_cache_read = sum_cache_write = sum_total = 0
max_pct = 0.0
ctx_sum = 0.0
by_agent = {}

for s in recent:
    if not isinstance(s, dict):
        continue
    inp = s.get('inputTokens', 0) or 0
    out = s.get('outputTokens', 0) or 0
    cr = s.get('cacheRead', 0) or 0
    cw = s.get('cacheWrite', 0) or 0
    tt = s.get('totalTokens', 0) or 0
    pct = s.get('percentUsed', 0) or 0
    ctx = s.get('contextTokens', 0) or 0
    agent = s.get('agentId', s.get('key', 'unknown')).split(':')[0] if s.get('key') else 'unknown'

    sum_input += inp
    sum_output += out
    sum_cache_read += cr
    sum_cache_write += cw
    sum_total += tt
    max_pct = max(max_pct, pct)
    ctx_sum += ctx

    by_agent.setdefault(agent, {'sessions':0,'input':0,'output':0,'cache_read':0})
    by_agent[agent]['sessions'] += 1
    by_agent[agent]['input'] += inp
    by_agent[agent]['output'] += out
    by_agent[agent]['cache_read'] += cr

# avg pct: weighted by context window
avg_pct = round(sum((s.get('percentUsed',0) or 0) * (s.get('contextTokens',1) or 1) for s in recent if isinstance(s,dict)) / max(ctx_sum, 1), 2) if ctx_sum else 0

record = {
    'ts': '$TS',
    'sessions': total,
    'total_tokens': sum_total,
    'input_tokens': sum_input,
    'output_tokens': sum_output,
    'cache_read_tokens': sum_cache_read,
    'cache_write_tokens': sum_cache_write,
    'cache_efficiency': round(sum_cache_read / max(sum_input + sum_output, 1), 4),
    'avg_context_pct': avg_pct,
    'max_context_pct': max_pct,
    'agents': {k: v for k, v in by_agent.items()},
}

print(json.dumps(record, ensure_ascii=False))
" <<< "$STATUS" >> "$OUTFILE" 2>/dev/null

# Rotate: keep 7 days (10080 entries at 1/hour)
LINES=$(wc -l < "$OUTFILE" 2>/dev/null || echo 0)
if [ "$LINES" -gt 11000 ]; then
    tail -n 10080 "$OUTFILE" > "$OUTFILE.tmp" && mv "$OUTFILE.tmp" "$OUTFILE"
fi
