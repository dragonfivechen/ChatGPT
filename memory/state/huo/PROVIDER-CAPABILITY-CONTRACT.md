# Provider Capability Contract v1.0 FINAL

```yaml
contract:
  name: PROVIDER-CAPABILITY
  version: v1.0
  level: L1
  parent: FREEZE-CONTRACT
  scope: provider/model capability governance
  owner: 燃🔥
  status: active
```

**Phase 6.2.1 — 架构规范，非源码改动**
**Status:** FINAL
**Date:** 2026-07-19
**Owner:** 燃🔥 (Phase 6.2)
**Dependencies:** PHASE-6.2-AUDIT-REPORT.md (审计事实依据), Plugin Capability Contract, Extension Boundary

---

## Section 0 — Scope

### 0.1 合同定位

Provider Capability Contract 是 **Provider/Model 对 Runtime 能力支持情况的声明与验证协议**。

不是：
- ❌ 模型选择策略
- ❌ 路由决策依据
- ❌ 成本策略
- ❌ fallback 规则

### 0.2 治理目标

将当前分散在 `ModelDefinitionConfig.reasoning`、`ModelCompatConfig.*`、`detectOpenAICompletionsCompat()` 推断、`OpenRouterModelCapabilities` 中的能力碎片，收敛为统一能力治理对象。

```
治理前                              治理后
-----                              -----
reasoning (ModelConfig)            ProviderCapability.thinking
supportsTools (compat)             ProviderCapability.tool_calls
supportsReasoningEffort (compat)   ProviderCapability.reasoning_effort
supportsStrictMode (compat)        ProviderCapability.strict_schema
thinkingFormat (compat)            format: reasoning_content
detectOpenAICompat() (runtime)     provenance: runtime_detected
OpenRouterModelCapabilities        provenance: external_catalog
```

### 0.3 适用范围

本合约适用于所有通过 OpenClaw Provider 体系接入的模型提供商，包括：
- 静态配置 provider（DeepSeek, Ollama 等）
- 运行时检测 provider（OpenRouter 等）
- 动态发现 provider（Bedrock, Copilot 等）

### 0.4 不适用范围

本合约不适用于：
- Plugin Capability — 由 Plugin Capability Contract 治理
- Agent 工具能力 — 由 Tool Call Governance 治理
- Runtime 内部能力 — 由 Runtime/Extension Boundary 治理

### 0.5 架构分层

```
ModelCompatConfig
   │ 传输协议适配
   v
Provider Capability Contract   ← 本合约
   │ 能力事实治理
   v
Capability Registry
   │ Runtime 查询
   v
Execution Policy
```

---

## Section 1 — Capability Definition

### 1.1 Capability 定义

Capability = "能做什么" 的事实声明。

示例：
- `thinking.supported = true`  — 模型支持推理输出
- `tool_calls.supported = true`  — 模型支持工具调用
- `streaming.supported = true`  — 模型支持流式输出

### 1.2 Format 定义

Format = "怎么做" 的表现形式。**与 Capability 分离。**

示例：
- `tool_calls.format = "openai_function"`  — 工具调用的协议格式
- `thinking.format = "reasoning_content"`  — 推理输出的字段格式
- `tool_calls.schema_validation = "strict"`  — schema 校验严格度

### 1.3 分离规则

```yaml
Capability 变动:   supported: true → false     = 能力变化
Format 变动:       format: "A" → "B"           = 表现形式变化，能力不变

禁止绑定:
  ❌ "格式变了 = 能力变了"
  ❌ "格式不变 = 能力不变"

正确判断:
  supported: true, format: "reasoning_content"
      ↓ API 升级，格式变为 "thinking_content"
  supported: true, format: "thinking_content"   ← 能力仍在，格式变更
```

### 1.4 命名规范

```
<capability>:
  supported: <boolean>
  format:    <string | null>
```

不支持的能力 `format` 必须为 null，不得出现 `"format": ""` 或 `"format": "unused"`。

---

## Section 2 — Ownership & Provenance

### 2.1 能力证据优先级

能力来源从证据可信度排列，不是从配置路径排列：

```
1st Priority: Runtime Verified Evidence        — 运行时验证通过
2nd Priority: Provider Adapter Declaration     — 适配器集成声明
3rd Priority: Runtime Detection                — 基于 baseUrl/API 签名推断
4th Priority: Static Configuration Hint        — 配置文件中的备注/提示
```

**配置不是事实。配置只是声明。**
`supportsTools: true` 不能等价于 "API 已验证支持 tool_calls"。

### 2.2 evidence 与 provenance 分离

