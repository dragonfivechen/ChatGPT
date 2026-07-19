# Phase 7.2 Boundary Enforcement Matrix v1.0

**Phase 7 — DRAFT**
**Date:** 2026-07-19
**Status:** DRAFT
**前置条件:** Phase 7.1 Audit Contract 🔒 FROZEN

---

## §0 定位

### Phase 7.2 是什么

```
Phase 7.1: 定义要验证什么         ← FROZEN
Phase 7.2: 确认边界在源码中存在    ← CURRENT

B 不是新架构设计。
B 是边界验证:
  每条边界:
    Contract 声明
      ↓ 源码中是否存在对应的 Enforcement Point
    Evidence
      ↓
    Boundary Status (EXISTS / MISSING / BYPASSABLE)
```

### 边界定义

```
Boundary = Contract 定义的"应该在这里检查"的逻辑分界点

例:
  Contract: LLM tool call 必经 Gateway
  Boundary: attempt.ts 中 tool_calls → execute() 之间的 intercept point
  Enforcement: Gateway.intercept() 是否存在, 是否必经
```

### 不做什么

```
❌ 修改 Phase 6 Contract
❌ 修改 Phase 7.1 Audit Contract
❌ 自动修复/self-healing
❌ LLM 参与判断
❌ 性能/基准测试
❌ 实现实现
```

---

## §1 五条边界

### 1.1 Plugin → Tool Gateway

| 字段 | 值 |
|:---|:---|
| **Owner** | Tool Gateway |
| **Boundary** | Plugin 发起的 tool call 必须经过 Tool Call Gateway |
| **Contract 引用** | Phase 6.4 §2: Gateway 是 LLM tool call 统一入口 (G-001) Extension Boundary (Phase 1): Plugin 不可直接调用 Runtime 核心 API |
| **Entry Point** | `src/plugins/tools.ts` → `registerTool.registerTool` → `tool.execute()` |
| **Bypass Risk** | Plugin 内部直接调用 `tool.execute()` 绕过 Gateway |
| **Enforcement Point** | Gateway.intercept() 在 Plugin tool 路径上 |
| **Evidence** | call-graph + source snapshot + tool invocation trace |
| **PASS Condition** | 所有 Plugin tool 调用路径必经 Gateway, 零直接调用 execute() |
| **Phase 7.1 关联** | TC-01, TC-02, TC-06 |

### 1.2 Worker → Runtime Policy

| 字段 | 值 |
|:---|:---|
| **Owner** | Governance Kernel (Runtime Policy) |
| **Boundary** | External Worker 调用 Runtime 功能必须遵循 Runtime Policy (Capability Enforcement / Context Projection / Event) |
| **Contract 引用** | Phase 6.2 §3: Capability Enforcement 覆盖 Runtime 所有入口 Phase 6.3 §4: Context Projection 覆盖 Context 所有生产者 |
| **Entry Point** | Worker 脚本 → `openclaw` API / 直接文件系统 / Provider API |
| **Bypass Risk** | Worker 直接调用 Provider API (不经过 Gateway), 直接读文件系统 (不经过 Context Projection) |
| **Enforcement Point** | Worker 入口 → Runtime Policy 检查点 |
| **Evidence** | call-graph + source snapshot + runtime sample |
| **PASS Condition** | Worker 调用 Runtime 的所有路径存在 Policy 检查点, 零绕过 |
| **Phase 7.1 关联** | CP-04, TC-06, CR-03 |

### 1.3 Capability → Registry

| 字段 | 值 |
|:---|:---|
| **Owner** | Capability Registry |
| **Boundary** | Capability 的注册、查询、执行必须经过 Provider Capability Registry |
| **Contract 引用** | Phase 6.2 §2: Registry 是 Capability 的唯一权威来源 CR-01/CR-02/CR-03/CR-04 |
| **Entry Point** | `provider-transport-stream.ts`, `openai-completions-compat.ts`, `model-auth-markers.ts` |
| **Bypass Risk** | Provider 直接调用能力函数而不查询 Registry |
| **Enforcement Point** | 每条 provider 调用路径上的 registry.query() 或等效检查 |
| **Evidence** | call-graph + diff (registry vs 实现) + trace |
| **PASS Condition** | 所有 capability 调用路径必经 Registry 查询, 零未注册能力执行 |
| **Phase 7.1 关联** | CR-01, CR-02, CR-03, CR-04 |

### 1.4 Context → Projection

| 字段 | 值 |
|:---|:---|
| **Owner** | Context Projection Layer |
| **Boundary** | 所有进入 LLM 的 Context 内容必须经过 Context Projection Interface |
| **Contract 引用** | Phase 6.3 §2: Projection 是 Context 的唯一合法构造路径 CP-01/CP-02 |
| **Entry Point** | `system-prompt.ts`, `memory` 插件, `session` 数据, `event` 数据 |
| **Bypass Risk** | 文件直接读, Worker 直接注入, Memory 直接组装 |
| **Enforcement Point** | Context 构建路径上的 Projection Interface 检查点 |
| **Evidence** | call-graph + trace + source snapshot |
| **PASS Condition** | 所有 Context 入口路径必经 Projection, 零直接注入 |
| **Phase 7.1 关联** | CP-01, CP-02, CP-03, CP-04 |

