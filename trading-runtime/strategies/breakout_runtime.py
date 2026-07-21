"""
trading-runtime — strategies/breakout_runtime.py (突破策略 Runtime版)

逻辑: 20期唐奇安通道突破
  - 价格突破过去 N 期最高价 → BUY
  - 价格跌破过去 N 期最低价 → SELL
  - 反向突破时先 CLOSE 再开新仓

输入: FUTURES_QUOTE dict (单条)
输出: FUTURES_SIGNAL dict | None
"""

from collections import deque
from typing import Optional
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))


class BreakoutRuntime:
    """突破策略 Runtime版 (20期唐奇安通道)"""

    def __init__(self, strategy_id: str = "Breakout",
                 lookback: int = 20,
                 qty: int = 1):
        self.strategy_id = strategy_id
        self.lookback = lookback
        self.qty = qty

        self._prices: dict[str, deque] = {}
        self._position_direction: dict[str, Optional[str]] = {}

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[dict]:
        """收到单条行情 → 返回策略信号 or None"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        if symbol not in self._prices:
            self._prices[symbol] = deque(maxlen=self.lookback)

        # 检查突破前需要完整窗口
        need_more = len(self._prices[symbol]) < self.lookback

        if not need_more:
            window = list(self._prices[symbol])
            channel_high = max(window)
            channel_low = min(window)

            current_dir = self._position_direction.get(symbol)
            signal = None

            # 向上突破
            if price > channel_high:
                if current_dir == "LONG":
                    return None
                action = "CLOSE" if current_dir == "SHORT" else "BUY"
                signal = self._make_signal(symbol, action,
                                           f"向上突破 ¥{channel_high:.1f}")
            # 向下突破
            elif price < channel_low:
                if current_dir == "SHORT":
                    return None
                action = "CLOSE" if current_dir == "LONG" else "SELL"
                signal = self._make_signal(symbol, action,
                                           f"向下突破 ¥{channel_low:.1f}")

            if signal:
                self._prices[symbol].append(price)
                return signal

        # 加入当前价格到窗口
        self._prices[symbol].append(price)
        return None

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
            "confidence": 0.65,
            "note": note,
        }

    def reset(self, symbol: str = None):
        if symbol:
            self._prices.pop(symbol, None)
            self._position_direction.pop(symbol, None)
        else:
            self._prices.clear()
            self._position_direction.clear()
