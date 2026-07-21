# Observer Abstraction Layer v1.0

> 观察者抽象层 — 从事件中发现能力缺口，提供抽象建议给人工审核
> 定位: L2 辅助观察能力 | 只读 | 无修改权限 | 无契约写入权限
> 归属: 燃🔥 维护范围
> 状态: proposal
> 日期: 2026-07-21

---

## 1. 目标

解决：

```text
大量事件
    ↓
人工逐个分析
    ↓
容易遗漏系统级能力缺口
```

转变为：

```text
事件
 ↓
模型分析
 ↓
能力缺口候选
 ↓
人工确认
 ↓
契约演化
```

---

## 2. 边界

| 维度 | 边界 |
|:-----|:-----|
| 读取 | ✅ 事件流 |
| 写入 | ❌ 事件流 / ❌ 配置 / ❌ 状态 |
| 触发行动 | ❌ 禁止 |
| 创建契约 | ❌ 禁止 |
| 生成报告 | ✅ `observer-gap-report.jsonl` |
| 输入约束 | 仅结构化事件 |

### Observer Influence Boundary（强约束）

```text
Observer output is advisory only.
It has no execution authority and no influence
on model runtime behavior.

Any runtime change MUST pass through
DECISION-CONTRACT and CHANGE-CONTRACT.
```

Observer 输出仅作为人工判断依据，不具备执行权，不影响模型运行行为。任何运行时调整必须经过 DECISION-CONTRACT 与 CHANGE-CONTRACT。

### Observer 可以：

- ✅ 读取事件
- ✅ 聚合模式
- ✅ 提出抽象等级
- ✅ 提供能力缺口候选
- ✅ 生成分析报告

### Observer 不可以：

- ❌ 改变模型 prompt
- ❌ 改变模型配置
- ❌ 改变任务路由
- ❌ 改变评分规则
- ❌ 触发执行动作
- ❌ 直接创建契约
- ❌ 影响 Agent 行为概率

### 与模型运行的关系

正确关系：

```text
模型运行
    ↓
产生事件
    ↓
Observer 分析
    ↓
人工查看
```

错误关系（禁止）：

```text
模型运行
    ↓
Observer
    ↓
自动调整模型行为
```

### 调整后的链路

```text
Event
  ↓
Observer Layer
  ↓
observer-gap-report.jsonl
  ↓
Human Review
  ↓
+----------------+
|                |
v                v
仅供参考        正式治理流程
                |
                v
          Decision / Change / Contract
```

## 3. 演化速度与稳定性

### 演化速度分层

抽象粒度的变化速度应远低于运行参数。演化速度层级：

```text
快

运行参数
  |
  |  日/小时级
  v

Prompt / 任务格式
  |
  |  天级
  v

观察规则
  |
  |  周/月级
  v

抽象粒度模型     ← Observer 核心
  |
  |  月/季度级
  v

核心契约原则
  |
  |  极慢
  v

慢
```

抽象粒度决定的是系统认知边界：事件如何理解、什么算能力缺失、什么值得进入治理。它不是普通配置。

### 稳定层与变化层

| 维度 | 内容 | 变化速度 |
|:-----|:-----|:--------:|
| 稳定层 | 抽象等级定义、分类原则、判断边界 | 极慢（月/季度级） |
| 变化层 | 事件映射、候选缺口、分析报告 | 随事件产生而变化 |

Observer 的抽象等级层次不应根据单次事件调整：

```
G0 事件
G1 模块能力
G2 流程能力
G3 治理能力
G4 架构能力
```

❌ 错误：发现一次 prompt 问题 → 新增 G3 治理缺陷分类

✅ 正确：大量事件积累 → 重复模式出现 → 人工确认现有抽象无法表达 → 调整粒度

### 抽象内容 vs 抽象实例

| 维度 | 稳定度 | 示例 |
|:----|:------|:-----|
| 抽象内容 | 稳定（月/季度级） | `G2 = 流程能力缺失`，等级定义不变 |
| 抽象实例 | 变化（随事件） | `event_classify 输出约束不足 → G2`，随事件映射 |

结构上保持稳定层与变化层分离：

```text
稳定层:
  抽象等级定义
  分类原则
  判断边界

变化层:
  事件映射
  候选缺口
  分析报告
```

---

## 4. 架构

```text
                 Event Source
                      |
                      v
              events.jsonl / 系统事件
                      |
                      v
        +---------------------------+
        | Observer Abstraction      |
        | Layer                     |
        +---------------------------+
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
   异常识别      模式聚合       能力映射
                      |
                      v
           Capability Gap Report
           (observer-gap-report.jsonl)
                      |
                      v
                  Human Review
                      |
          +-----------+-----------+
          |                       |
          v                       v
      Ignore              Contract Proposal
```

---

## 5. 输入格式

