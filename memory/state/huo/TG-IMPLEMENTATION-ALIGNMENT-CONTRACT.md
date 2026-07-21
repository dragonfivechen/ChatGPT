# TG-IMPLEMENTATION-ALIGNMENT-CONTRACT v1.0

> TG 建设对齐契约 — 将基线约束转化为建设阶段可执行的规则
> 定位: 非验收标准，而是 TG 模型在建设功能模块时自我约束的行为规则
> 上位契约:
>   FREEZE-CONTRACT → FUNCTION-MODULE-BASELINE-CHECK-CONTRACT → 本契约
> 核心目标: 降低终端验收发现问题的数量、降低返工修改次数、降低架构偏移概率

```yaml
contract:
  name: TG-IMPLEMENTATION-ALIGNMENT
  version: v1.0
  level: L3
  parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
  scope: TG module construction process
  owner: 燃🔥
  status: active
```

---

## 契约定位

### 与传统验收的关系

| | 验收契约 (Audit) | 本契约 (Build Alignment) |
|---|---|---|
| 时间 | 建设完成后 | 建设过程中 |
| 目的 | 判断是否合格 | 避免不合格 |
| 使用者 | 终端（审计者） | TG 模型（建设者） |
| 输出 | PASS / WARNING / FAIL | 建设行为约束 + 阶段证据 |

### 三层契约体系

```text
                  FREEZE-CONTRACT
                        │
                        │  仲裁规则：冻结定义 / 修复vs扩展 / 发现分类
                        ▼
        FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
                        │
                        │  14 项验收维度 + 检查模板
                        │
               ┌────────┴────────┐
               │                 │
               ▼                 ▼
        Human Audit       TG Build Alignment
        (验收发现问题)     (建设中预防问题)
```

---

## 第一章：TG 建设基本规则

### 1.1 先声明，后实现

TG 开始建设任何功能模块前，必须生成 **Module Boundary Declaration**：

```
MODULE BOUNDARY DECLARATION
============================
模块名称: <名称>
所属目录: <路径>
Owner:    燃🔥（终端）
输入范围: <输入源 / 类型>
输出范围: <输出目标 / 类型>
Core 修改: 是/否（须为否，否则需终端确认）
依赖模块: <列表>
```

**禁止：** 无声明直接开始实现。

### 1.2 选适配契约，再写代码

```text
需求
  ↓
模块分类（业务模块 / 系统模块 / TG 模块）
  ↓
适配契约选择（通用 / TG / trading / lottery …）
  ↓
Baseline Checklist
  ↓
实现
```

**不允许：**

```text
需求 → 直接写代码
```

### 1.3 分阶段产出证据

按以下阶段迭代，每阶段完成必须输出证据记录：

| 阶段 | 产出 | 证据 |
|:----:|------|------|
| Phase 1 | 边界确认 | Module Boundary Declaration |
| Phase 2 | 接口确认 | Schema / Contract 文档 |
| Phase 3 | 实现确认 | 代码 + 目录结构 |
| Phase 4 | 测试确认 | Test Result + 环境信息 |
| Phase 5 | 冻结确认 | PHASE_STATUS + 冻结声明 |

**禁止：** 跳过任一阶段的证据输出。

### 1.4 禁止 TG 自行优化架构

TG 在建设中的权限边界：

允许：
- ✅ 实现需求（按用户指令）
- ✅ 补充缺失文档（文档层，不改变架构）
- ✅ 发现风险并上报（不上报不等于自动处理）

禁止：
- ❌ 扩大实现范围
- ❌ 引入未规划的架构设计
- ❌ 替换已有方案（即使看似更好）
- ❌ 自动优化冻结设计

遵守链：

```text
User Intent > Architecture Constraint > Implementation
```

### 1.5 验收前自检

模块建设完成后，TG 必须先输出 **SELF-BASELINE-CHECK**，再进入终端验收：

