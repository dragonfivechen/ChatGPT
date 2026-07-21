# CONTRACT-LEVEL-CLASSIFICATION v1.0

> ```yaml
> contract:
>   name: CONTRACT-LEVEL-CLASSIFICATION
>   version: v1.0
>   level: L0
>   parent: null
>   scope: all contracts
>   owner: 燃🔥
>   status: active
> ```
>
> 契约等级分类 — 定义系统内所有契约的权重等级
> 目的: 防止普通约束和仲裁规则权重不清，确保 TG 建设时知道哪些不可违反、哪些可调整

---

## 等级总览

```text
M0  Meta Governance Contract      元治理级
        │
        │ 定义契约产生规则、等级判定、生命周期
        │
        v
L0  System Authority Contract    系统仲裁级
        │
        v
L1  Baseline Governance Contract  基线治理级
        │
        v
L2  Module Adaptation Contract    模块适配级
        │
        v
L3  Implementation Alignment      建设执行级
        │
        v
L4  Operational Evidence          运行证据级
```

---

## M0 — 元治理级（Meta Governance）

### 定位

契约体系的治理层，管理其他契约如何产生、分类、归属、变更。

**不定义业务规则，定义规则如何产生。**

### 包含

| 契约 | 职责 |
|------|------|
| `META-CONTRACT.md` | 契约分类 / 等级判定 / 生成约束 / 越权仲裁 / 生命周期 |

### 约束

- M0 高于 L0，M0 定义规则产生方式，L0 定义规则内容
- M0 不直接约束功能模块，只约束如何创建和管理契约
- 违反 M0 意味着契约体系自身混乱

### 修改要求

**元治理层变更，必须人工终端确认。**

---

## L0 — 系统仲裁级（System Authority）

### 定位

最高优先级业务约束规则，任何 L1-L4 契约不得覆盖。

元治理关系: M0 定义 L0 的变更规则，L0 定义具体冻结/仲裁规则。

### 包含

| 契约 | 职责 |
|------|------|
| `FREEZE-CONTRACT.md` | 什么允许修改 / 什么禁止修改 / 冻结定义 / 修复vs扩展 / 发现分类 |

### 约束

- L0 规则不可被 L1-L4 放宽或覆盖
- 示例：L3 要求方便开发 ≠ 可以违反 L0 冻结规则

### 修改要求

**必须人工确认（终端）。**

---

## L1 — 基线治理级（Baseline Governance）

### 定位

所有功能模块共同遵守的基线框架。

### 包含

| 契约 | 职责 |
|------|------|
| `FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md` | 14 项验收维度：Extension Boundary, Ownership, Namespace, Interface, State Ownership, Data Provenance, Determinism, Authority, Risk, Recovery, Test, Config, Audit, Freeze |

### 特点

- 所有模块默认继承，无需单独声明
- 不能降低 L0 要求

### 修改要求

**基线评审（终端确认）。**

---

## L2 — 模块适配级（Module Adapter）

### 定位

针对特定领域在 L1 基础上增加约束。

### 包含

| 契约 | 领域 | 增加约束 |
|------|------|----------|
| `TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md` | TG 模型 | Capability Boundary / Decision Boundary / Tool Boundary |
| `TRADING-RUNTIME-V0.5-ARCH.md` | Paper Trading | Risk Boundary / Market Data Contract |
| `lottery-module`（未来） | 彩票 | （待定义） |

### 约束

- **只能增加约束，不能降低 L0/L1 要求**
- 未适配的模块按 L1 通用标准验收

### 修改要求

**模块 Owner 确认。**

---

## L3 — 建设执行级（Implementation Alignment）

### 定位

给建设过程使用的规则，让实现提前符合 L1/L2。

### 包含

| 契约 | 职责 |
|------|------|
| `TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md` | 建设前声明边界 / 分阶段产出证据 / 完工前自检 / 禁止自行优化架构 / 违规分级 |

### 作用链

```text
需求
  ↓
选择 L2 Adapter
  ↓
L3 约束生成 Baseline Checklist
  ↓
实现
  ↓
自检 (SELF-BASELINE-CHECK)
  ↓
L1/L2 验收
```

### 修改要求

**建设流程调整（TG + 模块 Owner 协商）。**

---

## L4 — 运行证据级（Operational Evidence）

### 定位

运行后产生的事实证明。

### 包含

