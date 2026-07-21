"""
trading-runtime — strategies/rsi_runtime.py (RSI策略 Runtime版)

逻辑: 14期 RSI
  - RSI < 30 (超卖区回升) → BUY
  - RSI > 70 (超买区回落) → SELL
  - RSI 回到 40-60 中性区 → CLOSE

输入: FUTURES_QUOTE dict (单条)
输出: FUTURES_SIGNAL dict | None
"""

from collections import deque
from typing import Optional
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))


class RSIRuntime:
    """RSI策略 Runtime版 (14期)"""

    def __init__(self, strategy_id: str = "RSI",
                 period: int = 14,
                 oversold: float = 30.0,
                 overbought: float = 70.0,
                 close_low: float = 40.0,
                 close_high: float = 60.0,
                 qty: int = 1):
        self.strategy_id = strategy_id
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.close_low = close_low
        self.close_high = close_high
        self.qty = qty

        self._changes: dict[str, deque] = {}
        self._prev_price: dict[str, float] = {}
        self._prev_rsi: dict[str, float] = {}
        self._position_direction: dict[str, Optional[str]] = {}

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[dict]:
        """收到单条行情 → 返回策略信号 or None"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        # 需要前值计算变化
        if symbol not in self._prev_price:
            self._prev_price[symbol] = price
            self._changes[symbol] = deque(maxlen=self.period)
            return None

        change = price - self._prev_price[symbol]
        self._prev_price[symbol] = price

        if symbol not in self._changes:
            self._changes[symbol] = deque(maxlen=self.period)
        self._changes[symbol].append(change)

        if len(self._changes[symbol]) < self.period:
            return None

        changes = list(self._changes[symbol])
        avg_gain = sum(c for c in changes if c > 0) / self.period
        avg_loss = sum(-c for c in changes if c < 0) / self.period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rsi = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

        prev_rsi = self._prev_rsi.get(symbol, 50.0)
        self._prev_rsi[symbol] = rsi

        current_dir = self._position_direction.get(symbol)
        signal = None

        # RSI 从超卖区回升 → BUY
        if rsi > self.oversold and prev_rsi <= self.oversold:
            if current_dir != "LONG":
                action = "CLOSE" if current_dir == "SHORT" else "BUY"
                signal = self._make_signal(symbol, action,
                                           f"RSI回升 {prev_rsi:.1f}→{rsi:.1f}")

        # RSI 从超买区回落 → SELL
        elif rsi < self.overbought and prev_rsi >= self.overbought:
            if current_dir != "SHORT":
                action = "CLOSE" if current_dir == "LONG" else "SELL"
                signal = self._make_signal(symbol, action,
                                           f"RSI回落 {prev_rsi:.1f}→{rsi:.1f}")

        # RSI 回到中性区 → CLOSE
        elif self.close_low <= rsi <= self.close_high and current_dir is not None:
            signal = self._make_signal(symbol, "CLOSE",
                                       f"RSI中性区 {rsi:.1f}")

        return signal

    def _make_signal(self, symbol: str, action: str, note: str) -> dict:
        if action == "BUY":
            self._position_direction[symbol] = "LONG"
        elif action == "SELL":
            self._position_direction[symbol] = "SHORT"
        elif action == "CLOSE":
            self._position_direction[symbol] = None
        return {
            "event_type": "FUTURES_SIGNAL",
            "ts": datetime.now(BJT).isoformat(),
            "strategy_id": self.strategy_id,
            "symbol": symbol,
            "action": action,
            "qty": self.qty,
            "confidence": 0.6,
            "note": note,
        }

    def reset(self, symbol: str = None):
        if symbol:
            self._changes.pop(symbol, None)
            self._prev_price.pop(symbol, None)
            self._prev_rsi.pop(symbol, None)
            self._position_direction.pop(symbol, None)
        else:
            self._changes.clear()
            self._prev_price.clear()
            self._prev_rsi.clear()
            self._position_direction.clear()
