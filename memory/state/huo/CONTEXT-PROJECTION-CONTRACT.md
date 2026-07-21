# Context Projection Contract v1.0 — FINAL

```yaml
contract:
  name: CONTEXT-PROJECTION
  version: v1.0
  level: L1
  parent: FREEZE-CONTRACT
  scope: context projection for LLM
  owner: 龙哥
  status: active
```

**Phase 6.3**
**Status:** FINAL
**Date:** 2026-07-19
**Frozen:** 2026-07-19 09:40 CST
**Owner:** 龙哥

**Dependencies (all FROZEN):**
- Event Source Truth
- Memory Governance (Namespace / Ownership / Writer Boundary)
- REASONING-ISOLATION-CONTRACT.md v1.0 FINAL
- PROVIDER-CAPABILITY-CONTRACT.md v1.0 FINAL

**Upgrade path:** DRAFT → FINAL (2026-07-19)
- Phase 6.3.1 Schema: COMPLETE
- Phase 6.3.2 Event Integration: COMPLETE
- Phase 6.3.3 Runtime Integration: COMPLETE
- Phase 6.3 Validation: 6 invariants × 20 scenarios, ALL PASS

**Known gaps (scoped to Phase 6.4):**
- Unknown-source data injection by plugins bypassing Context Builder
- External Worker Context not governed by Projection Contract

**Preservation guarantee:**
- LLM = Consumer of Projection (not Builder, not Selector)
- Runtime = Builder (collect → validate → record)
- Event = Truth (projection_event, not LLM input backup)
- Memory ≠ Context (Writer cannot directly mutate Context)
- Reasoning_content never enters Context (dual constraint with §6.1)
- Context is ephemeral (request-scoped, 5min TTL)
- Event records projection source + provenance, not full content

---

## §0 定位

### Context Projection 是什么

```yaml
Context Projection:
  定义: Runtime State → LLM 输入之间的显式投影层
  不是: 上下文构建器的重命名
  不是: OpenClaw 消息系统的替代
  不是: 提示词注入的入口

定位:
  Runtime 内部状态 (Events, Memory, Knowledge)
    ↓
  Context Projection (显式选择 & 格式化)
    ↓
  LLM Request (系统提示 + 消息历史 + 投影内容)
```

### 要解决的核心问题

```yaml
现有风险:
  Memory → Context → LLM 构成隐式状态通道
  即: Memory 中的内容通过 Context 自动进入 LLM
      且 LLM 的响应可以通过 Memory Writer 重新存入 Memory
  
  这个通道如果不受控:
    Memory (写入不受限)
      ↓
    Context (选择不受限)
      ↓
    LLM (读取所有投影内容)
      ↓
    Memory Writer (LLM 输出写入 Memory)
      ↓
    Context (下一轮读取写入的内容)

  形成: 隐式状态循环，没有权限边界

Contract 目标:
  将上述隐式通道转为显式: 
  每次投影:
    - 确认源头
    - 确认格式
    - 确认权限
    - 确认生命周期
    - 记录 Event
```

### 保持冻结的原则

```yaml
LLM = Producer
  LLM 生成响应，不直接读取原始 Memory
  
Runtime = Executor
  Runtime 选择哪些内容投影给 LLM
  
Governance = Judge
  Governance 判定投影是否符合 Contract
  
Event = Truth
  每次投影必须记录 Event
```

---

## §1 投影源分类

### 1.1 允许投影的源

