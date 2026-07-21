# Trading-Runtime v0.5 — 架构冻结文档

> ```yaml
> contract:
>   name: TRADING-RUNTIME-V0.5-ARCH
>   version: v0.5
>   level: L2
>   parent: FUNCTION-MODULE-BASELINE-CHECK-CONTRACT
>   scope: paper trading runtime
>   owner: 燃🔥
>   status: frozen
> ```
>
> 冻结时间: 2026-07-21
> 状态: 🔒 FROZEN（Phase 6.5 全线通过）
> 归属: Futures-Sim v0.1 → Paper Trading Runtime Layer
> 前置依赖: `market_futures/` (回测/验证层, FROZEN)
> 定位: 独立 Paper Trading 持续仿真层，不属 Simulation Layer
> 非定位: ❌ 实盘交易 ❌ 自动执行 ❌ 生产级部署 ❌ AI 决策增强

---

## 1. 顶层定位

```
OpenClaw Core (不可接入)
│
├── stock-sim                 ← A股模拟验证
│
└── market_futures/           ← 期货回测/验证层 (FROZEN)
     │
     │  历史CSV replay / 策略验证
     │
     └── trading-runtime/     ← 期货 Paper Trading 持续仿真层 (FROZEN)
          ├── Signal → Order → Fill
          ├── Position → Valuation → Risk
          ├── Session Scheduler
          ├── Notifier + Daily Report
          └── State Persistence (断点恢复)
```

**核心原则：**
- Paper Trading = Runtime Observation Layer，不是交易执行层
- `market_futures/` 是上游验证源，只历史 replay，不共享状态
- 输出仅限本地 JSONL / console，不推送外部通知
- 不和 OpenClaw Core / Kernel / Gateway / Memory 交互

---

## 2. 目录结构

```
trading-runtime/
├── PHASE_STATUS.json              ← Phase 6.1-6.5 全部 FROZEN
├── runtime_config.json            ← 账户/市场/风控/时段配置
├── session_config.json            ← 交易时段定义 (2日盘 + 1夜盘)
├── account_init.py                ← 账户初始化 (10M CNY PAPER)
│
├── live_session.py                ← 长驻运行入口 (Phase 6.4)
├── run_runtime.py                 ← 回放运行入口 (Phase 6.2)
├── session_scheduler.py           ← 交易时段状态机调度器
├── preloader.py                   ← 盘前预采集
│
├── market_stream.py               ← 行情流 (CSV → QUOTE, 时钟驱动)
├── strategy_runner.py             ← 实时策略运行 (4策略)
├── signal_receiver.py             ← SIGNAL → ORDER 转换
├── paper_executor.py              ← ORDER + QUOTE → FILL
├── runtime_account.py             ← 账户模型 (保证金+盯市结算)
├── market_monitor.py              ← 品种最新行情快照
├── valuation.py                   ← 持仓估值 (浮盈/权益/风险率)
├── risk_snapshot.py               ← 风险快照 (回撤/阈值预警)
├── position_sync.py               ← 持仓一致性校验
│
├── notifier.py                    ← 本地通知 (成交/持仓/风控/状态)
├── daily_report.py                ← 日结报告生成
│
├── state/                         ← 运行时持久化 (断点恢复)
│   └── session_<date>_<time>/
│       ├── account.json
│       ├── market_snapshot.json
│       ├── risk_snapshots.jsonl
│       └── state_meta.json
│
├── reports/                       ← 运行报告输出
│   ├── daily/                     ← 日报 JSON
│   ├── notifications/             ← 通知 JSONL
│   ├── runtime_events.jsonl
│   ├── runtime_fills.jsonl
│   ├── runtime_orders.jsonl
│   └── runtime_positions.jsonl
│
├── strategies/                    ← 实时策略 (复用 market_futures 接口)
│   ├── ma_runtime.py
│   ├── breakout_runtime.py
│   ├── rsi_runtime.py
│   └── activity_test.py
│
└── tests/
    ├── test_all.py                ← Phase 6.2 三验证
    ├── test_phase6_3.py
    ├── test_phase6_4.py
    └── test_phase6_5.py
```

---

## 3. 管道架构（Pipeline）

### 3.1 11 层管道

