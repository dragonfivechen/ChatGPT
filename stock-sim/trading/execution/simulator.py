"""execution/simulator.py — 成交模拟器

输入: Order + MARKET_QUOTE
输出: TRADE_EXECUTED / 未成交（等待下一周期）

不持有账户状态。成交事件由上层（account 模块）消费。
"""

from ..order.status import SUBMITTED, FILLED


class ExecutionSimulator:
    """简单成交模拟器。每收到一条 MARKET_QUOTE，检查所有活跃 SUBMITTED 订单。

    使用方法：
        sim = ExecutionSimulator()
        sim.add_order(order_dict)           # 添加已通过校验的订单
        trades = sim.on_quote(quote_dict)   # 处理行情，返回成交列表
    """

    def __init__(self):
        # order_id → order_dict，仅保存 SUBMITTED 状态订单
        self._orders: dict[str, dict] = {}

    def add_order(self, order: dict):
        """添加已提交订单"""
        oid = order["order_id"]
        if oid in self._orders:
            return
        entry = dict(order)
        entry["status"] = SUBMITTED
        entry["filled_qty"] = 0
        self._orders[oid] = entry

    def remove_order(self, order_id: str):
        self._orders.pop(order_id, None)

    def on_quote(self, quote: dict) -> list[dict]:
        """处理一条 MARKET_QUOTE，返回本周期成交事件列表"""
        trades = []
        symbol = quote.get("symbol", "")
        price = quote.get("data", {}).get("price", 0)

        if not symbol or price <= 0:
            return trades

        # 收集该 symbol 的活跃订单
        active = [
            o for o in self._orders.values()
            if o["symbol"] == symbol and o["status"] == SUBMITTED
        ]

        for order in active:
            trade = self._check(order, price)
            if trade:
                trades.append(trade)
                # 标记订单已完成
                order["status"] = FILLED
                self._orders.pop(order["order_id"], None)

        return trades

    def _check(self, order: dict, market_price: float) -> dict | None:
        """单个订单成交检查"""
        side = order["side"]
        otype = order["order_type"]
        qty = order["quantity"]

        if otype == "MARKET":
            return self._make_trade(order, market_price, qty)

        if otype == "LIMIT":
            limit = order.get("limit_price", 0)
            if side == "BUY" and market_price <= limit:
                return self._make_trade(order, market_price, qty)
            if side == "SELL" and market_price >= limit:
                return self._make_trade(order, market_price, qty)

        return None

    def _make_trade(self, order: dict, price: float, qty: int) -> dict:
        from ..events import trade_executed_event
        return trade_executed_event(order, price, qty)

    def active_count(self) -> int:
        return len(self._orders)

    def active_orders(self) -> list[dict]:
        return list(self._orders.values())
