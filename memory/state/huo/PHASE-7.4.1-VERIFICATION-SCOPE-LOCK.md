# Phase 7.4.1 — Verification Scope Lock

**Phase 7.4 — Runtime Verification**
**Date:** 2026-07-19
**前置条件:**
- Phase 7.3 🔒 CLOSED

---

## §0 Phase 7.4 定位

### 0.1 不是重复 Phase 7.2

```
Phase 7.2:  What can bypass?
  → 验证边界是否存在
  → 输出: Boundary Reality (MISSING / BYPASSABLE)

Phase 7.3:  How should bypass be governed?
  → 分类 + 决策
  → 输出: Decision State (DEFERRED_TO_PHASE / ACCEPTED_GAP / etc.)

Phase 7.4:  After governance classification,
            does Runtime actual behavior
            match accepted/deferred/requires states?
  → 验证治理分类后的运行时一致性
  → 输出: PASS / FAIL per verification target
```

### 0.2 约束

```
- 不是发现新的缺口
  Phase 7.2 已完成: 15 条 bypass paths, 不会再增加

- 不是修复
  同 Phase 7.2/7.3 原则: 只验证, 不修复

- 不是重复 Phase 6 设计验证
  Phase 6 不解冻, 不评估设计正确性

- 验证的是:
  治理决策后的运行时实际行为

- 验证对象:
  每条 bypass path 对应的 Runtime Path

  验证:
  - ACCEPTED_GAP: 是否运行时保持"被绕过" = 一致
  - DEFERRED: 是否运行时保持"绕过但等待" = 一致
  - DEFERRED_TO_PHASE: 是否运行时保持"绕过且不出错误" = 一致
  - REQUIRE_CHANGE: 是否运行时存在 "绕过导致异常" = 可能需确认
  - DEPENDENCY_GAP: 是否运行时行为 = 预期

  确定: 不是引入新分类, 而是验证分类是否匹配当前运行时行为。
```

### 0.3 范围锁定规则

```
纳入:
  每条 bypass path 的 Runtime 实际执行路径
  验证 Decision State 与运行时行为的一致性

不纳入:
  Phase 6 Contract 正确性
  Design-level ideality
  新的 bypass 发现
  Gateway / Projection / Event Truth 实现评估

出口条件:
  每条 bypass path 至少一条 Runtime Trace
  验证:
    trace 结果 ↔ Decision State 一致
  不要求:
    所有路径 FULL COVERAGE
    代码级别覆盖率报告
```

---

## §1 验证范围

### 1.1 验证目标分布

| Category | Count | 验证要求 |
|:---|---:|:---|
| DEFERRED_TO_PHASE | 4 | 确认 bypass 路径运行时存在, 且当前不影响核心功能 |
| REQUIRE_CHANGE | 1 | 确认 bypass 路径存在, 且造成可观测的 policy 偏差 |
| ACCEPTED_GAP | 7 | 确认 bypass 路径可被触发, 行为符合预期 |
| DEPENDENCY_GAP | 1 | 确认 schema 未 emit, 行为符合等待状态 |
| DEFERRED | 3 | 确认 bypass 路径存在, 且不影响主执行路径 |

### 1.2 不需要重新验证的路径

