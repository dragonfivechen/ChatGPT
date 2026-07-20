"""account/model.py — Account 和 Position 数据模型

账户由 Cash + Positions + PnL 组成。
不直接修改资金，通过 ledger.py 处理成交入账。
"""

import uuid
import copy

DEFAULT_INITIAL_CASH = 10_000_000.0


class Position:
    """单只股票持仓"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.quantity = 0          # 总持仓
        self.today_buy = 0         # 今日买入（T+1 不可卖）
        self.available_quantity = 0  # 可卖数量
        self.avg_cost = 0.0        # 持仓平均成本

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "today_buy": self.today_buy,
            "available_quantity": self.available_quantity,
            "avg_cost": round(self.avg_cost, 4),
        }

    def __repr__(self):
        return (
            f"Position({self.symbol}: {self.quantity}股 "
            f"@ {self.avg_cost:.2f}, 可卖={self.available_quantity})"
        )


class Account:
    """模拟交易账户"""

    def __init__(self, account_id: str = "", initial_cash: float = DEFAULT_INITIAL_CASH):
        self.account_id = account_id or f"SIM{uuid.uuid4().hex[:6].upper()}"
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}  # symbol → Position
        self.realized_pnl = 0.0
        self.equity = initial_cash
        self._total_fees = 0.0

    def get_position(self, symbol: str) -> Position:
        """获取或创建持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        return self.positions[symbol]

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "initial_cash": self.initial_cash,
            "cash": round(self.cash, 2),
            "positions": {
                sym: p.to_dict()
                for sym, p in sorted(self.positions.items())
                if p.quantity > 0
            },
            "equity": round(self.equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "total_fees": round(self._total_fees, 2),
        }

    def summary(self) -> str:
        d = self.to_dict()
        pos_str = "; ".join(
            f"{sym}: {p['quantity']}股 @ {p['avg_cost']:.2f}"
            for sym, p in d["positions"].items()
        )
        return (
            f"Account({d['account_id']} | "
            f"现金={d['cash']:.2f} | "
            f"权益={d['equity']:.2f} | "
            f"盈亏={d['realized_pnl']:.2f} | "
            f"{pos_str})"
        )

    def __repr__(self):
        return self.summary()