```yaml
投影源 A: System Instructions (系统提示)
  来源: openclaw.json configuration
  归属: 系统配置
  投影权限: ✅ 总是允许
  格式: 静态文本
  生命周期: 会话级别
  provenance: { source: "config", detail: "system instructions from configuration" }

投影源 B: Conversation History (消息历史)
  来源: 当前会话的消息列表
  归属: Runtime 会话状态
  投影权限: ✅ 总是允许
  格式: message[] (role + content)
  生命周期: 会话级别
  约束: 必须携带 role (user/assistant/tool)
  provenance: { source: "runtime_session", detail: "current conversation messages" }

投影源 C: Memory Projection (记忆投影)
  来源: Memory 文件 (memory/*)
  归属: 内存系统
  投影权限: ✅ 有条件允许 (见 §2)
  格式: 文本摘要 (非原始文件)
  生命周期: 每次查询独立
  约束: 必须经过 Memory Governance Writer Boundary 检查
  provenance: { source: "memory", detail: "memory search result for context injection" }

投影源 D: Event Projection (事件投影)
  来源: Events (memory/events/*)
  归属: 事件系统
  投影权限: ✅ 有条件允许 (见 §2)
  格式: 结构化的时序摘要
  生命周期: 每次查询独立
  provenance: { source: "events", detail: "event query result for context" }

投影源 E: Tool Results (工具调用结果)
  来源: Tool/Plugin 执行结果
  归属: Runtime
  投影权限: ✅ 总是允许
  格式: 原始执行输出
  生命周期: 每次工具调用独立
  provenance: { source: "tool_execution", detail: "tool/plugin call result" }

投影源 F: Knowledge Projection (知识投影)
  来源: Knowledge 文件 (memory/knowledge/*)
  归属: 知识系统
  投影权限: ✅ 有条件允许 (见 §2)
  格式: 文本摘要 (非原始文件)
  生命周期: 每次查询独立
  provenance: { source: "knowledge", detail: "knowledge query result for context" }

投影源 G: System State (系统状态投影)
  来源: Runtime 状态 (时间、版本、可用性)
  归属: Runtime
  投影权限: ✅ 总是允许
  格式: 结构化数据
  生命周期: 每次请求独立
  provenance: { source: "runtime_state", detail: "current system state snapshot" }
```

### 1.2 禁止投影的源

```yaml
禁止投影 X: 原始凭证 / Secrets
  来源: secrets.json, auth-profiles.json
  原因: SecretRef Migration 已确立 Secrets 层
  禁止规则: 任何未经 SecretRef Resolver 脱敏的凭证不入 Context
  严重度: P0

禁止投影 Y: 系统配置文件 (原始)
  来源: openclaw.json, runtime 配置
  原因: 配置包含基础设施信息
  例外: System Instructions 允许 (显式配置的提示内容)
  严重度: P0

禁止投影 Z: 跨会话原始 Memory
  来源: 不属于当前用户的 Memory 文件
  原因: Memory Governance Writer Boundary 确立的隔离
  严重度: P1

禁止投影 W: 推理痕迹 (reasoning_content)
  来源: reasoning_content 输出
  原因: REASONING-ISOLATION-CONTRACT.md §2.2.2
       reasoning_content 不进入下一轮 Context
  严重度: P0 (不可违反)
```

### 1.3 条件投影规则

```yaml
条件投影 = 允许投影但必须满足以下所有:
  1. 来源属于 §1.1 允许列表
  2. 不是 §1.2 禁止列表
  3. 经过 Memory Governance Writer Boundary 检查
  4. 携带 provenance 标记
  5. 记录 projection_event
```

---

## §2 Memory ↔ Context 边界

### 2.1 Memory ≠ Context

```yaml
Memory:
  - 持久化文件
  - 身份隔离 (通过 Namespace + Ownership)
  - Writer Boundary 控制写入
  - 作为长期知识存储

Context:
  - 临时投影
  - 每次请求构建
  - 请求完成后销毁
  - 作为 LLM 输入的一部分

Memory → Context 不是直接拷贝，而是:
  Memory 文件
    ↓ 查询/选择/摘要
  Context Projection
    ↓
  LLM 输入

关键规则:
  Context 不是 Memory 的运行时镜像
  Context 构建必须显式选择 (非自动全量投影)
```

### 2.2 Memory 投影的显式选择

```yaml
显式选择规则:
  每次 Memory → Context 投影必须:
  1. 明确指定查询范围 (文件名、命名空间、时间范围)
  2. 不是自动投影所有 Memory
  3. 投影结果不能保留超出请求生命周期的引用

示例:
  正确: "查询 memory/preferences/temperature.md → 提取偏好摘要 → 加入 Context"
  错误: "加载 memory/* → 加入 Context"

违反规则:
  Context 中包含未指定查询范围的 Memory 内容 = 隐式通道
  严重度: P1
```

### 2.3 Memory Writer 不允许直接写入 Context

