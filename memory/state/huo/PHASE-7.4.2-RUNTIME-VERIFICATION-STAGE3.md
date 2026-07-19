# PHASE-7.4.2-RUNTIME-VERIFICATION-STAGE3.md

**Phase 7.4.2 — Runtime Verification Execution: Stage 3**
**Date:** 2026-07-19
**Object:** B2-BP1, B3-BP1, B3-BP3, B4-BP1, B5-BP3, B5-BP4, B2-BP3, B4-BP3

---

## §0 验证对象

| Bypass ID | Decision State | Verification Target |
|:---|---:|:---|
| B2-BP1 | REQUIRE_CHANGE | Worker policy path exists; confirm scope escape matches classification |
| B3-BP1 | DEFERRED_TO_PHASE | Registry ≠ Runtime Provider Resolver — confirm separate paths |
| B3-BP3 | DEFERRED_TO_PHASE | Provider direct execution bypasses Registry — confirm runtime path |
| B4-BP1 | DEFERRED_TO_PHASE | No runtime Projection layer — confirm absence |
| B5-BP3 | ACCEPTED_GAP | Event system = Observer, not enforcement — confirm pattern |
| B5-BP4 | DEPENDENCY_GAP | Schema exists, Producer absent — confirm status |
| B2-BP3 | DEFERRED | Temporal policy exists as timeout enforcement, not structural boundary |
| B4-BP3 | DEFERRED | Memory direct access through plugin path, not Projection |

---

## §1 B2-BP1: Worker Policy Path Enforcement

### Verification

**Decision State:** REQUIRE_CHANGE

**Expected:** Worker policy enforcement exists but scope escape can occur

### Evidence

**Primary — Source Code Path:**

```
subagent-spawn-ALADHNnO.js:726
  resolveSubagentTargetPolicy({
    requesterAgentId,
    targetAgentId,
    requestedAgentId,
    allowAgents: resolveAgentConfig(cfg)?.subagents?.allowAgents,
    configuredAgentIds: resolveConfiguredAgentIds(cfg)
  })
  ↓
if (!targetPolicy.ok) → return { status: "forbidden", error }
```

```
spawn-requester-origin-DcTBCToo.js:43-77
  resolveSubagentTargetPolicy() {
    const allowed = resolveSubagentAllowedTargetIds({
      requesterAgentId,
      allowAgents: params.allowAgents,
      configuredAgentIds: params.configuredAgentIds
    });
    if (allowed.allowedIds.includes(targetAgentId)) return { ok: true };
    if (allowed.allowAny) return { ok: false, error: "not in configured agent registry" };
    return { ok: false, error: "agentId is not allowed" };
  }
```

**Observations:**
- ✅ Policy enforcement exists at spawn time
- ✅ Enforcement checks: agentId allowlist, config-based allowAgents
- ✅ Policy scope: agentIdentity-level, not execution-level
- ✅ Worker execution path (after spawn) has no re-policy check

**Secondary — Runtime Log:**

```
No spawn policy errors observed in runtime trace
Policy enforcement only triggers on explicit scope violations
```

### Result

```
Decision: REQUIRE_CHANGE
Expected: Policy path exists, scope escape possible
Observed: resolveSubagentTargetPolicy at spawn; no execution-time re-check
Evidence: subagent-spawn-ALADHNnO.js:726-735, spawn-requester-origin-DcTBCToo.js:43-77
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §2 B3-BP1: Registry Design-Time Only

### Verification

**Decision State:** DEFERRED_TO_PHASE (Phase 6.2)

**Expected:** Registry exists as design-time contract; runtime uses separate resolver

### Evidence

**Primary — Source Code Path:**

```
capability-provider-runtime-BOVCDaed.js (entire file):
- CAPABILITY_CONTRACT_KEY = { memoryEmbeddingProviders, speechProviders, ... }
- resolveCapabilityPluginIds() → loads from plugin manifest contracts
  - loadManifestContractSnapshot()
  - hasManifestContractValue(plugin, contract, value)
