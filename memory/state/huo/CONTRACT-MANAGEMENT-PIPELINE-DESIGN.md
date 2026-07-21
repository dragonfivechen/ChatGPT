# Contract Management Pipeline — Design v0.1

**Date:** 2026-07-21
**Status:** 🏗 DESIGN — 非冻结变更，非实现任务
**Source:** TG 模型规则生成需求 → 受控写入链路

---

## §0 定位

不是 Phase 6.4 Tool Call Gateway。不是 Runtime 变更。
是一个 Governance Layer 内的受控规则写入链路。

### 核心原则：规则集演进（Rule Set Evolution）

规则变更不是盲写覆盖，也不是无限堆积。每次写入遵循：

```
旧规则
  ↓
读取分析
  ↓
去重 / 冲突检查 / 过时标记
  ↓
保留有效约束
  ↓
合并优化
  ↓
新规则集
  ↓
替换旧规则
```

| 禁止 | 允许 |
|------|------|
| 盲写覆盖 | 增量优化替换 |
| 删除有效约束 | 去重保留有效规则 |
| 创建重复规则 | 冲突检查后合并 |
| 规则堆积 | 维护单一有效规则集 |

这条原则确保规则库持续优化，不退化。

### 双语义层结构

规则文件包含两个互补语义层：

| 层 | 载体 | 作用 | 消费者 |
|:---:|:----:|------|--------|
| 人类语义 | .md Markdown | 设计意图、行为原则、维护共识 | 人 / LLM |
| 机器语义 | .yaml / .json | 可解析、可验证、可执行 | Validator / 工具 |

```
Human Contract (.md)      Machine Contract (.yaml)
"为什么"                   "如何检查"
    │                           │
    └───────────┬───────────────┘
                │
                v
          L2 Validator
```

**关系：** 机器语义不替代人类语义。两者共存，用途不同。配置正确 ≠ 意图正确。


## §1 问题

直接给 TG 模型写文件权限会导致行为边界不稳定。模型知道如何写，但无法判断：
- 该写哪个文件？
- 该写哪个章节？
- 是否有权限写？
- 写入后是否违反其它契约？

需要一条受控链路：用户意图 → 契约分类 → 目标文件 → 校验 → 写入。

## §2 链路

```
用户声明（自然语言）
    ↓
TG Agent 理解意图
    ↓
Contract Router → 确定目标契约 + 章节
    ↓
Rule Patch Generator → 生成结构化修改提案
    ↓
Contract Validator（现有 L2）→ 校验合规
    ↓
Writer Boundary Check → 确认写入权限
    ↓
Contract Writer → 写入文件
    ↓
Events → contract_update.jsonl
```

## §3 四层

### 3.1 Rule Router — 意图 → 契约映射

```yaml
# contract_router.yaml（示例结构）
intent_mapping:
  "禁止读取系统文件":
    target: IDENTITY-CONTRACT.md
    section: forbidden_capabilities
  "禁止写入记忆":
    target: MEMORY-WRITER-BOUNDARY.md
  "禁止推理入事实":
    target: REASONING-ISOLATION-CONTRACT.md
  "禁止调用某工具":
    target: CAPABILITY-REGISTRY.md
```

### 3.2 Patch Generator — 结构化提案

```json
{
  "contract": "IDENTITY-CONTRACT",
  "section": "forbidden_capabilities",
  "change_type": "append",
  "rule": "tg-agent禁止访问events目录",
  "reason": "user declaration"
}
```

### 3.3 Contract Writer — 受控写入

```yaml
writer_policy:
  tg-agent:
    auto_write:
      - TG-BUILD-BOUNDARIES.md
    require_validation:
      - REASONING-ISOLATION-CONTRACT.md
      - MEMORY-WRITER-BOUNDARY.md
    proposal_only:
      - IDENTITY-CONTRACT.md
      - CAPABILITY-REGISTRY.md
    forbidden:
      - FREEZE-CONTRACT.md
      - PHASE-*.md (FROZEN documents)
```

### 3.4 Event — 写入审计

```json
{
  "event": "contract_update",
  "actor": "tg-agent",
  "contract": "IDENTITY-CONTRACT",
  "section": "forbidden_capabilities",
  "change_type": "append",
  "source": "user_declaration",
  "validation": "passed"
}
```

## §4 不覆盖

- Runtime tool call 拦截
- LLM 推理约束
- 自动规则推荐
- 超越现有 writer_policy 的权限

## §5 依赖

- contract_router.yaml（新建）
- contract_patch_generator.py（新建）
- contract_writer.py（新建，调用现有 validator）
- contract_update.jsonl（新建 event 流）

## §6 关联

- 依赖: MEMORY-WRITER-BOUNDARY.md（writer policy 扩展）
- 复用: contract_validator.py（L2 校验）
- 保持: Phase 6.4 🔒 FROZEN
- 不改变: Runtime
