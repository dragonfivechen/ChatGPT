#!/usr/bin/env python3
"""
Futures-Sim v0.1 — strategies/signal.py（信号合约 & 事件）

冻结约束:
  - Signal 只包含: strategy_id, symbol, action, qty
  - action 限: BUY / SELL / CLOSE
  - 不包含: 保证金、止损、强制平仓等执行层信息
  - 策略不知道账户/成交/保证金
"""

from __future__ import annotations
from typing import Optional
import json
import os
import time
from datetime import datetime, timezone, timedelta


VALID_ACTIONS = frozenset({"BUY", "SELL", "CLOSE"})


class Signal:
    """策略信号—建议，非指令"""

    def __init__(
        self,
        strategy_id: str,
        symbol: str,
        action: str,
        qty: int = 0,
        confidence: float = 0.5,
        note: str = "",
    ):
        if action not in VALID_ACTIONS:
            raise ValueError(f"无效动作 {action}，允许: {VALID_ACTIONS}")
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.action = action.upper()
        self.qty = qty
        self.confidence = confidence
        self.note = note

    def to_dict(self) -> dict:
        return {
            "event_type": "FUTURES_SIGNAL",
            "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "action": self.action,
            "qty": self.qty,
            "confidence": self.confidence,
            "note": self.note,
        }

    def __repr__(self):
        return f"Signal({self.strategy_id}: {self.action} {self.qty}×{self.symbol}, conf={self.confidence})"


def signal_to_order(signal: Signal, order_type: str = "MARKET") -> dict:
    """将策略 Signal 转换为 FUTURES_ORDER 事件

    BUY  → BUY
    SELL → SELL
    CLOSE → 根据当前账户状态决定方向

    这个转换由 run_strategy 调用，run_strategy 持有账户引用。
    """
    import uuid
    from datetime import datetime, timezone, timedelta

    order_id = f"F{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"

    return {
        "event_type": "FUTURES_ORDER",
        "order_id": order_id,
        "ts": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "symbol": signal.symbol,
        "side": signal.action,
        "action": "SIGNAL",
        "order_type": order_type,
        "quantity": signal.qty if signal.qty > 0 else 1,
        "strategy_id": signal.strategy_id,
    }


def append_signal(signal_or_evt, events_path: str = "") -> None:
    """追加信号事件到 futures_events.jsonl"""
    if not events_path:
        events_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "futures_events.jsonl",
        )
    if isinstance(signal_or_evt, Signal):
        evt = signal_or_evt.to_dict()
    else:
        evt = signal_or_evt
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
