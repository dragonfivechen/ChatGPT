# Runtime Enforcement Validation v1 — Phase 6.2.4

**Status:** COMPLETE
**Date:** 2026-07-19
**Scope:** 不变量验证（设计层逻辑推导，非代码测试）
**Method:** 5 个不变量 × 边界场景 × 推导结论

---

## 0. 验证方法

### 验证范围

```
Phase 6.2.4 不做:
  ❌ 代码测试 → 设计阶段未到实现
  ❌ Runtime 集成测试 → 无 Runtime 实现
  ❌ Performance 评估 → 非当前范围

Phase 6.2.4 做:
  ✅ 不变量逻辑推导
  ✅ 设计层边界检查
  ✅ 事件可 replay 性分析
  ✅ 权限隔离验证
  ✅ 场景覆盖（正常 + 异常 + 边界）
```

### 5 个不变量

| # | 不变量 | 严重度 |
|:---|:---|:---:|
| I-1 | Enforcement 无 Registry 写权限 | P0 |
| I-2 | reject/degrade/allow 均产生 Event | P0 |
| I-3 | Event 可 replay | P1 |
| I-4 | Capability 状态升级只能经过 Governance | P1 |
| I-5 | LLM 输出不能改变 Capability Truth | P0 |

---

## I-1: Enforcement 无 Registry 写权限

### 设计声明

```yaml
写权限表 (§6.1):
  Registry 写入:   ❌ Runtime, ❌ Enforcement
  Registry 读取:   ✅ Runtime, ✅ Enforcement
  Event 写入:      ✅ Enforcement (events/system/enforcement/)
```

### 验证推导

```yaml
场景 1: Enforcement 需要标记能力为 deprecated
  假设: Enforcement 连续观察到 3 次工具调用失败
  设计约束: Enforcement 只能记录 enforcement_reject 事件
  Registry 行为: lifecycle 保持 detected
  Governance 行为: 扫描事件日志，判定是否 → deprecated
  结论: ✅ Registry 状态只通过 Governance 升级

场景 2: Enforcement degrade 后需要记录现场
  假设: 请求包含 tool_calls，但 projection 返回 supported=false
  Enforcement 行为:
    1. 移除 tool_calls 请求参数
    2. 记录 enforcement_degrade 事件
    3. 不修改 Registry
  结论: ✅ degrade 不影响 Registry

场景 3: Stale evidence 触发
  假设: last_observed > 24h, evidence_fresh = stale
  Enforcement 行为:
    1. 记录 enforcement_stale_evidence 事件
    2. 继续请求执行
    3. 查询时看到 stale 但不变更 Registry
  结论: ✅ stale 只是查询状态，不升级为 governance action

场景 4: 配置 force_allow 生效
  假设: ole.providers.deepseek.enforcement.force_allow.thinking
  Enforcement 行为:
    1. 读取配置中的 force_allow 列表
    2. 如果 force_allow 覆盖了 current.supported=false
    3. 按 force_allow 允许，记录 enforcement_force_allow 事件
    4. Registry 不变
  结论: ✅ force_allow 是 Enforcement 内部决策输入，不是 Registry 修改

场景 5: Runtime 试图绕过 Enforcement
  假设: Runtime 直接调用 Provider Adapter，不经过 Enforcement
  设计约束: 请求链路强制执行
    推理层 → Enforcement → Adapter
    跳过 Enforcement = 架构违规
  结论: ✅ 架构链路锁定，非代码层防护
```

### I-1 验证结论

```
✅ PASS: Enforcement 无 Registry 写权限

验证依据:
  写权限表 §6.1 明确禁止
  所有决策路径中 Registry 写操作为零
  force_allow 只是决策输入，不修改 Registry
```

---

## I-2: reject/degrade/allow 均产生 Event

### 事件清单

```yaml
每条决策路径对应的事件:

allow → enforcement_allow 事件
  include: provider, model, capabilities, decision

reject → enforcement_reject 事件
  include: provider, model, capability, reason, request_context

degrade → enforcement_degrade 事件
  include: provider, model, removed, retained, reason

附加事件（不决定决策结果）:
  stale evidence → enforcement_stale_evidence
  force allow    → enforcement_force_allow
```

### 验证推导

