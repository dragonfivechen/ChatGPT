# Phase 6.3.3 Runtime Integration Design

**Status:** COMPLETE
**Date:** 2026-07-19
**Dependencies:**
- CONTEXT-PROJECTION-CONTRACT.md v1.0 DRAFT
- context-projection.schema.json v1
- context-projection-bundle.schema.json v1
- context-projection-event.schema.json v1
- PHASE-6.3.2-EVENT-INTEGRATION-DESIGN.md
- OpenClaw system-prompt.ts (buildAgentSystemPrompt)
- OpenClaw plugins/memory-state.ts (buildMemoryPromptSection)
- OpenClaw pi-embedded-runner/run/attempt.ts

---

## 0. Design Principles

### Integration = Interface Definition, Not Implementation

```yaml
本设计定义:
  Context Builder 的接口边界
  投影查询的入口位置
  Bundle 生成流程
  Event 写入位置
  Failure handling 策略
  与现有系统的隔离边界

本设计不定义:
  具体实现代码
  修改现有 Runtime 源码
  增加新依赖
```

### 核心隔离

```yaml
现有管道:
  buildAgentSystemPrompt() ──→ LLM
  buildMemoryPromptSection() ──→ LLM
  system_prompt_report ──→ LLM

新增管道:
  Context Projection ──→ Bundle ──→ Event Store
                     └──→ LLM (通过现有管道)

关键隔离:
  Context Projection 不覆盖现有管道
  Context Projection 在现有管道外层增加治理
  Context Projection Event 是现有诊断事件的新类型
```

---

## 1. 三层集成架构

### 1.1 集成视图

```
┌─────────────────────────────────────────────────────────────┐
│                    Runtime Intelligence Layer                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Layer 3: Context Projection Governance (新增)          ││
│  │                                                         ││
│  │  ContextBuilder.validate()    ← schema check            ││
│  │  ContextBuilder.record()      ← write projection_event  ││
│  │  ContextBuilder.reject()      ← add to violations[]     ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│                            v                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Layer 2: Context Projection Interface (新增)            ││
│  │                                                         ││
│  │  ProjectionSource.resolve()   ← 收集投影源               ││
│  │  ProjectionSource.format()    ← 格式化为标准格式         ││
│  │  BundleBuilder.build()        ← 生成 projection bundle   ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│                            v                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Layer 1: Existing Runtime (保持不变)                    ││
│  │                                                         ││
│  │  buildAgentSystemPrompt()    ← 系统提示                  ││
│  │  buildMemoryPromptSection()  ← 记忆                      ││
│  │  resolveSessionMessages()    ← 会话历史                  ││
│  │  resolveContextEngine()      ← Context Engine            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 1.2 为什么是三层

```yaml
Layer 1 (Existing Runtime):
  不修改。现有构建管道继续工作。
  Context 投影不替换现有逻辑。

Layer 2 (Projection Interface):
  新增接口。定义标准格式出口。
  现有管道产生的数据进入标准格式后
    经过 Layer 3 校验，写入 Event。

Layer 3 (Governance):
  新增校验层。不改变投影内容，只记录。
  validate + record + reject 不阻塞 Runtime。

分离原因:
  Layer 1: 稳定性优先。现有管道经过充分验证。
  Layer 2: 统一格式出口。可逐步接入不同投影源。
  Layer 3: 治理边界。不干扰现有行为。
```

---

## 2. 接口定义

### 2.1 Core Interface

```typescript
// 核心接口 — 只定义类型，不定义实现

interface ProjectionSource {
  /** 投影源标识 (对应 Contract §1.1) */
  readonly kind: 
    | "system_instruction"
    | "conversation_history"
    | "memory"
    | "events"
    | "tool_result"
    | "knowledge"
    | "system_state";

  /** 投影元数据 */
  readonly metadata: {
    /** 查询描述 (文件名/namespace/查询参数) */
    query: string;
    /** 投影条目数 */
    entries: number;
    /** 投影总字符数 */
    totalChars: number;
  };

