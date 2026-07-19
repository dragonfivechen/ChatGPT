# Phase 7.3.2 — Gap Decision Framework

**Phase 7.3 — Bypass Closure**
**Date:** 2026-07-19
**前置条件:**
- Phase 7.1 Audit Contract 🔒 FROZEN
- Phase 7.2 Boundary Matrix 🔒 FROZEN
- Phase 7.3 Stage 1: Bypass Register v1.0 ✅ COMPLETE

---

## §0 核心规则

### 规则 0.1 — Gap classification ≠ Implementation requirement

```
MISSING:
  不代表"必须立即实现"
  只代表"Enforcement Point 在源码中不存在"

BYPASSABLE:
  不代表"必须关闭"
  只代表"绕过路径存在且可达"
```

### 规则 0.2 — Decision 先于 Action

```
Bypass Found
  ↓
Gap Classification (Phase 7.3.1)
  ↓
Decision (Phase 7.3.2)        ← 此处
  ↓
Action Phase (Phase 7.4+)
```

### 规则 0.3 — 每个 bypass path 有且只有一个 Decision State

```
互斥: 一条 bypass path 不能同时是 ACCEPTED_GAP 和 REQUIRE_CHANGE
终局: Decision 一旦设定, 进入该 gap 的治理轨道
可逆: 只有新的 Architecture Phase 可以重新评估 Decision
```

---

## §1 Decision State 定义

### 1.1 五态

| State | 含义 | 触发条件 | 后续行为 |
|:---|:---|:---|:---|
| **PENDING** | 待决策 | 初始状态, 未评审 | 等待治理评审 |
| **ACCEPTED_GAP** | 已知设计限制, 不修复 | 绕过路径在架构设计中被归类为"可接受的设计边界" | 记录到架构知识库, 标记为已知缺口 |
| **DEFERRED** | 后续 Phase 修复 | 绕过路径需要修复, 但不在当前 Phase 范围 | 进入下一 Architecture Phase 的 scope |
| **REQUIRE_CHANGE** | 当前层需要修正 | 绕过路径直接破坏 Phase 6 Contract 的强制执行 | 归属 Owner 负责规划修正方案 |
| **OUT_OF_SCOPE** | 不属于 Runtime Integrity | 绕过路径不在 Phase 6/7 的设计覆盖范围内 | 记录但退出轨道 |

### 1.2 判定路径

```
Bypass Found
  ↓
Q1: 是否属于 Phase 6 Contract 覆盖范围?
  ├── NO  → OUT_OF_SCOPE
  └── YES → Q2

Q2: 绕过路径是否允许在当前架构层存在?
  ├── YES → ACCEPTED_GAP (设计边界内有原因)
  └── NO  → Q3

Q3: 修复是否属于当前 Phase 7 范围?
  ├── YES → REQUIRE_CHANGE
  └── NO  → DEFERRED (排入后续 Phase)
```

### 1.3 判定约束

```
ACCEPTED_GAP 判定必须附:
  - 架构理由: 为什么这个 bypass 是允许的
  - 风险等级: LOW / MEDIUM / HIGH
  - 影响域: 安全 / 正确性 / 可审计性 / 一致性

DEFERRED 判定必须附:
  - 排期 Phase: 哪个 Phase 处理
  - 前提条件: 什么条件达成后可以关闭

REQUIRE_CHANGE 判定必须附:
  - Owner: 哪个模块负责
  - 优先级: CRITICAL / HIGH / MEDIUM
  - 依赖: 修复是否依赖其他 Phase 解冻

OUT_OF_SCOPE 判定必须附:
  - 理由: 为什么不属于 Phase 6/7 范围
  - 归属: 属于哪个架构层的决策边界
```

---

## §2 决策矩阵 — B1 Plugin → Gateway

### 2.1 B1-BP1: agent-loop.js direct execute

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B1-BP1 |
| **Classification** | 🟥 MISSING |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.4 G-001: Gateway 是 LLM tool call 统一入口
     direct execute 路径直接违反该不变量

