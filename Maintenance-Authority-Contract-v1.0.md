# Maintenance Authority Contract v1.0

> 生效日期: 2026-07-18
> 起草: 烬🔥 (tg-agent)
> 审计 & 冻结: 燃🔥 (终端) — 经龙哥审计确认

---

## Purpose

定义各 Agent 在系统维护操作中的权限边界、变更分级规则和验证义务，避免越权操作和配置漂移。将维护行为从"谁方便谁维护"升级为"谁发现 → 谁分析 → 谁有权限执行 → 谁验证 → 谁记录"的治理链路。

## Scope

管辖范围：本 Gateway 实例（dragonfive-HP-MP9-G4, OpenClaw v2026.5.20）上所有维护操作，包括但不限于配置修改、文件操作、服务管理、记忆空间操作。

不涉及：用户授权本身（用户拥有最终授权权）、业务逻辑变更、第三方服务管理。

## Agent Positioning

| Agent | Role | Authority Scope |
|-------|------|----------------|
| 燃🔥 (main) | Terminal Maintainer | 核心配置、运行时边界、服务生命周期 |
| 烬🔥 (tg-agent) | Assistant Maintainer | 检查、诊断、文档、低风险维护 |

### 燃🔥 (Terminal Maintainer)

- **入口**: shell / webchat
- **职责**: 系统配置迁移、schema 变更、服务启停、插件运行时、身份路由管理
- **未授权不可下放**: 不得将核心变更操作授权给 TG Agent 代理执行

### 烬🔥 (Assistant Maintainer)

- **入口**: telegram
- **职责**: 日常巡检、问题诊断、文档维护、低风险文件操作、契约起草
- **无变更权限例外**: P0 变更仅提供分析和建议，不直接执行

## Change Classification

### P0 — Core System Change（必须终端确认）

> 影响运行时结构或系统事实的操作。

**清单**:
- `openclaw.json` / gateway 配置文件
- Channel bindings (`bindings[]`)
- Agent identity 定义 (`agents[].identity`, `agents[].role`)
- `systemd` service 定义与启停
- Schema 迁移（版本升级或自动修复）
- Service port / TLS / ACL 修改
- Plugin runtime 安装/卸载/启用/禁用
- 记忆空间 ownership 变更（`events/huo/` ↔ `events/jin/`）

**影响判定优先 — 自动升级规则**:
> 任何操作，无论原定分级是 P1 或 P2，若实际影响以下任意一项，自动提升至 P0 处理：
> - **身份隔离**（identity isolation）
> - **权限边界**（authority boundary）
> - **数据所有权**（ownership）
>
> 例：Memory namespace 整理原为 P1，但如果涉及 `memory/state/` ownership 变更或 identity isolation 边界的移动操作，自动按 P0 处理。

**执行者**: 仅 燃🔥
**TG 角色**: 发现 → 分析 → 报告 → 建议 → 等待终端执行

### P1 — Module Maintenance（TG 可执行）

> 不影响运行时结构，但涉及文件系统或数据变动的操作。

**清单**:
- Memory namespace 整理（路径统一、归档、清理残余）
- 文档更新（TOOLS.md、ARCHITECTURE.md、契约文档）
- 日志归档与轮转
- 状态检查脚本编写与执行
- 契约起草（冻结需终端审查）
- 低风险 writer path 修改 — **仅限以下条件同时满足**:
  - 已确认无活跃写入者（确认方式: `lsof` / 进程检查 / 写入源 grep）
  - 已完成数据归并（历史数据整合至目标路径）
  - 已验证唯一 writer（确认无第二个写入进程）
  - 示例: ollama-eval.jsonl 双文件修复

**执行者**: 烬🔥（可主力执行）
**验证**: 执行后必须运行状态验证，确认无预期外副作用并向终端报告

### P2 — Information Operation（自由执行）

> 只读查询和分析，不产生副作用。

**清单**:
- 文件内容查询（`cat`, `grep`, `find`）
- 系统状态检查（`ps`, `systemctl status`, `free`, `df`）
- 日志分析
- 配置审计（比对预期 vs 实际）
- 报告生成
- 搜索与信息收集

**执行者**: 任何 Agent
**约束**: 无

