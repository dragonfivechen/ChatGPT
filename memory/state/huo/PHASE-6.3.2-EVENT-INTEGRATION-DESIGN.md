# Phase 6.3.2 Projection Event Integration Design

**Status:** COMPLETE
**Date:** 2026-07-19
**Dependencies:**
- CONTEXT-PROJECTION-CONTRACT.md v1.0 DRAFT (§6)
- context-projection-event.schema.json v1
- Event Source Truth (FROZEN)
- Memory Governance (FROZEN)

---

## 0. Design Principles

### 事件闭环

```
Projection Request
    │
    v
Context Builder ──────┬──→ Projection Generated
    │                  │        │
    │                  │        v
    │                  │   projection_event ←── 当前焦点
    │                  │        │
    │                  │        v
    │                  │   Event Store (memory/events/system/context-projection/)
    │                  │
    └── Rejected ──────┘
         │
         v
    violation_event (已包含在 event schema 中)
```

### 核心验证

```yaml
必须满足:
  V1: 每次 Context 构建产生 1 条 projection_event
  V2: 每条 event 包含 source + provenance
  V3: 过期投影记录 expires_at 到 event
  V4: 删除/失效可追踪 (通过 violation 字段)
  V5: Replay 可恢复投影事实 (通过 event → bundle 还原)
```

---

## 1. 事件触发时机

### 1.1 正常投影

```yaml
触发点: Context 构建完成，准备注入 LLM 请求时

时序:
  request_arrival
    │
    v
  context_build_start
    │
    ├── collect projections
    ├── validate against schema
    ├── resolve rejections
    │
    v
  context_build_complete
    │
    ├── inject into LLM request
    ├── WRITE projection_event ←── 此时触发
    │
    v
  LLM response generation
```

### 1.2 拒绝投影

```yaml
触发点: 投影验证发现禁止源/缺失 provenance 时

行为:
  1. 拒绝该条投影 (不进入 LLM 请求)
  2. 在 projection_event.violations[] 中记录
  3. 其他合法投影正常构建

violation 记录:
  - source: 被拒绝的源
  - reason: 拒绝原因 (enum)
  - context_build 继续执行 (非致命)
```

### 1.3 投影失效

```yaml
触发点: expires_at 到达，投影过期时

行为:
  1. 过期投影不再用于后续请求 (Runtime 保证)
  2. 不产生单独失效事件 (已在原始 event 的 expires_at 中记录)
  3. Replay 时通过 event.expires_at 判断是否有效

原因: 失效是自然行为，不需要额外事件
     重复失败 (expired violation) 会产生正常 violation
```

---

## 2. 事件写入规范

### 2.1 写入路径

```yaml
路径: memory/events/system/context-projection/
文件: YYYY-MM-DD.md
格式: yaml block (每条 ≤ 20 行, 同 Event Source Truth 规范)

写入时机: 非阻塞
  - Context 构建完成后异步写入
  - 不影响 LLM 请求延迟

写入者:
  - Runtime Context Builder (Projection 生成者)
```

### 2.2 事件与文件的对应

```yaml
每条 projection_event 对应:
  1 条 Context 构建
  1 条 LLM 请求 (假设 1:1)
  1 条 event entry (yaml block)

示例:
  ```yaml
  type: context_projection
  timestamp: "2026-07-19T09:30:00.000+08:00"
  request_id: "req-abc-001"
  projections:
    - source: system_instruction
      query: "openclaw.json instructions"
      entries: 1
      total_chars: 450
      provenance: { source: static_config, detail: "system instructions" }
    - source: conversation_history
      query: "session/current"
      entries: 12
      total_chars: 8600
      provenance: { source: runtime_session, detail: "session messages" }
    - source: memory
      query: "preferences/time-format"
      entries: 1
      total_chars: 120
      provenance: { source: memory_search, detail: "preferences/time-format.md" }
  total_projection_size: 9170
  ```
```

### 2.3 存储约束

