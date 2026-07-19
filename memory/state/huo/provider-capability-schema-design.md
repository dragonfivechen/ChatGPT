# Provider Capability Schema v1 — 设计说明

**Phase 6.2.2**
**Date:** 2026-07-19
**Status:** DRAFT
**Schema file:** `provider-capability.schema.json`

---

## 1. Schema 设计目标

将 PROVIDER-CAPABILITY-CONTRACT v1.0 FINAL 的 **语义规则** 转化为 **机器可验证的结构约束**。

```yaml
目标:
  ✅ 强制 provenance — 所有能力必须有 source
  ✅ 强制 evidence — 所有能力必须有 type + value
  ✅ 分离 capability 与 format — supported ≠ format
  ✅ 支持多 provider、多 model — provider + models 层
  ✅ 支持 lifecycle 状态 — unknown/detected/verified/deprecated
  ✅ 可扩展 — 新增能力不需要修改 schema

不负责:
  ❌ routing — 属于 Policy Layer
  ❌ fallback — 属于 Policy Layer
  ❌ cost — 属于 Policy Layer
  ❌ model selection — 属于 Policy Layer
  ❌ 自动决策 — 属于 Policy Layer
```

## 2. 数据结构

```
provider-capability.json
│
├── provider: "deepseek"              ← Provider 标识
│
├── capabilities: {                   ← Provider 级默认能力
│   ├── thinking:           CapabilityEntry
│   ├── tool_calls:         CapabilityEntry + SubCapability
│   ├── reasoning_effort:   CapabilityEntry
│   ├── temperature:        CapabilityEntry
│   ├── streaming:          CapabilityEntry
│   └── vision:             CapabilityEntry
│ }
│
└── models: {                          ← Model 级覆盖
    └── "deepseek-v4-flash": {
        inherits: "provider-defaults"  ← 可选的继承标记
        capabilities: { ... }          ← 仅覆盖有差异的
    }
}
```

## 3. CapabilityEntry 强制字段

```json
{
  "supported": true,          ← 必须，boolean
  "format": "reasoning_content",  ← 可选，string，null 当 supported=false
  "provenance": {             ← 必须
    "source": "runtime_verification",
    "detail": "..."
  },
  "evidence": {               ← 必须
    "type": "api_response_observation",
    "value": "POST /chat → reasoning_content present",
    "timestamp": "2026-07-19T01:23:45Z"
  },
  "state": "verified"         ← 可选，lifecycle 状态
}
```

### 禁止通过 Schema 验证的模式

```json
// ❌ 无来源 — schema 拒绝
{ "thinking": true }

// ❌ 无 provenance — schema 拒绝（required 缺失）
{ "thinking": { "supported": true } }

// ❌ 无 evidence — schema 拒绝（required 缺失）
{ "thinking": { "supported": true, "provenance": { "source": "..." } } }

// ❌ supported=false 但 format 不为 null
{ "thinking": { "supported": false, "format": "reasoning_content" } }
```

## 4. Schema 关键设计决策

### 4.1 命名规范

| 元素 | 规范 | 正则 |
|:---|:---|:---:|
| 能力名 | lowercase snake_case | `^[a-z_][a-z0-9_]*$` |
| Provider ID | alphanumeric + hyphen/underscore | `^[a-zA-Z0-9_-]+$` |
| Model ID | alphanumeric + dot/hyphen/underscore | `^[a-zA-Z0-9_.-]+$` |

### 4.2 provenanceSource 枚举

```
runtime_verification  → API 响应验证（最高信任）
provider_adapter      → 适配器声明
runtime_detection     → 启发式检测（baseUrl/API 签名）
external_catalog      → 外部目录（OpenRouter API）
config_hint           → 静态配置备注（最低信任，非事实）
unknown               → 来源未知（应避免）
```

### 4.3 evidenceType 枚举

```
api_response_observation  → 直接观察到能力证据（最高信任）
api_error_pattern         → 错误模式推断
adapter_declaration       → 适配器代码声明
runtime_detection         → 运行时检测
openrouter_catalog        → OpenRouter 目录
static_config             → 静态配置（最低信任）
```

### 4.4 tool_calls 子能力

`tool_calls` 是唯一带子能力的条目。`schema_validation` 是子能力，不是独立能力：

