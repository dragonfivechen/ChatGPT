# Diagnostics Behavior Layer v2.0

```yaml
contract:
  name: DIAGNOSTICS-BEHAVIOR-LAYER
  version: v2.0
  level: L2
  type: architecture
  parent: FREEZE-CONTRACT
  scope: cross-agent behavior observation & maintenance
  owner: 燃🔥
  status: active
  created: 2026-07-21
  source: 龙哥 架构设计
```

---

## §0 定位

> 通过观察用户与 TG Agent 的交互轨迹，识别行为偏移；
> 在确认存在持续性缺陷后，通过受控维护流程修复；
> 不让用户纠偏数据直接污染模型治理层。

### 核心原则

```
1. 对话不是训练数据
   transcript → 证据/分析/维护依据
   transcript → memory ❌ | global rules ❌

2. 用户纠偏不是修复
   当前上下文内调整成功 ≠ 长期行为改变

3. 修复必须证明存在系统性问题
   重复出现 + 同类模式 + 影响用户体验 + 已有约束不足
```

---

## §1 总体架构

```text
                 用户
                  |
                  v
          Telegram Conversation
                  |
                  v
        +-------------------+
        | Behavior Observer |
        +-------------------+
                  |
                  |
       +----------+----------+
       |                     |
       v                     v
  Error Pattern        Correction Pattern
       |                     |
       +----------+----------+
                  |
                  v
          Behavior Findings
                  |
                  v
          Maintenance Queue
                  |
                  v
       Controlled Maintenance Layer
                  |
                  v
             Verification
```

---

## §2 Phase A: Behavior Observation Layer

**状态: ACTIVE**
**职责:** 采集 → 分析 → 人工审核 → 发现 | **不修改**

### Pipeline

```
Reader
  ↓
Analyzer      ← 机器负责：发现、聚合、排序
  ↓
Finding
  ↓
Human Review  ← Phase A.5 新增 — 人负责：理解、确认、授权
  ↓
Confirmed Finding
  ↓
User-facing Interpretation  ← 新增：翻译为体验描述
  ↓
Maintenance Queue
  ↓
Phase B Gate
```

### 输出原则

```
底层：  JSON 检测标签（机器用）
审核层： Human-readable audit report（人审用）
用户层： User-facing interpretation（体验描述）
指标：   辅助判断，不是结论

Sequence:
  原始事件 → 人类快速理解 → 人工确认 → 进入指标 → 维护决策
```

### 用户层输出规范

回答三个问题：

1. **遇到了什么？** — 不是 duplicate_rate=21.4%，而是 "部分会话存在短时间重复发送现象"
2. **严重吗？** — 不是 severity=medium，而是 "不影响模型理解能力，不证明逻辑错误"
3. **需要修吗？** — 不是 Phase B triggered=NO，而是 "继续观察，等待根因确认"

转化规则：

```
机器层                    用户层
────────────────────────  ────────────────────────
142 burst duplicate       "24/29会话存在短时重复回复"
median interval 2s        "间隔~2秒，非模型重新思考"
C3 = 19                   "部分用户曾要求改变回答方式"
B = 0                     "未发现越权执行"
```

示例输出：

```
🟡 回复稳定性: 存在短时间重复发送现象，影响24/29会话
🟢 行为边界:   未发现越权执行
🟡 用户反馈:   部分用户需要纠正Agent行为方式
维护状态: 继续观察
```

---

## §3 观察维度 D: Intent Fulfillment

**状态: DESIGNED**
**定位:** 观察指标，不是自动判错。需要 Phase A.5 人工确认。

### 背景

当前系统主要观察输出稳定性(A)、讨论/执行边界(B)、用户纠偏(C)，
但缺少"理解→响应"转换的观测。

### D0 Intent Gap 检测流程

```
用户请求
    |
    v
模型响应
    |
    v
是否识别用户目标？
    |
    +---- 否 → 理解失败
    |
    +---- 是
           |
           v
    是否输出满足目标？
         |
    +----+----+
    |         |
    是       否
    |         |
  正常    Intent Gap
```

### D 类拆分

| 类 | 名称 | 说明 | 示例 |
|:---|:-----|:-----|:-----|
| D1 | 理解错误 | 模型未理解用户意图 | 用户要求A，模型回答B |
| D2 | 理解未执行 ⭐ | 模型知道用户要什么，但继续解释/确认/输出无关分析 | 用户"直接推进"，模型解释为什么分阶段设计 |
| D3 | 合理拒绝 | 不是缺陷 | 用户要求危险操作，模型理解但拒绝 |
| D4 | 需求冲突 | 用户要求之间冲突，需要澄清 | — |

### 与 C 的区别

| 类型 | 例子 | 分类 |
|:-----|:-----|:-----|
| 用户纠正模型行为 | "不要这样回复" | C3 |
| 模型没有满足请求 | "我说直接做，你还解释" | D2 |
| 模型不知道用户想什么 | 答非所问 | D1 |

