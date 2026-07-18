"""contract.py — Market Data Contract v0.1

冻结数据契约。只定义事件类型和字段结构。
禁止：请求接口、写文件、业务逻辑。
"""

MARKET_QUOTE = "MARKET_QUOTE"
MARKET_FEED_ERROR = "MARKET_FEED_ERROR"
MARKET_STATUS = "MARKET_STATUS"

QUOTE_FIELDS_REQUIRED = [
    "event_type",
    "timestamp",
    "source",
    "symbol",
    "price",
    "volume",
]

QUOTE_FIELDS_OPTIONAL = [
    "open",
    "high",
    "low",
    "pre_close",
    "amount",
]

QUOTE_SCHEMA = {
    "event_type": MARKET_QUOTE,
    "timestamp": "",        # ISO8601 with tz
    "source": "",           # feed provider name
    "symbol": "",           # 6-digit A-share code
    "data": {
        "price": 0.0,       # latest price
        "open": 0.0,        # optional
        "high": 0.0,        # optional
        "low": 0.0,         # optional
        "pre_close": 0.0,   # optional
        "volume": 0,        # volume (shares)
        "amount": 0.0,      # optional, turnover
    },
}

MARKET_FEED_ERROR_SCHEMA = {
    "event_type": MARKET_FEED_ERROR,
    "timestamp": "",
    "source": "",
    "symbol": "",
    "reason": "",           # timeout / empty / parse_error
}

MARKET_STATUS_CLOSED = {
    "event_type": MARKET_STATUS,
    "market_status": "CLOSED",
}
