# 系统架构里程碑

**最后更新:** 2026-07-19 09:24 CST
**当前状态:** Architecture Governance Layer v1.0 — FROZEN (观察期)
Phase 6 Runtime Intelligence Layer — COMPLETE (v1)

---

## Phase 1 — Extension Boundary v1.0 ✅ COMPLETE

| 项 | 状态 | 说明 |
|---|------|------|
| Runtime 注入路径关闭 | ✅ | NODE_OPTIONS 已移除，billing 独立运行 |
| External Worker 标准化 | ✅ | timer + oneshot 模型，无常驻 daemon |
| 通知出口统一 | ✅ | push-notify → push-gate 唯一出口 |
| crontab 清除 | ✅ | 零条目 |
| Secret 边界清理 | ✅ | 无脚本硬编码 token |

**源码校验:** systemd timer 正确（OpenClaw cron 是 Agent Workflow Scheduler 非 worker scheduler）、push-gate 独立保持正确（OpenClaw outbound 在 Runtime 内）、External Secret 后续优化。

---

## Phase 2 — Memory Semantic Namespace v1.0 ✅ COMPLETE

### Phase 2.1 — Directory Contract

```
memory/
├── state/huo/       当前系统状态（中期，可更新）
├── events/huo/      已发生记录（永久，append-only）
├── events/jin/      TG交互模型的事件记录
├── facts/           用户确认事实（永久，尚无写入）
├── preferences/     用户偏好（长期，尚无写入）
├── knowledge/       外部知识（长期，尚无写入）
└── cache/           临时信息（短期，尚无写入）
```

**验收:** memory root 语义化 ✅, agent 隔离保留 ✅, 无 SQLite 改动 ✅, 无 memory-core 修改 ✅

### Phase 2.2 — Ownership Contract

定稿于 `MEMORY-OWNERSHIP-CONTRACT.md`，Authority Order: Ownership Policy > Directory Namespace > Agent Namespace > Frontmatter Metadata

### Phase 2.3 — Writer Boundary

定稿于 `MEMORY-WRITER-BOUNDARY.md`，6 类 Writer 分类 + 8 Namespace 权限矩阵 + Writer Registry（已注册 5 个）、3 条禁止规则。

### Phase 2.4 — Metadata Contract

定稿于 `METADATA-CONTRACT.md`，定义 Identity/Provenance/Version/Lifecycle 四层描述，frontmatter 可选非强制。

---

## Phase 3 — Plugin Capability Governance ✅ COMPLETE

### Phase 3.1 — Capability Surface Audit

审计 OpenClaw Plugin API 暴露 50+ registerXxx 函数，覆盖 7 大能力域：runtime/memory/event/io/notification/provider/security。

### Phase 3.2 — Capability Contract

定稿于 `PLUGIN-CAPABILITY-CONTRACT.md`，定义能力命名空间 + 三层授权模型（Allowlist + Capability Grant + Enforcement）。

### Phase 3.3 — Capability Registry

定稿于 `CAPABILITY-REGISTRY.md`，20 项能力注册表 + 依赖展开规则 + 风险等级（low/medium/high）。

### Phase 3.4 — Enforcement Boundary Audit

源码验证：`registerTool` 已有 `contracts.tools` 检查作为 enforcement point。Enforcement Boundary 已自然存在于 `registry.ts`，无需新增。

---

## 架构层次状态

```
OpenClaw Architecture v3
├── Foundation Layer                 ✅ COMPLETE
├── Governance Layer                 ✅ COMPLETE
│   ├── Phase 1 Extension Boundary   ✅ COMPLETE
│   ├── Phase 2 Memory Governance    ✅ COMPLETE
│   └── Phase 3 Plugin Governance    ✅ COMPLETE
├── Security Layer                   ✅ COMPLETE
│   └── SecretRef Migration v1.0     🔒 FROZEN
└── Runtime Intelligence Layer       ✅ COMPLETE
    ├── Phase 6.1 Reasoning Isolation    🔒 FROZEN
    ├── Phase 6.2 Capability Registry    🔒 FROZEN
    ├── Phase 6.3 Context Projection     🔒 FROZEN
    └── Phase 6.4 Tool Call Gateway      🔒 FROZEN
```

### Phase 6 建设路线

```
Phase 6.1: Reasoning Isolation Contract   🔒 FROZEN
Phase 6.2: Provider Capability Registry   🔒 FROZEN
Phase 6.3: Context Projection Contract    🔒 FROZEN
Phase 6.4: Tool Call Gateway              🔒 FROZEN
```

### 运行中组件

| 服务 | 类型 | 生命周期管理 |
|------|------|-------------|
| openclaw-gateway | Runtime | systemd daemon |
| oek-billing-snapshot | External Worker | systemd timer (5min) + oneshot |
| oek-billing-push | External Worker | systemd timer (1h) + oneshot |
| oek-token-observe | External Worker | systemd timer (hourly) + oneshot |

### 治理层文档清单

