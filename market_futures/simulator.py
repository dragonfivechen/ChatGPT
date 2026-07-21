#!/usr/bin/env python3
"""
Futures-Sim v0.1 — simulator.py（撮合引擎）

职责:
  接收 FUTURES_QUOTE + 手动订单 → 输出 FUTURES_FILL

冻结约束:
  - 成交价格只能来自 quote（禁止 fill_price = random()）
  - 市价单: 以 quote.price 成交
  - 限价单: 价格条件满足才成交
  - 不持有账户状态（由 account.py 消费 fill 事件）
"""

from __future__ import annotations
import uuid
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional


# ─── 事件写入 ───
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVENTS_PATH = os.path.join(BASE_DIR, "futures_events.jsonl")

_lock = None  # lazy import threading lock


def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


def append_event(event: dict):
    with _get_lock():
        with open(EVENTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _now_ts() -> str:
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def make_order_event(symbol: str, side: str, qty: int,
                     order_type: str = "MARKET",
                     limit_price: float = 0,
                     action: str = "") -> dict:
    """构造 FUTURES_ORDER 事件"""
    order_id = f"F{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
    evt = {
        "event_type": "FUTURES_ORDER",
        "order_id": order_id,
        "ts": _now_ts(),
        "symbol": symbol,
        "side": side,
        "action": action,
        "order_type": order_type,
        "quantity": qty,
    }
    if limit_price > 0:
        evt["limit_price"] = limit_price
    return evt


def make_fill_event(order: dict, price: float, qty: int, fee: float) -> dict:
    """构造 FUTURES_FILL 事件"""
    return {
        "event_type": "FUTURES_FILL",
        "order_id": order["order_id"],
        "fill_id": f"FILL_{uuid.uuid4().hex[:8].upper()}",
        "ts": _now_ts(),
        "symbol": order["symbol"],
        "side": order["side"],
        "action": order.get("action", ""),
        "fill_price": round(price, 2),
        "fill_qty": qty,
        "fee": round(fee, 4),
    }


class Simulator:
    """成交模拟器

    用法:
      sim = Simulator()
      sim.add_order(order_event)       # 添加订单
      fills = sim.on_quote(quote)      # 处理行情，返回成交列表
    """

    def __init__(self, fee_calculator=None):
        """
        fee_calculator: (symbol, side, qty, price) → float
                        默认为固定费率模式
        """
        self._orders: dict[str, dict] = {}  # order_id → order dict
        self._fill_events: list[dict] = []
        self._fee_calc = fee_calculator or self._default_fee

    @staticmethod
    def _default_fee(symbol: str, side: str, qty: int, price: float) -> float:
        """默认手续费计算: 万分之0.5 按成交额"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "futures_contracts.json")
        with open(path, "r", encoding="utf-8") as f:
            contracts = json.load(f)["contracts"]
        cfg = contracts.get(symbol, {})
        mult = cfg.get("multiplier", 10)
        fee_rate = cfg.get("fee_rate", 0.00005)
        return price * mult * qty * fee_rate

    def add_order(self, order: dict):
        """添加已构造的订单事件"""
        oid = order["order_id"]
        if oid in self._orders:
            return
        entry = dict(order)
        entry["status"] = "SUBMITTED"
        entry["filled_qty"] = 0
        self._orders[oid] = entry

    def remove_order(self, order_id: str):
        self._orders.pop(order_id, None)

    @property
    def active_orders(self) -> list[dict]:
        return [o for o in self._orders.values() if o["status"] == "SUBMITTED"]

    @property
    def active_count(self) -> int:
        return len(self.active_orders)

    def on_quote(self, quote: dict) -> list[dict]:
        """处理一条 FUTURES_QUOTE → 检查可成交订单 → 返回 FUTURES_FILL 列表"""
        symbol = quote.get("symbol", "")
        price = quote.get("price", 0)

        if not symbol or price <= 0:
            return []

        active = [
            o for o in self._orders.values()
            if o["symbol"] == symbol
            and o["status"] == "SUBMITTED"
        ]

        fills = []
        for order in active:
            fill = self._check(order, price)
            if fill:
                fills.append(fill)
                order["status"] = "FILLED"
                self._orders.pop(order["order_id"], None)

        return fills

    def _check(self, order: dict, market_price: float) -> Optional[dict]:
        """检查单个订单是否可成交"""
        otype = order["order_type"]
        qty = order["quantity"]

        if otype == "MARKET":
            return self._execute(order, market_price, qty)

        if otype == "LIMIT":
            side = order["side"]
            limit = order.get("limit_price", 0)
            if side == "BUY" and market_price <= limit:
                return self._execute(order, market_price, qty)
            if side == "SELL" and market_price >= limit:
                return self._execute(order, market_price, qty)

        return None

    def _execute(self, order: dict, price: float, qty: int) -> dict:
        """执行订单，生成 fill 事件"""
        fee = self._fee_calc(order["symbol"], order["side"], qty, price)
        fill = make_fill_event(order, price, qty, fee)

        # 同时写入事件文件
        append_event(order)   # 先写 order
        append_event(fill)    # 再写 fill

        return fill

    def get_and_clear_fills(self) -> list[dict]:
        """获取并清空自上次调用以来的 fill 事件（供 account 消费）"""
        fills = list(self._fill_events)
        self._fill_events.clear()
        return fills
