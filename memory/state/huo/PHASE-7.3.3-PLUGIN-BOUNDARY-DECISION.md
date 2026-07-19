# Phase 7.3.3 — Plugin Boundary Decision

**Phase 7.3 — Bypass Closure**
**Date:** 2026-07-19
**前置条件:**
- Phase 7.1 Audit Contract 🔒 FROZEN
- Phase 7.2 Boundary Matrix 🔒 FROZEN
- Phase 7.3.1 Bypass Register ✅ COMPLETE (15 paths)
- Phase 7.3.2 Gap Decision Framework ✅ COMPLETE (龙哥确认)
- Phase 6.1-6.4 🔒 FROZEN

---

## §0 定位

### 为什么需要 Plugin Boundary Decision

```
Phase 7.3.2 治理评审后, 15 条 bypass 中 4 条共享同一个根因:

  4 条 bypass = Plugin internal execution path
  B1-BP2: Plugin → Gateway  bypass
  B2-BP2: Plugin → Policy   bypass
  B4-BP2: Plugin → Projection bypass
  B5-BP2: Plugin → Event    bypass

核心问题:
  不归 Runtime Kernel 管
  不在 Runtime Governance 范围

当前决定:
  不要继续扩大 Runtime Kernel 去"覆盖" Plugin 路径
  而是建立 Plugin Execution Contract
```

### Phase 7.3.3 的定位

```
❌ 不是 Runtime Integrity 的扩展
❌ 不是 Plugin SDK 的实现
❌ 不是新的 Design Contract

✅ 是边界划定
   Plugin 的 Governance 归属在哪层?
   Runtime 与 Plugin 的 Trust Boundary 是什么?

输出:
  1. Plugin Governance Model (方案)
  2. 每条 Plugin bypass 的 Decision
```

### 约束

```
- Phase 6 不解冻
- 不修改 Plugin SDK 代码
- 不扩大 Runtime Kernel 治理范围
- 只分类 + 建议
- Decision → 龙哥确认后关闭 Phase 7.3
```

---

## §1 当前架构中的 Plugin 角色

### 1.1 Plugin 在哪里运行

```text
Runtime Kernel                    Plugin Layer
┌─────────────────────┐          ┌─────────────────────┐
│  agent-loop.js      │          │  plugins/tools.ts  │
│  tool-policy-       │          │  capability-        │
│  pipeline.ts        │          │  provider-runtime.ts│
│  attempt.ts          │          │  memory-state.ts   │
│  context-engine-    │          │  hooks.ts          │
│  lifecycle.ts       │          └─────────────────────┘
└─────────────────────┘                   │
         ↓                                ↓
  Plugin 注册工具                    Plugin 内部直接执行
  → 经 Runtime 治理                 → 不经 Runtime 治理
```

### 1.2 Plugin 的两种执行路径

```text
Path A: Plugin as Tool Provider (经 Runtime)
  Plugin registerTool
    ↓
  Runtime: tool-policy-pipeline → filterToolsByPolicy
    ↓
  LLM tool_call → agent-loop → prepareToolCall → execute
    ↓
  Runtime Event: runToolLifecycle → emit lifecycle events
    ↓
  ✅ 经 Runtime Governance

Path B: Plugin internal direct execute (不经 Runtime)
  Plugin internal logic
    ↓
  matchedTool.execute()  /  custom function
    ↓
  不在 agent-loop, 不在 policy pipeline, 不在 event path
    ↓
  ❌ 不经 Runtime Governance
  绕过: B1-BP2, B2-BP2, B4-BP2, B5-BP2
```

### 1.3 Plugin 的 Trust Boundary

```text
Plugin === 受信任扩展

当前假设:
  Plugin 是可信代码
  Plugin 开发者被授权使用 Runtime 核心功能

但:
  可信 ≠ 不受约束
  授权 ≠ 不需要 Governance

问题:
  Plugin 的"可信"边界在哪里?
  - 可以直接调用 tool.execute()?
  - 可以直接替换 systemPrompt?
  - 可以不产生 Event?
```

---

## §2 Plugin 治理模型方案

### 模型 A: 完全独立 (Plugin SDK 自治)

