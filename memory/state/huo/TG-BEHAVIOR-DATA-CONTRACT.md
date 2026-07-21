# TG Behavior Data Contract v1.0

```
contract:
  name: TG-BEHAVIOR-DATA-CONTRACT
  version: v1.0
  level: L2
  parent: FREEZE-CONTRACT
  scope: cross-agent behavior data isolation
  owner: 燃🔥
  status: active
  created: 2026-07-21
```

---

## 目的

终端模型（燃🔥）可读取 TG 模型（烬🔥）行为记录用于诊断维护，
但 TG 数据不能反向进入终端模型记忆、规则和行为约束。

---

## 允许

| 操作 | 说明 |
|:-----|:-----|
| `read transcript` | 读取 TG session 原始对话记录 |
| `analyze behavior` | 分析 6 类行为异常 |
| `generate finding` | 输出诊断分析报告 |

## 禁止

| 操作 | 说明 |
|:-----|:-----|
| `write memory` | TG 行为数据不进入 `memory/` 或 `rules/` |
| `modify SOUL` | 不基于 TG 观察修改终端模型人格规则 |
| `modify core contract` | 不基于 TG 行为数据修改 L0/L1 契约 |
| `alter terminal personality` | 不继承 TG 行为模式 |

---

## 数据流

```
TG Agent (烬🔥)
    ↓
transcript files (~/.openclaw/agents/main/sessions/*.jsonl)
    ↓
[Read Only Adapter]  →  tg_transcript_reader.py
    ↓
Behavior Observation Layer  →  tg_behavior_analyzer.py
    ↓
Finding / Anomaly Event  →  diagnostics/agent_behavior/telegram/findings/
    ↓
Maintenance Queue  →  diagnostics/agent_behavior/telegram/maintenance/
    ↓
人工确认后的修复
```

---

## 阻断路径

```
TG transcript
    ↓
memory_candidate   ← 🚫 永久阻断
    ↓
rules/             ← 🚫
    ↓
SOUL.md            ← 🚫
```

TG 错误行为 → 被提取成规则 → 终端模型永久继承 = 全局污染。

---

## 与现有 Phase 8 对接

```
Integrity Observation
    ↓
Analyzer Foundation      ←  tg_behavior_analyzer.py 接入
    ↓
Maintenance Queue        ←  tg_maintenance_queue.py 接入
```

不接 Memory Governance Pipeline。

---

## 文件结构

```
diagnostics/
└── agent_behavior/
    └── telegram/
        ├── raw/           ← transcript reader 输出
        ├── findings/      ← behavior analyzer 输出
        └── maintenance/   ← maintenance queue 状态
```

---

## 工具链

| 工具 | 功能 |
|:-----|:------|
| `tools/tg_transcript_reader.py` | session 抽取，输出到 raw/ |
| `tools/tg_behavior_analyzer.py` | 6 类检测，输出到 findings/ |
| `tools/tg_maintenance_queue.py` | findings → queue，管理状态流转 |

---

## 版本记录

| 版本 | 日期 | 变更 |
|:---|---:|:---|
| v1.0 | 2026-07-21 | 初版，龙哥架构设计落地 |
