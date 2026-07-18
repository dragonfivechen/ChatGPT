"""strategy/events.py — 策略事件构造

STRATEGY_SIGNAL 事件的生成和追加。
"""

import time
import json
import os

from .base import Signal


def signal_event(signal: Signal) -> dict:
    """Signal → STRATEGY_SIGNAL event dict"""
    d = signal.to_dict()
    d["timestamp"] = time.strftime(
        "%Y-%m-%dT%H:%M:%S+08:00", time.localtime()
    )
    return d


def append_signal_event(event: dict, events_dir: str = "") -> None:
    """追加信号事件到 events.jsonl"""
    if not events_dir:
        events_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "events",
        )
    os.makedirs(events_dir, exist_ok=True)
    path = os.path.join(events_dir, "strategy_signals.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