```yaml
文件大小: 每个文件 ≤ 500 条 (单个 event ≈ 500B → 250KB)
分割: 按天分割 (YYYY-MM-DD.md)
历史: 自动轮转 (保留 90 天，可配置)
```

---

## 3. 事件与 Schema 的连接

### 3.1 从 Bundle → Event

```yaml
Bundle (context-projection-bundle.schema.json):
  - 完整的投影数据
  - 包含 projection entry 的全部字段
  - 用于验证和 Runtime 操作

Event (context-projection-event.schema.json):
  - 投影摘要
  - 不含 projection entry 的完整 content 字段
  - 用于审计和 Governance

映射:
  Bundle.projections[].source     → Event.projections[].source     ✅ 1:1
  Bundle.projections[].provenance → Event.projections[].provenance ✅ 1:1
  Bundle.projections[].content    → Event.projections[].total_chars ✅ 摘要 (不含原文)
  Bundle.request_id               → Event.request_id               ✅ 1:1
  Bundle.projection_counts         → Event.total_projection_size    ✅ 派生
  Bundle 无 violation               → Event.violations[]             ✅ Event 新增
```

### 3.2 为什么 Event 不含完整 content

```yaml
原因:
  1. 审计不需要看到 LLM 输入原文
  2. 投影 content 可能包含临时状态 (5min TTL)
  3. Event 追求可审计性，不追求可还原性

可还原范围:
  通过 Event 可以知道:
    - 哪些源被投影
    - 每个源投影了多少内容
    - 投影来源 provenance

  通过 Event 不能知道:
    - 投影的具体内容
    - LLM 实际看到了什么

补充:
  如果需要还原具体投影内容:
    需要 Event + Context 构建日志 + Memory 快照
    属于 Phase 7 Replay Integrity 范围
```

---

## 4. Replay 验证

### 4.1 Replay 能恢复什么

```yaml
从 Events 可恢复:
  request_id → 确认哪次请求产生了投影
  projected_at → 确认投影时间
  source list → 确认使用了哪些投影源
  provenance → 确认投影来源
  violations → 确认哪些投影被拒绝

从 Events 不可恢复:
  投影的内容 (content/full text)
  投影的格式细节 (text vs json vs message)
  LLM 最终输入的精确尺寸

恢复边界:
  治理审计: ✅ 足够 (检查来源合规性)
  精准构建: ❌ 不够 (需要原始数据)
```

### 4.2 Replay 流程

```yaml
Audit Request:
  request_id: "req-abc-001"
    │
    v
Event Store Lookup:
  path: memory/events/system/context-projection/2026-07-19.md
  filter: request_id == "req-abc-001"
    │
    v
Event Found:
  projections: [3 entries]
  sources: [system_instruction, conversation_history, memory]
  total_chars: 9170
  violations: []  # 没有拒绝
    │
    v
Audit Output:
  ✅ 投影源合规 (均在 §1.1)
  ✅ provenance 完整
  ✅ 无 violation
  ⚠️ 无法验证投影内容准确性
```

### 4.3 Replay 范围限制

```yaml
Event 只覆盖:
  Context 构建阶段 (从投影选择到注入 LLM)

Event 不覆盖:
  LLM 收到投影后如何处理 (LLM 内部)
  Provider 决策 (Phase 6.2 范围)
  响应生成过程

补充:
  完整的请求链 replay 需要:
    Event (Context 投影) → Provider Cap Event → LLM Response Event
    需要 Phase 7 统一协调
```

---

## 5. 事件与现有系统的连接

### 5.1 与 Event Source Truth 的关系

```yaml
Event Source Truth (FROZEN):
  原则: 所有事件不可变、可溯源、可重放

Context Projection Event:
  符合: ✅ 不可变 (写入后不修改)
  符合: ✅ 可溯源 (request_id + projected_at + provenance)
  符合: ✅ 可重放 (从 event store 可查询)

差异:
  Event Source Truth 关注"发生了什么"
  Context Projection Event 关注"投影了什么"
  两者互补不冲突
```

