# Phase 6.4.3 Tool Call Gateway — Validation

**Status:** COMPLETE
**Date:** 2026-07-19
**Base documents:**
- TOOL-CALL-GATEWAY-CONTRACT.md v1 DRAFT (Phase 6.4)
- PHASE-6.4.1-SCHEMA-DESIGN.md (Phase 6.4.1)
- tool-call-request.schema.json, gateway-decision.schema.json, tool-call-event.schema.json
- PHASE-6.4.2-RUNTIME-INTEGRATION-DESIGN.md (Phase 6.4.2)

---

## 1. Invariant 定义

### 1.1 Contract Invariants (G-001~G-012)

```yaml
G-001: 所有 LLM 发出的 tool call 必须经过 Gateway
G-002: Gateway 不执行工具
G-003: Gateway 不修改工具参数
G-004: Gateway 不缓存工具结果
G-005: Gateway 不注册工具能力
G-006: Gateway 记录每个 tool call 的 event
G-007: Gateway 拒绝未注册的 tool
G-008: Gateway 拒绝能力不匹配的 tool
G-009: Gateway 检测并标记绕过路径
G-010: Gateway 的拒绝不影响 LLM 主路径
G-011: Gateway 不依赖 Provider 的 allow/deny
G-012: Gateway 不替换 Plugin 的 allowlist/denylist
```

### 1.2 Integration Invariants (I-001~I-005)

```yaml
I-001: Gateway 可开关 (disabled → 跳过, 走现有路径)
I-002: Gateway 失败不阻塞 LLM 主路径 (allowOnFailure=true)
I-003: Event 写入异步不阻塞 (fire-and-forget)
I-004: 绕过检测不影响 tool 执行 (only log, 不阻塞)
I-005: Gateway 配置变更不影响现有 Policy 层
```

---

## 2. 验证场景设计

### 2.1 验证矩阵

| 场景 | 验证 | 覆盖 Invariant |
|:---|:---|---:|
| V1 | tool call 必经 Gateway | G-001, I-001 |
| V2 | Gateway 不执行工具 | G-002, G-003, G-004, G-005 |
| V3 | decision 必有 event | G-006, I-003 |
| V4 | 未注册工具 reject | G-007 |
| V5 | 能力不匹配 reject/degrade | G-008, G-011 |
| V6 | 绕过检测 | G-009, I-004 |
| V7 | Gateway failure 不阻断 LLM | G-010, I-002 |
| V8 | Gateway 不替换 Policy | G-012, I-005 |

### 2.2 一致性检查域

| Domain | 参与文件 |
|:---|:---|
| Schema ↔ Contract | tool-call-request ↔ §2 Gateway interface |
| Schema ↔ Schema | request → decision → event 三层组合 |
| Schema ↔ Integration | schema 字段与 Runtime 数据来源一致性 |
| Contract ↔ Integration | §2-Gateway interface 与 §3-flow 一致性 |
| Event ↔ Integration | event 写入点与 async model 一致性 |

---

## 3. 验证结果

### V1: tool call 必经 Gateway

**场景 V1a: Gateway enabled**
```
条件: config.toolCallGateway.enabled = true
输入: LLM 发出 tool_call { name: "web_search", args: { query: "news" } }

预期:
  tool_call → Gateway.intercept() → [Gateway 内部流程] → decision
  tool 仅在 Gateway 决策后进入 Policy 层

验证点:
  [1.1] intercept point 在执行之前 → ✅ PHASE-6.4.2 §1.2
  [1.2] LLM tool_calls → Gateway → execution 单向链 → ✅ PHASE-6.4.2 §2.1
  [1.3] Gateway 决策后 tool 才可执行 → ✅ PHASE-6.4.2 §3.1
```

