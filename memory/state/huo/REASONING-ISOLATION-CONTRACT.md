# Reasoning Isolation Contract v1.0

**Phase 6.1 — 架构契约，非源码改动**
**Date:** 2026-07-19
**Status:** ✅ FINAL
**Owner:** Runtime Governance

---

**变更记录**
| 版本 | 日期 | 变更 |
|:---|:---|:---|
| v1.0 | 2026-07-19 | 初始定稿 |

**后续修改规则**
- 仅允许 version bump（版本号递增）
- 任何修改需审计复核
- 不存在

---

## 0. 定位

Reasoning Isolation Contract 是 OpenClaw Runtime Intelligence Layer 的第一个建设单元。
它**不新增能力**，而是为**已有行为声明边界**。

### 已有事实

经 DeepSeek TMW P1-P3 验证：

```text
DeepSeek API
    ↓
reasoning_content (thinking block)
    ↓
structured storage (暂存)
    ↓
replay (session 回放)
    ↓
销毁/丢弃
```

当前行为正确，但无正式契约约束。未来若开发者在非认知下将 `reasoning_content` 用于持久化，将造成架构污染。

### 目标

建立 `reasoning_content` 的正式生命周期与持久化禁令，使其在架构层面被视为 ——
不是"有价值的上下文"
而是"临时推理痕迹，用完即弃"

---

## Section 1: 定义

### 1.1 reasoning_content

`reasoning_content` 是指 LLM 在生成最终响应之前产生的内部推理过程数据，包括但不限于：

- DeepSeek API 返回的 `reasoning_content` 字段
- 映射后的 `ContentBlock.thinking` 类型块
- 任何形式的"思维链"、"中间推理"、"思考过程"
- 多轮推理中间结果（如 tool loop 中的连续推理）

### 1.2 性质声明

```yaml
reasoning_content:
  nature: inference_trace         # 推理痕迹，非结果
  scope: request                  # 请求级，不跨越 session 边界
  semantics: opaque_to_contract   # 语义对治理层不透明
```

**治理层不对 reasoning_content 的内容做任何语义判断。**
不检查它是否"有用"、"可恢复"、"有价值"。
治理层只管理它的**生命周期**和**存储边界**。

---

## Section 2: 生命周期

### 2.1 生命周期状态机

```text
inference_begin
    ↓
reasoning_content 生成
    ↓
┌─────────────────────────┐
│     Request Scope       │
│                         │
│  temporary_context      │
│  provider_transport     │
│  debugging              │
│                         │
│   ↓ tool/result/final   │
│   ↓ response_complete   │
└─────────────────────────┘
    ↓
     销毁
```

### 2.2 生命周期阶段

| 阶段 | 允许 | 禁止 |
|:---|:---|:---|
| `inference_begin` → `response_complete` | provider 传输, 临时上下文, 会话内回放 | 持久化, 跨 session 传递 |
| `response_complete` 后 | 无 | 任何形式的保留 |
| `inference_abort` | 异常清理 | 任何形式保留 |
| `tool_failure` | 异常清理 | 任何形式保留 |
| `timeout` | 异常清理 | 任何形式保留 |
| `provider_error` | 异常清理 | 任何形式保留 |

**异常路径说明：** 任何非正常结束的请求（abort/failure/timeout/error）也必须触发 reasoning_content 清理。异常 session 不应残留推理数据。

### 2.3 例外

仅以下情况允许 reasoning_content 在 `response_complete` 后保留：

| 用途 | 条件 | 存储位置 |
|:---|:---|:---|
| 调试 / 诊断 | 非生产，有开关保护 | `debug/*` 隔离目录 |
| 测试验证 | 有专用回收策略 | `test/*` 自动清理 |
| Provider 日志（限 headers） | 不可包含完整 body | Provider 传输层，审计日志除外 |

**任何例外都必须：**
1. 有显式开关（非默认启用）
2. 有自动过期/清理策略
3. 记录在对应模块的 README 或配置中

### 2.4 Audit Metadata 例外

允许记录 reasoning_content 的**存在事实**，但不记录内容：