  /** provenance 信息 */
  readonly provenance: {
    source: string;      // static_config | runtime_session | memory_search | ...
    detail: string;      // 描述
  };

  /** 将源格式化为 LLM 输入 (投影核心操作) */
  toMessage(): { role: string; content: string };
  
  /** 序列化为 event 记录 (仅 metadata, 不含 content) */
  toEventRecord(): ProjectionEventRecord;
}

interface BundleBuilder {
  /** 添加投影源 */
  addSource(source: ProjectionSource): void;
  
  /** 构建 bundle (传递到 LLM) */
  build(): ProjectionBundle;
  
  /** 构建 event (写入 Event Store) */
  buildEvent(requestId: string): ProjectionEvent;
}

interface ProjectionGovernance {
  /** 验证单条投影是否符合 Contract */
  validate(entry: unknown): ValidationResult;
  
  /** 记录 projection_event */
  record(event: ProjectionEvent): void;
  
  /** 记录 violation */
  reject(violation: { source: string; reason: string }): void;
}
```

### 2.2 接口不做什么

```yaml
接口不:
  修改现有 buildAgentSystemPrompt 的返回结果 ❌
  替换现有 memory search 逻辑 ❌
  控制 LLM 的输入顺序 ❌
  过滤或修改现有 provider prompt contribution ❌

接口只:
  标准格式输出现有系统的投影数据 ✅
  记录投影 event ✅
  检测违反 Constract 的投影 ✅
```

---

## 3. 投影查询入口

### 3.1 现有入口映射

```yaml
现有入口:
  A: system_instruction
     来源: buildAgentSystemPrompt() 的输出
     现有类型: 字符串 (text)
     投影入口位置: system prompt 构建完成后

  B: conversation_history
     来源: pi-agent-core 的 session messages
     现有类型: Message[]
     投影入口位置: 消息列表传递给 LLM 前

  C: memory
     来源: buildMemoryPromptSection() 的输出
     现有类型: 字符串 (report section)
     投影入口位置: memory prompt 构建完成后

  D: events
     来源: (当前没有主动事件投影)
     现有类型: 无
     投影入口位置: 需要新增入口点

  E: tool_result
     来源: pi-agent-core 的 tool call responses
     现有类型: ToolMessage[]
     投影入口位置: 工具调用结果返回后

  F: knowledge
     来源: (当前通过记忆查询实现)
     现有类型: memory search result 的子集
     投影入口位置: 与 memory 同位置

  G: system_state
     来源: buildAgentSystemPrompt 中的时间/版本/设备信息
     现有类型: 字符串片段
     投影入口位置: system prompt 构建完成后
```

### 3.2 入口位置

```yaml
理想接入点: attempt.ts 中 prompt 构建完成后 → LLM 调用前

具体位置:
  run attempt() 流程:
    1. resolve system prompt     ← 此处可以捕获 system_instruction + system_state
    2. resolve memory prompt     ← 此处可以捕获 memory + knowledge
    3. resolve session messages  ← 此处可以捕获 conversation_history
    4. resolve tool results      ← 此处可以捕获 tool_result
    --- projection event 写入点 ---
    5. call LLM                  ← LLM 实际看到投影内容

写入点选择:
  必须放在步骤 4 之后、步骤 5 之前
  且是异步非阻塞 (不增加 LLM 延迟)
```

### 3.3 新增入口

```yaml
需要新增的入口点:

D (events projection):
  当前不主动投影事件。
  Phase 6.3 暂不添加主动事件投影。
  原因: Event Projection 需要 Phase 7 (Replay/Event 投喂) 范围。

  辅助方案: 如果 Runtime 需要给 LLM 提供近期事件摘要:
    projection = {
      source: "events",
      query: "last 5 events from memory/events/system/",
      entries: 5,
      content: format_events_as_summary(last_5_events),
      provenance: { source: "runtime_detection", detail: "recent system events" }
    }

  注意: 不投影推理痕迹 (上 Phase 6.1 禁止)