- resolveCapabilityContractProviders() → resolves runtime providers

Compare:
  Registry (design) = PROVIDER-CAPABILITY-REGISTRY.json schema
  Runtime Resolver = capability-provider-runtime.js → manifest contracts
```

```
bundled-capability-runtime-B8DnC9Wj.js:
- Separates bundled capability runtimes:
  - config-runtime
  - media-runtime
  - speech-core
- Each has independent resolution path, not going through registry validation
```

**Observations:**
- ✅ Registry schema exists (`provider-capability.schema.json`, 225 lines)
- ✅ Runtime resolver uses plugin manifest contracts, not registry
- ✅ Two separate paths: design-time registry ≠ runtime provider resolver
- ✅ Image/media providers have independent runtime via `image-generation/provider-registry.ts`

### Result

```
Decision: DEFERRED_TO_PHASE
Expected: Registry (design) ≠ Runtime Provider Resolver
Observed: capability-provider-runtime resolves via manifest contracts, not registry
Evidence: capability-provider-runtime-BOVCDaed.js, bundled-capability-runtime-B8DnC9Wj.js
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §3 B3-BP3: Provider Direct Execution Bypass

### Verification

**Decision State:** DEFERRED_TO_PHASE (Phase 6.2)

**Expected:** Provider execution exists outside Registry validation path

### Evidence

**Primary — Source Code Path:**

```
Bundled capability runtimes have independent execution paths:
1. image-generation/provider-registry.ts → imageGenerationProviders runtime
2. media-understanding/provider-capability-registry.ts → separate registry
3. speech providers → separate runtime path

Each bypasses the formal Capability Registry (Phase 6.2 design):
- Design Registry  = provider-capability.schema.json
- Runtime Provider = plugin contract-based resolver → direct execution
```

### Result

```
Decision: DEFERRED_TO_PHASE
Expected: Provider execution outside Registry validation
Observed: Multiple independent provider runtimes bypass registry validation
Evidence: capability-provider-runtime-BOVCDaed.js (manifest contract path)
         bundled-capability-runtime-B8DnC9Wj.js (independent runtimes)
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §4 B4-BP1: No Runtime Projection Layer

### Verification

**Decision State:** DEFERRED_TO_PHASE (Phase 6.3)

**Expected:** Context assembly goes directly to LLM without Projection layer

### Evidence

**Primary — Source Code Path:**

```
$ grep -rn "projection\|Projection\|context.*projection" dist/
→ ZERO matches in runtime code ✓

Context construction path:
  execute.runtime-DFKn7pjR.js:
    bootstrap-context → bundle-tools → system-prompt → agent-session → stream-setup
    
    Context injection via:
    - applyPluginTextReplacements()  ← Plugin text transforms
    - context.backendResolved.textTransforms?.input  ← Plugin input transforms
    - No ContextProjection.validate() or ContextProjection.format()
```

**Secondary — Runtime Log:**

```
[agent/embedded]: "context-engine compaction failed" → Context Engine is active
[agent/embedded]: trace:embedded-run prep stages → workspace-sandbox, skills,
  core-plugin-tools, bootstrap-context, bundle-tools, system-prompt,
  session-resource-loader, agent-session, stream-setup
  → NO projection stage ✓
```

### Result

```
Decision: DEFERRED_TO_PHASE
Expected: No runtime Projection layer
Observed: Zero "projection" matches in dist runtime; context via Plugin transforms
Evidence: execute.runtime-DFKn7pjR.js (context path), runtime log (no projection)
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §5 B5-BP3: Event as Observer

### Verification

**Decision State:** ACCEPTED_GAP

**Expected:** Event system = Observer pattern; no execution enforcement

### Evidence

**Primary — Source Code Path:**

