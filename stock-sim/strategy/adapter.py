"""strategy/adapter.py — 信号 → 订单适配器

将 STRATEGY_SIGNAL 转为 ORDER_CREATED。
策略不直接创建订单。
"""

import sys
import os

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from typing import Optional
from .base import Signal
from trading.order.model import Order


def signal_to_order(signal_event: dict) -> Optional[Order]:
    """信号事件 → Order 对象。返回 None 如果信号不可下单 (HOLD)。"""
    action = signal_event.get("action", "HOLD")
    if action == "HOLD":
        return None

    symbol = signal_event.get("symbol", "")
    quantity = signal_event.get("quantity", 0)
    sid = signal_event.get("strategy_id", "unknown")

    if not symbol or quantity <= 0:
        return None

    order_type = "MARKET"  # v0.1: 信号默认市价单
    order = Order(
        symbol=symbol,
        side=action,
        order_type=order_type,
        quantity=quantity,
    )
    return order
