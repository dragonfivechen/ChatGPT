# Self-Healing Evolution — 系统存档

**归档时间：** 2026-07-22 03:57 CST
**来源入口：** 燃🔥 (main/webchat)

---

## 架构演进路径

### 初始问题
自愈能力分散在 Runtime、Extension、Doctor 三个区域，没有形成统一闭环。
系统不能回答"发生过多少次自愈"、"恢复耗时多少"。

### 源码验证驱动修正（关键决策点）
基于 OpenClaw 官方源码 `openclaw-src` (v2026.5.20, e510042) 分析：

| 源码位置 | 发现 |
|:---------|:-----|
| `src/gateway/channel-health-monitor.ts` | TG 通道已 L3 自动 restart |
| `src/gateway/channel-health-policy.ts` | 5 种状态判定 + 重启原因 |
| `src/commands/doctor/repair-sequencing.ts` | maybeRepair* 标准化修复引擎 |
| `src/provider-runtime/operation-retry.ts` | 同 provider retry 已存在 |
| `src/agents/api-key-rotation.ts` | 多 API key 轮转 fallback |
| `src/gateway/server-methods/agent.ts` | TG 模型链路无外部 hook |

**核心纠正：** 系统不需要"实现自愈"，而是需要"治理已有自愈"。

### TG 模型链路结论
TG 对话中的模型调用不可外部治理。链路（TG → Gateway → Agent → Provider → API）
中不存在外部 hook 点。模型可靠性只能依赖 Runtime 内部 retry + key rotation。

---

## 当前系统状态（冻结矩阵）

```
P0 Self-Healing Audit Observer  →  FROZEN ✅
P1.1 Pipeline Health Graph      →  FROZEN ✅
M0 Health Source Integration     →  DONE   ✅
P1.2 Health State Model          →  PROPOSAL ⏸ (依赖 7 天证据)
P3 Model Reliability Observation →  RUNNING ✅ (Day 0/7)
```

### P0 — Self-Healing Audit Observer
- 检测 channel restart（telegram 2 accounts）
- 记录 doctor repair config diff
- 追踪恢复耗时（detected → recovered 配对）
- 输出：`events/self_healing.jsonl`

### P1.1 — Pipeline Health Graph
- 22 个模块健康状态映射（systemd 13 + file_output 7 + channel 2）
- 三种 collector：systemctl / file mtime / channel_state
- 语义状态模型：ACTIVE / IDLE / STALE / FAILED

### M0 — Health Source Integration
- 22 模块 → 22 健康源 = 100% 覆盖率
- `self-healing/modules.yaml` 配置注册表
- `health_graph.py` 统一 snapshot → diff → event

### P3 — Model Reliability Observation
- per-session 级别 provider 记录
- 当前 deepseek 100% 覆盖，19 sessions，2 终端（1 done + 1 timeout）
- 输出：`events/provider_observe.jsonl`

---

## 运行管道

| 管道 | 调度 | 产出 |
|:-----|:-----|:-----|
| `observer.py --once` | `*/5 * * * *` | P0 self-healing + P1.1 health graph + M0 module health |
| `provider_observe.py` | `0 * * * *` | P3 per-session provider metrics |

## 文件结构

```
self-healing/
├── observer.py              ← 主入口（所有阶段集成）
├── health_diff.py           ← P0: channel restart + recovery duration
├── health_graph.py          ← P1.1+M0: 22-module health graph + semantic evaluator
├── config_audit.py          ← P0: doctor repair diff
├── provider_observe.py      ← P3: per-session provider metrics
├── event_writer.py          ← 统一事件写入
├── modules.yaml             ← M0: 22 module → health source 映射
└── schemas/
    └── self-healing-event.json

self-healing/state/
├── channel_state.json
├── health_graph_prev.json
├── pending_recovery.json
├── observer_state.json
└── provider_observe.json

events/
├── self_healing.jsonl
├── provider_observe.jsonl
└── integrity_observe.jsonl
```

## 关键文档索引

| 文档 | 位置 |
|:-----|:------|
| P1.2 Health State Model 提案 | `memory/state/huo/P1.2-HEALTH-STATE-MODEL-PROPOSAL.md` |
| 功能模块自愈可行性分析 | `memory/state/huo/FUNCTIONAL-MODULE-SELF-HEAL-FEASIBILITY.md` |
| 本日事件日志 | `memory/events/huo/2026-07-22.md` |
| MEMORY.md 治理索引 | `MEMORY.md` |

## 下一决策点

**日期：** 2026-07-29
**输入：**
  - provider failure_rate (P3)
  - module state transitions (M0)
  - false positive ratio (M0 + P1.1)
  - runtime distribution (P3)

**决策：** 是否进入 Recovery Policy 设计

---

## Baseline A: Self-Healing Governance 架构基线（2026-07-22）

```
P0:  Self-Healing Audit Observer       FROZEN
P1.1: Pipeline Health Graph            FROZEN
M0:   Health Source Integration         DONE
P1.2: Health State Model               PROPOSAL (依赖证据)
P3:   Model Reliability Observation     RUNNING
```

**运行调度：**
- `*/5 * * * *` → `observer.py --once`（P0 + P1.1 + M0 巡检）
- `0 * * * *` → `provider_observe.py`（P3 每小时采集）

**核心原则：**
- Evidence First — 所有决策基于数据，不提前进入 Recovery
- Observe → Measure → Decide — 观察先行，测量验证，数据驱动决策
- 不提前进入 Recovery Policy、Provider Fallback、Output Validator