**场景 V1b: Gateway disabled**
```
条件: config.toolCallGateway.enabled = false
输入: LLM 发出 tool_call

预期:
  Gateway 无操作
  tool call 走现有路径 (跳过 Gateway)

验证点:
  [1.4] disabled → 跳过 Gateway → ✅ PHASE-6.4.2 §8.2 B1
  [1.5] 走现有 Policy → execution 路径 → ✅ PHASE-6.4.2 §1.4
  [1.6] 现有路径不变 → ✅ I-001
```

**场景 V1c: Gateway enabled, 无 tool call**
```
条件: LLM 未产生 tool_calls (纯文本响应)

预期:
  Gateway 无操作
  不产生 event

验证点:
  [1.7] 空 tool_calls → Gateway 无操作 → ✅ PHASE-6.4.2 §8.2 B2
  [1.8] 不产生 event → ✅ Event 设计 (无 event = 无 tool call)
```

**结论: G-001 ✅, I-001 ✅**

---

### V2: Gateway 不执行工具

**场景 V2a: Gateway 不调用工具执行**
```
条件: Gateway.intercept() 执行期间

检查项:
  [2.1] Gateway 不调用 tool.execute() → ✅ 设计: intercept() 返回 decision, 不执行
  [2.2] execute() 调用属于 Tool Adapter 层 → ✅ PHASE-6.4.2 §1.2
  [2.3] Tool Adapter 在 Gateway 之后 → ✅ PHASE-6.4.2 §1.2
```

**场景 V2b: Gateway 不修改参数**
```
条件: Gateway 收到 tool args

检查项:
  [2.4] intercept() 只读取 args, 不修改 → ✅ PHASE-6.4.2 §1.3 Step 2-5
  [2.5] decision 输出不含 args 副本 (不在 decision schema 中) → ✅ gateway-decision.schema.json
  [2.6] params_summary 只含 argCount + totalChars, 不含修改 → ✅ tool-call-event.schema.json
```

**场景 V2c: Gateway 不缓存结果**
```
条件: Gateway 处理 tool call 期间

检查项:
  [2.7] 无缓存层设计 → ✅ §1.3 "Gateway 不做什么"
  [2.8] tool 执行在 Gateway 之后, Gateway 不接触结果 → ✅ PHASE-6.4.2 §1.2
  [2.9] Event 不含 tool result → ✅ tool-call-event.schema.json (params_summary, no results)
```

**场景 V2d: Gateway 不注册能力**
```
条件: Gateway.intercept() 期间

检查项:
  [2.10] Registry 查询只读 → ✅ PHASE-6.4.2 §7.1 Gateway 不写 Registry
  [2.11] Capability Registry 查询由 Gateway 明确排除写操作 → ✅ TOOL-CALL-GATEWAY-CONTRACT.md §0
```

**结论: G-002 ✅, G-003 ✅, G-004 ✅, G-005 ✅**

---

### V3: decision 必有 event

**场景 V3a: allow → event**
```
条件: Gateway decision = allow

预期:
  tool-call-event 被写入
  eventKind: "tool_call.gateway"
  gatewayDecision.decision: "allow"

验证点:
  [3.1] 所有 decision 必经 recordEvent() → ✅ PHASE-6.4.2 §4.1
  [3.2] allow event 记录成功 → ✅ PHASE-6.4.2 §4.3 示例
  [3.3] event 包含必要 metadata → ✅ tool-call-event.schema.json
```

**场景 V3b: reject → event**
```
条件: Gateway decision = reject

预期:
  event 被写入
  gatewayDecision.decision: "reject"
  reasonCode 和 checksFailed 包含在 event 中

验证点:
  [3.4] reject 同样触发 event 写入 → ✅ PHASE-6.4.2 §4.1
  [3.5] reject 原因写入 event → ✅ PHASE-6.4.2 §4.3 示例
```

**场景 V3c: degrade → event**
```
条件: Gateway decision = degrade

预期:
  event 被写入
  gatewayDecision.decision: "degrade"
  degradation 信息包含在 event 中

验证点:
  [3.6] degrade 同样触发 event 写入 → ✅ PHASE-6.4.2 §4.1
  [3.7] degradation_advisory 包含在 event → ✅ PHASE-6.4.2 §4.3
```