```yaml
Writer 权限:
  Memory Writer:     写入 memory/* 文件 ✅
  Context Builder:   构建 Context ✅
  Memory Writer → Context: 禁止 ❌
  原因: Memory Writer 执行完成后
        Memory 写入与 Context 构建是两个独立阶段
        不能写入 Memory 的同时推送到 Context

撤销规则:
  Memory 中的内容不会自动进入下一轮 Context
  除非通过显式 Context 查询

LLM 写入 Memory → 下一轮:
  LLM 响应
    ↓ Memory Writer 写入
  memory/preferences/xxx.md
    ↓ 下一轮 Context 构建 (显式查询)
  投影到 LLM
```

---

## §3 Context ↔ Reasoning Isolation 边界

### 3.1 不冲突声明

```yaml
Reasoning Isolation Contract (§2.2.2):
  reasoning_content 不进入:
    - Memory
    - Knowledge
    - Event Source Truth
  
Context Projection Contract:
  reasoning_content 不入 Context (禁止投影 W)
  即使 Memory/Event/Knowledge 本身不存 reasoning_content
  Context 构建时也不能引用已销毁的推理痕迹
```

### 3.2 完整隔离链

```
LLM Response
  │
  ├── content (最终输出)
  │     ↓
  │   Context (下一轮) ✅ 允许 (作为 conversation history)
  │
  └── reasoning_content (推理痕迹)
        ↓
      Destroy (Reasoning Isolation §2.2)
        ↓
      ❌ 不入 Context
      ❌ 不入 Memory
      ❌ 不入 Event
      ❌ 不入 Knowledge
```

### 3.3 隔离一致性

```yaml
如果违反 (reasoning_content 进入 Context):
  1. 违反 REASONING-ISOLATION-CONTRACT.md RI-001
  2. 违反 CONTEXT-PROJECTION-CONTRACT §1.2 禁止投影 W
  3. 双重 Contract Violation

检测:
  Runtime 不可检测 (reasoning_content 在进入 Context 前已销毁)
  Governance Audit: 通过回放事件检查 Context 构建内容
```

---

## §4 投影格式

### 4.1 投影入口格式

```yaml
每条投影必须声明:

projection_entry:
  source: "memory|events|knowledge|system|tool"    # 来源分类
  target: "system_instruction|message|attachment"    # 投影目标位置
  format: "text|json|structured_summary"            # 投影格式
  content: "..."                                    # 投影内容
  provenance:
    source: "memory_search|event_query|static_config"
    detail: "where the content came from"
  project_at: "ISO-8601 timestamp"                  # 投影时间
  expires_at: "ISO-8601 timestamp"                  # 过期时间 (可选)
```

### 4.2 投影格式约束

```yaml
格式 A: 文本投影 (text)
  用于: Memory 摘要、Knowledge 查询结果
  约束: 
    - 必须有明确的长度限制
    - 不能是原始文件全文
    - 必须标记为 "summary" 类型

格式 B: 结构化投影 (json)
  用于: 系统状态、工具结果、事件摘要
  约束:
    - 必须符合 schema (如果有定义)
    - 不能嵌套原始敏感数据

格式 C: 消息投影 (message)
  用于: 会话历史
  约束:
    - 必须携带 role
    - content 不能包含系统指令
    - 遵循 conversation history 标准格式
```

### 4.3 禁止格式

```yaml
禁止:
  原始 Memory 文件内容作为 Context
  未脱敏的 Secrets 产物
  未封装的 Tool 原始输出 (必须经过 Tool Result 格式)
  没有任何 provenance 标记的投影内容
```

---

## §5 生命周期

### 5.1 投影生命周期

```
Context Build (请求到达)
    ↓
投影选择 (选择源 + 格式化)
    ↓
投影注入 (加入 LLM 输入)
    ↓
LLM 生成响应
    ↓
Context 销毁 (响应完成后)
```

### 5.2 过期时间

```yaml
投影过期规则:
  Memory 投影:    expires_at = project_at + 5min (最多)
  Event 投影:     expires_at = project_at + 5min (最多)
  Knowledge 投影: expires_at = project_at + 5min (最多)
  System State:   expires_at = project_at + 5s (系统状态变化快)
  Tool Result:    expires_at = 下一轮工具调用时

过期后行为:
  投影内容不可用于后续请求
  Context 构建每次请求独立
  不可复用上一轮的投影 (会话历史除外)
```