```
agent-events-BuYtWSh4.js:
  function emitAgentEvent(event) {
    const state = getAgentEventState();
    // 1. increment sequence
    // 2. enrich with seq + ts
    // 3. notifyListeners(state.listeners, enriched)
    // NO: enforcement, validation, execution delay
  }
  
  function onAgentEvent(listener) {
    return registerListener(state.listeners, listener);
  }
  
  Architecture:
    emitAgentEvent → notifyListeners → registered listeners (push only)
    No: validate → reject → enforce lifecycle
```

**Observations:**
- ✅ pure Observer pattern: notifyListeners only
- ✅ No execution enforcement in event path
- ✅ No validation/rejection capability in event system
- ✅ Event is post-fact observation, not pre-execution gate

### Result

```
Decision: ACCEPTED_GAP
Expected: Event = Observer, not enforcement
Observed: emitAgentEvent → notifyListeners → listeners only
Evidence: agent-events-BuYtWSh4.js:56-80
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §6 B5-BP4: Schema Exists, Producer Absent

### Verification

**Decision State:** DEPENDENCY_GAP

**Expected:** Schemas designed, no runtime producer implements them

### Evidence

**Primary — Schema Files (state/huo):**

```
context-projection-bundle.schema.json   56 lines  ← Phase 6.3 design
context-projection-event.schema.json   112 lines  ← Phase 6.3 design
context-projection.schema.json         141 lines  ← Phase 6.3 design
gateway-decision.schema.json           120 lines  ← Phase 6.4 design
provider-capability.schema.json        225 lines  ← Phase 6.2 design
tool-call-event.schema.json            108 lines  ← Phase 6.4 design
tool-call-request.schema.json           58 lines  ← Phase 6.4 design
Total: 820 lines, 7 schemas
```

**Secondary — Runtime Evidence:**

```
$ grep -rn "context-projection\|gateway-decision\|tool-call-event\|tool-call-request" dist/
→ ZERO matches for runtime consumption of these schemas ✓

$ grep -rn "provider-capability" dist/
→ The CAPABILITY_CONTRACT_KEY exists in capability-provider-runtime
→ but uses manifest contract keys, NOT the provider-capability schema
```

**Observations:**
- ✅ 7 schema files exist (820 total lines, Phase 6 design)
- ✅ Zero runtime code consumes gateway-decision, context-projection, or tool-call-* schemas
- ✅ provider-capability schema has design-time equivalent but runtime uses manifest contracts instead
- ✅ Confirms: Schema exists, Producer absent

### Result

```
Decision: DEPENDENCY_GAP
Expected: Schemas exist, no runtime producer
Observed: 7 schema files (820 lines), zero runtime consumers
Evidence: ls + wc of *.schema.json; grep -rn in dist (zero consumers)
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §7 B2-BP3: Temporal Policy

### Verification

**Decision State:** DEFERRED

**Expected:** Temporal enforcement exists (timeout), but as operational safety, not structural boundary

### Evidence

**Primary — Source Code Path:**

```
agent-runner-execution-DJZC3dxh.js:
  CLI_BACKEND_OVERALL_TIMEOUT_RE = /CLI exceeded timeout/
  timeout logic: error message formatting, timeoutSeconds config
  rateLimit handling: formatRateLimitOrOverloadedErrorCopy, buildRateLimitCooldownMessage
```

**Observations:**
- ✅ timeout enforcement exists (operational safety)
- ✅ rate limit handling exists (operational safety)
- ❌ No structural boundary enforcement (tool identity, capability, context)

### Result

```
Decision: DEFERRED
Expected: Temporal policy = operational safety only
Observed: timeoutSeconds config, rateLimit handling — not structural boundary
Evidence: agent-runner-execution-DJZC3dxh.js
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §8 B4-BP3: Memory Direct

### Verification

**Decision State:** DEFERRED

**Expected:** Memory tools execute directly through plugin path, not through Projection

### Evidence

**Primary — Source Code Path:**

```
Memory-core is a Plugin:
  plugin-sdk/memory-core.d.ts
  plugin-sdk/memory-core-host-engine-embeddings.d.ts
  plugin-sdk/memory-core-host-events.d.ts
  
  memory-core is in plugin list:
    "9 plugins: browser, canvas, device-pair, duckduckgo, file-transfer,
     memory-core, phone-control, talk-voice, telegram"