```text
Plugin 在自己的 Trust Boundary 内:
  - 自由调用 execute()
  - 自由组装 Context
  - 自由决定 Event 产出

Runtime 不干预 Plugin 内部执行

治理责任:
  Plugin SDK 自行提供:
    - tool 执行约束
    - context 管理
    - event 记录
  Runtime 不检查 Plugin 内部路径

Bypass 状态:
  B1-BP2 → ACCEPTED_GAP (Plugin 自治)
  B2-BP2 → ACCEPTED_GAP (Plugin 自治)
  B4-BP2 → ACCEPTED_GAP (Plugin 自治)
  B5-BP2 → ACCEPTED_GAP (Plugin 自治)

优点:
  - 干净边界
  - 不扩大 Runtime Kernel
  - Plugin 独立演化

代价:
  - Plugin 内部执行不受 Runtime 约束
  - 安全隐患由 Plugin SDK 负责
  - Event coverage 有缺口
```

### 模型 B: 契约自治 (Plugin Execution Contract)

```text
Plugin 在自身 Trust Boundary 内
但自愿遵守一份 Plugin Execution Contract:

Contract 声明:
  [1] Plugin tool execution 至少需满足:
        - tool 注册时声明策略 (policy intent)
        - 执行时内部记录 (local event)
  [2] Plugin context 组装:
        - 若使用 Context Engine, 声明替换意图
        - 不在 Projection 路径上绕过
  [3] Plugin event:
        - 关键执行产生 event
        - event 格式兼容 Runtime Event Schema

Runtime 不强制:
  - 不拦截 Plugin 内部 execute
  - 不检查 Plugin 是否遵守 Contract

但:
  - Plugin 声明遵守 Contract = 接受可审计
  - 发现违反 = 被视为 Plugin 缺陷, 非 Runtime 问题

Bypass 状态:
  B1-BP2 → ACCEPTED_GAP (契约自治)
  B2-BP2 → ACCEPTED_GAP (契约自治)
  B4-BP2 → ACCEPTED_GAP (契约自治)
  B5-BP2 → ACCEPTED_GAP (契约自治)

优点:
  - 不扩大 Runtime Kernel
  - Plugin 有自愿约束
  - 审计时有 Contract 作为参照

代价:
  - 自愿 ≠ 必须
  - 依赖 Plugin 开发者遵守
  - 审计发现违反时处置权在 Plugin 不在 Runtime
```

### 模型 C: 硬绑定 (Plugin 纳入 Runtime Governance)

```text
Plugin 内部执行也归 Runtime 管:
  - Plugin tool execute → 经 Gateway
  - Plugin context → 经 Projection
  - Plugin execution → 产生标准 Event

修改范围:
  - Plugin SDK: execute() 改为经 Gateway 路由
  - Context Engine: Plugin context 也经 Projection
  - Event: Plugin 执行路径注入 lifecycle

Bypass 状态:
  B1-BP2 → REQUIRE_CHANGE
  B2-BP2 → REQUIRE_CHANGE
  B4-BP2 → REQUIRE_CHANGE
  B5-BP2 → REQUIRE_CHANGE

优点:
  - 统一的 Governance 层
  - 无 bypass 缺口
  - Event 覆盖无盲区

代价:
  - 扩大 Runtime Kernel 范围
  - Plugin 开发者受 Runtime 约束
  - 修改 Plugin SDK = Phase 6 范围扩展
```

---

## §3 模型对比

| 维度 | 模型 A: 完全独立 | 模型 B: 契约自治 | 模型 C: 硬绑定 |
|:---|:---:|:---:|:---:|
| Runtime Kernel 范围 | 不变 | 不变 | **扩大** |
| Plugin 自由度 | **最高** | 中 | 最低 |
| Governance 覆盖率 | 最低 | 中 (自愿) | **最高** |
| Event 覆盖率 | 缺口 | 自愿覆盖 | **全覆盖** |
| 安全性 | Plugin 自管 | Plugin 负责 | Runtime 管 |
| 实现成本 | 0 | Contract 文档 | SDK 修改 + Kernel 扩展 |
| Phase 6 依赖 | 无 | 无 | **解冻** |
| Bypass 判定 | ACCEPTED_GAP | ACCEPTED_GAP | REQUIRE_CHANGE |

### 推荐: 模型 B — 契约自治

