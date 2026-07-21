#!/usr/bin/env python3
"""strategy_live.py — 期货实盘策略执行（oneshot, 被 systemd timer 调用）

流程:
  1. 读取 futurs_events.jsonl 全部历史行情
  2. 加载账户状态
  3. 用全部历史初始化策略引擎（MA/Breakout/RSI）
  4. 仅提取最近一轮信号的成交 → 更新账户
  5. 推送通知（持仓变化/净成交/权益≥1%波动）
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta

BJT = timezone(timedelta(hours=8))

_BASE = os.path.dirname(os.path.abspath(__file__))
_EVENTS_FILE = os.path.join(_BASE, "futures_events.jsonl")
_ACCOUNT_FILE = os.path.join(_BASE, "data", "account_state.json")
_PUSH_SCRIPT = os.path.join(
    _BASE, "..", "hooks", "oek-ci-gate", "push-notify.mjs"
)
_TRADING_RUNTIME = os.path.join(_BASE, "..", "trading-runtime")

sys.path.insert(0, _TRADING_RUNTIME)
from strategy_runner import StrategyRunner  # noqa: E402

INITIAL_CASH = 10_000_000.0
MARGIN_RATES = {
    "RB": 0.10, "I": 0.12, "JM": 0.12,
    "CU": 0.08, "AL": 0.08, "SC": 0.15,
}
MULTIPLIERS = {
    "RB": 10, "I": 100, "JM": 60,
    "CU": 5, "AL": 5, "SC": 1000,
}
SYMBOL_NAMES = {
    "RB": "螺纹钢", "I": "铁矿石", "JM": "焦煤",
    "CU": "沪铜", "AL": "沪铝", "SC": "原油",
}
MIN_SIGNAL_GAP_S = 120  # 同品种信号最小间隔（秒）


def is_trading_time() -> bool:
    now = datetime.now(BJT)
    if now.weekday() >= 5:
        return False
    h, m = now.hour, now.minute
    t = h * 100 + m
    return (
        (900 <= t <= 1130) or
        (1330 <= t <= 1500) or
        (2100 <= t <= 2359) or
        (0 <= t <= 230)
    )


def load_all_quotes() -> dict[str, list[dict]]:
    """加载全部 futurs_events.jsonl，按品种分组"""
    if not os.path.exists(_EVENTS_FILE):
        return {}
    by_sym = {}
    with open(_EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                q = json.loads(line)
            except json.JSONDecodeError:
                continue
            sym = q.get("symbol", "")
            if sym:
                by_sym.setdefault(sym, []).append(q)
    return by_sym


def load_account_state() -> dict:
    if os.path.exists(_ACCOUNT_FILE):
        with open(_ACCOUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "cash": INITIAL_CASH,
        "equity": INITIAL_CASH,
        "positions": {},
        "peak_equity": INITIAL_CASH,
        "last_signal_ts": {},
        "last_processed_idx": 0,  # futurs_events.jsonl 已处理行数
        "trades_log": [],
    }


def save_account_state(state: dict):
    os.makedirs(os.path.dirname(_ACCOUNT_FILE), exist_ok=True)
    with open(_ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def calc_margin(symbol: str, price: float, qty: int) -> float:
    rate = MARGIN_RATES.get(symbol, 0.10)
    mult = MULTIPLIERS.get(symbol, 10)
    return price * mult * qty * rate


def execute_signal(sig: dict, account: dict, quote: dict) -> dict | None:
    sym = sig.get("symbol", "")
    action = sig.get("action", "")
    size = sig.get("size", 1)
    price = sig.get("price", 0)
    if price <= 0:
        price = quote.get("price", 0)
    if price <= 0:
        return None
    ts = quote.get("ts", datetime.now(BJT).isoformat())
    mult = MULTIPLIERS.get(sym, 10)

    positions = account["positions"]
    pos = positions.get(sym, {"quantity": 0, "direction": "多", "avg_cost": 0})
    cur_qty = pos.get("quantity", 0)

    pnl = 0

    if action == "BUY":
        qty = size
        margin_needed = calc_margin(sym, price, qty)
        if account["cash"] < margin_needed:
            return None
        account["cash"] -= price * mult * qty
        new_qty = cur_qty + qty
        if cur_qty > 0:
            new_cost = (pos["avg_cost"] * cur_qty + price * qty) / new_qty
        else:
            new_cost = price
        positions[sym] = {
            "quantity": new_qty,
            "direction": "多",
            "avg_cost": round(new_cost, 2),
            "entry_price": price,
        }

    elif action == "SELL":
        qty = size
        margin_needed = calc_margin(sym, price, qty)
        if account["cash"] < margin_needed:
            return None
        account["cash"] -= calc_margin(sym, price, qty)
        positions[sym] = {
            "quantity": qty,
            "direction": "空",
            "avg_cost": round(price, 2),
            "entry_price": price,
        }

    elif action == "CLOSE":
        if cur_qty == 0:
            return None
        qty = min(size, cur_qty)
        cost = pos["avg_cost"]
        direction = pos["direction"]
        if direction == "多":
            pnl = (price - cost) * mult * qty
            account["cash"] += price * mult * qty
        else:
            pnl = (cost - price) * mult * qty
            account["cash"] += price * mult * qty
        account["total_realized_pnl"] = account.get("total_realized_pnl", 0) + round(pnl, 2)
        new_qty = cur_qty - qty
        if new_qty <= 0:
            del positions[sym]
        else:
            positions[sym]["quantity"] = new_qty
    else:
        return None

    fill = {
        "ts": ts,
        "symbol": sym,
        "action": action,
        "qty": size,
        "price": round(price, 2),
        "pnl": round(pnl, 2),
    }
    account["last_signal_ts"][sym] = ts
    account.setdefault("trades_log", []).append(fill)
    return fill


def main():
    if not is_trading_time():
        print("[strategy_live] 非交易时段，跳过")
        return

    by_sym = load_all_quotes()
    if not by_sym or not any(quotes for quotes in by_sym.values()):
        print("[strategy_live] 无行情数据")
        return

    account = load_account_state()
    prev_has_pos = any(p.get("quantity", 0) > 0 for p in account.get("positions", {}).values())
    prev_equity = account.get("equity", INITIAL_CASH)

    # 找出最新一轮的时间边界
    all_ts = [q["ts"] for qs in by_sym.values() for q in qs]
    latest_ts = max(all_ts)
    latest_minute = latest_ts[:16]  # YYYY-MM-DDTHH:MM

    runner = StrategyRunner()
    runner.add_default_strategies()
    fills = []
    total_upnl = 0
    total_margin = 0

    for sym, quotes in sorted(by_sym.items()):
        runner.sync_positions(account.get("positions", {}))
        last_sig_ts = account.get("last_signal_ts", {}).get(sym, "")

        for q in quotes:
            signals = runner.on_quote(q, account.get("positions", {}))
            if not signals:
                continue

            sig_ts = q.get("ts", "")
            is_latest_batch = sig_ts.startswith(latest_minute)

            for sig in signals:
                # 信号间隔过滤
                if last_sig_ts and sig_ts:
                    try:
                        gap = (datetime.fromisoformat(sig_ts) - datetime.fromisoformat(last_sig_ts)).total_seconds()
                        if gap < MIN_SIGNAL_GAP_S:
                            continue
                    except (ValueError, TypeError):
                        pass
                # 仅执行最新轮信号
                if not is_latest_batch:
                    continue
                fill = execute_signal(sig, account, q)
                if fill:
                    fills.append(fill)

    # 计算权益
    positions = account.get("positions", {})
    for sym, pos in positions.items():
        qty = pos.get("quantity", 0)
        if qty == 0:
            continue
        sym_quotes = by_sym.get(sym, [])
        price = sym_quotes[-1]["price"] if sym_quotes else pos.get("avg_cost", 0)
        direction = pos.get("direction", "多")
        cost = pos.get("avg_cost", 0)
        mult = MULTIPLIERS.get(sym, 10)
        pnl = (price - cost) * mult * qty if direction == "多" else (cost - price) * mult * qty
        total_upnl += pnl
        total_margin += calc_margin(sym, price, qty)
        pos["current_price"] = price
        pos["unrealized_pnl"] = round(pnl, 2)
        pos["pnl_pct"] = round((price / cost - 1) * 100, 2) if cost > 0 else 0

    equity = account["cash"] + total_upnl
    free_cash = account["cash"] - total_margin
    pos_count = sum(1 for p in positions.values() if p.get("quantity", 0) > 0)

    account["equity"] = round(equity, 2)
    if equity > account.get("peak_equity", INITIAL_CASH):
        account["peak_equity"] = round(equity, 2)
    account["free_cash"] = round(free_cash, 2)
    save_account_state(account)

    # ── 推送决策 ──
    has_pos = pos_count > 0
    should_push = bool(fills) or (has_pos != prev_has_pos)
    if has_pos and not should_push:
        eq_change = abs(equity - prev_equity) / prev_equity * 100 if prev_equity > 0 else 0
        if eq_change >= 1.0:
            should_push = True

    if should_push:
        lines = []
        for f in fills:
            emoji = "🟢" if f["action"] in ("BUY",) or (f["action"] == "CLOSE" and f["pnl"] >= 0) else "🔴"
            pnl_s = f" PnL={f['pnl']:+.0f}" if f.get("pnl") else ""
            lines.append(f"{emoji} {f['symbol']} {f['action']} {f['qty']}手 @{f['price']:.0f}{pnl_s}")

        for sym, pos in sorted(positions.items()):
            qty = pos.get("quantity", 0)
            if qty == 0:
                continue
            pnl = pos.get("unrealized_pnl", 0)
            cost = pos.get("avg_cost", 0)
            price = pos.get("current_price", 0)
            emoji = "🟢" if pnl >= 0 else "🔴"
            name = SYMBOL_NAMES.get(sym, sym)
            pnl_pct = pos.get("pnl_pct", 0)
            lines.append(f"{emoji} {sym} {name} {pos.get('direction','')}{qty}手 成本{cost:.0f} 现价{price:.0f} 浮盈{pnl:+.0f}({pnl_pct:+.1f}%)")

        lines.append(f"权益 ¥{equity:,.0f}")
        push_body = "\n".join(lines)

        if os.path.exists(_PUSH_SCRIPT):
            subprocess.Popen(
                ["node", _PUSH_SCRIPT, "🔥 期货", push_body],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    print(
        f"[strategy_live] equity={equity:.0f} "
        f"pos={pos_count} margin={total_margin:.0f} "
        f"upnl={total_upnl:.0f} trades={len(fills)}"
    )


if __name__ == "__main__":
    main()