### 1.5 Event → Truth Boundary

| 字段 | 值 |
|:---|:---|
| **Owner** | Event Kernel |
| **Boundary** | Event 记录必须反映实际 Runtime 行为, 不遗漏、不虚报 |
| **Contract 引用** | Phase 6.3 §3, Phase 6.4 §4: Event = Truth |
| **Entry Point** | project_event 写入点, gateway_event 写入点, enforcement_event 写入点 |
| **Bypass Risk** | Event 写入异步丢失, Event 路径遗漏, Event 不完整 |
| **Enforcement Point** | Event 写入确认点, Event 计数与 decision 1:1 |
| **Evidence** | sample + trace + diff |
| **PASS Condition** | Event 记录与 Runtime 行为一致: decision 数 = event 数, 无未记录行为 |
| **Phase 7.1 关联** | R-04, TC-04, CP-02, CP-03 |

---

## §2 边界矩阵

### 2.1 汇总矩阵

| Boundary | Entry Point | Bypass Risk | Enforcement Point | Priority |
|:---|:---|:---|:---:|:---:|
| B1: Plugin → Gateway | `src/plugins/tools.ts` | 直接调用 execute() | Gateway.intercept() | **HIGH** |
| B2: Worker → Policy | Worker 脚本入口 | 直接调用 Provider/文件读 | Runtime Policy 检查点 | **HIGH** |
| B3: Capability → Registry | Provider transport | 未注册能力执行 | registry.query() | MEDIUM |
| B4: Context → Projection | system-prompt / memory | 直接注入 | Projection Interface | **HIGH** |
| B5: Event → Truth | event 写入点 | 异步丢失 / 遗漏 | event 确认点 | MEDIUM |

### 2.2 优先级判定

```
HIGH:
  - 绕过直接导致 Phase 6 契约失效
  - 绕过路径存在且可达
  - 影响安全/治理

MEDIUM:
  - 绕过导致契约验证降级
  - 但不直接影响 LLM 路径
  - 可通过审计发现

LOW:
  - 理论上可绕过
  - 无实际代码路径
  - 属于第二阶段验证
```

---

## §3 验证方法

### 3.1 每条边界的验证流程

```
Step 1: 定位边界
  - 找到 Contract 声明的边界点
  - 映射到源码文件/行号
  - 确认入口和出口

Step 2: 构建调用链
  - trace: 入口 → 边界 → 出口 的代码路径
  - call-graph: 确认所有路径都经过 Enforcement Point

Step 3: 验证 Enforcement
  - Enforcement Point 是否存在
  - 是否在必经路线上
  - 是否可绕过 (有直接路径)

Step 4: 记录 Evidence
  - trace 输出: 函数调用链
  - call-graph: 静态调用关系
  - diff: Contract vs 实现的差异

Step 5: 判定
  - EXISTS: Enforcement Point 存在且必经
  - MISSING: Enforcement Point 不存在
  - BYPASSABLE: Enforcement Point 存在但可绕过
```

### 3.2 判定规则 — 🔒 FROZEN

**枚举固定为三态:**

```yaml
EXISTS:
  定义:
    = Enforcement Point 在源码中找到
    + 位于必经路线
    + 零直接绕过路径
  含义:
    = Contract 边界在源码中存在
  对应 Phase 7.1:
    = 对应审计项 PASS (待证据收集)

MISSING:
  定义:
    = Contract 声明了边界
    - 对应 Enforcement Point 在源码中不存在
  含义:
    = Contract 边界在源码中缺失
  对应 Phase 7.1:
    = 对应审计项将 FAIL
  处置:
    不自动修复
    记录缺口
    标记 Phase 7.3/7.4

BYPASSABLE:
  定义:
    = Enforcement Point 在源码中找到
    + 存在绕过路径 (不走 Enforcement Point)
  含义:
    = 边界存在但可绕过
  对应 Phase 7.1:
    = 对应审计项将触发 bypass 记录
  处置:
    记录绕过路径
    标记 Phase 7.3 Bypass Closure 范围
```

**约束:**

```yaml
EXISTS / MISSING / BYPASSABLE 是互斥三态:
  - 不能同时为两个
  - 每条边界的判定只能选其一
  - 判定后不可中途退回到"未判定"

三态模型与 Phase 7.1 结论模型对应:
  EXISTS  ↔ PASS (证据收集后)
  MISSING ↔ FAIL
  BYPASSABLE ↔ FAIL (bypass 路径触发)
```

