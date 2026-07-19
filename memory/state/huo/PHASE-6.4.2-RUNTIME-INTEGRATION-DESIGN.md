# Phase 6.4.2 Tool Call Gateway — Runtime Integration Design

**Status:** COMPLETE
**Date:** 2026-07-19
**Dependencies:**
- TOOL-CALL-GATEWAY-CONTRACT.md v1 DRAFT (Phase 6.4)
- tool-call-request.schema.json (Phase 6.4.1)
- gateway-decision.schema.json (Phase 6.4.1)
- tool-call-event.schema.json (Phase 6.4.1)
- CONTEXT-PROJECTION-CONTRACT.md v1.0 FINAL (Phase 6.3)
- RUNTIME-ENFORCEMENT-DESIGN.md v1 (Phase 6.2.3)

---

## 0. 定位

Phase 6.4.2 定义 Gateway 如何在现有 Runtime 中接入。

### 设计原则

```yaml
1. 旁路治理 (Sidecar Governance)
   与 Phase 6.3.3 一致: Gateway 不修改 Runtime 核心逻辑
   通过插入拦截点 (intercept point) 工作

2. 零侵入
   不修改:
   - tool.execute() 签名
   - Plugin tool registration
   - allowlist/denylist 逻辑
   - LLM response 解析逻辑
   
   新增:
   - intercept point (配置开关)
   - Gateway event writer (异步)
   - Bypass detection (后处理)

3. 异步非阻塞
   Event write: fire-and-forget
   Gateway failure: 不阻塞 LLM 主路径 (与 Phase 6.3 §6 一致)

4. 可开关
   Gateway 默认 disabled, 配置启用
   Gateway 不可用时, tool call 走现有路径 (无治理降级)
```

---

## 1. 接入位置

### 1.1 现有 tool call 流水线 (现状)

```
LLM Response
    │
    ├── 解析 tool_calls[]
    │
    v
[before_tool_call hooks]       ← attempt.ts ~line 2234
    │
    ├── name 校验
    ├── policy 检查 (allow/deny)
    │
    v
[Tool execution]                ← attempt.ts ~line 3274
    │
    ├── toolParams.tool.execute(id, args, signal, onUpdate)
    │
    v
[Tool Result → LLM]
```

### 1.2 Gateway 接入位置 (设计)

```
LLM Response
    │
    ├── 解析 tool_calls[]
    │
    v
[⭐ Tool Call Gateway]           ← 新增 intercept point
    │                              位置: 在 execute() 之前
    │                              条件: 配置 gateway.enabled = true
    │
    ├── schema validate          ← tool-call-request.schema.json
    ├── registry lookup          ← Plugin Registry + CAPABILITY-REGISTRY
    ├── capability check         ← provider-capability-registry.json
    ├── enforcement query        ← Phase 6.2.3 (optional)
    ├── decision                 ← allow | reject | degrade
    ├── event write (async)      ← tool-call-event.schema.json
    │
    v
[Policy layer]                   ← 现有 (allow/deny remaining)
    │
    v
[Tool execution]                 ← 现有 (unchanged)
    │
    ├── toolParams.tool.execute(id, args, signal, onUpdate)
    │
    v
[Tool Result → LLM]
```

### 1.3 为什么插在执行前

```yaml
原因:
  此时 tool name 和 args 已从 LLM 解析完成
  Runtime 上下文 (providerId, modelId, sessionKey) 可用
  政策层尚未执行, Gateway 可提前拒绝

位置选择影响:
  未注册工具 → 提前拒绝, 节省 Policy 和 Tool Adapter 执行
  能力不匹配 → 提前降级/拒绝
  Event 在政策层之前记录, 可保留"被政策拒绝"的完整审计信息
```

### 1.4 配置整合

```yaml
toolCallGateway:
  enabled: false                    # 默认关闭
  enforcementCheck: false           # 是否查询 Phase 6.2.3 (可选)
  eventWriteEnabled: true           # 是否写 event
  eventPath: "memory/events/system/tool-call/"  # event 存储位置
  bypassDetectionEnabled: false      # 是否启用绕过检测
  bypassDetectionMode: "log"         # log | warn | alert
  allowOnFailure: true              # Gateway 不可用时, 放行 (降级)
  schemaVersion: 1                  # 当前 schema 版本
```

