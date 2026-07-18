"""normalize.py — 原始行情 → MARKET_QUOTE Event

输入：TencentFeed / SinaFeed 返回的原始字典
输出：符合 contract.py 的标准化 quote event

禁止：预测 / 补值 / 修正 / 平滑
"""

import copy
from . import contract
from .symbols import detect_market, format_symbol


def normalize(raw: dict) -> dict:
    """Feed 原始字典 → MARKET_QUOTE event"""

    symbol = format_symbol(raw.get("_symbol", ""))

    data = {
        "price": raw.get("price", 0.0),
        "volume": raw.get("volume", 0),
    }

    for field in contract.QUOTE_FIELDS_OPTIONAL:
        val = raw.get(field)
        if val is not None and val != 0.0:
            data[field] = val

    event = {
        "event_type": contract.MARKET_QUOTE,
        "timestamp": raw.get("_ts", ""),
        "source": raw.get("_feed", "unknown"),
        "symbol": symbol,
        "market": detect_market(symbol),
        "data": data,
    }

    return event


def error_event(symbol: str, reason: str, source: str = "unknown") -> dict:
    """生成 MARKET_FEED_ERROR 事件"""
    import time
    return {
        "event_type": contract.MARKET_FEED_ERROR,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "source": source,
        "symbol": symbol,
        "reason": reason,
    }
