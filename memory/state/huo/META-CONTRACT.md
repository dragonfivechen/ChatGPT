# META-CONTRACT v1.2

> ```yaml
> contract:
>   name: META-CONTRACT
>   version: v1.2
>   level: M0
>   parent: null
>   scope: contract governance
>   owner: 燃🔥
>   status: active
> ```
>
> 元契约 — 定义如何识别、生成、归类、约束其他契约
> 定位: 契约体系自身的治理层（元治理层 M0），不定义业务规则，定义"规则如何产生"
> 核心目标: 新契约出现时，自动判断应处于哪个治理层级

---

## 一、元契约定位

### 与传统契约的关系

```text
M0  META-CONTRACT（本契约 — 元治理层）
   │
   │ 定义契约产生规则、等级判定规则、生命周期
   │
   ▼
L0  FREEZE-CONTRACT                   系统仲裁级
L1  FUNCTION-MODULE-BASELINE-CHECK    基线治理级
L2  Module Adapter Contract           模块适配级
L3  Implementation Alignment          建设执行级
L4  Evidence Contract                 运行证据级
```

**区别：**

| | 元契约 | 普通契约 |
|--|--------|----------|
| 作用 | 定义契约如何产生 | 定义业务/治理约束 |
| 对象 | 契约本身 | 功能模块 / 系统行为 |
| 变化频率 | 极少（治理层变动） | 按模块建设节奏 |
| 违反后果 | 治理混乱 | 具体违规 |

---

## 二、契约分类输入（Contract Classification Questions）

任何新契约产生时，逐级回答以下 5 个问题：

### Q1：是否改变系统最高约束？

涉及：

- Core 行为
- Freeze 规则
- 权限根规则
- 治理基本原则

如果是 → **L0**

```
实例: FREEZE-CONTRACT
     ↓
L0 System Authority
```

---

### Q2：是否所有模块都必须遵守？

影响范围：

```text
All Modules
```

如果是 → **L1**

```
实例: FUNCTION-MODULE-BASELINE-CHECK
     ↓
L1 Baseline Governance
```

---

### Q3：是否只约束某一类模块？

范围：

```text
Specific Domain
```

例如：交易、TG模型、彩票

如果是 → **L2**

```
实例: TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT
     ↓
L2 Module Adapter
```

---

### Q4：是否约束建设过程而非验收标准？

对象：

```text
How to Build（建设行为）
```

不是：

```text
What Must Exist（验收标准）
```

如果是 → **L3**

```
实例: TG-IMPLEMENTATION-ALIGNMENT
     ↓
L3 Implementation Alignment
```

---

### Q5：是否只是记录运行事实？

内容：

- 测试结果
- 审计记录
- 运行数据
- Observation 数据
- 性能指标

如果是 → **L4**

```
实例: test result / audit event / runtime log
     ↓
L4 Evidence
```

### 判定流程

```text
New Contract
   │
   ├─ Q1=YES ─→ L0（系统仲裁级）
   │
   ├─ Q2=YES ─→ L1（基线治理级）
   │
   ├─ Q3=YES ─→ L2（模块适配级）
   │
   ├─ Q4=YES ─→ L3（建设执行级）
   │
   ├─ Q5=YES ─→ L4（运行证据级）
   │
   └─ 全部 NO ─→ Q6（现有等级是否可表达？）
                     │
                ┌────┴────┐
                是         否
                │          │
              type 扩展   Level Extension Review

等级判定后, 追加 Q7 权限影响判定:
   A0/A1 ─→ 正常登记
   A2    ─→ 边界审核
   A3    ─→ privilege_control 审核
   A4    ─→ M0 仲裁
```

**注意：** Q1-Q5 是互斥筛选，按顺序命中即终止。Q1 命中不继续检查 Q2-Q5。

### Q6：是否无法被已有等级准确表达？

当 Q1-Q5 全部为 NO（不符合任何已有等级），或判定结果与契约内容明显不匹配时触发。

判断：

- 是否有独立治理对象？（scope_gap_proof）
- 是否有独立生命周期？（lifecycle_definition）
- 是否有独立所有权？（ownership_definition）
- 是否不破坏已有 parent chain？

如果是 → 触发 **Level Extension Review**，经 M0 仲裁可产生新等级

```
实例: 现有 L0-L4 无法表达跨模块协议
     ↓
Level Extension Review
     ↓
M0 仲裁
     ↓
新增 Level（如 LX）
```

**注意：** 等级不是 type 的替代品。纯新治理维度（如 security）应在 L1 内通过 `type: security` 扩充分类，不应创建新数字等级。

### Q7：Authority Impact — 权限影响判定

> 判断契约是否涉及系统控制权、不可逆操作、跨边界权限提升。

权限等级：

```
A0  无权限影响         普通规则、数据格式、模块逻辑
A1  模块权限           单模块能力边界
A2  系统能力           工具调用、服务管理、配置修改
A3  特权能力           root、sudo、credential、系统级写权限
A4  治理控制权         修改契约、冻结规则、等级体系
```

#### 判定方式

