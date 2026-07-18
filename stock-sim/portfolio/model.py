"""portfolio/model.py — Portfolio 组合快照模型

Portfolio 是 Account 的分析视图，不修改账户状态。
"""


class Holding:
    """单只股票的持仓估值快照"""

    def __init__(
        self,
        symbol: str,
        quantity: int,
        avg_cost: float,
        current_price: float,
        market_value: float,
        weight: float,
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.avg_cost = avg_cost
        self.current_price = current_price
        self.market_value = market_value
        self.weight = weight  # 占总资产比例

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_cost": round(self.avg_cost, 4),
            "current_price": round(self.current_price, 2),
            "market_value": round(self.market_value, 2),
            "weight": round(self.weight, 4),
        }

    def __repr__(self):
        return (
            f"Holding({self.symbol}: {self.quantity}股 @ "
            f"{self.current_price:.2f} = {self.market_value:.2f}, "
            f"{self.weight*100:.1f}%)"
        )


class Portfolio:
    """组合快照——某一时刻的完整视图"""

    def __init__(
        self,
        account_id: str,
        cash: float,
        market_value: float,
        equity: float,
        holdings: list[Holding],
        total_return: float,
        peak_equity: float,
        drawdown: float,
    ):
        self.account_id = account_id
        self.cash = cash
        self.market_value = market_value
        self.equity = equity
        self.holdings = holdings
        self.total_return = total_return
        self.peak_equity = peak_equity
        self.drawdown = drawdown

    def to_dict(self) -> dict:
        return {
            "account_id": self.account_id,
            "cash": round(self.cash, 2),
            "market_value": round(self.market_value, 2),
            "equity": round(self.equity, 2),
            "holdings": [h.to_dict() for h in self.holdings],
            "total_return": round(self.total_return, 4),
            "peak_equity": round(self.peak_equity, 2),
            "drawdown": round(self.drawdown, 4),
        }

    def __repr__(self):
        return (
            f"Portfolio({self.account_id}: "
            f"权益={self.equity:.2f}, "
            f"市值={self.market_value:.2f}, "
            f"收益率={self.total_return*100:.2f}%, "
            f"回撤={self.drawdown*100:.2f}%)"
        )