```
以下路径已在 Phase 7.2 通过源码 trace 验证,
Phase 7.4 只做运行时快照确认, 不重复源码审计:

B1-BP1: agent-loop.js direct execute
  → 源码已确认 Gateway.intercept() 不在路径
  → Runtime 验证: 确认 tool.execute() 不产生 Gateway decision event

B1-BP2: Plugin internal direct execute
  → 源码已确认 plugins/tools.ts direct execute
  → Runtime 验证: 确认 Plugin tool call 不在 agent-loop 日志中

B2-BP1: Cross-agent spawn
  → 源码已确认 subagent-spawn.ts bypass
  → Runtime 验证: 确认 spawned agent 可访问 parent 未授权的工具

B2-BP2: Plugin internal policy bypass
  → 同 B1-BP2 路径
  → Runtime 验证: 确认 Plugin internal tool call 无 policy filter 日志

B2-BP3: Temporal policy gap
  → 源码已确认 registration-time only
  → Runtime 验证: 确认执行时 policy 不重新检查

B3-BP1: Registry bypass
  → 源码已确认 resolvePluginCapabilityProviders 路径
  → Runtime 验证: 确认 Plugin capability 不产生 Registry 验证日志

B3-BP2: Creation ≠ Execution
  → 源码已确认
  → Runtime 验证: 无需; 这是语义 gap, 无法通过运行时观测

B3-BP3: Registry ↔ Runtime desync
  → 源码已确认两条独立路径
  → Runtime 验证: 确认 Registry 声明与 Runtime Resolver 的 provider 列表不一致

B4-BP1: Direct system prompt
  → 源码已确认 buildAgentSystemPrompt 路径
  → Runtime 验证: 确认 systemPrompt 不经过 Projection 层

B4-BP2: Context Engine Plugin
  → 源码已确认 Plugin 可直接替换 systemPrompt
  → Runtime 验证: 确认 Context Engine Plugin 返回的 context 不是 Projection 格式

B4-BP3: Direct memory injection
  → 源码已确认 buildMemoryPromptSection 路径
  → Runtime 验证: 确认 MEMORY.md 内容注入时不经过 Projection

B5-BP1: Direct tool execute — no lifecycle event
  → 源码已确认 agent-loop execute 路径
  → Runtime 验证: 确认 agent-loop.js execute 路径不产生 lifecycle 事件

B5-BP2: Plugin internal — no event
  → 源码已确认 plugins/tools.ts 无 event emit
  → Runtime 验证: 确认 Plugin internal execute 没有任何事件记录

B5-BP3: Fire-and-forget — no verification
  → 源码已确认 notifyListeners fire-and-forget
  → Runtime 验证: 确认 emitAgentEvent 后无人确认

B5-BP4: Schema not emitted
  → 源码已确认 0 处 emit
  → Runtime 验证: 确认当前事件输出不包含 Phase 6 schema 类型的 event
```

---

## §2 验证格式

### 2.1 每条验证输出格式

```yaml
Target: <Bypass ID> - <path description>
Category: <DEFERRED_TO_PHASE | REQUIRE_CHANGE | ACCEPTED_GAP | DEPENDENCY_GAP | DEFERRED>
Expected: <运行时预期的行为>
Method: <验证方法 - 日志追踪 / 事件观察 / 行为快照>
Result: PASS | FAIL
Evidence: <运行时证据>
```

### 2.2 PASS Criteria

```
PASS 条件:
  运行时行为与 Decision State 描述一致

  例如:
  - ACCEPTED_GAP: bypass 路径确实可触发 (non-blocked)
  - DEFERRED: bypass 路径存在, 不影响核心执行流
  - DEFERRED_TO_PHASE: bypass 路径存在, Phase 6 Contract 未生效
  - REQUIRE_CHANGE: bypass 路径的可观测影响符合预期 (存在偏差)
  - DEPENDENCY_GAP: 相关 schema 未被 emit

FAIL 条件:
  运行时行为与 Decision State 不一致

  例如:
  - ACCEPTED_GAP: 实际被阻断 (不应发生, 因定义为接受)
  - DEFERRED: 实际导致可观测错误 (deferred 应为"可等待")
  - REQUIRE_CHANGE: 实际无偏差 (说明分类过度)
  - DEPENDENCY_GAP: schema 已被 emit (说明缺口已闭)
```

---

## §3 验证顺序

### 3.1 阶段: 日志追踪流 (B1-BP1, B5-BP1, B5-BP2)

```
方法:
  触发一次 LLM tool call
  追踪 agent-loop.js 日志输出
  确认:
    tool.execute() 路径 → 无 Gateway.intercept() 日志
    agent-loop.js 路径 → 无 lifecycle event 日志
    Plugin tool call 路径 → 无 event 日志

工具:
  openclaw 日志 / process log
  运行时 stdout / stderr
```

### 3.2 阶段: 行为快照 (B2-BP1, B3-BP3, B4-BP2)

```
方法:
  确认 cross-agent spawn policy scope discrepancy
  确认 Registry ↔ Runtime provider list 不匹配
  确认 Context Engine Plugin 可产生非 Projection 格式 context

工具:
  openclaw spawn 测试
  Registry dump vs Runtime provider list 对比
  Context Engine Plugin 输出采样
```