| 类型 | 内容 | 实例 |
|------|------|------|
| 测试记录 | Test result + version + environment | `run_strategy.py --verify` 输出 |
| 审计记录 | 审计链事件 | `runtime_events.jsonl` |
| 运行日志 | 运行时日志 | `notify_*.jsonl`, `risk_snapshots.jsonl` |
| 性能数据 | Token 观测 / 响应时间 | `token_observe.jsonl` |
| Observation 数据 | 治理观测事实 | `integrity_observe.jsonl` |

### 作用

证明"系统实际运行符合设计要求"。

### 修改要求

**可持续补充，无需审批。**

---

## 优先级规则

契约冲突时，按等级裁决：

```text
M0 → L0 → L1 → L2 → L3 → L4
```

高等级覆盖低等级。

示例：

```text
L3 要求方便开发 → 与 L0 冻结规则冲突 → L0 优先 → 不可违反冻结
L2 TG 适配约束  → 与 L1 基线规则无冲突 → 均可生效
L4 缺少证据记录 → 不构成基线违规 → 补充即可
```

**M0 特殊说明：** M0 不直接参与业务规则冲突，当 L0-L4 契约的产生方式、分类归属、变更流程发生争议时，M0 作为仲裁依据。

---

## 违规严重度映射

| 违反等级 | 严重度 | 含义 | 处理 |
|:--------:|:------:|------|------|
| **M0** | 🔴 契约体系违规 | 破坏了契约治理规则 | 立即停止，终端介入，恢复治理秩序 |
| **L0** | 🔴 基线违规 | 破坏了系统仲裁规则 | 立即停止，终端介入，根因修复 |
| **L1** | 🔴 模块不合规 | 模块未满足基线框架 | 验收失败，修复后重新验收 |
| **L2** | 🟡 模块适配缺失 | 领域约束不全 | 补契约，升级适配 |
| **L3** | 🟡 建设流程偏差 | 建设阶段行为失当 | 纠正流程，补证据 |
| **L4** | 🟢 证据完善问题 | 证据缺失或不全 | 补充记录，不影响冻结 |

---

## 等级生命周期（Level Lifecycle）

### 等级状态

每个等级经历以下阶段：

```text
Proposal（提议）
    │
    │ 新等级需求识别，scope_gap_proof 提交
    ▼
Review（M0 仲裁）
    │
    │ 审查 5 条件：scope_gap / authority / ownership / lifecycle / parent_chain
    ▼
Active（生效）
    │
    │ 等级可用，可录入契约
    ▼
Frozen（冻结）
    │
    │ 等级锁定，不可新增契约
    ▼
Deprecated（废弃）
    │
    │ 等级不再使用，已有契约迁移或归档
    ▼
Archived（归档）
```

### 各阶段说明

| 状态 | 契约可登记？ | 修改要求 |
|------|:-----------:|----------|
| Proposal | ❌ | 等待 M0 仲裁 |
| Active | ✅ | 经 M0 确认 |
| Frozen | ❌（新契约） | 不可修改 |
| Deprecated | ❌ | 已有契约迁移 |
| Archived | ❌ | 历史记录 |

### 等级废弃条件

等级废弃需同时满足：

1. 该等级下无活跃契约（active 状态）
2. 残留契约已迁移到其他等级或已归档
3. 等级定义不再适用于现有系统
4. 经 M0 人工确认

### 等级只增不减规则

等级是治理结构，不是功能版本。

- 废弃的等级不删除，只标记 `deprecated` / `archived`
- 防止历史审计断裂
- 新等级应优先使用 type 扩展而非新增数字等级

---

## 完整体系图

```text
M0  META-CONTRACT
      └── 契约产生规则 / 等级判定 / 越权仲裁 / 生命周期
        │
        v
L0  FREEZE-CONTRACT
      └── 系统仲裁规则
            │
            v
L1  FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
      └── 14 项通用验收维度
            │
            ├── L2  Human Audit（验收适配）
            │     ├── TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT
            │     ├── trading-runtime (TRADING-RUNTIME-V0.5-ARCH)
            │     └── lottery-module（待定）
            │
            └── L3  Build Alignment（建设预防）
                  └── TG-IMPLEMENTATION-ALIGNMENT-CONTRACT
                        │
                        v
                  L4  Evidence（运行证明）
                        ├── Test Records
                        ├── Audit Events
                        ├── Run Logs
                        ├── Performance Data
                        └── Observation Data
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始等级分类，L0-L5 五层定义 |
| v1.1 | 2026-07-21 | 增加等级生命周期：Proposal→Active→Frozen→Deprecated→Archived |