```yaml
# ✅ 允许
Audit Metadata:
  reasoning_present: true         # 是否产生 reasoning
  provider: deepseek              # 提供商
  model: deepseek-v4-flash        # 模型
  duration_ms: 1234               # 推理耗时
  token_count: 567                # 推理 token 数

# ❌ 禁止
Audit Metadata:
  reasoning_content: "..."       # 禁止完整内容
```

**规则：** 记录**事实**，不记录**内容**。

---

## Section 3: 持久化禁令

### 3.1 Memory 域

```yaml
memory:
  MEMORY.md:              forbidden  # 长期记忆
  memory/events/:         forbidden  # 事件日志
  memory/knowledge/:      forbidden  # 知识库
  memory/facts/:          forbidden  # 事实数据
  memory/state/:          forbidden  # 系统状态
  memory/preferences/:    forbidden  # 偏好配置
  memory/data/:           forbidden  # 业务数据
```

**禁止理由：** reasoning_content 是推理痕迹，不是"记忆"、"事实"或"知识"。
使其进入 Memory 域会污染长期数据质量，导致推理过程被误认为是系统状态。

### 3.2 Event 域

```yaml
event:
  events.jsonl:           forbidden  # 事件日志
  AcpEventLedgerEntry:    forbidden  # ACP event ledger
```

**禁止理由：** Event 域是事实源的记录层。推理过程不是事实，不应进入 Event。
Event 只记录：
- 用户输入
- 系统行为（tool execution, error, state change）
- 模型最终输出
不记录：
- 模型的"思考过程"

### 3.3 知识 / 缓存域

```yaml
knowledge:
  memory/knowledge/:      forbidden  # 知识库

cache:
  memory/cache/:          forbidden  # 缓存（除非明确标记为临时推理缓存）
```

### 3.4 临时允许

```yaml
temporary:
  runtime/cache/reasoning/*:  allowed  # 运行态临时缓存，自动清理策略要求：session 生命周期 < 1h

**注意：** `runtime/cache/` 是运行态命名空间，与 Memory Governance 的 `memory/` 域严格区分。
不写作 `memory/cache/`，避免与 Memory 子系统混淆。
```

---

## Section 4: 传输层规则

### 4.1 Provider 传输

```yaml
provider_transport:
  reasoning_content:
    transport: allowed           # provider → runtime 允许传输
    persistence: forbidden       # 传输后必须处理（映射/丢弃/临时存储）
    logging:
      full_body: forbidden       # 禁止完整 body 写日志
      header_metadata: allowed   # header 级元数据（如 token count）允许
```

### 4.2 日志脱敏规则

```yaml
logging:
  # ✅ 允许
  request_id:     allowed
  provider:       allowed
  model:          allowed
  token_count:    allowed
  latency_ms:     allowed

  # ❌ 禁止
  prompt_full_dump:   forbidden  # 完整 prompt
  reasoning_dump:     forbidden  # reasoning 完整内容
  tool_hidden_state:  forbidden  # tool 内部状态
```

### 4.3 跨模型传输

```yaml
cross_model_transport:
  v3.2 → v4:      allowed (已验证 replay 兼容)
  v4 → v3.2:      allowed (已验证 cleanup 兼容)
  model_fallback: allowed_only_if_cleanup  # failover 时需清理后传递
```

跨模型的 reasoning_content 传递仅限于：
- 同一个请求生命周期内
- 仅作为 provider_transport 的一部分
- 目标模型不支持时，必须清理后再传递（已验证通过）

---

## Section 5: 审计要求

### 5.1 违反检测

| 检测点 | 方法 |
|:---|:---|
| reasoning_content → Memory write | 静态检查 + runtime log 监控 |
| reasoning_content → Event append | Event Ledger 只读接口校验 |
| reasoning_content → Knowledge 写入 | 写入路径监控 |
| reasoning_content → 持久化未清理 | TTL 审计 |

### 5.2 审计日志

以下事件应记录到 Audit：

```
reasoning_content.produced         # 何时产生（request_id, token count）
reasoning_content.transported      # 何时传输（provider → runtime）
reasoning_content.cleaned          # 何时清理（response_complete）
reasoning_content.violation        # 违反事件（含越界路径）
```

### 5.3 永久不变量 (Invariants)