```json
{
  "event_id":        "str",
  "timestamp":       "ISO-8601",
  "source":          "str",
  "event_type":      "str",
  "payload":         "object",
  "related_events":  ["str"]
}
```

禁止：修改事件、写入事件、触发行动。

---

## 6. 输出格式

```json
{
  "event_id":      "evt-001",
  "generated_at":  "ISO-8601",

  "observation": {
    "summary":     "event_classify 输出格式不一致"
  },

  "candidate_gap": {
    "level":       "G2 / G3",
    "category":    "analysis_contract",
    "description": "分析输出缺少格式约束"
  },

  "confidence":   0.82,

  "suggestion": {
    "possible_action":  "add output constraint",
    "contract_candidate": null
  },

  "human_review": "pending"
}
```

写入 `observer-gap-report.jsonl`（append-only）。

---

## 7. 抽象等级

| 等级 | 定义 | 示例 | 可能处理 |
|:----:|:-----|:-----|:---------|
| G0 | 事件级，不抽象 | 某脚本执行失败 | 直接修复 |
| G1 | 模块能力级 | worker 缺少输入校验 | 模块优化 |
| G2 | 流程能力级 | 分析结果缺少验证步骤 | 增加流程规则 |
| G3 | 治理能力级 | 系统没有证据约束分析行为 | 建立契约 |
| G4 | 架构级 | 事件源设计无法支持追溯 | 架构评审 |

---

## 8. 抽象稳定性原则

### Abstraction Stability Principle

> 抽象粒度变化必须满足：
> 1. 多案例证据支持
> 2. 现有等级无法表达
> 3. 人工评审确认
> 4. 不因单次事件调整

### 约束范围

| 条目 | 说明 |
|:----|:-----|
| 适用范围 | G0-G4 等级定义、分类原则、判断边界 |
| 不适用范围 | 事件映射、候选缺口、分析报告（变化层自由调整） |
| 违反后果 | Observer 重新校准期，已产生的 gap 报告标记为 unstable |

### Phase 1 观察项

当前 Phase 1（7-14 天）应将 **抽象粒度稳定性** 作为核心观察项之一：

- ✅ 持续跟踪现有 G0-G4 是否足够表达发现的能力缺口
- ✅ 记录任何需要跨越抽象等级调整的冲动
- ❌ 不在观察期内新增抽象等级
- ❌ 不因单次事件修改等级定义

若 14 天后发现 G0-G4 确实无法覆盖某些模式，按稳定性原则流程调整。

---

## 9. 人工审核门

能力缺口候选进入 Proposal 需满足：

| 条件 | 说明 |
|:----|:-----|
| 1. 重复出现 | 非单次偶发 |
| 2. 跨模块影响 | 影响 >1 模块 |
| 3. 当前规则无法表达 | 无已有契约覆盖 |
| 4. 有明确收益 | 可量化或可感知 |

未通过 → `archive`。

---

## 10. 与现有契约体系的关系

- **不进入 Contract Registry。** 不是治理契约，是观察工具。
- **不经过 META-CONTRACT 分类。** 不约束行为，不定义规则。

```text
META-CONTRACT
       |
Existing Contracts (27/27)
       |
Event Stream
       |
       v
Observer Layer     ← 新增，契约体系之外
       |
       v
Capability Gap Report
       |
       v
Human Decision
       |
       +--→ Ignore (archive)
       +--→ Contract Proposal → META-CONTRACT 分类 → Registry
```

---

## 11. 实施阶段

### Phase 1（观察）— 当前

- 仅生成报告：`observer-gap-report.jsonl`
- 周期：7–14 天

### Phase 2（人工验证）

统计评估：

| 指标 | 说明 |
|:-----|:-----|
| 命中率 | 人工确认有效的报告比例 |
| 误报率 | 人工驳回的比例 |
| 抽象准确率 | 抽象等级匹配度 |

### Phase 3（扩展）

若 Phase 2 有效，考虑：

- 自动聚类
- 趋势分析
- 契约建议生成

---

## 12. 首个验证案例

使用 `event_classify prompt 优化` 事件测试抽象能力：

| 抽象等级 | 输出 | 人工确认 |
|:--------:|:-----|:--------:|
| G1 | prompt 约束不足 | ✅ |
| G2 | 模型任务接口缺少输出规范 | — |
| G3 | 分析任务缺少证据约束 → **实际产出: EVIDENCE-CONTRACT** | ✅ |
| G4 | 不适用 | — |

---

## 文件位置

- 本方案：`memory/state/huo/OBSERVER-ABSTRACTION-LAYER-v1.0.md`
- 输出数据：`memory/data/system/observer-gap-report.jsonl`（append-only）

## 与 MEMORY.md 中的 Phase 8 观察层的关系

- Phase 8: 定量观察（确定性指标、阈值、Integrity State）
- Observer Layer: 定性观察（模式识别、能力映射、抽象建议）
- 两者互补，不重叠，不冲突。
