# PHASE-7.4.2-RUNTIME-VERIFICATION-STAGE2.md

**Phase 7.4.2 — Runtime Verification Execution: Stage 2**
**Date:** 2026-07-19
**Object:** B1-BP2, B2-BP2, B4-BP2, B5-BP2

---

## §0 验证对象

### B1-BP2: Plugin internal direct execute (ACCEPTED_GAP)

| 字段 | 值 |
|:---|:---|
| **Decision State** | ACCEPTED_GAP (Plugin PEC-01: Tool Execution Declaration, SHOULD) |
| **Expected** | Plugin tool execute 独立于 agent-loop 核心执行路径 |
| **PASS 条件** | Plugin execute 路径无 Gateway.intercept(), 且独立于 agent-loop direct path |

### B2-BP2: Plugin internal policy bypass (ACCEPTED_GAP)

| 字段 | 值 |
|:---|:---|
| **Decision State** | ACCEPTED_GAP (Plugin PEC-01) |
| **Expected** | Plugin internal execute 绕过 Policy Pipeline |
| **PASS 条件** | Plugin tool execute 不经过 applyToolPolicyPipeline / filterToolsByPolicy |

### B4-BP2: Context Engine Plugin replacement (ACCEPTED_GAP)

| 字段 | 值 |
|:---|:---|
| **Decision State** | ACCEPTED_GAP (Plugin PEC-02, Plugin-owned extension boundary) |
| **Expected** | Context Engine Plugin 具备替换 Context Projection 的能力 |
| **PASS 条件** | Runtime 存在 Context Engine 注册机制 + Plugin text transforms |

### B5-BP2: Plugin internal — no event (ACCEPTED_GAP)

| 字段 | 值 |
|:---|:---|
| **Decision State** | ACCEPTED_GAP (Plugin PEC-03: Event Observability, SHOULD) |
| **Expected** | Plugin tool execute 不产生 emitAgentEvent / emitTrustedDiagnosticEvent |
| **PASS 条件** | Plugin execute 路径无 lifecycle event emit |

---

## §1 验证方法

### 1.1 Source Code Trace

```
LLM tool call → agent-loop.js executeToolCalls()
  ↓ prepareToolCall()
  ↓ executePreparedToolCall() → prepared.tool.execute()
  ↓
Core tool?    → tool.execute() directly (B1-BP1 verified)
Plugin tool?  → createCachedDescriptorPluginTool()
                      ↓
                resolvePluginToolRegistry()
                      ↓
                candidate.factory(ctx) → matchedTool
                      ↓
                matchedTool.execute(toolCallId, executeParams, signal, onUpdate)
```

### 1.2 Evidence Priority

```
Primary:    Source code execution path (runtime binary)
Secondary:  Runtime log trace (24h+ log)
Supporting: Trace:embedded-run prep stages
```

---

## §2 验证执行

### 2.1 Primary Evidence: Source Code Path

**Evidence 1: Plugin Tool Execution Path (tools-KjqE-Yhb.js L394-450)**

```javascript
// createCachedDescriptorPluginTool():
async execute(toolCallId, executeParams, signal, onUpdate) {
    // Step 1: resolve runtime registry for plugin
    const candidates = resolvePluginToolRegistry({
        loadOptions: buildPluginRuntimeLoadOptions(params.loadContext, {
            activate: false, toolDiscovery: true,
            onlyPluginIds: [pluginId],
        }),
        onlyPluginIds: [pluginId]
    })?.tools.filter((candidate) => candidate.pluginId === pluginId);

    // Step 2: find matching candidate
    const resolved = candidate.factory(params.ctx);  // ← Plugin's own factory
    const runtimeTool = toolRaw;
    // ...
    return matchedTool.execute(toolCallId, executeParams, signal, onUpdate);  // ← Plugin's execute
}
```

**Observations:**
- ✅ No Gateway.intercept() in this path
- ✅ Independent of agent-loop's core execute
- ✅ Plugin tool calls its own matchedTool.execute() directly
- ✅ Bootstrap context injection via `candidate.factory(params.ctx)`

---

**Evidence 2: B1-BP2 — No Gateway.intercept() (agent-loop.js L416-435)**

```javascript
async function executePreparedToolCall(prepared, signal, emit) {
    // Direct call: prepared.tool.execute()
    // No Gateway.intercept() wrapping
    const result = await prepared.tool.execute(
        prepared.toolCall.id,
        prepared.args,
        signal,
        (partialResult) => { ... }
    );
    return { result, isError: false };
}
```