Q2: 允许存在?
  → NO. Gateway 设计目的是拦截 + 决策 + 执行
     direct execute 使 Gateway 设计失效

Q3: 当前 Phase 7 修复?
  → Phase 7 定位是 Verification + Hardening, 不是实现设计层
     Gateway 的实现属于 Phase 6.4 的解冻范围
  → ⚠️ REQUIRE_CHANGE 但依赖 Phase 6.4 解冻

建议判定:
  REQUIRE_CHANGE (归属 Phase 6.4)
  优先级: CRITICAL
```

### 2.2 B1-BP2: Plugin internal direct execute

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B1-BP2 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Extension Boundary (Phase 1) 允许 Plugin 调用 Runtime API
     但 Phase 6.4 要求所有 tool call 经 Gateway

Q2: 允许存在?
  → 取决于架构策略:
     方案 A: Plugin tool 也经 Gateway → 不可接受 bypass
     方案 B: Plugin tool 是独立路径, 由 Plugin SDK 自行负责 → 可接受
  这需要架构决策: Plugin tool 是否应纳入 Gateway 范围

建议判定:
  PENDING — 需要架构策略决策:
    Plugin tool 是否应纳入 Gateway scope?
    如果纳入 → REQUIRE_CHANGE
    如果独立 → ACCEPTED_GAP
```

---

## §3 决策矩阵 — B2 Worker → Policy

### 3.1 B2-BP1: Cross-agent spawn bypass

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B2-BP1 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.2 §3: Capability Enforcement 覆盖 Runtime 所有入口

Q2: 允许存在?
  → Spawned agent 的 tool policy 继承当前是个设计选择:
     继承 parent policy = 限制 spawn 能力
     独立 policy = spawn 自建范围
  当前: SPAWN_TOOLS 在 pipeline 过滤前就已确定
  → 这是设计缺陷, 不是正确的设计选择

Q3: 当前 Phase 7 修复?
  → 修复属于 Governance Kernel (Policy) 的调整范围
  若新增 spawn-time policy 继承检查, 不涉及 Phase 6 解冻

建议判定:
  REQUIRE_CHANGE (High)
  归属: Governance Kernel
  修复范围: spawn 时应用 parent policy 约束
  不依赖 Phase 6 解冻
```

### 3.2 B2-BP2: Plugin internal direct execute

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B2-BP2 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Policy 应覆盖所有具体执行入口

Q2: 允许存在?
  → 同 B1-BP2: 取决于 Plugin tool 是否应纳入 policy 范围
  当前 Plugin 直接 execute() 不在任何 policy 路径

建议判定:
  PENDING — 与 B1-BP2 的架构决策绑定
  是否要求所有 Plugin tool 经 policy pipeline?
```

### 3.3 B2-BP3: Registration-time only (temporal gap)

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B2-BP3 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Policy Enforcement 应是持续生效, 不是一次性

Q2: 允许存在?
  → 当前架构: tool 注册时 filter 一次, 后续无 re-check
     这意味着:
       - 注册后 policy 变更不生效
       - 工具注册后行为不受 policy 约束
  → 这是时态缺口, 不是架构选择

Q3: 当前 Phase 7 修复?
  → 执行时 policy re-check 可以作为一个 hook 点加入
     不涉及 Phase 6 解冻

建议判定:
  DEFERRED (MEDIUM)
  归属: Governance Kernel
  排期: Phase 8+
  前提: Gateway 实现后, policy check 可集成到 Gateway 决策层
  竞合: 如果 Gateway 实现, 这个 gap 自然闭合
```

---

## §4 决策矩阵 — B3 Capability → Registry

### 4.1 B3-BP1: Plugin direct registration to Runtime Resolver

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B3-BP1 |
| **Classification** | 🟥 MISSING |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.2 §2 CR-01: Registry 是 Capability 唯一权威来源
     Plugin 直接注册到 Runtime Resolver 绕过 Registry

Q2: 允许存在?
  → NO. Registry 设计的核心就是权威来源
     绕过 Registry = 绕过整个 Phase 6.2 契约

Q3: 当前 Phase 7 修复?
  → 涉及 Registry ↔ Runtime Resolver 的同步机制
     需要修改 capability-provider-runtime.ts 的注册路径
  这属于 Phase 6.2 的实现范围, 需要解冻 Phase 6.2

建议判定:
  REQUIRE_CHANGE (CRITICAL)
  归属: Capability Registry
  依赖: Phase 6.2 解冻
  修复: Registry 成为 Runtime Resolver 的唯一上游
```

