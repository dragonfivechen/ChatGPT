"""validator.py — Quote Event 边界检查

只检查，不修复。
"""

from . import contract
from .symbols import is_valid_symbol


def validate_quote(event: dict) -> tuple[bool, list[str]]:
    """检查 quote event 是否合法。返回 (is_valid, errors)。"""
    errors = []

    if event.get("event_type") != contract.MARKET_QUOTE:
        errors.append(f"wrong event_type: {event.get('event_type')}")

    if not event.get("timestamp"):
        errors.append("missing timestamp")

    if not event.get("source"):
        errors.append("missing source")

    sym = event.get("symbol", "")
    if not is_valid_symbol(sym):
        errors.append(f"invalid symbol: {sym}")

    data = event.get("data", {})

    price = data.get("price", 0)
    if not isinstance(price, (int, float)) or price <= 0:
        errors.append(f"invalid price: {price}")

    volume = data.get("volume", -1)
    if not isinstance(volume, int) or volume < 0:
        errors.append(f"invalid volume: {volume}")

    return len(errors) == 0, errors


def is_trading_time() -> bool:
    """判断当前是否在 A 股交易时段。
    不考虑节假日，Feed 无数据即视为闭市。
    """
    import time
    t = time.localtime()
    hour = t.tm_hour
    minute = t.tm_min
    wday = t.tm_wday  # 0=Mon

    # 周末
    if wday >= 5:
        return False

    # 上午 09:30-11:30
    if (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
        return True

    # 下午 13:00-15:00
    if (hour == 13) or (hour == 14) or (hour == 15 and minute == 0):
        return True

    return False
