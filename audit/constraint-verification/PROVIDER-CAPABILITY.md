# Constraint Verification: PROVIDER-CAPABILITY

> 验证 provider 能力声明是否真实限制调用范围
> Date: 2026-07-21 07:26 CST

```yaml
contract: PROVIDER-CAPABILITY
authority: A2
level: L1
verification_method: source_trace
```

## Verification

### 1. Provider Capability Runtime Checks

| 检查点 | 源码 | 结果 |
|--------|------|:----:|
| capability 声明字段 | `config/types.googlechat.ts`: `capability?: string[]` | ✅ |
| provider-owned capability 归一化 | `gateway/session-utils.ts`: capability normalization | ✅ |
| node capability 过滤 | `gateway/node-registry.ts`: `(surface.caps ?? []).filter(capability => declaredCaps.has(capability))` | ✅ |
| capability CLI 验证 | `cli/capability-cli.ts`: 支持 `model.run` 等 capability 的子命令 | ✅ |
| provider catalog | `plugin-sdk/provider-catalog-shared.ts`: `capability: "llm"` | ✅ |

### 2. Capability Enforcement 链

```text
Provider 声明 capability
    ↓
Node Registry 过滤 (declaredCaps)
    ↓
Session-utils 归一化
    ↓
Provider 路由决策
```

**capability 声明影响调用路由。声明不匹配的 provider 不会接收对应调用。**

## Result

```yaml
verification:
  contract: PROVIDER-CAPABILITY
  result: PASS
  evidence:
    - src/config/types.googlechat.ts
    - src/gateway/node-registry.ts (capability filter)
    - src/cli/capability-cli.ts
  finding: |
    Provider capability 声明确实影响调用范围。
    Node registry 存在 capability 过滤机制。
    但 capability 粒度较粗（"llm"/"model.run"），暂未支持细粒度筛选。
  timestamp: 2026-07-21 07:26 CST
```
