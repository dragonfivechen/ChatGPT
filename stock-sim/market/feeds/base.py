"""feeds/base.py — MarketFeed 抽象接口

所有行情源必须实现此接口。
"""

from abc import ABC, abstractmethod
from typing import Optional


class MarketFeed(ABC):

    @abstractmethod
    def fetch_quote(self, symbol: str) -> Optional[dict]:
        """获取单只股票实时行情。
        返回原始字典（尚未标准化），失败返回 None。
        """
        ...

    @abstractmethod
    def fetch_quotes(self, symbols: list[str]) -> dict[str, Optional[dict]]:
        """批量获取行情。返回 {symbol: raw_dict_or_None}。"""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """确认数据源是否可达。"""
        ...