**场景 V3d: event 异步, 不阻断 decision**
```
条件: event 写入耗时 (磁盘 I/O)

预期:
  eventWriter.record() 立即返回
  decision 返回不等待写入完成
  tool 执行在 event 写入确认之前开始

验证点:
  [3.8] event 写入 fire-and-forget → ✅ PHASE-6.4.2 §4.1
  [3.9] event 写入失败不阻挡 decision 返回 → ✅ PHASE-6.4.2 §5.4
  [3.10] tool 执行与 event 写入无因果依赖 → ✅ PHASE-6.4.2 §4.1
```

**结论: G-006 ✅, I-003 ✅**

---

### V4: 未注册工具 reject

**场景 V4a: 完全未注册**
```
条件: toolName 不在 Plugin Registry 或 Core Tool Registry 中
输入: tool_call { name: "execute_script", args: { script: "rm -rf /" } }

预期:
  Registry 查询失败
  decision: reject
  reasonCode: "unregistered_tool"
  checksFailed: ["registered"]

验证点:
  [4.1] Registry 查询 toolName → 未注册 → ✅ PHASE-6.4.2 §1.3 Step 3
  [4.2] reject 决策 → ✅ PHASE-6.4.2 §3.2
  [4.3] 未注册一定 reject, 不考虑 allow/deny → ✅ G-007
```

**场景 V4b: Plugin 工具未启用**
```
条件: toolName 在 Plugin Registry 中, 但 plugin 未启用
输入: tool_call { name: "canvas_render", pluginId: "canvas" }
但 PLUGIN-ENABLED: canvas = false

预期:
  Registry 查询返回 pluginId, 但 plugin 不可用
  此情况由现有 Policy 层处理 (plugin-disabled)
  Gateway 不重复检查 (职责分离)

验证点:
  [4.4] Gateway 只查 Registry, 不查 plugin enabled → ✅ G-012 (Gateway 不替换 Plugin allowlist)
  [4.5] Policy 层处理 plugin-disabled → ✅ 现有行为
  [4.6] Gateway event 记录: toolName 已注册但 Policy 层可拒绝 → ✅ 设计接受的路径
```

**场景 V4c: 拼写错误的 tool name**
```
条件: LLM 推断出错误的 tool name
输入: tool_call { name: "web_searcch", args: { ... } }

预期:
  Registry 查询失败
  decision: reject
  reasonCode: "unregistered_tool"
  event 记录错误名

验证点:
  [4.7] 拼写错误 → Registry 未注册 → reject → ✅ G-007
  [4.8] LLM 收到 reject 后自纠 → ✅ PHASE-6.4.2 §3.2 (LLM 可选择重试)
```

**结论: G-007 ✅**

---

### V5: 能力不匹配 reject/degrade

**场景 V5a: 能力完全不支持 → reject**
```
条件: tool 要求的能力 provider 完全不支持
示例: tool: "gpt4_vision", provider: "deepseek"
      skill.vision 不在 deepseek capability registry 中

预期:
  capability check 失败
  decision: reject
  reasonCode: "capability_not_supported"
  checksFailed: ["capabilitySupported"]

验证点:
  [5.1] Capability Registry 查询 → 不支持 → ✅ PHASE-6.4.2 §1.3 Step 4
  [5.2] reject 决策 → ✅ G-008
  [5.3] event 包含 capability_not_supported → ✅ PHASE-6.4.2 §4.2
```

