# Tool Call Gateway Contract v1.0 — FINAL

```yaml
contract:
  name: TOOL-CALL-GATEWAY
  version: v1.0
  level: L1
  parent: FREEZE-CONTRACT
  scope: system-wide tool call flow
  owner: 燃🔥
  status: active
```

**Phase 6.4**
**Status:** FINAL
**Date:** 2026-07-19
**Dependencies:**
- PLUGIN-CAPABILITY-CONTRACT.md v1.0 (Phase 3.2 FINAL)
- CAPABILITY-REGISTRY.md v1.0 (Phase 3.3)
- PROVIDER-CAPABILITY-CONTRACT.md v1.0 FINAL (Phase 6.2.1)
- CONTEXT-PROJECTION-CONTRACT.md v1.0 FINAL (Phase 6.3 FINAL)
- REASONING-ISOLATION-CONTRACT.md v1.0 FINAL (Phase 6.1 FINAL)

---

## §0 定位

### Tool Call Gateway 是什么

```yaml
Tool Call Gateway:
  定义: LLM 发出的 tool call 进入 Runtime 前的统一拦截层

角色定位:
  非执行层 — 不执行工具逻辑
  非能力注册层 — 不声明工具能力
  拦截层 — 检查、记录、放行或拒绝

与 Enforcement 分工:
  Tool Call Gateway: 检查 LLM 请求的工具是否能调用 (request governance)
  Capability Enforcement: 检查 Provider 的能力是否可用 (capability decision)
  前者面向工具入口, 后者面向 Provider 能力
  两者是检查链的前后段, 不是替代关系
```

### Gateway 不做什么

```yaml
❌ 执行工具逻辑
❌ 注册工具能力
❌ 修改工具参数
❌ 缓存工具结果
❌ 提供工具发现
❌ 替代 Plugin 的 allowlist/denylist
```

### 为什么需要 Gateway

```yaml
Phase 6.3 验证揭示的缺口:
  插件可直接调用 LLM API, 绕过 Context Projection
  工具调用没有统一的拦截点
  Tool call 缺少标准 event 记录
  不存在绕过检测

Phase 6.4 补全:
  LLM → Gateway → Enforcement → Plugin → Execution → Event
  所有 LLM 发起的 tool call 必须经过 Gateway
  Gateway 记录每个 tool call 的 event
  Gateway 检测并拒绝绕过路径
```

---

## §1 核心架构

### 1.1 请求链路

```
LLM Response
    │
    ├── content (直接返回用户)
    └── tool_calls[]
            │
            v
    [Tool Call Gateway]          ← §2 统一入口
            │
            ├── validate tool name against Registry §2.7
            ├── check capability match §2.8
            │
            v
    [Capability Enforcement]     ← Phase 6.2.3
            │
            ├── check provider capability §2.9
            │
            v
    [Plugin / Tool Adapter]      ← 现有 tool.execute()
            │
            ├── resolve plugin tool
            ├── execute
            │
            v
    [Execution Event]            ← §4 Tool Call Event
            │
            v
    Result back to LLM
```

### 1.2 职责边界

```yaml
Layer               | 角色                                  | 现有/新增
────────────────────┼───────────────────────────────────────┼──────────
LLM                 | 发出 tool call                       | 现有
Tool Call Gateway   | 拦截、校验、记录 event                | 新增 §2
Capability Enforcement | Provider 能力决策                  | Phase 6.2.3
Plugin Registry     | 工具注册 + allowlist/denylist          | 现有
Tool Adapter        | 执行工具                              | 现有
Event Store         | 记录 tool call event                  | 新增 §4

Gateway 职责:
  - 接收 LLM 发出的 tool call
  - 查询 Registry 验证工具是否注册
  - 查询 Capability Registry 验证能力是否匹配
  - 记录 tool_call event
  - 拒绝不可用的 tool call
  - 检测绕过路径

Gateway 非职责:
  - 执行工具 (Tool Adapter 负责)
  - 注册工具 (Plugin Registry 负责)
  - 缓存工具 (Runtime 负责)
  - 修改参数 (Tool Adapter 负责)
```

### 1.3 不变量