### 3.3 偏差处理

```yaml
MISSING:
  记录: "Boundary X: Enforcement Point 缺失"
  影响: Phase 6 Contract 在运行时无对应检查
  结论: FAIL (Phase 7.1 审计项对应)
  处置: 不自动修, 标记 Phase 7.3/7.4

BYPASSABLE:
  记录: "Boundary X: 绕过路径 Y 存在"
  影响: Contract 不变量在绕过路径上不成立
  结论: 对应审计项 → 记录 bypass 路径
  处置: Phase 7.3 Bypass Closure
```

---

## §4 输出格式

### 4.1 每条边界的输出

```
Boundary: [B1] Plugin → Tool Gateway
Status: EXISTS / MISSING / BYPASSABLE
Evidence:
  trace: attempt.ts:line -> plugins/tools.ts:line -> execute():line
  call-graph: [call-graph output]
  bypass-check: [bypass paths or "none found"]
Enforcement Point: Gateway.intercept() at attempt.ts:line
Bypass Paths: [list or "none detected"]
Recommendation: [for BYPASSABLE only]
```

### 4.2 汇总报告

```
Boundary Enforcement Matrix v1.0 — 结果

B1 Plugin → Gateway:        EXIST / MISSING / BYPASSABLE
B2 Worker → Policy:          EXIST / MISSING / BYPASSABLE
B3 Capability → Registry:    EXIST / MISSING / BYPASSABLE
B4 Context → Projection:     EXIST / MISSING / BYPASSABLE
B5 Event → Truth:            EXIST / MISSING / BYPASSABLE

缺口清单:
  - Boundary X: MISSING
  - Boundary Y: BYPASSABLE (路径 Z)

Phase 7.3 输入:
  - bypass 路径: [list]
```

---

## §6 Exit Criteria

Phase 7.2 COMPLETE 必须满足:

```yaml
[1] Boundary IDs frozen
    五条边界编号固定:
      B1 Plugin → Gateway
      B2 Worker → Policy
      B3 Capability → Registry
      B4 Context → Projection
      B5 Event → Truth
    无未经确认的新增边界

[2] Owner defined
    每条边界的 Owner 已定义:
      B1: Tool Gateway
      B2: Governance Kernel
      B3: Capability Registry
      B4: Context Projection Layer
      B5: Event Kernel
    后续发现 FAIL 时, Owner 负责维护

[3] Enforcement Point located
    每条边界的 Enforcement Point 已在源码中定位
    (文件路径 + 函数/行范围)

[4] Call path mapped
    每条边界的完整调用链已构建:
      入口 → Enforcement Point → 出口
      确认是否必经

[5] Evidence collected
    每条边界的证据已采集:
      call-graph / trace / source snapshot / diff / runtime sample
    证据类型与定义一致

[6] Result classified
    每条边界的判定已完成:
      EXISTS / MISSING / BYPASSABLE
    三态互斥, 不存在同时两个

[7] No automatic modification performed
    验证过程中零自动修改:
      - 不改源码
      - 不改 Contract
      - 不改 Schema
      - 不改 Event
      - 不改 Registry

[8] Exit confirmed by Brother Long
    Matrix 冻结
    进入 Phase 7.3 Bypass Closure
```

---

## §5 与 Phase 7.1 的关系

### 5.1 映射

| Phase 7.1 Audit Item | Phase 7.2 Boundary | 关系 |
|:---|:---|:---|
| TC-01, TC-02, TC-06 | B1 Plugin → Gateway | Gateway 必经 + 不执行 + 绕过检测 |
| CP-04, TC-06, CR-03 | B2 Worker → Policy | Worker bypass + 绕过检测 |
| CR-01~CR-04 | B3 Capability → Registry | Registry 一致性 + 必经 |
| CP-01~CP-04 | B4 Context → Projection | Projection 必经 + bypass gap |
| R-04, TC-04, CP-02, CP-03 | B5 Event → Truth | Event 完整性 + 一致性 |

### 5.2 先后关系

```
Phase 7.1 (定义) → Phase 7.2 (验证) → Phase 7.3 (闭环)

7.1: Audit Items
   ↓ 定义
7.2: Boundary Enforcement Matrix
   ↓ 验证
      [EXISTS] → 证据收集 → 7.5 Integrity Freeze
      [MISSING] → 缺口记录 → 7.3/7.4
      [BYPASSABLE] → 绕过路径 → 7.3 Bypass Closure
```

---

---

## §7 验证结果与证据

### 7.1 B1 Plugin → Gateway — 验证结果

| 字段 | 值 |
|:---|:---|
| **Status** | 🟥 **MISSING** + ⚠️ **BYPASSABLE** |
| **Verification Date** | 2026-07-19 |
| **Verification Method** | Source code call-graph trace |

#### 预期路径

