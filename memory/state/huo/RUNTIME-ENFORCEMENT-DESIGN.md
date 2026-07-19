# Runtime Enforcement Design v1 — Phase 6.2.3

**Status:** DRAFT
**Date:** 2026-07-19
**Dependencies:**
- PROVIDER-CAPABILITY-CONTRACT.md v1.0 FINAL
- provider-capability.schema.json v1
- PROVIDER-CAPABILITY-REGISTRY-DESIGN.md v1
- REASONING-ISOLATION-CONTRACT.md v1.0 FINAL

---

## 0. 定位

### Enforcement 是 Runtime 的执行层，不是 Governance 的判断层

```
Model Request
    │
    v
[Enforcement Layer]    ← 当前设计
    │
    ├── 查询 Registry (只读 projection)
    ├── 校验请求与能力是否匹配
    ├── 做出执行决策 (allow / reject / degrade)
    └── 记录 decision event
    │
    v
Provider Adapter (实际 API 调用)
```

### Enforcement 不负责

```
❌ 修改 Registry             → Governance 层
❌ 判定证据可信度            → Governance 层
❌ 自动升级能力状态          → Governance 层
❌ 自动解决能力冲突          → Governance 层
❌ Provider 探测             → Phase 6.2.2 Registry 维护
❌ 模型选择                  → Policy Layer (外部)
❌ Routing / Fallback        → Policy Layer
```

---

## 1. 读取接口

### 1.1 Registry Projection

Enforcement 不直接读取 Registry 原始数据。它通过 **Projection** 访问：

```yaml
Request:
  provider: deepseek
  model: deepseek-v4-flash
  requested_capabilities:
    - thinking
    - tool_calls

Projection Response:
  provider: deepseek
  model: deepseek-v4-flash
  capabilities:
    thinking:
      supported: true
      format: reasoning_content
      state: detected
      evidence_fresh: true
    tool_calls:
      supported: true
      format: openai_function
      state: detected
      evidence_fresh: true
  errors: []
```

Projection 是 Registry 的 **只读视图**，包含：

```yaml
projection 字段:
  supported:           来自 current.supported
  format:              来自 current.format
  state:               来自 lifecycle (unknown/detected/verified/deprecated)
  evidence_fresh:      true | false (基于 last_observed 与当前时间的比较)
  provenance:          来自 current.provenance (可选，用于 debug)
```

### 1.2 缺失能力处理

```yaml
场景: 请求中包含 Registry 未索引的能力名

示例:
  请求: { capabilities: ["thinking", "image_generation"] }
  Registry: 只有 ["thinking", "tool_calls", "streaming"]

投影行为:
  对 "thinking"     → 返回 known + 实际值
  对 "image_generation" → 返回:
    capability: image_generation
    known: false
    supported: false
    reason: "capability_not_indexed"
    evidence_fresh: false

Enforcement 决策:
  当 known = false → 等同于不支持
  原因: Registry 没有记录 = 没有证据支持
```

### 1.3 投影缓存

```yaml
投影结果可缓存:
  同一 provider + model + capability 组合
  TTL = 5 分钟
  缓存失效: 新 evidence 写入时触发

缓存不影响证据新鲜度判断:
  evidence_fresh 基于原始 evidence.timestamp 计算
  不受缓存影响
```

---

## 2. Evidence Freshness 判断

### 2.1 新鲜度计算

```yaml
evidence_fresh:
  if state == verified:
    fresh if (now - last_verified) < 24h
    stale if (now - last_verified) >= 24h
  if state == detected:
    fresh if (now - last_observed) < 1h
    stale if (now - last_observed) >= 1h
  if state == deprecated:
    fresh = false
  if state == unknown:
    fresh = false
```

### 2.2 新鲜度级别

| 级别 | 条件 | Enforcement 行为 |
|:---|:---|:---|
| fresh | 证据在 TTL 内 | 正常决策 |
| stale | 证据过期 | 允许通过，但不信任。记录 `enforcement_stale_evidence` 事件 |
| critical | 从未验证过 (unknown) | 拒绝请求，除非强制覆盖配置 |

### 2.3 新鲜度事件

```yaml
enforcement 发现 stale evidence 时:
  - 记录 enforcement_stale_evidence 事件
  - 继续执行请求（不阻塞）
  - 事件供 Governance Audit 消费
```

---

## 3. 执行决策

### 3.1 决策链

```
Request capabilities
    │
    v
Registry Projection
    │
    v
Decision Matrix
    │
    ├── allow       → 正常转发请求
    ├── reject      → 拒绝请求，返回错误
    └── degrade     → 部分降级（移除不支持的能力）
    │
    v
Event Record
```

