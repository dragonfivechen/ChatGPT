#!/usr/bin/env python3
"""collector.py — 行情采集调度入口

被 systemd timer 调用。每次运行：
  1. 检查是否交易时段
  2. 如果是：采集行情 → 标准化 → 校验 → 追加 events.jsonl
  3. 如果否：退出

运行方式：systemd oneshot timer（交易时段每 5 秒触发）
"""

import json
import os
import sys
import time

# 确保能找到 market 包
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)  # stock-sim/
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from market.feeds.tencent import TencentFeed
from market.feeds.sina import SinaFeed
from market.normalize import normalize, error_event
from market.validator import validate_quote, is_trading_time
from market.symbols import format_symbol

EVENTS_FILE = os.path.join(PROJECT_DIR, "events", "market_events.jsonl")

# 默认股票池（第一版硬编码，后续可配置）
DEFAULT_SYMBOLS = [
    "000001",  # 平安银行
    "600519",  # 贵州茅台
    "300750",  # 宁德时代
    "000333",  # 美的集团
    "601318",  # 中国平安
]


def append_event(event: dict):
    """追加事件到 events.jsonl（原子追加）"""
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def collect(symbols: list[str] = None):
    """单次采集周期"""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    if not is_trading_time():
        return

    # Primary feed
    primary = TencentFeed()
    raw = primary.fetch_quotes(symbols)

    for sym in symbols:
        raw_data = raw.get(sym)

        # Fallback to Sina
        if raw_data is None:
            backup = SinaFeed()
            raw_data = backup.fetch_quote(sym)
            if raw_data is None:
                evt = error_event(sym, "tencent_and_sina_failed", "tencent+sina")
                append_event(evt)
                continue

        try:
            quote = normalize(raw_data)
        except Exception as e:
            evt = error_event(sym, f"normalize_failed: {e}", raw_data.get("_feed", "unknown"))
            append_event(evt)
            continue

        valid, errors = validate_quote(quote)
        if not valid:
            evt = error_event(sym, f"validation_failed: {'; '.join(errors)}", quote.get("source", "unknown"))
            append_event(evt)
            continue

        append_event(quote)


def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="stock-sim 行情采集器")
    parser.add_argument("--once", action="store_true", help="采集一次后退出")
    parser.add_argument("--watch", action="store_true", help="连续采集（5s间隔）")
    parser.add_argument("--symbols", nargs="+", help="指定股票代码")
    args = parser.parse_args()

    symbols = [format_symbol(s) for s in (args.symbols or DEFAULT_SYMBOLS)]

    if args.watch:
        print(f"[collector] watch mode — {len(symbols)} symbols, 5s interval")
        while True:
            collect(symbols)
            time.sleep(5)
    else:
        collect(symbols)
        print(f"[collector] done — {len(symbols)} symbols")


if __name__ == "__main__":
    main()
