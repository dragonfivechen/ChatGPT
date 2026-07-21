```yaml
contract:
  name: DECISION-CONTRACT
  version: v1.0
  purpose: 定义从"观察"进入"行动"的决策规则——什么情况下可以改、谁决策、决策等级
  scope: 所有涉及系统变更的行动决策（配置/prompt/非核心逻辑/核心链路）
  level: L1
  parent: FREEZE-CONTRACT
  owner: 燃🔥
  status: active
  type: decision / action_governance
  authority_impact: A1
  created: 2026-07-21

verification:
  required: true
  method: manual
  evidence:
    - "memory/events/huo/"
    - "EVIDENCE-CONTRACT.md"

binding:
  target: model-context

enforcement:
  mode: advisory
  mechanism: bootstrap-prompt
```

# DECISION-CONTRACT v1.0

> 决策契约 — "观察"与"行动"之间的授权边界
> 等级: L1（基线治理级）
> 上位约束: FREEZE-CONTRACT
> 权限影响: A1（要求行动/证明）

**在整个治理链中的位置：**

```text
EVIDENCE-CONTRACT
    ↓
   DECISION-CONTRACT    ← 新增
    ↓
   CHANGE 动作
    ↓
   MAINTENANCE 验证
```

---

## 1. 触发条件（Decision Trigger）

从"观察"进入"行动"必须同时满足以下条件：

| 条件 | 说明 | 检查项 |
|:----|:-----|:-------|
| T1 | 证据确认缺陷/改进点存在 | 引用 EVIDENCE-CONTRACT §2 |
| T2 | 影响范围明确 | 知道改什么、不改什么 |
| T3 | 风险等级可评估 | 至少 D0-D3 |
| T4 | 修改目标明确 | 改前状态 + 改后预期 |

**不满足 T1 时，禁止进入决策流程。** 推测/直觉不构成触发条件。

---

## 2. 决策等级（Decision Classification）

| 等级 | 定义 | 示例 | 要求 |
|:----:|:-----|:-----|:-----|
| D0 | 纯观察，不行动 | 发现可疑模式，等待更多证据 | 无行动 |
| D1 | 文档/注释/命名调整 | 修复注释、重命名变量 | 记录即可 |
| D2 | 配置/prompt/非核心逻辑修改 | 优化 prompt、修改超参、调整 worker | 需要证据 + 可回滚 |
| D3 | 核心链路/架构修改 | 修改事件流、变更 Runtime 行为、变更身份路由 | 需要完整评审 + 冻结操作 |

**等级判定原则：**

- 不确信 → 升一级
- 不可回滚 → 升一级
- 涉及多模块 → 升一级
- 触及 FREEZE 范围 → 自动 D3

---

## 3. 冻结交互（Freeze Interaction）

冻结状态不禁止所有变更，但约束变更等级：

```text
冻结状态下的变更规则：

D1:      允许，无需解冻
D2:      允许，但必须在 Change Record 中声明冻结状态
D3:      严禁。需先经 FREEZE-CONTRACT 解冻流程
```

解冻 ≠ 取消冻结。解冻仅针对特定变更申请，不改变整体的冻结状态。

---

## 4. 变更记录要求

D2 及以上变更必须附带 Change Record，最简格式：

```yaml
change_id:
  str          # 唯一标识

evidence:
  str          # 引用 EVIDENCE-CONTRACT 的证据链路径

decision:
  level:       # D0-D3
  rationale:   # 为什么是此等级

change:
  scope:       # 改什么
  action:      # 怎么改

verification:
  method:      # 如何验证修复有效
  criteria:    # 验收标准

rollback:
  method:      # 回滚方式
  confidence:  # high / medium / low
```

---

## 5. 本次事件的完整闭环

用作首个应用案例：

```yaml
# event_classify prompt 优化闭环

evidence: |
  EVIDENCE-CONTRACT v1.0 §2
  source: ollama-production.jsonl
  records: 48 条 event_classify
  result: 38% 逐行分类 → prompt 歧义

decision:
  level: D2
  rationale: |
    - 非核心链路（仅模型 prompt）
    - 可回滚（恢复原 prompt）
    - 影响范围在 single task
    - 证据充分（48 条生产记录）

trigger:
  - T1 ✅ 证据确认缺陷
  - T2 ✅ 只改 prompt 文本
  - T3 ✅ D2 风险
  - T4 ✅ 改前逐行分类 → 改后单分类输出

freeze: 未触及冻结范围

change:
  action: 替换 prompt 为强约束格式
  rollback: git checkout 恢复原文件
  verification: 观察后续 24h 生产输出
```

---

## 6. 违反与纠正

| 违反类型 | 后果 | 纠正 |
|:---------|:-----|:-----|
| 无证据进入 D2+ | 变更无效，需补充证据 | 回滚后重新决策 |
| 跨等级执行 | 标记 contaminated | 修复后重评等级 |
| 冻结期内执行 D3 | 系统违规记录 | A4 介入 |

---

## 附录 A：决策流模板

```text
[发现] ________________________________
[证据] ________________________________
[决策等级] ___  [触发条件] T1__T2__T3__T4__
[冻结状态] ____
[变更记录] change_id: ________________
[验证方法] ________________________________
[回滚方式] ________________________________
```
