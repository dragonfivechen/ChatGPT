#!/usr/bin/env python3
"""
trading-runtime — signal_receiver.py

职责: 消费 FUTURES_SIGNAL → 验证 → 产出 ORDER 事件

输入: SIGNAL 事件流 (JSONL 文件或列表)
      {
        "event_type": "FUTURES_SIGNAL",
        "ts": "2026-01-06T09:00:00+08:00",
        "strategy_id": "MA",
        "symbol": "RB",
        "action": "BUY",
        "qty": 1,
        "confidence": 0.5,
        "note": ""
      }

输出: ORDER 事件 (写入 JSONL)
      {
        "event_type": "ORDER",
        "ts": "2026-01-06T09:00:00+08:00",
        "symbol": "RB",
        "action": "BUY",
        "qty": 1,
        "strategy_id": "MA"
      }

约束:
  - action 只接受 BUY / SELL / CLOSE
  - 不做转换，保持和 Signal 合约一致
  - 不接触行情、账户、成交
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Iterator

VALID_ACTIONS = frozenset({"BUY", "SELL", "CLOSE"})

BJT = timezone(timedelta(hours=8))


def read_signals(path: str) -> list[dict]:
    """从 JSONL 文件读取 SIGNAL 事件"""
    signals = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if evt.get("event_type") == "FUTURES_SIGNAL":
                signals.append(evt)
    return signals


def generate_orders(signals: list[dict]) -> list[dict]:
    """将 SIGNAL 事件转换为 ORDER 事件"""
    orders = []
    drop = 0
    for s in signals:
        action = s.get("action", "").upper()
        if action not in VALID_ACTIONS:
            drop += 1
            continue

        orders.append({
            "event_type": "ORDER",
            "ts": s.get("ts", datetime.now(BJT).isoformat()),
            "symbol": s["symbol"],
            "action": action,
            "qty": max(s.get("qty", 1), 1),
            "strategy_id": s.get("strategy_id", "unknown"),
        })

    if drop:
        print(f"[signal_receiver] ⚠️  丢弃 {drop} 个无效 action 信号")
    return orders


def write_orders(orders: list[dict], path: str) -> int:
    """写入 ORDER 事件到 JSONL"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for o in orders:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return len(orders)


def load_orders(path: str) -> list[dict]:
    """从 JSONL 读取 ORDER 事件"""
    orders = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            orders.append(json.loads(line))
    return orders


def _replay_verify():
    """验证: 能从已有 replay 信号文件消费并输出 ORDER"""
    import tempfile

    # 读取 market_futures 在 replay 阶段产生的信号
    test_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "market_futures", "futures_events.jsonl"
    )
    if not os.path.exists(test_path):
        print("[signal_receiver] ❌ 测试: 无信号文件，跳过")
        return

    signals = read_signals(test_path)
    orders = generate_orders(signals)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        tmp = f.name
        write_orders(orders, tmp)

    n = len(open(tmp).readlines())
    print(f"[signal_receiver] ✅ 验证: {len(signals)} 信号 → {n} ORDER")
    os.unlink(tmp)


if __name__ == "__main__":
    _replay_verify()
