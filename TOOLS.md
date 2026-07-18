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