**Confirmation:**
- ✅ executePreparedToolCall calls prepared.tool.execute() directly
- ✅ No Gateway.intercept() before or after tool execution
- ✅ Works identically for core and plugin tools

---

**Evidence 3: B2-BP2 — Plugin Policy Bypass (agent-loop.js L254-280)**

```javascript
async function executeToolCalls(currentContext, assistantMessage, config, signal, emit) {
    const toolCalls = assistantMessage.content.filter((c) => c.type === "toolCall");
    // Policy filtering happens at tool registration time (resolvePluginTools)
    // NOT at execution time
    const preparation = await prepareToolCall(currentContext, assistantMessage, toolCall, config, signal);
    // executePreparedToolCall calls prepared.tool.execute() directly
}
```

**Confirmation:**
- ✅ Policy pipeline (filterToolsByPolicy) operates at tool resolution, not execution
- ✅ Plugin tool execute() bypasses execution-time policy checks
- ✅ Plugin factory self-governs its execution

---

**Evidence 4: B4-BP2 — Context Engine exists in runtime**

```javascript
// subagent-spawn-ALADHNnO.js:
import { i as resolveContextEngine } from "./registry-B-mVXdYO.js";
import { t as ensureContextEnginesInitialized } from "./init-DUm5_Rd2.js";

async function prepareContextEngineSubagentSpawn(params) {
    subagentSpawnDeps.ensureContextEnginesInitialized();
    preparation: await (await subagentSpawnDeps.resolveContextEngine(params.cfg))
        .prepareSubagentSpawn?.({ ... });
}
```

```javascript
// execute.runtime-DFKn7pjR.js:
let prompt = applyPluginTextReplacements(
    appendBootstrapPromptWarning(basePrompt, context.bootstrapPromptWarningLines, ...),
    context.backendResolved.textTransforms?.input    // ← Plugin text transforms
);
```

**Confirmation:**
- ✅ Context Engine is a registered runtime component
- ✅ Plugin text transforms (`applyPluginTextReplacements`) modify context content
- ✅ No formal Context Projection layer (Phase 6.3) is enforced

---

**Evidence 5: B5-BP2 — No lifecycle events in plugin path**

```javascript
// agent-loop.js executePreparedToolCall (B1-BP1 checked)
// No emitAgentEvent, no emitTrustedDiagnosticEvent

// tools-KjqE-Yhb.js createCachedDescriptorPluginTool execute
// No emitAgentEvent, no emitTrustedDiagnosticEvent
// Only agent-loop internal events: tool_execution_start/end/update/result

// Compare: Where DO emitAgentEvent exist?
// agent-runner-execution-DJZC3dxh.js → agent lifecycle
// execute.runtime-DFKn7pjR.js → CLI runners
// NOT in plugin tool execution path
```

**Confirmation:**
- ✅ Plugin tool execute path has no emitAgentEvent
- ✅ Plugin tool execute path has no emitTrustedDiagnosticEvent
- ✅ agent-loop only emits internal execution events (not lifecycle events)

---

### 2.2 Secondary Evidence: Runtime Log Trace (24h+)

**Evidence 6: Runtime log confirms absence**

```bash
# emitAgentEvent / emitTrusted in runtime log
$ grep -E "emitAgentEvent|emitTrusted|projection|Gateway\.intercept|tool_lifecycle|runToolLifecycle" /tmp/openclaw/openclaw-2026-07-19.log
→ 0 matches (excluding persistence edit failures) ✓

# Plugin tool execution log
$ grep "plugin.*tool\|tool.*plugin\|resolvePlugin\|createCached" /tmp/openclaw/openclaw-2026-07-19.log
→ 0 matches (plugin execution is silent) ✓
```

**Evidence 7: Context Engine runtime activity**

```bash
$ grep "context.engine" /tmp/openclaw/openclaw-2026-07-19.log
→ "context-engine compaction failed" — confirms Context Engine is active ✓
```

**Evidence 8: Plugin boot at Gateway startup**

```bash
$ grep "plugins:" /tmp/openclaw/openclaw-2026-07-19.log
→ "http server listening (9 plugins: browser, canvas, device-pair, duckduckgo,
    file-transfer, memory-core, phone-control, talk-voice, telegram; 4.2s)"
→ Confirms plugins loaded at runtime ✓
```

---

### 2.3 Supporting Evidence: trace:embedded-run prep stages

