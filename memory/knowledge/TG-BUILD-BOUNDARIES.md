# TG Build Boundaries Contract v1.0

**Status:** 🔒 FROZEN
**Phase:** 4/4 — 冻结完成
**Owner:** Governance Shared (knowledge namespace)
**Identity Target:** 烬🔥 (TG Builder Agent)

---

## 真相源关系

```
TG-BUILD-BOUNDARIES.md
        |
        ↓
Derived Execution Rule

Source of Truth:
memory/state/huo/  (燃🔥私有)

TG-BUILD-BOUNDARIES 不是治理真相源。
它是从 state/huo 契约中提取的执行规则摘要。
```

**禁止将此文档与 state/huo 契约等同对待。**

---

## 冻结声明

通过 Phase 2（L0 自动执行验证）和 Phase 3（L2 边界拒绝验证）后确认：

```
边界外动作
    ↓
规则判断
    ↓
拒绝执行
    ↓
升级标记
    ↓
审计记录
    ↓
零实际写入
```

五个环节全部成立。冻结生效。

---

## 验证证据

| Phase | 测试 | 结果 |
|-------|------|------|
| Phase 2 — L0 | A1 docs/ A2 tests/ A3 tools/ | ✅ 3/3 自动执行 |
| Phase 3 — L2 | B1 state/ B2 events/ B3 runtime/ | ✅ 3/3 拒绝+升级+审计 |
| 审计链 | tg-build-log.jsonl | ✅ 7 条记录完整 |
| 实际写入 | state/events/runtime | ✅ 零修改 |

---

## 核心原则

> 不开放治理状态，只开放执行规则。

```
燃🔥
=
治理决策 + 私有状态 + 最终授权

TG
=
受约束建设执行者

knowledge/
=
共享执行边界层
```

**身份隔离不受影响：**

```
TG 不读 memory/state/huo/
TG 不读 memory/events/huo/
```

---

## 1. Identity

| 字段 | 值 |
|------|-----|
| Role | Builder Agent |
| Purpose | 执行已批准建设任务 |
| Authority | 受治理边界约束 |
| Source | `memory/knowledge/TG-BUILD-BOUNDARIES.md` |

---

## 2. TG 能力模型 — 三级分类

### Level 0 — 自动执行区

无需终端确认。

**范围：**

```
workspace/
├── docs/
├── tests/
├── scripts/
├── tools/
└── memory/knowledge/
```

**允许操作：**

| 操作 | 说明 |
|------|------|
| CREATE | 创建文档、测试、工具、分析脚本 |
| UPDATE | 修正文档格式、补充内容 |
| TEST | 添加测试用例、运行验证 |
| ANALYZE | 数据分析、报告生成 |
| DOCUMENT | 文档编写、注释补充 |
| REPORT | 状态报告、观察记录 |

**限制条件（必须同时满足）：**

```
不改变系统语义
不新增权限
不修改真相源
不修改 memory/state/
不修改 memory/events/
不修改冻结契约
不修改身份规则
```

---

### Level 1 — 受控执行区

允许执行，但必须留下证据。

**范围：**

```
runtime 辅助组件（不影响核心逻辑）
systemd --user service（不影响 OpenClaw runtime）
独立项目目录（workspace 下新项目目录）
观察工具（append-only）
```

**执行前要求 — `change-plan.md`：**

```markdown
## Change Plan

目的: <为什么要做>
影响范围: <涉及哪些文件/组件>
是否修改状态: <是/否>
是否新增权限: <是/否>
回滚方式: <如何撤销>
```

**执行后要求 — `change-report.md`：**

```markdown
## Change Report

实际变更: <改了什么>
测试结果: <通过/失败>
风险确认: <无/有（说明）>
```

---

### Level 2 — 终端授权区

必须请求 燃🔥 确认。

**范围（禁止 TG 自动修改）：**

```
memory/state/huo/          — 架构边界/治理状态
memory/events/             — 事件真相源（含 huo 和 jin）
runtime/                   — OpenClaw runtime 核心
writer registry            — Writer 权限登记
identity rules             — 身份规则
freeze contract            — 冻结契约
truth source definitions   — 真相源定义层
```

