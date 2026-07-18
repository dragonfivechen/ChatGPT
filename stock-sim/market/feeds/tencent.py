"""feeds/tencent.py — 腾讯财经实时行情源（主入口）

HTTP GET:
  https://qt.gtimg.cn/q=sh600519

返回格式：
  v_sh600519="1~贵州茅台~...~1450.20~..."

解析后返回原始字典。
"""

import time
import urllib.request
from typing import Optional

from .base import MarketFeed

TENCENT_URL = "https://qt.gtimg.cn/q={market}{symbol}"

MARKET_MAP = {
    "SH": "sh",
    "SZ": "sz",
}

# 腾讯返回字段索引（0-based）
# 完整格式见腾讯开放文档
FIELDS = [
    "market",          # 0  市场
    "name",            # 1  名称
    "code",            # 2  代码
    "price",           # 3  当前价
    "last_close",      # 4  昨收
    "open",            # 5  开盘
    "volume",          # 6  成交量(手)
    "bid_vol1",        # 7  买一量
    "bid1",            # 8  买一价
    "ask1",            # 9  卖一价
    "ask_vol1",        # 10 卖一量
    # ... 中间多数不解析
    "high",            # 33 最高
    "low",             # 34 最低
    "pre_close",       # 35 昨收(冗余)
    "amount",          # 38 成交额
]


class TencentFeed(MarketFeed):

    def fetch_quote(self, symbol: str) -> Optional[dict]:
        return self._fetch(symbol)

    def fetch_quotes(self, symbols: list[str]) -> dict[str, Optional[dict]]:
        result = {}
        for sym in symbols:
            result[sym] = self._fetch(sym)
            time.sleep(0.1)  # 避免频率过高
        return result

    def health_check(self) -> bool:
        try:
            return self._fetch("000001") is not None
        except Exception:
            return False

    def _fetch(self, symbol: str) -> Optional[dict]:
        from ..symbols import detect_market
        market = MARKET_MAP.get(detect_market(symbol))
        if not market:
            return None

        url = TENCENT_URL.format(market=market, symbol=symbol)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                text = resp.read().decode("gbk")
        except Exception:
            return None

        # 腾讯返回: v_sh600519="...";
        if "=\"" not in text:
            return None

        raw = text.split("=\"", 1)[1].rstrip("\";\n\r ")
        parts = raw.split("~")

        if len(parts) < 40:
            return None

        def safe_float(idx):
            try:
                return float(parts[idx]) if parts[idx] else 0.0
            except (ValueError, IndexError):
                return 0.0

        def safe_int(idx):
            try:
                return int(float(parts[idx])) if parts[idx] else 0
            except (ValueError, IndexError):
                return 0

        return {
            "_feed": "tencent",
            "_symbol": symbol,
            "_ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
            "price": safe_float(3),
            "open": safe_float(5),
            "high": safe_float(33),
            "low": safe_float(34),
            "pre_close": safe_float(4),
            "volume": safe_int(6) * 100,   # 腾讯返回手数 → 股
            "amount": safe_float(38),
            "name": parts[1] if len(parts) > 1 else "",
        }