**场景 V5b: 能力部分支持 → degrade**
```
条件: tool 的部分能力受支持
示例: tool: "web_search", mode: "image" — 当前 provider 不支持图像搜索
      provider 支持 web_search 文本搜索

预期:
  capability check 部分支持
  decision: degrade
  reasonCode: "degradation_advisory"
  degradation 含 fallbackTool: "image_search" 建议

验证点:
  [5.4] Capability Registry 查询 → 部分支持 → ✅ PHASE-6.4.2 §3.3
  [5.5] degrade 包含 fallback 建议 → ✅ PHASE-6.4.2 §3.3
  [5.6] LLM 可选择降级方案 → ✅ PHASE-6.4.2 §3.3 (LLM 触发新的 tool_call)
```

**场景 V5c: 能力完全支持 → allow**
```
条件: tool 所有能力 provider 支持
示例: tool: "web_search", provider: "deepseek", mode: "text"

预期:
  capability check 通过
  decision: allow

验证点:
  [5.7] Capability Registry 查询 → 支持 → ✅ PHASE-6.4.2 §3.1
  [5.8] allow 决策 → ✅ 正常路径
```

**场景 V5d: Gateway 能力检查不替代 Provider 决策**
```
条件: Gateway 查到能力支持, 但 Provider 自身拒绝

预期:
  Gateway decision = allow
  Provider 执行时拒绝
  Provider 拒绝属于下游, Gateway 不干涉

验证点:
  [5.9] Gateway 查 capability → allow → ✅ G-011 (Gateway 不依赖 Provider allow/deny)
  [5.10] Provider 拒绝是独立决策 → ✅ Contract §1.4
```

**结论: G-008 ✅, G-011 ✅**

---

### V6: 绕过检测

**场景 V6a: 检测到 tool call 未经过 Gateway**
```
条件: BypassDetector 对比 LLM tool_calls 和 Gateway events

输入:
  LLM tool_calls = ["web_search", "canvas_render"]
  Gateway events  = ["web_search"] (canvas_render 没有 event)

预期:
  BypassDetector.detect() 检测到:
    toolCall "canvas_render" 没有对应 event
    bypassType: "gateway_bypassed"
    severity: "alert"

验证点:
  [6.1] BypassDetector 可检测缺失 event → ✅ PHASE-6.4.2 §6.3
  [6.2] "gateway_bypassed" → ALERT → ✅ PHASE-6.4.2 §6.3 [5]
```

**场景 V6b: 检测到 event 数量不匹配**
```
条件: LLM tool_calls > Gateway events (部分 event 丢失)

输入:
  LLM tool_calls = ["web_search", "memory_search", "read"]
  Gateway events  = ["web_search", "read"] (memory_search event 丢失)

预期:
  BypassDetector 检测到数量不一致
  找到具体哪个 tool call 缺失
  bypassType: "gateway_missing_event"
  severity: "warn"

验证点:
  [6.3] 数量不匹配检测 → ✅ PHASE-6.4.2 §6.3 [4]
  [6.4] "gateway_missing_event" → WARN → ✅ PHASE-6.4.2 §6.3 [5]
```

**场景 V6c: 绕过检测不影响执行**
```
条件: BypassDetector 在 tool call 执行完成后运行

预期:
  BypassDetector.detect() 不干涉执行结果
  绕过记录仅限于 event/log

验证点:
  [6.5] BypassDetector 在 Phase 5 之后运行 → ✅ PHASE-6.4.2 §6.1
  [6.6] bypass 不撤销已执行的 tool → ✅ PHASE-6.4.2 §6.4 (only log)
  [6.7] bypass 不重新触发 Gateway → ✅ PHASE-6.4.2 §6.4
```

**场景 V6d: bypass detection mode 可配置**
```
条件: config.toolCallGateway.bypassDetectionMode = "log" | "warn" | "alert"

预期:
  "log": 记录日志, 不通知
  "warn": logWarn, 写入 bypass event
  "alert": logWarn + bypass event + 触发 Governance Alert

验证点:
  [6.8] mode="log" → 仅日志 → ✅ PHASE-6.4.2 §6.4
  [6.9] mode="warn" → logWarn + event → ✅ PHASE-6.4.2 §6.4
  [6.10] mode="alert" → logWarn + event + alert → ✅ PHASE-6.4.2 §6.4
  [6.11] 所有 mode 不影响 tool 执行 → ✅ PHASE-6.4.2 §6.4 (I-004)
```

