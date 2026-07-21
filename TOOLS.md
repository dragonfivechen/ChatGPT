# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

### 产品输出边界 — 彩票日报

用户日报（推送内容）：
├── 开奖号码
├── 基础统计
└── 预测核验

内部信息（不推送）：
├── 数据源验证
├── 期号校验
├── 系统状态
└── 其他后台调试信息

当日未开奖彩种不出现在日报中。

### 产品输出边界 — 维护报告

输出范围（只输出这些，不输出判断）：
├── 事件列表
│   ├── 会话标识
│   ├── 原文摘录（用户/模型）
│   ├── 匹配规则
│   └── 时间戳
├── 汇总
│   ├── 事件数量
│   ├── 涉及会话数
│   └── 时间范围
└── 附录
    └── 原始数据索引

禁止输出：
├── 这是问题/不是问题
├── 影响低/中/高
├── 无需维护/需要维护
└── 建议/判定/结论

判断层归用户，统计层归模型。

### 跨 Agent 诊断读取边界

基于 `DIAGNOSTICS-BEHAVIOR-LAYER.md` v2.0：

| 能力 | ✅/❌ |
|------|:----:|
| 读取 TG transcript | ✅ — `~/.openclaw/agents/main/sessions/*.jsonl` |
| 写入诊断发现 | ✅ — `diagnostics/agent_behavior/telegram/findings/` |
| 提取 TG 对话入 Memory | ❌ 永久禁止 |
| 用 TG 观察修改 SOUL.md | ❌ 永久禁止 |
| 自动改变自身行为规则 | ❌ 永久禁止 |

**分析五类（v2.3）：**
| 类 | 内容 | 状态 |
|:--|:-----|:----:|
| A | Response Stability — 重复/遗漏/格式/爆发 | ⚠️ 部分覆盖 |
| B | Reasoning Boundary — 讨论→执行 | ✅ 已覆盖 |
| C | User Feedback Classification — 分层 | ✅ C0-C4 已定义 |
|   | C1 内容纠正 / C2 方案讨论 / C3 行为纠正 / C4 交互纠正 | — |
|   | C0.5 Intent Filter — 先判断否定对象再路由 | ✅ 新增设计 |
| D | Intent Fulfillment — 理解→响应落差 | 📄 新增观察维度 |
| E | Regression — 复发检测 | ❌ 依赖 C3+D |

**核心指标：** User Behavior Rejection Rate = C3 数量 / 总会话数
**后续重点指标：** Burst Duplicate Rate / Duplicate Interval / Session Locality

**Phase A Pipeline:** Reader → Analyzer → Finding → **Human Review** → Confirmed Finding → **User Interpretation** → Queue → Phase B Gate

**Output layers:**
- 机器层: JSON 检测标签
- 审核层: Audit report（人审用）
- 用户层: User-facing interpretation（体验描述）

执行前确认：当前任务属于 Diagnostics 读取层，不是 Memory 写入层。

### 架构建设规范（Architecture Governance Layer v1.0）

源自 燃🔥 系统重构 + 龙哥审计纠正，固化以下规范：

#### Extension Boundary
- **Runtime 核心不动** — Gateway/Plugin/Hook/Agent 不改源码
- **外部工作走标准模式** — systemd timer + oneshot worker，不长期 daemon
- **通知统一出口** — 所有推送走 push-gate.mjs，不能各自持有 token
- **Secrets 隔离** — 独立 `.secrets/` 目录，脚本零硬编码

#### Memory Semantic Namespace
```
memory/
├── state/       ← 系统状态 / 契约 / 架构文档（ownership controlled）
│   ├── system/  ← 系统共享状态（无身份归属）
│   ├── huo/     ← 燃🔥私有状态
│   └── jin/     ← 烬🔥私有状态
├── events/      ← 身份事件日志（按身份隔离子目录）
├── data/        ← 原始系统数据、业务数据、采集结果（不参与身份记忆读取）
│   └── system/  ← 系统运行数据（telemetry、备份记录等）
├── facts/       ← 事实数据
├── preferences/ ← 偏好配置
├── knowledge/   ← 知识库
└── cache/       ← 缓存
```

#### 身份隔离
- 燃🔥（系统维护） vs 烬🔥（TG交互） — 严格互不读对方 memory
- 见 IDENTITY.md + IDENTITY-RULES.md

#### Memory Governance Rules (v1.0)
- `events/` → 身份事件日志，严禁根目录存放，必须按身份隔离
- `data/` → 系统运行数据，不参与身份记忆读取，无身份归属
- `state/` → ownership controlled，必须通过一级目录声明归属：
  - `system/` = 系统共享状态
  - `huo/` = 燃🔥私有状态
  - `jin/` = 烬🔥私有状态
- `knowledge/` → 共享允许，无需隔离

#### Terminal Authority — 由 Maintenance Authority Contract v1.0 管理

> 本规则已升级为正式契约，见 `Maintenance-Authority-Contract-v1.0.md`。
> 以下为摘要回溯，具体以契约为准。

**变更分级**:
- **P0 — Core System Change**: 必须终端确认（配置、身份绑定、service、身份路由）
- **P1 — Module Maintenance**: TG 可执行（memory 整理、文档、日志、已验证的 writer path 修改）
- **P2 — Information Operation**: 自由执行（查询、分析、报告）

**影响判定优先**: P1/P2 操作若影响身份隔离/权限边界/数据所有权，自动升级 P0。

**双重验证原则**: 任何 P0/P1 修改必须：保存前状态 → 验证 → 记录 events → 可回滚。

**核心控制点：**
不是限制 TG 的手，而是限制谁可以改变系统事实。
涉及身份、核心配置、运行时边界变更时，需要终端确认。

#### Module Ownership Rule (v1.1)
- 模块 Owner 由维护责任决定，不由调用入口决定。
- 执行身份 ≠ 变更权限 ≠ 最终责任。
- TG Agent 可在维护范围内执行操作，不改变模块所有权。
- 协作入口产生的数据、日志、建议，不自动改变模块 Ownership。

#### Plugin Governance
- Capability Registry Model v1.0 定义能力目录
- Plugin Capability Contract 规范插件声明
- 见 `memory/state/huo/CAPABILITY-REGISTRY.md`

#### 结构审计四层（纠正后）
| 层 | 范围 |
|----|------|
| Layer 1: Runtime State | 进程/PID/服务状态 |
| Layer 2: Configuration State | 配置漂移 |
| Layer 3: Filesystem/Namespace | 目录/文件结构变化 |
| Layer 4: Governance Contract | 契约/边界/模型文档 |

---

### Token 观测

- 脚本: `/home/dragonfive/.openclaw/observe-token.sh`
- 输出: `/home/dragonfive/.openclaw/token_observe.jsonl`
- 周期: 每小时整点 (crontab)
- 指标: session_count, total_tokens_k, transcript_bytes, trajectory_bytes, compaction/prune 事件数

### 本地源码资料库

- 路径: `/home/dragonfive/.openclaw/repos/openclaw-src/`
- 版本: 2026.5.20 (e510042)
- 索引: `/home/dragonfive/.openclaw/repos/INDEX.md`
- 搜索: `bash /home/dragonfive/.openclaw/repos/claw-search.sh <关键词> [docs|src|skills|config|all]`

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Related

- [Agent workspace](/concepts/agent-workspace)