### 3.3 阶段: Event 观察 (B5-BP3, B5-BP4)

```
方法:
  触发 agent-loop 执行
  观察事件流输出
  确认:
    事件 fire-and-forget, 无回读确认
    事件类型中无 Phase 6 schema 事件

工具:
  openclaw events / transcript 观察
  Event schema 匹配
```

### 3.4 阶段: 存在性确认 (其余 bypass)

```
方法:
  确认 bypass 路径可到达
  确认当前不影响核心功能
  不需要详尽的量化数据

工具:
  一致性检查
  Runtime 行为观察
```

---

## §4 不验证清单

```yaml
以下排除在 Phase 7.4 之外:

B3-BP2: Creation ≠ Execution
  理由: 语义 gap, 无法通过运行时观测
  这是声明式系统的固有属性
  运行时无法证明"注册时可用, 执行时不可用"
  此 gap 在 B3-BP3 验证中隐含覆盖

Phase 6 Contract 正确性:
  理由: Phase 6 🔒 FROZEN, 不解冻
  不评估设计正确性

Gateway / Projection / Event Truth 实现:
  理由: 不存在, 无需验证

新的 bypass 路径:
  理由: Phase 7.2 已完成发现
  Phase 7.4 不是重复发现阶段
```

---

## §5 验证执行入口

### 5.1 第一阶段: 日志追踪优先

```
建议从 B1-BP1 / B5-BP1 开始:
  这两个 bypass 路径共享 agent-loop.js 执行路径
  一次 LLM tool call 可同时验证:
    - Gateway 缺失 (B1-BP1)
    - Lifecycle event 缺失 (B5-BP1)
  高效覆盖 2 条路径
```

### 5.2 第二阶段: Plugin 路径验证

```
B1-BP2 / B2-BP2 / B4-BP2 / B5-BP2
  共享 Plugin internal execution 根因
  一条 Plugin 执行可验证 4 条 path
```

### 5.3 第三阶段: 独立路径验证

```
剩余路径没有共享执行上下文
  需要独立触发
  但验证成本较低 (存在性确认)
```

---

## §6 等待确认

```
1. Scope Lock 是否接受?
   Phase 7.4 验证范围: 15 条 bypass paths 的运行时一致性
   不包含: 新的缺口发现 / Phase 6 设计评估

2. 验证方法是否合理?
   日志追踪 + 行为快照 + Event 观察 + 存在性确认
   不需要代码级别覆盖

3. 执行顺序:
   Stage 1: 日志追踪 (B1-BP1, B5-BP1, B5-BP2)
   Stage 2: Plugin 路径 (B1-BP2, B2-BP2, B4-BP2, B5-BP2)
   Stage 3: 独立路径 (剩余)

4. 确认后进入 Phase 7.4.2 Runtime Verification Execution
```

---

## §7 Verification Governance Rules

### 7.1 No Reclassification During Verification

```
7.4 只回答:
  Observed == Decision?

不回答:
  Decision correct?

如果发现 Decision ≠ Runtime:
  记录: Verification FAIL
  原因: <observed mismatch>
  返回: 治理层 (龙哥)

验证结果 ≠ 决策更新
```

### 7.2 Evidence 优先级

| Priority | Type | Source |
|:---|---:|:---|
| **Primary** | Runtime trace | 实时执行日志 / stdout / stderr |
| **Secondary** | Snapshot / source reference | 配置状态 / 源码引用 |
| **Supporting** | Event observation | Event 输出 (注意: Event = Observer, 不可反向作为唯一真实性证明) |

### 7.3 PASS/FAIL 严格定义

```
PASS:
  Observed runtime behavior == Decision State description

FAIL:
  Observed runtime behavior != Decision State description

FAIL 不触发:
  - 自动重新分类
  - 修复决策
  - Phase 6 解冻

FAIL 触发:
  - 记录证据
  - 返回治理层
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:---|
| v1.0 | 2026-07-19 | Phase 7.4.1 Verification Scope Lock — 范围定义, 验证格式, PASS/FAIL 条件, 执行顺序 |
| v1.1 | 2026-07-19 | 补充 §7 Verification Governance Rules (No Reclassification, Evidence Priority) |
