# Futures-Sim v0.1 — 架构冻结文档

> 冻结时间: 2026-07-21
> 状态: 🔒 FROZEN（锁边界，再动代码）
> 定位: Stock-Sim 的期货版策略验证环境
> 非定位: ❌ 娱乐交易游戏 ❌ LLM 自动判断 ❌ 核心 Kernel 扩展

---

## 1. 顶层定位

```
OpenClaw (不可接入 Kernel)
│
├── stock-sim          ← A股模拟验证环境
│
└── market_futures/    ← 期货模拟验证环境 (NEW)
     ├── 行情生成/采集
     ├── 合约管理
     ├── 策略实验
     └── 交易账户结算
```

**核心原则:**
- Futures-Sim = Simulation Layer, 不是 Trading Layer
- Event 是唯一事实来源（futures_events.jsonl）
- 策略接口与 Stock-Sim 复用，一套策略可跨市场测试
- 不接入核心 Kernel / Gateway / Runtime

---

## 2. 目录结构

```
market_futures/
├── futures_contracts.json      ← 合约定义（乘数/保证金/费率）
├── futures_events.jsonl        ← Event 事实来源
│
├── collector.py                 ← 行情生成器（模拟/历史）
├── simulator.py                 ← 撮合引擎
├── run_strategy.py              ← 策略运行入口（对标 stock-sim/runtime/run_strategy.py）
│
├── contract.py                  ← 合约模型
├── account.py                   ← 期货账户（保证金/盯市结算）
├── position.py                  ← 多空持仓模型
│
├── strategies/                  ← 策略
│   ├── __init__.py
│   ├── MA.py                    ← 移植 stock-sim
│   ├── breakout.py              ← 移植 stock-sim
│   └── rsi.py                   ← 移植 stock-sim
│
└── reports/                     ← 绩效报告
    └── (待定)
```

**与 stock-sim 的镜像关系:**

