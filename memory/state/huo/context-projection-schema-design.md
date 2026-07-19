# Context Projection Schema v1 — Design + JSON Schema

**Phase 6.3.1**
**Status:** COMPLETE
**Date:** 2026-07-19
**Dependencies:**
- CONTEXT-PROJECTION-CONTRACT.md v1.0 DRAFT
- provider-capability.schema.json (for pattern reference)

---

## 0. Design Principles

### Schema 覆盖范围

```
Schema 验证:
  ✅ 投影源来源检查 (source in allowed list)
  ✅ 投影格式检查 (format conforms to allowed types)
  ✅ provenance 强制存在
  ✅ expires_at 格式验证
  ✅ 投影大小约束
  ✅ role 约束 (message 类型必须带 role)
  
Schema 不验证:
  ❌ 投影内容语义 (Context 内容由 Runtime 保证)
  ❌ 生命周期执行 (Runtime 保证)
  ❌ 事件记录完整性
  ❌ 权限执行
```

### Schema 层级

```
Level 1: ProjectionEntry (单条投影)
  - 基本字段校验
  - source + format + provenance 强制存在
  
Level 2: ProjectionBundle (单次 Context 构建)
  - 投影列表校验
  - 总大小限制
  - 源分布约束

Level 3: ProjectionEvent (Event 记录)
  - 事件格式校验
  - 与 bundle 的一致性
```

---

## 1. Schema: ProjectionEntry

### File: `context-projection.schema.json`

```jsonc
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "urn:openclaw:schema:context-projection:v1",
  "title": "Context Projection Entry",
  "description": "单条 Context 投影的 Schema，验证来源、格式、provenance",

  "definitions": {
    "projectionSource": {
      "type": "string",
      "enum": [
        "system_instruction",
        "conversation_history",
        "memory",
        "events",
        "tool_result",
        "knowledge",
        "system_state"
      ],
      "description": "投影源分类 (§1.1 允许源 A-G)"
    },

    "projectionFormat": {
      "type": "string",
      "enum": ["text", "json", "message"],
      "description": "投影格式 (§4.1)"
    },

    "projectionTarget": {
      "type": "string",
      "enum": ["system_instruction", "message", "attachment"],
      "description": "投影目标在 LLM 请求中的位置"
    },

    "provenance": {
      "type": "object",
      "properties": {
        "source": {
          "type": "string",
          "enum": [
            "static_config",
            "runtime_session",
            "memory_search",
            "event_query",
            "tool_execution",
            "knowledge_query",
            "runtime_detection"
          ],
          "description": "provenance 来源 (§4.1 provenance.source)"
        },
        "detail": {
          "type": "string",
          "description": "provenance 详细描述",
          "maxLength": 256
        }
      },
      "required": ["source", "detail"],
      "additionalProperties": false
    },

    "textProjection": {
      "type": "object",
      "properties": {
        "type": { "const": "text" },
        "content": {
          "type": "string",
          "maxLength": 8192,
          "description": "文本投影内容，最长 8192 字符"
        },
        "summary": {
          "type": "boolean",
          "default": true,
          "description": "必须是摘要而非原文"
        }
      },
      "required": ["type", "content"],
      "additionalProperties": false
    },

    "jsonProjection": {
      "type": "object",
      "properties": {
        "type": { "const": "json" },
        "content": {
          "type": "object",
          "maxProperties": 50,
          "description": "结构化投影，最多 50 个字段"
        },
        "schema": {
          "type": "string",
          "description": "内容的 schema URI (如果有)"
        }
      },
      "required": ["type", "content"],
      "additionalProperties": false
    },

    "messageProjection": {
      "type": "object",
      "properties": {
        "type": { "const": "message" },
        "role": {
          "type": "string",
          "enum": ["user", "assistant", "tool", "system"],
          "description": "消息角色"
        },
        "content": {
          "type": "string",
          "maxLength": 64000,
          "description": "消息内容"
        }
      },
      "required": ["type", "role", "content"],
      "additionalProperties": false
    },

    "projectionEntry": {
      "type": "object",
      "properties": {
        "source": { "$ref": "#/definitions/projectionSource" },
        "target": { "$ref": "#/definitions/projectionTarget" },
        "format": {
          "oneOf": [
            { "$ref": "#/definitions/textProjection" },
            { "$ref": "#/definitions/jsonProjection" },
            { "$ref": "#/definitions/messageProjection" }
          ]
        },
        "provenance": { "$ref": "#/definitions/provenance" },
        "projected_at": {
          "type": "string",
          "format": "date-time",
          "description": "投影时间 (ISO-8601)"
        },
        "expires_at": {
          "type": "string",
          "format": "date-time",
          "description": "过期时间 (ISO-8601)，可选"
        }
      },
      "required": ["source", "target", "format", "provenance", "projected_at"],
      "additionalProperties": false
    }
  },

  "$ref": "#/definitions/projectionEntry"
}
```