### 4.2 B3-BP2: Creation-time check ≠ Execution-time guarantee

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B3-BP2 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🟢 **ACCEPTED_GAP (建议)** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Registry 设计应保证 capability 可用性

Q2: 允许存在?
  → 创建时检查 vs 执行时保证 — 这是所有声明式系统的固有缺口
     无法在注册时保证执行时可用 (auth 过期, 网络不通等)
     这是操作性 gap, 不是架构性 gap
  → 在 Registry 契约中, 保证"声明可用"和"执行可用"是两回事

建议判定:
  ACCEPTED_GAP
  风险: LOW
  理由: 执行时可用性是运行时问题, 不是 Registry 契约的验证范围
  Runtime 层的错误处理机制 (认证刷新, 重试, failover) 应处理这个 gap
```

### 4.3 B3-BP3: Registry ↔ Runtime desync (no sync bridge)

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B3-BP3 |
| **Classification** | 🟥 MISSING |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. CR-02/CR-03 要求 Registry 与 Runtime 一致

Q2: 允许存在?
  → NO. Registry 与 Runtime 可分歧意味着:
     - Registry 说"有 capability"但 Runtime 说"没有" → 工具创建成功但执行失败
     - Registry 说"没有"但 Runtime 有 → 能力未声明但可执行
  这两种情况都破坏 Phase 6.2 契约

Q3: 当前 Phase 7 修复?
  → 需要同步机制: Registry ↔ Runtime Resolver 之间建立一致性
     这涉及 capability-provider-runtime.ts 的修改
  属于 Phase 6.2 的解冻范围

建议判定:
  REQUIRE_CHANGE (CRITICAL)
  归属: Capability Registry
  依赖: Phase 6.2 解冻
  与 B3-BP1 关联修复
```

---

## §5 决策矩阵 — B4 Context → Projection

### 5.1 B4-BP1: Direct system prompt assembly

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B4-BP1 |
| **Classification** | 🟥 MISSING |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.3 CP-01: Projection 是 Context 唯一合法构造路径
     当前: system prompt 直接组装, 0 行 Projection 代码

Q2: 允许存在?
  → NO. Projection 设计在 Phase 6.3 被冻结
     0 行实现意味着 Contract 只存活在文档层

Q3: 当前 Phase 7 修复?
  → 实现 Projection layer 是 Phase 6.3 的解冻范围
     Phase 7 不实现设计层

建议判定:
  REQUIRE_CHANGE
  归属: Context Projection Layer
  依赖: Phase 6.3 解冻
  优先级: CRITICAL — 无 Projection 时 Phase 6.3 契约不成立
```

### 5.2 B4-BP2: Context Engine Plugin replacement

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B4-BP2 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. 所有 Context 进入 LLM 的路径应经 Projection

Q2: 允许存在?
  → Context Engine Plugin 的设计意图就是允许自定义 context 组装
     如果 Projection 实现后, Plugin 仍可绕过 Projection 直接替换 systemPrompt
     → 这是 Plugin SDK 能力与 Governance 约束的冲突

  需要架构决策:
    方案 A: Plugin context 替换也经 Projection 层
    方案 B: Plugin context 替换是独立路径, 由 Plugin 自行负责一致性

建议判定:
  PENDING — 需要架构策略决策
  Plugin Context Engine 的定位: 是替代 Projection 还是投影后的自定义层?
```

### 5.3 B4-BP3: Direct memory injection

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B4-BP3 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Memory 是 Context 的生产者, 应经 Projection

