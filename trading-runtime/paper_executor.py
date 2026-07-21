#!/usr/bin/env python3
"""
trading-runtime — paper_executor.py

职责: 消费 ORDER 事件 → 匹配行情 → 产出 FILL 事件

输入: ORDER + QUOTE 双事件流
      ORDER: {"event_type": "ORDER", "symbol": "RB", "action": "BUY", ...}
      QUOTE: {"event_type": "FUTURES_QUOTE", "symbol": "RB", "price": 3295, ...}

输出: FILL 事件
      {"event_type": "FILL", "ts": "...", "symbol": "RB", "price": 3295, "qty": 1}

规则:
  - 只接受 CLOSE/BUY/SELL 方向 ORDER
  - FILL 价格 = 最近一条同品种 QUOTE 的 price
  - 无可用 QUOTE 时抛弃该 ORDER（不堆积）
  - 记录未成交和被成交计入统计
"""

import json
import os
from collections import defaultdict
from typing import Iterator


class PaperExecutor:
    """纸交易执行器"""

    def __init__(self):
        self.quote_cache: dict[str, dict] = {}       # symbol → 最新 QUOTE
        self.fills: list[dict] = []
        self.dropped: list[dict] = []                 # 因无行情放弃的 ORDER
        self.stats = {"processed": 0, "filled": 0, "dropped": 0}

    def feed_quote(self, quote: dict):
        """注入一条 QUOTE 事件"""
        sym = quote.get("symbol", "")
        if not sym:
            return
        price = quote.get("price") or quote.get("close", 0)
        if price:
            self.quote_cache[sym] = {
                "price": float(price),
                "ts": quote.get("ts", ""),
            }

    def execute(self, order: dict) -> dict | None:
        """执行一条 ORDER, 返回 FILL 或 None（未成交）"""
        self.stats["processed"] += 1
        sym = order.get("symbol", "")
        action = order.get("action", "").upper()
        qty = order.get("qty", 1)

        if action not in ("BUY", "SELL", "CLOSE"):
            self.dropped.append(order)
            self.stats["dropped"] += 1
            return None

        if sym not in self.quote_cache:
            self.dropped.append(order)
            self.stats["dropped"] += 1
            return None

        market = self.quote_cache[sym]
        fill_price = market["price"]
        fill_ts = order.get("ts", market.get("ts", ""))

        fill = {
            "event_type": "FILL",
            "ts": fill_ts,
            "symbol": sym,
            "action": action,
            "price": fill_price,
            "qty": qty,
            "strategy_id": order.get("strategy_id", ""),
        }
        self.fills.append(fill)
        self.stats["filled"] += 1
        return fill

    def run_events(self, orders: list[dict], quotes: list[dict]) -> list[dict]:
        """运行完整的事件序列: 先灌入全部 QUOTE, 再消费 ORDER"""
        # 构建 QUOTE 索引: symbol → [quotes in chronological order]
        quote_index: dict[str, list[dict]] = defaultdict(list)
        for q in quotes:
            if q.get("event_type") not in ("FUTURES_QUOTE", "QUOTE", "quote"):
                continue
            sym = q.get("symbol", "")
            if sym:
                quote_index[sym].append(q)

        # 按 ORDER 时间有序执行，使用 ORDER 发生时最接近的 QUOTE
        fills = []
        for o in sorted(orders, key=lambda x: x.get("ts", "")):
            sym = o.get("symbol", "")
            order_ts = o.get("ts", "")

            # 找到这条 ORDER 之前或同时的最新 QUOTE
            best = None
            for q in quote_index.get(sym, []):
                q_ts = q.get("ts", "")
                if q_ts <= order_ts:
                    best = q
                elif not best:
                    best = q  # 没有更早的，用第一个可用的

            if best:
                self.feed_quote(best)
            f = self.execute(o)
            if f:
                fills.append(f)

        return fills

    def report(self) -> dict:
        return dict(self.stats)

    def save_fills(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for fill in self.fills:
                f.write(json.dumps(fill, ensure_ascii=False) + "\n")
        print(f"[paper_executor] 💾 {len(self.fills)} FILL → {path}")