```
G-001: 所有 LLM 发出的 tool call 必须经过 Gateway
G-002: Gateway 不执行工具
G-003: Gateway 不修改工具参数
G-004: Gateway 不缓存工具结果
G-005: Gateway 不注册工具能力
G-006: Gateway 记录每个 tool call 的 event
G-007: Gateway 拒绝未注册的 tool
G-008: Gateway 拒绝能力不匹配的 tool
G-009: Gateway 检测并标记绕过路径
G-010: Gateway 的拒绝不影响 LLM 主路径 (与 Phase 6.3 §6 一致)
G-011: Gateway 不依赖 Provider 的 allow/deny (Provider 决策归 Enforcement)
G-012: Gateway 不替换 Plugin 的 allowlist/denylist (两者叠加)
```

---

## §2 Gateway 接口

### 2.1 接口定义

```typescript
interface ToolCallGateway {
  /** 拦截并处理 LLM 发出的 tool call */
  intercept(params: ToolCallInterceptParams): Promise<ToolCallInterceptResult>;

  /** 记录 tool call event (异步, 不阻塞) */
  recordEvent(event: ToolCallEvent): void;

  /** 检测绕过 (对比 LLM response 中的 tool call 与 Gateway 拦截记录) */
  detectBypass(params: BypassDetectionParams): BypassReport;
}

interface ToolCallInterceptParams {
  requestId: string;
  toolName: string;
  toolArgs: unknown;
  pluginId?: string;         // plugin 解析后得知
  providerId?: string;       // 当前使用 provider
  modelId?: string;          // 当前使用 model
  sessionKey?: string;       // session 标识
}

interface ToolCallInterceptResult {
  /** 决策: allow | reject | degrade */
  decision: "allow" | "reject" | "degrade";
  /** 拒绝原因 (仅 reject/degrade 时) */
  reason?: string;
  /** degradation 建议 (仅 degrade 时) */
  degradation?: {
    fallbackTool?: string;
    fallbackProvider?: string;
  };
  /** 经过 Gateway 标记 */
  gatewayProcessed: true;
}
```

### 2.2 拦截流程

```
intercept() 内部:

[1] 校验 tool name 是否在 Plugin Registry 中注册
    ├── 不注册 → reject("unregistered_tool")
    └── 已注册 → continue

[2] 校验 tool 对应的 capability
    ├── 从 CAPABILITY-REGISTRY.md 查询 tool -> capability 映射
    ├── 从 provider-capability-registry.json 查询 capability 是否支持
    ├── 不支持 → reject("capability_not_supported")
    └── 支持 → continue

[3] 查询 Plugin allowlist/denylist
    ├── 插件列表允许
    ├── 工具名允许
    ├── 被 deny → reject("denied_by_policy")
    └── allow → continue

[4] 查询 Capability Enforcement (Phase 6.2.3)
    ├── 不可用 → reject("enforcement_rejected")
    ├── degrade → 建议降级
    └── allow → 放行

[5] 记录 event (异步)
    ├── decision
    ├── tool_name
    ├── plugin_id
    └── reason (如有)
```

### 2.3 拒绝 vs 降级

```yaml
reject:
  定义: tool call 被拒绝, LLM 收到拒绝信息
  触发条件:
    - 工具未注册
    - 能力不支持
    - 策略拒绝
    - Enforcement 不可用

degrade:
  定义: tool call 被允许, 但使用降级路径
  触发条件:
    - 请求的能力在指定 Provider 上不可用, 但在另一个 Provider 上可用
    - 工具需要不同级别的能力

  示例:
    LLM 请求 tool_calls → Provider A 不支持 → degrade to Provider B
    LLM 请求 streaming → Provider A 不支持 → degrade to non-streaming
```

### 2.4 放行条件

```yaml
ALLOW 条件 (同时满足):
  [1] tool 在 Plugin Registry 中注册
  [2] tool 对应的 capability 在 provider-capability-registry 中声明
  [3] Plugin allowlist 允许该 tool
  [4] Capability Enforcement 放行
  [5] Gateway 记录 event (异步不阻塞)

任一不符合 → reject
```

### 2.5 event 格式

```yaml
tool_call_event:
  version: 1
  event_kind: "tool_call.gateway"
  request_id: "(string)"
  timestamp: "(ISO 8601)"
  tool_name: "(string)"
  plugin_id: "(string)"
  decision: "allow" | "reject" | "degrade"
  reason: "(string | null)"
  enforcement_check: "(object | null)"
  gateway_version: 1
```

### 2.6 与现有 Policy 的关系

```yaml
现有 policy (Phase 3):
  tool_allowlist / tool_denylist
  plugin allow/deny
  policy 由 Config 和 Session 层决定

Gateway:
  不替换现有 policy
  Gateway 校验注册能力 + 能力匹配
  Gateway 与 policy 叠加:
    Policy deny → 不注册该 tool → Gateway reject
    Gateway allow + Policy deny → Gateway 不覆盖 (policy 最后拦截)

协调:
  Gateway 在前段: 检查注册 + 能力
  Policy 在后段: 检查权限
  两者独立运行, 各司其职
```