**场景 V6e: bypass detection disabled**
```
条件: config.toolCallGateway.bypassDetectionEnabled = false

预期:
  BypassDetector 不运行
  无 bypass 日志

验证点:
  [6.12] disabled → BypassDetector 跳过 → ✅ PHASE-6.4.2 §6.1
```

**结论: G-009 ✅, I-004 ✅**

---

### V7: Gateway failure 不阻断 LLM

**场景 V7a: Gateway 不可用 → 放行 (allowOnFailure=true)**
```
条件: Gateway 服务故障, allowOnFailure = true (默认)
LLM 发出 tool_call

预期:
  logWarn("ToolCallGateway unavailable, skipping")
  Gateway 跳过
  tool call 走现有路径
  LLM 主路径不受影响

验证点:
  [7.1] Gateway 不可用 → skip → ✅ PHASE-6.4.2 §5.1
  [7.2] 走现有路径 → ✅ PHASE-6.4.2 §5.1
  [7.3] 事件丢失 (无 event) → ✅ 设计容忍
  [7.4] LLM 主路径不受影响 → ✅ G-010
```

**场景 V7b: Gateway 不可用 → 拒绝 (allowOnFailure=false)**
```
条件: Gateway 服务故障, allowOnFailure = false
LLM 发出 tool_call

预期:
  logWarn("ToolCallGateway unavailable, rejecting all tool calls")
  所有 tool call 被拒绝
  LLM 主路径不受影响

验证点:
  [7.5] allowOnFailure=false → 拒绝所有 → ✅ PHASE-6.4.2 §5.1
  [7.6] 拒绝不影响 LLM 主路径 → ✅ PHASE-6.4.2 §5.5 失败矩阵
```

**场景 V7c: Schema 校验失败 → reject, 不影响 LLM**
```
条件: toolName = "" (空字符串) 或 toolArgs = null

预期:
  Gateway 校验失败
  decision: reject
  reasonCode: "invalid_tool_name" / "invalid_tool_args"
  tool 未执行
  LLM 收到 reject 结果 (可重试)

验证点:
  [7.7] schema 校验失败 → reject → ✅ PHASE-6.4.2 §5.2
  [7.8] reject 返回 → 不抛异常 → ✅ PHASE-6.4.2 §5.3
  [7.9] LLM 主路径不受影响 → ✅ G-010
```

**场景 V7d: Event 写入失败 → 不影响 LLM**
```
条件: 文件写入异常 (磁盘满 / 权限)

预期:
  logWarn("ToolCallEvent write failed")
  event 丢失 (不重试)
  decision 正常返回
  tool 正常执行

验证点:
  [7.10] event 写入失败 → 不阻塞 → ✅ PHASE-6.4.2 §5.4
  [7.11] event 写入失败 → 不重试 → ✅ PHASE-6.4.2 §5.4
  [7.12] LLM 主路径不受影响 → ✅ G-010
```

**场景 V7e: Registry 查询失败 → 保守拒绝**
```
条件: Plugin Registry / Capability Registry 不可用

预期:
  保守策略: reject
  reasonCode: "unregistered_tool"
  event 记录: errors["registry_lookup_failed"]
  tool 未执行
  LLM 主路径不受影响

验证点:
  [7.13] Registry 不可用 → 保守拒绝 → ✅ PHASE-6.4.2 §5.3
  [7.14] 备选 (allowOnFailure): 降级到 Policy 层 → ✅ PHASE-6.4.2 §5.3
  [7.15] LLM 主路径不受影响 → ✅ G-010
```

**结论: G-010 ✅, I-002 ✅**

---

### V8: Gateway 不替换 Policy