---

## 2. Tool Call 生命周期

### 2.1 总览

```
┌─────────────────────────────────────────────────────────┐
│                    Tool Call 生命周期                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Phase 1: LLM Output                                    │
│  ├── LLM generates tool_calls[] in response             │
│  ├── Runtime parses tool_name + tool_args               │
│  └── tool_calls[] ready for dispatch                    │
│                                                         │
│  Phase 2: Gateway Interception (新增)                   │
│  ├── request_id 生成                                    │
│  ├── schema validation (tool-call-request schema)       │
│  ├── registry lookup (Plugin Registry)                  │
│  ├── capability check (Capability Registry)             │
│  ├── enforcement query (Phase 6.2.3, optional)          │
│  ├── decision: allow / reject / degrade                  │
│  └── event write (async)                                │
│                                                         │
│  Phase 3: Policy (现有)                                 │
│  ├── allowlist/denylist 检查                            │
│  └── policy decision                                    │
│                                                         │
│  Phase 4: Tool Execution (现有)                         │
│  ├── tool.execute(toolCallId, args, signal, onUpdate)   │
│  └── tool result returned                               │
│                                                         │
│  Phase 5: Result Processing (现有)                      │
│  ├── result truncation / formatting                     │
│  └── result → LLM next turn                            │
│                                                         │
│  Phase 6: Post-processing (新增)                        │
│  ├── bypass detection (对比 tool_calls[] vs events)      │
│  └── audit report                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Phase 1 → Phase 2 转换

```yaml
LLM Output:
  {
    "choices": [{
      "message": {
        "content": "...",
        "tool_calls": [
          {
            "id": "call_xxx",
            "type": "function",
            "function": {
              "name": "web_search",
              "arguments": "{\"query\": \"today news\"}"
            }
          }
        ]
      }
    }]
  }

→ Runtime 解析:
  tool_calls[] = [
    {
      id: "call_xxx",
      name: "web_search",
      args: { query: "today news" }
    }
  ]

→ Gateway 接收 (Phase 2 入口):
  ToolCallInterceptParams {
    requestId:       "req-hash-001",
    toolName:        "web_search",
    toolArgs:        { query: "today news" },
    pluginId:        "builtin",        // Registry 查询结果
    providerId:      "deepseek",        // 当前 provider
    modelId:         "deepseek-v4-flash", // 当前 model
    sessionKey:      "tg:1411509945",
    rawToolCallIndex: 0
  }
```

### 2.3 Phase 2 internal (Gateway 内部)

```yaml
Gateway.intercept():
  Step 1: 构造 request
    - 生成 requestId (或复用上游 traceId)
    - 从 Runtime 上下文提取 providerId / modelId / sessionKey
    - 从 Registry 查询 pluginId (通过 toolName 查询)
    - 获取 capability (通过 toolName 查询 Capability Registry)

  Step 2: Schema 校验
    - 使用 tool-call-request.schema.json
    - 校验 toolName: 非空, 合法格式
    - 校验 toolArgs: object, 非 null
    - 校验 providerId / pluginId: 非空 (如果已解析)

  Step 3: Registry 查询
    - 检查 toolName 是否在 Plugin Registry 中注册
    - 如果是 plugin tool: 获取 pluginId
    - 如果是 core tool: 标记为 core
    - 未注册 → reasonCode: "unregistered_tool"

  Step 4: Capability 校验
    - 从 CAPABILITY-REGISTRY.md 查询 toolName → capability 映射
    - 从 provider-capability-registry.json 查询 capability 是否支持
    - 不支持 → reasonCode: "capability_not_supported"
    - 部分支持 → degradation_advisory

  Step 5: Enforcement 查询 (可选, 取决于配置)
    - 调用 Phase 6.2.3 Enforcement 接口
    - 传入 provider, model, capability
    - 获取 allow/reject/degrade 结果
    - Enforcement 不可用时, 跳过 (不阻塞)

  Step 6: 决策
    - 汇总 Step 2-5 结果
    - ALLOW: 所有检查通过
    - REJECT: 任意检查失败
    - DEGRADE: 能力部分支持或 Enforcement 建议降级

  Step 7: Event 写入 (异步)
    - 构造 tool-call-event JSON
    - 写入 memory/events/system/tool-call/{date}.md
    - fire-and-forget, 不等待写入结果