---

## §3 绕过路径定义

### 3.1 绕过类型

```yaml
B1: 插件直接调用 LLM API
  描述: 插件通过 provider API 绕过 Gateway
  现有: 存在 (Phase 6.3 Validation 发现)
  检测: Gateway 无法拦截 (插件不走 Gateway)
  治理: Phase 6.4 标记 + Phase 7 处理

B2: Worker 直接调用 LLM API
  描述: 外部 worker 绕过 Gateway
  现有: 存在 (lottery worker)
  检测: Gateway 无法拦截
  治理: 外部 worker 统一接入 Gateway

B3: 插件直接修改 tool 参数后调用
  描述: 插件在 Gateway 之后修改参数
  现有: 不处理
  检测: 基于 event 和 tool execution log 对比

B4: LLM 生成 tool call 但 Gateway 未记录
  描述: Gateway 缺失 event
  现有: 不处理
  检测: 对比 LLM response 中的 tool_calls 与 Gateway events

B5: 工具绕过 allowlist/denylist
  描述: 工具在 Gateway 之后被调用但 Denylist 拒绝
  现有: Policy 层在 Gateway 之后
  检测: 基于 log 分析
```

### 3.2 绕过检测

```yaml
绕过检测不阻止绕过, 只检测绕过:
  原因: 某些绕过是运行时的正常路径 (worker)
        检测绕过是指出绕过路径, 不是阻止

绕过级别:
  B1: ALERT  (严重违反)
  B2: WARN   (已知缺口)
  B3: WARN   (需要 Runtime 安全)
  B4: INFO   (event 丢失是设计容忍, 参见 Phase 6.3 §6)
  B5: INFO   (policy 层最后拦截)
```

### 3.3 禁止路径

```yaml
禁止:
  LLM → Provider API (不经过 Gateway)
  LLM → Plugin API (不经过 Gateway)
  LLM → tool.execute() (不经过 Gateway)
  Provider → tool.execute() (不经过 Gateway)

允许:
  LLM → Gateway → tool.execute() (标准路径)
  Gateway → Enforcement → tool.execute() (标准路径)
  Plugin → tool.execute() (插件内部的工具调用, 不是 LLM 发起的)
```

---

## §4 Tool Call Event

### 4.1 Event 格式

```yaml
版本: 1
位置: memory/events/system/tool-call/{date}.md

格式:
  - event_kind: tool_call.gateway
    request_id: "req-xxx"
    tool_name: "web_search"
    plugin_id: "builtin"
    capability: "io.web_search"
    decision: "allow"
    enforcement_check:
      provider: deepseek
      model: deepseek-v4-flash
      capabilities_requested: [tool_calls]
      capabilities_result: allow
    params_summary:  # 仅 metadata, 不含完整参数
      arg_count: 3
      chars: 128
    errors: []

  - event_kind: tool_call.gateway
    request_id: "req-yyy"
    tool_name: "web_search"
    plugin_id: "builtin"
    capability: "io.web_search"
    decision: "reject"
    reason: "unregistered_tool"
    params_summary: null
    errors: ["tool not found in plugin registry"]
```

### 4.2 Event 字段

```yaml
字段             | 必须 | 类型       | 说明
─────────────────┼──────┼────────────┼──────────────────────
event_kind       | 是   | string     | 固定 "tool_call.gateway"
request_id       | 是   | string     | 关联请求
tool_name        | 是   | string     | 工具名
plugin_id        | 是   | string     | 插件 ID
capability       | 是   | string     | Phase 3 能力名
decision         | 是   | string     | allow | reject | degrade
reason           | 否   | string     | 拒绝/降级原因
enforcement_check| 否   | object     | Phase 6.2.3 结果
params_summary   | 否   | object     | arg_count + chars
errors           | 否   | string[]   | 异常列表
```

### 4.3 Event 不包含

```yaml
Event 不包含:
  - tool 参数完整内容 (仅 param_summary: count + chars)
  - tool 执行结果
  - LLM 输入/输出内容
  - Session 私密信息

原因: 与 Phase 6.3 Event 一致原则
  Event 记录说明性元数据, 不是数据副本
  完整参数和执行结果在独立的 execution log 中
```

---

## §5 与现有系统的集成

### 5.1 Plugin Registry