Q2: 允许存在?
  → 如果 Projection 层实现后, memory injection 应该改为经 Projection
     当前 memory 直接读文件 → 追加到 systemPrompt → LLM
     → 这是集成缺口, 不是设计决策

Q3: 当前 Phase 7 修复?
  → 内存入 Projection 路径依赖于 Projection 层的实现
     在 Projection 实现前, 无法"修复" memory bypass

建议判定:
  DEFERRED — 依赖于 B4-BP1 的修复
  归属: Context Projection Layer
  前提: Projection runtime 实现后, memory 集成到 Projection 路径
```

---

## §6 决策矩阵 — B5 Event → Truth

### 6.1 B5-BP1: Direct tool execute — no lifecycle event

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B5-BP1 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.4 R-04: Event = Truth

Q2: 允许存在?
  → 当前: agent-loop.js 的直接 execute 不产生事件
     这是 agent-loop.js 的实现选择: 它不包装 runToolLifecycle
  → 原则上: B1-BP1 修复 (Gateway 实现) 后, agent-loop execute 路径消失
     → B5-BP1 随 B1-BP1 自然闭合

建议判定:
  DEFERRED — 随 B1-BP1 (Gateway 实现) 自然闭合
  不单独修复
  验证条件: Gateway 实现后, 确认所有 agent-loop execute 经事件路径
```

### 6.2 B5-BP2: Plugin internal execute — no event at all

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B5-BP2 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🔴 **PENDING** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. 所有 Runtime 执行应有 event 记录

Q2: 允许存在?
  → 同 B1-BP2: 取决于 Plugin tool 是否纳入 Gateway/Event 范围
  如果 Plugin tool 不纳入 Gateway, 则 event 覆盖也需要独立决策

建议判定:
  PENDING — 与 B1-BP2 的架构决策绑定
  Plugin tool 的 Event 覆盖是 Plugin SDK 的责任还是 Runtime 事件系统的责任?
```

### 6.3 B5-BP3: Fire-and-forget — no truth verification

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B5-BP3 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🟢 **ACCEPTED_GAP (建议)** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Event = Truth 要求事件可验证

Q2: 允许存在?
  → 当前 Event 系统的定位是 Observer / Telemetry Layer
     不是 Execution Truth Authority
  → 引入 Event 验证机制 (数据签名 / 时序验证 / 来源绑定)
     在当前架构层是合理的增强
  → 但这改变了 Event System 的角色: 从观察者 → 权威记录
  这是一个升级, 不是 bug 修复

Q3: 当前 Phase 7 修复?
  → Phase 7 定位是 Verification + Hardening
     引入 event 真实性验证可以归属于 Hardening
  → 但需要 Event Kernel 的扩展, 变更较大

建议判定:
  ACCEPTED_GAP (当前架构层)
  → 当前 Event System 观察者角色是可接受的
  → 如果未来 Event 升级为 Truth Authority, 再解决验证问题
  风险: MEDIUM — 缺少可验证的事件链, 但当前运行路径已有事件覆盖 (主路径)
```

### 6.4 B5-BP4: Phase 6 event schemas not emitted

| 字段 | 值 |
|:---|:---|
| **Bypass ID** | B5-BP4 |
| **Classification** | ⚠️ BYPASSABLE |
| **Decision State** | 🟢 **ACCEPTED_GAP (建议)** |
| **判定分析** | |

```
Q1: Phase 6 Contract 覆盖?
  → YES. Phase 6.3.2 设计文档要求:
     每次 projection → 1 projection_event
     每次 Gateway decision → 1 gateway_decision_event

Q2: 允许存在?
  → Phase 6.3/6.4 的 event schema 是设计层产物
     Runtime 未 emit 是因为 Projection 和 Gateway 都没有实现
     → Schema 存在但 emit 不存在 = 上游层未实现
  → 这本身就是 design contract 和 runtime 之间的 gap
     但 gap 的原因在于 Projection/Gateway 本身未实现

建议判定:
  ACCEPTED_GAP
  风险: LOW
  理由: Schema event 未 emit 的原因是上游层 (Projection/Gateway) 未实现
  当 Projection 和 Gateway 实现后, 这些 schema 才进入 emit 路径
  不应在 Projection/Gateway 不存在时单独要求 emit
```