```

### 2.4 Phase 6 → Bypass Detection

```yaml
绕过检测在 tool call 执行完成后进行:

  BypassDetection.detect():
    输入: LLM response 中的所有 tool_calls + Gateway events 列表

    对比:
      LLM response 中的 tool_calls[]
      vs
      Gateway events 中的 requestId + toolName

    不一致:
      1. tool_calls[].length > events.length
         → 部分 tool call 未经过 Gateway
         → bypass_type: "gateway_missing_event" (B4)

      2. tool_calls[].name not in events[].toolName
         → tool call 未经过 Gateway (完全绕过)
         → bypass_type: "gateway_bypassed" (B1/B2)

      3. events[] 有但 tool_calls[] 没有
         → event 孤立, 无影响

    报告:
      bypass_event 写入 event 文件
      bypass_detection_mode 决定行为: log | warn | alert
```

---

## 3. Allow / Reject / Degrade 流程

### 3.1 Allow 流程

```
LLM: tool_call { name: "web_search", args: { query: "news" } }
    │
    v
Gateway.intercept():
    │
    ├── schema validate:            ✅ [toolName OK, toolArgs OK]
    ├── registry lookup:            ✅ [web_search → builtin]
    ├── capability check:           ✅ [io.web_search → supported]
    ├── enforcement:                 ✅ [tool_calls → allow]
    │
    v
decision: allow
    │
    ├── event write (async)
    │     └── tool_call.gateway, allow, web_search, builtin
    │
    v
Policy layer:                       ✅ [allowlist OK]
    │
    v
tool.execute("web_search", args)   [执行]
    │
    v
Result → LLM

副作用:
  - tool 执行正常
  - event 写入
  - LLM 收到结果
```

### 3.2 Reject 流程

```
LLM: tool_call { name: "execute_script", args: { script: "..." } }
    │
    v
Gateway.intercept():
    │
    ├── schema validate:            ✅ [toolName OK, toolArgs OK]
    ├── registry lookup:            ❌ [execute_script 未注册]
    │
    v
decision: reject
    │
    ├── reasonCode: "unregistered_tool"
    ├── reasonMessage: "工具未注册, 无法执行"
    ├── checksFailed: ["registered"]
    │
    ├── event write (async)
    │     └── tool_call.gateway, reject, execute_script, null, unregistered_tool
    │
    v
返回 reject 结果到 LLM:
  tool_result {
    toolCallId: "...",
    content: "工具未注册, 无法执行",
    isError: true
  }

副作用:
  - tool 未执行
  - event 写入
  - LLM 收到错误
  - LLM 可选择: 重试其他工具 / 结束
```

### 3.3 Degrade 流程

```
LLM: tool_call { name: "web_search", args: { query: "image", mode: "image" } }
    │
    v
Gateway.intercept():
    │
    ├── schema validate:            ✅
    ├── registry lookup:            ✅ [web_search → builtin]
    ├── capability check:           ⚠️ [io.web_search 不支持图像搜索]
    │
    v
decision: degrade
    │
    ├── degradation.fallbackTool:   "image_search"
    ├── degradation.fallbackProvider: "deepseek"
    ├── degradation.reason:         "web_search 不支持图像搜索, 建议使用 image_search"
    ├── reasonCode:                 "degradation_advisory"
    ├── checksFailed:               ["capabilitySupported"]
    │
    ├── event write (async)
    │     └── tool_call.gateway, degrade, web_search, builtin
    │
    v
返回 degrade 结果到 LLM:
  tool_result {
    toolCallId: "...",
    content: "web_search 不支持图像搜索, 建议使用 image_search",
    isError: false,
    data: { degradation: { fallbackTool: "image_search" } }
  }

LLM: 使用 image_search 工具 (新的 tool_call)
    │
    v
Gateway.intercept():
    ├── registry lookup:            ✅ [image_search → builtin]
    ├── capability check:           ✅ [io.image_search → supported]
    ├── decision: allow
    │
    v
tool.execute("image_search", args) [执行]

副作用:
  - 原 tool 降级/未执行
  - 新 tool 触发重新经过 Gateway
  - event 两条 (degrade + allow)