```
LLM tool_call
  ↓
agent-loop.js: prepareToolCall
  ↓
Gateway.intercept()           ← Phase 6.4 Contract 要求的 Enforcement Point
  ↓
executePreparedToolCall
  ↓
tool.execute()
```

#### 实际路径

```
LLM tool_call
  ↓
agent-loop.js:255 → executeToolCallsParallel/Sequential
  ↓
agent-loop.js:360 → prepareToolCall (includes before_tool_call hooks)
  ↓
agent-loop.js:419 → executePreparedToolCall
  ↓
prepared.tool.execute()
  ↓
[NO Gateway intercept]
```

#### Enforcement Point 检查

| 检查项 | 结果 |
|:---|:---|
| Gateway.intercept() 在 agent-loop.js | ❌ 不存在 |
| before_tool_call hooks 作为 Gateway 替代 | ⚠️ Plugin SDK 特性, 非 Phase 6.4 Gateway |
| hook 拦截能力 (修改/拒绝) | ⚠️ 存在, 但被用于工具参数转换, 非 Gateway 决策 |
| Gateway 代码存在 | ✅ `TOOL-CALL-GATEWAY-CONTRACT.md` + schemas 存在 |
| Gateway 在执行路径 | ❌ 不在 agent-loop.js → tool.execute() 路径 |

#### 绕过路径

**B1-BP1 — agent-loop.js direct execute**
```
agent-loop.js:419 executePreparedToolCall
  ↓
prepared.tool.execute()
  ↓
结果: tool 直接执行, 不经 Gateway
```

**B1-BP2 — Plugin internal direct execute**
```
createCachedDescriptorPluginTool
  ↓
resolvePluginToolRegistry
  ↓
entry.factory(ctx)
  ↓
matchedTool.execute()
  ↓
结果: Plugin tool 不走 agent-loop, 不经 Gateway
```

#### 证据

- `agent-loop.js` line 255: executeToolCalls entry
- `agent-loop.js` line 360: prepareToolCall (before_tool_call hooks)
- `agent-loop.js` line 419: executePreparedToolCall → tool.execute()
- `src/plugins/tools.ts`: createCachedDescriptorPluginTool → direct execute path
- Gateway Contract: Phase 6.4 §2 G-001 (Gateway 是唯一入口)

#### 结论

```
MISSING:
  Gateway.intercept() 在 agent-loop.js 执行路径中不存在
  0 行代码对应 Gateway 决策层

BYPASSABLE:
  B1-BP1: agent-loop.js 直接执行
  B1-BP2: Plugin 内部直接执行

两者均不经过 Gateway
```

---

### 7.2 B2 Worker → Policy — 验证结果

| 字段 | 值 |
|:---|:---|
| **Status** | 🟡 **PARTIAL** + 🟥 **MISSING** + ⚠️ **BYPASSABLE** |
| **Verification Date** | 2026-07-19 |
| **Verification Method** | Source code call-graph trace |

#### 预期路径

```
Worker / Subagent Tool Call
  ↓
Policy Enforcement
  ↓
Capability Check
  ↓
Tool Execution
```

#### 实际路径

```
subagent-spawn.ts:697
  ↓
runEmbeddedAttempt
  ↓
collectAttemptExplicitToolAllowlistSources
  ↓
applyToolPolicyPipeline (registration time)
  ↓
filterToolsByPolicy
  ↓
registered tools
  ↓
LLM tool_calls → agent-loop.js
  ↓
prepareToolCall
  ↓
tool.execute()
  ↓
[NO execution-time policy re-check]
```

#### Enforcement Point 检查

| 检查项 | 结果 |
|:---|:---|
| tool-policy-pipeline.ts 存在 | ✅ `tool-policy-pipeline.ts:117` applyToolPolicyPipeline |
| filterToolsByPolicy 存在 | ✅ 注册时工具过滤 |
| resolveSubagentToolPolicyForSession 存在 | ✅ 子 agent 策略解析 |
| resolveInheritedToolPolicyForSession 存在 | ✅ 继承策略解析 |
| 执行时每调用重新检查 policy | ❌ 不存在 |
| pi-tools.policy.ts 执行时检查 | ⚠️ 工具级别, 非 policy 级别 |

#### 绕过路径

**B2-BP1 — Cross-agent spawn bypass**
```
subagent-spawn.ts
  ↓
subagent.SPAWN_TOOLS
  ↓
bypass tool-policy-pipeline registration-time filtering
  ↓
结果: spawn 的 agent 可携带超出 parent policy 的工具
```

**B2-BP2 — Plugin internal direct execute**
```
Plugin tool registration
  ↓
tool.execute() directly
  ↓
不在 agent-loop 路径
  ↓
结果: 不经 policy pipeline, 不经 policy 检查
```

