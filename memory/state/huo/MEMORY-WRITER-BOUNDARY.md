# Memory Writer Boundary v1.0

**Phase 2.3 — 架构规范，非源码改动**
**Date:** 2026-07-17

---

## 基线事实

OpenClaw 当前源码已验证：

- Agent 只有 `memory_search` / `memory_get`（只读 tools）
- Agent 无 `memory_write` tool
- Memory 写入口仅 3 条：filesystem / dreaming promotion / deep dreaming
- 其中 filesystem 是无管控路径

---

## Section 1: Writer Classification

| Class | ID | 当前状态 | 定义 |
|-------|-----|---------|------|
| Runtime Writer | `runtime` | Existing | 系统组件运行时写入（state/events） |
| Generated Memory Writer | `generated` | Existing | Dreaming 系统自动从 session 提取写入 |
| Worker Writer | `worker` | Existing | External worker 写入（cache） |
| Human Writer | `human` | Future | 用户确认后写入（facts/preferences） |
| Import Writer | `import` | Future | 外部知识源版本化导入（knowledge） |
| External Event Producer | `external-event-producer` | Future | 受治理的外部 Worker，可 append 到指定 events/ 子域，不扩及整个 events namespace |
| Agent Direct Writer | `agent-direct` | Forbidden | 禁止 Agent 直接写 Memory |

---

## Section 2: Namespace Permission Matrix

| Namespace | runtime | generated | worker | human | import | external-event-producer | agent-direct |
|-----------|---------|-----------|--------|-------|--------|------------------------|-------------|
| facts | ❌ | ❌ | ❌ | ✅ explicit | ❌ | ❌ | ❌ |
| preferences | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| state | ✅ update | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| events | ✅ append | ❌ | ❌ | ❌ | ❌ | ✅ append (owned-domain only) | ❌ |
| knowledge | ❌ | ❌ | ❌ | ❌ | ✅ versioned | ❌ | ❌ |
| cache | ❌ | ❌ | ✅ disposable | ❌ | ❌ | ❌ | ❌ |
| MEMORY.md (root) | ❌ | ✅ controlled | ❌ | ❌ | ❌ | ❌ | ❌ |
| memory/dreaming/ | ❌ | ✅ append | ❌ | ❌ | ❌ | ❌ | ❌ |
| memory/data/ | ✅ update | ❌ | ✅ append+update | ❌ | ❌ | ❌ | ❌ |

---

## Section 3: Allowed Mutation

| Namespace | Allowed Operations | Notes |
|-----------|-------------------|-------|
| facts | create (explicit), read | 禁止自动覆盖，采用版本更新 |
| preferences | create, update, read | 用户修改覆盖旧值 |
| state | create, update, delete (stale), read | 允许覆盖当前状态 |
| events | append, read | ❌ modify / ❌ delete |
| knowledge | create (versioned), read | 版本化替换，保留旧版本 |
| cache | create, update, delete, read | 随时覆盖，可自动清理 |
| memory/data/ | append, update, read | 管道日志 + 治理状态 + 系统遥测。append-only 日志，update 状态快照 |

---

## Section 4: Forbidden Writers

### 硬禁止

| Writer | 理由 |
|--------|------|
| Agent Direct Writer | Agent 是 Consumer，不是 Writer。需通过 Human Confirm 或 Dreaming 系统间接写入。 |
| Model Inference → facts | 模型推断结果自动进入 facts namespace 会污染最高价值区。 |
| Unregistered External Process | 任何未经注册的 Process 直接写 memory/ 不被认可。 |

### 当前系统实际约束

Filesystem 写入在架构层面不被禁止（trusted local environment），但在 Ownership Contract 层面不被承认。即：

```
Filesystem permission ≠ Memory ownership permission
```

物理写入能力不代表 Memory 写入授权。

---

## Section 5: Writer Registry

所有 Writer 必须先注册，才获得 Namespace 权限。

注册记录包含：

```yaml
writer:
  id:          # 唯一标识
  class:       # runtime | generated | worker | human | import | external-event-producer
  namespaces:  # 允许写入的 namespace 列表
  mutation:    # 允许的变更类型（append | update | create | delete）
  provenance:  # 写入来源说明
  domain:      # external-event-producer 专属：指定 events/ 子域，如 lottery
```

当前已注册 Writer：

| ID | Class | Namespace | Domain | Mutation |
|----|-------|-----------|--------|----------|
| huo (Runtime) | runtime | state, events, data | — | update, append |
| jin (Runtime) | runtime | events | — | append |
| dreaming | generated | MEMORY.md, memory/dreaming/ | — | controlled, append |
| billing | worker | cache | — | disposable |
| token-observe | worker | cache | — | disposable |
| lottery-worker | external-event-producer | events | lottery | append only |
| governance-worker | worker | data | governance | append (pipeline log), update (state snapshot) |
| collect-sensors | worker | data | system | append (telemetry jsonl) |

---

## Section 6: Future Extension Rule

新 Writer 加入流程：

1. 确定 Writer Class
2. 声明目标 Namespace（必须符合 Permission Matrix）
3. 注册到 Writer Registry
4. 实现写入逻辑
5. 通过 Ownership Contract 校验

禁止：

- 新 Writer 跳过注册直接文件写入
- Writer 跨 Namespace 越权写入
- Writer 声明 class 但实际行为不符
