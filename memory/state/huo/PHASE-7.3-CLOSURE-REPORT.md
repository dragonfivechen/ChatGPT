# PHASE-7.3-CLOSURE-REPORT.md

**Phase 7.3 — Bypass Closure**
**Date:** 2026-07-19
**Status:** ✅ COMPLETE

---

## §0 总览

### 0.1 Phase 7 全链路状态

| Phase | Stage | Status |
|:---|---:|:---:|
| Phase 6.1-6.4 | Design Contract Layer | 🔒 **FROZEN** |
| Phase 7.1 | Runtime Integrity Audit Contract | 🔒 **FROZEN** |
| Phase 7.2 | Boundary Enforcement Matrix (5/5 verified) | 🔒 **FROZEN** |
| Phase 7.3.1 | Bypass Register v1.0 (15 paths) | ✅ **COMPLETE** |
| Phase 7.3.2 | Gap Decision Framework | ✅ **COMPLETE** |
| Phase 7.3.3 | Plugin Boundary Decision | ✅ **COMPLETE** |
| **Phase 7.3** | **Closure Report** | **⬅️ CURRENT** |

### 0.2 Phase 7 的工作原则

```
Phase 7 ≠ 修复阶段

定位:
  Phase 6 = What we want (Design Contract)
  Phase 7 = What we have (Runtime Reality)

不执行:
  - 不修复缺口
  - 不解冻 Phase 6
  - 不实现 Gateway / Projection / Event Truth
  - 不修改 Phase 6 Contract
```

---

## §1 Boundary Verification Summary

### 1.1 验证结论

| Boundary | Owner | Status | Key Finding |
|:---|:---|---:|:---|
| **B1 Plugin → Gateway** | Tool Gateway | 🟥 MISSING + ⚠️ BYPASSABLE | Gateway.intercept() 不在 agent-loop 执行路径 |
| **B2 Worker → Policy** | Governance Kernel | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | 注册时过滤存在, 执行时 policy re-check 不存在 |
| **B3 Capability → Registry** | Capability Registry | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | Registry 是声明式 metadata, 不在执行路径 |
| **B4 Context → Projection** | Context Projection Layer | 🟡 DESIGN ONLY + 🟥 MISSING + ⚠️ BYPASSABLE | 0 行 Projection runtime 代码 |
| **B5 Event → Truth** | Event Kernel | 🟡 PARTIAL + 🟥 MISSING + ⚠️ BYPASSABLE | Event 是观察者层, 非 Truth Authority |

### 1.2 验证方法

```
所有边界通过源码 call-graph trace 验证
证据分布:
  - agent-loop.js         (B1/B2/B5)
  - plugins/tools.ts      (B1/B2/B5)
  - tool-policy-pipeline.ts (B2)
  - subagent-spawn.ts     (B2)
  - provider-capability-registry.ts (B3)
  - provider-registry.ts  (B3)
  - system-prompt.ts      (B4)
  - memory-state.ts       (B4)
  - attempt.ts            (B4/B5)
  - agent-events.ts       (B5)
  - diagnostic-events.ts  (B5)
  - pi-embedded-subscribe.ts (B5)
```

---

## §2 Bypass Classification Final

### 2.1 15 条 bypass paths 最终判定

| # | ID | Boundary | 分类 | Decision State |
|:---:|:---|---|:---:|:---|
| 1 | B1-BP1 | B1 Plugin → Gateway | 🟥 MISSING | 🟢 DEFERRED_TO_PHASE (Phase 6.4 Future Revision) |
| 2 | B1-BP2 | B1 Plugin → Gateway | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP (Plugin Execution Contract PEC-01) |
| 3 | B2-BP1 | B2 Worker → Policy | ⚠️ BYPASSABLE | 🟢 REQUIRE_CHANGE (Phase 7.x Boundary Hardening) |
| 4 | B2-BP2 | B2 Worker → Policy | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP (Plugin Execution Contract PEC-01) |
| 5 | B2-BP3 | B2 Worker → Policy | ⚠️ BYPASSABLE | 🟢 DEFERRED |
| 6 | B3-BP1 | B3 Capability → Registry | 🟥 MISSING | 🟢 DEFERRED_TO_PHASE (Phase 6.2 Future Revision) |
| 7 | B3-BP2 | B3 Capability → Registry | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP |
| 8 | B3-BP3 | B3 Capability → Registry | 🟥 MISSING | 🟢 DEFERRED_TO_PHASE (Phase 6.2 Future Revision) |
| 9 | B4-BP1 | B4 Context → Projection | 🟥 MISSING | 🟢 DEFERRED_TO_PHASE (Phase 6.3 Future Revision) |
| 10 | B4-BP2 | B4 Context → Projection | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP (Plugin Execution Contract PEC-02) |
| 11 | B4-BP3 | B4 Context → Projection | ⚠️ BYPASSABLE | 🟢 DEFERRED |
| 12 | B5-BP1 | B5 Event → Truth | ⚠️ BYPASSABLE | 🟢 DEFERRED |
| 13 | B5-BP2 | B5 Event → Truth | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP (Plugin Execution Contract PEC-03) |
| 14 | B5-BP3 | B5 Event → Truth | ⚠️ BYPASSABLE | 🟢 ACCEPTED_GAP (Event = Observer) |
| 15 | B5-BP4 | B5 Event → Truth | ⚠️ BYPASSABLE | 🟢 DEPENDENCY_GAP |