| Stock-Sim | Futures-Sim | 说明 |
|-----------|-------------|------|
| market/collector.py | collector.py | 行情来源不同（期货模拟生成） |
| trading/execution/simulator.py | simulator.py | 撮合逻辑不同（保证金/双向） |
| account/model.py | account.py | 账户模型不同（盯市结算/强平） |
| portfolio/model.py | position.py | 持仓模型不同（多空/手数） |
| strategy/base.py | strategies/ (复用接口) | Signal 复用，策略基类复用 |
| events/*.jsonl | futures_events.jsonl | 事件流分离，不混入 stock-sim |
| runtime/run_strategy.py | run_strategy.py | 入口模式对齐 |

---

## 3. 合约模型（Asset Model）

### 3.1 期货 vs 股票核心差异

| 维度 | 股票 | 期货 |
|------|------|------|
| 单位 | 股 | 手 |
| 资金需求 | 全额买入 | 保证金（杠杆） |
| 方向 | 单向做多 | 双向（多/空） |
| 结算 | 卖出后结算 | 每日盯市结算（逐日盯市） |
| 持仓周期 | 无限制 | 交割月限制 |
| T+规则 | T+1（A股） | T+0 |
| 费用 | 印花税+佣金 | 开仓+平仓手续费 |

### 3.2 合约定义格式

```json
{
  "symbol": "RB",
  "name": "螺纹钢",
  "exchange": "上期所",
  "multiplier": 10,
  "margin_rate": 0.10,
  "tick_size": 1,
  "tick_value": 10,
  "fee_open": 3.0,
  "fee_close": 3.0,
  "base_price": 3300,
  "price_step": 5,
  "delivery_month": [1, 5, 10],
  "limit_up": 0.05,
  "limit_down": 0.05
}
```

字段说明:
- `multiplier`: 合约乘数（每手多少吨/桶/克）
- `margin_rate`: 保证金比例（如 0.10 = 10%）
- `tick_size`: 最小变动价位
- `tick_value`: 每跳价值 = multiplier × tick_size
- `fee_open`/`fee_close`: 开/平仓手续费（元/手，固定费率模式）
- `base_price`: 模拟行情的基准价
- `limit_up`/`limit_down`: 涨跌停板幅度

### 3.3 首批合约（15个品种）

| 代码 | 名称 | 乘数 | 保证金 | 最小变动 | 每跳价值 | 基准价 |
|------|------|------|--------|---------|---------|--------|
| RB | 螺纹钢 | 10 | 10% | 1 | 10 | 3300 |
| I | 铁矿石 | 100 | 12% | 0.5 | 50 | 800 |
| SC | 原油 | 1000 | 10% | 0.1 | 100 | 520 |
| CU | 沪铜 | 5 | 8% | 10 | 50 | 68000 |
| AU | 沪金 | 1000 | 8% | 0.02 | 20 | 450 |
| AG | 沪银 | 15 | 10% | 1 | 15 | 5800 |
| RU | 橡胶 | 10 | 10% | 5 | 50 | 13500 |
| M | 豆粕 | 10 | 8% | 1 | 10 | 3100 |
| P | 棕榈油 | 10 | 10% | 2 | 20 | 7800 |
| TA | PTA | 5 | 8% | 2 | 10 | 5200 |
| MA | 甲醇 | 10 | 10% | 1 | 10 | 2200 |
| FG | 玻璃 | 20 | 10% | 1 | 20 | 1400 |
| ZC | 动力煤 | 100 | 12% | 0.2 | 20 | 750 |
| HC | 热卷 | 10 | 10% | 1 | 10 | 3500 |
| SN | 沪锡 | 1 | 10% | 10 | 10 | 220000 |

---

## 4. 事件流（Event Model）

### 4.1 事件文件

```
market_futures/
└── futures_events.jsonl    ← 单文件事件流，append-only
```

**不混入 stock-sim 的 events/ 目录**，原因：
- 期货事件有独立的字段（保证金、盯市结算等）
- 两条事件流分开，互不影响
- replay 的时候各自重放

### 4.2 事件类型定义

```python
# ─── 行情事件 ───
{
  "event_type": "FUTURES_QUOTE",
  "ts": "2026-07-21T09:30:00+08:00",
  "symbol": "RB",
  "price": 3210.0,
  "open": 3200.0,
  "high": 3225.0,
  "low": 3190.0,
  "pre_close": 3200.0,
  "volume": 53200,
  "oi": 1250000
}

# ─── 策略信号事件 ───
# 复用 stock-sim 的 Signal 结构，但 event_type 区分
{
  "event_type": "FUTURES_SIGNAL",
  "strategy_id": "MA_RB_V1",
  "symbol": "RB",
  "action": "BUY",          # BUY / SELL / HOLD
  "quantity": 2,            # 手数
  "confidence": 0.7,
  "note": "MA5_cross_MA20_up"
}

# ─── 订单事件 ───
{
  "event_type": "FUTURES_ORDER",
  "order_id": "F20260721_001",
  "ts": "2026-07-21T09:30:01+08:00",
  "symbol": "RB",
  "side": "BUY",            # BUY (开多) / SELL (开空)
  "order_type": "MARKET",
  "quantity": 2
}

# ─── 成交事件 ───
{
  "event_type": "FUTURES_FILL",
  "order_id": "F20260721_001",
  "fill_id": "FILL_001",
  "ts": "2026-07-21T09:30:02+08:00",
  "symbol": "RB",
  "side": "BUY",
  "fill_price": 3211.0,
  "fill_qty": 2,
  "fee": 6.0,
  "margin": 6422.0
}

# ─── 持仓变更事件 ───
{
  "event_type": "FUTURES_POSITION_CHANGE",
  "ts": "2026-07-21T09:30:02+08:00",
  "symbol": "RB",
  "direction": "long",
  "qty": 2,
  "entry_price": 3211.0,
  "margin_used": 6422.0
}

# ─── 盯市结算事件 ───
{
  "event_type": "FUTURES_SETTLEMENT",
  "ts": "2026-07-21T15:00:00+08:00",
  "settle_price": 3215.0,
  "positions": [
    {"symbol": "RB", "direction": "long", "qty": 2, "entry": 3211.0, "pnl": 80.0}
  ],
  "equity_change": 80.0,
  "margin_required": 6430.0,
  "risk_ratio": 1.35
}

# ─── 强平事件 ───
{
  "event_type": "FUTURES_LIQUIDATION",
  "ts": "2026-07-21T13:45:00+08:00",
  "symbol": "RB",
  "direction": "long",
  "qty": 2,
  "liquidation_price": 3180.0,
  "realized_pnl": -620.0,
  "reason": "risk_ratio_below_1.0"
}
```

### 4.3 事件生产-消费流

```
行情生成器 (collector.py)
    │
    ├──→ futures_events.jsonl [FUTURES_QUOTE]
    │
    ▼
策略引擎 (run_strategy.py 内)
    │  signal = strategy.on_quote()
    │
    ├──→ futures_events.jsonl [FUTURES_SIGNAL]
    │
    ▼
模拟撮合 (simulator.py)
    │  order → check → fill
    │
    ├──→ futures_events.jsonl [FUTURES_ORDER → FUTURES_FILL]
    │
    ▼
账户结算 (account.py)
    │  position update → margin check → settlement
    │
    ├──→ futures_events.jsonl [FUTURES_POSITION_CHANGE / FUTURES_SETTLEMENT / FUTURES_LIQUIDATION]
    │
    ▼
绩效分析 (reports/)
```

---

## 5. 账户模型（保证金+盯市结算）

### 5.1 账户结构

```
FuturesAccount
├── initial_equity: 1,000,000
├── balance: float              ← 现金余额（入金-出金+已实现盈亏）
├── positions: dict             ← symbol → FuturesPosition
│   ├── direction: "long" | "short"
│   ├── qty: int                ← 手数
│   ├── entry_price: float      ← 开仓均价
│   └── latest_price: float     ← 最新/结算价
│
├── floating_pnl: float         ← 浮动盈亏（按最新价计算）
├── margin_used: float          ← 保证金占用
├── equity: float               ← 动态权益 = balance + floating_pnl
├── available: float            ← 可用资金 = equity - margin_used
├── risk_ratio: float           ← 风险率 = equity / margin_used (≤1.0 → 强平)
├── realized_pnl: float         ← 已实现盈亏
└── total_fees: float           ← 总手续费
```

### 5.2 保证金计算

```
保证金 = 最新价 × 合约乘数 × 手数 × 保证金比例

例: 螺纹钢(RB) @ 3210, 2手:
保证金 = 3210 × 10 × 2 × 0.10 = 6,420 元
```

### 5.3 逐日盯市结算

```
浮动盈亏:
  多头: (当前价 - 开仓价) × 乘数 × 手数
  空头: (开仓价 - 当前价) × 乘数 × 手数

盯市结算（盘后）:
  结算价 = 收盘/指定结算价
  保证金 = 结算价 × 乘数 × 手数 × 保证金率
  盈亏入账 balance
  可用资金 = balance - 保证金
```

### 5.4 强平逻辑

```python
risk_ratio = equity / margin_used

if risk_ratio < 1.2:     # 风险率 < 120%
    warnings.append("保证金不足")

if risk_ratio < 1.0:     # 风险率 < 100%
    liquidation()        # 强平（从持仓最大品种开始）
```

### 5.5 手续费

```
固定费率模式:
  开仓手续费 = price × multiplier × qty × fee_rate
  平仓手续费 = price × multiplier × qty × fee_rate

fee_rate = 0.00005 (万分之0.5)

或固定金额模式（按品种）:
  开仓 = 3元/手
  平仓 = 3元/手
```

---

## 6. 行情生成器

### 6.1 模式一：模拟行情（夜间/离线测试）

```
MarketGenerator
├── 随机游走 + 均值回归基础模型
├── 趋势状态机 (up/down/sideways/volatile)
├── 周期切换 (日盘/夜盘开盘特征)
├── 成交量模拟 (价格波动大 → 放量)
└── 极端行情注入 (可选压力测试)
```

### 6.2 模式二：历史重放（真实行情验证）

```
HistoricReplay
├── 加载历史分钟K线
├── 按时间推进 → 生成 FUTURES_QUOTE
└── 策略在真实数据上运行
```

### 6.3 市场状态定义

```python
MARKET_STATES = {
    "trend_up":     "趋势上涨",
    "trend_down":   "趋势下跌",
    "sideways":     "震荡盘整",
    "breakout_up":  "向上突破",
    "breakout_down":"向下突破",
    "high_vol":     "高波动",
    "gap_open":     "跳空开盘",
}
```

---

## 7. 策略接口

### 7.1 复用 stock-sim 的 Signal + Strategy 基类

策略接口与 stock-sim 保持一致：

```python
class FuturesStrategy(ABC):
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self._active = False

    @abstractmethod
    def on_quote(self, quote: dict, positions: dict) -> Optional[Signal]:
        """
        参数:
          quote: FUTURES_QUOTE event dict
          positions: 当前持仓 dict {symbol: {direction, qty, entry_price, pnl}}
        返回:
          Signal(action="BUY"/"SELL"/"HOLD", symbol, quantity)
        """
        ...
```

### 7.2 首批策略（移植）

| 策略 | 移植自 | 说明 |
|------|--------|------|
| MA | stock-sim | 均线交叉，改为期货合约参数 |
| Breakout | stock-sim | 突破策略，适配期货波动率 |
| RSI | stock-sim | 超买超卖，改为期货多空适用 |

### 7.3 策略运行入口

```
run_strategy.py --strategy MA --symbol RB --mode simulate --duration 2h
run_strategy.py --strategy breakout --symbol CU --mode replay --data kline.csv
```

与 `stock-sim/runtime/run_strategy.py` 使用相同参数风格。

---

## 8. 与 stock-sim 的关系

### 8.1 共享组件

| 组件 | 模式 | 说明 |
|------|------|------|
| Strategy 基类 (Signal) | 复用 | `from stock_sim.strategy.base import Signal` 或 fork |
| 策略引擎 (dispatch) | 复用 | 行情分发逻辑一致 |
| 报告指标 | 复用 | 收益率/夏普/最大回撤/胜率 |

### 8.2 独立组件（不可复用）

| 组件 | 原因 |
|------|------|
| 合约模型 | 期货有乘数/保证金/多空方向 |
| 账户模型 | 保证金/盯市结算/风险率 |
| 撮合引擎 | 双向开平/保证金检查 |
| 行情生成 | 期货波动特征不同（高杠杆放大波动） |
| 事件类型 | FUTURES_* 前缀，独立 jsonl |

### 8.3 不共享

- ❌ events.jsonl（不混入 stock-sim 的 events/ 目录）
- ❌ Account（股票全额 vs 期货保证金）
- ❌ Portfolio（股票 T+1 vs 期货 T+0）
- ❌ Order（股票只买 vs 期货多空双向）

---

## 9. 治理边界

### 9.1 ✅ 第一阶段做

1. 复制目录结构（`market_futures/` + 核心文件）
2. 合约定义 JSON（15 个品种）
3. 行情生成器（模拟模式）
4. 账户模型（保证金/多空/盯市结算）
5. 撮合引擎（双向/保证金检查/强平）
6. 移植 3 个策略（MA/Breakout/RSI）
7. 事件流（futures_events.jsonl）
8. 运行入口（run_strategy.py）

### 9.2 ❌ 第一阶段不做

- LLM 自动判断期货买卖方向
- 多因子模型
- 强化学习
- 实时行情接入（实盘数据源）
- 与 OpenClaw Kernel/Gateway 集成
- 自动交易执行
- Web/TG 交互界面（后期可考虑，当前只 CLI）

### 9.3 架构底线

```
1. Event 是唯一事实来源     ← 必须遵守
2. 策略不碰账户             ← 必须遵守（策略只输出 Signal）
3. 撮合不决定价格           ← 必须遵守（价格来自行情生成器）
4. futures_events.jsonl 独立 ← 必须遵守（不混入 stock-sim）
5. 保证金检查不可绕过        ← 必须遵守（期货核心风控）
```

---

## 10. 现文件处理

| 文件 | 处理 |
|------|------|
| `workspace/futures_sim.py` | 保留，标记为 `v0.1-LEGACY`，**不继续堆功能** |
| `workspace/market_futures/` | 新建（本架构对应目录） |

---

## 11. 后续阶段规划

| 阶段 | 内容 | 时间 |
|------|------|------|
| v0.1 | 架构冻结 + 核心框架 + 模拟行情 + 3 策略 | 当前 |
| v0.2 | 历史数据重放 + 报告系统 | 待定 |
| v0.3 | 策略组合 + 资金管理模块 | 待定 |
| v1.0 | 实盘数据源 + 策略优化 | 待定 |

---

## 12. 冻结声明

> 本文件锁定 Futures-Sim v0.1 的架构边界、数据结构、事件流和治理规则。
> 任何对该架构的修改必须通过架构审计。
> 代码实现必须严格遵循本文件中定义的合约和边界。
>
> 🔒 FROZEN at 2026-07-21

---

## 附录：关键指标计算公式

```
收益率 = (期末权益 - 期初权益) / 期初权益
胜率 = 盈利交易次数 / 总交易次数
盈亏比 = 平均盈利 / 平均亏损
最大回撤 = max(峰值权益 - 谷值权益) / 峰值权益
夏普比 = (平均收益率 - 无风险利率) / 收益率标准差
持仓周期 = 平均每笔持仓的 tick 数
风险率 = 动态权益 / 保证金占用
```
