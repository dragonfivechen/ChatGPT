"""account/pnl.py — 盈亏计算

浮动盈亏: (current_price - avg_cost) × quantity
已实现盈亏: 由 ledger.py 在卖出时计算
"""

from .model import Account


def calc_unrealized_pnl(account: Account, quote: dict) -> dict[str, float]:
    """计算每只持仓股票的浮动盈亏。
    输入: Account + MARKET_QUOTE event
    输出: {symbol: unrealized_pnl}
    """
    symbol = quote.get("symbol", "")
    price = quote.get("data", {}).get("price", 0)

    result = {}
    if not symbol or price <= 0:
        return result

    pos = account.positions.get(symbol)
    if pos and pos.quantity > 0:
        pnl = round((price - pos.avg_cost) * pos.quantity, 2)
        result[symbol] = pnl

    return result


def calc_total_unrealized_pnl(account: Account, quotes: dict[str, float]) -> float:
    """批量计算总浮动盈亏。
    输入: {symbol: current_price}
    输出: 总浮动盈亏
    """
    total = 0.0
    for sym, pos in account.positions.items():
        if pos.quantity > 0 and sym in quotes:
            total += (quotes[sym] - pos.avg_cost) * pos.quantity
    return round(total, 2)