### 输出格式

```
用户目标: （用户实际想要的）
模型理解: ✅/❌
模型输出: ✅/❌ 满足目标
分类: D1/D2/D3/D4
```

### 现有架构中的位置

```
Phase A Observation
  ├── A Response Stability
  ├── B Reasoning Boundary
  ├── C User Feedback
  └── D Intent Fulfillment   ← 新增观察维度
```

### 2.1 数据采集

| 来源 | 状态 |
|:-----|:----:|
| TG transcript | ✅ 已有 |
| runtime event | 📄 待接 |
| tool event | 📄 待接 |
| delivery log | 📄 待接 |

**提取字段:** time, role, text, session
**禁止:** thinking, memory, system prompt

### 2.2 行为分析 — 五类

| 类 | 名称 | 示例 |
|:--|:-----|:-----|
| A | Response Stability | 短窗口重复爆发, median~2s, 24/29 sessions |
| B | Reasoning Boundary Failure | 讨论架构 → 直接改文件 |
| C | User Feedback Classification | 用户反馈分层 （C0-C4 + Intent Filter）|
| D | Intent Fulfillment | 理解→响应落差，重点：理解但未执行(D2) |
| E | Regression | 已修正问题重新出现 |

### 2.3 用户反馈分层（C0-C4 + Intent Filter）

```
C0 Candidate
    |
    v
[Intent Filter] ← 先判断：用户否定对象是什么？
    |
+---+---+
|       |
否定内容   否定行为
|       |
C1/C2  C3/C4
```

**C0 — 全量候选：** 所有疑似反馈，不筛选。

**C0.5 — Intent Filter（新增）：** 在 C1-C4 前判断用户否定对象：

| 否定对象 | 路由 | 示例 |
|:---------|:----|:-----|
| 答案内容 | C1/C2 | "这个方案方向错了" |
| Agent 做事方式 | C3 | "不要拿冻结阻止修改" |
| 交流方式 | C4 | "不要分话题，直接推进" |

**C1 — 内容纠正：** 用户否定模型输出内容。维护价值低。

```
用户: 这个时间不对
```

**C2 — 方案讨论：** 用户否定方案方向。一般不是 Agent 行为问题。

```
用户: 不应该这样设计
```

**C3 — 行为纠正（重点）：** 用户明确否定模型行为模式。

```
用户: 不要拿冻结做挡箭牌
       ↓
模型行为: 利用冻结规则拒绝修改
用户: 否定这种行为模式
```

**C4 — 交互纠正：** 用户否定回复方式/交互风格。

```
用户: 不要分话题，直接推进
```

### 2.5 A 类证据链补充方向

当前 A 类已确认现象但根因未知。需要补充证据链条：

```
assistant event timestamp
    → 关联 message_id
    → 关联 delivery status
    → 关联 retry/log
```

目标区分：

| 可能性 | 判断依据 |
|:-------|:---------|
| 生成重复 | 同一个 message_id，模型产生两次 |
| 发送重复 | 不同 message_id，delivery 层重试 |

**不在 Phase A 阶段修复。** 保持 observe，等待证据链完整。

### 2.4 核心指标：User Behavior Rejection Rate

替代单一 precision 指标：

```
C3数量 / 总会话数
```

比 `C candidates / precision` 更有意义，因为回答的是：

> 用户是否持续反对某种 Agent 行为？

而不是：

> 用户有没有说过

```text
错误行为
    ↓
用户纠偏
    ↓
即时接受 (L1)
    ↓
会话保持 (L2)
    ↓
跨会话保持 (L3)
```

| 级别 | 名称 | 判断 |
|:----|:-----|:-----|
| L1 | 即时纠正 | 当前回复正确 |
| L2 | 会话保持 | 当前聊天持续正确 |
| L3 | 跨会话保持 | 新聊天仍正确 |

### 2.4 Finding 格式

```json
{
  "id": "TG-xxx",
  "type": "correction_failure",
  "category": "execution_boundary",
  "severity": "medium",
  "evidence": {
    "sessions": 3,
    "occurrences": 5
  },
  "status": "observe"
}
```

---

## §3 Phase B: Controlled Maintenance Execution Layer

**状态: DESIGNED**
**触发条件:** confirmed finding + 维护授权

### 3.1 九阶段维护生命周期

```text
[1] Trigger     NEW           — 用户要求/审计/观察升级
[2] Scope       SCOPED        — 限定 target + area
[3] Evidence    EVIDENCE_READY — 收集 transcript/findings/runtime
[4] Diagnosis   DIAGNOSED     — Q1真实? Q2哪层? Q3根因?
[5] Decision    DECIDED       — 误报→关闭 / 偶发→观察 / 缺陷→修复
[6] Execute     PATCHING      — 只改目标范围
[7] Verify      VERIFYING     — 功能+回归+隔离 三层
[8] Monitor     MONITORING    — 7天观察窗口
[9] Close       CLOSED        — 成功关闭 / 失败回滚
```

