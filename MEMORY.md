# MEMORY.md — 系统维护索引

> 系统恢复后第一时间读这个文件。
> 身份不由本文件提供，由入口通道绑定决定（见 `IDENTITY.md`）。

---

## 🆘 恢复自检

读完确认：

- [ ] 我是龙哥的 AI 助理，不是聊天机器人
- [ ] 身份由入口通道决定：shell/webchat → 燃🔥，telegram → 烬🔥
- [ ] 龙哥是我老板，行动前确认，不擅自执行
- [ ] SOUL.md 铁律：简洁、有证据、不嘴炮、不猜测、输出双部分
- [ ] BOOTSTRAP.md 存在即读（救命入口）

---

## 身份治理（基线）

```
webchat / shell  ──→  agents.list[].id: main      ──→  燃🔥
telegram         ──→  bindings[].agentId: tg-agent  ──→  烬🔥
```

- 身份由入口绑定决定，不由 MEMORY.md 声明
- 严格记忆隔离：燃🔥不读烬🔥记忆，反之亦然
- 见 `IDENTITY.md` + `IDENTITY-RULES.md`

---

## 架构冻结基线

### 四层治理链

| 层 | 范围 |
|----|------|
| Layer 1: Runtime State | 进程/PID/服务状态 |
| Layer 2: Configuration State | 配置漂移 |
| Layer 3: Filesystem/Namespace | 目录/文件结构变化 |
| Layer 4: Governance Contract | 契约/边界/模型文档 |

### 关键边界规则

| 规则 | 要点 |
|------|------|
| Extension Boundary | Runtime 核心不动；外部走 systemd timer + oneshot；通知统一出口 |
| Memory Semantic Namespace | `state/` owned by identity；`events/` 身份隔离；`knowledge/` 可共享 |
| Terminal Authority | 核心模块 Owner = 燃🔥；烬🔥为协作入口，不拥有修改权 |
| Module Ownership | 模块 Owner 由维护责任决定，不由调用入口决定 |
| Config Migration | 版本升级/自动修复前必须确认 schema 兼容性；恢复后执行 identity route verification |

### 记忆文件结构

```
memory/
├── events/       ← 事件日志（按身份隔离子目录）
├── state/        ← 系统状态/契约/架构文档（ownership controlled）
├── data/         ← 原始业务数据
├── knowledge/    ← 知识库（可共享）
├── facts/        ← 事实数据
├── preferences/  ← 偏好配置
└── cache/        ← 缓存
```

---

## 运维基线

- **服务器：** dragonfive-HP-MP9-G4，6核 i5-8500，无独显，Node.js v22
- **Ollama：** 跑 qwen3:4b 纯 CPU，systemd 服务
- **OpenClaw：** v2026.5.20 (e510042)，端口 18789，loopback-only
- **本地源码：** `/home/dragonfive/.openclaw/repos/openclaw-src/`
- **Token 观测：** `/home/dragonfive/.openclaw/observe-token.sh`，每小时整点

---

## 维护原则

### 排查铁律
- 没有证据不给根因
- 最多说：观察到现象 X，可能原因 A/B/C，需要查证据
- 被质疑时回到证据，不继续解释

### 证据提交
- 执行完成 ≠ 验收完成
- 工具输出 ≠ 用户可见证据
- 输出分段提交，保持原始内容，不省略，不用"…"

### 记录边界
- 只记录：系统维护知识、架构基线、运维约定
- 不记录：建设过程、临时排障细节、已解决问题、对话噪声

### `doctor --fix` 使用边界
- 恢复的是"官方默认可运行态"，不是"当前架构态"
- 多 agent/多身份系统上必须手动确认 schema 兼容性 + 身份路由

---

## 未完成事项

| 事项 | 优先级 | 状态 |
|------|--------|------|
| Telegram `accounts.default` 缺失 | 低 | 标记待处理，当前 defaultAccount: main 回退启用 |
| Local Model Production Trial v1.0 | 中 | Step 1-3 ✅ (解耦链 + validation + 手动验证)。48h batch 观察中 ⏳ |
| Maintenance Runbook v1.0 | — | Phase 1 ✅ → Phase 2 ✅ → Phase 3 ✅ → Phase 4 🔒 FROZEN |

### Local Model Production Trial v1.0 ✅ COMPLETE

**Status:** production active (scoped) — 已验证可承担生产职责

| Step | Status |
|:---|:---:|
| Step 1 解耦链 | ✅ |
| Step 2 validation | ✅ |
| Step 3 手动验证 | ✅ |
| Step 4 生产路由注册 | ✅ |
| Production evidence (144 calls, 100%) | ✅ |