### 3.2 决策矩阵

```yaml
请求: { capability: X, action: Y }

# allow
  X.supported = true
  AND X.state != deprecated
  AND X.evidence_fresh != critical
  → allow

# reject
  X.supported = false
  OR X.state = deprecated
  OR X.evidence_fresh = critical (且未配置强制覆盖)
  → reject with reason:
    - "capability_not_supported" if supported = false
    - "capability_deprecated" if state = deprecated
    - "evidence_too_old" if evidence_fresh = critical

# degrade
  请求中部分能力不支持:
    - 移除不支持的能力参数
    - 保留支持的参数
    - 记录 degrade 事件
  示例:
    请求: reasoning_effort + temperature
    reasoning_effort.supported = true
    temperature.supported = false
    → 移除 temperature, 保留 reasoning_effort
    → 记录 enforcement_degrade 事件
```

### 3.3 降级规则

```yaml
降级条件:
  1. capability.supported = false           → 移除
  2. capability.state = deprecated          → 移除
  3. capability.known = false               → 移除 (不在 Registry 中)
  4. capability.evidence_fresh = stale      → 保留，记录事件
  5. capability.evidence_fresh = critical   → 移除 (除非强制配置)

降级不改变请求语义:
  - 移除参数 ≠ 修改请求目标
  - 移除 tool_calls ≠ 切换到非工具模式
  - 只是清理了不支持的部分

降级记录:
  enforcement_degrade 事件必须包含:
  - 请求 ID
  - provider, model
  - removed capabilities + 移除原因
  - retained capabilities
```

### 3.4 强制覆盖

```yaml
强制覆盖配置 (仅在明确配置时生效):
  enforcement:
    force_allow:
      - provider: deepseek
        model: deepseek-v4-flash
        capability: thinking
        reason: "已知工作正常，覆盖新鲜度检查"

用途:
  1. 早期注册能力（Registry 还没有 evidence 时）
  2. 已知但不通过 API 验证的能力
  3. 临时绕过 Registry 延迟

约束:
  - 强制覆盖不是默认值
  - 必须显式配置
  - 每次使用记录 enforcement_force_allow 事件
  - Governance Audit 应该定期审查 force_allow 列表
```

---

## 4. 事件记录

### 4.1 Enforcement 事件清单

| Event | 触发 | 包含 |
|:---|:---|:---|
| `enforcement_allow` | 请求通过 | provider, model, capabilities, decision |
| `enforcement_reject` | 请求被拒 | provider, model, capability, reason, request_context |
| `enforcement_degrade` | 部分降级 | provider, model, removed, retained, reason |
| `enforcement_stale_evidence` | 证据过期 | provider, model, capability, last_observed, age |
| `enforcement_force_allow` | 强制覆盖 | provider, model, capability, config_reason |

### 4.2 事件定位

```yaml
所有 Enforcement 事件写入:
  memory/events/system/enforcement/
  
文件命名:
  YYYY-MM-DD.md (按日聚合)

格式:
  每个事件一条 yaml 块，不超过 15 行

事件包含 request_id (如果可用):
  用于跨系统追踪 (Registry → Enforcement → Provider Adapter)
```

### 4.3 事件示例

```yaml
# enforcement_degrade
type: enforcement_degrade
timestamp: "2026-07-19T09:30:00+08:00"
request_id: "req-abc-123"
provider: deepseek
model: deepseek-chat
removed:
  - capability: reasoning_effort
    reason: capability_not_supported
    evidence: "reasoning=false for deepseek-chat"
  - capability: temperature
    reason: capability_not_indexed
    evidence: "not in registry projection"
retained:
  - thinking
  - streaming
```

```yaml
# enforcement_reject
type: enforcement_reject
timestamp: "2026-07-19T09:31:00+08:00"
request_id: "req-def-456"
provider: deepseek
model: deepseek-reasoner
capability: tool_calls
reason: capability_not_supported
evidence: "deepseek-reasoner tool_calls.supported=false"
state: detected
```

---

## 5. Enforcement Decision Event 格式

### 5.1 统一事件结构

```yaml
enforcement_decision:
  type: enforcement_decision
  timestamp: "2026-07-19T09:32:00+08:00"
  request_id: "req-ghi-789"
  
  request:
    provider: deepseek
    model: deepseek-v4-flash
    requested_capabilities:
      - thinking
      - tool_calls
      - image_generation
    raw_params: { ... }
  
  decision:
    result: degrade
    reason: "部分能力不支持"
  
  allow:
    - thinking (supported=true, state=detected, fresh=true)
    - tool_calls (supported=true, state=detected, fresh=true)
  
  reject:
    - image_generation (known=false, reason=capability_not_indexed)
  
  registry:
    projection_query: "deepseek/deepseek-v4-flash"
    query_time_ms: 12
  
  chain: [Enforcement → Provider Adapter]
```