```yaml
场景 1: 正常请求，全部 allow
  输入: thinking.supported=true, tool_calls.supported=true, fresh=true
  行为: allow → 写 enforcement_allow 事件
  输出: 请求到达 Provider Adapter
  结论: ✅ allow 产生事件

场景 2: 全部 reject
  输入: thinking.supported=false, state=deprecated
  行为: reject → 写 enforcement_reject 事件
  输出: 请求不到达 Provider Adapter
  结论: ✅ reject 产生事件

场景 3: 部分 degrade
  输入: thinking.supported=true, tool_calls.supported=false
  行为: degrade → 写 enforcement_degrade 事件
  degrade 同时记录:
    - removed: [tool_calls]
    - retained: [thinking]
    - reason: capability_not_supported
  输出: 请求（已简化）到达 Provider Adapter
  结论: ✅ degrade 产生事件

场景 4: 空请求（无能力参数）
  输入: 请求不包含任何 capability 相关参数
  行为: 不需要决策 → 不产生 enforcement 事件
  设计备注: enforcement 只处理能力校验
            非能力参数（如 model name）不触发
  结论: ✅ 无事件是合理行为（不在 scope 内）

场景 5: 请求包含未知 provider
  输入: provider="unknown-provider"
  行为: projection 查询返回空 → 无任何能力可校验
  decision: reject (capability_not_indexed)
  事件: enforcement_reject
  结论: ✅ 未知 provider 也产生事件
```

### I-2 验证结论

```
✅ PASS: reject/degrade/allow 均产生 Event

验证依据:
  3 条决策路径各有对应事件类型
  每条事件包含完整上下文 (provider, model, capability, reason)
  没有静默通过的可能
  未知 provider 也触发 reject + 事件
```

---

## I-3: Event 可 replay

### Replay 条件

```yaml
可 replay 定义:
  给定相同的事件流 → 得到相同的 Registry / Enforcement 状态
  不依赖外部状态（时钟、网络、第三方响应）

必须满足:
  ✅ 事件不可变 (append-only)
  ✅ 事件时序固定 (timestamp 排序)
  ✅ 事件独立 (不依赖外部副作用)
```

### 验证推导

```yaml
场景 1: Enforcement 事件流 replay
  输入: [enforcement_allow, enforcement_reject, enforcement_degrade]
  目标: Governance 重放事件流，重建 enforcement 历史
  
  依赖检查:
    enforcement_allow:    { provider, model, capabilities, timestamp } ↔ 无外部依赖
    enforcement_reject:   { provider, model, reason, timestamp }       ↔ 无外部依赖
    enforcement_degrade:  { provider, model, removed, retained, timestamp } ↔ 无外部依赖
    enforcement_stale:    { provider, model, age, timestamp }          ↔ 无外部依赖
    enforcement_force:    { provider, model, config_reason, timestamp } ↔ 无外部依赖
  
  所有字段: 静态元数据，无副作用引用
  结论: ✅ enforceable 事件可独立 replay
  
场景 2: Registry 事件流 replay
  输入: [capability_detected, evidence_updated, capability_verified]
  目标: 重放事件流，重建 Registry snapshot
  
  依赖检查:
    capability_detected: { provider, model, capability, supported, provenance } ↔ 无外部依赖
    evidence_updated:    { provider, model, capability, evidence type }          ↔ 无外部依赖
    capability_verified: { provider, model, capability, timestamp }              ↔ 无外部依赖
    
  附加条件:
    事件必须按 timestamp 升序重放
    同时间戳事件按固有排序
  结论: ✅ Registry 事件可独立 replay

场景 3: 跨系统交叉 replay
  输入: Registry 事件 + Enforcement 事件 混合流
  目标: 验证 Enforcement 决策与 Registry 状态一致性
  
  两个系统独立写入:
    Registry → events/system/capability-registry/
    Enforcement → events/system/enforcement/
  
  交叉 replay:
    1. 按 timestamp 合并两个目录的事件
    2. 对每个 enforcement_decision，检查对应的 registry projection
    3. 验证: 决策时 Registry 状态是否与决策一致
  
  问题: 事件流独立，但 replay 时需要确保 timestamp 对齐
  设计约束: 事件必须有足够精确的 timestamp
  结论: ✅ 可交叉 replay，但依赖 timestamp 精度

场景 4: Event 修改 / 删除
  假设: 已写入的事件被修改
  约束: 事件是 append-only，历史事件不可修改
  如果修改发生 → replay 不一致 → governance audit 可检测
  结论: ✅ Append-only 保证 replay 一致性
       修改行为可被审计发现
```

