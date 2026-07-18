#!/usr/bin/env bash
# Local Capability Observer v1 — qwen2.5:3b 能力观测
# 职责: 定期测试本地模型能力，记录真实指标，提供分流依据
# 禁止: 自动切换模型、修改路由、影响生产请求
# Output: events/huo/ollama-eval.jsonl

set -euo pipefail

MODEL="qwen2.5:3b"
LOGFILE="$HOME/.openclaw/workspace/memory/events/huo/ollama-eval.jsonl"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

TASKS=(
  '{"type":"short_qa","prompt":"用一句话解释什么是DNS。"}'
  '{"type":"explain","prompt":"解释一下Linux的grep命令是做什么的，一句话。"}'
  '{"type":"format","prompt":"把这行json格式化输出：{\"name\":\"test\",\"value\":123}"}'
  '{"type":"summarize","prompt":"总结这句话：服务器CPU使用率持续85%以上，内存占用70%，磁盘IO等待时间增加，建议扩容。"}'
  '{"type":"report","prompt":"用一句话描述当前状态：服务运行正常，最近5分钟无错误日志。"}'
)

ollama_pid() {
  pgrep -x ollama || echo ""
}

for task in "${TASKS[@]}"; do
  TYPE=$(echo "$task" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
  PROMPT=$(echo "$task" | python3 -c "import sys,json; print(json.load(sys.stdin)['prompt'])")

  # Start resource monitor (sample every 2s)
  MONITOR_PID=""
  OLLAMA_PID=$(ollama_pid)
  CPU_PEAK=0
  MEM_PEAK=0
  if [ -n "$OLLAMA_PID" ]; then
    (
      while true; do
        STAT=$(ps -p "$OLLAMA_PID" -o %cpu=,rss= 2>/dev/null) || break
        CPU=$(echo "$STAT" | awk '{print int($1)}')
        MEM=$(echo "$STAT" | awk '{print int($2/1024)}')  # KB → MB
        [ "$CPU" -gt "$CPU_PEAK" ] && CPU_PEAK=$CPU
        [ "$MEM" -gt "$MEM_PEAK" ] && MEM_PEAK=$MEM
        echo "RES:${CPU_PEAK}:${MEM_PEAK}" > /tmp/ollama-res-$$.tmp
        sleep 1
      done
    ) &
    MONITOR_PID=$!
  fi

  # Execute task via REST API (get token counts)
  START=$(date +%s%N)
  API_RESP=$(curl -s http://localhost:11434/api/generate \
    -d "{\"model\":\"$MODEL\",\"prompt\":\"$PROMPT\",\"stream\":false}" 2>/dev/null || echo '{"error":"API call failed"}')
  END=$(date +%s%N)
  LATENCY_MS=$(( (END - START) / 1000000 ))

  OUTPUT=$(echo "$API_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','ERROR: empty response'))" 2>/dev/null || echo "ERROR: parse failed")
  INPUT_TOKENS=$(echo "$API_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt_eval_count',0))" 2>/dev/null || echo 0)
  OUTPUT_TOKENS=$(echo "$API_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('eval_count',0))" 2>/dev/null || echo 0)

  # Stop monitor
  [ -n "$MONITOR_PID" ] && kill "$MONITOR_PID" 2>/dev/null || true
  if [ -f "/tmp/ollama-res-$$.tmp" ]; then
    read -r CPU_PEAK MEM_PEAK <<< "$(tail -1 /tmp/ollama-res-$$.tmp | tr ':' ' ' | cut -d' ' -f2,3)"
    rm -f "/tmp/ollama-res-$$.tmp"
  fi
  CPU_PEAK=${CPU_PEAK:-0}
  MEM_PEAK=${MEM_PEAK:-0}

  # Quality check
  if echo "$OUTPUT" | grep -q "^ERROR"; then
    SUCCESS=false
    QUALITY="fail"
  else
    SUCCESS=true
    QUALITY="pass"
  fi

  TOTAL_TOKENS=$(( INPUT_TOKENS + OUTPUT_TOKENS ))

  # Log (added token fields)
  echo "{\"timestamp\":\"$TIMESTAMP\",\"model\":\"$MODEL\",\"task\":\"$TYPE\",\"latency_ms\":$LATENCY_MS,\"input_tokens\":$INPUT_TOKENS,\"output_tokens\":$OUTPUT_TOKENS,\"total_tokens\":$TOTAL_TOKENS,\"success\":$SUCCESS,\"quality\":\"$QUALITY\",\"output_length\":${#OUTPUT},\"cpu_peak_pct\":$CPU_PEAK,\"mem_peak_mb\":$MEM_PEAK}" >> "$LOGFILE"
done

echo "[$(date)] LCO: 5 tasks logged" >> /dev/null
