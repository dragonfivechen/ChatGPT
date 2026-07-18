"""portfolio/calculator.py — 组合计算逻辑

输入: Account + MARKET_QUOTE(s)
输出: Portfolio Snapshot 所需的指标
"""

import sys
import os

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from account.model import Account


def calc_market_value(account: Account, quotes: dict[str, float]) -> float:
    """计算持仓总市值。quotes: {symbol: current_price}"""
    total = 0.0
    for sym, pos in account.positions.items():
        if pos.quantity > 0:
            price = quotes.get(sym, pos.avg_cost)
            total += price * pos.quantity
    return total


def calc_holdings(
    account: Account, quotes: dict[str, float], equity: float
) -> list[dict]:
    """生成每只持仓的估值快照"""
    result = []
    for sym, pos in sorted(account.positions.items()):
        if pos.quantity <= 0:
            continue
        price = quotes.get(sym, pos.avg_cost)
        mv = price * pos.quantity
        weight = mv / equity if equity > 0 else 0
        result.append({
            "symbol": sym,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "current_price": price,
            "market_value": mv,
            "weight": weight,
        })
    return result


def calc_return(equity: float, initial_cash: float) -> float:
    """总收益率"""
    return (equity - initial_cash) / initial_cash if initial_cash > 0 else 0.0
