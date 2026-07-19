# Runtime Context Contract v1.0

> 定义运行时事实的获取、使用和验证规则。
> 不属于 Memory，不属于 SOUL.md，属于 Runtime Layer。

---

## 1. 核心原则

**时间只能有一个真相源，所有时间消费必须从这个源获取。**
**任何模块都不能自己定义「当前时间」。**

- OS Clock → 底层事实源（2026-07-20 00:30:00 CST — 这是事实）
- Context Provider → 标准化入口（不让每个模块各自 datetime.now()）
- 消费者 → 只消费，不创造事实

## 2. 架构

```
Time Truth Source (OS Clock)
 │
 ├── Runtime API (实时系统：cron 调度、精确计时、高精度任务)
 │
 └── Context Snapshot (文件快照：对话上下文、日报展示、模型消费)
       │
       ▼
    runtime/time_context.json
       │
       ├── Scheduler (cron)     → 执行时间
       ├── Reporter (日报)      → 展示日期
       └── Model Context (对话) → 自然语言表达
```

## 3. 真相源一致性

与 OpenClaw 已有原则一致：

| 域 | 真相源 | 备注 |
|----|--------|------|
| 事件 | Event Store | Event → 唯一事件真相 |
| 时间 | OS Clock → Context Provider | Runtime Time → 唯一时间真相 |
| 配置 | Config Registry | Config → 唯一配置真相 |

**缺少真相源时靠规则补救；建立真相源后，规则数量自然下降。**

## 4. Truth Architecture（真相源架构）

### 4.1 优先级顺序

```
建立各领域 Truth Source
 ↓
明确事实边界
 ↓
形成消费契约
 ↓
观察真实调用模式
 ↓
判断是否需要统一访问层
```

不按此顺序提前抽象统一接口 → 属于无证据扩展。

### 4.2 各域状态

| 域 | Truth Source | 消费契约 | 状态 |
|:---|---:|:---:|:---:|
| Time | OS Clock → `context_provider` → `time_context.json` | 本契约 v1.0 | ✅ 已建立 |
| Event | `memory/events/`（append-only 事件存储） | 未契约化 | 🟡 需要契约 |
| Config | Config Registry（框架内建） | 未契约化 | 🟡 需要契约 |
| Fact | `memory/facts/`（可追溯的事实存储） | 未契约化 | 🟡 需要契约 |

### 4.3 各域要求（目标）

**Event 域：**
- append-only，不允许直接修改历史
- 查询结果可追溯
- 时间排序可信
- 有标准消费入口（不直接读文件）

**Config 域：**
- 当前版本明确
- 修改有记录
- 消费者不能读取散落配置绕过真相源

**Fact 域：**
- 来源可追踪
- 区分事实和推论
- 不把模型生成内容直接当事实

### 4.4 统一访问层

暂不设计。等待出现以下真实需求：

- 多个模块都需要查询事实、验证来源、获取版本、审计访问
- 且已有重复实现

否则保持领域自治。

## 5. 覆盖场景

以下场景**必须**使用 runtime context 作为时间事实源：

| 场景 | 示例 | 必须使用？ |
|------|------|:---:|
| 涉及当前日期/时间 | "今天 ××"、"现在 ××" | ✅ |
| 涉及相对时间表达 | "明天 N点"、"N小时后" | ✅ |
| 涉及调度/截止时间 | "X 分钟后触发" | ✅ |
| 不涉及任何时间信息 | 纯技术回答 | ❌ |

## 5. 获取方式

### 5.1 Context Snapshot（对话/脚本场景）

```
runtime/time_context.json
```

由 OS clock → context_provider.py 生成，每 5 分钟刷新（crontab）。
消费者读取文件，不自行推断。

### 5.2 Runtime API（实时场景）

高精度/实时需求直接调用 `runtime/context_provider.py --stdout` 或 OS clock API。
不走文件，不增加延迟。

## 6. 工具链职责

| 工具 | 职责 | 不做什么 |
|------|------|---------|
| context_provider.py | OS clock → time_context.json | 不参与模型推理 |
| temporal_resolver.py | 自然语言时间 → 绝对时间 | 不判断用户意图 |
| context_validator.py | 标记歧义表达 | 不下结论、不自动修正 |

## 7. 边界

- Runtime Context **不能**成为新的隐藏状态（入模型前注入，不入模型内部持久化）
- Runtime Context **不**承载行为规则（行为规则在 SOUL.md 和 memory/rules/）
- Runtime Context **不**做决策（Resolver 解析语义，Validator 标记矛盾，不选择）

## 8. 冻结状态

```
Runtime Context Layer v1.0

Baseline:
🔒 Frozen

Audit Remediation:
✅ Relative Date Resolution (前天/昨天/大前天)

New Capability:
❌ None

Integrity Fix:
✅ Yes
```

**冻结定义：**
- ❌ 无证据扩展、功能膨胀、重新设计
- ❌ 新增经验规则替代事实基础设施
- ✅ 审计发现的缺口修复、正确性修复、边界覆盖补齐

## 9. 演化（规划中）

- Phase 2: 任务状态、执行阶段、配置版本（未部署，不推进）

---

## A. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-20 | 初始版本。Runtime API + Context Snapshot 双通道。三层架构：Truth Source → Adapter → Consumer。 |
| v1.0-audit-1 | 2026-07-20 | 审计修复：Temporal Resolver 补充 Relative Date（前天/昨天/大前天）。基线架构不变。 |
