"""strategy/base.py — Strategy 抽象基类

策略职责: 接收行情+组合状态 → 输出 Signal。
策略不接触 Account / Execution / events.jsonl。
"""

from abc import ABC, abstractmethod
from typing import Optional


class Signal:
    """策略信号——建议，非指令"""

    def __init__(
        self,
        strategy_id: str,
        symbol: str,
        action: str,       # BUY / SELL / HOLD
        quantity: int = 0,
        confidence: float = 0.5,
        note: str = "",
    ):
        self.strategy_id = strategy_id
        self.symbol = symbol
        self.action = action.upper()
        self.quantity = quantity
        self.confidence = confidence
        self.note = note

    def to_dict(self) -> dict:
        return {
            "event_type": "STRATEGY_SIGNAL",
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "note": self.note,
        }

    def __repr__(self):
        return (
            f"Signal({self.strategy_id}: {self.action} "
            f"{self.quantity}×{self.symbol}, "
            f"conf={self.confidence})"
        )


class Strategy(ABC):
    """策略基类。所有策略必须实现 on_quote。"""

    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id
        self._active = False

    @abstractmethod
    def on_quote(self, quote: dict, portfolio: dict) -> Optional[Signal]:
        """收到行情 + 当前组合状态 → 返回信号或 None"""
        ...

    def start(self):
        self._active = True

    def stop(self):
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active
