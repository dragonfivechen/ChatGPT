#!/usr/bin/env python3
"""
Futures-Sim v0.1 — strategies/breakout.py（突破策略）

逻辑:
  - 计算过去 N 期的最高价/最低价（通道上下轨）
  - 价格突破上轨 → BUY（做多）
  - 价格突破下轨 → SELL（做空）
  - CLOSE: 反向信号时平仓

冻结约束:
  - 只输出 Signal
  - 通道周期固定，不做自适应
"""

from __future__ import annotations
from collections import deque
from typing import Optional

from .signal import Signal


class BreakoutStrategy:
    """突破策略 (20期唐奇安通道)"""

    def __init__(self, strategy_id: str = "Breakout",
                 lookback: int = 20,
                 qty: int = 1):
        self.strategy_id = strategy_id
        self.lookback = lookback
        self.qty = qty

        # 每个品种维护价格窗口
        self._prices: dict[str, deque] = {}

    def on_quote(self, quote: dict, position_info: dict = None) -> Optional[Signal]:
        """收到行情 → 返回策略信号或 None

        注意: 模拟行情数据不含真实 OHLC 条，使用 price 构建滚动窗口。
        """
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return None

        signal = None

        # 初始化窗口
        if symbol not in self._prices:
            self._prices[symbol] = deque(maxlen=self.lookback)

        # 检查突破前需要完整的窗口 — 先检查再 append
        if len(self._prices[symbol]) >= self.lookback:
            window = list(self._prices[symbol])
            channel_high = max(window)
            channel_low = min(window)

            # 向上突破: 价格超过过去 N 期的最高价
            if price > channel_high:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    action="BUY",
                    qty=self.qty,
                    confidence=0.65,
                    note=f"向上突破 ¥{channel_high:.2f} (当前¥{price:.2f})",
                )
            # 向下突破: 价格低于过去 N 期的最低价
            elif price < channel_low:
                signal = Signal(
                    strategy_id=self.strategy_id,
                    symbol=symbol,
                    action="SELL",
                    qty=self.qty,
                    confidence=0.65,
                    note=f"向下突破 ¥{channel_low:.2f} (当前¥{price:.2f})",
                )

        # 加入当前价格到窗口
        self._prices[symbol].append(price)
        if len(self._prices[symbol]) < self.lookback:
            return None

        return signal  # None or Signal
