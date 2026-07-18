"""account/ledger.py — 成交入账逻辑

唯一修改 Account cash/position 的入口。

输入: Account + TRADE_EXECUTED event
输出: 修改后的 Account（直接修改传入对象）
"""

from .model import Account
from .fee import calc_buy_fees, calc_sell_fees


def apply_trade(account: Account, trade: dict) -> dict:
    """处理一笔成交，返回 ACCOUNT_UPDATE 事件数据"""

    t = trade.get("trade", trade)
    symbol = t.get("symbol", "")
    side = t.get("side", "BUY").upper()
    price = float(t.get("price", 0))
    quantity = int(t.get("quantity", 0))
    trade_amount = price * quantity

    position = account.get_position(symbol)

    if side == "BUY":
        fee = calc_buy_fees(trade_amount)
        total_cost = trade_amount + fee

        if account.cash < total_cost:
            raise ValueError(
                f"Insufficient cash: need {total_cost:.2f}, have {account.cash:.2f}"
            )

        account.cash -= total_cost
        account._total_fees += fee

        # 更新持仓
        prev_cost = position.avg_cost * position.quantity
        new_cost = prev_cost + trade_amount
        position.quantity += quantity
        position.today_buy += quantity
        position.avg_cost = new_cost / position.quantity if position.quantity > 0 else 0

    elif side == "SELL":
        fee = calc_sell_fees(trade_amount)
        net_amount = trade_amount - fee

        if quantity > position.quantity:
            raise ValueError(
                f"Insufficient holdings: need {quantity}, have {position.quantity}"
            )

        account.cash += net_amount
        account._total_fees += fee

        # 已实现盈亏（卖出部分）
        sell_cost = position.avg_cost * quantity
        realized = (trade_amount - fee) - sell_cost
        account.realized_pnl += realized

        # 更新持仓
        position.quantity -= quantity
        position.today_buy = max(0, position.today_buy - quantity)
        position.available_quantity = max(0, position.available_quantity - quantity)

    else:
        raise ValueError(f"Unknown side: {side}")

    # 更新权益
    account.equity = account.cash + _calc_market_value(account, price, symbol)

    return _build_account_update(account, trade)


def _calc_market_value(account: Account, current_price: float, quote_symbol: str) -> float:
    """计算持仓市值，仅用最新报价更新目标股票"""
    total = 0.0
    for sym, pos in account.positions.items():
        qty = pos.quantity
        if qty > 0:
            p = current_price if sym == quote_symbol else pos.avg_cost
            total += qty * p
    return total


def _build_account_update(account: Account, trade_event: dict) -> dict:
    """构造 ACCOUNT_UPDATE 事件"""
    import time
    ts = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())
    return {
        "event_type": "ACCOUNT_UPDATE",
        "timestamp": ts,
        "related_trade_id": (
            trade_event.get("trade", trade_event).get("trade_id", "")
        ),
        "account": account.to_dict(),
    }
