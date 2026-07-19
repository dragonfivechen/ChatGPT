# Bypass Register v1.0

**Phase 7.3 — Bypass Closure**
**Date:** 2026-07-19
**前置条件:**
- Phase 7.1 Audit Contract 🔒 FROZEN
- Phase 7.2 Boundary Enforcement Matrix 🔒 FROZEN (B1-B5 verified)
- Phase 6.1-6.4 🔒 FROZEN

---

## §0 定位

Bypass Register 是 Phase 7 从 "发现" 进入 "分类" 的桥梁。

```
Phase 7.1: 定义验证契约          → 🔒 FROZEN
Phase 7.2: 验证边界存在性        → 🔒 FROZEN (5/5 COMPLETE)
                             ↓
Phase 7.3: 分类所有绕过路径      → CURRENT
   输出: BYPASS REGISTER v1.0
                             ↓
决策: 哪些关, 哪些留, 哪些排期
```

### 约束

```
  detect        → done (B1-B5)
   ↓
  classify      → current (Bypass Register)
   ↓
  decision      → 等待治理决策 (龙哥)

❌ 不修复
❌ 不解冻 Phase 6
❌ 不实现 Gateway / Projection / Event Truth
❌ 不修改 Phase 6 Contract
```

---

## §1 汇总

| 总量 | B1 | B2 | B3 | B4 | B5 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **15 bypass paths** | 2 | 3 | 3 | 3 | 4 |

---

## §2 B1 — Plugin → Gateway (2 bypass paths)

### B1-BP1: agent-loop.js direct execute

| 字段 | 值 |
|:---|:---|
| **Boundary** | B1 Plugin → Gateway |
| **Bypass ID** | B1-BP1 |
| **Path** | `agent-loop.js:419` executePreparedToolCall → `prepared.tool.execute()` |
| **Impact** | LLM tool call 不经 Gateway.intercept() 直接执行。Phase 6.4 Contract G-001 (Gateway 唯一入口) 失效 |
| **Evidence** | agent-loop.js 源码: prepareToolCall (line 360) → executePreparedToolCall (line 419) → tool.execute(). 0 行 Gateway 代码在两个函数之间 |
| **Classification** | 🟥 **MISSING** — Gateway.intercept() 不在执行路径 |
| **Decision State** | DEFERRED_TO_PHASE (Phase 6.4 Future Revision) |

### B1-BP2: Plugin internal direct execute

| 字段 | 值 |
|:---|:---|
| **Boundary** | B1 Plugin → Gateway |
| **Bypass ID** | B1-BP2 |
| **Path** | `createCachedDescriptorPluginTool` → `resolvePluginToolRegistry` → `entry.factory(ctx)` → `matchedTool.execute()` |
| **Impact** | Plugin 工具不走 agent-loop, 不经 Gateway. Extension Boundary (Phase 1) 允许 Plugin 直接调用 Runtime 核心 API |
| **Evidence** | `src/plugins/tools.ts`: createCachedDescriptorPluginTool 返回的直接执行函数, 不经过 agent-loop |
| **Classification** | ⚠️ **BYPASSABLE** — Plugin SDK 允许 direct execute |
| **Decision State** | ACCEPTED_GAP (Plugin Execution Contract PEC-01) |

---

## §3 B2 — Worker → Policy (3 bypass paths)

### B2-BP1: Cross-agent spawn bypass

| 字段 | 值 |
|:---|:---|
| **Boundary** | B2 Worker → Policy |
| **Bypass ID** | B2-BP1 |
| **Path** | `subagent-spawn.ts` → subagent.SPAWN_TOOLS 绕过 `tool-policy-pipeline.ts` 注册时过滤 |
| **Impact** | Spawned agent 可携带超出 parent policy 允许的工具。Policy Enforcement (Phase 6.2/6.4) 不一致 |
| **Evidence** | `src/agents/subagent-spawn.ts:697`: runEmbeddedAttempt. SPAWN_TOOLS 列表在 policy pipeline 过滤前就已确定 |
| **Classification** | ⚠️ **BYPASSABLE** — spawn 时 policy 未覆盖全部工具集 |
| **Decision State** | REQUIRE_CHANGE (Phase 7.x Boundary Hardening) |

### B2-BP2: Plugin internal direct execute

| 字段 | 值 |
|:---|:---|
| **Boundary** | B2 Worker → Policy |
| **Bypass ID** | B2-BP2 |
| **Path** | Plugin 内部 `matchedTool.execute()` — 不在 agent-loop, 不经 tool-policy-pipeline |
| **Impact** | Plugin 工具不经 Policy 检查直接执行。Runtime Policy 不覆盖全部执行路径 |
| **Evidence** | 同 B1-BP2 路径。Plugin 工具注册后可直接 execute(), 无 policy pipeline |
| **Classification** | ⚠️ **BYPASSABLE** — Plugin 工具不经 policy |
| **Decision State** | ACCEPTED_GAP (Plugin Execution Contract PEC-01) |

### B2-BP3: Registration-time only (temporal gap)

