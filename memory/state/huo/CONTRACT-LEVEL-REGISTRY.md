# CONTRACT-LEVEL-REGISTRY v1.0

> 等级注册表 — 记录现有等级的创建理由、治理范围和边界约束
> 归属: M0 META-CONTRACT v1.1 — 等级生成协议配套管理索引

---

## 登记等级

### M0 — 元治理级（Meta Governance）

```yaml
level:
  id: M0
  name: Meta Governance
  parent: null
  created: 2026-07-21
  creation_reason:
    契约体系需要自洽的治理层；
    定义契约分类、等级判定、生成约束、越权仲裁、生命周期；
    不定义业务规则，定义规则如何产生。
  authority:
    管理所有其他契约的产生、分类、归属、变更
  prohibited:
    - 直接约束功能模块
    - 定义业务规则
  status: active
```

---

### L0 — 系统仲裁级（System Authority）

```yaml
level:
  id: L0
  name: System Authority
  parent: M0
  created: 2026-07-21
  creation_reason:
    需要不可越权的系统最高约束规则；
    定义冻结边界、修复vs扩展、审计发现分类；
    任何其他等级不得覆盖。
  authority:
    冻结定义 / 仲裁规则 / 系统不可越权边界
  prohibited:
    - 模块专属规则
    - 实现细节约束
  status: active
```

已登记契约:
- FREEZE-CONTRACT — 冻结规则
- CONTRACT-LEVEL-CLASSIFICATION — 等级定义

---

### L1 — 基线治理级（Baseline Governance）

```yaml
level:
  id: L1
  name: Baseline Governance
  parent: L0
  created: 2026-07-21
  creation_reason:
    所有功能模块共同遵守的系统级规则；
    定义扩展边界、命名空间隔离、接口契约、确定性、审计链等通用准入标准；
    所有模块默认继承，无需单独声明。
  authority:
    系统基线治理规则，跨所有功能模块
  prohibited:
    - 单模块专属规则
    - 实现建设流程
  status: active
  internal_types:
    - governance: 治理规则 (FREEZE rules等)
    - boundary: 边界约束 (TOOL-CALL-GATEWAY, CREDENTIAL-ACCESS, EVENT-SOURCE)
    - capability: 能力治理 (PROVIDER-CAPABILITY, PLUGIN-CAPABILITY)
    - runtime: 运行时规则 (REASONING-ISOLATION, CONTEXT-PROJECTION)
    - data_source: 数据来源 (CONFIG-SOURCE, EVENT-SOURCE, FACT-SOURCE, MEMORY-OWNERSHIP)
    - verification: 验证框架 (PHASE-7.1-AUDIT-CONTRACT)
    - (security, compliance, ...) — 未来可通过 type 扩展
```

已登记契约 (12):
- FUNCTION-MODULE-BASELINE-CHECK — 通用模块准入
- TOOL-CALL-GATEWAY — 工具调用边界
- EVENT-SOURCE — 事件真相源
- CREDENTIAL-ACCESS — 凭据访问规则
- CONFIG-SOURCE — 配置真相源
- MEMORY-OWNERSHIP — Memory 所有权
- PLUGIN-CAPABILITY — 插件能力模型
- PROVIDER-CAPABILITY — Provider 能力治理
- REASONING-ISOLATION — Reasoning 隔离
- CONTEXT-PROJECTION — Context 投影
- FACT-SOURCE — 事实真相源
- PHASE-7.1-AUDIT-CONTRACT — 审计验证框架

---

### L2 — 模块适配级（Module Adapter）

```yaml
level:
  id: L2
  name: Module Adapter
  parent: L1
  created: 2026-07-21
  creation_reason:
    不同功能模块需要领域专属的附加约束；
    在 L1 基线之上增加模块特定的能力、边界、数据规则；
    不是模块分类，而是模块约束层。
  authority:
    模块特定治理规则（能力、数据源、统计、预测边界等）
  prohibited:
    - 系统级治理规则
    - 实现建设细节
    - 跨模块约束（升级至 L1）
  status: active
```

已登记契约 (6):
- TG-MODEL-FUNCTION-MODULE-BASELINE — TG 模型适配
- TRADING-RUNTIME-V0.5-ARCH — Paper Trading 适配
- LOTTERY-CAPABILITY — 彩票能力适配
- LOTTERY-SOURCE — 彩票数据源适配
- LOTTERY-PREDICTION — 彩票预测边界
- LOTTERY-STATISTICS — 彩票统计边界

---

### L3 — 建设执行级（Implementation Alignment）

```yaml
level:
  id: L3
  name: Implementation Alignment
  parent: L1
  created: 2026-07-21
  creation_reason:
    定义建设阶段的约束，预防模块建完后再返工；
    覆盖开工声明、分阶段证据输出、完工自检、禁止自行优化架构；
    降低终端验收修复率。
  authority:
    模块建设过程的约束规则
  prohibited:
    - 运行时行为约束（升级至 L1）
    - 模块能力定义（升级至 L2）
    - 验收标准（由 L1/L2 定义）
  status: active
```

已登记契约 (2):
- TG-IMPLEMENTATION-ALIGNMENT — TG 建设约束
- LOTTERY-WORKER-DIRECTORY — Lottery Worker 建设约束

---

### L4 — 运行证据级（Operational Evidence）

```yaml
level:
  id: L4
  name: Operational Evidence
  parent: L1
  created: 2026-07-21
  creation_reason:
    需要运行后的事实证明来验证契约是否被遵守；
    包括测试记录、审计事件、运行日志、性能数据、Observation 数据；
    不是契约类型，是运行事实记录。
  authority:
    无 — 证据只记录，不约束
  prohibited:
    - 定义规则（升级至 L1/L2）
    - 约束行为（升级至 L1/L2）
  status: active
```

已登记: 无独立契约实体。证据由各模块运行时自然产生。

---

## 等级关系总图

```text
M0  Meta Governance         契约体系的治理层
 │
 └── L0  System Authority   不可越权系统仲裁
      │
      └── L1  Baseline      所有模块通用基线
           │
           ├── L2  Adapter        → 模块专属约束
           │
           ├── L3  Alignment      → 建设过程约束
           │
           └── L4  Evidence       → 运行事实证明
```

---

## 维护规则

| 操作 | 要求 |
|------|------|
| 新增 L0-L4 内 type | 无需审批，在 Registry 中登记 type |
| 新增等级 (新 id) | 经 M0 Level Extension Review, 人工审批 |
| 废弃等级 | 等级生命周期 policy 执行 |
| 修改等级定义 | M0 仲裁 |

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始等级注册表，6 个等级全部归档 |