---

## §7 决策矩阵汇总

### 7.1 最终建议

| ID | Bypass | 建议 Decision | 归属 | 依赖 / 前提 |
|:---|:---|:---:|:---|:---|
| B1-BP1 | agent-loop direct execute | 🟢 DEFERRED_TO_PHASE | Phase 6.4 Future Revision | Gateway intercept 缺失, 不立即解冻 |
| B1-BP2 | Plugin internal execute | 🟡 PENDING → PHASE 7.3.3 | Plugin Governance | Plugin Execution Contract, 不归入 Runtime Kernel |
| B2-BP1 | Cross-agent spawn bypass | 🟢 REQUIRE_CHANGE | Phase 7.x Boundary Hardening | Worker Identity → Policy Scope → Execution Authority, 可独立处理 |
| B2-BP2 | Plugin internal policy bypass | 🟡 PENDING → PHASE 7.3.3 | Plugin Governance | Plugin Execution Contract 范围 |
| B2-BP3 | Registration-time only | 🟢 DEFERRED | Governance Kernel | 依赖 Execution Gateway |
| B3-BP1 | Registry bypass direct register | 🟢 DEFERRED_TO_PHASE | Phase 6.2 Future Revision | Registry Declaration ≠ Runtime Authority, 不解冻 |
| B3-BP2 | Creation ≠ Execution guarantee | 🟢 ACCEPTED_GAP | — | 声明阶段 ≠ 运行阶段, 运行时事实 |
| B3-BP3 | Registry ↔ Runtime desync | 🟢 DEFERRED_TO_PHASE | Phase 6.2 Future Revision | Declared Capability ≠ Available Runtime Capability, 不解冻 |
| B4-BP1 | Direct system prompt assembly | 🟢 DEFERRED_TO_PHASE | Phase 6.3 Future Revision | Context Assembly → LLM 缺少 Projection Boundary, 不解冻 |
| B4-BP2 | Plugin context replacement | PENDING | 架构决策 | 需决定 Plugin context 定位 |
| B4-BP3 | Direct memory injection | 🟢 DEFERRED | Context Projection | 依赖 Projection 实现后集成 |
| B5-BP1 | Direct execute no lifecycle event | 🟢 DEFERRED | Event Kernel | 依赖统一执行入口 |
| B5-BP2 | Plugin execute no event | 🟡 PENDING → PHASE 7.3.3 | Plugin Governance | Plugin Execution Contract 范围 |
| B5-BP3 | Fire-and-forget no verification | 🟢 ACCEPTED_GAP | — | Event = Observer (Telemetry), 非 Truth Authority |
| B5-BP4 | Phase 6 schema events not emitted | 🟢 DEPENDENCY_GAP | — | Schema exists, Runtime producer absent, 等待 Gateway/Projection |

### 7.2 统计 (治理评审后)

| Decision | 数量 | 分布 |
|:---|---:|:---|
| **DEFERRED_TO_PHASE** | 4 | B1-BP1, B3-BP1, B3-BP3, B4-BP1 |
| **REQUIRE_CHANGE** | 1 | B2-BP1 |
| **ACCEPTED_GAP** | 2 | B3-BP2, B5-BP3 |
| **DEPENDENCY_GAP** | 1 | B5-BP4 |
| **DEFERRED** | 3 | B2-BP3, B4-BP3, B5-BP1 |
| **PENDING → PHASE 7.3.3** | 4 | B1-BP2, B2-BP2, B4-BP2, B5-BP2 |

### 7.3 决策依赖图 (治理评审后)