```
理由:
  1. 龙哥确认: Plugin 有自己的 Trust Boundary
     不应继续扩大 Runtime Kernel

  2. 模型 C 需要 Phase 6 解冻
     当前不解冻

  3. 模型 A 完全放任
     有安全隐患, 且审计时无参照

  4. 模型 B 居中:
     - 不扩大 Runtime
     - Plugin 有 Contract 约束
     - 审计时 Contract 为参考标准
     - 未来可升级 (模型 B → 模型 C 需要建 Contract + 实现)
```

---

## §4 Plugin Execution Contract v1 (草案)

### 4.1 Contract 结构

```
Plugin Execution Contract

Scope:
  适用于所有 Plugin 内部直接执行的路径
  (不在 agent-loop, 不在 policy pipeline, 不在 lifecycle event 路径)

Clauses:
  [PEC-01] Tool Execution Declaration
  [PEC-02] Context Integrity
  [PEC-03] Event Observability
  [PEC-04] Audit Compliance

Severity:
  MUST / SHOULD / MAY
```

### 4.2 PEC-01: Tool Execution Declaration

```
Clause:
  Plugin 内部直接调用 tool.execute() 时,
  SHOULD 提供执行声明 (execution declaration)
  说明: 调用的 tool, 传入的参数, 执行的时间

Severity: SHOULD

理由:
  - 不是强制执行, 是 Plugin 自管范围
  - 但声明支持后续审计
  - 不声明意味着该执行不可审计

实现方式:
  - Plugin SDK 提供 optional `declareExecution(toolId, params)`
  - 不强制调用
  - 调用后产生 local event, 不注入 Runtime event stream
```

### 4.3 PEC-02: Context Integrity

```
Clause:
  Plugin 通过 Context Engine 替换 systemPrompt 时,
  MUST 声明替换意图 (context replacement declaration)
  SHOULD 保持 Context Projection 的格式兼容

Severity: MUST (声明) / SHOULD (格式兼容)

理由:
  - Context Engine Plugin 的设计意图就是允许自定义 context
  - 但替换后, Plugin 负责 context 的正确性
  - 声明意图 = 谁替换的, 为什么替换, 替换了什么

实现方式:
  - Context Engine Plugin 已有 lifecycle hooks
  - 在替换 systemPrompt 时, Plugin SHOULD 记录:
    { action: "replace", reason: "...", originalSize, replacedSize }
```

### 4.4 PEC-03: Event Observability

```
Clause:
  Plugin 内部执行的关键操作
  SHOULD 产生对应的 Observability Event
  格式 SHOULD 与 Runtime Event Schema 兼容

Severity: SHOULD

理由:
  - Event 覆盖全部执行路径是理想状态
  - 但 Plugin 内部路径不由 Runtime 控制
  - Plugin 开发者应自行选择 Event 覆盖策略

实现方式:
  - Plugin SDK 提供 `emitPluginEvent(type, data)` helper
  - Event 流向 Plugin 事件流 (独立于 Runtime event stream)
  - Plugin 事件流可被 Runtime Event System 订阅
```

### 4.5 PEC-04: Audit Compliance

```
Clause:
  Plugin Execution Contract 的遵守情况
  SHOULD 可审计 (auditable)
  Plugin 提供:
    - execution 日志
    - context 替换记录
    - event 产出记录

Severity: SHOULD

理由:
  - Contract 的价值在于可审计
  - Plugin 不遵守 ≠ Runtime 的问题
  - 审计时通过 Contract 评估 Plugin 质量
```

### 4.6 Contract 状态

| Clause | Severity | 当前状态 |
|:---|:---:|:---|
| PEC-01 Tool Execution Declaration | SHOULD | 不存在 |
| PEC-02 Context Integrity | MUST (声明) / SHOULD (格式) | 部分存在 (Context Engine 已记录) |
| PEC-03 Event Observability | SHOULD | 部分存在 (Plugin SDK 无标准 helper) |
| PEC-04 Audit Compliance | SHOULD | 不存在 |

---

## §5 Plugin Bypass 决策建议 (基于模型 B)

| Bypass | 分类 | 建议 Decision | Contract 覆盖 |
|:---|---:|:---|:---|
| B1-BP2 Plugin → Gateway direct execute | ⚠️ BYPASSABLE | 🟢 **ACCEPTED_GAP (Contract 自治)** | PEC-01 |
| B2-BP2 Plugin → Policy direct execute | ⚠️ BYPASSABLE | 🟢 **ACCEPTED_GAP (Contract 自治)** | PEC-01 |
| B4-BP2 Plugin → Projection context replace | ⚠️ BYPASSABLE | 🟢 **ACCEPTED_GAP (Contract 自治)** | PEC-02 |
| B5-BP2 Plugin → Event no coverage | ⚠️ BYPASSABLE | 🟢 **ACCEPTED_GAP (Contract 自治)** | PEC-03 |

