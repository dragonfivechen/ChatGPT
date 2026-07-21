#!/usr/bin/env python3
"""
Futures-Sim v0.1 — strategies/ma.py（移动均线策略）

逻辑:
  - 计算 MA5 (快线) 和 MA20 (慢线)
  - 金叉: MA5 上穿 MA20 → BUY
  - 死叉: MA5 下穿 MA20 → SELL
  - CLOSE: 反向信号发出时先平仓

冻结约束:
  - 只输出 Signal（不接触账户/成交）
  - 不包含止损/止盈/仓位管理
"""

from __future__ import annotations
from collections import deque
from typing import Optional

from .signal import Signal


class MAStrategy:
    """移动均线策略 (MA5/MA20)"""

    def __init__(self, strategy_id: str = "MA",
                 fast_period: int = 5,
                 slow_period: int = 20,
                 qty: int = 1):
        self.strategy_id = strategy_id
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.qty = qty

        # 每个品种维护价格窗口
        self._windows: dict[str, deque] = {}
        self._prev_fast: dict[str, Optional[float]] = {}
        self._prev_slow: dict[str, Optional[float]] = {}

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[Signal]:
        """收到行情 → 返回策略信号或 None"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        # 维护窗口
        if symbol not in self._windows:
            self._windows[symbol] = deque(maxlen=self.slow_period + 1)
        self._windows[symbol].append(price)

        window = list(self._windows[symbol])
        if len(window) < self.slow_period:
            return None  # 数据不够

        # 计算 MA
        fast_ma = sum(window[-self.fast_period:]) / self.fast_period
        slow_ma = sum(window) / len(window)

        prev_fast = self._prev_fast.get(symbol)
        prev_slow = self._prev_slow.get(symbol)

        signal = None

        if prev_fast is not None and prev_slow is not None:
            # 金叉: 快线上穿慢线
            if prev_fast <= prev_slow and fast_ma > slow_ma:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    action="BUY",
                    qty=self.qty,
                    confidence=0.7,
                    note=f"MA金叉 MA{self.fast_period}={fast_ma:.1f} MA{self.slow_period}={slow_ma:.1f}",
                )
            # 死叉: 快线下穿慢线
            elif prev_fast >= prev_slow and fast_ma < slow_ma:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    action="SELL",
                    qty=self.qty,
                    confidence=0.7,
                    note=f"MA死叉 MA{self.fast_period}={fast_ma:.1f} MA{self.slow_period}={slow_ma:.1f}",
                )

        self._prev_fast[symbol] = fast_ma
        self._prev_slow[symbol] = slow_ma

        return signal
