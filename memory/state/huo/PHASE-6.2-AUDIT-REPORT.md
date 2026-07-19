# Provider Capability Registry v1.0 — 建设阶段审计报告

**Phase 6.2 — 只读审计，无修改**
**Date:** 2026-07-19
**Mode:** Audit only
**Scope:** Provider Identity · Capability Model · Schema · Registry · Runtime Enforcement

---

## A. 当前状态总览

| 维度 | 当前状态 |
|:---|:---|
| Provider 管理体系 | ✅ 存在（配置层 `models.providers`） |
| Provider Identity | ⚠️ 存在但未分离（身份与能力耦合） |
| Capability 声明 | ⚠️ 分散在多个类型中，无统一表述 |
| Capability Schema | ❌ 不存在 |
| Capability Contract | ❌ 不存在 |
| Registry (Provider 粒度) | ❌ 不存在 |
| Runtime Enforcement | ⚠️ 局部存在（通过字段检查） |

---

## B. Provider Identity 审计

### B.1 当前模型

```
openclaw.json
    └── models.providers.{provider_id}
        ├── baseUrl             # 服务端点
        ├── api                 # API 协议类型
        ├── apiKey              # 认证凭据（SecretRef）
        └── models[]            # 模型定义列表
            ├── id              # 模型标识
            ├── reasoning       # ⚠️ 身份字段中含能力判别
            ├── compat          # ⚠️ 能力分散在此处
            ├── cost            # 定价
            └── contextWindow   # 上下文窗口
```

### B.2 身份耦合分析

| 问题 | 表现 | 影响 |
|:---|:---|:---|
| `reasoning` 字段在 Model 层 | `ModelDefinitionConfig.reasoning: boolean` | 能力标记藏在型号定义中，无法按 Provider 级查询 |
| compat 字段在 Model 层 | `ModelCompatConfig` 含 `supportsTools`, `supportsReasoningEffort` 等 | 能力标识分散在 7+ 个字段中，无统一入口 |
| Auth 与 Capability 在同一层级 | `apiKey` 和 `reasoning` 并列在 Model/Provider 下 | 身份验证和能力声明耦合 |
| OpenRouter 独有能力检测 | `openrouter-model-capabilities.ts` 单独实现能力发现 | 能力检测实现不统一 |

### B.3 Provider ID 简洁性

当前 Provider 注入方式：

| Provider | ID | 模型 |
|:---|:---|:---|
| DeepSeek | `deepseek` | deepseek-v4-flash, deepseek-v4-pro, deepseek-chat, deepseek-reasoner |
| Ollama | `ollama` | qwen2.5:3b |

Provider ID 和 Model ID 已分离。✅

---

## C. Capability 现状审计

### C.1 现有能力表达方式

能力散落在以下位置：

| 来源 | 表达式 | 粒度 |
|:---|:---|:---:|
| `ModelDefinitionConfig.reasoning` | `boolean` | per-model |
| `ModelCompatConfig.supportsTools` | `boolean \| undefined` | per-model |
| `ModelCompatConfig.supportsReasoningEffort` | `boolean \| undefined` | per-model |
| `ModelCompatConfig.supportsStrictMode` | `boolean \| undefined` | per-model |
| `ModelCompatConfig.thinkingFormat` | `string \| undefined` | per-model (format: "deepseek", "openai", etc.) |
| `ModelCompatConfig.supportsStore` | `boolean \| undefined` | per-model |
| `ModelCompatConfig.supportsDeveloperRole` | `boolean \| undefined` | per-model |
| `ModelCompatConfig.supportsUsageInStreaming` | `boolean \| undefined` | per-model |
| `ModelDefinitionConfig.input` | `Array<"text"\|"image"\|"video"\|"audio">` | per-model |
| `OpenRouterModelCapabilities.reasoning` | `boolean` | per-model (OpenRouter only) |
| `OpenRouterModelCapabilities.supportsTools` | `boolean \| undefined` | per-model (OpenRouter only) |

### C.2 实例：当前 DeepSeek 配置中的能力

以 deepseek-v4-flash 模型配置为例（`<openclaw.json>`）：

