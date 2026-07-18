# 系统架构文档 (Architecture)

---

## 1. Agent Identity Governance

### 1.1 原则

```text
身份不能依赖模型记忆，必须由运行环境提供可验证身份。
```

### 1.2 身份源

唯一身份源：`IDENTITY-CONTRACT.md`

身份通过环境变量注入：

```bash
export AGENT_ID=agent-terminal   # 终端身份
export AGENT_ROLE=maintenance

export AGENT_ID=agent-tg          # TG 身份
export AGENT_ROLE=assistant
```

当前身份：由 `$AGENT_ID` / `$AGENT_ROLE` 确定。

### 1.3 身份越界防护

| Channel | 允许 | 禁止 |
|---------|------|------|
| shell | system_observation, maintenance_operation | 用户数据通知 |
| telegram | notification, user_interaction, report | 运行时修改 |

### 1.4 无法确定身份时

```text
fallback: agent-tg, role: assistant（最低权限）
```

### 1.5 关联

- `IDENTITY-CONTRACT.md` — 唯一身份源
- `IDENTITY.md` — 显示名称
- `IDENTITY-RULES.md` — 职责边界

---

## 2. 系统治理原则

### 2.1 Trust Boundary

```text
Event 不相信生产者
Memory 不相信写入者
Identity 不相信模型自述
```

### 2.2 数据治理

```text
写入后不修改
错误数据不删除，由修正事件补充
事件是事实源，不是缓存
```

### 2.3 扩展边界

```text
Runtime 核心不动
外部工作走标准模式（systemd timer + oneshot）
通知统一出口（push-gate.mjs）
Secrets 隔离（.secrets/ 目录）
```

---

## 3. 文档归属

```text
docs/ARCHITECTURE.md                    ← 本文件：系统治理原则、身份治理
docs/MODULE-CONSTRUCTION-HANDBOOK.md    ← 模块建设方法、避坑经验
docs/MODULE-INDEX.md                    ← 能力地图、模块目录
memory/state/huo/*-CONTRACT.md          ← 各模块领域规则
IDENTITY-CONTRACT.md                    ← 唯一身份源
```
