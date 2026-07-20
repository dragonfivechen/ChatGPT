#!/usr/bin/env python3
"""trade/trade_ledger.py — 交易生命周期账本 v1

以"一次完整交易"为单位，追踪：
  开仓 → 持仓过程（排名/价格/峰值）→ 平仓 → 退出后观察

输入： events/ 下的信号 + 快照 + 排名
输出： events/trade_ledger.jsonl (append-only)

调用时机： run_strategy.py 末尾，组合快照之后
"""

import json
import os
from datetime import datetime, timezone, timedelta

_EVENTS_DIR = None
_LEDGER_PATH = None

# ── 事件类型 ──
TRADE_OPEN = "TRADE_OPEN"
TRADE_UPDATE = "TRADE_UPDATE"
TRADE_CLOSE = "TRADE_CLOSE"
TRADE_POST_EXIT = "TRADE_POST_EXIT"

_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def _ts() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _ensure_paths(events_dir: str):
    global _EVENTS_DIR, _LEDGER_PATH
    _EVENTS_DIR = events_dir
    _LEDGER_PATH = os.path.join(events_dir, "trade_ledger.jsonl")
    os.makedirs(events_dir, exist_ok=True)


def _read_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def _append_event(event: dict):
    with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _parse_rank(note: str) -> int:
    """从信号 note 中解析 rank={N}"""
    import re
    m = re.search(r"rank=(\d+)", note)
    return int(m.group(1)) if m else 0


def _next_trade_seq(symbol: str, existing_events: list[dict]) -> int:
    """为该 symbol 生成下一个 trade_id 序列号"""
    count = sum(
        1 for e in existing_events
        if e.get("event_type") == TRADE_OPEN
        and e.get("symbol") == symbol
    )
    return count + 1


def _make_trade_id(symbol: str, seq: int) -> str:
    date_part = datetime.now(_TZ).strftime("%Y%m%d")
    return f"RFV1_{symbol}_{date_part}_{seq:02d}"


def _build_snapshot_holdings(snapshots: list[dict]) -> dict:
    """从快照列表提取最新持仓：symbol → 持仓信息"""
    if not snapshots:
        return {}
    last = snapshots[-1]
    pf = last.get("portfolio", {})
    holdings = {}
    for h in pf.get("holdings", []):
        sym = h.get("symbol", "")
        holdings[sym] = {
            "quantity": h.get("quantity", 0),
            "avg_cost": h.get("avg_cost", 0),
            "price": h.get("current_price", 0),
            "weight": h.get("weight", 0),
        }
    return holdings


def _get_previous_snapshot_holdings(snapshots: list[dict]) -> dict:
    """获取倒数第二个快照的持仓（用于 diff）"""
    if len(snapshots) < 2:
        return {}
    prev = snapshots[-2]
    pf = prev.get("portfolio", {})
    holdings = {}
    for h in pf.get("holdings", []):
        sym = h.get("symbol", "")
        holdings[sym] = {
            "quantity": h.get("quantity", 0),
            "avg_cost": h.get("avg_cost", 0),
            "price": h.get("current_price", 0),
            "weight": h.get("weight", 0),
        }
    return holdings


# ── 公开 API ──


def rebuild(events_dir: str) -> dict:
    """重建内存状态：返回 {symbol: trade_id} 映射 + open_trades 详情"""
    _ensure_paths(events_dir)
    events = _read_jsonl(_LEDGER_PATH)

    open_trades = {}  # trade_id → event
    # 最新事件顺序遍历，被 CLOSE 的移出
    for e in events:
        tid = e.get("trade_id", "")
        et = e.get("event_type")
        if et == TRADE_OPEN:
            open_trades[tid] = {"event": e, "latest": e}
        elif et == TRADE_UPDATE:
            if tid in open_trades:
                open_trades[tid]["latest"] = e
        elif et == TRADE_CLOSE:
            open_trades.pop(tid, None)

    symbol_to_trade = {}
    for tid, state in open_trades.items():
        sym = state["event"].get("symbol", "")
        symbol_to_trade[sym] = tid

    return {
        "open_trades": open_trades,         # trade_id → {event, latest}
        "symbol_to_trade": symbol_to_trade,  # symbol → trade_id
        "all_events": events,
    }


