# Phase 7.1 Runtime Integrity Audit Contract v1.0 — 🔒 FROZEN

```yaml
contract:
  name: PHASE-7.1-AUDIT-CONTRACT
  version: v1.0
  level: L1
  type: audit_verification
  parent: FREEZE-CONTRACT
  scope: phase contract verification
  owner: 燃🔥
  status: frozen
  created: 2026-07-19
```

**Phase 7**
**Date:** 2026-07-19
**Status:** FINAL
**前置条件:** Phase 6 所有契约已冻结 (6.1~6.4)

---

## §0 定位

### Phase 7 是什么

```
Phase 7 不是新架构设计。
Phase 7 是验证层。

Phase 6: 定义系统应该如何运行。     ← DONE / FROZEN
Phase 7: 证明系统实际上如此运行。    ← CURRENT

Contract → Implementation → Runtime Reality → Integrity Verification
             ↑ 现有代码       ↑ 实际执行       ↑ Phase 7 入口
```

### Phase 7.1 是什么

Phase 7.1 定义验证契约：

```yaml
不写实现代码。
不改 Phase 6 契约。
只定义:
  验证什么 (scope)
  验证方法 (method)
  通过条件 (criteria)
  证据类型 (evidence)
```

### 与 Phase 6 的差异

```yaml
Phase 6 (设计层):
  产出: Contract, Schema, Design, Validation
  验证: 设计级不变量 (design invariants)
  方法: 场景推理 (scenario reasoning)

Phase 7 (验证层):
  产出: Audit Contract, Audit Report, Evidence
  验证: 运行时级不变量 (runtime invariants)
  方法: 源码审计 + 路径追踪 + 证据链
```

### 不做什么

```yaml
❌ 修改 Phase 6 契约
❌ 引入新能力/新模型
❌ 引入自动修复/self-healing
❌ 让 LLM 参与治理决策
❌ 跳过证据直接结论
```

---

## §1 验证架构

### 1.1 四层审计模型

```
Layer A: Contract — Implementation 映射
  冻结契约 → 代码路径 → 证据文件
  范围: 每份 Phase 6 契约在 源码中的对应实现

Layer B: Runtime — Contract 一致性
  运行时行为 ↔ 契约不变量
  范围: 实际执行路径与契约声明的差距

Layer C: Bypass Surface
  绕过路径 (已识别 + 未识别)
  范围: Phase 6 B1-B5 + Phase 6.3 gap

Layer D: Event — Reality 闭环
  Event 记录是否反映现实
  范围: event/projection/gateway/enforcement 的完整性
```

### 1.2 最终目标

```
Phase 7 完成时:
  ✅ 每个 Phase 6 契约有对应的执行证据
  ✅ 已知 bypass 路径已检测
  ✅ 运行时行为与契约一致
  ✅ 证据链可审计
  ✅ Integrity Freeze 条件满足
```

---

## §2 审计清单

### 2.1 Phase 6.1 — Reasoning Isolation

| ID | Target | Invariant | Evidence | PASS Condition |
|:---|:---|:---|:---|:---|
| R-01 | Context Projection Output | reasoning_content 不进入 runtime context | snapshot + trace | 未发现 reasoning 字段传播到 Context 构建路径 |
| R-02 | reasoning stream lifecycle (thinking.ts → stream-resolution → LLM response) | reasoning 生命周期: 产生 → 使用 → 丢弃 | trace + snapshot | reasoning 丢弃点确认在 LLM 响应结束后, 无可持久化路径 |
| R-03 | openai-reasoning-effort.ts 触发条件 | non-reasoning 模式下零 reasoning 产生 | trace | reasoning=false → 零 reasoning 输出 (每条入口路径检查) |
| R-04 | projection_event schema + event 实例 | Event schema 不含 reasoning 字段 | diff + snapshot | event.schema 中无 reasoning 字段, 且 event 实例无 reasoning 内容 |

### 2.2 Phase 6.2 — Provider Capability Registry

| ID | Target | Invariant | Evidence | PASS Condition |
|:---|:---|:---|:---|:---|
| CR-01 | provider-capability-registry.json vs 实现层 (provider-transport-stream.ts / openai-completions-compat.ts) | registry.json 与 Provider 真实能力声明一致 | diff | 差异为零 (字段级比对, 包含能力名/参数/模式) |
| CR-02 | attempt.ts 中 enforcement 查询路径 | Enforcement 逻辑在运行时可查询 | trace | 调用链: tool_call → enforcement.query → decision, 路径完整 |
| CR-03 | 所有 provider 调用路径 | Enforcement 决策不绕过, 必经 enforcement 查询 | trace | 每条 provider 调用路径上存在 enforcement 查询点 |
| CR-04 | model-auth-markers.ts / models-config.ts 变更路径 | Capability 变更必须经过注册 | trace + diff | 未注册能力不可见于 runtime |