### 5.3 会话历史例外

```yaml
会话历史 (user/assistant/tool messages):
  生命周期: 会话级别
  不设 expires_at
  因为: 会话历史是跨请求累加的
  但: 每条消息在加入前经过 Context Projection

约束:
  会话历史中的每条消息必须有来源标记
  系统级别的 message 与用户消息必须区分
  超过会话上限 (max_tokens) 时丢弃最早的
```

---

## §6 事件记录

### 6.1 Context Projection Event

```yaml
每次 Context 构建 (每个请求) 记录:

projection_event:
  type: context_projection
  timestamp: "ISO-8601"
  request_id: "req-xxx"
  
  projections:
    - source: memory
      query: "preferences/temperature"
      entries: 3
      total_chars: 1240
      provenance: "memory_search → user.preferences"
    
    - source: system
      entries: 1
      total_chars: 450
      provenance: "static_config → system_instructions"
    
    - source: conversation
      entries: 12
      total_chars: 8600
      provenance: "runtime_session → history"
  
  total_projection_size: 10290
  max_context_window: 32000
  utilization_pct: 32.2
```

### 6.2 事件定位

```yaml
写入: memory/events/system/context-projection/
文件: YYYY-MM-DD.md
格式: 每条 yaml 块 ≤ 20 行
```

### 6.3 事件用途

```yaml
Governance Audit:
  - 检查投影源的合理分布
  - 检查是否有 prohibited source 被误投影
  - 检查投影大小是否可控

Runtime Optimization:
  - 投影大小统计
  - Context window 利用率
  
Compliance:
  - 验证投影内容是否满足 Contract 要求
  - 检测未记录的投影
```

---

## §7 权限矩阵

### 谁可以定义 Context Projection

```yaml
System Configuration (openclaw.json):
  定义: 系统指令、默认投影规则
  权限: ✅ 系统级
  范围: 全局

Plugin:
  定义: 通过 Capability Registry 注册的插件投影
  权限: ✅ 有条件 (Plugin Capability Contract)
  范围: 插件注册的能力

Agent Configuration:
  定义: Agent 级别的 system instructions
  权限: ✅ Agent 级
  范围: 当前 Agent

Runtime:
  定义: 会话历史、系统状态
  权限: ✅ 运行时自动
  范围: 当前会话

LLM:
  定义: ❌ 不能定义投影
  范围: N/A

User Configuration:
  定义: 偏好、知识库查询
  权限: ✅ 用户级
  范围: 当前用户命名空间
```

### 谁可以读取 Context

```yaml
读取 Context 的内容:
  LLM:      ✅ (Context 的消费方)
  Runtime:  ✅ (Context 的构建方)
  Plugin:   ❌ (Plugin 通过工具调用获取 Context 子集)
  User:     ❌ (不直接暴露原始 Context)
  Governance: ✅ (通过 Event 间接查看)
```

---

## §8 允许/禁止投影检查表

### 8.1 每次投影的验证步骤

```
Projection Request:
    │
    v
Step 1: 源是否在 §1.1 允许列表?
    ├── No → 拒绝投影 (记录 violation event)
    └── Yes → Step 2
    
Step 2: 源是否在 §1.2 禁止列表?
    ├── Yes → 拒绝投影 (记录 violation event)
    └── No → Step 3

Step 3: 源是条件投影吗?
    ├── No → Step 4
    └── Yes → 检查:
        1. Memory Governance Writer Boundary ✅
        2. provenance 标记 ✅
        3. 投影格式符合 §4 ✅
        4. 生命周期符合 §5 ✅
        所有通过 → Step 4
        任一失败 → 拒绝投影

Step 4: 投影格式符合 §4?
    ├── No → 拒绝投影 (格式错误)
    └── Yes → Step 5

Step 5: 生命周期可追踪?
    ├── No → 拒绝投影 (无法设置 expires_at)
    └── Yes → 允许投影 + 记录 projection_event
```

### 8.2 常见场景检查表

