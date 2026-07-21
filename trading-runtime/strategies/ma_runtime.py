"""
trading-runtime — strategies/ma_runtime.py (MA策略 Runtime版)

逻辑: MA5 金叉/死叉
  - 快线(MA5) 上穿 慢线(MA20) → BUY
  - 快线下穿慢线 → SELL
  - 策略自行管理持仓方向, 反向信号时自动 CLOSE

输入: FUTURES_QUOTE dict (单条)
输出: FUTURES_SIGNAL dict | None
"""

from collections import deque
from typing import Optional
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))


class MARuntime:
    """MA策略 Runtime版 (MA5/MA20)"""

    def __init__(self, strategy_id: str = "MA",
                 fast_period: int = 5,
                 slow_period: int = 20,
                 qty: int = 1):
        self.strategy_id = strategy_id
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.qty = qty

        # 状态: symbol → 数据窗口
        self._windows: dict[str, deque] = {}
        self._prev_fast: dict[str, Optional[float]] = {}
        self._prev_slow: dict[str, Optional[float]] = {}
        self._position_direction: dict[str, Optional[str]] = {}  # LONG / SHORT / None

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[dict]:
        """
        收到单条行情 → 返回策略信号 or None

        Args:
            quote: FUTURES_QUOTE event dict
            position_info: {symbol: {"qty": int, "direction": str}}

        Returns:
            FUTURES_SIGNAL dict or None
        """
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        # 维护窗口
        if symbol not in self._windows:
            self._windows[symbol] = deque(maxlen=self.slow_period)
        self._windows[symbol].append(price)

        if len(self._windows[symbol]) < self.slow_period:
            return None

        window = list(self._windows[symbol])
        fast_ma = sum(window[-self.fast_period:]) / self.fast_period
        slow_ma = sum(window) / self.slow_period

        prev_fast = self._prev_fast.get(symbol)
        prev_slow = self._prev_slow.get(symbol)

        signal = None
        current_dir = self._position_direction.get(symbol)

        if prev_fast is not None and prev_slow is not None:
            # 金叉 (快线上穿慢线)
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                if current_dir == "LONG":
                    return None  # 已在多头
                action = "CLOSE" if current_dir == "SHORT" else "BUY"
                signal = self._make_signal(symbol, action,
                                           f"MA金叉 {fast_ma:.1f}/{slow_ma:.1f}")
            # 死叉 (快线下穿慢线)
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                if current_dir == "SHORT":
                    return None
                action = "CLOSE" if current_dir == "LONG" else "SELL"
                signal = self._make_signal(symbol, action,
                                           f"MA死叉 {fast_ma:.1f}/{slow_ma:.1f}")

        self._prev_fast[symbol] = fast_ma
        self._prev_slow[symbol] = slow_ma

        return signal

    def _make_signal(self, symbol: str, action: str, note: str) -> dict:
        """构造 FUTURES_SIGNAL"""
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
            "confidence": 0.7,
            "note": note,
        }

    def reset(self, symbol: str = None):
        """重置策略状态 (用于恢复后)"""
        if symbol:
            self._windows.pop(symbol, None)
            self._prev_fast.pop(symbol, None)
            self._prev_slow.pop(symbol, None)
            self._position_direction.pop(symbol, None)
        else:
            self._windows.clear()
            self._prev_fast.clear()
            self._prev_slow.clear()
            self._position_direction.clear()