### 5.2 与 Memory Governance 的关系

```yaml
Memory Governance:
  写入: Memory Writer Boundary 控制
  读取: Context 构建通过显式查询读取

Event 记录:
  Memory 投影的每次查询记录在 projection_event 中
  通过 event.projections[].provenance 可追踪 Memory 查询

闭环:
  Memory (Writer Boundary)
    │
    v
  Context Builder (显式查询)
    │
    v
  projection_event (追踪查询)
    │
    v
  Event Store (可审计)
```

### 5.3 与 Reasoning Isolation 的关系

```yaml
Reasoning Isolation (Phase 6.1):
  reasoning_content 不入 Event Source Truth

Context Projection Event:
  reasoning_content 不入投影 Event

一致:
  两个 Contract 各自禁止 reasoning_content
  形成双重约束:
    Phase 6.1: reasoning_content 不进入持久化
    Phase 6.3: reasoning_content 不进入 LLM 输入
```

---

## 6. 运行时集成接口

### 6.1 Context Builder 接口

```yaml
# 输入
build_context(request):
  request_id: str
  session: SessionState
  memory_results: Optional[MemorySearchResult]
  knowledge_results: Optional[KnowledgeSearchResult]

# 内部流程
build_context(request):
  projections = []
  violations = []
  
  # Step 1: 收集投影源
  projections.append(system_instruction(request.config))
  projections.append(conversation_history(request.session))
  
  if request.memory_results:
    p = memory_projection(request.memory_results)
    if validate(p):
      projections.append(p)
    else:
      violations.append({ source: "memory", reason: p.failure_reason })
  
  if request.knowledge_results:
    p = knowledge_projection(request.knowledge_results)
    if validate(p):
      projections.append(p)
    else:
      violations.append({ source: "knowledge", reason: p.failure_reason })
  
  # Step 2: 构建 Bundle + Event
  bundle = build_bundle(request_id, projections)
  event = build_event(request_id, projections, violations)
  
  # Step 3: 异步写入 Event
  write_event_async(event)
  
  # Step 4: 给 LLM 请求
  return llm_request(projections)

# 输出
projection_event:
  type: context_projection
  timestamp: now()
  request_id: request.request_id
  projections: [summary]
  total_projection_size: sum(projections.content.len)
  violations: [denied projections]
```

### 6.2 Event Writer 接口

```yaml
write_event(event):
  path = "memory/events/system/context-projection/{date}.md"
  content = yaml_dump(event)
  
  # 非阻塞写入
  return async_append(path, content)

# 写入确认不阻止请求
# Event 丢失不影响运行时
# 但 Governance Audit 可检测 Event 缺失
```

---

## 7. 验证检查表

### 7.1 必须满足的验证

```yaml
V1: 每次 Context 构建产生 1 条 projection_event
  验证: 构建前后 event count +1
  误判: None (构建失败不计 event)

V2: Event 包含 source + provenance
  验证: event.projections[].source present
        event.projections[].provenance present
  误判: 缺少 provenance 的 event 不可接受

V3: 过期投影记录 expires_at
  验证: memory/events/knowledge 投影的 event 包含 expires_at
  误判: 无 expires_at 的持久投影违反 Contract

V4: 删除/失效可追踪
  验证: 拒绝的投影在 event.violations[] 中
  误判: 拒绝投影不记录 = 审计盲区

V5: Replay 能恢复投影事实
  验证: event → source list → provenance
  误判: Event 不能证明投影内容准确
```

### 7.2 验收条件

```yaml
Phase 6.3.2 COMPLETE 条件:
  [ ] 事件闭环定义完成 (§1-§4)
  [ ] Event ↔ Schema 映射确认 (§3)
  [ ] Replay 边界确认 (§4)
  [ ] 现有系统连接确认 (§5)
  [ ] 运行时接口概要定义 (§6)
  [ ] 验证检查表确认 (§7)
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Phase 6.3.2 Event Integration Design, 7 章节 |
