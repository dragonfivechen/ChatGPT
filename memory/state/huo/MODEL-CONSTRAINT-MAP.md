# Model Constraint Map v1.0

> 模型约束的四层结构：配置 → 身份 → 边界 → 验证
> 非契约，非设计，仅为现有约束能力的索引图。

## 四层模型

```
TG Agent
    |
openclaw.json     模型选择          L3 (config-enforced)
    ↓
IDENTITY-CONTRACT 身份权限          L4 (identity-enforced)
    ↓
TG-BUILD-BOUNDARIES 行为边界         🔒 FROZEN (guideline, not truth source)
    ↓
Validator Layer   验证              L2 (post-hoc observation)
    ↓
violation record
```

## 约束目标 → 文件映射

| 目标 | 主要文件 | 当前强度 | 机制 |
|------|----------|:--------:|------|
| 限制模型选择 | openclaw.json | L3 | config |
| 限制身份权限 | IDENTITY-CONTRACT.md | L4 | bindings + identity |
| 限制记忆归属 | IDENTITY-RULES.md + MEMORY-OWNERSHIP-CONTRACT.md | L4/L2 | identity + validator |
| 限制推理进事实 | REASONING-ISOLATION-CONTRACT.md | L2 | validator |
| 限制写入行为 | MEMORY-WRITER-BOUNDARY.md | L2 | validator |
| 限制工具能力 | CAPABILITY-REGISTRY.md | L2 | registry + validator |
| 限制 runtime 调用 | TOOL-CALL-GATEWAY-CONTRACT.md | 🔒 FROZEN | design only |

## 关键原则

1. **TG-BUILD-BOUNDARIES.md 不是最高约束文件** — 自身定位为"执行规则摘要，非治理真相源"
2. **IDENTITY-CONTRACT 是当前最强约束路径** — L4 enforcement 已存在
3. **REASONING / WRITER / CAPABILITY 当前只有 L2** — 可观察不可阻断
4. **TOOL-CALL-GATEWAY 不能作为当前修改入口** — Phase 6.4 🔒 FROZEN

## 用途

- 评估约束某模型需要改哪些文件
- 判断某项约束当前有没有执行能力
- 避免把"写规则"误认为"产生约束"