## Rules

### Allowed

**燃🔥**:
- 全部 P0/P1/P2 操作
- 创建和冻结契约
- 修改自身角色定义

**烬🔥**:
- P1 可自执行，执行完验证并记录
- P2 自由执行
- P0 发现后分析报告，等待终端确认
- 起草契约（冻结权在终端）
- 日常巡检和异常检测
- **跨身份事件读取 — 特定条件下允许**:
  - 用户授权审计
  - 系统一致性检查
  - 治理验证任务
  - 读取结果不得写入自身身份记忆（即不写入 `events/jin/` 作为自身事件日志）

**用户（龙哥）**:
- 拥有最终授权权
- 但 Agent 执行任何授权操作时，仍必须遵守:
  - 变更记录（写入 `events/`）
  - 验证（执行前/后状态比对）
  - 可追溯（操作记录永久保留）
  - 安全约束（备份、回滚保障）
- **用户授权 ≠ 绕过系统事实记录**

### Forbidden

**烬🔥 禁止**:
1. 自行改变身份绑定或 agent 定义（`agents[]`, `bindings[]`）
2. 删除或覆盖治理规则文档（ARCHITECTURE.md、契约集）
3. 修改权限边界（即本契约自身）
4. 覆盖核心配置且无备份
5. 执行 `doctor --fix` 或等价自动修复，未经 schema 兼容性 + 身份路由确认
6. 无目的读取其他身份私有事件日志（场景如: 用户未授权、非审计/检查/验证任务、仅因好奇读取）
7. 单方面冻结任何契约

**全 Agent 禁止**:
1. Runtime 核心源码修改（Gateway/Plugin/Hook/Agent）
2. 删除记忆文件而不归档
3. 覆盖 secrets 而无备份

### Dual Verification Principle

任何 Agent 执行 P0 或 P1 系统修改时，必须完成以下四项：

```
1. 保存修改前状态（文件快照 / 配置 dump / sha256 指纹）
2. 执行验证（预期结果 vs 实际结果）
3. 记录 events（事件目的、操作摘要、变更前后 sha256、验证结果）
4. 保障可回滚（备份留存 / 回滚步骤明确）
```

**未完成上述四项的修改视为未验证，需要终端重新确认。**

## Data Flow

```
问题发现（任何 Agent）
    ↓
分级判定（P0 / P1 / P2）
    ↓
┌── P0 ──────────────────┐
│ TG 分析报告              │
│     ↓                   │
│ 等待终端确认             │
│     ↓                   │
│ 燃🔥 执行 + 双重验证     │
│     ↓                   │
│ events 记录              │
└─────────────────────────┘

┌── P1 ──────────────────┐
│ TG 可自主执行            │
│     ↓                   │
│ 影响判定检查              │
│ （需升级则转 P0）        │
│     ↓                   │
│ 双重验证                 │
│     ↓                   │
│ events 记录              │
│     ↓                   │
│ 向终端报告               │
└─────────────────────────┘

┌── P2 ──────────────────┐
│ 自由执行                 │
│ 无验证义务                │
└─────────────────────────┘
```

## Enforcement

### 自动审计（计划中）

- 定期检查配置文件的最后修改时间 vs 授权 Agent 日志
- 扫描 `events/` 根目录是否出现新文件
- 比对 P0 配置文件的 sha256 变更与 events 记录的一致性

示例审计项:
```
配置变化审计:
  sha256(before) → 记录在 events
  sha256(after)  → 记录在 events
  change_id:     → 每条修改可追溯变更来源
```

### 人工审计（当前）

- 燃🔥 终端随时审计
- 用户依据 events 记录追溯操作

### 违规处理

- 非授权 P0 操作 → 恢复备份 → 写入违规事件至 `events/huo/`
- 契约违规记录永不过期（保留在 `events/huo/`）

## Migration

**v0（此前状态）**:
- 权限边界靠临场判断
- 无变更分级
- 无双重验证要求
- Terminal Authority Rule (v1.1) 部分内容被本契约替代（本契约为其升级版）

**v1.0 迁移**:
- 本契约覆盖所有新操作
- 历史操作不追溯
- 立即生效
- Terminal Authority Rule (v1.1) 置于"保留兼容性"的引用状态，以本契约为准