| 字段 | 值 |
|:---|:---|
| **Boundary** | B2 Worker → Policy |
| **Bypass ID** | B2-BP3 |
| **Path** | Registration (T1): `applyToolPolicyPipeline` → `filterToolsByPolicy`. Execution (T2): `tool.execute()` — T1→T2 之间无 policy re-check |
| **Impact** | Policy 变更在 T1→T2 窗口不生效。注册后修改 policy 不影响已注册工具 |
| **Evidence** | `src/agents/tool-policy-pipeline.ts:117`: 注册时过滤. `agent-loop.js:419`: `tool.execute()` 执行时无 policy 检查. 两段之间 0 行 policy 相关代码 |
| **Classification** | ⚠️ **BYPASSABLE** — temporal gap in policy enforcement |
| **Decision State** | DEFERRED |

---

## §4 B3 — Capability → Registry (3 bypass paths)

### B3-BP1: Plugin direct registration to Runtime Resolver

| 字段 | 值 |
|:---|:---|
| **Boundary** | B3 Capability → Registry |
| **Bypass ID** | B3-BP1 |
| **Path** | `resolvePluginCapabilityProviders` → `capabilityProviderRuntime.resolvePluginCapabilityProviders` → 直接注册到 Runtime provider 列表. 不经过 Registry |
| **Impact** | 插件 capability 绕过 Phase 6.2 Contract 的 Registry, 直接进入运行时. Registry 身为"唯一权威来源"的声明不成立 |
| **Evidence** | `src/plugins/capability-provider-runtime.ts`: resolvePluginCapabilityProviders. 注入到 `listRuntimeImageGenerationProviders` 路径. 不经过 `src/media-understanding/provider-capability-registry.ts` |
| **Classification** | 🟥 **MISSING** — Registry 不在 Runtime Resolver 路径 |
| **Decision State** | DEFERRED_TO_PHASE (Phase 6.2 Future Revision) |

### B3-BP2: Creation-time check ≠ Execution-time guarantee

| 字段 | 值 |
|:---|:---|
| **Boundary** | B3 Capability → Registry |
| **Bypass ID** | B3-BP2 |
| **Path** | 创建时 (T1): `hasGenerationToolAvailability` → manifest 检查. 执行时 (T2): Runtime Resolver → Provider 调用. T1 的注册 ≠ T2 的执行可用 |
| **Impact** | 工具创建时认为 capability 可用（通过 Manifest 声明）, 执行时可能实际不可用（auth 过期, provider 不可达）。Registry 只参与创建时检查 |
| **Evidence** | `src/agents/tools/image-generate-tool.ts`: createImageGenerateTool → hasGenerationToolAvailability. 执行时: `resolveCapabilityModelConfigForTool` → `listRuntimeImageGenerationProviders` |
| **Classification** | ⚠️ **BYPASSABLE** — temporal gap between registration check and execution |
| **Decision State** | ACCEPTED_GAP |

### B3-BP3: Registry ↔ Runtime desync (no sync bridge)

| 字段 | 值 |
|:---|:---|
| **Boundary** | B3 Capability → Registry |
| **Bypass ID** | B3-BP3 |
| **Path** | Registry (declarative metadata) ↔ Runtime Resolver (operational) — 两条独立路径, 无强制同步桥接 |
| **Impact** | Registry 声明与 Runtime 实际可分解。Phase 6.2 CR-01~CR-04 的一致性要求不成立 |
| **Evidence** | `src/media-understanding/provider-capability-registry.ts` (Registry) vs `src/image-generation/provider-registry.ts` (Runtime Resolver). 两个文件无相互调用, 无共享状态, 无同步事件 |
| **Classification** | 🟥 **MISSING** — No synchronization mechanism |
| **Decision State** | DEFERRED_TO_PHASE (Phase 6.2 Future Revision) |

---

## §5 B4 — Context → Projection (3 bypass paths)

### B4-BP1: Direct system prompt assembly

| 字段 | 值 |
|:---|:---|
| **Boundary** | B4 Context → Projection |
| **Bypass ID** | B4-BP1 |
| **Path** | `buildEmbeddedSystemPrompt` → `buildAgentSystemPrompt` → `systemPromptText` → `LLM provider.sendMessages()`. 无 Projection 层 |
| **Impact** | Context 直接组装并注入 LLM, 不经过 Projection governance layer. Phase 6.3 CP-01 (Projection 唯一合法构造路径) 失效 |
| **Evidence** | `system-prompt.ts:670`: buildAgentSystemPrompt → 直接返回 systemPromptText. `agent-loop.js` → `provider.sendMessages({ system: systemPromptText })`. 0 行 Projection 代码在路径上 |
| **Classification** | 🟥 **MISSING** — Projection runtime implementation absent |
| **Decision State** | DEFERRED_TO_PHASE (Phase 6.3 Future Revision) |

### B4-BP2: Context Engine Plugin replacement

