# Provider Capability Registry v2 — Design

**Phase 6.2.2 — Capability Registry v2**
**Status:** DRAFT
**Date:** 2026-07-19
**Dependencies:** PROVIDER-CAPABILITY-CONTRACT.md v1.0 FINAL, provider-capability.schema.json
**Standing on:** CAPABILITY-REGISTRY.md (Plugin Registry v1 — unchanged)

---

## 0. 定位

### Registry = Observation Index，不是 Capability Authority

```yaml
Authority Chain:
  Runtime Verified Evidence  ← 事实来源
  Provider Adapter           ← 事实来源
  Governance Audit           ← 权威判定
  
Registry (观察索引):
  接收观察结果
  记录 provenance + evidence
  提供只读查询
  不判定谁对谁错
  不自产事实
```

### 与 Plugin Registry v1 的关系

```
Plugin Registry v1 (现有, 20 entries)
  类别: runtime, memory, event, io, notification, provider, security
  粒度: 插件级
  不修改

Provider Registry v2 (新增)
  类别: provider.capability
  粒度: 提供商级 + 模型级
  新增
```

两者共存，无冲突。

---

## 1. Registry 数据模型

### 1.1 顶层结构

```
provider-capability-registry/
│
├── providers/                          ← 按提供商索引
│   ├── deepseek/
│   │   ├── metadata/                   ← 提供商元数据
│   │   ├── capabilities/               ← 提供商级默认能力
│   │   │   ├── thinking/
│   │   │   ├── tool_calls/
│   │   │   └── ...
│   │   └── models/
│   │       ├── deepseek-v4-flash/
│   │       │   ├── capabilities/       ← 模型级能力覆盖
│   │       │   └── evidence_log/       ← 观察历史
│   │       ├── deepseek-chat/
│   │       └── deepseek-reasoner/
│   │
│   └── ollama/
│       └── models/
│           └── qwen2.5:3b/
│
├── capabilities/                       ← 按能力视图索引
│   ├── thinking/                       ← 所有支持/不支持 thinking 的模型
│   └── tool_calls/
│
├── events/                             ← Registry 生成的事件日志
│   ├── capability_detected/
│   ├── evidence_updated/
│   ├── lifecycle_transition/
│   └── conflict_resolved/
│
└── conflicts/                          ← 未解决的冲突列表
    └── pending/
```

### 1.2 单条能力记录（完整结构）

```yaml
entry:
  provider: deepseek
  model: deepseek-v4-flash
  
  capability: thinking
  
  current:                              # 当前聚合值
    supported: true
    format: reasoning_content
    
    # 聚合规则：
    # - 取 evidence 中 timestamp 最新且已验证的
    # - 冲突时标记 conflict，不停用
    
    provenance:
      source: runtime_verification
      detail: "API response contains reasoning_content"
    
    evidence:
      type: api_response_observation
      value: "POST /chat/completions → reasoning_content present"
      timestamp: "2026-07-19T01:23:45Z"
    
    state: verified
    last_updated: "2026-07-19T01:23:45Z"
  
  observations:                         # 所有历史观察
    - supported: true
      format: reasoning_content
      provenance: { source: config_hint, detail: "ModelDefinitionConfig.reasoning=true (legacy)" }
      evidence: { type: static_config, value: "openclaw.json → reasoning: true", timestamp: "2026-07-17T00:00:00Z" }
      state: detected
      recorded_at: "2026-07-17T00:00:00Z"
    
    - supported: true
      format: reasoning_content
      provenance: { source: runtime_verification, detail: "API response contains reasoning_content" }
      evidence: { type: api_response_observation, value: "POST /chat → reasoning_content present", timestamp: "2026-07-19T01:23:45Z" }
      state: verified
      recorded_at: "2026-07-19T01:23:45Z"
  
  conflicts: []                         # 当前未解决的冲突
  lifecycle: verified
  last_verified: "2026-07-19T01:23:45Z"
```

### 1.3 观测列表累积规则

```yaml
新增观察:
  1. 记录 provenance + evidence + timestamp
  2. 追加到 observations 列表
  3. 触发 evidence_updated 事件
  4. 不删除历史观察
  
历史保留原则:
  - observations 不可删除（审计追溯需要）
  - 仅最新被标记为 current
  - 历史记录只读
```

---

## 2. Provider/Model 层级合并规则