### 2.3 Phase 6.3 — Context Projection

| ID | Target | Invariant | Evidence | PASS Condition |
|:---|:---|:---|:---|:---|
| CP-01 | system-prompt.ts / memory 到 LLM 的所有入口路径 | Context 所有入口经过 Projection | trace + call-graph | 零直接注入路径, 每条入口必经 Projection interface |
| CP-02 | projection_event 写入点 | Event 在 Context Build Complete 后写入 | trace + sample | 写入点确认在 Context 组装完成后, LLM inject 前 |
| CP-03 | projection_event 数据源字段 (sourceId, sourceKind, identity) | Source metadata 完整传递到 Event | diff + sample | event schema 字段完整, event 实例包含 source provenance |
| CP-04 | External Worker Context 读取路径 | Phase 6.3 已知 bypass gap 已确认 | trace | bypass 路径 (不经过 Projection 直接读 memory) 已识别并记录 |

### 2.4 Phase 6.4 — Tool Call Gateway

| ID | Target | Invariant | Evidence | PASS Condition |
|:---|:---|:---|:---|:---|
| TC-01 | attempt.ts tool_calls → execute() 路径 | LLM tool call 必经 Gateway intercept | trace + call-graph | 每条 LLM tool call 路径经过 Gateway.intercept() |
| TC-02 | intercept point 与 tool.execute() 分离 | Gateway 不执行工具 | trace | intercept() → decision → execute() 为二次调用, Gateway 不调用 execute() |
| TC-03 | Gateway 对 tool args 的操作 | Gateway 不修改工具参数 | diff | input args = output args (Gateway 只读, 无写操作) |
| TC-04 | decision 输出与 event 1:1 计数 | 每个 decision 对应一条 event 记录 | sample + trace | decision 数 = event 数, 无遗漏 |
| TC-05 | BypassDetector 检测路径 | 绕过检测逻辑可运行 | trace + sample | detect 逻辑完整: 比对 LLM tool_calls vs Gateway events |
| TC-06 | B1-B5 绕过路径 | 已知 bypass 路径已识别和追踪 | trace | 所有 5 类 bypass 在真实代码中存在性已确认 |
| TC-07 | registry 查询失败路径 | 未注册工具可被 Gateway 拒绝 | trace | registry 查不到 toolName → Gateway 拒绝 → LLM 收到 reject |

---

## §3 审计范围

### 3.1 源码范围

```yaml
必须覆盖的源码文件:

Phase 6.1 (Reasoning Isolation):
  src/agents/pi-embedded-runner/thinking.ts
  src/agents/openai-reasoning-effort.ts
  src/agents/pi-embedded-runner/openai-stream-wrappers.ts
  src/agents/openai-completions-compat.ts
  src/agents/pi-embedded-runner/run/attempt.ts (reasoning 部分)
  src/auto-reply/thinking.shared.ts

Phase 6.2 (Capability Registry):
  src/agents/models-config.ts
  src/agents/models-config.providers.normalize.ts
  src/agents/model-auth-markers.ts
  src/agents/provider-transport-stream.ts
  src/agents/pi-embedded-runner/extra-params.ts
  外部: provider-capability-registry.json

Phase 6.3 (Context Projection):
  src/agents/system-prompt.ts
  src/agents/system-prompt-report.ts
  外部: CONTEXT-PROJECTION-CONTRACT.md + schemas

Phase 6.4 (Tool Call Gateway):
  src/agents/pi-embedded-runner/run/attempt.ts (tool_calls 部分)
  src/agents/tools/execute.ts
  src/tools/execution.ts
  src/tools/types.ts
  src/agents/pi-embedded-runner/run/message-tool-terminal.ts
  外部: TOOL-CALL-GATEWAY-CONTRACT.md + schemas
```

### 3.2 绕过路径

