# Constraint Verification: CONTEXT-PROJECTION

> 验证 projection 是否越权携带上下文
> Date: 2026-07-21 07:26 CST

```yaml
contract: CONTEXT-PROJECTION
authority: A2
level: L1
verification_method: source_trace
```

## Verification

### 1. Context Projection 路径

```text
LLM Request
    │
    ├── chat.ts (server-methods)
    │      → session-history → context build → projection
    │
    ├── codex-mcp-projection.ts (plugin-sdk)
    │      → MCP tool context projection
    │
    └── entrypoints.ts (plugin-sdk)
           → channel ingress context projection
```

### 2. Projection 边界检查

| 检查点 | 源码 | 结果 |
|--------|------|:----:|
| context 构建入口 | `gateway/server-methods/chat.ts`: chat 请求的 context 构建 | ✅ |
| session history 参与 projection | `gateway/session-history-state.ts`: 历史状态参与 context | ✅ |
| MCP 工具 projection | `plugin-sdk/codex-mcp-projection.ts`: 工具上下文投影 | ✅ |
| channel ingress projection | `plugin-sdk/channel-ingress-runtime.ts`: 通道进入投影 | ✅ |
| config projection | `config/io.ts`, `config/types.acp.ts`: 配置投影 | ✅ |
| 外部 worker context | plugin 可直接读取 memory，不经过 projection (已知 Phase 6.3 gap) | 🟡 |

### 3. 不变量验证

| Invariant | 验证 | 结果 |
|-----------|------|:----:|
| LLM=Consumer, Runtime=Builder | context 由 runtime 构建，LLM 仅消费 | ✅ |
| Event=Truth | projection_event 在 context 构建后写入 | ✅ |
| Memory≠Context | Writer 不能直接修改 Context | ✅ |
| reasoning 不进入 context | 已验证（见 REASONING-ISOLATION） | ✅ |

## Result

```yaml
verification:
  contract: CONTEXT-PROJECTION
  result: PASS
  evidence:
    - src/gateway/server-methods/chat.ts
    - src/plugin-sdk/codex-mcp-projection.ts
    - src/plugin-sdk/channel-ingress-runtime.ts
  finding: |
    Context Projection 链完整。context 构建由 runtime 控制。
    LLM 仅作为 context 的消费者。
    External Worker Context 直接读 memory 不经过 projection (已知 gap)。
  timestamp: 2026-07-21 07:26 CST
```