**证据文件：**
- `events/self_healing.jsonl` — P0 + P1.1 事件
- `events/provider_observe.jsonl` — P3 per-session 记录
- `self-healing/state/health_graph_prev.json` — 模块健康快照
- `self-healing/state/pending_recovery.json` — 恢复追踪

**下一决策：** 2026-07-29

---

## Evolution Lineage — 演化路径

```
Runtime 能力发现（源码验证：openclaw-src）
  │
  │ 发现：TG 通道已 L3、doctor 已是修复引擎、provider retry 存在
  │ 修正：系统不缺自愈，缺治理可见性
  │
  ▼
P0 Self-Healing Audit Observer
  │ 范围：channel restart + doctor repair + recovery duration
  │ 停止：已有自愈只需要记录，不重复建设
  │ 验收：events/self_healing.jsonl 持续追加
  │
  ▼
P1.1 Pipeline Health Graph
  │ 范围：telegram + event_kernel + cron_pipeline 健康状态
  │ 停止：先统一健康观察面，再谈修复
  │ 触发 P1.2：event_kernel frozen_63h 暴露二元状态语义缺陷
  │
  ▼
M0 Health Source Integration
  │ 范围：22 模块 × 3 种健康源（file / systemd / channel）
  │ 发现："cron 模块不可观测"假设错误 — 已有输出文件，无需 touch-file
  │ 停止：已有健康源优先接入，不新建监控体系
  │ 验收：22/22 = 100% 健康源覆盖
  │
  ▼
P1.2 Health State Model
  │ 范围：ACTIVE / IDLE / STALE / FAILED 语义判定
  │ 停止：状态语义需要运行证据验证，暂不修改 P1.1
  │ 依赖：M0 观察数据 + false positive ratio
  │
  ▼
P3 Model Reliability Observation
  │ 范围：per-session provider metrics（deepseek）
  │ 发现：TG 模型链路不可外部 hook，依赖 Runtime 内部
  │ 停止：模型可靠性需要真实故障数据，不预设 fallback
  │ 验收：events/provider_observe.jsonl 7 天基线
  │
  ▼
M1 Module Health Observation（当前）
  │ 范围：module_state_transition + false_positive_ratio
  │ 等待：2026-07-29 证据窗口关闭
  │
  ▼
Recovery Policy（未进入）
  │ 进入条件：evidence + pattern + risk assessment + recovery value
  │ 否则：保持 Observation
```

## Frozen Boundary — 已冻结决策

| 决策 | 冻结原因 | 违反后果 |
|:-----|:---------|:---------|
| ❌ 不实现自愈引擎 | Runtime 已有 L3，缺的是治理 | double recovery logic |
| ❌ 不实现 provider fallback | 当前 n=2，统计不可靠 | 复杂度 > 收益 |
| ❌ 不实现 output validator | TG 链路不可外部 hook | 误判损失 > 收益 |
| ❌ 不给 cron 加 touch-file | 已有输出文件 | 多余的维护负担 |
| ❌ 不建设独立监控系统 | P1.1 snapshot→diff→event 已覆盖 | 三套独立监控 |
| ❌ 不提前进入 Recovery Policy | 缺少故障频率与收益证据 | 无数据支撑的自动修复 |

## Decision Gate — 下一阶段进入条件

| 目标 | 条件 | 数据来源 | 时间 |
|:-----|:-----|:---------|:----|
| Provider Fallback | failure_rate > 5% + 集中在单 provider | `provider_observe.jsonl` | 2026-07-29 |
| Output Validator | 本地任务质量问题 > 10% + shadow precision > 90% | 待建设 | 待定 |
| P1.2 Health State Model | false_positive_ratio < 5% | `health_graph_prev.json` diff | 2026-07-29 |
| Recovery Policy | 故障模式可识别 + 恢复收益可证明 | 所有上述证据 | 2026-07-29 后决策 |

---

## Enforcement Level 定义（审计修复契约 v1.1）

审计项分类时必须包含控制强度，不再是单一"检测"：

| 类型 | 目标 | 动作 | 示例 |
|:-----|:-----|:-----|:-----|
| **Observation** | 看见问题 | 记录 | event_kernel stale 检测，provider 失败率统计 |
| **Protection** | 防止问题 | 阻断+记录 | boundary_gate 跨域写入阻挡，身份混用拦截 |
| **Governance** | 控制流转 | 审批+审计 | TG→燃🔥 promote 闸门，config 变更审核 |

### 边界安全问题默认不低于 Protection

对以下类型问题，审计项必须定义为 **Protection** 及以上：

- 身份边界（燃🔥/烬🔥跨域访问）
- 数据边界（huo/jin 内存路径混写）
- 状态边界（experiment → production 无审核迁移）
- 配置边界（关键配置被非授权修改）

### 禁止将边界安全问题定义为 Observation-only

原因：

```text
Observation-only 的边界检测
        ↓
只能回答 "发生了"
        ↓
不能回答 "阻止了"
```

需要：

```text
Protection
        ↓
发现 → 验证 → 阻断 → 记录
        ↓
可证明安全边界完整
```

### 历史修正

- 2026-07-22: `boundary_observe.py`（Observation）→ `boundary_gate.py`（Protection + Governance）
- 触发事件：实际的 `jin_read_huo_state` 违规被发现
