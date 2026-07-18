# OpenClaw Architecture Governance Layer v1.0
## System Blueprint — TG Model Edition

**Version:** v1.0 · **Status:** Frozen  
**Purpose:** 架构认知基线，供 TG 交互模型（烬🔥）理解系统边界与治理层

---

## 1. 整体架构

```
 User / External Interaction
          │
          ▼
  ┌─────────────────────┐
  │    Channel Layer    │
  └────────┬────────────┘
           │
           ▼
  ┌─────────────────────────────────────┐
  │          OpenClaw Runtime           │
  │                                     │
  │  Gateway · Agent · Plugin · Tool    │
  │  Session · Channel                  │
  └──────────────┬──────────────────────┘
                 │
          API / Event Boundary
                 │
                 ▼
  ┌─────────────────────────────────────┐
  │         External Worker Domain      │
  │                                     │
  │  Billing · Token Observe · Future   │
  └─────────────────────────────────────┘
```

**核心原则：**
- **Runtime** — 负责在线交互与能力调度（systemd service）
- **External Worker** — 负责独立任务执行（systemd timer → oneshot worker）
- 两者通过明确接口通信，**不共享生命周期**

---

## 2. Extension Boundary

### Runtime Domain
| 组件 | 管理方式 | 职责 |
|------|----------|------|
| Gateway | systemd service | 请求路由、会话管理 |
| Agent | — | 交互调度 |
| Plugin | — | 能力扩展接口 |
| Tool | — | Agent 可用工具 |
| Session | — | 对话状态管理 |
| Channel | — | 外部通信接入 |

### External Worker Domain
| Worker | 触发器 | 职责 |
|--------|--------|------|
| billing-snapshot | 5min timer | 余额快照 + 日统计 |
| billing-push | 1h timer | 推送账单报告 |
| token-observe | 整点 | Token 用量观测 |
| future | — | 按需扩展 |

### Worker 约束
- ❌ 禁止注入 Gateway 生命周期
- ❌ 禁止修改 OpenClaw Core
- ❌ 禁止直接调用外部通知出口

### 通知统一出口
```
Worker → push-notify → push-gate → Telegram / External Service
```

---

## 3. Memory Governance

### Namespace 结构

```
memory/
├── state/       系统状态 · 契约 · 架构文档
├── events/      事件日志（append-only）
├── facts/       已确认事实（human confirmation only）
├── preferences/ 用户明确偏好
├── knowledge/   外部知识导入 · 版本可追踪
└── cache/       临时数据 · 可丢弃
```

### Namespace 责任

| 目录 | 性质 | 规则 |
|------|------|------|
| `state/` | 可更新 | 表示当前事实状态 |
| `events/` | append-only | 不修改历史，不删除 |
| `facts/` | 不可推论 | ❌ Model inference → facts ✅ Human confirmation → facts |
| `preferences/` | 用户驱动 | 来源：用户明确操作 |
| `knowledge/` | 来源明确 | 版本可追踪 |
| `cache/` | 可丢弃 | 不作为事实来源 |

### 身份隔离

| 身份 | 场景 | 记忆域 | 约束 |
|------|------|--------|------|
| **燃🔥** | 终端/系统维护 | `state/huo/` + `events/huo/` | 不读 `events/jin/` |
| **烬🔥** | TG 交互 | `events/jin/` | 不读 `state/huo/` + `events/huo/` |

---

## 4. Memory Writer Boundary

Memory 写入采用 **Writer 分类制**。当前 Writer 类型：

| Writer | 说明 |
|--------|------|
| Runtime Writer | 系统运行时写入 |
| Worker Writer | External Worker 写入 |
| Dreaming Writer | 保留 |
| User Confirm Writer | 用户确认后写入 facts |
| Import Writer | 外部导入知识 |
| Agent Request Writer | Agent 请求触发写入 |

