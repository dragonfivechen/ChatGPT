"""strategy/breakout.py — 简单突破策略 v0.1

逻辑:
  当前价突破 N 日高点 → BUY
  当前价跌破 N 日低点 → SELL

参数:
  lookback: 观察窗口（条数）
  buy_threshold: 买入倍数
  sell_threshold: 卖出倍数

初始状态: 空仓。
"""

from .base import Strategy, Signal


class BreakoutStrategy(Strategy):
    """简单突破策略。跟踪近期价格区间，突破则反向操作。"""

    def __init__(self, strategy_id: str = "BREAKOUT_V1",
                 lookback: int = 2, atr_multiple: float = 1.5):
        super().__init__(strategy_id)
        self.lookback = lookback
        self.atr_multiple = atr_multiple
        self._prices: dict[str, list[float]] = {}
        self._position_side: dict[str, str] = {}  # symbol → "LONG"/"SHORT"/""

    def on_quote(self, quote: dict, portfolio: dict) -> Signal | None:
        symbol = quote.get("symbol", "")
        price = quote.get("data", {}).get("price", 0)
        if not symbol or price <= 0:
            return None

        if symbol not in self._prices:
            self._prices[symbol] = []
            self._position_side[symbol] = ""

        prices = self._prices[symbol]
        prices.append(price)
        if len(prices) > self.lookback + 1:
            prices.pop(0)

        if len(prices) < self.lookback + 1:
            return None

        recent = prices[:-1]
        high = max(recent)
        low = min(recent)
        mid = (high + low) / 2
        atr = (high - low) * self.atr_multiple / 2

        current_side = self._position_side.get(symbol, "")
        cash = portfolio.get("cash", 0)
        positions = portfolio.get("positions", {})
        held_qty = positions.get(symbol, {}).get("quantity", 0)

        # BUY: 价格突破 mid + atr，且空仓
        if current_side != "LONG" and price > mid + atr and cash > 10000:
            qty = max(100, int(cash * 0.2 / price / 100) * 100)
            self._position_side[symbol] = "LONG"
            return Signal(self.strategy_id, symbol, "BUY", qty, 0.65,
                          f"breakout_high_{high:.2f}")

        # SELL: 价格跌破 mid - atr，且持仓
        if current_side == "LONG" and price < mid - atr and held_qty > 0:
            self._position_side[symbol] = ""
            return Signal(self.strategy_id, symbol, "SELL", held_qty, 0.65,
                          f"breakout_low_{low:.2f}")

        return None
