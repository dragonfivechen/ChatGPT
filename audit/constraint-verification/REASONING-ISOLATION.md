# Constraint Verification: REASONING-ISOLATION

> 验证 reasoning 是否可能污染 memory/event/fact
> Date: 2026-07-21 07:26 CST

```yaml
contract: REASONING-ISOLATION
authority: A2
level: L1
verification_method: source_trace
```

## Verification

### 1. Reasoning 生命周期

```
LLM Response
  ├── content → agent conversation
  └── reasoning → 使用后丢弃
                   │
                   └── 不进入 context / memory / event / fact
```

### 2. Reasoning 隔离检查

| 检查点 | 源码 | 结果 |
|--------|------|:----:|
| reasoning 写入 context | `agents/btw.ts`: reasoningText 仅用于事件 delta 计算，不持久化 | ✅ |
| reasoning 进入 memory | memory 写入路径无 reasoning 字段 | ✅ |
| reasoning 进入 event | diagnostic-events 含 reasoning 但仅用于调试，非业务 event | ✅ |
| reasoning → context context | `auto-reply/thinking.ts`: reasoning 仅在 thinking 上下文传递 | ✅ |
| reasoning 流分离 | openai-http.ts: reasoning 独立处理 | ✅ |

### 3. 禁止路径验证

```text
reasoning
   │
   ├── → Context        ❌ 禁止
   ├── → Memory         ❌ 禁止  
   ├── → Event (业务)    ❌ 禁止
   ├── → Fact           ❌ 禁止
   └── → Diagnostic     ✅ 仅用于调试/日志
```

## Result

```yaml
verification:
  contract: REASONING-ISOLATION
  result: PASS
  evidence:
    - src/gateway/openai-http.ts (reasoning stream handling)
    - src/agents/btw.ts (reasoningText scoped)
    - src/auto-reply/thinking.ts (thinking context)
  finding: |
    Reasoning content 生命周期受限制。
    不进入 context 构建路径、不写入 memory/event/fact。
    Diagnostic 渠道存在 reasoning 信息但隔离于业务路径。
  timestamp: 2026-07-21 07:26 CST
```
