"""account/validator.py — 账户边界检查

验证成交事件是否可以安全入账。
"""

from .model import Account


def validate_trade_for_account(account: Account, trade: dict) -> tuple[bool, str]:
    """成交入账前检查"""
    t = trade.get("trade", trade)
    symbol = t.get("symbol", "")
    side = t.get("side", "BUY").upper()
    price = float(t.get("price", 0))
    quantity = int(t.get("quantity", 0))

    if not symbol:
        return False, "missing symbol"
    if side not in ("BUY", "SELL"):
        return False, f"invalid side: {side}"
    if price <= 0:
        return False, f"invalid price: {price}"
    if quantity <= 0:
        return False, f"invalid quantity: {quantity}"

    trade_amount = price * quantity

    if side == "BUY":
        total_cost = trade_amount + max(trade_amount * 0.0003, 5.0)
        if account.cash < total_cost:
            return False, (
                f"insufficient cash: need {total_cost:.2f}, "
                f"have {account.cash:.2f}"
            )

    elif side == "SELL":
        pos = account.positions.get(symbol)
        held = pos.quantity if pos else 0
        if quantity > held:
            return False, (
                f"insufficient holdings: need {quantity}, have {held}"
            )

    return True, ""
