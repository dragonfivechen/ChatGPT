#!/usr/bin/env python3
"""runtime/run_strategy.py — 策略运行时（RANK_FOLLOW_V1）

被 systemd timer 调用。每次执行:
  1. 读取最新的 MARKET_QUOTE events
  2. 加载策略引擎（RankFollowV1）
  3. 分发行情给策略
  4. 收集 SIGNAL → ORDER（自动）
  5. EXECUTION → ACCOUNT → PORTFOLIO
  6. 输出 ACCOUNT_UPDATE + PORTFOLIO_SNAPSHOT

运行方式: systemd oneshot timer（5min 采集后调用）
"""

import sys
import os
import json
import re
import time

_THIS = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.dirname(_THIS)  # stock-sim/
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from strategy.engine import StrategyEngine
from strategy.rank_follow_v1 import RankFollowV1
from strategy.events import append_signal_event
from strategy.adapter import signal_to_order
from trading.execution.simulator import ExecutionSimulator
from account.model import Account
from account.ledger import apply_trade
from portfolio.calculator import (calc_market_value, calc_holdings, calc_return)
from portfolio.drawdown import DrawdownTracker
from portfolio.snapshot import snapshot as pf_snapshot
from trade.trade_ledger import update as ledger_update, update_post_exit

# ── 推送格式化 ──────────────────────────────────────────

_RANK_EMOJI = {1: '🥇', 2: '🥈', 3: '🥉', 4: '4️⃣', 5: '5️⃣'}
_RANK_ALLOC = {1: 25, 2: 18, 3: 12, 4: 9, 5: 6}


def _ts8() -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime())


def _fmt_money(v: float) -> str:
    if v >= 10000:
        return f"{v / 10000:.1f}万"
    return f"{v:.0f}"


def _load_name_map() -> dict[str, str]:
    """从 scoring_pool.json details 加载 symbol→名称 映射"""
    pool_path = os.path.join(_PROJECT, "market", "scoring_pool.json")
    if not os.path.exists(pool_path):
        return {}
    try:
        with open(pool_path, "r", encoding="utf-8") as f:
            pool = json.load(f)
        details = pool.get("details", [])
        return {d["symbol"]: d["name"] for d in details if "symbol" in d and "name" in d}
    except Exception:
        return {}


def _ledger_field(events_dir: str, symbol: str, field: str):
    """读取 trade_ledger.jsonl 尾端，找 symbol 当前持仓的 open 字段"""
    path = os.path.join(events_dir, "trade_ledger.jsonl")
    if not os.path.exists(path):
        return None
    val = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("symbol") != symbol:
                continue
            et = e.get("event_type", "")
            if et == "TRADE_OPEN":
                val = e.get("entry", {}).get(field, None)
            elif et == "TRADE_CLOSE":
                val = None
    return val