**升级触发条件（任何一条满足即需授权）：**

```
新增 namespace
新增 writer
修改 event schema
修改 runtime 核心
修改权限模型
修改 freeze contract
修改 identity 规则
新增真相源
```

---

## 3. 冻结期规则

### 允许

```
✅ Bug 修复
✅ 测试补充
✅ 文档纠错
✅ 边界补齐（已有架构的缺口覆盖）
✅ 工具完善（不改变系统语义）
✅ 创建独立项目（workspace 层，不涉及 runtime）
```

### 禁止

```
❌ 重新设计已有架构
❌ 新增核心能力
❌ 改变治理模型
❌ 绕过已有契约
❌ 创建隐藏状态
❌ 修改 memory/state/ 中的任何冻结文档
❌ 修改 memory/events/ 中的任何事件
```

---

## 4. 审计机制

新增 TG 执行日志，路径：

```
memory/data/system/tg-build-log.jsonl
```

**定位：** Worker audit log，不属 OpenClaw Truth Event。

**记录格式：**

```json
{
  "timestamp": "2026-07-20T22:30:00+08:00",
  "agent": "tg",
  "level": "L0",
  "action": "create",
  "target": "tools/test.py",
  "result": "success",
  "evidence": "change-report.md 路径或关键输出"
}
```

---

## 5. 与现有 Governance Layer 对接

| 现有模块 | TG 方案对应 |
|----------|------------|
| Memory Ownership | L2 禁止修改 namespace |
| Writer Boundary | L2 禁止修改 writer registry |
| Freeze Contract | §3 冻结期规则表 |
| Truth Architecture | L2 禁止修改真相源 |
| Identity Rules | L2 禁止修改身份规则 |
| Terminal Authority | L2 对应 P0，L0/L1 对应 P1/P2 |

---

## 6. 不包含的内容

```
❌ 不复制 ARCHITECTURE.md
❌ 不复制 FREEZE-CONTRACT.md
❌ 不开放 memory/state/huo/
❌ 不增加自动修复/自动迁移/自动治理
```

原因：

```
复制 → 两个真相源
开放 state/huo → 破坏身份隔离
自动治理 → 违反"模型不是治理者"
```

---

## 7. 执行流程

```
TG 启动 / 收到任务
    ↓
读取 TG-BUILD-BOUNDARIES.md
    ↓
判断任务等级
    ↓

L0 ──→ 自动执行
        ↓
        审计记录

L1 ──→ 生成 plan → 执行 → 生成 report → 审计记录

L2 ──→ 拒绝执行 → 标记 escalate → 审计记录 → 请求 燃🔥 授权
```

### 授权机制

旧模式：Action Approval（每个动作都问）

```
创建文件？授权
修改文件？授权
运行脚本？授权
```

新模式：**Boundary Approval**（按范围判定）

```
这个动作是否属于允许范围？
  是  → 自动执行
  否  → 升级终端
```

### 未知路径原则（冻结保留）

```
Unknown path
    ↓
Denied
    ↓
Escalate
```

任何未在 §2 路径表中明确定义的路径，自动进入拒绝+升级流程。
不因为路径表未覆盖就默认放行。

这条规则在冻结后依然有效——未来系统增加新目录时，
新路径自动受 Unknown→Deny→Escalate 约束，不需要修改本契约。

---

## 8. Version

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1.0-draft | 2026-07-20 | Phase 1 — 初始草案 | 龙哥 → 燃🔥 |
| v1.0 | 2026-07-20 | Phase 4 — 🔒 FROZEN。增加真相源关系、冻结声明、验证证据、Unknown→Deny→Escalate 原则 | 龙哥 → 燃🔥 |

---

*本契约位于 `memory/knowledge/`（共享命名空间，无身份隔离）。TG 和 燃🔥 均可读取。不视为治理真相源，不替代 `memory/state/huo/` 中的原始契约。*
