# Phase 6.4.1 Tool Call Gateway Schema Design

**Status:** COMPLETE
**Date:** 2026-07-19
**Dependencies:**
- TOOL-CALL-GATEWAY-CONTRACT.md v1 DRAFT
- context-projection.schema.json (Phase 6.3.1 格式参考)
- context-projection-bundle.schema.json (Phase 6.3.1 bundle 模式参考)
- context-projection-event.schema.json (Phase 6.3.1 event 模式参考)

---

## 0. Schema 设计原则

### 一致性

```yaml
与 Phase 6.3 Schema 保持一致的风格:
  相同 draft-07
  相同 $id 命名规范
  相同 description/type/required/enum 模式
  相同 oneOf 分支 (text | json | message)
```

### 三层分离

```yaml
三个独立 JSON Schema 文件:

1. tool-call-request.schema.json
   定义: LLM 发出的 tool call 请求格式
   用途: Gateway 输入校验

2. gateway-decision.schema.json
   定义: Gateway 决策结果格式
   用途: Gateway 输出 + event 记录模板

3. tool-call-event.schema.json
   定义: Event 记录格式
   用途: 事件存储
```

### 组合设计

```yaml
gateway-decision   ──引用──→  tool-call-request (作为输入快照)
tool-call-event   ──包含──→  gateway-decision (作为决策记录)
```

---

## 1. Tool Call Request Schema

### 1.1 定义

```yaml
用途: 描述 LLM 发出的 tool call 请求格式
位置: state/huo/tool-call-request.schema.json

来源: LLM response
包含:
  - toolName (LLM 请求的工具名)
  - toolArgs (工具参数)
  - (可选) pluginId (Gateway 解析后附加)
  - (可选) providerId (当前 Provider)
  - (可选) modelId (当前 Model)
  - (可选) sessionKey
```

### 1.2 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "state/huo/tool-call-request.schema.json",
  "title": "Tool Call Request",
  "description": "LLM 发出的 tool call 请求, 由 Gateway 在 intercept() 中接收并校验",
  "type": "object",
  "required": ["toolName", "toolArgs"],
  "definitions": {
    "toolArgs": {
      "description": "工具参数: key-value 结构, 值可以是任意 JSON 类型",
      "type": "object",
      "additionalProperties": true,
      "minProperties": 0
    }
  },
  "properties": {
    "requestId": {
      "description": "请求标识 (Gateway 生成或上游传递)",
      "type": "string",
      "minLength": 8
    },
    "toolName": {
      "description": "LLM 请求的工具名",
      "type": "string",
      "minLength": 1,
      "examples": ["web_search", "web_fetch", "memory_search"]
    },
    "toolArgs": {
      "$ref": "#/definitions/toolArgs"
    },
    "pluginId": {
      "description": "插件 ID (Gateway 解析后填充, 非 LLM 提供)",
      "type": "string",
      "minLength": 1
    },
    "providerId": {
      "description": "当前使用的 Provider ID (非 LLM 提供)",
      "type": "string",
      "minLength": 1
    },
    "modelId": {
      "description": "当前使用的 Model ID (非 LLM 提供)",
      "type": "string",
      "minLength": 1
    },
    "sessionKey": {
      "description": "Session Key (非 LLM 提供)",
      "type": "string",
      "minLength": 1
    },
    "rawToolCallIndex": {
      "description": "在 LLM response 中 tool_calls[] 里的索引",
      "type": "integer",
      "minimum": 0
    }
  },
  "additionalProperties": false
}
```

### 1.3 字段来源

```yaml
字段              | 来源               | 提供时机
──────────────────┼────────────────────┼────────────────
requestId         | Runtime 生成        | Gateway 调用前
toolName          | LLM response        | 解析 LLM 输出
toolArgs          | LLM response        | 解析 LLM 输出
pluginId          | Registry 查询       | Gateway 解析
providerId        | Session 上下文      | Gateway 注入
modelId           | Session 上下文      | Gateway 注入
sessionKey        | Session 上下文      | Gateway 注入
rawToolCallIndex  | LLM response 解析   | Gateway 注入
```

### 1.4 输入校验规则

```yaml
Gateway 接收前的预处理:
  1. 解析 LLM response -> 提取 tool_calls[]
  2. 对每个 tool_call:
     2.1 tool_name -> 格式检查 (小写字母+下划线)
     2.2 tool_args -> 结构检查 (必须是 object)
     2.3 补充上下文信息 (pluginId/providerId/modelId/sessionKey)
  3. 构造 ToolCallInterceptParams -> 传入 intercept()