### 2.1 层级结构

```
Provider 级:   capabilities.thinking.supported = true    ← 默认值
                   |
                   v
Model 级:     models.deepseek-v4-flash.capabilities.thinking  ← 覆盖
```

### 2.2 合并规则

```yaml
查询模型 X 的能力时:

Step 1: 读取 Provider 级默认能力
    ↓
Step 2: 检查 Model X 是否有显式覆盖
    ↓
Step 3: 有覆盖 → 使用 model 级值（覆盖整个 capability 对象）
    ↓
        无覆盖 → 使用 provider 级默认
    ↓
Step 4: 检查 evidence 是否 conflict
    ↓
    conflict → 标记 capability 为 conflicted，返回 current 值（不做降级）
    ↓
    no conflict → 返回合并结果
```

### 2.3 覆盖粒度

```
Model 级覆盖 = 整个 capability entry 替换，不是字段级 merge

示例:
  Provider 级:  thinking.supported = true, format = "reasoning_content"
  Model 级:     thinking.supported = false
  结果:         thinking.supported = false, format = null
  
防误解:
  ❌ Model 级 thinking.supported = false, format = "reasoning_content"
     → Schema 拒绝（supported=false 时 format 须 null）
```

### 2.4 继承标记

`inherits` 是文档标记，不是 merge 指令。

```yaml
deepseek-v4-flash:
  inherits: provider-defaults    # 文档标记，表示意图继承
  capabilities: {}               # 无覆盖 → 完全使用 provider 级
  
deepseek-chat:
  # 无 inherits
  capabilities:
    thinking:
      supported: false           # 显式覆盖，与 provider 级无关
```

---

## 3. Evidence 累积策略

### 3.1 观测到 Registry 的路径

```
证据产生端                    Registry 端
---------------              --------------
Runtime Verification  ──→    registry.push_evidence(
                                provider, model, capability,
                                supported, format,
                                provenance, evidence
                              )

Provider Adapter      ──→    同上

Runtime Detection     ──→    同上

Config Hint           ──→    同上（标记为 config_hint）
```

### 3.2 证据类型优先级

Registry 内部使用优先级排序，但不自动覆盖：

```yaml
证据优先级（用于排序，不用于裁决）:
  Level 1: api_response_observation    ← 直接观测，最高
  Level 2: api_error_pattern           ← 错误推断
  Level 3: adapter_declaration         ← 适配器声明
  Level 4: runtime_detection           ← 启发式检测
  Level 5: openrouter_catalog          ← 外部目录
  Level 6: static_config               ← 静态配置，最低
```

**排序规则**：每次新增 evidence 时，将 `observations` 列表按优先级降序重新排列。`current` 指向列表中最高优先级的已验证条目。如果最高优先级不可用，取次高。

### 3.3 证据保留策略

```yaml
保留规则:
  - 所有证据永久保留在 observations 列表
  - 不设 TTL 自动过期
  - stale 标记由外部审计触发
  
清理触发:
  - Provider 下线 → Provider 级归档
  - Model 退役 → Model 级归档
  - 审计确认证据错误 → 标记为 invalid，不删除
```

### 3.4 证据唯一性

```yaml
避免重复:
  同一 type + value + source 在 5 分钟内反复提交 → 合并（更新 timestamp）
  差异证据 → 追加新记录
```

---

## 4. Capability 生命周期迁移

### 4.1 Registry 内状态

```
                 +-- detect()
                 v
    [unknown] ────→ [detected]
                       │
                       │ verify()
                       v
                   [verified]
                       │
                       │ fail(3x)
                       v
                   [deprecated]
                       │
                       │ re-verify()
                       v
                   [verified] (可恢复)
```

### 4.2 迁移触发条件

| 迁移 | 触发 | 事件 |
|:---|:---|:---|
| unknown → detected | 首次 evidence 提交 | `capability_detected` |
| detected → verified | Runtime 验证通过 | `capability_verified` |
| detected → deprecated | Provider 版本变更确认 | `capability_deprecated` |
| verified → deprecated | 连续 3 次验证失败 | `capability_verification_failed` → `capability_deprecated` |
| deprecated → verified | 重新验证通过 | `capability_verified` |