def _build_push_body(
    events_dir: str,
    signals: list[dict],
    prev_held: set[str],
    rank_map: dict[str, int],
    score_map: dict[str, float],
    acc,
    prices: dict[str, float],
) -> str:
    lines = []
    lines.append("🧾 模拟交易执行")
    lines.append(f"策略: RANK_FOLLOW_V1")
    lines.append(f"时间: {_ts8()}")

    name_map = _load_name_map()

    def _stock_label(sym: str) -> str:
        n = name_map.get(sym, "")
        return f"{sym} {n}" if n else sym

    lines.append("")

    # ── 建仓（新票） ──
    new_buys = []
    add_buys = []
    for sig in signals:
        if sig.get("action") != "BUY":
            continue
        sym = sig["symbol"]
        if sym not in prev_held:
            new_buys.append(sig)
        else:
            add_buys.append(sig)

    if new_buys:
        lines.append("【建仓】")
        for sig in new_buys:
            sym = sig["symbol"]
            note = sig.get("note", "")
            rank = rank_map.get(sym, 0)
            score = score_map.get(sym, 0)
            qty = sig.get("quantity", 0)
            price = prices.get(sym, 0)
            amount = price * qty
            alloc_pct = _RANK_ALLOC.get(rank, 0)
            m = re.search(r"(\d+)%", note)
            alloc_pct = int(m.group(1)) if m else alloc_pct
            emoji = _RANK_EMOJI.get(rank, f"#{rank}")
            lines.append(f"{emoji} {_stock_label(sym)}")
            lines.append(f"Rank:{rank}  L3:{score:.1f}")
            lines.append(f"仓位:{alloc_pct}%  成交:{int(qty)}×{price:.2f}")
            lines.append(f"金额:{_fmt_money(amount)}")
            lines.append("")

    if new_buys and not add_buys and not any(s.get("action") == "SELL" for s in signals):
        lines.pop()  # remove trailing blank if only buys

    # ── 加仓 ──
    if add_buys:
        lines.append("【加仓】")
        for sig in add_buys:
            sym = sig["symbol"]
            rank = rank_map.get(sym, 0)
            score = score_map.get(sym, 0)
            qty = sig.get("quantity", 0)
            price = prices.get(sym, 0)
            amount = price * qty
            lines.append(f"  {sym}  +{int(qty)}×{price:.2f}={_fmt_money(amount)}")
        lines.append("")

    # ── 卖出 ──
    sell_signals = [s for s in signals if s.get("action") == "SELL"]
    if sell_signals:
        lines.append("【卖出】")
        for sig in sell_signals:
            sym = sig["symbol"]
            note = sig.get("note", "")
            qty = sig.get("quantity", 0)
            price = prices.get(sym, 0)
            curr_rank = rank_map.get(sym, 0)
            entry_rank = _ledger_field(events_dir, sym, "rank")

            # 原因判定
            reason = "RANK_DROP"
            if "替换" in note:
                reason = "REPLACE"
            elif "止损" in note:
                reason = "STOP_LOSS"
            elif "回撤" in note:
                reason = "DRAWDOWN"
            elif "止盈" in note:
                reason = "TAKE_PROFIT"

            # 卖出比例
            m = re.search(r"卖(\d+)%", note)
            sell_pct = int(m.group(1)) if m else 0

            # 盈亏估算
            entry_price = _ledger_field(events_dir, sym, "price")
            if not entry_price:
                if hasattr(acc, 'positions') and sym in acc.positions:
                    entry_price = acc.positions[sym].avg_cost
            ret = (price / entry_price - 1) * 100 if entry_price and entry_price > 0 else 0

            emoji = _RANK_EMOJI.get(curr_rank, f"#{curr_rank}")
            lines.append(f"{emoji} {_stock_label(sym)}")
            lines.append(f"原因: {reason}")
            if entry_rank and entry_rank != curr_rank:
                lines.append(f"Rank:{entry_rank} → {curr_rank}")
            else:
                lines.append(f"Rank:{curr_rank}")
            if sell_pct > 0:
                lines.append(f"卖出:{sell_pct}%")
            lines.append(f"盈亏:{ret:+.1f}%")
            lines.append("")

        lines.pop()  # remove trailing blank

    # ── 账户 ──
    mv = calc_market_value(acc, prices)
    pos_count = sum(1 for p in acc.positions.values() if p.quantity > 0)
    lines.append("")
    lines.append("【账户】")
    lines.append(f"总权益:{_fmt_money(acc.equity)}")
    lines.append(f"持仓:{_fmt_money(mv)}")
    lines.append(f"现金:{_fmt_money(acc.cash)}")
    lines.append(f"持仓:{pos_count}/5")

    return "\n".join(lines)


# ── 数据加载 ─────────────────────────────────────────────


def load_all_quotes(events_dir: str) -> list[dict]:
    """从 market_events.jsonl 读取全部行情事件，按时间正序"""
    path = os.path.join(events_dir, "market_events.jsonl")
    if not os.path.exists(path):
        return []
    quotes = []
    with open(path, "r", encoding="utf-8") as f:
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
    quotes.sort(key=lambda x: x.get("timestamp", ""))
    return quotes


def get_latest_batch(all_quotes: list[dict]) -> list[dict]:
    """从全部行情中提取最新一轮采集批次（同分钟内的全部 symbols）"""
    if not all_quotes:
        return []
    latest_ts = all_quotes[-1].get("timestamp", "")
    batch_minute = latest_ts[:16]
    batch = [q for q in all_quotes if q.get("timestamp", "").startswith(batch_minute)]
    return batch if batch else [all_quotes[-1]]