```

---

## 4. Bundle 生成流程

### 4.1 流程

```
Runtime Run Start
    │
    v
[1] Build system prompt
    │   generate: system_instruction projection
    │   generate: system_state projection
    │
    v
[2] Build memory prompt
    │   generate: memory projection
    │   generate: knowledge projection
    │
    v
[3] Build conversation messages
    │   generate: conversation_history projection
    │
    v
[4] Execute tools
    │   generate: tool_result projection
    │
    v
[5] Context Builder: collect all projections
    │
    ├── validate each against schema
    ├── collect violations
    │
    v
[6] Bundle generated
    │
    ├── pass projections to LLM request (现有流程)
    └── write projection_event (新增, 异步)
```

### 4.2 Bundle 内容 (输入 LLM 的实际数据)

```yaml
Bundle 不是新数据结构。
Bundle = 现有 LLM 输入的投影摘要记录:

现有 LLM 输入 = system_prompt + memory_prompt + messages + tool_results

Bundle 描述 = {
  哪些源参与,
  每个源多少数据,
  每个源来自哪里 (provenance),
  需要哪些过期约束
}

Bundle 没有:
  改变 LLM 输入的结构
  增加新层到系统提示
  修改消息顺序
```

---

## 5. Event 写入位置

### 5.1 写入时序

```
LLM 调用前:
  Context Builder 收集 → validate → 生成 bundle → 写入 event
  写入是异步的, 不阻塞 LLM 调用

LLM 调用中:
  Event 已写入 Event Store
  LLM 输出不改变 Event 内容

LLM 调用后:
  Event 不可变
  Event 记录的是 LLM 接收到什么, 不是 LLM 输出了什么
```

### 5.2 写入位置代码级

```yaml
在 attempt.ts 中:

现有:
  const session = await createAgentSession(agent, { sessionMessages })
  const prompt = await buildAgentSystemPrompt({ ... })
  const memoryPrompt = await buildMemoryPromptSection({ ... })
  const fullPrompt = { prompt, memoryPrompt, messages }

  发送到 LLM

新增 (在 发送到 LLM 之前):
  const bundle = await ContextBuilder.collect({ prompt, memoryPrompt, messages, session })
  const event = await ContextBuilder.buildEvent(bundle, requestId)
  ContextBuilder.record(event)  // 异步, 不 await

  发送到 LLM
```

### 5.3 写入确认

```yaml
Event 写入:
  异步 append 到 memory/events/system/context-projection/{date}.md
  主流程不等待写入完成

异常处理:
  写入失败 → 不影响 LLM 调用
  写入失败 → 记录到 Runtime 日志
  写入失败 → 不重试 (Event 丢失不影响运行时)

恢复:
  Governance Audit 可检测 event 缺失
  (对比请求日志和执行日志)
```

---

## 6. Failure Handling

### 6.1 错误分类

```yaml
F1: Projection validation 失败 (违反 Contract)
  处理: 记录 violation 到 event, 不 block 请求
  严重度: WARNING
  示例: memory 投影缺少 provenance

F2: Bundle 构建失败
  处理: 跳过 Event 记录, 不 block LLM 请求
  严重度: WARNING
  示例: bundle schema 与 event schema 不匹配

F3: Event 写入失败
  处理: 不 block LLM 请求, 不重试
  严重度: INFO (持续失败则升级)
  示例: 文件锁冲突、磁盘满

F4: 投影源无法解析
  处理: 跳过该源, 不 block 其他源
  严重度: WARNING
  示例: memory search 查询超时

F5: Contract 严重违反 (P0)
  处理: 记录 violation, 记录 Governance Alert
  严重度: ALERT
  示例: secrets 出现在 LLM 输入中