### 3.2 状态机

```text
NEW → SCOPED → EVIDENCE_READY → DIAGNOSED → DECIDED
                                                |
                                    +-----------+-----------+
                                    |                       |
                                 observe                  patch
                                    |                       |
                                 CLOSED                 VERIFYING
                                                           |
                                                        MONITORING
                                                           |
                                                     +-----+-----+
                                                     |           |
                                                  CLOSED    ROLLBACK
```

### 3.3 诊断三层问答

| Q | 问题 | 回答 |
|:-|:-----|:-----|
| Q1 | 是否真实问题？ | 不是误报 |
| Q2 | 属于哪一层？ | runtime / logic / contract / configuration |
| Q3 | 根因是什么？ | 定位到具体机制，非"模型不听话" |

### 3.4 验证三层

| 层 | 确认 |
|:---|:-----|
| 功能验证 | 问题是否减少 |
| 回归验证 | 是否破坏其他能力 |
| 隔离验证 | TG data 未进入 Memory |

---

## §4 当前系统落点

```text
Phase A
=======
Reader       PASS    (tg_transcript_reader.py)
Analyzer     ACTIVE  (tg_behavior_analyzer.py — 5类 + correction)
Queue        ACTIVE  (tg_maintenance_queue.py — observe 46)
Memory link  BLOCKED
Auto repair  OFF

Phase B
=======
Lifecycle   DESIGNED (9-stage + state machine)
Executor    OFF
Auto repair OFF
```

### 当前 Phase A 缺口

| 五类 | 检测器覆盖 | 状态 |
|:-----|:---------:|:----:|
| A. Output Failure | 部分覆盖（B_style_drift） | ⚠️ 需补充 duplicate/format |
| B. Reasoning Boundary | ✅ (C+F) | active |
| C. User Correction | ❌ 缺失 | **待追加** |
| D. Correction Persistence | ❌ 缺失 | **待追加** |
| E. Regression | ❌ 缺失 | **待追加** |

### 后续观察指标

| 指标 | 含义 | 状态 |
|:-----|:-----|:----:|
| Correction Frequency | 用户纠偏次数 | 📄 待采集 |
| Correction Persistence | 纠偏后保持率 | 📄 需跨 session 分析 |
| Correction Regression | 纠偏后重新犯错次数 | 📄 需跨 session 分析 |
| User Correction Cost | 用户需要重复纠正次数 | 📄 需跨 session 分析 |

### Phase A Evolvement — Next Actions

来源于全量 TG 对话维护测试 (2026-07-21)，归档后确认的执行顺序：

```
[1] C 检测器校准
    target: precision 9.2% → >70%
    method: 过滤事实争议/方案意见/方向讨论，仅保留行为模式/执行边界/交互方式纠正

[2] Duplicate Temporal Analyzer (v2.2)
    Input:  143 R2 true duplicates
    Method: temporal classification — 不是按总量判断，按时间密度判断
    Output: {
      short_burst:   密集爆发（分钟级，高风险）
      session_repeat:同 session 间隔重复（中风险）
      long_cycle:    跨天复发（观察）
      expected:      周期性信息需求（排除）
    }
    Key metric: Burst Duplicate Rate (30s/5min/30min window)

[3] 重跑 Phase A
    → 新基线 Behavior Baseline v2.2
    → 加入 A1 exact / A2 semantic / A3 burst / A4 long-cycle / A5 expected
```

三个完成后产生新一轮基线。再决定是否触发 Phase B。

**当前不执行。保持 observe。**

---

## §5 最终判断逻辑

```text
一次错误:     观察
一次纠正:     记录
多次纠正:     分析
跨会话复发:    维护候选
确认系统性缺陷: 进入 Phase B
```

---

## §6 阻断路径

```text
transcript
    ↓
memory        ← 🚫 永久阻断
    ↓
global rules  ← 🚫
    ↓
SOUL.md       ← 🚫
```

---

## 版本记录

| 版本 | 日期 | 变更内容 |
|:---|---:|:--------|
| v1.0 | 2026-07-21 | 初版，龙哥架构设计落地 |
| v1.1 | 2026-07-21 | 追加 Engineer 维护流程规范 |
| v2.0 | 2026-07-21 | 升级为行为轨迹稳定性观测，新增 Correction Lifecycle / 五类分析 / 9阶段生命周期 |

## Related

- [TG-BEHAVIOR-DATA-CONTRACT.md](TG-BEHAVIOR-DATA-CONTRACT.md)
- [FREEZE-CONTRACT.md](FREEZE-CONTRACT.md)
- [PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md](PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md)
- [REASONING-ISOLATION-CONTRACT.md](REASONING-ISOLATION-CONTRACT.md)