### Validation Rules (beyond schema)

| Rule | Description | Schema Mode |
|:---|:---|:---:|
| R-1 | `source` must be in §1.1 allowed list | ✅ enum |
| R-2 | `source` must not be in §1.2 forbidden list | ✅ enum |
| R-3 | `provenance` is mandatory | ✅ required |
| R-4 | `provenance.source` + `detail` both required | ✅ required |
| R-5 | `format` must match content type | ✅ oneOf |
| R-6 | `text` content max 8192 chars | ✅ maxLength |
| R-7 | `json` content max 50 fields | ✅ maxProperties |
| R-8 | `message` type must have `role` | ✅ required |
| R-9 | `projected_at` must be valid ISO-8601 | ✅ format date-time |
| R-10 | `expires_at` if present must be ISO-8601 | ✅ format date-time |
| R-11 | no undefined fields at any level | ✅ additionalProperties: false |

---

## 2. Schema: ProjectionBundle

### 单次 Context 构建的整体校验

```jsonc
{
  "$id": "urn:openclaw:schema:context-projection-bundle:v1",
  "title": "Context Projection Bundle",
  "description": "单次 Context 构建的完整投影集合",

  "type": "object",
  "properties": {
    "request_id": {
      "type": "string",
      "description": "请求 ID，用于跨系统追踪"
    },
    "projected_at": {
      "type": "string",
      "format": "date-time",
      "description": "构建时间"
    },
    "projections": {
      "type": "array",
      "items": {
        "$ref": "urn:openclaw:schema:context-projection:v1#/definitions/projectionEntry"
      },
      "minItems": 1,
      "maxItems": 50,
      "description": "投影列表，最少 1 条 (至少 system_instruction)"
    },
    "projection_counts": {
      "type": "object",
      "properties": {
        "total_entries": { "type": "integer", "minimum": 1 },
        "total_chars": { "type": "integer", "minimum": 0 },
        "by_source": {
          "type": "object",
          "description": "按源统计投影条目数",
          "additionalProperties": { "type": "integer", "minimum": 0 }
        }
      },
      "required": ["total_entries", "total_chars", "by_source"],
      "additionalProperties": false
    }
  },
  "required": ["request_id", "projected_at", "projections", "projection_counts"],
  "additionalProperties": false
}
```

### Bundle 验证规则

```yaml
Bundle 约束:
  B-1: projections 列表中每条必须通过 entry 验证
  B-2: projections 必须包含至少 1 条 system_instruction 源
  B-3: total_entries = projections.length
  B-4: total_chars = sum(每条投影的内容长度)
  B-5: by_source 统计与 projections 列表一致
  B-6: 同一 projection 不能重复提交 (request_id + projected_at 唯一)
```

---

## 3. Schema: ProjectionEvent

### 事件格式