预处理失败:
  tool_name 格式无效 → reject("invalid_tool_name")
  tool_args 不是 object → reject("invalid_tool_args")
  requestId 缺失 → reject("missing_request_id")
```

---

## 2. Gateway Decision Schema

### 2.1 定义

```yaml
用途: Gateway 的决策结果
位置: state/huo/gateway-decision.schema.json

三个决策值:
  allow  - 放行
  reject - 拒绝
  degrade - 降级 (部分批准 + 建议)
```

### 2.2 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "state/huo/gateway-decision.schema.json",
  "title": "Gateway Decision",
  "description": "Gateway 对 tool call 的决策结果",
  "type": "object",
  "required": ["decision", "gatewayProcessed"],
  "definitions": {
    "reasonCodes": {
      "description": "拒绝/降级的原因枚举",
      "type": "string",
      "enum": [
        "unregistered_tool",
        "capability_not_supported",
        "denied_by_policy",
        "enforcement_rejected",
        "invalid_tool_name",
        "invalid_tool_args",
        "missing_request_id",
        "format_outdated",
        "degradation_advisory"
      ]
    },
    "degradation": {
      "description": "降级建议",
      "type": "object",
      "required": ["fallbackTool"],
      "properties": {
        "fallbackTool": {
          "type": "string",
          "minLength": 1
        },
        "fallbackProvider": {
          "type": "string",
          "minLength": 1
        },
        "fallbackModel": {
          "type": "string",
          "minLength": 1
        },
        "reason": {
          "type": "string",
          "minLength": 1
        }
      },
      "additionalProperties": false
    },
    "enforcementResult": {
      "description": "Capability Enforcement (Phase 6.2.3) 的检查结果",
      "type": "object",
      "properties": {
        "provider": {
          "type": "string",
          "minLength": 1
        },
        "model": {
          "type": "string",
          "minLength": 1
        },
        "capability": {
          "type": "string",
          "minLength": 1
        },
        "allowed": {
          "type": "boolean"
        },
        "reason": {
          "type": "string"
        }
      },
      "required": ["provider", "capability", "allowed"]
    }
  },
  "properties": {
    "requestId": {
      "type": "string",
      "minLength": 8
    },
    "decision": {
      "description": "Gateway 的决策",
      "type": "string",
      "enum": ["allow", "reject", "degrade"]
    },
    "gatewayProcessed": {
      "description": "强制标记: 标识经过 Gateway 处理",
      "type": "boolean",
      "const": true
    },
    "reasonCode": {
      "description": "拒绝/降级的标准化原因 (仅 reject/degrade 时)",
      "$ref": "#/definitions/reasonCodes"
    },
    "reasonMessage": {
      "description": "拒绝/降级的人类可读说明 (可选)",
      "type": "string",
      "maxLength": 200
    },
    "degradation": {
      "description": "降级建议 (仅 degrade 时)",
      "$ref": "#/definitions/degradation"
    },
    "enforcement": {
      "description": "来自 Phase 6.2.3 Enforcement 的结果 (如果有)",
      "$ref": "#/definitions/enforcementResult"
    },
    "pluginId": {
      "description": "目标工具归属的插件 ID",
      "type": "string",
      "minLength": 1
    },
    "toolName": {
      "description": "目标工具名",
      "type": "string",
      "minLength": 1
    },
    "capability": {
      "description": "工具对应的 Phase 3.3 能力名",
      "type": "string",
      "minLength": 1,
      "examples": ["io.web_search", "io.web_fetch", "memory.read"]
    },
    "checks": {
      "description": "Gateway 检查链结果汇总",
      "type": "object",
      "properties": {
        "registered": {
          "type": "boolean"
        },
        "capabilitySupported": {
          "type": "boolean"
        },
        "policyAllowed": {
          "type": "boolean"
        },
        "enforcementAllowed": {
          "type": "boolean"
        }
      },
      "required": ["registered", "capabilitySupported", "policyAllowed", "enforcementAllowed"],
      "additionalProperties": false
    },
    "checksFailed": {
      "description": "检查链中失败的原因 (仅 reject/degrade 时)",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "processedAt": {
      "description": "Gateway 处理时间戳",
      "type": "string",
      "format": "date-time"
    }
  },
  "additionalProperties": false
}
```