```yaml
集成点: getPluginToolMeta()
  现有: 返回 { pluginId, optional }
  补充: Gateway 通过 pluginId 查询 Capability Registry

集成点: resolvePluginTools()
  现有: 返回 AnyAgentTool[] (包含 execute 方法)
  补充: Gateway 在 execute 之前校验

集成点: tool name 校验
  现有: 插件注册时验证名称冲突
  补充: Gateway 验证工具名是否在注册表中
```

### 5.2 Capability Registry (Phase 3.3)

```yaml
现有映射:
  runtime.tool.register  → 工具注册
  runtime.hook.subscribe → 生命周期
  io.web_fetch           → 网页抓取
  io.web_search          → 搜索
  memory.read            → 记忆查询
  ...

Gateway 需要:
  tool_name → capability 映射表
  每个注册的工具关联一个 capability

新增映射:
  每条工具注册时附带 capability tag
  例如: web_search → io.web_search
  允许: 一个工具对应多个 capability
```

### 5.3 Context Projection (Phase 6.3)

```yaml
集成点: tool_result projection
  Phase 6.3 §3.1 E: 工具调用结果
  Gateway 记录 event 后, Context Projection 在结果返回时捕获

集成点: projection_event 关联
  tool_call_event 的 request_id 与 projection_event 的 request_id 一致
  可关联: 哪个请求 → 哪些投影 → 哪些工具调用

不重叠:
  Context Projection: LLM 输入侧治理
  Tool Call Gateway: LLM 输出侧治理
  各自独立, 通过 request_id 关联
```

### 5.4 Capability Enforcement (Phase 6.2.3)

```yaml
分工:
  Gateway: tool call的入口治理 (是否可调用)
  Enforcement: provider能力的执行决策 (是否支持该能力)
  两者是查询链: Gateway → Enforcement

Gateway 查询 Enforcement 用于告知:
  该 tool 对应的 capability 在目标 provider 上是否可用
  如果不可用 → degrade 或 reject

不重叠:
  Gateway 不自己做能力决定
  Enforcement 不拦截 tool call
```

---

## §6 数据流

### 6.1 正常路径

```
User: "搜索今天的新闻"

Runtime:
  LLM: tool_call { name: "web_search", args: { query: "today news" } }

Gateway.intercept():
  [1] tool name check: web_search → 已注册 (builtin)       ✅
  [2] capability check: io.web_search → deepseek supports   ✅
  [3] allowlist check: web_search → allowed                  ✅
  [4] enforcement check: tool_calls → allow                  ✅
  [5] decision: allow                                        ✅
  [6] record event: tool_call.gateway / allow                ✅

Plugin.execute("web_search", args): 执行

Result → LLM → User

Event 记录:
  event_kind: tool_call.gateway
  tool_name: web_search
  plugin_id: builtin
  decision: allow
  capability: io.web_search
  enforcement_check: { provider: deepseek, result: allow }
```

### 6.2 拒绝路径

```
User: "执行自定义脚本"

Runtime:
  LLM: tool_call { name: "execute_script", args: { script: "..." } }

Gateway.intercept():
  [1] tool name check: execute_script → 未注册                ❌
  [2] capability check: 跳过                                   ❌
  [3] decision: reject                                        ❌
  [4] record event: tool_call.gateway / reject                ✅

Result: LLM 收到拒绝信息 → User "该工具不可用"

Event 记录:
  event_kind: tool_call.gateway
  tool_name: execute_script
  plugin_id: null
  decision: reject
  reason: "unregistered_tool"
```

### 6.3 Degrade 路径

```
User: "搜索图片"

Runtime:
  LLM: tool_call { name: "web_search", args: { query: "images" } }

Gateway.intercept():
  [1] tool name check: web_search → 已注册                    ✅
  [2] capability check: io.web_search → 不支持图像             ⚠️
  [3] decision: degrade
  [4] degradation: { fallbackTool: "image_search" }            ✅
  [5] record event: tool_call.gateway / degrade               ✅

Result: LLM 收到 degrade 信息 → 使用 image_search 工具

Event 记录:
  event_kind: tool_call.gateway
  tool_name: web_search
  plugin_id: builtin
  decision: degrade
  reason: "capability_io_web_search不支持图像"
  degradation: { fallbackTool: "image_search" }
```

### 6.4 绕过检测