```
DEFERRED_TO_PHASE (4 items):
  B1-BP1 (Gateway intercept)     → Phase 6.4 Future Revision (不解冻)
  B3-BP1 (Registry bypass)       → Phase 6.2 Future Revision (不解冻)
  B3-BP3 (Registry↔Runtime sync) → Phase 6.2 Future Revision (不解冻)
  B4-BP1 (Projection missing)    → Phase 6.3 Future Revision (不解冻)

REQUIRE_CHANGE (1 item):
  B2-BP1 (Cross-agent spawn)     → Phase 7.x Boundary Hardening (独立处理)

DEFERRED (3 items):
  B2-BP3 (Temporal policy)       → 依赖 Execution Gateway
  B4-BP3 (Memory direct)         → 依赖 Projection 实现
  B5-BP1 (No lifecycle event)    → 依赖统一执行入口

ACCEPTED_GAP (2 items):
  B3-BP2 (Register ≠ Execute)    → 运行时固有 gap
  B5-BP3 (No verification)       → Event = Observer (Telemetry), 非 Truth Authority

DEPENDENCY_GAP (1 item):
  B5-BP4 (Schema not emitted)    → Schema exists, Runtime producer absent
                                  等待 Gateway/Projection

PHASE 7.3.3 (4 items) — Plugin Boundary Decision:
  B1-BP2 / B2-BP2 / B4-BP2 / B5-BP2
  → Plugin internal execution path
  → 不归入 Runtime Kernel
  → 需要 Plugin Execution Contract
```

---

## §8 治理决策记录

### 8.1 龙哥决策摘要

```
A. REQUIRE_CHANGE (5) → 调整:
  B1-BP1 Gateway intercept    → DEFERRED_TO_PHASE (Phase 6.4 Future Revision)
  B2-BP1 Cross-agent spawn    → 保持 REQUIRE_CHANGE (Phase 7.x 独立处理)
  B3-BP1 Registry bypass      → DEFERRED_TO_PHASE (Phase 6.2 Future Revision)
  B3-BP3 Registry↔Runtime     → DEFERRED_TO_PHASE (Phase 6.2 Future Revision)
  B4-BP1 Projection missing   → DEFERRED_TO_PHASE (Phase 6.3 Future Revision)

B. ACCEPTED_GAP (3) → 调整:
  B3-BP2 Creation ≠ Execution → ACCEPTED_GAP ✅
  B5-BP3 Fire-and-forget      → ACCEPTED_GAP ✅ (Event = Observer, 非 Truth Authority)
  B5-BP4 Schema not emitted   → DEPENDENCY_GAP (Schema exists, 等待上游)

C. DEFERRED (3) → 保持:
  B2-BP3 Temporal policy      → DEFERRED
  B4-BP3 Memory direct        → DEFERRED
  B5-BP1 No lifecycle event   → DEFERRED

D. PENDING Plugin (4) → Phase 7.3.3:
  B1-BP2 / B2-BP2 / B4-BP2 / B5-BP2
  → Plugin internal execution path
  → 不归入 Runtime Kernel
  → 建立 Plugin Execution Contract
```

### 8.2 不解冻确认

```
Phase 6 各子模块 = 🔒 FROZEN (拒绝自动解冻)

B1-BP1 (Gateway)  → Phase 6.4 Future Revision
B3-BP1 (Registry) → Phase 6.2 Future Revision
B3-BP3 (Registry) → Phase 6.2 Future Revision
B4-BP1 (Project)  → Phase 6.3 Future Revision
```

### 8.3 独立修复确认

```
B2-BP1 (Cross-agent spawn)
  → 不需要解冻 Phase 6
  → 属于 Worker Governance
  → 归属 Phase 7.x Boundary Hardening
```

---

## §9 下一步指向

| Phase | 定位 | 状态 |
|:---|:---|---:|
| Phase 7.3.3 | Plugin Boundary Decision | 🆕 NEXT |

剩余 4 条 Plugin 类 bypass (B1-BP2, B2-BP2, B4-BP2, B5-BP2) 共享根因:
- Plugin internal execution path
- 不在 Runtime Kernel 治理范围
- 需要独立的 Plugin Execution Contract

```
Phase 7.3.2 → 治理决策完成 → Phase 7.3.3 Plugin Boundary Decision
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Phase 7.3.2 Gap Decision Framework — 15 gap 决策建议 |