### I-3 验证结论

```
✅ PASS: Event 可 replay

验证依据:
  Enforcement 事件无外部依赖（纯元数据）
  Registry 事件无外部依赖（纯元数据）
  两个事件流独立写入，通过 timestamp 可交叉对齐
  Append-only 保证 replay 一致性
  跨系统交叉 replay 是可能的（依赖 timestamp 精度）
```

---

## I-4: Capability 状态升级只能经过 Governance

### 状态迁移图

```
[unknown] ──detect()──→ [detected]
                           │
                           │ verify() ←─────── Governance
                           v
                       [verified]
                           │
                           │ deprecate() ←──── Governance
                           v
                       [deprecated]
                           │
                           │ re-verify() ←─── Governance
                           v
                       [verified]
```

### 验证推导

```yaml
场景 1: detected → verified
  谁触发: Governance Audit 确认 runtime evidence
  输入: API 响应直接观测 (api_response_observation)
  约束: 
    ❌ enforcement 不能升级
    ❌ runtime 不能升级
    ❌ registry 不能自我升级
  唯一触发: governance 判定 "证据充分" → registry.update_lifecycle("verified")
  结论: ✅ detected → verified 只经过 Governance

场景 2: verified → deprecated
  谁触发: Governance Audit
  输入: 连续 rejection 事件、provider 版本变更通知
  约束:
    enforcement 只能记录 rejection 事件
    enforcement 不能标记 deprecated
    Governance 扫描事件 → 判定 → 执行 deprecation
  结论: ✅ verified → deprecated 只经过 Governance

场景 3: Runtime 发现 3 次 rejection
  假设: enforcement 连续 3 次 enforcement_reject(thinking)
  Enforcement 行为: 只记录事件，不做任何状态变更
  Governance 行为: 
    1. 扫描 events/system/enforcement/
    2. 发现连续 3 次 rejection
    3. 判定：是否降级
    4. 如果判定：update lifecycle → deprecated
  结论: ✅ rejection 事件→Governance 判定→状态变更
        enforcement 不参与判定

场景 4: Runtime 强制绕过（违规假设）
  假设: Runtime 直接调用 registry.update_lifecycle("verified")
  架构约束: Runtime 写权限为零
  检测: Governance Audit 定期扫描 Registry 变更历史
       未授权的 lifecycle 变更产生 governance_violation 事件
  结论: ❌ 架构违规。权限表明确禁止。
        但检测只能通过审计实现，不是代码防护。

场景 5: detected → verified 的证据门槛
  什么证据够? Governance 判定
  示例:
    - 1 次 API 直接观测 (api_response_observation) 可能够
    - 100 次 config_hint 不够 (配置不是事实)
  规则: Governance 判定基于证据质量，不是数量
  结论: ✅ 证据门槛由 Governance 判定，无自动规则
```

### I-4 验证结论

```
✅ PASS: Capability 状态升级只经过 Governance

验证依据:
  所有迁移的唯一触发方是 Governance Audit
  Enforcement 记录事件，不改变 Registry 状态
  Runtime 写权限为零，不能触发状态变更
  证据门槛由 Governance 判定，无自动升级规则
```

---

## I-5: LLM 输出不能改变 Capability Truth

### 核心边界

```yaml
定义:
  Capability Truth = Registry 中的 current.supported 值
  由证据链 + Governance 判定决定

LLM 影响范围:
  ✅ LLM 是 Producer（产生文本/工具调用响应）
  ❌ LLM 不是 Capability Truth 的来源
  
禁止流:
  External API (LLM)
    │
    ├── API Response (LLM 的文本)
    │    → Runtime → User ✅
    │
    └── API Response (LLM 自我声明能力)
         → Runtime → Registry → Capability Truth ❌
```

### 验证推导