```

### 6.2 分级响应

```yaml
级别 | 条件                  | 响应
─────┼───────────────────────┼─────────────────────
INFO | Event 写入失败        | 不处理
WARN | validation 失败       | 记录 violation
WARN | 投影源解析失败         | 跳过该源
WARN | bundle 构建失败        | 跳过 event
ALERT| P0 violation 检测     | 记录 + 告警

所有级别:
  不中断 LLM 请求
  不影响现有 pipeline
```

### 6.3 不可修复的错误

```yaml
Runtime Integration 不引入"修复"机制:
  不自动补全缺失的 provenance
  不自动替换禁止的投影源
  不自动重试失败的投影查询

原因:
  Context Builder 记录事实, 不改变事实
  修复属于 Governance / 配置管理
```

---

## 7. 与现有系统的隔离

### 7.1 Memory Search

```yaml
现有 memory search:
  流程: memory_search() → prompt section → LLM
  位置: memory-state.ts

Context Projection:
  流程: memory_search() → prompt section → Context Builder → Event

隔离:
  Context Projection 不改变 memory search 的输入/输出
  Context Projection 只在 memory search 完成后读取结果
  memory search 不用知道 Context Projection 存在

现有 memory search 的保持:
  buildMemoryPromptSection() 返回值不变
  memory citations 功能不变
  memory governance writer boundary 不变
```

### 7.2 Session Context

```yaml
现有 session context:
  session.messages → LLM

Context Projection:
  session.messages → Context Builder → Event

隔离:
  Context Projection 不修改 session messages
  Context Projection 不查看 session 状态
  session 的 compaction/truncation 不受影响
```

### 7.3 Context Engine

```yaml
现有 context-engine:
  resolveContextEngineOwnerPluginId() → context injection
  delegate.ts → context assembly

Context Projection:
  暂不接入 context-engine
  原因: context-engine 是 OpenClaw 内部系统
        Phase 6.3 在外部治理层
        context-engine 接入属于实现阶段
```

### 7.4 Provider System Prompt

```yaml
现有 provider contribution:
  resolveProviderSystemPromptContribution() → prompt injection
  transformProviderSystemPrompt() → prompt modification

Context Projection:
  不遮挡 provider contribution
  provider contribution 作为 system_instruction 的一部分被投影
  Event 记录中有 system_instruction 的投影统计
```

---

## 8. 集成验证

### 8.1 验证场景

```yaml
S1: 正常请求
  输入: 用户消息 + session history + memory
  预期: 
    bundle = [system_instruction, conversation_history, memory]
    event 写入
    LLM 正常调用
  验证: event 包含 3 条 projections

S2: 无 memory 投影
  输入: 用户消息 + 空 memory
  预期:
    bundle = [system_instruction, conversation_history]
    event 写入 (仅 2 条)
    LLM 正常调用
  验证: event 正确反映投影源数量

S3: 违反 Contract
  输入: 投影中缺少 provenance
  预期:
    violation 记录
    缺 provenance 的投影被拒绝
    合法投影正常构建
    LLM 正常调用
  验证: event.violations[] 非空

S4: Event 写入失败
  输入: event store 不可写
  预期:
    LLM 正常调用
    Runtime 日志记录写入失败
  验证: 请求正常完成

S5: 投影源全部空
  输入: 无 session history, 无 memory, 无 system instruction
  预期:
    bundle 最少包含 1 条 (system_instruction)
    如果是 test 场景: 至少 system_state
    event 写入
  验证: bundle.minItems >= 1
```

### 8.2 集成检查表

```yaml
Phase 6.3.3 COMPLETE 条件:
  [ ] 三层架构定义完成 (§1)
  [ ] 接口类型定义完成 (§2)
  [ ] 投影入口映射完成 (§3)
  [ ] Bundle 生成流程定义完成 (§4)
  [ ] Event 写入位置定义完成 (§5)
  [ ] Failure handling 策略定义完成 (§6)
  [ ] 与现有系统的隔离确认 (§7)
  [ ] 验证场景定义完成 (§8)
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Phase 6.3.3 Runtime Integration Design, 8 章节 |