```yaml
B1: Plugin 直接调用工具 API
  - 检查 registerTool 的 tool.execute() 是否可直接绕过
  - 检查 plugin tool 执行路径
  - 检查 src/plugins/tools.ts

B2: External Worker 直接调用 Provider
  - 检查 worker 如何调用 LLM
  - 检查 worker 是否绕过 Context Projection
  - 外部文件: oek-billing-snapshot, oek-billing-push, oek-token-observe

B3: Post-gateway 参数修改
  - 检查 gateway → execute 中间路径
  - 参数是否可被 hook/plugin 修改

B4: Event 缺失
  - 检查 event 写入是否存在盲点
  - 异步写入是否存在丢失路径

B5: Allowlist bypass
  - 检查 Policy 层是否存在直接绕过

Phase 6.3 gap:
  - 检查 External Worker 是否直接读 memory/state 而不经过 Context Projection
```

### 3.3 排除范围

```yaml
❌ 新架构设计
❌ 修改 Phase 6 契约
❌ 实现代码 (只审计)
❌ 第三方 Provider SDK 内部逻辑
❌ Gateway 实现性能基准
❌ Plugin 内部数据流 (只审计 bypass)
```

---

## §4 证据标准

### 4.1 证据链规范

```
每条审计项的最终交付必须包含:

[1] 审计目标
    具体说明验证什么

[2] 证据类型
    snapshot | trace | diff | sample | call-graph

[3] 证据收集方法
    如何获取: exec cmd / 源码阅读 / 运行时观察

[4] 证据原始输出
    不可编辑, 不可截断
    长输出分段提交

[5] 结论
    PASS | FAIL | INCONCLUSIVE
    必须有可观察事实支撑

[6] 二次验证
    结论必须可被另一独立审计员复现
```

### 4.2 证据类型定义

| 类型 | 说明 | 示例 |
|:---|:---|:---|
| `snapshot` | 当前状态快照 | registry.json 内容, 配置项值 |
| `trace` | 调用链追踪 | 函数 A → B → C 的调用路径 |
| `diff` | 对比差异 | schema vs 实现字段差异 |
| `sample` | 运行时样本 | 一次 tool call 的 event 记录 |
| `call-graph` | 调用图 | 函数之间静态调用关系 |

### 4.3 验收规则

#### 结论定义

```yaml
PASS:
  = Contract invariant satisfied
  + Evidence sufficient
  + Reproduction possible

FAIL:
  = Contract invariant violated
  + Evidence sufficient
  + Reproduction possible

INCONCLUSIVE:
  = Evidence insufficient
  OR runtime path unknown
  OR reproduction failed
```

#### FAIL 处理

```yaml
记录具体偏差:
  - 偏差类别: Contract | Schema | Runtime | Event
  - 偏差描述: 契约声明 vs 运行时行为差距
  - 证据引用: 审计项 ID + 证据文件

不修改 Phase 6 契约:
  - 偏差记录到审计报告
  - 追溯至 Phase 6 验证文档, 标记"运行时偏差"
  - 偏差影响评估: 安全/功能/性能

偏差不自动触发回改:
  - 需龙哥确认是否解冻 Phase 6
  - 解冻不是 Phase 7 角色
```

#### INCONCLUSIVE 处理

```yaml
补充证据收集:
  - 扩大审计范围
  - 增加证据类型
  - 直至可判定 PASS / FAIL

无法判定不阻塞进展:
  - 记录为 INCONCLUSIVE
  - 标记后续审计优先级
  - 不影响其他审计项完成
```

---

## §5 审计报告要求

### 5.1 报告结构

```
Phase 7.1 Integrity Audit Report

§0 执行摘要
  - 审计范围总览
  - 整体结论 (PASS / FAIL / CONDITIONAL)
  - 关键发现

§1 审计项结果
  逐项: 目标 → 方法 → 证据 → 结论

§2 偏差清单
  - Contract 偏差
  - Schema 偏差
  - Runtime 偏差
  - Event 偏差

§3 Bypass Surface
  - B1-B5 已验证路径
  - Phase 6.3 gap 确认
  - 新发现绕过路径

§4 未覆盖路径
  - 已知排除项
  - 需要后续审计项

§5 证据索引
  - 证据文件清单
  - 证据采集时间戳
  - 可复现性说明
```

### 5.2 逐项报告模板

```yaml
审计项: R-01
契约: reasoning_content 不进入 Context
方法: 源码追踪 reasoning_content 流向
证据:
  - 调用链: thinking.ts → stream-resolution → LLM response
  - Context 构建路径: system-prompt.ts → Context
  - 引用检查: reasoning_content 不在 Context schema 中
结论: PASS
可复现: 是
```

---

## §6 Audit Exit Criteria