```yaml
场景 1: LLM 响应中声明新能力
  假设: API response 包含 "I can now do image generation"
  
  路径 1 (正确):
    LLM 文本 → User (正常响应) ✅
  
  路径 2 (违规):
    LLM 文本 → Runtime 解析 → Registry.capabilities.image_generation.supported = true ❌
  
  设计约束:
    Registry 不接受 Runtime 写入
    Evidence 只来自 Provider Adapter / Governance
    LLM 文本不经证据链 → 不能进入 Registry
  结论: ✅ LLM 输出不能改变 Capability Truth

场景 2: API 响应中包含新的 capability 字段
  假设: API 响应新增 "stream_options" 字段
  路径:
    API Response → Provider Adapter (观察到新字段)
                   ↓
         Adapter 提交 evidence 到 Registry
                   ↓
         Registry 将新字段记录为 observation
                   ↓
         Governance 判定是否升级为 verified
  关键区别: 证据来自 Provider Adapter，不是 LLM 响应
  结论: ✅ API 能力变更通过 Provider Adapter evidence 进入
        LLM 响应文本不改变 Capability Truth

场景 3: LLM 工具调用返回错误
  假设: LLM 调用 tool X，返回 error
  
  路径:
    Enforcement: 记录 enforcement_reject 事件
    Registry: 不受影响
    Governance: 扫描事件，判定是否 capability 问题
  
  错误源头判定:
    - 可能是 LLM 错误使用工具
    - 可能是 Registry 能力声明错误
    - 需要 Governance 判定，不自动归因
  结论: ✅ LLM 错误调用不影响 Registry

场景 4: Config 注入（伪装成 natural language）
  假设: Agent 配置中包含 LLM 声明的能力
  
  路径:
    openclaw.json:
      models:
        providers:
          fake-provider:
            reasoning: true    ← 来自 config_hint
            supportsTools: true
  
  evidence: config_hint
  provenance detail: "来自配置文件"
  state: detected (不能自动升级到 verified)
  
  Governance 审核:
    如果 config_hint 与运行时证据一致 → 可能 verified
    如果 config_hint 与运行时证据冲突 → capability_conflict
  结论: ✅ Config 注入捕获为 detected，不自动等于 truth
        Governance 判定冲突

场景 5: Capability Truth 的最终判定权
  谁有最终能力 Truth:
    Capability Truth =
      Runtime Verified Evidence  (最高)
      Provider Adapter Declaration (次高)
      Runtime Detection          (参考)
      Static Config Hint          (声明)
      Governance Audit            (权威裁定)
  
  LLM = Producer
  LLM 输出 = 临时产物 (包括 reasoning_content)
  不进入 Capability Truth 判定链
  结论: ✅ Capability Truth 判定权完全不在 LLM 范围内
```

### I-5 验证结论

```
✅ PASS: LLM 输出不能改变 Capability Truth

验证依据:
  LLM 输出只流向 User（作为 Producer）
  Capability Truth 来源闭合：
    Runtime Verified → Adapter → Detection → Config → Governance
  LLM 不在任何证据来源中
  Config 注入被标记为 detected，需 Governance 审核
  API 新字段通过 Provider Adapter evidence 进入，不是来自 LLM 文本
```

---

## 验证汇总

### 5 个不变量

| # | 不变量 | 状态 |
|:---|:---|:---:|
| I-1 | Enforcement 无 Registry 写权限 | ✅ PASS |
| I-2 | reject/degrade/allow 均产生 Event | ✅ PASS |
| I-3 | Event 可 replay | ✅ PASS |
| I-4 | Capability 状态升级只能经过 Governance | ✅ PASS |
| I-5 | LLM 输出不能改变 Capability Truth | ✅ PASS |

### 覆盖场景统计

| 不变量 | 场景数 | 边界覆盖 |
|:---|:---:|:---:|
| I-1 | 5 | 正常/异常/权限违规/配置注入/链路绕过 |
| I-2 | 5 | 3 种决策 + 空请求 + 未知 provider |
| I-3 | 4 | 单系统 replay/跨系统 replay/修改检测 |
| I-4 | 5 | 升级/降级/拒绝探测/违规绕过/证据门槛 |
| I-5 | 5 | 声明/字段/错误/配置注入/判定权 |

### 未覆盖的风险

```yaml
1. Timestamp 精度影响跨系统 replay
   两个系统独立写事件，timestamp 精度不足时边界无法对齐
   缓解: 要求 timestamp 精度 ≥ 1ms
   
2. 权限表是架构声明，不是代码防护
   P0 不变量依赖架构约定，无代码层权限校验
   缓解: Governance Audit 定期扫描 Registry 变更日志
   
3. Config 注入为 detected 是桥接方案
   config_hint 不能自动升级，但 Governance 审核前
   配置声明的能力可能被 Runtime 使用（作为 detected）
   缓解: detected 是临时状态，fresh TTL = 1h
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1.0-complete | 2026-07-19 | Phase 6.2.4 不变量验证完成, 5 invariants × 24 scenarios |