**B2-BP3 — Registration-to-execution gap**
```
Registration: 工具列表经 policy pipeline 过滤 (时间 T1)
  ↓
Execution: LLM tool_call → tool.execute() (时间 T2)
  ↓
T1 → T2 之间无 policy re-check
  ↓
结果: policy 在注册时检查, 执行时不检查
```

#### 证据

- `src/agents/tool-policy-pipeline.ts`:117: applyToolPolicyPipeline
- `src/agents/subagent-spawn.ts`:697: runEmbeddedAttempt
- `src/agents/pi-tools.policy.ts`: 工具策略
- `src/agents/pi-embedded-subscribe.ts`: runToolLifecycle wrapper
- `agent-loop.js`:419: tool.execute() — 执行时无 policy 检查

#### 结论

```
EXISTS (partial):
  - tool-policy-pipeline.ts 注册时过滤
  - resolveSubagentToolPolicyForSession
  - resolveInheritedToolPolicyForSession

MISSING:
  - 每调用执行时 policy 重新检查
  - 工具执行前最后一道 policy 关卡

BYPASSABLE:
  - B2-BP1: cross-agent spawn bypass
  - B2-BP2: plugin internal direct execute
  - B2-BP3: registration-time only, execution-time gap
```

---

### 7.3 B3 Capability → Registry — 验证结果

| 字段 | 值 |
|:---|:---|
| **Status** | 🟡 **PARTIAL** + 🟥 **MISSING** + ⚠️ **BYPASSABLE** |
| **Verification Date** | 2026-07-19 |
| **Verification Method** | Source code call-graph trace |

#### 预期路径

```
Capability Request
  ↓
Capability Registry (Phase 6.2 Contract)
  ↓
Validation
  ↓
Provider Runtime
  ↓
Execution
```

#### 实际路径 (工具创建时)

```
createImageGenerateTool (image-generate-tool.ts)
  ↓
hasGenerationToolAvailability
  ↓
检查 Registry ManifestSnapshot / plugin manifest contracts
  ↓
确认 capability 可用性
  ↓
工具注册
```

#### 实际路径 (工具执行时)

```
tool.execute()
  ↓
resolveImageGenerationModelConfigForTool
  ↓
resolveCapabilityModelConfigForTool
  ↓
listRuntimeImageGenerationProviders
  ↓
listImageGenerationProviders (image-generation/provider-registry.ts)
  ↓
resolvePluginImageGenerationProviders
  ↓
capabilityProviderRuntime.resolvePluginCapabilityProviders
  ↓                    ← Registry (provider-capability-registry.ts) 不在这个路径上
 ↓
Provider Runtime
```

#### Registry ↔ Runtime 分离

```
Registry (Phase 6.2 Contract):
  media-understanding/provider-capability-registry.ts
  → 声明式 metadata 快照
  → 不参与执行路径

Runtime Provider Resolver (operational):
  image-generation/provider-registry.ts
  + plugins/capability-provider-runtime.ts
  → 实际 provider 发现
  → 不经过 Registry 查询
  → 无强制同步桥接
```

| 检查项 | 结果 |
|:---|:---|
| Provider Capability Registry 存在 | ✅ `media-understanding/provider-capability-registry.ts` |
| Registry 在执行路径 | ❌ 不在执行路径 |
| Runtime Provider Resolver 存在 | ✅ `image-generation/provider-registry.ts` + `capability-provider-runtime.ts` |
| Registry ↔ Runtime 强制同步 | ❌ 无强制同步 |
| 工具创建时检查 Registry | ✅ `hasGenerationToolAvailability` |
| 工具执行时检查 Registry | ❌ 使用 Runtime Resolver |

#### 绕过路径

**B3-BP1 — Plugin 直接注册到 Runtime Resolver**
```
resolvePluginCapabilityProviders
  ↓
capabilityProviderRuntime.resolvePluginCapabilityProviders
  ↓
直接注册到 Runtime provider 列表
  ↓
结果: 不经过 Registry, 直接到运行时
```

**B3-BP2 — 创建时检查 ≠ 执行时检查**
```
创建时 (T1):
  hasGenerationToolAvailability → manifest 声明有 provider → PASS
  ↓
执行时 (T2):
  运行时 auth 可能失效, provider 可能不可用
  但这不是 Registry 拦截, 而是运行时错误
```

**B3-BP3 — Registry ↔ Runtime 可以分歧**
```
Registry 声明: Provider X 有 capability Y
Runtime Resolver: Provider X 实际可解析 Z
无强制同步 → 两者可以有分歧
```

#### 证据

- `src/media-understanding/provider-capability-registry.ts`: 正式 Registry
- `src/image-generation/provider-registry.ts`: 运行时 provider 解析
- `src/plugins/capability-provider-runtime.ts`: 插件 capability 运行时
- `src/agents/tools/image-generate-tool.ts`: createImageGenerateTool → hasGenerationToolAvailability
- `src/agents/tools/media-tool-shared.ts`: resolveImageGenerationModelConfigForTool → resolveCapabilityModelConfigForTool → listRuntimeImageGenerationProviders

