#!/usr/bin/env python3
"""
trading-runtime — market_monitor.py

职责: 消费 QUOTE 事件流 → 维护最新行情快照

输入: FUTURES_QUOTE 事件
      {"event_type": "FUTURES_QUOTE", "ts": "...", "symbol": "RB",
       "price": 3295, "open": 3280, "high": 3300, "low": 3270, ...}

输出: 按品种的最新行情缓存 (price, ts, bid/ask 等)

特性:
  - 只保存最新一条 QUOTE/品种
  - 支持回放模式和实时追加模式
  - get_price(symbol) → 最新价格
  - snapshot() → 全部品种快照
"""

import json
import os


class MarketMonitor:
    """行情监控器 — 维护品种最新价格"""

    def __init__(self, initial_snapshots: dict | None = None):
        # symbol → {"price": float, "ts": str, "raw": dict}
        self.latest: dict[str, dict] = initial_snapshots or {}

    def feed(self, quote: dict):
        """注入一条行情事件"""
        sym = quote.get("symbol", "")
        if not sym:
            return

        price = quote.get("price")
        if price is None:
            price = quote.get("close")
        if price is None:
            return

        self.latest[sym] = {
            "price": float(price),
            "ts": quote.get("ts", ""),
            "raw": quote,
        }

    def feed_many(self, quotes: list[dict]):
        """批量注入"""
        for q in quotes:
            self.feed(q)

    def get_price(self, symbol: str) -> float | None:
        """获取某品种最新价格"""
        entry = self.latest.get(symbol)
        return entry["price"] if entry else None

    def get_ts(self, symbol: str) -> str:
        """获取某品种最新行情时间"""
        entry = self.latest.get(symbol)
        return entry["ts"] if entry else ""

    def has(self, symbol: str) -> bool:
        return symbol in self.latest

    def snapshot(self) -> dict:
        """返回全部品种行情快照"""
        return {
            sym: {"price": v["price"], "ts": v["ts"]}
            for sym, v in self.latest.items()
        }

    def save_snapshot(self, path: str):
        """保存行情快照到 JSONL (用于断点恢复)"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.latest, ensure_ascii=False))

    @staticmethod
    def load_snapshot(path: str) -> dict:
        """从文件恢复行情快照"""
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, dict)}