```

```
Execution path for memory operations:
  Plugin Tool → createCachedDescriptorPluginTool()
    → resolvePluginToolRegistry()
    → factory(ctx) → matchedTool.execute()
    → memory-core internal execute
    → No Context Projection layer
    → Direct memory read/write
```

**Observations:**
- ✅ memory-core is a registered plugin (9 plugins list)
- ✅ Memory tools execute through Plugin Tool path (B1-BP2 path)
- ✅ No Projection layer involvement
- ✅ Direct memory access — matches DEFERRED classification

### Result

```
Decision: DEFERRED
Expected: Memory direct through plugin path, not Projection
Observed: memory-core plugin → direct execute path
Evidence: plugin list (runtime log), memory-core plugin SDK (dist), B1-BP2 path
Result:   Observed == Decision → ✅ PASS
No Reclassification: ✅
```

---

## §9 验证汇总

| Bypass ID | Decision State | Observed Runtime | Evidence | Result |
|:---|---:|:---|---:|:---:|
| B2-BP1 | REQUIRE_CHANGE | Spawn policy exists; execution-time scope escape possible | subagent-spawn L726, spawn-requester-origin L43-77 | ✅ PASS |
| B3-BP1 | DEFERRED_TO_PHASE | Registry (design) ≠ Runtime Resolver (manifest contracts) | cap-provider-runtime.js (manifest contract path) | ✅ PASS |
| B3-BP3 | DEFERRED_TO_PHASE | Independent provider runtimes bypass Registry | bundled-capability-runtime, image-generation providers | ✅ PASS |
| B4-BP1 | DEFERRED_TO_PHASE | No runtime Projection; context via Plugin transforms | 0 grep matches; execute.runtime path (no projection) | ✅ PASS |
| B5-BP3 | ACCEPTED_GAP | Event = Observer pattern (notifyListeners only) | agent-events.js L56-80 (emit → notify) | ✅ PASS |
| B5-BP4 | DEPENDENCY_GAP | 7 schemas (820 lines); zero runtime consumers | ls *.schema.json; grep -rn dist (0 matches) | ✅ PASS |
| B2-BP3 | DEFERRED | Timeout/rateLimit = operational, not structural | agent-runner-execution.js (timeout/rateLimit) | ✅ PASS |
| B4-BP3 | DEFERRED | memory-core plugin → direct execute → no Projection | plugin list, memory-core SDK, B1-BP2 path | ✅ PASS |

### Validation Signature

```
Stage 3 = COMPLETE
  8/8 paths → ✅ PASS
  No reclassification triggered
  All observations match governance decisions

Phase 7.4 Summary:
  Stage 1 (Gateway/Event):  2 paths → 2 PASS
  Stage 2 (Plugin):         4 paths → 4 PASS
  Stage 3 (Remaining):      8 paths → 8 PASS
  Total:                   14 paths → 14 PASS
  Excluded (7.4 Scope):     1 path (B3-BP2, semantic gap, runtime-inherent)
```

---

## §10 Phase 7.4 Complete — Transition Ready

```
Phase 7.4.1 Verification Scope Lock    🔒 ACCEPTED
Phase 7.4.2 Runtime Verification:
  Stage 1 (Runtime Trace)              ✅ COMPLETE
  Stage 2 (Plugin Boundary)            ✅ COMPLETE
  Stage 3 (Remaining)                  ✅ COMPLETE
Phase 7.4 Closure:                     🔒 PENDING

Next: Phase 8+ Transition
Phase 7 series complete:
  Phase 7.1: Audit Contract            🔒 FROZEN
  Phase 7.2: Boundary Matrix           🔒 FROZEN
  Phase 7.3: Bypass Closure            🔒 CLOSED
  Phase 7.4: Runtime Verification       ✅ COMPLETE
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Stage 3 Verification Execution — 8 remaining paths |