### 2.2 决策分布

```
DEFERRED_TO_PHASE (4):   等待未来 Phase 修复, 不解冻
  B1-BP1 → Phase 6.4
  B3-BP1 → Phase 6.2
  B3-BP3 → Phase 6.2
  B4-BP1 → Phase 6.3

REQUIRE_CHANGE (1):      可独立修复
  B2-BP1 → Phase 7.x Boundary Hardening

ACCEPTED_GAP (7):        接受, 不修复
  B1-BP2 / B2-BP2 (Plugin PEC-01)
  B3-BP2 (运行时固有缺口)
  B4-BP2 (Plugin PEC-02)
  B5-BP2 (Plugin PEC-03)
  B5-BP3 (Event = Observer)

DEFERRED (3):            等待关联组件
  B2-BP3 (Execution Gateway)
  B4-BP3 (Projection)
  B5-BP1 (统一执行入口)

DEPENDENCY_GAP (1):      等待上游
  B5-BP4 (Gateway / Projection)
```

---

## §3 Accepted Gap Register

```yaml
B1-BP2: Plugin → Gateway direct execute
  Decision: ACCEPTED_GAP
  Grounds: Plugin 在自己的 Trust Boundary 内执行
           Plugin Execution Contract PEC-01 负责声明机制
  Risk: LOW (Plugin 可信, 不扩大 Runtime Kernel)

B2-BP2: Plugin → Policy direct execute
  Decision: ACCEPTED_GAP
  Grounds: 同 B1-BP2 机制
           Plugin 内部路径不纳入 Policy 范围
  Risk: LOW

B3-BP2: Creation-time check ≠ Execution-time guarantee
  Decision: ACCEPTED_GAP
  Grounds: 这是所有声明式系统的固有缺口
           注册时无法保证执行时可用 (auth 过期, 网络不通)
           运行时错误处理机制应处理此 gap
  Risk: LOW

B4-BP2: Context Engine Plugin replacement
  Decision: ACCEPTED_GAP
  Grounds: Plugin Context Engine = Plugin-owned extension boundary
           必须遵守 PEC-02: 声明替换意图
           不可声称 Plugin context == Runtime Truth
  Risk: MEDIUM (依赖 PEC-02 声明遵守)

B5-BP2: Plugin execute no event
  Decision: ACCEPTED_GAP
  Grounds: Plugin 内部执行不在 Runtime Event stream 范围内
           PEC-03 要求 Plugin 自行产生 observability signal
           Plugin event ≠ Runtime Truth Event
  Risk: LOW

B5-BP3: Fire-and-forget, no truth verification
  Decision: ACCEPTED_GAP
  Grounds: 当前 Event System 定位 = Observer / Telemetry
           不是 Truth Authority
           接受: Event = Observer
  Risk: MEDIUM (缺少可验证事件链, 但主路径有覆盖)

B5-BP4: Phase 6 event schemas not emitted
  Decision: DEPENDENCY_GAP (not permanent ACCEPTED_GAP)
  Grounds: Schema exists. Runtime producer absent.
           非事件系统本身问题
           等待 Gateway / Projection 实现后进入 emit 路径
  Risk: LOW
```

---

## §4 Deferred Gap Register

```yaml
B2-BP3: Registration-time only (temporal policy gap)
  Decision: DEFERRED
  Dependency: Execution Gateway
  Condition: Gateway 实现后可自然在决策层集成 policy re-check

B4-BP3: Direct memory injection
  Decision: DEFERRED
  Dependency: Context Projection Layer
  Condition: Projection 实现后, memory 集成到 Projection 路径

B5-BP1: Direct tool execute — no lifecycle event
  Decision: DEFERRED
  Dependency: Unified execution entry (Gateway)
  Condition: B1-BP1 修复 (Gateway) 后, agent-loop execute 路径消失
             不再需要单独修复 event coverage
```

---

## §5 Future Phase Dependency Map

### 5.1 依赖关系

```
Phase 6.2 Future Revision (B3-BP1, B3-BP3)
  ↑ Registry → Runtime sync mechanism
  ↑ Capability Authority consistency

Phase 6.3 Future Revision (B4-BP1, B4-BP3)
  ↑ Context Projection runtime implementation
  ↑ Memory integration into Projection

Phase 6.4 Future Revision (B1-BP1, B2-BP3, B5-BP1)
  ↑ Gateway intercept in agent-loop execution path
  ↑ Policy re-check at execution time
  ↑ Unified lifecycle event coverage

Phase 7.x Boundary Hardening (B2-BP1)
  ↑ Cross-agent spawn policy enforcement
  ← 可独立处理, 不依赖 Phase 6 解冻

Plugin Execution Contract (B1-BP2, B2-BP2, B4-BP2, B5-BP2)
  ↑ Self-governance contract (4 PEC clauses)
  ← 当前为 ACCEPTED_GAP, 无需解冻
```

