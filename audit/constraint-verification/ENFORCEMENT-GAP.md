# Enforcement Gap Register

> 契约 enforcement 声明与实际的偏差记录
> META-CONTRACT v1.2 Integrity Check — 2026-07-21 08:22 CST

```yaml
rule: 不能保持 "声明 > 实际" 的状态长期存在。
      Contract 必须反映真实的约束能力。

status_values:
  open: 发现 gap，尚未处理
  pending_repair: 已确认修复方向，等待执行
  resolved: 已修复，声明与实际一致
```

---

## Gap 1: PRIVILEGE-CONTROL

```yaml
contract: PRIVILEGE-CONTROL
authority: A3
declared:
  binding:
    target: runtime
  enforcement:
    mode: automatic
    mechanism: gateway-policy/sandbox

actual:
  target: runtime
  mode: procedural
  mechanism: exec-approval-manager (未配置, default: auto)
  evidence:
    - config.yaml: execApprovals 未设置
    - 无 ask:"always" 配置
    - 无 sandbox 配置

gap:
  type: declaration_overreach
  severity: high
  description: |
    契约声明约束力 automatic，但实际运行时无 approval gate。
    Rule 1 (默认拒绝) 依赖人工遵守，非代码强制。

options:
  A: 降级声明
    binding:
      target: workspace
    enforcement:
      mode: procedural
      mechanism: governance-review
    影响: 承认特权控制当前不是硬约束
    成本: 无

  B: 补实现
    配置:
      config.yaml: execApprovals.enabled: true
      agent config: ask: "always" (高风险操作)
    影响: 契约声明与实际一致
    成本: 中等 — 需终端配置

decision:
  action: keep_declaration
  reason: PRIVILEGE-CONTROL 语义是权限边界，不是流程约定。声明保持 automatic
  repair_required: true
  repair:
    - 补 exec approval 配置 (config.yaml: execApprovals)
    - 高风险操作配置 ask:"always"
    - 完成后重新验证
  status: pending_repair
```

---

## Gap 2: MEMORY-OWNERSHIP

```yaml
contract: MEMORY-OWNERSHIP
authority: A1
declared:
  binding:
    target: workspace
  enforcement:
    mode: procedural
    mechanism: governance-convention

actual:
  target: workspace
  mode: advisory
  mechanism: directory convention + agent runtime check
  evidence:
    - memory/events/ 文件 664/600 无 ACL 区分
    - state/huo/ 目录 775 无 ACL
    - namespace 分离依赖 agent 遵守

gap:
  type: declaration_overreach
  severity: medium
  description: |
    声明 procedural (流程保证)，实际 advisory (模型自觉)。
    namespace 分离无 filesystem 强制，agent 可写错位置。

resolution:
  action: declaration_adjusted
  detail: |
    声明 mode 从 procedural 修正为 advisory。
    当前无 filesystem ACL 或 namespace validator。
    namespace 分离依赖模型遵守。
  status: resolved ✅
  evidence:
    - MEMORY-OWNERSHIP-CONTRACT.md 声明块已更新
```
