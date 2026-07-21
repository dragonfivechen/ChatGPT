# Constraint Verification: CREDENTIAL-ACCESS

> 验证凭据访问是否符合最小权限
> Date: 2026-07-21 07:24 CST

```yaml
contract: CREDENTIAL-ACCESS
authority: A3
level: L1
verification_method: source_trace
```

## Verification

### 1. SecretRef 访问模型

```typescript
// src/config/types.secret-ref.ts — SecretRef 类型定义
// SecretRef 统一对象形状:
//   { source: "env"|"file"|"exec", provider: string, id: string }
```

```yaml
SecretRef contract (OpenClaw docs/gateway/secrets.md):
  - 统一对象形状
  - 启动时 fail-fast
  - 不活跃 surface 自动过滤
  - last-known-good 回退
```

### 2. 最小权限验证

| 凭据类型 | 访问方式 | 最小范围 |
|---------|----------|---------|
| env SecretRef | 环境变量读取 | 仅读取指定 key |
| file SecretRef | 文件读取 | 仅读取指定路径 |
| exec SecretRef | 命令执行读取 | 仅执行指定命令 |

**无通配符凭据读取。所有凭据通过命名引用解析。**

### 3. CREDENTIAL-ACCESS Rule 验证

| Rule | 源码证据 | 结果 |
|------|---------|:----:|
| 凭据引用不包含实际值 | SecretRef 只存 {source, provider, id}，不存值 | ✅ |
| token 不进入 memory | SecretRef resolve 路径绕过 memory 层 | ✅ |
| token 不进入 event | exec approval 和 SecretRef 均过滤 credential 值 | ✅ |
| 操作范围限制 | .secrets/push-gate.json 限定 git push 操作 | ✅ |

## Result

```yaml
verification:
  contract: CREDENTIAL-ACCESS
  result: PASS
  evidence:
    - src/config/types.secret-ref.ts
    - docs/gateway/secrets.md
    - .secrets/push-gate.json
  finding: |
    SecretRef 机制覆盖凭据访问控制。
    凭据引用不暴露值到 memory/event 路径。
    最小范围验证通过：所有凭据通过命名引用，无通配符。
  timestamp: 2026-07-21 07:24 CST
```
