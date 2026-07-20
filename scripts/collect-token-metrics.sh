#!/usr/bin/env bash
# Token Metrics Collector v1.2 — 每小时采集 Token 状态 + 配置快照
# Output: memory/data/system/token-metrics.jsonl (append-only)
# 不修改运行状态，只记录观测数据
set -euo pipefail

BASE="$HOME/.openclaw/workspace"
OUTFILE="$BASE/memory/data/system/token-metrics.jsonl"
TS=$(TZ='Asia/Shanghai' date +"%Y-%m-%dT%H:%M:%S%z")
CONFIG="/home/dragonfive/.openclaw/openclaw.json"

mkdir -p "$(dirname "$OUTFILE")"

# 1. 读取配置快照到临时文件
CONFIG_TMP=$(mktemp)
python3 -c "
import json
try:
    with open('$CONFIG') as f:
        cfg = json.load(f)
    defaults = cfg.get('agents', {}).get('defaults', {})
    pruning = defaults.get('contextPruning', {})
    compaction = defaults.get('compaction', {})
    agent_model = defaults.get('model', {})
    primary_model = agent_model.get('primary', '')
    print(json.dumps({
        'contextPruning': {
            'mode': pruning.get('mode'),
            'softTrimRatio': pruning.get('softTrimRatio'),
            'hardClearRatio': pruning.get('hardClearRatio'),
            'keepLastAssistants': pruning.get('keepLastAssistants'),
        },
        'compaction': {
            'maxActiveTranscriptBytes': str(compaction.get('maxActiveTranscriptBytes','')),
            'keepRecentTokens': compaction.get('keepRecentTokens'),
            'reserveTokensFloor': compaction.get('reserveTokensFloor'),
            'maxHistoryShare': compaction.get('maxHistoryShare'),
            'truncateAfterCompaction': compaction.get('truncateAfterCompaction'),
        },
        'agent_default_model': primary_model,
    }))
except Exception as e:
    print(json.dumps({'error': str(e)}))
" > "$CONFIG_TMP" 2>/dev/null

# 2. 采集 runtime 指标
STATUS=$(openclaw status --json 2>/dev/null || echo "")

if [ -z "$STATUS" ]; then
  CONFIG_JSON=$(cat "$CONFIG_TMP")
  echo "{\"ts\":\"$TS\",\"metrics\":{},\"config\":$CONFIG_JSON,\"error\":\"status_unavailable\"}" >> "$OUTFILE"
  rm -f "$CONFIG_TMP"
  exit 0
fi

# 3. 合并指标和配置快照
CONFIG_JSON=$(cat "$CONFIG_TMP")
echo "$STATUS" | python3 -c "
import sys, json

CONFIG_SNAPSHOT = '''$CONFIG_JSON'''  # 由 shell 注入

try:
    root = json.loads(sys.stdin.read())
except:
    print(json.dumps({'ts':'0','error':'parse_failed'}))
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
weighted_pct_sum = 0.0
weight_sum = 0.0
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
    ctx = s.get('contextTokens', 1) or 1
    agent = 'unknown'
    key = s.get('key', '')
    if ':' in key:
        parts = key.split(':')
        agent = parts[1] if len(parts) > 1 else 'unknown'

    sum_input += inp
    sum_output += out
    sum_cache_read += cr
    sum_cache_write += cw
    sum_total += tt
    max_pct = max(max_pct, pct)
    weighted_pct_sum += pct * ctx
    weight_sum += ctx

    by_agent.setdefault(agent, {'sessions':0,'input':0,'output':0,'cache_read':0,'cache_write':0})
    by_agent[agent]['sessions'] += 1
    by_agent[agent]['input'] += inp
    by_agent[agent]['output'] += out
    by_agent[agent]['cache_read'] += cr
    by_agent[agent]['cache_write'] += cw

avg_pct = round(weighted_pct_sum / max(weight_sum, 1), 2) if weight_sum else 0

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
    'agents': by_agent,
    'config': json.loads(CONFIG_SNAPSHOT),
}

print(json.dumps(record, ensure_ascii=False))
" >> "$OUTFILE" 2>/dev/null

rm -f "$CONFIG_TMP"

# 4. Rotate: keep 10080 entries (7 days)
LINES=$(wc -l < "$OUTFILE" 2>/dev/null || echo 0)
if [ "$LINES" -gt 11000 ]; then
    tail -n 10080 "$OUTFILE" > "$OUTFILE.tmp" && mv "$OUTFILE.tmp" "$OUTFILE"
fi
