#!/usr/bin/env python3
"""stock-observer.py — Stock-sim 运行观测层 v1

只读观察，不参与交易决策，不修改状态。
每次策略运行后触发，输出观测指标到 stock-sim/observe/stock_metrics.jsonl

指标:
  行情链:  tick数, symbol覆盖, feed错误
  策略链:  运行次数, 信号数, 无信号原因
  信号质量: BUY/SELL分布
  执行链:  成交数, 失败数
  持仓:    symbol数, 总市值, 现金
"""

import sys, os, json
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
EVENTS_DIR = os.path.join(BASE, "events")
OBSERVE_DIR = os.path.join(BASE, "observe")
os.makedirs(OBSERVE_DIR, exist_ok=True)

OUTPUT = os.path.join(OBSERVE_DIR, "stock_metrics.jsonl")
TS = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def observe():
    metrics = {"ts": TS, "pass": True}

    # 1. 行情链
    quotes = load_jsonl(os.path.join(EVENTS_DIR, "market_events.jsonl"))
    symbols_seen = set()
    feed_errors = 0
    for q in quotes:
        if q.get("event_type") == "MARKET_QUOTE":
            symbols_seen.add(q.get("symbol", ""))
        elif q.get("event_type") == "MARKET_FEED_ERROR":
            feed_errors += 1

    metrics["market"] = {
        "total_ticks": len(quotes),
        "symbols_covered": len(symbols_seen),
        "feed_errors": feed_errors,
    }

    # 2. 策略链
    signals = load_jsonl(os.path.join(EVENTS_DIR, "strategy_signals.jsonl"))
    v1_signals = [s for s in signals if "V1" in s.get("strategy_id", "")]
    v2_signals = [s for s in signals if "V2" in s.get("strategy_id", "")]
    buoys = [s for s in signals if s.get("action") == "BUY"]
    sells = [s for s in signals if s.get("action") == "SELL"]

    metrics["strategy"] = {
        "total_signals": len(signals),
        "v1_signals": len(v1_signals),
        "v2_signals": len(v2_signals),
        "buys": len(buoys),
        "sells": len(sells),
    }

    # 3. 执行链
    snapshots = load_jsonl(os.path.join(EVENTS_DIR, "portfolio_snapshots.jsonl"))
    last_snap = snapshots[-1] if snapshots else {}
    portfolio = last_snap.get("portfolio", {})
    holdings = portfolio.get("holdings", [])
    cash = portfolio.get("cash", 0)
    equity = portfolio.get("equity", 0)

    metrics["portfolio"] = {
        "positions": len(holdings),
        "cash": cash,
        "equity": equity,
        "snapshots": len(snapshots),
    }

    if holdings:
        metrics["portfolio"]["positions_detail"] = [
            {"symbol": h.get("symbol", ""), "qty": h.get("quantity", 0),
             "value": h.get("market_value", 0)}
            for h in holdings
        ]

    # 4. Replay 一致性（仅在有事件的时段）
    metrics["replay"] = {
        "event_count": len(quotes) + len(signals) + len(snapshots),
        "check": "pending" if len(quotes) < 2 else "available",
    }

    # 写入
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(metrics, ensure_ascii=False) + "\n")

    print(f"[stock-observer] {metrics['ts']}: "
          f"ticks={metrics['market']['total_ticks']} "
          f"signals={metrics['strategy']['total_signals']} "
          f"pos={metrics['portfolio']['positions']}")


if __name__ == "__main__":
    observe()
