# Constraint Verification: MEMORY-OWNERSHIP

> 验证写入来源、owner、生命周期是否真实执行
> Date: 2026-07-21 07:24 CST

```yaml
contract: MEMORY-OWNERSHIP
authority: A1
level: L1
verification_method: source_trace
```

## Verification

### 1. Memory 写入入口

memory namespace 写入路径：

```text
Agent/Plugin
    │
    ├── tools/memory_write (plugin agent tool)
    │      → plugin invocation → slot resolve
    │
    ├── events (session event recording)
    │      → append to memory/events/{agent}/{date}.md
    │
    └── config/runtime state
           → state/ directory (module-level)
```

### 2. Namespace Ownership 验证

| Namespace | Owner | 写入来源限制 | 验证 |
|-----------|-------|-------------|:----:|
| events | Runtime/Agent | append-only, 通过 tools/ 或身份绑定模块 | ✅ |
| state | Runtime/Agent | module/identity scoped | ✅ |
| facts | Human/Confirmed | 需显式确认后写入 | ✅ |
| preferences | User | 用户主动修改 | ✅ |
| knowledge | Importer/Human | 外部知识导入 | ✅ |
| cache | Runtime | 临时数据，可清理 | ✅ |

### 3. 禁止路径验证

| 禁止操作 | 验证方式 | 结果 |
|---------|---------|:----:|
| 直接修改已写入 event 行 | events 文件为 append-only | ✅ |
| TG 自动写入 memory | TG 不拥有 memory 写入权限 | ✅ |
| 跨 namespace 写入 | namespace 绑定 agent/identity | ✅ |

### 4. 实际写入流程

```typescript
// Session event 写入:
//   events/{agent}/{date}.md — append-only
//   无 edit/delete API

// Plugin memory tool:
//   memory_write 需经过 agent 运行时授权
```

## Result

```yaml
verification:
  contract: MEMORY-OWNERSHIP
  result: PASS
  evidence:
    - src/agents/ (tool registration)
    - memory/events/ 结构 (append only, agent-scoped)
    - identity binding rules
  finding: |
    Memory namespace 边界由 runtime 强制。
    append-only 模式确保 events 不可篡改。
    namespace 绑定 agent/identity 防止跨域写入。
    但 memory_write 插件工具的执行控制依赖 plugin 授权链，非独立 memory gate。
  timestamp: 2026-07-21 07:24 CST
```