```yaml
provenance:
  source: 谁提供的能力信息
  detail: 详细信息

evidence:
  type:   为什么相信
  value:  具体的验证事实
  timestamp: 验证时间
```

**示例对比：**

```yaml
# Runtime Verified Evidence（最高优先级）
capabilities:
  thinking:
    supported: true
    format: reasoning_content
    provenance:
      source: runtime_verification
      detail: "API 响应包含 reasoning_content 字段"
    evidence:
      type: api_response_observation
      value: "POST /chat/completions → response.reasoning_content present"
      timestamp: "2026-07-19T01:23:45Z"

# Provider Adapter Declaration（次高）
capabilities:
  tool_calls:
    supported: true
    format: openai_function
    provenance:
      source: provider_adapter
      detail: "deepseek-provider-adapter v1.2"
    evidence:
      type: adapter_declaration
      value: "adapter.supportsToolCalls = true"

# Static Configuration Hint（最低优先级）
capabilities:
  reasoning_effort:
    supported: true
    provenance:
      source: config_hint
      detail: "compat.supportsReasoningEffort=true in openclaw.json"
    evidence:
      type: static_config
      value: "models[].compat.supportsReasoningEffort"
      timestamp: "2026-07-18T00:00:00Z"
```

### 2.3 禁止行为

- ❌ 纯 `"thinking": true` 无 provenance — 无效声明
- ❌ 配置 = 事实 — `supportsTools:true` ≠ API 已验证
- ❌ LLM 自报能力 — 触发 `capability_ownership_violation`
- ❌ Plugin 修改 Provider 能力声明 — 触发 `capability_ownership_violation`

### 2.4 所有权变更规则

| 事件 | 效果 |
|:---|:---|
| Runtime 验证完成 | 覆盖 adapter / config，新增 verified evidence |
| Adapter 更新 | 重新声明，触发 re-verification |
| Config 变更 | 记录 config_hint，不覆盖已验证证据 |
| Runtime 升级 | 检测逻辑更新 → re-detection，不覆盖已存在证据 |

---

## Section 3 — Capability Schema Semantics

### 3.1 语义 Schema（当前合约定义，非最终机器约束）

```json
{
  "thinking": {
    "supported": true,
    "format": "reasoning_content",
    "provenance": { "source": "runtime_verification" },
    "evidence": { "type": "api_response_observation", "value": "..." }
  },
  "tool_calls": {
    "supported": true,
    "format": "openai_function",
    "schema_validation": "strict",
    "provenance": { "source": "provider_adapter" },
    "evidence": { "type": "adapter_declaration", "value": "..." }
  },
  "reasoning_effort": {
    "supported": true,
    "provenance": { "source": "config_hint" },
    "evidence": { "type": "static_config", "value": "..." }
  },
  "temperature": {
    "supported": false,
    "provenance": { "source": "provider_adapter" },
    "evidence": { "type": "adapter_declaration", "value": "..." }
  },
  "streaming": {
    "supported": true,
    "provenance": { "source": "provider_adapter" },
    "evidence": { "type": "adapter_declaration", "value": "..." }
  },
  "vision": {
    "supported": false,
    "provenance": { "source": "provider_adapter" },
    "evidence": { "type": "adapter_declaration", "value": "..." }
  }
}
```

### 3.2 Capability 列表

| 能力 | 含义 | supported 类型 | format 示例 |
|:---|:---|:---:|:---|
| `thinking` | 推理/思维链输出 | boolean | `"reasoning_content"`, `"thinking_content"` |
| `tool_calls` | 工具调用 | boolean | `"openai_function"`, `"anthropic_tool"` |
| `reasoning_effort` | 推理强度控制参数 | boolean | — |
| `temperature` | 温度参数 | boolean | — |
| `streaming` | 流式输出 | boolean | — |
| `vision` | 图像输入支持 | boolean | — |

### 3.3 子能力

仅 `tool_calls` 有子能力：

```yaml
tool_calls:
  supported: bool
  format: string
  schema_validation: "strict" | "lax"      ← supportsStrictMode 映射至此
```

### 3.4 Schema 边界

Capability Schema **只描述"能不能"**，不包含：
- ❌ `preferred: true` — 属于路由策略
- ❌ `cost_weight: 0.5` — 属于成本策略
- ❌ `fallback_model: "deepseek-chat"` — 属于 fallback 策略

---

## Section 4 — Evidence Model

### 4.1 evidence 与 provenance 职责分离