#### 结论

```
EXISTS (partial):
  - Registry 代码存在 (provider-capability-registry.ts)
  - 创建时 Manifest Snapshot 检查 (hasGenerationToolAvailability)
  - 执行时 Runtime Provider Resolver (listRuntimeImageGenerationProviders)

MISSING:
  - Registry 不在执行路径
  - 执行使用 Runtime Provider Resolver, 不是 Phase 6.2 Registry
  - Registry 是声明式 metadata, 不是强制执行关卡

BYPASSABLE:
  - B3-BP1: 直接注册到 Runtime Resolver
  - B3-BP2: 创建时检查 ≠ 执行时保证
  - B3-BP3: Registry ↔ Runtime 无强制同步
```

---

### 7.4 B4 Context → Projection — 验证结果

| 字段 | 值 |
|:---|:---|
| **Status** | 🟡 **EXISTS (design only)** + 🟥 **MISSING** + ⚠️ **BYPASSABLE** |
| **Verification Date** | 2026-07-19 |
| **Verification Method** | Source code call-graph trace |

#### 预期路径

```
Context Sources (memory / event / state)
  ↓
Context Projection Layer
  ↓
validate
  ↓
format
  ↓
bundle
  ↓
record
  ↓
LLM Context
```

#### 实际路径

```
Session History
  ↓
Message Assembly
  ↓
buildAttemptSystemPrompt (attempt-system-prompt.ts)
  ↓
buildEmbeddedSystemPrompt
  ↓
buildConfiguredAgentSystemPrompt
  ↓
buildAgentSystemPrompt (system-prompt.ts:670)
  ↓
+ buildMemoryPromptSection (memory-state.ts)
+ runtimeInfo
+ tool summaries
  ↓
systemPromptText
  ↓
LLM provider.sendMessages({ system: systemPromptText })
  ↓
[NO Context Projection governance layer]
```

#### Context Engine Plugin 路径

```
assembleAttemptContextEngine (attempt.ts:3087)
  ↓
harness/context-engine-lifecycle.ts
  ↓
Plugin can REPLACE systemPrompt
  ↓
绕过 Projection 直接到 LLM
```

#### Enforcement Point 检查

| 检查项 | 结果 |
|:---|:---|
| Context Projection Contract | ✅ `CONTEXT-PROJECTION-CONTRACT.md` |
| Schema 文件 | ✅ `context-projection.schema.json`, `-bundle.schema.json`, `-event.schema.json` |
| Runtime Implementation | ❌ **0 行执行代码** |
| contextProjection 类型引用 | ⚠️ 仅1处: `context-engine/types.ts` 类型定义 |
| Context Validation Point | ❌ 不存在 |
| Context Formatting Boundary | ❌ 不存在 |
| Context Bundle Record | ❌ 不存在 |
| Unified Context Exit | ❌ 不存在 |
| Memory 中间验证 | ❌ 不存在 |

#### 绕过路径

**B4-BP1 — Direct system prompt assembly**
```
buildEmbeddedSystemPrompt
  ↓
buildAgentSystemPrompt
  ↓
systemPromptText
  ↓
LLM
  ↓
结果: Context 直接组装, 不经过 Projection
```

**B4-BP2 — Context Engine Plugin replacement**
```
assembleAttemptContextEngine
  ↓
context-engine-lifecycle
  ↓
Plugin custom prompt
  ↓
LLM
  ↓
结果: 独立 Context 出口, 绕过 Projection
```

**B4-BP3 — Direct memory injection**
```
buildMemoryPromptSection (memory-state.ts)
  ↓
读取 MEMORY.md + memory/*.md
  ↓
直接追加到 system prompt
  ↓
结果: Memory source 未经 Context Governance
```

#### 证据

- `src/agents/pi-embedded-runner/run/attempt-system-prompt.ts`: buildAttemptSystemPrompt
- `src/agents/pi-embedded-runner/system-prompt.ts:670`: buildAgentSystemPrompt
- `src/plugins/memory-state.ts`: buildMemoryPromptSection
- `src/agents/pi-embedded-runner/run/attempt.ts:3087`: assembleAttemptContextEngine
- `src/agents/pi-embedded-runner/run/attempt.context-engine-helpers.ts`: 上下文引擎
- `harness/context-engine-lifecycle.ts`: engine lifecycle
- `context-engine/types.ts`: 唯一 contextProjection 引用
- Schema files: `context-projection.schema.json`, `-bundle.schema.json`, `-event.schema.json`
- Design doc: `PHASE-6.3.3-RUNTIME-INTEGRATION-DESIGN.md`

#### 结论

