#!/usr/bin/env python3
"""
trading-runtime — live_session.py

Phase 6.4 Live Paper Trading — 长驻运行入口 (含实时策略)

职责:
  - 账户初始化 (10,000,000 CNY)
  - 实时行情流启动 (market_stream)
  - 实时策略运行 (strategy_runner: MA/Breakout/RSI/ActivityTest)
  - 策略信号 → ORDER → FILL → POSITION
  - 连续盯市估值 + 风险快照
  - 周期状态持久化
  - 优雅关闭 (SIGINT/SIGTERM)

架构 (v2):
  实时时钟
     ↓
  market_stream.py
     ↓  FUTURES_QUOTE
     ↓
  strategy_runner.py  ←── 4 策略 (MA/Breakout/RSI/ActivityTest)
     ↓  FUTURES_SIGNAL
     ↓
  signal_receiver → ORDER
     ↓
  paper_executor → FILL
     ↓
  runtime_account → POSITION
     ↓
  market_monitor + valuation + risk_snapshot
     ↓
  strategy_runner.sync_positions() (每 N 条 QUOTE)
     ↓
  状态持久化

使用:
  python3 live_session.py [--speed 10] [--no-strategy] [--signals signal.jsonl]
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone, timedelta

from market_stream import MarketStream
from signal_receiver import generate_orders
from paper_executor import PaperExecutor
from runtime_account import RuntimeAccount
from market_monitor import MarketMonitor
from valuation import PortfolioValuation
from risk_snapshot import RiskSnapshot
from account_init import load_config, create_account, init_status_report
from strategy_runner import StrategyRunner

BJT = timezone(timedelta(hours=8))

# ── 路径 ──────────────────────────────────────────────────
WORKSPACE = os.path.dirname(os.path.abspath(__file__))
MARKET_FUTURES_DIR = os.path.join(WORKSPACE, "..", "market_futures")
HISTORICAL_DIR = os.path.join(MARKET_FUTURES_DIR, "data", "historical")
STATE_DIR = os.path.join(WORKSPACE, "state")
REPORTS_DIR = os.path.join(WORKSPACE, "reports")

SESSION_RUNNING = True


def signal_handler(sig, frame):
    """优雅关闭"""
    global SESSION_RUNNING
    print(f"\n[live_session] 🛑 收到信号 {sig}, 正在停止...")
    SESSION_RUNNING = False


def find_signal_file() -> str | None:
    """查找最近的信号文件"""
    candidates = [
        os.path.join(MARKET_FUTURES_DIR, "data", "historical",
                     "replay_akshare_6sym.jsonl"),
        os.path.join(MARKET_FUTURES_DIR, "futures_events.jsonl"),
        os.path.join(REPORTS_DIR, "runtime_events.jsonl"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def load_signals_from_file(path: str) -> list[dict]:
    """从 JSONL 加载 SIGNAL 事件"""
    signals = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            evt = json.loads(line)
            if evt.get("event_type") in ("FUTURES_SIGNAL", "SIGNAL"):
                signals.append(evt)
            elif evt.get("strategy_id") and evt.get("action"):
                signals.append(evt)
    return signals


def build_signal_index(signals: list[dict]) -> dict[str, list[dict]]:
    """按品种建立信号索引 (按时间排序)"""
    index: dict[str, list[dict]] = {}
    for sig in signals:
        sym = sig.get("symbol", "")
        if not sym:
            continue
        index.setdefault(sym, []).append(sig)
    for sym in index:
        index[sym].sort(key=lambda x: x.get("ts", ""))
    return index


def signal_matches_bar(signals_for_sym: list[dict], bar_ts: str) -> list[dict]:
    """找出时间戳 <= bar_ts 的待匹配信号"""
    matched = []
    while signals_for_sym and signals_for_sym[0].get("ts", "") <= bar_ts:
        matched.append(signals_for_sym.pop(0))
    return matched


def get_position_info(account: RuntimeAccount) -> dict:
    """从账户提取持仓信息 (用于策略 position_info)"""
    info = {}
    summary = account.summary()
    positions = summary.get("positions", {})
    for sym, p in positions.items():
        info[sym] = {
            "qty": p["qty"],
            "direction": "LONG" if p["qty"] > 0 else "SHORT",
            "avg_cost": p["avg_cost"],
            "unrealized_pnl": p["unrealized_pnl"],
        }
    return info


def format_elapsed(seconds: float) -> str:
    """格式化运行时长"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    elif m > 0:
        return f"{m}m{s:02d}s"
    else:
        return f"{s}s"


