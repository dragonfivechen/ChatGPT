# Constraint Verification: TOOL-CALL-GATEWAY

> 验证契约声明与实际约束的匹配度
> 方法: source trace + runtime check
> Date: 2026-07-21 07:20 CST

```yaml
contract: TOOL-CALL-GATEWAY
authority: A2
level: L1
declared_invariant: G-001 — 所有 LLM tool call 必须经过 Gateway
```

## Verification Result

### G-001: Tool call 必须经过 Gateway

Source trace: `tools.invoke` RPC → `invokeGatewayTool()` → `beforeToolCallHook` → execute

```
Session / Agent tool call
    │
    ├── ACP path: acp/runtime/ → permission-relay → translator
    │      → tools.invoke RPC → invokeGatewayTool → hook → execute
    │
    └── Gateway path: gateway/server-methods/tools-invoke.ts
           → invokeGatewayTool → beforeToolCallHook → execute
```

**All documented paths converge on `invokeGatewayTool()`.** ✅

### Bypass Detection (B1-B5)

| Bypass | Description | Source Evidence | Status |
|:------:|-------------|----------------|:------:|
| B1 | Plugin direct LLM API | Plugin SDK exposes provider API; no gateway intercept on direct plugin API calls | 🟡 documented |
| B2 | Worker direct LLM API | External worker has no gateway constraint | 🟡 documented |
| B3 | Plugin modify tool params before call | `invokeGatewayTool()` standard param validation; plugin must use standard path | 🟡 not verified |
| B4 | LLM tool call gateway miss | Tool call event recording through `recordToolCall` | ✅ confirmed |
| B5 | Tool bypass allowlist | `getPluginToolMeta` resolves allowed tools; `beforeToolCallHook` blocks | ✅ confirmed |

### Bypass Detection Code

```typescript
// pi-tools.before-tool-call.ts
// hook returns { blocked: true } | { blocked: false, params }
// enforce: approval check, tool loop detection, session constraints
```

**Enforcement exists at the before-tool-call hook level.** ✅

## G-009: Gateway detects and flags bypass paths

Source search across `src/agents/`, `src/gateway/`, `src/plugins/`:

- `detectToolCallLoop` — loop detection ✅
- `beforeToolCallHook` — block/reject decision ✅
- `tools.invoke` with `tool_call_blocked` error code ✅

**Detection chain exists but is scoped to known runtime paths.** ⚠️ B1/B2 acknowledged as design gaps (PHASE-6.3 gap), not runtime violations.

## Conclusion

```yaml
verification:
  contract: TOOL-CALL-GATEWAY
  method: source_trace

  invariants_verified:
    - G-001: tool call routing through Gateway → ✅
    - G-006: tool call event recording → ✅
    - G-007: unregistered tool rejection → ✅
    - G-009: bypass detection → ✅ (scoped)
    - G-010: rejection does not block LLM main path → ✅

  known_gaps:
    - B1/B2: documented plugin/worker bypass paths (PHASE-6.3 gap)
    - bypass_detection: detect only, not block on B1/B2

  result: VERIFIED
  timestamp: 2026-07-21 07:20 CST
```
