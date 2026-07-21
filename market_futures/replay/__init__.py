#!/usr/bin/env python3
"""
Futures-Sim v0.1 — replay/__init__.py

历史行情回放适配层入口。

暴露接口:
  load_historical(path)        → list[dict] CSV 原始行
  convert_to_quotes(rows)      → list[dict] FUTURES_QUOTE 事件
  run_replay(path)             → 直接写入 futures_events_replay.jsonl
"""

from .loader import load_historical
from .converter import convert_to_quotes, write_replay_events

__all__ = ["load_historical", "convert_to_quotes", "write_replay_events"]
