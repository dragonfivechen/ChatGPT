# EVENT-SOURCE-CONTRACT.md — Event Truth Source v1.0

> ```yaml
> contract:
>   name: EVENT-SOURCE
>   version: v1.0
>   level: L1
>   parent: FREEZE-CONTRACT
>   scope: event truth source
>   owner: 燃🔥
>   status: active
> ```
>
> 建立于 2026-07-20，属于 Truth Architecture Phase A。
> 此契约定义事件域的唯一事实源和消费规则。

---

## 1. Authority

```
event_source:
  authority: memory/events/
  mode: append_only
  state: ✅ Established v1.0
  interface: tools/event_source.py
```

`memory/events/` 是本系统事件事实的**唯一权威真相源**。

所有事件相关查询、审计、回放、时间线分析，必须从此源获取事实。

## 2. Properties

| 属性 | 约束 |
|:---|---:|
| Append-only | 只追加，不修改、不删除旧事件 |
| Immutable | 已写入事件不可变更 |
| Timestamp ordered | 每个事件按时间戳排序，事件文件以日期命名 |
| Traceable | 每个事件可追溯到原始写入来源（agent + 文件 + 行号） |

## 3. Consumer Rules

### 3.1 禁止

Consumers **不得**：

```
open("memory/events/*.md")
自行解析事件文件
```

直接读取文件会导致：
- 解析逻辑分散，无统一时间排序保证
- 日期范围查询各自实现，不一致
- 无法对事件访问进行审计

### 3.2 必须

Consumers **必须**使用 Event Reader（`tools/event_source.py`）作为唯一入口：

```
Event Storage (events/)
 ↓
Event Reader (event_source.py)
 ↓
Consumer
```

### 3.3 允许

通过 Event Reader 进行以下操作：
- **Query** — 按时间/agent/category 查询事件
- **Filter** — 基于元数据（类别、来源、内容）筛选
- **Replay** — 按时间范围顺序读取事件流

## 4. Event Reader API

### 4.1 接口

```
query_events(
    start_time: str | None = None,      # ISO-8601 或 date
    end_time: str | None = None,        # ISO-8601 或 date
    agent: str | None = None,           # 'huo' | 'jin'
    category: str | None = None,        # 'architecture' | 'interaction' | ...
    keyword: str | None = None,         # 内容关键词过滤
    limit: int | None = None            # 返回条数上限
) -> list[Event]
```

### 4.2 返回结构

```python
{
    "event_id":   "evt-2026-07-20-001",   # 唯一事件标识
    "timestamp":  "2026-07-20T12:00:00+08:00",  # 事件时间戳
    "agent":      "huo",                  # 来源身份
    "category":   "architecture",         # 事件类别（descriptive only，不可驱动决策）
    "category_source": "derived",         # 类别来源：derived | explicit
    "authority_source": "event",          # 权威来源标识，category 不等同于 authority
    "content":    "事件描述内容",          # 事件正文
    "source":     "memory/events/huo/2026-07-20.md#L12",  # 来源可追溯
}

### 4.3 Category Governance

```
category:
  status: descriptive only
  cannot:
    - drive persistence
    - override event authority
    - trigger promotion
```

### 4.3 不负责

Event Reader 不做以下事情：
- **推理** — 不分析事件含义
- **摘要** — 不生成事件摘要
- **分类** — 不自动分类事件
- **自动修复** — 不修改事件数据
- **存储** — 不写入事件，仅读取

## 5. 写入规则

Event Truth Source 的写入端遵循现有 Event Kernel 契约：

- 事件通过 `tools/` 或身份绑定模块写入 `memory/events/{agent}/{date}.md`
- 禁止直接修改已写入事件行
- 事件写入必须包含事件主体和上下文

## 6. 验收标准

| 标准 | 状态 |
|:---|---:|
| ✅ query_events 返回结果来自唯一事件源 | ✅ PASS |
| ✅ 消费者不再直接解析 events 文件 | 👁 观察中 |
| ✅ Replay/Audit 可复用同一入口 | 👁 观察中 |
| ✅ 不引入数据库 | ✅ PASS |
| ✅ 不改变现有 Event Kernel 契约 | ✅ PASS |
| ✅ category descriptive only + authority_source | ✅ PASS |
| ✅ append-only + immutable 强制执行 | 👁 合规依赖 |

## 7. 版本记录

| 版本 | 日期 | 变更 |
|:---|---:|:---|
| v1.0 | 2026-07-20 | 初始契约。建立 Event Truth Source。 |
| v1.0-audit-1 | 2026-07-20 | 验收确认。🔒 Frozen Baseline + 👁 Runtime Observation。Phase A 完成。 |
| v1.0-audit-2 | 2026-07-20 | Category Governance + authority_source 声明。 |
