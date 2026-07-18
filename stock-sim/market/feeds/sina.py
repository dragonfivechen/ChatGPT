"""feeds/sina.py — 新浪财经实时行情源（备用）

HTTP GET:
  https://hq.sinajs.cn/list=sh600519

仅在 TencentFeed 失败时调用。
"""

import time
import urllib.request
from typing import Optional

from .base import MarketFeed

SINA_URL = "https://hq.sinajs.cn/list={market}{symbol}"

MARKET_MAP = {
    "SH": "sh",
    "SZ": "sz",
}


class SinaFeed(MarketFeed):

    def fetch_quote(self, symbol: str) -> Optional[dict]:
        return self._fetch(symbol)

    def fetch_quotes(self, symbols: list[str]) -> dict[str, Optional[dict]]:
        result = {}
        for sym in symbols:
            result[sym] = self._fetch(sym)
            time.sleep(0.1)
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

        url = SINA_URL.format(market=market, symbol=symbol)
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                text = resp.read().decode("gbk")
        except Exception:
            return None

        if "=\"" not in text:
            return None

        raw = text.split("=\"", 1)[1].rstrip("\";\n\r ")
        parts = raw.split(",")

        if len(parts) < 32:
            return None

        def f(idx):
            try:
                return float(parts[idx]) if parts[idx] else 0.0
            except (ValueError, IndexError):
                return 0.0

        def iv(idx):
            try:
                return int(float(parts[idx])) if parts[idx] else 0
            except (ValueError, IndexError):
                return 0

        return {
            "_feed": "sina",
            "_symbol": symbol,
            "_ts": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
            "price": f(3),
            "open": f(1),
            "high": f(4),
            "low": f(5),
            "pre_close": f(2),
            "volume": iv(8),
            "amount": f(9),
            "name": parts[0],
        }
