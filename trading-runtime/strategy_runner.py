"""
trading-runtime — strategy_runner.py (策略运行器)

职责: QUOTE → 多策略 → 信号 → 交易链路

输入: FUTURES_QUOTE 事件 (实时流)
输出: FUTURES_SIGNAL 事件 (进入 signal_receiver → ORDER → FILL)

架构:
  market_stream (QUOTE)
     ↓
  strategy_runner
     ├── MARuntime       (MA5/20 金叉死叉)
     ├── BreakoutRuntime (20期突破)
     ├── RSIRuntime      (RSI超买超卖)
     └── ActivityTest    (高频触发验证)
     ↓
  FUTURES_SIGNAL
     ↓
  signal_receiver → ORDER → paper_executor → FILL → runtime_account

使用:
  from strategy_runner import StrategyRunner

  runner = StrategyRunner()
  runner.add_default_strategies()

  # for each quote:
  signals = runner.on_quote(quote)

  # for each signal:
  orders = generate_orders([signals])

边界:
  - 不接触账户/成交/保证金
  - 不存储策略状态 (只在内存)
  - 策略间独立, 互不影响
"""

from typing import Optional
from datetime import datetime, timezone, timedelta

from strategies.ma_runtime import MARuntime
from strategies.breakout_runtime import BreakoutRuntime
from strategies.rsi_runtime import RSIRuntime
from strategies.activity_test import ActivityTest

BJT = timezone(timedelta(hours=8))

# 品种列表 (与历史数据一致)
ALL_SYMBOLS = ["RB", "I", "JM", "CU", "AL", "SC"]


class StrategyRunner:
    """多策略运行器 — 统一调度"""

    def __init__(self):
        self.strategies: list = []
        self._signal_log: list[dict] = []

    def add_strategy(self, strategy):
        """添加一个策略实例"""
        self.strategies.append(strategy)
        strat_id = getattr(strategy, "strategy_id", type(strategy).__name__)
        print(f"[strategy_runner] ➕ 策略注册: {strat_id}")

    def add_default_strategies(self):
        """添加默认策略集"""
        self.add_strategy(MARuntime(qty=1))
        self.add_strategy(BreakoutRuntime(qty=1))
        self.add_strategy(RSIRuntime(qty=1))
        self.add_strategy(ActivityTest(
            entry_every_n=3,
            take_profit_pct=0.5,
            stop_loss_pct=-0.3,
            max_hold_bars=10,
            qty=1,
        ))

    def add_strategies_by_list(self, config: list[dict]):
        """
        从配置列表添加策略

        config: [
            {"type": "MA", "qty": 1, "fast_period": 5, "slow_period": 20},
            {"type": "Breakout", "qty": 1, "lookback": 20},
            {"type": "RSI", "qty": 1, "period": 14},
            {"type": "ActivityTest", "qty": 1, "entry_every_n": 3},
        ]
        """
        type_map = {
            "MA": MARuntime,
            "Breakout": BreakoutRuntime,
            "RSI": RSIRuntime,
            "ActivityTest": ActivityTest,
        }
        for cfg in config:
            cls = type_map.get(cfg.get("type", ""))
            if not cls:
                print(f"[strategy_runner] ⚠️ 未知策略类型: {cfg.get('type')}")
                continue
            params = {k: v for k, v in cfg.items() if k != "type"}
            self.add_strategy(cls(**params))

    def on_quote(self, quote: dict, position_info: dict = None) -> list[dict]:
        """
        收到一条 QUOTE → 运行所有策略 → 收集信号

        Args:
            quote: FUTURES_QUOTE event dict
            position_info: 当前持仓信息 {symbol: {"qty": int, ...}}

        Returns:
            list[dict]: FUTURES_SIGNAL 事件列表
        """
        signals = []

        for strategy in self.strategies:
            try:
                sig = strategy.on_quote(quote, position_info)
                if sig is not None:
                    signals.append(sig)
                    self._signal_log.append({
                        "ts": sig.get("ts", ""),
                        "strategy": sig.get("strategy_id", ""),
                        "symbol": sig.get("symbol", ""),
                        "action": sig.get("action", ""),
                    })
            except Exception as e:
                strat_id = getattr(strategy, "strategy_id", "?")
                print(f"[strategy_runner] ⚠️ 策略 {strat_id} 异常: {e}")

        return signals

    def sync_positions(self, position_info: dict):
        """同步持仓状态到各策略"""
        for strategy in self.strategies:
            if hasattr(strategy, "sync_positions"):
                strategy.sync_positions(position_info)

    def signal_stats(self) -> dict:
        """信号统计"""
        counts = {}
        for s in self._signal_log:
            key = f"{s['strategy']}:{s['action']}"
            counts[key] = counts.get(key, 0) + 1

        by_strategy = {}
        for s in self._signal_log:
            sid = s["strategy"]
            by_strategy.setdefault(sid, {"signals": 0, "actions": {}})
            by_strategy[sid]["signals"] += 1
            act = s["action"]
            by_strategy[sid]["actions"][act] = \
                by_strategy[sid]["actions"].get(act, 0) + 1

        return {
            "total_signals": len(self._signal_log),
            "by_strategy": by_strategy,
            "action_summary": dict(counts),
        }

    def reset(self):
        """重置所有策略状态"""
        for strategy in self.strategies:
            if hasattr(strategy, "reset"):
                strategy.reset()
        self._signal_log.clear()
        print("[strategy_runner] 🔄 全部策略状态已重置")