**架构:** 本地模型不作为云端降级替代。通过 `local-task-worker.sh` 处理 4 类确定型生产任务：`system_status_brief`, `config_explain`, `event_classify`, `log_summary`。
**边界:** 复杂推理/主任务 → DeepSeek；确定型任务 → Ollama qwen2.5:3b。
**关键文件:** `ollama-production.jsonl` (144 条, 0 失败), `local-task-worker.sh`。

## SecretRef Migration v1.0 — FROZEN

| Phase | 状态 |
|------|------|
| Phase 0: Baseline Audit | ✅ Complete (models.json 基线缺失) |
| Phase 1: Target Identification | ✅ Complete |
| Phase 2: Provider Selection | ✅ Complete (file provider) |
| Phase 3: Config Set (Telegram block) | ✅ Complete |
| Phase 3.5: Provider Name Registry | ✅ Complete |
| Phase 3.6: DeepSeek keyRef Compatibility | ✅ Complete (源码确认) |
| Phase 4.1: Telegram + Gateway SecretRef | ✅ Written to secrets.json |
| Phase 4.2: DeepSeek SecretRef | ✅ Resolved at runtime |
| Runtime Validation | ✅ PASS (unresolved=0) |
| Final Archive | ✅ COMPLETE |

**归档文件:** `secretref-migration-v1.0-FINAL.md`

**审计结果:**
- plaintext=1 (Ollama 本地占位符，按策略排除)
- unresolved=0 ✅
- shadowed=1 (models.providers.deepseek.apiKey 被 auth-profile 遮蔽，auth-profile 优先)
- legacy=0

**已知缺口:**
- models.json pre-migration 基线未采集（不影响安全完成度）

**冻结原则:**
- 不重新 apply
- 不修改 SecretRef
- 不删除备份
- 不回写 models.json
- 不调整 Ollama apiKey
- 不扩展 Secret 平台

## Lottery Timeline Refactor v1.0 — COMPLETE

```
Step 1:   fetch timer 22:10           ✅
Step 2:   check 消除重复 fetch        ✅
Step 2.5: 输入完整性（KL8链路补齐）    ✅
Step 3:   日报能力迁移                ✅
Step 4:   出口收敛                    ✅
```

**最终链路：**
- 22:10 `fetch_only.sh` → 数据事件
- 22:15/22:25/22:30 `run_check.sh` → `lottery-worker.sh` (SKIP_REPORT=true) → 仅校验+推送核对
- 22:35 `daily_report.sh` → `unified_report_gen.py` → **唯一日报出口**

**关键文件：**
- `unified_report_gen.py` (9134B, 6模块 A-F)
- `daily_report.sh` 仅作为入口，业务逻辑已迁移
- `daily_report_gen.py` (3525B) 旧版保留待观察后清理
- `run_check.sh` 已注入 `SKIP_REPORT=true`

## Phase 7 Runtime Integrity — COMPLETE 🔒

**Phase 7 系列全线完成：**

| Phase | Status |
|:---|---:|
| 7.1 Audit Contract | 🔒 FROZEN |
| 7.2 Boundary Matrix (5/5) | 🔒 FROZEN |
| 7.3 Bypass Closure (15 paths) | 🔒 CLOSED |
| 7.4 Runtime Verification (14/14 PASS) | 🔒 CLOSED |
| 7.5 Integrity Freeze | 🔒 FROZEN |

**核心结论：**
- Phase 6 Contracts 6.1-6.4 未被解冻
- Runtime Reality = Governance Decision 确认一致
- 15 bypass paths 全部治理分类完成
- No Reclassification 触发
- 进入 Observe/Evidence Accumulation 周期

**文档位置:** `memory/state/huo/PHASE-7.5-INTEGRITY-FREEZE.md`

## Phase 8 Integrity Observation — FROZEN 🔒

**Observe Layer — 只采集事实，不修改 Runtime**

| 子阶段 | 状态 | 内容 |
|:---|---:|:---|
| 8.1 Analyzer Foundation | 🔒 FROZEN | 10 项确定性检查 + 阈值 config |
| 8.2 Capability Contract | 🔒 FROZEN | 6 能力契约替代业务事件模型 |
| 8.3 Maintenance Queue | 🔒 FROZEN | Writer + Viewer + 日报集成 |
| 8.4 Notification Routing | 🚫 SHELVED | 当前无需求，cron 满足治理需求 |

### 完成闭环
```
系统运行
 ↓
Evidence (jsonl)
 ↓
Integrity Analyzer
 ↓
Integrity State (GREEN/YELLOW/RED)
 ↓
Maintenance Queue
 ↓
Human Governance
```

**输出：** `~/.openclaw/events/integrity_observe.jsonl`（append-only）
**推送管道：** 复用 push-notify.mjs → Telegram
**约束：** ❌不自动修复 ❌不改Runtime ❌不解冻Phase6

**文档位置:** `memory/state/huo/PHASE-8.0-RUNTIME-OBSERVATION-LAYER.md`