```
           ┌──────────────┐
           │ session_     │  ← 交易时段状态机 (WAITING→PRE_MARKET→OPEN→TRADING→CLOSE→REPORT→DONE)
           │ scheduler    │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ preloader    │  ← 盘前预采集：检查数据可用性、加载历史基准
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ market_stream│  ← 行情流：CSV → FUTURES_QUOTE (时钟/批量/调度模式)
           └──────┬───────┘
                  │ FUTURES_QUOTE
                  ▼
           ┌──────────────┐
           │ strategy_    │  ← 实时策略：MA/Breakout/RSI/ActivityTest
           │ runner       │     每 N 条 QUOTE 同步持仓
           └──────┬───────┘
                  │ FUTURES_SIGNAL
                  ▼
           ┌──────────────┐
           │ signal_      │  ← 信号接收：SIGNAL → ORDER (过滤无效 action)
           │ receiver     │
           └──────┬───────┘
                  │ ORDER
                  ▼
           ┌──────────────┐
           │ paper_       │  ← 模拟执行：ORDER + QUOTE → FILL (按时间戳匹配)
           │ executor     │
           └──────┬───────┘
                  │ FILL
                  ▼
           ┌──────────────┐
           │ runtime_     │  ← 账户：FILL → POSITION + 保证金 + 资金
           │ account      │
           └──────┬───────┘
                  │ POSITION
                  ▼
           ┌──────────────┐
           │ valuation    │  ← 估值：浮盈浮亏 + equity + margin + risk_ratio
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ risk_        │  ← 风险快照：权益峰值/回撤/阈值预警
           │ snapshot     │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ notifier     │  ← 通知：成交/持仓/风控/状态 → 本地 JSONL + console
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ daily_report │  ← 日报：成交统计/胜率/品种分析 → JSON + text
           └──────────────┘
```

### 3.2 数据流

```
market_stream ──→ strategy_runner ──→ signal_receiver
                                         │
                                         ▼
                                    paper_executor
                                         │
                                         ▼
                                   runtime_account
                                         │
                                         ▼
                              market_monitor + valuation
                                         │
                                         ▼
                                   risk_snapshot
                                         │
                                    ┌────┴────┐
                                    ▼         ▼
                               notifier   daily_report
                                    │
                                    ▼
                              local JSONL
```

### 3.3 交易日生命周期

```
PRE_MARKET (08:45)
    │  preloader: 历史数据检查 + 基准加载
    ▼
OPEN (09:00)
    │  scheduler → market_stream → strategy → signal
    ▼
TRADING (09:00-10:15, 10:30-11:30, 13:30-15:00, 21:00-23:00)
    │  小节区间: 盘中持续交易
    │  小节间隔: 10:15-10:30 休息 (状态不切换)
    │  全链路: QUOTE → SIGNAL → ORDER → FILL → POSITION → RISK
    ▼
CLOSE (各小节最末收市)
    │  scheduler → notifier.session_state
    ▼
REPORT
    │  daily_report.generate() → JSON + text
    ▼
DONE
```

---

## 4. 状态所有权

### 4.1 状态空间划分

```
OpenClaw Memory (不可接入)
├── events/       ← 系统事件日志 (不包含交易信号)
├── state/        ← 系统契约/架构文档
├── data/         ← 原始业务数据 (不含交易运行时)

Trading Runtime (独立状态空间)
├── state/        ← 模块级运行时持久化 (断点恢复)
│   └── session_<date>_<time>/
│       ├── account.json         ← 账户状态快照
│       ├── market_snapshot.json  ← 行情快照
│       ├── risk_snapshots.jsonl  ← 风险记录
│       └── state_meta.json      ← 元数据
│
├── reports/      ← 业务运行日志 (非系统 event namespace)
│   ├── runtime_events.jsonl
│   ├── runtime_fills.jsonl
│   ├── runtime_orders.jsonl
│   ├── runtime_positions.jsonl
│   ├── daily/
│   └── notifications/
```

**约束：**
- 不写入 `memory/events/` — 交易运行时日志不属于系统事件
- 不写入 `memory/state/` — 架构文档归燃🔥所有，已在此文件
- 不写入 `memory/data/` — 原始行情数据仍存于 `market_futures/data/historical/`

### 4.2 身份隔离

- Owner: 燃🔥（终端全权维护）
- TG Agent: 审计/分析/建议，零执行权限
- 无 TG 修改代码、注入策略、代替执行的情况

---

## 5. 与 market_futures 的边界

| 维度 | market_futures | trading-runtime |
|------|---------------|-----------------|
| 层级 | 回测/验证层 | Paper Trading 持续仿真层 |
| 行情源 | 模拟生成 + 历史 CSV | 仅历史 CSV replay |
| 策略 | signals/ (同源接口) | strategies/ (实时变体) |
| 执行 | simulator.py (批量撮合) | paper_executor.py (逐笔撮合) |
| 输出 | 绩效报告 (reports/) | 通知+日报 (reports/) |
| 状态 | 函数式，无持久化 | 状态持久化 (断点恢复) |
| 冻结 | FROZEN | FROZEN |
| 依赖方向 | ← 无 | → 读取历史 CSV |

