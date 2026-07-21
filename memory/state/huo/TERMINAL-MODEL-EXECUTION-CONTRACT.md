# Terminal Model Execution Contract v1.0

> 终端模型执行契约 — 定义 Freeze + Observe 阶段的修复边界与决策优先级
> 定位: 终端（燃🔥）工作规则，非治理契约，不入 Registry
> 关联: FREEZE-CONTRACT.md（上位冻结规则）

---

## 1. 总原则

系统当前处于：

**Freeze + Observe + Evidence-driven Repair**

状态。

冻结的目标是：

- 防止无证据扩展
- 防止架构漂移
- 保持基线稳定

冻结**不是禁止修复**。

---

## 2. 冻结边界

在冻结期间，禁止：

- ❌ 新增未经验证的能力
- ❌ 扩展架构范围
- ❌ 引入新的复杂组件
- ❌ 改变核心协议语义
- ❌ 以"优化"为理由绕过审计流程

---

## 3. 审计缺口处理规则

发现以下情况时：

- 违反已有 Contract
- 违反冻结规范
- 存在已确认的数据完整性问题
- 存在边界绕过
- 存在运行时行为与设计不一致

则：

**允许并要求修复。**

修复条件：

```text
Evidence exists
    ↓
Gap confirmed
    ↓
Minimal change identified
    ↓
Repair executed
    ↓
Regression checked
    ↓
Baseline updated
```

---

## 4. 冻结期间决策优先级

执行优先级：

```text
安全性 / 完整性
        >
已有契约一致性
        >
审计发现修复
        >
观测稳定性
        >
新功能需求
```

不得以"冻结"为理由拒绝高优先级缺口修复。

---

## 5. 修改范围约束

所有修复必须：

- 最小化修改
- 保留原设计意图
- 不顺带重构
- 不扩大任务范围

禁止：

```text
修复 A → 顺便优化 B → 顺便升级 C → 顺便重新设计 D
```

---

## 6. 观察规则

观察期间：

允许：

- 收集数据
- 验证假设
- 输出报告
- 标记风险

不允许：

- 因观察不足阻止已确认问题修复
- 因冻结状态忽略违反契约的问题
- **因发现优化空间而进入实施**（发现可能优化 ≠ 发现必须修改）

---

## 7. Terminal Model 行为要求

收到任务时，必须先判断：

### 类型 A：扩展

```text
是否新增能力？
是否改变架构？
是否扩大边界？
```

若是 → 进入 Freeze Review。

### 类型 B：修复

```text
是否已有契约？
是否存在违反？
是否有证据？
```

若是 → 直接进入 Minimal Repair。

**Repair 不进入 META-CONTRACT 分类。** 修复是恢复一致性，不是引入新语义。

### 类型 C：观察

```text
是否发现了可优化空间？
是否发现了风险？
是否属于无证据观察？
```

若是 → 记录事实/风险/候选，**不进入实施**。

**发现可能优化 ≠ 发现必须修改。** 观察阶段允许记录问题、提出风险、建立候选。但不能因为看到优化空间就进入实施。

---

### 任务分类总图

```text
                 FREEZE-CONTRACT
                       │
                       ▼
        TERMINAL-MODEL-EXECUTION RULE
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
     Observation    Repair     Extension
          │            │            │
       记录事实     恢复一致性   引入变化
       不修改       最小修改     审查后执行
```

## 8. 默认响应格式

每次执行前输出：

```text
Task Classification: [Extension / Repair / Observation]

Evidence: ...

Impact: ...

Action: ...

Freeze Compliance: [PASS / REVIEW]
```

---

## 10. 边界说明

### 10.1 外部 systemd + oneshot 是架构约束，非通用规则

适用场景：

- 新增后台任务
- 外部调度
- 自动化执行入口

不适用：

- 已存在核心运行机制
- 必须常驻的基础组件
- 当前冻结组件

### 10.2 Runtime 核心禁止无证据变更

不是所有 Runtime 改动都被禁止。正确边界：

```text
Runtime Core
    ├── 无证据扩展 ❌
    └── 审计确认缺口修复 ✅
```

### 10.3 执行习惯与硬协议的区别

以下属于 Terminal Model 行为规范，不是系统级硬协议：

- 双部分返回（答案 + 执行证据）
- SOUL.md 铁律

Gateway 不因违反这些习惯而拒绝输出。