```text
契约内容是否涉及以下之一：
  - root / sudo 操作          → A3
  - credential / token 管理    → A3
  - 系统级配置修改             → A2
  - 工具调用/服务管理           → A2
  - 模块内能力边界              → A1
  - 纯描述/格式/记录            → A0
  - 契约体系/等级/冻结规则       → A4
```

**A4 限制：仅允许以下契约进入 A4**

```
META-CONTRACT
FREEZE-CONTRACT
Governance Amendment Contract（未来）
```

**禁止：**
- 普通模块声明自己影响治理（权限提升漏洞）
- 功能扩展契约自动获得 A4
- AI/TG 自动生成契约声明 A4

#### 仲裁流程

```text
新契约
   │
   ├── A0/A1 ─→ 正常等级流程
   │
   ├── A2    ─→ 增加边界审核
   │
   ├── A3    ─→ privilege_control 审核，归入 L1 type: privilege_control
   │
   └── A4    ─→ M0 仲裁，归入 L0/M0
```

#### 与等级的关系

权限影响是正交维度，不替代等级判定：

```
             等级 (Level)
              ↑

M0
L0
L1 ─────────────────→ 权限影响 (Authority Impact)
L2                A0  A1  A2  A3  A4
L3
L4
```

示例：

- CREDENTIAL-ACCESS: L1 + A3（系统基线 + 特权能力）
- TOOL-CALL-GATEWAY: L1 + A2（系统基线 + 系统能力）
- LOTTERY-CAPABILITY: L2 + A1（模块适配 + 模块权限）
- META-CONTRACT: M0 + A4（元治理 + 治理控制权）

同一等级可以有不同权限影响，同一权限影响可以出现在不同等级。

---

## 三、契约生成约束

### 3.1 所有契约必须包含的字段

任何新治理契约文件必须包含符合 `CONTRACT-DECLARATION-SCHEMA.md` 的声明块：

```yaml
contract:
  name:        契约名称
  purpose:     契约目的（一句话，必须）
  scope:       影响范围描述
  level:       M0/L0/L1/L2/L3/L4
  parent:      上位契约（可选，null 表示无）
  owner:       Owner 身份
  status:      proposal / active / frozen / deprecated / archived
```

完整字段定义和约束见 `CONTRACT-DECLARATION-SCHEMA.md`。

**与 OpenClaw Runtime Contract 的关系：**

META-CONTRACT 体系定义的是 **Governance Contract（治理契约）**，与 OpenClaw 源码中的 **Runtime Contract**（TypeScript interface / JSON schema / test fixture）属于不同抽象层，无字段冲突，不替代彼此。

| 维度 | Governance Contract（本体系） | OpenClaw Runtime Contract |
|------|------------------------------|--------------------------|
| 作用 | 治理规则声明 | 运行时 API/数据约束 |
| 格式 | YAML + Markdown | TypeScript / JSON schema |
| 验证 | META-CONTRACT 五问 + 人工 | 编译 + 运行时校验 |
| 位置 | `memory/state/huo/` | `src/` / `test/fixtures/` |

### 3.2 示例

```yaml
# TG-IMPLEMENTATION-ALIGNMENT-CONTRACT
contract:
  name: TG-IMPLEMENTATION-ALIGNMENT
  purpose: 将基线约束转化为 TG 建设阶段可执行的规则
  scope: TG model construction process
  level: L3
  parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
  owner: 燃🔥
  status: active
```

---

## 四、等级不可越权原则

### 4.1 基本规则

```text
Lower Level 不能修改 Higher Level 的要求
```

| 等级关系 | 允许？ | 说明 |
|----------|:------:|------|
| L3 修改 L1 要求 | ❌ | 建设流程不能降低基线标准 |
| L2 修改 L0 规则 | ❌ | 模块适配不能覆盖系统仲裁 |
| L4 修改 L2 约束 | ❌ | 运行证据不能改变模块契约 |
| L0 修改本身 | ✅ | 人工确认下可修订 |
| L1 修改 L1 | ✅ | 基线评审 |
| L2 增加约束 | ✅ | 只能增加，不能降低 |

### 4.2 冲突处理流程

```text
新契约 vs 现有契约
       │
       ▼
等级比较（META-CONTRACT 分类）
       │
       ├── 高等级不冲突 → 共存
       ├── 高等级冲突 → 高覆盖低
       ├── 同级冲突 → 优先更具体的一方
       └── 新契约意图降低高等级要求 → 禁止，升级审核
```

---

## 五、契约生命周期

每个契约经历以下阶段：

```text
Proposal（提议）
   │
Classification（元契约判定等级）
   │
Assignment（分配到对应层级）
   │
Review（评审）
   │
Active（生效）
   │
Freeze（冻结）
   │
Archived（归档）
```

| 阶段 | 行为 | TG 可否执行 |
|------|------|:-----------:|
| Proposal | 识别需求，生成候选契约 | ✅ 可提议 |
| Classification | 通过元契约六问 (Q1-Q6) 判定等级 | ✅ 可自检 |
| Assignment | 分配到层级目录 | ⚠️ 需 Owner 确认 |
| Review | 终端审核 | ❌ 终端执行 |
| Active | 标记生效 | ❌ 终端执行 |
| Freeze | 基线锁定 | ❌ 终端执行 |
| Archived | 标记归档 | ❌ 终端执行 |

