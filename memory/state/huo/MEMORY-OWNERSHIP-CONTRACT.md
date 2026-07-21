# Memory Ownership Contract v1.0

```yaml
contract:
  name: MEMORY-OWNERSHIP
  version: v1.0
  level: L1
  parent: FREEZE-CONTRACT
  scope: memory namespace ownership
  owner: 燃🔥
  status: active

binding:
  target: workspace

enforcement:
  mode: advisory
  mechanism: agent-convention
  note: "当前无 filesystem ACL 或 namespace validator。namespace 分离依赖模型遵守。"
```

**Phase 2.2 — 架构约束，非源码改动**
**Date:** 2026-07-17

## Authority Order

```
Ownership Policy（最高）
        ↑
Directory Namespace
        ↑
Agent Namespace
        ↑
Frontmatter Metadata（最低）
```

目录 = 分类。Ownership = 权力边界。目录说明"这是什么"，Contract 说明"谁能改、怎么改、能否回滚"。

---

## Contract 表

| Namespace | Owner | 生命周期 | 写入规则 | 覆盖规则 | 删除规则 |
|-----------|-------|---------|---------|---------|---------|
| **facts** | Human / Confirmed Agent | 永久 | 必须显式确认后写入 | 禁止自动覆盖，采用版本更新 | 禁止物理删除，采用废弃标记 |
| **preferences** | User | 长期 | 用户主动修改 | 用户修改覆盖旧值 | 允许修改，不建议删除历史 |
| **state** | Runtime / Agent | 中期 | 状态变化可更新 | 允许覆盖当前状态 | 允许清理旧状态 |
| **events** | Runtime / Agent | 永久 | append-only | ❌ 禁止覆盖 | ❌ 禁止删除 |
| **knowledge** | Importer / Human | 长期 | 外部知识导入 | 版本化替换 | 保留版本 |
| **cache** | Any Worker / Agent | 短期 | 自动生成 | 随时覆盖 | 可自动清理 |
| **data** | Runtime / Worker | 短期 | 管道日志 append，状态 update | 状态快照可覆盖 | 定期自动清理 |

---

## 严格边界

### events — 最严格

create ✅ | append ✅ | read ✅ | modify ❌ | delete ❌

events 是事实链。禁止编辑旧日志、自动整理、AI 修正历史。

### state — 与 events 区分

events = "发生过什么"，state = "当前是什么状态"

state 可更新，events 不可更新。

### facts — 最高价值区，初始最严格

禁止模型推断自动写入 facts。仅允许：
- human 显式确认
- 从 events 手动 promotion

### cache — 最宽松

允许任何 worker/agent 写入。但 cache ≠ memory，不参与长期事实检索。

### data — 管道观测层

append (日志/遥测) ✅ | update (状态快照) ✅ | read ✅ | modify ❌ | delete (自动清理) ✅

data = "系统运行时产生的观测数据"，不属于事实 truth。
- 治理管道日志 (governance-pipeline.jsonl)
- 治理状态快照 (governance-state.json)
- 系统遥测 (system-health.jsonl, service-state.jsonl, memory-snapshot.jsonl)

与 events 的区别：
- events = 事实链，永不可删除
- data = 观测数据，周期性清理

---

## 后续

Phase 2.3 — Memory Writer Boundary（谁有权写，需要什么机制）
Phase 2.4 — Frontmatter Metadata（按需增加）