def get_historical_quotes(all_quotes: list[dict], latest_batch: list[dict]) -> list[dict]:
    """最新批次前的全部历史行情（用于策略价格恢复）"""
    if not latest_batch:
        return all_quotes
    batch_minute = latest_batch[0].get("timestamp", "")[:16]
    return [q for q in all_quotes if q.get("timestamp", "")[:16] < batch_minute]


def load_account() -> Account:
    return Account()


# ── 主流程 ───────────────────────────────────────────────


def main():
    events_dir = os.path.join(_PROJECT, "events")

    all_quotes = load_all_quotes(events_dir)
    if not all_quotes:
        print("[strategy-runner] no market data yet")
        return

    latest_batch = get_latest_batch(all_quotes)
    historical = get_historical_quotes(all_quotes, latest_batch)

    print(f"[strategy-runner] batch={len(latest_batch)}syms hist={len(historical)}quotes")

    # ── 策略引擎: RankFollowV1 ──
    engine = StrategyEngine()
    rfv1 = RankFollowV1()
    engine.register(rfv1)

    # 历史行情恢复（用于价格追踪）
    rfv1.feed_history(historical)

    # 执行 + 账户 + 组合
    sim = ExecutionSimulator()
    acc = load_account()
    dd = DrawdownTracker(acc.initial_cash)

    # ── 批量处理最新一轮 ──
    all_signals = []
    all_trades = []
    prev_held = {sym for sym, p in acc.positions.items() if p.quantity > 0}
    for idx, q in enumerate(latest_batch):
        pf_view = {
            "cash": acc.cash,
            "equity": acc.equity,
            "positions": {
                sym: {
                    "quantity": p.quantity,
                    "avg_cost": p.avg_cost,
                    "current_price": q.get("data", {}).get("price", p.avg_cost),
                }
                for sym, p in acc.positions.items() if p.quantity > 0
            },
        }
        # 策略处理行情 → 信号
        sig_evts = engine.on_quote(q, pf_view)
        for sig_evt in sig_evts:
            append_signal_event(sig_evt, events_dir)
            o = signal_to_order(sig_evt)
            if o is None:
                continue
            o.status = "SUBMITTED"
            sim.add_order(o.to_dict())
        all_signals.extend(sig_evts)

        # 执行交易
        ts = sim.on_quote(q)
        for t in ts:
            apply_trade(acc, t)
        all_trades.extend(ts)

    # ── 报价字典（用于组合计算 + 推送） ──
    quotes_dict = {}
    for q in latest_batch:
        sym = q.get("symbol", "")
        pr = q.get("data", {}).get("price", 0)
        if sym and pr > 0:
            quotes_dict[sym] = pr

    # ── 组合快照 ──
    mv = calc_market_value(acc, quotes_dict)
    eq = acc.cash + mv
    peak, draw = dd.update(eq)
    h = calc_holdings(acc, quotes_dict, eq)
    pf_snapshot(
        acc.account_id, acc.cash, mv, eq, h,
        calc_return(eq, acc.initial_cash), peak, draw,
        events_dir,
    )

    # ── 交易账本更新（先于推送，推送会读取账本） ──
    ledger_update(
        events_dir, all_signals,
        rank_map=rfv1._score_rank_map,
        score_map=rfv1._score_map,
    )
    quote_prices = {
        q["symbol"]: q.get("data", {}).get("price", 0)
        for q in latest_batch
    }
    update_post_exit(events_dir, quote_prices)

    # ── 推送（结构化交易摘要） ──
    if all_trades:
        push_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "hooks", "oek-ci-gate", "push-notify.mjs"
        )
        push_body = _build_push_body(
            events_dir, all_signals, prev_held,
            rfv1._score_rank_map, rfv1._score_map,
            acc, quotes_dict,
        )
        subprocess.Popen(
            ["node", push_script, "🧾 模拟交易执行", push_body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    print(
        f"[strategy-runner] batch={len(latest_batch)}syms "
        f"signals={len(all_signals)} trades={len(all_trades)} "
        f"eq={eq:.0f}"
    )


if __name__ == "__main__":
    import subprocess
    main()