```

---

## 4. Event 写入时机

### 4.1 写入点

```yaml
写入时机: Gateway.intercept() 决策完成后, 返回 decision 之前

写入模式: fire-and-forget (异步)
  - Gateway 调用 eventWriter.record(event)
  - eventWriter 立即返回
  - eventWriter 在后台异步写入文件
  - 写入失败不影响 Gateway 决策返回

确保写入的优先级:
  1. event 写入不阻塞 decision 返回 ← 核心保证
  2. event 写入不阻塞 tool 执行
  3. event 写入不导致 LLM 主路径异常
```

### 4.2 Event Writer 设计

```yaml
interface ToolCallEventWriter {
  record(event: ToolCallEvent): void;    // fire-and-forget
  flush(): Promise<void>;                // 强制刷写 (可选)
}

实现:
  - 写入: memory/events/system/tool-call/{date}.md
  - 格式: 每行一个 JSON
  - 异步: setTimeout(0) 或 microtask
  - 错误处理: logWarn, 不抛出

写入内容 (来自 tool-call-event.schema.json):
  - eventKind: "tool_call.gateway"
  - version: 1
  - requestId, timestamp, toolName, pluginId
  - capability
  - gatewayDecision: { decision, reasonCode, checksFailed }
  - enforcement (如果有)
  - paramSummary: { argCount, totalChars }
  - errors (如果有)
```

### 4.3 写入示例

```
memory/events/system/tool-call/2026-07-19.md:

{"eventKind":"tool_call.gateway","version":1,"requestId":"req-abc-001","timestamp":"2026-07-19T09:45:00+08:00","toolName":"web_search","pluginId":"builtin","capability":"io.web_search","gatewayDecision":{"decision":"allow"},"paramSummary":{"argCount":1,"totalChars":12,"keyNames":["query"]}}

{"eventKind":"tool_call.gateway","version":1,"requestId":"req-abc-002","timestamp":"2026-07-19T09:45:01+08:00","toolName":"memory_search","pluginId":"builtin","capability":"memory.read","gatewayDecision":{"decision":"allow"},"paramSummary":{"argCount":1,"totalChars":10,"keyNames":["text"]}}

{"eventKind":"tool_call.gateway","version":1,"requestId":"req-abc-003","timestamp":"2026-07-19T09:45:02+08:00","toolName":"execute_script","pluginId":null,"capability":"","gatewayDecision":{"decision":"reject","reasonCode":"unregistered_tool","checksFailed":["registered"]},"paramSummary":{"argCount":0,"totalChars":0}}
```

---

## 5. Failure Handling

### 5.1 Gateway 不可用

```yaml
场景: Gateway 服务故障 (配置错误 / 文件损坏 / 依赖缺失)

行为 (由 config.toolCallGateway.allowOnFailure 决定):
  allowOnFailure = true (默认):
    跳过 Gateway
    logWarn("ToolCallGateway unavailable, skipping")
    tool call 走现有路径 (无治理降级)
    LLM 主路径不受影响 ← 核心保证

  allowOnFailure = false:
    tool call 被拒绝
    logWarn("ToolCallGateway unavailable, rejecting all tool calls")
    所有 tool call 返回 reject

设计选择: allowOnFailure = true 作为默认
  原因: 与 Phase 6.3 §6 保持一致
  Gateway 是治理层, 不可用时不应阻塞 LLM 主路径
```

### 5.2 Schema 校验失败

```yaml
场景: LLM 发出的 tool call 不符合 tool-call-request schema

行为:
  Gateway 生成 reject 决策
  reasonCode: "invalid_tool_name" / "invalid_tool_args" / "missing_request_id"
  尝试记录 event (即使 schema 校验失败, event 应尽可能写入)
  event 写入失败不算 Gateway 失败

示例:
  toolName = "" (空字符串) → reject, "invalid_tool_name"
  toolArgs = null → reject, "invalid_tool_args"
```

### 5.3 Registry 查询失败

```yaml
场景: Plugin Registry / Capability Registry 不可用

行为:
  保守策略: reject (不能确认工具是否注册 / 能力是否支持)
  reasonCode: "unregistered_tool" (最严格的决策)
  event 记录: errors["registry_lookup_failed"]

