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

### 模块基线检查契约

`memory/state/huo/FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md` v1.0

所有新增功能模块进入冻结基线前，须通过 14 项基线检查：

| 维度 | 检查项 |
|------|--------|
| A | Extension Boundary — Core 零修改 |
| B | Ownership — 归属明确 |
| C | Namespace — 状态隔离 |
| D | Interface Contract — 接口契约固定 |
| E | State Ownership — 状态所有权 |
| F | Data Provenance — 数据来源可追溯 |
| G | Determinism — 行为可重复 |
| H | Authority Boundary — 不越权 |
| I | Risk Boundary — 观察/决策/执行隔离 |
| J | Recovery — 异常后可恢复 |
| K | Test Evidence — 测试证据归档 |
| L | Config Governance — 配置治理 |
| M | Audit Trail — 审计链完整 |
| N | Freeze Integrity — 检查不破坏冻结 |

上位约束: FREEZE-CONTRACT.md

**契约体系三层结构:**

```
FREEZE-CONTRACT.md
  └── 仲裁规则：冻结定义 / 修复vs扩展 / 发现分类
        │
        v
FUNCTION-MODULE-BASELINE-CHECK-CONTRACT.md
  └── 14 项验收维度 + 检查模板
        │
        ├── Human Audit 方向:
        │   └── TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md (TG适配)
        │
        └── TG Build Alignment 方向 (预防问题):
            └── TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md
```

**契约等级: `CONTRACT-LEVEL-CLASSIFICATION.md` v1.0**

```
M0  META-CONTRACT            元治理级
L0  FREEZE-CONTRACT          系统仲裁级
L1  FUNCTION-MODULE-BASELINE 基线治理级
L2  Module Adapter           模块适配级
L3  Implementation Alignment 建设执行级
L4  Operational Evidence     运行证据级
```

**契约注册表: `CONTRACT-REGISTRY.md` v1.0** — META-CONTRACT 的管理索引，27/27 Contract Entities 已登记（新增 `EVIDENCE-CONTRACT.md` + `DECISION-CONTRACT.md` + `CHANGE-CONTRACT.md`）。Authority Review 27/27 ✅，Evidence: `audit/authority-review/`。

**元契约: `META-CONTRACT.md` v1.2** — 定位在 M0（元治理级），高于 L0。

治理链：Contract Declaration → Q1-Q7 Classification → Authority Review → Evidence → Registry

完成状态：
- Q1-Q7 分类判定全覆盖
- Authority Impact A0-A4 全覆盖 (27/27)
- Authority Review 27/27 ✅
- 等级生成协议 (Level Generation Protocol) 已定义
- CONTRACT-DECLARATION-SCHEMA v1.1 已定稿（含 verification 块）

定义：
- 新契约的 Q1-Q6 分类判定 + Q7 权限影响判定
- 契约生成约束（`CONTRACT-DECLARATION-SCHEMA.md`）
- 等级不可越权原则
- 等级生成协议（Level Extension 条件/流程/禁止场景）
- 契约生命周期（Proposal → Active → Frozen → Archived）
- Authority Impact A0-A4 + 不跃迁规则

所有现有契约已按此流程归档，后续新契约必须经过 META-CONTRACT 分类后再创建。

### 治理链闭环状态（2026-07-21 12:40）

```
发现  →  证据  →  决策  →  变更  →  维护
✅      ✅       ✅       ✅       ⚠️
```

| 环节 | 状态 | 备注 |
|:-----|:----:|:------|
| 发现 | ✅ 能力已存在 | 事件源/审计/观察层，未独立契约化 |
| 证据 | ✅ `EVIDENCE-CONTRACT` v1.0 | L1, active |
| 决策 | ✅ `DECISION-CONTRACT` v1.0 | L1, active |
| 变更 | ✅ `CHANGE-CONTRACT` v1.0 | L1, parent=DECISION, active |
| 维护 | ⚠️ Phase 8 能力已有 | 真实违反案例后考虑契约化 |

**关闭当前扩张周期，进入 Observe 阶段。** 后续只关注三个信号：证据误判/决策边界模糊/变更追踪缺失。

**闭环案例：** `event_classify` prompt 优化 — 覆盖发现→证据→决策(D2)→变更→验证全链。

**已知适配实例:**
- `trading-runtime` — 详见 `TRADING-RUNTIME-V0.5-ARCH.md` + `BASELINE-COMPLETENESS-SUPPLEMENT.md`
- `TG-model-module` — 详见 `TG-MODEL-FUNCTION-MODULE-BASELINE-CONTRACT.md` + `TG-IMPLEMENTATION-ALIGNMENT-CONTRACT.md`
- `lottery-module` — 4 L2 + 1 L3 契约已登记，详见 `CONTRACT-REGISTRY.md`

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

### Futures-Sim v0.1 — Phase 5 COMPLETE 🔒

**日期:** 2026-07-21
**文档:** `memory/state/huo/FUTURES-SIM-V0.1-ARCH.md`
**状态:** Phase 1-5 全线通过，BASELINE_READY

### Phase 5.1 Historical Dataset Expansion ✅ (2026-07-21)

