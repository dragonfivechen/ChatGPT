```yaml
contract:
  name: CHANGE-CONTRACT
  version: v1.0
  purpose: 记录和证明变更——为什么改、谁决定、改了什么、如何验证、如何回退
  scope: 所有 D2 及以上决策触发的变更操作
  level: L1
  parent: DECISION-CONTRACT
  owner: 燃🔥
  status: active
  type: change / record_governance
  authority_impact: A1
  created: 2026-07-21

verification:
  required: true
  method: manual
  evidence:
    - "DECISION-CONTRACT.md"
    - "memory/events/huo/"

binding:
  target: model-context

enforcement:
  mode: advisory
  mechanism: bootstrap-prompt
```

# CHANGE-CONTRACT v1.0

> 变更契约 — 记录和证明变更，而不是自动管理变更
> 等级: L1（基线治理级）
> 上位约束: DECISION-CONTRACT
> 权限影响: A1（要求行动/证明）

**定位：**

```text
EVIDENCE-CONTRACT
    ↓
DECISION-CONTRACT
    ↓
CHANGE-CONTRACT       ← 新增
    ↓
MAINTENANCE（观察验证）
```

**原则：** 只记录和证明，不审批、不自动化、不流水线。

---

## 1. 触发条件

仅当 DECISION-CONTRACT 判定为 D2 及以上时须记录 Change Record。D1 变更只需记录于事件日志。

---

## 2. Change Record 格式

```yaml
change_id:
  str          # 唯一标识，格式: <domain>-<action>-<seq>

decision_id:
  str          # 对应 DECISION-CONTRACT 的决策记录

evidence_ref:
  str          # 证据来源，引用 EVIDENCE-CONTRACT

before:
  state:       # 变更前的状态描述
  reference:   # 原始文件/配置的快照路径（如有）

change:
  scope:       # 变更范围描述
  action:      # 具体操作描述
  files:       # 涉及的文件列表

after:
  state:       # 变更后的状态描述

verification:
  method:      # 如何验证变更有效
  criteria:    # 验收标准
  result:      # 验证结论（验收后填写）

rollback:
  method:      # 回滚方式
  confidence:  # high / medium / low
```

---

## 3. 本事件的 Change Record（示例）

```yaml
change_id: event-classify-prompt-001

decision_id: DECISION-CONTRACT-20260721-01
evidence_ref: EVIDENCE-CONTRACT §2 — ollama-production.jsonl, 48 recs

before:
  state: prompt 存在歧义，38% 逐行分类
  reference: scripts/local-task-worker.sh (修复前)

change:
  scope: event_classify 任务 prompt
  action: 替换原 prompt 为强约束格式
  files:
    - scripts/local-task-worker.sh:35-42

after:
  state: prompt 明确要求单分类输出，标签含义固定

verification:
  method: 观察后续 24h 生产输出
  criteria: 逐行分类比例下降至 <10%
  result: 待观察

rollback:
  method: git checkout 恢复原 prompt
  confidence: high
```

---

## 4. 本契约不做什么

| 不做的 | 原因 |
|:-------|:-----|
| ❌ 自动审批 | 决策由 DECISION-CONTRACT 完成 |
| ❌ 自动修复 | 修复超出契约范围 |
| ❌ 变更机器人 | 无独立变更服务 |
| ❌ 强制流水线 | 当前以人工验证为主 |
| ❌ 回滚自动化 | 仅记录回滚方式 |

---

## 5. 本契约做什么

| 做的 | 价值 |
|:----|:-----|
| ✅ 记录变更来源 | 追踪链条完整 |
| ✅ 记录改前改后 | 变更可审计 |
| ✅ 记录验证结果 | 修复可证明 |
| ✅ 记录回滚方式 | 任何时候可撤回 |
