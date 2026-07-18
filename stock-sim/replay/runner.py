"""replay/runner.py — 事件回放引擎

按时间顺序重放历史 events，驱动完整交易闭环。
只读，不修改事件。
"""

import json
import time
import sys
import os
from typing import Optional

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

class ReplayRunner:
    """事件回放器。输入 events 列表，按时间戳排序后依次驱动引擎。"""

    def __init__(self, initial_cash: float = 1_000_000.0):
        self.initial_cash = initial_cash

    def run(
        self,
        events: list[dict],
        strategy_engine,
        execution_sim,
        account,
        drawdown_tracker,
        portfolio_snapshot_fn,
    ) -> dict:
        """执行回放。

        参数:
            events: 事件列表（未排序，会按 timestamp 排序）
            strategy_engine: StrategyEngine 实例
            execution_sim: ExecutionSimulator 实例
            account: Account 实例
            drawdown_tracker: DrawdownTracker 实例
            portfolio_snapshot_fn: 生成快照的函数

        返回: BACKTEST_RESULT dict
        """
        # 按时间排序
        sorted_events = sorted(
            events,
            key=lambda e: e.get("timestamp", ""),
        )

        trade_count = 0
        quotes_processed = 0
        signals_generated = 0

        for evt in sorted_events:
            etype = evt.get("event_type", "")

            if etype == "MARKET_QUOTE":
                quotes_processed += 1

                # 构建 portfolio view
                pos = account.positions
                pf_view = {
                    "cash": account.cash,
                    "equity": account.equity,
                    "positions": {
                        sym: {"quantity": p.quantity}
                        for sym, p in pos.items()
                        if p.quantity > 0
                    },
                }

                # 策略处理
                signals = strategy_engine.on_quote(evt, pf_view)
                signals_generated += len(signals)

                for sig_evt in signals:
                    from strategy.adapter import signal_to_order
                    o = signal_to_order(sig_evt)
                    if o is None:
                        continue
                    o.status = "SUBMITTED"
                    execution_sim.add_order(o.to_dict())

                # 成交检查
                trades = execution_sim.on_quote(evt)
                for t in trades:
                    from account.ledger import apply_trade
                    apply_trade(account, t)
                    trade_count += 1

                # 组合快照
                if portfolio_snapshot_fn:
                    from portfolio.calculator import (
                        calc_market_value,
                        calc_holdings,
                        calc_return,
                    )
                    symbol = evt.get("symbol", "")
                    price = evt.get("data", {}).get("price", 0)
                    quotes = {symbol: price} if symbol and price else {}

                    mv = calc_market_value(account, quotes)
                    eq = account.cash + mv
                    peak, draw = drawdown_tracker.update(eq)
                    h = calc_holdings(account, quotes, eq)
                    portfolio_snapshot_fn(
                        account.account_id,
                        account.cash,
                        mv,
                        eq,
                        h,
                        calc_return(eq, account.initial_cash),
                        peak,
                        draw,
                    )

        # 结果汇总
        final_eq = account.cash + sum(
            p.quantity * p.avg_cost
            for p in account.positions.values()
        )
        total_return = (
            (final_eq - self.initial_cash) / self.initial_cash
            if self.initial_cash > 0
            else 0.0
        )

        return {
            "event_type": "BACKTEST_RESULT",
            "initial_cash": self.initial_cash,
            "final_equity": round(final_eq, 2),
            "total_return": round(total_return, 4),
            "final_cash": round(account.cash, 2),
            "realized_pnl": round(account.realized_pnl, 2),
            "trades": trade_count,
            "quotes_processed": quotes_processed,
            "signals_generated": signals_generated,
            "peak_equity": round(drawdown_tracker.peak_equity, 2),
        }