```yaml
连续失败判定:
  单 session 内同一 capability 连续 3 次 rejection
  或者跨 session 累计 5 次 rejection 且无成功验证
  
计数器:
  verification_fail_count: 3
  last_fail: "2026-07-19T02:00:00Z"
  成功验证后重置
```

### 4.3 生命周期事件的副作用

```yaml
detected → verified:
  聚合值 current 不变（detected 时已可信）
  但标记 state = verified，高风险操作放行

verified → deprecated:
  聚合值 current 保持最后一次 verified 值
  标记 state = deprecated
  Runtime 不再依赖此能力（触发 capability_rejection）

deprecated → verified:
  聚合值 current 使用新的 verified 证据
  覆盖 deprecated 标记
```

---

## 5. Conflict Resolution

### 5.1 Registry 内冲突识别

Registry 通过比较 `observations` 列表检测冲突：

```yaml
冲突触发条件:
  两个不同的 evidence 来源
  对同一 capability
  给出不同 supported 值（true vs false）
  或不同 format 值

示例:
  evidence A (api_response_observation):  thinking.supported = true
  evidence B (config_hint):               thinking.supported = false
  → 冲突
```

### 5.2 冲突时 Registry 行为

```yaml
Registry 检测到冲突:
  Step 1: 保持 current 不变（已有值）
  Step 2: 追加新 observation 到列表
  Step 3: 追加到 conflicts/pending 列表
  Step 4: 生成 capability_conflict 事件
  Step 5: 不做自动解决、不做降级、不做回退
  
不解决原则:
  Registry 不判断谁对
  即使 Level 1 evidence 与 Level 6 evidence 冲突
  Registry 仍然只记录，不裁决
```

### 5.3 冲突解决路径

仅 Governance Audit 可解决：

```yaml
Governance Audit:
  ↓
扫描 conflicts/pending 列表
  ↓
对每个冲突:
  - 审查 evidence 链
  - 必要时触发 re-verification
  - 输出决定
  ↓
Registry 接收决定:
  - 标记某 observation 为 authoritative
  - 更新 current
  - 关闭冲突（移动到 resolved 子列表）
  - 生成 conflict_resolved 事件
```

### 5.4 Conflict Event 格式

```yaml
event:
  type: capability_conflict
  timestamp: "2026-07-19T09:00:00Z"
  provider: deepseek
  model: deepseek-v4-flash
  capability: tool_calls
  
  conflict:
    - id: obs-001
      supported: true
      provenance: { source: runtime_verification, detail: "API tool call success" }
      evidence: { type: api_response_observation, value: "POST /chat → tool_call success", timestamp: "..." }
      recorded_at: "..."
    
    - id: obs-002
      supported: false
      provenance: { source: config_hint, detail: "supportsTools=false" }
      evidence: { type: static_config, value: "openclaw.json → compat.supportsTools: false", timestamp: "..." }
      recorded_at: "..."
  
  current: true
  action_taken: none
  governance: pending
  resolution: null
```

---

## 6. Registry 查询 API（只读）

### 6.1 查询接口

```yaml
# 查询单能力
GET /v1/providers/:provider/models/:model/capabilities/:capability

响应:
  provider: deepseek
  model: deepseek-v4-flash
  capability: thinking
  current:
    supported: true
    format: reasoning_content
    state: verified
    provenance: { source: "runtime_verification" }
    evidence: { type: "api_response_observation", value: "..." }
  observations: [ ... ]         # 完整历史
  conflicts: []                 # 未解决冲突
```

```yaml
# 查询模型所有能力（合并后）
GET /v1/providers/:provider/models/:model/capabilities

响应:
  provider: deepseek
  model: deepseek-v4-flash
  capabilities:
    thinking:
      supported: true
      state: verified
    tool_calls:
      supported: true
      state: verified
    reasoning_effort:
      supported: true
      state: detected
    ...
```

```yaml
# 按能力查询所有模型
GET /v1/capabilities/:capability?supported=true

响应:
  capability: thinking
  supported: true
  models:
    - provider: deepseek, model: deepseek-v4-flash, state: verified
    - provider: deepseek, model: deepseek-v4-pro,   state: detected
  supported: false
  models:
    - provider: ollama, model: qwen2.5:3b, state: unknown
```

### 6.2 Runtime 读取约束