## 6. Registry ↔ Runtime 写权限边界

### 6.1 明确的写权限表

| 操作 | Registry | Runtime | Enforcement | Governance |
|:---|:---:|:---:|:---:|:---:|
| 创建 entry | ✅ | ❌ | ❌ | ✅ |
| 提交 evidence | ✅ | ❌ | ❌ | ✅ |
| 修改 current | ✅ | ❌ | ❌ | ✅ |
| 追加 observation | ✅ | ❌ | ❌ | ✅ |
| 删除 evidence | ❌ | ❌ | ❌ | ❌ (audit only) |
| 升级 lifecycle | ✅ | ❌ | ❌ | ✅ |
| 强制修改 | ✅ | ❌ | ❌ | ✅ |
| 读取 projection | ✅ | ✅ | ✅ | ✅ |
| 读取 full data | ✅ | ❌ | ❌ | ✅ |
| 强制覆盖配置 | N/A | ❌ | ✅ (只读配置) | ✅ (写入配置) |

### 6.2 Runtime 写权限为零

```yaml
Runtime:
  - 读取 Projection:  ✅
  - 提交 Evidence:     ❌ (证据由 Adapter / Detection 提交)
  - 修改 Registry:     ❌ (无论如何)
  - 修改 Lifecycle:    ❌
  - 记录事件:          ✅ (仅 enforcement 事件)
```

### 6.3 Enforcement 写权限严格限制

```yaml
Enforcement:
  - 读取 Projection:        ✅
  - 写入 enforcement 事件:   ✅ (events/system/enforcement/)
  - 写入 Registry:           ❌
  - 强制覆盖:                ❌ (读取配置中的 force_allow 参数)
  - 缓存:                    ✅ (只读缓存，5min TTL)
```

---

## 7. Enforcement 与已有隔离层的交互

### 7.1 请求链路（完整）

```
User / Agent
    │
    v
[Reasoning Isolation Layer]     ← Phase 6.1
    │ reasoning_content lifecycle, storage isolation
    │
    v
[Enforcement Layer]             ← Phase 6.2.3 (当前)
    │ query Registry projection
    │ check capability
    │ allow/reject/degrade
    │
    v
[Provider Adapter / Transport]
    │
    v
[External API]
```

### 7.2 相互作用

```yaml
Reasoning Isolation 先于 Enforcement:
  - 先隔离 reasoning_content
  - 再校验能力 (thinking, reasoning_effort)
  原因: reasoning_content 是 Provider 响应的一部分
        Enforcement 是请求端校验

如果 Enforcement reject:
  - 请求不会到达 Adapter
  - 不会产生 reasoning_content
  - 直接返回错误

如果 Enforcement degrade:
  - 移除不支持的能力参数
  - 请求到达 Adapter
  - 响应正常处理
```

---

## 8. Implementation Path

### 8.1 实现步骤

```yaml
Step 1: Enforcement 决策逻辑 (纯函数)
  - 输入: request capabilities + registry projection
  - 输出: decision (allow/reject/degrade with reasons)
  - 可测试: 输入/输出确定性
  
Step 2: Projection 查询适配
  - 从 Registry 读取
  - 构建 projection 响应
  - 缓存支持
  
Step 3: 事件集成
  - 确保 enforcement 事件写入 memory/events/system/enforcement/
  - 统一事件格式
  
Step 4: 强制覆盖配置
  - 读取 openclaw.json 中的 force_allow 列表
  
Step 5: 集成 Reasoning Isolation
  - 确保请求链路顺序正确
```

### 8.2 截止条件

```yaml
Phase 6.2.3 COMPLETE 条件:
  [ ] Enforcement 决策逻辑定义完成 (3 种输出: allow/reject/degrade)
  [ ] Projection 查询接口定义完成
  [ ] Evidence Freshness 判断逻辑定义完成
  [ ] Enforcement 事件格式定义完成
  [ ] Registry ↔ Runtime 写权限边界确认
  [ ] 强制覆盖机制定义完成
  [ ] 与 Reasoning Isolation 交互确认
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|:---|:---|
| v1.0-draft | 2026-07-19 | Runtime Enforcement Design v1, 8 章节 |
