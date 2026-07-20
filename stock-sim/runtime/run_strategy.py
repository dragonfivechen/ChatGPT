#!/usr/bin/env python3
"""runtime/run_strategy.py — 策略运行时

被 systemd timer 调用。每次执行:
  1. 读取最新的 MARKET_QUOTE events
  2. 加载策略引擎
  3. 分发行情给策略
  4. 收集 SIGNAL → ORDER（自动）
  5. EXECUTION → ACCOUNT → PORTFOLIO
  6. 输出 ACCOUNT_UPDATE + PORTFOLIO_SNAPSHOT

运行方式: systemd oneshot timer（5min 采集后调用）
"""

import sys
import os
import json

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from strategy.engine import StrategyEngine
from strategy.breakout import BreakoutStrategy
from strategy.breakout_v2 import BreakoutV2
from strategy.events import append_signal_event
from strategy.adapter import signal_to_order
from trading.execution.simulator import ExecutionSimulator
from account.model import Account
from account.ledger import apply_trade
from portfolio.calculator import (calc_market_value, calc_holdings, calc_return)
from portfolio.drawdown import DrawdownTracker
from portfolio.snapshot import snapshot as pf_snapshot


def load_latest_quote(events_dir: str) -> dict | None:
    """从 market_events.jsonl 读取最新一条行情"""
    path = os.path.join(events_dir, "market_events.jsonl")
    if not os.path.exists(path):
        return None
    last_line = None
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if last_line:
        return json.loads(last_line)
    return None


def load_historical_quotes(events_dir: str) -> list[dict]:
    """从 market_events.jsonl 读取历史行情，按时间正序返回"""
    path = os.path.join(events_dir, "market_events.jsonl")
    if not os.path.exists(path):
        return []
    quotes = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                q = json.loads(line)
                if q.get("event_type") == "MARKET_QUOTE":
                    quotes.append(q)
            except json.JSONDecodeError:
                continue
    # 按时间正序排列
    quotes.sort(key=lambda x: x.get("timestamp", ""))
    return quotes


def load_account() -> Account:
    """加载/创建账户（v0.1: 每次重新创建）"""
    return Account()


def main():
    events_dir = os.path.join(_PROJECT, "events")

    quote = load_latest_quote(events_dir)
    if quote is None:
        print("[strategy-runner] no market data yet")
        return

    # 引擎 + 策略
    engine = StrategyEngine()
    # 注册策略
    bs = BreakoutStrategy()
    engine.register(bs)
    bs_v2 = BreakoutV2()
    engine.register(bs_v2)

    # 从历史行情恢复策略状态（避免无状态快照问题）
    historical = load_historical_quotes(events_dir)
    for hq in historical:
        for strat in [bs, bs_v2]:
            strat.on_quote(hq, {"cash": 0, "positions": {}})
    # 馈入最新行情，触发实际信号判断
    pf_view_init = {"cash": 0, "positions": {}}
    for strat in [bs, bs_v2]:
        strat.on_quote(quote, pf_view_init)

    # 执行 + 账户 + 组合
    sim = ExecutionSimulator()
    acc = load_account()
    dd = DrawdownTracker(acc.initial_cash)

    # 构建 portfolio 视图
    pf_view = {
        "cash": acc.cash,
        "equity": acc.equity,
        "positions": {
            sym: {"quantity": p.quantity}
            for sym, p in acc.positions.items() if p.quantity > 0
        },
    }

    signals = engine.on_quote(quote, pf_view)
    for sig_evt in signals:
        append_signal_event(sig_evt, events_dir)
        o = signal_to_order(sig_evt)
        if o is None:
            continue
        o.status = "SUBMITTED"
        sim.add_order(o.to_dict())

    trades = sim.on_quote(quote)
    trade_details = []
    for t in trades:
        apply_trade(acc, t)
        td = t.get("trade", t)
        sym = td.get("symbol", "")
        side = td.get("side", "")
        price_t = td.get("price", 0)
        qty = td.get("quantity", 0)
        trade_details.append(f"{side} {qty}×{sym} @ {price_t:.2f}")

    if trade_details:
        push_title = "🟢 模拟交易执行"
        push_body = "策略: " + signals[0].get("strategy_id", "?")[:20] if signals else "?"
        push_body += "\n" + "\n".join(trade_details)
        push_body += f"\n现金: {acc.cash:.0f}"
        import subprocess, os as _os
        _script_dir = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        push_script = _os.path.join(_script_dir, "hooks", "oek-ci-gate", "push-notify.mjs")
        subprocess.Popen(["node", push_script, push_title, push_body],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 组合快照
    symbol = quote.get("symbol", "")
    price = quote.get("data", {}).get("price", 0)
    quotes = {symbol: price} if symbol and price else {}
    mv = calc_market_value(acc, quotes)
    eq = acc.cash + mv
    peak, draw = dd.update(eq)
    h = calc_holdings(acc, quotes, eq)
    evt = pf_snapshot(
        acc.account_id, acc.cash, mv, eq, h,
        calc_return(eq, acc.initial_cash), peak, draw,
        events_dir,
    )

    print(
        f"[strategy-runner] quote={symbol}@{price} "
        f"signals={len(signals)} trades={len(trades)} "
        f"eq={eq:.0f}"
    )


if __name__ == "__main__":
    main()