```
state/huo/ARCHITECTURE.md                   系统里程碑总览
state/huo/MEMORY-OWNERSHIP-CONTRACT.md      所有权+生命周期规则（Phase 2.2）
state/huo/MEMORY-WRITER-BOUNDARY.md         Writer 分类+权限矩阵（Phase 2.3）
state/huo/METADATA-CONTRACT.md              Frontmatter 描述规范（Phase 2.4）
state/huo/PLUGIN-CAPABILITY-CONTRACT.md     能力命名空间+授权模型（Phase 3.2）
state/huo/CAPABILITY-REGISTRY.md            20 项能力注册表（Phase 3.3）
state/huo/REASONING-ISOLATION-CONTRACT.md   推理痕迹生命周期契约（Phase 6.1）
state/huo/PROVIDER-CAPABILITY-CONTRACT.md   Provider 能力声明与验证契约（Phase 6.2.1）
state/huo/provider-capability.schema.json   Provider 能力 Schema（Phase 6.2.1）
state/huo/PROVIDER-CAPABILITY-REGISTRY-DESIGN.md Registry v2 设计文档（Phase 6.2.2）
state/huo/provider-capability-registry.json  Provider 能力注册表数据（Phase 6.2.2）
state/huo/RUNTIME-ENFORCEMENT-DESIGN.md     Runtime Enforcement 决策设计（Phase 6.2.3）
state/huo/RUNTIME-ENFORCEMENT-VALIDATION.md  Enforcement 不变量验证（Phase 6.2.4）
state/huo/CONTEXT-PROJECTION-CONTRACT.md     Context Projection 契约（Phase 6.3）
state/huo/TOOL-CALL-GATEWAY-CONTRACT.md      Tool Call Gateway 契约（Phase 6.4）
state/huo/PHASE-6.4.1-SCHEMA-DESIGN.md       Tool Call Gateway Schema 设计（Phase 6.4.1）
state/huo/tool-call-request.schema.json       Tool Call Request Schema（Phase 6.4.1）
state/huo/gateway-decision.schema.json        Gateway Decision Schema（Phase 6.4.1）
state/huo/tool-call-event.schema.json         Tool Call Event Schema（Phase 6.4.1）
```

### Phase 6 — Runtime Intelligence Layer v1.0 ✅ ALL FROZEN

| 阶段 | 产出 | 状态 |
|:---|:---|:---:|
| 6.1 Reasoning Isolation Contract | REASONING-ISOLATION-CONTRACT.md (10 章节) | 🔒 FROZEN |
| 6.2.0 Provider Capability Audit | PHASE-6.2-AUDIT-REPORT.md (7 节) | 🔒 FROZEN |
| 6.2.1 Provider Capability Contract + Schema | PROVIDER-CAPABILITY-CONTRACT.md + schema.json + design/mapping docs | 🔒 FROZEN |
| 6.2.2 Registry v2 Design + Initialization | PROVIDER-CAPABILITY-REGISTRY-DESIGN.md + registry.json (6 capabilities, 4 models) | 🔒 FROZEN |
| 6.2.3 Runtime Enforcement Design | RUNTIME-ENFORCEMENT-DESIGN.md (8 章节) | 🔒 FROZEN |
| 6.2.4 Enforcement Validation | RUNTIME-ENFORCEMENT-VALIDATION.md (5 invariants × 24 scenarios) | 🔒 FROZEN |
| 6.3 Context Projection | CONTEXT-PROJECTION-CONTRACT.md + 3 schemas + PHASE-6.3.2/6.3.3 design + validation | 🔒 FROZEN |
| 6.4 Tool Call Gateway | TOOL-CALL-GATEWAY-CONTRACT.md + 3 schemas + PHASE-6.4.2 runtime design + 6.4.3 validation | 🔒 FROZEN |

**核心原则：** `LLM = Producer, Runtime = Executor, Governance = Judge, Event = Truth`

---

## 未完成项目 / 待定项

### 架构治理层（无紧迫性，等待运行证据驱动）

| 项 | 优先级 | 说明 |
|---|--------|------|
| Frontmatter metadata 推广使用 | 低 | Contract 已定义，frontmatter 可选，待观察是否需要强制 |
| Plugin Capability 分级 enforcement 实现 | 低 | Contract 和 Registry 已定义，源码已有 enforcement point，但无实现需求 |
| External Secret Interface 统一 | 低 | 当前 `.secrets/push-gate.json` 独立，后续可考虑接入 `src/secrets/` |
| Memory Writer Pipeline 微调 | 低 | dreaming 自动写入与 Writer Boundary 的对应关系需运行数据验证 |
| cron→systemd timer 全面迁移 | 已完成 | crontab 已清零 |

### 非架构维护项

| 项 | 状态 | 说明 |
|---|------|------|
| secret 文件权限 0600 | ✅ 已执行 | push-gate.json 0644 → 0600 |
| allowInsecureAuth 关闭 | ✅ 已执行 | gateway.controlUi.allowInsecureAuth false |
| 旧系统残留清理 | ✅ 已执行 | dpkg rc 清零、lottery service 清除、日志裁剪 |

### 未进入架构设计的领域

| 领域 | 说明 |
|------|------|
| Phase 4 Governance Validation | 观察期，以运行证据驱动，不新增抽象层 |
| Plugin Capability Runtime Enforcement 实现 | 暂不实现，当前可信环境无迫切需求 |
| Memory Semantic Namespace 的 Core 改动 | 零改源码原则，契约层已覆盖 |
| Phase 6.3 Provider Capability Runtime Detection | 设计完成（Enforcement），实际代码等待 Phase 7 |
| Phase 7 Runtime Integrity Verification | 待规划 Phase 7+ |
| Phase 7 Runtime Integrity Verification | 后续 Planning 阶段范围

---

## 后续衔接方向

### 如何接手

1. 阅读 `state/huo/` 下 6 份治理文档
2. 参考审计清单模板执行新一轮 Compliance Audit
3. 对比运行状态是否偏离已冻结边界
4. 出现以下情况才重新进入设计：新 Worker 无法归类 / Memory 出现无法追踪写入 / Plugin 能力越界 / 现有 Contract 无法表达新需求

### 核心原则

- 治理层不替代 OpenClaw 机制，只归类和固化已有边界
- 零改源码（现有 Contract 层全部为文档规范）
- 保持冻结直到运行证据证明现有模型不足