```
EXISTS (design only):
  - Context Projection Contract 存在
  - Schema 文件存在
  - Context assembly pipeline 存在
  - 但: Schema / Design ≠ Runtime Enforcement

MISSING:
  - Context Projection Runtime Layer: 0 行代码在执行路径
  - 执行路径: Source → Assembly → LLM (无 Projection 层)
  - 预期: Source → Projection → Bundle → LLM

BYPASSABLE:
  - B4-BP1: system prompt direct assembly
  - B4-BP2: context engine replacement
  - B4-BP3: memory direct injection
```

---

### 7.5 B5 Event → Truth — 验证结果

| 字段 | 值 |
|:---|:---|
| **Status** | 🟡 **PARTIAL** + 🟥 **MISSING** + ⚠️ **BYPASSABLE** |
| **Verification Date** | 2026-07-19 |
| **Verification Method** | Source code call-graph trace |

#### 预期路径

```
Runtime Action
  ↓
Event Generation
  ↓
Immutable Record
  ↓
Truth Verification
```

#### 事件基础设施

```
Agent Events:
  emitAgentEvent (infra/agent-events.ts:209)
    ├── stream: "lifecycle"  (tool_execution_start/end)
    ├── stream: "item"       (assistant/tool results)
    ├── stream: "plan"       (agent plans)
    ├── stream: "approval"   (approval requests)
    └── stream: "command_output" / "patch"

Diagnostic Events:
  emitTrustedDiagnosticEvent (infra/diagnostic-events.ts)
    ├── type: "model.usage" / "model.failover"
    ├── type: "run.attempt" / "run.progress"
    ├── type: "session.state" / "queue.*" / "webhook.*"
    └── type: "diagnostic.heartbeat" / "session.recovery.*"

Lifecycle Events:
  runToolLifecycle (pi-embedded-subscribe.ts:1064)
    ├── handleToolExecutionStart → emit lifecycle event
    ├── tool.execute()
    └── handleToolExecutionEnd → emit lifecycle event
```

#### 事件路径 vs 执行路径

```
Primary Path (attempt.ts:3269):
  toolSearchCatalogExecutor
    ↓
  runToolLifecycle(operation)
    ├── EMIT: handleToolExecutionStart
    ├── await tool.execute()
    └── EMIT: handleToolExecutionEnd
  → 生命周期事件 emitted ✅

B1 Bypass Path (agent-loop.js:419 direct execute):
  executePreparedToolCall
    ↓
  prepared.tool.execute()
    ↓
  NO runToolLifecycle wrapper
  → 无生命周期事件 ❌

B1 Bypass Path (Plugin internal direct):
  matchedTool.execute()
    ↓
  NO agent-loop, NO runToolLifecycle
  → 无任何事件 ❌
```

#### Enforcement Point 检查

| 检查项 | 结果 |
|:---|:---|
| Agent Event System 存在 | ✅ emitAgentEvent multi-stream |
| Diagnostic Event System 存在 | ✅ emitTrustedDiagnosticEvent |
| Lifecycle Events (主路径) | ✅ runToolLifecycle wrapper |
| 全部执行路径覆盖 | ❌ bypass 路径无事件 |
| 事件验证执行正确性 | ❌ events are observational |
| 事件不可篡改 | ❌ fire-and-forget, no immutability |
| 事件 ↔ 执行证明链 | ❌ no proof chain |
| Event Store 完整性 | ❌ listeners only |
| Phase 6 设计事件 emit | ❌ schemas 存在, 未 emit |

#### 绕过路径

**B5-BP1 — Direct tool execute bypass events**
```
agent-loop.js:419
  ↓
tool.execute()
  ↓
无 runToolLifecycle
  ↓
结果: 无生命周期事件
```

**B5-BP2 — Plugin internal execute bypass events**
```
matchedTool.execute() (plugin internal)
  ↓
不在 agent-loop 路径
不在 runToolLifecycle 路径
  ↓
结果: 无任何事件
```

**B5-BP3 — Fire-and-forget, no truth verification**
```
emitAgentEvent() / emitTrustedDiagnosticEvent()
  ↓
notifyListeners(listeners, enriched)
  ↓
Fire-and-forget
  ↓
无机制验证:
  - 事件 data 是否匹配实际执行结果
  - 事件 ts 是否匹配实际时间窗
  - 事件 seq 是否连续无缺失
```

**B5-BP4 — Phase 6 event schemas not emitted**
```
tool-call-event.schema.json               → 存在, 未 emit
context-projection-event.schema.json      → 存在, 未 emit
gateway-decision.schema.json              → 存在, 未 emit
```

#### 证据