**当前 Agent（烬🔥）权限：**
- ✅ `memory_search` · `memory_get` — 读取
- ❌ `memory_write` — 不存在此能力
- 结论：Agent **不直接改变 Memory 状态**

---

## 5. Plugin Capability Governance

### 能力模型链路

```
Capability → Capability Registry → Contract Declaration → Runtime Enforcement
```

### 能力类别

| 类别 | 包含 |
|------|------|
| **Runtime** | Tool · Hook · Service · Lifecycle |
| **Memory** | Embedding Provider · Memory Runtime |
| **Event** | Event Subscription |
| **External IO** | Web Fetch · Search |
| **Notification** | Channel |
| **Provider** | Model · Speech · Media |
| **Security** | Audit · Policy |

### 禁止规则

| 违规类型 | 说明 |
|----------|------|
| **Capability Escalation** | 插件不得用 A 能力偷偷获得 B 能力 |
| **Hidden Capability** | 未声明能力不得暴露 |
| **Transitive Leak** | 不得通过其他组件间接扩大权限 |

### 插件获取能力路径

```
Declared → Registered → Validated
```

---

## 6. Core Integrity Rule

**不可触碰的三条红线：**
1. ❌ 修改 OpenClaw Core
2. ❌ 修改 Replay 语义
3. ❌ 引入隐藏状态

所有扩展通过以下途径实现：
- Plugin API
- External Worker
- 预定义外部接口

---

## 7. Governance Status

| 治理域 | 状态 |
|--------|------|
| Extension Boundary | ✅ Frozen |
| Memory Governance | ✅ Frozen |
| Plugin Governance | ✅ Frozen |
| Core Integrity | ✅ Verified |

---

## 8. Controlled Extension Model

> 冻结的是架构边界，不是冻结功能。

当前系统处于 **受控扩展模式**：新能力可增加，但受 Governance Layer 约束。

### ✅ 允许增加的模块类型

#### 1. External Worker 模块（最安全）

已验证模式：
```
systemd timer → oneshot worker → push-notify / event
```

适用场景：
- 数据采集、报表生成、定时检查
- 外部 API 同步、监控任务
- 例：`market-monitor-worker` · `backup-worker` · `health-report-worker`

条件：
- 独立生命周期
- 不侵入 Gateway
- 不修改 Core
- 输出走标准出口（push-gate）

#### 2. Plugin Capability 扩展

流程：
```
需求 → Capability 分类 → Registry 登记 → Contract 声明 → 实现 → 运行验证
```

条件：
- 必须回答：属于哪个 Capability？谁拥有？风险等级？是否已有接口？
- ❌ 禁止绕过 Registry 直接注册能力

#### 3. Memory 内容扩展

可以增加内容，但**不能随意增加记忆类型**。

✅ 正确：`memory/knowledge/project-x/`
❌ 错误：`memory/project-x-memory/`（创造新 namespace）

当前 6 个命名空间 `state` `events` `facts` `preferences` `knowledge` `cache` 是语义边界，不可新增。

#### 4. Governance 文档扩展

可新增规范类文档，不破坏运行结构：
- `SECURITY-RUNBOOK.md`
- `BACKUP-CONTRACT.md`
- `INCIDENT-RESPONSE.md`

### 调度任务策略 — systemd timer vs OpenClaw Cron

#### ✅ 优先：External Worker（systemd timer + oneshot worker）

```
systemd timer → oneshot worker → 结果输出 → event / report / push-gate
```

适合：

| 类型 | 适合？|
|------|------|
| 系统健康检查 | ✅ |
| 备份检查 | ✅ |
| 数据采集 | ✅ |
| 报表生成 | ✅ |
| API 同步 | ✅ |
| 资源监控 | ✅ |
| 账单统计 | ✅ |

**原因：** 生命周期独立、失败隔离、不占 Gateway 上下文、不增加 Agent token 消耗、容易审计。

#### ⚠️ 谨慎：OpenClaw Cron