Phase 7.1 COMPLETE 必须满足:

```yaml
[1] Audit item IDs frozen
    所有审计项编号固定:
      R-01~R-04
      CR-01~CR-04
      CP-01~CP-04
      TC-01~TC-07
    无未经确认的新增审计项

[2] Evidence requirement defined
    每条审计项的证据类型已定义:
      snapshot | trace | diff | sample | call-graph
    每种证据的收集方法已确定

[3] Collection method defined
    证据来源明确:
      - 源码文件路径
      - exec 命令
      - 运行时观察手段
      - 对比基准 (contract / schema / event)

[4] PASS/FAIL criteria defined
    每条审计项的 PASS Condition 已定义
    PASS = invariant satisfied + evidence sufficient + reproduction possible
    FAIL = invariant violated (evidence sufficient)
    INCONCLUSIVE = evidence insufficient or runtime path unknown

[5] No implementation change required
    7.1 只负责定义:
      - 什么算违规
      - 如何证明违规
    7.1 不负责修 -> Phase 7.2/7.3/7.4

[6] Exit confirmed by Brother Long
    Audit Contract 冻结
    审计进入执行阶段
```

---

## §8 实施流程

### 8.1 审计执行顺序

```
Phase 7.1 执行流程:

┌──────────────────────────┐
│ Step 1: 审计入口确认      │  ← 当前所在
│  - 锁定所有审计项          │
│  - 确认源码文件清单        │
│  - 确认证据收集方法        │
│                          │
│ Step 2: Phase 6.1 审计    │  ← 可并行
│  - R-01 ~ R-04            │
│  - reasoning 路径追踪      │
│                          │
│ Step 3: Phase 6.2 审计    │  ← 可并行
│  - CR-01 ~ CR-04          │
│  - registry vs 实现对比    │
│                          │
│ Step 4: Phase 6.3 审计    │  ← 可并行
│  - CP-01 ~ CP-04          │
│  - Context 入口审计        │
│                          │
│ Step 5: Phase 6.4 审计    │  ← 可并行
│  - TC-01 ~ TC-07          │
│  - Gateway 路径审计        │
│                          │
│ Step 6: Bypass Surface    │
│  - B1-B5 验证              │
│  - Phase 6.3 gap 确认      │
│                          │
│ Step 7: 报告生成           │
│  - 偏差清单               │
│  - 证据索引               │
│  - 完整性评估              │
└──────────────────────────┘
```

### 8.2 可并行性

```yaml
Phase 6.1-6.4 审计项:
  - 互相独立 (不同源码文件, 不同契约)
  - 可并行执行
  - 证据类型不同, 不影响

Bypass Surface:
  - 依赖 Phase 6.4 审计结果
  - 需要 Gateway 路径确认后才能做 bypass 检测
  - 建议 Step 6 (最后)
```

---

## §9 与 Phase 6 的关系

### 9.1 边界

```
Phase 6 (设计层)          Phase 7 (验证层)
───────────────          ───────────────
Contract / Schema        Audit Contract
Scenario validation      Evidence collection
Design invariants        Runtime invariants
Known gaps (设计级)       Known bypass (运行时)
                         Bypass detection
                         Implementation verification
```

### 9.2 信息流

```
Phase 6 Contract
     │
     ├──→ Phase 7.1 Audit Contract (当前) ← 定义要验证什么
     │
     ├──→ Phase 7.2 Boundary Enforcement ← 确认边界在源码中成立
     │
     ├──→ Phase 7.3 Bypass Closure       ← detect → classify → decision
     │
     ├──→ Phase 7.4 Runtime Verification  ← 执行验证
     │
     └──→ Phase 7.5 Integrity Freeze      ← 所有证据闭环
```

### 9.3 不改 Phase 6

```yaml
Phase 7 审计过程中:

- 发现 Phase 6 契约与运行时偏差 → 记录偏差, 不修改契约
- 发现 Phase 6 验证遗漏 → 记录到 Phase 7 审计报告
- 发现 bypass 路径 → 标记到 Phase 7.3 范围
- 发现实现层问题 → 标记到 Phase 7.2/7.4 范围

不回改 Phase 6 契约:
  除非:
    - 违反已冻结不变量
    - 且无法通过 Phase 7 验证层报错

  如果违反:
    - 冻结解冻流程 (需龙哥确认)
    - 不是 Phase 7 单方面决定
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1-draft | 2026-07-19 | Phase 7.1 Runtime Integrity Audit Contract, 7 章节 |