def update(
    events_dir: str,
    signals: list[dict],
    rank_map: dict[str, int],
    score_map: dict[str, float],
) -> list[dict]:
    """每次策略运行后调用"""
    _ensure_paths(events_dir)

    # 1. 读取当前状态
    state = rebuild(events_dir)
    open_trades = state["open_trades"]
    symbol_to_trade = state["symbol_to_trade"]
    existing = state["all_events"]

    # 2. 读取当前快照
    snapshots = _read_jsonl(os.path.join(events_dir, "portfolio_snapshots.jsonl"))
    current_holdings = _build_snapshot_holdings(snapshots)
    prev_holdings = _get_previous_snapshot_holdings(snapshots)

    now_ts = _ts()
    new_events = []

    # 3. 检测每种情况
    current_symbols = set(current_holdings.keys())
    open_symbols = set(symbol_to_trade.keys())

    # ── 新开仓：当前持仓但无对应 open trade ──
    for sym in current_symbols - open_symbols:
        info = current_holdings[sym]
        # 从本次信号找建仓相关 note
        rank = 0
        entry_reason = "L3_TOP5"
        entry_qty = info["quantity"]

        # 从当前排名获取
        rank = rank_map.get(sym, 0)
        score = score_map.get(sym, 0)

        # 从当前 batch 信号中提取额外信息
        for sig in signals:
            s_sym = sig.get("symbol", "")
            s_action = sig.get("action", "")
            if s_sym == sym and s_action == "BUY":
                rank = _parse_rank(sig.get("note", "")) or rank
                entry_qty = sig.get("quantity", entry_qty)
                entry_reason = "L3_TOP5" if "建仓" in sig.get("note", "") else "RANK_UP"

        seq = _next_trade_seq(sym, existing)
        trade_id = _make_trade_id(sym, seq)
        event = {
            "event_type": TRADE_OPEN,
            "trade_id": trade_id,
            "timestamp": now_ts,
            "symbol": sym,
            "strategy": "RANK_FOLLOW_V1",
            "entry": {
                "price": info["price"],
                "rank": rank,
                "score": score,
                "position_ratio": info["weight"],
                "reason": entry_reason,
                "quantity": entry_qty,
            },
        }
        _append_event(event)
        new_events.append(event)
        # 更新内存状态
        symbol_to_trade[sym] = trade_id
        open_trades[trade_id] = {"event": event, "latest": event}

    # ── 持仓更新：两者都有 → UPDATE ──
    for sym in current_symbols & open_symbols:
        trade_id = symbol_to_trade[sym]
        info = current_holdings[sym]
        rank = rank_map.get(sym, 0)
        prev_state = open_trades.get(trade_id, {})
        prev_event = prev_state.get("latest", {})
        prev_peak = prev_event.get("peak", {})

        # 计算峰值
        price = info["price"]
        avg_cost = info["avg_cost"]
        profit_pct = (price / avg_cost - 1) * 100 if avg_cost > 0 else 0

        max_price = prev_peak.get("max_price", info["price"])
        if price > max_price:
            max_price = price
        max_profit_pct = prev_peak.get("max_profit_pct", profit_pct)
        if profit_pct > max_profit_pct:
            max_profit_pct = profit_pct
        drawdown_pct = (max_price - price) / max_price * 100 if max_price > 0 else 0

        # 只记录变化
        event = {
            "event_type": TRADE_UPDATE,
            "trade_id": trade_id,
            "timestamp": now_ts,
            "symbol": sym,
            "update": {
                "price": price,
                "rank": rank,
                "profit_pct": round(profit_pct, 2),
                "quantity": info["quantity"],
                "position_ratio": info["weight"],
            },
            "peak": {
                "max_price": round(max_price, 4),
                "max_profit_pct": round(max_profit_pct, 2),
                "drawdown_pct": round(drawdown_pct, 2),
            },
        }
        _append_event(event)
        new_events.append(event)
        open_trades[trade_id]["latest"] = event

    # ── 平仓：open trade 存在但不在当前持仓 ──
    exited = open_symbols - current_symbols
    for sym in exited:
        trade_id = symbol_to_trade[sym]
        entry_event = open_trades[trade_id]["event"]
        latest = open_trades[trade_id]["latest"]

        entry_info = entry_event.get("entry", {})
        entry_price = entry_info.get("price", 0)
        entry_ts = entry_event.get("timestamp", "")

        # 计算退出价格和收益
        # 从最新 UPDATE 或 signal 中获取
        exit_price = latest.get("update", {}).get("price", 0)
        exit_rank = latest.get("update", {}).get("rank", 0)

        # 计算最终的 return
        holding_return = (exit_price / entry_price - 1) * 100 if entry_price > 0 else 0

        # 计算持仓天数
        try:
            dt_entry = datetime.fromisoformat(entry_ts[:19])
            dt_exit = datetime.fromisoformat(now_ts[:19])
            holding_days = (dt_exit - dt_entry).days
        except (ValueError, TypeError):
            holding_days = 0

        # 从信号中推断退出原因
        exit_reason = "UNKNOWN"
        total_sold = 0
        for sig in signals:
            s_sym = sig.get("symbol", "")
            s_action = sig.get("action", "")
            if s_sym == sym and s_action == "SELL":
                total_sold += sig.get("quantity", 0)

                # 判断触发原因
                note = sig.get("note", "")
                if "止损" in note:
                    exit_reason = "STOP_LOSS"
                elif "止盈" in note and "回撤" not in note:
                    exit_reason = "TAKE_PROFIT"
                elif "回撤" in note:
                    exit_reason = "DRAWDOWN"
                elif "替换" in note:
                    exit_reason = "REPLACE"
                elif "rank" in note and ("减调" in note or "减仓" in note):
                    exit_reason = "RANK_DROP"

        # 如果 signals 中没有，查看之前的 note
        if exit_reason == "UNKNOWN":
            prev_note = latest.get("update", {}).get("note", "")
            if prev_note:
                if "止损" in prev_note:
                    exit_reason = "STOP_LOSS"
                elif "回撤" in prev_note:
                    exit_reason = "DRAWDOWN"
                elif "替换" in prev_note:
                    exit_reason = "REPLACE"
                elif "rank" in prev_note:
                    exit_reason = "RANK_DROP"

        event = {
            "event_type": TRADE_CLOSE,
            "trade_id": trade_id,
            "timestamp": now_ts,
            "symbol": sym,
            "exit": {
                "price": exit_price,
                "rank": exit_rank,
                "exit_reason": exit_reason,
                "return_pct": round(holding_return, 2),
                "holding_days": holding_days,
                "exit_quantity": total_sold,
            },
        }
        _append_event(event)
        new_events.append(event)

        # 已平仓，准备 post-exit 跟踪
        _init_post_exit(
            trade_id=trade_id,
            symbol=sym,
            exit_price=exit_price,
            exit_rank=exit_rank,
            exit_reason=exit_reason,
            return_pct=holding_return,
            holding_days=holding_days,
        )

    return new_events