**场景 V8a: Gateway allowlist 与 Plugin allowlist 独立**
```
条件: Gateway 允许, 但 Plugin allowlist 拒绝

输入:
  Gateway.decision = allow
  Policy: tool is denied (allowlist)

预期:
  Gateway 放行 → Policy 拒绝 → tool 不执行
  Gateway event 记录: allow
  Policy 拒绝由 Policy 层处理

验证点:
  [8.1] Gateway 放行 + Policy 拒绝 = 不执行 → ✅ PHASE-6.4.2 §1.2
  [8.2] Gateway 不取消 Policy 拒绝 → ✅ G-012
```

**场景 V8b: Gateway reject + Policy allow (冲突)**
```
条件: Gateway 拒绝, 但 Policy 允许

输入:
  Gateway.decision = reject (未注册)
  Policy: no deny rule (允许)

预期:
  Gateway 拒绝 = tool 不经过 Policy
  Gateway event 记录: reject
  Policy 不介入

验证点:
  [8.3] Gateway reject → tool 不进 Policy → ✅ PHASE-6.4.2 §1.3 Step 3
  [8.4] Gateway 决策独立于 Policy → ✅ G-012
```

**场景 V8c: 配置变更不影响 Policy**
```
条件: Gateway 配置从 disabled → enabled

预期:
  Policy (allowlist/denylist) 配置不变
  Policy 层继续按原配置运行
  Gateway 只是叠加, 不替换

验证点:
  [8.5] Gateway 配置变更 → Policy 层不变 → ✅ PHASE-6.4.2 关于配置 §1.4
  [8.6] Policy 层继续独立运行 → ✅ PHASE-6.4.2 §8.1 I-005
```

**结论: G-012 ✅, I-005 ✅**

---

## 4. Schema 一致性验证

### 4.1 三层 Schema 链

```
tool-call-request.schema.json     →  LLM → Gateway 输入格式
gateway-decision.schema.json      →  Gateway → Runtime 决策输出
tool-call-event.schema.json       →  Gateway → Event Store 持久化
```

### 4.2 字段映射一致性

| 数据域 | request | decision | event | 一致? |
|:---|:---|:---|:---|---:|
| toolName | required string | required string | required string | ✅ |
| toolArgs | required object | — | — (excluded) | ✅ |
| providerId | required string | optional string | optional string | ✅ |
| modelId | required string | optional string | optional string | ✅ |
| pluginId | optional string | optional string | optional string | ✅ |
| decision | — | "allow"/"reject"/"degrade" | same via gatewayDecision | ✅ |
| reasonCode | — | optional string | optional string | ✅ |
| checksFailed | — | optional string[] | optional string[] | ✅ |
| requestId | required string | required string | required string | ✅ |
| paramSummary | — | — | argCount+totalChars+keyNames | ✅ |

### 4.3 Schema → Contract 一致性

```
C1: tool-call-request 不包含 execution 字段 (G-002)        ✅
C2: tool-call-request 不允许修改 (readOnly) (G-003)         ✅
C3: decision 不包含 tool result (G-004)                     ✅
C4: decision 不包含 capability 声明 (G-005)                 ✅
C5: event 包含 gatewayDecision (G-006)                      ✅
C6: event 不包含 tool result                                ✅
C7: event 不包含 reasoning_content (Phase 6.1)              ✅
C8: event 不包含 full prompt/context (Phase 6.3)            ✅
C9: requestId 在 request→decision→event 一致                ✅
```

### 4.4 Schema → Integration 一致性

```
D1: request.providerId 来自 Runtime 上下文 (config.model.xxx)  ✅ (PHASE-6.4.2 §1.3 Step 1)
D2: request.toolName 来自 LLM response 解析                  ✅ (现有解析逻辑)
D3: decision 输出到 Policy 层                                 ✅ (PHASE-6.4.2 §1.2)
D4: event 写入 memory/events/system/tool-call/               ✅ (PHASE-6.4.2 §4.2)
D5: paramSummary 只含象元数据, 不包含 args 值                ✅ (Contract §4)
```

