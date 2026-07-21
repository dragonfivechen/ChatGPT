# Enforcement Consistency Verification

> 验证 A2-A4 契约的 enforcement 声明与真实执行层是否一致
> Date: 2026-07-21 08:20 CST

```yaml
method: config_snapshot + source_trace
```

## 1. PRIVILEGE-CONTROL

```yaml
declared:
  binding:
    target: runtime
  enforcement:
    mode: automatic
    mechanism: gateway-policy

reality:
  target: runtime
  mode: "procedural (config: not set, default: auto)"
  mechanism: exec-approval-manager
  evidence:
    - config.yaml: execApprovals → 未配置 (default: auto)
    - 无 ask:"always" 配置

gap:
  - 声明 automatic（自动执行代码强制）
  - 实际 exec approval 未配置，依赖 default allow 策略
  - 非 automatic，实际为 procedural（流程因无配置而绕过）

recommendation:
  - 如果 PRIVILEGE-CONTROL 的 Rule 1 (默认拒绝) 要生效，需配置 execApprovals
  - 或调整契约声明为 procedural 以匹配现实
```

## 2. CREDENTIAL-ACCESS

```yaml
declared:
  binding:
    target: runtime
  enforcement:
    mode: automatic
    mechanism: SecretRef/OS permission

reality:
  target: runtime
  mode: automatic
  mechanism: SecretRef resolve + OS file permission
  evidence:
    - SecretRef 统一 resolve 链 (src/config/types.secret-ref.ts)
    - .secrets/ 目录权限 600
    - token 值不暴露到 env/event

gap: none ✅
```

## 3. MEMORY-OWNERSHIP

```yaml
declared:
  binding:
    target: workspace
  enforcement:
    mode: procedural
    mechanism: governance-convention

reality:
  target: workspace
  mode: advisory (filesystem 无 ACL)
  mechanism: directory convention + agent runtime check
  evidence:
    - memory/ namespace 无 ACL 区分
    - state/huo/ 目录 775, 非 700
    - events 文件 664 非 600

gap:
  - 声明 procedural（流程保证）
  - 实际 advisory — namespace 分离依赖 agent 遵守，无 filesystem 强制
  - 建议修正 enforcement.mode 为 advisory，或增加 ACL
```

## 4. FREEZE-CONTRACT

```yaml
declared:
  binding:
    target: workspace
  enforcement:
    mode: procedural
    mechanism: governance-review

reality:
  target: workspace
  mode: procedural
  mechanism: governance-review
  evidence:
    - 无 git hook 阻止修改治理文件
    - 无 runtime checker 强制冻结规则
    - 但 Registry 和审查流程可检测未授权变更

gap: none ✅ (procedural 模式描述准确)
```

## 汇总

| 契约 | 声明 mode | 实际 mode | Gap | 风险 |
|------|:---------:|:---------:|:---:|:----:|
| PRIVILEGE-CONTROL | automatic | procedural | 🔴 声明过强 | 未配置执行审批 |
| CREDENTIAL-ACCESS | automatic | automatic | ✅ | — |
| MEMORY-OWNERSHIP | procedural | advisory | 🟡 声明偏强 | 无 ACL 强制 |
| FREEZE-CONTRACT | procedural | procedural | ✅ | — |