def _init_post_exit(
    trade_id: str,
    symbol: str,
    exit_price: float,
    exit_rank: int,
    exit_reason: str,
    return_pct: float,
    holding_days: int,
):
    """初始化退出后跟踪状态（在现有数据中记录首个 post-exit 入口标记）

    TRADE_POST_EXIT 事件由后续的报价触发更新，
    当前只记录一个占位标记，表明该 trade 已进入退出后观察期。
    """
    event = {
        "event_type": TRADE_POST_EXIT,
        "trade_id": trade_id,
        "timestamp": _ts(),
        "symbol": symbol,
        "post_exit": {
            "days_since_exit": 0,
            "price": exit_price,
            "return_since_exit_pct": 0.0,
            "status": "TRACKING",
        },
    }
    _append_event(event)


def update_post_exit(
    events_dir: str,
    symbol_price: dict[str, float],
) -> list[dict]:
    """更新退出后跟踪（后续行情的后处理调用）

    读取已平仓的 trade_id，检查是否在跟踪期内，
    如果是，追加 TRADE_POST_EXIT 事件。
    """
    _ensure_paths(events_dir)

    events = _read_jsonl(_LEDGER_PATH)
    if not events:
        return []

    # 找最近未完成跟踪的平仓记录
    closed_trades = {}  # trade_id → exit_event
    tracking_trades = {}  # trade_id → latest_post_exit

    for e in events:
        tid = e.get("trade_id", "")
        et = e.get("event_type")
        if et == TRADE_CLOSE:
            closed_trades[tid] = e
            tracking_trades.pop(tid, None)  # 新平仓重置跟踪状态
        elif et == TRADE_POST_EXIT:
            tracking_trades[tid] = e

    now_ts = _ts()
    new_events = []

    for tid, close_evt in closed_trades.items():
        sym = close_evt.get("symbol", "")
        exit_info = close_evt.get("exit", {})
        exit_price = exit_info.get("price", 0)
        exit_ts = close_evt.get("timestamp", "")

        # 检查天数
        try:
            dt_exit = datetime.fromisoformat(exit_ts[:19])
            dt_now = datetime.fromisoformat(now_ts[:19])
            days_since = (dt_now - dt_exit).days
        except (ValueError, TypeError):
            days_since = 0

        # 最多跟踪 5 天
        if days_since > 5:
            continue

        # 获取当前价格
        current_price = symbol_price.get(sym, 0)
        if current_price <= 0:
            continue

        return_since = (current_price / exit_price - 1) * 100 if exit_price > 0 else 0

        event = {
            "event_type": TRADE_POST_EXIT,
            "trade_id": tid,
            "timestamp": now_ts,
            "symbol": sym,
            "post_exit": {
                "days_since_exit": days_since,
                "price": current_price,
                "return_since_exit_pct": round(return_since, 2),
                "status": "COMPLETE" if days_since >= 5 else "TRACKING",
            },
        }
        _append_event(event)
        new_events.append(event)

    return new_events