### 5.2 依赖无环

```text
验证: 无循环依赖

Phase 6.2 → 独立 (Registry sync)
Phase 6.3 → 独立 (Projection)
Phase 6.4 → 独立 (Gateway)
Phase 7.x → 独立 (Worker Governance)
Plugin PEC → 独立 (自管契约)
```

---

## §6 No-Unlock Confirmation

### 6.1 Phase 6 解冻拒绝确认

```
Phase 6.1 Reasoning Isolation          → 🔒 FROZEN (不涉及)
Phase 6.2 Capability Registry          → 🔒 FROZEN (拒绝解冻)
Phase 6.3 Context Projection           → 🔒 FROZEN (拒绝解冻)
Phase 6.4 Tool Call Gateway            → 🔒 FROZEN (拒绝解冻)
```

### 6.2 理由

```yaml
Phase 6.2:
  B3-BP1: Registry bypass
    → DEFERRED_TO_PHASE, 不解冻
    → Registry 结构应保留, 修复等 Future Revision

Phase 6.3:
  B4-BP1: Projection missing
    → DEFERRED_TO_PHASE, 不解冻
    → Projection 是设计层, Phase 7 不实现

Phase 6.4:
  B1-BP1: Gateway intercept missing
    → DEFERRED_TO_PHASE, 不解冻
    → Gateway 不进入 Phase 7
```

### 6.3 独立修复

```yaml
B2-BP1: Cross-agent spawn
  → 唯一 REQUIRE_CHANGE
  → 不需要 Phase 6 解冻
  → 属于 Worker Governance
  → 归属 Phase 7.x Boundary Hardening
```

---

## §7 Plugin Execution Contract

### 7.1 Contract Status

| Clause | Severity | Status |
|:---|---:|:---:|
| PEC-01 Tool Execution Declaration | SHOULD | ✅ Accepted as governance contract |
| PEC-02 Context Integrity | MUST declare / SHOULD format | ✅ Accepted |
| PEC-03 Event Observability | SHOULD | ✅ Accepted |
| PEC-04 Audit Compliance | SHOULD | ✅ Accepted |

### 7.2 Contract 属性

```
Contract 类型: Self-Governance Contract
不是: Runtime Enforcement Layer

定位:
  Plugin 声明:
    I follow PEC
  Runtime 不强制 Plugin 内部实现
  Audit 检查时, Contract 为评估依据

边界:
  Plugin event ≠ Runtime Truth Event
  Plugin context ≠ Runtime Truth
  Plugin execution ≠ Runtime-governed execution
```

---

## §8 最终决策矩阵

```
                        设计层 (Phase 6)        运行时层 (Phase 7)
                        ─────────────────       ─────────────────
B1 Plugin → Gateway     Gateway Design          Gateway MISSING
                        🔒 FROZEN               → 2 bypass paths
                                                 ↓ DEFERRED_TO_PHASE
                                                 ↓ Plugin PEC

B2 Worker → Policy      Policy Contract         PARTIAL + MISSING
                        🔒 FROZEN               → 3 bypass paths
                                                 ↓ REQUIRE_CHANGE (Phase 7.x)
                                                 ↓ Plugin PEC
                                                 ↓ DEFERRED

B3 Capability → Registry Registry Design        PARTIAL + MISSING
                        🔒 FROZEN               → 3 bypass paths
                                                 ↓ DEFERRED_TO_PHASE (Phase 6.2)
                                                 ↓ ACCEPTED_GAP

B4 Context → Projection Projection Design       DESIGN ONLY + MISSING
                        🔒 FROZEN               → 3 bypass paths
                                                 ↓ DEFERRED_TO_PHASE (Phase 6.3)
                                                 ↓ Plugin PEC
                                                 ↓ DEFERRED

B5 Event → Truth        Event Truth Contract    PARTIAL + MISSING
                        🔒 FROZEN               → 4 bypass paths
                                                 ↓ DEFERRED
                                                 ↓ Plugin PEC
                                                 ↓ ACCEPTED_GAP
                                                 ↓ DEPENDENCY_GAP
```

---

## §9 Phase 7 切换

### 9.1 Phase 7 当前状态

```
Phase 7.1 Audit Contract     🔒 FROZEN
Phase 7.2 Boundary Matrix    🔒 FROZEN
Phase 7.3 Bypass Closure     ✅ COMPLETE
```

### 9.2 Phase 7.4 入口

```
Phase 7.4: Runtime Verification
定位: 验证实际运行时行为是否符合 Phase 7 的发现
输入:
  - Phase 7.1 Audit Contract (验证契约)
  - Phase 7.2 Boundary Matrix (边界定义)
  - Phase 7.3 Closure Report (绕过路径 + 决策)

原则:
  - 不修复
  - 不解冻 Phase 6
  - 确认 Phase 7 发现的可复现性
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Phase 7.3 Closure Report — 15 bypass paths final classification, accepted/deferred registers, future phase maps, no-unlock confirmation |
