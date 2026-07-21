#!/usr/bin/env python3
"""
Futures-Sim v0.1 — position.py（持仓模型）

方向: LONG / SHORT（仅支持单一方向净持仓，不支持双向同时持仓）
仓类型: 纯净持仓模型，不做网格/策略/智能仓。

冻结约束:
- 每个品种同时只有一个方向
- 反向开仓 = 先平再开
- 不支持锁仓（同时持有多空）
"""

from __future__ import annotations
from typing import Optional


# ─── 方向常量 ───
LONG = "LONG"
SHORT = "SHORT"
DIRECTIONS = frozenset({LONG, SHORT})

# ─── 动作常量 ───
OPEN = "OPEN"
CLOSE = "CLOSE"


class Position:
    """单一品种持仓

    期货采用净持仓模型:
      direction=None  → 无持仓
      direction=LONG  → 净多头 qty 手
      direction=SHORT → 净空头 qty 手
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.direction: Optional[str] = None  # LONG / SHORT / None
        self.qty: int = 0                       # 手数
        self.avg_price: float = 0.0             # 开仓均价
        self.margin_used: float = 0.0           # 当前保证金占用

    def is_empty(self) -> bool:
        return self.qty == 0 or self.direction is None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "qty": self.qty,
            "avg_price": round(self.avg_price, 2),
            "margin_used": round(self.margin_used, 2),
        }

    def __repr__(self) -> str:
        if self.is_empty():
            return f"Position({self.symbol}: ∅)"
        dir_cn = "多" if self.direction == LONG else "空"
        return (f"Position({self.symbol}: {dir_cn} {self.qty}手 "
                f"@ ¥{self.avg_price:.2f}, 保证金=¥{self.margin_used:.2f})")


class Positions:
    """持仓集合 — 管理所有品种的净持仓"""

    def __init__(self):
        self._positions: dict[str, Position] = {}

    def get(self, symbol: str) -> Position:
        if symbol not in self._positions:
            self._positions[symbol] = Position(symbol)
        return self._positions[symbol]

    def to_dict(self) -> dict:
        return {
            sym: p.to_dict()
            for sym, p in self._positions.items()
            if not p.is_empty()
        }

    def list_active(self) -> list[Position]:
        return [p for p in self._positions.values() if not p.is_empty()]

    @property
    def active_count(self) -> int:
        return len(self.list_active())

    def __repr__(self) -> str:
        active = self.list_active()
        if not active:
            return "Positions(∅)"
        return f"Positions({', '.join(str(p) for p in active)})"