```text
SELF-BASELINE-CHECK
====================
Module:   <名称>
Version:  <版本>

A  Extension Boundary     🟢/🟡/🔴
B  Ownership              🟢/🟡/🔴
C  Namespace              🟢/🟡/🔴
D  Interface Contract     🟢/🟡/🔴
E  State Ownership        🟢/🟡/🔴
F  Data Provenance        🟢/🟡/🔴
G  Determinism            🟢/🟡/🔴
H  Authority Boundary     🟢/🟡/🔴
I  Risk Boundary          🟢/🟡/🔴
J  Recovery               🟢/🟡/🔴
K  Test Evidence          🟢/🟡/🔴
L  Config Governance      🟢/🟡/🔴
M  Audit Trail            🟢/🟡/🔴
N  Freeze Integrity       🟢/🟡/🔴

Evidence ref: <文件路径>
```

**禁止：** 不自检直接交终端验收。

---

## 第二章：TG 建设过程约束细则

### 2.1 目录与权限约束

| 操作 | 约束 |
|------|------|
| 新建文件到模块目录 | ✅ 允许 |
| 修改模块目录内已有文件 | ✅ 允许 |
| 修改系统 `memory/state/` 下的契约 | ✅ 允许（补充文档） |
| 修改系统 `memory/` 下的其他目录 | ❌ 需要确认 |
| 修改 OpenClaw 配置 | ❌ P0，需终端 |
| 修改运行中服务状态 | ❌ 禁止 |
| 删除已有文件 | ⚠️ 需要确认（非 owner 不删） |

### 2.2 输出渠道约束

| 输出类型 | 约束 |
|----------|------|
| 模块内部文件 | ✅ 自由 |
| TG 聊天回复 | ✅ 按照 SOUL.md 规则 |
| 推送/通知 | ❌ 走统一出口 (push-gate.mjs) |
| 系统 memory 写入 | ❌ 需要治理流程 |

### 2.3 依赖约束

| 依赖类型 | 约束 |
|----------|------|
| 新增 Python 包依赖 | ⚠️ 声明到 requirements.txt |
| 新增 Node.js 依赖 | ⚠️ 声明到 package.json |
| 调用系统 API | ❌ 需授权 |
| 调用外部 HTTP | ❌ 需白名单 |

---

## 第三章：违规处理

### 3.1 违规分级

| 级别 | 定义 | 动作 |
|:----:|------|------|
| 🟡 轻微 | 未按阶段输出证据 | 提醒 + 补记录 |
| 🟠 中等 | 无边界声明开始实现 | 暂停 → 补声明 → 恢复 |
| 🔴 严重 | 自行修改 Core / 越权执行 / 自动优化冻结架构 | 终端介入，定位根因，治理闭环 |

### 3.2 修复原则

同 FREEZE-CONTRACT.md：

```text
发现缺口 → 根因分析 → 确认责任层
  └── 治理层 → 补契约/规则
  └── 实现层 → 修复代码
  └── 流程层 → 修复流程
验证闭环 → 关闭缺口
```

---

## 第四章：效果度量

### 4.1 Terminal Repair Rate（终端修复率）

公式：

```
终端验收后发现的修复项数量
─────────────────────────── = Repair Rate
验收检查总项数量
```

### 4.2 目标

| 阶段 | 预期 Repair Rate |
|------|:----------------:|
| 契约运行前 | 基线未知（首次度量） |
| 契约运行后 | 降至 0-2 项 / 次验收 |
| 成熟期 | 接近 0 |

### 4.3 数据来源

每次终端验收记录：

```json
{
  "module": "模块名",
  "check_date": "YYYY-MM-DD",
  "total_items": 14,
  "issues_found": 3,
  "repair_rate": 0.21,
  "self_check_result": "PASS / WARNING / FAIL",
  "audit_result": "PASS / WARNING / FAIL"
}
```

累计形成模块建设的质量基线。

---

## 附录：TG 建设检查清单

### 开工前检查

```text
- [ ] Module Boundary Declaration 已生成
- [ ] 适配契约已选择
- [ ] 本期建设目标未超出声明范围
- [ ] 不涉及 Core 修改（如涉及，已报终端）
```

### 每阶段结束检查

```text
- [ ] 阶段证据已输出（文件/日志）
- [ ] 未引入未规划的架构
- [ ] 未越权执行
- [ ] 未污染 Memory / Namespace
```

### 完工前检查

```text
- [ ] SELF-BASELINE-CHECK 已输出
- [ ] 所有 14 项均自检完成
- [ ] 证据文件可访问
- [ ] 冻结状态未破坏
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-21 | 初始契约，将基线检查转化为 TG 建设阶段约束 |