- `src/infra/agent-events.ts`: emitAgentEvent, notifyListeners
- `src/infra/diagnostic-events.ts`: emitTrustedDiagnosticEvent
- `src/agents/pi-embedded-subscribe.ts`:1064: runToolLifecycle
- `src/agents/pi-embedded-subscribe.handlers.tools.ts`:673: handleToolExecutionStart
- `src/agents/pi-embedded-subscribe.handlers.tools.ts`:919: handleToolExecutionEnd
- `src/shared/listeners.ts`: notifyListeners (fire-and-forget)
- `agent-loop.js`:419: executePreparedToolCall → tool.execute()
- `src/agents/pi-embedded-runner/run/attempt.ts`:3269: toolSearchCatalogExecutor
- Schema files: `tool-call-event.schema.json`, `context-projection-event.schema.json`, `gateway-decision.schema.json`

#### 结论

```
EXISTS (partial):
  - Agent/Diagnostic/Lifecycle 三层事件系统
  - Primary tool path 有 lifecycle 事件包装
  - 事件 schema 设计存在

MISSING:
  - 事件真实性自验证机制缺失
  - 事件不可篡改/可审计存储缺失
  - Phase 6 设计事件 (tool-call-event / projection-event / gateway-decision) 未 emit
  - 事件 ↔ 执行对应证明链缺失
  - Event Store 完整性保证缺失

BYPASSABLE:
  - B5-BP1: agent-loop.js direct execute → 无事件
  - B5-BP2: plugin internal execute → 无事件
  - B5-BP3: fire-and-forget → 无真实性验证
  - B5-BP4: Phase 6 schema 事件未 emit
```

---

## §8 汇总结果

### 8.1 最终判定

| Boundary | Status | Evidence |
|:---|:---|---:|
| **B1 Plugin → Gateway** | 🟥 MISSING + ⚠️ BYPASSABLE | 2 bypass paths |
| **B2 Worker → Policy** | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | 3 bypass paths |
| **B3 Capability → Registry** | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | 3 bypass paths |
| **B4 Context → Projection** | 🟡 EXISTS(design) + 🟥 MISSING + ⚠️ BYPASSABLE | 3 bypass paths |
| **B5 Event → Truth** | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | 4 bypass paths |

### 8.2 缺口清单

| 缺口 | 边界 | 类型 | 影响 |
|:---|:---|---:|:---|
| Gateway.intercept() 不在执行路径 | B1 | MISSING | LLM tool call 无 Gateway 拦截 |
| Plugin internal direct execute | B1 | BYPASSABLE | Plugin 绕过 Gateway |
| 执行时无 policy re-check | B2 | MISSING | 注册后 policy 变更不生效 |
| Cross-agent spawn bypass | B2 | BYPASSABLE | Spawned agent 超出 parent policy |
| Registry 不在执行路径 | B3 | MISSING | Registry 是声明 metadata, 非执行关卡 |
| Registry ↔ Runtime 无强制同步 | B3 | BYPASSABLE | Registry 声明与运行时可分歧 |
| Context Projection 无 runtime 实现 | B4 | MISSING | 0 行执行代码 |
| Memory direct injection | B4 | BYPASSABLE | Memory 未经过 governance |
| 事件无自验证机制 | B5 | MISSING | Event 不验证执行真实性 |
| Phase 6 schema events 未 emit | B5 | BYPASSABLE | 设计事件不产生 |

### 8.3 绕过路径汇总 (Phase 7.3 输入)

| ID | 边界 | 路径 | 类型 |
|:---|:---|---:|:---|
| B1-BP1 | B1 | agent-loop.js → tool.execute() 直接执行 | Direct bypass |
| B1-BP2 | B1 | Plugin internal → matchedTool.execute() | Plugin bypass |
| B2-BP1 | B2 | Cross-agent spawn → 超 policy 工具 | Spawn bypass |
| B2-BP2 | B2 | Plugin internal → tool.execute() | Plugin bypass |
| B2-BP3 | B2 | Registration-time only → 执行时不检查 | Temporal gap |
| B3-BP1 | B3 | Plugin → Runtime Resolver 直接注册 | Registry bypass |
| B3-BP2 | B3 | 创建时检查 ≠ 执行时保证 | Temporal gap |
| B3-BP3 | B3 | Registry ↔ Runtime 无强制同步 | Sync gap |
| B4-BP1 | B4 | Direct system prompt assembly | Assembly bypass |
| B4-BP2 | B4 | Context Engine Plugin replacement | Plugin bypass |
| B4-BP3 | B4 | Direct memory injection | Memory bypass |
| B5-BP1 | B5 | agent-loop.js direct execute → 无事件 | Event bypass |
| B5-BP2 | B5 | Plugin internal execute → 无事件 | Event bypass |
| B5-BP3 | B5 | Fire-and-forget → 无真实性验证 | Verification gap |
| B5-BP4 | B5 | Phase 6 schema events 未 emit | Schema gap |

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|---:|:---|
| v1-draft | 2026-07-19 | Phase 7.2 Boundary Enforcement Matrix v1.0, 5 章节 |
| v1 | 2026-07-19 | B1-B5 源码验证完成, 证据 + 分类 + 绕过路径写入 |
