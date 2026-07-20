#!/usr/bin/env bash
# Local Model Production Trial v1.0 — 实战任务 worker
# 职责: 将真实系统数据作为任务发送给本地模型，记录结果
# 原则: 只产生 Observation，不修改状态
# 禁止: 写入系统状态、修改配置、自动修复、治理决策
# Output: events/huo/ollama-production.jsonl

set -euo pipefail

MODEL="qwen2.5:3b"
LOGFILE="$HOME/.openclaw/workspace/memory/events/huo/ollama-production.jsonl"
DATA_DIR="$HOME/.openclaw/workspace/memory/data/system"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
CURL_TIMEOUT=120  # per-request max seconds

# ── 任务工厂：短输入，适合本地模型速度 ──

# Task 1: 系统状态简报
gen_status_brief() {
  local health_file="$DATA_DIR/system-health.jsonl"
  if [ ! -f "$health_file" ]; then
    echo '{"type":"system_status_brief","prompt":"暂无系统健康数据"}'
    return
  fi
  local recent=$(tail -1 "$health_file" 2>/dev/null | python3 -c "
import sys, json
l = json.loads(sys.stdin.read())
print(f\"cpu={l.get('cpu_pct',0)}% mem={l.get('mem_mb',0)}MB disk={l.get('disk_pct',0)}% load={l.get('load',0)}\")
" 2>/dev/null || echo "无数据")
  local prompt="一句话描述系统状态：${recent}"
  echo "{\"type\":\"system_status_brief\",\"prompt\":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 2: 事件分类（简短版）
gen_event_classify() {
  local recent=$(journalctl --since "30 min ago" --no-pager -n 5 --output=short 2>/dev/null || echo "无日志")
  local prompt="将以下系统事件分为 normal/warning/error，只输出分类：${recent}"
  echo "{\"type\":\"event_classify\",\"prompt\":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 3: 日志摘要（简短输入）
gen_log_summary() {
  local log_sample=$(journalctl --since "1 hour ago" --no-pager -n 8 --output=short 2>/dev/null || echo "获取日志失败")
  local prompt="用一句话概括最近系统日志要点：${log_sample}"
  echo "{\"type\":\"log_summary\",\"prompt\":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 4: 配置文件解释（简短片段，通过 Config Reader）
gen_config_explain() {
  local reader="$HOME/.openclaw/workspace/tools/config_source.py"
  if [ ! -f "$reader" ]; then
    echo '{"type":"config_explain","prompt":"暂无配置读取器"}'
    return
  fi
  local snippet=$(python3 -c "
import json, subprocess
r = subprocess.run(['python3', '$reader', '--key', 'models.providers'], capture_output=True, text=True)
if r.returncode != 0:
    print('获取配置失败')
else:
    d = json.loads(r.stdout)
    prov = d.get('value', {})
    out = {}
    for pid in list(prov.keys())[:1]:
        p = prov[pid]
        out[pid] = {k: p.get(k) for k in ['api','baseUrl'] if k in p}
    print(json.dumps(out, indent=2))
" 2>/dev/null || echo "获取配置失败")
  local prompt="解释以下配置项的作用（一句话）：${snippet}"
  echo "{\"type\":\"config_explain\",\"prompt\":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 5: JSON 结构校验 / 修复建议
gen_json_validate() {
  local state_file="$DATA_DIR/governance-state.json"
  if [ ! -f "$state_file" ]; then
    echo '{"type":"json_validate","prompt":"暂无状态文件"}'
    return
  fi
  local snippet=$(tail -c 500 "$state_file" 2>/dev/null || echo "{}")
  local prompt="验证以下 JSON 结构是否合法，只输出 valid:true/false 和 issues 列表：${snippet}"
  echo "{"type":"json_validate","prompt":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 6: Event 标签生成
gen_event_tagging() {
  local recent=$(journalctl --since "30 min ago" --no-pager -n 3 --output=short 2>/dev/null || echo "无日志")
  local prompt="为以下系统事件生成分类标签（category,severity,tags），JSON 格式输出：${recent}"
  echo "{"type":"event_tagging","prompt":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 7: Commit / Change Summary（⚠️ 低置信 — 不直接作为事实来源）
gen_change_summary() {
  local git_dir="$HOME/.openclaw/workspace"
  local log=$(cd "$git_dir" && git log --oneline -5 2>/dev/null || echo "无提交记录")
  local prompt="总结以下 Git 变更记录的类型和影响范围，标明你的置信度(high/medium/low)：${log}"
  echo "{"type":"change_summary","prompt":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}

# Task 8: Markdown 报告格式化
gen_report_format() {
  local report_file="$DATA_DIR/daily-report/latest.md"
  if [ ! -f "$report_file" ]; then
    echo '{"type":"report_format","prompt":"暂无报告"}'
    return
  fi
  local snippet=$(head -30 "$report_file" 2>/dev/null | grep -v '^#' | head -15 || echo "无内容")
  local prompt="将以下系统状态文本整理为 Markdown 格式报告（含标题、指标表、风险标注）：${snippet}"
  echo "{"type":"report_format","prompt":$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")}"
}


# ── 执行引擎 ──

run_task() {
  local task_json="$1"
  local TYPE=$(echo "$task_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['type'])")
  local PROMPT=$(echo "$task_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['prompt'])")

  local PAYLOAD=$(jq -nc --arg model "$MODEL" --arg prompt "$PROMPT" '{model:$model,prompt:$prompt,stream:false}')
  local START=$(date +%s%N)
  local API_RESP=$(curl -s --max-time "$CURL_TIMEOUT" http://localhost:11434/api/generate -d "$PAYLOAD" 2>/dev/null || echo '{"error":"API call timeout or failed"}')
  local END=$(date +%s%N)
  local LATENCY_MS=$(( (END - START) / 1000000 ))

  if ! echo "$API_RESP" | jq -e '.response' >/dev/null 2>&1; then
    local OLLAMA_ERR=$(echo "$API_RESP" | jq -r '.error // "unknown"')
    echo "[local-task-worker] ERROR: $OLLAMA_ERR" >&2
    OUTPUT="ERROR: $OLLAMA_ERR"
    SUCCESS=false
  else
    OUTPUT=$(echo "$API_RESP" | jq -r '.response')
    SUCCESS=true
  fi

  local INPUT_TOKENS=$(echo "$API_RESP" | jq -r '.prompt_eval_count // 0')
  local OUTPUT_TOKENS=$(echo "$API_RESP" | jq -r '.eval_count // 0')
  local TOTAL_TOKENS=$(( INPUT_TOKENS + OUTPUT_TOKENS ))

  # Validation: min content check
  local VALIDATION="ok"
  if [ "$SUCCESS" = false ]; then
    VALIDATION="api_fail"
  elif [ -z "$OUTPUT" ]; then
    VALIDATION="empty"
  elif [ ${#OUTPUT} -lt 3 ]; then
    VALIDATION="too_short"
  fi

  local OUT_ESCAPED=$(echo "$OUTPUT" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")
  echo "{\"timestamp\":\"$TIMESTAMP\",\"model\":\"$MODEL\",\"type\":\"$TYPE\",\"latency_ms\":$LATENCY_MS,\"input_tokens\":$INPUT_TOKENS,\"output_tokens\":$OUTPUT_TOKENS,\"total_tokens\":$TOTAL_TOKENS,\"success\":$SUCCESS,\"validation\":\"$VALIDATION\",\"output\":$OUT_ESCAPED}" >> "$LOGFILE"

  echo "[local-task-worker] $TYPE: $SUCCESS val=$VALIDATION (${LATENCY_MS}ms, ${TOTAL_TOKENS} tokens)"
}

# ── 主流程 ──

mkdir -p "$(dirname "$LOGFILE")"

TASKS=()
TASKS+=("$(gen_status_brief)")
TASKS+=("$(gen_event_classify)")
TASKS+=("$(gen_log_summary)")
TASKS+=("$(gen_config_explain)")
TASKS+=("$(gen_json_validate)")
TASKS+=("$(gen_event_tagging)")
TASKS+=("$(gen_change_summary)")
TASKS+=("$(gen_report_format)")

SUCCESS_COUNT=0
FAIL_COUNT=0
for task_json in "${TASKS[@]}"; do
  if run_task "$task_json"; then
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

logger -t local-task-worker "done: ${SUCCESS_COUNT} success, ${FAIL_COUNT} fail at ${TIMESTAMP}"
echo "[local-task-worker] done: ${SUCCESS_COUNT} success, ${FAIL_COUNT} fail"