```yaml
Runtime 只能:
  - GET /v1/providers/:provider/models/:model/capabilities
  - GET /v1/providers/:provider/models/:model/capabilities/:capability
  
Runtime 不能:
  - POST /v1/providers (注册)
  - PUT /v1/providers (修改)
  - DELETE (删除)
  - PUSH /v1/evidence (提交证据)

证据提交由:
  - Provider Adapter
  - Runtime Detection
  - Config Scanner
  负责
  
Runtime 的职责:
  只读查询 + 校验请求是否符合能力声明
```

### 6.3 缓存策略

```yaml
Registry 查询可缓存:
  - 能力聚合值（current）缓存 TTL = 5 min
  - observations + conflicts 不缓存（仅用于审计）
  
缓存失效:
  新 evidence 提交时自动失效 current 缓存
```

---

## 7. Event 记录规范

### 7.1 Registry 生成的事件清单

| Event | 触发 | 包含 |
|:---|:---|:---|
| `capability_detected` | 首次 evidence 提交 | provider, model, capability, supported, provenance |
| `evidence_updated` | 新的 observation 追加 | provider, model, capability, evidence type |
| `capability_verified` | 状态 → verified | provider, model, capability, verification timestamp |
| `capability_deprecated` | 状态 → deprecated | provider, model, capability, reason, fail count |
| `capability_conflict` | 检测到冲突 | provider, model, capability, conflict evidence pair |
| `conflict_resolved` | 治理解决冲突 | provider, model, capability, resolution, authoritative obs |
| `capability_rejection` | Runtime 校验失败 | provider, model, capability, request context |

### 7.2 事件定位

```yaml
所有事件写入:
  memory/events/system/capability-registry/  ← 系统级事件（无身份归属）
  
文件命名:
  YYYY-MM-DD.md (按日聚合)
  
格式:
  每个事件一条 yaml 块，不超过 20 行
```

### 7.3 事件消费方

| 消费方 | 关注的事件 | 用途 |
|:---|:---|:---|
| Governance Audit | capability_conflict, capability_deprecated | 周期性扫描未解决问题 |
| Runtime | capability_rejection | 请求拒绝统计 |
| Provider Adapter | capability_verified | 确认适配正常 |
| Human Operator | capability_detected, capability_deprecated | 状态变更通知 |

---

## 8. 与现有 Plugin Registry v1 的关系

### 8.1 共存

```
CAPABILITY-REGISTRY.md (v1)
├── Plugin Capabilities (20 entries)        ← 不动
├── 命名空间: runtime.*, memory.*, event.* ...
└── Plugin Declaration 格式

Provider Capability Registry v2 (新增文件)
├── Provider Capabilities
├── 命名空间: provider.capability.*
├── Registry 数据模型
├── 查询 API
└── Event 规范
```

### 8.2 命名空间分离

```yaml
Plugin 名称空间:
  runtime.tool.register
  memory.read
  event.subscribe
  provider.model              ← 注意：这里与 Provider 能力不同

Provider 名称空间:
  provider.capability.thinking
  provider.capability.tool_calls
  provider.capability.reasoning_effort

不冲突:
  provider.model               = 插件的"注册 AI 模型提供商"能力
  provider.capability.thinking = DeepSeek 模型的"推理"能力
```

### 8.3 分离存储

```yaml
Plugin Registry:     CAPABILITY-REGISTRY.md (已有文件)
Provider Registry:   新建 memory/state/huo/provider-capability-registry.json (按 schema 格式)
                     + memory/state/huo/PROVIDER-CAPABILITY-REGISTRY-DESIGN.md (本文件)
```

---

## 9. 实现路径

### 9.1 Phase 6.2.2 步骤

```
Step 1: Registry 数据模型设计      ← 当前（本文件）
Step 2: Registry 文件建立          
   → 创建 provider-capability-registry.json
   → 填入基线数据（附录 A 的 current provider snapshot）
Step 3: 查询接口设计
   → 定义 Runtime 可用的查询方式
Step 4: Event 集成
   → 确保 Registry 输出事件到 memory/events/system/capability-registry/
```

### 9.2 截止条件

```yaml
Phase 6.2.2 COMPLETE 条件:
  [ ] Registry 数据模型设计通过复核
  [ ] provider-capability-registry.json 存在，包含基线数据
  [ ] 查询 API 定义完成
  [ ] Event 规范定义完成
  [ ] 无自动决策逻辑引入
```

---

