"""strategy/breakout_v2.py — Donchian Breakout 验证增强版

相对 BREAKOUT_V1 的改进:
  1. Donchian 通道突破 (window_high) 代替 ATR 带
  2. MA3 趋势过滤，降低横盘假突破
  3. 成交量确认 (volume > avg_volume)
  4. 固定止损 (entry_price * 0.95)
  5. 移动止盈 (highest * 0.95)

状态:
  _prices[symbol]      → price window (FIFO)
  _volumes[symbol]     → volume window
  _entry_price[symbol] → 买入价，用于止损
  _highest[symbol]     → 持仓期间最高价，用于回撤止盈
"""

from .base import Strategy, Signal


class BreakoutV2(Strategy):
    """Donchian 通道突破策略 v2"""

    def __init__(self, strategy_id: str = "BREAKOUT_V2",
                 lookback: int = 5,
                 stop_loss_pct: float = 0.95,
                 trailing_stop_pct: float = 0.95):
        super().__init__(strategy_id)
        self.lookback = lookback
        self.stop_loss_pct = stop_loss_pct      # 止损线 (买入价 × 0.95)
        self.trailing_stop_pct = trailing_stop_pct  # 移动止盈 (最高价 × 0.95)

        self._prices: dict[str, list[float]] = {}
        self._volumes: dict[str, list[float]] = {}
        self._entry_price: dict[str, float] = {}
        self._highest: dict[str, float] = {}

    def on_quote(self, quote: dict, portfolio: dict) -> Signal | None:
        symbol = quote.get("symbol", "")
        price = quote.get("data", {}).get("price", 0)
        volume = quote.get("data", {}).get("volume", 0)

        if not symbol or price <= 0:
            return None

        # 初始化状态
        if symbol not in self._prices:
            self._prices[symbol] = []
            self._volumes[symbol] = []
            self._entry_price.setdefault(symbol, 0)
            self._highest.setdefault(symbol, 0)

        # 更新价格窗口
        prices = self._prices[symbol]
        prices.append(price)
        if len(prices) > self.lookback + 1:
            prices.pop(0)

        # 更新成交量窗口
        volumes = self._volumes[symbol]
        if volume > 0:
            volumes.append(volume)
            if len(volumes) > self.lookback + 1:
                volumes.pop(0)

        # 窗口不足，无法计算
        if len(prices) < self.lookback + 1:
            return None

        # 计算窗口指标
        recent = prices[:-1]  # 排除当前价
        window_high = max(recent)
        window_low = min(recent)
        ma3 = sum(prices[-3:]) / min(len(prices), 3)
        avg_volume = sum(volumes) / max(len(volumes), 1) if volumes else 0

        # 读取当前状态
        entry = self._entry_price.get(symbol, 0)
        highest = self._highest.get(symbol, 0)
        cash = portfolio.get("cash", 0)
        positions = portfolio.get("positions", {})
        held_qty = positions.get(symbol, {}).get("quantity", 0) if isinstance(positions, dict) else 0

        # 更新持仓最高价
        if held_qty > 0 and price > highest:
            self._highest[symbol] = price
            highest = price

        # === 持有检查: 止损/止盈 ===
        if held_qty > 0 and entry > 0:
            # 固定止损
            if price < entry * self.stop_loss_pct:
                self._entry_price[symbol] = 0
                self._highest[symbol] = 0
                return Signal(self.strategy_id, symbol, "SELL", held_qty, 0.85,
                              f"stop_loss entry={entry:.2f}@{price:.2f}")

            # 移动止盈
            if highest > 0 and price < highest * self.trailing_stop_pct:
                self._entry_price[symbol] = 0
                self._highest[symbol] = 0
                return Signal(self.strategy_id, symbol, "SELL", held_qty, 0.75,
                              f"trailing_stop high={highest:.2f}@{price:.2f}")

        # === 买入条件: 突破 + 趋势 + 放量 ===
        if held_qty == 0 and cash > 10000:
            buy_signal = False
            reasons = []

            # 1. Donchian 突破
            if price > window_high:
                buy_signal = True
                reasons.append(f"breakout_high_{window_high:.2f}")

            # 2. MA3 趋势确认
            if price > ma3:
                reasons.append(f"above_ma3_{ma3:.2f}")
            else:
                buy_signal = False

            # 3. 成交量确认
            if volume > 0 and avg_volume > 0 and volume < avg_volume * 0.8:
                buy_signal = False

            if buy_signal:
                qty = max(100, int(cash * 0.2 / price / 100) * 100)
                self._entry_price[symbol] = price
                self._highest[symbol] = price
                return Signal(self.strategy_id, symbol, "BUY", qty, 0.70,
                              ";".join(reasons))

        return None