| 字段 | 回答 | 示例 |
|:---|:---|:---|
| `provenance.source` | 谁提供的能力信息 | `"runtime_verification"` |
| `provenance.detail` | 具体来源路径 | `"API 响应包含 reason_content"` |
| `evidence.type` | 为什么相信 | `"api_response_observation"` |
| `evidence.value` | 具体的验证事实 | `"POST /chat/completions → response.reasoning_content present"` |
| `evidence.timestamp` | 验证时间 | `"2026-07-19T01:23:45Z"` |

### 4.2 evidence type 枚举

| type | 含义 | 可信度 |
|:---|:---|:---:|
| `api_response_observation` | API 实际响应中观察到能力证据 | 最高 |
| `api_error_pattern` | API 返回特定错误指示能力不支持 | 高 |
| `adapter_declaration` | Provider Adapter 代码声明 | 中 |
| `runtime_detection` | 基于 baseUrl/API 签名的启发式检测 | 中低 |
| `openrouter_catalog` | OpenRouter 模型目录 | 中低 |
| `static_config` | 静态配置文件中的 hint | 低 |

### 4.3 evidence 生命周期

```
evidence 创建 → 附加到 capability
     ↓
evidence 验证 → 升级可信度（static_config → runtime_detection → api_response_observation）
     ↓
evidence 过期 → 标记为 stale，触发 re-verification
```

**禁止静默替换 evidence**。evidence 变更必须记录到 events。

---

## Section 5 — Lifecycle

### 5.1 Capability 状态

```
         +-- 新 Provider/Model 接入
         |
         v
    [unknown]  ← 初始状态，无任何声明
         |
         v
    [detected] ← 已声明或检测，有 provenance + evidence
         |
         v
    [verified] ← 运行时验证通过
         |
         v
    [deprecated] ← 不再支持，保留历史记录
```

### 5.2 各状态定义

| 状态 | 含义 | 允许操作 | 时长 |
|:---|:---|:---|:---:|
| `unknown` | 未声明、未检测 | 仅声明/检测可进入下一状态 | transient |
| `detected` | 已有声明或检测结果 | 运行时读取，参与能力校验 | session 或持久 |
| `verified` | 运行时已验证 | 高风险操作依赖 verified | session 级 |
| `deprecated` | 标记为不再支持 | 保留记录，不允许新操作依赖 | 永久 |

### 5.3 状态转换规则

```
unknown → detected:
  条件: Adapter 声明 或 Runtime Detection 完成
  示例: 新配 DeepSeek provider → runtime 检测 baseUrl → detected

detected → verified:
  条件: 运行时验证通过（API 响应与声明一致）
  示例: tool_calls.supported=true → 首次 tool call 成功 → verified

detected → deprecated:
  条件: Provider 版本变更，能力不再支持
  示例: API 更新后 thinking 不再可用

verified → deprecated:
  条件: 连续验证失败
  示例: tool_calls 连续 3 次不可用
```

### 5.4 禁止传递

```
直接: true （无 provenance、无 evidence）
```

不允许存在无 provenance 的能力值。所有能力声明必须可通过 `provenance + evidence` 链追溯到验证基础。

---

## Section 6 — Conflict Handling

### 6.1 冲突类型

| 类型 | 表现 | 示例 |
|:---|:---|:---|
| C1: 证据 vs 证据 | 两个来源不一致 | Verification 说 thinking=true, Adapter 说 thinking=false |
| C2: 声明 vs 运行时 | 运行时结果与声明冲突 | 声明 supportsTools=true, API 返回不支持 |
| C3: 检测 vs 检测 | 两次检测结果不一致 | 同一 provider 推理格式不同 |

### 6.2 核心原则

**不要自动覆盖。生成 capability_conflict event，交给治理层。**

```yaml
规则:
  冲突发现:         记录事件
  自动解决:         ❌ 禁止
  向上报告:         ✅ 必须
  治理层处理:       ✅ 由 Governance Audit 判定
```

### 6.3 Conflict Event

```yaml
event:
  type: capability_conflict
  timestamp: 2026-07-19T09:00:00Z
  provider: deepseek
  model: deepseek-v4-flash
  capability: tool_calls
  conflicts:
    - provenance: { source: static_config, detail: "supportsTools=false in openclaw.json" }
      evidence: { type: static_config, value: "compat.supportsTools", timestamp: "..." }
    - provenance: { source: runtime_verification, detail: "API 返回 tool_calls 成功" }
      evidence: { type: api_response_observation, value: "POST /... → tool use success", timestamp: "..." }
  action_taken: none
  governance: pending
```

### 6.4 运行时行为

```
R1: 运行时读取已存在的能力值 → 继续（不作变更）
R2: 记录 capability_conflict event → 事件日志
R3: 不做自动覆盖、不做自动降级、不做自动 fallback
R4: Governance Audit 周期性检查未解决的冲突事件
```

