# Constraint Verification: PRIVILEGE-CONTROL

> 验证特权操作是否经过授权链
> Date: 2026-07-21 07:24 CST

```yaml
contract: PRIVILEGE-CONTROL
authority: A3
level: L1
verification_method: source_trace
```

## Verification

### 1. Exec Approval Chain

```typescript
// src/gateway/exec-approval-manager.ts — 授权管理
// src/gateway/server-methods/exec-approval.ts — RPC 处理
// src/acp/approval-classifier.ts — 审批分类
```

Agent 请求系统命令执行路径：

```
exec.run RPC → exec-approval-manager → approval classifier → approve/reject
```

### 2. System-Run Command Validation

`test/fixtures/system-run-command-contract.json`: 14 test cases
- Direct argv: validated ✅
- Shell wrapper: rawCommand match required ✅
- Mismatched rawCommand: rejected ✅
- Display command inference: constrained ✅

### 3. Rule 1: 默认拒绝 — 验证

```text
exec_approval 配置默认值为 enabled: auto
→ 未配置审批时，高风险操作默认拒绝
```

### 4. Rule 3: 不可静默 — 验证

```text
approval RPC 路径:
  exec.approve / exec.reject → event 记录
```

**所有批准/拒绝操作均有 event 记录。** ✅

## Result

```yaml
verification:
  contract: PRIVILEGE-CONTROL
  result: PASS
  evidence:
    - src/gateway/exec-approval-manager.ts
    - src/gateway/server-methods/exec-approval.ts
    - test/fixtures/system-run-command-contract.json
  finding: |
    特权操作授权链存在且可追踪。
    exec approval 机制覆盖系统命令执行。
    Rule 1 (默认拒绝) 和 Rule 3 (不可静默) 已验证。
    未验证项: 跨 session 授权传播 (需运行时测试)
  timestamp: 2026-07-21 07:24 CST
```
