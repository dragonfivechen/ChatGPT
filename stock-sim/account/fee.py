"""account/fee.py — 佣金和印花税计算

v0.1 固定费率模型：
  佣金: 万三，最低 5 元
  印花税: 千一（仅卖出）
"""

COMMISSION_RATE = 0.0003
COMMISSION_MIN = 5.0
STAMP_TAX_RATE = 0.001


def calc_commission(trade_amount: float) -> float:
    """买入/卖出佣金。trade_amount = price × quantity"""
    fee = trade_amount * COMMISSION_RATE
    return max(fee, COMMISSION_MIN)


def calc_stamp_tax(trade_amount: float) -> float:
    """卖出印花税。买入为 0"""
    return trade_amount * STAMP_TAX_RATE


def calc_buy_fees(trade_amount: float) -> float:
    """买入总费用 = 佣金"""
    return calc_commission(trade_amount)


def calc_sell_fees(trade_amount: float) -> float:
    """卖出总费用 = 佣金 + 印花税"""
    return calc_commission(trade_amount) + calc_stamp_tax(trade_amount)