**关键约束：** trading-runtime 不修改 `market_futures/` 任何文件。历史 CSV 只读。

---

## 6. 部署生命周期

### 6.1 当前阶段：手动运行

```
阶段: Observation
入口: python3 live_session.py / run_runtime.py
调度: 无 systemd / cron / daemon
通知: 仅本地 JSONL + console
```

### 6.2 未来阶段（待批准后执行）

```
阶段: Scheduled Paper Trading
入口: systemd timer → oneshot worker
通知: → push-gate.mjs → Telegram
约束:
  - 不引入 daemon (timer + oneshot)
  - 通知走统一出口 (push-gate)
  - 不自动执行实盘操作
```

### 6.3 部署原则

- 生产部署前必须通过终端确认（P0 变更）
- 接入通知链前必须集成 push-gate.mjs
- 所有凭证零硬编码（.secrets/ 隔离）

---

## 7. 冻结状态

### 7.1 总体状态

```
Phase 6.1 — Signal → Runtime Pipeline        🔒 FROZEN
Phase 6.2 — Runtime Mark-to-Market            🔒 FROZEN
Phase 6.3 — Market Stream + Strategy Runner   🔒 FROZEN
Phase 6.4 — Live Session + Scheduler          🔒 FROZEN
Phase 6.5 — Preloader + Notifier + Report     🔒 FROZEN
```

### 7.2 验证通过记录

| Phase | Tests | Result |
|:-----:|-------|:------:|
| 6.1 | 独立消费 / 账本一致性 / 可复现性 (3/3) | ✅ PASS |
| 6.2 | 浮盈一致 / 持仓同步 / 断点恢复 (3/3) | ✅ PASS |
| 6.3 | 6品种 streaming / 4策略 / 全链路 (3/3) | ✅ PASS |
| 6.4 | 300s 稳定运行 / 信号过滤 / 动态加载 (3/3) | ✅ PASS |
| 6.5 | preloader / notifier / report / scheduler / integration (5/5) | ✅ PASS |

### 7.3 冻结约束

```
基线保护: Phase 6.5 架构、管道、接口
允许修复: 审计缺口 / 正确性 / 数据完整性
禁止扩展: 新策略 / 新数据源 / 实盘 / AI 决策 / 自动修复
```

---

## 8. 配置定义

### 8.1 runtime_config.json

```json
{
  "account": {
    "initial_cash": 10000000,
    "account_type": "PAPER"
  },
  "market": {
    "stream": { "speed_sec": 10.0 },
    "trading_hours": [
      ["09:00", "11:30"],
      ["13:30", "15:00"],
      ["21:00", "23:00"]
    ]
  },
  "session": {
    "state_save_interval": 300,
    "max_events_per_session": 10000
  },
  "risk": {
    "max_drawdown_pct": 20.0,
    "max_margin_ratio": 80.0,
    "max_position_per_symbol": 10
  }
}
```

### 8.2 session_config.json

```json
{
  "sessions": [
    {
      "name": "morning",
      "prepare": "08:45", "open": "09:00",
      "sections": [
        {"start": "09:00", "end": "10:15"},
        {"start": "10:30", "end": "11:30"}
      ]
    },
    {
      "name": "afternoon",
      "prepare": "12:45", "open": "13:30",
      "sections": [
        {"start": "13:30", "end": "15:00"}
      ]
    }
  ],
  "night_session": {
    "enabled": true,
    "prepare": "20:45", "open": "21:00",
    "sections": [{"start": "21:00", "end": "23:00"}]
  },
  "data": {
    "history_lookback": 120,
    "symbols": ["RB", "I", "JM", "CU", "AL", "SC"]
  },
  "daily_report": { "enable": true },
  "notification": {
    "enable": true,
    "events": ["fill","position","risk_warning","session_state"]
  }
}
```

---

## 9. 相关文档

| 文档 | 位置 | 关系 |
|------|------|------|
| FUTURES-SIM-V0.1-ARCH.md | `memory/state/huo/` | 上游回测层架构，本模块的前置依赖 |
| FUTURES-SIM-VALIDATION-NOTE.md | `market_futures/` | 验证差异记录 |
| PHASE_STATUS.json | `market_futures/` | 上游冻结标记 |
| PHASE_STATUS.json | `trading-runtime/` | 本模块冻结标记 (Phase 6.5) |
| FREEZE-CONTRACT.md | `memory/state/huo/` | 冻结契约，本模块受其约束 |
| MEMORY.md | workspace root | 系统维护索引，包含 Phase 6 状态记录 |

---

## 10. 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.5 | 2026-07-21 | 初始冻结文档，覆盖 Phase 6.1-6.5 完整架构 |