```
core-plugin-tools: 260ms@261ms  ← Plugin tool resolution at stream start
bootstrap-context: 14ms@275ms   ← Context bootstrap injection
```

**Observations:**
- Plugin tools resolved at stream phase, not execution phase
- Context bootstrap occurs before agent-loop starts

---

## §3 验证结果

| Bypass ID | Decision State | Observed Path | Result |
|:---|---:|:---|---:|
| **B1-BP2** | ACCEPTED_GAP | Plugin execute independent of Gateway → no intercept | ✅ PASS |
| **B2-BP2** | ACCEPTED_GAP | Plugin execute bypasses execution-time policy pipeline | ✅ PASS |
| **B4-BP2** | ACCEPTED_GAP | Context Engine registered + Plugin text transforms replace Projection | ✅ PASS |
| **B5-BP2** | ACCEPTED_GAP | Plugin execute path has no emitAgentEvent/emitTrustedDiagnosticEvent | ✅ PASS |

### Result Details

**B1-BP2: ✅ PASS**
```
Decision: ACCEPTED_GAP (Plugin PEC-01)
Expected: Plugin tool execute independent of Gateway
Observed: createCachedDescriptorPluginTool → resolvePluginToolRegistry → factory → matchedTool.execute()
          No Gateway.intercept() wrapping
Evidence: tools-KjqE-Yhb.js:394-450, agent-loop.js:416-435
Result:   Observed == Decision
No Reclassification: ✅
```

**B2-BP2: ✅ PASS**
```
Decision: ACCEPTED_GAP (Plugin PEC-01)
Expected: Plugin internal execute bypasses Policy Pipeline
Observed: Policy filtering at resolution time; execution bypasses applyToolPolicyPipeline
Evidence: agent-loop.js:254-280, tools-KjqE-Yhb.js:620-720
Result:   Observed == Decision
No Reclassification: ✅
```

**B4-BP2: ✅ PASS**
```
Decision: ACCEPTED_GAP (Plugin PEC-02)
Expected: Context Engine Plugin replaces Context Projection
Observed: resolveContextEngine registered + applyPluginTextReplacements active
          No formal Projection layer present
Evidence: subagent-spawn-ALADHNnO.js:505-528, execute.runtime-DFKn7pjR.js:305
          Runtime log: "context-engine compaction failed"
Result:   Observed == Decision
No Reclassification: ✅
```

**B5-BP2: ✅ PASS**
```
Decision: ACCEPTED_GAP (Plugin PEC-03)
Expected: Plugin tool execute no lifecycle event
Observed: Zero emitAgentEvent/emitTrustedDiagnosticEvent in plugin path
Evidence: tools-KjqE-Yhb.js:394-450 (no emit), agent-loop.js:416-435 (no emit)
          Runtime log: zero matches for lifecycle patterns
Result:   Observed == Decision
No Reclassification: ✅
```

---

## §4 验证签名

```
Stage 2 = COMPLETE
  4/4 ACCEPTED_GAP → ✅ PASS
  No reclassification triggered
  All observations match governance decisions

Summary:
  B1-BP2: Plugin execute → independent path → match ACCEPTED_GAP
  B2-BP2: Plugin policy → bypass at execution → match ACCEPTED_GAP
  B4-BP2: Context Engine → Projection replacement → match ACCEPTED_GAP
  B5-BP2: Plugin event → no lifecycle event → match ACCEPTED_GAP
```

---

## §5 Next: Stage 3 — Remaining Independent Paths

Stage 2 complete. Ready for:

```
Stage 3:
  B1-BP2 → merged into Stage 2 (DONE)
  B2-BP1: Worker policy bypass               (REQUIRE_CHANGE)
  B3-BP1: Registry design-time only           (DEFERRED_TO_PHASE)
  B3-BP3: Provider direct execution bypass    (DEFERRED_TO_PHASE)
  B4-BP1: No runtime Projection layer         (DEFERRED_TO_PHASE)
  B5-BP3: Event as Observer — no enforcement  (ACCEPTED_GAP)
  B5-BP4: Schema exists, upstream absent       (DEPENDENCY_GAP)
  B2-BP3: Temporal policy                     (DEFERRED)
  B4-BP3: Memory direct                        (DEFERRED)
  B3-BP2: semantic gap                         (ACCEPTED_GAP — excluded from 7.4)
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Stage 2 Verification Execution — B1-BP2, B2-BP2, B4-BP2, B5-BP2 |