备选: 如果 allowOnFailure=true 且 registry 失败:
  跳过 Gateway 能力校验
  降级到现有 Policy 层 (allowlist/denylist)
  logWarn("Registry unavailable, degrading to policy-only")
  此备选仅当 registry 完全不可用时
```

### 5.4 Event 写入失败

```yaml
场景: 文件写入异常 (磁盘满 / 权限 / 路径不存在)

行为:
  logWarn("ToolCallEvent write failed")
  不影响 decision 返回
  不影响 tool 执行
  不影响 LLM 主路径

恢复:
  下次 Healthy Event Write 成功时自动恢复
  无重试机制 (fire-and-forget 设计)
```

### 5.5 失败矩阵

```yaml
失败点                    | 影响                    | 主路径     | 恢复
────────────────────────┼─────────────────────────┼──────────┼────────
Gateway service         | 跳过 Gateway, 直接执行    | 不受影响  | 配置修复
Schema 校验失败         | 拒绝 tool call            | 不受影响  | LLM 重试
Registry 查询失败       | 保守拒绝                  | 不受影响  | Registry 修复
Event 写入失败          | 丢失 event 记录           | 不受影响  | 自动恢复
Enforcement 不可用      | 跳过 enforcement 检查     | 不受影响  | 服务恢复
Bypass 检测            | 日志记录, 不影响执行       | 不受影响  | 手动处理
```

---

## 6. Bypass Detection Path

### 6.1 检测点

```yaml
检测时机: tool call 执行完成后, 下一轮 LLM 调用之前

检测执行体: BypassDetector (独立模块, 不依赖 Gateway)

调用方: attempt.ts (在 Phase 5: Result Processing 完成后)

输入:
  LLM Response (tool_calls[] 完整列表)
  Gateway events (同一 request 的 events)

输出:
  BypassReport (如有绕过)
```

### 6.2 BypassDetector 接口

```yaml
interface BypassDetector {
  detect(params: BypassDetectionParams): BypassReport;
}

interface BypassDetectionParams {
  requestId: string;
  llmToolCalls: ToolCallRef[];     // LLM response 中的 tool_calls
  gatewayEvents: ToolCallEvent[];  // Gateway 记录的 events
}

interface ToolCallRef {
  name: string;
  id: string;
  index: number;
}

interface BypassReport {
  detected: boolean;
  bypasses: BypassEntry[];
}

interface BypassEntry {
  bypassType: "gateway_bypassed" | "gateway_missing_event";
  toolName: string;
  toolCallId: string;
  index: number;
  severity: "info" | "warn" | "alert";
}
```

### 6.3 检测逻辑

```
detect():
  [1] 收集 LLM tool_calls 列表
  [2] 收集 Gateway events 列表 (按 requestId 过滤)

  [3] 遍历 LLM tool_calls:
      for each toolCall in llmToolCalls:
        event = gatewayEvents.find(
          e => e.toolName === toolCall.name
        )
        if not event:
          bypassReport.add({
            bypassType: "gateway_bypassed",
            toolName: toolCall.name,
            toolCallId: toolCall.id,
            severity: "alert"
          })

  [4] 对比数量:
      if llmToolCalls.length > gatewayEvents.length:
        bypassReport.add({
          bypassType: "gateway_missing_event",
          severity: "warn"
        })

  [5] 严重级别:
      "gateway_bypassed":     ALERT (严重违反治理)
      "gateway_missing_event": WARN  (event 丢失, 设计容忍)

  [6] 输出 BypassReport
```

### 6.4 绕过处理

```yaml
绕过处理行为 (由 config.toolCallGateway.bypassDetectionMode 决定):

  mode = "log":
    记录日志
    不通知
    不中断

  mode = "warn":
    记录日志
    logWarn 输出到 logger
    写入 bypass event

  mode = "alert":
    记录日志
    logWarn
    写入 bypass event
    触发 Governance Alert (Phase 7 范围: 通知 / 诊断)