## 附录 A: 当前 Provider Capability 基线快照（用于 Registry 填充）

基于 PROVIDER-CAPABILITY-CONTRACT.md v1.0 FINAL 附录 A。

### A.1 DeepSeek 默认

```yaml
provider: deepseek
capabilities:
  thinking:
    supported: true
    format: reasoning_content
    provenance: { source: config_hint, detail: "ModelDefinitionConfig.reasoning=true (legacy)" }
    evidence: { type: static_config, value: "openclaw.json → reasoning: true", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
  tool_calls:
    supported: true
    format: openai_function
    provenance: { source: runtime_detection, detail: "detectOpenAICompletionsCompat() based on baseUrl=api.deepseek.com" }
    evidence: { type: runtime_detection, value: "baseUrl pattern match → openai-compatible", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
  reasoning_effort:
    supported: true
    provenance: { source: config_hint, detail: "compat.supportsReasoningEffort=true" }
    evidence: { type: static_config, value: "openclaw.json → compat.supportsReasoningEffort: true", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
  streaming:
    supported: true
    provenance: { source: runtime_detection, detail: "openai-compatible API supports SSE" }
    evidence: { type: runtime_detection, value: "openai-compatible transport → streaming available", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
  vision:
    supported: false
    provenance: { source: config_hint, detail: "ModelDefinitionConfig does not include image input config" }
    evidence: { type: static_config, value: "no input.mimeTypes configured", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
```

### A.2 DeepSeek 模型级覆盖

```yaml
provider: deepseek
models:
  deepseek-chat:
    capabilities:
      thinking:
        supported: false
        provenance: { source: config_hint, detail: "deepseek-chat is non-reasoning model" }
        evidence: { type: static_config, value: "ModelDefinitionConfig.reasoning=false for deepseek-chat", timestamp: "2026-07-17T00:00:00Z" }
        state: detected
      reasoning_effort:
        supported: false
        provenance: { source: config_hint, detail: "non-reasoning model → no reasoning_effort" }
        evidence: { type: static_config, value: "ModelDefinitionConfig.reasoning=false implies no reasoning_effort", timestamp: "2026-07-17T00:00:00Z" }
        state: detected

  deepseek-reasoner:
    capabilities:
      thinking:
        supported: true
        format: reasoning_content
        provenance: { source: config_hint, detail: "deepseek-reasoner is reasoning model" }
        evidence: { type: static_config, value: "ModelDefinitionConfig.reasoning=true for deepseek-reasoner", timestamp: "2026-07-17T00:00:00Z" }
        state: detected
      tool_calls:
        supported: false
        provenance: { source: config_hint, detail: "deepseek-reasoner does not support tool calls" }
        evidence: { type: static_config, value: "no tool_calls config for deepseek-reasoner", timestamp: "2026-07-17T00:00:00Z" }
        state: detected
      reasoning_effort:
        supported: true
        provenance: { source: config_hint, detail: "reasoning model → supports reasoning_effort" }
        evidence: { type: static_config, value: "deepseek-reasoner is reasoning model", timestamp: "2026-07-17T00:00:00Z" }
        state: detected
```

### A.3 Ollama

```yaml
provider: ollama
capabilities:
  thinking:
    supported: false
    provenance: { source: unknown, detail: "no detection triggered for ollama capabilities" }
    evidence: { type: static_config, value: "ollama provider config does not set reasoning", timestamp: "2026-07-17T00:00:00Z" }
    state: unknown
  tool_calls:
    supported: false
    provenance: { source: unknown, detail: "estimated, no runtime verification" }
    evidence: { type: static_config, value: "ollama provider config does not set supportsTools", timestamp: "2026-07-17T00:00:00Z" }
    state: unknown
  streaming:
    supported: true
    provenance: { source: runtime_detection, detail: "openai-compatible API via Ollama" }
    evidence: { type: runtime_detection, value: "ollama baseUrl → openai-compatible transport", timestamp: "2026-07-17T00:00:00Z" }
    state: detected
  vision:
    supported: false
    provenance: { source: unknown, detail: "no vision configuration for qwen2.5:3b" }
    evidence: { type: static_config, value: "no vision config", timestamp: "2026-07-17T00:00:00Z" }
    state: unknown
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1.0-draft | 2026-07-19 | Registry v2 设计草案，9 章节 + 附录 A 基线数据 |