# ── 查询 API ──


def summarize(events_dir: str) -> dict:
    """返回交易账本摘要"""
    _ensure_paths(events_dir)
    events = _read_jsonl(_LEDGER_PATH)

    trades = {}
    for e in events:
        tid = e.get("trade_id", "")
        if tid not in trades:
            trades[tid] = {"symbol": e.get("symbol", ""), "events": []}
        trades[tid]["events"].append(e.get("event_type", ""))

    # 统计
    open_count = 0
    open_info = []
    close_count = 0
    exit_reasons = {}

    for tid, info in trades.items():
        ev_types = info["events"]
        has_close = TRADE_CLOSE in ev_types
        has_post = TRADE_POST_EXIT in ev_types
        sym = info["symbol"]

        if has_close:
            close_count += 1
            # 提取退出原因
            for e in events:
                if e.get("trade_id") == tid and e.get("event_type") == TRADE_CLOSE:
                    reason = e.get("exit", {}).get("exit_reason", "UNKNOWN")
                    ret = e.get("exit", {}).get("return_pct", 0)
                    days = e.get("exit", {}).get("holding_days", 0)
                    exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
                    break
        else:
            open_count += 1
            # 提取当前状态
            for e in reversed(events):
                if e.get("trade_id") == tid and e.get("event_type") == TRADE_UPDATE:
                    u = e.get("update", {})
                    p = e.get("peak", {})
                    open_info.append({
                        "symbol": sym,
                        "price": u.get("price", 0),
                        "rank": u.get("rank", 0),
                        "profit_pct": u.get("profit_pct", 0),
                        "max_profit_pct": p.get("max_profit_pct", 0),
                        "drawdown_pct": p.get("drawdown_pct", 0),
                    })
                    break

    live_metrics = {}
    if open_info:
        live_metrics = {
            "avg_profit_pct": round(sum(o["profit_pct"] for o in open_info) / len(open_info), 2),
            "max_drawdown": round(max(o["drawdown_pct"] for o in open_info), 2),
            "best_profit": round(max(o["profit_pct"] for o in open_info), 2),
            "worst_profit": round(min(o["profit_pct"] for o in open_info), 2),
        }

    return {
        "total_trades": len(trades),
        "open_trades": open_count,
        "closed_trades": close_count,
        "exit_reason_distribution": exit_reasons,
        "live": live_metrics,
        "open_details": open_info,
    }


# ── CLI ──

if __name__ == "__main__":
    import sys
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ev_dir = os.path.join(base, "events")
    action = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if action == "summary":
        s = summarize(ev_dir)
        print(json.dumps(s, ensure_ascii=False, indent=2))
    elif action == "rebuild":
        s = rebuild(ev_dir)
        print(f"open_trades: {len(s['open_trades'])}")
        print(f"total_events: {len(s['all_events'])}")
        print(f"symbols_tracked: {list(s['symbol_to_trade'].keys())}")
    else:
        print(f"usage: {sys.argv[0]} [summary|rebuild]")