```jsonc
{
  "$id": "urn:openclaw:schema:context-projection-event:v1",
  "title": "Context Projection Event",
  "description": "Context 构建事件记录格式",

  "type": "object",
  "properties": {
    "type": {
      "const": "context_projection",
      "description": "事件类型 (§6)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "request_id": {
      "type": "string"
    },
    "projections": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": { "$ref": "urn:openclaw:schema:context-projection:v1#/definitions/projectionSource" },
          "query": {
            "type": "string",
            "maxLength": 512,
            "description": "查询描述 (如文件名、namespace)"
          },
          "entries": {
            "type": "integer",
            "minimum": 0
          },
          "total_chars": {
            "type": "integer",
            "minimum": 0
          },
          "provenance": {
            "$ref": "urn:openclaw:schema:context-projection:v1#/definitions/provenance"
          }
        },
        "required": ["source", "query", "entries", "total_chars", "provenance"],
        "additionalProperties": false
      }
    },
    "total_projection_size": {
      "type": "integer",
      "minimum": 0
    },
    "violations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "source": { "type": "string" },
          "reason": {
            "type": "string",
            "enum": [
              "prohibited_source",
              "missing_provenance",
              "invalid_format",
              "no_expires_at",
              "source_not_allowed"
            ]
          }
        },
        "required": ["source", "reason"],
        "additionalProperties": false
      },
      "description": "本次构建中被拒绝的投影 (如果有)"
    }
  },
  "required": ["type", "timestamp", "request_id", "projections", "total_projection_size"],
  "additionalProperties": false
}
```

---

## 4. Schema 验证与 Contract 映射

### §1.1 允许源 → 验证

| Contract §1.1 源 | Schema enum | 验证方式 |
|:---|:---|:---|
| System Instructions | `system_instruction` | ✅ enum |
| Conversation History | `conversation_history` | ✅ enum |
| Memory Projection | `memory` | ✅ enum |
| Event Projection | `events` | ✅ enum |
| Tool Results | `tool_result` | ✅ enum |
| Knowledge Projection | `knowledge` | ✅ enum |
| System State | `system_state` | ✅ enum |

### §1.2 禁止源 → 验证

```yaml
Contract 禁止源:
  X: raw secrets          → 不在 enum 中 → 自然阻止
  Y: raw config           → 不在 enum 中 → 自然阻止
  Z: cross-user memory    → 不在 enum 中 → 自然阻止
  W: reasoning_content    → 不在 enum 中 → 自然阻止

验证方式:
  Schema 层面: 禁止源不在 projectionSource enum 中
  Runtime 层面: 输出 projection 前校验
  双重保障
```

### §4 投影格式 → 验证

| Contract §4 | Schema type | 约束 |
|:---|:---|:---|
| Text | `textProjection` | maxLength: 8192, `summary: true` |
| JSON | `jsonProjection` | maxProperties: 50 |
| Message | `messageProjection` | role required, maxLength: 64000 |

### §5 生命周期 → 验证

```yaml
Contract §5:
  expires_at = projected_at + 5min (Memory/Event/Knowledge)
  expires_at = projected_at + 5s  (System State)

Schema 验证:
  expires_at: format date-time (只验证格式)
  TTL 执行: Runtime 负责，Schema 不验证 TTL

原因:
  Schema 是静态校验
  TTL 是运行时行为
  Schema 保证 expires_at 存在 + 格式正确
  Runtime 保证 TTL 执行
```

### 覆盖总结

| Contract 章节 | Schema 覆盖 | 说明 |
|:---|:---:|:---|
| §1.1 允许源 | ✅ enum | 完全覆盖 |
| §1.2 禁止源 | ✅ enum exclusion | 完全覆盖 |
| §2 Memory↔Context | ⚠️ 间接 | Schema 保证 source=memory 时有 provenance |
| §3 Reasoning Isolation | ⚠️ 间接 | reasoning_content 不在 enum |
| §4 投影格式 | ✅ oneOf x 3 | 完全覆盖 |
| §5 生命周期 | ✅ 格式 | expires_at 格式验证，TTL 运行时 |
| §6 事件 | ✅ event schema | 完全覆盖 |
| §7 权限 | ❌ | Schema 不验证权限执行 |
| §8 检查表 | ⚠️ 部分 | Step 1-4 可 Schema 验证，Step 5 运行时 |
| §9 Capability Registry | ❌ | 不需要 Schema 验证 |
| §10 验证条件 | ⚠️ 部分 | 条件 1-4 可 Schema 验证 |

---

## 5. Schema 文件

### 文件清单

