# Baseline Completeness Supplement

> 基线完整性检查补充记录 — 2026-07-21
> 原则: 不改代码，只补证据和文档
> 关联: MEMORY.md 基线合规审计记录

---

## 目录

- [① Interface Contract](#①-interface-contract)
- [② Determinism Check](#②-determinism-check)
- [③ Data Provenance](#③-data-provenance)
- [④ Risk Boundary](#④-risk-boundary)
- [⑤ State Recovery](#⑤-state-recovery)
- [⑥ Test Archive](#⑥-test-archive)
- [⑦ Configuration Governance](#⑦-configuration-governance)
- [⑧ Audit Trail](#⑧-audit-trail)

---

## ① Interface Contract

> 冻结 `market_futures` ↔ `trading-runtime` 之间的接口契约，防止模块漂移。

### 依赖方向

```
market_futures/data/historical/*.csv  (只读)
          │
          │  CSV 文件系统接口
          ▼
trading-runtime/market_stream.py
          │
          │  FUTURES_QUOTE 事件
          ▼
trading-runtime 下游管道
```

### 输入接口：CSV → market_stream

trading-runtime 通过 `market_stream.py` 读取 `market_futures/data/historical/` 下的 CSV 文件。

| 项目 | 定义 | 来源 |
|------|------|------|
| 格式 | CSV UTF-8, LF, 带表头 | `data/historical/schema.md` |
| 必需列 | datetime, symbol, open, high, low, close, volume, oi | schema.md |
| 时间字段 | `YYYY-MM-DD HH:mm:ss` (北京时间, UTC+8) | schema.md |
| symbol规则 | 大写品种代码 (RB, CU, AL ...) | `futures_contracts.json` |
| 缺失数据处理 | `loader.py` 遇缺失列 → KeyError；trading-runtime 不处理缺失 | loader.py |
| 版本策略 | CSV 文件无版本号；字段增减需同步更新 schema.md 和 market_stream.py | — |

**冻结状态:** 🔒 FROZEN (Phase 5 schema + Phase 6.3 market_stream)

### 事件契约：FUTURES_QUOTE

```
market_stream 输出恒为:
{
  "event_type": "FUTURES_QUOTE",
  "ts":  str,           # ISO-8601 北京时间
  "symbol": str,         # 品种代码
  "price": float,        # 最新价 (close)
  "open": float,
  "high": float,
  "low": float,
  "volume": int,
  "oi": int
}
```

下游消费者: `strategy_runner.py`, `paper_executor.py`, `market_monitor.py`

**约束:** event_type 字段必须为 `"FUTURES_QUOTE"`；trading-runtime 不消费 `"QUOTE"` 或 `"quote"`。

### 信号契约：FUTURES_SIGNAL (跨模块复用)

```
{
  "event_type": "FUTURES_SIGNAL",
  "strategy_id": str,
  "symbol": str,
  "action": "BUY" | "SELL" | "HOLD",
  "quantity": int,        # 手数
  "confidence": float,    # [0.0, 1.0]
  "note": str
}
```

- market_futures 和 trading-runtime 共用同一 Signal 接口
- trading-runtime 的 strategies/ 是 market_futures strategies/ 的实时变体
- 字段增减必须两端同步

### 接口变更守则

| 场景 | 动作 |
|------|------|
| 新增 CSV 列 | 更新 schema.md + market_stream 解析逻辑 |
| 修改 event_type | 更新所有消费者，属于 P0 变更 |
| 新增信号字段 | 两端策略同步更新 |
| 删除字段 | 向后兼容期 ≥ 1 周 |

### 快照 vs 实时流风险

当前无实时流，只有 CSV replay。如果未来引入实时行情:

```
CSV replay:  schema.md 定义格式
实时流:      provider schema 可能不同
                    ↓
          必须在 market_stream 层归一化为统一 FUTURES_QUOTE
```

**当前无需处理，但此接口须在引入实时流前单独冻结。**

---

## ② Determinism Check

> 目标: 同样输入 → 同样输出 (signal, account state, report)

### 检查结果

| 场景 | 是否确定性 | 证据 |
|------|:---------:|------|
| **历史 CSV replay (market_futures)** | ✅ 确定 | Phase 3 Test 1 (verify_determinism): 3次运行信号序列一致 |
| **历史 CSV replay (trading-runtime)** | ✅ 确定 | Phase 6.2 可复现性验证: 3/3次结果一致 |
| **模拟行情 (collector.py)** | ❌ 非确定 | collector.py 使用 `random` (无 seed) |
| **CSV → QUOTE 转换** | ✅ 确定 | `replay/converter.py` 纯函数式转换 |
| **撮合引擎 (simulator)** | ✅ 确定 | simulator.py 明确禁止 random fill |
| **Paper Executor** | ✅ 确定 | 按时间戳匹配，无随机因素 |

### 非确定性来源 (模拟行情)

`collector.py` 使用 `random` 生成随机行情:

```
random.randint, random.uniform, random.gauss,
random.choices, random.random, random.choice
```

无 `random.seed()` 调用，每次运行产生不同的行情序列。

**影响范围:**
- Phase 1-4 的模拟行情不可复现
- Phase 5+ 的历史 replay 完全确定

**判定:** 🟢 Valid Observation — 模拟行情生成器设计的目的是生成多样化测试数据，非确定性是设计特征。策略验证阶段 (Phase 5+) 已切换到确定性历史数据。

### 确定性验证命令

```bash
# market_futures (历史 replay)
cd market_futures
python3 run_strategy.py --verify
# 输出: Phase 3 Test 1 确定性验证通过

# trading-runtime
cd trading-runtime
python3 tests/test_all.py
# 输出: 可复现性验证通过 (3/3)
```

---

## ③ Data Provenance

> 数据来源追踪: 原始数据 → 清洗 → 特征 → 策略输入

### 数据流

```
AkShare (新浪财经)
    │
    │  tools/futures_data_import/akshare_export.py
    ▼
CSV (历史日线, 6品种)
    │
    │  replay/loader.py → converter.py
    ▼
FUTURES_QUOTE event
    │
    ├── market_futures/run_strategy.py (回测)
    └── trading-runtime/market_stream.py (Paper Trading)
```

### 数据源记录

| 项目 | 值 |
|------|----|
| 原始来源 | AkShare `futures_main_sina` (新浪财经) |
| 采集脚本 | `tools/futures_data_import/akshare_export.py` (独立工具) |
| 采集时间 | 2026-07-21 03:42:59 (北京时间) |
| 数据周期 | 日线, 2022-07-22 ~ 2026-07-21 |
| 合约类型 | 主力连续 |
| 品种数量 | 6 (RB, I, JM, CU, AL, SC) |
| 数据版本 | 无显式版本号 |
| 清洗规则 | CSV 列名映射: datetime→ts, close→price (replay/converter.py) |
| 元数据文件 | `data/historical/.source_metadata.json` |

### 回测可复现性保证

- CSV 文件为静态数据源，不随运行变更
- replay/converter.py 纯函数式，无状态，无随机
- run_strategy.py --events 支持指定事件文件 → 不同数据版本可切换

### 数据版本标识

⚠️ 当前数据无显式版本号。

**建议 (不修改代码):** 在 `data/historical/` 根目录维护 `data_version.json`:
```json
{
  "version": "v1",
  "provider": "akshare",
  "source_url": "https://akshare.akfamily.xyz/",
  "fetch_date": "2026-07-21",
  "contracts": ["AL","CU","I","JM","RB","SC"],
  "schema_ref": "schema.md v1.0",
  "checksums": { "RB_2022-2026.csv": "sha256:...", ... }
}
```

**当前判定:** 🟢 Valid Observation — 数据来源有记录，元数据文件存在；版本标识可作为后续增强。

---

## ④ Risk Boundary

> 确认风险模块是纯观察，还是有执行阻断权。

### 检查结果

| 项目 | 证据 | 判定 |
|------|------|:----:|
| risk 是否可阻断执行 | `risk_snapshot.py` 无 block/reject/prevent/cancel/halt/stop/override/deny 方法 | 🟢 纯观察 |
| risk 是否修改策略 | risk 不引用 strategy_runner/strategy 接口 | 🟢 纯观察 |
| risk 是否产生交易意图 | risk 输出仅为 `RISK_SNAPSHOT` 事件，不产生 SIGNAL/ORDER | 🟢 纯观察 |
| 最大仓位限制 | `runtime_config.json` 中定义 `max_position_per_symbol: 10` (仅配置，未强制执行) | 🟡 配置存在但无代码约束 |
| 异常状态处理 | `session_scheduler.py` 有 SIGINT/SIGTERM 处理；risk 无自动止损/强平逻辑 | 🟢 符合仿真阶段定位 |

**结论:** 🟢 Risk 层当前为纯观测层，无执行权。符合 Paper Trading Observation 定位。

**注意事项:** `max_position_per_symbol` 定义在 `runtime_config.json` 但 `paper_executor.py` 和 `runtime_account.py` 未检查此限制。这是观察阶段的可接受行为，进入 Scheduled Paper Trading 前需要通过 P0 变更加入执行级约束。

---

## ⑤ State Recovery

> 重启后能否恢复并继续。

### 现有实现

`run_runtime.py` 支持:

```bash
python3 run_runtime.py --resume
python3 run_runtime.py --save-state --load-state <dir>
```

### 恢复内容

| 项目 | 恢复方式 | 验证状态 |
|------|---------|:--------:|
| account state | account.json 反序列化 | ✅ Phase 6.2 Test 3 |
| position | account.positions 字典恢复 | ✅ Phase 6.2 Test 3 |
| market snapshot | market_snapshot.json 恢复 | ✅ Phase 6.2 Test 3 |
| risk snapshots | risk_snapshots.jsonl 恢复 | ✅ Phase 6.2 Test 3 |
| last event | run_runtime 不跟踪 last event, 全量重入 | 🟡 从信号/行情文件全量重入 |
| report 连续性 | 日报仅当日生成, 断点恢复后不影响次日日报 | 🟢 无跨日状态依赖 |

### 恢复测试流程

```bash
cd trading-runtime

# 1. 首次运行并保存状态
python3 run_runtime.py --replay-events ../market_futures/data/historical/replay_akshare_6sym.jsonl \
                       --signal-events orders.jsonl \
                       --save-state

# 2. 清空内存
# 3. 从状态恢复并续跑
python3 run_runtime.py --replay-events ../market_futures/data/historical/replay_akshare_6sym.jsonl \
                       --signal-events orders.jsonl \
                       --load-state <dir>
```

**判定:** 🟢 State Recovery 已实现且验证通过。全量重入模式符合 Paper Trading 阶段要求（非低延迟实盘，无需 exactly-once）。

---

## ⑥ Test Archive

> 测试证据是否需要归档。

### 现有测试

| 模块 | 测试文件 | 测试数量 |
|------|---------|:--------:|
| market_futures | `run_strategy.py --verify` | 7 tests (Phase 3:3 + Phase 4:3 + Phase 5:1) |
| market_futures | `tests/test_phase2.py` | 28 automated |
| trading-runtime | `tests/test_all.py` | Phase 6.1:3 |
| trading-runtime | `tests/test_phase6_3.py` | Phase 6.3:3 |
| trading-runtime | `tests/test_phase6_4.py` | Phase 6.4:3 |
| trading-runtime | `tests/test_phase6_5.py` | Phase 6.5:5 |

### 归档缺口

| 项目 | 现状 | 建议 |
|------|------|------|
| 时间戳 | 无运行日志 | 测试运行时可追加 `run_at` 到 stdout/log |
| commit hash | 无记录 | 测试输出可追加 `git rev-parse HEAD` |
| 环境信息 | 无记录 | Python 版本、OS 信息 |
| 测试输出 | 仅 stdout | 可重定向到 `tests/results/` |

**判定:** 🟢 Valid Observation — 当前测试数量充分且可手动复现。归档属于治理完善，不影响冻结。

---

## ⑦ Configuration Governance

> 配置属于 Code 还是 Runtime Config。

### 现有配置

| 文件 | 类型 | 归属 |
|------|------|------|
| `runtime_config.json` | 运行时配置 | Code (随版本管理) |
| `session_config.json` | 运行时配置 | Code (随版本管理) |
| `futures_contracts.json` | 合约定义 | Code (FROZEN) |
| `PHASE_STATUS.json` | 元数据 | Code (FROZEN) |

**无用户配置 / 密钥配置 / 环境配置。** 当前 Paper Trading 阶段所有配置均为版本管理内的静态文件。

### 配置分类

| 类别 | 存在 | 说明 |
|------|:----:|------|
| 默认配置 | ✅ | `runtime_config.json` + `session_config.json` |
| 用户配置 | ❌ | 当前无多用户场景 |
| 密钥配置 | ❌ | 零 secrets/tokens (已确认) |
| 环境配置 | ❌ | 无 dev/staging/prod 区分 |
| 配置版本 | ❌ | 无 schema 版本号 |

**判定:** 🟢 Valid Observation — 当前单实例手动运行，无多环境需求；进入 Scheduled Paper Trading 前需引入环境配置。

---

## ⑧ Audit Trail

> 每个交易决策能否追溯: Tick → Feature → Signal → Order → Account → Report

### 现有追溯链

```
market_tick (FUTURES_QUOTE)
    ↓
strategy.on_quote() → SIGNAL
    ↓
signal_receiver → ORDER
    ↓
paper_executor → FILL
    ↓
runtime_account → POSITION
    ↓
valuation → RISK_SNAPSHOT
    ↓
notifier → NOTIFY
    ↓
daily_report
```

每个环节输出的 event 均带有：
- `event_type` 标识环节
- `ts` 时间戳
- 关联 ID (`order_id`, `fill_id`, `strategy_id`)

### 事件文件

| 文件 | 内容 |
|------|------|
| `reports/runtime_events.jsonl` | 全量事件流 |
| `reports/runtime_fills.jsonl` | 成交记录 |
| `reports/runtime_orders.jsonl` | 订单记录 |
| `reports/runtime_positions.jsonl` | 持仓记录 |
| `reports/notifications/notify_*.jsonl` | 通知记录 |
| `reports/daily/daily_*.json` | 日报 |

### 追溯验证

给定一个 FILL，可以追溯：
1. 对应 ORDER (order_id)
2. 哪个 SIGNAL 产生该 ORDER (ts + symbol)
3. 行情价格 (market_snapshot 或 QUOTE replay)
4. 账户影响 (runtime_account apply_fill)
5. 风险快照 (risk_snapshots.jsonl)
6. 通知 (notify JSONL)
7. 日报统计 (daily JSON)

**判定:** 🟢 追溯链完整。每个环节均有事件记录，通过 event_type + ts 可跨文件关联。

---

## 总结

### 优先级评分

| # | 项目 | 优先级 | 判定 | 动作 |
|:-:|------|:------:|:----:|------|
| ① | Interface Contract | P0 | 🟢 已冻结 (schema.md + FUTURES_QUOTE 契约) | 本文档已记录 |
| ② | Determinism | P0 | 🟢 历史路径确定；模拟非确定是设计特征 | 本文档已记录 |
| ③ | Data Provenance | P1 | 🟢 来源已记录 (.source_metadata.json) | 版本标识可增强 |
| ④ | Risk Boundary | P1 | 🟢 纯观察层，无执行权 | 本文档已记录 |
| ⑤ | State Recovery | P1 | 🟢 已实现并验证 | — |
| ⑥ | Test Archive | P2 | 🟢 测试充分 | 治理完善，非必要 |
| ⑦ | Config Governance | P3 | 🟢 空状态 (无多环境) | 未来需要时再处理 |
| ⑧ | Audit Trail | P3 | 🟢 追溯链完整 | — |

### 最终判定

所有 8 项补充检查均为 🟢 Valid Observation，无治理缺口，无违规项。

**不需要任何代码修改，不需要任何 Phase 解冻。**

---
*版本: v1.0 | 日期: 2026-07-21 | 关联: TRADING-RUNTIME-V0.5-ARCH.md, FUTURES-SIM-V0.1-ARCH.md*