def print_status_bar(account: RuntimeAccount, stream: MarketStream,
                     risk: RiskSnapshot, start_time: float,
                     quotes_emitted: int, fills_count: int,
                     signals_count: int = 0):
    """实时状态条"""
    elapsed = time.time() - start_time
    stream_summary = stream.summary()
    risk_summary = risk.summary()
    latest = risk_summary.get("current", {})

    dd = latest.get("drawdown", 0)
    dd_pct = latest.get("drawdown_pct", 0)

    bar = (
        f"\r⏱ {format_elapsed(elapsed)}  "
        f"📊 {stream_summary['progress_pct']:.1f}% "
        f"({quotes_emitted}/{stream_summary['total_bars']})  "
        f"📡 {signals_count} SIG  "
        f"💱 {fills_count} FILL  "
        f"💰 ¥{account.equity:>10,.0f}  "
        f"📉 {dd:>+7,.0f} ({dd_pct:+.2f}%)  "
        f"📦 {len(account.positions)} 品种"
    )
    print(bar, end="", flush=True)


def main():
    global SESSION_RUNNING

    parser = argparse.ArgumentParser(
        description="Phase 6.4 Live Paper Trading (实时策略)")
    parser.add_argument("--speed", type=float, default=10.0,
                        help="行情输出间隔 (秒/条, 默认 10)")
    parser.add_argument("--signals", default=None,
                        help="信号文件路径 (覆盖策略运行器)")
    parser.add_argument("--no-strategy", action="store_true",
                        help="不启动实时策略, 仅加载信号文件")
    parser.add_argument("--data-dir", default=HISTORICAL_DIR,
                        help="历史数据目录路径")
    parser.add_argument("--save-interval", type=int, default=300,
                        help="状态保存间隔 (秒, 默认 300)")
    parser.add_argument("--max-events", type=int, default=0,
                        help="最大输出事件数 (0=不限)")
    parser.add_argument("--position-sync-interval", type=int, default=5,
                        help="持仓同步间隔 (条QUOTE, 默认 5)")
    args = parser.parse_args()

    # ── 信号处理 ──────────────────────────────────────────
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ── Banner ────────────────────────────────────────────
    start_time = time.time()
    print(f"\n{'🔥 Phase 6.4 — Live Paper Trading + Strategy 🔥':^60}")
    print(f"{'=' * 60}")
    print(f"  启动时间: {datetime.now(BJT).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  行情速度: {args.speed}s/条")
    print(f"  历史数据: {args.data_dir}")
    mode = "实时策略" if not args.no_strategy else "信号文件回放"
    print(f"  策略模式: {mode}")
    if args.no_strategy:
        print(f"  信号文件: {args.signals or '(自动查找)'}")
    print(f"{'=' * 60}")
    print()

    # ── Step 1: 账户初始化 (10,000,000 CNY) ──────────────
    config = load_config()
    if args.speed:
        if "market" not in config:
            config["market"] = {}
        if "stream" not in config["market"]:
            config["market"]["stream"] = {}
        config["market"]["stream"]["speed_sec"] = args.speed

    account = create_account(config)
    print()

    # ── Step 2: 策略 / 信号初始化 ────────────────────────
    strategy_runner = None
    use_precomputed_signals = args.no_strategy or args.signals

    if use_precomputed_signals:
        signal_path = args.signals or find_signal_file()
        all_signals = []
        if signal_path:
            all_signals = load_signals_from_file(signal_path)
            print(f"[live_session] 📥 预计算信号: {len(all_signals)} 条")
        else:
            print("[live_session] ⚠️ 未找到信号文件, 无交易信号输入")
        signal_index = build_signal_index(all_signals)
        print(f"  信号索引: {len(signal_index)} 品种")
        print()
    else:
        # 实时策略模式
        strategy_runner = StrategyRunner()
        strategy_runner.add_default_strategies()
        signal_index = {}  # 不使用预计算信号
        print()

    # ── Step 3: 启动行情流 ────────────────────────────────
    speed = args.speed if args.speed else \
        config.get("market", {}).get("stream", {}).get("speed_sec", 10.0)
    stream = MarketStream(speed_sec=speed)

    data_dir = args.data_dir or \
        config.get("market", {}).get("stream", {}).get(
            "history_dir", HISTORICAL_DIR)
    if data_dir.startswith(".."):
        data_dir = os.path.join(WORKSPACE, data_dir)

    if not os.path.exists(data_dir):
        print(f"[live_session] ❌ 数据目录不存在: {data_dir}")
        sys.exit(1)

    stream.load_historical_dir(data_dir)
    if stream.total_bars == 0:
        print("[live_session] ❌ 无行情数据")
        sys.exit(1)
    print()

    # ── Step 4: 运行时组件 ────────────────────────────────
    monitor = MarketMonitor()
    executor = PaperExecutor()
    pv = PortfolioValuation()
    risk = RiskSnapshot(initial_balance=account.initial_balance)

    max_events = args.max_events or \
        config.get("session", {}).get("max_events_per_session", 0)
    save_interval = args.save_interval or \
        config.get("session", {}).get("state_save_interval", 300)
    report_interval = config.get("session", {}).get("report_interval", 60)

    # ── Step 5: 运行循环 ──────────────────────────────────
    quotes_emitted = 0
    fills_count = 0
    signals_count = 0
    last_save_time = time.time()
    last_report_time = time.time()
    sync_counter = 0

    print(f"{'─' * 60}")
    print(f"  开始运行... (保存间隔: {save_interval}s, Ctrl+C 停止)")
    print(f"{'─' * 60}")

    try:
        for quote in stream.run():
            if not SESSION_RUNNING:
                stream.stop()
                break

            if max_events > 0 and quotes_emitted >= max_events:
                print(f"\n[live_session] ⏹ 已达最大事件数 {max_events}")
                break

            quotes_emitted += 1
            sym = quote.get("symbol", "")
            bar_ts = quote.get("ts", "")

            # ── 5a: 行情流入 ──
            monitor.feed(quote)

            # ── 5b: 获取信号 (实时策略 or 预计算) ──
            current_signals = []

            if strategy_runner:
                # 实时策略: QUOTE → 策略 → 信号
                pos_info = get_position_info(account)
                strategy_signals = strategy_runner.on_quote(quote, pos_info)
                current_signals.extend(strategy_signals)
            else:
                # 预计算信号: 按时间匹配
                matched = signal_matches_bar(
                    signal_index.get(sym, []), bar_ts)
                current_signals.extend(matched)

            # ── 5c: 信号 → ORDER → FILL ──
            if current_signals:
                orders = generate_orders(current_signals)
                signals_count += len(current_signals)
                for o in orders:
                    executor.feed_quote(quote)
                    fill = executor.execute(o)
                    if fill:
                        fills_count += 1
                        account.apply_fill(fill)

                        # 连续估值
                        pv.sync_from_account(account.positions)
                        market_snap = monitor.snapshot()
                        eq_info = pv.compute_equity(
                            account.balance, market_snap)
                        risk.record(eq_info, ts=bar_ts)

            # ── 5d: 持仓盯市 ──
            if account.positions:
                for sym_pos, pos in list(account.positions.items()):
                    if pos["qty"] != 0:
                        px = monitor.get_price(sym_pos)
                        if px is not None:
                            account.mark_to_market(sym_pos, px)

            # ── 5e: 策略持仓同步 ──
            if strategy_runner:
                sync_counter += 1
                if sync_counter >= args.position_sync_interval:
                    pos_info = get_position_info(account)
                    strategy_runner.sync_positions(pos_info)
                    sync_counter = 0

            # ── 5f: 状态保存 ──
            if time.time() - last_save_time >= save_interval:
                label = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                from run_runtime import save_state
                save_state(account, monitor, risk, label=label)
                last_save_time = time.time()

            # ── 5g: 状态条 ──
            if time.time() - last_report_time >= 1.0:
                print_status_bar(account, stream, risk, start_time,
                                 quotes_emitted, fills_count, signals_count)
                last_report_time = time.time()

    except KeyboardInterrupt:
        print(f"\n[live_session] 🛑 用户中断")

    elapsed = time.time() - start_time

    # ── Final Report ──────────────────────────────────────
    print(f"\n\n{'═' * 60}")

    # 策略统计
    if strategy_runner:
        sig_stats = strategy_runner.signal_stats()
        print(f"  📊 策略信号统计:")
        for sid, st in sig_stats.get("by_strategy", {}).items():
            acts = ", ".join(f"{a}={c}" for a, c in st["actions"].items())
            print(f"     {sid:15s}: {st['signals']:4d} 信号 ({acts})")
        print()

    print(f"  Phase 6.4 — Session Complete")
    print(f"{'═' * 60}")
    print(f"  运行时长: {format_elapsed(elapsed)}")
    print(f"  行情输出: {quotes_emitted} QUOTE")
    print(f"  策略信号: {signals_count} SIGNAL")
    print(f"  成交:     {fills_count} FILL")
    print(f"  最终权益: ¥{account.equity:>10,.2f}")
    print(f"  持仓品种: {len(account.positions)}")

    # 最终持仓
    pos_summary = account.summary().get("positions", {})
    if pos_summary:
        for sym, p in sorted(pos_summary.items()):
            dir_str = "多" if p["qty"] > 0 else "空"
            print(f"     {sym}: {dir_str} {abs(p['qty'])}手, "
                  f"成本¥{p['avg_cost']:.1f}, "
                  f"浮盈¥{p.get('unrealized_pnl', 0):+.2f}")

    risk_summary = risk.summary()
    if risk_summary.get("warnings"):
        print()
        for w in risk_summary["warnings"]:
            print(f"  {w}")

    # ── 保存最终状态 ──────────────────────────────────────
    label = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_final"
    from run_runtime import save_state
    save_state(account, monitor, risk, label=label)

    # ── 事件流保存 ────────────────────────────────────────
    events_path = os.path.join(REPORTS_DIR, "runtime_events.jsonl")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(events_path, "a" if os.path.exists(events_path) else "w",
              encoding="utf-8") as f:
        session_event = {
            "event_type": "SESSION",
            "ts": datetime.now(BJT).isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "quotes_emitted": quotes_emitted,
            "signals": signals_count,
            "fills": fills_count,
            "final_equity": round(account.equity, 2),
            "final_balance": round(account.balance, 2),
            "peak_equity": risk.peak_equity,
            "max_drawdown_pct": risk_summary.get("total_drawdown_pct", 0),
            "positions": {s: p["qty"]
                          for s, p in account.positions.items() if p["qty"] != 0},
        }
        if strategy_runner:
            session_event["strategy_signals"] = \
                strategy_runner.signal_stats()
        f.write(json.dumps(session_event, ensure_ascii=False) + "\n")

    print(f"\n  📦 事件流 → {events_path}")
    print(f"{'═' * 60}")
    print(f"{'🔥 Phase 6.4 LIVE PAPER TRADING COMPLETE 🔥':^60}")
    print(f"{'═' * 60}")
    print()


if __name__ == "__main__":
    main()
