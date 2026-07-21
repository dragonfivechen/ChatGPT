# BUILD-ACCEPTANCE-CONTRACT Design Candidate

**Status:** `candidate` — 观察，不实现
**Layer:** Governance
**Date:** 2026-07-21

---

## 发现

```
TG-BUILD-BOUNDARIES.md 存在
        ↓
建设规范已定义（能做什么/不能做什么/边界在哪里）
        ↓
但缺少独立验收层
        ↓
模型可能将"实现动作"误认为"目标完成"
```

当前已有：

- 建设规范层：`TG-BUILD-BOUNDARIES.md`
- 运行事实层：Runtime / Event Observation

缺少：

- 建设验收层：Build Acceptance

## 候选方案

在 Governance Layer 新增 `BUILD-ACCEPTANCE-CONTRACT.md`，职责：

> 将建设规范中的要求转化为可验证条件。

### 验收对象

```yaml
acceptance_target:
  type:
    - capability
    - workflow
    - integration
    - deployment

  source:
    - user_intent
    - build_contract
```

### 验收状态

```
PLANNED → IMPLEMENTED → INTEGRATED → VERIFIED → ACCEPTED
```

### 证据来源

```
文件状态 + 配置状态 + 注册状态 + 事件记录 + 测试结果
禁止：模型自述"完成"
```

## 范围

此设计不绑定任何特定模型。覆盖：

```
Model Agents
├── Telegram Agent (烬🔥)
├── Terminal Agent (燃🔥)
├── Main Agent
└── Future Agents
```

共同约束：

```yaml
acceptance:
  claim_completion:
    forbidden: true
  completion_requires:
    - evidence
    - verification
    - acceptance_state
```

触发背景：期货案例、TG 写入路径案例均暴露同一类信号——**模型能力 ≠ 系统完成**。

## 与现有架构关系

```text
TG-BUILD-BOUNDARIES
        ↓
建设规则

BUILD-ACCEPTANCE-CONTRACT
        ↓
建设验收
```

两者互补不替代。不涉及 Runtime 变更。

## 当前状态

```yaml
BUILD-ACCEPTANCE-CONTRACT:
  status: candidate
  layer: Governance
  implementation: frozen
  evidence_observed: true
  reason:
    - design gap identified
    - multi-case completion gap signals (futures, write_path, session)
    - implementation threshold not reached
```

> 已有触发信号（3 例），但尚未证明需要完整机制。
> implementation: frozen，不推进设计，不涉及 Runtime。
> 状态语义：candidate + evidence_observed + implementation_frozen

## 触发升级条件

以下条件满足后从 candidate 进入 Design 阶段：

1. 出现 >=N 次建设完成误判案例（模型宣布完成但实际未完成）
2. 现有审计无法定位缺失环节
3. 用户目标无法转换为验收条件

## 归档

```
created: 2026-07-21
author: 龙哥 → 燃🔥
related:
  - TG-BUILD-BOUNDARIES.md
  - MEMORY-WRITER-BOUNDARY.md
  - IDENTITY-RULES.md
```