| 字段 | 值 |
|:---|:---|
| **Boundary** | B4 Context → Projection |
| **Bypass ID** | B4-BP2 |
| **Path** | `attempt.ts:3087` → `assembleAttemptContextEngine` → `harness/context-engine-lifecycle.ts` → Plugin returns custom systemPrompt → LLM |
| **Impact** | Plugin 可完全替换 systemPrompt, 不经过 Projection. 独立 Context 出口存在 |
| **Evidence** | `src/agents/pi-embedded-runner/run/attempt.ts:3087`: assembleAttemptContextEngine. `harness/context-engine-lifecycle.ts`: Plugin can return custom systemPrompt |
| **Classification** | ⚠️ **BYPASSABLE** — Plugin can replace context bypassing Projection |
| **Decision State** | ACCEPTED_GAP (Plugin Execution Contract PEC-02 — Plugin-owned extension boundary) |

### B4-BP3: Direct memory injection

| 字段 | 值 |
|:---|:---|
| **Boundary** | B4 Context → Projection |
| **Bypass ID** | B4-BP3 |
| **Path** | `buildMemoryPromptSection` (memory-state.ts) → 读取 MEMORY.md + memory/*.md → 直接追加到 systemPrompt |
| **Impact** | Memory 内容不经过 Context Governance, 直接注入 LLM context. 无中间验证/过滤/格式约束 |
| **Evidence** | `src/plugins/memory-state.ts`: buildMemoryPromptSection 读取文件 → 返回文本 → 追加到 systemPrompt. `system-prompt.ts`: 调用 buildMemoryPromptSection |
| **Classification** | ⚠️ **BYPASSABLE** — Memory loaded without governance layer |
| **Decision State** | DEFERRED |

---

## §6 B5 — Event → Truth (4 bypass paths)

### B5-BP1: Direct tool execute — no lifecycle event

| 字段 | 值 |
|:---|:---|
| **Boundary** | B5 Event → Truth |
| **Bypass ID** | B5-BP1 |
| **Path** | `agent-loop.js:419` → `tool.execute()` — 不经 `runToolLifecycle`, 不 emit lifecycle 事件 |
| **Impact** | B1 bypass 路径执行的工具调用不产生事件.Event 系统不覆盖全部执行路径.Phase 6.4 R-04 (event = truth) 不成立 |
| **Evidence** | `agent-loop.js` vs `attempt.ts:3269`: 前者直接 execute(), 后者包装 runToolLifecycle. 两条路径的执行效果等价, 事件产出不等价 |
| **Classification** | ⚠️ **BYPASSABLE** — Execution path without event coverage |
| **Decision State** | DEFERRED |

### B5-BP2: Plugin internal execute — no event at all

| 字段 | 值 |
|:---|:---|
| **Boundary** | B5 Event → Truth |
| **Bypass ID** | B5-BP2 |
| **Path** | Plugin internal `matchedTool.execute()` — 不在 agent-loop, 不在 attempt.ts, 不在任何事件路径 |
| **Impact** | Plugin 内部工具执行完全不可见. 没有任何事件记录该执行 |
| **Evidence** | `src/plugins/tools.ts`: createCachedDescriptorPluginTool → execute(). 无 emitAgentEvent, 无 runToolLifecycle, 无 emitTrustedDiagnosticEvent |
| **Classification** | ⚠️ **BYPASSABLE** — Invisible execution path |
| **Decision State** | ACCEPTED_GAP (Plugin Execution Contract PEC-03) |

### B5-BP3: Fire-and-forget — no truth verification

| 字段 | 值 |
|:---|:---|
| **Boundary** | B5 Event → Truth |
| **Bypass ID** | B5-BP3 |
| **Path** | `emitAgentEvent()` → `notifyListeners()` — fire-and-forget. 无验证: 事件 data 是否匹配实际结果, ts 是否准确, seq 是否连续 |
| **Impact** | Event 是观测层, 不是 truth anchor. 无法从 event 反推执行真相 |
| **Evidence** | `src/shared/listeners.ts`: notifyListeners — try/catch, fire-and-forget. 无回读/无确认/无完整性验证 |
| **Classification** | ⚠️ **BYPASSABLE** — Event system is observational, not verifiable |
| **Decision State** | ACCEPTED_GAP (Event = Observer) |

### B5-BP4: Phase 6 event schemas not emitted

| 字段 | 值 |
|:---|:---|
| **Boundary** | B5 Event → Truth |
| **Bypass ID** | B5-BP4 |
| **Path** | Schema 存在: `tool-call-event.schema.json`, `context-projection-event.schema.json`, `gateway-decision.schema.json`. Runtime: 0 次 emit |
| **Impact** | Phase 6 设计要求的结构化事件不存在. Event 系统缺少契约指定的 truth record |
| **Evidence** | Grep 确认 0 处 emit/create/publish 引用这些 schema 类型. Schemas 作为独立文件存在但未被运行时引用 |
| **Classification** | ⚠️ **BYPASSABLE** — Schema exists but not emitted |
| **Decision State** | DEPENDENCY_GAP |

---

## §7 分类汇总



---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | BYPASS REGISTER v1.0 — 15 bypass paths across 5 boundaries |
| v1.1 | 2026-07-19 | 治理决策注入: 15 条 Decision State 更新 (DEFERRED_TO_PHASE / ACCEPTED_GAP / REQUIRE_CHANGE / DEFERRED / DEPENDENCY_GAP) |