### 2.3 决策和原因

```yaml
decision=allow:
  required: decision, gatewayProcessed, requestId, toolName, capability, checks, processedAt

decision=reject:
  required: decision, gatewayProcessed, requestId, toolName, reasonCode, checksFailed, processedAt

decision=degrade:
  required: decision, gatewayProcessed, requestId, toolName, degradation, reasonCode, checksFailed, processedAt
```

---

## 3. Tool Call Event Schema

### 3.1 定义

```yaml
用途: Event Store 中的 tool call 事件记录
位置: state/huo/tool-call-event.schema.json

写入位置:
  memory/events/system/tool-call/{date}.md

Event 包含:
  - gateway_decision (决策结果)
  - 工具元信息 (tool_name / plugin_id / capability)
  - 运行时上下文 (provider / model)
  - 无参数内容, 保留 param_summary
```

### 3.2 Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "state/huo/tool-call-event.schema.json",
  "title": "Tool Call Event",
  "description": "Gateway 记录的 tool call 事件, 用于 Event Store 持久化",
  "type": "object",
  "required": [
    "eventKind",
    "version",
    "requestId",
    "timestamp",
    "toolName",
    "gatewayDecision"
  ],
  "definitions": {
    "enforcementCheck": {
      "description": "Enforcement (Phase 6.2.3) 检查结果",
      "type": "object",
      "properties": {
        "provider": { "type": "string", "minLength": 1 },
        "model": { "type": "string" },
        "capabilitiesRequested": {
          "type": "array",
          "items": { "type": "string", "minLength": 1 },
          "minItems": 1
        },
        "capabilitiesResult": {
          "type": "string",
          "enum": ["allow", "reject", "degrade"]
        }
      },
      "required": ["provider", "capabilitiesRequested", "capabilitiesResult"],
      "additionalProperties": false
    },
    "paramSummary": {
      "description": "工具参数摘要 (非完整内容)", 
      "type": "object",
      "properties": {
        "argCount": {
          "type": "integer",
          "minimum": 0
        },
        "totalChars": {
          "type": "integer",
          "minimum": 0
        },
        "keyNames": {
          "type": "array",
          "items": { "type": "string" },
          "uniqueItems": true
        }
      },
      "required": ["argCount"],
      "additionalProperties": false
    }
  },
  "properties": {
    "eventKind": {
      "description": "事件类型标识",
      "type": "string",
      "const": "tool_call.gateway"
    },
    "version": {
      "description": "Schema 版本",
      "type": "integer",
      "const": 1
    },
    "requestId": {
      "description": "关联请求标识",
      "type": "string",
      "minLength": 8
    },
    "timestamp": {
      "description": "事件发生时间 (ISO 8601)",
      "type": "string",
      "format": "date-time"
    },
    "toolName": {
      "description": "工具名",
      "type": "string",
      "minLength": 1
    },
    "pluginId": {
      "description": "工具归属的插件 ID",
      "type": "string",
      "minLength": 1
    },
    "capability": {
      "description": "对应 Phase 3.3 能力标识",
      "type": "string",
      "minLength": 1
    },
    "gatewayDecision": {
      "description": "Gateway 的决策结果",
      "type": "object",
      "required": ["decision"],
      "properties": {
        "decision": {
          "type": "string",
          "enum": ["allow", "reject", "degrade"]
        },
        "reasonCode": {
          "description": "标准化拒绝原因",
          "type": "string",
          "minLength": 1
        },
        "reasonMessage": {
          "description": "人类可读说明",
          "type": "string"
        },
        "checksFailed": {
          "description": "失败检查项列表",
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "additionalProperties": false
    },
    "enforcement": {
      "description": "Enforcement 检查结果 (包含 provider/capability 决策)",
      "$ref": "#/definitions/enforcementCheck"
    },
    "paramSummary": {
      "description": "工具参数摘要 (不含完整参数内容)",
      "$ref": "#/definitions/paramSummary"
    },
    "requestId": {
      "description": "关联请求标识 (用于与 projection_event 关联)",
      "type": "string",
      "minLength": 8
    },
    "errors": {
      "description": "处理过程中的异常列表",
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "uniqueItems": true
    }
  },
  "additionalProperties": false
}
```

### 3.3 Event 存储规则

```yaml
存储格式: 每行一个 JSON

位置: memory/events/system/tool-call/{date}.md
  该文件每行一个完整 tool_call_event JSON

示例内容:
  {"eventKind":"tool_call.gateway","version":1,"requestId":"req-abc-001","timestamp":"2026-07-19T09:45:00+08:00","toolName":"web_search","pluginId":"builtin","capability":"io.web_search","gatewayDecision":{"decision":"allow"},"paramSummary":{"argCount":2,"totalChars":35,"keyNames":["query","language"]}}

Event 不包含:
  ❌ 工具执行结果
  ❌ 工具参数完整内容
  ❌ LLM hidden reasoning
  ❌ Prompt snapshot
  ❌ Session 私密信息
```

---

## 4. 三层关系

### 4.1 组合图

```
LLM Response
    │
    ├── tool_name   ──→  tool-call-request.schema.json
    ├── tool_args   ──→     ↑
    │                       │ (输入)
    │                       v
    └── Runtime     ──→  Gateway.intercept()
                              │
                              v (输出)
                   ──→  gateway-decision.schema.json
                              │
                              │ (存储)
                              v
                   ──→  tool-call-event.schema.json
```

### 4.2 字段映射

```yaml
tool-call-request        gateway-decision          tool-call-event
─────────────────────    ──────────────────        ────────────────
requestId                requestId                 requestId
toolName                 toolName                  toolName
toolArgs (args object)   —                        paramSummary (精简)
pluginId (注入)          pluginId                  pluginId
providerId (注入)        enforcement.provider      enforcement.provider
modelId (注入)           enforcement.model         enforcement.model
—                        decision                  gatewayDecision.decision
—                        reasonCode                gatewayDecision.reasonCode
—                        checks                    gatewayDecision.checksFailed
—                        degrade                   — (event 不保留 degrade, 已
                                                    在 decision 中表达)
—                        processedAt               timestamp
```

### 4.3 一致性检查

```yaml
每个 Gateway Decision 必须对应 1 个 Tool Call Event.
每个 Tool Call Request (从 LLM 解析的) 必须通过 Gateway 产生 1 个 Decision.

违反:
  LLM response 中 tool_calls.length > gateway_events.length
  → 绕过检测 (Bypass Detection, Phase 6.4 Contract §3)
```

---

## 5. Schema 文件清单

| 文件 | 位置 |
|:---|:---|
| tool-call-request.schema.json | `state/huo/tool-call-request.schema.json` |
| gateway-decision.schema.json | `state/huo/gateway-decision.schema.json` |
| tool-call-event.schema.json | `state/huo/tool-call-event.schema.json` |
| 本设计文档 | `state/huo/PHASE-6.4.1-SCHEMA-DESIGN.md` |

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Phase 6.4.1 Schema Design, 3 schemas (request/decision/event) |
