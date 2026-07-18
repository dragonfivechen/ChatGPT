"""order/validator.py — 订单提交前校验

拒绝条件（ORDER_REJECTED）：
- symbol 非法
- quantity 非 100 整数倍
- side 非 BUY/SELL
- order_type 非 MARKET/LIMIT
- LIMIT 单 limit_price <= 0
- quantity <= 0

输出: (is_valid, reason)
"""

import sys
import os

# 确保能找到 stock-sim/market
_THIS = os.path.dirname(os.path.abspath(__file__))       # trading/order/
_PROJECT = os.path.dirname(os.path.dirname(_THIS))       # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from market.symbols import is_valid_symbol


def validate_order(order_dict: dict) -> tuple[bool, str]:
    """基础校验，不依赖账户/持仓状态"""

    symbol = order_dict.get("symbol", "")
    if not is_valid_symbol(symbol):
        return False, f"invalid_symbol:{symbol}"

    side = order_dict.get("side", "").upper()
    if side not in ("BUY", "SELL"):
        return False, f"invalid_side:{side}"

    order_type = order_dict.get("order_type", "").upper()
    if order_type not in ("MARKET", "LIMIT"):
        return False, f"invalid_order_type:{order_type}"

    quantity = order_dict.get("quantity", 0)
    if not isinstance(quantity, int) or quantity <= 0:
        return False, f"invalid_quantity:{quantity}"
    if quantity % 100 != 0:
        return False, f"quantity_not_multiple_of_100:{quantity}"

    if order_type == "LIMIT":
        limit_price = order_dict.get("limit_price", 0)
        if not isinstance(limit_price, (int, float)) or limit_price <= 0:
            return False, f"invalid_limit_price:{limit_price}"

    return True, ""


def validate_buy_sufficient_funds(
    order_dict: dict, available_cash: float
) -> tuple[bool, str]:
    """买入资金检查"""

    if order_dict.get("side", "").upper() != "BUY":
        return True, ""

    price = (
        order_dict.get("limit_price", 0)
        if order_dict.get("order_type", "").upper() == "LIMIT"
        else 99999  # MARKET 用最高价估算
    )
    estimated_cost = price * order_dict.get("quantity", 0)
    if estimated_cost > available_cash:
        return (
            False,
            f"insufficient_funds:need={estimated_cost:.2f},have={available_cash:.2f}",
        )
    return True, ""


def validate_sell_sufficient_holdings(
    order_dict: dict, available_shares: int
) -> tuple[bool, str]:
    """卖出持仓检查"""

    if order_dict.get("side", "").upper() != "SELL":
        return True, ""
    qty = order_dict.get("quantity", 0)
    if qty > available_shares:
        return False, f"insufficient_holdings:have={available_shares},need={qty}"
    return True, ""
