"""portfolio/snapshot.py — PORTFOLIO_SNAPSHOT 事件构造

将 Portfolio 模型转为标准化事件，追加到 events.jsonl。
"""

import time
import json
import os

from .model import Portfolio


def build_snapshot_event(portfolio: Portfolio) -> dict:
    """构造 PORTFOLIO_SNAPSHOT 事件"""
    return {
        "event_type": "PORTFOLIO_SNAPSHOT",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "portfolio": portfolio.to_dict(),
    }


def append_snapshot_event(event: dict, events_dir: str = "") -> None:
    """追加快照事件到 events.jsonl"""
    if not events_dir:
        events_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "events",
        )
    os.makedirs(events_dir, exist_ok=True)
    path = os.path.join(events_dir, "portfolio_snapshots.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def snapshot(
    account_id: str,
    cash: float,
    market_value: float,
    equity: float,
    holdings: list[dict],
    total_return: float,
    peak_equity: float,
    drawdown: float,
    events_dir: str = "",
) -> dict:
    """全流程：生成 Portfolio → 构造事件 → 追加存储 → 返回事件"""
    from .model import Holding, Portfolio

    holding_objs = [
        Holding(**h) for h in holdings
    ]
    pf = Portfolio(
        account_id=account_id,
        cash=cash,
        market_value=market_value,
        equity=equity,
        holdings=holding_objs,
        total_return=total_return,
        peak_equity=peak_equity,
        drawdown=drawdown,
    )
    event = build_snapshot_event(pf)
    append_snapshot_event(event, events_dir)
    return event