### 6.5 升级路径

仅 Governance Audit 可解决冲突：

```
Governance Audit
  ↓
审查 capability_conflict 事件
  ↓
根据 evidence 可信度判断:
  - api_response_observation > adapter_declaration > static_config
  ↓
输出决定 → 写入契约更新 / 配置修正
```

---

## Section 7 — Runtime Boundary

### 7.1 读取权限

```
✅ 允许:
  Runtime (Agent Runner)
    ↓
  读取 capability registry
    ↓
  校验请求是否符合能力声明
```

### 7.2 禁止操作

```
❌ 禁止:
  LLM 自身
    ↓
  修改 capability 声明

❌ 禁止:
  Tool call 返回结果
    ↓
  反向修改 capability 声明

❌ 禁止:
  Agent 推理过程
    ↓
  动态调整能力
```

### 7.3 校验规则

Runtime 在发起 provider 请求前必须校验：

```yaml
校验点 1: 请求 thinking → 检查 capability.thinking.supported
  不通过 → 返回 capability_rejection

校验点 2: 请求 tool_calls → 检查 capability.tool_calls.supported
  不通过 → 返回 capability_rejection

校验点 3: 请求 reasoning_effort → 检查 capability.reasoning_effort.supported
  不通过 → 返回 capability_rejection
   注：静默忽略 reasoning_effort 参数不视为 violation

校验点 4: 请求 streaming → 检查 capability.streaming.supported
  不通过 → 返回 capability_rejection
```

**所有 rejection 必须生成事件 `capability_rejection`，禁止静默降级。**

### 7.4 审计证据

```yaml
# 每次读取
audit:
  capability_read:
    - provider: deepseek
      model: deepseek-v4-flash
      queried: [thinking, tool_calls]
      timestamp: ...

# 每次校验失败
  capability_rejection:
    - provider: deepseek
      model: deepseek-chat
      capability: thinking
      reason: "not_supported"
      evidence: { type: api_response_observation, value: "no reasoning_content in response", timestamp: "..." }
      request_id: ...
```

---

## Section 8 — ModelCompatConfig Separation

### 8.1 定位

`ModelCompatConfig` = **传输协议适配层**。
`ProviderCapability` = **能力声明层**。

```
Provider Capability Contract
       │                        ← 语义层（能不能做什么）
       v
thinking.supported = true
tool_calls.supported = true
       │
       │ 映射到
       v
ModelCompatConfig
  supportsTools: true          ← 协议适配（如何实现）
  thinkingFormat: "deepseek"   ← 协议适配（使用什么格式）
  supportsReasoningEffort: true
```

### 8.2 归属判断

```yaml
属于 ProviderCapability:      属于 ModelCompatConfig (传输协议):
  thinking                        supportsUsageInStreaming
  tool_calls                      maxTokensField
  reasoning_effort                requiresToolResultName
  temperature                     requiresAssistantAfterToolResult
  streaming                       cacheControlFormat
  vision                          sendSessionAffinityHeaders
                                  supportsPromptCacheKey
                                  strictMessageKeys
                                  requiresStringContent
```

**判别规则：**
- 属于 "Provider/Model 是否支持某项 AI 能力" → ProviderCapability
- 属于 "传输协议如何适配" → ModelCompatConfig
- 两者不重叠。`supportsTools` 归属 ProviderCapability，`thinkingFormat` 归属 `tool_calls.format`

### 8.3 共存规则

| 阶段 | 规则 |
|:---|:---|
| Phase 6.2 (Contract + Schema) | ModelCompatConfig 不变；Contract 定义归属 |
| Phase 6.2.3 (Registry v2) | Registry 记录能力声明，运行时仍然读取 ModelCompatConfig |
| Phase 6.2.4 (Enforcement) | 运行时新增 `capability_hass(cap_name)` 统一查询 |
| 未来 | ModelCompatConfig 的 capability 字段逐步由 Registry 替代 |

---

## Section 9 — Registry Relationship

### 9.1 层次关系

```
Provider Capability Contract     ← Phase 6.2.1 (当前，FINAL)
   │ 定义语义和规则
   v
Provider Capability Schema       ← Phase 6.2.2 (待建设)
   │ 定义机器约束
   v
Registry v2 (Provider 粒度)      ← Phase 6.2.3 (待建设)
   │ 注册能力事实
   v
Enforcement Audit                ← Phase 6.2.4 (待建设)
   │ 验证执行
   v
Runtime Policy Integration       ← 后续阶段
```

### 9.2 Contract → Registry 映射