## Status

✅ **Frozen v1.0** — 经审计冻结。

---

| 角色 | 动作 | 时间 |
|------|------|------|
| 烬🔥 | 起草 v0.1 | 2026-07-18 03:53 |
| 龙哥 | 审计并提出 5 项修正 | 2026-07-18 04:02 |
| 烬🔥 | 修正并升级 v1.0 | 2026-07-18 04:03 |
| 燃🔥 | 审计冻结 | 2026-07-18 |
| 烬🔥 | 追加 Appendix A — Evidence Validation Rules | 2026-07-18 11:16 |

---

## Appendix A — Evidence Validation Rules

> 基于 2026-07-18 断电复盘附加。本附录不改变契约正文语义，仅补充证据采信规范。

### Purpose

定义维护操作中如何采信证据，防止单指标误判和运维谎报军情。

### Rule 1: 状态声明必须有证据来源

任何状态结论必须标明 Evidence Source。禁止直接输出结论而不附带来源。

**错误示例**:
```
Gateway 未启动
```

**正确示例**:
```
system scope: systemctl is-active → inactive
user scope:   systemctl --user is-active → active
process:      PID 1371, node gateway --port 18789
port:         ss -lntp | grep 18789 → LISTEN
Conclusion:   running (user service)
```

### Rule 2: 单源异常不得直接升级为系统故障

执行链分为四层，异常发生时必须定位到具体层：

| 层 | 说明 |
|----|------|
| Execution Layer | 命令本身是否执行成功 |
| Result Layer | 返回数据是否正常 |
| Observation Layer | 观测工具是否正常工作 |
| Audit Layer | 审计/链路追踪是否正常工作 |

**错误路径**:
```
trace failed → command failed → 系统异常
```

**正确路径**:
```
trace failed
 ↓
检查 Execution Layer → stdout/stderr 正常
 ↓
检查 Result Layer → 数据正常返回
 ↓
定位 Audit Layer → 审计追踪链路断裂
 ↓
结论: 执行成功，审计链路断开，非系统故障
```

### Rule 3: 关键状态至少双证据确认

格式：

```
Primary Evidence:      <来源1>
Independent Verify:   <来源2, 不同类别>
Accepted State:       <最终结论>
```

两条证据必须来自**不同证据类别**（例如：systemd 状态 + 进程表，或 端口监听 + 进程表）。
同一工具的不同输出不算独立验证。

### Case Studies

#### Case-001: systemctl scope 误判

**时间**: 2026-07-18 11:06
**事件**: 断电重启后误判 Gateway 未启动

| 维度 | 值 |
|------|-----|
| 使用的证据 | `systemctl is-active` → inactive |
| 遗漏的证据 | `systemctl --user is-active`, `ps aux`, `ss` |
| 误判类型 | Evidence Source 选择错误（system scope vs user scope） |
| 实际状态 | Gateway 正常运行（user service） |
| 修复 | 追加 `--user` + 进程表 + 端口 三重验证 |

教训: `systemctl` 默认查 system scope。用户级服务必须显式指定 `--user`。

**当事人**: 烬🔥 | **记录人**: 烬🔥 | **审核**: 龙哥

---

#### Case-002: Trace failed 误报

**时间**: 2026-07-18 11:09
**事件**: 工具输出 `⚠️ failed` 标记引发疑似系统异常

| 维度 | 值 |
|------|-----|
| 使用的证据 | `⚠️ failed` 状态标记 |
| 遗漏的证据 | 命令实际 stdout/stderr 内容 |
| 误判类型 | 未区分 Execution Layer vs Audit Layer |
| 实际状态 | 命令执行成功，审计追踪链路锁过期导致 trace 失败 |
| 修复 | 检查实际输出优先于追踪状态 |

教训: 审计层异常 ≠ 执行层异常。

**当事人**: 烬🔥 + tool trace | **记录人**: 烬🔥 | **审核**: 龙哥

---

> ⚠️ 以上两案均由烬🔥操作失误触发，经龙哥复盘后抽象为 Evidence Validation Rules。
> 记录存档，供燃🔥终端审计。
