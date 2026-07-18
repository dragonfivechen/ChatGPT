# Frontmatter Metadata Contract v1.0

**Phase 2.4 — 架构规范，非源码改动**
**Date:** 2026-07-17

---

## 定位

Metadata 是 Memory Provenance 描述层，不是权限系统。

权限已由 Ownership Contract (Phase 2.2) + Writer Boundary (Phase 2.3) 定义。

---

## 前序依赖

Phase 2.4 建立在已冻结的治理链之上：

```
Namespace (Phase 2.1)
        ↓
Ownership Contract (Phase 2.2)   → 谁负责
        ↓
Writer Boundary (Phase 2.3)       → 谁能写
        ↓
Frontmatter Metadata (Phase 2.4)  → 如何描述
```

---

## Section 1: Identity

回答：这条 Memory 是什么？

```yaml
---
id:             # 可选。唯一标识，格式推荐 namespace/agent/YYYY-MM-DD-slug
type:           # 记录类型：log | decision | note | reference | report
namespace:      # 所属语义命名空间，与目录路径一致
---
```

### 规则

- `namespace` 必须与所在目录路径一致（例如 `state/huo/` 下的文件 namespace 应为 `state`）
- `type` 由写者自定，推荐维持小集合
- `id` 可选，用于引用/溯源

---

## Section 2: Provenance

回答：从哪里来的？

```yaml
---
source:         # 来源：runtime | dreaming | human | import | worker
writer:         # Writer ID，对应 Writer Registry 中的注册 ID
created:        # ISO 8601 时间戳
---
```

### 规则

- `source` 必须对应 Writer Classification 中定义的 Class ID
- `writer` 必须对应 Writer Registry 中的注册 ID（参见 MEMORY-WRITER-BOUNDARY.md）
- `created` 为文件首次写入时间

---

## Section 3: Version

回答：是否经历变化？

```yaml
---
version:        # 整数版本号，从 1 开始
supersedes:     # 被替代的文件路径或 ID（可选）
---
```

### 规则

- `facts` 和 `knowledge` namespace 下的文件应追踪版本
- `events` 和 `cache` 不追踪版本（events append-only, cache disposable）
- `supersedes` 仅在显式替代场景使用

---

## Section 4: Lifecycle

回答：如何管理？

```yaml
---
status:         # active | deprecated | archived
ttl:            # 可选。过期时间，例如 "permanent" | "7d" | "30d"
---
```

### 规则

- `status` 默认 `active`
- `deprecated` 表示旧版本不再使用，但保留记录
- `archived` 表示不再参与搜索，仅存留追溯
- `ttl` 仅用于 `cache` namespace，其他 namespace 默认 permanent

---

## 完整示例

```yaml
---
id: state/huo/architecture
type: report
namespace: state

source: runtime
writer: huo
created: 2026-07-17T07:00:00+08:00

version: 1

status: active
ttl: permanent
---
```

---

## 非目标（明确不包含）

Phase 2.4 暂不引入：

- 自动评分 / importance 字段
- AI 自动分类 / tagging
- 自动 promotion / 归档
- 复杂 schema engine / 校验器
- 权限字段（已在 Ownership + Writer Boundary 定义）

---

## Authority Order

继承 MEMORY-OWNERSHIP-CONTRACT.md 中定义的权威顺序：

```
Ownership Policy（最高）
        ↑
Directory Namespace
        ↑
Agent Namespace
        ↑
Frontmatter Metadata（最低）
```

Frontmatter Metadata 是描述层，不应覆盖目录路径已决定的语义分类。
