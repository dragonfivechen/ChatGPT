# 交易系统快速部署指导手册

> 基于 Trading Runtime Kernel 架构，新交易系统部署流程标准化。
> 适用：期货 / 股票 / 加密 / 期权 / 股指

---

## 一、新系统清单

| # | 必须实现 | 可复用 |
|---|----------|--------|
| 1 | `{market}_adapter.py` — 行情适配器 | `runtime/event_reader.py` |
| 2 | `{market}_engine.py` — 交易引擎 | `runtime/state_store.py` |
| — | — | `runtime/push_hook.py` |
| — | — | `runtime/strategy_base.py` |
| — | — | `deploy/install.sh` |

---

## 二、标准部署步骤

### Day 1 — 实现 Market Adapter

**文件：** `{market}/{market}_adapter.py`

职责：外部数据源 → 统一 `QUOTE` 事件

```python
def fetch() -> list[dict]:
    """获取最新行情，返回 list[Quote]"""
    ...

def is_trading_time() -> bool:
    """判断当前是否在交易时段"""
    ...
```

**事件格式：**
```python
{
    "event_type": "QUOTE",
    "symbol": "品种代码",
    "price": 100.0,
    "ts": "2026-07-22T10:00:00+08:00"
}
```

### Day 1 — 实现 Trading Engine

**文件：** `{market}/{market}_engine.py`

职责：市场规则全封装

| 方法 | 期货 | 股票 | 加密 |
|------|------|------|------|
| `open_long(symbol, qty, price)` | 开多 | — | 买入 |
| `open_short(symbol, qty, price)` | 开空 | — | — |
| `close_long(symbol, qty, price)` | 平多 | — | 卖出 |
| `close_short(symbol, qty, price)` | 平空 | — | — |
| `buy(symbol, qty, price)` | — | 买入 | — |
| `sell(symbol, qty, price)` | — | 卖出 | — |
| `margin(symbol)` | 保证金计算 | — | — |
| `fee(symbol, qty, price)` | 手续费 | 手续费 | 手续费 |

**账户模型必须包含：**
- `balance` — 可用资金
- `equity` — 总权益 = balance + 持仓浮动盈亏
- `positions` — 持仓字典
- `orders` — 订单记录
- `trades` — 成交记录
- `pnl_total` — 累计盈亏

### Day 2 — 接入 Runtime

**文件修改量：**

| 修改 | 行数 | 操作 |
|------|------|------|
| `runtime/engine_registry.py` | +1 | 注册新 Engine |
| `runtime/adapter_registry.py` | +1 | 注册新 Adapter |
| `deploy/timers/{market}_collector.conf` | ~10 | 采集定时器 |
| `deploy/timers/{market}_strategy.conf` | ~10 | 策略定时器 |

**注册示例：**

```python
# engine_registry.py
REGISTRY = {
    "futures": FuturesEngine,
    "stock": StockEngine,
    "crypto": CryptoEngine,
}
```

### Day 2 — 写策略

**文件：** `strategies/{name}_fx.py`

```python
from runtime.strategy_base import StrategyBase

class MyStrategy(StrategyBase):
    def on_quote(self, quote, position_info=None):
        if condition:
            return Signal(action="OPEN_LONG", symbol=..., qty=...)
```

**启动：**
```bash
python run.py --strategy my_strategy --engine futures --live
```

### Day 3 — 观察窗口

| 检查项 | 命令 |
|--------|------|
| 采集稳定 | `journalctl -u {market}-collector` |
| 增量推进 | `cat state/live_{strategy}.json | jq .last_line` |
| 账户一致 | `cat data/account_state.json | jq '{cash, positions, equity}'` |
| 推送正常 | TG 收到通知或确认静默 |

---

## 三、系统结构模板

```
{market}/
├── {market}_adapter.py       # [必须] 行情适配
├── {market}_engine.py        # [必须] 交易引擎
├── collector_{market}.py      # 采集入口（调用 adapter）
├── data/
│   └── account_state.json    # 自动生成
├── state/
│   └── live_*.json          # 自动生成
└── run.py                    # 入口脚本
```

**runtime/（复用，不改）**

```
runtime/
├── __init__.py
├── event_reader.py           # 增量读取 event log
├── state_store.py            # 策略/账户状态持久化
├── push_hook.py              # 通知管道
├── strategy_base.py          # Strategy ABC
├── engine_registry.py        # 引擎注册表
└── adapter_registry.py       # 适配器注册表
```

**deploy/（按需修改定时）**

```
deploy/
├── install.sh                # 安装 timer
├── templates/
│   ├── collector.service
│   ├── collector.timer
│   ├── strategy.service
│   └── strategy.timer
└── timers/
    ├── futures_collector.conf
    ├── futures_strategy.conf
    └── ...
```

---

## 四、部署成本预估

| 阶段 | 期货（实际） | 按模板重做 | 节省 |
|------|-------------|-----------|------|
| 行情采集 | 1 天 | 半天 | 50% |
| 账户/成交模型 | 2 天 | 1 天 | 50% |
| 增量引擎 | 1 天 | 复用 | 100% |
| 状态持久化 | 半天 | 复用 | 100% |
| 定时部署 | 半天 | 复用 | 100% |
| 推送管道 | 半天 | 复用 | 100% |
| **合计** | **5.5 天** | **1.5 天** | **73%** |

---

## 五、检查清单

部署完成后逐项确认：

- [ ] Adapter 能稳定采集（无连续 3 次失败）
- [ ] Engine 开仓/平仓计算正确
- [ ] 策略增量加载（第二次执行不重复处理）
- [ ] State offset 持续增长
- [ ] Account equity 每日归零或累积正确
- [ ] Push 通知：有成交必推，无成交不推
- [ ] systemd timer 在交易时段正常触发
- [ ] 非交易时段静默（is_trading_time 生效）

---

## 六、Pre-Flight 检查清单（部署前强制确认）

每启动一个新交易系统，逐项确认后签字：

| # | 检查项 | 判定 |
|:-:|--------|:----:|
| 1 | □ Event Schema 已确定 | ✅/❌ |
| 2 | □ Adapter 输出统一事件 | ✅/❌ |
| 3 | □ Engine 定义账户模型（balance/equity/positions） | ✅/❌ |
| 4 | □ Engine 定义成交规则（开/平/费/保证金/强制平仓） | ✅/❌ |
| 5 | □ Engine 定义风险参数（最大杠杆/持仓限制/止损） | ✅/❌ |
| 6 | □ Strategy 与 Engine 无耦合（策略不感知市场规则） | ✅/❌ |
| 7 | □ State 可恢复（中断后重启不丢数据 / 不重复成交） | ✅/❌ |
| 8 | □ timer 可独立部署（不依赖其他系统组件的安装顺序） | ✅/❌ |

**红线规则：**
- 1-5 任意 ❌ → 暂停部署，补齐再动
- 6-8 任意 ❌ → 标记技术债务，1 周内修复

---

## 七、常见问题

| 问题 | 原因 | 处理 |
|------|------|------|
| 采集连续失败 | DNS / API key / 网络 | 检查 adapter.fetch() |
| 策略重复成交 | offset 未持久化 | 检查 state_store |
| 账户 equity 负值 | 保证金不够 | 降低 qty 或提高初始资金 |
| 推送没收到 | push 脚本路径不对 | 检查 push_hook.py |
| Timer 没触发 | systemd 未 enable | `systemctl enable --now *.timer` |