```

---

## 7. 集成架构总览

### 7.1 文件层次

```
Tool Call Gateway Layer (新增)
├── ToolCallGateway                 ← 核心 intercept 逻辑
│   ├── intercept()
│   └── recordEvent()
├── ToolCallEventWriter             ← event 写入 (异步)
│   ├── record()
│   └── flush()
├── BypassDetector                  ← 绕过检测
│   └── detect()
└── GatewayConfig                   ← 配置
    ├── enabled
    ├── enforcementCheck
    ├── eventWriteEnabled
    ├── bypassDetectionEnabled
    └── allowOnFailure

现有系统 (不受影响)
├── Plugin Registry                 ← tool name 解析
│   └── resolvePluginTools()
├── Capability Registry             ← 能力查询
│   └── provider-capability-registry.json
├── Enforcement (Phase 6.2.3)       ← 能力决策
├── Policy Layer                    ← allowlist/denylist
├── Tool Adapter                    ← 工具执行
└── Event Store                     ← memory/events/system/tool-call/
```

### 7.2 配置实例

```yaml
# OpenClaw Config
agents:
  main:
    toolCallGateway:
      enabled: false                      # 默认关闭
      enforcementCheck: false
      eventWriteEnabled: true
      eventPath: "memory/events/system/tool-call/"
      bypassDetectionEnabled: false
      bypassDetectionMode: "log"
      allowOnFailure: true
      schemaVersion: 1
```

### 7.3 与现有文件的映射

```yaml
Config / Code Name            | Design Document              | Schema
────────────────────────────┼────────────────────────────┼────────────────────
ToolCallGateway.intercept()  | §1-3                        | tool-call-request.schema.json
ToolCallGateway.decision()   | §3                          | gateway-decision.schema.json
ToolCallEventWriter          | §4                          | tool-call-event.schema.json
BypassDetector.detect()      | §6                          | (no schema, 纯逻辑)
```

---

## 8. 不变量与边界验证

### 8.1 不变量映射

```
原有 Contract 不变量 (Phase 6.4):
  G-001:  所有 LLM tool call → Gateway     ✅ (intercept point 在执行前)
  G-002:  Gateway 不执行工具                 ✅ (只调用 decision → 返回)
  G-003:  Gateway 不修改参数                 ✅ (只校验, 不修改)
  G-004:  Gateway 不缓存结果                 ✅ (无缓存层)
  G-005:  Gateway 不注册能力                 ✅ (依赖 Registry)
  G-006:  Event 记录                         ✅ (异步 fire-and-forget)
  G-007:  未注册 reject                      ✅ (Step 3)
  G-008:  能力不匹配 reject/degrade           ✅ (Step 4)
  G-009:  绕过检测                            ✅ (BypassDetector)
  G-010:  拒绝不影响 LLM                     ✅ (返回结果, 不抛异常)
  G-011:  不依赖 Provider allow/deny          ✅ (Gateway 在 Policy 之前)
  G-012:  不替换 Plugin allowlist/denylist    ✅ (Policy 层后执行)

新增 Integration 不变量:
  I-001:  可开关 (disabled=不执行)             ✅ (config.enabled)
  I-002:  失败不阻塞主路径                     ✅ (allowOnFailure=true)
  I-003:  Event 异步不阻塞                     ✅ (fire-and-forget)
  I-004:  绕过检测不影响执行                   ✅ (only log)
  I-005:  配置变更不影响现有 Policy             ✅ (Policy 层不变)
```

### 8.2 边界条件

```yaml
B1: Gateway disabled
  config.enabled = false
  → Gateway 跳过, tool call 走现有路径

B2: Gateway enabled + empty tool list
  LLM 未产生 tool_calls
  → Gateway 无操作, 跳过

B3: Gateway enabled + reject all
  config.allowOnFailure = false
  且 Gateway 不可用
  → 所有 tool call 被拒绝

B4: Gateway enabled + partial reject
  多个 tool_calls, 部分注册/部分未注册
  → 每个 tool call 独立决策
  → 已注册的 allow, 未注册的 reject

B5: Enforcement unavailable
  config.enforcementCheck = true
  但 Enforcement 服务不可用
  → 跳过 enforcement, 继续检查链
  → event 记录: errors["enforcement_unavailable"]

B6: Concurrent tool calls
  多个并行执行的 tool call
  → 每个 tool call 独立通过 Gateway
  → event 独立记录
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-complete | 2026-07-19 | Phase 6.4.2 Runtime Integration Design, 8 章节 |