```yaml
model: deepseek-v4-flash
  reasoning: true                                           # ✅ 推理能力
  input: [text]                                             # 文本输入
  compat:
    supportsReasoningEffort: true                           # ✅ reasoning_effort
    supportsUsageInStreaming: true                          # streaming 用量
    maxTokensField: max_tokens                              # 参数映射
  # supportsTools: 未显式配置（默认 true via detection）     # ✅ Tool Calls (隐式)
  # supportsStrictMode: 未显式配置（默认 false via detection）
  # thinkingFormat: 未显式配置（检测为 "deepseek"）
```

当前 DeepSeek 的 `supportsTools` 和 `thinkingFormat` 由 `detectOpenAICompletionsCompat()` 运行时推断，非配置层显式声明。

### C.3 能力清单整理

根据源码和配置，提炼出当前系统涉及的 Provider 能力：

| 能力 | 类型 | 存在方式 | DeepSeek v4-flash | Ollama qwen2.5:3b |
|:---|:---:|:---|:---:|:---:|
| `thinking` | boolean | reasoning 字段 | ✅ true | ❌ (不支持) |
| `reasoning_effort` | boolean | compat.supportsReasoningEffort | ✅ true | ❌ |
| `tool_calls` | boolean | compat.supportsTools (默认推断) | ✅ true | ❌ (未配置) |
| `strict_schema` | boolean | compat.supportsStrictMode | ❌ false | ❌ |
| `streaming` | boolean | compat.supportsUsageInStreaming | ✅ true | ✅ (Ollama) |
| `vision` | boolean | input.includes("image") | ❌ | ❌ |

---

## D. Schema 审计

### D.1 当前类型定义

存在但分散：

```
types.models.ts:
  ModelDefinitionConfig            # model 级配置，含 reasoning
  ModelCompatConfig                # compat 级能力标识（7+ 字段）
  ModelProviderConfig              # provider 级配置，无能力字段
  SupportedThinkingFormat          # thinkingFormat 枚举

openrouter-model-capabilities.ts:
  OpenRouterModelCapabilities      # OpenRouter 专有能力类型（3 字段）
```

### D.2 缺失的 Schema

| 缺失项 | 说明 |
|:---|:---|
| `ProviderCapability` 联合类型 | 无统一类型定义所有能力 |
| `ProviderCapabilitySchema` JSON Schema | 无 schema 验证文件 |
| Provider 级能力声明字段 | `ModelProviderConfig` 无 `capabilities` 字段 |

---

## E. Registry 差距审计

### E.1 当前 Registry

`CAPABILITY-REGISTRY.md` 目前仅有 Plugin 级能力，其中 provider 分类只有：

```yaml
provider:
  - model.provider        # 注册模型提供商（插件级）
  - speech.provider       # 注册语音提供商
  - media.generation      # 注册媒体生成提供商
```

**没有 per-provider 能力目录。** 即 `provider.model` 只定义了"谁可以注册提供者"，没有定义"这个提供者有什么能力"。

### E.2 差距

| Registry 目前 | Registry 目标 |
|:---|:---|
| `provider.model` | `providers.deepseek.capabilities` |
| 只定义"能注册" | 定义"能做什么" |
| Plugin 粒度 | Provider + Model 粒度 |

---

## F. Runtime 差距审计

### F.1 当前 Enforcement

Runtime 通过以下方式检查能力：

```
attempt.ts:
  └─ reasoningLevel 参数传递
  └─ model.reasoning 条件判断

openai-transport-stream.ts:
  └─ getCompat().supportsReasoningEffort → reasoning_effort
  └─ getCompat().supportsTools → tool_calls 启用
  └─ getCompat().thinkingFormat → thinking block
  └─ detectOpenAICompletionsCompat() → 默认推断

openai-stream-wrappers.ts:
  └─ compat.supportsTools → 工具流判断

openrouter-model-capabilities.ts:
  └─ 独立的能力检测 + 缓存
```

### F.2 检查点分布

