"""order/model.py — Order 数据模型

不可变订单事实。创建后字段不修改，状态通过状态机转移。
"""

import uuid
import time

from . import status as _status


class Order:
    """模拟交易订单——不可变值对象"""

    def __init__(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: int,
        limit_price: float = 0.0,
        order_id: str = "",
    ):
        self.order_id = order_id or str(uuid.uuid4())[:12]
        self.symbol = symbol
        self.side = side.upper()       # BUY / SELL
        self.order_type = order_type.upper()  # MARKET / LIMIT
        self.quantity = quantity
        self.limit_price = limit_price
        self.status = _status.CREATED
        self.created_at = time.strftime(
            "%Y-%m-%dT%H:%M:%S+08:00", time.localtime()
        )

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "limit_price": self.limit_price,
            "status": self.status,
            "created_at": self.created_at,
        }

    def __repr__(self):
        return (
            f"Order({self.order_id}: {self.side} {self.quantity}×"
            f"{self.symbol} @ {self.order_type})"
        )