以下两个不变量在任何架构变更后必须保持满足：

```
RI-001  Reasoning 不得进入 Event Store
       grep events.jsonl "reasoning_content" = 0

RI-002  Reasoning 不得进入 Memory namespace
       grep -r "reasoning_content" memory/ = 0
```

**验证方法：** 每次 Compliance Audit 扫描上述两个路径。
发现违反 → 立即回滚 + 提交事件。

### 5.4 周期性验证

在 Governance Compliance Audit 中增加以下检查项：

```
[ ] RI-001: reasoning_content 未出现在 events.jsonl
[ ] RI-002: reasoning_content 未出现在 memory/
[ ] reasoning_content 未出现在 MEMORY.md
[ ] reasoning_content 未出现在 memory/events/
[ ] reasoning_content 未出现在 memory/knowledge/
[ ] 临时缓存 < 1h
[ ] Provider 日志无完整 reasoning_content body
```

---

## Section 6: 与现有契约的关系

### 6.1 依赖关系

```yaml
depends_on:
  - Event Source Truth           # Event 是事实源，推理不是事实
  - Replay Contract              # reasoning_content 仅限 request-scoped replay
  - Memory Governance            # Memory 命名空间由本契约扩展禁止规则
```

### 6.2 对现有契约的补充

| 现有契约 | 本契约补充 |
|:---|:---|
| Event Source Truth | 明确 excluded: reasoning_content |
| Replay Contract | 明确 reasoning_content 仅在 replay 中临时存在 |
| Memory Governance | 新增 "推理痕迹" 类别的写入禁令 |
| Memory Writer Boundary | 新增 `reasoning_writer` 分类（若需要） |

### 6.3 不改变

```
- Event Ledger schema         不修改
- Memory Ownership Contract   不修改
- Memory Metadata Contract    不修改
- ACP 协议                    不修改
- Plugin API                  不修改
```

---

## Section 7: 本契约的边界

### 7.1 本契约不定义

- reasoning_content 的格式 / schema / 解析方式
- 模型内部如何生成推理
- 用户是否应该看到 reasoning_content（由 surface/channel 决定）
- reasoning_content 是否用于 prompt engineering（由 LLM worker 决定）

### 7.2 本契约不涉及

```
- Provider Capability Registry    → Phase 6.2
- Context Projection              → Phase 6.3
- Tool Call Gateway               → Phase 6.4
```

---

## Section 8: 违反后果

| 违反 | 严重程度 | 处理 |
|:---|:---:|:---|
| reasoning_content 写入 MEMORY.md | 🔴 P0 | 立即事件回滚 + 契约审计 |
| reasoning_content 写入 events.jsonl | 🔴 P0 | 立即事件回滚 + 数据清理 |
| reasoning_content 写入 knowledge | 🟡 P1 | 数据清理 + Contract 审计 |
| reasoning_content 缓存超时 1h | 🟡 P1 | 缓存清理 + TTL 策略审计 |
| Provider 日志含完整 body | 🟠 P2 | 日志裁剪 + 配置审计 |

---

## 附录 A: 验证清单

### A.1 当前验证状态

基于 DeepSeek TMW P2/P3 结果：

```
[✅] reasoning_content → structured storage (暂存，request-scoped)
[✅] reasoning_content → V3.2 → V4 replay (兼容)
[✅] reasoning_content → V4 → V3.2 cleanup (兼容)
[✅] reasoning_content → tool loop 中间推理 (已验证)
[ ] reasoning_content → Memory 禁令 (未显式验证)
[ ] reasoning_content → Event 禁令 (未显式验证)
[ ] reasoning_content → Knowledge 禁令 (未显式验证)
[ ] reasoning_content cache TTL (未显式验证)
```

### A.2 后续验证项

| 验证项 | 方法 |
|:---|:---|
| reasoning_content 未进入 MEMORY.md | 文件扫描 + grep |
| reasoning_content 未进入 events/ | Event Ledger 审计 |
| reasoning_content 未进入 events.jsonl | 日志审计 |
| temporary cache < 1h | 文件 mtime 扫描 |

---

*本草案定义了 reasoning_content 的生命周期和存储边界，不修改任何源码。待龙哥复核后进入定稿。*