**工具:** `tools/futures_data_import/akshare_export.py` — 独立采集脚本，不属于 market_futures 核心
**数据:** AkShare (新浪财经) 6 品种主力连续日线，2022-2026，每品种 967 bar
**品种:** RB (螺纹钢), I (铁矿石), JM (焦煤), CU (沪铜), AL (沪铝), SC (原油)
**架构约束:** ✅ 不增加 provider 模块 ✅ 不改 Phase 1-5 架构 ✅ 不改 Event Contract
**关键发现:** Breakout 模拟 +179.83% → 真实 -95.93%，验证了模拟行情偏置的严重性
**文档更新:** `FUTURES-SIM-VALIDATION-NOTE.md` v1.1（追加新证据）
**状态标记:** PHASE_STATUS 应更新为 phase5.1=PASS

**关键更新 (Phase 5):**
- 新增 `replay/loader.py` + `converter.py` — 历史 CSV → FUTURES_QUOTE 转换
- 输出完全符合 Event Contract（100% Schema 兼容）
- `run_strategy.py --events <path>` 支持自定义事件源
- 验证三连通过: Schema 一致性 ✅ / Replay 集成 ✅ / 确定性 ✅
- 验证了同一策略在历史 vs 模拟数据上行为差异明显（MA +12.77% vs -1.22%），确认模拟行情具有实验偏差需要 Phase 6 分析

**已完成基线:**
```
Phase 1-4 (模拟闭环)  ✅
Phase 5 (历史Replay)  ✅  新增 replay/ + data/historical/
```
**下一阶段:** Phase 6 — 策略验证差异分析（模拟 vs 历史）

**文件结构:**
```
market_futures/
├── futures_contracts.json         ✅ Phase 1
├── collector.py                   ✅ Phase 1
├── position.py                    ✅ Phase 2
├── account.py                     ✅ Phase 2
├── simulator.py                   ✅ Phase 2
├── strategies/                    ✅ Phase 3
├── run_strategy.py                ✅ Phase 3+4+5 (--events 支持)
├── reports/performance.py         ✅ Phase 4
├── replay/
│   ├── __init__.py                ✅ Phase 5
│   ├── loader.py                  ✅ Phase 5
│   └── converter.py               ✅ Phase 5
├── data/historical/               ✅ Phase 5 (示例CSV)
├── FUTURES-SIM-VALIDATION-NOTE.md  ✅ v1.0 (验证差异记录)
└── PHASE_STATUS.json              ✅ FROZEN
```

### Local Model Production Trial v1.0 ✅ COMPLETE

**Status:** production active (scoped) — 已验证可承担生产职责

| Step | Status |
|:---|:---:|
| Step 1 解耦链 | ✅ |
| Step 2 validation | ✅ |
| Step 3 手动验证 | ✅ |
| Step 4 生产路由注册 | ✅ |
| Production evidence (144 calls, 100%) | ✅ |

**架构:** 本地模型不作为云端降级替代。通过 `local-task-worker.sh` 处理 8 类确定型生产任务。
**边界:** 复杂推理/主任务 → DeepSeek；确定型任务 → Ollama qwen2.5:3b。
**关键文件:** `ollama-production.jsonl` (232 条, 0 失败), `local-task-worker.sh`。

### 引号 Bug 修复 (2026-07-21 12:00)

**事件:** `local-task-worker.sh` 中 4 个任务生成函数（json_validate/event_tagging/change_summary/report_format）echo JSON 时 key 双引号未转义，导致 44 条空类型记录混入生产数据。

**数据边界:** 修复前 44 条缺陷数据。旧数据保留用作工程缺陷审计，不用于评价模型表现。新观察窗口 `2026-07-21T04:00:33Z`。

**当前状态:** Local Model Production v1 — 修复完成，重新进入观察期。8 任务全链路稳定性验收中。

**生产观察表:**
| 任务 | 状态 |
|:---|:---:|
| system_status_brief | ✅ |
| log_summary | ✅ |
| config_explain | ✅ |
| event_classify | ⚠️ 0% 空输出，模型能力 ✅；38% 逐行分类（prompt 歧义），需收敛输出格式 |
| json_validate | 🆕 修复后观察 |
| event_tagging | 🆕 修复后观察 |
| change_summary | 🆕 修复后观察 |
| report_format | 🆕 修复后观察 |

**详情:** `memory/events/huo/2026-07-21.md`

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

## Phase 6 Runtime Paper Trading

### Phase 6.1 — Signal → Runtime Pipeline ✅ (2026-07-21)

**文件:** `trading-runtime/` (独立于 `market_futures/`)

| 组件 | 状态 |
|:---|:---:|
| `signal_receiver.py` | ✅ SIGNAL → ORDER (含无效 action 过滤) |
| `paper_executor.py` | ✅ ORDER + QUOTE → FILL (按时间戳匹配最近行情) |
| `runtime_account.py` | ✅ FILL → POSITION + 账户资金/保证金 |
| `position_sync.py` | ✅ FILL 重放 vs 账户持仓一致性校验 |
| `run_runtime.py` | ✅ 主入口 (支持 --replay-events, --signal-events) |
| `tests/test_all.py` | ✅ 三项验证: 独立消费/账本一致性/可复现性 |