| Contract 章节 | Registry v2 对应 |
|:---|:---|
| §1 Capability Definition | 每项能力条目必须有 `supported` + `format` |
| §2 Ownership & Provenance | 每项能力必须有 `provenance` + `evidence` |
| §3 Schema Semantics | Registry 条目必须符合 Schema 约束 |
| §4 Evidence Model | Registry 条目必须有 `evidence` 字段 |
| §5 Lifecycle | Registry 条目包含状态和最后一次变更时间 |
| §6 Conflict Handling | Registry 驱动产生 capability_conflict event |
| §7 Runtime Boundary | Registry 提供只读接口供 Runtime 读取 |
| §8 ModelCompatConfig Separation | Registry 不包含协议适配字段 |

### 9.3 契约先行

本合约的完成是 Registry v2 的准入条件。

```
Contract (语义) → Schema (约束) → Registry (实例)

不反序：
❌ Registry 先建，再套 Contract
❌ Schema 先定义，再约束 Contract
```

---

## Section 10 — Audit Requirements

### 10.1 审计检查项

以下检查项应纳入 Governance Compliance Audit：

```
[ ] 所有已注册 Provider 的能力是否有 provenance + evidence 链
[ ] 是否存在无来源的 "thinking:true"（无 provenance, 无 evidence）
[ ] LLM 是否试图自报能力（events 中搜索 capability_ownership_violation）
[ ] 是否存在 capability_conflict 事件未解决
[ ] capability_rejection 事件是否有追溯审计
[ ] ModelCompatConfig.supportsTools 是否已映射到 Registry
[ ] 是否存在静默降级（冲突处理时绕过 event 生成）
[ ] 是否存在 Runtime 写能力声明（违反 §7 Runtime Boundary）
```

### 10.2 违背后果分级

| 违背类型 | 等级 | 后果 |
|:---|:---:|:---|
| LLM 自报能力 | **P0** | 触发 `capability_ownership_violation`，记录到 events |
| Runtime 写能力声明 | **P0** | 触发 `capability_boundary_violation`，立即终止 |
| Plugin 修改 Provider 能力 | **P1** | 拒绝修改，触发 `capability_ownership_violation` |
| 无 provenance 的能力声明 | **P1** | Governance Audit 标记，要求补充 |
| 静默降级（冲突时自动覆盖） | **P2** | Governance Audit 标记，标记为设计违规 |
| Config 声明不存在的能力 | **P2** | Registry 拒绝登记，生成 `capability_config_mismatch` |
| 校验路径绕过 | **P1** | 审计事件，要求修复校验点 |

### 10.3 审计周期

```yaml
运营级: 每次心跳检查 capability_conflict 未解决事件数
架构级: 每次架构审计时执行完整 §10.1 检查项
事件驱动: capability_ownership_violation / capability_boundary_violation 触发即时审计
```

---

## 附录 A: 当前 Provider Capability 基线快照

基于 PHASE-6.2-AUDIT-REPORT.md 审计结果。

### A.1 DeepSeek

| Provider | Model | thinking | tool_calls | reasoning_effort | streaming | vision |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| deepseek | deepseek-v4-flash | ✅ | ✅ | ✅ | ✅ | ❌ |
| deepseek | deepseek-v4-pro | ✅ | ✅ | ✅ | ✅ | ❌ |
| deepseek | deepseek-chat | ❌ | ✅ | ❌ | ✅ | ❌ |
| deepseek | deepseek-reasoner | ✅ | ❌ | ❌ | ✅ | ❌ |

### A.2 Ollama

| Provider | Model | thinking | tool_calls | reasoning_effort | streaming | vision |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| ollama | qwen2.5:3b | ❌ | ❌ (est.) | ❌ | ✅ | ❌ |

### A.3 当前能力来源（pre-Contract 基线）

| Provider | Model | 能力 | 当前来源 | 来源类型 |
|:---|:---|:---|:---|:---:|
| deepseek | v4-flash | thinking | `ModelDefinitionConfig.reasoning=true` | config_hint |
| deepseek | v4-flash | tool_calls | `detectOpenAICompletionsCompat()` 基于 baseUrl | runtime_detection |
| deepseek | v4-flash | reasoning_effort | `compat.supportsReasoningEffort=true` | config_hint |
| ollama | qwen2.5:3b | thinking | 未配置，无 detection 触发 | unknown |

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1.0-draft | 2026-07-19 | 初始版本，8 章节 |
| **v1.0-final** | **2026-07-19** | **完成 3 项修正：① 证据优先级重新排序 ② 新增 evidence 字段 ③ Capability/Format 分离；扩展至 10+附录 章节** |