```json
{
  "tool_calls": {
    "supported": true,
    "format": "openai_function",
    "provenance": { "source": "provider_adapter" },
    "evidence": { "type": "adapter_declaration", "value": "..." },
    "schema_validation": {
      "supported": true,
      "format": "strict",
      "provenance": { ... },
      "evidence": { ... }
    }
  }
}
```

### 4.5 继承机制

`model.inherits` 是可选的字符串标记，引用 provider 级能力。当存在时：
- Provider 级能力作为默认值
- Model 级能力覆盖（merge）
- 主要用于减少重复声明

继承不是必需的 schema 约束（JSON Schema 无法表达条件继承），仅作为 Registry 实现的设计指引。

### 4.6 可扩展性

`capabilities` 对象使用 `additionalProperties` 开放，允许未来新增能力名而不需要更新 schema。新增的能力仍然受 `capabilityEntry` 约束：
- 必须有 `supported`
- 必须有 `provenance`
- 必须有 `evidence`

## 5. 验证能力

| 验证方面 | 手段 |
|:---|:---|
| 语义验证 | 对 PROVIDER-CAPABILITY-CONTRACT 人工复核 |
| 结构验证 | 对 schema 进行 JSON Schema 格式验证（`ajv validate`） |
| 兼容性验证 | 用 schema 验证示例数据（见下方） |

## 6. 示例验证数据

```json
{
  "provider": "deepseek",
  "capabilities": {
    "thinking": {
      "supported": true,
      "format": "reasoning_content",
      "provenance": { "source": "runtime_verification", "detail": "API response contains reasoning_content" },
      "evidence": { "type": "api_response_observation", "value": "POST /chat/completions → reasoning_content present", "timestamp": "2026-07-19T01:23:45Z" },
      "state": "verified"
    },
    "tool_calls": {
      "supported": true,
      "format": "openai_function",
      "provenance": { "source": "provider_adapter", "detail": "deepseek-provider-adapter v1.2" },
      "evidence": { "type": "adapter_declaration", "value": "adapter.supportsToolCalls = true" },
      "state": "detected",
      "schema_validation": {
        "supported": false,
        "format": null,
        "provenance": { "source": "runtime_detection", "detail": "No strict mode found in deepseek API docs" },
        "evidence": { "type": "runtime_detection", "value": "deepseek API → supplyStrictMode not in response" }
      }
    },
    "reasoning_effort": {
      "supported": true,
      "provenance": { "source": "config_hint", "detail": "compat.supportsReasoningEffort=true" },
      "evidence": { "type": "static_config", "value": "openclaw.json → models[].compat.supportsReasoningEffort" },
      "state": "detected"
    },
    "temperature": {
      "supported": false,
      "provenance": { "source": "provider_adapter", "detail": "deepseek API does not expose temperature" },
      "evidence": { "type": "adapter_declaration", "value": "adapter.supportsTemperature = false" }
    },
    "streaming": {
      "supported": true,
      "provenance": { "source": "provider_adapter", "detail": "deepseek API supports SSE streaming" },
      "evidence": { "type": "adapter_declaration", "value": "adapter.supportsStreaming = true" }
    },
    "vision": {
      "supported": false,
      "provenance": { "source": "provider_adapter", "detail": "deepseek does not support image input" },
      "evidence": { "type": "adapter_declaration", "value": "adapter.supportsVision = false" }
    }
  },
  "models": {
    "deepseek-v4-flash": {
      "inherits": "provider-defaults",
      "capabilities": {}
    },
    "deepseek-chat": {
      "capabilities": {
        "thinking": {
          "supported": false,
          "provenance": { "source": "config_hint", "detail": "deepseek-chat is non-reasoning model" },
          "evidence": { "type": "static_config", "value": "ModelDefinitionConfig.reasoning=false" }
        }
      }
    },
    "deepseek-reasoner": {
      "capabilities": {
        "tool_calls": {
          "supported": false,
          "provenance": { "source": "config_hint", "detail": "deepseek-reasoner does not support tool calls" },
          "evidence": { "type": "static_config", "value": "ModelDefinitionConfig.reasoning=true, tool_calls not configured" }
        }
      }
    }
  }
}
```
