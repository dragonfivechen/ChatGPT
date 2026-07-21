# PRIVILEGE-CONTROL-CONTRACT v1.0

```yaml
contract:
  name: PRIVILEGE-CONTROL
  version: v1.0
  level: L1
  type: privilege_control
  authority_impact: A3
  parent: FREEZE-CONTRACT
  scope: privileged operations (root, sudo, credential, irreversible)
  owner: 燃🔥
  status: active
  purpose: 定义特权操作的授权、执行、审计规则，防止权限滥用和跃迁
```

> 权限控制契约 — 定义特权操作（root/sudo/credential/不可逆操作）的授权、执行、审计规则。
> 新增于 META-CONTRACT v1.2 Q7 Authority Impact 框架。

---

## 1. 定位

特权操作超出普通模块能力边界（A1）和系统能力（A2），触及系统控制权和数据所有权。

本契约不是特权来源文档，而是特权使用的治理规则。

---

## 2. Root 操作四条硬约束

### Rule 1：默认拒绝

```text
root capability = deny by default
```

没有明确授权，不存在隐式 root。

已有凭据（token, PAT）不代表拥有 root 权限。凭据只能用于授权范围内的指定操作。

---

### Rule 2：最小范围

禁止：

```text
sudo ALL（无限制 root）
```

每次特权操作必须声明：

| 维度 | 要求 |
|------|------|
| command scope | 精确命令/脚本路径 |
| time scope | 操作时间窗口（非永久） |
| purpose scope | 操作原因（必须可审计） |
| target scope | 操作目标对象 |

---

### Rule 3：不可静默

所有 root 级别操作必须产生不可抵赖的事件记录：

```text
privilege_event:
  trace_id:   str（全局唯一）
  actor:      str（执行身份）
  operation:  str（具体操作描述）
  command:    str（精确命令）
  scope:      dict（范围声明）
  timestamp:  ISO-8601
  result:     success / failure / partial
  evidence:   str（日志/输出引用）
```

禁止：

- root 操作不记录
- root 操作记录不包含操作内容
- root 操作记录没有 trace_id

---

### Rule 4：不能修改自身治理边界

特权操作不能用于修改治理体系本身。

禁止：

| 操作 | 原因 |
|------|------|
| 修改 META-CONTRACT | 治理层变更需 M0 仲裁 |
| 降低 FREEZE-CONTRACT 规则 | 冻结规则不可由特权覆盖 |
| 删除 Event / Evidence | 审计链不可破坏 |
| 提升自身权限 | 权限膨胀自指 |

---

## 3. 授权流程

```text
特权操作请求
      │
      v
授权申请 (request + reason + scope)
      │
      v
审核 (终端确认)
      │
      v
授权执行 (最小范围, 带 event)
      │
      v
执行后证据提交 (event + trace_id)
      │
      v
审计归档
```

---

## 4. 禁止的特权模式

| 模式 | 说明 | 约束 |
|------|------|------|
| 永久 root 授权 | 授权无限期 | ❌ 禁止 |
| 隐式 root | 凭据即 root 权限 | ❌ 禁止 |
| 静默 root | root 不记录 | ❌ 禁止 |
| root 修改治理 | root 改 META/Freeze | ❌ 禁止 (Rule 4) |
| 循环授权 | root 授权另一个 root | ❌ 禁止 |

---

## 5. 与 CREDENTIAL-ACCESS-CONTRACT 的关系

| 维度 | CREDENTIAL-ACCESS | PRIVILEGE-CONTROL |
|------|------------------|--------------------|
| Level | L1 | L1 |
| Authority Impact | A3 | A3 |
| 范围 | Git push credential | 全系统特权操作 |
| 对象 | token 管理 | root/sudo/credential/不可逆操作 |
| 交集 | credential 是特权操作的子集 | 覆盖更大范围 |

两个契约共同构成特权治理的 A3 层。

---

## 6. 权限提升规则（Authority Escalation Rule）

> 防止权限从低等级跃迁到高等级，产生越权。

### 6.1 权限升级路径

任何操作或角色的权限变更必须严格按照以下路径逐级审批：

```text
A0 → A1   模块负责人批准
               │
               v
A1 → A2   系统治理批准
               │
               v
A2 → A3   特权审批（本契约流程）
               │
               v
A3 → A4   M0 治理变更流程（人工终端确认）
```

### 6.2 禁止的跃迁

| 跃迁 | 风险 |
|------|------|
| A0 → A3 | 普通模块获得特权 |
| A1 → A4 | 模块权限直接升级为治理权 |
| A2 → A4 | 系统能力直接获得治理权 |
| 跳过审批级 | 任何直接升级 |

### 6.3 权限降级

降级不需要审批，但需记录：

```
A3 → A2: 特权收回，记录 event
A2 → A1: 系统能力收回
```

### 6.4 与 Contract Registry 的关系

Registry 中每个契约的 authority_impact 字段记录当前权限等级。

如有权限冲突，以高等级为准：

```text
A2 契约 A + A3 契约 B → 执行 B 的权限约束
```

---

## 7. 违规处理

| 违规 | 严重度 | 处理 |
|------|:------:|------|
| 无授权 root 操作 | 🔴 P0 | 立即终止，审计所有操作 |
| root 操作无 event | 🔴 P0 | 补充记录，修复审计链 |
| root 修改治理边界 | 🔴 P0 | 回滚操作，M0 仲裁 |
| root 超范围执行 | 🟠 P1 | 评估影响，收紧范围 |
| root 授权未记录 | 🟠 P1 | 补授权记录 |

---

## 8. 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始契约，META-CONTRACT v1.2 Q7 框架下第一个 A3 实例 |
