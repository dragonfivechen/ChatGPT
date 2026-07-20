# Contract Enforcement Skeleton — Design v0.1

**Date:** 2026-07-21
**Source:** 契约 vs 执行验证（7份契约仅2份ENFORCED）
**Status:** ✅ L2 VALIDATION LOOP COMPLETE — 首次闭环完成 (2026-07-21)
**Result:** No L3 escalation required
**Mode:** Continuous evidence-driven evaluation

---

## Purpose

> **Contract Enforcement Skeleton 不是 Enforcement 实现，而是为未来 Enforcement 建立可观测升级路径。**

建立契约从声明到执行的演进路径。仅定义验证框架。

不改变 Runtime，不阻断执行，不自动修复，不解冻 Phase 6.4。

## §1 问题

当前 7 份核心契约中 5 份停留在 L1（声明层），无 L2（验证层），无法自然演进到 L3（执行层）。

```
契约生命周期:

L0 Design
    |
    v
L1 Rule Only         ← 当前大部分契约 (5/7)
    |
    |  (缺少 L2)
    |
    v
L3 Enforcement       ← IDENTITY, FREEZE (2/7)
    |
    v
L4 Hard Boundary     ← 未定义
```

当前缺口：

```
L1 ────────────────> L3
       缺少 L2
```

Skeleton 的目标不是增强约束，而是补 L1 → L2 这一步。

## §2 目标

建立一个最小契约验证层，使现有契约从「规则文档」升级为「可验证、可升级的约束」。

```
action/event/write/tool
        ↓
契约注册表 (contract_id + version + strength + owner)
        ↓
validator (pass / reject / violation)
        ↓
contract_violation.jsonl (append-only, observe only)
```

验证层保持 post-hoc 模式：

```
行为发生 → Validator → 记录 violation → 分析
```

不是：

```
行为请求 → Validator → 拒绝
```

不改变当前运行时。

## §3 执行点

| 契约 | 当前层级 | 验证入口 | 验证逻辑 |
|------|:--------:|----------|----------|
| MEMORY-OWNERSHIP | L1 | write → events/ | 写入者身份 == 目录身份？ |
| REASONING-ISOLATION | L1 | memory write | source 是否标记为 reasoning？ |
| WRITER BOUNDARY | L1 | file write | writer 是否在注册列表中？ |
| CAPABILITY-REGISTRY | L1 | tool call | 工具是否在 registry 中？ |
| TOOL-CALL-GATEWAY | L1 (design) | tool call | capability 派生（非 Gateway 实现） |

**TOOL-CALL-GATEWAY 特别标注：** Skeleton 只验证 capability derivation（工具声明 vs registry），不是实现 Gateway 拦截逻辑。避免与 Phase 6.4 混淆。

## §4 不覆盖

```
- Runtime tool call 拦截（Phase 6.4，保持 🔒 FROZEN）
- 实时阻断（post-hoc only）
- 自动修复（违反只记录，不修改）
- 自动改变规则
- 自动提升权限
```

## §5 contract_violation.jsonl 状态定义

```
用途:
  - 记录契约偏离事实
  - 提供升级证据
  - 支持后续 Enforcement 决策

禁止:
  - 自动修复
  - 自动改变规则
  - 自动提升权限
  - 作为实时阻断依据
```

## §6 关联

- Dependent on: bypass register (BYPASS-REGISTER-v1.0.md)
- Follows: governance pipeline (memory_governance_worker.py) pattern
- Not: Phase 6.4 unfreeze

## §7 定位

```
Phase 6.4      🔒 FROZEN     (设计已冻结，不解冻)
Skeleton       📝 Observe Only (仅验证，不阻断)
Future         Evidence-driven Enforcement (基于违规证据的升级决策)
```