| 场景 | 投影源 | 允许? | 条件 |
|:---|:---|:---:|:---|
| 系统指令 | config | ✅ | 总是 |
| 会话历史 | runtime | ✅ | 总是 |
| 工具调用结果 | runtime | ✅ | 总是 |
| Memory 偏好查询 | memory | ✅ | 显式查询 + provenance |
| Memory 跨用户查询 | memory | ❌ | 禁止 (Writer Boundary) |
| Event 摘要 | events | ✅ | 显式查询 + provenance |
| Knowledge 查询 | knowledge | ✅ | 显式查询 + provenance |
| 原始 secrets | secrets | ❌ | P0 禁止 |
| 会话历史中含 reasoning_content | history | ❌ | P0 禁止 (已销毁) |
| 配置文件内容 | config (原始) | ❌ | P0 禁止 |
| 系统状态 (时间/版本) | runtime | ✅ | 总是 |
| 前一轮 Memory 自动投影 | memory | ❌ | 必须显式重新查询 |
| LLM 自我声明的 Context 需求 | LLM | ❌ | LLM 不能定义投影 |
| Plugin 注册的投影 | plugin | ✅ | 有条件 (Capability Registry) |

---

## §9 Context 与 Capability Registry 关系

### 9.1 Context 投影不经过 Enforcement

```yaml
Context Projection (Phase 6.3):
  投影方向: Runtime → LLM (输入侧)
  不涉及: Provider 能力校验
  
Provider Capability Enforcement (Phase 6.2.3):
  校验方向: LLM → Provider (输出侧)
  不涉及: Context 构建

两者独立:
  Context 投影: 决定 LLM 接收什么输入
  Capability Enforcement: 决定 LLM 请求如何发送给 Provider
```

### 9.2 Capability Registry 的查询不进入 Context

```yaml
Registry 查询:
  - 属于 Runtime 内部操作
  - 查询结果不投影给 LLM
  - LLM 不需要知道 Registry 状态

例外:
  debug/审计场景下可投影 Registry 查询结果
  但必须标记 provenance: "runtime_debug" + 记录 event
```

---

## §10 验证 & 冻结条件

### 10.1 必须验证的场景

```yaml
必须验证:
  1. Memory → Context 投影必须有显式查询源
  2. 禁止投影源不能进入 Context
  3. 每次投影记录 projection_event
  4. reasoning_content 不能出现在 Context 中
  5. Context 生命周期在请求结束后销毁
  6. 无 provenance 的投影不能构造
```

### 10.2 冻结条件

```yaml
Phase 6.3 COMPLETE 条件:
  [ ] Context Projection Contract v1.0 FINAL
  [ ] 允许/禁止投影源清单确认
  [ ] Memory ↔ Context 边界确认
  [ ] Reasoning Isolation 边界一致性确认
  [ ] 事件记录格式确认
  [ ] 权限矩阵确认
```

---

## 附录 A: 当前 OpenClaw Context 构建映射

### A.1 现有的 Context 构建点

```yaml
System Instructions:
  OpenClaw 位置: agents.list[].instructions / openclaw.json
  已知投影: ✅ 系统指令
  问题: 格式自由，无 provenance 追踪

Conversation Messages:
  OpenClaw 位置: 运行时会话消息列表
  已知投影: ✅ 消息历史
  问题: 无来源标记，system/user 消息混合

Memory Context:
  OpenClaw 位置: memory_search() → context messages
  已知投影: ✅ (通过 memory search 注入)
  问题: 无显式投影边界，无 provenance 标记

Knowledge Context:
  OpenClaw 位置: memory/knowledge/* 文件内容
  已知投影: ✅ (通过知识查询注入)
  问题: 同 Memory Context

Tool Results:
  OpenClaw 位置: tool 执行后的 function_output
  已知投影: ✅ 工具结果作为消息返回
  问题: 无标准投影格式
```

### A.2 当前架构与 Contract 的差距

| 现有行为 | Contract 要求 | 差距 |
|:---|:---|:---:|
| Memory 自动注入 Context | 显式查询 + provenance | ❌ |
| 无投影事件记录 | 每次投影记录 event | ❌ |
| 无投影生命周期 | 每次投影有 expires_at | ❌ |
| 无投影格式约束 | 3 种格式 + 约束 | ❌ |
| 无禁止投影检查 | 4 个禁止投影源 + 检查表 | ❌ |

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1.0-draft | 2026-07-19 | Context Projection Contract v1.0 DRAFT, 10 章节 + 附录 A |
