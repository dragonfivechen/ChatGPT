# FACT-SOURCE-CONTRACT.md — Fact Truth Source v1.0

> 建立于 2026-07-20，属于 Truth Architecture Phase C。
> 此契约定义事实域的唯一来源和生命周期，是 Memory Governance 的自然延伸。

---

## 1. Authority

```
fact_source:
  authority: memory/facts/
  mode: validated_append
  state: 🟡 Contract Design
  interface: TBD (tools/fact_source.py)
```

`memory/facts/` 是本系统已确认事实的**唯一权威存储**。

**核心原则：** 区分"事实"和"模型生成内容"。

## 2. Fact Lifecycle

```
Observation (观察到现象)
  ↓
Candidate (候选事实，不确定)
  ↓
Validation (验证证据)
  ↓
Validated Fact (已确认事实，写入 facts/)
```

不允许：

```
LLM output
  ↓
facts/                   ❌ 模型生成不直接成为事实
```

也不允许：

```
model inference
  ↓
facts/                   ❌ 推理结果不直接成为事实
```

## 3. Properties

| 属性 | 约束 |
|:---|---:|
| Validated | 事实必须经过验证才能进入 facts/ |
| Traceable | 每个事实关联来源事件（source_event） |
| Confidence-graded | 事实带置信度（high/medium/low） |
| Timestamped | 创建时间和验证时间 |
| Append-only | 不删除、不覆盖既有事实 |

## 4. Fact Schema

```python
{
    "fact_id":      "fact-001",                    # 唯一标识
    "content":      "观察期不应用于延迟已确认的审计缺口修复",  # 事实内容
    "source_event": "evt-2026-07-20-002",          # 来源事件 ID
    "confidence":   "high",                        # high / medium / low
    "created_at":   "2026-07-20T00:58:00+08:00",   # 创建时间
    "validator":    "龙哥",                         # 验证人/机制
    "domain":       "governance",                   # 事实领域
}
```

### 4.1 置信度定义

| 级别 | 含义 | 触发条件 |
|:---|---:|:---|
| high | 已确认，可做决策依据 | 龙哥明确确认 |
| medium | 有证据，但待观察 | 观察到重复模式，待验证 |
| low | 候选事实，需进一步验证 | 单次事件，不确认是否模式 |

## 5. Consumer Rules

### 5.1 禁止

Consumers **不得**：

```
将模型推理输出直接写入 facts/
将未经验证的观察作为事实引用
修改或删除已写入事实
```

### 5.2 必须

通过 `tools/fact_source.py` 访问事实：

```
memory/facts/
 ↓
Fact Reader (fact_source.py)
 ↓
Consumer
```

### 5.3 允许

- **查询事实** — `query_facts()`
- **获取来源** — `get_fact_source()`
- **按域/置信度过滤** — `query_facts(domain, confidence)`

## 6. Fact Reader API (契约，待实现)

### 6.1 接口

```python
query_facts(
    domain: str | None = None,          # governance / architecture / interaction
    confidence: str | None = None,       # high / medium / low
    keyword: str | None = None,          # 内容关键词
    source_event: str | None = None,     # 来源事件
    limit: int | None = None,            # 返回条数上限
) -> list[Fact]

get_fact_source(
    fact_id: str
) -> SourceInfo
```

### 6.2 返回结构

```python
{
    "fact_id":      "fact-001",
    "content":      "...",
    "source_event": "evt-...",
    "confidence":   "high",
    "created_at":   "2026-07-20T00:58:00+08:00",
    "validator":    "龙哥",
    "domain":       "governance",
}
```

### 6.3 不负责

Fact Reader 不做以下事情：
- **推理** — 不生成新事实
- **提升置信度** — 不自动将 candidate→validated
- **摘要** — 不总结事实
- **写入** — 不写入事实

## 7. 与 Memory Governance 的关系

Fact Truth Source 与 Memory Governance Pipeline 互补而非重复：

| | Memory Governance | Fact Truth Source |
|:---|---:|:---|
| **角色** | 规则提炼 | 事实存储 |
| **输入** | 事件（events/） | 已验证事实 |
| **输出** | 规则文件（rules/） | 事实记录（facts/） |
| **生命周期** | 规则提炼 → 促进 → 归档 | 观察 → 候选 → 验证 → 存储 |

两者共享一个原则：**不将模型输出直接作为权威内容。**

## 8. 验收标准

| 标准 | 状态 |
|:---|---:|
| ✅ 模型输出不直接成为事实 | ❌ 待验证 |
| ✅ 每个事实可追溯到来源事件 | ❌ 待验证 |
| ✅ 事实带置信度标识 | ❌ 待验证 |
| ✅ 消费者不再直接写 facts/ | ❌ 待验证 |
| ✅ 不推理、不生成、不提升 | ✅ 无障碍 |

## 9. 版本记录

| 版本 | 日期 | 变更 |
|:---|---:|:---|
| v1.0 | 2026-07-20 | 初始契约。建立 Fact Truth Source 边界定义。 |

| v1.0-audit-1 | 2026-07-20 | Reader 实现完成（fact_source.py）。首批 3 条事实写入 governance.jsonl。 |
