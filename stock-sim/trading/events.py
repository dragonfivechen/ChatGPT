"""trading/events.py — 交易事件类型和构造器

符合 Order Contract v0.1 + Market Data Contract v0.1
"""

import uuid
import time

ORDER_CREATED = "ORDER_CREATED"
ORDER_SUBMITTED = "ORDER_SUBMITTED"
ORDER_REJECTED = "ORDER_REJECTED"
ORDER_CANCELLED = "ORDER_CANCELLED"
TRADE_EXECUTED = "TRADE_EXECUTED"


def _ts():
    return time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())


def order_created_event(order: dict) -> dict:
    return {
        "event_type": ORDER_CREATED,
        "timestamp": _ts(),
        "order": dict(order),
    }


def order_submitted_event(order: dict) -> dict:
    return {
        "event_type": ORDER_SUBMITTED,
        "timestamp": _ts(),
        "order_id": order["order_id"],
        "symbol": order["symbol"],
        "side": order["side"],
        "quantity": order["quantity"],
    }


def order_rejected_event(order: dict, reason: str) -> dict:
    return {
        "event_type": ORDER_REJECTED,
        "timestamp": _ts(),
        "order_id": order.get("order_id", ""),
        "symbol": order.get("symbol", ""),
        "reason": reason,
        "order": dict(order),
    }


def order_cancelled_event(order_id: str) -> dict:
    return {
        "event_type": ORDER_CANCELLED,
        "timestamp": _ts(),
        "order_id": order_id,
    }


def trade_executed_event(order: dict, price: float, quantity: int) -> dict:
    trade_id = str(uuid.uuid4())[:8]
    return {
        "event_type": TRADE_EXECUTED,
        "timestamp": _ts(),
        "trade": {
            "trade_id": trade_id,
            "order_id": order["order_id"],
            "symbol": order["symbol"],
            "side": order["side"],
            "price": price,
            "quantity": quantity,
            "timestamp": _ts(),
        },
    }