```
OpenClaw Cron → Agent Session → 执行任务
```

属于 **Runtime Capability**，不是 External Worker。风险：
- 消耗 session / context
- 影响运行态
- 增加 Agent 行为不确定性
- 审计边界变复杂

**不是不能用，而是需要明确理由。**

#### 判断标准

新增定时任务前问：

| 问题 | 走 systemd worker | 才考虑 Cron |
|------|-------------------|-------------|
| 需要模型推理吗？ | ❌ 不需要 | ✅ 需要 |
| 需要访问 Runtime 内部状态吗？ | ❌ 不需要 | ✅ 需要 |
| 产生 Memory？ | 必须经过 Writer Boundary | 必须经过 Writer Boundary |

#### 调度政策总结

```yaml
scheduler_policy:
  systemd_worker:
    allowed: true
    preferred: true

  openclaw_cron:
    allowed: true
    requires_reason: true

  hidden_scheduler:
    forbidden: true
```

简单说：**不是不能加定时任务，而是不建议把简单任务塞进 Agent 运行时。**

---

### ❌ 当前不建议增加的类型

| 类型 | 原因 |
|------|------|
| **Core 修改** | 除非 Extension Boundary 无法满足需求，否则不进入 |
| **新隐藏通道** | Worker 直呼 Telegram API / plugin 绕过 registry — 破坏已冻结的治理链 |

### 新模块准入检查表

| 问题 | 必须回答 |
|------|----------|
| 属于 Runtime 还是 Worker？ | ✅ |
| 属于哪个 Capability？ | ✅ |
| 是否需要 Memory 写权限？ | ✅ |
| Writer 是谁？ | ✅ |
| 数据生命周期？ | ✅ |
| 是否修改 Core？ | ❌ 必须否 |
| 是否有标准出口？ | ✅ |

### 当前发展方向

系统已从 **建设期** 进入 **能力增长期**：

```
External Worker
    +
Capability Registry
    +
Memory Governance
```

三个组合足够承载业务模块。方向是**小而独立的能力**，规则：
- 新功能 → 外挂优先
- 新能力 → Capability 注册
- 新数据 → Namespace 归属
- 新写入 → Writer 明确

---

## 9. 已知治理盲区 — Agent Capability Policy

### 当前状态

| 维度 | 现状 | 风险 |
|------|------|------|
| Agent 身份区分 | 记忆路径约定，非架构强制 | 无运行时隔离 |
| 工具集隔离 | 同一模型共享同一套工具 | 无能力分级 |
| 入口权限控制 | Telegram / TUI 无权限分级 | 无访问控制 |
| Capability 覆盖 | 仅 Plugin 层 | Agent/Model 层未覆盖 |

### 具体表现

当前 `agent:main` 下两个身份（燃🔥 / 烬🔥）：

- 同一个 agent
- 同一个模型（deepseek-v4-flash）
- 同一套工具集（exec / read / write / web_search 等）
- 隔离仅靠 `IDENTITY-RULES.md` 文本约束

### 缺失的治理层

如果要做到身份级能力分级（例如：
- 限制 TG 入口不能调 exec
- 区分 read-only 和 write 模式
- 不同身份不同工具集
），需要 **Agent Capability Policy** — 当前治理层尚未定义到这层。

### 当前缓解

靠记忆隔离 + 身份规则 + 人工审查。架构上暂无强制保障。

---

## 10. 当前阶段

```
Design → Implementation → Audit → Freeze → Observation
                                  ⬆ 当前：Observation Window
```

**观察目标：**
- 边界是否稳定
- Writer 是否可追踪
- Capability 是否可解释
- 是否出现治理漂移

---

## 最终原则

> OpenClaw 不是通过增加复杂度获得稳定。
> 而是通过：
> **明确边界 + 明确所有权 + 明确写入口 + 明确能力声明 + 持续证据验证**
> 保持系统可理解、可维护、可演进。
