#!/usr/bin/env bash
# 传感器日报 — 每日推送系统状态到 Telegram
# 依赖: push-notify.mjs (通过 push-gate 统一出口)
set -euo pipefail

BASE="$HOME/.openclaw/workspace/memory/data/system"
HUO="$HOME/.openclaw/workspace/memory/events/huo"
PUSH="$HOME/.openclaw/workspace/hooks/oek-ci-gate/push-notify.mjs"
DATE=$(TZ='Asia/Shanghai' date +"%Y-%m-%d %H:%M")
TITLE="📊 传感器日报 — ${DATE}"

# ── 系统健康 (最新一条) ──
SYS=$(tail -1 "$BASE/system-health.jsonl" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f\"CPU: {d['cpu_pct']}% | MEM: {d['mem_mb']}MB | DISK: {d['disk_pct']} | LOAD: {d['load']}\")
except:
    print('N/A')
" 2>/dev/null || echo "N/A")

# ── 服务状态 (读取整个文件，按service分组取最新) ──
SVC_DATA=$(python3 -c "
import json
with open('$BASE/service-state.jsonl') as f:
    lines=[l.strip() for l in f if l.strip() and not l.startswith('#')]
gw='N/A'
ol='N/A'
for l in lines:
    try:
        d=json.loads(l)
        if d['service']=='openclaw-gateway':
            gw=f\"Gateway: {d['status']} (restarts: {d['restarts']})\"
        elif d['service']=='ollama':
            ol=f\"Ollama: {d['status']} (restarts: {d['restarts']})\"
    except:
        pass
print(gw)
print(ol)
" 2>/dev/null)
GW=$(echo "$SVC_DATA" | head -1)
OL=$(echo "$SVC_DATA" | tail -1)

# ── 记忆快照 ──
MEM=$(tail -1 "$BASE/memory-snapshot.jsonl" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(f\"文件: {d['mem_file_count']} | 大小: {d['mem_dir_kb']}KB | 跨度: {d['oldest_day']} ~ {d['newest_day']}\")
except:
    print('N/A')
" 2>/dev/null || echo "N/A")

# ── 模型评估 (当天汇总) ──
EVAL=$(python3 -c "
import json,sys
today='$DATE'[:10]
today_entries=[]
with open('$HUO/ollama-eval.jsonl') as f:
    for line in f:
        line=line.strip()
        if not line or line.startswith('#'):
            continue
        try:
            d=json.loads(line)
            ts=d.get('timestamp','')
            if ts[:10]==today:
                today_entries.append(d)
        except:
            pass
if not today_entries:
    print('今日无评估数据')
else:
    total=len(today_entries)
    succ=sum(1 for e in today_entries if e.get('success'))
    lat=[e['latency_ms'] for e in today_entries if 'latency_ms' in e]
    avg=sum(lat)/len(lat)/1000 if lat else 0
    cpu=[e.get('cpu_peak_pct',0) for e in today_entries]
    mem=[e.get('mem_peak_mb',0) for e in today_entries]
    avg_cpu=sum(cpu)/len(cpu) if cpu else 0
    peak_mem=max(mem) if mem else 0
    print(f\"任务: {total}次 | 成功: {succ}/{total} | 平均延迟: {avg:.1f}s | CPU峰值: {avg_cpu:.0f}% | 内存峰值: {peak_mem}MB\")
" 2>/dev/null || echo "N/A")

BODY="🖥 系统
${SYS}

🔧 服务
${GW}
${OL}

🧠 记忆
${MEM}

🤖 本地模型
${EVAL}"

# 推送
node "$PUSH" "$TITLE" "$BODY" 2>/dev/null && echo "[$(date)] 日报已推送" || echo "[$(date)] 推送失败"