```yaml
context-projection.schema.json:
  定位: 单条投影入口校验 (ProjectionEntry)
  大小: ~120 lines
  内容: definitions + $ref

context-projection-bundle.schema.json:
  定位: 单次 Context 构建校验 (ProjectionBundle)
  大小: ~40 lines
  内容: 组合多个 ProjectionEntry

context-projection-event.schema.json:
  定位: 事件记录校验
  大小: ~50 lines
  内容: Event 格式 + violation 检测
```

---

## 6. 验证场景

### 场景 1: 正常 Context 构建

```yaml
输入:
  request_id: "req-001"
  projections:
    - source: system_instruction
      target: system_instruction
      format: { type: text, content: "You are an AI assistant." }
      provenance: { source: static_config, detail: "system instructions" }
      projected_at: "2026-07-19T09:30:00+08:00"
    - source: conversation_history
      target: message
      format: { type: message, role: user, content: "Hello" }
      provenance: { source: runtime_session, detail: "message 1" }
      projected_at: "2026-07-19T09:30:00+08:00"

验证:
  ✅ 格式正确
  ✅ provenance 完整
  ✅ 源 enum 合法
  ✅ 格式 oneOf 匹配
  ✅ bundle 约束满足
```

### 场景 2: 缺失 provenance

```yaml
输入:
  - source: memory
    target: message
    format: { type: text, content: "User prefers..." }
    # ❌ 缺少 provenance
    projected_at: "2026-07-19T09:30:00+08:00"

验证:
  Schema: provenance is required → ❌ FAIL
  Contract violation: §4.1 provenance required → ❌ VIOLATION
```

### 场景 3: 禁止投影源

```yaml
输入:
  - source: raw_secrets   # ❌ 不在 enum
    ...

验证:
  Schema: raw_secrets not in projectionSource enum → ❌ FAIL
  Contract violation: §1.2 禁止投影 X → ❌ VIOLATION
```

### 场景 4: 投影格式不匹配

```yaml
输入:
  - source: memory
    target: message
    format: { type: json, content: { text: "..." } }
    # memory 投影必须是 text 类型 (§4.2)
    # 但 content 使用了 json 格式

验证:
  Schema: source=memory, format.type=json → ✅ 格式通过
  Contract: §4.2 `memory 投影必须是 text 类型`
  Schema 不验证特定 source 的格式限制
  ⚠️ Schema 覆盖 gap: source-specific format 约束
```

### 场景 5: 空投影列表

```yaml
输入:
  projections: []

验证:
  Schema: minItems: 1 → ❌ FAIL
  Bundle: B-2 要求至少 1 条 system_instruction → ❌ FAIL
```

---

## 7. Notes

### Schema Gaps (notable)

```yaml
1. Source-specific format 约束
   Contract: memory/knowledge 投影必须 text (摘要)
   Schema: 不验证 source+format 组合
  
   原因: 组合约束在 Schema 中需要 conditionals
         oneOf 会导致验证复杂度上升
   缓解: Runtime 层 + 自定义验证器

2. TTL 执行
   Contract: 5min / 5s TTL
   Schema: 只验证 expires_at 格式
   
   原因: TTL 是运行时行为
   缓解: Runtime Event Log 可验证

3. 权限验证
   Contract §7: 谁可以定义投影
   Schema: 不验证权限
   
   原因: 权限是执行层 (Enforcement-like)
   缓解: 结合 Identity 层验证
```

### Design Decision: 为什么不用 conditional schema

```yaml
问题: source=memory 要求 format=text
      knowledge 也要求 format=text

方案 A: conditional if/then/else in JSON Schema
  优点: 所有约束在 schema 中
  缺点: 
    - Draft-07 if/then 有限
    - 7 种 source × 3 种 format = 21 条件
    - schema size 爆炸

方案 B: enum + Runtime 验证
  当前选择
  优点:
    - Schema 保持简单 (120 lines vs 400+)
    - 约束在 Runtime 实现
    - 可维护 > 可静态验证
  缺点:
    - 不是所有约束都在 Schema 中
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Context Projection Schema Design, 3 schema files, 5 scenarios, gaps documented |