**Schema 一致性: ✅ ALL PASS**

---

## 5. 已知缺口 (归属 Phase 7+)

与 Phase 6.3 验证相同, 以下缺口不阻塞 Phase 6.4 冻结:

| 缺口 | 归属 | 说明 |
|:---|:---|:---|
| Plugin 直接调用工具 API (B1) | Phase 7+ | Gateway 覆盖 LLM 路径, Plugin 内直接 call 绕过 |
| External Worker Context bypass (B2) | Phase 7+ | Worker 直接调用 Provider API 绕过 Gateway |
| Gateway 实现层性能 | Phase 7 | Runtime 代码层优化的性能基准 |
| bypass auto-block | Phase 7+ | 当前 bypass 只 detect 不 block |

与 Phase 6.3 验证已知缺口合并:

| 缺口 | 原始归属 | 状态 |
|:---|:---|---:|
| Unknown-source data injection by plugins | Phase 6.3 GAP → Phase 6.6 | 未改变 |
| External Worker Context bypass | Phase 6.3 GAP → Phase 6.6 (Phase 6.4 B2) | 未改变 |
| Plugin 直接调用 | Phase 6.4 B1 → Phase 7+ | 未改变 |

---

## 6. 汇总

### 6.1 Invariant 验证结果

| Invariant | 验证场景 | 结果 |
|:---|:---|---:|
| G-001: 必经 Gateway | V1a, V1b, V1c | ✅ |
| G-002: 不执行工具 | V2a | ✅ |
| G-003: 不修改参数 | V2b | ✅ |
| G-004: 不缓存结果 | V2c | ✅ |
| G-005: 不注册能力 | V2d | ✅ |
| G-006: 必有 event | V3a, V3b, V3c, V3d | ✅ |
| G-007: 未注册 reject | V4a, V4b, V4c | ✅ |
| G-008: 能力不匹配 | V5a, V5b, V5c, V5d | ✅ |
| G-009: 绕过检测 | V6a, V6b, V6c, V6d, V6e | ✅ |
| G-010: 不阻断 LLM | V7a, V7b, V7c, V7d, V7e | ✅ |
| G-011: 不依赖 Provider | V5d | ✅ |
| G-012: 不替换 Policy | V8a, V8b, V8c | ✅ |
| I-001: 可开关 | V1b | ✅ |
| I-002: 失败不阻塞 | V7a, V7b, V7c, V7d, V7e | ✅ |
| I-003: Event 异步 | V3d | ✅ |
| I-004: 绕过不影响 | V6c, V6d | ✅ |
| I-005: Policy 不变 | V8c | ✅ |

### 6.2 Schema 一致性

| Domain | 检查项 | 结果 |
|:---|:---|---:|
| Schema ↔ Contract | C1-C9 | ✅ |
| Schema ↔ Schema | 字段映射 | ✅ |
| Schema ↔ Integration | D1-D5 | ✅ |

### 6.3 总计

```
Verification scenarios:  8 (V1-V8)
      V1: 必经 Gateway       3 sub-scenarios
      V2: 不执行工具          4 sub-scenarios
      V3: 必有 event          4 sub-scenarios
      V4: 未注册 reject       3 sub-scenarios
      V5: 能力不匹配          4 sub-scenarios
      V6: 绕过检测            5 sub-scenarios
      V7: 失败不阻断          5 sub-scenarios
      V8: 不替换 Policy       3 sub-scenarios
Total sub-scenarios:     31

Contract → Schema → Event → Integration 一致性: ALL PASS
RTL (Reasoning Isolation + Capability + Context + Gateway) 闭环: COMPLETE
已知缺口: Phase 7+ (Plugin direct call, Ext Worker bypass, Implementation perf)
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Phase 6.4.3 Validation, 8 场景 × 31 子场景, 17 invariants ALL PASS |
