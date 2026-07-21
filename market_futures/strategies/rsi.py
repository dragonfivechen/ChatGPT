#!/usr/bin/env python3
"""
Futures-Sim v0.1 — strategies/rsi.py（RSI策略）

逻辑:
  - 计算 14 期 RSI
  - RSI < 30（超卖）→ BUY（做多信号）
  - RSI > 70（超买）→ SELL（做空信号）
  - RSI 回到 40-60 区间 → CLOSE（平仓）

冻结约束:
  - 只输出 Signal
  - RSI 使用收盘价（quote.price）
  - 不做自适应周期/动态阈值
"""

from __future__ import annotations
from collections import deque
from typing import Optional

from .signal import Signal


class RSIStrategy:
    """RSI 策略 (14期)"""

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

        # 每个品种维护价格变化
        self._changes: dict[str, deque] = {}
        self._prev_price: dict[str, float] = {}
        self._prev_rsi: dict[str, float] = {}
        self._in_position: dict[str, str] = {}  # symbol → "LONG"/"SHORT"

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[Signal]:
        """收到行情 → 返回策略信号或 None"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        # 更新前价格
        if symbol not in self._prev_price:
            self._prev_price[symbol] = price
            return None

        # 计算价格变化
        change = price - self._prev_price[symbol]
        self._prev_price[symbol] = price

        if symbol not in self._changes:
            self._changes[symbol] = deque(maxlen=self.period)

        self._changes[symbol].append(change)

        if len(self._changes[symbol]) < self.period:
            return None

        # 计算 RSI
        gains = [c for c in self._changes[symbol] if c > 0]
        losses = [-c for c in self._changes[symbol] if c < 0]

        avg_gain = sum(gains) / self.period if gains else 0
        avg_loss = sum(losses) / self.period if losses else 0

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        prev_rsi = self._prev_rsi.get(symbol, 50.0)
        self._prev_rsi[symbol] = rsi

        current_pos = position_info or self._in_position.get(symbol)

        signal = None

        # RSI 从超卖区回升 → 做多
        if rsi > self.oversold and prev_rsi <= self.oversold:
            signal = Signal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                action="BUY",
                qty=self.qty,
                confidence=0.6,
                note=f"RSI突破超卖 {prev_rsi:.1f} → {rsi:.1f}",
            )
        # RSI 从超买区下跌 → 做空
        elif rsi < self.overbought and prev_rsi >= self.overbought:
            signal = Signal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                action="SELL",
                qty=self.qty,
                confidence=0.6,
                note=f"RSI脱离超买 {prev_rsi:.1f} → {rsi:.1f}",
            )
        # RSI 回到中间区 → 平仓
        elif (self.close_low <= rsi <= self.close_high
              and current_pos is not None
              and current_pos != "∅"):
            signal = Signal(
                strategy_id=self.strategy_id,
                symbol=symbol,
                action="CLOSE",
                qty=self.qty,
                confidence=0.5,
                note=f"RSI回到中性区 {rsi:.1f}",
            )

        return signal

    @property
    def in_position(self) -> dict:
        return dict(self._in_position)
