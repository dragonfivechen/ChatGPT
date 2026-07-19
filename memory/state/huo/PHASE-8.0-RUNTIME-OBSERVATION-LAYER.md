# PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md

**Phase 8.0 — Runtime Observation Layer v1**
**Date:** 2026-07-19
**Base:** Phase 7.5 Integrity Freeze 🔒
**Position:** Observe Layer — 只采集事实，不修改 Runtime

---

## §0 定位声明

```
Phase 8.0 不属于架构修改阶段。
Phase 8.0 是 Phase 7.5 冻结后的 Observation Layer。

核心原则：
  ❌ 不自动修复
  ❌ 不改变 Runtime 行为
  ❌ 不让 LLM 参与治理判断
  ✅ 只采集事实
  ✅ 推送状态和趋势
```

**生命周期：**

```
Runtime Frozen Baseline (Phase 7.5)
  ↓
Observation Metrics (Phase 8.0)
  ↓
JSONL / Event Snapshot
  ↓
Bot Push
  ↓
人工判断
```

---

## §1 指标分类

### A. Integrity 状态指标（核心）

对应 Phase 7 冻结基线。

| Metric | Source | Period |
|:---|---:|:---:|
| phase_status | Phase 7.5 Freeze Baseline | daily |
| boundary_state | B1-B5 Matrix | daily |
| bypass_count | Bypass Register v1.0 | daily |
| unresolved_gap | Gap Ledger | daily |

**示例载荷：**

```json
{
  "type": "runtime_integrity",
  "phase": "7.5",
  "status": "FROZEN",
  "boundaries": {
    "B1": "MISSING",
    "B2": "PARTIAL",
    "B3": "PARTIAL",
    "B4": "DESIGN_ONLY",
    "B5": "OBSERVER"
  },
  "timestamp": "2026-07-19T10:50:00"
}
```

### B. Runtime Health

监控系统事实状态，重点积累证据，不是报警。

**Gateway**（当前属 Future Gap，只观察不干预）：

| Metric | Meaning |
|:---|---:|
| gateway_detect_count | Gateway 事件数量 |
| direct_execute_count | 直接执行次数 |
| tool_call_total | 总 tool call |

**Event**（对应 B5）：

| Metric | Meaning |
|:---|---:|
| event_emit_total | 事件数量 |
| lifecycle_event_total | lifecycle 数量 |
| event_gap_detected | 执行无事件数量 |

**Context**（对应 B4）：

| Metric | Meaning |
|:---|---:|
| context_build_total | Context 构建次数 |
| projection_event_total | Projection event 数量 |
| memory_inject_total | Memory 注入次数 |

### C. Token / Session 观测

在已有 Token Observe 基础（`/home/dragonfive/.openclaw/observe-token.sh`）上扩展。

**指标：**

```
session_count
context_tokens
transcript_bytes
compaction_total
prune_total
cache_hit_rate
```

**示例载荷：**

```json
{
  "type": "token_observe",
  "context_tokens": 142000,
  "compaction": 1,
  "prune": 1
}
```

### D. Worker / Plugin 观测

对应 B2（Worker→Policy）和 Plugin PEC。

| Metric | Description |
|:---|---:|
| worker_spawn_total | Worker 创建次数 |
| worker_depth_max | 最大嵌套深度 |
| plugin_execute_total | Plugin 执行次数 |
| plugin_event_missing | Plugin 执行无事件计数 |

---

## §2 数据格式

**存储：** append-only JSONL

```
events/
├── runtime_observe.jsonl    ← Runtime Health / Worker / Plugin
├── token_observe.jsonl      ← Token / Session （已有）
├── integrity_observe.jsonl  ← Integrity 基线状态
```

**规则：**
- 不引入数据库
- 不修改已有数据
- 每条 JSONL 行独立可解析
- 时间戳统一 UTC ISO-8601

---

## §3 推送架构

**沿用已有 Telegram 推送链：**

```
observer script
  ↓
format_report.py
  ↓
push-notify
  ↓
Telegram Bot
```

**统一出口原则：**
- 不让每个指标自己发消息
- 所有观测数据合并为一条日报/时报

```
metrics collector
  ↓
report formatter
  ↓
bot
```

**推送建议频率：**

| 类型 | Period |
|:---|---:|
| Runtime Health | 1 小时 |
| Token Observe | 1 小时（已有） |
| Integrity Summary | 每日 |
| Gap Ledger Diff | 事件触发 |

**Bot 日报示例：**

```
OpenClaw Runtime Observation

Status:
🟢 Integrity Freeze

Phase:
7.5 FROZEN

Boundary:
B1 Gateway        MISSING
B2 Worker Policy  PARTIAL
B3 Registry       PARTIAL
B4 Projection     DESIGN_ONLY
B5 Event Truth    OBSERVER

Runtime:
Tool Calls:      324
Events:          324
Context Builds:  156
Compaction:       2

Token:
Current:        142K
Growth:         +8K/day

Gap:
No Reclassification
```

---

## §4 实施顺序

### 第一阶段（核心）

```
runtime_observer.py
  ↓
integrity_observe.jsonl
  ↓
Telegram daily summary
```

**覆盖范围：**
- Phase 状态（phase_status）
- B1-B5 边界状态
- Token 观测
- Event 计数
- Gap 变化检测

### 第二阶段

```
runtime_health_observer.py
  ↓
runtime_observe.jsonl
  ↓
hourly bot push
```

### 第三阶段

```
worker_plugin_observer.py
  ↓
worker/plugin metrics
  ↓
gap diff detection
```

---

## §5 冻结约束

### Phase 7.5 Freeze Rules 继承

| Rule | Status |
|:---|:---:|
| 不自动修复 | ✅ |
| 不改变 Runtime 行为 | ✅ |
| 不让 LLM 参与治理判断 | ✅ |
| 不解冻 Phase 6 | ✅ |
| 不重新分类 bypass | ✅ |

### 数据所有权

```
All observation data → memory/data/system/observations/
  observations/
  ├── integrity.jsonl
  ├── runtime.jsonl
  └── token.jsonl

Ownership: system (无身份归属)
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Phase 8.0 Runtime Observation Layer v1 设计文档 |
