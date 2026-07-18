# IDENTITY-CONTRACT.md v2.0

> 唯一身份源。身份由入口通道绑定决定，不由模型自行声明。

---

## 1. 身份定义

```yaml
identity_version: 2.0

agents:
  main:
    display_name: 燃🔥
    channel: [shell, webchat]
    role: maintenance
    authority:
      - system_observation
      - maintenance_operation

  tg-agent:
    display_name: 烬🔥
    channel: [telegram]
    role: assistant
    authority:
      - notification
      - user_interaction
      - report
```

## 2. 身份来源链

```text
入口 (shell / webchat / telegram)
 ↓
Channel Binding (config.bindings[])
   main ← default (no binding match)
   tg-agent ← match: { channel: telegram }
 ↓
Agent Identity (config.agents.<id>.identity.name)
   main      → 燃🔥
   tg-agent  → 烬🔥
 ↓
运行时使用
```

### 注入方式

```yaml
# openclaw.json 配置（生效层）
agents:
  main:
    identity:
      name: 燃🔥
      emoji: 🔥
  tg-agent:
    identity:
      name: 烬🔥
      emoji: 🔥

# 绑定（路由层）
bindings:
  - agentId: tg-agent
    match:
      channel: telegram
```

## 3. 身份越界防护

| 入口 | 允许 | 禁止 |
|------|------|------|
| shell | system_observation, maintenance_operation | 用户数据通知 |
| webchat | system_observation, maintenance_operation | TG 消息推送 |
| telegram | notification, user_interaction, report | 运行时修改 |

## 4. 架构约束

### Runtime 限制

OpenClaw runtime 身份解析流程（`assistant-identity.ts`）：

```
P0: cfg.ui.assistant (全局 UI 配置)
P1: cfg.agents.<id>.identity (agent 配置)
P2: workspace/IDENTITY.md (文件级别)
```

- **Embedded (local) 模式**：单 agent（main），bindings 不生效。所有通道共享 燃🔥 身份。
- **Gateway 模式**：bindings 生效，telegram 路由至 tg-agent（烬🔥），其余默认路由至 main（燃🔥）。

### Fallback 策略

```text
未知入口
 ↓
默认 agent: main
 ↓
身份: 燃🔥
```

不再将 telegram 身份作为全局 fallback。

## 5. 关联文档

- `IDENTITY.md` — 身份显示名称 / 入口-身份映射表
- `IDENTITY-RULES.md` — 职责边界约定
- `openclaw.json` — agents 配置（生效层）
- `TOOLS.md` — 架构建设规范

## 6. 身份解析验证方法

```bash
# 检查当前运行时 agent identity
openclaw agent identity

# 检查 bindings 配置
openclaw agent list --bindings

# 检查 gateway 模式
openclaw status | grep mode
```

## 7. 本契约不覆盖

- 加密认证
- 运行时权限校验
- 多节点分发