| 运行时决策 | 检查方式 | 来源 |
|:---|:---|:---|
| 是否启用 thinking | `model.reasoning` | 配置 |
| reasoning_effort 参数 | `compat.supportsReasoningEffort` | 配置 / default detection |
| tool loop 启用 | `compat.supportsTools` | 配置 / default detection |
| thinking_format 选择 | `compat.thinkingFormat` | 配置 / detection (baseUrl) |
| strict schema 启用 | `compat.supportsStrictMode` | 配置 / detection |
| 文本/图像输入 | `model.input` | 配置 |

### F.3 当前特点

1. **Enforcement 局部但可用** — 能力检查散落在各执行路径，通过各自条件判断
2. **默认检测** — 未显式配置时由 `detectOpenAICompletionsCompat()` 基于 baseUrl 推断
3. **无统一能力 API** — 没有像 `model.hasCapability("thinking")` 这样的调用接口
4. **无 capability violation 事件** — 能力失效时静默降级，无事件记录
5. **无 capability-based routing** — 能力不参与模型选择决策

---

## G. Phase 6.2 建设建议

### G.1 建设优先级

| 项 | 难度 | 依赖 | 建议顺序 |
|:---|:---:|:---:|:---:|
| Provider Capability Contract | 低 | 无 | **P1** |
| Provider Capability Schema | 中 | Contract | **P2** |
| Registry 升级（per-provider） | 中 | Schema | **P3** |
| Runtime Enforcement (统一检查) | 中高 | Registry | **P4** |

### G.2 建议类型设计

基于现有代码结构，建议 `ProviderCapability` 类型：

```typescript
interface ProviderCapability {
  thinking: boolean;           // 是否支持推理（reasoning_content）
  reasoning_effort: boolean;   // 是否支持 reasoning_effort 参数
  tool_calls: boolean;         // 是否支持工具调用
  strict_schema: boolean;      // 是否支持 strict schema
  streaming: boolean;          // 是否支持 streaming 输出
  vision: boolean;             // 是否支持图像输入
  input: Array<"text" | "image">;  // 输入模态
}
```

### G.3 能力声明源

建议规则（基于龙哥指示）：

```yaml
# ✅ 允许声明
Provider Adapter (Runtime): 声明 ProviderCapability
Config (静态): 配置覆盖 Provider 默认能力

# ❌ 禁止
LLM 自身: 禁止自报能力
Plugin: 禁止修改 Provider 能力声明
```

### G.4 建议 Registry 格式

```
CAPABILITY-REGISTRY.md (升级版 v2)

providers:
  - id: deepseek
    capabilities:
      thinking:       true
      reasoning_effort: true
      tool_calls:     true
      strict_schema:  false
      streaming:      true
      vision:         false
    models:
      - id: deepseek-v4-flash
        capabilities:
          thinking:   true
          tool_calls: true
      - id: deepseek-v4-pro
        capabilities:
          thinking:   true
          tool_calls: true
      - id: deepseek-chat
        capabilities:
          thinking:   false
          tool_calls: true
      - id: deepseek-reasoner
        capabilities:
          thinking:   true
          reasoning_effort: false
          tool_calls: false
```

### G.5 暂缓项

以下不纳入 Phase 6.2：

- ❌ Capability-based routing（依赖 Registry + Task Classification + Policy Layer）
- ❌ 自动 capability fallback（属于 Runtime Policy，非 Registry）
- ❌ capability violation eventing（属于 Enforcement layer）

---

## 审计结论

```
Phase 6.2 Provider Capability Registry

运行基础:
  Provider 配置     ✅ 存在
  Capability 标识   ⚠️ 分散（7+ 字段，3 种表达方式）
  Capability 检测   ✅ 部分运行时自动推断

建设差距:
  Contract          ❌ 不存在
  Schema            ❌ 不存在
  Registry          ❌ 不存在（provider.model 是插件级，不是能力级）
  Enforcement       ⚠️ 局部存在（分散在各执行路径）
```

**结论：** Phase 6.2 当前覆盖度约 **15%**。Provider 运行基础设施完备，但能力治理体系（Contract → Schema → Registry → Enforcement）全部处于缺失或分散状态。建设应从 Provider Capability Contract 开始。