### 建议理由

```text
1. 龙哥确认: Plugin 有自己的 Trust Boundary
   → 不应扩大 Runtime Kernel

2. 模型 B 提供了 Governance 框架
   → 不强制, 但可审计

3. 当前不解冻 Phase 6
   → 模型 C 需要解冻, 不可行

4. 4 条 Plugin bypass 共享根因
   → 不单独处理, 统一用 Plugin Execution Contract 覆盖

5. Contract 是"可升级"的
   → 模型 B → 模型 C 需要: Contract + Plugin SDK 实现
   → 但不影响当前 Phase
```

---

## §6 影响分析

### 6.1 对 Phase 6 Contract 的影响

| Contract | 影响 |
|:---|:---|
| Phase 6.2 Capability Registry | 不受影响. Plugin tool 注册仍经 Registry |
| Phase 6.3 Context Projection | Plugin 替换 context 被标记为 Contract 自治, 不纳入 Runtime Projection 范围 |
| Phase 6.4 Tool Call Gateway | Plugin direct execute 标记为 ACCEPTED_GAP. Gateway 范围限定于 LLM → Runtime 路径 |

### 6.2 对 Bypass Register 的更新

```text
B1-BP2:  PENDING → ACCEPTED_GAP (Plugin Execution Contract)
B2-BP2:  PENDING → ACCEPTED_GAP (Plugin Execution Contract)
B4-BP2:  PENDING → ACCEPTED_GAP (Plugin Execution Contract)
B5-BP2:  PENDING → ACCEPTED_GAP (Plugin Execution Contract)
```

### 6.3 最终 Bypass Register 快照

| ID | Decision | 归属 |
|:---|---:|:---|
| B1-BP1 | DEFERRED_TO_PHASE | Phase 6.4 Future Revision |
| B1-BP2 | ACCEPTED_GAP | Plugin Execution Contract |
| B2-BP1 | REQUIRE_CHANGE | Phase 7.x Boundary Hardening |
| B2-BP2 | ACCEPTED_GAP | Plugin Execution Contract |
| B2-BP3 | DEFERRED | Execution Gateway |
| B3-BP1 | DEFERRED_TO_PHASE | Phase 6.2 Future Revision |
| B3-BP2 | ACCEPTED_GAP | 运行时固有缺口 |
| B3-BP3 | DEFERRED_TO_PHASE | Phase 6.2 Future Revision |
| B4-BP1 | DEFERRED_TO_PHASE | Phase 6.3 Future Revision |
| B4-BP2 | ACCEPTED_GAP | Plugin Execution Contract |
| B4-BP3 | DEFERRED | Projection 实现后集成 |
| B5-BP1 | DEFERRED | 统一执行入口 |
| B5-BP2 | ACCEPTED_GAP | Plugin Execution Contract |
| B5-BP3 | ACCEPTED_GAP | Event = Observer |
| B5-BP4 | DEPENDENCY_GAP | 等待 Gateway/Projection |

---

## §7 下一步

### 7.1 当前 Phase 7.3 总体状态

| Stage | 产出 | 状态 |
|:---|---:|:---:|
| 7.3.1 | Bypass Register v1.0 | ✅ COMPLETE |
| 7.3.2 | Gap Decision Framework | ✅ COMPLETE (龙哥确认) |
| **7.3.3** | **Plugin Boundary Decision** | **⬅️ CURRENT** |
| 7.3.4 | Phase 7.3 Finalize | PENDING |

### 7.2 等待龙哥确认

```text
1. Plugin 治理模型选择:
   模型 A (完全独立)
   模型 B (契约自治)  ← 推荐
   模型 C (硬绑定)

2. 如果选模型 B:
   Plugin Execution Contract 草案是否可接受?
   是否需要调整 Contract 条款?

3. 确认后: Phase 7.3 进入 Finalize 阶段
   输出: Phase 7.3 Closure Report
   状态: Phase 7.3 COMPLETE
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Phase 7.3.3 Plugin Boundary Decision — 3 个模型, Plugin Execution Contract 草案 |