**验证结果 (MA 策略 × 6 品种 × 4 年):**
- 328 SIGNAL → 328 ORDER → 328 FILL (100% 链路)
- 持仓一致性: 6 品种全通过
- 可复现性: 3/3 次结果一致

**冻结:** `market_futures/` 零改动

### Phase 6.2 — Runtime Mark-to-Market ✅ (2026-07-21)

**新增组件:**
| 组件 | 职责 |
|:---|:---|
| `market_monitor.py` | QUOTE 消费 → 按品种最新行情快照 |
| `valuation.py` | 持仓估值 → unrealized_pnl + equity + margin_used + risk_ratio |
| `risk_snapshot.py` | 风险快照 → 权益峰值/回撤/阈值预警 + 断点恢复 |

**验证三项通过:**
- Test 1: 浮盈浮亏一致 ✅ (多头/空头/组合/亏损均正确)
- Test 2: 持仓变化同步 ✅ (FILL→POSITION→VALUATION 一致)
- Test 3: 断点恢复 ✅ (存→清空→恢复→续跑, 状态不丢)

**当前系统形态:**
```
market_futures (回测/验证)
  Strategy → SIGNAL
              ↓
       ┌─────┴──────┐
       ↓             ↓
  simulator    trading-runtime (持续仿真)
  (回测)         Signal → Order → Fill
                            → Position → Valuation → Risk
                            → State Persistence
```

**架构文档:** `memory/state/huo/TRADING-RUNTIME-V0.5-ARCH.md` (Phase 6.5 冻结基线)

**下阶段建议 (Phase 6.3):**
- 实时行情推送模拟
- 长时间运行稳定性
- 绩效报告层衔接

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

**互补层（Observe 阶段新增）：**
| 层 | 类型 | 输出 | 状态 |
|:---|:----|:-----|:----:|
| Phase 8 Integrity | 定量观察（指标/阈值） | `integrity_observe.jsonl` | 🔒 FROZEN |
| Observer Abstraction | 定性观察（模式/抽象） | `observer-gap-report.jsonl` | 📄 proposal — 7-14d 观察期 |

**文档位置:** `memory/state/huo/OBSERVER-ABSTRACTION-LAYER-v1.0.md`

**Phase 1 观察指标：** 抽象准确率 / 误升级率 / 重复模式发现能力

### TG 对话观察工具 — 新增

**相关文件:**
- `memory/state/huo/TG-BEHAVIOR-DATA-CONTRACT.md` — 数据隔离规则
- `memory/state/huo/DIAGNOSTICS-BEHAVIOR-LAYER.md` — 工作笔记

**工具（仅限离线 Observer 使用）：**
| 工具 | 功能 |
|:-----|:------|
| `tools/tg_transcript_reader.py` | session 抽取 |
| `tools/tg_behavior_analyzer.py` | 6 类检测 |
| `tools/tg_maintenance_queue.py` | findings → queue |

**阻断路径：** TG transcript → Memory → 终端模型行为融合（🚫 永久阻断）

**注意：** 以上工具不属于系统运行时能力，仅用于离线观察。读取 TG transcript 的行为由 TG-BEHAVIOR-DATA-CONTRACT 约束，禁止任何数据进入 memory/rules/SOUL。

---

## 基线合规审计记录

**日期:** 2026-07-21
**范围:** `market_futures/` + `trading-runtime/`
**结论:** 🟢 PASS

```
Extension Boundary     🟢 PASS
Memory Namespace       🟢 PASS
Terminal Authority     🟢 PASS
Module Ownership       🟢 PASS
Freeze Integrity       🟢 PASS

Documentation Coverage 🟡 YELLOW-A → ✅ 已修复 (TRADING-RUNTIME-V0.5-ARCH.md)

Overall:               GREEN WITH DOCUMENTATION WARNING
```

**修复记录:** YELLOW-A 治理缺口 (trading-runtime 缺独立架构文档) 于 2026-07-21 通过新增 `memory/state/huo/TRADING-RUNTIME-V0.5-ARCH.md` 闭环。

### Baseline Completeness Supplement

**文档:** `memory/state/huo/BASELINE-COMPLETENESS-SUPPLEMENT.md`
**日期:** 2026-07-21
**结论:** 8 项补充检查全部 🟢 Valid Observation，无治理缺口，无违规项。

| # | 项目 | 优先级 | 判定 |
|:-:|------|:------:|:----:|
| ① | Interface Contract | P0 | 🟢 已冻结 (schema.md + FUTURES_QUOTE 契约) |
| ② | Determinism | P0 | 🟢 历史路径确定 |
| ③ | Data Provenance | P1 | 🟢 来源已记录 |
| ④ | Risk Boundary | P1 | 🟢 纯观察层 |
| ⑤ | State Recovery | P1 | 🟢 已实现并验证 |
| ⑥ | Test Archive | P2 | 🟢 测试充分 |
| ⑦ | Config Governance | P3 | 🟢 无多环境需求 |
| ⑧ | Audit Trail | P3 | 🟢 追溯链完整 |