```
Runtime:
  LLM response: tool_call { name: "web_search" }
  但 Gateway 未记录该调用

BypassDetection:
  [1] 解析 LLM response 中的 tool_calls[]
  [2] 查询 Gateway events 中该 request_id 的记录
  [3] 未找到 → 绕过标记
  [4] 记录 bypass event

Event 记录:
  event_kind: tool_call.bypass
  request_id: "req-xxx"
  tool_name: "web_search"
  bypass_type: B4 (Gateway missing event)
```

---

## §7 集成验证

### 7.1 验证场景

```yaml
V1: 正常路径
  输入: 已注册工具 + 能力匹配 + allowlist 允许
  预期: decision: allow, event 记录
  验证: event.decision == "allow"

V2: 未注册工具
  输入: 未注册工具
  预期: decision: reject, event 记录
  验证: event.decision == "reject", event.reason == "unregistered_tool"

V3: 能力不匹配
  输入: 已注册工具 + 能力不支持
  预期: decision: reject or degrade
  验证: event.decision == "reject" or "degrade"

V4: Denylist 拒绝
  输入: 已注册工具 + 能力匹配 + denylist 拒绝
  预期: decision: reject (policy 层面)
  验证: event.decision == "reject", event.reason == "denied_by_policy"

V5: 绕过检测
  输入: LLM response 中有 tool_calls 但 Gateway 无 event
  预期: 绕过标记
  验证: bypass event 记录

V6: 能力降级
  输入: 已注册工具 + 能力部分支持
  预期: decision: degrade, fallback 建议
  验证: event.decision == "degrade", event.degradation.fallbackTool 非空
```

### 7.2 不变量验证

```yaml
G-001: LLM tool call → Gateway: ✅ 标准路径
G-002: Gateway 不执行: ✅ 职责分离
G-003: Gateway 不修改参数: ✅ intercept() 只检查
G-004: Gateway 不缓存: ✅ 无缓存层
G-005: Gateway 不注册能力: ✅ 依赖 Registry
G-006: Event 记录: ✅ 异步
G-007: 未注册 reject: ✅
G-008: 能力不匹配 reject/degrade: ✅
G-009: 绕过检测: ✅ (不阻止, 只记录)
G-010: 拒绝不影响 LLM: ✅ (与 Phase 6.3 一致)
G-011: 不依赖 Provider: ✅ Gateway 在 Enforcement 之前
G-012: 不替换 Policy: ✅ 两者叠加
```

---

## §8 已知局限

```yaml
L1: 插件直接调用 LLM API
  描述: 插件不走 Gateway
  影响: Gateway 无法拦截此路径的 tool call
  定位: 治理层无法覆盖 (需 Runtime 安全层)

L2: 外部 Worker 绕过
  描述: 外部 worker 不通过 LLM → Gateway 路径
  影响: worker 调用的 tool call 不经过 Gateway
  定位: Phase 6.4 治理层范围外

L3: Gateway 不可用 → 降级
  描述: Gateway 服务不可用时
  影响: tool call 直接跳过 Gateway
  定位: 待设计高可用方案 (Phase 7)

L4: 绕过检测无自动阻止
  描述: 绕过检测只记录, 不阻止
  影响: 后续处理依赖人工/事件驱动
  定位: Phase 6.4 治理范围
```

---

## §9 设计决策

### 9.1 为什么 Gateway 是 Contract 层而不是 Runtime 层

```yaml
原因:
  Phase 6 是治理层设计, 不是实现层
  Gateway 定义了"LLM 输出的 tool call 应该被如何治理"
  实现选择留在 Phase 7 (Runtime Implementation)

决策:
  Phase 6.4 = Gateway Contract
  Phase 7 = Gateway Implementation (可选)
```

### 9.2 为什么 Gateway 不自己做能力决定

```yaml
原因:
  能力决定属于 Phase 6.2 Capability Enforcement
  Gateway 是请求层, 不是能力层
  如果 Gateway 自己决定能力, 则 Enforcement 层失去意义

决策:
  Gateway 查询 Enforcement
  Enforcement 返回 allow/reject/degrade
  Gateway 执行结果
```

### 9.3 为什么 Gateway 不替换现有 allowlist/denylist

```yaml
原因:
  现有 allowlist/denylist 是 Plugin 层面的访问控制
  Gateway 是 tool call 层面的入口治理
  两者解决的问题不同:
    Policy: 哪些用户/会话可以调用哪些工具
    Gateway: 哪些 LLM 请求的工具可以执行

决策:
  Gateway + Policy 叠加, 不替换
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-draft | 2026-07-19 | Phase 6.4 Tool Call Gateway Contract DRAFT, 9 章节 |