---

## 七、完整体系总图

```text
                 META-CONTRACT
                      │
                      │  契约分类 / 生成约束 / 越权仲裁
                      │
                      ▼
             CONTRACT-LEVEL-CLASSIFICATION
                      │
                      │  L0-L4 等级定义
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
    L0 System      L1 Baseline   L2-L4 Instances
    Authority      Governance
    ┌─────────┐  ┌────────────┐
    │ FREEZE  │  │ FUNCTION   │
    │ CONTRACT│  │ MODULE     │
    │         │  │ BASELINE   │
    └─────────┘  │ CHECK      │
                  └────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    L2 Adapter    L3 Build      L4 Evidence
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ TG      │  │ TG      │  │ Test    │
    │ Model   │  │ Impl.   │  │ Records │
    │ Adapter │  │ Align.  │  │         │
    ├─────────┤  └─────────┘  ├─────────┤
    │ Trading │               │ Audit   │
    │ Runtime │               │ Events  │
    ├─────────┤               ├─────────┤
    │ Lottery │               │ Run     │
    │ (未来)  │               │ Logs    │
    └─────────┘               └─────────┘
```

---

## 六、等级生成协议（Level Generation Protocol）

> 定义新等级的产生条件和流程。防止未来因业务增长不断污染等级体系。

### 6.1 基础等级表

固定等级，不可扩展：

```text
M0  META-CONTRACT          元治理级
L0  FREEZE-CONTRACT        系统仲裁级
L1  Baseline Governance    基线治理级
L2  Module Adapter         模块适配级
L3  Implementation Align   建设执行级
L4  Evidence               运行证据级
```

新需求优先通过 **type 字段扩展** 而不是创建新等级。

### 6.2 允许 type 扩展（不创建新等级）

| 场景 | 方式 | 示例 |
|------|------|------|
| L1 内新增治理维度 | 增加 `type: security` | 安全治理增加为 L1 security |
| L2 内新增模块类型 | 增加 `type: module_adapter` | 新增彩票模块 |
| L3 内新增建设流程 | 增加 `type: implementation_alignment` | 新增彩票建设约束 |

### 6.3 新等级创建条件

仅在所有满足时允许创建：

1. **现有等级无法表达** — scope_gap_proof 证明 Q1-Q6 均不匹配
2. **有独立治理对象** — authority_definition 证明层级拥有独立约束边界
3. **有独立生命周期** — lifecycle_definition: 创建/维护/废弃规则
4. **有明确所有权** — ownership_definition: 谁维护
5. **不破坏 parent chain** — 新增后仍可追溯到 FREEZE-CONTRACT → META-CONTRACT

### 6.4 新等级创建流程

```text
发现新契约
      │
      v
六问分类 (Q1-Q6)
      │
      v
已有 Level 匹配?
      │
  ┌───┴───┐
  是       否
  │        │
 登记     Level Extension Review
            │
            ├── scope_gap_proof
            ├── authority_definition
            ├── ownership_definition
            ├── lifecycle_definition
            └── parent_chain_validation
            │
            v
        M0 仲裁（人工终端确认）
            │
            v
        更新 CONTRACT-LEVEL-CLASSIFICATION
            │
            v
        Registry 生效
```

### 6.5 禁止的新等级场景

| 场景 | 原因 | 正确做法 |
|------|------|----------|
| 业务模块专属等级 | 等级不是模块分类 | 归入 L2 + type |
| 临时/未定级需求 | 未满足 6.3 条件 | 归入 L4 Evidence 暂存 |
| 方便开发/建设 | 流程需求不是治理等级 | 归入 L3 + type |

### 6.6 等级协议声明格式

新等级在 CONTRACT-LEVEL-CLASSIFICATION.md 中登记时，必须包含：

```yaml
level:
  id: LX
  name: 等级名称
  parent: 上位等级
  created: 创建日期
  approval: M0 review reference
  scope_gap: 现有等级无法表达的原因
  authority: 本等级治理范围
```

---

## 八、元契约自身约束

### 7.1 元契约属于哪一层？

```
M0  META-CONTRACT（元治理层）
  原因：元契约定义所有契约的产生规则和等级判定，不属于业务约束层
  与 L0 区别: L0 FREEZE-CONTRACT 定义"基线怎么冻结"
              M0 META-CONTRACT 定义"规则怎么产生"
  层级关系: M0 高于 L0，M0 定义规则产生方式，L0 定义规则内容
```

### 7.2 元契约的修改要求

```text
级别: M0（元治理层）
修改: 必须人工终端确认
触发: 契约体系结构需要变更时
频率: 极少
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始元契约，定义契约分类、生成约束、越权原则、生命周期 |
| v1.1 | 2026-07-21 | 增加 Q6 Extension + Level Generation Protocol，支持等级演化 |
| v1.2 | 2026-07-21 | 增加 Q7 Authority Impact，权限影响正交维度 |
